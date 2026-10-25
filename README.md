# ✨ CaptionCraft AI — Multimodal Social Media Caption Studio

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Multimodal%20API-8E75C2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Auth%20%26%20History-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Asset%20Storage-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white)](https://cloudinary.com/)
[![Tests](https://img.shields.io/badge/Tests-57%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](backend/tests/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

**CaptionCraft AI** is a Generative AI social media caption studio designed for content creators, marketers, and digital brands. Powered by **Google Gemini** multimodal models (`google-genai`), the studio transforms text prompts, high-resolution imagery, and emoji sequences into viral, audience-tailored captions across 8 major social platforms.

Built with an enterprise-grade Python backend, MongoDB persistence, Cloudinary asset storage, Gmail SMTP password-recovery workflows, persistent cookie-backed sessions, and a custom **60–30–10 aesthetic design system**, CaptionCraft AI combines AI capabilities with a polished user experience.

---

## 📑 Table of Contents

- [🎨 Design Aesthetics & UI System](#-design-aesthetics--ui-system)
- [⚡ Key Features](#-key-features)
  - [1. User Authentication & Session Security](#1-user-authentication--session-security)
  - [2. Text-to-Caption Generator](#2-text-to-caption-generator)
  - [3. Image-to-Caption (Multimodal Vision + Cloudinary)](#3-image-to-caption-multimodal-vision--cloudinary)
  - [4. Emoji-to-Caption Mode](#4-emoji-to-caption-mode)
  - [5. User-Isolated History & Favorites](#5-user-isolated-history--favorites)
  - [6. Analytics & Caption Metrics](#6-analytics--caption-metrics)
- [🏗️ Project Architecture](#️-project-architecture)
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
- **Modular External CSS Architecture**: Zero inline CSS spaghetti in Python files. All styles are cleanly separated into `main.css`, `components.css`, `auth.css`, and `responsive.css`.

---

## ⚡ Key Features

### 1. User Authentication & Session Security
- **MongoDB-Backed Registration & Login**: Full schema validation for Full Name, Gender, Age (1–120), normalized Email, and Password (minimum 8 characters).
- **Bcrypt Hashing with Dynamic Salt**: Passwords are securely hashed and salted; plain-text passwords never touch database collections.
- **Persistent Browser Sessions**:
  - Implements cryptographically signed session tokens (`itsdangerous.URLSafeTimedSerializer`).
  - Stored in HTTP cookies (`captioncraft_session`) and verified against the MongoDB `sessions` collection with a 7-day rolling window.
  - **Preserves authenticated state across browser refreshes and page reloads**.
  - Explicit logout safely revokes both the browser cookie and the database session document.
- **Gmail SMTP Password Recovery**:
  - Delivers styled multipart HTML/plain-text password reset instructions via Gmail SMTP (`smtp.gmail.com:587` with STARTTLS).
  - Generates secure single-use 32-character tokens hashed with SHA-256 with a 15-minute expiry.
  - **Intelligent Google App Password Sanitization**: Automatically handles spaces, quotes, and stray keystrokes without throwing authentication errors.
  - **Categorized Diagnostic Feedback**: Accurately distinguishes between connection timeouts, TLS handshake failures, Google App Password bad credentials (`535 5.7.8`), and server disconnections.
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

### 4. Emoji-to-Caption Mode
- **6 Themed Emoji Categories**: Faces & Moods, Aesthetic Vibes, Hearts & Romance, Nature & Wanderlust, Food & Lifestyle, Wins & Celebration.
- **One-Click Story Presets**: Instant starter presets including *Tropical Getaway*, *Coffee & Cozy Books*, *Fitness Grinding*, and *Friday Night Out*.
- **Emoji-Only Mode**: Creative storytelling crafted purely through curated emoji arrangements paired with punchy micro-hooks.

### 5. User-Isolated History & Favorites
- **Multi-Tenant User Isolation**: Every history record is bound to the owner's `user_id`. Queries strictly enforce ownership boundaries, preventing cross-account exposure.
- **Separate Feature Views**: Dedicated tabs for **Text Captions** and **Image Captions**.
- **Management Controls**: One-click clipboard copy, individual record deletion with ownership verification, and bulk history purge.
- **Robust Export Serialization**:
  - Exports history to **JSON** and **CSV**.
  - Features custom serialization handling Python `datetime.datetime`, `datetime.date`, BSON `ObjectId`, and UUID instances to guarantee zero JSON serialization crashes.

### 6. Analytics & Caption Metrics
- Real-time character counters and word counts tailored to platform character limits.
- Hashtag frequency and density analysis.
- Readability metrics and engagement potential estimations.

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
    ├── ai_service.py           # Google Gemini API client, multimodal requests & JSON parsing
    ├── auth.py                 # Bcrypt hashing, persistent cookies, JWT, Gmail SMTP delivery
    ├── database.py             # MongoDB client, connection pooling & unique indexes
    ├── cloudinary_service.py   # Cloudinary image storage, SHA-256 deduplication cache
    ├── prompt_templates.py     # Prompt engineering templates for text, images, and emojis
    ├── utils.py                # Text metrics, fallback file storage, robust JSON/CSV serializers
    │
    ├── data/                   # Local Fallback Data Storage (when MongoDB is offline)
    │   ├── history.json        # Fallback history storage
    │   └── favorites.json      # Fallback favorites storage
    │
    └── tests/                  # Automated Test Suite (57 Unit & Integration Tests)
        ├── __init__.py
        ├── test_auth.py        # Authentication, bcrypt, sessions & input validation (19 tests)
        ├── test_captioncraft.py# Prompt generation, Gemini handling & text metrics (8 tests)
        ├── test_cloudinary_gmail.py # Cloudinary caching & Gmail SMTP delivery (15 tests)
        └── test_history.py     # Multi-user data isolation & datetime export serialization (15 tests)
```

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
# Optional: GEMINI_MODEL=gemini-2.5-flash

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

CaptionCraft AI includes an automated test suite comprising **57 tests** executed via Python's standard `unittest` framework:

```powershell
# Run the entire test suite (57 tests)
python -m unittest discover -s backend/tests -v
```

### Individual Test Suites:

| Suite | Focus Areas | Tests | Command |
|:---|:---|:---:|:---|
| **`test_auth.py`** | Registration validation, bcrypt hashing, session cookies, expiration, and database disconnect safety | **19** | `python -m unittest backend/tests/test_auth.py -v` |
| **`test_captioncraft.py`** | Prompt generation, JSON cleaners, text metrics, and offline utilities | **8** | `python -m unittest backend/tests/test_captioncraft.py -v` |
| **`test_cloudinary_gmail.py`** | Cloudinary uploads, SHA-256 deduplication, SMTP STARTTLS, password sanitization & diagnostics | **15** | `python -m unittest backend/tests/test_cloudinary_gmail.py -v` |
| **`test_history.py`** | User-to-user data isolation, cross-account access prevention, and datetime JSON/CSV export serialization | **15** | `python -m unittest backend/tests/test_history.py -v` |

---

## 🛡️ Security & Privacy Engineering

- **Zero Secret Ingestion**: `.env`, session keys, and database credentials are excluded from Git via comprehensive `.gitignore` rules.
- **Credential Sanitization**: Passwords, auth tokens, and session secrets are never printed in console logs, exception tracebacks, or API error messages.
- **Cryptographic Cookie Protection**: Persistent session tokens are signed using HMAC with SHA-512 serializers to prevent client-side tampering.
- **Single-Use Expiring Tokens**: Password-reset tokens use cryptographically random 32-character hex strings, hashed with SHA-256 in MongoDB, and automatically invalidated upon single use or after 15 minutes.
- **Cross-Account Isolation**: Multi-tenant database queries strictly query by verified `user_id`. Unauthenticated or manipulated IDs return empty record sets.
- **Safe Fallback Modes**: If MongoDB, Cloudinary, or Gmail SMTP are unreachable, CaptionCraft AI safely degrades into non-blocking fallback modes without crashing the active UI session.

---

## 📄 License & Authors

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed with ❤️ using **Streamlit**, **Google Gemini**, and **MongoDB**.
