#!/usr/bin/env python3
"""Line-level slop classifier support: split a doc, score predictions, pick lines to label, add labels.

  slop_lines.py split DOC.md > lines.json          number the body sentences and list items
  slop_lines.py eval PRED.json [--labels FILE]     precision/recall of predictions on labelled lines
  slop_lines.py uncertain PRED.json [-n 20]        lines the classifier is least sure of, to label
  slop_lines.py add "TEXT" slop|human [--why ...] [--rewrite ...]   add one author label

PRED.json is the classifier agent's output, {"lines": [{"i", "text", "p_slop", "label", "why",
"rewrite"}]}, per references/slop-classifier.md. Labels live in data/slop_labels.jsonl, one
{"text", "label", "why", "rewrite", "source"} object per line; the author's labels are the
ground truth the classifier is measured against and learns from.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "..", "data", "slop_labels.jsonl")
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


def load_labels(path: str) -> dict[str, str]:
    return {norm(r["text"]): r["label"] for r in map(json.loads, open(path, encoding="utf-8")) if r.get("label") in ("slop", "human")}


def main() -> None:
    ap = argparse.ArgumentParser(usage=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split"); s.add_argument("doc")
    e = sub.add_parser("eval"); e.add_argument("pred"); e.add_argument("--labels", default=LABELS)
    u = sub.add_parser("uncertain"); u.add_argument("pred"); u.add_argument("-n", type=int, default=20)
    a = sub.add_parser("add"); a.add_argument("text"); a.add_argument("label", choices=["slop", "human"])
    a.add_argument("--why", default=""); a.add_argument("--rewrite", default="")
    o = ap.parse_args()

    if o.cmd == "split":
        json.dump({"lines": split(o.doc)}, sys.stdout, indent=1)
    elif o.cmd == "eval":
        gold = load_labels(o.labels)
        tp = fp = fn = tn = 0
        for p in json.load(open(o.pred))["lines"]:
            g = gold.get(norm(p["text"]))
            if g is None:
                continue
            pred = p["label"] == "slop"
            tp += pred and g == "slop"; fp += pred and g == "human"
            fn += (not pred) and g == "slop"; tn += (not pred) and g == "human"
        n = tp + fp + fn + tn
        prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
        print(f"labelled lines scored: {n}  precision {prec:.0%}  recall {rec:.0%}  accuracy {(tp + tn) / max(n, 1):.0%}  (tp {tp} fp {fp} fn {fn} tn {tn})")
    elif o.cmd == "uncertain":
        lines = sorted(json.load(open(o.pred))["lines"], key=lambda p: abs(p["p_slop"] - 0.5))[: o.n]
        for p in sorted(lines, key=lambda p: p["i"]):
            print(f"{p['i']:3}. [{p['p_slop']:.2f}] {p['text']}")
    elif o.cmd == "add":
        with open(LABELS, "a", encoding="utf-8") as f:
            f.write(json.dumps({"text": o.text, "label": o.label, "why": o.why, "rewrite": o.rewrite, "source": "author label"}) + "\n")
        print(f"added ({o.label}); {sum(1 for _ in open(LABELS))} labels")


if __name__ == "__main__":
    main()
