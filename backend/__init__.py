"""
CaptionCraft AI — Backend Package
Contains database operations, authentication, AI integration, Cloudinary, and utilities.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_DIR = _PROJECT_ROOT / "Frontend"

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure project root .env is loaded
_root_env = _PROJECT_ROOT / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env)
else:
    load_dotenv(find_dotenv(usecwd=True))
