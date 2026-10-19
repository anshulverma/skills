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
from datetime import datetime

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
UNBLOCK = {"sdd": "fix the remediation in run.json blocked_reason, then comment `Action: unblock`",
           "doc_not_private": "remove the extra sharing on that doc; the next check clears this",
           "all_parked": "answer the parked task docs listed below", "reopen": "accept the reopened doc again"}
STEER = ('<h2>How to steer this run</h2><table><tr><th>Comment (on the title)</th><th>Example</th></tr>'
         "<tr><td>Action</td><td>Action: pause / resume / abort / unblock / close</td></tr>"
         "<tr><td>Confirm</td><td>reply Confirm under a \u201cNeeds Confirm\u201d reply</td></tr>"
         "<tr><td>Diff ids</td><td>D123456789 (recorded for the Land phase)</td></tr>"
         "<tr><td>Reopen</td><td>Reopen: on an accepted doc, to put it back in review</td></tr>"
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


def waiting_intervals(events: list[dict], now: datetime) -> dict[str, list[tuple[datetime, datetime]]]:
    """Per doc: waits run from gate_open, confirm_pending or a pre-accept publish to the next owner comment or accept."""
    out, since, accepted = {}, {}, set()
    for e in events:
        doc, t = e.get("doc"), parse_ts(e["ts"])
        if not doc:
            continue
        if e["kind"] in ("gate_open", "confirm_pending") or (e["kind"] == "published" and doc not in accepted):
            since.setdefault(doc, t)
        elif e["kind"] in OWNER_KINDS and doc in since:
            out.setdefault(doc, []).append((since.pop(doc), t))
        if e["kind"] == "accept":
            accepted.add(doc)
        elif e["kind"] == "reopen":
            accepted.discard(doc)
    for doc, t in since.items():
        out.setdefault(doc, []).append((t, now))
    return out


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


def timeline_chart(events, now, out):
    waits = [w for ws in waiting_intervals(events, now).values() for w in ws]
    spans = []
    for i, e in enumerate(events):
        start = parse_ts(e["ts"])
        end = parse_ts(events[i + 1]["ts"]) if i + 1 < len(events) else now
        phase = e.get("phase") if e.get("phase") in PHASES else (spans[-1][0] if spans else "INIT")
        spans.append((phase, start, end, any(ws <= start and end <= we for ws, we in waits)))
    fig, ax = plt.subplots(figsize=(10, 2.6), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    t0 = parse_ts(events[0]["ts"])
    rows = [p for p in PHASES if any(s[0] == p for s in spans)]
    for phase, s, e, wait in spans:
        y = rows.index(phase)
        ax.barh(y, (e - s).total_seconds() / 60, left=(s - t0).total_seconds() / 60, height=0.5,
                color=ORANGE if wait else BLUE, edgecolor="#fcfcfb", linewidth=1.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r.title() for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("minutes since request")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#e5e4e0")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="skill working"), Patch(color=ORANGE, label="waiting on you")],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=9)
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
            events.append(append_event(run_dir, "milestone", note, now=now))
    figdir = os.path.join(run_dir, "tracker")
    os.makedirs(figdir, exist_ok=True)
    flow_chart(run, os.path.join(figdir, "flow.png"))
    if events:
        timeline_chart(events, now, os.path.join(figdir, "timeline.png"))
    waits = waiting_intervals(events, now)
    t0 = parse_ts(events[0]["ts"]) if events else now
    st = run["tracker_status"]
    since = f" (since {hhmm(st['since'])})" if st.get("since") else ""
    h = ['<p data-style="TITLE">' + esc(run.get("tracker_title", "Tracker")) + "</p>", STEER]
    h.append("<h2>Status</h2>" + _table(["", ""], [
        ("<b>Last updated</b>", f"{now:%Y-%m-%d %H:%M} UTC (tick {esc(run.get('tick', 0))})"),
        ("<b>Status</b>", esc(run.get("status", ""))),
        ("<b>Now</b>", esc(st.get("now", "")) + (f" (sdd stage {esc(sdd.get('stage'))})" if sdd else "")),
        ("<b>Waiting on</b>", esc(st.get("waiting_on", "")) + since),
        ("<b>Next wake</b>", esc(st.get("next_wake", ""))),
    ]))
    h.append("<h2>Where the run is</h2>" + _figure(figdir, "flow.png", "run phases", 1,
             "Run phases from request to done; the current phase is filled blue, each gated doc shows its state, "
             "and the dashed edges are the review loops."))
    if events:
        h.append("<h2>Timeline</h2>" + _figure(figdir, "timeline.png", "timeline", 2,
                 "Time per phase, split into the skill working and waiting on you."))

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
            dur = fmt_dur(((t.get("task_done") or now) - t["task_start"]).total_seconds()) if "task_start" in t else ""
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
             f"{fmt_dur(((end or now) - t0).total_seconds())}{'' if end else ' so far'}. Test runs: {sum(tests.values())}.</p>")
    closure = [(f"T{n}", fmt_dur((t["task_done"] - t["task_start"]).total_seconds()) if "task_done" in t else "running",
                str(tests.get(n, 0))) for n, t in sorted(times.items()) if "task_start" in t]
    if closure:
        h.append(_table(["Task", "Implementation time", "Test runs"], closure))
    if diff_ev:
        h.append(_table(["Diff", "Created", "Published", "Reviewed", "Landed"],
                        [(esc(d), v.get("created", ""), v.get("published", ""), v.get("reviewed", ""), v.get("landed", ""))
                         for d, v in diff_ev.items()]))

    gates = []
    for k, d in run["docs"].items():
        if not isinstance(d, dict) or not d.get("id") or d.get("kind") in ("plan", "explainer"):
            continue
        versions = sum(1 for e in events if e.get("doc") == k and e["kind"] in ("published", "humanize"))
        wait = sum((we - ws).total_seconds() for ws, we in waits.get(k, []))
        gates.append((_doc_link(d, k), str(versions or 1), esc(d.get("status", "").replace("_", " ")),
                      hhmm(d.get("opened_at")), hhmm(d.get("accepted_at")), fmt_dur(wait), _qcount(run_dir, d)))
    h.append("<h2>Gates</h2>" + _table(["Doc", "Version", "Status", "Opened", "Accepted", "Waiting on you", "Questions"], gates))

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
        ("Elapsed since request", fmt_dur((now - t0).total_seconds())),
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
