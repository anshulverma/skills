#!/usr/bin/env python3
"""Score how much a markdown doc reads as AI-generated: 0 is clean, 100 is all slop.

Usage: slop_score.py ORIGINAL [PASS1 PASS2 ...] [--detail]

Pass the files in order (the original first, then each humanize pass) to get
the score trajectory and the drop from the original. --detail prints every
tell count and shape metric behind each score.

The score is normalised per 1,000 words, so a longer doc does not score worse
for being longer. Every count is a place to look, not a verdict. Code spans and
fenced blocks are skipped so identifiers do not count as prose.
"""

import re
import statistics
import sys

TELLS = {
    "em/en dash": r"[—–]",
    "bold run-in label": r"(?m)^\s*(?:[-*]|\d+\.)?\s*\*\*[^*\n]{1,60}?[.:]\*\*",
    "arguing contrast": r"\b(?:rather than|instead of|would have|does not mean|what this buys)\b",
    "x-not-y frame": r",\s+not\s+\w+",
    "announcement": r"\b(?:in (?:two|three|four|five) ways|(?:two|three|four|five) things|as follows|the following (?:sections?|points?))\b",
    "hedge clause": r"\b(?:seems? to|appears? to|may potentially|could potentially|it is possible that|arguably)\b",
    "process narration": r"\b(?:I (?:found|noticed|looked|checked|couldn't|can't|could not)|we (?:found|noticed|looked))\b",
    "signpost": r"\b(?:it(?:'s| is) worth noting|importantly|crucially|notably|in short|bottom line|the key (?:insight|point|takeaway)|here's the thing|that said|put simply)\b",
    "puffery": r"\b(?:robust|seamless(?:ly)?|leverag(?:e|es|ing)|delve|comprehensive|holistic|cutting-edge|tapestry|pivotal|underscores?|showcas(?:e|es|ing)|streamlin(?:e|es|ing)|empower(?:s|ing)?|foster(?:s|ing)?|realm|intricate|in today's)\b",
    "-side/-path coinage": r"\b[a-z]+-(?:side|path)\b",
    "semicolon chain": r";",
    "blockquote": r"(?m)^\s*>",
}

# Diff, task, SEV and paste numbers, and file:line pointers, that a reader would
# want to click. Counted only outside links.
REFERENCE = r"\b(?:D\d{7,}|T\d{8,}|S\d{6}|P\d{9,})\b|\b[\w/.-]+\.(?:py|cpp|h|php|thrift|yaml|cconf|md):\d+"
LINK = r"\[[^\]]*\]\([^)]*\)|<a\b[^>]*>.*?</a>|https?://\S+"
# A prose run longer than this many words with no heading, list, table,
# diagram, image or callout between its paragraphs reads as a wall of text.
WALL_WORDS = 300

# (weight, saturation): a component scores weight x min(1, value / saturation).
# Weights sum to 100. Calibrated on argument prose (proposals, reports): see
# the reference points in SKILL.md.
WEIGHTS = {
    "tells per 1k words": (30, 30.0),
    "bold spans per 1k words": (10, 15.0),
    "list share above 30%": (10, 0.5),
    "one-sentence paragraph share": (10, 0.6),
    "sentence-length uniformity": (10, 0.35),
    "headings per 1k words above 4": (5, 8.0),
    "unlinked references per 1k words": (15, 10.0),
    "share of prose in walls of text": (10, 0.5),
}

LIST_LINE = re.compile(r"\s*(?:[-*]|\d+\.)\s")
NON_PROSE = re.compile(r"\s*(?:[-*#|>]|\d+\.)")


def prose_only(text: str) -> str:
    """Prose a reader reads: no code blocks, tables, images or link targets."""
    text = re.sub(r"(?s)```.*?```", "", text)
    text = re.sub(r"(?m)^\s*\|.*$", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"`[^`\n]*`", "x", text)


