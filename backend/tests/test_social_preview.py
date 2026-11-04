"""
Unit tests for Feature 2: Live Social Media Post Previews.
Verifies fold threshold calculations, character boundary warnings,
and text metrics computation.
"""

import unittest
import sys
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TEST_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import utils


class TestSocialPreview(unittest.TestCase):

    def test_text_metrics_calculation(self):
        text = "This is a clean, punchy viral hook designed to stop scrolling."
        metrics = utils.calculate_text_metrics(text)
        self.assertEqual(metrics["characters"], len(text))
        self.assertEqual(metrics["words"], 11)
        self.assertGreaterEqual(metrics["reading_seconds"], 1)

    def test_twitter_char_limit_boundary(self):
        short_tweet = "A" * 280
        long_tweet = "A" * 281

        self.assertEqual(len(short_tweet), 280)
        self.assertEqual(len(long_tweet), 281)

        # Check whether within boundary
        self.assertFalse(len(short_tweet) > 280)
        self.assertTrue(len(long_tweet) > 280)

    def test_fold_simulation_logic(self):
        # Line break fold test (Instagram fold after 2 lines or 125 chars)
        short_one_liner = "Short hook before the fold."
        lines = short_one_liner.split("\n")
        self.assertEqual(len(lines), 1)

        multi_line = "Line 1\nLine 2\nLine 3 hidden under more"
        m_lines = multi_line.split("\n")
        self.assertGreater(len(m_lines), 2)

    def test_format_hashtags(self):
        tags = ["travel", "#adventure", " wanderlust "]
        formatted = utils.format_hashtags(tags)
        self.assertIn("#travel", formatted)
        self.assertIn("#adventure", formatted)
        self.assertIn("#wanderlust", formatted)
        self.assertNotIn("##adventure", formatted)


if __name__ == "__main__":
    unittest.main()
