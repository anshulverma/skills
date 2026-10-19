#!/usr/bin/env python3
"""List pending owner comments on a run's docs and classify each one, oldest first.

Usage: sweep.py --run RUN_DIR --owner NAME [--doc KEY ...]
Prints {"docs": {key: {"status": "ok", "items": [...]} | {"status": "error", "error": str}}}.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys

from state import parse_ts, read_json

ACCEPT = re.compile(r"^\s*(approve[sd]?|accept(ed)?|lgtm)\b", re.I)
CHANGES = re.compile(r"^\s*changes?\s*:", re.I)
CONFIRM = re.compile(r"^\s*confirm\b", re.I)
REOPEN = re.compile(r"^\s*reopen\b", re.I)
ACTION = re.compile(r"^\s*action\s*:", re.I)
REQ = re.compile(r"\b(should|must|make sure|needs?|has to|want)\b", re.I)
DIFF = re.compile(r"\bD\d{6,}\b")


def qref(qprefix: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(qprefix) + r"\s?(\d+)\b", re.I)


def own(text: str) -> bool:
    return text.startswith("[🤖") or text.startswith("(cont'd")


def clean(s) -> str:
    return html.unescape(s or "").strip()


def parse_list_output(out: str) -> tuple[list[dict], str | None]:
    dec = json.JSONDecoder()
    for i, ch in enumerate(out):  # skip noise like "Warning: ..." or "[INFO] ..." before the JSON
        if ch not in "[{":
            continue
        try:
            raw, _ = dec.raw_decode(out[i:])
        except ValueError:
            continue
        if isinstance(raw, list):
            return raw, None
        if isinstance(raw, dict) and isinstance(raw.get("data"), list):
            token = raw.get("next_page_token")
            if raw.get("truncated") and not token:
                raise ValueError("listing truncated with no next_page_token")
            return raw["data"], token
    raise ValueError(f"no comment list JSON in output: {out.strip()[:200]!r}")


def list_comments(doc_id: str) -> list[dict]:
    rows, token = [], None
    while True:
        cmd = ["meta", "google.docs.comment", "list", f"--id={doc_id}", "--output=json", "-l", "200", "--columns=all"]
        if token:
            cmd.append(f"--page-token={token}")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"comment list failed ({p.returncode}): {(p.stdout + p.stderr).strip()[:200]}")
        page, nxt = parse_list_output(p.stdout)
        rows += page
        if not nxt:
            return rows
        if nxt == token:
            raise RuntimeError(f"comment list repeated page token {nxt!r}")
        token = nxt


def _answer_q(root: dict, text: str, doc: dict) -> int | None:
    anchor = clean(root.get("quoted_text"))
    if anchor:
        for i, q in enumerate(doc.get("questions") or []):
            qc = clean(q)
            if anchor in qc or qc in anchor:
                return i + 1
    m = qref(doc["qprefix"]).match(text.lstrip())  # "S3: ..." answers S3; "an S3 bucket" does not
    if not m:
        return None
    q, nq = int(m.group(1)), len(doc.get("questions") or [])
    return q if not nq or 1 <= q <= nq else None


def pending(rows: list[dict], doc: dict, owner: str, handled: set[str], pending_actions: dict, scope: str) -> list[dict]:
    by_id = {r["id"]: r for r in rows}
    title = clean(doc.get("title"))
    status = doc.get("status")
    frozen = scope == "accepted" and status in ("accepted", "superseded", "reference")
    accept_root = doc.get("accept_comment")
    answered = set(doc.get("answered") or [])
    former = set(doc.get("superseded_accepts") or [])
    nq = len(doc.get("questions") or [])

    def root_of(r):
        return by_id.get(r.get("parent_id"), r) if r.get("parent_id") else r

    candidates = []
    for r in rows:
        text = (r.get("content") or "").strip()
        root = root_of(r)
        if r.get("action") or not text or own(text) or r["id"] in handled:
            continue
        if "humanize-context" in (root.get("content") or ""):
            continue
        candidates.append(r)
    candidates.sort(key=lambda r: (parse_ts(r["created_time"]), r["id"]))

    items = []
    for r in candidates:
        text = r["content"].strip()
        root = root_of(r)
        top = r is root
        on_title = top and bool(title) and clean(root.get("quoted_text")) == title
        q = None
        if r.get("author") != owner:
            kind = "other_author"
        elif ACTION.match(text):
            kind = "action"
        elif (not top and root["id"] in pending_actions and CONFIRM.match(text)
              and _after(r, by_id.get(pending_actions[root["id"]].get("asked_reply_id")))):
            kind = "confirm_action"
        elif scope == "tracker":
            kind = "diff_ids" if DIFF.search(text) else "ignored"
        elif frozen and REOPEN.match(text):
            if status == "accepted":
                kind, status, frozen = "reopen", "awaiting_acceptance", False
            else:
                kind = "already_accepted"  # superseded and reference docs never re-gate
        elif frozen and on_title and (ACCEPT.match(text) or CHANGES.match(text)):
            kind = "already_accepted"
        elif on_title and ACCEPT.match(text):
            if status == "awaiting_acceptance":
                kind = "accept"
                former.add(root["id"])
                if all(i in answered for i in range(1, nq + 1)):
                    status = "accepted"
                else:
                    status, accept_root = "confirm_pending", root["id"]
            elif status == "accepted":
                kind = "already_accepted"
            elif status == "confirm_pending":
                kind, status = "confirm", "accepted"  # a second top-level accept confirms, like a reply would
            else:
                kind = "question"
        elif not top and status == "confirm_pending" and root["id"] == accept_root and (ACCEPT.match(text) or CONFIRM.match(text)):
            kind, status = "confirm", "accepted"
        elif not top and root["id"] in former and (ACCEPT.match(text) or CONFIRM.match(text)):
            kind = "already_accepted" if status == "accepted" else "stale_confirm"
        elif on_title and CHANGES.match(text):
            if status == "accepted":
                kind = "already_accepted"
            else:
                kind = "changes"
                if status == "confirm_pending":
                    former.add(accept_root)
                    status, accept_root = "awaiting_acceptance", None
        elif (q := _answer_q(root, text, doc)) is not None:
            kind = "answer"
            answered.add(q)
        elif REQ.search(text) and "?" not in text:
            kind = "requirement"
        else:
            kind = "question"
        items.append({"id": r["id"], "root": root["id"], "created_time": r["created_time"], "author": r.get("author"),
                      "quoted": root.get("quoted_text"), "text": text, "kind": kind, "q": q,
                      "doc_status_after": status})
    return items


def _after(r: dict, asked: dict | None) -> bool:
    # A confirm only counts after the skill's "Needs Confirm" reply; if that reply cannot be found, it does not.
    return asked is not None and parse_ts(r["created_time"]) > parse_ts(asked["created_time"])


def _doc_dict(run_dir: str, key: str, d: dict) -> dict:
    for field in ("qprefix", "title"):
        if not d.get(field):
            raise ValueError(f"docs.{key}.{field} is required")
    qfile = d.get("questions_file")
    questions = []
    if qfile:
        path = os.path.join(run_dir, qfile)
        if not os.path.exists(path):
            raise FileNotFoundError(f"docs.{key}.questions_file not found: {path}")
        questions = read_json(path)
    return {**d, "questions": questions, "answered": list(d.get("answered") or []),
            "superseded_accepts": list(d.get("superseded_accepts") or [])}


def _handled(run_dir: str, key: str) -> set[str]:
    path = os.path.join(run_dir, "docs", key, "handled.json")
    return set(read_json(path)) if os.path.exists(path) else set()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--owner", default="")
    ap.add_argument("--doc", action="append")
    a = ap.parse_args(argv)
    if not a.owner.strip():
        print("owner required", file=sys.stderr)
        return 2
    p = read_json(os.path.join(a.run, "pipeline.json"))
    docs = p.get("docs", {})
    swept = [k for k, d in docs.items() if d.get("kind") != "external"]  # linked docs the run does not own
    keys = a.doc or [*swept, *(["tracker"] if p.get("tracker_doc") else [])]
    result = {}
    for key in keys:
        try:  # one doc failing never aborts the others
            if key == "tracker":
                if not p.get("tracker_doc"):
                    raise ValueError("tracker_doc is not set")
                doc, scope, doc_id = {"title": p.get("tracker_title", ""), "qprefix": "Q"}, "tracker", p["tracker_doc"]
            else:
                d = docs[key]
                doc = _doc_dict(a.run, key, d)
                scope = "accepted" if d.get("status") in ("accepted", "superseded", "reference") else "gate"
                doc_id = d["id"]
            items = pending(list_comments(doc_id), doc, a.owner, _handled(a.run, key), p.get("pending_actions") or {}, scope)
            result[key] = {"status": "ok", "items": items}
        except Exception as e:
            result[key] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
    print(json.dumps({"docs": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
