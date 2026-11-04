"""
Unit tests for Feature 1: Emoji-to-Caption Generator & State Flow.
Verifies prompt construction, emoji generation, emoji-only mode directive,
and exact emoji sequence propagation without stale or default caching.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
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


class TestEmojiCaption(unittest.TestCase):

    def test_build_emoji_to_caption_prompt_standard(self):
        prompt = prompt_templates.build_emoji_to_caption_prompt(
            emojis="✨ ☕ 📚",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            emoji_only_mode=False,
            user_context="Cozy rainy morning reading",
            include_hashtags=True,
            hashtag_count=5
        )
        self.assertIn("✨ ☕ 📚", prompt)
        self.assertIn("Instagram", prompt)
        self.assertIn("Aesthetic", prompt)
        self.assertIn("Include 5 hashtags", prompt)
        self.assertIn("Cozy rainy morning reading", prompt)
        self.assertNotIn("EMOJI-ONLY MODE ACTIVATED", prompt)

    def test_build_emoji_to_caption_prompt_emoji_only(self):
        prompt = prompt_templates.build_emoji_to_caption_prompt(
            emojis="🔥 🚀 💯",
            tone="Savage",
            platform="Twitter / X",
            length="Short",
            emoji_only_mode=True,
            include_hashtags=False
        )
        self.assertIn("EMOJI-ONLY MODE ACTIVATED", prompt)
        self.assertIn("No hashtags", prompt)

    @patch("ai_service._call_gemini")
    def test_generate_emoji_captions_success(self, mock_gemini):
        mock_gemini.return_value = (
            True,
            '{"captions": [{"caption": "Living for slow mornings and rich espresso. ✨", "hook": "Slow down and sip.", "vibe_label": "Pure Aesthetic", "hashtags": ["coffee", "morningvibes"], "cta": "What is your morning brew?"}]}',
            "gemini-3.5-flash"
        )

        success, captions, err = ai_service.generate_emoji_captions(
            emojis="☕ 🥐 ✨",
            tone="Aesthetic",
            platform="Instagram",
            length="Short",
            api_key="test_dummy_key"
        )

        self.assertTrue(success)
        self.assertEqual(len(captions), 1)
        self.assertEqual(captions[0]["hook"], "Slow down and sip.")
        self.assertEqual(captions[0]["platform"], "Instagram")
        self.assertIsNone(err)

    def test_generate_emoji_captions_empty_emojis(self):
        success, captions, err = ai_service.generate_emoji_captions(
            emojis="   ",
            tone="Funny",
            platform="TikTok",
            length="Short"
        )
        self.assertFalse(success)
        self.assertEqual(captions, [])
        self.assertIn("select or enter at least one emoji", err.lower())

    # -----------------------------------------------------------------
    # Dedicated Regression Suite: Stale/Default Emoji Bug Prevention
    # -----------------------------------------------------------------

    @patch("ai_service._call_gemini")
    def test_1_exact_emojis_reach_prompt_builder(self, mock_gemini):
        """Test 1: Select '✨ 🚀 🔥' and verify exact sequence reaches prompt & Gemini."""
        mock_gemini.return_value = (
            True,
            '{"captions": [{"caption": "Ready for takeoff ✨🚀🔥", "hook": "Ignite your passion.", "vibe_label": "Bold"}]}',
            "gemini-3.5-flash"
        )

        seq = "✨ 🚀 🔥"
        success, captions, err = ai_service.generate_emoji_captions(
            emojis=seq,
            tone="Bold",
            platform="Instagram",
            length="Short",
            api_key="test_key"
        )

        self.assertTrue(success)
        mock_gemini.assert_called_once()
        call_kwargs = mock_gemini.call_args.kwargs
        prompt_passed = call_kwargs.get("prompt", "")
        self.assertIn("✨ 🚀 🔥", prompt_passed)

    @patch("ai_service._call_gemini")
    def test_2_changing_sequence_uses_new_not_previous(self, mock_gemini):
        """Test 2: Change sequence to '☕ 📖 🌧️' and verify new sequence is used, not previous."""
        mock_gemini.return_value = (
            True,
            '{"captions": [{"caption": "Cozy rainy vibes", "hook": "Rain and coffee.", "vibe_label": "Aesthetic"}]}',
            "gemini-3.5-flash"
        )

        first_seq = "✨ 🚀 🔥"
        ai_service.generate_emoji_captions(emojis=first_seq, tone="Aesthetic", platform="Instagram", length="Short")

        second_seq = "☕ 📖 🌧️"
        ai_service.generate_emoji_captions(emojis=second_seq, tone="Aesthetic", platform="Instagram", length="Short")

        self.assertEqual(mock_gemini.call_count, 2)
        second_call_prompt = mock_gemini.call_args_list[1].kwargs.get("prompt", "")
        self.assertIn("☕ 📖 🌧️", second_call_prompt)
        self.assertNotIn("✨ 🚀 🔥", second_call_prompt)

    @patch("ai_service._call_gemini")
    def test_3_preset_manually_edited_priority(self, mock_gemini):
        """Test 3: Select a preset, manually edit its emojis, verify edited sequence takes priority."""
        mock_gemini.return_value = (
            True,
            '{"captions": [{"caption": "Beach paradise", "hook": "Paradise found.", "vibe_label": "Vibes"}]}',
            "gemini-3.5-flash"
        )

        preset_emojis = "🌴 🏖️ 🌊 🍹 ✈️"
        manually_edited = f"{preset_emojis} 🌺"

        ai_service.generate_emoji_captions(
            emojis=manually_edited,
            tone="Relaxed",
            platform="Instagram",
            length="Medium"
        )

        prompt_passed = mock_gemini.call_args.kwargs.get("prompt", "")
        self.assertIn(manually_edited, prompt_passed)
        self.assertIn("🌺", prompt_passed)

    @patch("ai_service._call_gemini")
    def test_4_clear_emoji_input_validation_and_no_gemini_call(self, mock_gemini):
        """Test 4: Clear emoji input and generate. Verify validation appears and no Gemini call is made."""
        success, captions, err = ai_service.generate_emoji_captions(
            emojis="",
            tone="Aesthetic",
            platform="Instagram",
            length="Short"
        )

        self.assertFalse(success)
        self.assertEqual(captions, [])
        self.assertIn("select or enter at least one emoji", err.lower())
        mock_gemini.assert_not_called()

        # Whitespace only
        success2, captions2, err2 = ai_service.generate_emoji_captions(
            emojis="    \n\t  ",
            tone="Aesthetic",
            platform="Instagram",
            length="Short"
        )
        self.assertFalse(success2)
        mock_gemini.assert_not_called()

    @patch("ai_service._call_gemini")
    def test_5_two_consecutive_generations_independent_sequences(self, mock_gemini):
        """Test 5: Generate twice with two different sequences. Verify complete independence."""
        mock_gemini.side_effect = [
            (True, '{"captions": [{"caption": "Party time 🎉🥂🍾", "hook": "Celebrate.", "vibe_label": "Party"}]}', "gemini-3.5-flash"),
            (True, '{"captions": [{"caption": "Gym time 💪🏋️💦", "hook": "Grind.", "vibe_label": "Fitness"}]}', "gemini-3.5-flash")
        ]

        seq_a = "🎉 🥂 🍾"
        seq_b = "💪 🏋️ 💦"

        ok_a, caps_a, _ = ai_service.generate_emoji_captions(emojis=seq_a, tone="Energetic", platform="Instagram", length="Short")
        ok_b, caps_b, _ = ai_service.generate_emoji_captions(emojis=seq_b, tone="Energetic", platform="Instagram", length="Short")

        self.assertTrue(ok_a)
        self.assertTrue(ok_b)

        prompt_a = mock_gemini.call_args_list[0].kwargs.get("prompt", "")
        prompt_b = mock_gemini.call_args_list[1].kwargs.get("prompt", "")

        self.assertIn(seq_a, prompt_a)
        self.assertNotIn(seq_b, prompt_a)

        self.assertIn(seq_b, prompt_b)
        self.assertNotIn(seq_a, prompt_b)

    @patch("ai_service._call_gemini")
    def test_6_story_context_platform_tone_preserved(self, mock_gemini):
        """Test 6: Verify story context, platform, tone, length, and hashtags are preserved."""
        mock_gemini.return_value = (
            True,
            '{"captions": [{"caption": "Tech startup launch day 🚀💡", "hook": "Big news.", "vibe_label": "Professional", "hashtags": ["startup", "ai"], "cta": "Check the link."}]}',
            "gemini-3.5-flash"
        )

        seq = "🚀 💡 ⚡"
        ctx = "Seed round funding announced today"

        success, captions, err = ai_service.generate_emoji_captions(
            emojis=seq,
            tone="Professional",
            platform="LinkedIn",
            length="Long",
            emoji_only_mode=False,
            user_context=ctx,
            include_hashtags=True,
            hashtag_count=4
        )

        self.assertTrue(success)
        self.assertEqual(len(captions), 1)
        self.assertEqual(captions[0]["platform"], "LinkedIn")
        self.assertEqual(captions[0]["tone"], "Professional")

        prompt = mock_gemini.call_args.kwargs.get("prompt", "")
        self.assertIn(seq, prompt)
        self.assertIn(ctx, prompt)
        self.assertIn("LinkedIn", prompt)
        self.assertIn("Professional", prompt)
        self.assertIn("Include 4 hashtags", prompt)


if __name__ == "__main__":
    unittest.main()
