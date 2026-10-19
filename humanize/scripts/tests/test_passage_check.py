# scripts/tests/test_passage_check.py
import contextlib, io, json, math, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import passage_check as pc


def para(n, word="word"):
    return " ".join([word] * (n - 1)) + " end."


class T(unittest.TestCase):
    def test_splitter(self):
        doc = "\n\n".join([
            "---\ntitle: x\n---", "<!-- humanize-context\ntype: report\n-->", "# A",
            para(30, "alpha"), para(40, "beta"),            # merged: 70 words
            "| a | b |\n|---|---|", "```\ncode " + para(80) + "\n```", "![fig](f.png)", "*Figure 1. " + para(70) + "*",
            "# B", para(20, "gamma"),                       # alone under its heading: skipped
            "# C", " ".join(para(50, "delta") for _ in range(10)),  # 500 words: cut at a sentence boundary
            "## Appendix", para(100, "omega")])
        out, skipped = pc.passages(doc)
        self.assertEqual([len(p.split()) for p in out], [70, 400, 100])
        self.assertTrue(out[0].startswith("alpha") and "beta" in out[0])
        self.assertEqual(skipped, 1)
        self.assertFalse(any(w in " ".join(out) for w in ("gamma", "omega", "code", "Figure", "title", "humanize")))

    def test_probability_and_flags(self):
        model = {"name": "fake", "version": "0", "features": ["lex-humanize-tells"], "mean": [1.0], "scale": [2.0],
                 "coef": [3.0], "intercept": -1.0, "threshold": 0.5}
        self.assertAlmostEqual(pc.probability(model, {"lex-humanize-tells": 5.0}), 1 / (1 + math.exp(-5.0)))
        with tempfile.TemporaryDirectory() as d:
            json.dump(model, open(f"{d}/m.json", "w"))
            open(f"{d}/doc.md", "w").write("# A\n\n" + para(70, "plain") + "\n\n# B\n\n" + para(70, "other"))
            with mock.patch("detectors.score", lambda f, texts, md: [5.0, -5.0][:len(texts)]), \
                    mock.patch.object(sys, "argv", ["pc", f"{d}/doc.md", "--model", f"{d}/m.json", "--json"]), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                pc.main()
        r = json.loads(out.getvalue())
        self.assertEqual([p["flag"] for p in r["passages"]], [True, False])
        self.assertEqual((r["flagged"], r["scored"]), (1, 2))

    def test_missing_model_names_both_paths(self):
        with mock.patch.dict(os.environ, {"HUMANIZE_SLOP_MODEL": "/nope.json"}), mock.patch.object(sys, "argv", ["pc", "x.md"]), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            pc.main()
        self.assertIn("/nope.json", err.getvalue())
        self.assertIn(pc.DEFAULT_MODEL, err.getvalue())


if __name__ == "__main__":
    unittest.main()
