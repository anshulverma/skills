#!/usr/bin/env python3
"""Checks for tabs.py. Run: ~/.cache/humanize-venv/bin/python test_tabs.py (or -m pytest -q test_tabs.py)."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tabs  # noqa: E402
from PIL import Image  # noqa: E402

TAB = "t.x"
# shapes as the live doc returns them (scratch doc readback, 2026-10-29)
ASIDE_TEXT = ('<aside hidden><div data-id="c1" data-author="Owner" data-quote="{q}" data-status="OPEN" '
              'data-ranges="1-15" data-tab-id="t.x">note</div></aside>')
ASIDE_IMG = ('<aside hidden><div data-id="{cid}" data-author="Owner" data-status="OPEN" data-ranges="90-91" '
             'data-tab-id="t.x">on the figure</div></aside>')


def live_img(oid, w=300, h=150):
    return f'<img src="https://docs.google.com/docs-images-rt/x" width="{w}" height="{h}" data-object-id="{oid}"/>'


def png(d, name, size, colour=(42, 120, 214)):
    path = os.path.join(d, name)
    Image.new("RGB", size, colour).save(path)
    return path


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ---------- build_from ----------

def test_build_from_images():
    d = tempfile.mkdtemp()
    keep = png(d, "keep.png", (400, 200))
    changed = png(d, "changed.png", (380, 200))
    new = png(d, "new.png", (100, 100))
    stale = png(d, "stale.png", (200, 400))
    threaded = png(d, "threaded.png", (200, 400))
    live = "".join([f"<p>{live_img('kix.keep')}</p>\n", f"<p>{live_img('kix.chg')}</p>\n",
                    f"<p>{live_img('kix.stale')}</p>\n", f"<p>{live_img('kix.thr')}</p>\n",
                    ASIDE_IMG.format(cid="cimg"), "\n<p>tail</p>"])
    figs = {keep: {"object_id": "kix.keep", "sha256": sha(keep)},
            changed: {"object_id": "kix.chg", "sha256": "old"},
            stale: {"object_id": "kix.stale", "sha256": "old"},
            threaded: {"object_id": "kix.thr", "sha256": "old"}}
    body = "".join(f'<p><img src="file://{p}"></p>\n' for p in (keep, changed, new, stale, threaded))
    r = tabs.build_from(body, live, figs, TAB)
    assert live_img("kix.keep") in r["html"] and f'file://{keep}' not in r["html"]        # unchanged: no swap
    assert f'file://{new}' in r["html"] and r["new_images"] == [new]                       # new: uploaded by apply
    by = {s["object_id"]: s for s in r["swaps"]}
    assert set(by) == {"kix.chg", "kix.stale"}
    assert by["kix.chg"]["preserve"] and (by["kix.chg"]["w"], by["kix.chg"]["h"]) == (300, 150)
    assert not by["kix.stale"]["preserve"]                                                 # stale frame, no threads
    assert r["blocked"] == {"kix.thr": ["cimg"]}                                           # stale frame with a thread
    r2 = tabs.build_from(body, live, figs, TAB, allow_reset=["kix.thr"])
    assert not r2["blocked"] and not {s["object_id"]: s for s in r2["swaps"]}["kix.thr"]["preserve"]


def test_build_from_holds_row_and_paragraph():
    # asides follow the anchored paragraph, or the whole table for a comment in a cell
    live = ("<h1>Sweep</h1>\n<p>Status: the sweep is running with four arms today.</p>\n"
            + ASIDE_TEXT.format(q="four arms") + "\n<p>The sweep uses four arms of compute.</p>\n"
            "<table><tr><td>#</td><td>Job</td></tr>\n<tr><td>7</td><td>run seven, eval pending</td></tr>\n"
            "<tr><td>8</td><td>run eight</td></tr></table>\n" + ASIDE_TEXT.format(q="eval pending"))
    body = ("<h1>Sweep</h1>\n<p>Status: the sweep is running with five arms today.</p>\n"
            "<p>The sweep uses four arms of compute.</p>\n"
            "<table><tr><td>#</td><td>Job</td></tr>\n<tr><td>7</td><td>run seven, eval done</td></tr>\n"
            "<tr><td>8</td><td>run eight, done</td></tr></table>")
    r = tabs.build_from(body, live, {}, TAB)
    assert sorted(r["held"]) == ["eval pending", "four arms"]   # the quote elsewhere in BODY does not count
    assert "running with four arms" in r["html"] and "five arms" not in r["html"]
    assert "run seven, eval pending" in r["html"] and "run eight, done" in r["html"]
    removed = body.replace("<tr><td>7</td><td>run seven, eval done</td></tr>\n", "")
    assert "<tr><td>7</td><td>run seven, eval pending</td></tr>" in tabs.build_from(removed, live, {}, TAB)["html"]
    same = body.replace("five arms", "four arms").replace("eval done", "eval pending, then done")
    assert tabs.build_from(same, live, {}, TAB)["held"] == []
    other_tab = tabs.build_from(body, live.replace('data-tab-id="t.x"', 'data-tab-id="t.0"'), {}, TAB)
    assert other_tab["held"] == [] and other_tab["html"] == body


def test_figs_keyed_by_run_relative_path():
    # two studies each draw figs/summary.png on one tab: one basename, two images
    run = tempfile.mkdtemp()
    a, b = (os.path.join(run, "studies", x, "figs") for x in ("a", "b"))
    os.makedirs(a), os.makedirs(b)
    pa, pb = png(a, "summary.png", (400, 200)), png(b, "summary.png", (400, 200), (9, 9, 9))
    assert tabs.fig_key(run, pa) == "studies/a/figs/summary.png"
    assert tabs.fig_key(run, "/elsewhere/x.png") == "/elsewhere/x.png"
    live = f"<p>{live_img('kix.a')}</p>\n<p>{live_img('kix.b')}</p>"
    figs = {"studies/a/figs/summary.png": {"object_id": "kix.a", "sha256": sha(pa)},
            "studies/b/figs/summary.png": {"object_id": "kix.b", "sha256": sha(pb)}}
    body = f'<p><img src="file://{pa}"></p>\n<p><img src="file://{pb}"></p>'
    r = tabs.build_from(body, live, figs, TAB, run=run)
    assert r["swaps"] == [] and r["new_images"] == [] and r["html"] == live
    # an old basename-keyed figs.json: moved when one BODY image has the name, dropped when two do, else kept
    other = png(a, "other.png", (100, 100))
    os.makedirs(os.path.join(run, "docs", "studies"))
    json.dump({"summary.png": {"object_id": "kix.b"}, "other.png": {"object_id": "kix.o"},
               "gone.png": {"object_id": "kix.g"}}, open(os.path.join(run, "docs", "studies", "figs.json"), "w"))
    got = tabs._figs(run, "studies", body + f'<p><img src="file://{other}"></p>')
    assert got == {"studies/a/figs/other.png": {"object_id": "kix.o"}, "gone.png": {"object_id": "kix.g"}}


def test_hold_uses_the_same_place_not_the_closest_text():
    # study B's Jobs line carries the comment; study A's changed line now reads like B's live line
    live = ("<h2>Study A</h2>\n<p>Jobs: 3 running, 2 done</p>\n<h2>Study B</h2>\n<p>Jobs: 4 running, 1 done</p>\n"
            + ASIDE_TEXT.format(q="4 running"))
    body = "<h2>Study A</h2>\n<p>Jobs: 4 running, 2 done</p>\n<h2>Study B</h2>\n<p>Jobs: 5 running, 1 done</p>"
    r = tabs.build_from(body, live, {}, TAB)
    assert r["held"] == ["4 running"] and r["unplaced"] == []
    assert r["html"] == body.replace("5 running, 1 done", "4 running, 1 done")
    gone = tabs.build_from("<h2>Study A</h2>\n<p>Jobs: 4 running, 2 done</p>", live, {}, TAB)
    assert gone["held"] == [] and gone["unplaced"] == ["4 running"]          # no counterpart: no guess


def test_pass1_same_key_rows_only():
    live = ("<p>old para</p><table><tr><td>#</td><td>Job</td></tr><tr><td>1</td><td>a</td></tr>"
            "<tr><td>2</td><td>b</td></tr></table><table><tr><td>K</td></tr><tr><td>x</td></tr></table>")
    new = ("<p>new para</p><table><tr><td>#</td><td>Job</td></tr><tr><td>2</td><td>B</td></tr>"
           "<tr><td>1</td><td>A</td></tr><tr><td>3</td><td>c</td></tr></table>"
           "<table><tr><td>K</td><td>V</td></tr><tr><td>x</td><td>1</td></tr></table>")
    out = tabs.pass1(live, new)
    assert out == ("<p>old para</p><table><tr><td>#</td><td>Job</td></tr><tr><td>1</td><td>A</td></tr>"
                   "<tr><td>2</td><td>B</td></tr></table><table><tr><td>K</td></tr><tr><td>x</td></tr></table>")


def test_pad_matches_frame():
    d = tempfile.mkdtemp()
    out = tabs.pad(png(d, "p.png", (380, 200)), 300, 150, os.path.join(d, "o.png"))
    w, h = Image.open(out).size
    assert (w, h) == (400, 200) and Image.open(out).getpixel((0, 0)) == (42, 120, 214)


def test_threads_and_image_threads():
    live = ("<h1>Title</h1>\n" + ASIDE_TEXT.format(q="Title") + "\n<p>" + live_img("kix.a") + "</p>\n"
            + ASIDE_IMG.format(cid="ci") + "\n<p>x</p>" + ASIDE_IMG.format(cid="stray").replace("90-91", ""))
    assert [t["quote"] for t in tabs.threads(live, TAB)] == ["Title", ""]
    assert tabs.image_threads(live, TAB) == {"kix.a": ["ci"]}
    assert tabs.threads(live, "t.0") == []


# ---------- CLI with a fake meta ----------

FAKE = r'''#!/usr/bin/env python3
import json, os, shutil, sys
D = os.environ["FAKE_DIR"]
a = sys.argv[1:]
open(os.path.join(D, "log"), "a").write(json.dumps(a) + "\n")
s = " ".join(a)
opt = lambda k: next((x.split("=", 1)[1] for x in a if x.startswith(k + "=")), None)
if "share list" in s:
    print(open(os.path.join(D, "share.json")).read() if os.path.exists(os.path.join(D, "share.json"))
          else '[{"role": "owner", "email": "o@x"}]')
elif "tab list" in s:
    print(open(os.path.join(D, "tabs.json")).read())
elif "tab add" in s:
    print("Poll hint: noise\n" + json.dumps({"tabId": "t.added", "title": opt("--title")}))
elif a[:2] == ["google.docs", "get"]:
    n = len([l for l in open(os.path.join(D, "log")) if '"get"' in l])
    src = os.path.join(D, f"live.{n}.html")
    src = src if os.path.exists(src) else os.path.join(D, "live.html")
    dest = opt("--dest")[len("file://"):]
    shutil.copyfile(src, dest); shutil.copyfile(src, dest + ".base")
    print("wrote")
elif a[:2] == ["google.docs", "apply"]:
    if "--dry-run" in a and os.path.exists(os.path.join(D, "nochange")):
        print("No changes"); sys.exit(0)
    if os.path.exists(os.path.join(D, "orphan")):
        print("✗ This edit would orphan 1 anchored comment(s): it razes the text"); sys.exit(1)
    print("Dry run — changes" if "--dry-run" in a else "✓ Applied 3 requests")
elif a[:2] == ["google.docs", "replace-image"]:
    oid = opt("--image-id")
    if os.path.exists(os.path.join(D, "fail-" + oid)):
        print("backend error", file=sys.stderr); sys.exit(1)
    print(json.dumps({"imageObjectId": oid if "--preserve-frame" in a else "kix.fresh", "replacedImageObjectId": oid}))
else:
    print("unexpected", s, file=sys.stderr); sys.exit(9)
'''


def fake_run(docs=None, live="<p>x</p>"):
    run, fake = tempfile.mkdtemp(), tempfile.mkdtemp()
    p = {"slug": "t", "phase": "BUILD", "layout": "tabs", "tracker_doc": "DOC", "tracker_tab": "t.0",
         "terminal": None, "paused": False, "blocked_reasons": [], "waiting_reasons": [], "docs": docs or {}}
    json.dump(p, open(os.path.join(run, "pipeline.json"), "w"))
    open(os.path.join(run, "events.jsonl"), "w").close()
    open(os.path.join(fake, "meta"), "w").write(FAKE)
    os.chmod(os.path.join(fake, "meta"), 0o755)
    open(os.path.join(fake, "live.html"), "w").write(live)
    return run, fake


def cli(run, fake, *args):
    env = {**os.environ, "PATH": fake + ":" + os.environ["PATH"], "FAKE_DIR": fake, "LOCKSTEP_RETRY_SLEEP": "0"}
    return subprocess.run([sys.executable, os.path.join(HERE, "tabs.py"), *args], capture_output=True, text=True,
                          env=env, timeout=60)


def calls(fake):
    path = os.path.join(fake, "log")
    return [json.loads(x) for x in open(path)] if os.path.exists(path) else []


def events(run):
    return [json.loads(x) for x in open(os.path.join(run, "events.jsonl"))]


def test_ensure_adopts_existing_tab_then_adds():
    run, fake = fake_run()
    json.dump([{"tabId": "t.0", "title": "Tracker", "parent_tabId": ""},
               {"tabId": "t.ev", "title": "Event log", "parent_tabId": "t.0"}], open(os.path.join(fake, "tabs.json"), "w"))
    r = cli(run, fake, "ensure", run, "events", "--title", "Event log", "--tab-title", "Event log", "--kind", "log",
            "--parent", "tracker")
    assert r.returncode == 0 and r.stdout.strip() == "t.ev", r.stderr
    assert not any(c[:2] == ["google.docs.tab", "add"] for c in calls(fake))
    p = json.load(open(os.path.join(run, "pipeline.json")))
    assert p["docs"]["events"]["tab"] == "t.ev" and p["tracker_events_tab"] == "t.ev"
    assert p["docs"]["events"]["status"] == "reference" and p["docs"]["events"]["id"] == "DOC"
    assert [e["kind"] for e in events(run)] == ["tab_created"]
    r = cli(run, fake, "ensure", run, "events", "--title", "Event log", "--tab-title", "Event log", "--kind", "log",
            "--parent", "tracker")
    assert r.stdout.strip() == "t.ev" and len(events(run)) == 1                 # recorded tab is live: no-op
    r = cli(run, fake, "ensure", run, "spec", "--title", "[Design] X", "--tab-title", "Spec", "--kind", "spec",
            "--qprefix", "S")
    assert r.returncode == 0 and r.stdout.strip() == "t.added", r.stderr
    add = [c for c in calls(fake) if c[:2] == ["google.docs.tab", "add"]]
    assert len(add) == 1 and "--title=Spec" in add[0] and not any(x.startswith("--parent-tab-id") for x in add[0])
    spec = json.load(open(os.path.join(run, "pipeline.json")))["docs"]["spec"]
    assert spec["status"] == "drafting" and spec["qprefix"] == "S"


def test_ensure_qprefix_rules():
    run, fake = fake_run({"studies": {"id": "DOC", "tab": "t.st"}})
    json.dump([{"tabId": "t.0", "title": "Tracker", "parent_tabId": ""}], open(os.path.join(fake, "tabs.json"), "w"))
    r = cli(run, fake, "ensure", run, "spec", "--title", "S", "--tab-title", "Spec", "--kind", "spec")
    assert r.returncode == 2 and "qprefix" in r.stderr and calls(fake) == []
    r = cli(run, fake, "ensure", run, "study-a", "--title", "R", "--tab-title", "Study: A", "--kind", "study",
            "--parent", "studies", "--qprefix", "L")
    assert r.returncode == 0, r.stderr
    assert "qprefix" not in json.load(open(os.path.join(run, "pipeline.json")))["docs"]["study-a"]


def test_ensure_never_adopts_an_owned_or_archived_tab():
    run, fake = fake_run({"studies": {"id": "DOC", "tab": "t.st"},
                          "study-a": {"id": "DOC", "tab": "t.a", "parent": "studies", "kind": "study"},
                          "spec": {"id": "DOC", "tab": "t.s", "kind": "spec", "qprefix": "S", "archived": True}})
    json.dump([{"tabId": "t.st", "title": "Studies", "parent_tabId": ""},
               {"tabId": "t.a", "title": "Study: Same", "parent_tabId": "t.st"},
               {"tabId": "t.s", "title": "Spec", "parent_tabId": ""}], open(os.path.join(fake, "tabs.json"), "w"))
    r = cli(run, fake, "ensure", run, "study-b", "--title", "R", "--tab-title", "Study: Same", "--kind", "study",
            "--parent", "studies")
    assert r.returncode == 0 and r.stdout.strip() == "t.added", r.stderr       # t.a belongs to study-a
    r = cli(run, fake, "ensure", run, "spec", "--title", "S", "--tab-title", "Spec", "--kind", "spec")
    assert r.returncode == 0 and r.stdout.strip() == "t.added", r.stderr       # archived: a fresh tab
    spec = json.load(open(os.path.join(run, "pipeline.json")))["docs"]["spec"]
    assert spec["tab"] == "t.added" and "archived" not in spec and spec["qprefix"] == "S"
    assert len([c for c in calls(fake) if c[:2] == ["google.docs.tab", "add"]]) == 2


def test_legacy_run_refused():
    run, fake = fake_run()
    p = json.load(open(os.path.join(run, "pipeline.json")))
    del p["layout"]
    json.dump(p, open(os.path.join(run, "pipeline.json"), "w"))
    r = cli(run, fake, "ensure", run, "events", "--title", "E", "--tab-title", "E", "--kind", "log")
    assert r.returncode == 2 and calls(fake) == []


def test_ours_refused_for_non_tracker_key():
    run, fake = fake_run({"experiments": {"id": "DOC", "tab": "t.x"}})
    body = os.path.join(run, "b.html")
    open(body, "w").write("<p>x</p>")
    r = cli(run, fake, "apply", run, "experiments", "--body", body, "--ours")
    assert r.returncode == 2 and "refused" in r.stderr and calls(fake) == []


def test_private_predicate():
    run, fake = fake_run()
    assert cli(run, fake, "private", run).returncode == 0
    open(os.path.join(fake, "share.json"), "w").write('[{"role": "owner"}, {"role": "reader", "type": "domain"}]')
    assert cli(run, fake, "private", run).returncode == 2
    open(os.path.join(fake, "share.json"), "w").write('{"permissions": []}')
    assert cli(run, fake, "private", run).returncode == 2


def test_apply_swaps_on_the_tab_and_records_new_images():
    run, fake = fake_run({"experiments": {"id": "DOC", "tab": TAB}}, live=f"<p>{live_img('kix.fig')}</p>\n<p>old</p>")
    figdir = tempfile.mkdtemp()
    fig, new = png(figdir, "fig.png", (380, 200)), png(figdir, "new.png", (100, 100), (1, 2, 3))
    os.makedirs(os.path.join(run, "docs", "experiments"))
    json.dump({"fig.png": {"object_id": "kix.fig", "sha256": "old"}},
              open(os.path.join(run, "docs", "experiments", "figs.json"), "w"))
    # gets 2 and 3 read the doc after the apply: the new image has an object id now
    after = f"<p>{live_img('kix.fig')}</p>\n<p>new</p>\n<p>{live_img('kix.new', 100, 100)}</p>"
    for n in (2, 3):
        open(os.path.join(fake, f"live.{n}.html"), "w").write(after)
    body = os.path.join(run, "b.html")
    open(body, "w").write(f'<p><img src="file://{fig}"></p>\n<p>new</p>\n<p><img src="file://{new}"></p>')
    r = cli(run, fake, "apply", run, "experiments", "--body", body)
    assert r.returncode == 0, r.stderr
    applies = [c for c in calls(fake) if c[:2] == ["google.docs", "apply"]]
    assert len(applies) == 2 and all(f"--tab-id={TAB}" in c and "--conflict-resolution=ours" not in c for c in applies)
    assert "--dry-run" in applies[0] and "--dry-run" not in applies[1]
    swap = [c for c in calls(fake) if c[:2] == ["google.docs", "replace-image"]]
    assert len(swap) == 1 and f"--tab-id={TAB}" in swap[0] and "--preserve-frame" in swap[0]
    assert "--image-id=kix.fig" in swap[0]
    figs = json.load(open(os.path.join(run, "docs", "experiments", "figs.json")))
    assert set(figs) == {fig, new}                          # the basename key moved to the image's path
    assert figs[fig]["sha256"] == sha(fig) and figs[new]["object_id"] == "kix.new"
    assert (figs[new]["w"], figs[new]["h"]) == (100, 100)
    assert open(os.path.join(run, "docs", "experiments", "live.html")).read() == after


def test_apply_frame_reset_needs_replies():
    live = f"<p>{live_img('kix.fig')}</p>\n" + ASIDE_IMG.format(cid="cimg")
    run, fake = fake_run({"experiments": {"id": "DOC", "tab": TAB}}, live=live)
    fig = png(tempfile.mkdtemp(), "fig.png", (200, 400))
    os.makedirs(os.path.join(run, "docs", "experiments"))
    json.dump({"fig.png": {"object_id": "kix.fig", "sha256": "old"}},
              open(os.path.join(run, "docs", "experiments", "figs.json"), "w"))
    body = os.path.join(run, "b.html")
    open(body, "w").write(f'<p><img src="file://{fig}"></p>')
    r = cli(run, fake, "apply", run, "experiments", "--body", body)
    assert r.returncode == 5 and json.loads(r.stdout) == {"frame_reset_needs_replies": {"kix.fig": ["cimg"]}}
    assert not any(c[:2] in (["google.docs", "apply"], ["google.docs", "replace-image"]) for c in calls(fake))
    r = cli(run, fake, "apply", run, "experiments", "--body", body, "--allow-reset", "kix.fig")
    assert r.returncode == 0, r.stderr
    swap = [c for c in calls(fake) if c[:2] == ["google.docs", "replace-image"]]
    assert len(swap) == 1 and "--preserve-frame" not in swap[0] and f"--tab-id={TAB}" in swap[0]
    figs = json.load(open(os.path.join(run, "docs", "experiments", "figs.json")))
    assert figs[fig]["object_id"] == "kix.fresh"
    assert "figure_frame_reset" in [e["kind"] for e in events(run)]


def test_apply_held_when_dry_run_orphans():
    run, fake = fake_run({"tracker": {"id": "DOC", "tab": "t.0"}},
                         live="<table><tr><td>#</td></tr><tr><td>1</td></tr></table><p>a</p>")
    open(os.path.join(fake, "orphan"), "w").close()
    body = os.path.join(run, "b.html")
    open(body, "w").write("<table><tr><td>#</td></tr><tr><td>1</td></tr></table><p>b</p>")
    r = cli(run, fake, "apply", run, "tracker", "--body", body, "--ours")
    assert r.returncode == 3, r.stderr
    applies = [c for c in calls(fake) if c[:2] == ["google.docs", "apply"]]
    assert len(applies) == 1 and "--dry-run" in applies[0] and "--conflict-resolution=ours" in applies[0]
    assert not any("--orphan-comments-ok" in c for c in calls(fake))
    held = [e for e in events(run) if e["kind"] == "apply_held"]
    assert len(held) == 1 and held[0]["apply_pass"] == "structure" and "orphans" in held[0]["event"]


def test_apply_records_each_swap_before_the_next():
    run, fake = fake_run({"experiments": {"id": "DOC", "tab": TAB}},
                         live=f"<p>{live_img('kix.a')}</p>\n<p>{live_img('kix.b')}</p>")
    d = tempfile.mkdtemp()
    a, b = png(d, "a.png", (200, 400)), png(d, "b.png", (200, 400))
    os.makedirs(os.path.join(run, "docs", "experiments"))
    json.dump({a: {"object_id": "kix.a", "sha256": "old"}, b: {"object_id": "kix.b", "sha256": "old"}},
              open(os.path.join(run, "docs", "experiments", "figs.json"), "w"))
    open(os.path.join(fake, "fail-kix.b"), "w").close()
    body = os.path.join(run, "b.html")
    open(body, "w").write(f'<p><img src="file://{a}"></p>\n<p><img src="file://{b}"></p>')
    r = cli(run, fake, "apply", run, "experiments", "--body", body)
    assert r.returncode == 1                                 # the second replace-image failed twice
    figs = json.load(open(os.path.join(run, "docs", "experiments", "figs.json")))
    assert figs[a]["object_id"] == "kix.fresh" and figs[b]["object_id"] == "kix.b"


def test_apply_exit_3_when_nothing_applied():
    # the cells pass has nothing to do and the structure pass holds (the commented paragraph has no counterpart)
    live = ("<table><tr><td>#</td></tr><tr><td>1</td><td>a</td></tr></table>\n<h2>Notes</h2>\n<p>keep this</p>\n"
            + ASIDE_TEXT.format(q="keep this").replace('data-tab-id="t.x"', 'data-tab-id="t.0"'))
    run, fake = fake_run({"tracker": {"id": "DOC", "tab": "t.0"}}, live=live)
    open(os.path.join(fake, "nochange"), "w").close()
    body = os.path.join(run, "b.html")
    open(body, "w").write("<table><tr><td>#</td></tr><tr><td>1</td><td>b</td></tr></table>")
    r = cli(run, fake, "apply", run, "tracker", "--body", body, "--ours")
    assert r.returncode == 3, r.stderr
    assert json.loads(r.stdout)["passes"] == ["nochange", "held: no counterpart for an open comment"]
    applies = [c for c in calls(fake) if c[:2] == ["google.docs", "apply"]]
    assert len(applies) == 1 and "--dry-run" in applies[0]    # the structure pass never ran
    assert [e["apply_pass"] for e in events(run) if e["kind"] == "apply_held"] == ["structure"]
    open(body, "w").write("<table><tr><td>#</td></tr><tr><td>1</td><td>b</td></tr></table>\n<h2>Notes</h2>\n"
                          "<p>keep this</p>")
    r = cli(run, fake, "apply", run, "tracker", "--body", body, "--ours")
    assert r.returncode == 0 and json.loads(r.stdout)["passes"] == ["nochange", "nochange"], r.stderr


def test_apply_authored_uses_get_base():
    run, fake = fake_run({"spec": {"id": "DOC", "tab": TAB}}, live="<p>live</p>")
    assert cli(run, fake, "apply", run, "spec", "--authored").returncode == 2        # no get yet
    r = cli(run, fake, "get", run, "spec")
    assert r.returncode == 0 and json.loads(r.stdout)["bytes"] == len("<p>live</p>"), r.stderr
    wd = os.path.join(run, "docs", "spec")
    open(os.path.join(wd, "live.html"), "w").write("<p>live, edited</p>")
    r = cli(run, fake, "apply", run, "spec", "--authored")
    assert r.returncode == 0, r.stderr
    applies = [c for c in calls(fake) if c[:2] == ["google.docs", "apply"]]
    assert len(applies) == 2 and all("--conflict-resolution=ours" not in c for c in applies)
    base = next(x for x in applies[1] if x.startswith("--base="))[len("--base=file://"):]
    assert base.startswith("/tmp/") and open(base).read() == "<p>live</p>"
    assert len([c for c in calls(fake) if c[:2] == ["google.docs", "get"]]) == 1      # no re-fetch
    assert cli(run, fake, "apply", run, "spec", "--authored", "--ours").returncode == 2


def test_size_limits():
    run, fake = fake_run({"a": {"tab": "t.a"}, "b": {"tab": "t.b"}, "c": {"id": "OTHER"}})
    for k, n in (("a", 250_000), ("b", 150_000), ("c", 900_000)):
        os.makedirs(os.path.join(run, "docs", k))
        open(os.path.join(run, "docs", k, "live.html"), "w").write("x" * n)
    r = cli(run, fake, "size", run)
    assert r.returncode == 0 and json.loads(r.stdout)["total"] == 400_000           # standalone doc not counted
    open(os.path.join(run, "docs", "b", "live.html"), "w").write("x" * 210_000)
    assert cli(run, fake, "size", run).returncode == 4                              # total over 450 KB
    open(os.path.join(run, "docs", "b", "live.html"), "w").write("x" * 310_000)
    open(os.path.join(run, "docs", "a", "live.html"), "w").write("x")
    assert cli(run, fake, "size", run).returncode == 4                              # one tab over 300 KB


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"all ok ({len(tests)} tests)")


if __name__ == "__main__":
    main()
