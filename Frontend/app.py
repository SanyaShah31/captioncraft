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
import pandas as pd
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
if "input_emoji_seq" not in st.session_state:
    st.session_state["input_emoji_seq"] = "✨ 🚀 🔥"
if "selected_emojis" not in st.session_state:
    st.session_state["selected_emojis"] = st.session_state["input_emoji_seq"]
if "input_emoji_notes" not in st.session_state:
    st.session_state["input_emoji_notes"] = ""
if "emoji_user_notes" not in st.session_state:
    st.session_state["emoji_user_notes"] = ""
if "sidebar_api_key" not in st.session_state:
    st.session_state["sidebar_api_key"] = ""
if "active_tab_index" not in st.session_state:
    st.session_state["active_tab_index"] = 0
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "preview_caption_text" not in st.session_state:
    st.session_state["preview_caption_text"] = ""
if "preview_hook" not in st.session_state:
    st.session_state["preview_hook"] = ""
if "preview_hashtags" not in st.session_state:
    st.session_state["preview_hashtags"] = []
if "preview_platform" not in st.session_state:
    st.session_state["preview_platform"] = "Instagram"
if "preview_image" not in st.session_state:
    st.session_state["preview_image"] = None
if "analyzer_input_caption" not in st.session_state:
    st.session_state["analyzer_input_caption"] = ""
if "analyzer_platform" not in st.session_state:
    st.session_state["analyzer_platform"] = "Instagram"
if "analyzer_tone" not in st.session_state:
    st.session_state["analyzer_tone"] = "Aesthetic"
if "viral_analysis_result" not in st.session_state:
    st.session_state["viral_analysis_result"] = None
if "improved_caption_result" not in st.session_state:
    st.session_state["improved_caption_result"] = None
if "creator_tools_active_tab" not in st.session_state:
    st.session_state["creator_tools_active_tab"] = "Social Preview"
if "multi_platform_results" not in st.session_state:
    st.session_state["multi_platform_results"] = {}
if "carousel_story_result" not in st.session_state:
    st.session_state["carousel_story_result"] = None
