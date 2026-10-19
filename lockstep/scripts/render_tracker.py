#!/usr/bin/env python3
"""Render the live tracker dashboard from run state.

Usage: render_tracker.py RUN_DIR OUT.html
Reads RUN_DIR/pipeline.json, RUN_DIR/run.json (sdd state, PLAN/BUILD/LAND), RUN_DIR/events.jsonl and RUN_DIR/request.md;
writes figures to RUN_DIR/tracker/ and a ghtml body to OUT.html. Images are absolute file:// paths, so deliver with
`meta google.docs apply` (create cannot stage local images).
"""
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from state import now_utc, parse_ts, read_events, read_json  # noqa: E402,F401

PHASES = ["INIT", "RESEARCH", "PROPOSAL", "SPEC", "PLAN", "BUILD", "LAND", "DONE"]
PHASE_LABEL = {"PLAN": "Plan\\n(write + harden)", "BUILD": "Build\\n(implement)", "LAND": "Land\\n(optional review, merge)"}
BLUE, ORANGE, GREY, LIGHT = "#2a78d6", "#eb6834", "#52514e", "#efeeea"
TASK_STATES = {  # state: (fill, border, font, legend)
    "pending": ("#efeeea", "#8a8984", "#52514e", "not started"),
    "in_progress": ("#2a78d6", "#2a78d6", "white", "in progress"),
    "complete": ("#2e9e5b", "#2e9e5b", "white", "complete"),
    "parked": ("#eb6834", "#eb6834", "white", "parked on your answer"),
    "blocked": ("#c8312b", "#c8312b", "white", "blocked"),
}
CREDENTIAL = [  # mask only the value; KEY=value (incl. MY_TOKEN, client_secret, "token: Bearer x"), then bare bearer tokens
    re.compile(r"(?i)(?<![A-Za-z0-9])([A-Za-z0-9_]*(?:token|secret|password|passwd|api[_-]?key|access[_-]?key))"
               r"([ \t]*[:=][ \t]*(?:bearer[ \t]+)?)([^\s\[][^\s]*)"),
    re.compile(r"(?i)(?<![A-Za-z0-9])(bearer)([ \t]+)([A-Za-z0-9._~+/-]{20,})")]
OWNER_KINDS = ("comment", "answer", "requirement", "accept", "changes", "confirm", "action")
UNBLOCK = {"sdd": "fix the remediation in run.json blocked_reason, comment `Action: unblock`, then reply Confirm",
           "doc_not_private": "remove the extra sharing on that doc; the next check clears this",
           "all_parked": "answer the parked task docs listed below", "reopen": "accept the reopened doc again"}
STEER = ('<h2>How to steer this run</h2><table><tr><th>Comment (on the title)</th><th>Example</th></tr>'
         "<tr><td>Action</td><td>Action: pause / resume / abort / unblock / close</td></tr>"
         "<tr><td>Confirm</td><td>reply Confirm under a \u201cNeeds Confirm\u201d reply</td></tr>"
         "<tr><td>Diff ids</td><td>D123456789 (recorded for the Land phase)</td></tr>"
         "</table><p></p>")


def fmt_dur(sec):
    sec = int(max(sec, 0))
    h, m = divmod(sec // 60, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def hhmm(s):
    return s[:16].replace("T", " ") if s else ""


def mask_credentials(text: str) -> tuple[str, list[str]]:
    keys = []
    for pat in CREDENTIAL:
        def sub(m):
            keys.append(m.group(1))
            return m.group(1) + m.group(2) + "[credential masked]"
        text = pat.sub(sub, text)
    return text, keys


# Only active time counts: the skill doing real work, or the owner engaged (reading, commenting, messaging).
OWNER_GAP = 10 * 60   # owner comments closer than this belong to one reading session (decision Q8)
LEAD_IN = 5 * 60      # reading before the first comment of a session
SKILL_GAP = 45 * 60   # after a work event, a quiet gap longer than this means nothing was running
IDLE_KINDS = ("tick", "gate_open")   # after these the agent waits for the owner unless a unit is running
OWNER_ACTIVITY = OWNER_KINDS + ("reopen", "owner_active")


def _merge(spans):
    out = []
    for s, t in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], t))
        else:
            out.append((s, t))
    return out


