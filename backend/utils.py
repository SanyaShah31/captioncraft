"""
Utility functions for CaptionCraft AI.
Includes JSON local storage for history and favorites, image validation,
text metrics calculation, and data export helpers (JSON/CSV).
"""

import os
import sys
from pathlib import Path
import json
import uuid
import hashlib
from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import io
import pandas as pd
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

import database

# Paths for local JSON storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")

def ensure_data_dir() -> None:
    """Ensures data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
    if not os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def generate_caption_id(caption_text: str, timestamp: str = "") -> str:
    """Generates a stable unique hash identifier for a caption."""
    raw = f"{caption_text}_{timestamp}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]

# ---------------------------------------------------------------------
# History Storage (User-Specific and Feature-Separated)
# ---------------------------------------------------------------------

FEATURE_TEXT_TO_CAPTION = "text_to_caption"
FEATURE_IMAGE_TO_CAPTION = "image_to_caption"


def normalize_feature_type(
    feature_type: Optional[str] = None,
    mode: Optional[str] = None
) -> Optional[str]:
    """
    Normalizes feature identifiers to either 'text_to_caption' or 'image_to_caption'.
    Handles both canonical feature strings and UI mode labels.
    """
    val = (feature_type or mode or "").strip().lower()
    if not val:
        return None
    if "image" in val:
        return FEATURE_IMAGE_TO_CAPTION
    if "text" in val:
        return FEATURE_TEXT_TO_CAPTION
    return val


def save_generation_to_history(
    mode: str,
    input_summary: str,
    tone: str,
    platform: str,
    length: str,
    captions: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    feature_type: Optional[str] = None,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Saves a generation batch to the history store.
    Associates the record with the authenticated user_id and feature_type.
    Persists to MongoDB collection 'history' and mirrors to local JSON store.
    """
    ensure_data_dir()
    resolved_feature_type = normalize_feature_type(feature_type, mode) or FEATURE_TEXT_TO_CAPTION
    now_utc = datetime.now(timezone.utc)
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec_id = str(uuid.uuid4())[:8]

    history_entry = {
        "id": rec_id,
        "user_id": str(user_id).strip() if user_id else None,
        "feature_type": resolved_feature_type,
        "timestamp": timestamp_str,
        "created_at": now_utc,
        "mode": mode,
        "input_summary": input_summary,
        "tone": tone,
        "platform": platform,
        "length": length,
        "captions": captions,
        "metadata": metadata or {}
    }

    # 1. Persist to MongoDB if reachable
    try:
        database_inst = db if db is not None else database.get_db()
        history_col = database_inst["history"]
        mongo_doc = dict(history_entry)
        history_col.insert_one(mongo_doc)
    except Exception:
        pass

    # 2. Mirror into local JSON store to preserve data continuity
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []

    json_entry = dict(history_entry)
    if isinstance(json_entry.get("created_at"), datetime):
        json_entry["created_at"] = json_entry["created_at"].isoformat()

    history.insert(0, json_entry)
    history = history[:200]

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return history_entry


