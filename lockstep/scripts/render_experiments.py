#!/usr/bin/env python3
"""Render the Experiments, Experiment log and Studies tabs from experiments/state.json.

Usage: render_experiments.py RUN OUTDIR [--held-json F] [--now ISO]
Writes OUTDIR/experiments.html, experiment_log.html and studies.html, each only when its source exists;
exits 0 silently when RUN/experiments/state.json is missing. --held-json is {tab key: [open comment quotes]}
from `tabs.py get`: a concluded unit with a quote on one of its rows stays on the Experiments tab.
Figures go to RUN/experiments/fig/ as absolute file:// images (deliver with `tabs.py apply`).
"""
import argparse
import html
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import figures
import md2ghtml
import render_tracker as rt
from render_tracker import _figure, _table, esc, fmt_dur, local
from state import now_utc, parse_ts, read_json

import matplotlib.dates as mdates  # noqa: E402  (figures set the Agg backend)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

JOB_STATES = {  # row state: (fill, border, font, legend); stopped = failed with stopped_done
    "queued": rt.TASK_STATES["pending"][:3] + ("queued",),
    "starting": rt.TASK_STATES["in_progress"][:3] + ("starting",),
    "running": (rt.BLUE, rt.BLUE, "white", "running"),
    "done": rt.TASK_STATES["complete"][:3] + ("done",),
    "failed": rt.TASK_STATES["blocked"][:3] + ("failed",),
    "stopped": (rt.PURPLE, rt.PURPLE, "white", "stopped on purpose"),
    "void": ("#ffffff", "#8a8984", "#8a8984", "void (never ran)"),
}
TERMINAL = ("done", "failed", "stopped", "void")
LIVE = ("queued", "starting", "running")
SUB_CAP = 32       # sub-rows per lane; past this, bars share the last sub-row, faded
SUB_IN = 0.2       # minimum sub-row height (in); the figure grows taller instead of going thinner
SUB_MAX = 0.32     # maximum, so a few jobs do not draw slabs; spare panel height stays blank below
RUN_IN = 1.2       # jobs-running panel
FONT = 8
HEAD = ["#", "Date", "Job", "Hypothesis or change", "Kind", "Signal", "Readout", "Verdict"]


def shown(j: dict) -> str:
    st = j.get("state") or "queued"
    if st not in JOB_STATES:
        raise ValueError(f"job {j.get('name')}: unknown state {st!r}")
    return "stopped" if j.get("stopped_done") and st in ("failed", "stopped") else st


def settled(j: dict) -> bool:
    """Terminal with a verdict; a void job (never ran) needs none."""
    return shown(j) in TERMINAL and (bool(j.get("verdict")) or shown(j) == "void")


def unit_of(j: dict) -> str:
    return f"study:{j['study']}" if j.get("study") else f"job:{j['n']}"


def _norm(s: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html.unescape(str(s))).split())


def _chip(state: str, text: str | None = None) -> str:
    fill, _, font, legend = JOB_STATES[state]
    return f'<span style="color:{font}; background-color:{fill}">{esc(text or legend)}</span>'


def _tab_link(run: dict, key: str, text: str, tab: str | None = None) -> str:
    """`text` linked to the docs.<key> tab (or to `tab` on the lockstep doc); plain text when neither is known."""
    d = (run.get("docs") or {}).get(key) or {}
    doc, tab = d.get("id") or run.get("tracker_doc"), d.get("tab") or tab
    if tab and doc:
        return f'<a href="https://docs.google.com/document/d/{esc(doc)}/edit?tab={esc(tab)}">{esc(text)}</a>'
    return esc(text)


def _extent(j: dict, now: datetime) -> tuple[datetime, datetime]:
    """Start to end; a live job runs to now, a terminal one ends at ended_utc, so a job that never ran spans its queue time."""
    a = parse_ts(j.get("started_utc") or j["launched_utc"])
    b = parse_ts(j["ended_utc"]) if j.get("ended_utc") else a if shown(j) in TERMINAL else now
    return a, max(a, b)


