# scripts/tests/test_metrics.py
import importlib.util, json, os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import metrics

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "metrics.py")
HAS_MPL = importlib.util.find_spec("matplotlib") is not None


def judge(**kw):
    j = {"scope": "full", "material_changes": 0, "minor_changes": 0, "regions_changed": [],
         "gaps": {"blocks_execution": 0, "inconsistency": 0, "cosmetic": 0},
         "tasks_read": 10, "tasks_total": 10, "anchors_checked": 20, "anchors_wrong": 0,
         "executable_steps": 5, "run_steps": 5, "spec_items_mapped": 8, "spec_items_total": 8,
         "gaps_in_last_changed_text": 0, "self_report_matches": True}
    j.update(kw)
    return j


def run_of(*judges, words=1000):
    rows = []
    for n, j in enumerate(judges, 1):
        rows.append(metrics.make_row(j, n, words, 0, 0, rows))
    return rows


class T(unittest.TestCase):
    def test_clean_full_judge_converges(self):
        self.assertEqual(metrics.verdict(run_of(judge()), 6), "CONVERGED")

    def test_scoped_judge_cannot_converge(self):
        self.assertEqual(metrics.verdict(run_of(judge(scope="scoped", tasks_read=1)), 6), "CONTINUE")
        # Declaring "full" while reading only part of the plan is not full coverage either.
        self.assertEqual(metrics.verdict(run_of(judge(tasks_read=9)), 6), "CONTINUE")

    def test_failing_gate_blocks_convergence(self):
        self.assertEqual(metrics.verdict(run_of(judge(executable_steps=4)), 6), "CONTINUE")
        self.assertEqual(metrics.verdict(run_of(judge(spec_items_mapped=7)), 6), "CONTINUE")
        # A spec-only run has no plan gates.
        self.assertEqual(metrics.verdict(run_of(judge(executable_steps=None, run_steps=None,
                                                      spec_items_mapped=None, spec_items_total=None)), 6), "CONVERGED")

    def test_unresolved_marker_blocks_convergence(self):
        self.assertEqual(metrics.verdict([metrics.make_row(judge(), 1, 1000, 1, 0, [])], 6), "CONTINUE")

    def test_plateau_counts_full_coverage_judgments_only(self):
        g = lambda n, **kw: judge(gaps={"blocks_execution": n, "inconsistency": 0, "cosmetic": 0}, **kw)
        self.assertEqual(metrics.verdict(run_of(g(2), g(2), g(2)), 20), "PLATEAU")
        self.assertEqual(metrics.verdict(run_of(g(1), g(1), g(3)), 20), "PLATEAU")
        self.assertEqual(metrics.verdict(run_of(g(3), g(2), g(2)), 20), "CONTINUE")
        # A scoped 0 in between does not hide a flat gap count.
        scoped0 = judge(scope="scoped", tasks_read=1)
        self.assertEqual(metrics.verdict(run_of(g(1), scoped0, g(1), scoped0, g(1)), 20), "PLATEAU")

    def test_oscillation(self):
        a, b = judge(material_changes=1, regions_changed=["plan:Task 3"]), judge(material_changes=1, regions_changed=["spec:retry"])
        self.assertEqual(metrics.verdict(run_of(a, b, a), 20), "OSCILLATION")

    def test_cap(self):
        busy = judge(material_changes=2, regions_changed=["x"])
        rows = run_of(busy, judge(material_changes=1, regions_changed=["y"]), judge(material_changes=3, regions_changed=["z"]))
        self.assertEqual(metrics.verdict(rows, 3), "CAP")
        self.assertEqual(metrics.verdict(rows, 4), "CONTINUE")

    def test_regression_rate(self):
        rows = run_of(judge(gaps={"blocks_execution": 2, "inconsistency": 2, "cosmetic": 0}),
                      judge(gaps={"blocks_execution": 1, "inconsistency": 0, "cosmetic": 0}, gaps_in_last_changed_text=1),
                      judge(gaps_in_last_changed_text=0))
        self.assertIsNone(rows[0]["regression_rate"])
        self.assertEqual(rows[1]["regression_rate"], 0.25)   # 1 new gap in changed text / 4 handed in
        self.assertEqual(rows[2]["regression_rate"], 0.0)

    def test_length_vs_pass_1(self):
        rows = []
        for n, w in ((1, 1000), (2, 1200), (3, 1400)):
            rows.append(metrics.make_row(judge(), n, w, 0, 0, rows))
        self.assertAlmostEqual(rows[2]["length_ratio"], 1.4)
        status = {t[0]: t[3] for t in metrics.table(rows, metrics.TARGETS)}
        self.assertEqual(status["length vs pass 1"], "FAIL")
        loose = dict(metrics.TARGETS, **metrics.parse_targets("Length vs pass 1 <= 1.5"))
        self.assertEqual({t[0]: t[3] for t in metrics.table(rows, loose)}["length vs pass 1"], "ok")

    def test_cli_logs_and_rejudge_replaces(self):
        with tempfile.TemporaryDirectory() as d:
            p = lambda name: os.path.join(d, name)
            open(p("plan.md"), "w").write("Task 1: run it. " * 50)
            hist, csvf = p("history.jsonl"), p("conv.csv")

            def call(n, j, *extra):
                open(p("judge.md"), "w").write("### Verdict: X\n\n### Metrics\n```json\n" + json.dumps(j) + "\n```\n")
                return subprocess.run([sys.executable, SCRIPT, "--judge", p("judge.md"), "--artifact", p("plan.md"),
                                       "--pass", str(n), "--history", hist, "--csv", csvf, "--max-passes", "6", *extra],
                                      capture_output=True, text=True)
            r = call(1, judge(material_changes=3, regions_changed=["a"]))
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertTrue(r.stdout.strip().endswith("CONTINUE"))
            r = call(2, judge(scope="scoped", tasks_read=2))
            self.assertIn("re-judge this pass with a full-coverage judge", r.stdout)
            self.assertEqual(r.returncode, 1)
            r = call(2, judge())
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertTrue(r.stdout.strip().endswith("CONVERGED"))
            self.assertEqual([x["pass"] for x in metrics.load_run(hist)], [1, 2])
            lines = open(csvf).read().splitlines()
            self.assertEqual(lines[0], ",".join(metrics.CSV_COLUMNS))
            self.assertEqual([ln.split(",")[0] for ln in lines[1:]], ["1", "2"])
            self.assertNotEqual(call(3, judge(), "--targets", "fact retention >= 0.5").returncode, 0)
            # A restart at pass 1 (sdd's plan stage) is a new run with its own length baseline.
            open(p("plan.md"), "w").write("word " * 2000)
            call(1, judge(material_changes=1))
            self.assertEqual([x["pass"] for x in metrics.load_run(hist)], [1])
            self.assertEqual(metrics.load_run(hist)[0]["length_ratio"], 1.0)


    @unittest.skipUnless(HAS_MPL, "needs matplotlib (run with ~/.cache/humanize-venv/bin/python)")
    def test_progress_chart_and_upload(self):
        with tempfile.TemporaryDirectory() as d:
            p = lambda name: os.path.join(d, name)
            open(p("plan.md"), "w").write("Task 1: run it. " * 50)
            hist, png = p("plan-history.jsonl"), p("plan-history-progress.png")
            os.mkdir(p("bin"))

            def stub(body):
                open(p("bin/meta"), "w").write("#!/bin/sh\n" + body + "\n")
                os.chmod(p("bin/meta"), 0o755)

            def call(n, j, *extra):
                open(p("judge.md"), "w").write("```json\n" + json.dumps(j) + "\n```\n")
                env = dict(os.environ, PATH=p("bin") + os.pathsep + os.environ["PATH"])
                return subprocess.run([sys.executable, SCRIPT, "--judge", p("judge.md"), "--artifact", p("plan.md"),
                                       "--pass", str(n), "--history", hist, "--max-passes", "6", *extra],
                                      capture_output=True, text=True, env=env)
            r = call(1, judge(material_changes=2, regions_changed=["a"]))
            self.assertTrue(os.path.getsize(png) > 0, r.stdout + r.stderr)
            self.assertNotIn("chart_url", metrics.load_run(hist)[-1])
            self.assertEqual(metrics.load_run(hist)[-1]["verdict"], "CONTINUE")
            stub('echo "Uploaded: https://pxl.cl/abC12"')
            r = call(2, judge(scope="scoped", tasks_read=3), "--upload")
            self.assertIn("https://pxl.cl/abC12", r.stdout)
            self.assertEqual(metrics.load_run(hist)[-1]["chart_url"], "https://pxl.cl/abC12")
            stub('echo "permission denied" >&2; exit 3')
            r = call(3, judge(), "--upload")
            self.assertIn("upload failed", r.stdout)
            self.assertEqual((r.returncode, r.stdout.strip().splitlines()[-1]), (0, "CONVERGED"))
            last = metrics.load_run(hist)[-1]
            self.assertEqual((last["verdict"], last.get("chart_url")), ("CONVERGED", None))


if __name__ == "__main__":
    unittest.main()
