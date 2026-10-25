"""
CaptionCraft AI — Multimodal Caption Generator
Streamlit application with 60-30-10 color theme:
60% Warm Beige (#E8DCC6) background, 30% Forest Green (#1F3B2E) structural
elements & typography, and 10% Soft Lavender (#CBB3EB) primary CTAs & accents.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure backend, frontend, and project root are always available on sys.path
_FRONTEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _FRONTEND_DIR.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
from datetime import datetime, date
from PIL import Image

# Initialize page config as early as possible
st.set_page_config(
    page_title="CaptionCraft AI — Multimodal Caption Generator",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

from prompt_templates import PLATFORMS, TONES, LENGTHS
import ai_service
import utils
import auth
import auth_ui
import cloudinary_service

# ---------------------------------------------------------------------
# External Stylesheet Loader (Spatial UI Design System)
# ---------------------------------------------------------------------

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


# Load core stylesheets
load_css("main.css", "components.css", "responsive.css")

# ---------------------------------------------------------------------
# Session State Initialization & Persistent Authentication Restoration
# ---------------------------------------------------------------------

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Generate"
if "generated_captions" not in st.session_state:
    st.session_state["generated_captions"] = []
if "latest_generation_meta" not in st.session_state:
    st.session_state["latest_generation_meta"] = None
if "selected_emojis" not in st.session_state:
    st.session_state["selected_emojis"] = "✨ 🚀 🔥"
if "sidebar_api_key" not in st.session_state:
    st.session_state["sidebar_api_key"] = ""
if "active_tab_index" not in st.session_state:
    st.session_state["active_tab_index"] = 0
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None

# Restore persistent browser session from secure cookie if unauthenticated
if not st.session_state.get("authenticated", False):
    cookie_session_token = st.context.cookies.get(auth.SESSION_COOKIE_NAME)
    if cookie_session_token:
        is_valid, user_info = auth.verify_user_session(cookie_session_token)
        if is_valid and user_info:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_info

# If a fresh login just occurred, ensure session cookie is committed
if st.session_state.get("_set_cookie_token"):
    auth_ui.set_session_cookie(st.session_state.pop("_set_cookie_token"))

# ---------------------------------------------------------------------
# Authentication Guard (Protects Application from Unauthenticated Access)
# ---------------------------------------------------------------------

if not st.session_state.get("authenticated", False):
    auth_ui.render_auth_page()
    st.stop()

# ---------------------------------------------------------------------
# Sidebar Navigation & Controls
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="brand-badge">✨ CaptionCraft AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Multimodal Viral Social Media Caption Generator</div>', unsafe_allow_html=True)

    # Logged-in User Profile Badge & Logout
    user_info = st.session_state.get("user") or {}
    user_name = user_info.get("full_name", "Creator")
    user_email = user_info.get("email", "")

    st.markdown(
        f"""
        <div class="user-badge">
            <div class="user-badge-name">👤 {user_name}</div>
            <div class="user-badge-email">{user_email}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout_btn"):
        cookie_session_token = st.context.cookies.get(auth.SESSION_COOKIE_NAME)
        if cookie_session_token:
            auth.invalidate_user_session(cookie_session_token)
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["auth_mode"] = "login"
        st.session_state["_clear_cookie"] = True
        auth_ui.clear_session_cookie()
        st.rerun()

    st.markdown("---")

    # Navigation Radio
    nav_options = [
        "⚡ Generate",
        "🏠 Home",
        "📜 History",
        "⭐ Favorites",
        "ℹ️ About"
    ]
    # Match current page to select radio
    current_nav_index = 0
    for idx, opt in enumerate(nav_options):
        if st.session_state["current_page"] in opt:
            current_nav_index = idx

    selected_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=current_nav_index,
        label_visibility="collapsed"
    )

    clean_page = selected_nav.split()[-1]
    st.session_state["current_page"] = clean_page

    st.markdown("---")

    # API Key Configuration Section
    env_key_found = ai_service.is_api_key_configured()
    
    st.markdown('<div class="sidebar-heading">🔑 Gemini API Status</div>', unsafe_allow_html=True)
    if env_key_found:
        st.success("API Key Active (via .env / system)")
    else:
        st.warning("API Key Not Detected in .env")

    with st.expander("⚙️ Configure API Key", expanded=not env_key_found):
        st.caption("Provide your Google Gemini API key if not configured in `.env`.")
        entered_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("sidebar_api_key", ""),
            type="password",
            placeholder="AIzaSy...",
            help="Free key available from Google AI Studio"
        )
        if entered_key:
            st.session_state["sidebar_api_key"] = entered_key
            st.info("Using session API key")
        st.markdown("[Get free Gemini Key ↗](https://aistudio.google.com/app/apikey)")

    # Model Selection
    selected_model = st.selectbox(
        "Gemini Model",
        options=["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"],
        index=0,
        help="Fast multimodal models with advanced reasoning and visual understanding."
    )

    st.markdown("---")

    # Realtime Quick Stats
    current_user_id = (st.session_state.get("user") or {}).get("user_id")
    history_items = utils.get_history(user_id=current_user_id)
    fav_items = utils.get_favorites()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(history_items)}</div>
            <div class="stat-label">Batches</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(fav_items)}</div>
            <div class="stat-label">Favorites</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Built with Python, Streamlit & Google Gemini Multimodal SDK.")

