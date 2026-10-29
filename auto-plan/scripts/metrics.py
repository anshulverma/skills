#!/usr/bin/env python3
"""Per-pass metrics and the stop verdict for auto-plan's --harden loop.

Usage:
  metrics.py --judge JUDGE.md --artifact SPEC.md [--artifact PLAN.md ...] --pass N --history HISTORY.jsonl
             [--csv CONVERGENCE.csv] [--png CONVERGENCE.png] [--pending N] [--max-passes 3]
             [--targets "grounding precision >= 0.9 | length vs pass 1 <= 1.5"]
             [--tokens N] [--seconds N] [--escapes N]

--judge is the convergence judge's response (or just its Metrics JSON); the first ```json block
is read. --artifact is every artifact under hardening (spec, ADRs, plan): their words give the
length, and their `UNRESOLVED:` markers are counted here. --pending is the number of bubble-up
questions still waiting for an answer.

--history gets one JSON line per pass. A pass number lower than the line before starts a new run
(sdd's plan stage restarts at 1); a pass logged again (a full-coverage re-judge, the escape audit)
replaces its earlier line. --csv appends the
convergence CSV row and --png redraws the convergence chart (needs matplotlib; without it an
ASCII sparkline prints instead).

Verdict, on the last line printed:
  CONVERGED    instability 0, from a full-coverage judge, every gate passes -> stop
  OSCILLATION  this pass changed the same regions as two passes ago         -> stop
  PLATEAU      open gaps did not fall over the last three full-coverage judgments -> stop
  CAP          --max-passes reached                                         -> stop
  CONTINUE     run another pass (or a full-coverage judge, when one is asked for)
Exit status is 0 when the loop should stop and 1 when it should continue.
"""

import argparse
import csv
import json
import os
import re
import sys

TARGETS = {"grounding precision": (">=", 0.95), "self-report accuracy": (">=", 1.0), "length vs pass 1": ("<=", 1.3)}
CSV_COLUMNS = ["pass", "material_changes", "minor_changes", "open_gaps", "pending_questions", "unresolved_markers", "instability_score"]


def parse_targets(text: str) -> dict[str, tuple[str, float]]:
    items = re.findall(r"\s*([^|<>=]+?)\s*(<=|>=)\s*([\d.]+)(%?)", text or "")
    return {name.strip().lower(): (goal, float(v) / (100 if pct else 1)) for name, goal, v, pct in items}


def read_judge(path: str) -> dict:
    raw = open(path, encoding="utf-8").read()
    m = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S)
    return json.loads(m.group(1) if m else raw)


def load_run(path: str) -> list[dict]:
    """The latest run's rows, one per pass, in pass order."""
    rows = [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()] if os.path.exists(path) else []
    start = max([i for i in range(1, len(rows)) if rows[i]["pass"] < rows[i - 1]["pass"]], default=0)
    by_pass = {r["pass"]: r for r in rows[start:]}
    return [by_pass[p] for p in sorted(by_pass)]


def share(num, den):
    return None if not den else num / den


def make_row(j: dict, n: int, words: int, unresolved: int, pending: int, run: list[dict]) -> dict:
    """One pass's numbers; run holds the earlier passes of this run."""
    g = j.get("gaps", {})
    gaps = {k: int(g.get(k, 0)) for k in ("blocks_execution", "inconsistency", "cosmetic")}
    r = {"pass": n, "scope": j.get("scope", "scoped"), "regions": sorted(j.get("regions_changed", [])),
         "material_changes": int(j.get("material_changes", 0)), "minor_changes": int(j.get("minor_changes", 0)),
         "gaps_blocking": gaps["blocks_execution"], "gaps_inconsistency": gaps["inconsistency"],
         "gaps_cosmetic": gaps["cosmetic"], "open_gaps": sum(gaps.values()),
         "pending_questions": pending, "unresolved_markers": unresolved, "words": words}
    for k in ("tasks_read", "tasks_total", "anchors_checked", "anchors_wrong", "executable_steps", "run_steps",
              "spec_items_mapped", "spec_items_total", "gaps_in_last_changed_text", "self_report_matches"):
        r[k] = j.get(k)
    r["instability_score"] = r["material_changes"] + r["open_gaps"] + pending + unresolved
    r["full_coverage"] = r["scope"] == "full" and bool(r["tasks_total"]) and r["tasks_read"] == r["tasks_total"]
    r["coverage"] = share(r["tasks_read"] or 0, r["tasks_total"])
    r["executability"] = share(r["executable_steps"] or 0, r["run_steps"])
    r["spec_coverage"] = share(r["spec_items_mapped"] or 0, r["spec_items_total"])
    r["gates_failing"] = [name for name, ok in (("judge coverage", r["full_coverage"]),
                                                ("literal executability", r["executability"] in (None, 1.0)),
                                                ("spec coverage", r["spec_coverage"] in (None, 1.0))) if not ok]
    r["grounding_precision"] = share((r["anchors_checked"] or 0) - (r["anchors_wrong"] or 0), r["anchors_checked"])
    prev = run[-1] if run else None
    # Gaps the judge found in text this pass changed, over the gaps this pass was handed to fix.
    r["regression_rate"] = None if prev is None or r["gaps_in_last_changed_text"] is None else \
        r["gaps_in_last_changed_text"] / max(prev["open_gaps"], 1)
    r["length_ratio"] = words / max(run[0]["words"] if run else words, 1)
    return r


