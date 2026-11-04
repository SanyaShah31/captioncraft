"""
Unit tests for Feature 4: One-Click Multi-Platform Caption Generator.
Verifies prompt construction, platform-native outputs, character count tracking,
and multi-platform data handling.
"""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TEST_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import prompt_templates
import ai_service
import utils
import pandas as pd


class TestMultiPlatform(unittest.TestCase):

    def test_build_multi_platform_prompt(self):
        prompt = prompt_templates.build_multi_platform_prompt(
            topic="Launching our AI caption creator toolkit",
            platforms=["Instagram", "Twitter / X", "LinkedIn"],
            tone="Professional",
            length="Medium",
            include_hashtags=True,
            hashtag_count=5
        )
        self.assertIn("Launching our AI caption creator toolkit", prompt)
        self.assertIn("Instagram", prompt)
        self.assertIn("Twitter / X", prompt)
        self.assertIn("LinkedIn", prompt)
        self.assertIn("Twitter / X MUST strictly be under 280 characters", prompt)

    @patch("ai_service._call_gemini")
    def test_generate_multi_platform_captions_success(self, mock_gemini):
        mock_response = """{
          "platforms": {
            "Instagram": {
              "caption": "Aesthetic caption for IG with clean spacing.",
              "hook": "Stop scrolling.",
              "hashtags": ["igcreator", "growth"],
              "emojis": ["✨"],
              "cta": "Save this for later!",
              "char_count": 48,
              "platform_tip": "Hook placed before fold"
            },
            "Twitter / X": {
              "caption": "Punchy tweet under 280 characters. Retweet if you agree.",
              "hook": "Big update today.",
              "hashtags": ["tech"],
              "emojis": ["⚡"],
              "cta": "RT if you agree",
              "char_count": 56,
              "platform_tip": "Concise tweet"
            }
          }
        }"""
        mock_gemini.return_value = (True, mock_response, "gemini-3.5-flash")

        success, results, err = ai_service.generate_multi_platform_captions(
            topic="Product launch",
            platforms=["Instagram", "Twitter / X"],
            tone="Professional",
            api_key="test_dummy_key"
        )

        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertIn("Instagram", results)
        self.assertIn("Twitter / X", results)
        self.assertEqual(results["Instagram"]["hook"], "Stop scrolling.")
        self.assertEqual(results["Twitter / X"]["char_count"], len(results["Twitter / X"]["caption"]))

    def test_generate_multi_platform_empty_topic(self):
        success, results, err = ai_service.generate_multi_platform_captions(
            topic="",
            platforms=["Instagram"],
            tone="Professional"
        )
        self.assertFalse(success)
        self.assertIn("provide a topic", err.lower())

    def test_generate_multi_platform_empty_platforms(self):
        success, results, err = ai_service.generate_multi_platform_captions(
            topic="Valid topic",
            platforms=[],
            tone="Professional"
        )
        self.assertFalse(success)
        self.assertIn("select at least one", err.lower())

    def test_export_multi_platform_to_df_all_five_platforms(self):
        """Regression test: verifies DataFrame & CSV export for all 5 platforms."""
        mock_mp_data = {
            "Instagram": {
                "id": "ig_1",
                "caption": "Aesthetic visual caption for Instagram.",
                "hook": "Stop scrolling and take a breath.",
                "hashtags": ["mindset", "growth"],
                "char_count": 38,
                "platform_tip": "Keep hook above fold"
            },
            "X (Twitter)": {
                "id": "tw_1",
                "caption": "Concise tweet under 280 characters.",
                "hook": "Here's what nobody tells you:",
                "hashtags": ["tech", "startup"],
                "char_count": 35,
                "platform_tip": "Thread continuation hook"
            },
            "LinkedIn": {
                "id": "li_1",
                "caption": "Thought leadership narrative on leadership.",
                "hook": "I used to think grit was enough.",
                "hashtags": ["leadership", "careers"],
                "char_count": 43,
                "platform_tip": "Encourage professional comments"
            },
            "TikTok": {
                "id": "tt_1",
                "caption": "Fast-paced, high energy caption.",
                "hook": "Wait till the end...",
                "hashtags": ["fyp", "viral"],
                "char_count": 32,
                "platform_tip": "First 3 seconds are critical"
            },
            "Threads": {
                "id": "th_1",
                "caption": "Conversational, casual take for Threads.",
                "hook": "Hot take on modern workflows:",
                "hashtags": ["productivity"],
                "char_count": 40,
                "platform_tip": "Reply with your thoughts"
            }
        }

        df = utils.export_multi_platform_to_df(mock_mp_data)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)
        expected_cols = ["Platform", "Caption", "Hook", "Hashtags", "Character_Count", "Platform_Tip"]
        self.assertEqual(list(df.columns), expected_cols)

        # Verify CSV export byte conversion
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        self.assertGreater(len(csv_bytes), 50)
        self.assertIn(b"Instagram", csv_bytes)
        self.assertIn(b"TikTok", csv_bytes)
        self.assertIn(b"LinkedIn", csv_bytes)

    def test_export_multi_platform_to_df_empty_and_graceful_handling(self):
        """Verifies empty dict, None, and partial rows do not raise NameError or KeyError."""
        # Empty dict
        df_empty = utils.export_multi_platform_to_df({})
        self.assertIsInstance(df_empty, pd.DataFrame)
        self.assertEqual(len(df_empty), 0)

        # None input
        df_none = utils.export_multi_platform_to_df(None)
        self.assertIsInstance(df_none, pd.DataFrame)
        self.assertEqual(len(df_none), 0)

        # Partial row missing fields
        partial_data = {
            "Instagram": {"caption": "Just a caption"}
        }
        df_partial = utils.export_multi_platform_to_df(partial_data)
        self.assertEqual(len(df_partial), 1)
        self.assertEqual(df_partial.iloc[0]["Caption"], "Just a caption")
        self.assertEqual(df_partial.iloc[0]["Hook"], "")


if __name__ == "__main__":
    unittest.main()
