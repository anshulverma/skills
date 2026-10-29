#!/usr/bin/env python3
"""Experiment and study tracker for a lockstep run: one state file, <run>/experiments/state.json.

Usage:
  experiments.py job record RUN --name N --kind K --hypothesis H [--study ID] [--url U] [--eta ISO]
  experiments.py job set RUN NAME k=v ...       (verdict -> job_verdict; terminal state -> job_done;
                                                 stopped_done=1 turns failed into stopped)
  experiments.py job poll RUN                   (MAST backend)
  experiments.py job missing RUN                (terminal rows lacking a readout or verdict)
  experiments.py study new RUN ID --title T --question Q [--requested-by owner|plan|self] [--thread ID]
  experiments.py study conclude RUN ID --verdict V --short S --learning L [--learning L ...]   (2-5 learnings)
  experiments.py study reopen RUN ID
  experiments.py study set RUN ID k=v ...       (learnings_tab, questions, followups)
  experiments.py study check RUN
  experiments.py set RUN k=v ...                (learnings, bottom_line, primary_metric, sweep_stopped, archive)
  experiments.py summary RUN
Read commands exit 0 silently when the state file is missing; record and new create it. Exit 2 = refused.
"""
import argparse
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from state import append_event, atomic_write_json, iso, load, now_utc, read_json

TERMINAL = frozenset({"done", "failed", "void", "stopped"})
ROW_STATES = TERMINAL | {"queued", "starting", "running"}
# FAILED may be restarted by MAST; DEAD is final. UNKNOWN is what _status_from returns for JOB_NOT_FOUND.
MAST_TO_ROW = {"PENDING": "queued", "RUNNING": "running", "SHUTTING_DOWN": "running", "COMPLETE": "done",
               "FAILED": "queued", "DEAD": "failed", "UNKNOWN": "void"}
MAST_URL = "https://www.internalfb.com/mlhub/pipelines/runs/mast/"  # job links in the tabs default to this
MAST_STATE_ENUM = {0: "PENDING", 1: "RUNNING", 2: "COMPLETE", 3: "FAILED", 4: "DEAD"}  # HpcJobState
STARTUP_S = 1200
VERDICTS = ("confirmed", "negative", "inconclusive", "default-stays")
JOB_KEYS = ("url", "kind", "study", "hypothesis", "launched_utc", "eta_utc", "state", "started_utc", "ended_utc",
            "attempts", "gpus", "cost_gpu_h", "readout", "verdict", "stopped_done", "void_reason")
JSON_KEYS = frozenset({"attempts", "gpus", "cost_gpu_h", "stopped_done", "questions", "followups", "learnings",
                       "archive"})
STUDY_SET_KEYS = ("learnings_tab", "questions", "followups")
TOP_SET_KEYS = ("learnings", "bottom_line", "primary_metric", "sweep_stopped", "archive")
STUDY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class Refused(Exception):
    pass


# --- MAST backend, lifted from the ShopEV run's sweep/sweep.py ---

