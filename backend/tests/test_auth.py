"""
Automated unit tests for CaptionCraft AI Authentication & MongoDB integration.
Covers:
1. New user registration
2. All field validations (name, gender, age, email, password, confirm_password)
3. Duplicate email rejection (both application level and MongoDB unique index)
4. Email normalization preventing case/whitespace duplicate accounts
5. Password & confirm password mismatch rejection
6. Passwords stored securely as bcrypt hashes, never plain text
7. Successful login with valid credentials
8. Login rejection with incorrect password
9. Login rejection with unregistered email
10. Unauthenticated access prevention
11. Session preservation & access for authenticated users
12. Logout clearing authenticated session state
13. Password reset with valid single-use token
14. Rejection of expired and reused reset tokens
15. Successful login with new password after reset
16. Safe handling of MongoDB connection failures
17. Isolation and data cleanup
"""

import os
import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_TESTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import auth
import database
from database import DatabaseConnectionError


class TestAuthenticationUnit(unittest.TestCase):
    """Isolated unit tests for field validations, hashing, and token logic."""

    def test_01_email_normalization(self):
        """Test Case 4: Email normalization trims whitespace and lowers case."""
        raw_email = "   User.Name+Test@Example.COM   "
        normalized = auth.normalize_email(raw_email)
        self.assertEqual(normalized, "user.name+test@example.com")
        self.assertEqual(auth.normalize_email(""), "")
        self.assertEqual(auth.normalize_email(None), "")

    def test_02_field_validation_full_name(self):
        """Test Case 2: Full Name validation."""
        # Empty name
        valid, err = auth.validate_registration_fields("", "Male", 25, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)
        self.assertIn("Full Name is required", err)

        # Whitespace only
        valid, err = auth.validate_registration_fields("   ", "Male", 25, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)

        # Too short
        valid, err = auth.validate_registration_fields("A", "Male", 25, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)
        self.assertIn("at least 2 characters", err)

    def test_03_field_validation_gender(self):
        """Test Case 2: Gender validation."""
        valid, err = auth.validate_registration_fields("Alice", "Other", 25, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)
        self.assertIn("Gender must be one of", err)

        for valid_gender in ["Male", "Female", "Prefer not to say"]:
            valid, err = auth.validate_registration_fields("Alice", valid_gender, 25, "test@test.com", "Password123", "Password123")
            self.assertTrue(valid)

    def test_04_field_validation_age(self):
        """Test Case 2: Age range validation (1-120)."""
        # Negative age
        valid, err = auth.validate_registration_fields("Alice", "Female", -5, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)

        # Zero age
        valid, err = auth.validate_registration_fields("Alice", "Female", 0, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)

        # Out of bounds (> 120)
        valid, err = auth.validate_registration_fields("Alice", "Female", 150, "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)

        # Non-numeric age
        valid, err = auth.validate_registration_fields("Alice", "Female", "twenty", "test@test.com", "Password123", "Password123")
        self.assertFalse(valid)

        # Valid age
        valid, err = auth.validate_registration_fields("Alice", "Female", "28", "test@test.com", "Password123", "Password123")
        self.assertTrue(valid)

    def test_05_field_validation_email_format(self):
        """Test Case 2: Email format validation."""
        invalid_emails = ["notanemail", "user@", "@domain.com", "user@domain", "user domain.com"]
        for bad_email in invalid_emails:
            valid, err = auth.validate_registration_fields("Alice", "Female", 25, bad_email, "Password123", "Password123")
            self.assertFalse(valid, f"Expected {bad_email} to fail validation")
            self.assertIn("valid email address", err)

    def test_06_field_validation_password_length(self):
        """Test Case 2: Minimum password length requirement."""
        valid, err = auth.validate_registration_fields("Alice", "Female", 25, "a@b.com", "short", "short")
        self.assertFalse(valid)
        self.assertIn("at least 8 characters", err)

    def test_07_field_validation_password_mismatch(self):
        """Test Case 5: Password and Confirm Password mismatch rejection."""
        valid, err = auth.validate_registration_fields("Alice", "Female", 25, "a@b.com", "Password123", "DifferentPass123")
        self.assertFalse(valid)
        self.assertIn("do not match", err)

    def test_08_password_hashing_security(self):
        """Test Case 6: Passwords are hashed securely with bcrypt, never plain text."""
        raw_pass = "MySecretPassword!2026"
        hashed = auth.hash_password(raw_pass)

        # Ensure hash does not contain raw password
        self.assertNotIn(raw_pass, hashed)
        # Ensure bcrypt hash signature ($2b$)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))

        # Verify correct password succeeds
        self.assertTrue(auth.verify_password(raw_pass, hashed))
        # Verify incorrect password fails
        self.assertFalse(auth.verify_password("WrongPassword!", hashed))

    def test_09_database_connection_failure_handling(self):
        """Test Case 16: Database connection failure produces safe error without leaking credentials."""
        with patch("pymongo.MongoClient") as mock_client:
            mock_client.side_effect = database.ConnectionFailure("Refused connection")
            # Clear singleton
            database._client = None

            with self.assertRaises(DatabaseConnectionError) as cm:
                database.get_mongo_client(uri="mongodb://secret_user:secret_pass@unreachable:27017")

            err_text = str(cm.exception)
            # Ensure no credentials or raw URI are leaked
            self.assertNotIn("secret_user", err_text)
            self.assertNotIn("secret_pass", err_text)
            self.assertIn("Unable to connect to the database", err_text)


class TestAuthenticationIntegration(unittest.TestCase):
    """Integration tests with live local MongoDB instance."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.db = database.get_db()
            cls.available = True
        except Exception:
            cls.available = False

    def setUp(self):
        if not self.available:
            self.skipTest("Live MongoDB instance is not available for integration testing.")
        # Ensure clean test sandbox
        self.test_emails = []

    def tearDown(self):
        if self.available and self.test_emails:
            for email in self.test_emails:
                norm = auth.normalize_email(email)
                self.db["users"].delete_many({"email": norm})
                self.db["password_resets"].delete_many({"email": norm})

    def test_10_user_registration_success(self):
        """Test Case 1: A new user can register successfully."""
        email = "integration_alice@example.com"
        self.test_emails.append(email)

        success, msg, user = auth.register_user(
            full_name="Alice Smith",
            gender="Female",
            age=26,
            email=email,
            password="StrongPassword123",
            confirm_password="StrongPassword123",
            db=self.db
        )
        self.assertTrue(success)
        self.assertIn("Registration successful", msg)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], email)
        self.assertNotIn("password_hash", user)  # Safe dict returned

        # Verify database record
        doc = self.db["users"].find_one({"email": email})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["full_name"], "Alice Smith")
        self.assertEqual(doc["gender"], "Female")
        self.assertEqual(doc["age"], 26)
        self.assertNotIn("confirm_password", doc)
        self.assertIn("password_hash", doc)
        self.assertTrue(auth.verify_password("StrongPassword123", doc["password_hash"]))

    def test_11_duplicate_email_registration_rejected(self):
        """Test Case 3: Registration fails when email is already registered."""
        email = "duplicate_user@example.com"
        self.test_emails.append(email)

        # First registration
        ok1, _, _ = auth.register_user("Bob A", "Male", 30, email, "Pass123456", "Pass123456", db=self.db)
        self.assertTrue(ok1)

        # Second registration with exact same email
        ok2, msg2, _ = auth.register_user("Bob B", "Male", 31, email, "DifferentPass123", "DifferentPass123", db=self.db)
        self.assertFalse(ok2)
        self.assertIn("already registered", msg2)

    def test_12_email_normalization_prevents_duplicate_accounts(self):
        """Test Case 4: Duplicate accounts rejected across case/whitespace variations."""
        email_base = "normalize_check@example.com"
        email_variant = "  Normalize_Check@Example.COM  "
        self.test_emails.append(email_base)

        ok1, _, _ = auth.register_user("User One", "Prefer not to say", 22, email_base, "Pass123456", "Pass123456", db=self.db)
        self.assertTrue(ok1)

        # Attempt to register using capitalization & whitespace variation
        ok2, msg2, _ = auth.register_user("User Two", "Prefer not to say", 23, email_variant, "OtherPass987", "OtherPass987", db=self.db)
        self.assertFalse(ok2)
        self.assertIn("already registered", msg2)

    def test_13_login_authentication_success_and_failure(self):
        """Test Cases 7, 8, 9: Valid login, incorrect password, and unregistered email."""
        email = "login_test@example.com"
        self.test_emails.append(email)

        auth.register_user("Login Tester", "Male", 29, email, "CorrectPass123", "CorrectPass123", db=self.db)

        # Case 7: Correct email & password
        ok, msg, user = auth.authenticate_user(email, "CorrectPass123", db=self.db)
        self.assertTrue(ok)
        self.assertEqual(user["email"], email)
        self.assertNotIn("password_hash", user)

        # Case 8: Incorrect password
        ok_bad_pass, msg_bad_pass, _ = auth.authenticate_user(email, "WrongPass999", db=self.db)
        self.assertFalse(ok_bad_pass)
        self.assertEqual(msg_bad_pass, "Invalid email or password.")

        # Case 9: Unregistered email
        ok_unreg, msg_unreg, _ = auth.authenticate_user("unregistered_random@example.com", "AnyPassword123", db=self.db)
        self.assertFalse(ok_unreg)
        self.assertEqual(msg_unreg, "Invalid email or password.")

    def test_14_forgot_password_reset_flow(self):
        """Test Cases 13, 14, 15: Token generation, expiration, single-use, and login with new password."""
        email = "reset_flow@example.com"
        self.test_emails.append(email)

        auth.register_user("Reset Subject", "Female", 34, email, "OriginalPass123", "OriginalPass123", db=self.db)

        # 1. Generate token
        token, user_doc, expires_at = auth.create_password_reset_token(email, db=self.db)
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 20)
        self.assertIsNotNone(expires_at)

        # Verify token is stored as hash, not plain text
        token_hash = auth.hash_reset_token(token)
        reset_record = self.db["password_resets"].find_one({"token_hash": token_hash})
        self.assertIsNotNone(reset_record)
        self.assertFalse(reset_record["used"])

        # 2. Case 13: Verify valid token
        valid, doc, err = auth.verify_reset_token(token, db=self.db)
        self.assertTrue(valid)
        self.assertIsNone(err)

        # 3. Case 15: Reset password with token
        reset_ok, reset_msg = auth.reset_password_with_token(token, "BrandNewPassword456", "BrandNewPassword456", db=self.db)
        self.assertTrue(reset_ok)
        self.assertIn("successfully reset", reset_msg)

        # 4. Case 15: Log in with new password
        login_new_ok, _, _ = auth.authenticate_user(email, "BrandNewPassword456", db=self.db)
        self.assertTrue(login_new_ok)

        # Old password must no longer work
        login_old_ok, _, _ = auth.authenticate_user(email, "OriginalPass123", db=self.db)
        self.assertFalse(login_old_ok)

        # 5. Case 14: Reused token must be rejected
        reused_valid, _, reused_err = auth.verify_reset_token(token, db=self.db)
        self.assertFalse(reused_valid)
        self.assertIn("already been used", reused_err)

        # 6. Case 14: Expired token must be rejected
        expired_token, _, _ = auth.create_password_reset_token(email, db=self.db)
        exp_hash = auth.hash_reset_token(expired_token)
        # Manually backdate expiration in DB to simulate expired token
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.db["password_resets"].update_one(
            {"token_hash": exp_hash},
            {"$set": {"expires_at": past_time}}
        )

        exp_valid, _, exp_err = auth.verify_reset_token(expired_token, db=self.db)
        self.assertFalse(exp_valid)
        self.assertIn("expired", exp_err)

    def test_15_smtp_unconfigured_behavior(self):
        """Verifies SMTP unconfigured state is detected safely without raising exceptions."""
        with patch.dict(os.environ, {
            "EMAIL_USER": "",
            "EMAIL_PASS": "",
            "SMTP_HOST": "",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": ""
        }, clear=False):
            self.assertFalse(auth.is_email_service_configured())
            sent, msg = auth.send_password_reset_email("user@example.com", "fake_token_123")
            self.assertFalse(sent)
            self.assertIn("not configured", msg)
            self.assertNotIn("fake_token_123", msg)

    def test_16_dev_mode_explicit_configuration(self):
        """Verifies development mode is disabled by default and only enabled via explicit env var."""
        with patch.dict(os.environ, {"AUTH_DEV_MODE": "false"}, clear=False):
            self.assertFalse(auth.is_dev_mode())
            # When disabled, record_dev_reset_token must return False
            self.assertFalse(auth.record_dev_reset_token("test_tok", "dev@example.com"))

        with patch.dict(os.environ, {"AUTH_DEV_MODE": "true"}, clear=False):
            self.assertTrue(auth.is_dev_mode())
            # When enabled, writes token to local file for dev testing
            recorded = auth.record_dev_reset_token("test_tok", "dev@example.com")
            self.assertTrue(recorded)
            dev_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dev_reset_token.txt")
            if os.path.exists(dev_file):
                os.remove(dev_file)

    def test_17_persistent_session_creation_and_verification(self):
        """Verifies cryptographically signed session tokens can be created and verified."""
        mock_db = MagicMock()
        mock_users = MagicMock()
        mock_sessions = MagicMock()
        mock_db.__getitem__.side_effect = lambda k: mock_users if k == "users" else mock_sessions

        # Mock user exists
        mock_users.find_one.return_value = {
            "user_id": "test_user_persistent_1",
            "full_name": "Persistent User",
            "gender": "Female",
            "age": 28,
            "email": "persist@example.com",
            "created_at": datetime.now(timezone.utc)
        }

        # Create session
        token, expires = auth.create_user_session("test_user_persistent_1", db=mock_db)
        self.assertIsNotNone(token)
        self.assertIsNotNone(expires)
        self.assertTrue(mock_sessions.insert_one.called)

        # Mock session doc returned from DB for verification
        mock_sessions.find_one.return_value = {
            "user_id": "test_user_persistent_1",
            "token_hash": auth.hash_reset_token(token),
            "expires_at": expires,
            "active": True
        }

        # Verify session
        valid, user_info = auth.verify_user_session(token, db=mock_db)
        self.assertTrue(valid)
        self.assertEqual(user_info["user_id"], "test_user_persistent_1")
        self.assertEqual(user_info["email"], "persist@example.com")

    def test_18_persistent_session_tampering_and_invalidation(self):
        """Verifies tampered tokens and invalidated sessions are rejected."""
        mock_db = MagicMock()
        mock_users = MagicMock()
        mock_sessions = MagicMock()
        mock_db.__getitem__.side_effect = lambda k: mock_users if k == "users" else mock_sessions

        # Tampered token
        valid, user_info = auth.verify_user_session("tampered.token.here", db=mock_db)
        self.assertFalse(valid)
        self.assertIsNone(user_info)

        # Invalidate session
        mock_sessions.update_many.return_value = MagicMock(modified_count=1)
        res = auth.invalidate_user_session("valid_token_string", db=mock_db)
        self.assertTrue(res)
        self.assertTrue(mock_sessions.update_many.called)

    def test_19_persistent_session_expiration(self):
        """Verifies expired sessions are rejected and marked inactive."""
        mock_db = MagicMock()
        mock_users = MagicMock()
        mock_sessions = MagicMock()
        mock_db.__getitem__.side_effect = lambda k: mock_users if k == "users" else mock_sessions

        mock_users.find_one.return_value = {"user_id": "u1", "email": "u1@example.com"}
        token, _ = auth.create_user_session("u1", db=mock_db)

        # Mock expired session in DB
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sessions.find_one.return_value = {
            "_id": "sess_1",
            "user_id": "u1",
            "token_hash": auth.hash_reset_token(token),
            "expires_at": expired_time,
            "active": True
        }

        valid, user_info = auth.verify_user_session(token, db=mock_db)
        self.assertFalse(valid)
        self.assertIsNone(user_info)
        self.assertTrue(mock_sessions.update_one.called)


if __name__ == "__main__":
    unittest.main()
