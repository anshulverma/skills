#!/usr/bin/env python3
"""Regression checks for the humanize scripts. Run: python3 test_scripts.py"""

import json
import re
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fact_check import has_literal, normalise  # noqa: E402
from metrics import length_target  # noqa: E402
from slop_score import long_sentences, metrics, tldr_text  # noqa: E402


def write(d: str, name: str, text: str) -> str:
    p = os.path.join(d, name)
    open(p, "w").write(text)
    return p


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def main() -> None:
    # A literal may not start mid-word or extend a number.
    body = normalise("The hold lasts 15 min. Commonly 18 jobs ran.")
    assert not has_literal(body, "5 min") and not has_literal(body, "only") and not has_literal(body, "8")
    assert has_literal(normalise("up to 5 min, with 20K rows/s and 2.0-2.3M"), "5 min")
    assert has_literal(normalise("Shedding request: x"), "Shedding request:")
    assert not has_literal(normalise("80 jobs"), "8") and has_literal(normalise("the tiers crash-looped"), "crash-loop")
    assert has_literal(normalise("Trainer._handle_host_preempt"), "_handle_host_preempt")

    # A blank line after the TL;DR header still counts its bullets.
    assert "never more" in tldr_text("**TL;DR**\n\n- send less, never more.\n")
    assert "never more" in tldr_text("| **TL;DR**<br>- send less, never more. |\n")

    # A bold-led paragraph keeps its long sentences.
    long = "**Note:** " + " ".join(["word"] * 30) + "."
    assert long_sentences(long + "\n")

    with tempfile.TemporaryDirectory() as d:
        # Decimal page counts.
        f = write(d, "facts.md", "length: 1.5 pages of body\nF1 | a | 5 min | source: x\n")
        assert length_target(f) == 750, length_target(f)
        doc = write(d, "doc.md", "Holds for 5 min.\n")

        # The meaning gate's denominator is the fact sheet.
        audit = write(d, "audit.json", json.dumps({"meaning": [], "claims_total": 1, "unsupported_claims": []}))
        r = run(os.path.join(HERE, "metrics.py"), "--facts", f, "--doc", doc, "--audit", audit)
        assert r.returncode == 1 and "0/1" in r.stdout, r.stdout

        # A usage error prints usage, not a traceback.
        r = run(os.path.join(HERE, "metrics.py"), "--author-pair", "a:b")
        assert "Traceback" not in r.stderr and r.returncode == 2, r.stderr

        # A deck with no on-slide words scores without dividing by zero.
        deck = write(d, "deck.md", "# Title\n\n---\n\n# Only a title\n\n![x](x.png)\n")
        r = run(os.path.join(HERE, "slop_score.py"), deck, deck, "--type", "slides")
        assert r.returncode == 0, r.stderr

        # A cards block counts as a slide's visual.
        cards = write(d, "cards.md", "# Title\n\n---\n\n# Three jobs sent 3.2M\n\n```cards\n3.2M requests/min | on 10-01 | tiers fell over\n```\n")
        r = run(os.path.join(HERE, "slop_score.py"), cards, "--type", "slides", "--detail")
        assert re.search(r"content slides without a visual\s+0\.00", r.stdout), r.stdout

    assert metrics("Plain text.\n")[0]["words"] > 0
    print("ok")


if __name__ == "__main__":
    main()
