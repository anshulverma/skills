#!/usr/bin/env python3
"""Score how much a markdown doc reads as AI-generated: 0 is clean, 100 is all slop.

Usage: slop_score.py ORIGINAL [PASS1 PASS2 ...] [--detail] [--type slides]

Pass the files in order (the original first, then each humanize pass) to get
the score trajectory and the drop from the original. --detail prints every
tell count and shape metric behind each score.

The score is normalised per 1,000 words, so a longer doc does not score worse
for being longer. Every count is a place to look, not a verdict. Code spans and
fenced blocks are skipped so identifiers do not count as prose.

--type slides scores a deck instead: one slide per block between "---" lines,
speaker notes in "Notes:" paragraphs or ">" lines. It weighs words and bullets
on each slide, title length, topic-label titles and slides with no visual, and
the word count it prints is on-slide words only.
"""

import argparse
import re
import statistics

TELLS = {
    "em/en dash": r"[—–]",
    "bold run-in label": r"(?m)^\s*(?:[-*]|\d+\.)?\s*\*\*[^*\n]{1,60}?[.:]\*\*",
    "arguing contrast": r"\b(?:rather than|instead of|would have|does not mean|what this buys)\b",
    "x-not-y frame": r",\s+not\s+\w+",
    "announcement": r"\b(?:in (?:two|three|four|five) ways|(?:two|three|four|five) things|as follows|the following (?:sections?|points?))\b",
    "hedge clause": r"\b(?:seems? to|appears? to|may potentially|could potentially|it is possible that|arguably)\b",
    "process narration": r"\b(?:I (?:found|noticed|looked|checked|couldn't|can't|could not)|we (?:found|noticed|looked))\b",
    "signpost": r"\b(?:it(?:'s| is) worth noting|importantly|crucially|notably|in short|bottom line|the key (?:insight|point|takeaway)|here's the thing|that said|put simply)\b",
    "puffery": r"\b(?:robust|seamless(?:ly)?|leverag(?:e|es|ing)|delve|comprehensive|holistic|cutting-edge|tapestry|pivotal|underscor(?:es|ing)|showcas(?:e|es|ing)|streamlin(?:e|es|ing)|empower(?:s|ing)?|foster(?:s|ing)?|realm|intricate|in today's)\b",
    "-side/-path coinage": r"\b[a-z]+-(?:side|path)\b",
    "semicolon chain": r";",
    "compressing verb": r"\b(?:drew|draws|budgeted at|binds|trips|tripped|settles at|fires when)\b",
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
    "tells per 1k words": (25, 30.0),
    "bold spans per 1k words": (10, 15.0),
    "list share above 30%": (10, 0.5),
    "one-sentence paragraph share": (10, 0.6),
    "sentence-length uniformity": (5, 0.35),
    "headings per 1k words above 4": (5, 8.0),
    "unlinked references per 1k words": (10, 10.0),
    "share of prose in walls of text": (10, 0.5),
    # People rarely write past 25 words a sentence; hand-written fbcode docs
    # keep 0-21% of sentences over it, so only the share above 15% counts.
    "long-sentence share above 15%": (15, 0.25),
}

# The required Nomenclature appendix (a heading or bold line, then its rows up to the
# next heading) is reference material, not prose, so it stays out of every count.
NOMENCLATURE = re.compile(r"(?ims)^[#*\s]*(?:appendix:?\s*)?nomenclature\b.*?(?=^#|\Z)")
LIST_LINE = re.compile(r"\s*(?:[-*]|\d+\.)\s")
NON_PROSE = re.compile(r"\s*(?:[-*#|>]|\d+\.)")


def prose_only(text: str) -> str:
    """Prose a reader reads: no code blocks, tables, images or link targets."""
    text = NOMENCLATURE.sub("", re.sub(r"(?s)```.*?```", "", text))
    # The TL;DR repeats the body by design, so it stays out of the length comparison.
    text = re.sub(r"\*\*TL;DR\*\*[ \t]*\n(?:[ \t]*\n)?(?:[ \t]*[-*] [^\n]*\n)+", "", text)
    text = re.sub(r"(?m)^\s*\|.*$", "", text)
    # Figure captions may keep compact notation, so they are not prose here.
    text = re.sub(r"(?m)^\s*[*_]Figure \d+\..*$", "", text)
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
        "long-sentence share above 15%": max(0.0, sum(1 for n in lengths if n > 25) / max(len(lengths), 1) - 0.15),
    }
    return m, tells


# Weights sum to 100. Calibrated on agent-drafted decks: see references/slides.md.
SLIDE_WEIGHTS = {
    "tells per 1k words": (30, 30.0),
    "bold spans per 1k words": (5, 15.0),
    "notes words per slide above 150": (5, 150.0),
    "on-slide words per slide above 30": (15, 30.0),
    "title words above 8": (10, 4.0),
    "topic-label title share": (10, 0.3),
    "content slides without a visual": (15, 0.5),
    "unlinked references per 1k words": (10, 10.0),
}
TOPIC_TITLE = re.compile(
    r"^(?:agenda|overview|background|introduction|context|problem(?: statement)?|goals|"
    r"summary|key takeaways|takeaways|conclusions?|next steps|questions|q&a|thank you|"
    r"proposed design|design|rollout(?: plan)?|open questions)\b\W*(?::|$)",
    re.IGNORECASE,
)
VISUAL = re.compile(r"!\[|<img\b|<embed\b|```mermaid|^\s*\|", re.MULTILINE)


