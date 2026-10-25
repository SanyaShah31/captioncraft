"""
Authentication UI component for CaptionCraft AI.
Renders Registration, Login, Forgot Password, and Reset Password views
styled with the 60-30-10 color theme:
60% Warm Beige (#E8DCC6) background, 30% Forest Green (#1F3B2E) structural
elements & typography, and 10% Soft Lavender (#CBB3EB) primary CTAs & accents.
"""

import sys
from pathlib import Path

# Ensure backend and project root are discoverable
_FRONTEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _FRONTEND_DIR.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import auth
import database
from database import DatabaseConnectionError

# ---------------------------------------------------------------------------
# Stylesheet Loader — Spatial UI Authentication
# ---------------------------------------------------------------------------

STYLES_DIR = _FRONTEND_DIR / "styles"


def load_css(*filenames: str) -> None:
    """Loads external CSS stylesheets from the Frontend/styles directory."""
    for filename in filenames:
        css_path = STYLES_DIR / filename
        if not css_path.is_file():
            err_msg = f"Critical Error: Missing required stylesheet '{filename}' at {css_path}"
            st.error(err_msg)
            raise FileNotFoundError(err_msg)
        content = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>\n/* [{filename}] */\n{content}\n</style>", unsafe_allow_html=True)


def set_session_cookie(token: str, max_age: int = 604800) -> None:
    """Sets persistent session cookie in the user's browser."""
    import streamlit.components.v1 as components
    cookie_str = f"{auth.SESSION_COOKIE_NAME}={token}; path=/; max-age={max_age}; SameSite=Lax"
    js = f"""
    <script>
    try {{
        window.parent.document.cookie = "{cookie_str}";
    }} catch (e) {{
        document.cookie = "{cookie_str}";
    }}
    </script>
    """
    components.html(js, height=0)


def clear_session_cookie() -> None:
    """Clears persistent session cookie in the user's browser."""
    import streamlit.components.v1 as components
    cookie_str = f"{auth.SESSION_COOKIE_NAME}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax"
    js = f"""
    <script>
    try {{
        window.parent.document.cookie = "{cookie_str}";
    }} catch (e) {{
        document.cookie = "{cookie_str}";
    }}
    </script>
    """
    components.html(js, height=0)



