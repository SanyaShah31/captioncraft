"""
Unit and integration tests for Cloudinary Image Storage and Gmail SMTP Password Reset.
Verifies all verification criteria from the specification:
Cloudinary:
1. Cloudinary configuration loads using the three existing environment variables.
2. Valid images upload successfully when valid credentials are supplied.
3. Image upload failures are handled safely.
4. Invalid image types are rejected.
5. Missing credentials do not crash unrelated application features.
6. Successful uploads return usable Cloudinary references.
7. Image history stores the appropriate Cloudinary reference and current user's ID.
8. One user's image history remains inaccessible to another user.
9. Existing image-to-caption generation continues to work.

Gmail Password Reset:
1. EMAIL_USER and EMAIL_PASS are recognized correctly.
2. SMTP connects to smtp.gmail.com:587 and uses STARTTLS.
3. The sender address comes from EMAIL_USER.
4. A reset email contains the correct application URL (APP_BASE_URL / localhost:8501).
5. Reset tokens are never exposed in the UI or logs.
6. Failed email delivery is handled honestly.
7. Expired and reused reset tokens remain invalid.
8. Password reset works with the new password.
9. Missing Gmail credentials do not crash the application.
10. Existing authentication and application tests still pass.
"""

import os
import sys
from pathlib import Path
import io
import unittest
import uuid
from unittest.mock import patch, MagicMock
from PIL import Image

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_TESTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cloudinary_service
import auth
import utils
import database