# Effective API Key
effective_api_key = ai_service.get_api_key(st.session_state.get("sidebar_api_key"))

# ---------------------------------------------------------------------
# Application-Owned Integrated Header
# ---------------------------------------------------------------------

def render_app_header(title: str, subtitle: Optional[str] = None, badge: Optional[str] = None):
    """Renders the unified, application-owned header integrated into the main canvas."""
    badge_html = f'<span class="tag-badge tag-badge-accent">{badge}</span>' if badge else ""
    sub_html = f'<p class="app-header-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div class="app-header">
        <h1 class="app-header-title">{title} {badge_html}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Page: HOME
# ---------------------------------------------------------------------

def render_home_page():
    render_app_header(
        title="✨ Welcome to CaptionCraft AI",
        subtitle="Multimodal social media caption generator powered by Google Gemini vision intelligence."
    )
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">Craft Scroll-Stopping Captions with Multimodal AI</div>
        <div class="hero-desc">
            Transform ideas and photos into high-converting social media captions in seconds.
            Powered by Google Gemini multimodal vision, tailored across 8 platforms and 8 distinct tones.
        </div>
        <div>
            <span class="feature-badge">⚡ Text-to-Caption</span>
            <span class="feature-badge">🖼️ Image Vision Analysis</span>
            <span class="feature-badge">⭐ Favorites & History</span>
            <span class="feature-badge">📋 One-Click Copy</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🚀 Start Generating Captions", type="primary", use_container_width=True):
            st.session_state["current_page"] = "Generate"
            st.rerun()

    st.markdown("### 🌟 Specialized Generation Modes")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="glass-card">
            <h3 class="mode-title-text">✍️ Text-to-Caption</h3>
            <p class="mode-desc">
                Turn concepts, topics, or rough notes into 5 targeted captions. Fine-tune by tone, character length, platform, and hashtag density.
            </p>
            <span class="meta-pill">8 Tones</span>
            <span class="meta-pill">8 Platforms</span>
            <span class="meta-pill">Hashtags & Emojis</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="glass-card">
            <h3 class="mode-title-img">🖼️ Image-to-Caption</h3>
            <p class="mode-desc">
                Upload JPG, PNG, or WebP images. Gemini's visual reasoning scans composition, lighting, emotions, and subtle details to generate authentic copy.
            </p>
            <span class="meta-pill">Multimodal Vision</span>
            <span class="meta-pill">Format Validated</span>
            <span class="meta-pill">Context Merging</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💡 Why Multimodal Caption Generation?")
    c_a, c_b = st.columns(2)
    with c_a:
        st.markdown("""
        - **Algorithm-Optimized Hooks**: Put the punchiest sentence in line 1 before the fold.
        - **Format Awareness**: LinkedIn paragraphs are spaced for scanability, while Twitter/X enforces 280-char limits.
        - **Hashtag Intelligence**: Relevant, niche-targeted hashtags rather than banned or generic spam tags.
        """)
    with c_b:
        st.markdown("""
        - **Visual Sentiment Extraction**: Recognizes aesthetic palettes (e.g. golden hour, minimalism, moody neon).
        - **Zero Data Loss**: Caption history and favorites are saved locally in structured JSON.
        - **Privacy First**: Your API keys and data remain on your machine.
        """)

