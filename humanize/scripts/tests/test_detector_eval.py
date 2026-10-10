# scripts/tests/test_detector_eval.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import detector_eval as de


class T(unittest.TestCase):
    def test_auc(self):
        self.assertEqual(de.auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertEqual(de.auc([0, 1], [0.5, 0.5]), 0.5)

    def test_tpr_needs_negatives(self):
        self.assertIsNone(de.tpr_at_fpr([0] * 50 + [1] * 50, list(range(100)), 0.01))
        self.assertEqual(de.tpr_at_fpr([0] * 100 + [1] * 100, list(range(200)), 0.05), 1.0)

    def test_threshold_and_ci(self):
        y = [0] * 50 + [1] * 50; s = [i / 100 for i in range(100)]
        self.assertAlmostEqual(de.best_f1_threshold(y, s), 0.5, delta=0.02)
        lo, hi = de.bootstrap_auc_ci(y, s, list(range(100)), n=200)
        self.assertLessEqual(lo, 1.0); self.assertGreaterEqual(hi, lo)


if __name__ == "__main__":
    unittest.main()