if "carousel_active_slide_idx" not in st.session_state:
    st.session_state["carousel_active_slide_idx"] = 1

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
    nav_map = {
        "⚡ Generate": "Generate",
        "🛠️ Creator Tools": "Creator Tools",
        "🏠 Home": "Home",
        "📜 History": "History",
        "⭐ Favorites": "Favorites",
        "ℹ️ About": "About"
    }

    current_nav_index = 0
    current_stored_page = st.session_state.get("current_page", "Generate")
    for idx, (label, p_val) in enumerate(nav_map.items()):
        if current_stored_page == p_val:
            current_nav_index = idx

    selected_nav = st.radio(
        "Navigation",
        options=list(nav_map.keys()),
        index=current_nav_index,
        label_visibility="collapsed"
    )

    st.session_state["current_page"] = nav_map[selected_nav]

    st.markdown("---")

    # API Key Configuration Section
    active_masked, active_source = ai_service.get_api_key_source(st.session_state.get("sidebar_api_key"))
    env_key_found = ai_service.is_api_key_configured(st.session_state.get("sidebar_api_key"))
    
    st.markdown('<div class="sidebar-heading">🔑 Gemini API Status</div>', unsafe_allow_html=True)
    if env_key_found:
        st.success(f"API Key Active ({active_source}: `{active_masked}`)")
    else:
        st.warning("API Key Not Detected")

    with st.expander("⚙️ Configure API Key", expanded=not env_key_found):
        st.caption("Provide your Google Gemini API key if not configured in `.env`.")
        entered_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("sidebar_api_key", ""),
            type="password",
            placeholder="AQ... or AIzaSy...",
            help="Free key available from Google AI Studio"
        )
        if entered_key:
            st.session_state["sidebar_api_key"] = entered_key
            st.info("Using session API key override")
        st.markdown("[Get free Gemini Key ↗](https://aistudio.google.com/app/apikey)")

    # Model Selection
    selected_model = st.selectbox(
        "Gemini Model",
        options=["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"],
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
            <span class="feature-badge">🖼️ Image Vision</span>
            <span class="feature-badge">🎭 Emoji Storyteller</span>
            <span class="feature-badge">🌍 Multi-Platform</span>
            <span class="feature-badge">🎞️ Carousel Story</span>
            <span class="feature-badge">📱 Feed Mockups</span>
            <span class="feature-badge">🚀 Viral Analyzer</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 3])
    with col_btn1:
        if st.button("🚀 Start Generating Captions", type="primary", use_container_width=True):
            st.session_state["current_page"] = "Generate"
            st.rerun()
    with col_btn2:
        if st.button("🛠️ Open Creator Tools", use_container_width=True):
            st.session_state["current_page"] = "Creator Tools"
            st.rerun()

    st.markdown("### 🌟 Specialized Generation Modes")
    col1, col2, col3 = st.columns(3)

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
            <span class="meta-pill">Cloudinary Sync</span>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="glass-card">
            <h3 style="color:#1F3B2E; margin-top:0; font-weight:700;">🎭 Emoji-to-Caption</h3>
            <p class="mode-desc">
                Pick expressive emoji combinations or one-click story presets. Generates rich prose or minimalist emoji-only storytelling hooks.
            </p>
            <span class="meta-pill">10 Categories</span>
            <span class="meta-pill">8 Story Presets</span>
            <span class="meta-pill">Emoji-Only Mode</span>
        </div>
        """, unsafe_allow_html=True)

    col4, col5 = st.columns(2)
    with col4:
        st.markdown("""
        <div class="glass-card">
            <h3 style="color:#1F3B2E; margin-top:0; font-weight:700;">🌍 Multi-Platform Generator</h3>
            <p class="mode-desc">
                One-click omnichannel campaign creation. Generates distinct, platform-native captions for Instagram, X / Twitter, LinkedIn, TikTok, and Threads in one pass.
            </p>
            <span class="meta-pill">5 Platforms at Once</span>
            <span class="meta-pill">280-char Limit Enforced</span>
            <span class="meta-pill">Download TXT & CSV</span>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="glass-card">
            <h3 style="color:#1F3B2E; margin-top:0; font-weight:700;">🎞️ Carousel Storyteller</h3>
            <p class="mode-desc">
                Upload 2 to 5 images to generate a cohesive visual narrative: Cover Hook, Story Progression, and Closing Call-to-Action with on-screen text overlay suggestions.
            </p>
            <span class="meta-pill">Multi-Image Vision</span>
            <span class="meta-pill">Slide-by-Slide Narrative</span>
            <span class="meta-pill">Master Caption Export</span>
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
            b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([1.2, 1.2, 1.2, 1.2, 2.5])

            with b_col1:
                # Copy friendly display
                with st.popover("📋 Copy"):
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

            with b_col3:
                if st.button("📱 Preview", key=f"prev_btn_{cid}", help="Inspect simulated appearance across social feeds"):
                    st.session_state["preview_caption_text"] = cap_text
                    st.session_state["preview_hook"] = hook
                    st.session_state["preview_hashtags"] = hashtags
                    st.session_state["preview_platform"] = platform
                    st.session_state["current_page"] = "Creator Tools"
                    st.session_state["creator_tools_active_tab"] = "Social Preview"
                    st.rerun()

            with b_col4:
                if st.button("🚀 Analyze", key=f"anal_btn_{cid}", help="Score virality & polish with AI"):
                    st.session_state["analyzer_input_caption"] = cap_text
                    st.session_state["analyzer_platform"] = platform
                    st.session_state["analyzer_tone"] = tone
                    st.session_state["current_page"] = "Creator Tools"
                    st.session_state["creator_tools_active_tab"] = "Viral Analyzer"
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
            short_feat = "Text" if "text" in feature_type else ("Image" if "image" in feature_type else ("Emoji" if "emoji" in feature_type else ("Multi" if "multi" in feature_type else "Carousel")))
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

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "✍️ Text-to-Caption",
        "🖼️ Image-to-Caption",
        "🎭 Emoji-to-Caption",
        "🌍 Multi-Platform",
        "🎞️ Carousel Storyteller"
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

    # ----------------- Mode 3: Emoji-to-Caption -----------------
    with tab3:
        st.markdown("#### 3. Select Emojis & Story Theme")
        st.caption("Translate expressive emoji combinations into 5 viral captions or minimal emoji-only micro-hooks.")

        # Story Presets
        st.markdown("**⚡ Instant Story Presets:**")
        presets = [
            ("☕ Coffee & Cozy", "☕ 📚 🛋️ 🕯️ ✨", "Quiet rainy morning with warm coffee and a good book"),
            ("🌴 Tropical Vacation", "🌴 🏖️ 🌊 🍹 ✈️", "Unwinding on a sun-drenched beach with ocean breeze"),
            ("❤️ Love & Relationship", "❤️ 👩‍❤️‍👨 💍 💐 🫶", "Celebrating deep love, shared moments, and sweet milestones"),
            ("🌅 Sunset Vibes", "🌅 🧡 ✨ 🌊 🕊️", "Golden hour glow and introspective sunset serenity"),
            ("🎉 Party & Celebration", "🎉 🥂 🍾 💃 🎊", "Epic night out with music, dance, and celebratory toasts"),
            ("💪 Fitness Motivation", "💪 🏋️ 💦 🥗 🏆", "Early morning gym grind, pushing limits, and crushing goals"),
            ("🌸 Self-Care Day", "🌸 🛁 🕯️ 🧘 🍵", "Recharging mind and body with peaceful mindful self-care"),
            ("🌧️ Rainy Day Mood", "🌧️ ☕ 🎧 🛋️ 💭", "Lo-fi beats, rain on window panes, and cozy introspective thoughts")
        ]

        pr_cols = st.columns(4)
        for idx, (p_name, p_emojis, p_dir) in enumerate(presets):
            with pr_cols[idx % 4]:
                if st.button(p_name, key=f"emoji_preset_{idx}", use_container_width=True):
                    st.session_state["input_emoji_seq"] = p_emojis
                    st.session_state["selected_emojis"] = p_emojis
                    st.session_state["input_emoji_notes"] = p_dir
                    st.session_state["emoji_user_notes"] = p_dir
                    st.rerun()

        # Emoji Categories Accordion (10 groups)
        with st.expander("🎨 Browse Emoji Picker Palette (10 Themed Categories)", expanded=False):
            emoji_categories = {
                "😊 Emotions": ["😀", "😂", "🥹", "😍", "🤩", "😎", "🤔", "🥳", "😴", "🤯"],
                "☕ Lifestyle": ["☕", "🛋️", "📚", "🎧", "🕯️", "🪴", "🛁", "🍷", "🥐", "✨"],
                "🌴 Travel": ["✈️", "🌴", "🏖️", "🗺️", "🏕️", "🧳", "⛰️", "🚗", "🌅", "🌊"],
                "🍕 Food": ["🍕", "🍔", "🍣", "🌮", "🍦", "🍩", "🥑", "🍓", "🍜", "🥂"],
                "❤️ Love": ["❤️", "💖", "🥰", "💍", "💌", "👩‍❤️‍👨", "💕", "💐", "🫶", "✨"],
                "🎉 Celebration": ["🎉", "🥂", "🎂", "🎈", "🎊", "🎆", "🍾", "🕺", "💃", "🎁"],
                "💪 Fitness": ["💪", "🏋️", "🏃", "🥗", "👟", "🧘", "🚴", "💦", "🥊", "🏆"],
                "🌸 Nature": ["🌸", "🌿", "🌻", "🍁", "🌺", "🌞", "🌈", "🌙", "⭐", "🦋"],
                "💻 Technology": ["💻", "🚀", "📱", "🤖", "⚡", "💡", "📊", "🔥", "🎯", "🌐"],
                "🎨 Creativity": ["🎨", "📸", "✍️", "🎭", "🎬", "✨", "🎤", "🖌️", "🎵", "🧵"]
            }

            for cat_title, em_list in emoji_categories.items():
                st.markdown(f"<div class='emoji-group-header'>{cat_title}</div>", unsafe_allow_html=True)
                btn_cols = st.columns(10)
                for c_idx, emo in enumerate(em_list):
                    with btn_cols[c_idx]:
                        if st.button(emo, key=f"btn_em_{cat_title}_{c_idx}"):
                            current_ems = (st.session_state.get("input_emoji_seq") or "").strip()
                            new_seq = f"{current_ems} {emo}".strip() if current_ems else emo
                            st.session_state["input_emoji_seq"] = new_seq
                            st.session_state["selected_emojis"] = new_seq
                            st.rerun()

        # Selected Emojis Box
        cur_emojis = (st.session_state.get("input_emoji_seq") or "").strip()
        st.markdown(f"""
        <div class="emoji-display-box">
            <b>Selected Emojis:</b> &nbsp; {cur_emojis if cur_emojis else '<span style=\"color:#888;\">(Click emojis above or type below)</span>'}
        </div>
        """, unsafe_allow_html=True)

        em_col_edit, em_col_clr = st.columns([4, 1.2])
        with em_col_edit:
            emoji_input = st.text_input(
                "Edit Emoji Sequence",
                key="input_emoji_seq",
                help="Type, paste, or delete emojis freely"
            )
            st.session_state["selected_emojis"] = emoji_input
        with em_col_clr:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Clear Emojis", key="btn_clear_emojis", use_container_width=True):
                st.session_state["input_emoji_seq"] = ""
                st.session_state["selected_emojis"] = ""
                st.rerun()

        emoji_context = st.text_input(
            "Story Direction / Context (Optional)",
            placeholder="e.g., Friday sunset drinks with colleagues celebrating a project launch",
            key="input_emoji_notes"
        )
        st.session_state["emoji_user_notes"] = emoji_context

        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            emoji_platform = st.selectbox("Platform", PLATFORMS, index=0, key="emoji_platform")
        with col_e2:
            emoji_tone = st.selectbox("Tone", TONES, index=0, key="emoji_tone")
        with col_e3:
            emoji_length = st.selectbox("Length", LENGTHS, index=1, key="emoji_length")

        col_e_opt1, col_e_opt2 = st.columns(2)
        with col_e_opt1:
            emoji_only_mode = st.checkbox(
                "🎭 Emoji-Only Mode (Micro-hooks & visual sequences without full prose)",
                value=False,
                key="emoji_only_toggle"
            )
        with col_e_opt2:
            emoji_inc_ht = st.checkbox("Include Hashtags", value=True, key="emoji_inc_ht")

        b_sub3, b_reset3, _ = st.columns([1.5, 1, 4])
        with b_sub3:
            gen_emoji_btn = st.button("✨ Generate 5 Captions", type="primary", use_container_width=True, key="btn_gen_emoji")
        with b_reset3:
            if st.button("Reset", key="btn_reset_emoji"):
                st.session_state["input_emoji_seq"] = "✨ 🚀 🔥"
                st.session_state["selected_emojis"] = "✨ 🚀 🔥"
                st.session_state["input_emoji_notes"] = ""
                st.session_state["emoji_user_notes"] = ""
                st.rerun()

        if gen_emoji_btn:
            active_emoji_input = (st.session_state.get("input_emoji_seq") or emoji_input or "").strip()
            active_context = (st.session_state.get("input_emoji_notes") or emoji_context or "").strip()

            if not active_emoji_input:
                st.error("Please pick or type at least one emoji before generating.")
            elif not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                with st.spinner("Decoding emoji subtext & crafting 5 viral captions with Gemini..."):
                    success, captions, error_msg = ai_service.generate_emoji_captions(
                        emojis=active_emoji_input,
                        tone=emoji_tone,
                        platform=emoji_platform,
                        length=emoji_length,
                        emoji_only_mode=emoji_only_mode,
                        user_context=active_context if active_context else None,
                        include_hashtags=emoji_inc_ht,
                        hashtag_count=5,
                        api_key=effective_api_key,
                        model_name=selected_model
                    )
                    if success:
                        st.session_state["generated_captions"] = captions
                        st.session_state["latest_generation_meta"] = {
                            "mode": "Emoji-to-Caption",
                            "emojis": active_emoji_input,
                            "tone": emoji_tone,
                            "platform": emoji_platform,
                            "length": emoji_length,
                            "emoji_only_mode": emoji_only_mode,
                            "user_context": active_context
                        }
                        utils.save_generation_to_history(
                            mode="Emoji-to-Caption",
                            input_summary=f"Emojis: {active_emoji_input} ({active_context[:45] if active_context else 'No extra notes'})",
                            tone=emoji_tone,
                            platform=emoji_platform,
                            length=emoji_length,
                            captions=captions,
                            user_id=current_user_id,
                            feature_type=utils.FEATURE_EMOJI_TO_CAPTION
                        )
                        st.success("Successfully generated 5 emoji-inspired captions!")
                        st.rerun()
                    else:
                        st.error(error_msg)

        # Feature-Specific History: Emoji-to-Caption
        st.markdown("---")
        render_feature_history(
            user_id=current_user_id,
            feature_type=utils.FEATURE_EMOJI_TO_CAPTION,
            feature_label="Emoji-to-Caption",
            key_prefix="emoji_tab_hist"
        )

    # ----------------- Mode 4: Multi-Platform Generator -----------------
    with tab4:
        st.markdown("#### 4. Generate Platform-Native Captions in One Pass")
        st.caption("Craft distinct, culturally native captions for Instagram, X / Twitter, LinkedIn, TikTok, and Threads simultaneously.")

        mp_topic = st.text_area(
            "Campaign Topic, Concept, or Raw Notes",
            placeholder="e.g., We just crossed 10,000 active community members! Sharing what we learned about community-led growth, retention, and customer support.",
            height=100,
            key="mp_input_topic"
        )

        mp_img_file = st.file_uploader(
            "Optional Accompanying Image (JPG, PNG, WebP)",
            type=["jpg", "jpeg", "png", "webp"],
            key="mp_image_uploader"
        )
        mp_pil_img = None
        if mp_img_file is not None:
            is_valid, err_msg, mp_pil_img, _ = utils.validate_image(mp_img_file)
            if is_valid and mp_pil_img:
                st.image(mp_pil_img, caption="Loaded visual context", width=200)
            elif not is_valid:
                st.warning(err_msg)

        st.markdown("**Select Platforms to Target:**")
        available_mp_platforms = ["Instagram", "Twitter / X", "LinkedIn", "TikTok", "Threads"]

        col_all_btn, _ = st.columns([2, 4])
        with col_all_btn:
            select_all_mp = st.checkbox("Select All 5 Platforms", value=True, key="mp_select_all")

        p_cols = st.columns(5)
        selected_platforms = []
        for idx, plat in enumerate(available_mp_platforms):
            with p_cols[idx]:
                checked = st.checkbox(plat, value=select_all_mp, key=f"mp_check_{idx}")
                if checked:
                    selected_platforms.append(plat)

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            mp_tone = st.selectbox("Tone", TONES, index=3, key="mp_tone")
        with col_m2:
            mp_length = st.selectbox("Base Length", LENGTHS, index=1, key="mp_length")
        with col_m3:
            mp_audience = st.text_input("Target Audience (Optional)", placeholder="e.g. Founders, Marketers", key="mp_aud")

        b_sub4, b_reset4, _ = st.columns([1.5, 1, 4])
        with b_sub4:
            gen_mp_btn = st.button("🌍 Generate for All Selected Platforms", type="primary", use_container_width=True, key="btn_gen_mp")
        with b_reset4:
            if st.button("Reset", key="btn_reset_mp"):
                st.session_state["mp_input_topic"] = ""
                st.session_state["multi_platform_results"] = {}
                st.rerun()

        if gen_mp_btn:
            if not mp_topic.strip():
                st.error("Please enter a campaign topic or concept first.")
            elif not selected_platforms:
                st.error("Please select at least one social media platform.")
            elif not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                with st.spinner("Generating tailored cross-platform captions with Gemini..."):
                    success, mp_results, error_msg = ai_service.generate_multi_platform_captions(
                        topic=mp_topic,
                        platforms=selected_platforms,
                        tone=mp_tone,
                        length=mp_length,
                        include_hashtags=True,
                        hashtag_count=5,
                        audience=mp_audience,
                        image=mp_pil_img,
                        api_key=effective_api_key,
                        model_name=selected_model
                    )
                    if success:
                        st.session_state["multi_platform_results"] = mp_results
                        batch_captions = [
                            {
                                "id": item["id"],
                                "caption": item["caption"],
                                "hook": item["hook"],
                                "vibe_label": f"{item['platform']} Native",
                                "platform": item["platform"],
                                "tone": mp_tone,
                                "hashtags": item["hashtags"],
                                "cta": item["cta"]
                            }
                            for item in mp_results.values()
                        ]
                        utils.save_generation_to_history(
                            mode="Multi-Platform",
                            input_summary=f"Multi-Platform: {mp_topic[:65]} ({len(selected_platforms)} platforms)",
                            tone=mp_tone,
                            platform=f"{len(selected_platforms)} Platforms",
                            length=mp_length,
                            captions=batch_captions,
                            user_id=current_user_id,
                            feature_type=utils.FEATURE_MULTI_PLATFORM
                        )
                        st.success(f"Generated {len(mp_results)} platform-native captions!")
                        st.rerun()
                    else:
                        st.error(error_msg)

        # Render Multi-Platform Results
        mp_data = st.session_state.get("multi_platform_results", {})
        if mp_data:
            st.markdown(f"### 🌍 Multi-Platform Captions ({len(mp_data)} Platforms)")

            all_text_export = []
            for p_name, p_info in mp_data.items():
                if not isinstance(p_info, dict):
                    continue
                p_cap = p_info.get("caption", "")
                p_tags = p_info.get("hashtags", [])
                if isinstance(p_tags, list):
                    tag_str = " ".join(["#" + str(h).lstrip("#") for h in p_tags if str(h).strip()])
                else:
                    tag_str = str(p_tags)
                all_text_export.append(f"=== {str(p_name).upper()} ===\n{p_cap}\nHashtags: {tag_str}\n")

            full_txt_str = "\n".join(all_text_export)
            mp_df = utils.export_multi_platform_to_df(mp_data)

            g_col1, g_col2, g_col3 = st.columns([1.5, 1.5, 3])
            with g_col1:
                with st.popover("📋 Copy All Platforms"):
                    st.text_area("All Platform Captions", value=full_txt_str, height=200)
                    st.caption("Press Ctrl+A / Ctrl+C to copy all platforms at once.")
            with g_col2:
                st.download_button(
                    "📥 Download TXT",
                    data=full_txt_str.encode("utf-8"),
                    file_name="captioncraft_multiplatform.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with g_col3:
                st.download_button(
                    "📥 Export CSV",
                    data=mp_df.to_csv(index=False).encode("utf-8"),
                    file_name="captioncraft_multiplatform.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            for p_name, p_info in mp_data.items():
                if not isinstance(p_info, dict):
                    continue
                p_id = p_info.get("id") or utils.generate_caption_id(str(p_name))
                p_cap = p_info.get("caption", "")
                p_hook = p_info.get("hook", "")
                p_tags = p_info.get("hashtags", [])
                p_chars = p_info.get("char_count", len(p_cap))
                p_tip = p_info.get("platform_tip", "")

                char_warning = ""
                if p_name == "Twitter / X" and p_chars > 280:
                    char_warning = f"<span style='color:#DC2626; font-weight:700;'>⚠️ {p_chars}/280 chars (Exceeds limit)</span>"
                elif p_name == "Twitter / X":
                    char_warning = f"<span style='color:#15803D; font-weight:600;'>✅ {p_chars}/280 chars</span>"
                else:
                    char_warning = f"<span class='caption-metrics'>{p_chars} chars</span>"

                st.markdown(f"""
                <div class="multi-platform-card">
                    <div class="multi-platform-card-header">
                        <div>
                            <b style="font-size:1.1rem; color:#1F3B2E;">{p_name}</b>
                        </div>
                        <div>
                            {char_warning}
                        </div>
                    </div>
                    <div class="hook-text">"{p_hook}"</div>
                    <div class="body-caption">{p_cap}</div>
                """, unsafe_allow_html=True)

                if p_tags:
                    ht_html = "".join([f'<span class="tag-badge">#{h.lstrip("#")}</span>' for h in p_tags])
                    st.markdown(f'<div class="hashtags-container">{ht_html}</div>', unsafe_allow_html=True)

                if p_tip:
                    st.markdown(f'<div class="platform-tip-banner">💡 <b>Optimization Note:</b> {p_tip}</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                act1, act2, act3, _ = st.columns([1.2, 1.2, 1.2, 3])
                with act1:
                    with st.popover(f"📋 Copy", key=f"mp_pop_{p_id}"):
                        st.text_area("Ready to paste", value=p_cap, height=120, key=f"mp_copy_{p_id}")
                with act2:
                    is_p_fav = utils.is_favorite(p_id)
                    fav_txt = "❤️ Saved" if is_p_fav else "🤍 Favorite"
                    if st.button(fav_txt, key=f"mp_fav_{p_id}"):
                        if is_p_fav:
                            utils.remove_favorite(p_id)
                        else:
                            utils.add_favorite({
                                "id": p_id,
                                "caption": p_cap,
                                "hook": p_hook,
                                "vibe_label": f"{p_name} Native",
                                "hashtags": p_tags,
                                "cta": p_info.get("cta", ""),
                                "platform": p_name,
                                "tone": p_info.get("tone", "Creative")
                            })
                        st.rerun()
                with act3:
                    if st.button("📱 Preview", key=f"mp_prev_{p_id}"):
                        st.session_state["preview_caption_text"] = p_cap
                        st.session_state["preview_hook"] = p_hook
                        st.session_state["preview_hashtags"] = p_tags
                        st.session_state["preview_platform"] = p_name
                        st.session_state["current_page"] = "Creator Tools"
                        st.session_state["creator_tools_active_tab"] = "Social Preview"
                        st.rerun()

                st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        # Feature-Specific History: Multi-Platform
        st.markdown("---")
        render_feature_history(
            user_id=current_user_id,
            feature_type=utils.FEATURE_MULTI_PLATFORM,
            feature_label="Multi-Platform",
            key_prefix="mp_tab_hist"
        )

    # ----------------- Mode 5: Carousel Storyteller -----------------
    with tab5:
        st.markdown("#### 5. Multi-Image Visual Carousel & Photo Dump Generator")
        st.caption("Upload 2 to 5 images to craft a coherent slide-by-slide storyline with cover hooks, narrative transitions, and a closing CTA.")

        uploaded_carousel_files = st.file_uploader(
            "Upload 2 to 5 Images (JPG, JPEG, PNG, WebP — max 15MB each)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="carousel_uploader"
        )

        valid_carousel_images = []
        if uploaded_carousel_files:
            if len(uploaded_carousel_files) > 5:
                st.warning("⚠️ Maximum 5 images supported for carousel story generation. Only the first 5 images will be processed.")
                uploaded_carousel_files = uploaded_carousel_files[:5]

            st.markdown("##### 🖼️ Uploaded Slide Sequence:")
            t_cols = st.columns(len(uploaded_carousel_files))
            for f_idx, c_file in enumerate(uploaded_carousel_files):
                is_valid, err_msg, p_img, meta = utils.validate_image(c_file)
                if is_valid and p_img:
                    valid_carousel_images.append(p_img)
                    with t_cols[f_idx]:
                        st.image(p_img, use_container_width=True)
                        role_label = "Cover Hook" if f_idx == 0 else ("Final CTA" if f_idx == len(uploaded_carousel_files) - 1 else f"Slide {f_idx + 1}")
                        st.caption(f"**Slide #{f_idx + 1}**\n({role_label})")
                else:
                    st.error(f"File {getattr(c_file, 'name', '')}: {err_msg}")

        c_ctx = st.text_area(
            "Carousel Theme / Story Direction (Optional)",
            placeholder="e.g., A 48-hour weekend road trip exploring coastal cliffs and secret coves. The moment everything went wrong, and why it ended up being the best trip ever.",
            height=90,
            key="carousel_theme_notes"
        )

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            carousel_platform = st.selectbox("Platform", ["Instagram", "LinkedIn"], index=0, key="carousel_platform")
        with col_c2:
            carousel_tone = st.selectbox("Tone", TONES, index=0, key="carousel_tone")
        with col_c3:
            carousel_aud = st.text_input("Audience", placeholder="e.g. Travel enthusiasts", key="carousel_aud")

        b_sub5, b_reset5, _ = st.columns([1.5, 1, 4])
        with b_sub5:
            gen_carousel_btn = st.button("🎞️ Generate Carousel Storyline", type="primary", use_container_width=True, key="btn_gen_carousel")
        with b_reset5:
            if st.button("Reset", key="btn_reset_carousel"):
                st.session_state["carousel_story_result"] = None
                st.session_state["carousel_active_slide_idx"] = 1
                st.rerun()

        if gen_carousel_btn:
            if len(valid_carousel_images) < 2:
                st.error("Please upload at least 2 images (up to 5) to generate a carousel storyline.")
            elif not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                with st.spinner("Analyzing visual sequence, lighting, and narrative arc with Gemini..."):
                    success, c_result, error_msg = ai_service.generate_carousel_story(
                        images=valid_carousel_images,
                        tone=carousel_tone,
                        platform=carousel_platform,
                        topic_context=c_ctx,
                        audience=carousel_aud,
                        api_key=effective_api_key,
                        model_name=selected_model
                    )
                    if success:
                        st.session_state["carousel_story_result"] = c_result
                        st.session_state["carousel_active_slide_idx"] = 1

                        hist_captions = [
                            {
                                "id": f"{c_result['id']}_{s['slide_number']}",
                                "caption": s["caption"],
                                "hook": s["title"],
                                "vibe_label": s["slide_type"],
                                "overlay_text": s.get("overlay_text", "")
                            }
                            for s in c_result.get("slides", [])
                        ]
                        utils.save_generation_to_history(
                            mode="Carousel-Story",
                            input_summary=f"Carousel ({c_result['total_slides']} slides): {c_result['theme_title']}",
                            tone=carousel_tone,
                            platform=carousel_platform,
                            length="Multi-Slide",
                            captions=hist_captions,
                            metadata={"master_caption": c_result.get("master_caption", ""), "master_hashtags": c_result.get("master_hashtags", [])},
                            user_id=current_user_id,
                            feature_type=utils.FEATURE_CAROUSEL_STORY
                        )
                        st.success("Visual carousel storyline generated!")
                        st.rerun()
                    else:
                        st.error(error_msg)

        # Render Carousel Storyboard Results
        c_story = st.session_state.get("carousel_story_result")
        if c_story:
            st.markdown(f"### 🎞️ {c_story.get('theme_title', 'Carousel Story')} ({c_story.get('total_slides', 0)} Slides)")

            slides = c_story.get("slides", [])
            total_s = len(slides)

            col_nav_l, col_nav_mid, col_nav_r = st.columns([1, 4, 1])
            cur_s_idx = st.session_state.get("carousel_active_slide_idx", 1)

            with col_nav_l:
                if st.button("⬅️ Prev Slide", key="btn_prev_slide", disabled=(cur_s_idx <= 1)):
                    st.session_state["carousel_active_slide_idx"] = max(1, cur_s_idx - 1)
                    st.rerun()
            with col_nav_mid:
                st.markdown(f"<div class='carousel-nav-indicator'>Slide {cur_s_idx} of {total_s} ({slides[cur_s_idx-1]['slide_type'] if 0 <= cur_s_idx-1 < len(slides) else ''})</div>", unsafe_allow_html=True)
            with col_nav_r:
                if st.button("Next Slide ➡️", key="btn_next_slide", disabled=(cur_s_idx >= total_s)):
                    st.session_state["carousel_active_slide_idx"] = min(total_s, cur_s_idx + 1)
                    st.rerun()

            active_slide = slides[cur_s_idx - 1] if 0 <= cur_s_idx - 1 < len(slides) else slides[0]

            s_col_img, s_col_details = st.columns([1.2, 1.8])
            with s_col_img:
                if valid_carousel_images and cur_s_idx - 1 < len(valid_carousel_images):
                    st.image(valid_carousel_images[cur_s_idx - 1], use_container_width=True)
                else:
                    st.markdown("<div class='mockup-image-placeholder'>🖼️ Slide Visual</div>", unsafe_allow_html=True)

            with s_col_details:
                st.markdown(f"""
                <div class="carousel-slide-card">
                    <div class="carousel-slide-header">
                        <span class="tag-badge tag-badge-accent">Slide #{active_slide['slide_number']} • {active_slide['slide_type']}</span>
                    </div>
                    <h3 style="margin-top:0; color:#1F3B2E;">{active_slide['title']}</h3>
                    <p style="font-size:1rem; line-height:1.55; color:#1F3B2E;">{active_slide['caption']}</p>
                    <div style="margin-top:0.8rem;">
                        <span class="carousel-overlay-badge">🏷️ Suggested Overlay Text:</span><br>
                        <b style="font-size:1.05rem; color:#1F3B2E;">"{active_slide.get('overlay_text', '')}"</b>
                    </div>
                    <div style="font-size:0.82rem; color:#5C7568; margin-top:0.6rem;">
                        <b>Visual Tie-In:</b> {active_slide.get('visual_connection', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                act_s1, act_s2 = st.columns([1.5, 2])
                with act_s1:
                    with st.popover(f"📋 Copy Slide #{cur_s_idx}"):
                        st.text_area("Slide Text", value=f"{active_slide['title']}\n\n{active_slide['caption']}\n\nOverlay: {active_slide.get('overlay_text', '')}", height=120)
                with act_s2:
                    if st.button(f"🔄 Regenerate Slide #{cur_s_idx}", key=f"regen_slide_{cur_s_idx}"):
                        with st.spinner(f"Regenerating slide #{cur_s_idx}..."):
                            ref_img = valid_carousel_images[cur_s_idx - 1] if valid_carousel_images and cur_s_idx - 1 < len(valid_carousel_images) else None
                            reg_ok, new_s_data, _ = ai_service.regenerate_carousel_slide(
                                slide_index=cur_s_idx,
                                total_slides=total_s,
                                current_storyline=c_story.get("master_caption", ""),
                                tone=carousel_tone,
                                platform=carousel_platform,
                                image=ref_img,
                                api_key=effective_api_key,
                                model_name=selected_model
                            )
                            if reg_ok and new_s_data:
                                c_story["slides"][cur_s_idx - 1] = new_s_data
                                st.session_state["carousel_story_result"] = c_story
                                st.toast(f"Slide #{cur_s_idx} regenerated!", icon="✨")
                                st.rerun()

            st.markdown("#### 📝 Complete Master Post Caption")
            st.caption("Paste this into your Instagram / LinkedIn caption box to accompany your carousel:")

            master_cap = c_story.get("master_caption", "")
            master_tags = c_story.get("master_hashtags", [])
            tag_str = " ".join([f"#{t.lstrip('#')}" for t in master_tags])
            full_master_text = f"{master_cap}\n\n{tag_str}".strip()

            st.text_area("Master Caption Text", value=full_master_text, height=130, key="txt_master_cap")

            c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 3])
            with c_act1:
                with st.popover("📋 Copy Full Storyboard"):
                    sb_lines = [f"=== {c_story.get('theme_title', 'CAROUSEL STORY')} ===", f"\nMASTER CAPTION:\n{full_master_text}\n", "SLIDE BY SLIDE:"]
                    for s in slides:
                        sb_lines.append(f"\n[Slide {s['slide_number']} — {s['slide_type']}]\nTitle: {s['title']}\nCaption: {s['caption']}\nOverlay Text: {s.get('overlay_text', '')}")
                    sb_text = "\n".join(sb_lines)
                    st.text_area("Full Storyboard", value=sb_text, height=220)
                    st.caption("Press Ctrl+A / Ctrl+C to copy entire storyboard.")
            with c_act2:
                is_c_fav = utils.is_favorite(c_story["id"])
                c_fav_lbl = "❤️ Saved" if is_c_fav else "🤍 Favorite Story"
                if st.button(c_fav_lbl, key="fav_carousel_btn"):
                    if is_c_fav:
                        utils.remove_favorite(c_story["id"])
                        st.toast("Removed from Favorites")
                    else:
                        utils.add_favorite({
                            "id": c_story["id"],
                            "caption": master_cap,
                            "hook": c_story.get("theme_title", "Carousel Story"),
                            "vibe_label": f"Carousel ({total_s} slides)",
                            "hashtags": master_tags,
                            "cta": c_story.get("master_cta", ""),
                            "platform": carousel_platform,
                            "tone": carousel_tone
                        })
                        st.toast("Saved carousel story to favorites!", icon="⭐")
                    st.rerun()
            with c_act3:
                sb_lines = [f"=== {c_story.get('theme_title', 'CAROUSEL STORY')} ===", f"\nMASTER CAPTION:\n{full_master_text}\n", "SLIDE BY SLIDE:"]
                for s in slides:
                    sb_lines.append(f"\n[Slide {s['slide_number']} — {s['slide_type']}]\nTitle: {s['title']}\nCaption: {s['caption']}\nOverlay Text: {s.get('overlay_text', '')}")
                sb_text = "\n".join(sb_lines)
                st.download_button(
                    "📥 Export Storyboard (TXT)",
                    data=sb_text.encode("utf-8"),
                    file_name="captioncraft_carousel_story.txt",
                    mime="text/plain",
                    use_container_width=True
                )

        # Feature-Specific History: Carousel Story
        st.markdown("---")
        render_feature_history(
            user_id=current_user_id,
            feature_type=utils.FEATURE_CAROUSEL_STORY,
            feature_label="Carousel Story",
            key_prefix="carousel_tab_hist"
        )

    # ----------------- Render Active Results -----------------
    st.markdown("---")
    render_caption_cards(st.session_state.get("generated_captions", []))

# ---------------------------------------------------------------------
# Feature 2 & 3: Creator Tools (Social Previews & Viral Analyzer)
# ---------------------------------------------------------------------

def render_instagram_mockup(caption_text: str, image_obj: Any = None, hashtags: list = None, simulate_fold: bool = True):
    """Renders an authentic Instagram feed post simulation."""
    ht_list = hashtags or []
    ht_str = " ".join([f"#{h.lstrip('#')}" for h in ht_list])

    # Truncation logic: Instagram cuts off caption at ~125 chars or after line 1 before '...more'
    display_caption = caption_text
    is_truncated = False
    if simulate_fold and len(caption_text) > 125:
        first_line = caption_text.split("\n")[0]
        if len(first_line) > 125:
            display_caption = first_line[:120]
        else:
            display_caption = first_line
        is_truncated = True

    st.markdown("""
    <div class="mockup-wrapper">
        <div class="mockup-header-bar">
            <div class="mockup-user-group">
                <div class="mockup-avatar">CC</div>
                <div>
                    <div class="mockup-username">captioncraft.creator <span class="tag-badge" style="font-size:0.7rem; padding:1px 6px;">Following</span></div>
                    <div class="mockup-handle">Original Audio • Trending</div>
                </div>
            </div>
            <span class="mockup-badge-ig">Instagram</span>
        </div>
    """, unsafe_allow_html=True)

    if image_obj:
        st.image(image_obj, use_container_width=True)
    else:
        st.markdown("""
        <div class="mockup-image-frame">
            <div class="mockup-image-placeholder">
                <span style="font-size:2.5rem;">📸</span>
                <span>Visual Post Asset Preview</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="mockup-actions-bar">
            <div>❤️ &nbsp; 💬 &nbsp; ↗️</div>
            <div>🔖</div>
        </div>
        <div style="font-size:0.85rem; font-weight:700; color:#1F3B2E; margin:0.4rem 0;">1,420 likes</div>
        <div class="mockup-body-text">
            <b>captioncraft.creator</b> """ + display_caption + (""" <span class="mockup-more-fold">...more</span>""" if is_truncated else "") + """
        </div>
    """, unsafe_allow_html=True)

    if ht_str:
        st.markdown(f'<div style="font-size:0.85rem; color:#00376B; margin-bottom:0.4rem;">{ht_str}</div>', unsafe_allow_html=True)

    st.markdown("""
        <div style="font-size:0.75rem; color:#8E8E8E; text-transform:uppercase; margin-top:0.3rem;">2 hours ago</div>
        <div class="mockup-disclaimer">SIMULATION PREVIEW — Content not published to live Instagram</div>
    </div>
    """, unsafe_allow_html=True)


def render_twitter_mockup(caption_text: str, image_obj: Any = None, hashtags: list = None):
    """Renders an authentic X / Twitter post simulation with 280-char counter."""
    char_count = len(caption_text)
    exceeds_limit = char_count > 280
    overflow_chars = char_count - 280 if exceeds_limit else 0

    st.markdown("""
    <div class="mockup-wrapper">
        <div class="mockup-header-bar">
            <div class="mockup-user-group">
                <div class="mockup-avatar" style="background:#000000; color:#FFFFFF;">X</div>
                <div>
                    <div class="mockup-username">CaptionCraft Studio <span style="color:#1D9BF0;">✓</span></div>
                    <div class="mockup-handle">@captioncraft • 15m</div>
                </div>
            </div>
            <span class="mockup-badge-x">X / Twitter</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="mockup-body-text" style="font-size:1.02rem; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            {caption_text}
        </div>
    """, unsafe_allow_html=True)

    if image_obj:
        st.image(image_obj, use_container_width=True)

    # 280-char dynamic gauge & warning
    if exceeds_limit:
        st.markdown(f"""
        <div style="background:#FEF2F2; border:1px solid #F87171; border-radius:10px; padding:0.5rem 0.85rem; margin:0.6rem 0; font-size:0.84rem; color:#DC2626;">
            ⚠️ <b>Tweet Limit Exceeded ({char_count}/280 chars)</b> — Over by <b>{overflow_chars} characters</b>.<br>
            Standard tweets must be under 280 characters. Consider trimming or splitting into a thread.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #86EFAC; border-radius:10px; padding:0.4rem 0.85rem; margin:0.6rem 0; font-size:0.82rem; color:#15803D;">
            ✅ <b>Fits standard 280-char limit:</b> {char_count} / 280 chars ({280 - char_count} chars remaining)
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="mockup-actions-bar" style="color:#536471; font-size:0.92rem; padding-top:0.75rem;">
            <span>💬 48</span>
            <span>🔁 124</span>
            <span>❤️ 1.8K</span>
            <span>📊 32K</span>
            <span>🔖</span>
            <span>📤</span>
        </div>
        <div class="mockup-disclaimer">SIMULATION PREVIEW — Content not published to live X / Twitter</div>
    </div>
    """, unsafe_allow_html=True)


def render_linkedin_mockup(caption_text: str, image_obj: Any = None, hashtags: list = None, simulate_fold: bool = True):
    """Renders an authentic LinkedIn feed post simulation."""
    display_text = caption_text
    is_truncated = False
    if simulate_fold and len(caption_text) > 220:
        display_text = caption_text[:210]
        is_truncated = True

    st.markdown("""
    <div class="mockup-wrapper">
        <div class="mockup-header-bar">
            <div class="mockup-user-group">
                <div class="mockup-avatar" style="background:#0077B5; color:#FFFFFF;">IN</div>
                <div>
                    <div class="mockup-username">CaptionCraft Strategy Studio • 1st</div>
                    <div class="mockup-handle">AI Multimodal Content & Growth Lab • 3h • 🌐</div>
                </div>
            </div>
            <span class="mockup-badge-li">LinkedIn</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="mockup-body-text" style="font-size:0.92rem; font-family:-apple-system, system-ui, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            {display_text} """ + (""" <span class="mockup-more-fold" style="color:#0077B5;">...see more</span>""" if is_truncated else "") + f"""
        </div>
    """, unsafe_allow_html=True)

    if image_obj:
        st.image(image_obj, use_container_width=True)

    st.markdown("""
        <div style="font-size:0.78rem; color:#666666; padding:0.5rem 0 0.4rem 0; border-bottom:1px solid rgba(0,0,0,0.08);">
            👍 ❤️ 💡 842 • 56 comments • 12 reposts
        </div>
        <div class="mockup-actions-bar" style="color:#666666; font-size:0.88rem; font-weight:600; padding-top:0.6rem;">
            <span>👍 Like</span>
            <span>💬 Comment</span>
            <span>🔄 Repost</span>
            <span>📤 Send</span>
        </div>
        <div class="mockup-disclaimer">SIMULATION PREVIEW — Content not published to live LinkedIn</div>
    </div>
    """, unsafe_allow_html=True)


def render_tiktok_mockup(caption_text: str, image_obj: Any = None, hashtags: list = None):
    """Renders an authentic TikTok vertical media post simulation."""
    ht_list = hashtags or []
    ht_str = " ".join([f"#{h.lstrip('#')}" for h in ht_list])

    st.markdown("""
    <div class="mockup-wrapper" style="background:#0F0F12; color:#FFFFFF; border:1px solid #2A2A32;">
        <div class="mockup-header-bar" style="border-bottom:1px solid #222;">
            <div class="mockup-user-group">
                <div class="mockup-avatar" style="background:#FE2C55; color:#FFFFFF;">TT</div>
                <div>
                    <div class="mockup-username" style="color:#FFFFFF;">@captioncraft.ai</div>
                    <div class="mockup-handle" style="color:#A0A0B0;">Viral Sound • Creator Hub</div>
                </div>
            </div>
            <span class="mockup-badge-tt">TikTok</span>
        </div>
    """, unsafe_allow_html=True)

    if image_obj:
        st.image(image_obj, use_container_width=True)
    else:
        st.markdown("""
        <div class="mockup-image-frame" style="background:#18181E;">
            <div class="mockup-image-placeholder" style="background:transparent; color:#888899;">
                <span style="font-size:2.5rem;">🎵</span>
                <span>Vertical Video / Photo Mode Asset</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="mockup-body-text" style="color:#F1F1F5; font-size:0.9rem;">
            <b>@captioncraft.ai</b> {caption_text}
            <div style="color:#25F4EE; font-weight:600; margin-top:0.3rem;">{ht_str}</div>
        </div>
        <div style="font-size:0.8rem; color:#A0A0B0; margin:0.4rem 0;">
            🎵 Original Sound - Trending Beats (Audio Track)
        </div>
        <div class="mockup-actions-bar" style="border-top:1px solid #222; color:#F1F1F5; font-size:0.85rem;">
            <span>❤️ 84.5K</span>
            <span>💬 1,240</span>
            <span>🔖 9.4K</span>
            <span>↗️ 540</span>
        </div>
        <div class="mockup-disclaimer" style="color:#666677;">SIMULATION PREVIEW — Content not published to live TikTok</div>
    </div>
    """, unsafe_allow_html=True)


def render_threads_mockup(caption_text: str, image_obj: Any = None, hashtags: list = None):
    """Renders an authentic Threads post simulation."""
    st.markdown("""
    <div class="mockup-wrapper">
        <div class="mockup-header-bar">
            <div class="mockup-user-group">
                <div class="mockup-avatar" style="background:#101010; color:#FFFFFF;">@</div>
                <div>
                    <div class="mockup-username">captioncraft</div>
                    <div class="mockup-handle">2h • threads.net</div>
                </div>
            </div>
            <span class="mockup-badge-th">Threads</span>
        </div>
        <div class="mockup-body-text">
    """ + caption_text + """
        </div>
    """, unsafe_allow_html=True)

    if image_obj:
        st.image(image_obj, use_container_width=True)

    st.markdown("""
        <div class="mockup-actions-bar" style="font-size:1.15rem; color:#1F3B2E; padding-top:0.6rem;">
            <span>❤️ &nbsp; 💬 &nbsp; 🔁 &nbsp; ↗️</span>
        </div>
        <div style="font-size:0.8rem; color:#777777; margin-top:0.4rem;">42 replies • 312 likes</div>
        <div class="mockup-disclaimer">SIMULATION PREVIEW — Content not published to live Threads</div>
    </div>
    """, unsafe_allow_html=True)


def render_social_preview_tab():
    """Renders the Live Social Media Post Preview interface across 5 major platforms."""
    st.markdown("### 📱 Live Social Media Post Preview")
    st.caption("Inspect how your caption and visual assets appear across authentic simulated social feeds before posting.")

    # Caption source selection
    current_captions = st.session_state.get("generated_captions", [])
    default_text = st.session_state.get("preview_caption_text", "")
    if not default_text and current_captions:
        default_text = current_captions[0].get("caption", "")

    col_src1, col_src2 = st.columns([2, 1])
    with col_src1:
        if current_captions:
            cap_options = [f"#{idx+1} [{c.get('vibe_label', 'Option')}] — {c.get('caption', '')[:45]}..." for idx, c in enumerate(current_captions)]
            cap_options.append("✍️ Enter Custom Caption Text")
            chosen_cap_idx = st.selectbox("Load Caption from Current Batch", options=range(len(cap_options)), format_func=lambda i: cap_options[i])
            if chosen_cap_idx < len(current_captions):
                default_text = current_captions[chosen_cap_idx].get("caption", "")

    preview_input = st.text_area(
        "Caption Text for Simulation",
        value=default_text,
        height=120,
        key="preview_caption_editor"
    )

    # Image option
    preview_img_file = st.file_uploader("Upload Image to Include in Mockup (Optional)", type=["jpg", "jpeg", "png", "webp"], key="preview_img_uploader")
    preview_pil_img = None
    if preview_img_file:
        is_v, _, p_img, _ = utils.validate_image(preview_img_file)
        if is_v and p_img:
            preview_pil_img = p_img

    col_sim_fold, _ = st.columns([2, 3])
    with col_sim_fold:
        sim_fold_active = st.checkbox("Simulate mobile fold cutoff (...more / ...see more)", value=True, key="sim_fold_check")

    st.markdown("---")

    # Platform selector tabs
    sub_tab_ig, sub_tab_x, sub_tab_li, sub_tab_tt, sub_tab_th = st.tabs([
        "📸 Instagram",
        "🐦 X / Twitter",
        "💼 LinkedIn",
        "🎵 TikTok",
        "🧵 Threads"
    ])

    with sub_tab_ig:
        render_instagram_mockup(preview_input, preview_pil_img, simulate_fold=sim_fold_active)

    with sub_tab_x:
        render_twitter_mockup(preview_input, preview_pil_img)

    with sub_tab_li:
        render_linkedin_mockup(preview_input, preview_pil_img, simulate_fold=sim_fold_active)

    with sub_tab_tt:
        render_tiktok_mockup(preview_input, preview_pil_img)

    with sub_tab_th:
        render_threads_mockup(preview_input, preview_pil_img)


def render_viral_analyzer_tab():
    """Renders the AI Viral Caption Analyzer and One-Click Caption Improver."""
    st.markdown("### 🚀 AI Viral Caption Analyzer & Optimizer")
    st.caption("Evaluate your caption's engagement probability, hook magnetism, and scannability, then apply 1-click AI polish.")

    effective_api_key = ai_service.get_api_key(st.session_state.get("sidebar_api_key"))
    current_user_id = (st.session_state.get("user") or {}).get("user_id")

    current_captions = st.session_state.get("generated_captions", [])
    default_text = st.session_state.get("analyzer_input_caption", "")
    if not default_text and current_captions:
        default_text = current_captions[0].get("caption", "")

    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        if current_captions:
            an_options = [f"#{idx+1} [{c.get('vibe_label', 'Option')}] — {c.get('caption', '')[:50]}..." for idx, c in enumerate(current_captions)]
            an_options.append("✍️ Custom Text")
            sel_idx = st.selectbox("Select Caption to Audit", options=range(len(an_options)), format_func=lambda i: an_options[i], key="sel_anal_cap")
            if sel_idx < len(current_captions):
                default_text = current_captions[sel_idx].get("caption", "")

    anal_text = st.text_area(
        "Caption to Analyze",
        value=default_text,
        height=110,
        key="anal_caption_box"
    )

    c_p1, c_p2, c_p3 = st.columns([1.5, 1.5, 2])
    with c_p1:
        anal_platform = st.selectbox("Target Platform", PLATFORMS, index=0, key="anal_plat")
    with c_p2:
        anal_tone = st.selectbox("Target Tone", TONES, index=0, key="anal_tone")
    with c_p3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_analysis_btn = st.button("🚀 Evaluate Virality with AI", type="primary", use_container_width=True, key="btn_run_viral_eval")

    if run_analysis_btn:
        if not anal_text.strip():
            st.error("Please provide a caption to analyze.")
        elif not effective_api_key:
            st.error(ai_service.get_api_key_instruction())
        else:
            with st.spinner("Analyzing hook CTR, mobile readability, and viral metrics with Gemini..."):
                ok, eval_data, err_m = ai_service.analyze_viral_caption(
                    caption=anal_text,
                    platform=anal_platform,
                    tone=anal_tone,
                    api_key=effective_api_key
                )
                if ok:
                    st.session_state["viral_analysis_result"] = eval_data
                    st.session_state["analyzer_input_caption"] = anal_text
                    st.toast("Viral analysis complete!", icon="✨")
                    st.rerun()
                else:
                    st.error(err_m)

    # Render Evaluation Dashboard
    analysis = st.session_state.get("viral_analysis_result")
    if analysis:
        st.markdown("---")
        overall = analysis.get("overall_score", 0)

        # Score styling
        score_class = "viral-score-excellent" if overall >= 80 else ("viral-score-good" if overall >= 60 else "viral-score-fair")
        badge_label = "Viral Ready ✨" if overall >= 80 else ("Strong Engagement 👍" if overall >= 60 else "Needs Polish 🔧")

        st.markdown(f"""
        <div class="viral-gauge-card">
            <span class="tag-badge tag-badge-accent">{badge_label}</span>
            <div class="viral-score-number {score_class}">{overall}<span style="font-size:1.4rem; color:#5C7568;">/100</span></div>
            <div class="viral-score-verdict">{analysis.get('verdict', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📊 Algorithmic Scoring Breakdown")

        category_labels = {
            "hook_strength": ("🔥 Hook Strength", 25),
            "readability": ("📖 Mobile Readability", 20),
            "emotional_appeal": ("❤️ Emotional Appeal", 20),
            "cta_effectiveness": ("💬 CTA Effectiveness", 15),
            "platform_relevance": ("🎯 Platform Relevance", 20)
        }

        scores = analysis.get("scores", {})
        for cat_k, (cat_label, max_pts) in category_labels.items():
            cat_obj = scores.get(cat_k, {})
            c_score = cat_obj.get("score", 0)
            c_reason = cat_obj.get("reason", "")
            pct = int((c_score / max_pts) * 100) if max_pts > 0 else 0

            st.markdown(f"""
            <div class="viral-category-bar-box">
                <div class="viral-category-header">
                    <span>{cat_label}</span>
                    <span>{c_score} / {max_pts} pts</span>
                </div>
                <div class="viral-progress-bg">
                    <div class="viral-progress-fill" style="width: {pct}%;"></div>
                </div>
                <div class="viral-reason-text">{c_reason}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Strengths, Weaknesses, Suggestions
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown("##### 🟢 Strengths")
            for item in analysis.get("strengths", []):
                st.markdown(f'<div class="eval-bullet-green">✓ {item}</div>', unsafe_allow_html=True)
        with col_s2:
            st.markdown("##### 🟠 Areas to Refine")
            for item in analysis.get("weaknesses", []):
                st.markdown(f'<div class="eval-bullet-amber">! {item}</div>', unsafe_allow_html=True)
        with col_s3:
            st.markdown("##### 💡 Actionable Polish Tips")
            for item in analysis.get("suggestions", []):
                st.markdown(f'<div class="eval-bullet-purple">💡 {item}</div>', unsafe_allow_html=True)

        st.caption("*Disclaimer: AI viral analysis is an algorithmic heuristic and does not guarantee specific engagement metrics on third-party platforms.*")

        st.markdown("---")

        # One-Click Caption Improver
        st.markdown("#### ⚡ One-Click AI Caption Improver")
        st.caption("Apply focused algorithmic refinements to optimize this caption instantly:")

        imp_actions = [
            ("✨ Make It More Engaging", "engaging"),
            ("🔥 Create a Stronger Hook", "stronger_hook"),
            ("✂️ Make It Shorter", "shorter"),
            ("💬 Improve CTA", "better_cta"),
            ("🎯 Optimize for Selected Platform", "platform_optimize")
        ]

        action_cols = st.columns(len(imp_actions))
        selected_action = "engaging"
        chosen_action_label = st.radio(
            "Select Polish Goal",
            options=[a[0] for a in imp_actions],
            horizontal=True,
            key="radio_imp_action"
        )
        for label, act_key in imp_actions:
            if label == chosen_action_label:
                selected_action = act_key

        if st.button(f"⚡ Apply Polish ({chosen_action_label})", type="primary", use_container_width=True, key="btn_apply_polish"):
            if not effective_api_key:
                st.error(ai_service.get_api_key_instruction())
            else:
                with st.spinner("Rewriting & polishing with Gemini..."):
                    ok_imp, imp_data, err_imp = ai_service.improve_caption(
                        caption=anal_text,
                        action=selected_action,
                        platform=anal_platform,
                        tone=anal_tone,
                        api_key=effective_api_key
                    )
                    if ok_imp:
                        st.session_state["improved_caption_result"] = imp_data
                        st.toast("Caption improved successfully!", icon="🎉")
                        st.rerun()
                    else:
                        st.error(err_imp)

        # Show Side-by-Side Comparison
        improved = st.session_state.get("improved_caption_result")
        if improved:
            st.markdown("##### 🔄 Side-by-Side Comparison")
            c_comp1, c_comp2 = st.columns(2)

            orig_m = utils.calculate_text_metrics(improved["original_caption"])
            imp_m = utils.calculate_text_metrics(improved["improved_caption"])

            with c_comp1:
                st.markdown(f"""
                <div class="diff-box">
                    <span class="meta-pill">Original Version</span>
                    <span class="caption-metrics">{orig_m['characters']} chars • {orig_m['words']} words</span>
                    <div style="font-size:0.95rem; line-height:1.55; color:#1F3B2E; margin-top:0.6rem;">
                        {improved['original_caption']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with c_comp2:
                st.markdown(f"""
                <div class="diff-box" style="border: 2px solid #CBB3EB;">
                    <span class="tag-badge tag-badge-accent">Improved Version ✨</span>
                    <span class="caption-metrics">{imp_m['characters']} chars • {imp_m['words']} words</span>
                    <div style="font-size:0.95rem; line-height:1.55; color:#1F3B2E; margin-top:0.6rem; font-weight:500;">
                        {improved['improved_caption']}
                    </div>
                    <div style="font-size:0.82rem; color:#3D5A4C; margin-top:0.65rem;">
                        💡 <b>Changes:</b> {improved.get('improvement_summary', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            imp_text = improved["improved_caption"]
            imp_id = utils.generate_caption_id(imp_text, "improved")

            b_imp1, b_imp2, b_imp3, b_imp4 = st.columns([1.5, 1.2, 1.2, 1.5])
            with b_imp1:
                if st.button("✅ Keep This Version", key="btn_keep_improved", use_container_width=True):
                    # Add to session captions and save to history
                    new_item = {
                        "id": imp_id,
                        "index": 1,
                        "caption": imp_text,
                        "hook": improved.get("hook", ""),
                        "vibe_label": "AI Polished",
                        "hashtags": improved.get("hashtags", []),
                        "emojis": improved.get("emojis", []),
                        "cta": improved.get("cta", ""),
                        "platform": anal_platform,
                        "tone": anal_tone
                    }
                    st.session_state["generated_captions"] = [new_item] + st.session_state.get("generated_captions", [])
                    utils.save_generation_to_history(
                        mode="Polished-Caption",
                        input_summary=f"Polished: {imp_text[:60]}...",
                        tone=anal_tone,
                        platform=anal_platform,
                        length="Polished",
                        captions=[new_item],
                        user_id=current_user_id,
                        feature_type=utils.FEATURE_TEXT_TO_CAPTION
                    )
                    st.toast("Saved improved caption to active results & history!", icon="⭐")
            with b_imp2:
                with st.popover("📋 Copy"):
                    st.text_area("Ready to paste", value=imp_text, height=120, key="copy_imp_text")
            with b_imp3:
                is_imp_fav = utils.is_favorite(imp_id)
                fav_lbl = "❤️ Saved" if is_imp_fav else "🤍 Favorite"
                if st.button(fav_lbl, key="fav_imp_btn"):
                    if is_imp_fav:
                        utils.remove_favorite(imp_id)
                    else:
                        utils.add_favorite({
                            "id": imp_id,
                            "caption": imp_text,
                            "hook": improved.get("hook", ""),
                            "vibe_label": "AI Polished",
                            "hashtags": improved.get("hashtags", []),
                            "cta": improved.get("cta", ""),
                            "platform": anal_platform,
                            "tone": anal_tone
                        })
                    st.rerun()
            with b_imp4:
                if st.button("🚀 Re-Analyze", key="re_anal_btn", use_container_width=True):
                    st.session_state["analyzer_input_caption"] = imp_text
                    st.rerun()


def render_creator_tools_page():
    """Renders the Creator Tools page with Live Previews and Viral Caption Analyzer."""
    render_app_header(
        title="🛠️ Creator Tools Suite",
        subtitle="Simulate live feed appearances across 5 platforms and evaluate algorithmic viral engagement potential with AI."
    )

    t_prev, t_anal = st.tabs([
        "📱 Social Media Preview",
        "🚀 Viral Caption Analyzer"
    ])

    with t_prev:
        render_social_preview_tab()

    with t_anal:
        render_viral_analyzer_tab()


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
        mode_filter = st.selectbox("Filter Mode", ["All", "Text-to-Caption", "Image-to-Caption", "Emoji-to-Caption", "Multi-Platform", "Carousel-Story"])
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
elif page in ("Creator Tools", "Tools"):
    render_creator_tools_page()
elif page == "History":
    render_history_page()
elif page == "Favorites":
    render_favorites_page()
elif page == "About":
    render_about_page()
else:
    render_generate_page()