def get_history(
    user_id: Optional[str] = None,
    feature_type: Optional[str] = None,
    mode_filter: Optional[str] = None,
    search_term: Optional[str] = None,
    limit: int = 50,
    db: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves generation history strictly filtered by authenticated user_id.
    Enforces user ownership in the database query.
    Optionally filters by feature_type ('text_to_caption' or 'image_to_caption').
    Returns empty list if user_id is missing to prevent unauthorized data exposure.
    Legacy records without an owner user_id are never returned to any user.
    """
    if not user_id or not str(user_id).strip():
        return []

    clean_user_id = str(user_id).strip()
    resolved_feature = normalize_feature_type(feature_type, mode_filter)

    # 1. Attempt MongoDB query first
    try:
        database_inst = db if db is not None else database.get_db()
        history_col = database_inst["history"]

        and_conditions: List[Dict[str, Any]] = [{"user_id": clean_user_id}]

        if resolved_feature == FEATURE_TEXT_TO_CAPTION:
            and_conditions.append({
                "$or": [
                    {"feature_type": FEATURE_TEXT_TO_CAPTION},
                    {"mode": "Text-to-Caption"}
                ]
            })
        elif resolved_feature == FEATURE_IMAGE_TO_CAPTION:
            and_conditions.append({
                "$or": [
                    {"feature_type": FEATURE_IMAGE_TO_CAPTION},
                    {"mode": "Image-to-Caption"}
                ]
            })

        if search_term and search_term.strip():
            term = search_term.strip()
            regex = {"$regex": term, "$options": "i"}
            and_conditions.append({
                "$or": [
                    {"input_summary": regex},
                    {"captions.caption": regex},
                    {"captions.hook": regex},
                    {"platform": regex},
                    {"tone": regex}
                ]
            })

        mongo_query = {"$and": and_conditions} if len(and_conditions) > 1 else and_conditions[0]
        cursor = history_col.find(mongo_query).sort([("created_at", -1), ("_id", -1)]).limit(limit)

        records = []
        for doc in cursor:
            doc.pop("_id", None)
            records.append(doc)
        return records

    except Exception:
        # Fallback to local JSON storage if MongoDB connection is not available
        pass

    # 2. Fallback to local JSON file
    ensure_data_dir()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return []

    filtered = []
    for item in history:
        # Strict user ownership check: never expose records without owner or owned by another user
        if item.get("user_id") != clean_user_id:
            continue

        item_feature = normalize_feature_type(item.get("feature_type"), item.get("mode"))
        if resolved_feature and item_feature != resolved_feature:
            continue

        if search_term and search_term.strip():
            st_low = search_term.strip().lower()
            summary_match = st_low in item.get("input_summary", "").lower()
            caption_match = any(
                st_low in c.get("caption", "").lower() or st_low in c.get("hook", "").lower()
                for c in item.get("captions", [])
            )
            platform_match = st_low in item.get("platform", "").lower()
            tone_match = st_low in item.get("tone", "").lower()
            if not (summary_match or caption_match or platform_match or tone_match):
                continue

        filtered.append(item)

    return filtered[:limit]


def clear_history(
    user_id: Optional[str] = None,
    feature_type: Optional[str] = None,
    mode_filter: Optional[str] = None,
    db: Optional[Any] = None
) -> bool:
    """
    Clears generation history strictly for the authenticated user_id.
    If feature_type is specified, clears only records for that feature.
    Never deletes other users' records or other features' records.
    """
    if not user_id or not str(user_id).strip():
        return False

    clean_user_id = str(user_id).strip()
    resolved_feature = normalize_feature_type(feature_type, mode_filter)

    # 1. MongoDB delete
    try:
        database_inst = db if db is not None else database.get_db()
        history_col = database_inst["history"]

        del_conditions: List[Dict[str, Any]] = [{"user_id": clean_user_id}]
        if resolved_feature == FEATURE_TEXT_TO_CAPTION:
            del_conditions.append({
                "$or": [
                    {"feature_type": FEATURE_TEXT_TO_CAPTION},
                    {"mode": "Text-to-Caption"}
                ]
            })
        elif resolved_feature == FEATURE_IMAGE_TO_CAPTION:
            del_conditions.append({
                "$or": [
                    {"feature_type": FEATURE_IMAGE_TO_CAPTION},
                    {"mode": "Image-to-Caption"}
                ]
            })

        final_query = {"$and": del_conditions} if len(del_conditions) > 1 else del_conditions[0]
        history_col.delete_many(final_query)
    except Exception:
        pass

    # 2. Local JSON file delete
    ensure_data_dir()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        def should_keep(item):
            # Keep if belongs to another user or legacy record without user_id
            if item.get("user_id") != clean_user_id:
                return True
            # If user matches, check feature
            if resolved_feature:
                item_feat = normalize_feature_type(item.get("feature_type"), item.get("mode"))
                return item_feat != resolved_feature
            # If no feature filter, delete all records for this user
            return False

        updated_history = [item for item in history if should_keep(item)]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_history, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def delete_history_item(
    record_id: str,
    user_id: Optional[str] = None,
    db: Optional[Any] = None
) -> bool:
    """
    Deletes a single history record belonging to the authenticated user.
    """
    if not record_id or not user_id:
        return False
    clean_user_id = str(user_id).strip()

    try:
        database_inst = db if db is not None else database.get_db()
        history_col = database_inst["history"]
        history_col.delete_one({"id": record_id, "user_id": clean_user_id})
    except Exception:
        pass

    ensure_data_dir()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        updated = [
            item for item in history
            if not (item.get("id") == record_id and item.get("user_id") == clean_user_id)
        ]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------
# Favorites Storage
# ---------------------------------------------------------------------

def get_favorites() -> List[Dict[str, Any]]:
    """Returns the list of favorite captions."""
    ensure_data_dir()
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def is_favorite(caption_id: str) -> bool:
    """Checks if a caption is already favorited."""
    favorites = get_favorites()
    return any(f.get("id") == caption_id for f in favorites)

def add_favorite(caption_data: Dict[str, Any]) -> bool:
    """Adds a caption to favorites."""
    ensure_data_dir()
    favorites = get_favorites()
    cap_id = caption_data.get("id") or generate_caption_id(caption_data.get("caption", ""))
    caption_data["id"] = cap_id
    if not caption_data.get("favorited_at"):
        caption_data["favorited_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Avoid duplicate
    if not any(f.get("id") == cap_id for f in favorites):
        favorites.insert(0, caption_data)
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
        return True
    return False

def remove_favorite(caption_id: str) -> bool:
    """Removes a caption from favorites by its ID."""
    ensure_data_dir()
    favorites = get_favorites()
    original_len = len(favorites)
    favorites = [f for f in favorites if f.get("id") != caption_id]
    if len(favorites) < original_len:
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
        return True
    return False

# ---------------------------------------------------------------------
# Image Validation & Processing
# ---------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_MB = 15

def validate_image(uploaded_file) -> Tuple[bool, Optional[str], Optional[Image.Image], Dict[str, Any]]:
    """
    Validates uploaded image format and size.
    Returns: (is_valid, error_msg, PIL.Image, metadata_dict)
    """
    if uploaded_file is None:
        return False, "No image file uploaded.", None, {}

    # Check extension
    filename = getattr(uploaded_file, "name", "")
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Unsupported format '.{ext}'. Allowed formats: JPG, JPEG, PNG, WebP.",
            None,
            {}
        )

    # Check size
    file_bytes = uploaded_file.getvalue()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return (
            False,
            f"Image size ({size_mb:.2f} MB) exceeds maximum allowed limit of {MAX_FILE_SIZE_MB} MB.",
            None,
            {}
        )

    # Verify PIL image can open safely
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()  # Verify image integrity
        metadata = {
            "filename": filename,
            "format": image.format,
            "size_mb": round(size_mb, 2),
            "width": image.width,
            "height": image.height,
            "mode": image.mode
        }
        return True, None, image, metadata
    except Exception as e:
        return False, f"Failed to parse image: {str(e)}", None, {}

# ---------------------------------------------------------------------
# Metrics and Export Helpers
# ---------------------------------------------------------------------

def calculate_text_metrics(text: str) -> Dict[str, Any]:
    """Calculates character count, word count, and estimated reading time."""
    chars = len(text)
    words = len(text.split())
    # Avg reading speed ~ 200 words per minute
    reading_seconds = max(1, round((words / 200) * 60))
    return {
        "characters": chars,
        "words": words,
        "reading_seconds": reading_seconds
    }

def format_hashtags(hashtags: List[str]) -> str:
    """Formats hashtag list into a clean space-separated hashtag string."""
    formatted = []
    for tag in hashtags:
        tag = tag.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = f"#{tag}"
        formatted.append(tag)
    return " ".join(formatted)

def json_serializer(obj: Any) -> Any:
    """
    JSON serialization fallback helper for non-standard Python objects.
    - datetime / date: converted to ISO 8601 string (preserving timezone if present)
    - ObjectId (BSON) / UUID: converted to string
    - set / tuple: converted to list
    - bytes: decoded to UTF-8 or hex string
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (uuid.UUID, bytes)):
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except Exception:
                return obj.hex()
        return str(obj)
    if isinstance(obj, (set, tuple)):
        return list(obj)
    if hasattr(obj, "__str__"):
        type_name = type(obj).__name__
        if type_name in ("ObjectId", "Decimal128", "Binary"):
            return str(obj)
    return str(obj)

