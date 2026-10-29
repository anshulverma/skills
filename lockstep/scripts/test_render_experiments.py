#!/usr/bin/env python3
"""Checks for render_experiments.py and figures.py. Run: ~/.cache/humanize-venv/bin/python test_render_experiments.py (or pytest)"""
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figures  # noqa: E402
import render_experiments as rx  # noqa: E402

NOW = datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc)
ISO = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
H = lambda h: ISO(NOW - timedelta(hours=h))  # noqa: E731


def job(n, state, study=None, verdict="", kind="train", start=10, end=None, **kw):
    return {"n": n, "name": f"job-{n}", "url": f"https://mast/{n}", "kind": kind, "study": study,
            "hypothesis": f"hyp {n}", "launched_utc": H(start + 0.2), "started_utc": H(start),
            "ended_utc": H(end) if end is not None else None, "state": state, "attempts": 1, "gpus": 8,
            "cost_gpu_h": 8.0, "readout": f"readout {n}", "verdict": verdict, **kw}


def make_run(tmp, learnings=None, held_text=True):
    run = str(tmp)
    pipe = {"layout": "tabs", "owner_tz": "America/Los_Angeles", "tracker_doc": "DOC", "pageless": True,
            "docs": {"experiments": {"id": "DOC", "tab": "t.e", "title": "Experiments"},
                     "experiment_log": {"id": "DOC", "tab": "t.l", "title": "Experiment log"},
                     "studies": {"id": "DOC", "tab": "t.s", "title": "Studies"},
                     "study-s1": {"id": "DOC", "tab": "t.s1", "title": "Study: one"}}}
    studies = {"s1": {"title": "Study one", "question": "Does X help?", "status": "concluded", "verdict": "negative",
                      "short_answer": "No", "learnings": ["X does not help", "Noise is 0.01"],
                      "opened_utc": H(100), "concluded_utc": H(5)},
               "s2": {"title": "Study two", "question": "Does Y help?", "status": "running", "opened_utc": H(50)}}
    for i in range(3, 10):   # reading-only concluded studies: the Learnings fallback must cap at 5
        studies[f"r{i}"] = {"title": f"Read {i}", "question": "q", "status": "concluded", "short_answer": f"ans {i}",
                            "opened_utc": H(60 - i), "concluded_utc": H(40 - i)}
    jobs = [job(1, "done", "s1", "worse", start=100, end=90), job(2, "done", "s1", "worse", start=20, end=12),
            job(3, "failed", verdict="crash at step 0", kind="eval", start=30, end=29),
            job(4, "running", "s2", start=6, eta_utc=ISO(NOW + timedelta(hours=3))),
            job(5, "done", verdict="better", start=8, end=2), job(6, "queued", start=1, kind="eval",
                                                                  started_utc=None)]
    st = {"jobs": jobs, "studies": studies, "learnings": learnings or [], "bottom_line": "Keep the default.",
          "primary_metric": "auc", "archive": [{"paste": "P99", "through_n": 1}], "sweep_stopped": None}
    os.makedirs(os.path.join(run, "experiments"))
    os.makedirs(os.path.join(run, "studies", "s1", "figs"))
    json.dump(pipe, open(os.path.join(run, "pipeline.json"), "w"))
    json.dump(st, open(os.path.join(run, "experiments", "state.json"), "w"))
    open(os.path.join(run, "studies", "s1", "report.md"), "w").write(
        "# Study one\n\nStatus: concluded\n\n## 2. Question\n\nDoes X help?\n\n## 4. Design\n\n"
        "| Arm | Change |\n|---|---|\n| a | X on |\n\n### Decision rule\n\nPaired CI above 0.\n\n## 5. Cost\n\n16 GPU-h\n\n"
        "## 9. Results\n\n**Negative.** X lowered AUC by 0.002.\n\n## 10. Follow-ups\n\nSECRET-FOLLOWUP\n")
    figures.delta_band({"a": [0.501, 0.503], "b": 0.49}, 0.5, 0.002, os.path.join(run, "studies", "s1", "figs", "summary.png"),
                       threshold=0.001)
    held = {"experiments": ["readout 5"] if held_text else []}
    json.dump(held, open(os.path.join(run, "held.json"), "w"))
    return run


def cli(run, out, *extra):
    return subprocess.run([sys.executable, os.path.join(HERE, "render_experiments.py"), run, out, "--now", ISO(NOW), *extra],
                          capture_output=True, text=True)


def first_cells(html):
    return [int(x) for x in re.findall(r"<tr><td>(\d+)</td>", html)]


def test_placement_held_archived_and_pointer(tmp_path):
    run = make_run(tmp_path / "run")
    out = rx.render(run, NOW, json.load(open(os.path.join(run, "held.json"))))
    assert first_cells(out["experiments"]) == [4, 5, 6]          # 5 is concluded but held by an open quote
    assert first_cells(out["experiment_log"]) == [3, 2]           # newest first; 1 is archived
    assert "Older rows: paste P99" in out["experiment_log"]
    assert "?tab=t.l" in out["experiments"]
    unheld = rx.render(run, NOW, {})
    assert first_cells(unheld["experiments"]) == [4, 6]
    assert first_cells(unheld["experiment_log"]) == [5, 3, 2]


