#!/usr/bin/env python3
"""Check every version of a doc against its fact sheet.

Usage: fact_check.py FACTS.md VERSION.md [VERSION.md ...]

FACTS.md has one fact per line in this shape (other lines are ignored):

    F7 | Three jobs ran at 20K, 20K and 14K rows/s on 10-01 | 20K; 14K; 10-01 | source: https://...

The third column lists literals that must appear verbatim in every version:
numbers, identifiers, names, URLs. Matching ignores case and markdown markup,
so `20K` matches **20K**. A fact passes when all its literals are present.
This catches dropped or reworded numbers and links; whether a fact's meaning
survived still needs a reader, which is what the fresh-agent check is for.

Exit status is 1 when any version is missing a fact, so it can gate a loop.
"""

import re
import sys

FACT = re.compile(r"^\s*(F\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*source:\s*(.*)$")


def load_facts(path: str) -> list[tuple[str, str, list[str], str]]:
    facts = []
    for line in open(path, encoding="utf-8"):
        m = FACT.match(line)
        if m:
            fid, text, lits, src = m.groups()
            facts.append((fid, text, [x.strip() for x in lits.split(";") if x.strip()], src.strip()))
    return facts


def normalise(text: str) -> str:
    # Google Docs' markdown export escapes punctuation (nano\_retrieval).
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!<>|-])", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    # "fewer-than-3-scored-beams" matches "fewer than 3 scored beams"; ranges like 2.0-2.3M stay.
    text = re.sub(r"(?<=[A-Za-z])-(?=\w)|(?<=\d)-(?=[A-Za-z])", " ", text)
    return re.sub(r"\s+", " ", text).lower()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    facts = load_facts(sys.argv[1])
    if not facts:
        sys.exit(f"no facts parsed from {sys.argv[1]}: check the 'F<n> | fact | literals | source: ...' shape")
    unsourced = [f[0] for f in facts if f[3].lower() in ("", "unsourced", "none")]
    cut = [ln.split("|")[0].split()[1] for ln in open(sys.argv[1], encoding="utf-8") if re.match(r"\s*cut F\d+\s*\|", ln)]
    print(f"{len(facts)} facts, {len(unsourced)} unsourced{': ' + ', '.join(unsourced) if unsourced else ''}"
          f"{f', {len(cut)} cut by the author: ' + ', '.join(cut) if cut else ''}")
    failed = False
    for path in sys.argv[2:]:
        # A literal that only survives in the humanize-context comment is not in the doc.
        body = normalise(re.sub(r"(?s)<!--.*?-->", "", open(path, encoding="utf-8").read()))
        missing = [(fid, [lit for lit in lits if normalise(lit) not in body]) for fid, _, lits, _ in facts]
        missing = [(fid, lits) for fid, lits in missing if lits]
        print(f"{path}: {len(facts) - len(missing)}/{len(facts)} facts intact")
        for fid, lits in missing:
            print(f"  {fid} missing: {'; '.join(lits)}")
        failed |= bool(missing)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
