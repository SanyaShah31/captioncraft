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
    build_emoji_to_caption_prompt,
    build_viral_analyzer_prompt,
    build_caption_improvement_prompt,
    build_multi_platform_prompt,
    build_carousel_storyteller_prompt,
    build_carousel_single_slide_prompt
)
from utils import generate_caption_id

DEFAULT_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash"
]

def clean_api_key(raw_key: Optional[str]) -> Optional[str]:
    """
    Cleans, strips, and normalizes a Gemini API key.
    - Strips whitespace, carriage returns, and newlines.
    - Strips enclosing single or double quotes.
    - Strips trailing semicolons, commas.
    - Automatically heals common paste typos (e.g., accidental duplicate leading 'A' in 'AAQ.' -> 'AQ.').
    """
    if not raw_key:
        return None
    cleaned = raw_key.strip().strip("\"'").strip().rstrip(";,").strip()
    if not cleaned:
        return None
    # Google AI Studio authorization keys start with 'AQ.'
    # A common copy-paste error duplicates the initial 'A', resulting in 'AAQ.'
    if cleaned.startswith("AAQ.") and len(cleaned) > 10:
        cleaned = cleaned[1:]
    return cleaned

def get_api_key(override_key: Optional[str] = None) -> Optional[str]:
    """
    Retrieves the Google Gemini API key following strict precedence:
    1. UI override parameter (e.g. sidebar input)
    2. Environment variable GEMINI_API_KEY (from .env or os.environ)
    3. Environment variable GOOGLE_API_KEY (secondary fallback)
    4. Streamlit secrets (if available)
    """
    if override_key and override_key.strip():
        cleaned = clean_api_key(override_key)
        if cleaned:
            return cleaned

    # Check os environment / .env for GEMINI_API_KEY
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        cleaned = clean_api_key(env_key)
        if cleaned:
            return cleaned

    # Check GOOGLE_API_KEY as secondary fallback
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if google_key:
        cleaned = clean_api_key(google_key)
        if cleaned:
            return cleaned

    # Check Streamlit secrets if running inside streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for sec_var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
                if sec_var in st.secrets:
                    sec_key = st.secrets[sec_var]
                    if sec_key and str(sec_key).strip():
                        cleaned = clean_api_key(str(sec_key))
                        if cleaned:
                            return cleaned
    except Exception:
        pass

    return None

