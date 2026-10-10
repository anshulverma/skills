# scripts/tests/test_lexical.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import lexical


class T(unittest.TestCase):
    def test_keys_and_rates(self):
        f = lexical.features("It is not just a tool, but a revolution. She took a deep breath.")
        for k in ("lex-vale-any", "lex-antislop-regex", "lex-antislop-phrase", "lex-slopscore-word", "lex-slopscore-trigram", "lex-humanize-tells"):
            self.assertIn(k, f)
        self.assertGreater(f["lex-antislop-phrase"], 0)     # "took a deep breath"
        self.assertGreater(f["lex-vale-any"], 0)            # NegParallel fires on "not just ..., but"

    def test_plain_text_is_zero(self):
        f = lexical.features("The build uses three workers and finishes in ten minutes.")
        self.assertEqual(f["lex-antislop-phrase"], 0)


if __name__ == "__main__":
    unittest.main()
