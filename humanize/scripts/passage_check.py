# scripts/passage_check.py
"""Advisory: which passages of a doc still read as machine-made, per the slop detector ensemble. Always exits 0.

Usage: passage_check.py DOC.md [--model PATH] [--json]
Model: --model, else $HUMANIZE_SLOP_MODEL, else the default below. Setup and numbers: references/detectors.md.
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from slop_score import APPENDIX, strip_frontmatter  # noqa: E402
from slop_text import cut_words, n_words, normalize, sentences  # noqa: E402

DEFAULT_MODEL = os.path.expanduser("~/workspace/models/nlp/slop_detector_ensemble_lr/slop_detector_ensemble_lr-v1.0.0.json")
MIN, MAX = 60, 400  # the passage lengths the model was trained on


def passages(raw: str) -> tuple[list[str], int]:
    """Body passages as the model saw them in training, and the count of leftovers under MIN words."""
    raw = APPENDIX.split(strip_frontmatter(re.sub(r"(?s)<!--.*?-->", "", raw)), 1)[0]
    raw = re.sub(r"(?s)(```|~~~).*?(\1|\Z)", "", raw)
    raw = re.sub(r"(?m)^\s*(?:\||!\[|\[image|[*_]Figure \d).*$", "", raw)
    out, skipped = [], 0
    for section in re.split(r"(?m)^\s{0,3}#{1,6}\s.*$", raw):
        buf = ""
        for para in re.split(r"\n\s*\n", section):
            buf = f"{buf} {normalize(para)}".strip()
            while n_words(buf) > MAX:  # cut at a sentence boundary; a single over-long sentence goes whole
                head = cut_words(buf, MAX) or sentences(buf, 0)[0]
                out.append(head)
                buf = buf[len(head):].strip()
            if n_words(buf) >= MIN:
                out.append(buf)
                buf = ""
        skipped += bool(buf)
    return out, skipped


def probability(model: dict, scores: dict) -> float:
    z = model["intercept"] + sum(c * (scores[f] - m) / s for f, c, m, s in
                                 zip(model["features"], model["coef"], model["mean"], model["scale"]))
    return 1 / (1 + math.exp(-z))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("--model")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    path = a.model or os.environ.get("HUMANIZE_SLOP_MODEL") or DEFAULT_MODEL
    if not os.path.exists(path):
        print(f"passage_check: no model at {path}; pass --model, or set HUMANIZE_SLOP_MODEL, or put it at {DEFAULT_MODEL}",
              file=sys.stderr)
        return
    model = json.load(open(path))
    texts, skipped = passages(open(a.doc, encoding="utf-8").read())
    import detectors  # after the model check; the classifiers need the detector venv
    cols = {f: detectors.score(f, texts, None) for f in model["features"]} if texts else {}
    rows = []
    for i, t in enumerate(texts):
        p = probability(model, {f: cols[f][i] for f in model["features"]})
        rows.append({"n": i + 1, "start": " ".join(t.split()[:8]), "words": n_words(t), "p": round(p, 3), "flag": p > model["threshold"]})
    flagged = sum(r["flag"] for r in rows)
    summary = (f"{flagged} of {len(rows)} passages read as machine-made "
               f"(threshold {model['threshold']:.2f}, 5% false-flag rate on human passages)")
    if a.json:
        print(json.dumps({"model": f"{model['name']}-v{model['version']}", "threshold": model["threshold"], "passages": rows,
                          "flagged": flagged, "scored": len(rows), "skipped_short": skipped, "summary": summary}, indent=1))
        return
    print(f"{'#':>3}  {'starts':<60}  {'p':>5}")
    for r in rows:
        print(f"{r['n']:>3}  {r['start'][:60]:<60}  {r['p']:>5.3f}  {'FLAG' if r['flag'] else ''}")
    print(summary + (f"; {skipped} passages under {MIN} words skipped" if skipped else ""))


if __name__ == "__main__":
    main()
