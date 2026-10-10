# scripts/tests/test_slop_text.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import slop_text as st


class T(unittest.TestCase):
    def test_normalize(self):
        raw = "# Title\n\n- See [the doc](https://x.y) for **details**.\nAsk @alice about D12345678.\n“Quoted” text — kept.\n```\ncode\n```\n| a | b |"
        out = st.normalize(raw)
        self.assertIn("See the doc for details.", out)
        self.assertIn("my_var_name", st.normalize("Set my_var_name to 3 before the run starts."))
        self.assertNotIn("alice", out)            # sentence with @mention dropped
        self.assertNotIn("code", out)
        self.assertNotIn("|", out)
        self.assertIn('"Quoted" text — kept.', out)
        self.assertNotIn("#", out)

    def test_wrapping_does_not_change_output(self):
        wrapped = "Intro line that wraps\nonto a second line.\n\n- Moves the cache warmup into the trainer so that the first\n  step no longer stalls on load\n- Second item here\n\n    indented_code = 1\n\n~~~\nmore code\n~~~\n\nUse `A` and `B` here."
        flat = "Intro line that wraps onto a second line.\n\n- Moves the cache warmup into the trainer so that the first step no longer stalls on load\n- Second item here\n\nUse `A` and `B` here."
        self.assertEqual(st.normalize(wrapped), st.normalize(flat))
        self.assertIn("first step no longer stalls on load.", st.normalize(wrapped))
        self.assertNotIn("code", st.normalize(wrapped))
        self.assertIn("Use A and B here.", st.normalize(wrapped))

    def test_titles_match_markdown_headings(self):
        plain = "Winding Down The Old Cache\nWe turned off the cache because it served stale rows.\n\n  ### New Launch Process\n**tl;dr **We launch on Mondays now."
        md = "# Winding Down The Old Cache\n\nWe turned off the cache because it served stale rows.\n\n### New Launch Process\n\ntl;dr We launch on Mondays now."
        self.assertEqual(st.normalize(plain), st.normalize(md))
        self.assertTrue(st.normalize(plain).startswith("Winding Down The Old Cache. We turned"))

    def test_cut_words(self):
        t = "One two three four. Five six seven. Eight nine ten eleven twelve."
        self.assertEqual(st.cut_words(t, 8), "One two three four. Five six seven.")
        self.assertEqual(st.cut_words(t, 100), t)

    def test_sentences_min_words(self):
        self.assertEqual(st.sentences("Too short. This sentence has six words exactly."), ["This sentence has six words exactly."])

    def test_near_verbatim(self):
        self.assertTrue(st.near_verbatim("The cache was turned off today.", ["The cache was turned off today!"]))
        self.assertFalse(st.near_verbatim("We removed the stale cache.", ["Lunch is at noon in building 20."]))

    def test_dedupe(self):
        a = "the quick brown fox jumps over the lazy dog near the river bank today"
        self.assertEqual(st.dedupe([a, a + " again", "completely different words about compilers and linkers here now"]), [0, 2])


if __name__ == "__main__":
    unittest.main()