def paragraphs(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return [b for b in blocks if not NON_PROSE.match(b)]


def sentences(paras: list[str]) -> list[str]:
    out = []
    for p in paras:
        out += [s for s in re.split(r"(?<=[.!?])\s+", p.replace("\n", " ")) if s.strip()]
    return out


def wall_share(raw: str) -> float:
    """Share of prose words sitting in runs longer than WALL_WORDS."""
    text = re.sub(r"(?s)```.*?```", "\n\nBREAK\n\n", raw)
    text = re.sub(r"(?is)<(?:embed|img|aside|table)\b.*?(?:</\w+>|/?>)", "\n\nBREAK\n\n", text)
    run, walls, total = 0, 0, 0
    for block in [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()] + ["BREAK"]:
        if block == "BREAK" or NON_PROSE.match(block) or block.startswith("!["):
            walls += run if run > WALL_WORDS else 0
            run = 0
        else:
            n = len(block.split())
            run += n
            total += n
    return walls / max(total, 1)


def metrics(raw: str) -> tuple[dict[str, float], dict[str, int]]:
    unfenced = re.sub(r"(?s)```.*?```", "", raw)
    unlinked = len(re.findall(REFERENCE, re.sub(LINK, "", unfenced)))
    text = prose_only(raw)
    words = max(len(text.split()), 1)
    per_k = 1000.0 / words
    lines = [ln for ln in text.splitlines() if ln.strip()]
    bullets = sum(1 for ln in lines if LIST_LINE.match(ln))
    paras = paragraphs(text)
    sents = sentences(paras)
    lengths = [len(s.split()) for s in sents]
    one_sentence = sum(1 for p in paras if len(sentences([p])) == 1 and not p.rstrip().endswith(":"))
    headings = sum(1 for ln in lines if ln.lstrip().startswith("#"))
    tells = {n: len(re.findall(p, text, flags=re.IGNORECASE)) for n, p in TELLS.items()}
    cv = statistics.pstdev(lengths) / statistics.mean(lengths) if len(lengths) > 2 else 1.0
    list_share = bullets / max(bullets + len(paras), 1)
    m = {
        "words": words,
        "tells per 1k words": sum(tells.values()) * per_k,
        "bold spans per 1k words": len(re.findall(r"\*\*[^*\n]+\*\*", text)) * per_k,
        "list share above 30%": max(0.0, list_share - 0.3),
        "one-sentence paragraph share": one_sentence / max(len(paras), 1),
        # Human sentence lengths vary (coefficient of variation ~0.6+); generated
        # prose clusters (~0.3). Score how far below 0.6 the doc sits.
        "sentence-length uniformity": max(0.0, 0.6 - cv),
        "headings per 1k words above 4": max(0.0, headings * per_k - 4),
        "unlinked references per 1k words": unlinked * per_k,
        "share of prose in walls of text": wall_share(raw),
    }
    return m, tells


def score(m: dict[str, float]) -> float:
    return sum(w * min(1.0, m[k] / sat) for k, (w, sat) in WEIGHTS.items())


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--detail"]
    detail = "--detail" in sys.argv
    if not args:
        sys.exit(__doc__)
    results = []
    for path in args:
        m, tells = metrics(open(path, encoding="utf-8").read())
        results.append((path, score(m), m, tells))
        if detail:
            print(f"== {path}")
            for k in WEIGHTS:
                w, sat = WEIGHTS[k]
                print(f"  {k:32} {m[k]:8.2f}  -> {w * min(1.0, m[k] / sat):5.1f} / {w}")
            for k, v in tells.items():
                if v:
                    print(f"    {k:30} {v}")
    base_score, base_words = results[0][1], results[0][2]["words"]
    print(f"{'pass':6} {'slop':>5} {'change':>7} {'words':>6} {'vs orig':>8}  file")
    for i, (path, s, m, _) in enumerate(results):
        label = "orig" if i == 0 else f"v{i}"
        change = "" if i == 0 else f"{s - base_score:+.0f}"
        words = "" if i == 0 else f"{(m['words'] - base_words) / base_words:+.0%}"
        print(f"{label:6} {s:5.0f} {change:>7} {m['words']:6d} {words:>8}  {path}")


if __name__ == "__main__":
    main()
