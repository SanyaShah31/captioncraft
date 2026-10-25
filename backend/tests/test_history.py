"""
Automated tests for CaptionCraft AI user-specific generation history and feature separation.
Verifies all 12 key requirements:
1. User A generates a text caption; it appears in User A's text history.
2. User A generates an image caption; it appears in User A's image history.
3. User A's text history does not contain image-caption records.
4. User A's image history does not contain text-caption records.
5. User B cannot see User A's text history.
6. User B cannot see User A's image history.
7. User B sees only their own records in both features.
8. Clearing User A's text history does not delete User A's image history.
9. Clearing User A's history does not affect User B's records.
10. A user cannot access another user's records by manipulating a user ID in client input.
11. Existing history and generation functionality continues to work.
12. Legacy records without user ownership are never exposed to any user.
"""

import os
import sys
from pathlib import Path
import json
import unittest
import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, List

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_TESTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import utils
import database


class TestHistorySeparation(unittest.TestCase):
    """Integration test suite verifying user ownership and feature isolation in history storage."""

    @classmethod
    def setUpClass(cls):
        utils.ensure_data_dir()
        try:
            cls.db = database.get_db()
        except Exception:
            cls.db = None

    def setUp(self):
        # Create unique user IDs for User A and User B to avoid cross-test interference
        self.user_a_id = f"user_a_{uuid.uuid4().hex[:8]}"
        self.user_b_id = f"user_b_{uuid.uuid4().hex[:8]}"

        self.sample_text_captions = [
            {
                "id": f"c_{uuid.uuid4().hex[:6]}",
                "caption": "Crafting the perfect latte at home ☕",
                "hook": "Crafting the perfect latte",
                "vibe_label": "Aesthetic",
                "hashtags": ["coffee", "latteart"],
                "cta": "Tell me your favorite roast!"
            }
        ]

        self.sample_image_captions = [
            {
                "id": f"c_{uuid.uuid4().hex[:6]}",
                "caption": "Sunset on Amalfi Coast with vibrant colors 🌅",
                "hook": "Sunset on Amalfi Coast",
                "vibe_label": "Travel",
                "hashtags": ["travel", "sunset"],
                "cta": "Save this spot for later!"
            }
        ]

    def tearDown(self):
        # Clean up isolated test user data from both MongoDB and JSON file
        utils.clear_history(user_id=self.user_a_id, db=self.db)
        utils.clear_history(user_id=self.user_b_id, db=self.db)

    def test_01_user_a_text_caption_appears_in_text_history(self):
        """Req 1: User A generates a text caption; it appears in User A's text history."""
        entry = utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="Latte brewing guide",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertIsNotNone(entry.get("id"))
        self.assertEqual(entry.get("user_id"), self.user_a_id)
        self.assertEqual(entry.get("feature_type"), utils.FEATURE_TEXT_TO_CAPTION)

        user_a_text_hist = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(user_a_text_hist), 1)
        self.assertEqual(user_a_text_hist[0]["id"], entry["id"])
        self.assertEqual(user_a_text_hist[0]["user_id"], self.user_a_id)
        self.assertEqual(user_a_text_hist[0]["input_summary"], "Latte brewing guide")

    def test_02_user_a_image_caption_appears_in_image_history(self):
        """Req 2: User A generates an image caption; it appears in User A's image history."""
        entry = utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="Amalfi sunset photo",
            tone="Romantic",
            platform="Instagram",
            length="Short",
            captions=self.sample_image_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            metadata={"filename": "sunset.jpg"},
            db=self.db
        )
        self.assertIsNotNone(entry.get("id"))
        self.assertEqual(entry.get("user_id"), self.user_a_id)
        self.assertEqual(entry.get("feature_type"), utils.FEATURE_IMAGE_TO_CAPTION)

        user_a_img_hist = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(user_a_img_hist), 1)
        self.assertEqual(user_a_img_hist[0]["id"], entry["id"])
        self.assertEqual(user_a_img_hist[0]["user_id"], self.user_a_id)
        self.assertEqual(user_a_img_hist[0]["metadata"]["filename"], "sunset.jpg")

    def test_03_text_history_does_not_contain_image_caption_records(self):
        """Req 3: User A's text history does not contain image-caption records."""
        # Save both a text caption and an image caption for User A
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="Text prompt only",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="Image photo only",
            tone="Romantic",
            platform="Instagram",
            length="Short",
            captions=self.sample_image_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        text_hist = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(text_hist), 1)
        self.assertEqual(text_hist[0]["feature_type"], utils.FEATURE_TEXT_TO_CAPTION)
        self.assertEqual(text_hist[0]["input_summary"], "Text prompt only")
        # Ensure no image records leaked in
        self.assertFalse(any(r.get("feature_type") == utils.FEATURE_IMAGE_TO_CAPTION for r in text_hist))

    def test_04_image_history_does_not_contain_text_caption_records(self):
        """Req 4: User A's image history does not contain text-caption records."""
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="Text prompt only",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="Image photo only",
            tone="Romantic",
            platform="Instagram",
            length="Short",
            captions=self.sample_image_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        img_hist = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(img_hist), 1)
        self.assertEqual(img_hist[0]["feature_type"], utils.FEATURE_IMAGE_TO_CAPTION)
        self.assertEqual(img_hist[0]["input_summary"], "Image photo only")
        # Ensure no text records leaked in
        self.assertFalse(any(r.get("feature_type") == utils.FEATURE_TEXT_TO_CAPTION for r in img_hist))

    def test_05_and_06_user_b_cannot_see_user_a_history(self):
        """Req 5 & 6: User B cannot see User A's text history or image history."""
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User A Private Text",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="User A Private Image",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_image_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        # User B queries their history
        user_b_text = utils.get_history(
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        user_b_img = utils.get_history(
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )
        user_b_all = utils.get_history(
            user_id=self.user_b_id,
            db=self.db
        )

        self.assertEqual(len(user_b_text), 0)
        self.assertEqual(len(user_b_img), 0)
        self.assertEqual(len(user_b_all), 0)

    def test_07_user_b_sees_only_their_own_records(self):
        """Req 7: User B sees only their own records in both features."""
        # User A saves records
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User A Text",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )

        # User B saves records
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User B Text",
            tone="Professional",
            platform="LinkedIn",
            length="Long",
            captions=self.sample_text_captions,
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="User B Image",
            tone="Fun",
            platform="TikTok",
            length="Short",
            captions=self.sample_image_captions,
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        user_b_text = utils.get_history(
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        user_b_img = utils.get_history(
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        self.assertEqual(len(user_b_text), 1)
        self.assertEqual(user_b_text[0]["input_summary"], "User B Text")
        self.assertEqual(user_b_text[0]["user_id"], self.user_b_id)

        self.assertEqual(len(user_b_img), 1)
        self.assertEqual(user_b_img[0]["input_summary"], "User B Image")
        self.assertEqual(user_b_img[0]["user_id"], self.user_b_id)

    def test_08_clearing_text_history_does_not_delete_image_history(self):
        """Req 8: Clearing User A's text history does not delete User A's image history."""
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User A Text",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="User A Image",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_image_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )

        # Clear only text history for User A
        success = utils.clear_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertTrue(success)

        # Verify text history is empty
        user_a_text = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(user_a_text), 0)

        # Verify image history is STILL intact
        user_a_img = utils.get_history(
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            db=self.db
        )
        self.assertEqual(len(user_a_img), 1)
        self.assertEqual(user_a_img[0]["input_summary"], "User A Image")

    def test_09_clearing_user_a_history_does_not_affect_user_b(self):
        """Req 9: Clearing User A's history does not affect User B's records."""
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User A Text Batch",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User B Text Batch",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_b_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )

        # User A clears ALL their history
        utils.clear_history(user_id=self.user_a_id, db=self.db)

        # User A has 0 records
        self.assertEqual(len(utils.get_history(user_id=self.user_a_id, db=self.db)), 0)

        # User B still has their record
        user_b_hist = utils.get_history(user_id=self.user_b_id, db=self.db)
        self.assertEqual(len(user_b_hist), 1)
        self.assertEqual(user_b_hist[0]["input_summary"], "User B Text Batch")

    def test_10_missing_or_manipulated_user_id_returns_empty(self):
        """Req 10: Client tampering or unauthenticated query cannot access records."""
        utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="Secret User A Data",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )

        # Query with None
        self.assertEqual(utils.get_history(user_id=None, db=self.db), [])
        # Query with empty string
        self.assertEqual(utils.get_history(user_id="", db=self.db), [])
        self.assertEqual(utils.get_history(user_id="   ", db=self.db), [])

        # Nonexistent user ID
        self.assertEqual(utils.get_history(user_id="random_hacker_id", db=self.db), [])

    def test_11_legacy_records_without_owner_are_never_exposed(self):
        """Req 11: Legacy records without user_id are never exposed to any user."""
        # Insert a legacy record with no user_id into local file / DB
        legacy_entry = {
            "id": "legacy_999",
            "timestamp": "2026-01-01 00:00:00",
            "mode": "Text-to-Caption",
            "input_summary": "Legacy Anonymous Prompt",
            "tone": "Aesthetic",
            "platform": "Instagram",
            "length": "Short",
            "captions": self.sample_text_captions,
            "metadata": {}
        }
        if self.db is not None:
            self.db["history"].insert_one(dict(legacy_entry))

        # Query by User A
        records = utils.get_history(user_id=self.user_a_id, db=self.db)
        self.assertFalse(any(r.get("id") == "legacy_999" for r in records))

        # Clean up legacy test doc
        if self.db is not None:
            self.db["history"].delete_one({"id": "legacy_999"})

    def test_12_single_item_deletion_respects_ownership(self):
        """Req 12: Deleting a single record only succeeds if owned by that user."""
        entry = utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="User A Item",
            tone="Aesthetic",
            platform="Instagram",
            length="Medium",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        rec_id = entry["id"]

        # User B attempts to delete User A's item
        utils.delete_history_item(record_id=rec_id, user_id=self.user_b_id, db=self.db)

        # Item should still exist for User A
        user_a_records = utils.get_history(user_id=self.user_a_id, db=self.db)
        self.assertEqual(len(user_a_records), 1)
        self.assertEqual(user_a_records[0]["id"], rec_id)

        # User A deletes their own item
        utils.delete_history_item(record_id=rec_id, user_id=self.user_a_id, db=self.db)
        user_a_after = utils.get_history(user_id=self.user_a_id, db=self.db)
        self.assertEqual(len(user_a_after), 0)

    def test_13_history_json_serialization_with_datetime_objects(self):
        """Req: History JSON export properly serializes Python datetime, date, UUID, and BSON-like objects."""
        now_aware = datetime(2026, 10, 25, 10, 30, 0, tzinfo=timezone.utc)
        record = {
            "id": "rec_dt_123",
            "user_id": self.user_a_id,
            "created_at": now_aware,
            "date_only": date(2026, 10, 25),
            "custom_uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "mode": "Text-to-Caption",
            "input_summary": "Test summary",
            "captions": [
                {
                    "caption": "A cool caption",
                    "tags": {"travel", "explore"}
                }
            ],
            "metadata": {
                "uploaded_at": now_aware
            }
        }

        # Serializing with export_history_to_json must not raise TypeError
        json_output = utils.export_history_to_json([record])
        self.assertIsInstance(json_output, str)

        # Must be valid JSON
        parsed = json.loads(json_output)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "rec_dt_123")
        self.assertEqual(parsed[0]["created_at"], "2026-10-25T10:30:00+00:00")
        self.assertEqual(parsed[0]["date_only"], "2026-10-25")
        self.assertEqual(parsed[0]["custom_uuid"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(parsed[0]["metadata"]["uploaded_at"], "2026-10-25T10:30:00+00:00")

    def test_14_history_csv_export_with_datetime_and_missing_fields(self):
        """Req: History CSV export properly handles datetime timestamps and records with missing optional fields."""
        entry = utils.save_generation_to_history(
            mode="Text-to-Caption",
            input_summary="CSV test summary",
            tone="Professional",
            platform="LinkedIn",
            length="Short",
            captions=self.sample_text_captions,
            user_id=self.user_a_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            db=self.db
        )
        self.assertIsNotNone(entry)

        df = utils.export_history_to_df(user_id=self.user_a_id, db=self.db)
        self.assertFalse(df.empty)
        self.assertIn("Timestamp", df.columns)
        self.assertIn("Caption", df.columns)
        self.assertIn("Batch ID", df.columns)

        # Generating CSV string must succeed without error
        csv_str = df.to_csv(index=False)
        self.assertIn("CSV test summary", csv_str)

    def test_15_empty_history_export_json_and_csv(self):
        """Req: Exporting empty history returns valid empty JSON array and empty DataFrame."""
        json_output = utils.export_history_to_json([])
        self.assertEqual(json_output.strip(), "[]")
        parsed = json.loads(json_output)
        self.assertEqual(parsed, [])

        empty_df = utils.export_history_to_df(user_id="non_existent_user_999", db=self.db)
        self.assertTrue(empty_df.empty)
        csv_str = empty_df.to_csv(index=False)
        self.assertIsInstance(csv_str, str)


if __name__ == "__main__":
    unittest.main()