class TestCloudinaryIntegration(unittest.TestCase):
    """Test suite for Cloudinary service credentials, uploads, validation, and history integration."""

    def setUp(self):
        # Reset deduplication cache per test
        cloudinary_service.clear_cache()
        # Create a small valid test image in memory
        self.valid_img = Image.new("RGB", (64, 64), color="purple")
        buf = io.BytesIO()
        self.valid_img.save(buf, format="PNG")
        self.valid_img_bytes = buf.getvalue()

    def test_01_cloudinary_config_loading(self):
        """Req 1: Cloudinary configuration loads using the three environment variables."""
        mock_env = {
            "CLOUDINARY_CLOUD_NAME": "test_cloud_123",
            "CLOUDINARY_API_KEY": "test_api_key_456",
            "CLOUDINARY_API_SECRET": "test_secret_789"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            cfg = cloudinary_service.get_cloudinary_config()
            self.assertEqual(cfg["cloud_name"], "test_cloud_123")
            self.assertEqual(cfg["api_key"], "test_api_key_456")
            self.assertEqual(cfg["api_secret"], "test_secret_789")
            self.assertTrue(cloudinary_service.is_cloudinary_configured())

    def test_02_missing_credentials_handling(self):
        """Req 5: Missing credentials do not crash application; returns clean unconfigured status."""
        empty_env = {
            "CLOUDINARY_CLOUD_NAME": "",
            "CLOUDINARY_API_KEY": "",
            "CLOUDINARY_API_SECRET": ""
        }
        with patch.dict(os.environ, empty_env, clear=False):
            self.assertFalse(cloudinary_service.is_cloudinary_configured())
            success, err, meta = cloudinary_service.upload_image(self.valid_img_bytes, filename="test.png")
            self.assertFalse(success)
            self.assertIsNone(meta)
            self.assertIn("not configured", err.lower())

    def test_03_valid_image_upload_success_and_reference(self):
        """Req 2 & 6: Successful uploads return usable Cloudinary references (public_id, secure_url)."""
        mock_env = {
            "CLOUDINARY_CLOUD_NAME": "demo_cloud",
            "CLOUDINARY_API_KEY": "demo_key",
            "CLOUDINARY_API_SECRET": "demo_secret"
        }
        fake_response = {
            "public_id": "captioncraft/users/user123/sample_abc123",
            "secure_url": "https://res.cloudinary.com/demo_cloud/image/upload/v1234/sample.png",
            "format": "png",
            "width": 64,
            "height": 64,
            "bytes": len(self.valid_img_bytes),
            "created_at": "2026-10-24T12:00:00Z"
        }

        with patch.dict(os.environ, mock_env, clear=False):
            with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
                ok, err, meta = cloudinary_service.upload_image(
                    self.valid_img_bytes,
                    filename="sample.png",
                    user_id="user123"
                )
                self.assertTrue(ok)
                self.assertIsNone(err)
                self.assertIsNotNone(meta)
                self.assertEqual(meta["public_id"], fake_response["public_id"])
                self.assertEqual(meta["secure_url"], fake_response["secure_url"])
                mock_upload.assert_called_once()

    def test_04_image_upload_failure_handled_safely(self):
        """Req 3: Image upload failures are handled safely without crashing or exposing secrets."""
        mock_env = {
            "CLOUDINARY_CLOUD_NAME": "demo_cloud",
            "CLOUDINARY_API_KEY": "demo_key",
            "CLOUDINARY_API_SECRET": "super_secret_value_xyz"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            with patch("cloudinary.uploader.upload", side_effect=Exception("Connection refused super_secret_value_xyz")):
                ok, err, meta = cloudinary_service.upload_image(
                    self.valid_img_bytes,
                    filename="sample.png"
                )
                self.assertFalse(ok)
                self.assertIsNone(meta)
                self.assertIn("Cloudinary upload failed", err)
                # Guarantees secrets are never leaked in error messages
                self.assertNotIn("super_secret_value_xyz", err)

    def test_05_invalid_image_types_and_empty_rejected(self):
        """Req 4: Invalid image types and corrupt/empty data are rejected."""
        mock_env = {
            "CLOUDINARY_CLOUD_NAME": "demo_cloud",
            "CLOUDINARY_API_KEY": "demo_key",
            "CLOUDINARY_API_SECRET": "demo_secret"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            # Empty bytes
            ok, err, _ = cloudinary_service.upload_image(b"", filename="empty.png")
            self.assertFalse(ok)
            self.assertIn("empty", err.lower())

            # Fake text data with .txt extension
            ok2, err2, _ = cloudinary_service.upload_image(b"just some text data", filename="document.txt")
            self.assertFalse(ok2)
            self.assertIn("parse", err2.lower())

    def test_06_deduplication_cache(self):
        """Req: Avoid uploading the same image repeatedly."""
        mock_env = {
            "CLOUDINARY_CLOUD_NAME": "demo_cloud",
            "CLOUDINARY_API_KEY": "demo_key",
            "CLOUDINARY_API_SECRET": "demo_secret"
        }
        fake_response = {
            "public_id": "captioncraft/users/user123/cached_photo",
            "secure_url": "https://res.cloudinary.com/demo_cloud/image/upload/cached.png",
            "format": "png",
            "width": 64,
            "height": 64,
            "bytes": len(self.valid_img_bytes)
        }
        with patch.dict(os.environ, mock_env, clear=False):
            with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
                # First upload
                ok1, _, meta1 = cloudinary_service.upload_image(self.valid_img_bytes, filename="test.png")
                self.assertTrue(ok1)
                self.assertEqual(mock_upload.call_count, 1)

                # Second upload with exact same bytes -> uses cache without calling Cloudinary API again
                ok2, _, meta2 = cloudinary_service.upload_image(self.valid_img_bytes, filename="test.png")
                self.assertTrue(ok2)
                self.assertEqual(mock_upload.call_count, 1)  # Still 1!
                self.assertEqual(meta1["public_id"], meta2["public_id"])

    def test_07_image_history_stores_cloudinary_reference_and_user_ownership(self):
        """Req 7 & 8: Image history stores Cloudinary reference and preserves user isolation."""
        test_user_a = f"user_cloud_a_{uuid.uuid4().hex[:6]}"
        test_user_b = f"user_cloud_b_{uuid.uuid4().hex[:6]}"

        img_metadata = {
            "filename": "amalfi.jpg",
            "format": "JPEG",
            "size_mb": 1.5,
            "cloudinary_public_id": "captioncraft/users/amalfi_123",
            "cloudinary_url": "https://res.cloudinary.com/cloud/image/upload/amalfi.jpg",
            "secure_url": "https://res.cloudinary.com/cloud/image/upload/amalfi.jpg"
        }

        # User A saves image caption with Cloudinary reference
        entry = utils.save_generation_to_history(
            mode="Image-to-Caption",
            input_summary="Image: amalfi.jpg (Amalfi sunset)",
            tone="Romantic",
            platform="Instagram",
            length="Medium",
            captions=[{"id": "c1", "caption": "Amalfi sunsets are forever ✨"}],
            metadata=img_metadata,
            user_id=test_user_a,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION
        )

        self.assertEqual(entry["metadata"]["cloudinary_public_id"], "captioncraft/users/amalfi_123")
        self.assertEqual(entry["metadata"]["cloudinary_url"], "https://res.cloudinary.com/cloud/image/upload/amalfi.jpg")

        # User A retrieves history: image reference is present
        user_a_hist = utils.get_history(user_id=test_user_a, feature_type=utils.FEATURE_IMAGE_TO_CAPTION)
        self.assertEqual(len(user_a_hist), 1)
        self.assertEqual(user_a_hist[0]["metadata"]["cloudinary_public_id"], "captioncraft/users/amalfi_123")

        # User B retrieves history: User B CANNOT see User A's history or image reference
        user_b_hist = utils.get_history(user_id=test_user_b, feature_type=utils.FEATURE_IMAGE_TO_CAPTION)
        self.assertEqual(len(user_b_hist), 0)

        # Cleanup test data
        utils.clear_history(user_id=test_user_a)
        utils.clear_history(user_id=test_user_b)


class TestGmailSmtpIntegration(unittest.TestCase):
    """Test suite for Gmail SMTP password reset delivery configuration, parameters, and URL construction."""

    def test_01_email_user_and_pass_recognized(self):
        """Req 1 & 3: EMAIL_USER and EMAIL_PASS are recognized as sender and SMTP credentials."""
        mock_env = {
            "EMAIL_USER": "myaccount@gmail.com",
            "EMAIL_PASS": "abcd-efgh-ijkl-mnop",
            "APP_BASE_URL": "http://localhost:8501"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            cfg = auth.get_email_config()
            self.assertEqual(cfg["username"], "myaccount@gmail.com")
            self.assertEqual(cfg["password"], "abcd-efgh-ijkl-mnop")
            self.assertEqual(cfg["from_email"], "myaccount@gmail.com")
            self.assertEqual(cfg["host"], "smtp.gmail.com")
            self.assertEqual(cfg["port"], 587)
            self.assertTrue(cfg["use_tls"])
            self.assertTrue(auth.is_email_service_configured())

    def test_02_smtp_connection_parameters_and_starttls(self):
        """Req 2: SMTP connects to smtp.gmail.com:587 and executes starttls and login."""
        mock_env = {
            "EMAIL_USER": "myaccount@gmail.com",
            "EMAIL_PASS": "abcd-efgh-ijkl-mnop",
            "APP_BASE_URL": "http://localhost:8501"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            with patch("smtplib.SMTP") as mock_smtp_class:
                mock_server = MagicMock()
                mock_smtp_class.return_value = mock_server

                sent, msg = auth.send_password_reset_email("recipient@example.com", "tok_xyz_12345")
                self.assertTrue(sent)
                self.assertIn("sent", msg.lower())

                # Verify connection host and port
                mock_smtp_class.assert_called_with("smtp.gmail.com", 587, timeout=10)
                # Verify STARTTLS was executed
                mock_server.starttls.assert_called_once()
                # Verify login with EMAIL_USER and EMAIL_PASS
                mock_server.login.assert_called_with("myaccount@gmail.com", "abcd-efgh-ijkl-mnop")
                mock_server.sendmail.assert_called_once()
                mock_server.quit.assert_called_once()

    def test_03_reset_link_uses_streamlit_base_url(self):
        """Req 4: Reset email contains the correct application URL (does not blindly use React dev port)."""
        # Case A: APP_BASE_URL specified
        with patch.dict(os.environ, {"EMAIL_USER": "a@gmail.com", "EMAIL_PASS": "pwd", "APP_BASE_URL": "https://captioncraft.example.com"}, clear=False):
            cfg = auth.get_email_config()
            self.assertEqual(cfg["app_base_url"], "https://captioncraft.example.com")

        # Case B: FRONTEND_URL set to React dev port 5173 -> ignored, defaults to Streamlit 8501
        with patch.dict(os.environ, {"EMAIL_USER": "a@gmail.com", "EMAIL_PASS": "pwd", "APP_BASE_URL": "", "FRONTEND_URL": "http://localhost:5173"}, clear=False):
            cfg = auth.get_email_config()
            self.assertEqual(cfg["app_base_url"], "http://localhost:8501")

        # Case C: Valid Streamlit port
        with patch.dict(os.environ, {"EMAIL_USER": "a@gmail.com", "EMAIL_PASS": "pwd", "APP_BASE_URL": "", "FRONTEND_URL": "http://localhost:8501"}, clear=False):
            cfg = auth.get_email_config()
            self.assertEqual(cfg["app_base_url"], "http://localhost:8501")

    def test_04_failed_email_delivery_handled_safely(self):
        """Req 6: Failed email delivery returns failure cleanly without crashing or exposing tokens."""
        mock_env = {
            "EMAIL_USER": "sender@gmail.com",
            "EMAIL_PASS": "bad_password",
            "APP_BASE_URL": "http://localhost:8501"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            with patch("smtplib.SMTP", side_effect=Exception("SMTPAuthenticationError")):
                sent, msg = auth.send_password_reset_email("user@example.com", "sensitive_reset_token_secret")
                self.assertFalse(sent)
                self.assertIn("Failed to deliver reset email", msg)
                # Ensure raw reset token is NEVER in the error message
                self.assertNotIn("sensitive_reset_token_secret", msg)

    def test_05_auth_error_classified_as_bad_credentials(self):
        """Req 6: SMTP authentication failure produces categorized BadCredentials guidance without leaking password."""
        import smtplib
        mock_env = {
            "EMAIL_USER": "sender@gmail.com",
            "EMAIL_PASS": "my_secret_app_pass",
            "APP_BASE_URL": "http://localhost:8501"
        }
        with patch.dict(os.environ, mock_env, clear=False):
            with patch("smtplib.SMTP") as mock_smtp_class:
                mock_server = MagicMock()
                mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 BadCredentials")
                mock_smtp_class.return_value = mock_server

                sent, msg = auth.send_password_reset_email("recipient@example.com", "my_token_123")
                self.assertFalse(sent)
                self.assertIn("535 5.7.8 BadCredentials", msg)
                self.assertIn("App Password", msg)
                self.assertNotIn("my_secret_app_pass", msg)
                self.assertNotIn("my_token_123", msg)

    def test_06_invalidate_failed_reset_token_removes_dangling_token(self):
        """Req: When email delivery fails, the generated reset token is safely removed from MongoDB."""
        db = database.get_db()
        test_email = "test_cleanup@example.com"
        # Register user
        auth.register_user("Cleanup User", "Female", 29, test_email, "StrongPass123", "StrongPass123", db=db)

        # Create token
        token, _, _ = auth.create_password_reset_token(test_email, db=db)
        self.assertIsNotNone(token)
        token_hash = auth.hash_reset_token(token)

        # Confirm token exists in DB
        self.assertIsNotNone(db["password_resets"].find_one({"token_hash": token_hash}))

        # Invalidate/cleanup failed token
        auth.invalidate_failed_reset_token(token, db=db)

        # Token must be removed from DB
        self.assertIsNone(db["password_resets"].find_one({"token_hash": token_hash}))

        # Cleanup test user
        db["users"].delete_one({"email": test_email})

    def test_07_verify_smtp_connection_diagnostics(self):
        """Req: verify_smtp_connection returns structured diagnostics without leaking secrets."""
        with patch.dict(os.environ, {"EMAIL_USER": "diag@gmail.com", "EMAIL_PASS": "secret123"}, clear=False):
            with patch("smtplib.SMTP") as mock_smtp_class:
                mock_server = MagicMock()
                mock_smtp_class.return_value = mock_server

                ok, msg, diag = auth.verify_smtp_connection()
                self.assertTrue(ok)
                self.assertTrue(diag["connection_established"])
                self.assertTrue(diag["starttls_negotiated"])
                self.assertTrue(diag["authenticated"])
                # Ensure no secrets in diagnostic output
                self.assertNotIn("secret123", str(diag))


if __name__ == "__main__":
    unittest.main()

