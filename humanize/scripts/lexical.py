# scripts/lexical.py
"""Lexical slop features from vendored open-source lists (data/oss/, see LICENSES.md). Stdlib only."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OSS = os.path.join(HERE, "..", "data", "oss")
sys.path.insert(0, HERE)
from slop_score import TELLS  # noqa: E402

_vale = {k: re.compile(v["pattern"], re.I if v["ignorecase"] else 0) for k, v in json.load(open(f"{OSS}/vale_ai_tells.json")).items()}
_anti = json.load(open(f"{OSS}/antislop.json"))
_anti_rx = [re.compile(r) for r in _anti["regexes"]]
_anti_ph = sorted({p.lower() for p in _anti["phrases"]})  # the list has case variants of the same phrase
_ss = json.load(open(f"{OSS}/slop_score.json"))
_ss_words, _ss_tri, _ss_stop = set(_ss["words"]), {tuple(t.split()) for t in _ss["trigrams"]}, frozenset(_ss["stopwords"])
_tells = [re.compile(p, re.I) for p in TELLS.values()]


def features(text: str) -> dict[str, float]:
    words = re.findall(r"[a-z']+", text.lower())
    per100 = 100.0 / max(1, len(words))
    long_w = [w for w in words if w not in _ss_stop]  # slop-score trigrams are built with NLTK stopwords removed
    out = {f"lex-vale-{k}": len(r.findall(text)) * per100 for k, r in _vale.items()}
    out["lex-vale-any"] = sum(out.values())
    low = text.lower()
    out["lex-antislop-regex"] = sum(len(r.findall(text)) for r in _anti_rx) * per100
    out["lex-antislop-phrase"] = sum(low.count(p) for p in _anti_ph) * per100
    out["lex-slopscore-word"] = sum(w in _ss_words for w in words) * per100
    out["lex-slopscore-trigram"] = sum(t in _ss_tri for t in zip(long_w, long_w[1:], long_w[2:])) * per100
    out["lex-humanize-tells"] = sum(len(r.findall(text)) for r in _tells) * per100
    return out
