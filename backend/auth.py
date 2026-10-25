"""
Authentication module for CaptionCraft AI.
Handles user registration, credential validation, bcrypt password hashing,
authentication, secure single-use password reset tokens, and email notifications.
"""

import os
import sys
from pathlib import Path
import re
import uuid
import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv, find_dotenv

import bcrypt
from pymongo.errors import DuplicateKeyError
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Ensure project root and backend are on sys.path and .env is loaded
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_root_env = _PROJECT_ROOT / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env)
else:
    load_dotenv(find_dotenv(usecwd=True))

import database

# Regex for email validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
VALID_GENDERS = ["Male", "Female", "Prefer not to say"]
MIN_PASSWORD_LENGTH = 8
RESET_TOKEN_EXPIRY_MINUTES = 15


# ---------------------------------------------------------------------
# Normalization & Password Hashing
# ---------------------------------------------------------------------

def normalize_email(email: Optional[str]) -> str:
    """Consistently trims whitespace and converts email to lowercase."""
    if not email:
        return ""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def hash_reset_token(token: str) -> str:
    """Computes SHA-256 hash of a reset token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# Field Validations
# ---------------------------------------------------------------------

def validate_registration_fields(
    full_name: str,
    gender: str,
    age: Any,
    email: str,
    password: str,
    confirm_password: str
) -> Tuple[bool, Optional[str]]:
    """
    Validates all registration fields.
    Returns: (is_valid, error_message_or_none)
    """
    # 1. Full Name
    if not full_name or not full_name.strip():
        return False, "Full Name is required and cannot be empty."
    if len(full_name.strip()) < 2:
        return False, "Full Name must be at least 2 characters long."

    # 2. Gender
    if gender not in VALID_GENDERS:
        return False, f"Gender must be one of: {', '.join(VALID_GENDERS)}."

    # 3. Age
    try:
        age_int = int(age)
        if age_int < 1 or age_int > 120:
            return False, "Age must be a valid positive integer between 1 and 120."
    except (ValueError, TypeError):
        return False, "Age must be a valid positive integer."

    # 4. Email
    norm_email = normalize_email(email)
    if not norm_email or not EMAIL_REGEX.match(norm_email):
        return False, "Please enter a valid email address."

    # 5. Password
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."

    # 6. Confirm Password
    if password != confirm_password:
        return False, "Password and Confirm Password do not match."

    return True, None


def validate_login_fields(email: str, password: str) -> Tuple[bool, Optional[str]]:
    """Validates login inputs are non-empty."""
    if not email or not email.strip():
        return False, "Email Address is required."
    if not password:
        return False, "Password is required."
    return True, None


# ---------------------------------------------------------------------
# User Registration
# ---------------------------------------------------------------------

def register_user(
    full_name: str,
    gender: str,
    age: Any,
    email: str,
    password: str,
    confirm_password: str,
    db: Optional[Any] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new user in MongoDB.
    Validates fields, normalizes email, enforces email uniqueness,
    and stores bcrypt password hash.
    Never stores confirm_password.
    Returns: (success, message, created_user_info_without_password)
    """
    # Validate fields
    is_valid, err = validate_registration_fields(
        full_name=full_name,
        gender=gender,
        age=age,
        email=email,
        password=password,
        confirm_password=confirm_password
    )
    if not is_valid:
        return False, err or "Validation failed.", None

    norm_email = normalize_email(email)
    age_int = int(age)

    database_inst = db if db is not None else database.get_db()
    users_col = database_inst["users"]

    # Pre-check for duplicate email in application code
    existing = users_col.find_one({"email": norm_email})
    if existing:
        return False, "This email address is already registered. Please log in or use another email.", None

    pwd_hash = hash_password(password)
    user_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc)

    user_doc = {
        "user_id": user_id,
        "full_name": full_name.strip(),
        "gender": gender,
        "age": age_int,
        "email": norm_email,
        "password_hash": pwd_hash,
        "created_at": now_utc
    }

    try:
        users_col.insert_one(user_doc)
    except DuplicateKeyError:
        return False, "This email address is already registered. Please log in or use another email.", None
    except Exception as e:
        return False, "Registration failed due to a database error. Please try again.", None

    safe_user = {
        "user_id": user_id,
        "full_name": full_name.strip(),
        "gender": gender,
        "age": age_int,
        "email": norm_email,
        "created_at": now_utc
    }
    return True, "Registration successful! You can now log in.", safe_user