def row(j: dict, now: datetime) -> list[str]:
    st = shown(j)
    date = f"{local(parse_ts(j['launched_utc'])):%Y-%m-%d %H:%M}" if j.get("launched_utc") else ""
    if j.get("started_utc"):
        a, b = _extent(j, now)
        date += f"<br>ran {fmt_dur((b - a).total_seconds())}"
    name = f'<a href="{esc(j["url"])}">{esc(j["name"])}</a>' if j.get("url") else esc(j.get("name"))
    kind = esc(j.get("kind") or "other") + (f", study {esc(j['study'])}" if j.get("study") else "")
    sig = [_chip(st)]
    if st in LIVE and j.get("eta_utc"):
        sig.append(f"ETA {local(parse_ts(j['eta_utc'])):%m-%d %H:%M}")
    if (j.get("attempts") or 0) > 1:
        sig.append(f"x{j['attempts']} attempts")
    if j.get("cost_gpu_h"):
        sig.append(f"{j['cost_gpu_h']:.1f} GPU-h")
    return [str(j["n"]), date, name, esc(j.get("hypothesis")), kind, ", ".join(sig), esc(j.get("readout")),
            esc(j.get("verdict"))]


def concluded_units(st: dict, held: list[str], now: datetime) -> set[str]:
    """Units whose rows leave the Experiments tab: every job settled, the study concluded, no row held.
    A quote holds a unit only when it sits inside one cell of that unit's rows; quotes are tab-wide."""
    quotes = [q for q in (_norm(q) for q in held) if q]
    units: dict[str, list[dict]] = {}
    for j in st["jobs"]:
        units.setdefault(unit_of(j), []).append(j)
    out = set()
    for u, jobs in units.items():
        study = st["studies"].get(jobs[0].get("study") or "", {})
        if jobs[0].get("study") and study.get("status") != "concluded":
            continue
        if not all(settled(j) for j in jobs):
            continue
        cells = [_norm(c) for j in jobs for c in row(j, now)]
        if any(q in c for q in quotes for c in cells):
            continue
        out.add(u)
    return out


def pack(spans: list[tuple[datetime, datetime]], cap: int = SUB_CAP) -> tuple[list[tuple[int, bool]], int]:
    """Greedy sub-rows in start order: the first sub-row whose last bar ended by this start. Past `cap`
    sub-rows a bar shares the last one and is marked overflow (drawn faded)."""
    ends, out = [], []
    for a, b in spans:
        k = next((i for i, e in enumerate(ends) if e <= a), None)
        if k is not None:
            ends[k] = b
        elif len(ends) < cap:
            ends.append(b)
            k = len(ends) - 1
        else:
            k = cap - 1
            ends[k] = max(ends[k], b)
            out.append((k, True))
            continue
        out.append((k, False))
    return out, len(ends)


def _text_in(t: str) -> float:
    return len(t) * FONT * 0.6 / 72   # conservative width estimate of FONT-pt Liberation Sans


