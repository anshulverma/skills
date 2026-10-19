#!/usr/bin/env python3
"""Regression checks for the lockstep scripts. Run: ~/.cache/humanize-venv/bin/python test_scripts.py"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, HERE)
import state  # noqa: E402
import sweep  # noqa: E402
import md2ghtml  # noqa: E402
import render_tracker  # noqa: E402


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


def test_lease_unreadable_is_stale_and_cli_validates():
    d = tempfile.mkdtemp()
    open(os.path.join(d, ".lock"), "w").write('{"session_id": "s1", "heartb')
    assert state.acquire_lease(d, "s2")          # real clock, so the CLI calls below see a fresh lease
    cli = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, "state.py"), d, *a], capture_output=True).returncode
    assert cli("lease", "acquire", "s3") == 3
    assert cli("lease", "heartbeet", "s2") == 2 and os.path.exists(os.path.join(d, ".lock"))
    assert cli("reason", "add", "bogus", "x") == 2
    assert cli("event", "milestone", "text", "noequals") == 2


def test_atomic_write_cleans_temp_on_failure():
    d = tempfile.mkdtemp()
    try:
        state.atomic_write_json(os.path.join(d, "x.json"), {"bad": object()})
        assert False
    except TypeError:
        pass
    assert os.listdir(d) == []


# ---------- sweep.py ----------

def row(id, text, author="Owner", parent=None, quoted=None, t="2026-10-19T05:00:00Z", action=None, resolved=False):
    return {"id": id, "content": text, "author": author, "parent_id": parent, "quoted_text": quoted,
            "created_time": t, "action": action, "resolved": resolved}


DOC = {"title": "[Design] X", "status": "awaiting_acceptance", "qprefix": "Q",
       "questions": ["1. Which name? We recommend a.", "2. Push? We recommend no."], "answered": [],
       "accept_comment": None}


def kinds(items):
    return [i["kind"] for i in items]


def test_two_step_accept():
    rows = [row("a", "Approved", quoted="[Design] X")]
    it = sweep.pending(rows, dict(DOC), "Owner", set(), {}, "gate")
    assert kinds(it) == ["accept"] and it[0]["doc_status_after"] == "confirm_pending"
    rows += [row("b", "lgtm", parent="a", t="2026-10-19T05:01:00Z")]
    doc = {**DOC, "status": "confirm_pending", "accept_comment": "a"}
    assert kinds(sweep.pending(rows, doc, "Owner", {"a"}, {}, "gate")) == ["confirm"]


def test_accept_with_all_answered_is_immediate():
    rows = [row("q1", "a", quoted="1. Which name? We recommend a."), row("q2", "Q2: no", t="2026-10-19T05:01:00Z"),
            row("a", "LGTM", quoted="[Design] X", t="2026-10-19T05:02:00Z")]
    it = sweep.pending(rows, dict(DOC), "Owner", set(), {}, "gate")
    assert kinds(it) == ["answer", "answer", "accept"] and it[-1]["doc_status_after"] == "accepted"


def test_changes_then_confirm_in_one_sweep():
    doc = {**DOC, "status": "confirm_pending", "accept_comment": "a"}   # "a" becomes a former accept root via the changes
    rows = [row("a", "Approved", quoted="[Design] X"),
            row("c", "Changes: shorten it", quoted="[Design] X", t="2026-10-19T05:05:00Z"),
            row("d", "confirm", parent="a", t="2026-10-19T05:06:00Z")]
    it = sweep.pending(rows, doc, "Owner", {"a"}, {}, "gate")
    assert kinds(it) == ["changes", "stale_confirm"] and it[0]["doc_status_after"] == "awaiting_acceptance"


def test_reopen_and_already_accepted():
    doc = {**DOC, "status": "accepted"}
    rows = [row("r", "Reopen: S2 needs a rethink"), row("x", "approve", quoted="[Design] X", t="2026-10-19T05:01:00Z")]
    it = sweep.pending(rows, doc, "Owner", set(), {}, "accepted")
    assert kinds(it) == ["reopen", "accept"]
    assert it[0]["doc_status_after"] == "awaiting_acceptance"
    assert kinds(sweep.pending(rows[1:], doc, "Owner", set(), {}, "accepted")) == ["already_accepted"]


def test_action_confirm_and_scope():
    pa = {"r1": {"verb": "abort", "asked_reply_id": "bot1"}}
    rows = [row("r1", "Action: abort"), row("bot1", "[🤖 Claude Code] Needs Confirm: abort", parent="r1", t="2026-10-19T05:01:00Z"),
            row("c1", "Confirm", parent="r1", t="2026-10-19T05:02:00Z")]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", {"r1"}, pa, "tracker")) == ["confirm_action"]
    pa_close = {"r2": {"verb": "close", "asked_reply_id": "bot2"}}
    rows2 = [row("r2", "Action: close"), row("bot2", "[🤖 Claude Code] Needs Confirm: close", parent="r2", t="2026-10-19T05:01:00Z"),
             row("c2", "confirm", parent="r2", t="2026-10-19T05:03:00Z"), row("d", "D123456789 and D123456790", t="2026-10-19T05:04:00Z")]
    assert kinds(sweep.pending(rows2, dict(DOC), "Owner", {"r2"}, pa_close, "tracker")) == ["confirm_action", "diff_ids"]


def test_non_owner_and_own_replies():
    rows = [row("n", "Action: abort", author="Someone"), row("o", "[🤖 Claude Code] Running: pause", parent="n"),
            row("k", "(cont'd 2/2) tail", parent="n"), row("m", "", parent="n"), row("z", "resolve", action="resolve")]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", set(), {}, "gate")) == ["other_author"]


def test_resolved_thread_with_unhandled_reply_is_pending():
    rows = [row("a", "why X?", resolved=True), row("b", "and Y?", parent="a", t="2026-10-19T05:03:00Z")]
    it = sweep.pending(rows, dict(DOC), "Owner", {"a"}, {}, "gate")
    assert [i["id"] for i in it] == ["b"]


def test_two_owner_messages_oldest_first():
    rows = [row("a", "Q1: b", t="2026-10-19T05:00:00Z"), row("b", "it must stay private", parent="a", t="2026-10-19T05:02:00Z")]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", set(), {}, "gate")) == ["answer", "requirement"]


def test_pending_sorted_by_instant_across_offsets():
    rows = [row("late", "why?", t="2026-10-18T22:10:00-07:00"), row("early", "how?", t="2026-10-19T05:05:00Z")]
    assert [i["id"] for i in sweep.pending(rows, dict(DOC), "Owner", set(), {}, "gate")] == ["early", "late"]


def test_qprefix_is_escaped():
    p = sweep.qref("T3.")
    assert p.search("T3.1") and p.search("T3. 1") and not p.search("T301")
    assert sweep.qref("S").search("s2 sounds good")


def test_answer_match_unescapes_entities():
    doc = {**DOC, "questions": ["1. Can't we mount it? We recommend mounting."]}
    rows = [row("a", "yes", quoted="1. Can&#39;t we mount it?")]
    assert kinds(sweep.pending(rows, doc, "Owner", set(), {}, "gate")) == ["answer"]


def test_accept_on_title_with_entities():
    doc = {**DOC, "title": "[Design] Tom's & Jerry's plan"}
    rows = [row("a", "Accepted", quoted="[Design] Tom&#39;s &amp; Jerry&#39;s plan ")]
    assert kinds(sweep.pending(rows, doc, "Owner", set(), {}, "gate")) == ["accept"]


def test_parse_list_output_noise_and_shapes():
    rows, tok = sweep.parse_list_output('Warning: slow\n[{"id": "a"}]')
    assert rows == [{"id": "a"}] and tok is None
    rows, tok = sweep.parse_list_output('{"truncated": true, "data": [{"id": "b"}], "next_page_token": "T2"}')
    assert rows == [{"id": "b"}] and tok == "T2"
    for bad in ("", "Error: auth expired"):
        try:
            sweep.parse_list_output(bad)
            assert False, bad
        except ValueError:
            pass


def load_rows(name):
    rows = json.load(open(os.path.join(FIX, name)))
    return rows["data"] if isinstance(rows, dict) else rows


def test_recorded_fixtures_classify():
    spec_doc = {**DOC, "title": "[Design] Lockstep: Structured Development Reviewed One Doc at a Time", "qprefix": "S",
                "questions": json.load(open(os.path.join(FIX, "spec.questions.json")))}
    it = sweep.pending(load_rows("comments_spec.json"), spec_doc, "Anshul Verma", set(), {}, "gate")
    assert [i["id"] for i in it if i["kind"] == "accept"] == ["AAACI48AiLw"]
    prop = {**DOC, "title": "[Proposal] Galley: Doc-Gated Spec to Implementation", "qprefix": "Q",
            "questions": json.load(open(os.path.join(FIX, "proposal.questions.json")))}
    assert "accept" in kinds(sweep.pending(load_rows("comments_proposal.json"), prop, "Anshul Verma", set(), {}, "gate"))
    shop = {**DOC, "title": "[Design] RL and On-Policy Distillation for ShopEV Stage 1", "qprefix": "Q", "questions": []}
    assert "accept" not in kinds(sweep.pending(load_rows("comments_shopev_plan.json"), shop, "Anshul Verma", set(), {}, "gate"))


def test_cli_skips_unset_tracker_and_errors_on_missing_questions_file():
    d = tempfile.mkdtemp()
    json.dump({"owner_name": "Owner", "docs": {"p": {"id": "X", "title": "T", "status": "accepted", "qprefix": "Q",
               "questions_file": "docs/p/questions.json"}}}, open(os.path.join(d, "pipeline.json"), "w"))
    out = json.loads(subprocess.run([sys.executable, os.path.join(HERE, "sweep.py"), "--run", d, "--owner", "Owner"],
                                    capture_output=True, text=True).stdout)
    assert set(out["docs"]) == {"p"} and out["docs"]["p"]["status"] == "error"


def test_tracker_other_comments_ignored():
    rows = [row("a", "nice dashboard"), row("b", "Action: pause", t="2026-10-19T05:01:00Z")]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", set(), {}, "tracker")) == ["ignored", "action"]


def test_list_comments_follows_pages():
    d = tempfile.mkdtemp()
    fake = os.path.join(d, "meta")
    open(fake, "w").write("""#!/bin/bash