def owner_spans(events: list[dict], doc: str | None = None) -> list[tuple[datetime, datetime]]:
    """Reading sessions: owner activity with gaps under OWNER_GAP, each from LEAD_IN before its first comment."""
    ts = sorted(parse_ts(e.get("comment_ts") or e["ts"]) for e in events
                if e["kind"] in OWNER_ACTIVITY and (doc is None or e.get("doc") == doc))
    sessions = []
    for t in ts:
        if sessions and (t - sessions[-1][1]).total_seconds() < OWNER_GAP:
            sessions[-1][1] = t
        else:
            sessions.append([t, t])
    return _merge([(s - timedelta(seconds=LEAD_IN), t) for s, t in sessions])


def skill_spans(events: list[dict], now: datetime) -> list[tuple[datetime, datetime]]:
    """When the agent was working, whether or not the owner was around.

    A unit (unit_start to unit_done, or to now while it runs) counts in full however quiet it is. Outside
    units, the gap after a work event counts unless it ran past SKILL_GAP; quiet polls and an open gate are
    the agent waiting, not working."""
    spans, open_units = [], {}
    # Owner messages never split skill time; backfilled events may be out of file order.
    events = sorted((e for e in events if e["kind"] != "owner_active"), key=lambda e: parse_ts(e["ts"]))
    for i, e in enumerate(events):
        s = parse_ts(e["ts"])
        if e["kind"] == "unit_start":
            open_units.setdefault(e["event"], s)
        elif e["kind"] == "unit_done" and e["event"] in open_units:
            spans.append((open_units.pop(e["event"]), s))
        if e["kind"] in IDLE_KINDS:
            continue
        t = parse_ts(events[i + 1]["ts"]) if i + 1 < len(events) else now
        if (t - s).total_seconds() <= SKILL_GAP:
            spans.append((s, t))
    spans += [(s, now) for s in open_units.values()]
    return _merge(spans)


def overlap(spans, a: datetime, b: datetime) -> float:
    return sum(max(0.0, (min(t, b) - max(s, a)).total_seconds()) for s, t in spans)


def active_pieces(events: list[dict], now: datetime) -> list[tuple[datetime, datetime, str]]:
    """The union of skill and owner time, split into pieces labelled "you", "skill" or "both"."""
    own, sk = owner_spans(events), skill_spans(events, now)
    cuts = sorted({x for s, t in own + sk for x in (s, t)})
    pieces = []
    for a, b in zip(cuts, cuts[1:]):
        o, k = overlap(own, a, b), overlap(sk, a, b)
        who = "both" if o and k else "you" if o else "skill" if k else None
        if who:
            if pieces and pieces[-1][1] == a and pieces[-1][2] == who:
                pieces[-1] = (pieces[-1][0], b, who)
            else:
                pieces.append((a, b, who))
    return pieces


def plan_tasks(plan_path):
    """[(n, title, deps)] from '### Task N: Title' headings and their '**Depends on:**' lines."""
    tasks, text = [], open(plan_path).read()
    for m in re.finditer(r"^### Task (\d+): (.+)$", text, re.M):
        dm = re.match(r"\s*\*\*Depends on:\*\* (.+)", text[m.end():].lstrip("\n"))
        deps = [int(x) for x in re.findall(r"Task (\d+)", dm.group(1))] if dm else []
        tasks.append((int(m.group(1)), re.sub(r"[`*]", "", m.group(2)).strip(), deps))
    return tasks