def timeline(jobs: list[dict], now: datetime, out: str, pageless: bool, lo: datetime, hi: datetime,
             title: str) -> str | None:
    """Jobs in [lo, hi]: one lane per kind, greedy sub-rows, labels only where they fit, a jobs-running panel."""
    shown_jobs = sorted((j for j in jobs if j.get("launched_utc")), key=lambda j: (_extent(j, now)[0], j["n"]))
    shown_jobs = [j for j in shown_jobs if _extent(j, now)[1] >= lo and _extent(j, now)[0] <= hi]
    if not shown_jobs:
        return None
    x0 = max(lo, min(_extent(j, now)[0] for j in shown_jobs)) if hi >= now else lo
    x1 = max(hi, x0 + timedelta(hours=1))
    kinds = list(dict.fromkeys(j.get("kind") or "other" for j in sorted(shown_jobs, key=lambda j: j["n"])))
    lanes = []
    for k in kinds:
        items = [j for j in shown_jobs if (j.get("kind") or "other") == k]
        slots, nsub = pack([(max(_extent(j, now)[0], x0), _extent(j, now)[1]) for j in items])
        lanes.append((k, nsub, list(zip(items, slots))))
    figures.style()
    w, h0 = figures.size(pageless)
    nrows, pad = sum(n for _, n, _ in lanes), 0.15
    jobs_h = max(h0 - RUN_IN - 1.1, nrows * SUB_IN + pad * len(lanes))
    fig_h = jobs_h + RUN_IN + 1.1
    sub = min(SUB_MAX, (jobs_h - pad * len(lanes)) / nrows)
    fig, (ax, ax2) = plt.subplots(2, 1, sharex=True, figsize=(w, fig_h), height_ratios=[jobs_h, RUN_IN])
    left, right = 1.4 / w, 1 - 0.3 / w
    fig.subplots_adjust(left=left, right=right, top=1 - 0.45 / fig_h, bottom=1.0 / fig_h, hspace=0.1)
    N = mdates.date2num
    per_in = (N(x1) - N(x0)) / (w * (right - left))
    y, mids, labels, bars = 0.0, [], [], {}
    for li, (kind, nsub, items) in enumerate(lanes):
        hgt = pad + nsub * sub
        ax.axhspan(y, y + hgt, color="#f3f2ee" if li % 2 else figures.BG, lw=0, zorder=0)
        mids.append(y + hgt / 2)
        for j, (k, over) in items:
            a, b = _extent(j, now)
            s0, s1 = N(max(a, x0)), N(min(b, x1))
            yc = y + pad / 2 + (k + 0.5) * sub
            fill, edge, _, _ = JOB_STATES[shown(j)]
            ax.barh(yc, max(s1 - s0, per_in * 0.02), left=s0, height=sub * 0.7, color=fill, edgecolor=edge,
                    lw=0.6, zorder=3, alpha=0.5 if over else 1.0, hatch="//" if shown(j) == "void" else None)
            bars.setdefault((li, k), []).append((s0, s1))
            labels.append((li, k, s0, s1, yc, f"#{j['n']} {j['name']}", shown(j)))
        y += hgt
    taken: dict = {}
    gap = 0.04 * per_in
    for li, k, s0, s1, yc, text, st in labels:   # inside the bar, else right of it, else left, else dropped
        wd = _text_in(text) * per_in
        if wd + 2 * gap <= s1 - s0:
            a, colour = s0 + gap, JOB_STATES[st][2]
        else:
            clash = [(u, v) for u, v in bars[(li, k)] if (u, v) != (s0, s1)] + taken.get((li, k), [])
            a = next((a for a in (s1 + gap, s0 - gap - wd) if N(x0) <= a and a + wd <= N(x1)
                      and not any(a < v and a + wd > u for u, v in clash)), None)
            if a is None:
                continue
            colour = "#202124"
        taken.setdefault((li, k), []).append((a, a + wd))
        ax.text(a, yc, text, fontsize=FONT, va="center", ha="left", color=colour, zorder=5)
    ax.set_ylim(max(y, jobs_h), 0)   # y units are inches of panel; spare height stays blank below the lanes
    ax.set_yticks(mids, kinds, fontweight="bold")
    ax.tick_params(axis="y", length=0)
    ax.set_title(title, fontsize=11)
    pts = sorted({x0, x1, *(t for j in shown_jobs if j.get("started_utc")
                            for t in _extent(j, now) if x0 <= t <= x1)})
    spans = [_extent(j, now) for j in shown_jobs if j.get("started_utc")]
    counts = [sum(a <= t < b or (b == now and t == now) for a, b in spans) for t in pts]
    ax2.step([N(t) for t in pts], counts, where="post", color=rt.BLUE, lw=1.2)
    ax2.set_ylim(0, max(counts + [1]) * 1.2)
    ax2.set_ylabel("jobs running", fontsize=FONT + 1)
    if hi >= now:
        for a_ in (ax, ax2):
            a_.axvline(N(now), color="#c8312b", ls="--", lw=0.8, zorder=6)
    ax2.set_xlim(N(x0), N(x1))
    span_h = (x1 - x0).total_seconds() / 3600
    step = next(k for k in (1, 2, 3, 6, 12, 24, 48) if span_h / k <= (8 if pageless else 4) or k == 48)
    ax2.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, min(step, 24)), interval=max(step // 24, 1), tz=rt.TZ))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M", tz=rt.TZ))
    ax2.tick_params(labelsize=FONT + 1)
    ax2.set_xlabel(f"{local(now):%Z}", fontsize=FONT + 1)
    states = [s for s in JOB_STATES if any(shown(j) == s for j in shown_jobs)]
    handles = [Patch(fc=JOB_STATES[s][0], ec=JOB_STATES[s][1], label=JOB_STATES[s][3]) for s in states]
    if hi >= now:
        handles.append(Line2D([], [], color="#c8312b", ls="--", lw=0.8, label="now"))
    fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 8 if pageless else 4), fontsize=FONT,
               handlelength=1.2, columnspacing=0.8)
    return figures.save(fig, out)


def _section(md: str, name: str) -> str:
    """The body of report.md's `name` section (heading optionally numbered), up to the next heading at its level."""
    m = re.search(rf"^(#+)[ \t]*(?:\d+[.)][ \t]*)?{re.escape(name)}\b[^\n]*\n", md, re.M | re.I)
    if not m:
        return ""
    end = re.search(rf"^#{{1,{len(m.group(1))}}}[ \t]", md[m.end():], re.M)
    return md[m.end():m.end() + end.start() if end else None].strip()


def _md(md: str, src_dir: str) -> str:
    return md2ghtml.convert(md, src_dir)[1] if md else "<p>Not written yet.</p><p></p>"