case "$*" in
  *--page-token=T2*) echo '[{"id": "b"}]' ;;
  *--id=BAD*) echo 'Error: auth expired'; exit 1 ;;
  *) echo 'Warning: slow'; echo '{"truncated": true, "data": [{"id": "a"}], "next_page_token": "T2"}' ;;
esac
""")
    os.chmod(fake, 0o755)
    old = os.environ["PATH"]
    os.environ["PATH"] = d + ":" + old
    try:
        assert [r["id"] for r in sweep.list_comments("DOC1")] == ["a", "b"]
        try:
            sweep.list_comments("BAD")
            assert False
        except (RuntimeError, ValueError):
            pass
    finally:
        os.environ["PATH"] = old


def test_frozen_docs_never_regate():
    for st in ("superseded", "reference"):
        doc = {**DOC, "status": st}
        rows = [row("a", "Approved", quoted="[Design] X"), row("c", "Changes: x", quoted="[Design] X", t="2026-10-19T05:01:00Z"),
                row("r", "Reopen it", t="2026-10-19T05:02:00Z")]
        assert kinds(sweep.pending(rows, doc, "Owner", set(), {}, "accepted")) == ["already_accepted"] * 3, st


def test_parse_list_output_truncated_without_token_and_bracket_noise():
    try:
        sweep.parse_list_output('{"truncated": true, "data": [{"id": "a"}]}')
        assert False
    except ValueError:
        pass
    assert sweep.parse_list_output('[INFO] fetching\n[{"id": "a"}]')[0] == [{"id": "a"}]


def test_confirm_before_needs_confirm_reply_does_not_count():
    pa = {"r1": {"verb": "abort", "asked_reply_id": "bot1"}}
    rows = [row("r1", "Action: abort"), row("c0", "confirm", parent="r1", t="2026-10-19T05:00:30Z"),
            row("bot1", "[🤖 Claude Code] Needs Confirm: abort", parent="r1", t="2026-10-19T05:01:00Z")]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", {"r1"}, pa, "gate")) == ["question"]
    assert kinds(sweep.pending(rows, dict(DOC), "Owner", {"r1"}, {"r1": {"verb": "abort", "asked_reply_id": "gone"}}, "gate")) == ["question"]


# ---------- md2ghtml.py ----------

def test_md2ghtml_full():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "fig"))
    md = ("<!-- humanize-context\ntype: x\n-->\n# My Title\n\n| TL;DR |\n|---|\n| one **bold** |\n| two |\n\n"
          "Body *it*.\n\n![Flow](fig/a.png)\n\n*Figure 1. Caption.*\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    title, html_ = md2ghtml.convert(md, d)
    assert title == "My Title" and '<p data-style="TITLE">My Title</p>' in html_
    assert "humanize-context" not in html_ and "<aside" in html_ and "<b>bold</b>" in html_
    assert f'src="file://{d}/fig/a.png"' in html_ and "<i>Figure 1. Caption.</i>" in html_
    assert "</table>\n<p></p>" in html_ and "<strong>" not in html_


def test_md2ghtml_without_tldr():
    title, html_ = md2ghtml.convert("# T\n\nJust text.\n", tempfile.mkdtemp())
    assert title == "T" and "<aside" not in html_ and "Just text." in html_


def test_md2ghtml_edges():
    d = tempfile.mkdtemp()
    md = ("# A &amp; B\n\n![Flow](fig/a.png)\n\nsee ![x](b.png) inline and ![r](https://e.com/r.png)\n\n"
          "```\n| TL;DR |\n|---|\n| not a tldr |\n![no](c.png)\n```\n\n- one\n- two\n")
    title, h = md2ghtml.convert(md, d)
    assert title == "A & B" and "@@" not in h
    assert f'<p style="text-align:center"><img src="file://{d}/fig/a.png" alt="Flow"></p>' in h
    assert f'see <img src="file://{d}/b.png" alt="x"> inline' in h and 'src="https://e.com/r.png"' in h
    assert "<aside" not in h and "| TL;DR |" in h and "![no](c.png)" in h


# ---------- render_tracker.py ----------

RUN_FIX = os.path.join(FIX, "run")


def copy_run():
    d = tempfile.mkdtemp()
    shutil.copytree(RUN_FIX, d, dirs_exist_ok=True)
    return d


def test_render_every_section():
    html_ = render_tracker.render(copy_run(), state.parse_ts("2026-10-19T07:00:00Z"))
    for h in ("How to steer this run", "Status", "Implementation plan", "Build to closure", "Milestones",
              "Follow-ups and blockers", "Gates", "Metrics", "Docs produced", "Actions", "Parked tasks",
              "Diffs", "Original request (verbatim)", "Event log"):
        assert f"<h2>{h}</h2>" in html_, h
    assert html_.count('src="file:///') == 3 and "Confirm" in html_ and "Reopen" in html_
    assert "relocate the demo scripts" in html_ and "Action: unblock" in html_


def test_render_fails_loudly():
    for missing in ("docs", "tracker_status", "request.md"):
        d = copy_run()
        if missing == "request.md":
            os.remove(os.path.join(d, "request.md"))
        else:
            p = json.load(open(os.path.join(d, "pipeline.json")))
            p.pop(missing)
            json.dump(p, open(os.path.join(d, "pipeline.json"), "w"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "render_tracker.py"), d, os.path.join(d, "o.html")],
                           capture_output=True, text=True)
        assert r.returncode == 1 and missing in (r.stderr + r.stdout), (missing, r.stderr)


def test_request_rendered_escaped_and_masked():
    d = copy_run()
    open(os.path.join(d, "request.md"), "w").write("make <b>it</b> & ship; api_key=sk-abc123XYZ and teh typo\n")
    html_ = render_tracker.render(d, state.parse_ts("2026-10-19T07:00:00Z"))
    assert "make &lt;b&gt;it&lt;/b&gt; &amp; ship" in html_ and "teh typo" in html_
    assert "sk-abc123XYZ" not in html_ and "api_key=[credential masked]" in html_
    render_tracker.render(d, state.parse_ts("2026-10-19T07:01:00Z"))
    assert open(os.path.join(d, "events.jsonl")).read().count("credential masked") == 1


def test_render_skips_torn_event_line():
    d = copy_run()
    open(os.path.join(d, "events.jsonl"), "a").write('{"ts": "2026-10-19T06:59:00Z", "kind": "mile')
    assert "<h2>Event log</h2>" in render_tracker.render(d, state.parse_ts("2026-10-19T07:00:00Z"))


def test_title_byte_identical():
    d = copy_run()
    t = state.parse_ts("2026-10-19T07:00:00Z")
    a = render_tracker.render(d, t).split("\n", 1)[0]
    b = render_tracker.render(d, t + timedelta(hours=1)).split("\n", 1)[0]
    assert a == b


def test_task_states_and_chart():
    d = copy_run()
    sdd = json.load(open(os.path.join(d, "run.json")))
    tasks = render_tracker.plan_tasks(os.path.join(d, sdd["plan_path"]))
    assert [t[0] for t in tasks] == [1, 2, 3, 4] and all("`" not in t[1] for t in tasks)
    states, times = render_tracker.task_states(d, sdd, tasks, render_tracker.read_events(d))
    assert states == {1: "complete", 2: "parked", 3: "in_progress", 4: "blocked"} and "task_done" in times[1]
    render_tracker.render(d, state.parse_ts("2026-10-19T07:00:00Z"))
    dot = open(os.path.join(d, "tracker", "tasks.dot")).read()
    assert "#2e9e5b" in dot and "#eb6834" in dot and "#2a78d6" in dot and "#c8312b" in dot and "spec accepted" in dot
    assert "T1 -> T4" not in dot          # transitive edge removed (T4 reaches T1 through T2 and T3)
    flow = open(os.path.join(d, "tracker", "flow.dot")).read()
    assert "accepted?" in flow and "all code" in flow and 'shape=ellipse' in flow


def test_no_plan_section_before_plan():
    d = copy_run()
    os.remove(os.path.join(d, "run.json"))
    p = json.load(open(os.path.join(d, "pipeline.json")))
    p["phase"] = "SPEC"
    json.dump(p, open(os.path.join(d, "pipeline.json"), "w"))
    assert "<h2>Implementation plan</h2>" not in render_tracker.render(d, state.parse_ts("2026-10-19T07:00:00Z"))


# ---------- await_owner.sh ----------

def test_await_owner_filters_bot_events():
    d = tempfile.mkdtemp()
    fake = os.path.join(d, "meta")
    n = os.path.join(d, "n")
    open(fake, "w").write(f"""#!/bin/bash