# ---------------------------------------------------------------------
# Helper: Render Caption Cards
# ---------------------------------------------------------------------

def render_caption_cards(captions: list):
    """Renders 5 interactive caption cards with copy, favorite, and metrics."""
    if not captions:
        return

    st.markdown(f"### 🎉 Generated Captions ({len(captions)} Unique Options)")
    
    # Quick Batch Actions
    col_act1, col_act2, _ = st.columns([1.5, 1.5, 4])
    with col_act1:
        if st.button("🔄 Regenerate", help="Re-run with the exact same inputs"):
            meta = st.session_state.get("latest_generation_meta")
            if meta:
                st.session_state["trigger_regenerate"] = True
                st.rerun()
    with col_act2:
        if st.button("🗑️ Clear Results"):
            st.session_state["generated_captions"] = []
            st.session_state["latest_generation_meta"] = None
            st.rerun()

    for item in captions:
        cid = item.get("id")
        cap_text = item.get("caption", "")
        hook = item.get("hook", "")
        vibe = item.get("vibe_label", "Option")
        hashtags = item.get("hashtags", [])
        cta = item.get("cta", "")
        platform = item.get("platform", "Social")
        tone = item.get("tone", "Creative")
        
        metrics = utils.calculate_text_metrics(cap_text)
        is_fav = utils.is_favorite(cid)

        # Card container
        with st.container():
            st.markdown(f"""
            <div class="caption-card">
                <div class="caption-card-header">
                    <div>
                        <span class="tag-badge tag-badge-accent">
                            {vibe}
                        </span>
                        <span class="meta-pill">{platform}</span>
                        <span class="meta-pill">{tone}</span>
                    </div>
                    <div class="caption-metrics">
                        {metrics['characters']} chars • {metrics['words']} words
                    </div>
                </div>
                <div class="hook-text">"{hook}"</div>
                <div class="body-caption">{cap_text}</div>
            """, unsafe_allow_html=True)

            if hashtags:
                ht_html = "".join([f'<span class="tag-badge">#{h.lstrip("#")}</span>' for h in hashtags])
                st.markdown(f'<div class="hashtags-container">{ht_html}</div>', unsafe_allow_html=True)

            if cta:
                st.markdown(f'<div class="suggested-cta-box"><b>💡 Suggested CTA:</b> {cta}</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Interactive action buttons per card
            b_col1, b_col2, b_col3 = st.columns([1.2, 1.2, 5])

            with b_col1:
                # Copy friendly display
                with st.popover("📋 Copy Text"):
                    st.text_area(
                        "Ready to paste",
                        value=cap_text,
                        height=120,
                        key=f"copy_area_{cid}"
                    )
                    st.caption("Click into box and press Ctrl+A / Ctrl+C to copy.")

            with b_col2:
                fav_label = "❤️ Saved" if is_fav else "🤍 Favorite"
                if st.button(fav_label, key=f"fav_btn_{cid}"):
                    if is_fav:
                        utils.remove_favorite(cid)
                        st.toast(f"Removed from Favorites", icon="🗑️")
                    else:
                        utils.add_favorite({
                            "id": cid,
                            "caption": cap_text,
                            "hook": hook,
                            "vibe_label": vibe,
                            "hashtags": hashtags,
                            "cta": cta,
                            "platform": platform,
                            "tone": tone
                        })
                        st.toast(f"Saved to Favorites!", icon="⭐")
                    st.rerun()

            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Feature-Specific History Component
# ---------------------------------------------------------------------

def render_feature_history(user_id: Optional[str], feature_type: str, feature_label: str, key_prefix: str):
    """
    Renders feature-specific history for the authenticated user inside the generation tab.
    Strictly displays only the records belonging to the authenticated user and feature.
    """
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### 📜 {feature_label} History")

    if not user_id:
        st.info("Please log in to view your generation history.")
        return

    records = utils.get_history(user_id=user_id, feature_type=feature_type, limit=20)

    col_h1, col_h2 = st.columns([4, 1.8])
    with col_h1:
        st.caption(f"Showing your saved {feature_label.lower()} history ({len(records)} batches).")
    with col_h2:
        if records:
            short_feat = "Text" if "text" in feature_type else "Image"
            if st.button(f"🗑️ Clear {short_feat} History", key=f"{key_prefix}_clear_btn", use_container_width=True):
                utils.clear_history(user_id=user_id, feature_type=feature_type)
                st.toast(f"{feature_label} history cleared!", icon="🗑️")
                st.rerun()

    if not records:
        st.info(f"No {feature_label.lower()} history yet. Generated captions will appear here!")
        return

    for rec in records:
        rec_id = rec.get("id")
        timestamp = rec.get("timestamp")
        summary = rec.get("input_summary", "")
        platform = rec.get("platform", "")
        tone = rec.get("tone", "")
        captions = rec.get("captions", [])

        with st.expander(f"📌 [{timestamp}] {platform} ({tone}) — {summary[:50]}...", expanded=False):
            st.markdown(f"**Topic / Input:** {summary}")
            st.markdown(f"**Platform:** `{platform}` | **Tone:** `{tone}` | **Length:** `{rec.get('length')}`")

            c_url = rec.get("metadata", {}).get("cloudinary_url") or rec.get("metadata", {}).get("secure_url")
            if c_url:
                st.image(c_url, caption=f"Stored Image Reference ({rec.get('metadata', {}).get('filename', 'Image')})", width=240)

            st.markdown("##### Captions:")
            for idx, c in enumerate(captions, 1):
                c_text = c.get("caption", "")
                c_id = c.get("id") or utils.generate_caption_id(c_text, str(idx))
                is_fav = utils.is_favorite(c_id)

                st.markdown(f"""
                <div class="history-item-box">
                    <b class="history-item-title">#{idx} {c.get('vibe_label', '')}</b><br>
                    <span class="history-item-body">{c_text}</span>
                </div>
                """, unsafe_allow_html=True)

                act_col1, act_col2, _ = st.columns([1.2, 1.2, 5])
                with act_col1:
                    with st.popover(f"📋 Copy #{idx}", key=f"{key_prefix}_pop_{rec_id}_{idx}"):
                        st.text_area("Ready to paste", value=c_text, key=f"{key_prefix}_copy_{rec_id}_{idx}", height=100)
                with act_col2:
                    fav_txt = "❤️ Saved" if is_fav else "🤍 Favorite"
                    if st.button(fav_txt, key=f"{key_prefix}_fav_{rec_id}_{idx}"):
                        if is_fav:
                            utils.remove_favorite(c_id)
                        else:
                            utils.add_favorite({
                                "id": c_id,
                                "caption": c_text,
                                "hook": c.get("hook", ""),
                                "vibe_label": c.get("vibe_label", ""),
                                "hashtags": c.get("hashtags", []),
                                "cta": c.get("cta", ""),
                                "platform": platform,
                                "tone": tone
                            })
                        st.rerun()

# ---------------------------------------------------------------------
# Page: GENERATE (The 3 Multimodal Modes)
# ---------------------------------------------------------------------

def render_generate_page():
    render_app_header(
        title="⚡ Multimodal Caption Generator",
        subtitle="Select your input mode below to generate 5 tailored, viral-ready social captions."
    )

    current_user_id = (st.session_state.get("user") or {}).get("user_id")

    tab1, tab2 = st.tabs([
        "✍️ Text-to-Caption",
        "🖼️ Image-to-Caption"
    ])

    # ----------------- Mode 1: Text-to-Caption -----------------
    with tab1:
        st.markdown("#### 1. Describe Your Post")
        text_topic = st.text_area(
            "Topic, Description, or Raw Draft",
            placeholder="e.g., Launching our new eco-friendly reusable coffee tumbler made from bamboo fiber. Clean minimalist design, keeps drinks hot for 12 hours.",
            height=110,
            key="text_input_topic"
        )

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            text_platform = st.selectbox("Platform", PLATFORMS, index=0, key="text_platform")
        with col_t2:
            text_tone = st.selectbox("Tone", TONES, index=0, key="text_tone")
        with col_t3:
            text_length = st.selectbox("Length", LENGTHS, index=1, key="text_length")

        with st.expander("🛠️ Advanced Options (Hashtags, Emojis, Audience)"):
            c_opt1, c_opt2 = st.columns(2)
            with c_opt1:
                include_ht = st.checkbox("Include Hashtags", value=True, key="text_inc_ht")
                ht_count = st.slider("Hashtag Count", 1, 15, 5, key="text_ht_count") if include_ht else 0
            with c_opt2:
                include_em = st.checkbox("Include Emojis", value=True, key="text_inc_em")
                text_audience = st.text_input("Target Audience (Optional)", placeholder="e.g. Gen Z coffee lovers, eco-conscious professionals", key="text_aud")

        b_sub1, b_reset1, _ = st.columns([1.5, 1, 4])
        with b_sub1:
            gen_text_btn = st.button("✨ Generate 5 Captions", type="primary", use_container_width=True, key="btn_gen_text")
        with b_reset1:
            if st.button("Reset", key="btn_reset_text"):
                st.session_state["text_input_topic"] = ""
                st.rerun()

        if gen_text_btn:
            if not text_topic.strip():
                st.error("Please provide a topic or description before generating.")
            elif not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                with st.spinner("🤖 Crafting 5 viral captions with Gemini..."):
                    success, captions, error_msg = ai_service.generate_text_captions(
                        topic=text_topic,
                        tone=text_tone,
                        platform=text_platform,
                        length=text_length,
                        include_hashtags=include_ht,
                        hashtag_count=ht_count,
                        include_emojis=include_em,
                        audience=text_audience,
                        api_key=effective_api_key,
                        model_name=selected_model
                    )
                    if success:
                        st.session_state["generated_captions"] = captions
                        st.session_state["latest_generation_meta"] = {
                            "mode": "Text-to-Caption",
                            "topic": text_topic,
                            "tone": text_tone,
                            "platform": text_platform,
                            "length": text_length,
                            "include_hashtags": include_ht,
                            "hashtag_count": ht_count,
                            "include_emojis": include_em,
                            "audience": text_audience
                        }
                        utils.save_generation_to_history(
                            mode="Text-to-Caption",
                            input_summary=text_topic[:100],
                            tone=text_tone,
                            platform=text_platform,
                            length=text_length,
                            captions=captions,
                            user_id=current_user_id,
                            feature_type=utils.FEATURE_TEXT_TO_CAPTION
                        )
                        st.success("Successfully generated 5 captions!")
                        st.rerun()
                    else:
                        st.error(error_msg)

        # Feature-Specific History: Text-to-Caption
        st.markdown("---")
        render_feature_history(
            user_id=current_user_id,
            feature_type=utils.FEATURE_TEXT_TO_CAPTION,
            feature_label="Text-to-Caption",
            key_prefix="text_tab_hist"
        )

    # ----------------- Mode 2: Image-to-Caption -----------------
    with tab2:
        st.markdown("#### 2. Upload an Image for Visual Reasoning")
        uploaded_file = st.file_uploader(
            "Upload Image (JPG, JPEG, PNG, WebP — max 15MB)",
            type=["jpg", "jpeg", "png", "webp"],
            key="image_uploader"
        )

        col_img_prev, col_img_controls = st.columns([1.2, 1.8])

        is_valid_img = False
        pil_img = None
        img_meta = {}

        if uploaded_file is not None:
            is_valid, err_msg, pil_img, img_meta = utils.validate_image(uploaded_file)
            if not is_valid:
                st.error(err_msg)
            else:
                is_valid_img = True
                with col_img_prev:
                    st.image(pil_img, caption=f"{img_meta.get('filename')} ({img_meta.get('width')}x{img_meta.get('height')})", use_container_width=True)
                    st.markdown(f"""
                    <div class="img-meta-preview">
                        Size: {img_meta.get('size_mb')} MB • Format: {img_meta.get('format')}
                    </div>
                    """, unsafe_allow_html=True)

        with col_img_controls:
            img_context = st.text_area(
                "Creator Notes / Context (Optional)",
                placeholder="e.g. Taken during golden hour at Amalfi Coast. Celebrating a milestone anniversary.",
                height=90,
                key="image_user_notes"
            )

            col_i1, col_i2 = st.columns(2)
            with col_i1:
                img_platform = st.selectbox("Platform", PLATFORMS, index=0, key="img_platform")
                img_tone = st.selectbox("Tone", TONES, index=0, key="img_tone")
            with col_i2:
                img_length = st.selectbox("Length", LENGTHS, index=1, key="img_length")
                img_inc_ht = st.checkbox("Include Hashtags", value=True, key="img_inc_ht")

        b_sub2, b_reset2, _ = st.columns([1.5, 1, 4])
        with b_sub2:
            gen_img_btn = st.button("🖼️ Analyze Image & Generate Captions", type="primary", use_container_width=True, key="btn_gen_img")
        with b_reset2:
            if st.button("Reset", key="btn_reset_img"):
                st.session_state["image_uploader"] = None
                st.session_state["image_user_notes"] = ""
                st.rerun()

        if gen_img_btn:
            if not is_valid_img or pil_img is None:
                st.error("Please upload a valid image file (JPG, PNG, WebP) first.")
            elif not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                # Persistent Cloudinary image storage when credentials are configured
                if cloudinary_service.is_cloudinary_configured():
                    with st.spinner("☁️ Storing image in Cloudinary..."):
                        c_ok, c_err, c_data = cloudinary_service.upload_image(
                            image_data=uploaded_file.getvalue(),
                            filename=img_meta.get("filename"),
                            user_id=current_user_id
                        )
                        if c_ok and c_data:
                            img_meta["cloudinary_public_id"] = c_data.get("public_id")
                            img_meta["cloudinary_url"] = c_data.get("secure_url")
                            img_meta["secure_url"] = c_data.get("secure_url")
                        else:
                            st.warning(f"Cloudinary notice: {c_err}")

                with st.spinner("🔍 Inspecting visual mood, colors, and subject with Gemini Multimodal Vision..."):
                    success, captions, error_msg = ai_service.generate_image_captions(
                        image=pil_img,
                        tone=img_tone,
                        platform=img_platform,
                        length=img_length,
                        include_hashtags=img_inc_ht,
                        hashtag_count=5,
                        include_emojis=True,
                        user_context=img_context,
                        api_key=effective_api_key,
                        model_name=selected_model
                    )
                    if success:
                        st.session_state["generated_captions"] = captions
                        st.session_state["latest_generation_meta"] = {
                            "mode": "Image-to-Caption",
                            "tone": img_tone,
                            "platform": img_platform,
                            "length": img_length,
                            "user_context": img_context,
                            "filename": img_meta.get("filename"),
                            "cloudinary_public_id": img_meta.get("cloudinary_public_id"),
                            "cloudinary_url": img_meta.get("cloudinary_url")
                        }
                        utils.save_generation_to_history(
                            mode="Image-to-Caption",
                            input_summary=f"Image: {img_meta.get('filename')} ({img_context[:60] if img_context else 'Visual only'})",
                            tone=img_tone,
                            platform=img_platform,
                            length=img_length,
                            captions=captions,
                            metadata=img_meta,
                            user_id=current_user_id,
                            feature_type=utils.FEATURE_IMAGE_TO_CAPTION
                        )
                        st.success("Multimodal vision analysis complete!")
                        st.rerun()
                    else:
                        st.error(error_msg)

        # Feature-Specific History: Image-to-Caption
        st.markdown("---")
        render_feature_history(
            user_id=current_user_id,
            feature_type=utils.FEATURE_IMAGE_TO_CAPTION,
            feature_label="Image-to-Caption",
            key_prefix="img_tab_hist"
        )

    # ----------------- Render Active Results -----------------
    st.markdown("---")
    render_caption_cards(st.session_state.get("generated_captions", []))

# ---------------------------------------------------------------------
# Page: HISTORY
# ---------------------------------------------------------------------

def render_history_page():
    render_app_header(
        title="📜 Generation History",
        subtitle="View, search, filter, and export your previously generated caption batches."
    )

    current_user_id = (st.session_state.get("user") or {}).get("user_id")

    col_f1, col_f2, col_f3 = st.columns([1.5, 3, 1.5])
    with col_f1:
        mode_filter = st.selectbox("Filter Mode", ["All", "Text-to-Caption", "Image-to-Caption"])
    with col_f2:
        search_query = st.text_input("🔍 Search History", placeholder="Search by topic, keyword, or caption text...")
    with col_f3:
        st.markdown('<div class="form-spacer"></div>', unsafe_allow_html=True)
        if st.button("🗑️ Clear All History"):
            utils.clear_history(user_id=current_user_id)
            st.toast("Your history cleared successfully!")
            st.rerun()

    history_records = utils.get_history(user_id=current_user_id, mode_filter=mode_filter, search_term=search_query)

    # Export Buttons
    if history_records:
        st.markdown("<br>", unsafe_allow_html=True)
        exp_col1, exp_col2, _ = st.columns([1.5, 1.5, 4])
        with exp_col1:
            df = utils.export_history_to_df(user_id=current_user_id, mode_filter=mode_filter)
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Export History (CSV)",
                data=csv_data,
                file_name="captioncraft_history.csv",
                mime="text/csv"
            )
        with exp_col2:
            json_str = utils.export_history_to_json(history_records)
            st.download_button(
                "📥 Export History (JSON)",
                data=json_str.encode("utf-8"),
                file_name="captioncraft_history.json",
                mime="application/json"
            )

    st.markdown("---")

    if not history_records:
        st.info("No history records found matching your filters. Generate some captions to see them here!")
        return

    for rec in history_records:
        rec_id = rec.get("id")
        raw_ts = rec.get("timestamp") or rec.get("created_at")
        if isinstance(raw_ts, (datetime, date)):
            ts_display = raw_ts.strftime("%Y-%m-%d %H:%M:%S")
        elif raw_ts:
            ts_display = str(raw_ts)
        else:
            ts_display = "Recent"

        mode = rec.get("mode") or "Caption"
        summary = str(rec.get("input_summary") or "")
        summary_preview = summary[:55] if len(summary) > 55 else summary
        platform = rec.get("platform") or "Social"
        tone = rec.get("tone") or "Standard"
        captions = rec.get("captions", []) or []

        with st.expander(f"📌 [{ts_display}] {mode} • {platform} ({tone}) — {summary_preview}...", expanded=False):
            st.markdown(f"**Topic / Input:** {summary}")
            st.markdown(f"**Platform:** `{platform}` | **Tone:** `{tone}` | **Length:** `{rec.get('length')}`")

            c_url = rec.get("metadata", {}).get("cloudinary_url") or rec.get("metadata", {}).get("secure_url")
            if c_url:
                st.image(c_url, caption=f"Stored Image Reference ({rec.get('metadata', {}).get('filename', 'Image')})", width=240)

            st.markdown("#### Generated Captions:")
            for idx, c in enumerate(captions, 1):
                c_text = c.get("caption", "")
                c_id = c.get("id") or utils.generate_caption_id(c_text, str(idx))
                is_fav = utils.is_favorite(c_id)

                st.markdown(f"""
                <div class="history-item-box">
                    <b class="history-item-title">#{idx} {c.get('vibe_label', '')}</b><br>
                    <span class="history-item-body">{c_text}</span>
                </div>
                """, unsafe_allow_html=True)

                act_col1, act_col2, _ = st.columns([1.2, 1.2, 5])
                with act_col1:
                    with st.popover(f"📋 Copy #{idx}"):
                        st.text_area("Ready to paste", value=c_text, key=f"hist_copy_{rec_id}_{idx}", height=100)
                with act_col2:
                    fav_txt = "❤️ Saved" if is_fav else "🤍 Favorite"
                    if st.button(fav_txt, key=f"hist_fav_{rec_id}_{idx}"):
                        if is_fav:
                            utils.remove_favorite(c_id)
                        else:
                            utils.add_favorite({
                                "id": c_id,
                                "caption": c_text,
                                "hook": c.get("hook", ""),
                                "vibe_label": c.get("vibe_label", ""),
                                "hashtags": c.get("hashtags", []),
                                "cta": c.get("cta", ""),
                                "platform": platform,
                                "tone": tone
                            })
                        st.rerun()

