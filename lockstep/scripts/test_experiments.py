#!/usr/bin/env python3
"""Checks for experiments.py. Run: ~/.cache/humanize-venv/bin/python test_experiments.py (or pytest)"""

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import state  # noqa: E402

FAKE_MAST = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
assert args[:2] == ["--output", "json"], args
cmd, name = args[2], args[3]
job = json.load(open(os.path.join(os.environ["FAKE_MAST_DIR"], name + ".json")))
if cmd == "get-status":
    out = job["status"]
else:
    out = {"status": "ok", "data": job["history" if cmd == "get-job-history" else "definition"]}
print(json.dumps(out))
"""


def new_run() -> str:
    d = tempfile.mkdtemp()
    state.atomic_write_json(os.path.join(d, "pipeline.json"), {"phase": "BUILD", "owner_tz": "America/Los_Angeles"})
    return d


def cli(run_dir: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    argv = [sys.executable, os.path.join(HERE, "experiments.py"), *args[:2], run_dir, *args[2:]] if args[0] in (
        "job", "study") else [sys.executable, os.path.join(HERE, "experiments.py"), args[0], run_dir, *args[1:]]
    return subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)


def ok(run_dir: str, *args: str, env: dict | None = None) -> str:
    r = cli(run_dir, *args, env=env)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout


def exp(run_dir: str) -> dict:
    return state.read_json(os.path.join(run_dir, "experiments", "state.json"))


def events(run_dir: str) -> list[dict]:
    return state.read_events(run_dir) if os.path.exists(os.path.join(run_dir, "events.jsonl")) else []


def record(run_dir: str, name: str, *extra: str) -> str:
    return ok(run_dir, "job", "record", "--name", name, "--kind", "train", "--hypothesis", "h", *extra).strip()


def test_missing_state_file_is_silent():
    d = new_run()
    for args in (("job", "poll"), ("job", "missing"), ("study", "check"), ("summary",)):
        r = cli(d, *args)
        assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), args
    assert not os.path.exists(os.path.join(d, "experiments"))


def test_record_assigns_upserts_never_reuses():
    d = new_run()
    assert record(d, "a") == "1"
    assert record(d, "b", "--url", "u") == "2"
    assert record(d, "a", "--eta", "2026-10-29T20:00:00Z") == "1"  # upsert keeps n
    st = exp(d)
    assert [(j["n"], j["name"], j["state"]) for j in st["jobs"]] == [(1, "a", "queued"), (2, "b", "queued")]
    assert st["jobs"][0]["eta_utc"] == "2026-10-29T20:00:00Z" and st["jobs"][1]["url"] == "u"
    assert [e["n"] for e in events(d) if e["kind"] == "job_launch"] == [1, 2]
    ok(d, "set", 'archive={"paste": "P1", "through_n": 7}')
    assert record(d, "c") == "8"  # numbers covered by an archive are never reused
    assert cli(d, "job", "record", "--name", "x", "--kind", "k", "--hypothesis", "h", "--study", "nope").returncode == 2


def _attempt(running: float, end_state: str | None = None, end: float | None = None) -> dict:
    t = {"PENDING": running - 60, "RUNNING": running}
    if end_state:
        t[end_state] = end
    return {"jobStateTransitionTimestampSecs": t}


def _job(state_val, attempts: list[dict]) -> dict:
    return {"status": {"status": "ok", "data": {"state": state_val}},
            "history": {"jobExecutionHistory": {"jobExecutionAttempts": attempts}},
            "definition": {"hpcTaskGroups": [{"taskCount": 2, "spec": {"resourceLimit": {"compute": {"gpu": 8}}}}],
                           "applicationMetadata": {}}}


def _fake_mast(d: str, jobs: dict) -> dict:
    bindir = os.path.join(d, "bin")
    os.makedirs(bindir)
    with open(os.path.join(bindir, "mast"), "w") as f:
        f.write(FAKE_MAST)
    os.chmod(os.path.join(bindir, "mast"), 0o755)
    for name, job in jobs.items():
        with open(os.path.join(bindir, name + ".json"), "w") as f:
            json.dump(job, f)
    return {**os.environ, "PATH": bindir + ":" + os.environ["PATH"], "FAKE_MAST_DIR": bindir}


def test_poll_state_map():
    d = new_run()
    now = time.time()
    jobs = {
        "pend": _job(0, []),                                                    # enum int PENDING
        "old": _job("RUNNING", [_attempt(now - 7200)]),
        "fresh": _job(1, [_attempt(now - 300)]),                                # first RUNNING 5 min ago
        "done": _job(2, [_attempt(now - 7200, "COMPLETE", now - 3600)]),        # 1 h x 16 GPUs
        "retry": _job("FAILED", [_attempt(now - 7200, "FAILED", now - 3600)]),  # MAST may restart
        "dead": _job(4, [_attempt(now - 7200, "DEAD", now - 5400)]),
        "killed": _job("DEAD", [_attempt(now - 7200, "DEAD", now - 3600)]),
        "gone": {"status": {"status": "error", "error": {"message": "JOB_NOT_FOUND: gone"}}},
    }
    env = _fake_mast(d, jobs)
    for name in jobs:
        record(d, name)
    ok(d, "job", "set", "killed", "stopped_done=1")
    ok(d, "job", "poll", env=env)
    rows = {j["name"]: j for j in exp(d)["jobs"]}
    assert {n: r["state"] for n, r in rows.items()} == {
        "pend": "queued", "old": "running", "fresh": "starting", "done": "done", "retry": "queued",
        "dead": "failed", "killed": "stopped", "gone": "void"}
    assert rows["gone"]["void_reason"] and rows["done"]["gpus"] == 16 and rows["done"]["attempts"] == 1
    assert abs(rows["done"]["cost_gpu_h"] - 16.0) < 0.01 and abs(rows["dead"]["cost_gpu_h"] - 8.0) < 0.01
    assert rows["done"]["ended_utc"] and not rows["retry"]["ended_utc"]
    done = sorted(e["name"] for e in events(d) if e["kind"] == "job_done")
    assert done == ["dead", "done", "gone", "killed"]
    ok(d, "job", "poll", env=env)  # terminal rows are not re-polled or re-announced
    assert len([e for e in events(d) if e["kind"] == "job_done"]) == 4


def test_poll_unknown_state_fails_loud_and_writes_nothing():
    d = new_run()
    env = _fake_mast(d, {"a": _job(9, [])})
    record(d, "a")
    before = exp(d)
    r = cli(d, "job", "poll", env=env)
    assert r.returncode != 0 and "unknown MAST state 9" in r.stderr
    assert exp(d) == before


def test_job_set_events_and_missing():
    d = new_run()
    for name in ("fin", "fin2", "bad", "run"):
        record(d, name)
    ok(d, "job", "set", "fin", "state=done", "readout=AUC +0.002")
    ok(d, "job", "set", "fin2", "state=done", "verdict=win")
    ok(d, "job", "set", "bad", "state=failed")
    missing = {m["name"]: m["missing"] for m in json.loads(ok(d, "job", "missing"))}
    assert missing == {"fin": ["verdict"], "fin2": ["readout"], "bad": ["verdict"]}
    ok(d, "job", "set", "bad", "stopped_done=1", "verdict=stopped on purpose")
    assert exp(d)["jobs"][2]["state"] == "stopped"
    kinds = [(e["kind"], e["name"]) for e in events(d) if e["kind"] in ("job_done", "job_verdict")]
    assert kinds == [("job_done", "fin"), ("job_verdict", "fin2"), ("job_done", "fin2"), ("job_done", "bad"),
                     ("job_verdict", "bad")]
    assert cli(d, "job", "set", "run", "state=bogus").returncode == 2
    assert cli(d, "job", "set", "run", "n=5").returncode == 2
    assert cli(d, "job", "set", "nope", "verdict=x").returncode == 2


def test_study_new_conclude_reopen():
    d = new_run()
    out = ok(d, "study", "new", "A", "--title", "Staleness", "--question", "Does staleness hurt?",
             "--requested-by", "owner", "--thread", "AAA").strip()
    report = open(out).read()
    assert out == os.path.join(d, "studies", "A", "report.md")
    for section in ("## Question", "## What exists already", "## Design", "## Cost", "## Risks", "## Smoke gate",
                    "## Jobs", "## Results", "## Follow-ups", "## Proposed questions", "## Log"):
        assert section in report, section
    assert "Does staleness hurt?" in report and "thread AAA" in report
    open(out, "a").write("edited\n")
    ok(d, "study", "new", "A", "--title", "Staleness", "--question", "q")  # existing report is kept
    assert open(out).read().endswith("edited\n")
    assert cli(d, "study", "new", "../x", "--title", "t", "--question", "q").returncode == 2

    record(d, "j1", "--study", "A")
    record(d, "j2", "--study", "A")
    conclude = ("study", "conclude", "A", "--verdict", "negative", "--short", "No.")
    two = ("--learning", "L1", "--learning", "L2")
    assert cli(d, *conclude, *two).returncode == 2  # jobs not terminal
    assert json.loads(ok(d, "study", "check"))["ready"] == []
    ok(d, "job", "set", "j1", "state=done", "verdict=flat")
    ok(d, "job", "set", "j2", "state=failed")
    assert cli(d, *conclude, *two).returncode == 2  # j2 has no verdict
    ok(d, "job", "set", "j2", "verdict=crash")
    assert cli(d, *conclude, "--learning", "L1").returncode == 2
    assert cli(d, *conclude, *[x for i in range(6) for x in ("--learning", f"L{i}")]).returncode == 2
    check = json.loads(ok(d, "study", "check"))
    assert check["ready"] == ["A"] and check["no_learnings_tab"] == []
    ok(d, *conclude, *two)
    s = exp(d)["studies"]["A"]
    assert (s["status"], s["verdict"], s["short_answer"], s["learnings"]) == ("concluded", "negative", "No.", ["L1", "L2"])
    assert json.loads(ok(d, "study", "check")) == {"ready": [], "no_learnings_tab": ["A"], "poll": []}
    ok(d, "study", "set", "A", "learnings_tab=study-A", 'questions=["I3"]')
    assert exp(d)["studies"]["A"]["questions"] == ["I3"]
    assert cli(d, "study", "set", "A", "questions=I3").returncode == 2
    ok(d, "study", "reopen", "A")
    assert exp(d)["studies"]["A"]["status"] == "reopened"
    assert cli(d, "study", "reopen", "A").returncode == 2
    kinds = [e["kind"] for e in events(d) if e.get("study") == "A" and e["kind"].startswith(("study", "learning"))]
    assert kinds == ["study_start", "study_done", "learning", "learning", "study_reopen"]


def test_reading_only_study_and_poll_file():
    d = new_run()
    ok(d, "study", "new", "R", "--title", "Read", "--question", "q")
    open(os.path.join(d, "studies", "R", "poll"), "w").write("#!/bin/sh\nexit 1\n")
    assert json.loads(ok(d, "study", "check")) == {"ready": [], "no_learnings_tab": [], "poll": ["R"]}
    ok(d, "study", "conclude", "R", "--verdict", "confirmed", "--short", "s", "--learning", "a", "--learning", "b")


def test_top_set_and_summary():
    d = new_run()
    assert cli(d, "set", "bottom_line=x").returncode == 2  # set does not create the file
    record(d, "a", "--eta", "2026-10-30T01:00:00Z")
    record(d, "b")
    ok(d, "job", "set", "b", "state=done", "cost_gpu_h=3.5")
    assert cli(d, "set", "learnings=" + json.dumps([f"l{i}" for i in range(6)])).returncode == 2
    assert cli(d, "set", "learnings=not json").returncode == 2
    ok(d, "set", "learnings=" + json.dumps(["l1", "l2"]), "bottom_line=Ship it", "primary_metric=AUC",
       "sweep_stopped=confirmed close")
    st = exp(d)
    assert (st["learnings"], st["bottom_line"], st["primary_metric"], st["sweep_stopped"]) == (
        ["l1", "l2"], "Ship it", "AUC", "confirmed close")
    s = json.loads(ok(d, "summary"))
    assert s == {"jobs": 2, "by_state": {"queued": 1, "done": 1}, "gpu_h": 3.5,
                 "etas": [{"n": 1, "name": "a", "eta_utc": "2026-10-30T01:00:00Z"}], "studies": {}}


if __name__ == "__main__":  # no pytest in the humanize venv
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("all ok")
