# Open-source detectors

`scripts/detectors.py` scores every item of a dataset JSONL (`{"id", "text", ...}` per line) with AI-text detectors and the lexical lists, and writes one line per item: `{"id": ..., "scores": {method: float}}`. Higher is more AI for every method. It is resumable: an id already scored for a method is skipped, and the file is rewritten after each method, so a crash loses at most one method.

## Setup

```bash
python3 -m venv ~/.cache/humanize-detect-venv && ~/.cache/humanize-detect-venv/bin/pip install torch transformers sentencepiece safetensors huggingface_hub scikit-learn pyyaml matplotlib
```

Behind a proxy, set `HTTPS_PROXY` and `HTTP_PROXY` (`http://fwdproxy:8080` on Meta hosts) and `HF_HUB_DISABLE_XET=1`. Models download by Hugging Face ID into the standard cache (`HF_HOME` moves it); `--models-dir DIR` reads a local mirror laid out as `DIR/<org>/<model>` instead.

Run from a cwd outside fbcode with `env -u PYTHONPATH`: fbcode's `dill` and the host `PYTHONPATH` shadow the venv's packages. Pick one GPU with `CUDA_VISIBLE_DEVICES`; classifiers run in fp16 and the Falcon pair in bf16 on GPU; CPU works, slowly.

```bash
cd /tmp && env -u PYTHONPATH CUDA_VISIBLE_DEVICES=1 HTTPS_PROXY=http://fwdproxy:8080 HTTP_PROXY=http://fwdproxy:8080 HF_HUB_DISABLE_XET=1 \
  ~/.cache/humanize-detect-venv/bin/python ~/workspace/skills/humanize/scripts/detectors.py \
  --input passages.jsonl --out scores.jsonl [--methods roberta-openai,desklib] [--batch 32]
```

## Methods

| id | method | input cap | licence |
|---|---|---|---|
| `roberta-openai` | openai-community/roberta-base-openai-detector, P(`Fake`), label index 0 | 512 tokens | MIT |
| `desklib` | desklib/ai-text-detector-v1.01 (DeBERTa-v3-large, mean-pooled linear head, sigmoid) | 768 | MIT |
| `superannotate` | SuperAnnotate/ai-detector (RoBERTa-large, linear head `dense` on the first token, sigmoid; rebuilt from the safetensors keys with roberta-large's config) | 512 | SAIPL |
| `mpu-env3`, `mpu-env3short` | yuchuantian/AIGC_detector_env3 and env3short, P(`LABEL_1`) | 512 | Apache-2.0 |
| `binoculars` | negated Binoculars score, tiiuae/falcon-7b observer and falcon-7b-instruct performer | 512 | Apache-2.0 |
| `fast-detectgpt` | analytic Fast-DetectGPT criterion, falcon-7b sampling, falcon-7b-instruct scoring | 512 | Apache-2.0 |
| `lex-*` | `scripts/lexical.py`: vale-ai-tells per rule and any, antislop regexes and phrases, slop-score words and trigrams, humanize tells; counts per 100 words | all | see `data/oss/LICENSES.md` |

SuperAnnotate's SAIPL licence is AGPL-style: fine for evaluation, do not redistribute the weights. The MPU configs carry no label names; `LABEL_1` is AI per MPU's training code. roberta-openai was trained on GPT-2 output and scores modern chatbot prose as human, so expect it near or below chance. `binoculars` and `fast-detectgpt` come from one pass over both Falcon models (about 28 GiB peak on one GPU) with `--batch` capped at 8.
