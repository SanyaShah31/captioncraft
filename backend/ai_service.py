"""
AI Service module for CaptionCraft AI.
Integrates with the official Google Gemini Python SDK (google-genai)
with graceful fallback to google-generativeai.
Handles Text-to-Caption, Image-to-Caption, and Emoji-to-Caption generation.
"""

import os
import sys
from pathlib import Path
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from dotenv import load_dotenv, find_dotenv

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

from prompt_templates import (
    SYSTEM_INSTRUCTION,
    build_text_to_caption_prompt,
    build_image_to_caption_prompt,
    build_emoji_to_caption_prompt
)
from utils import generate_caption_id

DEFAULT_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-pro"
]

def get_api_key(override_key: Optional[str] = None) -> Optional[str]:
    """
    Retrieves the Google Gemini API key from:
    1. UI override parameter
    2. Environment variable GEMINI_API_KEY
    3. Streamlit secrets (if available)
    """
    if override_key and override_key.strip():
        return override_key.strip()

    # Check os environment / .env
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    # Check Streamlit secrets if running inside streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_key = st.secrets["GEMINI_API_KEY"]
            if sec_key and sec_key.strip():
                return sec_key.strip()
    except Exception:
        pass

    return None

def is_api_key_configured(override_key: Optional[str] = None) -> bool:
    """Checks whether an API key is present."""
    key = get_api_key(override_key)
    return bool(key and len(key) >= 10 and not key.startswith("your_gemini_api_key"))

def get_api_key_instruction() -> str:
    """Returns instructions on how to configure the Gemini API key."""
    return (
        "**Gemini API Key Missing or Invalid**\n\n"
        "To enable AI caption generation:\n"
        "1. Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).\n"
        "2. Either:\n"
        "   - Enter it directly into the **API Key** field in the sidebar, OR\n"
        "   - Create a `.env` file in the project folder with:\n"
        "     ```\n"
        "     GEMINI_API_KEY=your_actual_api_key_here\n"
        "     ```\n"
        "3. Refresh the page or click 'Generate'."
    )

def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """
    Extracts and parses JSON object from Gemini response.
    Handles markdown code blocks and partial wrappers.
    """
    text = raw_text.strip()

    # Look for ```json ... ``` blocks
    json_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_block:
        text = json_block.group(1).strip()
    else:
        # Look for the outer-most curly braces
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(1).strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict) or "captions" not in parsed:
        raise ValueError("Response JSON does not contain the expected 'captions' array.")

    return parsed

def _normalize_captions(raw_captions: List[Dict[str, Any]], platform: str, tone: str) -> List[Dict[str, Any]]:
    """Ensures each caption object has all expected fields and unique IDs."""
    normalized = []
    default_vibes = ["The Viral Hook", "The Core Aesthetic", "The Storyteller", "The Witty Take", "The Minimalist"]

    for idx, item in enumerate(raw_captions):
        caption_text = item.get("caption") or item.get("text") or ""
        if not caption_text.strip():
            continue

        hook = item.get("hook") or caption_text.split("\n")[0][:80]
        vibe_label = item.get("vibe_label") or (default_vibes[idx] if idx < len(default_vibes) else f"Option #{idx+1}")
        hashtags = item.get("hashtags") or []
        if isinstance(hashtags, str):
            hashtags = [h.strip() for h in hashtags.split() if h.strip()]
        emojis = item.get("emojis") or []
        if isinstance(emojis, str):
            emojis = [e.strip() for e in emojis.split() if e.strip()]
        cta = item.get("cta") or ""

        cid = generate_caption_id(caption_text, str(idx))

        normalized.append({
            "id": cid,
            "index": idx + 1,
            "caption": caption_text.strip(),
            "hook": hook.strip(),
            "vibe_label": vibe_label,
            "hashtags": hashtags,
            "emojis": emojis,
            "cta": cta.strip(),
            "platform": platform,
            "tone": tone
        })

    return normalized

