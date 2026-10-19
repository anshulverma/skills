#!/usr/bin/env python3
"""Review velocity: doc complexity, reading-time estimates and the owner's measured pace, across runs.

Usage:
  velocity.py metrics DOC.md QUESTIONS.json [--graded GRADED.json]   (prints METRICS JSON)
  velocity.py doc RUN DOC_KEY METRICS.json      (record a published/refreshed doc; prints its header line)
  velocity.py session RUN DOC_KEY               (record review sessions built from the doc's comment_ts events)
  velocity.py render OUT.html                   (velocity doc body)
  velocity.py publish                           (create the private velocity doc once, then re-render and apply it)
Data lives in $LOCKSTEP_VELOCITY_ROOT or /data/users/anshulverma/sdd-runs/_velocity.
"""
import fcntl
import html
import json
import math
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime

from state import atomic_write_json, iso, now_utc, parse_ts, read_events, read_json

EXPLAINER_THRESHOLD = 5.5  # 0-10 scale; a raw score of 20
SCALE = 25  # raw score that maps to 6.3; larger docs approach 10
DEFAULT_WPM = 200  # cold-start pace until the owner has measured sessions
SESSION_GAP_MIN = 10
TITLE = "Review velocity"
HUMANIZE = os.path.expanduser("~/.claude/skills/humanize/scripts")


def root() -> str:
    return os.environ.get("LOCKSTEP_VELOCITY_ROOT", "/data/users/anshulverma/sdd-runs/_velocity")


def raw_score(m: dict) -> float:
    return (m["words"] / 100 + 2 * m["figures"] + m["tables"] + 2 * m["open_questions"]
            + max(0, m["grade"] - 10) + m["unknown_terms"] + m["slop"] / 10)


def score(m: dict) -> float:
    return round(10 * (1 - math.exp(-raw_score(m) / SCALE)), 1)


def grade(text: str) -> float:
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return 0.0
    sentences = max(1, len([s for s in re.split(r"[.!?]+", text) if s.strip()]))
    syllables = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in words)
    return 0.39 * len(words) / sentences + 11.8 * syllables / len(words) - 15.59


def sessions(ts: list[datetime], gap_min: float = SESSION_GAP_MIN) -> list[tuple[datetime, datetime]]:
    out = []
    for t in sorted(ts):
        if out and (t - out[-1][1]).total_seconds() < gap_min * 60:
            out[-1] = (out[-1][0], t)
        else:
            out.append((t, t))
    return out


def lead_in(pairs: list[tuple[datetime, datetime]]) -> float:
    if not pairs:
        return 5
    return min(15, statistics.median((first - pub).total_seconds() / 60 for pub, first in pairs))


def active_minutes(sess: list[tuple[datetime, datetime]], lead_in_min: float) -> float:
    return sum((e - s).total_seconds() / 60 + lead_in_min for s, e in sess)


def pace_wpm(history: list[dict]) -> float:
    words = sum(h.get("words", 0) for h in history)
    minutes = sum(h.get("active_min", 0) for h in history)
    return words / minutes if words and minutes else DEFAULT_WPM


def estimate_minutes(words: int, wpm: float) -> int:
    return math.ceil(words / wpm)


def header_line(m: dict, wpm: float) -> str:
    return f"Complexity {score(m):.1f}/10 · about {estimate_minutes(m['words'], wpm)} min to read"


def _jsonl(name: str) -> list[dict]:
    path = os.path.join(root(), name)
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # torn last line
    return rows