def flow_chart(run, out):
    """Phase flowchart: start/end states, an accept decision with a revise loop for each gated doc."""
    current = run.get("phase", "PROPOSAL")
    gates = {k: v.get("status", "") for k, v in run.get("docs", {}).items() if isinstance(v, dict)}
    lines = ['digraph G { graph [rankdir=LR, bgcolor="#fcfcfb", pad=0.3, nodesep=0.35, ranksep=0.4];',
             'node [shape=box, style="rounded,filled", fontname="Liberation Sans", fontsize=13, penwidth=2];',
             'edge [color="#8a8984", penwidth=2, fontname="Liberation Sans", fontsize=10, fontcolor="#52514e"];',
             'start [shape=ellipse, label="request", fillcolor="#e3eefb", color="#2a78d6"];']
    done = True
    for p in PHASES:
        if p == "DONE":
            fill, col, font = (BLUE, BLUE, "white") if p == current else ("#e3eefb", BLUE, "#0b0b0b") if done else (LIGHT, GREY, "#52514e")
            lines.append(f'DONE [shape=ellipse, label="done", fillcolor="{fill}", color="{col}", fontcolor="{font}"];')
            continue
        if p == current:
            done = False
            fill, col, font = BLUE, BLUE, "white"
        elif done:
            fill, col, font = "#e3eefb", BLUE, "#0b0b0b"
        else:
            fill, col, font = LIGHT, GREY, "#52514e"
        label = PHASE_LABEL.get(p, p.title())
        g = gates.get(p.lower())
        if g:
            label += f"\\n({g.replace('_', ' ')})"
        lines.append(f'{p} [label="{label}", fillcolor="{fill}", color="{col}", fontcolor="{font}"];')
    chain = ["start"] + PHASES
    for a, b in zip(chain, chain[1:]):
        if a in ("PROPOSAL", "SPEC"):
            lines.append(f'{a}_ok [shape=diamond, style=filled, fillcolor="#fcfcfb", color="#8a8984", label="accepted?", fontsize=11];')
            lines.append(f'{a} -> {a}_ok; {a}_ok -> {b} [label="yes"]; {a}_ok -> {a} [label="no: answer,\\nrefresh", style=dashed, constraint=false];')
        elif a == "LAND":
            lines.append('LAND_ok [shape=diamond, style=filled, fillcolor="#fcfcfb", color="#8a8984", label="all code\\nlanded?", fontsize=11];')
            lines.append('LAND -> LAND_ok; LAND_ok -> DONE [label="yes"]; LAND_ok -> LAND [label="no: review\\nfixes", style=dashed, constraint=false];')
        else:
            lines.append(f"{a} -> {b};")
    lines.append("}")
    dot = out.replace(".png", ".dot")
    open(dot, "w").write("\n".join(lines))
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", dot, "-o", out], check=True)


def task_states(run_dir, sdd, tasks, events):
    """State per task from ledger.md lines, else in progress for a task_start with no task_done; timings from events."""
    states = {n: "pending" for n, _, _ in tasks}
    ledger = os.path.join(run_dir, "ledger.md")
    for line in (open(ledger).read().splitlines() if os.path.exists(ledger) else []):
        m = re.match(r"\s*Task (\d+): (complete|parked|blocked)", line)
        if m and int(m.group(1)) in states:
            states[int(m.group(1))] = m.group(2)
    times = {}
    for e in events:
        if e.get("task") and e["kind"] in ("task_start", "task_done"):
            t = times.setdefault(e["task"], {})
            if e["kind"] == "task_start":
                t.setdefault("task_start", parse_ts(e["ts"]))  # first start, for duration
                t["last_start"] = parse_ts(e["ts"])
            else:
                t["task_done"] = parse_ts(e["ts"])
    for n, t in times.items():
        if states.get(n) == "pending" and "last_start" in t and not (t.get("task_done") and t["task_done"] >= t["last_start"]):
            states[n] = "in_progress"  # started, and no task_done after the latest start (covers retries)
    return states, times


def task_chart(tasks, states, out):
    lines = ['digraph T { graph [rankdir=LR, bgcolor="#fcfcfb", pad=0.3, nodesep=0.25, ranksep=0.45];',
             'node [shape=box, style="rounded,filled", fontname="Liberation Sans", fontsize=12, penwidth=2];',
             'edge [color="#8a8984", penwidth=1.5];',
             'start [shape=ellipse, label="spec accepted", fillcolor="#e3eefb", color="#2a78d6"];',
             'end [shape=ellipse, label="all tasks\\ncomplete", fillcolor="#e3eefb", color="#2a78d6"];']
    dep = {n: set(d) for n, _, d in tasks}

    def reach(n, seen=None):
        seen = set() if seen is None else seen
        for d in dep.get(n, ()):
            if d not in seen:
                seen.add(d); reach(d, seen)
        return seen
    direct = {n: {d for d in ds if not any(d in reach(o) for o in ds - {d})} for n, ds in dep.items()}
    have_children = {d for ds in direct.values() for d in ds}
    known = {n for n, _, _ in tasks}
    for n, title, _ in tasks:
        deps = sorted(d for d in direct[n] if d in known)
        fill, col, font, _ = TASK_STATES[states[n]]
        short = title if len(title) <= 28 else title[:26] + "…"
        short = short.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'T{n} [label="T{n}\\n{short}", fillcolor="{fill}", color="{col}", fontcolor="{font}"];')
        lines += [f"T{d} -> T{n};" for d in deps] or [f"start -> T{n};"]
        if n not in have_children:
            lines.append(f"T{n} -> end;")
    lines.append('subgraph cluster_legend { label="Task state"; fontname="Liberation Sans"; fontsize=11; color="#d6d5d0";')
    for k, (fill, col, font, legend) in TASK_STATES.items():
        lines.append(f'L_{k} [label="{legend}", fillcolor="{fill}", color="{col}", fontcolor="{font}", fontsize=10];')
    lines.append(" -> ".join(f"L_{k}" for k in TASK_STATES) + ' [style=invis]; }')
    lines.append("}")
    dot = out.replace(".png", ".dot")
    open(dot, "w").write("\n".join(lines))
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", dot, "-o", out], check=True)


