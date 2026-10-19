#!/usr/bin/env python3
"""Regression checks for the lockstep scripts. Run: ~/.cache/humanize-venv/bin/python test_scripts.py"""

import json
import os
import sys
import tempfile
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, HERE)
import state  # noqa: E402


def test_recompute_status():
    base = {"terminal": None, "paused": False, "blocked_reasons": [], "waiting_reasons": [], "docs": {}}
    assert state.recompute_status(dict(base)) == "running"
    assert state.recompute_status({**base, "waiting_reasons": ["all_parked"]}) == "waiting"
    assert state.recompute_status({**base, "paused": True, "waiting_reasons": ["x"]}) == "paused"
    assert state.recompute_status({**base, "paused": True, "blocked_reasons": ["sdd"]}) == "blocked"
    assert state.recompute_status({**base, "terminal": "aborted", "blocked_reasons": ["sdd"]}) == "aborted"
    gated = {**base, "docs": {"proposal": {"status": "awaiting_acceptance"}}}
    assert state.recompute_status(gated) == "waiting"
    mixed = {**base, "docs": {"proposal": {"status": "accepted"}, "task-3": {"status": "confirm_pending"}}}
    assert state.recompute_status(mixed) == "waiting"
    assert state.recompute_status({**mixed, "phase": "BUILD"}) == "running"
    assert state.recompute_status({**gated, "phase": "PLAN"}) == "running"


def test_reasons_do_not_clear_each_other():
    p = {"blocked_reasons": [], "waiting_reasons": []}
    state.add_reason(p, "blocked", "sdd")
    state.add_reason(p, "blocked", "doc_not_private:spec")
    state.add_reason(p, "blocked", "sdd")
    assert p["blocked_reasons"] == ["sdd", "doc_not_private:spec"]
    state.drop_reason(p, "blocked", "sdd")
    assert p["blocked_reasons"] == ["doc_not_private:spec"]


def test_lease_rules():
    d = tempfile.mkdtemp()
    t0 = state.parse_ts("2026-10-19T06:00:00Z")
    assert state.acquire_lease(d, "s1", t0)
    assert not state.acquire_lease(d, "s2", t0 + timedelta(minutes=9))
    assert state.acquire_lease(d, "s1", t0 + timedelta(minutes=1))
    assert state.acquire_lease(d, "s2", t0 + timedelta(minutes=12))
    assert any(json.loads(line)["kind"] == "lease_takeover" for line in open(os.path.join(d, "events.jsonl")))
    state.release_lease(d, "s2")
    assert not os.path.exists(os.path.join(d, ".lock"))


def test_heartbeat_keeps_lease():
    d = tempfile.mkdtemp()
    t0 = state.parse_ts("2026-10-19T06:00:00Z")
    assert state.acquire_lease(d, "s1", t0)
    state.heartbeat(d, "s1", t0 + timedelta(minutes=9))
    assert not state.acquire_lease(d, "s2", t0 + timedelta(minutes=15))


def test_parse_ts_offsets():
    assert state.parse_ts("2026-10-18T22:37:13-07:00") == state.parse_ts("2026-10-19T05:37:13Z")


def test_save_recomputes_status_atomically():
    d = tempfile.mkdtemp()
    state.save(d, {"terminal": None, "paused": True, "blocked_reasons": [], "waiting_reasons": [], "docs": {}})
    assert state.load(d)["status"] == "paused"
    assert [f for f in os.listdir(d) if f.startswith("pipeline.json.")] == []


def test_append_event_fields():
    d = tempfile.mkdtemp()
    e = state.append_event(d, "task_start", "Task 3 started", now=state.parse_ts("2026-10-19T06:00:00Z"), task=3)
    assert e == {"ts": "2026-10-19T06:00:00Z", "phase": None, "kind": "task_start", "event": "Task 3 started", "task": 3}
    assert json.loads(open(os.path.join(d, "events.jsonl")).read()) == e


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("all ok")


if __name__ == "__main__":
    main()