def _append(name: str, row: dict) -> None:
    with open(os.path.join(root(), name), "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def metrics_for(md_path: str, questions_path: str, graded: str | None) -> dict:
    raw = re.sub(r"(?s)<!--.*?-->", "", open(md_path, encoding="utf-8").read())
    try:
        if HUMANIZE not in sys.path:
            sys.path.append(HUMANIZE)
        import slop_score
        raw = slop_score.strip_frontmatter(raw)
        m, _ = slop_score.metrics(raw)
        words, slop = int(m["words"]), round(slop_score.score(m, slop_score.WEIGHTS), 1)
    except Exception as e:  # humanize missing or changed: still measurable, slop unknown
        print(f"velocity: slop score unavailable ({type(e).__name__}: {e}); slop recorded as 0", file=sys.stderr)
        words, slop = len(re.findall(r"[A-Za-z0-9']+", raw)), 0
    unknown = 0
    if graded:
        g = read_json(graded)
        terms = g.get("unknown_terms", g.get("unfamiliar_terms", []))
        unknown = terms if isinstance(terms, int) else len(terms or [])
    raw = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", raw)  # code is not read like prose
    prose = re.sub(r"(?m)^\s*\|.*\|\s*$|!\[[^\]]*\]\([^)]*\)|^#+ .*$|`[^`]*`", " ", raw)
    return {"words": words, "slop": slop,
            "figures": len(re.findall(r"!\[[^\]]*\]\([^)]*\)", raw)),
            "tables": len(re.findall(r"(?m)^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", raw)),
            "open_questions": len(read_json(questions_path)), "grade": round(grade(prose), 1),
            "unknown_terms": unknown}


def record_session(run_dir: str, doc_key: str) -> list[dict]:
    """Rebuild this doc's sessions since its latest publish and replace their rows (repeat calls stay correct)."""
    run = os.path.basename(os.path.abspath(run_dir))
    events = [e for e in read_events(run_dir) if e.get("doc") == doc_key]
    pubs = [parse_ts(e["ts"]) for e in events if e["kind"] == "published"]
    if not pubs:
        return []
    pub = max(pubs)
    comments = [parse_ts(e["comment_ts"]) for e in events if e.get("comment_ts") and parse_ts(e["comment_ts"]) >= pub]
    sess = sessions(comments)
    leadins = [r for r in _jsonl("leadins.jsonl") if not (r.get("run") == run and r.get("doc") == doc_key
                                                          and r.get("published") == iso(pub))]
    if sess:
        leadins.append({"run": run, "doc": doc_key, "published": iso(pub), "first_comment": iso(sess[0][0])})
    _rewrite("leadins.jsonl", leadins)
    li = lead_in([(parse_ts(r["published"]), parse_ts(r["first_comment"])) for r in leadins])
    words = next((d["metrics"]["words"] for d in reversed(_jsonl("docs.jsonl"))
                  if d["run"] == run and d["doc"] == doc_key), 0)
    new = [{"run": run, "doc": doc_key, "published": iso(pub), "start": iso(s), "end": iso(e),
            "active_min": active_minutes([(s, e)], li), "words": words if i == 0 else 0}
           for i, (s, e) in enumerate(sess)]
    keep = [r for r in _jsonl("sessions.jsonl")
            if not (r.get("run") == run and r.get("doc") == doc_key and r.get("published", iso(pub)) == iso(pub))]
    _rewrite("sessions.jsonl", keep + new)
    return new


def _rewrite(name: str, rows: list[dict]) -> None:
    path = os.path.join(root(), name)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    os.replace(tmp, path)


def render_body(figdir: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    docs, sess = _jsonl("docs.jsonl"), _jsonl("sessions.jsonl")
    wpm = pace_wpm(sess)
    os.makedirs(figdir, exist_ok=True)
    actual = {}
    for s in sess:
        actual[(s["run"], s["doc"])] = actual.get((s["run"], s["doc"]), 0) + s["active_min"]
    latest = {}
    for d in docs:
        latest[(d["run"], d["doc"])] = d
    pts = [(score(d["metrics"]), d["metrics"]["words"] / actual[k]) for k, d in latest.items() if actual.get(k)]
    est = [(estimate_minutes(d["metrics"]["words"], wpm), actual[k]) for k, d in latest.items() if actual.get(k)]
    for name, data, xl, yl in (("pace.png", pts, "complexity score", "words per active minute"),
                               ("estimate.png", est, "estimated minutes", "actual active minutes")):
        fig, ax = plt.subplots(figsize=(6, 3.2), facecolor="#fcfcfb")
        if data:
            ax.scatter(*zip(*data), color="#2a78d6")
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.grid(color="#e5e4e0")
        plt.tight_layout()
        plt.savefig(os.path.join(figdir, name), dpi=150, facecolor="#fcfcfb")
        plt.close(fig)
    h = [f'<p data-style="TITLE">{TITLE}</p>',
         "<p>Steer a run from that run's own docs; comments here are not read.</p>",
         f"<p>Measured pace: {wpm:.0f} words per active minute over {len(sess)} sessions.</p>",
         f'<p style="text-align:center"><img src="file://{figdir}/pace.png" alt="pace vs complexity"></p>',
         '<p style="text-align:center"><i>Figure 1. Reading pace against doc complexity.</i></p><p></p>',
         f'<p style="text-align:center"><img src="file://{figdir}/estimate.png" alt="estimate vs actual"></p>',
         '<p style="text-align:center"><i>Figure 2. Estimated against actual active reading time.</i></p><p></p>',
         "<h2>Docs</h2><table><tr><th>Run</th><th>Doc</th><th>Complexity</th><th>Words</th><th>Estimate</th>"
         "<th>Actual</th></tr>"]
    for (run, doc), d in latest.items():
        m = d["metrics"]
        h.append(f"<tr><td>{html.escape(run)}</td><td>{html.escape(doc)}</td><td>{score(m):.1f}</td><td>{m['words']}</td>"
                 f"<td>{estimate_minutes(m['words'], wpm)} min</td><td>{actual.get((run, doc), 0):.0f} min</td></tr>")
    h.append("</table><p></p><h2>Sessions</h2><table><tr><th>Run</th><th>Doc</th><th>Start (UTC)</th>"
             "<th>Active minutes</th></tr>")
    for s in sess:
        h.append(f"<tr><td>{html.escape(s['run'])}</td><td>{html.escape(s['doc'])}</td>"
                 f"<td>{s['start'][:16].replace('T', ' ')}</td><td>{s['active_min']:.0f}</td></tr>")
    return "\n".join(h) + "</table><p></p>\n"


def _meta(*args: str) -> str:
    p = subprocess.run(["meta", *args], capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"meta {args[0]} failed: {(p.stdout + p.stderr).strip()[:200]}")
    return p.stdout


def _json_in(out: str):
    try:
        return json.loads(out)
    except ValueError:
        pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(out):
        if ch in "[{":
            try:
                return dec.raw_decode(out[i:])[0]
            except ValueError:
                continue
    raise ValueError(f"no JSON in meta output: {out.strip()[:200]!r}")


def publish() -> str:
    path = os.path.join(root(), "doc.json")
    if os.path.exists(path):
        doc_id = read_json(path)["id"]
    else:
        doc_id = _json_in(_meta("google.docs", "create", f"--title={TITLE}", "--output=json"))["id"]
        atomic_write_json(path, {"id": doc_id, "title": TITLE})  # recorded before the check, so retries reuse it
    perms = _json_in(_meta("google.docs.share", "list", f"--id={doc_id}", "--output=json"))
    private = isinstance(perms, list) and perms and all(isinstance(p, dict) and p.get("role") == "owner" for p in perms)
    if not private:  # fails closed on any shape it does not recognise
        raise PermissionError(f"velocity doc {doc_id} is not private; not writing to it")
    body = os.path.join(root(), "body.html")
    open(body, "w").write(render_body(os.path.join(root(), "fig")))
    _meta("google.docs", "apply", f"--id={doc_id}", f"--from=file://{body}", "--conflict-resolution=ours")
    return doc_id


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "metrics" and (len(rest) == 2 or (len(rest) == 4 and rest[2] == "--graded")):
        graded = rest[3] if len(rest) == 4 else None
        print(json.dumps(metrics_for(rest[0], rest[1], graded)))
        return 0
    if cmd not in ("doc", "session", "render", "publish"):
        print(__doc__, file=sys.stderr)
        return 2
    os.makedirs(root(), exist_ok=True)
    with open(os.path.join(root(), ".lock"), "a") as lock:  # one lock per command, around its whole body
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if cmd == "doc" and len(rest) == 3:
                m = read_json(rest[2])
                run = os.path.basename(os.path.abspath(rest[0]))
                _append("docs.jsonl", {"run": run, "doc": rest[1], "at": iso(now_utc()), "metrics": m})
                print(header_line(m, pace_wpm(_jsonl("sessions.jsonl"))))
                print(f"explainer: {'on' if score(m) >= EXPLAINER_THRESHOLD else 'off'}")
            elif cmd == "session" and len(rest) == 2:
                print(json.dumps(record_session(rest[0], rest[1])))
            elif cmd == "render" and len(rest) == 1:
                open(rest[0], "w").write(render_body(os.path.join(root(), "fig")))
            elif cmd == "publish" and not rest:
                print(publish())
            else:
                print(__doc__, file=sys.stderr)
                return 2
        except (RuntimeError, PermissionError, ValueError, OSError, KeyError, TypeError, AttributeError, ImportError,
                subprocess.TimeoutExpired) as e:
            print(e, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
