"""
Unit tests for Feature 3: AI Viral Caption Analyzer & Improver.
Verifies prompt generation, 5-category scoring normalization,
bounds validation, and one-click improvement directives.
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


class TestViralAnalyzer(unittest.TestCase):

    def test_build_viral_analyzer_prompt(self):
        prompt = prompt_templates.build_viral_analyzer_prompt(
            caption="Stop scrolling. This 1 mindset shift changed everything.",
            platform="Instagram",
            tone="Inspirational"
        )
        self.assertIn("Stop scrolling. This 1 mindset shift changed everything.", prompt)
        self.assertIn("Hook Strength (Max 25 points)", prompt)
        self.assertIn("Readability (Max 20 points)", prompt)
        self.assertIn("Emotional Appeal (Max 20 points)", prompt)
        self.assertIn("CTA Effectiveness (Max 15 points)", prompt)
        self.assertIn("Platform Relevance (Max 20 points)", prompt)

    def test_build_caption_improvement_prompt_actions(self):
        for act in ["engaging", "stronger_hook", "shorter", "better_cta", "platform_optimize"]:
            prompt = prompt_templates.build_caption_improvement_prompt(
                caption="Sample caption text.",
                action=act,
                platform="LinkedIn",
                tone="Professional"
            )
            self.assertIn("Sample caption text.", prompt)
            self.assertIn("LinkedIn", prompt)

    @patch("ai_service._call_gemini")
    def test_analyze_viral_caption_success_and_normalization(self, mock_gemini):
        mock_response = """{
          "overall_score": 88,
          "scores": {
            "hook_strength": {"score": 23, "max": 25, "reason": "Excellent curiosity gap."},
            "readability": {"score": 19, "max": 20, "reason": "Clean spacing."},
            "emotional_appeal": {"score": 17, "max": 20, "reason": "Strong empathy."},
            "cta_effectiveness": {"score": 14, "max": 15, "reason": "Direct question."},
            "platform_relevance": {"score": 18, "max": 20, "reason": "Fits Instagram norms."}
          },
          "verdict": "Exceptional viral potential.",
          "strengths": ["Bold opening", "Punchy rhythm"],
          "weaknesses": ["Hashtags slightly generic"],
          "suggestions": ["Add 2 niche tags"]
        }"""
        mock_gemini.return_value = (True, mock_response, "gemini-3.8-flash")

        success, result, err = ai_service.analyze_viral_caption(
            caption="Stop scrolling. This 1 mindset shift changed everything.",
            platform="Instagram",
            tone="Inspirational",
            api_key="test_dummy_key"
        )

        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertEqual(result["overall_score"], 88)
        self.assertEqual(result["scores"]["hook_strength"]["score"], 23)
        self.assertEqual(result["scores"]["readability"]["score"], 19)
        self.assertEqual(len(result["strengths"]), 2)

    @patch("ai_service._call_gemini")
    def test_improve_caption_success(self, mock_gemini):
        mock_response = """{
          "original_caption": "Basic caption.",
          "improved_caption": "Stop scrolling right now. This is why 99% fail before starting.",
          "hook": "Stop scrolling right now.",
          "hashtags": ["mindset", "success"],
          "emojis": ["🔥"],
          "cta": "Drop a 🔥 if you agree.",
          "improvement_summary": "Replaced weak opening with high-CTR hook.",
          "changes_made": ["Sharpened hook", "Added active CTA"]
        }"""
        mock_gemini.return_value = (True, mock_response, "gemini-3.8-flash")

        success, result, err = ai_service.improve_caption(
            caption="Basic caption.",
            action="stronger_hook",
            platform="Instagram",
            tone="Inspirational",
            api_key="test_dummy_key"
        )

        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertEqual(result["hook"], "Stop scrolling right now.")
        self.assertIn("99% fail", result["improved_caption"])
        self.assertEqual(result["action"], "stronger_hook")

    def test_analyze_empty_caption_validation(self):
        success, result, err = ai_service.analyze_viral_caption("")
        self.assertFalse(success)
        self.assertIn("provide a caption", err.lower())


if __name__ == "__main__":
    unittest.main()