# ---------------------------------------------------------------------
# Page: FAVORITES
# ---------------------------------------------------------------------

def render_favorites_page():
    render_app_header(
        title="⭐ Saved Favorite Captions",
        subtitle="Your curated collection of top-performing, favorite captions."
    )

    favorites = utils.get_favorites()

    if not favorites:
        st.info("You haven't added any captions to your favorites yet. Click the 🤍 Favorite button on any caption card to save it here!")
        return

    # Export Favorites
    exp_col1, exp_col2, _ = st.columns([1.5, 1.5, 4])
    with exp_col1:
        df = utils.export_favorites_to_df()
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Favorites (CSV)",
            data=csv_data,
            file_name="captioncraft_favorites.csv",
            mime="text/csv"
        )
    with exp_col2:
        json_str = utils.export_favorites_to_json(favorites)
        st.download_button(
            "📥 Export Favorites (JSON)",
            data=json_str.encode("utf-8"),
            file_name="captioncraft_favorites.json",
            mime="application/json"
        )

    st.markdown("---")

    for f in favorites:
        fid = f.get("id")
        cap_text = f.get("caption", "")
        hook = f.get("hook", "")
        vibe = f.get("vibe_label", "Favorite")
        platform = f.get("platform", "Social")
        tone = f.get("tone", "Creative")
        hashtags = f.get("hashtags", [])
        saved_at = f.get("favorited_at", "")

        metrics = utils.calculate_text_metrics(cap_text)

        st.markdown(f"""
        <div class="caption-card">
            <div class="caption-card-header">
                <div>
                    <span class="tag-badge tag-badge-favorite">
                        ⭐ {vibe}
                    </span>
                    <span class="meta-pill">{platform}</span>
                    <span class="meta-pill">{tone}</span>
                    <span class="meta-pill">Saved: {saved_at}</span>
                </div>
                <div class="caption-metrics">
                    {metrics['characters']} chars • {metrics['words']} words
                </div>
            </div>
            <div class="hook-text">"{hook}"</div>
            <div class="body-caption">{cap_text}</div>
        """, unsafe_allow_html=True)

        if hashtags:
            ht_html = "".join([f'<span class="tag-badge">#{h.lstrip("#")}</span>' for h in hashtags])
            st.markdown(f'<div class="hashtags-container">{ht_html}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        b1, b2, _ = st.columns([1.2, 1.5, 4])
        with b1:
            with st.popover("📋 Copy Text"):
                st.text_area("Ready to paste", value=cap_text, key=f"fav_copy_{fid}", height=120)
        with b2:
            if st.button("❌ Remove Favorite", key=f"fav_rem_{fid}"):
                utils.remove_favorite(fid)
                st.toast("Removed from favorites")
                st.rerun()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Page: ABOUT
# ---------------------------------------------------------------------

def render_about_page():
    render_app_header(
        title="ℹ️ About CaptionCraft AI",
        subtitle="Architecture, prompt engineering methodology, and multimodal capabilities of CaptionCraft AI."
    )
    st.markdown("""
    **CaptionCraft AI** is an advanced multimodal social media caption studio designed to eliminate writer's block and craft high-engagement copy.
    Built purely in **Python** with **Streamlit** and the official **Google Gemini Python SDK (`google-genai`)**, it delivers enterprise-grade multimodal generation right from your machine.
    """)

    st.markdown("### 🏗️ Technical Architecture")
    st.markdown("""
    - **Frontend & App Framework**: Streamlit with Spatial UI custom CSS — layered surfaces, soft shadows, and dimensional depth.
    - **Multimodal Intelligence**: Google Gemini API via official `google-genai` SDK (`gemini-3.5-flash`, `gemini-3.8-flash`).
    - **Vision Processing**: Pillow (`PIL`) image validation, format inspection, dimension detection, and payload encoding.
    - **Data Persistence**: Local JSON store (`data/history.json`, `data/favorites.json`) with zero external database dependencies.
    - **Environment Security**: `python-dotenv` for local `.env` API credential protection.
    """)

    st.markdown("### 🔑 Google Gemini API Key Setup")
    st.markdown("""
    1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
    2. Sign in with your Google Account and click **Create API Key**.
    3. Copy the key and add it to your project:
       - Either paste it in the **Sidebar > Configure API Key** box, OR
       - Open `.env` in the project root and insert:
         ```env
         GEMINI_API_KEY=AIzaSyYourActualKeyHere
         ```
    4. Save the file and restart or refresh the Streamlit app.
    """)

    st.markdown("### 🎯 Prompt Engineering Methodology")
    st.markdown("""
    Every request sends a structured persona prompt enforcing:
    1. **Strict JSON Schema output** for programmatic parsing.
    2. **5 Distinct Angles**: Viral hook, mood/aesthetic, storytelling, witty commentary, and punchy minimalism.
    3. **Platform-Specific Format Guidelines**: Twitter character boundaries, LinkedIn thought-leadership line breaks, and Instagram hook placements.
    4. **Safety & Zero Hallucination**: Verifies image elements directly without fabricating non-existent features.
    """)

# ---------------------------------------------------------------------
# Main Router
# ---------------------------------------------------------------------

page = st.session_state.get("current_page", "Generate")

if page == "Home":
    render_home_page()
elif page == "Generate":
    render_generate_page()
elif page == "History":
    render_history_page()
elif page == "Favorites":
    render_favorites_page()
elif page == "About":
    render_about_page()
else:
    render_generate_page()