def export_history_to_json(records: List[Dict[str, Any]], indent: int = 2) -> str:
    """
    Safely serializes history records into a formatted JSON string.
    Converts datetime objects to ISO 8601 strings and handles BSON/UUID types.
    """
    return json.dumps(records, indent=indent, ensure_ascii=False, default=json_serializer)

def export_favorites_to_json(favorites: List[Dict[str, Any]], indent: int = 2) -> str:
    """
    Safely serializes favorite records into a formatted JSON string.
    Converts datetime objects to ISO 8601 strings and handles BSON/UUID types.
    """
    return json.dumps(favorites, indent=indent, ensure_ascii=False, default=json_serializer)

def export_history_to_df(
    user_id: Optional[str] = None,
    feature_type: Optional[str] = None,
    mode_filter: Optional[str] = None,
    db: Optional[Any] = None
) -> pd.DataFrame:
    """Flattens authenticated user's history into a pandas DataFrame for CSV export."""
    history = get_history(user_id=user_id, feature_type=feature_type, mode_filter=mode_filter, limit=500, db=db)
    rows = []
    for h in history:
        raw_ts = h.get("timestamp") or h.get("created_at")
        if isinstance(raw_ts, (datetime, date)):
            ts_str = raw_ts.isoformat()
        elif raw_ts is not None:
            ts_str = str(raw_ts)
        else:
            ts_str = ""

        captions_list = h.get("captions") or []
        for idx, cap in enumerate(captions_list, 1):
            if not isinstance(cap, dict):
                continue
            rows.append({
                "Batch ID": str(h.get("id") or ""),
                "Timestamp": ts_str,
                "Mode": str(h.get("mode") or ""),
                "Topic / Context": str(h.get("input_summary") or ""),
                "Platform": str(h.get("platform") or ""),
                "Tone": str(h.get("tone") or ""),
                "Length": str(h.get("length") or ""),
                "Option #": idx,
                "Vibe": cap.get("vibe_label", ""),
                "Hook": cap.get("hook", ""),
                "Caption": cap.get("caption", ""),
                "Hashtags": " ".join(cap.get("hashtags", []) or []),
                "CTA": cap.get("cta", "")
            })
    return pd.DataFrame(rows)

def export_favorites_to_df() -> pd.DataFrame:
    """Flattens favorites into a pandas DataFrame for CSV export."""
    favorites = get_favorites()
    rows = []
    for f in favorites:
        raw_fav_at = f.get("favorited_at") or f.get("created_at")
        if isinstance(raw_fav_at, (datetime, date)):
            fav_at_str = raw_fav_at.isoformat()
        elif raw_fav_at is not None:
            fav_at_str = str(raw_fav_at)
        else:
            fav_at_str = ""

        rows.append({
            "Favorite ID": str(f.get("id") or ""),
            "Favorited At": fav_at_str,
            "Platform": str(f.get("platform", "") or ""),
            "Tone": str(f.get("tone", "") or ""),
            "Vibe": str(f.get("vibe_label", "") or ""),
            "Hook": str(f.get("hook", "") or ""),
            "Caption": str(f.get("caption", "") or ""),
            "Hashtags": " ".join(f.get("hashtags", []) or []),
            "CTA": str(f.get("cta", "") or "")
        })
    return pd.DataFrame(rows)
