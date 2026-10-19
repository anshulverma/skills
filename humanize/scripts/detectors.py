# scripts/detectors.py
"""Score dataset items with AI-text detectors and lexical lists. Resumable. Higher score = more AI.

Usage: detectors.py --input FILE.jsonl --out SCORES.jsonl [--methods m1,m2] [--models-dir DIR] [--batch 32]
Setup and method list: references/detectors.md.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lexical  # noqa: E402

HF = {"roberta-openai": "openai-community/roberta-base-openai-detector", "desklib": "desklib/ai-text-detector-v1.01",
      "superannotate": "SuperAnnotate/ai-detector", "mpu-env3": "yuchuantian/AIGC_detector_env3",
      "mpu-env3short": "yuchuantian/AIGC_detector_env3short", "roberta-large": "FacebookAI/roberta-large",
      "falcon": "tiiuae/falcon-7b", "falcon-instruct": "tiiuae/falcon-7b-instruct"}
MAXLEN = {"desklib": 768}
CLASSIFIERS = ["roberta-openai", "desklib", "superannotate", "mpu-env3", "mpu-env3short"]
LEXICAL = list(lexical.features(""))


def _src(key, models_dir):
    return os.path.join(models_dir, HF[key]) if models_dir and os.path.isdir(os.path.join(models_dir, HF[key])) else HF[key]


def _batches(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def classifier(method, texts, models_dir, batch=32):
    import torch
    from torch import nn
    from transformers import AutoConfig, AutoModel, AutoModelForSequenceClassification, AutoTokenizer, PreTrainedModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src = _src(method, models_dir)
    tok = AutoTokenizer.from_pretrained(src)
    if method == "desklib":
        class Desklib(PreTrainedModel):  # the model card's DesklibAIDetectionModel
            config_class = AutoConfig

            def __init__(self, c):
                super().__init__(c)
                self.model = AutoModel.from_config(c)
                self.classifier = nn.Linear(c.hidden_size, 1)
                self.post_init()

            def forward(self, input_ids, attention_mask):
                h = self.model(input_ids, attention_mask=attention_mask)[0].float()
                m = attention_mask.unsqueeze(-1).float()
                pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)
                return self.classifier(pooled.to(self.classifier.weight.dtype))[:, 0].float().sigmoid()
        m = Desklib.from_pretrained(src)
        run = lambda e: m(e["input_ids"], e["attention_mask"])  # noqa: E731
    elif method == "superannotate":
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        from transformers import RobertaModel

        class SuperAnnotate(nn.Module):  # generated_text_detector's RobertaClassifier: first token -> dense, sigmoid
            def __init__(self):
                super().__init__()
                try:
                    cfg = AutoConfig.from_pretrained(src)
                    assert cfg.model_type == "roberta"
                except Exception:  # the repo's config.json has no model_type; it was trained from roberta-large
                    cfg = AutoConfig.from_pretrained(_src("roberta-large", models_dir))
                self.roberta = RobertaModel(cfg, add_pooling_layer=False)
                self.dense = nn.Linear(cfg.hidden_size, 1)

            def forward(self, input_ids, attention_mask):
                return self.dense(self.roberta(input_ids, attention_mask=attention_mask)[0][:, 0])[:, 0].sigmoid()
        m = SuperAnnotate()
        weights = os.path.join(src, "model.safetensors") if os.path.isdir(src) else hf_hub_download(src, "model.safetensors")
        m.load_state_dict(load_file(weights), strict=True)
        run = lambda e: m(e["input_ids"], e["attention_mask"])  # noqa: E731
    else:
        m = AutoModelForSequenceClassification.from_pretrained(src)
        labels = {v.lower(): int(k) for k, v in m.config.id2label.items()}
        # MPU configs carry no id2label, so transformers names them LABEL_0/LABEL_1; LABEL_1 = AI per MPU's training code.
        ai = next((labels[k] for k in ("fake", "ai", "generated", "machine", "label_1") if k in labels), None)
        if ai is None:
            sys.exit(f"{method}: cannot tell the AI index from {m.config.id2label}")
        print(f"{method}: AI index {ai} of {m.config.id2label}", file=sys.stderr)
        run = lambda e: m(**e).logits.softmax(-1)[:, ai]  # noqa: E731
    m = m.to(dev).eval().half() if dev == "cuda" else m.eval()
    out = []
    with torch.no_grad():
        for b in _batches(texts, batch):
            e = tok(b, padding=True, truncation=True, max_length=MAXLEN.get(method, 512), return_tensors="pt").to(dev)
            out += run(e).float().cpu().tolist()
    return out


def falcon_pair(texts, models_dir, batch=8):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(_src("falcon", models_dir))
    tok.pad_token = tok.pad_token or tok.eos_token
    tok.padding_side = "right"
    kw = dict(dtype=torch.bfloat16) if dev == "cuda" else {}
    obs = AutoModelForCausalLM.from_pretrained(_src("falcon", models_dir), **kw).to(dev).eval()            # observer / reference
    perf = AutoModelForCausalLM.from_pretrained(_src("falcon-instruct", models_dir), **kw).to(dev).eval()  # performer / scorer
    bino, fdg = [], []
    with torch.no_grad():
        for b in _batches(texts, batch):
            e = tok(b, padding=True, truncation=True, max_length=512, return_tensors="pt", return_token_type_ids=False).to(dev)
            lo = obs(**e).logits[:, :-1].float()
            lp = perf(**e).logits[:, :-1].float()
            y = e["input_ids"][:, 1:]
            m = e["attention_mask"][:, 1:].float()
            lsp = lp.log_softmax(-1)
            ll = lsp.gather(-1, y.unsqueeze(-1)).squeeze(-1)                      # log p_perf(token)
            ppl = -(ll * m).sum(1) / m.sum(1)                                      # performer log-perplexity
            po = lo.softmax(-1)
            xent = (-(po * lsp).sum(-1) * m).sum(1) / m.sum(1)                     # observer->performer cross-entropy
            bino += (-(ppl / xent)).cpu().tolist()                                 # Binoculars: low ppl/xent = AI, negate
            mean = (po * lsp).sum(-1)
            var = (po * lsp.pow(2)).sum(-1) - mean.pow(2)
            fdg += (((ll - mean) * m).sum(1) / ((var * m).sum(1)).clamp(min=1e-9).sqrt()).cpu().tolist()
    if dev == "cuda":
        print(f"falcon_pair: batch {batch}, peak GPU {torch.cuda.max_memory_allocated() / 2**30:.1f} GiB", file=sys.stderr)
    return {"binoculars": bino, "fast-detectgpt": fdg}


FALCON = ["binoculars", "fast-detectgpt"]
_falcon_cache = {}


def score(method: str, texts: list[str], models_dir: str | None, batch: int = 32) -> list[float]:
    if method in LEXICAL:
        return [lexical.features(t)[method] for t in texts]
    if method in CLASSIFIERS:
        return classifier(method, texts, models_dir, batch)
    if method in FALCON:
        key = (tuple(texts), models_dir)
        if key not in _falcon_cache:
            _falcon_cache.clear()
            _falcon_cache[key] = falcon_pair(texts, models_dir, min(batch, 8))
        return _falcon_cache[key][method]
    sys.exit(f"unknown method {method}; known: {CLASSIFIERS + FALCON + LEXICAL}")


def _write(path, scores):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for i, s in scores.items():
            f.write(json.dumps({"id": i, "scores": s}) + "\n")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--methods", help="comma-separated method ids (default: all)")
    ap.add_argument("--models-dir", help="local mirror laid out as <dir>/<org>/<model>")
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args()
    items = [json.loads(line) for line in open(a.input) if line.strip()]
    scores = {}
    if os.path.exists(a.out):
        scores = {r["id"]: r["scores"] for r in (json.loads(line) for line in open(a.out) if line.strip())}
    for it in items:
        scores.setdefault(it["id"], {})
    for method in a.methods.split(",") if a.methods else CLASSIFIERS + FALCON + LEXICAL:
        todo = [it for it in items if method not in scores[it["id"]]]
        t0 = time.time()
        if todo:
            for it, s in zip(todo, score(method, [it["text"] for it in todo], a.models_dir, a.batch)):
                scores[it["id"]][method] = s
            _write(a.out, scores)
        print(f"{method}: {len(todo)} new in {time.time() - t0:.1f}s")


if __name__ == "__main__" and "--selftest-falcon" in sys.argv:
    pair = ["i cant beleive the build broke agian, fixed it by reverting the flag lol",
            "In conclusion, this comprehensive approach ensures robust and scalable outcomes for all stakeholders."]
    for k in FALCON:
        h, a = score(k, pair, None)
        print(f"{k}: human {h:.4f}  ai {a:.4f}  {'OK' if a > h else 'WRONG ORDER'}")
elif __name__ == "__main__":
    main()
