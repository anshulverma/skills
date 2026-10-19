#!/usr/bin/env python3
"""Run-state helpers for lockstep: pipeline.json, derived status, reasons, the tick lease, events.

Usage:
  state.py RUN status
  state.py RUN lease acquire|heartbeat|release SESSION   (acquire exits 3 if another session holds it)
  state.py RUN event KIND TEXT [key=value ...]
  state.py RUN reason add|drop blocked|waiting REASON
"""
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

LEASE_STALE = timedelta(minutes=10)
GATED_PHASES = (None, "PROPOSAL", "SPEC")
OPEN = ("awaiting_acceptance", "confirm_pending")


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_json(path: str):
    with open(path) as f:
        return json.load(f)


def atomic_write_json(path: str, obj) -> None:
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def recompute_status(p: dict) -> str:
    if p.get("terminal"):
        return p["terminal"]
    if p.get("blocked_reasons"):
        return "blocked"
    if p.get("paused"):
        return "paused"
    if p.get("waiting_reasons"):
        return "waiting"
    # Before PLAN, an open gate means the run can only wait for the owner; from PLAN on, a task gate
    # alone does not stop the build (only all_parked does).
    if p.get("phase") in GATED_PHASES and any(
        isinstance(d, dict) and d.get("status") in OPEN for d in p.get("docs", {}).values()
    ):
        return "waiting"
    return "running"


def load(run_dir: str) -> dict:
    return read_json(os.path.join(run_dir, "pipeline.json"))


def save(run_dir: str, p: dict) -> None:
    p["status"] = recompute_status(p)
    atomic_write_json(os.path.join(run_dir, "pipeline.json"), p)


def add_reason(p: dict, kind: str, reason: str) -> None:
    lst = p.setdefault(f"{kind}_reasons", [])
    if reason not in lst:
        lst.append(reason)


def drop_reason(p: dict, kind: str, reason: str) -> None:
    lst = p.setdefault(f"{kind}_reasons", [])
    if reason in lst:
        lst.remove(reason)


def append_event(run_dir: str, kind: str, event: str, now: datetime | None = None, **fields) -> dict:
    try:
        phase = load(run_dir).get("phase")
    except (OSError, ValueError, AttributeError):
        phase = None
    e = {**fields, "ts": iso(now or now_utc()), "phase": phase, "kind": kind, "event": event}
    with open(os.path.join(run_dir, "events.jsonl"), "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def _lease_path(run_dir: str) -> str:
    return os.path.join(run_dir, ".lock")


class _guard:
    """Exclusive flock on <run>/.lock.guard: every lease read-decide-write happens under it."""

    def __init__(self, run_dir: str):
        self.path = os.path.join(run_dir, ".lock.guard")

    def __enter__(self):
        self.f = open(self.path, "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *exc):
        self.f.close()


def _read_lease(path: str) -> dict | None:
    try:
        held = read_json(path)
        return held if isinstance(held, dict) and "heartbeat_at" in held else {}
    except FileNotFoundError:
        return None
    except ValueError:
        return {}  # unreadable lease (crash mid-write): treated as stale


def acquire_lease(run_dir: str, session_id: str, now: datetime | None = None) -> bool:
    now = now or now_utc()
    path = _lease_path(run_dir)
    with _guard(run_dir):
        held = _read_lease(path)
        same = bool(held) and held.get("session_id") == session_id
        if held:
            try:
                stale = now - parse_ts(held["heartbeat_at"]) > LEASE_STALE
            except (TypeError, ValueError):
                stale = True
            if not (stale or same):
                return False
        acquired = held.get("acquired_at", iso(now)) if same else iso(now)
        atomic_write_json(path, {"session_id": session_id, "acquired_at": acquired, "heartbeat_at": iso(now)})
    if held is not None and not same:
        append_event(run_dir, "lease_takeover", f"lease taken over from {held.get('session_id', 'an unreadable lease')}",
                     now=now, previous=held.get("session_id"))
    return True


def heartbeat(run_dir: str, session_id: str, now: datetime | None = None) -> None:
    path = _lease_path(run_dir)
    with _guard(run_dir):
        held = _read_lease(path)
        if not held or held.get("session_id") != session_id:
            raise RuntimeError(f"lease not held by {session_id}")
        held["heartbeat_at"] = iso(now or now_utc())
        atomic_write_json(path, held)


def release_lease(run_dir: str, session_id: str) -> None:
    path = _lease_path(run_dir)
    with _guard(run_dir):
        held = _read_lease(path)
        if held and held.get("session_id") == session_id:
            os.remove(path)


def _coerce(v: str):
    try:
        return int(v)
    except ValueError:
        return v


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    run_dir, cmd, rest = argv[0], argv[1], argv[2:]
    if cmd == "status":
        print(recompute_status(load(run_dir)))
    elif cmd == "lease" and len(rest) == 2 and rest[0] in ("acquire", "heartbeat", "release"):
        op, sid = rest
        if op == "acquire":
            return 0 if acquire_lease(run_dir, sid) else 3
        try:
            (heartbeat if op == "heartbeat" else release_lease)(run_dir, sid)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 3
    elif cmd == "event" and len(rest) >= 2 and all("=" in kv for kv in rest[2:]):
        fields = dict(kv.split("=", 1) for kv in rest[2:])
        print(json.dumps(append_event(run_dir, rest[0], rest[1], **{k: _coerce(v) for k, v in fields.items()})))
    elif cmd == "reason" and len(rest) == 3 and rest[0] in ("add", "drop") and rest[1] in ("blocked", "waiting"):
        op, kind, reason = rest
        p = load(run_dir)
        (add_reason if op == "add" else drop_reason)(p, kind, reason)
        save(run_dir, p)
        print(p["status"])
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