def slides(raw: str) -> list[tuple[str, str, str]]:
    """(title, on-slide text, notes) per slide; blocks with no text are skipped."""
    out = []
    for block in re.split(r"(?m)^---\s*$", re.sub(r"(?s)<!--.*?-->", "", raw)):
        notes, body = [], []
        for para in re.split(r"\n\s*\n", block.strip()):
            if para.lstrip().startswith(("Notes:", ">")):
                notes.append(re.sub(r"(?m)^\s*>\s?|^\s*Notes:\s*", "", para))
            else:
                body.append(para)
        lines = [ln for ln in "\n\n".join(body).splitlines() if ln.strip()]
        title = re.sub(r"^#+\s*|\*\*", "", lines[0]).strip() if lines else ""
        if lines and not re.match(r"(?i)(?:appendix:?\s*)?nomenclature\b", title):
            out.append((title, "\n".join(lines[1:]), "\n\n".join(notes)))
    return out


def slide_metrics(raw: str) -> tuple[dict[str, float], dict[str, int], list[str]]:
    deck = slides(raw)
    n = max(len(deck), 1)
    # Table cells count as words on the slide, so a list laid out as a table scores as text.
    on_slide = [len(prose_only(re.sub(r"(?m)^\s*\|[-:| ]*$", "", body).replace("|", " ")).split()) for _, body, _ in deck]
    title_words = [len(t.split()) for t, _, _ in deck]
    text = prose_only("\n\n".join(f"{t}\n\n{b}\n\n{nt}" for t, b, nt in deck))
    words = max(len(text.split()), 1)
    per_k = 1000.0 / words
    tells = {k: len(re.findall(p, text, flags=re.IGNORECASE)) for k, p in TELLS.items()}
    content = deck[1:] or deck
    unfenced = re.sub(r"(?s)```(?!mermaid).*?```", "", raw)
    m = {
        "words": sum(on_slide),
        "tells per 1k words": sum(tells.values()) * per_k,
        "bold spans per 1k words": len(re.findall(r"\*\*[^*\n]+\*\*", text)) * per_k,
        "on-slide words per slide above 30": sum(max(0, w - 30) for w in on_slide) / n,
        "notes words per slide above 150": sum(max(0, len(prose_only(nt).split()) - 150) for _, _, nt in deck) / n,
        "title words above 8": sum(max(0, w - 8) for w in title_words) / n,
        "topic-label title share": sum(1 for t, _, _ in deck if TOPIC_TITLE.match(t)) / n,
        "content slides without a visual": sum(1 for _, b, _ in content if not VISUAL.search(b)) / len(content),
        "unlinked references per 1k words": len(re.findall(REFERENCE, re.sub(LINK, "", unfenced))) * per_k,
    }
    flags = []
    for i, ((t, b, _), w, tw) in enumerate(zip(deck, on_slide, title_words), 1):
        issues = [f"{w} words on slide"] if w > 30 else []
        nw = len(prose_only(deck[i - 1][2]).split())
        issues += [f"{nw} words of notes"] if nw > 150 else []
        issues += [f"{tw}-word title"] if tw > 8 else []
        issues += ["topic-label title"] if TOPIC_TITLE.match(t) else []
        issues += ["no visual"] if i > 1 and not VISUAL.search(b) else []
        if issues:
            flags.append(f"slide {i} ({t[:40]}): {', '.join(issues)}")
    return m, tells, flags


def raw_identifiers(raw: str) -> list[str]:
    """Code-style names in body prose: backticked spans outside tables, fences and the appendix."""
    body = re.split(r"(?mi)^#+\s*appendix", raw)[0]
    body = re.sub(r"(?s)```.*?```", "", body)
    body = re.sub(r"(?m)^\s*\|.*$", "", body)
    return [s for s in re.findall(r"`([^`\n]+)`", body) if re.search(r"[_.(]|[a-z][A-Z]", s)]


def score(m: dict[str, float], weights: dict[str, tuple[int, float]]) -> float:
    return sum(w * min(1.0, m[k] / sat) for k, (w, sat) in weights.items())


def main() -> None:
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--type", choices=["prose", "slides"], default="prose")
    opts = parser.parse_args()
    args, detail, is_slides = opts.files, opts.detail, opts.type == "slides"
    weights = SLIDE_WEIGHTS if is_slides else WEIGHTS
    results = []
    for path in args:
        # The humanize-context block (an HTML comment) is metadata, not prose.
        raw = re.sub(r"(?s)<!--.*?-->", "", open(path, encoding="utf-8").read())
        m, tells, flags = slide_metrics(raw) if is_slides else (*metrics(raw), [])
        results.append((path, score(m, weights), m, tells))
        if detail:
            print(f"== {path}")
            ids = raw_identifiers(raw) if not is_slides else []
            if ids:
                print(f"  raw identifiers in body (move to Nomenclature): {', '.join(sorted(set(ids)))}")
            for f in flags:
                print(f"  {f}")
            for k in weights:
                w, sat = weights[k]
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
