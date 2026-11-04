"""
Unit tests for backend/auth.py.
Verifies password hashing, password validation, email normalization,
Google App Password sanitization, and registration field validation.
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

import auth


class TestAuth(unittest.TestCase):

    def test_normalize_email(self):
        self.assertEqual(auth.normalize_email("  User@Example.COM "), "user@example.com")
        self.assertEqual(auth.normalize_email("test@domain.org"), "test@domain.org")

    def test_password_hashing_and_verification(self):
        password = "SecurePassword123!"
        hashed = auth.hash_password(password)
        self.assertNotEqual(password, hashed)
        self.assertTrue(auth.verify_password(password, hashed))
        self.assertFalse(auth.verify_password("WrongPassword", hashed))

    def test_sanitize_app_password(self):
        raw = " abcd efgh ijkl mnop "
        cleaned = auth.sanitize_smtp_password(raw)
        self.assertEqual(cleaned, "abcdefghijklmnop")

    def test_validate_registration_inputs(self):
        # Valid input
        is_val, err = auth.validate_registration_fields(
            full_name="Jane Creator",
            gender="Female",
            age=25,
            email="jane@example.com",
            password="StrongPassword123",
            confirm_password="StrongPassword123"
        )
        self.assertTrue(is_val)
        self.assertIsNone(err)

        # Invalid short password
        is_val, err = auth.validate_registration_fields(
            full_name="Jane Creator",
            gender="Female",
            age=25,
            email="jane@example.com",
            password="123",
            confirm_password="123"
        )
        self.assertFalse(is_val)
        self.assertIn("at least 8 characters", err.lower())

        # Invalid age
        is_val, err = auth.validate_registration_fields(
            full_name="Jane Creator",
            gender="Female",
            age=0,
            email="jane@example.com",
            password="StrongPassword123",
            confirm_password="StrongPassword123"
        )
        self.assertFalse(is_val)
        self.assertIn("age", err.lower())


if __name__ == "__main__":
    unittest.main()