def get_api_key_source(override_key: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Returns a masked version of the active key and an informative description of its source.
    Never exposes the full secret.
    """
    if override_key and override_key.strip():
        cleaned = clean_api_key(override_key)
        if cleaned and len(cleaned) >= 8:
            masked = f"{cleaned[:4]}...{cleaned[-4:]}"
            return masked, "Manual Sidebar Override"

    env_gemini = os.getenv("GEMINI_API_KEY", "").strip()
    if env_gemini:
        cleaned = clean_api_key(env_gemini)
        if cleaned and len(cleaned) >= 8:
            masked = f"{cleaned[:4]}...{cleaned[-4:]}"
            return masked, "Environment (.env GEMINI_API_KEY)"

    env_google = os.getenv("GOOGLE_API_KEY", "").strip()
    if env_google:
        cleaned = clean_api_key(env_google)
        if cleaned and len(cleaned) >= 8:
            masked = f"{cleaned[:4]}...{cleaned[-4:]}"
            return masked, "Environment (.env GOOGLE_API_KEY)"

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_val = clean_api_key(str(st.secrets["GEMINI_API_KEY"]))
            if sec_val and len(sec_val) >= 8:
                return f"{sec_val[:4]}...{sec_val[-4:]}", "Streamlit Secrets"
    except Exception:
        pass

    return None, "Not Configured"

def is_api_key_configured(override_key: Optional[str] = None) -> bool:
    """Checks whether a valid API key is present."""
    key = get_api_key(override_key)
    return bool(key and len(key) >= 15 and not key.startswith("your_gemini_api_key"))

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

def _clean_and_parse_json(raw_text: str, expected_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts and parses JSON object from Gemini response.
    Handles markdown code blocks, partial wrappers, and trailing commas.
    If expected_key is provided, verifies that key exists in parsed dict.
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

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Attempt to strip trailing commas before closing braces/brackets
        sanitized = re.sub(r",\s*([\}\]])", r"\1", text)
        parsed = json.loads(sanitized)

    if not isinstance(parsed, dict):
        raise ValueError("Response JSON does not evaluate to a structured dictionary object.")
    if expected_key and expected_key not in parsed:
        raise ValueError(f"Response JSON does not contain the expected '{expected_key}' array or object.")

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
    image: Optional[Any] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    system_instruction: Optional[str] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Executes multimodal Gemini request using official google-genai SDK,
    with fallback to google-generativeai if needed.
    Supports single image, list of images (e.g. carousels), or text-only prompts.
    Returns: (success, response_text_or_error, used_model_name)
    """
    key = get_api_key(api_key)
    if not key or not is_api_key_configured(key):
        return False, get_api_key_instruction(), None

    effective_sys_inst = system_instruction or SYSTEM_INSTRUCTION

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
                if isinstance(image, (list, tuple)):
                    contents = list(image) + [prompt]
                elif image is not None:
                    contents = [image, prompt]
                else:
                    contents = [prompt]

                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.75,
                    system_instruction=effective_sys_inst
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
                    system_instruction=effective_sys_inst,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.75
                    }
                )
                if isinstance(image, (list, tuple)):
                    inputs = list(image) + [prompt]
                elif image is not None:
                    inputs = [image, prompt]
                else:
                    inputs = prompt

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
    err_upper = last_error.upper()
    if (
        "403" in last_error
        or "401" in last_error
        or "API_KEY_INVALID" in err_upper
        or "API KEY NOT VALID" in err_upper
        or "PERMISSION_DENIED" in err_upper
        or "ACCESS_TOKEN_TYPE_UNSUPPORTED" in err_upper
    ):
        friendly_msg = (
            "**Gemini API Authentication Failed**\n\n"
            "Your provided API key appears to be invalid, expired, or lacks permissions.\n"
            "Please check that you copied a complete, active Gemini key from [Google AI Studio](https://aistudio.google.com/app/apikey) "
            "and pasted it in the sidebar or configured `GEMINI_API_KEY` in `.env`."
        )
    elif "429" in last_error or "RESOURCE_EXHAUSTED" in err_upper:
        friendly_msg = (
            "**Gemini API Quota Exceeded**\n\n"
            "The free tier quota for this API key has been reached. Please wait a moment before retrying, "
            "or verify your account limits in Google AI Studio."
        )
    elif "503" in last_error or "UNAVAILABLE" in err_upper:
        friendly_msg = (
            "**Gemini Service Temporarily Unavailable**\n\n"
            "The Gemini models are currently experiencing high demand from Google. Please wait a few moments and retry."
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


# =====================================================================
# Feature 3: Viral Caption Analyzer & Improver Services
# =====================================================================

def analyze_viral_caption(
    caption: str,
    platform: str = "Instagram",
    tone: str = "Aesthetic",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Evaluates a caption across 5 dimensions:
    - Hook Strength (max 25)
    - Readability (max 20)
    - Emotional Appeal (max 20)
    - CTA Effectiveness (max 15)
    - Platform Relevance (max 20)
    Returns: (success, analysis_data_dict, error_message)
    """
    if not caption or not caption.strip():
        return False, {}, "Please provide a caption to analyze."

    prompt = build_viral_analyzer_prompt(caption=caption.strip(), platform=platform, tone=tone)

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=None,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, {}, response_text

    try:
        data = _clean_and_parse_json(response_text)

        # Validate and normalize category scores
        scores = data.get("scores", {})
        default_categories = {
            "hook_strength": {"score": 18, "max": 25, "reason": "Opening line introduces the topic clearly."},
            "readability": {"score": 16, "max": 20, "reason": "Good pacing and sentence structure."},
            "emotional_appeal": {"score": 14, "max": 20, "reason": "Contains evocative keywords and relatable sentiment."},
            "cta_effectiveness": {"score": 10, "max": 15, "reason": "Engages the reader toward interaction."},
            "platform_relevance": {"score": 15, "max": 20, "reason": "Formats appropriately for this platform."}
        }

        normalized_scores = {}
        total_calculated = 0
        for cat_key, default_val in default_categories.items():
            cat_data = scores.get(cat_key, {})
            try:
                sc = int(cat_data.get("score", default_val["score"]))
            except (ValueError, TypeError):
                sc = default_val["score"]
            max_sc = default_val["max"]
            sc = max(0, min(sc, max_sc))
            reason = str(cat_data.get("reason", default_val["reason"])).strip()
            normalized_scores[cat_key] = {
                "score": sc,
                "max": max_sc,
                "reason": reason
            }
            total_calculated += sc

        overall_score = data.get("overall_score")
        try:
            overall_score = int(overall_score)
        except (ValueError, TypeError):
            overall_score = total_calculated
        overall_score = max(0, min(100, overall_score))

        result = {
            "overall_score": overall_score,
            "scores": normalized_scores,
            "verdict": data.get("verdict", "Solid caption with good engagement potential."),
            "strengths": data.get("strengths", ["Clear messaging", "Engaging tone"]),
            "weaknesses": data.get("weaknesses", ["Call-to-action could be sharpened"]),
            "suggestions": data.get("suggestions", ["Add an open-ended question to trigger comments"]),
            "platform": platform,
            "tone": tone
        }
        return True, result, None
    except Exception as e:
        return False, {}, f"Failed to parse viral analysis data: {str(e)}"


def improve_caption(
    caption: str,
    action: str,
    platform: str = "Instagram",
    tone: str = "Creative",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Polishes an existing caption based on action directive:
    - 'engaging': Make it more magnetic and vibrant
    - 'stronger_hook': Transform line 1 into a high-CTR scroll-stopper
    - 'shorter': Make it concise and minimalist
    - 'better_cta': Improve engagement call-to-action
    - 'platform_optimize': Tailor natively for the platform
    """
    if not caption or not caption.strip():
        return False, {}, "Please provide a caption to improve."

    prompt = build_caption_improvement_prompt(
        caption=caption.strip(),
        action=action,
        platform=platform,
        tone=tone
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=None,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, {}, response_text

    try:
        data = _clean_and_parse_json(response_text)
        improved_caption = str(data.get("improved_caption", "")).strip()
        if not improved_caption:
            return False, {}, "AI did not return an improved caption text."

        return True, {
            "original_caption": caption,
            "improved_caption": improved_caption,
            "hook": str(data.get("hook", "")).strip(),
            "hashtags": data.get("hashtags", []),
            "emojis": data.get("emojis", []),
            "cta": str(data.get("cta", "")).strip(),
            "improvement_summary": str(data.get("improvement_summary", "Polished and optimized for higher engagement.")).strip(),
            "changes_made": data.get("changes_made", ["Optimized hook and flow"]),
            "platform": platform,
            "tone": tone,
            "action": action
        }, None
    except Exception as e:
        return False, {}, f"Failed to parse improved caption: {str(e)}"


# =====================================================================
# Feature 4: One-Click Multi-Platform Generator Services
# =====================================================================

def generate_multi_platform_captions(
    topic: str,
    platforms: List[str],
    tone: str,
    length: str = "Medium",
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    user_context: Optional[str] = None,
    audience: Optional[str] = None,
    image: Optional[Image.Image] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Generates distinct, platform-tailored captions for multiple social platforms in one pass.
    Optionally incorporates visual context if an image is provided.
    """
    if not topic or not topic.strip():
        return False, {}, "Please provide a topic or concept for multi-platform generation."
    if not platforms:
        return False, {}, "Please select at least one social media platform."

    prompt = build_multi_platform_prompt(
        topic=topic.strip(),
        platforms=platforms,
        tone=tone,
        length=length,
        include_hashtags=include_hashtags,
        hashtag_count=hashtag_count,
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
        return False, {}, response_text

    try:
        data = _clean_and_parse_json(response_text)
        raw_platforms = data.get("platforms", {})

        normalized_platforms = {}
        for p in platforms:
            p_data = raw_platforms.get(p)
            if not p_data:
                # Search case-insensitively or partial match
                for rk, rv in raw_platforms.items():
                    if p.lower() in rk.lower() or rk.lower() in p.lower():
                        p_data = rv
                        break

            if not p_data or not isinstance(p_data, dict):
                p_data = {
                    "caption": f"Explore our latest thoughts on {topic}.",
                    "hook": f"Here is a key perspective on {topic}:",
                    "hashtags": ["growth", "creative"],
                    "emojis": ["✨"],
                    "cta": "Share your thoughts below!"
                }

            cap_text = str(p_data.get("caption", "")).strip()
            hook_text = str(p_data.get("hook", "")).strip()
            hashtags = p_data.get("hashtags", [])
            if isinstance(hashtags, str):
                hashtags = [h.strip() for h in hashtags.split() if h.strip()]
            emojis = p_data.get("emojis", [])
            cta_text = str(p_data.get("cta", "")).strip()
            char_count = len(cap_text)
            tip = str(p_data.get("platform_tip", "")).strip()

            cid = generate_caption_id(cap_text, p)

            normalized_platforms[p] = {
                "id": cid,
                "platform": p,
                "caption": cap_text,
                "hook": hook_text,
                "hashtags": hashtags,
                "emojis": emojis,
                "cta": cta_text,
                "char_count": char_count,
                "platform_tip": tip,
                "tone": tone
            }

        return True, normalized_platforms, None
    except Exception as e:
        return False, {}, f"Failed to parse multi-platform captions: {str(e)}"


# =====================================================================
# Feature 5: AI Multi-Image Carousel & Photo Dump Generator Services
# =====================================================================

def generate_carousel_story(
    images: List[Image.Image],
    tone: str,
    platform: str = "Instagram",
    topic_context: Optional[str] = None,
    audience: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Generates a coherent visual storytelling carousel across an ordered list of images.
    Returns: (success, carousel_data_dict, error_message)
    """
    if not images or len(images) == 0:
        return False, {}, "Please provide at least one image for carousel generation."

    num_slides = len(images)
    prompt = build_carousel_storyteller_prompt(
        num_slides=num_slides,
        tone=tone,
        platform=platform,
        topic_context=topic_context,
        audience=audience
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=images,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, {}, response_text

    try:
        data = _clean_and_parse_json(response_text)
        theme_title = str(data.get("theme_title", "Visual Carousel Story")).strip()
        master_caption = str(data.get("master_caption", "")).strip()
        master_hashtags = data.get("master_hashtags", ["carousel", "visualstory", "photojourney"])
        if isinstance(master_hashtags, str):
            master_hashtags = [h.strip() for h in master_hashtags.split() if h.strip()]
        master_cta = str(data.get("master_cta", "Swipe through and let me know your thoughts! 👇")).strip()

        raw_slides = data.get("slides", [])
        normalized_slides = []

        for idx in range(num_slides):
            slide_data = raw_slides[idx] if idx < len(raw_slides) else {}
            slide_num = idx + 1
            if idx == 0:
                s_type = "Cover Hook"
            elif idx == num_slides - 1:
                s_type = "Closing & CTA"
            else:
                s_type = "Story Progression"

            title = str(slide_data.get("title", f"Slide #{slide_num}")).strip()
            caption = str(slide_data.get("caption", "")).strip()
            overlay = str(slide_data.get("overlay_text", "")).strip()
            connection = str(slide_data.get("visual_connection", "")).strip()

            normalized_slides.append({
                "slide_number": slide_num,
                "slide_type": s_type,
                "title": title,
                "caption": caption,
                "overlay_text": overlay,
                "visual_connection": connection
            })

        carousel_result = {
            "id": generate_caption_id(master_caption or theme_title, str(num_slides)),
            "theme_title": theme_title,
            "master_caption": master_caption,
            "master_hashtags": master_hashtags,
            "master_cta": master_cta,
            "total_slides": num_slides,
            "slides": normalized_slides,
            "tone": tone,
            "platform": platform
        }
        return True, carousel_result, None
    except Exception as e:
        return False, {}, f"Failed to parse carousel story response: {str(e)}"


def regenerate_carousel_slide(
    slide_index: int,
    total_slides: int,
    current_storyline: str,
    tone: str,
    platform: str = "Instagram",
    image: Optional[Image.Image] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """Regenerates a single slide in a carousel sequence."""
    prompt = build_carousel_single_slide_prompt(
        slide_index=slide_index,
        total_slides=total_slides,
        current_storyline=current_storyline,
        tone=tone,
        platform=platform
    )

    success, response_text, _ = _call_gemini(
        prompt=prompt,
        image=image,
        api_key=api_key,
        model_name=model_name
    )

    if not success:
        return False, {}, response_text

    try:
        slide_data = _clean_and_parse_json(response_text)
        return True, {
            "slide_number": slide_index,
            "slide_type": slide_data.get("slide_type", f"Slide #{slide_index}"),
            "title": str(slide_data.get("title", f"Slide #{slide_index}")).strip(),
            "caption": str(slide_data.get("caption", "")).strip(),
            "overlay_text": str(slide_data.get("overlay_text", "")).strip(),
            "visual_connection": str(slide_data.get("visual_connection", "")).strip()
        }, None
    except Exception as e:
        return False, {}, f"Failed to parse regenerated slide: {str(e)}"
