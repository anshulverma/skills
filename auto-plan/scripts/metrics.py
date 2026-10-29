#!/usr/bin/env python3
"""Per-pass metrics and the stop verdict for auto-plan's --harden loop.

Usage:
  metrics.py --judge JUDGE.md --artifact SPEC.md [--artifact PLAN.md ...] --pass N --history HISTORY.jsonl
             [--csv CONVERGENCE.csv] [--png CONVERGENCE.png] [--pending N] [--max-passes 3]
             [--targets "grounding precision >= 0.9 | length vs pass 1 <= 1.5"]
             [--tokens N] [--seconds N] [--escapes N] [--upload]

--judge is the convergence judge's response (or just its Metrics JSON); the first ```json block
is read. --artifact is every artifact under hardening (spec, ADRs, plan): their words give the
length, and their `UNRESOLVED:` markers are counted here. --pending is the number of bubble-up
questions still waiting for an answer.

--history gets one JSON line per pass. A pass number lower than the line before starts a new run
(sdd's plan stage restarts at 1); a pass logged again (a full-coverage re-judge, the escape audit)
replaces its earlier line. A line marked "backfilled": true (written by hand for passes logged
before this script) may carry only pass, scope, open_gaps, words and tasks_read/tasks_total: the
chart plots what it has and the verdict ignores it. --csv appends the
convergence CSV row and --png redraws the convergence chart (needs matplotlib; without it an
ASCII sparkline prints instead).

Every run redraws the progress chart next to the history, <history stem>-progress.png: one panel per
metric on one x axis with a tick for every pass of the run, target dashed, misses hollow red, scoped
judges as squares, escape audits as a dotted line (needs matplotlib: run with
~/.cache/humanize-venv/bin/python). With --upload, a verdict that stops the loop also uploads it to
Pixelcloud, prints the pxl.cl link and stores it on the pass's history line as chart_url; CONTINUE
never uploads, and a failed upload prints a warning and changes nothing else. The pass's line also
stores its verdict.

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
import subprocess
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
    rows = [r for r in rows if not r.get("backfilled")]
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
    rate, before = r["regression_rate"], prev and prev.get("regression_rate")
    add("fix regression rate", "n/a" if rate is None else f"{r['gaps_in_last_changed_text']}/{max(prev['open_gaps'], 1)} = {rate:.2f}"
        + ("" if before is None else f" (was {before:.2f})"), "falls", None if rate is None else rate == 0 or (before is not None and rate < before))
    judged = [x["self_report_matches"] for x in rows if x.get("self_report_matches") is not None]
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


def progress_chart(rows: list[dict], targets: dict, out: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seen, acc = [], []
    for r in rows:
        if r.get("self_report_matches") is not None:
            seen.append(bool(r["self_report_matches"]))
        acc.append(share(sum(seen), len(seen)))
    # Backfilled rows lack the derived values; rebuild the ones their fields allow.
    derived = {"coverage": lambda r: share(r.get("tasks_read") or 0, r.get("tasks_total")),
               "length_ratio": lambda r: r.get("words") and r["words"] / max(rows[0].get("words") or r["words"], 1)}
    col = lambda k: [r[k] if k in r else derived[k](r) if k in derived else None for r in rows]
    # (title, goal, target, [(label, values)]); misses are judged on the first series only.
    panels = [("instability score", "<=", 0, [("", col("instability_score"))]),
              ("open gaps by severity", "<=", 0, [("total", col("open_gaps")), ("blocking", col("gaps_blocking")),
                                                   ("inconsistency", col("gaps_inconsistency")),
                                                   ("cosmetic", col("gaps_cosmetic"))]),
              ("judge coverage [gate]", ">=", 1.0, [("", col("coverage"))]),
              ("literal executability [gate]", ">=", 1.0, [("", col("executability"))]),
              ("spec coverage [gate]", ">=", 1.0, [("", col("spec_coverage"))]),
              ("grounding precision", *targets["grounding precision"], [("", col("grounding_precision"))]),
              ("fix regression rate", "falls", 0, [("", col("regression_rate"))]),
              ("self-report accuracy", *targets["self-report accuracy"], [("", acc)]),
              ("length vs pass 1", *targets["length vs pass 1"], [("", col("length_ratio"))])]
    surface, ink, ink2, bad, audit = "#fcfcfb", "#0b0b0b", "#52514e", "#e34948", "#7b3fbf"
    colors = ["#2a78d6", "#9b2c2c", "#8a6d1f", "#9a9893"]
    xs = col("pass")
    ticks = list(range(xs[0], xs[-1] + 1))
    fig, axes = plt.subplots(3, 3, figsize=(10.8, 7.5), dpi=170)
    fig.patch.set_facecolor(surface)
    for ax, (name, goal, target, series) in zip(axes.flat, panels):
        ax.set_facecolor(surface)
        for x in (r["pass"] for r in rows if r.get("escapes") is not None):
            ax.axvline(x, color=audit, lw=1, ls=":")
        for i, (label, ys) in enumerate(series):
            pts = [(x, y, r) for x, y, r in zip(xs, ys, rows) if y is not None]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=colors[i], lw=2 if i == 0 else 1.2,
                    label=label or None, zorder=3)
            prev = None
            for x, y, r in pts:
                ok = y <= target if goal == "<=" else y >= target if goal == ">=" else y == 0 or (prev is not None and y < prev)
                miss = i == 0 and not ok
                ax.plot([x], [y], "o" if r.get("full_coverage", r.get("scope") == "full") else "s", ms=7 if miss else 5, mfc=surface if miss else colors[i],
                        mec=bad if miss else colors[i], mew=1.8 if miss else 1, zorder=4)
                prev = y
            if i == 0 and pts:
                ax.annotate(f"{pts[-1][1]:.0%}" if goal == ">=" and target <= 1 else f"{pts[-1][1]:.3g}", pts[-1][:2],
                            xytext=(4, 4), textcoords="offset points", color=ink, fontsize=8)
            elif i == 0:
                ax.text(0.5, 0.5, "not measured", transform=ax.transAxes, ha="center", color=ink2, fontsize=8)
        ax.axhline(target, color=ink2, lw=1, ls=(0, (4, 3)))
        if goal == ">=" and target <= 1:
            lo = min([y for y in series[0][1] if y is not None] + [target])
            # A metric sitting at 100% needs a decimal, or every tick reads the same.
            fmt = "{:.1%}" if 1 - lo < 0.05 else "{:.0%}"
            ax.yaxis.set_major_formatter(lambda y, _, fmt=fmt: fmt.format(y))
            ax.set_ylim(lo - 0.02, 1.01)
        shown = "falls, 0 best" if goal == "falls" else f"{goal} {target:.0%}" if goal == ">=" and target <= 1 else f"{goal} {target:g}"
        ax.set_title(f"{name}\n(target {shown})", fontsize=8.5, color=ink, loc="left")
        if len(series) > 1:
            ax.legend(fontsize=6.5, frameon=False)
        ax.set_xticks(ticks)
        ax.set_xlim(ticks[0] - 0.5, ticks[-1] + 0.5)
        ax.tick_params(labelsize=7, colors=ink2, length=0)
        if len(ticks) > 15:
            ax.tick_params(axis="x", labelsize=5.5, labelrotation=90)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#c9c8c3")
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=ink)
    fig.text(0.01, 0.005, "x: pass. Circle: full-coverage judge. Square: scoped judge. Hollow red: misses its target. "
             "Dashed line: the target. Dotted purple line: escape audit.", fontsize=7.5, color=ink2)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, facecolor=surface)
    plt.close(fig)


def upload(png: str) -> str:
    """The pxl.cl link for png, or raise RuntimeError."""
    try:
        p = subprocess.run(["meta", "pixelcloud.image", "upload", f"--file=file://{os.path.abspath(png)}"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(str(e)) from None
    m = re.search(r"https?://pxl\.cl/[\w-]+", p.stdout + p.stderr)
    if p.returncode or not m:
        raise RuntimeError(f"exit {p.returncode}: " + ((p.stderr or p.stdout).strip().splitlines() or ["no pxl.cl link"])[0])
    return m.group(0)


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
    ap.add_argument("--upload", action="store_true")
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
    rows = run + [row]
    v = row["verdict"] = verdict(rows, o.max_passes)
    if o.csv:
        write_csv(o.csv, row)

    out = table(rows, targets)
    w = [max(len(t[i]) for t in out + [("metric", "value", "target")]) for i in range(3)]
    print(f"{'metric':{w[0]}}  {'value':{w[1]}}  {'target':{w[2]}}  status")
    for t in out:
        print(f"{t[0]:{w[0]}}  {t[1]:{w[1]}}  {t[2]:{w[2]}}  {t[3]}")
    real = [r for r in rows if not r.get("backfilled")]
    if o.png:
        try:
            chart(real, o.png)
            print(f"chart: {o.png}")
        except ImportError:
            bars = "▁▂▃▄▅▆▇█"
            top = max(r["instability_score"] for r in real) or 1
            print("chart: skipped, matplotlib is missing; instability sparkline: "
                  + "".join(bars[min(7, r["instability_score"] * 7 // top)] for r in real))
    png = os.path.splitext(o.history)[0] + "-progress.png"
    try:
        progress_chart(rows, targets, png, f"{os.path.basename(png).removesuffix('-progress.png')}: {v} at pass {o.n}")
        print(f"progress chart: {png}")
        if o.upload and v != "CONTINUE":
            try:
                row["chart_url"] = upload(png)
                print(f"progress chart link: {row['chart_url']}")
            except RuntimeError as e:
                print(f"warning: progress chart upload failed ({e}); verdict unaffected")
    except ImportError:
        print("progress chart: skipped, matplotlib is missing (run with ~/.cache/humanize-venv/bin/python)")
    except Exception as e:  # a chart failure never costs the history line
        print(f"warning: progress chart failed ({e})")
    with open(o.history, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    for t in out:
        if t[3] == "FAIL":
            print(f"  short: {t[0]} = {t[1]} (target {t[2]})")
    if row["instability_score"] == 0 and not row["full_coverage"]:
        print("  short: this judgment is not full-coverage; re-judge this pass with a full-coverage judge before accepting convergence")
    print(v)
    sys.exit(0 if v != "CONTINUE" else 1)


if __name__ == "__main__":
    main()