def test_signal_cell_and_dates(tmp_path):
    run = make_run(tmp_path / "run")
    html = rx.render(run, NOW, {})["experiments"]
    r4 = re.search(r"<tr><td>4</td>.*?</tr>", html).group(0)
    assert "ETA 10-29 16:00" in r4 and "8.0 GPU-h" in r4 and "running" in r4   # PDT is UTC-7
    assert "ran 6h 00m" in r4 and "train, study s2" in r4 and 'href="https://mast/4"' in r4
    assert "Date (PDT)" in html


def test_learnings_cap_and_fallback(tmp_path):
    run = make_run(tmp_path / "a")
    html = rx.render(run, NOW, {})["experiments"]
    cell = re.search(r"<b>Learnings</b></td><td>(.*?)</td>", html).group(1)
    assert cell.count("•") == 5 and "<b>Study one</b>: No" in cell and "ans 6" in cell and "ans 5" not in cell  # newest 5
    run = make_run(tmp_path / "b", learnings=[f"L{i}" for i in range(7)])
    cell = re.search(r"<b>Learnings</b></td><td>(.*?)</td>", rx.render(run, NOW, {})["experiments"]).group(1)
    assert cell.count("•") == 5 and "L4" in cell and "L5" not in cell


def test_studies_tab(tmp_path):
    run = make_run(tmp_path / "run")
    html = rx.render(run, NOW, {})["studies"]
    assert "Paired CI above 0." in html and "<td>X on</td>" in html          # Design, subsections included
    assert "<b>Negative.</b> X lowered AUC" in html and "SECRET-FOLLOWUP" not in html and "16 GPU-h" not in html
    assert f'src="file://{run}/studies/s1/figs/summary.png"' in html
    assert 'href="https://docs.google.com/document/d/DOC/edit?tab=t.s1">Learnings</a>' in html
    assert "<li>X does not help</li>" in html and "2, 16.0 GPU-h" in html
    assert "Jobs: 2 done (16.0 GPU-h)" in html


def test_cli_deterministic_and_timeline_png(tmp_path):
    run = make_run(tmp_path / "run")
    outs = []
    for k in range(2):
        out = str(tmp_path / f"out{k}")
        r = cli(run, out, "--held-json", os.path.join(run, "held.json"))
        assert r.returncode == 0, r.stderr
        pngs = sorted(glob.glob(os.path.join(run, "experiments", "fig", "*.png")))
        outs.append(({f: open(os.path.join(out, f)).read() for f in sorted(os.listdir(out))},
                     {p: open(p, "rb").read() for p in pngs}))
    assert outs[0] == outs[1]
    html, pngs = outs[0]
    assert set(html) == {"experiments.html", "experiment_log.html", "studies.html"}
    names = {os.path.basename(p) for p in pngs}
    assert "timeline.png" in names and any(n.startswith("timeline-2026") for n in names)   # a completed 48h block
    assert all(open(p, "rb").read(4) == b"\x89PNG" for p in pngs)
    assert "<h2>Timeline</h2>" in html["experiment_log.html"]


def test_missing_state_is_silent(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "pipeline.json").write_text("{}")
    r = cli(str(run), str(tmp_path / "out"))
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
    assert not (tmp_path / "out").exists() or not os.listdir(tmp_path / "out")


def test_only_studies_without_jobs(tmp_path):
    run = make_run(tmp_path / "run")
    p = os.path.join(run, "experiments", "state.json")
    st = json.load(open(p))
    st.update(jobs=[], archive=[])
    json.dump(st, open(p, "w"))
    assert set(rx.render(run, NOW, {})) == {"studies"}


def test_pack_cap_and_unknown_state():
    t = lambda h: NOW + timedelta(hours=h)  # noqa: E731
    slots, n = rx.pack([(t(0), t(2)), (t(1), t(3)), (t(2), t(4))])
    assert slots == [(0, False), (1, False), (0, False)] and n == 2
    slots, n = rx.pack([(t(0), t(5))] * 4, cap=2)
    assert n == 2 and slots[-1] == (1, True)
    try:
        rx.shown({"name": "x", "state": "weird"})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown state must fail")
    assert rx.shown({"state": "failed", "stopped_done": 1}) == "stopped"


def test_figures_size_and_dot(tmp_path):
    assert figures.size(True) == (13.0, 7.5) and figures.size(False)[0] == 6.5
    png = figures.dot("digraph { a -> b }", str(tmp_path / "g.png"))
    assert open(png, "rb").read(4) == b"\x89PNG" and os.path.exists(tmp_path / "g.dot")


def main():
    """No pytest in the humanize venv: run every test_* here, handing tmp_path-taking tests a fresh temp dir."""
    import inspect
    import pathlib
    import tempfile
    for name, fn in sorted((k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)):
        if "tmp_path" in inspect.signature(fn).parameters:
            with tempfile.TemporaryDirectory() as d:
                fn(pathlib.Path(d))
        else:
            fn()
        print("ok", name)
    print("all ok")


if __name__ == "__main__":
    main()