def _parse_utc(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _status_from(st: dict | None, hist: dict | None, jdef: dict | None, now: datetime) -> dict:
    if st is None:
        return {"state": "UNKNOWN", "attempts": 0, "start_utc": None, "end_utc": None, "revision": None,
                "hosts": None, "gpus": None, "fail_cause": "", "wall_s": 0.0}
    st = {**st, "state": MAST_STATE_ENUM.get(st["state"], st["state"])}  # JSON gives some states as enum ints
    attempts = hist["jobExecutionHistory"]["jobExecutionAttempts"]
    wall, starts, ends = 0.0, [], []
    for a in attempts:
        t = a["jobStateTransitionTimestampSecs"]
        if "RUNNING" in t:
            end = max((v for k, v in t.items() if k in ("COMPLETE", "FAILED", "DEAD")), default=now.timestamp())
            wall += end - t["RUNNING"]
            starts.append(t["RUNNING"])
            ends.append(end)
    groups = jdef["hpcTaskGroups"]
    return {"state": st["state"], "attempts": len(attempts),
            "start_utc": _iso(min(starts)) if starts else None,
            "end_utc": _iso(max(ends)) if ends and st["state"] in ("COMPLETE", "FAILED", "DEAD") else None,
            "revision": jdef["applicationMetadata"].get("hg_commit_hash"),
            "hosts": sum(-(-g["taskCount"] // g.get("taskCountPerHost", 1)) for g in groups),
            "gpus": sum(g["taskCount"] * g["spec"]["resourceLimit"]["compute"].get("gpu", 0) for g in groups),
            "fail_cause": st.get("latestAttempt", {}).get("failureType") or "", "wall_s": float(wall)}


class CliMast:
    def _json(self, *args: str) -> dict:
        out = subprocess.run(["mast", "--output", "json", *args], capture_output=True, text=True, timeout=300, check=True)
        return json.loads(out.stdout)

    def status(self, name: str) -> dict:
        now = datetime.now(timezone.utc)
        st = self._json("get-status", name)
        if st["status"] != "ok":
            if "JOB_NOT_FOUND" in st["error"]["message"]:
                return _status_from(None, None, None, now)
            raise RuntimeError(st["error"]["message"])
        return _status_from(st["data"], self._json("get-job-history", name)["data"],
                            self._json("get-job-definition", name)["data"], now)


def gpu_hours(row: dict, status: dict) -> float:
    return (row.get("gpus") or status["gpus"] or 0) * status["wall_s"] / 3600


def poll_updates(jobs: list[dict], mast, now: datetime) -> dict[str, dict]:
    """Row updates per job name for every non-terminal row. Runs without the state lock (MAST calls are slow)."""
    out = {}
    for row in jobs:
        if row["state"] in TERMINAL:
            continue
        s = mast.status(row["name"])
        if s["state"] not in MAST_TO_ROW:
            raise RuntimeError(f"{row['name']}: unknown MAST state {s['state']!r}")
        new = MAST_TO_ROW[s["state"]]
        if new == "void":
            out[row["name"]] = {"state": "void", "void_reason": "JOB_NOT_FOUND in MAST"}
            continue
        # ponytail: wall-clock proxy for "before step 0"; read the first step log line if 20 min misleads
        if new == "running" and s["start_utc"] and (now - _parse_utc(s["start_utc"])).total_seconds() < STARTUP_S:
            new = "starting"
        u = {"state": new, "attempts": s["attempts"], "cost_gpu_h": gpu_hours(row, s)}
        if row.get("gpus") is None and s["gpus"]:
            u["gpus"] = s["gpus"]
        if s["start_utc"]:
            u["started_utc"] = s["start_utc"]
        if s["end_utc"] and new in TERMINAL:
            u["ended_utc"] = s["end_utc"]
        out[row["name"]] = u
    return out


# --- state file ---

def _path(run: str) -> str:
    return os.path.join(run, "experiments", "state.json")


def _empty() -> dict:
    return {"jobs": [], "studies": {}, "learnings": [], "bottom_line": "", "primary_metric": "", "archive": [],
            "sweep_stopped": None}


def _read(run: str) -> dict | None:
    return read_json(_path(run)) if os.path.exists(_path(run)) else None


@contextlib.contextmanager
def _locked(run: str, create: bool = False):
    """Yields (state, events); writes the state atomically and appends the events only if the body succeeds."""
    path = _path(run)
    if not create and not os.path.exists(path):
        raise Refused(f"no {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        st = read_json(path) if os.path.exists(path) else _empty()
        events: list[tuple[str, str, dict]] = []
        yield st, events
        atomic_write_json(path, st)
        for kind, text, fields in events:
            append_event(run, kind, text, **fields)


def _kv(items: list[str], allowed: tuple[str, ...]) -> dict:
    out = {}
    for item in items:
        k, sep, v = item.partition("=")
        if not sep or k not in allowed:
            raise Refused(f"bad key=value {item!r}; allowed keys: {', '.join(allowed)}")
        if k in JSON_KEYS:
            try:
                v = json.loads(v)
            except ValueError:
                raise Refused(f"{k} needs a JSON value, got {v!r}")
        out[k] = v
    return out


def _job(st: dict, name: str) -> dict:
    for row in st["jobs"]:
        if row["name"] == name:
            return row
    raise Refused(f"no job {name!r}")


def _study(st: dict, sid: str) -> dict:
    if sid not in st["studies"]:
        raise Refused(f"no study {sid!r}")
    return st["studies"][sid]


def _settle(row: dict, old_state: str, old_verdict: str, events: list) -> None:
    if row["state"] not in ROW_STATES:
        raise Refused(f"bad state {row['state']!r}; one of {', '.join(sorted(ROW_STATES))}")
    if row.get("stopped_done") and row["state"] == "failed":
        row["state"] = "stopped"  # stopped on purpose: not failed, GPU-h not wasted
    f = {"n": row["n"], "name": row["name"], "study": row["study"]}
    if row["verdict"] and row["verdict"] != old_verdict:
        events.append(("job_verdict", f"job {row['n']} {row['name']}: {row['verdict']}", f))
    if row["state"] in TERMINAL and old_state not in TERMINAL:
        events.append(("job_done", f"job {row['n']} {row['name']} {row['state']}", {**f, "state": row["state"]}))


def _needs(row: dict) -> list[str]:
    """Every finished job needs a readout; every terminal job needs a verdict."""
    if row["state"] not in TERMINAL:
        return []
    return (["readout"] if row["state"] == "done" and not row["readout"] else []) + ([] if row["verdict"] else ["verdict"])


def _study_jobs(st: dict, sid: str) -> list[dict]:
    return [j for j in st["jobs"] if j["study"] == sid]


def _unsettled(jobs: list[dict]) -> list[str]:
    return [j["name"] for j in jobs if j["state"] not in TERMINAL or not j["verdict"]]


def _local(run: str) -> str:
    try:
        tz = load(run).get("owner_tz")
    except (OSError, ValueError):
        tz = None
    return now_utc().astimezone(ZoneInfo(tz or "America/Los_Angeles")).strftime("%Y-%m-%d %H:%M %Z")


REPORT_A = """# Study {id}: {title}

Status: running, opened {opened}

## Question

{question}

## What exists already

## Design

| Arm | Change vs baseline | Expected |
|---|---|---|

Decision rule:

## Cost

## Risks

## Smoke gate

## Jobs

| Job | Role | Launched (PT) | Verdict |
|---|---|---|---|

## Results

**Verdict: pending.**

## Follow-ups

## Proposed questions

Each with a default.

## Log

- {opened}: opened, requested by {requested_by}{thread}
"""


# --- commands ---

def job_record(run: str, a) -> None:
    with _locked(run, create=True) as (st, events):
        if a.study:
            _study(st, a.study)
        given = {"kind": a.kind, "hypothesis": a.hypothesis, "study": a.study, "url": a.url, "eta_utc": a.eta}
        given = {k: v for k, v in given.items() if v is not None}
        row = next((j for j in st["jobs"] if j["name"] == a.name), None)
        if row:
            row.update(given)
            print(row["n"])
            return
        n = max([j["n"] for j in st["jobs"]] + [x.get("through_n", 0) for x in st["archive"]] + [0]) + 1
        st["jobs"].append({"n": n, "name": a.name, "url": MAST_URL + a.name, "kind": "", "study": "", "hypothesis": "",
                           "launched_utc": iso(now_utc()), "eta_utc": "", "state": "queued", "started_utc": "",
                           "ended_utc": "", "attempts": 0, "gpus": None, "cost_gpu_h": 0.0, "readout": "",
                           "verdict": "", "stopped_done": 0, "void_reason": "", **given})
        events.append(("job_launch", f"job {n} {a.name} launched", {"n": n, "name": a.name, "study": a.study or ""}))
        print(n)


def job_set(run: str, name: str, items: list[str]) -> None:
    kv = _kv(items, JOB_KEYS)
    with _locked(run) as (st, events):
        row = _job(st, name)
        old_state, old_verdict = row["state"], row["verdict"]
        row.update(kv)
        _settle(row, old_state, old_verdict, events)


def job_poll(run: str, mast=None, now: datetime | None = None) -> None:
    st = _read(run)
    if st is None:
        return
    updates = poll_updates(st["jobs"], mast or CliMast(), now or datetime.now(timezone.utc))
    with _locked(run) as (st, events):
        for row in st["jobs"]:
            u = updates.get(row["name"])
            if u is None or row["state"] in TERMINAL:  # set terminal by hand while MAST was polled
                continue
            old_state = row["state"]
            row.update(u)
            _settle(row, old_state, row["verdict"], events)


def study_new(run: str, a) -> None:
    if not STUDY_ID.fullmatch(a.id):
        raise Refused(f"bad study id {a.id!r}")
    with _locked(run, create=True) as (st, events):
        if a.id not in st["studies"]:
            st["studies"][a.id] = {"title": a.title, "question": a.question, "requested_by": a.requested_by,
                                   "source_thread": a.thread or "", "status": "running", "verdict": "",
                                   "short_answer": "", "learnings": [], "learnings_tab": "",
                                   "opened_utc": iso(now_utc()), "concluded_utc": "", "questions": [],
                                   "followups": []}
            events.append(("study_start", f"study {a.id} started: {a.title}", {"study": a.id}))
        report = os.path.join(run, "studies", a.id, "report.md")
        if not os.path.exists(report):
            os.makedirs(os.path.dirname(report), exist_ok=True)
            with open(report, "w") as f:
                f.write(REPORT_A.format(id=a.id, title=a.title, question=a.question, opened=_local(run),
                                        requested_by=a.requested_by,
                                        thread=f" (thread {a.thread})" if a.thread else ""))
        print(report)


def study_conclude(run: str, a) -> None:
    if not 2 <= len(a.learning) <= 5:
        raise Refused(f"need 2 to 5 learnings, got {len(a.learning)}")
    with _locked(run) as (st, events):
        s = _study(st, a.id)
        if s["status"] == "concluded":
            raise Refused(f"study {a.id} is already concluded")
        bad = _unsettled(_study_jobs(st, a.id))
        if bad:
            raise Refused(f"study {a.id} has jobs not terminal or without a verdict: {', '.join(bad)}")
        report = os.path.join(run, "studies", a.id, "report.md")
        if os.path.exists(report) and "**Verdict: pending.**" in open(report).read():
            raise Refused(f"write the Results section of {report} (bold verdict first) before concluding")
        s.update(status="concluded", verdict=a.verdict, short_answer=a.short, learnings=a.learning,
                 concluded_utc=iso(now_utc()))
        events.append(("study_done", f"study {a.id} concluded: {a.verdict}. {a.short}",
                       {"study": a.id, "verdict": a.verdict}))
        events.extend(("learning", text, {"study": a.id}) for text in a.learning)


def study_reopen(run: str, sid: str) -> None:
    with _locked(run) as (st, events):
        s = _study(st, sid)
        if s["status"] != "concluded":
            raise Refused(f"study {sid} is {s['status']}, not concluded")
        s.update(status="reopened", concluded_utc="")
        events.append(("study_reopen", f"study {sid} reopened", {"study": sid}))


def study_set(run: str, sid: str, items: list[str]) -> None:
    kv = _kv(items, STUDY_SET_KEYS)
    for k in ("questions", "followups"):
        if k in kv and not isinstance(kv[k], list):
            raise Refused(f"{k} needs a JSON list")
    with _locked(run) as (st, _):
        _study(st, sid).update(kv)


def study_check(run: str) -> None:
    st = _read(run)
    if st is None:
        return
    studies = st["studies"]
    # A reading-only study (no jobs) is never auto-ready: the agent concludes it when the reading is done.
    ready = [i for i, s in studies.items() if s["status"] != "concluded" and _study_jobs(st, i)
             and not _unsettled(_study_jobs(st, i))]
    print(json.dumps({"ready": ready,
                      "no_learnings_tab": [i for i, s in studies.items()
                                           if s["status"] == "concluded" and not s["learnings_tab"]],
                      "poll": [i for i in studies if os.path.isfile(os.path.join(run, "studies", i, "poll"))]}))


def top_set(run: str, items: list[str]) -> None:
    kv = _kv(items, TOP_SET_KEYS)
    if "learnings" in kv:
        ls = kv["learnings"]
        if not (isinstance(ls, list) and len(ls) <= 5 and all(isinstance(x, str) for x in ls)):
            raise Refused("learnings needs a JSON list of at most 5 strings")
    if "archive" in kv and not (isinstance(kv["archive"], dict) and {"paste", "through_n"} <= kv["archive"].keys()):
        raise Refused('archive needs JSON {"paste": ..., "through_n": N}')
    with _locked(run) as (st, _):
        if "archive" in kv:
            st["archive"].append(kv.pop("archive"))
        if kv.get("sweep_stopped") == "":
            kv["sweep_stopped"] = None
        st.update(kv)


def job_missing(run: str) -> None:
    st = _read(run)
    if st is None:
        return
    print(json.dumps([{"n": j["n"], "name": j["name"], "state": j["state"], "study": j["study"], "missing": m}
                      for j in st["jobs"] if (m := _needs(j))]))


def summary(run: str) -> None:
    st = _read(run)
    if st is None:
        return
    jobs = st["jobs"]
    print(json.dumps({"jobs": len(jobs), "by_state": dict(Counter(j["state"] for j in jobs)),
                      "gpu_h": round(sum(j["cost_gpu_h"] or 0 for j in jobs), 2),
                      "etas": [{"n": j["n"], "name": j["name"], "eta_utc": j["eta_utc"]}
                               for j in jobs if j["state"] not in TERMINAL and j["eta_utc"]],
                      "studies": dict(Counter(s["status"] for s in st["studies"].values()))}))


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    job = sub.add_parser("job").add_subparsers(dest="op", required=True)
    p = job.add_parser("record")
    p.add_argument("run")
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--study")
    p.add_argument("--url")
    p.add_argument("--eta")
    p = job.add_parser("set")
    p.add_argument("run")
    p.add_argument("name")
    p.add_argument("kv", nargs="+")
    for op in ("poll", "missing"):
        job.add_parser(op).add_argument("run")
    study = sub.add_parser("study").add_subparsers(dest="op", required=True)
    p = study.add_parser("new")
    p.add_argument("run")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--requested-by", choices=("owner", "plan", "self"), default="self")
    p.add_argument("--thread")
    p = study.add_parser("conclude")
    p.add_argument("run")
    p.add_argument("id")
    p.add_argument("--verdict", required=True, choices=VERDICTS)
    p.add_argument("--short", required=True)
    p.add_argument("--learning", action="append", default=[])
    p = study.add_parser("reopen")
    p.add_argument("run")
    p.add_argument("id")
    p = study.add_parser("set")
    p.add_argument("run")
    p.add_argument("id")
    p.add_argument("kv", nargs="+")
    study.add_parser("check").add_argument("run")
    p = sub.add_parser("set")
    p.add_argument("run")
    p.add_argument("kv", nargs="+")
    sub.add_parser("summary").add_argument("run")
    return ap


def main(argv: list[str]) -> int:
    a = _parser().parse_args(argv)
    cmd = (a.cmd, getattr(a, "op", None))
    try:
        {("job", "record"): lambda: job_record(a.run, a),
         ("job", "set"): lambda: job_set(a.run, a.name, a.kv),
         ("job", "poll"): lambda: job_poll(a.run),
         ("job", "missing"): lambda: job_missing(a.run),
         ("study", "new"): lambda: study_new(a.run, a),
         ("study", "conclude"): lambda: study_conclude(a.run, a),
         ("study", "reopen"): lambda: study_reopen(a.run, a.id),
         ("study", "set"): lambda: study_set(a.run, a.id, a.kv),
         ("study", "check"): lambda: study_check(a.run),
         ("set", None): lambda: top_set(a.run, a.kv),
         ("summary", None): lambda: summary(a.run)}[cmd]()
    except Refused as e:
        print(e, file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"{' '.join(e.cmd)} failed: {e.stderr}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