def render_auth_page() -> None:
    """
    Renders the authentication workflow (Login, Register, Forgot Password, Reset Password).
    Maintains authentication state in st.session_state.
    """
    # Inject Spatial UI stylesheets (ensuring base + auth styles are active)
    load_css("main.css", "components.css", "auth.css", "responsive.css")

    # Clear cookie if triggered by logout
    if st.session_state.get("_clear_cookie", False):
        clear_session_cookie()
        st.session_state["_clear_cookie"] = False

    # Initialize auth state if not present
    if "auth_mode" not in st.session_state:
        # Check if reset_token is in URL query parameters
        query_token = st.query_params.get("reset_token")
        if query_token:
            st.session_state["auth_mode"] = "reset"
            st.session_state["reset_token_input"] = query_token
        else:
            st.session_state["auth_mode"] = "login"

    # Pre-check database connectivity safely
    db_connected, db_err = database.check_db_connection()
    if not db_connected:
        st.markdown(
            """
            <div class="auth-brand">
                <div class="auth-brand-name">✨ CaptionCraft AI</div>
                <div class="auth-brand-sub">Multimodal Viral Social Media Caption Generator</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.error(
            "⚠️ **Database Connection Unavailable**\n\n"
            "Unable to connect to the MongoDB database. Please ensure your MongoDB service is running and accessible."
        )
        st.info(
            "**Troubleshooting:**\n"
            "- Verify that MongoDB Server is started (e.g. `mongod` or the Windows MongoDB service).\n"
            "- Check the `MONGODB_URI` environment variable if using an external database."
        )
        if st.button("🔄 Retry Connection", use_container_width=True):
            st.rerun()
        return

    # Container centered for authentication card
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div class="auth-brand">
                <div class="auth-brand-icon-wrap">
                    <span class="auth-brand-icon">✨</span>
                </div>
                <div class="auth-brand-name">CaptionCraft AI</div>
                <div class="auth-brand-sub">
                    <span class="auth-sparkle-dot">✦</span>
                    <span>A little creativity goes a long way</span>
                    <span class="auth-sparkle-dot">✦</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        mode = st.session_state.get("auth_mode", "login")

        if mode == "login":
            _render_login_view()
        elif mode == "register":
            _render_register_view()
        elif mode == "forgot":
            _render_forgot_password_view()
        elif mode == "reset":
            _render_reset_password_view()


def _render_login_view() -> None:
    """Renders the user login form."""
    with st.form("login_form", clear_on_submit=False):
        st.markdown(
            """
            <div class="auth-card-header">
                <span class="auth-pill-badge">✨ Welcome Back</span>
                <h2 class="auth-card-title">Let's Sign You In</h2>
                <p class="auth-card-subtitle">Enter your credentials to craft scroll-stopping captions.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        email = st.text_input("Email Address", placeholder="creator@example.com").strip()
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign In ✨", use_container_width=True, type="primary")

    if submitted:
        success, message, user_info = auth.authenticate_user(email, password)
        if success and user_info:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_info
            st.session_state["_clear_cookie"] = False
            token, _ = auth.create_user_session(user_info["user_id"])
            if token:
                st.session_state["_set_cookie_token"] = token
                set_session_cookie(token)
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error(message)

    st.markdown('<div class="auth-footer-divider"><span>or explore</span></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔑 Forgot Password?", use_container_width=True):
            st.session_state["auth_mode"] = "forgot"
            st.rerun()
    with col_b:
        if st.button("✨ Create Account", use_container_width=True):
            st.session_state["auth_mode"] = "register"
            st.rerun()


def _render_register_view() -> None:
    """Renders the user registration form with validation."""
    with st.form("registration_form", clear_on_submit=False):
        st.markdown(
            """
            <div class="auth-card-header">
                <span class="auth-pill-badge">🌸 New Creator</span>
                <h2 class="auth-card-title">Create Your Account</h2>
                <p class="auth-card-subtitle">Your next creative chapter starts here.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        full_name = st.text_input("Full Name *", placeholder="Jane Doe")
        
        col_g, col_a = st.columns([1, 1])
        with col_g:
            gender = st.selectbox(
                "Gender *",
                options=["Male", "Female", "Prefer not to say"],
                index=0
            )
        with col_a:
            age = st.number_input("Age *", min_value=1, max_value=120, value=25, step=1)

        email = st.text_input("Email Address *", placeholder="jane@example.com")
        password = st.text_input("Password *", type="password", placeholder="At least 8 characters")
        confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password")

        registered = st.form_submit_button("Create Account ✨", use_container_width=True, type="primary")

    if registered:
        success, msg, safe_user = auth.register_user(
            full_name=full_name,
            gender=gender,
            age=age,
            email=email,
            password=password,
            confirm_password=confirm_password
        )
        if success:
            st.success("✅ " + msg)
            st.info("You can now proceed to log in with your credentials.")
            if st.button("Go to Login", type="primary", use_container_width=True):
                st.session_state["auth_mode"] = "login"
                st.rerun()
        else:
            st.error(msg)

    st.markdown('<div class="auth-footer-divider"><span>already registered?</span></div>', unsafe_allow_html=True)
    if st.button("✨ Already have an account? Log In", use_container_width=True):
        st.session_state["auth_mode"] = "login"
        st.rerun()


def _render_forgot_password_view() -> None:
    """Renders the forgot password request view."""
    with st.form("forgot_password_form"):
        st.markdown(
            """
            <div class="auth-card-header">
                <span class="auth-pill-badge">💌 Account Help</span>
                <h2 class="auth-card-title">Forgot Password?</h2>
                <p class="auth-card-subtitle">No worries! Enter your registered email to receive reset instructions.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        email = st.text_input("Registered Email Address", placeholder="creator@example.com").strip()
        requested = st.form_submit_button("Send Reset Link 💌", use_container_width=True, type="primary")

    if requested:
        if not email:
            st.error("Please enter an email address.")
        elif not auth.is_email_service_configured() and not auth.is_dev_mode():
            # Do NOT generate a token unnecessarily when SMTP is unavailable
            st.warning(
                "⚠️ **Password Reset Unavailable**\n\n"
                "Automated password-reset email delivery is currently not configured on this server. "
                "The email password reset feature is unavailable until SMTP settings are configured in the environment. "
                "Please contact your system administrator."
            )
        else:
            # SMTP is configured (or explicit local development mode is active)
            token, user_doc, expires_at = auth.create_password_reset_token(email)

            if not token:
                # User is not registered: keep response generic to prevent account enumeration
                st.info("If an account exists for this email, password-reset instructions will be sent.")
            elif auth.is_email_service_configured():
                # Attempt email delivery via Gmail SMTP
                with st.spinner("Sending password reset email via Gmail SMTP..."):
                    sent, status_msg = auth.send_password_reset_email(email, token)

                if sent:
                    st.success(
                        "✅ **Reset Email Sent**\n\n"
                        "Password-reset instructions have been sent to your email address via Gmail SMTP. "
                        "Please check your inbox and Spam folder."
                    )
                else:
                    # Invalidate the failed token so the user can safely request a fresh reset
                    auth.invalidate_failed_reset_token(token)
                    st.error(
                        f"❌ **Email Delivery Failed**\n\n"
                        f"{status_msg}\n\n"
                        "The reset token was not dispatched. You may submit the form again once the issue is resolved."
                    )
            elif auth.is_dev_mode():
                # In explicit local development mode only, record token to local dev file (never displayed in UI)
                auth.record_dev_reset_token(token, email)
                st.info("If an account exists for this email, password-reset instructions will be sent.")
                st.caption("🛠️ *Development mode active: reset token recorded in `.dev_reset_token.txt`.*")

    st.markdown('<div class="auth-footer-divider"><span>or go back</span></div>', unsafe_allow_html=True)
    col_x, col_y = st.columns(2)
    with col_x:
        if st.button("🔑 Have a Reset Token?", use_container_width=True):
            if "reset_token_input" in st.session_state:
                del st.session_state["reset_token_input"]
            st.session_state["auth_mode"] = "reset"
            st.rerun()
    with col_y:
        if st.button("↩️ Back to Login", use_container_width=True):
            st.session_state["auth_mode"] = "login"
            st.rerun()


def _render_reset_password_view() -> None:
    """Renders the password reset form using a secure token."""
    initial_token = st.session_state.get("reset_token_input", "")

    with st.form("reset_password_form"):
        st.markdown(
            """
            <div class="auth-card-header">
                <span class="auth-pill-badge">🔐 New Key</span>
                <h2 class="auth-card-title">Reset Your Password</h2>
                <p class="auth-card-subtitle">Enter your 32-character token and pick a strong new password.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        token = st.text_input("Reset Token", value=initial_token, placeholder="Paste your 32-character token here").strip()
        new_password = st.text_input("New Password", type="password", placeholder="At least 8 characters")
        confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
        reset_submitted = st.form_submit_button("Update Password ✨", use_container_width=True, type="primary")

    if reset_submitted:
        success, message = auth.reset_password_with_token(token, new_password, confirm_password)
        if success:
            st.success("✅ " + message)
            st.info("You can now proceed to log in with your new password.")
            if "reset_token_input" in st.session_state:
                del st.session_state["reset_token_input"]
            try:
                st.query_params.clear()
            except Exception:
                pass
        else:
            st.error(message)

    st.markdown('<div class="auth-footer-divider"><span>or go back</span></div>', unsafe_allow_html=True)
    if st.button("↩️ Back to Login", use_container_width=True):
        st.session_state["auth_mode"] = "login"
        st.rerun()