def _call_gemini(
    prompt: str,
    image: Optional[Image.Image] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Executes multimodal Gemini request using official google-genai SDK,
    with fallback to google-generativeai if needed.
    Returns: (success, response_text_or_error, used_model_name)
    """
    key = get_api_key(api_key)
    if not key or not is_api_key_configured(key):
        return False, get_api_key_instruction(), None

    if model_name:
        models_to_try = [model_name] + [m for m in DEFAULT_MODELS if m != model_name]
    else:
        models_to_try = list(DEFAULT_MODELS)
    last_error = ""

    # Strategy 1: Official google-genai SDK
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        for model_candidate in models_to_try:
            if not model_candidate:
                continue
            try:
                contents = [image, prompt] if image is not None else [prompt]
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.75,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=contents,
                    config=config
                )
                if response and response.text:
                    return True, response.text, model_candidate
            except Exception as e:
                last_error = str(e)
                # Continue trying next model if model not found or quota
                continue
    except ImportError:
        pass
    except Exception as e:
        last_error = str(e)

    # Strategy 2: Fallback to google-generativeai if available
    try:
        import google.generativeai as legacy_genai

        legacy_genai.configure(api_key=key)
        for model_candidate in models_to_try:
            if not model_candidate:
                continue
            try:
                gen_model = legacy_genai.GenerativeModel(
                    model_name=model_candidate,
                    system_instruction=SYSTEM_INSTRUCTION,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.75
                    }
                )
                inputs = [image, prompt] if image is not None else prompt
                response = gen_model.generate_content(inputs)
                if response and response.text:
                    return True, response.text, model_candidate
            except Exception as e:
                last_error = str(e)
                continue
    except Exception as e:
        last_error = str(e)

    # If all attempts failed, craft informative error
    friendly_msg = f"Gemini API request failed: {last_error}"
    if "403" in last_error or "API_KEY_INVALID" in last_error.upper() or "PERMISSION_DENIED" in last_error.upper():
        friendly_msg = (
            "**Gemini API Authentication Failed**\n\n"
            "Your provided API key appears to be invalid or lacks permissions.\n"
            "Please check that you copied the complete key from [Google AI Studio](https://aistudio.google.com/app/apikey)."
        )
    elif "429" in last_error or "RESOURCE_EXHAUSTED" in last_error.upper():
        friendly_msg = (
            "**Gemini API Quota Exceeded**\n\n"
            "The free tier quota for this API key has been reached. Please wait a moment before retrying, "
            "or verify your account limits in Google AI Studio."
        )
    return False, friendly_msg, None

# ---------------------------------------------------------------------
# Public Generation APIs
# ---------------------------------------------------------------------

def generate_text_captions(
    topic: str,
    tone: str,
    platform: str,
    length: str,
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    include_emojis: bool = True,
    audience: Optional[str] = None,
    extra_notes: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Generates 5 captions from a text description."""
    if not topic or not topic.strip():
        return False, [], "Please provide a topic, keywords, or description for your caption."

    prompt = build_text_to_caption_prompt(
        topic=topic,
        tone=tone,
        platform=platform,
        length=length,
        include_hashtags=include_hashtags,
        hashtag_count=hashtag_count,
        include_emojis=include_emojis,
        audience=audience,
        extra_notes=extra_notes
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=None,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, [], response_text

    try:
        data = _clean_and_parse_json(response_text)
        captions = _normalize_captions(data.get("captions", []), platform, tone)
        if not captions:
            return False, [], "The AI response did not contain valid captions. Please retry."
        return True, captions, None
    except Exception as e:
        return False, [], f"Failed to parse AI response into structured captions: {str(e)}"

def generate_image_captions(
    image: Image.Image,
    tone: str,
    platform: str,
    length: str,
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    include_emojis: bool = True,
    user_context: Optional[str] = None,
    audience: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Generates 5 captions from an uploaded image using Gemini vision."""
    if image is None:
        return False, [], "No valid image provided for caption generation."

    prompt = build_image_to_caption_prompt(
        tone=tone,
        platform=platform,
        length=length,
        include_hashtags=include_hashtags,
        hashtag_count=hashtag_count,
        include_emojis=include_emojis,
        user_context=user_context,
        audience=audience
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=image,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, [], response_text

    try:
        data = _clean_and_parse_json(response_text)
        captions = _normalize_captions(data.get("captions", []), platform, tone)
        if not captions:
            return False, [], "The AI response did not contain valid captions. Please retry."
        return True, captions, None
    except Exception as e:
        return False, [], f"Failed to parse multimodal image response: {str(e)}"

def generate_emoji_captions(
    emojis: str,
    tone: str,
    platform: str,
    length: str,
    emoji_only_mode: bool = False,
    user_context: Optional[str] = None,
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Generates 5 captions from a sequence of emojis."""
    if not emojis or not emojis.strip():
        return False, [], "Please select or enter at least one emoji."

    prompt = build_emoji_to_caption_prompt(
        emojis=emojis,
        tone=tone,
        platform=platform,
        length=length,
        emoji_only_mode=emoji_only_mode,
        user_context=user_context,
        include_hashtags=include_hashtags,
        hashtag_count=hashtag_count
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=None,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, [], response_text

    try:
        data = _clean_and_parse_json(response_text)
        captions = _normalize_captions(data.get("captions", []), platform, tone)
        if not captions:
            return False, [], "The AI response did not contain valid captions. Please retry."
        return True, captions, None
    except Exception as e:
        return False, [], f"Failed to parse emoji caption response: {str(e)}"
