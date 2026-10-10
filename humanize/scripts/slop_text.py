"""Text utilities shared by the detector-eval dataset builders and harness (stdlib only)."""
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slop_score import sentences as _split  # noqa: E402

ID = re.compile(r"\b(?:D\d{6,}|T\d{6,}|S\d{5,}|P\d{8,})\b")
URL = re.compile(r"https?://\S+|www\.\S+")
MENTION = re.compile(r"(?<!\w)@\w+")


HEAD = re.compile(r"^\s{0,3}#{1,6}\s*(\S.*?)\s*$")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(\S.*?)\s*$")


def _end(s: str) -> str:
    return s if s[-1] in ".!?:" else s + "."


def _blocks(t: str) -> str:
    """Unwrap hard-wrapped lines, so headings and list items (wrapped or not) each become one sentence.
    Human docs wrap lines and AI output does not; anything line-based here would differ by label."""
    out = []
    for block in re.split(r"\n\s*\n", t):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines or all(re.match(r"( {4}|\t)", l) for l in lines):
            continue  # indented code block (a blank line precedes it; list continuations share a block)
        items = []
        for l in lines:
            if HEAD.match(l) or ITEM.match(l) or not items:
                items.append(l)
            else:
                items[-1] += " " + l.strip()
        out.append("\n".join(_end(m[1]) if (m := HEAD.match(i) or ITEM.match(i)) else i for i in items))
    return "\n\n".join(out)


def normalize(text: str) -> str:
    t = re.sub(r"(?s)(```|~~~).*?(\1|\Z)", " ", text)  # fenced code, including an unclosed fence
    t = "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("|"))
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = _blocks(t)
    t = re.sub(r"`([^`\n]+)`", r"\1", t)
    t = re.sub(r"(\*\*|\*)(\S(?:[^*\n]*?\S)?)\1", r"\2", t)
    t = re.sub(r"(?<!\w)(__|_)(\S.*?\S|\S)\1(?!\w)", r"\2", t)  # not inside snake_case words
    t = t.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "\u00a0": " "}))
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t) if p.strip()]  # hard-wrapped lines stay joined
    keep = [s for s in _split(paras) if not (URL.search(s) or MENTION.search(s) or ID.search(s))]
    return re.sub(r"\s+", " ", " ".join(keep)).strip()


def n_words(text: str) -> int:
    return len(text.split())


def sentences(text: str, min_words: int = 6) -> list[str]:
    return [s for s in _split([text]) if n_words(s) >= min_words]


def cut_words(text: str, n: int) -> str:
    out, total = [], 0
    for s in _split([text]):
        if total + n_words(s) > n:
            break
        out.append(s)
        total += n_words(s)
    return " ".join(out)


def near_verbatim(sent: str, others: list[str], thr: float = 0.8) -> bool:
    a = re.sub(r"\W+", " ", sent.lower()).strip()
    return any(difflib.SequenceMatcher(None, a, re.sub(r"\W+", " ", o.lower()).strip()).ratio() >= thr for o in others)


def _shingles(t: str, k: int = 5) -> set:
    w = re.findall(r"\w+", t.lower())
    return {tuple(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def dedupe(texts: list[str], thr: float = 0.5) -> list[int]:
    """Indices of texts kept after dropping any whose 5-word-shingle Jaccard with an earlier kept text is >= thr.
    ponytail: exact pairwise Jaccard, O(n^2) on ~1k items; switch to MinHash LSH past ~20k."""
    kept, sh = [], []
    for i, t in enumerate(texts):
        s = _shingles(t)
        if all(len(s & o) / max(1, len(s | o)) < thr for o in sh):
            kept.append(i)
            sh.append(s)
    return kept
