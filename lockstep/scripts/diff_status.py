#!/usr/bin/env python3
"""Poll Phabricator for every diff the run references and write RUN/tracker/diff_status.json.

Usage: diff_status.py RUN_DIR
Diff ids come from pipeline.json `task_diffs` values and `diffs` keys. Output:
{"D123": {"state": "landed|accepted|published|draft|abandoned", "title": "..."}}. A diff whose poll fails keeps
its previous entry. Read-only: `meta phabricator.diff describe` only.
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from state import atomic_write_json, read_json


def diff_ids(pipeline: dict) -> list[str]:
    text = " ".join(map(str, (pipeline.get("task_diffs") or {}).values())) + " " + " ".join(pipeline.get("diffs") or {})
    return sorted(set(re.findall(r"\bD\d{6,}\b", text)))


def state_of(d: dict) -> str:
    """First match top to bottom. AI Approved counts as accepted (it can land without a human accept); the
    ai_approved and has_human_accept flags are ignored because they outlive a newer version back in review."""
    if d.get("status") == "Abandoned":
        return "abandoned"
    if d.get("is_landed"):
        return "landed"
    if d.get("status") in ("Accepted", "AI Approved"):
        return "accepted"
    if d.get("published") not in (None, "", "N/A"):
        return "published"
    return "draft"


def describe(diff: str) -> dict | None:
    r = subprocess.run(["meta", "phabricator.diff", "describe", f"--number={diff}", "--output=json"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
    try:
        return json.loads(r.stdout) if r.returncode == 0 else None
    except json.JSONDecodeError:
        return None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    run_dir = os.path.abspath(argv[0])
    out = os.path.join(run_dir, "tracker", "diff_status.json")
    old = read_json(out) if os.path.exists(out) else {}
    ids = diff_ids(read_json(os.path.join(run_dir, "pipeline.json")))
    with ThreadPoolExecutor(8) as pool:
        polled = dict(zip(ids, pool.map(describe, ids)))
    status = {i: {"state": state_of(d), "title": d.get("title", "")} if d else old[i]
              for i, d in polled.items() if d or i in old}
    failed = [i for i, d in polled.items() if not d]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    atomic_write_json(out, status)
    counts = {}
    for v in status.values():
        counts[v["state"]] = counts.get(v["state"], 0) + 1
    print(json.dumps(counts, sort_keys=True) + (f" (poll failed, kept previous: {' '.join(failed)})" if failed else ""))
    return 1 if failed and len(failed) == len(ids) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
