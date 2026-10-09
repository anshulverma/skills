#!/usr/bin/env python3
"""Line-level slop classifier support: split a doc, score predictions, pick lines to label, add labels.

  slop_lines.py split DOC.md > lines.json          number the body sentences and list items
  slop_lines.py heldout OUTDIR [--set NAME]       examples (train split) + lines to classify (eval split)
  slop_lines.py eval PRED.json [--set NAME] [--log NOTE]   precision/recall/F1/AUC on labelled lines
  slop_lines.py freeze NAME                        pin today's eval split as a fixed eval set
  slop_lines.py metrics                            the logged eval history, oldest first
  slop_lines.py uncertain PRED.json [-n 20]        lines the classifier is least sure of, to label
  slop_lines.py add "TEXT" slop|human [--why ...] [--rewrite ...] [--source ...]   add one author label

PRED.json is the classifier agent's output, {"lines": [{"i", "text", "p_slop", "label", "why",
"rewrite"}]}, per references/slop-classifier.md. Labels live in data/slop_labels.jsonl, one
{"text", "label", "why", "rewrite", "source"} object per line; the author's labels are the
ground truth the classifier is measured against and learns from.

Each label's split is a hash of its text (one in three goes to eval), so a label never moves
between splits and the eval split only grows. `freeze` pins the eval split as it stands, so later
classifier versions can be compared on exactly the same lines; `eval --log` appends a row to
data/classifier_metrics.jsonl with the classifier prompt's hash, so the history shows which
change moved which number.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
LABELS = os.path.join(DATA, "slop_labels.jsonl")
METRICS = os.path.join(DATA, "classifier_metrics.jsonl")
PROMPT = os.path.join(HERE, "..", "references", "slop-classifier.md")
sys.path.insert(0, HERE)
from slop_score import APPENDIX, sentences, strip_frontmatter  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s.replace("\\", "")).replace("`", "").replace("*", "")).strip().lower()


def split(path: str) -> list[dict]:
    """Body sentences and list items, without tables, code, figures, headings or the appendix."""
    raw = APPENDIX.split(strip_frontmatter(re.sub(r"(?s)<!--.*?-->", "", open(path, encoding="utf-8").read())), 1)[0]
    raw = re.sub(r"(?s)```.*?```", "", raw)
    out = []
    for block in re.split(r"\n\s*\n", raw):
        for line in block.splitlines():
            s = line.strip()
            if not s or s.startswith(("|", "#", "!", "[image", "*Figure", "_Figure")):
                continue
            s = re.sub(r"^(?:[-*]|\d+\.)\s+", "", s)
            out += sentences([s])
    return [{"i": i, "text": t} for i, t in enumerate(out, 1)]


def key(text: str) -> str:
    return hashlib.sha1(norm(text).encode()).hexdigest()[:12]


def split_of(text: str) -> str:
    return "eval" if int(key(text), 16) % 3 == 0 else "train"


def records(path: str = LABELS, split: str | None = None, set_name: str | None = None) -> list[dict]:
    rs = [r for r in map(json.loads, open(path, encoding="utf-8")) if r.get("label") in ("slop", "human")]
    if split:
        rs = [r for r in rs if split_of(r["text"]) == split]
    if set_name:
        keep = set(open(os.path.join(DATA, "eval_sets", f"{set_name}.txt")).read().split())
        rs = [r for r in rs if key(r["text"]) in keep]
    return rs


def load_labels(path: str, set_name: str | None = None) -> dict[str, str]:
    return {norm(r["text"]): r["label"] for r in records(path, set_name=set_name)}


def prompt_hash(path: str) -> str:
    """Hash of the prompt section only, so edits elsewhere in the reference do not split the history."""
    return hashlib.sha1(open(path, encoding="utf-8").read().split("## The prompt", 1)[-1].strip().encode()).hexdigest()[:8]


def auc(pos: list[float], neg: list[float]) -> float:
    """Probability a random slop line scores above a random human one (ties count half)."""
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def main() -> None:
    ap = argparse.ArgumentParser(usage=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split"); s.add_argument("doc")
    h = sub.add_parser("heldout"); h.add_argument("outdir"); h.add_argument("--set")
    e = sub.add_parser("eval"); e.add_argument("pred"); e.add_argument("--labels", default=LABELS)
    e.add_argument("--set"); e.add_argument("--log", metavar="NOTE")
    e.add_argument("--prompt", default=PROMPT, help="the prompt file the run used, when not the current one")
    f = sub.add_parser("freeze"); f.add_argument("name")
    sub.add_parser("metrics")
    u = sub.add_parser("uncertain"); u.add_argument("pred"); u.add_argument("-n", type=int, default=20)
    a = sub.add_parser("add"); a.add_argument("text"); a.add_argument("label", choices=["slop", "human"])
    a.add_argument("--why", default=""); a.add_argument("--rewrite", default="")
    a.add_argument("--source", default="author label")
    o = ap.parse_args()

    if o.cmd == "split":
        json.dump({"lines": split(o.doc)}, sys.stdout, indent=1)
    elif o.cmd == "heldout":
        os.makedirs(o.outdir, exist_ok=True)
        with open(os.path.join(o.outdir, "examples.jsonl"), "w") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in records(split="train"))
        ev = records(split="eval", set_name=o.set)
        json.dump({"lines": [{"i": i, "text": r["text"]} for i, r in enumerate(ev, 1)]}, open(os.path.join(o.outdir, "lines.json"), "w"), indent=1)
        print(f"{o.outdir}: {len(records(split='train'))} examples, {len(ev)} eval lines")
    elif o.cmd == "eval":
        gold = load_labels(o.labels, o.set)
        tp = fp = fn = tn = 0
        pos, neg = [], []
        for p in json.load(open(o.pred))["lines"]:
            g = gold.get(norm(p["text"]))
            if g is None:
                continue
            (pos if g == "slop" else neg).append(p["p_slop"])
            pred = p["label"] == "slop"
            tp += pred and g == "slop"; fp += pred and g == "human"
            fn += (not pred) and g == "slop"; tn += (not pred) and g == "human"
        n = tp + fp + fn + tn
        prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
        row = {"n": n, "n_slop": tp + fn, "precision": round(prec, 3), "recall": round(rec, 3),
               "f1": round(2 * prec * rec / max(prec + rec, 1e-9), 3), "accuracy": round((tp + tn) / max(n, 1), 3),
               "auc": round(auc(pos, neg), 3), "tp": tp, "fp": fp, "fn": fn, "tn": tn}
        print(f"labelled lines scored: {n}  precision {prec:.0%}  recall {rec:.0%}  F1 {row['f1']:.2f}  AUC {row['auc']:.2f}  accuracy {row['accuracy']:.0%}  (tp {tp} fp {fp} fn {fn} tn {tn})")
        if o.log:
            row = {"date": datetime.date.today().isoformat(), "set": o.set or "eval split", "note": o.log,
                   "prompt": prompt_hash(o.prompt),
                   "examples": len(records(split="train")), **row}
            with open(METRICS, "a") as fh:
                fh.write(json.dumps(row) + "\n")
    elif o.cmd == "freeze":
        os.makedirs(os.path.join(DATA, "eval_sets"), exist_ok=True)
        ev = records(split="eval")
        open(os.path.join(DATA, "eval_sets", f"{o.name}.txt"), "w").write("\n".join(key(r["text"]) for r in ev) + "\n")
        print(f"froze {len(ev)} eval lines as {o.name}")
    elif o.cmd == "metrics":
        print(f"{'date':10} {'set':10} {'n':>3} {'P':>5} {'R':>5} {'F1':>5} {'AUC':>5} {'ex':>3} prompt   note")
        for r in map(json.loads, open(METRICS)):
            print(f"{r['date']:10} {r['set']:10} {r['n']:3} {r['precision']:5.2f} {r['recall']:5.2f} {r['f1']:5.2f} {r['auc']:5.2f} {r['examples']:3} {r['prompt']} {r['note']}")
        groups: dict[tuple, list[dict]] = {}
        for r in map(json.loads, open(METRICS)):
            groups.setdefault((r["set"], r["prompt"], r["examples"]), []).append(r)
        print("\nmean over runs (min-max):")
        for (s, pr, ex), rs in groups.items():
            cell = lambda m: f"{sum(r[m] for r in rs) / len(rs):.2f} ({min(r[m] for r in rs):.2f}-{max(r[m] for r in rs):.2f})"
            print(f"  {s} prompt {pr} examples {ex}, {len(rs)} runs: P {cell('precision')}  R {cell('recall')}  F1 {cell('f1')}  AUC {cell('auc')}")
    elif o.cmd == "uncertain":
        lines = sorted(json.load(open(o.pred))["lines"], key=lambda p: abs(p["p_slop"] - 0.5))[: o.n]
        for p in sorted(lines, key=lambda p: p["i"]):
            print(f"{p['i']:3}. [{p['p_slop']:.2f}] {p['text']}")
    elif o.cmd == "add":
        with open(LABELS, "a", encoding="utf-8") as f:
            f.write(json.dumps({"text": o.text, "label": o.label, "why": o.why, "rewrite": o.rewrite, "source": o.source,
                                "date": datetime.date.today().isoformat()}) + "\n")
        print(f"added ({o.label}, {split_of(o.text)} split); {sum(1 for _ in open(LABELS))} labels")


if __name__ == "__main__":
    main()
