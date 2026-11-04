# ✨ CaptionCraft AI 2.0 — Multimodal Social Media Caption Studio

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-google--genai%20SDK-8E75C2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Auth%20%26%20History-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Asset%20Storage-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white)](https://cloudinary.com/)
[![Pandas](https://img.shields.io/badge/Pandas-Export%20Engine-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Tests](https://img.shields.io/badge/Tests-38%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](backend/tests/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

**CaptionCraft AI 2.0** is an enterprise-grade AI social media content creation suite designed for content creators, agencies, founders, and social media managers. Powered by **Google Gemini** multimodal models (`google-genai`), the studio transforms text concepts, multi-image sequences, and emoji combinations into viral, platform-tailored copy across 8 major social networks.

Built with a modular Python backend, MongoDB persistence, Cloudinary asset storage, Gmail SMTP password-recovery workflows, persistent cookie-backed sessions, and a custom **60–30–10 spatial design system**, CaptionCraft AI pairs generative AI with a refined user experience.

---

## 📑 Table of Contents

- [🎨 Design Aesthetics & UI System](#-design-aesthetics--ui-system)
- [⚡ Key Features (CaptionCraft AI 2.0)](#-key-features-captioncraft-ai-20)
  - [1. User Authentication & Session Security](#1-user-authentication--session-security)
  - [2. Text-to-Caption Generator](#2-text-to-caption-generator)
  - [3. Image-to-Caption (Multimodal Vision + Cloudinary)](#3-image-to-caption-multimodal-vision--cloudinary)
  - [4. 🎭 Emoji-to-Caption Mode](#4--emoji-to-caption-mode)
  - [5. 📱 Live Social Media Post Previews (Creator Tools)](#5--live-social-media-post-previews-creator-tools)
  - [6. 🔬 AI Viral Caption Analyzer & 1-Click Improver](#6--ai-viral-caption-analyzer--1-click-improver)
  - [7. 🌍 One-Click Multi-Platform Generator](#7--one-click-multi-platform-generator)
  - [8. 📸 AI Multi-Image Carousel Storyteller & Photo Dump](#8--ai-multi-image-carousel-storyteller--photo-dump)
  - [9. User-Isolated History & Favorites](#9-user-isolated-history--favorites)
  - [10. Data Export & Analytics (Pandas Engine)](#10-data-export--analytics-pandas-engine)
- [🏗️ Project Architecture](#️-project-architecture)
- [🔑 Google Gemini API Configuration](#-google-gemini-api-configuration)
- [🚀 Quick Start Guide](#-quick-start-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Installation](#2-installation)
  - [3. Environment Configuration](#3-environment-configuration)
  - [4. Running the Studio](#4-running-the-studio)
- [🧪 Automated Test Suite](#-automated-test-suite)
- [🛡️ Security & Privacy Engineering](#️-security--privacy-engineering)
- [📄 License & Authors](#-license--authors)

---

## 🎨 Design Aesthetics & UI System

CaptionCraft AI features a custom-engineered **60–30–10 color harmony** and a responsive layout that replaces default Streamlit elements with an application-owned, cohesive canvas:

| Ratio | Color Palette | Hex Code | Purpose |
|:---:|:---|:---:|:---|
| **60%** | **Warm Beige** | `#E8DCC6` | Dominant page background, canvas surface, spacious padding |
| **30%** | **Deep Forest Green** / **Sidebar Green** | `#1F3B2E` / `#294A39` | High-contrast readable typography, sidebar navigation, card headers |
| **10%** | **Soft Lavender** | `#CBB3EB` | Interactive CTA buttons, active tabs, sparkle badges, focus rings |

### UI Highlights:
- **Application-Owned Header**: Integrated seamlessly inside the main content canvas, featuring the brand badge, dynamic greeting, current page indicator, and quick actions.
- **Cute & Animated Authentication Experience**: Soft cream authentication cards, floating sparkle icons with `@keyframes` animations, pastel badges, and gentle focus transitions.
- **Accessibility & Motion Controls**: Full compliance with `@media (prefers-reduced-motion: reduce)` to disable decorative floating and transforms for motion-sensitive users.
- **Modular External CSS Architecture**: Zero inline CSS clutter in Python files. All styles are cleanly separated into `main.css`, `components.css`, `auth.css`, and `responsive.css`.

---

## ⚡ Key Features (CaptionCraft AI 2.0)

### 1. User Authentication & Session Security
- **MongoDB-Backed Registration & Login**: Full schema validation for Full Name, Gender, Age (1–120), normalized Email, and Password (minimum 8 characters).
- **Bcrypt Hashing with Dynamic Salt**: Passwords are securely hashed and salted; plain-text passwords never touch database collections.
- **Persistent Browser Sessions**:
  - Cryptographically signed session tokens (`itsdangerous.URLSafeTimedSerializer`).
  - Stored in HTTP cookies (`captioncraft_session`) and verified against the MongoDB `sessions` collection with a 7-day rolling window.
  - **Preserves authenticated state across browser refreshes and page reloads**.
  - Explicit logout safely revokes both the browser cookie and the database session document.
- **Gmail SMTP Password Recovery**:
  - Multipart HTML/plain-text password reset instructions via Gmail SMTP (`smtp.gmail.com:587` with STARTTLS).
  - Single-use 32-character tokens hashed with SHA-256 with a 15-minute expiry.
  - **Intelligent Google App Password Sanitization**: Automatically handles spaces, quotes, and stray keystrokes without throwing authentication errors.
  - Anti-enumeration protection prevents leaking user existence.

### 2. Text-to-Caption Generator
- **5 Creative Variations per Generation**:
  1. *Viral Hook* — High-CTR, punchy opening line designed to stop scrolling.
  2. *Aesthetic Vibe* — Atmospheric, poetic, visually evocative prose.
  3. *Storyteller* — Relatable micro-narrative exploring journey and context.
  4. *Witty Take* — Clever, playful humor, puns, and banter.
  5. *Minimalist* — Short, clean, high-impact statement.
- **8 Dynamic Tones**: Funny, Aesthetic, Romantic, Professional, Inspirational, Emotional, Minimal, and Savage.
- **3 Length Formats**: Short (10–25 words), Medium (30–70 words), Long (80–150 words).
- **8 Platform Targets**: Instagram, Twitter / X, LinkedIn, TikTok, Facebook, Pinterest, YouTube Shorts, and Threads.
- **Custom Controls**: Configurable hashtag counts (0 to 30) and toggleable emoji density.

### 3. Image-to-Caption (Multimodal Vision + Cloudinary)
- **Supported Formats**: JPG, JPEG, PNG, WebP up to 15MB.
- **Gemini Multimodal Vision Analysis**: Evaluates image composition, subjects, lighting, focal points, color harmony, and emotional mood to generate contextual captions.
- **Cloudinary Cloud Storage Integration**:
  - Securely uploads visual assets to Cloudinary and stores HTTPS URLs and `public_id`s with the generated caption.
  - **SHA-256 Deduplication Cache**: Calculates image content hashes before uploading to prevent duplicate storage consumption.
  - **Graceful Offline Fallback**: Generates captions using in-memory byte buffers if Cloudinary credentials are not configured.

### 4. 🎭 Emoji-to-Caption Mode
- **10 Themed Emoji Categories**: Emotions, Lifestyle, Travel, Food, Love, Celebration, Fitness, Nature, Technology, and Creativity.
- **8 Instant Story Presets**:
  - ☕ *Coffee & Cozy*
  - 🌴 *Tropical Vacation*
  - ❤️ *Love & Relationships*
  - 🌅 *Sunset Vibes*
  - 🎉 *Party & Celebration*
  - 💪 *Fitness Motivation*
  - 🌸 *Self-Care Day*
  - 🌧️ *Rainy Day Mood*
- **Emoji-Only Mode**: Creative storytelling crafted purely through curated emoji arrangements paired with punchy micro-hooks.
- **Two-Way Synchronized Palette**: Click-to-add emoji chips, custom editable sequence input, instant clear controls, and bidirectional session-state synchronization ensuring the latest sequence is always passed to Gemini without stale caching.

### 5. 📱 Live Social Media Post Previews (Creator Tools)
- **Authentic Feed Simulations** across 5 platforms:
  - **Instagram**: Avatar, handle, image frame, action icons, likes counter, bold username, and **simulated "...more" fold cutoff**.
  - **X / Twitter**: Avatar, display name, verified badge (`✓`), full tweet text, rounded media frame, and **real-time 280-char limit indicator with overflow warning**.
  - **LinkedIn**: Professional avatar, headline, mobile-scannable paragraphs, **simulated "...see more" fold**, and reaction stats.
  - **TikTok**: Vertical media card, right action rail (Likes, Comments, Bookmarks, Shares, rotating disc), and bottom caption overlay.
  - **Threads**: Clean minimalist typography, engagement badges, and discussion counters.
- Strictly labeled as *Simulation Preview — Content not published to live platforms*.

### 6. 🔬 AI Viral Caption Analyzer & 1-Click Improver
- **100-Point Scoring Matrix across 5 Categories**:
  - *Hook Strength* (Max 25 pts)
  - *Mobile Readability* (Max 20 pts)
  - *Emotional Appeal* (Max 20 pts)
  - *CTA Effectiveness* (Max 15 pts)
  - *Platform Relevance* (Max 20 pts)
- **Diagnostic Insights**: Strengths, weaknesses, and actionable algorithmic polish tips.
- **One-Click AI Improver**: Refines captions with 5 directives:
  - *✨ Make It More Engaging*
  - *🔥 Create a Stronger Hook*
  - *✂️ Make It Shorter*
  - *💬 Improve CTA*
  - *🎯 Optimize for Selected Platform*
- **Side-by-Side Comparison**: Review original vs improved version with diff metrics and 1-click adoption.

### 7. 🌍 One-Click Multi-Platform Generator
- **Simultaneous Cross-Platform Generation**: Enter an idea or image once and craft tailored versions for **Instagram, X / Twitter, LinkedIn, TikTok, and Threads**.
- **Platform-Native Nuances**:
  - X / Twitter enforced under 280 characters.
  - LinkedIn structured with thought-leadership paragraphs.
  - Instagram optimized for line 1 hook before fold.
  - TikTok styled with high-velocity tags and hooks.
  - Threads formatted with conversational dialogue starters.
- **Batch Operations**: Global *Copy All Platforms*, *Download TXT*, and *Export CSV* via Pandas.

### 8. 📸 AI Multi-Image Carousel Storyteller & Photo Dump
- **Multi-Image Upload**: Upload 2 to 5 images (JPG, PNG, WebP) with thumbnail ordering and slide role indicators.
- **Sequential Storyline**:
  - *Slide 1 (Cover Hook)*: High-CTR scroll-stopping title.
  - *Slides 2–N-1 (Story Progression)*: Contextual transitions and 3–6 word on-screen text overlay suggestions.
  - *Final Slide (Closing CTA)*: Engagement prompts (Save, Share, Comment, Follow).
- **Master Caption & Single-Slide Regeneration**: Post-level master caption ready to paste, single-slide targeted regeneration, and full storyboard export.

### 9. User-Isolated History & Favorites
- **Multi-Tenant User Isolation**: Every history record is bound to the owner's `user_id`. Queries strictly enforce ownership boundaries, preventing cross-account exposure.
- **Dedicated Feature Views**: Separate history filters for **Text-to-Caption**, **Image-to-Caption**, **Emoji-to-Caption**, **Multi-Platform**, and **Carousel-Story**.
- **Management Controls**: One-click clipboard copy, individual record deletion with ownership verification, and bulk history purge.

### 10. Data Export & Analytics (Pandas Engine)
- Exports history, favorites, and multi-platform outputs to **JSON** and **CSV** via structured **Pandas DataFrames**.
- Real-time character counters and word counts tailored to platform character limits.
- ISO 8601 datetime serialization preventing export crashes.

---

## 🏗️ Project Architecture

The codebase enforces a clean modular architecture separating the Streamlit presentation layer from backend business logic:

```text
captioncraft/
├── app.py                      # Root launcher (preserves standard streamlit entrypoint)
├── requirements.txt            # Python dependencies manifest
├── .env.example                # Safe environment configuration template
├── .gitignore                  # Git exclusions (secrets, caches, local data)
├── README.md                   # Project documentation
│
├── Frontend/                   # Presentation Layer (Streamlit UI)
│   ├── __init__.py             # Package initializer and sys.path resolution
│   ├── app.py                  # Main dashboard, tab routing, generator layouts & exports
│   ├── auth_ui.py              # Cute animated views: Login, Register, Forgot, Reset
│   │
│   └── styles/                 # Modular Vanilla CSS Stylesheets
│       ├── main.css            # 60-30-10 palette variables, typography & layout resets
│       ├── components.css      # Generator cards, buttons, badges, tabs & analytics
│       ├── auth.css            # Soft cream cards, lavender shadows & floating sparkle icons
│       └── responsive.css      # Tablet & mobile media query adaptations
│
└── backend/                    # Application & Service Layer
    ├── __init__.py             # Package initializer and environment loading
    ├── ai_service.py           # Google Gemini API client, key healing, model fallbacks & JSON parser
    ├── auth.py                 # Bcrypt hashing, persistent cookies, JWT, Gmail SMTP delivery
    ├── database.py             # MongoDB client, connection pooling & unique indexes
    ├── cloudinary_service.py   # Cloudinary image storage, SHA-256 deduplication cache
    ├── prompt_templates.py     # Multimodal prompt templates for all 5 generation features
    ├── utils.py                # Text metrics, fallback file storage, Pandas DataFrame exports
    │
    ├── data/                   # Local Fallback Data Storage (when MongoDB is offline)
    │   ├── history.json        # Fallback history storage
    │   └── favorites.json      # Fallback favorites storage
    │
    └── tests/                  # Automated Test Suite (38 Unit & Integration Tests)
        ├── __init__.py
        ├── test_auth.py            # Authentication, bcrypt, sessions & input validation
        ├── test_carousel_story.py  # Carousel storyteller prompts, slides & slide regeneration
        ├── test_emoji_caption.py   # Emoji-to-caption prompts, state flow & regression tests
        ├── test_multi_platform.py  # Multi-platform generation, Pandas export & platform limits
        ├── test_social_preview.py  # Live feed simulation, text metrics & fold calculations
        ├── test_utils_history.py   # Multi-user data isolation & datetime export serialization
        └── test_viral_analyzer.py  # 100-point viral scoring, actions & improvement prompt tests
```

---

## 🔑 Google Gemini API Configuration

CaptionCraft AI supports the official **`google-genai`** SDK with resilient credential handling:

### 1. Supported Key Formats
- Standard API Keys (`AIzaSy...`)
- Modern Google AI Studio Authorization Keys (`AQ...`)
- **Self-Healing Key Sanitizer**: Automatically strips surrounding whitespace, quotes, and repairs accidental duplicate-character paste typos (e.g., `AAQ.` normalized to `AQ.`).

### 2. Configuration Precedence
The application resolves your Gemini API key in order:
1. **Sidebar Manual Override**: Entered in the sidebar "⚙️ Configure API Key" field.
2. **`GEMINI_API_KEY`**: Set in `.env` or system environment.
3. **`GOOGLE_API_KEY`**: Secondary fallback environment variable.
4. **`st.secrets`**: Streamlit secrets configuration (if hosted on Streamlit Cloud).

### 3. Recommended Models & Automatic Fallbacks
Configured in `backend/ai_service.py` with automatic graceful fallback if a model experiences high demand:
- **`gemini-3.5-flash`** (Default / Primary) — Ultra-fast, low-latency multimodal reasoning.
- **`gemini-3.6-flash`** (High Throughput)
- **`gemini-3.5-flash-lite`** (Ultra-lightweight)
- **`gemini-flash-lite-latest`**

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: Version `3.10` or higher (tested on Python 3.13).
- **MongoDB**: Local Community Server running at `mongodb://localhost:27017` or a MongoDB Atlas connection string.
- **Google Gemini API Key**: Obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
- *(Optional)* **Gmail App Password**: For password reset email delivery.
- *(Optional)* **Cloudinary Account**: For remote image hosting.

### 2. Installation

```powershell
# 1. Clone the repository
git clone https://github.com/SanyaShah31/captioncraft.git
cd captioncraft

# 2. Create and activate a Python virtual environment
# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example configuration to `.env`:

```powershell
# Windows:
copy .env.example .env

# Linux / macOS:
cp .env.example .env
```

Open `.env` in your editor and configure your credentials:

```env
# =====================================================================
# Google Gemini API Configuration (Required for Caption Generation)
# =====================================================================
GEMINI_API_KEY=your_google_gemini_api_key_here

# =====================================================================
# MongoDB Configuration (Required for Authentication & History)
# =====================================================================
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=captioncraft_db

# =====================================================================
# Gmail SMTP Configuration (Required for Password Reset Emails)
# =====================================================================
EMAIL_USER=your_gmail_address@gmail.com
EMAIL_PASS=xxxx xxxx xxxx xxxx
APP_BASE_URL=http://localhost:8501

# =====================================================================
# Cloudinary Image Storage (Optional: for Remote Image Hosting)
# =====================================================================
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

> [!TIP]
> **How to create a Google App Password:**
> 1. Visit your [Google Account Security Settings](https://myaccount.google.com/security).
> 2. Enable **2-Step Verification**.
> 3. Go to [Google App Passwords](https://myaccount.google.com/apppasswords).
> 4. Create an entry (e.g. `CaptionCraft`) and paste the 16-character code into `EMAIL_PASS`.

### 4. Running the Studio

Start the application using either the root launcher or direct entrypoint:

```powershell
# Standard Root Launcher (Recommended)
streamlit run app.py

# Or Direct Frontend Entry Point
streamlit run Frontend/app.py
```

The studio will launch automatically in your default browser at:
`http://localhost:8501`

---

## 🧪 Automated Test Suite

CaptionCraft AI includes an automated test suite comprising **38 tests** executed via Python's standard `unittest` framework:

```powershell
# Run the entire test suite (38 tests)
python -m unittest discover -s backend/tests -v
```

### Individual Test Suites:

| Suite | Focus Areas | Tests | Command |
|:---|:---|:---:|:---|
| **`test_auth.py`** | Registration validation, bcrypt hashing, session cookies, expiration, and database disconnect safety | **4** | `python -m unittest backend/tests/test_auth.py -v` |
| **`test_emoji_caption.py`** | Emoji prompt building, emoji-only mode, state sync & regression tests against stale sequences | **10** | `python -m unittest backend/tests/test_emoji_caption.py -v` |
| **`test_multi_platform.py`** | Multi-platform generation, 280-char boundaries, Pandas DataFrame and CSV export serialization | **6** | `python -m unittest backend/tests/test_multi_platform.py -v` |
| **`test_carousel_story.py`** | Multi-image sequence generation, cover hooks, CTAs, and single-slide regeneration | **4** | `python -m unittest backend/tests/test_carousel_story.py -v` |
| **`test_viral_analyzer.py`** | 100-pt scoring matrix, algorithmic diagnosis, and 5-action caption improvement prompts | **5** | `python -m unittest backend/tests/test_viral_analyzer.py -v` |
| **`test_social_preview.py`** | Feed preview metrics, simulated fold thresholds, character overflow indicators | **4** | `python -m unittest backend/tests/test_social_preview.py -v` |
| **`test_utils_history.py`** | Multi-user data isolation, cross-account access prevention, and datetime export serialization | **5** | `python -m unittest backend/tests/test_utils_history.py -v` |

---

## 🛡️ Security & Privacy Engineering

- **Zero Secret Ingestion**: `.env`, session keys, and database credentials are excluded from Git via comprehensive `.gitignore` rules.
- **Credential Sanitization**: Passwords, auth tokens, and session secrets are never printed in console logs, exception tracebacks, or API error messages. Masked previews (e.g. `AQ.Ab...GFrA`) are displayed safely in the UI.
- **Cryptographic Cookie Protection**: Persistent session tokens are signed using HMAC with SHA-512 serializers to prevent client-side tampering.
- **Single-Use Expiring Tokens**: Password-reset tokens use cryptographically random 32-character hex strings, hashed with SHA-256 in MongoDB, and automatically invalidated upon single use or after 15 minutes.
- **Cross-Account Isolation**: Multi-tenant database queries strictly query by verified `user_id`. Unauthenticated or manipulated IDs return empty record sets.
- **Safe Fallback Modes**: If MongoDB, Cloudinary, or Gmail SMTP are unreachable, CaptionCraft AI safely degrades into non-blocking fallback modes without crashing the active UI session.

---

## 📄 License & Authors

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed with ❤️ using **Streamlit**, **Google Gemini**, and **MongoDB**.