def time_split(events: list[dict], now: datetime) -> tuple[float, float, float]:
    """(owner seconds, agent seconds, active seconds). Each side counts its own time; the owner being away
    only lowers the owner's share, so time both worked counts for both and active = you + agent - both."""
    span = lambda spans: sum((t - s).total_seconds() for s, t in spans)
    total = sum((b - a).total_seconds() for a, b, _ in active_pieces(events, now))
    return span(owner_spans(events)), span(skill_spans(events, now)), total


def timeline_chart(events, now, out):
    """Active time only: idle stretches are cut out and marked with how long nothing was happening."""
    pieces = active_pieces(events, now)
    fig, ax = plt.subplots(figsize=(10, 2.8), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    phase_at = lambda t: next((e.get("phase") for e in reversed(events)
                               if parse_ts(e["ts"]) <= t and e.get("phase") in PHASES), "INIT")
    rows = [p for p in PHASES if any(phase_at(a) == p for a, _, _ in pieces)] or ["INIT"]
    x, prev = 0.0, None
    for a, b, who in pieces:
        if prev is not None and (a - prev).total_seconds() >= 15 * 60:
            ax.axvline(x, color=GREY, linestyle=":", linewidth=1)
            ax.text(x, -0.6, f"away {fmt_dur((a - prev).total_seconds())}", fontsize=7, color=GREY, ha="center")
        w, r = (b - a).total_seconds() / 60, rows.index(phase_at(a))
        if who in ("you", "both"):   # upper half: you engaged
            ax.barh(r - 0.13, w, left=x, height=0.26, color=ORANGE, edgecolor="#fcfcfb", linewidth=0.5)
        if who in ("skill", "both"):  # lower half: agent working
            ax.barh(r + 0.13, w, left=x, height=0.26, color=BLUE, edgecolor="#fcfcfb", linewidth=0.5)
        x, prev = x + w, b
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r.title() for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("active minutes (time when neither of you was working is cut out)")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#e5e4e0")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ORANGE, label="you engaged (reading, commenting)"), Patch(color=BLUE, label="agent working")],
              loc="lower center", bbox_to_anchor=(0.5, 1.08), ncol=2, frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor="#fcfcfb")
    plt.close(fig)


def esc(v) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def _doc_link(d, fallback):
    title = esc(d.get("title") or fallback)
    return f'<a href="https://docs.google.com/document/d/{esc(d["id"])}/edit">{title}</a>' if d.get("id") else title


def _qcount(run_dir, d):
    qf = d.get("questions_file")
    if not qf or not os.path.exists(os.path.join(run_dir, qf)):
        return ""
    return f"{len(d.get('answered') or [])}/{len(read_json(os.path.join(run_dir, qf)))}"


def _table(head, rows):
    out = "<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
    out += "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return out + "</table><p></p>"


def _figure(figdir, name, alt, n, caption):
    return (f'<p style="text-align:center"><img src="file://{figdir}/{name}" alt="{alt}"></p>'
            f'<p style="text-align:center"><i>Figure {n}. {caption}</i></p><p></p>')


