#!/usr/bin/env python3
"""Chart every metric across passes and decide whether the humanize loop stops.

Usage: progress.py HISTORY.jsonl [--out progress.png] [--max-passes 6]

HISTORY.jsonl has one line per version, written by `metrics.py --log HISTORY.jsonl --label vN`;
the first line is the original. The chart is one small panel per metric: its value at each
pass, a dashed line at its target, and the last value labelled. Needs matplotlib
(`~/.cache/humanize-venv/bin/python`); the verdict prints without it.

Verdict, on the last line printed:
  CONVERGED  every metric meets its target           -> stop
  PLATEAU    no metric moved since the pass before    -> stop, report what still misses
  CAP        --max-passes passes done                 -> stop, report what still misses
  CONTINUE   something misses and something is moving -> run another pass
Exit status is 0 when the loop should stop and 1 when it should continue.
"""

import argparse
import json
import sys

# How far a metric must move between passes to count as still moving.
TOLERANCE = {"slop score": 1.0, "unknown terms (cold read)": 0.5}
DEFAULT_TOLERANCE = 0.01


READBACK = "read-back checks failing"


def verdict(rows: list[dict], max_passes: int) -> tuple[str, list[str]]:
    last = rows[-1]["metrics"]
    missing = [k for k, m in last.items() if m["ok"] is False]
    # The read-back checks cover what no metric does, so the loop cannot converge without them.
    if READBACK not in last:
        missing.append(f"{READBACK} (not logged: pass --readback-failing)")
    if not missing:
        return "CONVERGED", []
    if len(rows) >= 2:
        prev = rows[-2]["metrics"]
        moved = [k for k in last if k in prev
                 and abs(last[k]["value"] - prev[k]["value"]) > TOLERANCE.get(k, DEFAULT_TOLERANCE)]
        if not moved:
            return "PLATEAU", missing
    if len(rows) - 1 >= max_passes:
        return "CAP", missing
    return "CONTINUE", missing


def chart(rows: list[dict], out: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(dict.fromkeys(k for r in rows for k in r["metrics"]))
    cols = min(3, len(names))
    nrows = -(-len(names) // cols)
    fig, axes = plt.subplots(nrows, cols, figsize=(3.6 * cols, 2.5 * nrows), dpi=170, squeeze=False)
    surface, ink, ink2, series, bad = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6", "#e34948"
    fig.patch.set_facecolor(surface)
    labels = [r["label"] for r in rows]
    for ax, name in zip(axes.flat, names):
        pts = [(i, r["metrics"][name]) for i, r in enumerate(rows) if name in r["metrics"]]
        xs, ms = [i for i, _ in pts], [m for _, m in pts]
        ys = [m["value"] for m in ms]
        ax.set_facecolor(surface)
        ax.plot(xs, ys, color=series, lw=2, marker="o", ms=5, zorder=3)
        # A point that misses its target is drawn hollow, so a reader sees where it still fails.
        for x, m in zip(xs, ms):
            if m["ok"] is False:
                ax.plot([x], [m["value"]], "o", ms=7, mfc=surface, mec=bad, mew=1.8, zorder=4)
        ax.axhline(ms[-1]["target"], color=ink2, lw=1, ls=(0, (4, 3)))
        last_share = ms[-1]["goal"] == ">=" and ms[-1]["target"] <= 1
        ax.annotate(f"{ys[-1]:.0%}" if last_share else f"{ys[-1]:.3g}", (xs[-1], ys[-1]), xytext=(4, 4),
                    textcoords="offset points", color=ink, fontsize=8)
        goal = "at most" if ms[-1]["goal"] == "<=" else "at least"
        share = ms[-1]["goal"] == ">=" and ms[-1]["target"] <= 1
        if share:
            # Shares read as percentages, with the target in view.
            # A narrow range (a metric sitting at 100%) needs a decimal, or every tick reads the same.
            fmt = "{:.1%}" if max(ys + [ms[-1]["target"]]) - min(ys + [ms[-1]["target"]]) < 0.05 else "{:.0%}"
            ax.yaxis.set_major_formatter(lambda y, _, fmt=fmt: fmt.format(y))
            ax.set_ylim(min(min(ys), ms[-1]["target"]) - 0.02, 1.01)
        shown = f"{ms[-1]['target']:.0%}" if share else f"{ms[-1]['target']:g}"
        ax.set_title(f"{name}\n(target {goal} {shown})", fontsize=8.5, color=ink, loc="left")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=7, color=ink2)
        ax.tick_params(axis="y", labelsize=7, colors=ink2, length=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color("#c9c8c3")
        ax.spines["bottom"].set_color("#c9c8c3")
    for ax in list(axes.flat)[len(names):]:
        ax.set_visible(False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=ink)
    fig.text(0.01, 0.005, "Filled point: meets its target. Hollow red point: misses it. Dashed line: the target.",
             fontsize=7.5, color=ink2)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, facecolor=surface)


def main() -> None:
    ap = argparse.ArgumentParser(usage=__doc__.replace("%", "%%"))
    ap.add_argument("history")
    ap.add_argument("--out")
    ap.add_argument("--max-passes", type=int, default=6)
    o = ap.parse_args()
    rows = [json.loads(ln) for ln in open(o.history, encoding="utf-8") if ln.strip()]
    if not rows:
        sys.exit(f"{o.history} has no passes yet: run metrics.py --log first")
    # A rerun appends a new "orig"; only the latest run counts toward the verdict and the chart.
    starts = [i for i, r in enumerate(rows) if r["label"] == "orig"]
    rows = rows[starts[-1]:] if starts else rows
    v, missing = verdict(rows, o.max_passes)
    at = rows[-1]["label"]
    title = f"Metrics by pass: converged at {at}" if v == "CONVERGED" else f"Metrics by pass, {at}: {len(missing)} still short of target"
    for k in missing:
        m = rows[-1]["metrics"].get(k)
        print(f"  short: {k} = {m['value']:.3g} (target {m['goal']} {m['target']:g}){' [gate]' if m['gate'] else ''}" if m else f"  short: {k}")
    if o.out:
        try:
            chart(rows, o.out, title)
            print(f"chart: {o.out}")
        except ImportError:
            print("chart: skipped, matplotlib is missing (run with ~/.cache/humanize-venv/bin/python)")
    print(v)
    sys.exit(0 if v != "CONTINUE" else 1)


if __name__ == "__main__":
    main()
