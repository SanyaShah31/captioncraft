# ✨ CaptionCraft AI — Multimodal Caption Generator

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io)
[![MongoDB](https://img.shields.io/badge/MongoDB-Persistent%20Auth%20%26%20History-47A248.svg)](https://www.mongodb.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Multimodal%20API-8E75C2.svg)](https://ai.google.dev/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Image%20Storage-3448C5.svg)](https://cloudinary.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**CaptionCraft AI** is an enterprise-grade Generative AI social media caption studio built with Python, Streamlit, MongoDB, and Google Gemini multimodal models (`google-genai`). It features **Text-to-Caption**, **Image-to-Caption**, and **Emoji-to-Caption** generation modes alongside complete user authentication, Cloudinary asset storage, Gmail SMTP password-reset workflows, and user-isolated generation history.

---

## 🎨 Key Features & Modules

### 1. 🔐 User Authentication & Account Security
- **MongoDB-Backed Registration & Login**: Validates full name, gender, age, email format, and password criteria (minimum 8 characters).
- **Bcrypt Password Hashing**: Passwords are securely hashed with salted bcrypt (never stored in plain text).
- **Email Normalization**: Trims whitespace and normalizes case to prevent duplicate account creation.
- **Forgot Password via Gmail SMTP**:
  - Securely delivers responsive HTML and plain-text reset emails via Gmail SMTP (`smtp.gmail.com:587` with STARTTLS).
  - Uses cryptographically secure, single-use tokens hashed with SHA-256 and subject to a 15-minute expiration.
  - Automatic failed-token cleanup: Purges undelivered tokens from MongoDB on send failures.
  - Categorized SMTP error handling: Distinguishes Google App Password authentication failures (`535 5.7.8 BadCredentials`), network timeouts, and TLS errors without leaking secrets.
  - Anti-enumeration protection: Displays generic guidance when an entered email is unregistered.
- **Session State Management**: Preserves user identity across Streamlit reruns with clean logout controls.

### 2. ✍️ Text-to-Caption Generation
- Generates **5 tailored caption variations** per run:
  1. *Viral Hook* (bold attention-grabber)
  2. *Aesthetic Vibe* (atmospheric and visual)
  3. *Storyteller* (relatable narrative journey)
  4. *Witty Take* (playful, clever humor)
  5. *Minimalist* (clean, punchy, high-impact)
- **8 Tone Controls**: Funny, Aesthetic, Romantic, Professional, Inspirational, Emotional, Minimal, and Savage.
- **3 Length Options**: Short (10–25 words), Medium (30–70 words), Long (80–150 words).
- **8 Platforms**: Instagram, Twitter / X, LinkedIn, TikTok, Facebook, Pinterest, YouTube Shorts, Threads.
- Optional toggles for custom hashtag quantities and emojis.

### 3. 🖼️ Image-to-Caption (Multimodal Vision + Cloudinary)
- Upload images in **JPG, JPEG, PNG, or WebP** formats (up to 15MB).
- In-memory validation, thumbnail previews, and image dimension badges.
- **Gemini Multimodal Analysis**: Examines visual composition, color palettes, lighting, emotional mood, and subjects to generate context-aware captions.
- **Cloudinary Integration**:
  - Uploads images to Cloudinary with secure HTTPS URL and `public_id` retrieval.
  - Deduplication caching: Uses SHA-256 image hashes to avoid duplicate uploads of identical images.
  - Graceful fallback: Continues processing locally if Cloudinary credentials are not configured.

### 4. ✨ Emoji-to-Caption Mode
- **Categorized Emoji Picker**: Faces & Emotions, Vibes & Aesthetic, Hearts & Love, Travel & Nature, Food & Treats, Celebration & Win.
- **Story Presets**: One-click combinations for rapid prompt crafting (e.g., Vacation, Cozy Reading, Night Out, Gym & Fitness).
- **Emoji-Only Mode**: Generates creative sequences of emojis paired with witty micro-taglines.

### 5. 🗂️ User-Specific History & Favorites
- **Per-User Isolation**: Every history entry is tied to the authenticated user's `user_id`. User A can never access or view User B's records.
- **Feature Separation**: Separate history views for **Text-to-Caption** and **Image-to-Caption**.
- **Management Controls**: One-click copy, individual item deletion (with user ownership validation), and bulk history clearing.
- **Favorites & Exports**: Star your best captions and export your collection to **CSV** or **JSON**.

---

## 🏗️ Project Architecture

The project follows a clean architectural separation between presentation (`Frontend/`) and application services (`backend/`):

```text
captioncraft/
├── app.py                      # Root launcher (delegates to Frontend/app.py)
├── requirements.txt            # Python dependency manifest
├── .env.example                # Sample configuration template
├── .gitignore                  # Git ignore rules (secrets, caches, data)
├── README.md                   # Project documentation
│
├── Frontend/                   # All frontend UI presentation code
│   ├── __init__.py             # Frontend package initializer (path setup)
│   ├── app.py                  # Main Streamlit dashboard, navigation, tabs & layout
│   └── auth_ui.py              # Streamlit authentication views (Login, Register, Reset)
│
└── backend/                    # All backend logic, persistence, integrations & tests
    ├── __init__.py             # Backend package initializer (loads root .env)
    ├── auth.py                 # Core authentication, bcrypt hashing, tokens & Gmail SMTP
    ├── database.py             # MongoDB connection, collections & indexes
    ├── cloudinary_service.py   # Cloudinary image storage, validation & caching
    ├── ai_service.py           # Gemini SDK client, multimodal execution & JSON parsing
    ├── prompt_templates.py     # Prompt engineering templates, tones & platforms
    ├── utils.py                # History/favorites persistence, image validation & metrics
    ├── data/                   # Data storage directory (history & favorites)
    │   ├── history.json
    │   └── favorites.json
    └── tests/                  # Automated test suite (49 tests)
        ├── __init__.py
        ├── test_auth.py        # Authentication & MongoDB test cases (16 tests)
        ├── test_captioncraft.py# Prompts, metrics & AI service tests (8 tests)
        ├── test_cloudinary_gmail.py # Cloudinary & Gmail SMTP test cases (14 tests)
        └── test_history.py     # User history isolation & separation tests (11 tests)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **MongoDB**: Local community server running on port `27017` or a MongoDB Atlas URI.
- **Google Gemini API Key**: Free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
- *(Optional)* **Gmail App Password**: For password-reset email delivery.
- *(Optional)* **Cloudinary Credentials**: For remote image hosting.

### 2. Installation

Clone or download the repository, then create and activate a virtual environment:

```bash
# Clone the repository
cd captioncraft

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in your configuration:

```env
# ---------------------------------------------------------------------
# Google Gemini API Configuration (Required for Caption Generation)
# ---------------------------------------------------------------------
GEMINI_API_KEY=AIzaSyYourActualGeminiApiKeyHere

# ---------------------------------------------------------------------
# MongoDB Configuration (Required for Authentication & History)
# ---------------------------------------------------------------------
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=captioncraft_db

# ---------------------------------------------------------------------
# Gmail SMTP Configuration (Required for Password Reset Emails)
# ---------------------------------------------------------------------
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=xxxx xxxx xxxx xxxx
APP_BASE_URL=http://localhost:8501

# ---------------------------------------------------------------------
# Cloudinary Image Storage (Optional: for Image-to-Caption hosting)
# ---------------------------------------------------------------------
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

#### How to Generate a Gmail App Password:
1. Navigate to your [Google Account Security Settings](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned **ON**.
3. Go to [App Passwords](https://myaccount.google.com/apppasswords).
4. Enter an app name (e.g., `CaptionCraft AI`) and click **Create**.
5. Copy the 16-character code into `EMAIL_PASS` in your `.env` file.

---

## 💻 Running the Application

You can launch CaptionCraft AI using either the standard root launcher or directly from the `Frontend` package:

### Option A: Standard Root Launcher (Recommended)
```bash
streamlit run app.py
```

### Option B: Direct Frontend Entry Point
```bash
streamlit run Frontend/app.py
```

The application will launch and open automatically in your browser at:
`http://localhost:8501`

---

## 🧪 Testing & Verification

CaptionCraft AI includes a comprehensive automated test suite with **49 tests** covering authentication, history isolation, Cloudinary uploads, Gmail SMTP delivery, and prompt engineering.

### Run All Tests:
```bash
python -m unittest discover -s backend/tests -v
```

### Run Individual Test Suites:
```bash
# Authentication & MongoDB Integration (16 tests)
python -m unittest backend/tests/test_auth.py -v

# Prompt Templates, Text Metrics & AI Service (8 tests)
python -m unittest backend/tests/test_captioncraft.py -v

# Cloudinary Storage & Gmail SMTP Password Reset (14 tests)
python -m unittest backend/tests/test_cloudinary_gmail.py -v

# User-Specific History Isolation & Separation (11 tests)
python -m unittest backend/tests/test_history.py -v
```

---

## 🛡️ Security Best Practices

- **Zero Credential Leaks**: API keys, passwords, and MongoDB URIs are excluded from Git via `.gitignore`.
- **Safe Password Storage**: Passwords are protected with salted `bcrypt` hashes.
- **Single-Use Tokens**: Password reset tokens use SHA-256 hashes and expire automatically after 15 minutes.
- **Anti-Enumeration Protection**: Forgot-password submission preserves generic confirmation messaging for unregistered email addresses.
- **Automatic Token Invalidation**: Failed SMTP attempts immediately remove undelivered tokens from MongoDB.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