# ---------------------------------------------------------------------
# User Authentication / Login
# ---------------------------------------------------------------------

def authenticate_user(
    email: str,
    password: str,
    db: Optional[Any] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates a user by email and password.
    Returns generic error message for invalid credentials or unregistered email.
    Never stores or returns password hash in session info.
    Returns: (success, message, safe_user_info)
    """
    is_valid, err = validate_login_fields(email, password)
    if not is_valid:
        return False, err or "Please provide email and password.", None

    norm_email = normalize_email(email)
    database_inst = db if db is not None else database.get_db()
    users_col = database_inst["users"]

    user_doc = users_col.find_one({"email": norm_email})
    if not user_doc:
        return False, "Invalid email or password.", None

    stored_hash = user_doc.get("password_hash", "")
    if not verify_password(password, stored_hash):
        return False, "Invalid email or password.", None

    safe_user = {
        "user_id": user_doc.get("user_id"),
        "full_name": user_doc.get("full_name"),
        "gender": user_doc.get("gender"),
        "age": user_doc.get("age"),
        "email": user_doc.get("email"),
        "created_at": user_doc.get("created_at")
    }
    return True, "Login successful.", safe_user


# ---------------------------------------------------------------------
# Forgot Password & Reset Token Management
# ---------------------------------------------------------------------

def create_password_reset_token(
    email: str,
    db: Optional[Any] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[datetime]]:
    """
    Creates a cryptographically secure, single-use password reset token.
    Stores the SHA-256 hash of the token in MongoDB with a 15-minute expiration.
    Invalidates any existing active reset tokens for this user.
    Returns: (plain_token, user_doc, expires_at) or (None, None, None) if user not found.
    """
    norm_email = normalize_email(email)
    database_inst = db if db is not None else database.get_db()
    users_col = database_inst["users"]
    resets_col = database_inst["password_resets"]

    user_doc = users_col.find_one({"email": norm_email})
    if not user_doc:
        return None, None, None

    # Generate secure 32-byte URL-safe token
    plain_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(plain_token)
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

    # Invalidate existing active tokens for this user
    resets_col.update_many(
        {"email": norm_email, "used": False},
        {"$set": {"used": True}}
    )

    reset_record = {
        "user_id": user_doc.get("user_id"),
        "email": norm_email,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
        "created_at": now_utc
    }
    resets_col.insert_one(reset_record)

    return plain_token, user_doc, expires_at


def verify_reset_token(
    token: str,
    db: Optional[Any] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Verifies that a password reset token exists, is not used, and is not expired.
    Returns: (is_valid, reset_doc, error_message)
    """
    if not token or not token.strip():
        return False, None, "Invalid password reset token."

    token_hash = hash_reset_token(token.strip())
    database_inst = db if db is not None else database.get_db()
    resets_col = database_inst["password_resets"]

    reset_doc = resets_col.find_one({"token_hash": token_hash})
    if not reset_doc:
        return False, None, "The password reset link is invalid or has already been used."

    if reset_doc.get("used", False):
        return False, None, "The password reset link has already been used."

    expires_at = reset_doc.get("expires_at")
    if expires_at:
        # Handle timezone-aware vs naive comparisons
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return False, None, "The password reset link has expired. Please request a new one."

    return True, reset_doc, None


def reset_password_with_token(
    token: str,
    new_password: str,
    confirm_password: str,
    db: Optional[Any] = None
) -> Tuple[bool, str]:
    """
    Validates token and updates user password with a new bcrypt hash.
    Immediately invalidates the token.
    Returns: (success, message)
    """
    # Validate token
    is_valid, reset_doc, err = verify_reset_token(token, db=db)
    if not is_valid or not reset_doc:
        return False, err or "Invalid or expired reset token."

    # Validate new password
    if not new_password or len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if new_password != confirm_password:
        return False, "Password and Confirm Password do not match."

    email = reset_doc.get("email")
    new_hash = hash_password(new_password)

    database_inst = db if db is not None else database.get_db()
    users_col = database_inst["users"]
    resets_col = database_inst["password_resets"]

    # Update user password
    update_res = users_col.update_one(
        {"email": email},
        {"$set": {"password_hash": new_hash}}
    )
    if update_res.matched_count == 0:
        return False, "Associated user account was not found."

    # Invalidate reset token immediately
    resets_col.update_one(
        {"_id": reset_doc["_id"]},
        {"$set": {"used": True}}
    )

    return True, "Your password has been successfully reset. Please log in with your new password."


# ---------------------------------------------------------------------
# Email Delivery
# ---------------------------------------------------------------------

def get_email_config() -> Dict[str, Any]:
    """
    Reads Gmail SMTP settings from environment variables.
    Supports EMAIL_USER and EMAIL_PASS as the primary Gmail sender credentials.
    Falls back to legacy SMTP_USERNAME/SMTP_PASSWORD if provided.
    Defaults to smtp.gmail.com:587 with STARTTLS.
    """
    email_user = os.getenv("EMAIL_USER", "").strip() or os.getenv("SMTP_USERNAME", "").strip()
    email_pass = os.getenv("EMAIL_PASS", "").strip() or os.getenv("SMTP_PASSWORD", "").strip()
    host = os.getenv("SMTP_HOST", "").strip() or "smtp.gmail.com"
    try:
        port = int(os.getenv("SMTP_PORT", "587").strip() or 587)
    except (ValueError, TypeError):
        port = 587

    # Construct application base URL for the password reset link
    base_url = os.getenv("APP_BASE_URL", "").strip()
    if not base_url:
        fe_url = os.getenv("FRONTEND_URL", "").strip()
        # Avoid blind React dev port 5173 for Streamlit app
        if fe_url and ":5173" not in fe_url:
            base_url = fe_url
        else:
            base_url = "http://localhost:8501"

    return {
        "host": host,
        "port": port,
        "username": email_user,
        "password": email_pass,
        "from_email": email_user,
        "use_tls": True,
        "app_base_url": base_url.rstrip("/")
    }


def is_email_service_configured() -> bool:
    """Checks whether Gmail SMTP delivery credentials (EMAIL_USER and EMAIL_PASS) are configured."""
    cfg = get_email_config()
    return bool(cfg["host"] and cfg["username"] and cfg["password"])


def is_dev_mode() -> bool:
    """Checks whether explicit local development mode is enabled via environment."""
    return os.getenv("AUTH_DEV_MODE", "false").strip().lower() in ("true", "1", "yes")


def record_dev_reset_token(token: str, email: str) -> bool:
    """
    In explicit development mode only, records the token to a local developer file
    so a developer can test token verification without an external SMTP server.
    Disabled by default and strictly never used in production.
    """
    if not is_dev_mode():
        return False
    try:
        dev_file = os.path.join(os.path.dirname(__file__), ".dev_reset_token.txt")
        with open(dev_file, "w", encoding="utf-8") as f:
            f.write(f"EMAIL={email}\nTOKEN={token}\nURL=http://localhost:8501/?reset_token={token}\n")
        return True
    except Exception:
        return False


def invalidate_failed_reset_token(plain_token: str, db: Optional[Any] = None) -> None:
    """
    Safely invalidates or deletes a reset token if SMTP email delivery fails,
    preventing stale, unusable tokens from lingering in the database.
    """
    if not plain_token:
        return
    token_hash = hash_reset_token(plain_token)
    try:
        database_inst = db if db is not None else database.get_db()
        resets_col = database_inst["password_resets"]
        resets_col.delete_one({"token_hash": token_hash})
    except Exception:
        pass


def send_password_reset_email(
    email: str,
    reset_token: str
) -> Tuple[bool, str]:
    """
    Sends password reset instructions and link to the user's email via Gmail SMTP.
    Includes multipart plain-text and HTML versions.
    Provides categorized, actionable error messages without leaking credentials.
    Returns: (sent, status_message)
    """
    cfg = get_email_config()
    if not is_email_service_configured():
        return False, (
            "Gmail SMTP service is not configured (missing EMAIL_USER or EMAIL_PASS in environment). "
            "Please configure EMAIL_USER and EMAIL_PASS with a valid Gmail account and App Password."
        )

    reset_url = f"{cfg['app_base_url']}/?reset_token={reset_token}"
    subject = "CaptionCraft AI — Password Reset Request"

    body_text = (
        f"CaptionCraft AI — Password Reset\n\n"
        f"We received a request to reset your password. Click the link below to set a new password:\n"
        f"{reset_url}\n\n"
        f"This link will expire in {RESET_TOKEN_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request this password reset, please ignore this email."
    )

    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 540px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #6366f1;">
          <h2 style="color: #c084fc;">CaptionCraft AI — Password Reset</h2>
          <p>We received a request to reset your password. Click the link below to set a new password:</p>
          <p style="text-align: center; margin: 24px 0;">
            <a href="{reset_url}" style="background: linear-gradient(135deg, #6366F1, #EC4899); color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
              Reset Password
            </a>
          </p>
          <p style="font-size: 0.9em; color: #94a3b8;">This link will expire in {RESET_TOKEN_EXPIRY_MINUTES} minutes.</p>
          <p style="font-size: 0.85em; color: #64748b;">If you did not request this password reset, please ignore this email.</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = email
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
        server.ehlo()
        if cfg["use_tls"]:
            server.starttls()
            server.ehlo()

        clean_password = cfg["password"].replace(" ", "")
        try:
            server.login(cfg["username"], clean_password)
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected) as auth_err:
            try:
                server.close()
            except Exception:
                pass
            return False, (
                "Gmail SMTP authentication failed (535 5.7.8 BadCredentials). "
                "Please verify that EMAIL_USER is your full Gmail address and EMAIL_PASS is a valid 16-character Google App Password "
                "generated from https://myaccount.google.com/apppasswords with 2-Step Verification enabled on your Google account."
            )

        server.sendmail(cfg["from_email"], [email], msg.as_string())
        server.quit()
        return True, "Password reset instructions have been sent and accepted by the Gmail SMTP server for delivery."

    except (smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as send_err:
        return False, f"Gmail SMTP message delivery was rejected ({type(send_err).__name__})."
    except (smtplib.SMTPConnectError, TimeoutError, OSError) as net_err:
        return False, f"Could not connect to Gmail SMTP server at {cfg['host']}:{cfg['port']} ({type(net_err).__name__}). Please check internet connectivity."
    except Exception as e:
        return False, f"Failed to deliver reset email due to SMTP error: {type(e).__name__}."


def verify_smtp_connection(
    test_recipient: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Performs a safe, non-destructive diagnostic check of the Gmail SMTP connection.
    Tests network reachability, STARTTLS negotiation, and credentials authentication.
    Optionally sends a harmless test message without a password reset token.
    Never exposes credentials or secrets in output.
    Returns: (is_successful, message, diagnostic_details)
    """
    cfg = get_email_config()
    diag: Dict[str, Any] = {
        "host": cfg["host"],
        "port": cfg["port"],
        "email_user_configured": bool(cfg["username"]),
        "email_pass_configured": bool(cfg["password"]),
        "use_tls": cfg["use_tls"],
        "connection_established": False,
        "starttls_negotiated": False,
        "authenticated": False,
        "test_email_submitted": False
    }

    if not is_email_service_configured():
        return False, "SMTP configuration incomplete (missing EMAIL_USER or EMAIL_PASS).", diag

    try:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=12)
        server.ehlo()
        diag["connection_established"] = True

        if cfg["use_tls"]:
            server.starttls()
            server.ehlo()
            diag["starttls_negotiated"] = True

        clean_password = cfg["password"].replace(" ", "")
        try:
            server.login(cfg["username"], clean_password)
            diag["authenticated"] = True
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected):
            try:
                server.close()
            except Exception:
                pass
            return False, (
                "Gmail SMTP rejected login credentials (535 BadCredentials). "
                "Ensure EMAIL_USER is your full Gmail address and EMAIL_PASS is a 16-character Google App Password with 2-Step Verification enabled."
            ), diag

        if test_recipient:
            test_msg = MIMEMultipart()
            test_msg["Subject"] = "CaptionCraft AI — Gmail SMTP Diagnostic Test"
            test_msg["From"] = cfg["from_email"]
            test_msg["To"] = test_recipient
            test_msg.attach(MIMEText("This is an automated diagnostic test email from CaptionCraft AI verifying that Gmail SMTP delivery is functioning correctly.", "plain"))
            server.sendmail(cfg["from_email"], [test_recipient], test_msg.as_string())
            diag["test_email_submitted"] = True

        server.quit()
        return True, "Gmail SMTP connection and authentication verified successfully.", diag

    except Exception as e:
        return False, f"SMTP diagnostic failed ({type(e).__name__}): {str(e)}", diag


# ---------------------------------------------------------------------
# Persistent Browser Session Management
# ---------------------------------------------------------------------

SESSION_COOKIE_NAME = "captioncraft_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def get_session_serializer() -> URLSafeTimedSerializer:
    """Returns a timed cryptographic serializer for persistent session tokens."""
    secret = (
        os.getenv("SESSION_SECRET")
        or os.getenv("JWT_SECRET")
        or hashlib.sha256(
            (os.getenv("CLOUDINARY_API_SECRET", "") + os.getenv("MONGODB_DATABASE", "captioncraft_db") + "captioncraft_session_key_v1").encode("utf-8")
        ).hexdigest()
    )
    return URLSafeTimedSerializer(secret, salt="captioncraft_session_signer")


def create_user_session(
    user_id: str,
    db: Optional[Any] = None
) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Creates a cryptographically signed persistent session token for the user.
    Stores the SHA-256 hash of the token in MongoDB user_sessions with expiration.
    Returns: (session_token, expires_at)
    """
    if not user_id:
        return None, None

    database_inst = db if db is not None else database.get_db()
    users_col = database_inst["users"]
    user_doc = users_col.find_one({"user_id": user_id})
    if not user_doc:
        return None, None

    serializer = get_session_serializer()
    session_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(seconds=SESSION_MAX_AGE_SECONDS)

    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "created_at": now_utc.isoformat()
    }
    session_token = serializer.dumps(payload)
    token_hash = hash_reset_token(session_token)

    sessions_col = database_inst["user_sessions"]
    session_record = {
        "user_id": user_id,
        "session_id": session_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_at": now_utc,
        "active": True
    }
    sessions_col.insert_one(session_record)

    return session_token, expires_at


def verify_user_session(
    session_token: Optional[str],
    db: Optional[Any] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifies a persistent session token:
    1. Cryptographically verifies signature and max age.
    2. Validates session state against MongoDB user_sessions.
    3. Confirms user account exists and is valid.
    Returns: (is_valid, safe_user_info)
    """
    if not session_token or not isinstance(session_token, str) or not session_token.strip():
        return False, None

    clean_token = session_token.strip()
    serializer = get_session_serializer()

    try:
        payload = serializer.loads(clean_token, max_age=SESSION_MAX_AGE_SECONDS)
    except (SignatureExpired, BadSignature, Exception):
        return False, None

    user_id = payload.get("user_id")
    if not user_id:
        return False, None

    try:
        database_inst = db if db is not None else database.get_db()
        sessions_col = database_inst["user_sessions"]
        token_hash = hash_reset_token(clean_token)

        session_doc = sessions_col.find_one({"token_hash": token_hash, "active": True})
        if not session_doc:
            return False, None

        expires_at = session_doc.get("expires_at")
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                sessions_col.update_one({"token_hash": token_hash}, {"$set": {"active": False}})
                return False, None

        users_col = database_inst["users"]
        user_doc = users_col.find_one({"user_id": user_id})
        if not user_doc:
            return False, None

        safe_user = {
            "user_id": user_doc.get("user_id"),
            "full_name": user_doc.get("full_name"),
            "gender": user_doc.get("gender"),
            "age": user_doc.get("age"),
            "email": user_doc.get("email"),
            "created_at": user_doc.get("created_at")
        }
        return True, safe_user
    except Exception:
        return False, None


def invalidate_user_session(
    session_token: Optional[str],
    db: Optional[Any] = None
) -> bool:
    """
    Immediately invalidates an active session in MongoDB.
    """
    if not session_token or not isinstance(session_token, str):
        return False

    clean_token = session_token.strip()
    token_hash = hash_reset_token(clean_token)

    try:
        database_inst = db if db is not None else database.get_db()
        sessions_col = database_inst["user_sessions"]
        res = sessions_col.update_many(
            {"token_hash": token_hash},
            {"$set": {"active": False, "invalidated_at": datetime.now(timezone.utc)}}
        )
        return res.modified_count > 0
    except Exception:
        return False


def invalidate_all_user_sessions(
    user_id: str,
    db: Optional[Any] = None
) -> bool:
    """
    Invalidates all active sessions for a given user.
    """
    if not user_id:
        return False

    try:
        database_inst = db if db is not None else database.get_db()
        sessions_col = database_inst["user_sessions"]
        res = sessions_col.update_many(
            {"user_id": user_id, "active": True},
            {"$set": {"active": False, "invalidated_at": datetime.now(timezone.utc)}}
        )
        return res.modified_count > 0
    except Exception:
        return False