def verdict(rows: list[dict], max_passes: int) -> str:
    last = rows[-1]
    if last["instability_score"] == 0 and last["full_coverage"] and not last["gates_failing"]:
        return "CONVERGED"
    if len(rows) >= 3 and last["regions"] and last["regions"] == rows[-3]["regions"]:
        return "OSCILLATION"
    g = [r["open_gaps"] for r in rows if r["full_coverage"]][-3:]
    if len(g) == 3 and g[0] <= g[1] <= g[2] and g[2] > 0:
        return "PLATEAU"
    if last["pass"] >= max_passes:
        return "CAP"
    return "CONTINUE"


def table(rows: list[dict], targets: dict) -> list[tuple[str, str, str, str]]:
    r, prev = rows[-1], (rows[-2] if len(rows) > 1 else None)
    out = []

    def add(name, value, target, ok):
        out.append((name, value, target, "-" if ok is None else ("ok" if ok else "FAIL")))

    def pct(x):
        return "n/a" if x is None else f"{x:.0%}"

    def check(name, x):
        goal, bound = targets[name]
        return None if x is None else (x <= bound if goal == "<=" else x >= bound)

    def tgt(name):
        goal, bound = targets[name]
        shown = f"{bound:.0%}" if goal == ">=" and bound <= 1 else f"{bound:g}x"
        return f"{goal} {shown}" + (" (run)" if TARGETS[name] != targets[name] else "")

    add("instability score", f"{r['instability_score']} (material {r['material_changes']}, gaps {r['open_gaps']}, "
        f"pending {r['pending_questions']}, unresolved {r['unresolved_markers']})", "0", r["instability_score"] == 0)
    add("open gaps by severity", f"{r['gaps_blocking']} blocking, {r['gaps_inconsistency']} inconsistency, "
        f"{r['gaps_cosmetic']} cosmetic", "0 blocking", r["gaps_blocking"] == 0)
    add("judge coverage [gate]", f"{r['tasks_read'] or 0}/{r['tasks_total'] or 0} read ({r['scope']}), "
        f"{r['anchors_checked'] or 0} anchors checked", "100% read, full", r["full_coverage"])
    for name, key, num, den in (("literal executability [gate]", "executability", "executable_steps", "run_steps"),
                                ("spec coverage [gate]", "spec_coverage", "spec_items_mapped", "spec_items_total")):
        x = r[key]
        add(name, "n/a" if x is None else f"{r[num]}/{r[den]} = {x:.0%}", "100%", None if x is None else x == 1.0)
    add("grounding precision", pct(r["grounding_precision"]) + (f" ({r['anchors_wrong']} wrong)" if r["anchors_wrong"] else ""),
        tgt("grounding precision"), check("grounding precision", r["grounding_precision"]))
    rate, before = r["regression_rate"], prev and prev["regression_rate"]
    add("fix regression rate", "n/a" if rate is None else f"{r['gaps_in_last_changed_text']}/{max(prev['open_gaps'], 1)} = {rate:.2f}"
        + ("" if before is None else f" (was {before:.2f})"), "falls", None if rate is None else rate == 0 or (before is not None and rate < before))
    judged = [x["self_report_matches"] for x in rows if x["self_report_matches"] is not None]
    acc = share(sum(map(bool, judged)), len(judged))
    add("self-report accuracy", "n/a" if acc is None else f"{sum(map(bool, judged))}/{len(judged)} passes = {acc:.0%}",
        tgt("self-report accuracy"), check("self-report accuracy", acc))
    add("length vs pass 1", f"{r['words']} / {rows[0]['words']} words = {r['length_ratio']:.2f}x", tgt("length vs pass 1"),
        check("length vs pass 1", r["length_ratio"]))
    if r.get("escapes") is not None:
        add("escapes (post-CONVERGED audit)", str(r["escapes"]), "falls over runs", None)
    if r.get("tokens") is not None or r.get("seconds") is not None:
        add("cost", f"{r.get('tokens') or '?'} tokens, {r.get('seconds') or '?'} s", "reported", None)
    return out


