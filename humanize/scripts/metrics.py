#!/usr/bin/env python3
"""Counter-metrics for a humanize pass: what a lower slop score must not cost.

Usage:
  metrics.py --facts FACTS.md --doc VERSION.md [--audit AUDIT.json] [--graded GRADED.json] [--figures FIGURES.json]
             [--author-pair DELIVERED.md:EDITED.md ...]

Computed here: fact retention (literals), length against the context's `length`
field, and author rewrite share. Read from the agent-judged JSON files that
references/counter-metrics.md describes: fact meaning, factual precision,
cold-read and TL;DR-only comprehension, unknown terms, and figures matching their text.

Exit status is 1 when a gating metric (fact retention, fact meaning, factual
precision) is below 100%.
"""

import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fact_check import has_literal, load_facts, normalise  # noqa: E402
from slop_score import metrics as slop_metrics, strip_frontmatter  # noqa: E402

WORDS_PER_PAGE = 500


def body(path: str) -> str:
    return strip_frontmatter(re.sub(r"(?s)<!--.*?-->", "", open(path, encoding="utf-8").read()))


def length_target(facts_path: str) -> int | None:
    """Upper bound of the context's `length` field, in body words."""
    m = re.search(r"(?m)^length:\s*(.*)$", open(facts_path, encoding="utf-8").read())
    n = m and re.search(r"(\d[\d,]*(?:\.\d+)?)(?:\s*-\s*(\d[\d,]*(?:\.\d+)?))?\s*(pages?|words?)", m.group(1))
    if not n:
        return None
    top = float((n.group(2) or n.group(1)).replace(",", ""))
    return round(top * WORDS_PER_PAGE if n.group(3).startswith("page") else top)


def rewrite_share(delivered: str, edited: str) -> float:
    """Share of the delivered doc's words the author changed or removed, tables and TL;DR included."""
    def words(p: str) -> list[str]:
        # Image and link URLs change on every fetch, so they are not the author's edits.
        return re.sub(r"!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)|https?://\S+", " ", body(p).replace("\\", "")).split()
    a, b = words(delivered), words(edited)
    kept = sum(blk.size for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return 1 - kept / max(len(a), 1)


def main() -> None:
    ap = argparse.ArgumentParser(usage=__doc__.replace("%", "%%"))
    ap.add_argument("--facts", required=True)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--audit")
    ap.add_argument("--graded")
    ap.add_argument("--figures")
    ap.add_argument("--author-pair", action="append", default=[])
    o = ap.parse_args()

    rows, gate_failed = [], False

    def row(name: str, value: str, target: str, ok: bool | None, gate: bool = False) -> None:
        nonlocal gate_failed
        gate_failed |= gate and ok is False
        rows.append((name, value, target, "-" if ok is None else ("ok" if ok else "FAIL")))

    facts = load_facts(o.facts)
    text = normalise(body(o.doc))
    intact = sum(all(has_literal(text, lit) for lit in lits) for _, _, lits, _ in facts)
    row("fact retention (literals)", f"{intact}/{len(facts)} = {intact / max(len(facts), 1):.0%}", "100%", intact == len(facts), True)

    if o.audit:
        a = json.load(open(o.audit))
        # The denominator is the fact sheet, not the audit: a fact the audit leaves out is not kept.
        status = {f["id"]: f["status"] for f in a["meaning"]}
        changed = [fid for fid, _, _, _ in facts if status.get(fid, "unaudited") != "kept"]
        n = len(facts)
        row("fact meaning kept", f"{n - len(changed)}/{n} = {(n - len(changed)) / max(n, 1):.0%}"
            + (f" (not kept: {', '.join(changed)})" if changed else ""), "100%", not changed, True)
        bad = a["unsupported_claims"]
        total = a["claims_total"]
        row("factual precision", f"{total - len(bad)}/{total} = {(total - len(bad)) / max(total, 1):.0%}", "100%", not bad, True)

    if o.figures:
        figs = json.load(open(o.figures))["figures"]
        bad = [str(f["figure"]) for f in figs if f["mismatches"] or f["slop"]]
        row("figures matching text, no slop", f"{len(figs) - len(bad)}/{len(figs)}" + (f" (fix: {', '.join(bad)})" if bad else ""), "all", not bad)

    if o.graded:
        g = json.load(open(o.graded))
        for key, label, target in (("full", "cold-read comprehension", 0.9), ("tldr", "TL;DR-only comprehension", 1.0)):
            qs = g[key]
            if not qs:
                # A doc type with no TL;DR and no stand-in has nothing for this reader to read.
                row(label, "not applicable for this doc type", f"{target:.0%}", None)
                continue
            right = sum(q["correct"] for q in qs)
            row(label, f"{right}/{len(qs)} = {right / max(len(qs), 1):.0%}", f"{target:.0%}", right / max(len(qs), 1) >= target)
        terms = g.get("unknown_terms", [])
        row("unknown terms (cold read)", str(len(terms)) + (f": {', '.join(terms)}" if terms else ""), "0", not terms)

    # `length` covers the body, so everything from the first appendix heading on is left out.
    words = int(slop_metrics(re.split(r"(?mi)^#+\s*appendix", body(o.doc))[0])[0]["words"])
    target = length_target(o.facts)
    if target:
        row("length vs target", f"{words} / {target} body words = {words / target:.2f}", "<= 1.00", words <= target)
    else:
        row("length vs target", f"{words} body words (no `length` field)", "-", None)

    for pair in o.author_pair:
        d, e = pair.split(":")
        row(f"author rewrite share {os.path.basename(d)} -> {os.path.basename(e)}", f"{rewrite_share(d, e):.1%}", "falls over time", None)

    w = [max(len(r[i]) for r in rows) for i in range(3)]
    print(f"{'metric':{w[0]}}  {'value':{w[1]}}  {'target':{w[2]}}  status")
    for r in rows:
        print(f"{r[0]:{w[0]}}  {r[1]:{w[1]}}  {r[2]:{w[2]}}  {r[3]}")
    sys.exit(1 if gate_failed else 0)


if __name__ == "__main__":
    main()