def _counts(jobs: list[dict]) -> str:
    c = {s: sum(shown(j) == s for j in jobs) for s in JOB_STATES}
    return ", ".join(f"{n} {s}" for s, n in c.items() if n) or "no jobs"


def _gpu_h(jobs: list[dict]) -> float:
    return sum(j.get("cost_gpu_h") or 0 for j in jobs)


def _learnings(st: dict) -> list[str]:
    if st.get("learnings"):
        return [esc(x) for x in st["learnings"][:5]]
    done = sorted(((k, s) for k, s in st["studies"].items() if s.get("status") == "concluded" and s.get("short_answer")),
                  key=lambda kv: (kv[1].get("concluded_utc") or "", kv[0]), reverse=True)[:5]
    return [f"<b>{esc(s.get('title') or k)}</b>: {esc(s['short_answer'])}" for k, s in done]


def render(run_dir: str, now: datetime, held: dict | None = None) -> dict[str, str]:
    """{experiments|experiment_log|studies: html} for each tab whose source exists; {} with no state file."""
    run_dir = os.path.abspath(run_dir)
    sp = os.path.join(run_dir, "experiments", "state.json")
    if not os.path.exists(sp):
        return {}
    run = read_json(os.path.join(run_dir, "pipeline.json"))
    rt.TZ = ZoneInfo(run.get("owner_tz") or "America/Los_Angeles")
    st = read_json(sp)
    st.setdefault("jobs", [])
    st.setdefault("studies", {})
    jobs = sorted(st["jobs"], key=lambda j: j["n"])
    docs, pageless, tzl = run.get("docs") or {}, bool(run.get("pageless")), f"{local(now):%Z}"
    title = lambda k, t: f'<p data-style="TITLE">{esc((docs.get(k) or {}).get("title") or t)}</p>'  # noqa: E731
    figdir = os.path.join(run_dir, "experiments", "fig")
    out = {}
    done = concluded_units(st, (held or {}).get("experiments") or [], now)
    live = [j for j in jobs if unit_of(j) not in done]
    logged = [j for j in jobs if unit_of(j) in done]
    windows = rt.timeline_windows([{"ts": j["launched_utc"]} for j in jobs if j.get("launched_utc")], now)

    if jobs:
        studies = st["studies"].values()
        status = (f"{sum(shown(j) in ('running', 'starting') for j in jobs)} running, "
                  f"{sum(shown(j) == 'queued' for j in jobs)} queued; studies: "
                  f"{sum(s.get('status') in ('running', 'reopened') for s in studies)} running, "
                  f"{sum(s.get('status') == 'concluded' for s in studies)} concluded")
        if st.get("sweep_stopped"):
            status += f"; sweep stopped ({esc(st['sweep_stopped'])})"
        h = [title("experiments", "Experiments"), "<h2>Summary</h2>" + _table(["", ""], [
            ("<b>Status</b>", status),
            ("<b>Cost spent</b>", f"{_gpu_h(jobs):.1f} GPU-h; jobs: {_counts(jobs)}"),
            ("<b>Learnings</b>", "<br>".join("• " + x for x in _learnings(st)) or "None yet."),
            ("<b>Bottom line</b>", esc(st.get("bottom_line")) or "Not yet."),
        ])]
        if timeline(jobs, now, os.path.join(figdir, "timeline.png"), pageless, now - rt.TIMELINE_WINDOW, now,
                    f"Jobs, last 48 h, updated {local(now):%Y-%m-%d %H:%M %Z}"):
            older = (" Older 48-hour blocks are on the " + _tab_link(run, "experiment_log", "Experiment log tab") + ".") if windows else ""
            h.append(_figure(figdir, "timeline.png", "jobs timeline", 1,
                             "Jobs in the last 48 hours, one lane per kind, coloured by state; the lower panel counts "
                             "jobs running, and the dashed line is now." + older))
        h.append("<p>Job state: " + " ".join(_chip(s) for s in JOB_STATES) + ". Rows move to the "
                 + _tab_link(run, "experiment_log", "Experiment log") + " once their study (or the job alone) has "
                 "concluded and no comment is open on them.</p>")
        h.append(_table(HEAD[:1] + [f"Date ({tzl})"] + HEAD[2:], [row(j, now) for j in live]) if live
                 else "<p>No live jobs.</p><p></p>")
        out["experiments"] = "\n".join(h) + "\n"

    def archived(j: dict) -> bool:   # an entry listing "units" cuts only those units; older entries cut every n <= through_n
        return any(j["n"] <= (a.get("through_n") or 0) and ("units" not in a or unit_of(j) in a["units"])
                   for a in st.get("archive") or [])

    if logged or st.get("archive") or windows:
        h = [title("experiment_log", "Experiment log")]
        if st.get("archive"):
            h.append("<p>Older rows: paste " + ", ".join(esc(a["paste"]) for a in st["archive"]) + "</p>")
        rows = [row(j, now) for j in sorted(logged, key=lambda j: -j["n"]) if not archived(j)]
        h.append(_table(HEAD[:1] + [f"Date ({tzl})"] + HEAD[2:], rows) if rows else "<p></p>")
        blocks = []
        for i, (a, b) in enumerate(windows, 1):
            name = f"timeline-{local(a):%Y%m%d%H%M}.png"
            rng = f"{local(a):%b %d %H:%M} to {local(b):%b %d %H:%M} {tzl}"
            if timeline(jobs, now, os.path.join(figdir, name), pageless, a, b, f"Jobs, {rng}"):
                blocks.append(f"<h3>{rng}</h3>" + _figure(figdir, name, "jobs timeline", f"E{i}",
                                                          "Jobs in this 48-hour block, drawn as on the Experiments tab."))
        if blocks:
            h.append("<h2>Timeline</h2>" + "".join(blocks))
        out["experiment_log"] = "\n".join(h) + "\n"

    if st["studies"]:
        order = sorted(st["studies"].items(), key=lambda kv: (kv[1].get("opened_utc") or "", kv[0]))
        by = {k: [j for j in jobs if j.get("study") == k] for k, _ in order}
        index = []
        for k, s in order:
            lt = s.get("learnings_tab") or ""   # a docs key (study-<id>), or a raw tab id "t.<...>"
            key = lt if lt in docs else f"study-{k}"
            tab = (docs.get(key) or {}).get("tab") or (lt if lt.startswith("t.") else None)
            link = _tab_link(run, key, "Learnings", tab) if tab else "-"
            index.append((esc(k), esc(s.get("title")), esc(s.get("question")), esc(s.get("status")),
                          esc(s.get("short_answer")), link, f"{len(by[k])}, {_gpu_h(by[k]):.1f} GPU-h"))
        h = [title("studies", "Studies"),
             _table(["ID", "Study", "Question", "Status", "Short answer", "Learnings", "Jobs"], index)]
        fig_n = 0
        for k, s in order:
            sdir = os.path.join(run_dir, "studies", k)
            rp = os.path.join(sdir, "report.md")
            md = open(rp, encoding="utf-8").read() if os.path.exists(rp) else ""
            h.append(f"<h2>{esc(k)}: {esc(s.get('title'))}</h2><p><b>Question:</b> {esc(s.get('question'))}</p>")
            h.append("<h3>What we did</h3>" + _md(_section(md, "Design"), sdir)
                     + f"<p>Jobs: {_counts(by[k])} ({_gpu_h(by[k]):.1f} GPU-h).</p>")
            h.append("<h3>Results</h3>" + _md(_section(md, "Results"), sdir))
            if os.path.exists(os.path.join(sdir, "figs", "summary.png")):
                fig_n += 1
                h.append(_figure(os.path.join(sdir, "figs"), "summary.png", f"{k} summary", fig_n,
                                 f"{esc(s.get('title') or k)}: lead figure."))
            if s.get("learnings"):
                h.append("<h3>What we learned</h3><ul>" + "".join(f"<li>{esc(x)}</li>" for x in s["learnings"])
                         + "</ul><p></p>")
            stat = esc(s.get("status") or "running") + (f", verdict {esc(s['verdict'])}" if s.get("verdict") else "")
            if s.get("concluded_utc") and s.get("status") == "concluded":
                stat += f", concluded {local(parse_ts(s['concluded_utc'])):%Y-%m-%d %H:%M %Z}"
            h.append(f"<p><b>Status:</b> {stat}.</p><p></p>")
        out["studies"] = "\n".join(h) + "\n"
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run")
    ap.add_argument("outdir")
    ap.add_argument("--held-json")
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    try:
        held = read_json(a.held_json) if a.held_json else {}
        tabs = render(a.run, parse_ts(a.now) if a.now else now_utc(), held)
    except (ValueError, OSError, KeyError) as e:
        print(f"render_experiments: {e!r}", file=sys.stderr)
        return 1
    os.makedirs(a.outdir, exist_ok=True)
    for key, body in tabs.items():
        with open(os.path.join(a.outdir, f"{key}.html"), "w", encoding="utf-8") as f:
            f.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