c=$(cat {n} 2>/dev/null || echo 0); echo $((c+1)) > {n}
case $c in
  0) b='[🤖 Claude Code] ack' ;; 1) b="(cont'd 2/2) tail" ;; *) b='Approved' ;;
esac
printf '{{"seq":1,"payload":{{"gdrive":{{"comment_body":"%s"}}}}}}\\n' "$b"
""")
    os.chmod(fake, 0o755)
    r = subprocess.run(["bash", os.path.join(HERE, "await_owner.sh"), "DOC1"], capture_output=True, text=True,
                       timeout=30, env={**os.environ, "PATH": d + ":" + os.environ["PATH"]})
    assert r.returncode == 0 and r.stdout.strip() == "HUMAN_EVENT doc=DOC1 body=Approved", (r.stdout, r.stderr)


def test_await_owner_leaves_no_orphans_and_backs_off():
    d = tempfile.mkdtemp()
    fake = os.path.join(d, "meta")
    open(fake, "w").write(f"""#!/bin/bash
case "$*" in
  *--id\\ SLOW*|*"--id SLOW"*) echo $$ > {d}/slow.pid; exec sleep 60 ;;
  *--id\\ FAIL*|*"--id FAIL"*) echo 'Error: cert expired'; exit 1 ;;
  *) printf '%s\\n' '{{"seq":1,"payload":{{"gdrive":{{"comment_body":"[🤖 x"}}}}}}' '{{"seq":2,"payload":{{"gdrive":{{"comment_body":"real\\nreply"}}}}}}' ;;
esac
""")
    os.chmod(fake, 0o755)
    env = {**os.environ, "PATH": d + ":" + os.environ["PATH"], "AWAIT_RETRY_SECS": "1"}
    import time
    p = subprocess.Popen(["bash", os.path.join(HERE, "await_owner.sh"), "SLOW", "FAIL"], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env)
    time.sleep(2.5)
    p.terminate()
    _, err = p.communicate(timeout=10)
    assert err.count("meta await failed for FAIL") <= 4, err          # backed off, not spinning
    pid = int(open(os.path.join(d, "slow.pid")).read())
    time.sleep(0.3)
    assert not os.path.exists(f"/proc/{pid}"), "orphaned meta await"
    r = subprocess.run(["bash", os.path.join(HERE, "await_owner.sh"), "OK"], capture_output=True, text=True, timeout=30, env=env)
    assert r.stdout.strip() == "HUMAN_EVENT doc=OK body=real reply", r.stdout   # batch scanned past the bot event
    assert subprocess.run(["bash", os.path.join(HERE, "await_owner.sh")], capture_output=True).returncode == 2



def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("all ok")


if __name__ == "__main__":
    main()