def write_csv(path: str, r: dict) -> None:
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else [",".join(CSV_COLUMNS)]
    # A pass logged again replaces its row.
    if len(lines) > 1 and lines[-1].split(",")[0] == str(r["pass"]):
        lines.pop()
    lines.append(",".join(str(r[c]) for c in CSV_COLUMNS))
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def chart(rows: list[dict], out: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [r["pass"] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    ax.plot(xs, [r["instability_score"] for r in rows], color="#0b0b0b", lw=2.2, marker="o", label="instability")
    for key, color in (("material_changes", "#2a78d6"), ("open_gaps", "#e34948"), ("gaps_blocking", "#9b2c2c"),
                       ("pending_questions", "#8a6d1f"), ("unresolved_markers", "#6b6a66")):
        ax.plot(xs, [r[key] for r in rows], color=color, lw=1.2, marker=".", label=key.replace("_", " "))
    # A hollow ring marks a scoped judgment, which cannot converge.
    for r in rows:
        if not r["full_coverage"]:
            ax.plot([r["pass"]], [r["instability_score"]], "o", ms=9, mfc="none", mec="#e34948", mew=1.5)
    ax.set_xlabel("pass")
    ax.set_xticks(xs)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title(f"Convergence — {os.path.basename(out).removesuffix('.png').removesuffix('-convergence')}", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out)


def main() -> None:
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--artifact", action="append", required=True)
    ap.add_argument("--pass", dest="n", type=int, required=True)
    ap.add_argument("--history", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--png")
    ap.add_argument("--pending", type=int, default=0)
    ap.add_argument("--max-passes", type=int, default=3)
    ap.add_argument("--targets", default="")
    ap.add_argument("--tokens", type=int)
    ap.add_argument("--seconds", type=int)
    ap.add_argument("--escapes", type=int)
    o = ap.parse_args()

    targets = dict(TARGETS)
    for name, goal in parse_targets(o.targets).items():
        if name not in TARGETS:
            ap.error(f"--targets: {name!r} is not an overridable target ({', '.join(TARGETS)}); gates stay at 100%")
        targets[name] = goal

    texts = [open(p, encoding="utf-8").read() for p in o.artifact]
    words = sum(len(t.split()) for t in texts)
    unresolved = sum(t.count("UNRESOLVED:") for t in texts)
    old = load_run(o.history)
    run = [] if old and o.n < old[-1]["pass"] else [r for r in old if r["pass"] < o.n]
    row = make_row(read_judge(o.judge), o.n, words, unresolved, o.pending, run)
    row.update(tokens=o.tokens, seconds=o.seconds, escapes=o.escapes)
    with open(o.history, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    rows = run + [row]
    if o.csv:
        write_csv(o.csv, row)

    out = table(rows, targets)
    w = [max(len(t[i]) for t in out + [("metric", "value", "target")]) for i in range(3)]
    print(f"{'metric':{w[0]}}  {'value':{w[1]}}  {'target':{w[2]}}  status")
    for t in out:
        print(f"{t[0]:{w[0]}}  {t[1]:{w[1]}}  {t[2]:{w[2]}}  {t[3]}")
    if o.png:
        try:
            chart(rows, o.png)
            print(f"chart: {o.png}")
        except ImportError:
            bars = "▁▂▃▄▅▆▇█"
            top = max(r["instability_score"] for r in rows) or 1
            print("chart: skipped, matplotlib is missing; instability sparkline: "
                  + "".join(bars[min(7, r["instability_score"] * 7 // top)] for r in rows))
    v = verdict(rows, o.max_passes)
    for t in out:
        if t[3] == "FAIL":
            print(f"  short: {t[0]} = {t[1]} (target {t[2]})")
    if row["instability_score"] == 0 and not row["full_coverage"]:
        print("  short: this judgment is not full-coverage; re-judge this pass with a full-coverage judge before accepting convergence")
    print(v)
    sys.exit(0 if v != "CONTINUE" else 1)


if __name__ == "__main__":
    main()