def render(run_dir: str, now: datetime) -> str:
    run_dir = os.path.abspath(run_dir)
    run = read_json(os.path.join(run_dir, "pipeline.json"))
    for key in ("docs", "tracker_status"):
        if key not in run:
            raise ValueError(f"pipeline.json is missing {key}; refusing to render a tracker without it")
    req_path = os.path.join(run_dir, "request.md")
    if not os.path.exists(req_path):
        raise ValueError("request.md is missing; the tracker always shows the original request verbatim")
    sdd_path = os.path.join(run_dir, "run.json")
    pre_plan = run.get("phase") in (None, "INIT", "RESEARCH", "PROPOSAL", "SPEC")
    sdd = read_json(sdd_path) if not pre_plan and os.path.exists(sdd_path) else {}
    events = read_events(run_dir) if os.path.exists(os.path.join(run_dir, "events.jsonl")) else []
    request, masked = mask_credentials(open(req_path, errors="replace").read().strip())
    if masked:
        note = f"credential masked in request.md ({', '.join(sorted(set(masked)))})"
        if not any(e["event"] == note for e in events):
            from state import append_event
            events.append(append_event(run_dir, "blocked", note, now=now))
    figdir = os.path.join(run_dir, "tracker")
    os.makedirs(figdir, exist_ok=True)
    flow_chart(run, os.path.join(figdir, "flow.png"))
    if events:
        timeline_chart(events, now, os.path.join(figdir, "timeline.png"))
    own_all, skill_all = owner_spans(events), skill_spans(events, now)
    you_s, agent_s, tot_s = time_split(events, now)
    tot_m, you_m, agent_m = round(tot_s / 60), round(you_s / 60), round(agent_s / 60)
    both_m = you_m + agent_m - tot_m   # derived from the displayed numbers so they add up exactly
    active = lambda a, b: overlap(_merge(own_all + skill_all), a, b)
    t0 = parse_ts(events[0]["ts"]) if events else now
    st = run["tracker_status"]
    since = f" (since {hhmm(st['since'])})" if st.get("since") else ""
    h = ['<p data-style="TITLE">' + esc(run.get("tracker_title", "Tracker")) + "</p>", STEER]
    h.append("<h2>Status</h2>" + _table(["", ""], [
        ("<b>Last updated</b>", f"{now:%Y-%m-%d %H:%M} UTC (tick {esc(run.get('tick', 0))})"),
        ("<b>Status</b>", esc(run.get("status", ""))),
        ("<b>Time spent</b>", f"{fmt_dur(tot_m * 60)} active: you {fmt_dur(you_m * 60)} + agent {fmt_dur(agent_m * 60)}"
                              + (f" − {fmt_dur(both_m * 60)} when both of you were working" if both_m > 0 else "")
                              + " (your time away is not yours, but counts for the agent while it works; "
                                "the agent waiting on you counts for neither)"),
        ("<b>Now</b>", esc(st.get("now", "")) + (f" (sdd stage {esc(sdd.get('stage'))})" if sdd else "")),
        ("<b>Waiting on</b>", esc(st.get("waiting_on", "")) + since),
        ("<b>Next wake</b>", esc(st.get("next_wake", ""))),
    ]))
    h.append("<h2>Where the run is</h2>" + _figure(figdir, "flow.png", "run phases", 1,
             "Run phases from request to done; the current phase is filled blue, each gated doc shows its state, "
             "and the dashed edges are the review loops."))
    if events:
        h.append("<h2>Timeline</h2>" + _figure(figdir, "timeline.png", "timeline", 2,
                 "Active time only, by phase: you engaged (upper bar) and the agent working (lower bar), counted separately. Stretches when neither of you was working (you away and the agent idle or waiting on you) are cut out; dotted lines mark the breaks."))

    plan_path = sdd.get("plan_path") and os.path.join(run_dir, sdd["plan_path"])
    tasks, states, times = [], {}, {}
    if plan_path and os.path.exists(plan_path):
        tasks = plan_tasks(plan_path)
        states, times = task_states(run_dir, sdd, tasks, events)
        task_chart(tasks, states, os.path.join(figdir, "tasks.png"))
        goal = re.search(r"^\*\*Goal:\*\* (.+)$", open(plan_path).read(), re.M)
        done = sum(v == "complete" for v in states.values())
        h.append(f"<h2>Implementation plan</h2><p>Full plan: {_doc_link(run['docs'].get('plan', {}), sdd['plan_path'])}. "
                 f"sdd stage: {esc(sdd.get('stage', ''))}. Tasks complete: {done}/{len(tasks)}.</p>")
        if goal:
            h.append(f"<p><b>Goal:</b> {esc(goal.group(1))}</p>")
        h.append(_figure(figdir, "tasks.png", "task flow", 3, "Plan tasks with their dependencies, coloured by state."))
        rows = []
        for n, title, deps in tasks:
            t = times.get(n, {})
            start = f"{t['task_start']:%m-%d %H:%M}" if "task_start" in t else ""
            dur = fmt_dur(overlap(skill_all, t["task_start"], t.get("task_done") or now)) if "task_start" in t else ""
            rows.append((f"T{n}", esc(title), ", ".join(f"T{d}" for d in deps) or "-", TASK_STATES[states[n]][3], start, dur))
        h.append(_table(["ID", "Task", "Depends on", "State", "Started (UTC)", "Duration"], rows))

    tests = {}
    for e in events:
        if e["kind"] == "test_run":
            tests[e.get("task")] = tests.get(e.get("task"), 0) + 1
    diff_ev = {}
    for e in events:
        if e["kind"].startswith("diff_") and e.get("diff"):
            diff_ev.setdefault(str(e["diff"]), {})[e["kind"][5:]] = hhmm(e["ts"])
    end = next((parse_ts(e["ts"]) for e in reversed(events) if e["kind"] == "done"), None)
    h.append("<h2>Build to closure</h2><p>Request to closure: "
             f"{fmt_dur(active(t0, end or now))} active{'' if end else ' so far'} "
             f"({fmt_dur(((end or now) - t0).total_seconds())} wall clock). Test runs: {sum(tests.values())}.</p>")
    closure = [(f"T{n}", fmt_dur(overlap(skill_all, t["task_start"], t["task_done"])) if "task_done" in t else "running",
                str(tests.get(n, 0))) for n, t in sorted(times.items()) if "task_start" in t]
    if closure:
        h.append(_table(["Task", "Implementation time", "Test runs"], closure))
    if diff_ev:
        h.append(_table(["Diff", "Created", "Published", "Reviewed", "Landed"],
                        [(esc(d), v.get("created", ""), v.get("published", ""), v.get("reviewed", ""), v.get("landed", ""))
                         for d, v in diff_ev.items()]))

    gates = []
    for k, d in run["docs"].items():
        if not isinstance(d, dict) or not d.get("id") or d.get("kind") in ("plan", "explainer", "external"):
            continue
        versions = sum(1 for e in events if e.get("doc") == k and e["kind"] in ("published", "humanize"))
        wait = overlap(owner_spans(events, k), t0, now)
        gates.append((_doc_link(d, k), str(versions or 1), esc(d.get("status", "").replace("_", " ")),
                      hhmm(d.get("opened_at")), hhmm(d.get("accepted_at")), fmt_dur(wait), _qcount(run_dir, d)))
    h.append("<h2>Gates</h2>" + _table(["Doc", "Version", "Status", "Opened", "Accepted", "Your active time", "Questions"], gates))

    ms, cum, last, phase0 = [], 0, None, None
    for e in events:
        if e["kind"] != "milestone":
            continue
        t = parse_ts(e["ts"])
        if e.get("phase") != phase0:
            cum, phase0 = 0, e.get("phase")
        elif last:
            cum += (t - last).total_seconds()
        ms.append((hhmm(e["ts"]), esc((e.get("phase") or "").title()), esc(e["event"]),
                   fmt_dur((t - last).total_seconds()) if last else "", fmt_dur(cum)))
        last = t
    h.append("<h2>Milestones</h2>" + _table(
        ["Time (UTC)", "Phase", "Milestone", "Since previous", "Since first milestone in phase"], ms))

    fu = []
    dec = os.path.join(run_dir, "decisions.md")
    if os.path.exists(dec):
        sec = re.search(r"^## Follow-ups\n(.*?)(?=^## |\Z)", open(dec, errors="replace").read(), re.M | re.S)
        fu = [("follow-up", esc(line.lstrip("-* ").strip()), "")
              for line in (sec.group(1).splitlines() if sec else []) if line.strip()]
    for kind in ("blocked", "waiting"):
        for r in run.get(f"{kind}_reasons") or []:
            fu.append((kind, esc(r), UNBLOCK.get(str(r).split(":")[0], "")))
    h.append("<h2>Follow-ups and blockers</h2>" + (_table(["Type", "Item", "What clears it"], fu) if fu else "<p>None.</p><p></p>"))

    agents = sum(e.get("agents", 0) for e in events if isinstance(e.get("agents"), int))
    slops = [esc(e["slop"]) for e in events if "slop" in e]
    counters = run.get("counters") or {}
    h.append("<h2>Metrics</h2>" + _table(["", ""], [
        ("Active time on the project (you or the agent working)", fmt_dur(tot_s)),
        ("You engaged (reading, commenting, messaging)", fmt_dur(you_s)),
        ("Agent working (including while you were away; waiting on you excluded)", fmt_dur(agent_s)),
        ("Both of you working at the same time", fmt_dur(max(0.0, you_s + agent_s - tot_s))),
        ("Wall clock since request (reference only)", fmt_dur((now - t0).total_seconds())),
        ("Comments answered", str(sum(e["kind"] in ("comment", "answer", "requirement") for e in events))),
        ("Requirements added from comments", str(sum(e["kind"] == "requirement" for e in events))),
        ("Agents dispatched", esc(agents or counters.get("agents", 0))),
        ("Humanize passes", esc(counters.get("humanize_passes", 0))),
        ("Comment checks", esc(counters.get("checks", 0))),
        ("Doc quality (slop score, lower is better)", " -> ".join(slops) or "n/a"),
    ]))

    docs = []
    for k, d in run["docs"].items():
        if not isinstance(d, dict) or not d.get("id"):
            continue
        opened, accepted = d.get("opened_at", ""), d.get("accepted_at", "")
        if d.get("status") == "reference":
            wait = "not gated"
        elif opened and accepted:
            wait = fmt_dur((parse_ts(accepted) - parse_ts(opened)).total_seconds())
        else:
            wait = f"open {fmt_dur((now - parse_ts(opened)).total_seconds())}" if opened else ""
        docs.append((_doc_link(d, k), esc(d.get("status", "").replace("_", " ")), hhmm(opened), hhmm(accepted), wait,
                     _qcount(run_dir, d)))
    h.append("<h2>Docs produced</h2>" + _table(
        ["Doc", "Status", "Created (UTC)", "Accepted (UTC)", "Time to accept", "Questions answered"], docs))

    acts = [(hhmm(e["ts"]), esc(e.get("verb", "")), esc(e["event"]), esc(e.get("status", "")))
            for e in events if e["kind"] == "action"]
    h.append("<h2>Actions</h2>" + (_table(["Time (UTC)", "Verb", "Action", "Status"], acts) if acts else "<p>None yet.</p><p></p>"))

    parked = [(f"T{n}", _doc_link(run["docs"].get(f"task-{n}", {}), f"task-{n}"),
               hhmm(next((e["ts"] for e in events if e["kind"] == "task_parked" and e.get("task") == n), "")))
              for n, s in states.items() if s == "parked"]
    h.append("<h2>Parked tasks</h2>" + (_table(["Task", "Doc", "Since"], parked) if parked else "<p>None.</p><p></p>"))

    diffs = []
    for d, state_ in (run.get("diffs") or {}).items():
        link = f'<a href="https://www.internalfb.com/diff/{esc(d)}">{esc(d)}</a>' if re.fullmatch(r"D\d+", str(d)) else esc(d)
        diffs.append((link, esc(state_)))
    h.append("<h2>Diffs</h2>" + (_table(["Diff", "State"], diffs) if diffs else "<p>None recorded.</p><p></p>"))

    h.append("<h2>Original request (verbatim)</h2><p><i>" + esc(request) + "</i></p><p></p>")
    log, prev = [], None
    for e in events:
        t = parse_ts(e["ts"])
        log.append((hhmm(e["ts"]), esc((e.get("phase") or "").title()), esc(e["event"]),
                    fmt_dur((t - prev).total_seconds()) if prev else ""))
        prev = t
    h.append("<h2>Event log</h2>" + _table(["Time (UTC)", "Phase", "Event", "Since previous"], log))
    return "\n".join(h) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        body = render(argv[0], now_utc())
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 1
    open(argv[1], "w").write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
