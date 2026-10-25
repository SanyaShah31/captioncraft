"""
CaptionCraft AI — Frontend Package
Contains Streamlit UI presentation components, auth forms, and views.
"""
import sys
from pathlib import Path

_FRONTEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _FRONTEND_DIR.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
