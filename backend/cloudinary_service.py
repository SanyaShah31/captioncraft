"""
Cloudinary Image Storage Service for CaptionCraft AI.
Handles secure upload, credentials loading from environment variables,
format and size validation, deduplicated caching, and metadata extraction.
"""

import os
import sys
from pathlib import Path
import io
import hashlib
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv, find_dotenv
import cloudinary
import cloudinary.uploader
from PIL import Image

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

# Allowed formats and maximum size matching CaptionCraft limits
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

# In-memory deduplication cache for session: hash -> metadata dict
_UPLOAD_CACHE: Dict[str, Dict[str, Any]] = {}
_IS_INITIALIZED = False


def get_cloudinary_config() -> Dict[str, str]:
    """Reads Cloudinary credentials from environment variables."""
    return {
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME", "").strip(),
        "api_key": os.getenv("CLOUDINARY_API_KEY", "").strip(),
        "api_secret": os.getenv("CLOUDINARY_API_SECRET", "").strip(),
    }


def is_cloudinary_configured() -> bool:
    """Checks whether all required Cloudinary credentials are set and non-empty."""
    cfg = get_cloudinary_config()
    has_name = bool(cfg["cloud_name"] and cfg["cloud_name"] != "your_cloudinary_cloud_name")
    has_key = bool(cfg["api_key"] and cfg["api_key"] != "your_cloudinary_api_key")
    has_secret = bool(cfg["api_secret"] and cfg["api_secret"] != "your_cloudinary_api_secret")
    return has_name and has_key and has_secret


def configure_cloudinary() -> bool:
    """Initializes Cloudinary client configuration if credentials exist."""
    global _IS_INITIALIZED
    if not is_cloudinary_configured():
        return False

    cfg = get_cloudinary_config()
    try:
        cloudinary.config(
            cloud_name=cfg["cloud_name"],
            api_key=cfg["api_key"],
            api_secret=cfg["api_secret"],
            secure=True
        )
        _IS_INITIALIZED = True
        return True
    except Exception:
        return False


def compute_image_hash(image_bytes: bytes) -> str:
    """Computes SHA-256 fingerprint of image data for upload deduplication."""
    return hashlib.sha256(image_bytes).hexdigest()


def clear_cache() -> None:
    """Clears the in-memory upload deduplication cache."""
    global _UPLOAD_CACHE
    _UPLOAD_CACHE.clear()


def validate_image_bytes(image_bytes: bytes, filename: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates image bytes size and format.
    Returns: (is_valid, error_msg, detected_format)
    """
    if not image_bytes:
        return False, "Image file data is empty.", None

    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(image_bytes) / (1024 * 1024)
        return False, f"Image size ({size_mb:.2f} MB) exceeds maximum allowed limit of 15 MB.", None

    # Verify PIL can open and identify format
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            fmt = (img.format or "").lower()
            if fmt == "jpeg":
                fmt = "jpg"
            if fmt not in ALLOWED_EXTENSIONS:
                if filename and "." in filename:
                    ext = filename.rsplit(".", 1)[-1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        fmt = ext
                if fmt not in ALLOWED_EXTENSIONS:
                    return False, f"Unsupported image format '{fmt}'. Allowed formats: JPG, JPEG, PNG, WebP.", None
            return True, None, fmt
    except Exception:
        return False, "Failed to parse image data.", None


def upload_image(
    image_data: Any,
    filename: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Uploads an image to Cloudinary securely.
    Extracts bytes, validates size/format, checks deduplication cache,
    and uploads to Cloudinary with secure URLs.
    
    Returns: (success, error_message, result_metadata)
    Guarantees that credentials/secrets are never printed or returned.
    """
    if not is_cloudinary_configured():
        return False, "Cloudinary is not configured. Missing CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, or CLOUDINARY_API_SECRET.", None

    image_bytes: Optional[bytes] = None
    if isinstance(image_data, bytes):
        image_bytes = image_data
    elif hasattr(image_data, "getvalue"):
        image_bytes = image_data.getvalue()
    elif isinstance(image_data, Image.Image):
        buf = io.BytesIO()
        save_fmt = image_data.format or "PNG"
        image_data.save(buf, format=save_fmt)
        image_bytes = buf.getvalue()
    else:
        return False, "Unsupported image data type.", None

    is_valid, err, detected_fmt = validate_image_bytes(image_bytes, filename)
    if not is_valid:
        return False, err, None

    # Check deduplication cache to avoid redundant uploads of the same image
    img_hash = compute_image_hash(image_bytes)
    if img_hash in _UPLOAD_CACHE:
        return True, None, dict(_UPLOAD_CACHE[img_hash])

    if not configure_cloudinary():
        return False, "Failed to initialize Cloudinary with configured credentials.", None

    folder_name = "captioncraft"
    if user_id and str(user_id).strip():
        folder_name = f"captioncraft/users/{str(user_id).strip()}"

    upload_options: Dict[str, Any] = {
        "folder": folder_name,
        "resource_type": "image",
        "use_filename": True,
        "unique_filename": True,
        "overwrite": False
    }

    try:
        upload_result = cloudinary.uploader.upload(
            io.BytesIO(image_bytes),
            **upload_options
        )

        public_id = upload_result.get("public_id")
        secure_url = upload_result.get("secure_url")

        if not public_id or not secure_url:
            return False, "Cloudinary upload response missing required identifiers.", None

        meta = {
            "public_id": public_id,
            "secure_url": secure_url,
            "url": secure_url,
            "format": upload_result.get("format", detected_fmt),
            "width": upload_result.get("width"),
            "height": upload_result.get("height"),
            "bytes": upload_result.get("bytes", len(image_bytes)),
            "created_at": upload_result.get("created_at")
        }

        _UPLOAD_CACHE[img_hash] = meta
        return True, None, meta

    except Exception as e:
        err_type = type(e).__name__
        err_str = str(e)
        cfg = get_cloudinary_config()
        if cfg["api_secret"] and cfg["api_secret"] in err_str:
            err_str = err_str.replace(cfg["api_secret"], "[REDACTED]")
        if cfg["api_key"] and cfg["api_key"] in err_str:
            err_str = err_str.replace(cfg["api_key"], "[REDACTED]")

        return False, f"Cloudinary upload failed ({err_type}): {err_str}", None
