"""
Unit tests for Feature 5: AI Multi-Image Carousel & Photo Dump Generator.
Verifies multi-image prompt construction, slide progression structure,
Cover Hook -> Progression -> CTA logic, and single slide regeneration.
"""

import unittest
from unittest.mock import patch
from PIL import Image
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


class TestCarouselStory(unittest.TestCase):

    def setUp(self):
        # Create small test PIL images
        self.img1 = Image.new("RGB", (64, 64), color="red")
        self.img2 = Image.new("RGB", (64, 64), color="blue")
        self.img3 = Image.new("RGB", (64, 64), color="green")

    def test_build_carousel_storyteller_prompt(self):
        prompt = prompt_templates.build_carousel_storyteller_prompt(
            num_slides=3,
            tone="Aesthetic",
            platform="Instagram",
            topic_context="Weekend getaway into the mountains"
        )
        self.assertIn("sequence of 3 photos", prompt)
        self.assertIn("Slide 1 (Cover Hook)", prompt)
        self.assertIn("Weekend getaway into the mountains", prompt)
        self.assertIn("Instagram", prompt)

    def test_build_carousel_single_slide_prompt(self):
        prompt = prompt_templates.build_carousel_single_slide_prompt(
            slide_index=2,
            total_slides=4,
            current_storyline="Exploring alpine valleys",
            tone="Inspirational"
        )
        self.assertIn("Slide #2 (out of 4", prompt)
        self.assertIn("Story Progression", prompt)

    @patch("ai_service._call_gemini")
    def test_generate_carousel_story_success(self, mock_gemini):
        mock_response = """{
          "theme_title": "Mountain Serenity",
          "master_caption": "48 hours in the peaks that restored our peace. Swipe through.",
          "master_hashtags": ["mountains", "nature", "wanderlust"],
          "master_cta": "Which photo is your favorite? 1, 2, or 3?",
          "slides": [
            {
              "slide_number": 1,
              "slide_type": "Cover Hook",
              "title": "We left at 4 AM.",
              "caption": "The journey began before dawn.",
              "overlay_text": "Worth waking up for.",
              "visual_connection": "Sunrise over peak"
            },
            {
              "slide_number": 2,
              "slide_type": "Story Progression",
              "title": "The halfway mark.",
              "caption": "Hiking past crystal streams.",
              "overlay_text": "Keep climbing.",
              "visual_connection": "River crossing"
            },
            {
              "slide_number": 3,
              "slide_type": "Closing & CTA",
              "title": "The summit view.",
              "caption": "Standing at the edge of the world.",
              "overlay_text": "Save for your next hike 🔖",
              "visual_connection": "Full panorama"
            }
          ]
        }"""
        mock_gemini.return_value = (True, mock_response, "gemini-3.8-flash")

        success, result, err = ai_service.generate_carousel_story(
            images=[self.img1, self.img2, self.img3],
            tone="Aesthetic",
            platform="Instagram",
            topic_context="Mountain trip",
            api_key="test_dummy_key"
        )

        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertEqual(result["total_slides"], 3)
        self.assertEqual(len(result["slides"]), 3)
        self.assertEqual(result["slides"][0]["slide_type"], "Cover Hook")
        self.assertEqual(result["slides"][2]["slide_type"], "Closing & CTA")
        self.assertEqual(result["theme_title"], "Mountain Serenity")

    def test_generate_carousel_story_empty_images(self):
        success, result, err = ai_service.generate_carousel_story(
            images=[],
            tone="Aesthetic"
        )
        self.assertFalse(success)
        self.assertIn("at least one image", err.lower())


if __name__ == "__main__":
    unittest.main()
