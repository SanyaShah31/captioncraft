"""
Automated unit tests for CaptionCraft AI.
Verifies prompt templates, storage utilities, image validation,
and JSON parsing functionality.
"""

import os
import sys
from pathlib import Path
import unittest
import json
import io
from PIL import Image

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_TESTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import prompt_templates
import utils
import ai_service

class TestPromptTemplates(unittest.TestCase):
    def test_text_to_caption_prompt_generation(self):
        prompt = prompt_templates.build_text_to_caption_prompt(
            topic="Eco-friendly bamboo coffee cup",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            include_hashtags=True,
            hashtag_count=5,
            include_emojis=True
        )
        self.assertIn("Eco-friendly bamboo coffee cup", prompt)
        self.assertIn("Instagram", prompt)
        self.assertIn("Aesthetic", prompt)
        self.assertIn("Medium", prompt)
        self.assertIn("5", prompt)

    def test_image_to_caption_prompt_generation(self):
        prompt = prompt_templates.build_image_to_caption_prompt(
            tone="Funny",
            platform="Twitter / X",
            length="Short",
            include_hashtags=False,
            user_context="Caught cat stealing pancake"
        )
        self.assertIn("Funny", prompt)
        self.assertIn("Twitter / X", prompt)
        self.assertIn("Caught cat stealing pancake", prompt)

    def test_emoji_to_caption_prompt_generation(self):
        prompt = prompt_templates.build_emoji_to_caption_prompt(
            emojis="✈️ 🌊 🌴",
            tone="Romantic",
            platform="TikTok",
            length="Short",
            emoji_only_mode=True
        )
        self.assertIn("✈️ 🌊 🌴", prompt)
        self.assertIn("EMOJI-ONLY MODE", prompt)

class TestUtils(unittest.TestCase):
    def setUp(self):
        utils.ensure_data_dir()

    def test_text_metrics(self):
        text = "Hello world! This is a test caption."
        metrics = utils.calculate_text_metrics(text)
        self.assertEqual(metrics["words"], 7)
        self.assertEqual(metrics["characters"], len(text))
        self.assertGreaterEqual(metrics["reading_seconds"], 1)

    def test_history_and_favorites(self):
        # Test History Saving
        sample_captions = [
            {
                "id": "c123",
                "caption": "Living my best life in the sun ✨",
                "hook": "Living my best life",
                "vibe_label": "The Aesthetic Vibe",
                "hashtags": ["sun", "travel"],
                "cta": "Drop your fav spot below!"
            }
        ]
        test_user_id = "test_user_unit_123"
        history_entry = utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="Sunny travel vibes",
            tone="Aesthetic",
            platform="Instagram",
            length="Short",
            captions=sample_captions,
            user_id=test_user_id,
            feature_type="text_to_caption"
        )
        self.assertEqual(history_entry["mode"], "Text-to-Caption")
        self.assertEqual(history_entry["user_id"], test_user_id)
        self.assertEqual(history_entry["feature_type"], "text_to_caption")

        history = utils.get_history(user_id=test_user_id, mode_filter="Text-to-Caption")
        self.assertTrue(len(history) > 0)

        # Test Favorites
        cap_fav = sample_captions[0]
        added = utils.add_favorite(cap_fav)
        self.assertTrue(utils.is_favorite(cap_fav["id"]))
        favs = utils.get_favorites()
        self.assertTrue(any(f["id"] == cap_fav["id"] for f in favs))

        # Test Remove Favorite
        removed = utils.remove_favorite(cap_fav["id"])
        self.assertTrue(removed)
        self.assertFalse(utils.is_favorite(cap_fav["id"]))

    def test_image_validation(self):
        # Create a small valid in-memory image
        img = Image.new("RGB", (100, 100), color="blue")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        # Mock an uploaded file
        class MockUploadedFile:
            def __init__(self, bytes_data, name):
                self.data = bytes_data
                self.name = name
            def getvalue(self):
                return self.data

        mock_file = MockUploadedFile(img_byte_arr.getvalue(), "test_photo.png")
        is_valid, err, pil_img, meta = utils.validate_image(mock_file)
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertEqual(meta["format"], "PNG")
        self.assertEqual(meta["width"], 100)

        # Test unsupported extension
        mock_invalid = MockUploadedFile(b"fake data", "file.txt")
        is_valid_inv, err_inv, _, _ = utils.validate_image(mock_invalid)
        self.assertFalse(is_valid_inv)
        self.assertIn("Unsupported format", err_inv)

class TestAiService(unittest.TestCase):
    def test_json_cleaner_and_parser(self):
        json_markdown = """```json
{
  "captions": [
    {
      "caption": "Golden hour never looked so good. 🌅",
      "hook": "Golden hour never looked so good.",
      "vibe_label": "The Aesthetic Vibe",
      "hashtags": ["goldenhour", "sunset"],
      "emojis": ["🌅", "✨"],
      "cta": "Tag your sunset buddy"
    }
  ]
}
```"""
        parsed = ai_service._clean_and_parse_json(json_markdown)
        self.assertIn("captions", parsed)
        self.assertEqual(len(parsed["captions"]), 1)

        normalized = ai_service._normalize_captions(parsed["captions"], "Instagram", "Aesthetic")
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["platform"], "Instagram")
        self.assertTrue(len(normalized[0]["id"]) > 0)

    def test_missing_api_key_handling(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            success, captions, err_msg = ai_service.generate_text_captions(
                topic="Test Topic",
                tone="Funny",
                platform="Instagram",
                length="Short",
                api_key=""
            )
            self.assertFalse(success)
            self.assertIn("API Key Missing", err_msg)

if __name__ == "__main__":
    unittest.main()
