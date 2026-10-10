#!/usr/bin/env python3
"""Run the prompted slop classifier (references/slop-classifier.md) over a JSONL of {"id", "text"} rows.

  prompted_eval.py --input FILE --out SCORES [--runs 3] [--model claude-opus-5-5] [--batch 20]

Writes one {"id", "scores": {"prompted": f}} line per input row, f = fraction of answered runs voting slop
(null if no run answered for the row); rows are shuffled per run (seed = run number) before batching,
and each run's raw outputs to <out>.run<k>.json. Examples come from the train split only.
"""
import argparse
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import slop_lines  # noqa: E402

CONTEXT = "readers: engineers at Meta reading internal docs, diffs, posts and tasks; depth: decision"
SYSTEM = "You are a careful annotator."


def prompt_template() -> str:
    path = os.path.join(HERE, "..", "references", "slop-classifier.md")
    section = open(path, encoding="utf-8").read().split("## The prompt", 1)[1].strip()
    text = "\n".join(l[2:] if l.startswith("> ") else l.lstrip(">") for l in section.splitlines())
    for old, new in (
        ("<context block>", CONTEXT),
        ("every labelled example in `data/slop_labels.jsonl`", "every labelled example in the EXAMPLES block below"),
        ("<lines file>", "the LINES block below"),
        # Batches hold unrelated rows; reading neighbours would let batch composition leak into the labels.
        ("judge each line in the context of its neighbours", "judge each line on its own (lines are unrelated)"),
    ):
        assert old in text, f"prompt section changed: {old!r} not found"
        text = text.replace(old, new)
    return text


def build_prompt(template: str, examples: str, rows: list[dict]) -> str:
    lines = json.dumps({"lines": [{"i": i, "text": r["text"]} for i, r in enumerate(rows, 1)]})
    return f"{template}\n\nEXAMPLES (JSON lines):\n{examples}\n\nLINES:\n{lines}\n"


def call(prompt: str, model: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    cmd = ["claude", "-p", "--bare", "--system-prompt", SYSTEM, "--tools", "", "--no-session-persistence", "--model", model]
    return subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd="/tmp", env=env, check=True).stdout


def parse(stdout: str) -> dict:
    return json.JSONDecoder().raw_decode(stdout[stdout.index("{"):])[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--batch", type=int, default=20, help="rows per call")
    o = ap.parse_args()

    rows = [json.loads(l) for l in open(o.input, encoding="utf-8") if l.strip()]
    template = prompt_template()
    examples = "\n".join(json.dumps(r) for r in slop_lines.records(split="train"))
    votes = {r["id"]: 0 for r in rows}
    answered = {r["id"]: 0 for r in rows}

    for k in range(1, o.runs + 1):
        raw, order = [], rows[:]
        random.Random(k).shuffle(order)
        for b in range(0, len(order), o.batch):
            chunk = order[b:b + o.batch]
            got, out, err = None, None, None
            for _attempt in range(2):  # one retry, then the batch's rows stay unanswered for this run
                try:
                    out = call(build_prompt(template, examples, chunk), o.model)
                    got = {p["i"]: p for p in parse(out)["lines"]}
                    break
                except (subprocess.CalledProcessError, ValueError, KeyError, TypeError) as e:
                    err = e
            if got is None:
                print(f"run {k} batch {b // o.batch}: call or parse failed twice ({err}); {len(chunk)} rows unanswered", file=sys.stderr)
                raw.append({"batch": b // o.batch, "ids": [r["id"] for r in chunk], "error": str(err), "stdout": out})
                continue
            raw.append({"batch": b // o.batch, "ids": [r["id"] for r in chunk], "output": list(got.values())})
            for i, r in enumerate(chunk, 1):
                p = got.get(i)
                if p is None:
                    print(f"run {k}: missing line {r['id']}", file=sys.stderr)
                    continue
                answered[r["id"]] += 1
                votes[r["id"]] += p.get("label") == "slop"
        json.dump(raw, open(f"{o.out}.run{k}.json", "w"), indent=1)

    with open(o.out, "w", encoding="utf-8") as fh:
        for r in rows:
            n = answered[r["id"]]
            fh.write(json.dumps({"id": r["id"], "scores": {"prompted": votes[r["id"]] / n if n else None}}) + "\n")


if __name__ == "__main__":
    main()
