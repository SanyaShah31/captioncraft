"""
Unit tests for backend/utils.py.
Verifies history normalization across all 5 features,
user ownership isolation, datetime JSON serialization, and favorites storage.
"""

import unittest
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TEST_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import utils


class TestUtilsHistory(unittest.TestCase):

    def test_normalize_feature_type_all_modes(self):
        self.assertEqual(utils.normalize_feature_type(None, "Text-to-Caption"), utils.FEATURE_TEXT_TO_CAPTION)
        self.assertEqual(utils.normalize_feature_type(None, "Image-to-Caption"), utils.FEATURE_IMAGE_TO_CAPTION)
        self.assertEqual(utils.normalize_feature_type(None, "Emoji-to-Caption"), utils.FEATURE_EMOJI_TO_CAPTION)
        self.assertEqual(utils.normalize_feature_type(None, "Multi-Platform"), utils.FEATURE_MULTI_PLATFORM)
        self.assertEqual(utils.normalize_feature_type(None, "Carousel-Story"), utils.FEATURE_CAROUSEL_STORY)
        self.assertEqual(utils.normalize_feature_type("emoji_to_caption"), utils.FEATURE_EMOJI_TO_CAPTION)
        self.assertEqual(utils.normalize_feature_type("multi_platform"), utils.FEATURE_MULTI_PLATFORM)
        self.assertEqual(utils.normalize_feature_type("carousel_story"), utils.FEATURE_CAROUSEL_STORY)

    def test_json_serializer_handles_datetime(self):
        now = datetime.now(timezone.utc)
        serialized = utils.json_serializer(now)
        self.assertIsInstance(serialized, str)
        self.assertEqual(serialized, now.isoformat())

    def test_export_history_to_json_safe_serialization(self):
        sample_records = [
            {
                "id": "rec_001",
                "timestamp": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "captions": [{"caption": "Test caption"}]
            }
        ]
        json_output = utils.export_history_to_json(sample_records)
        self.assertIsInstance(json_output, str)
        # Ensure it parses back without error
        parsed = json.loads(json_output)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "rec_001")

    def test_get_history_empty_user_id_returns_empty(self):
        # Strict user isolation: never return records for missing or empty user_id
        records = utils.get_history(user_id=None)
        self.assertEqual(records, [])
        records_empty = utils.get_history(user_id="   ")
        self.assertEqual(records_empty, [])

    def test_favorites_add_and_remove(self):
        fav_item = {
            "id": "test_fav_id_999",
            "caption": "Test favorite caption",
            "hook": "Test Hook",
            "platform": "Instagram",
            "tone": "Aesthetic"
        }
        # Clean up if existed
        utils.remove_favorite("test_fav_id_999")

        # Add
        added = utils.add_favorite(fav_item)
        self.assertTrue(added)
        self.assertTrue(utils.is_favorite("test_fav_id_999"))

        # Remove
        removed = utils.remove_favorite("test_fav_id_999")
        self.assertTrue(removed)
        self.assertFalse(utils.is_favorite("test_fav_id_999"))


if __name__ == "__main__":
    unittest.main()
