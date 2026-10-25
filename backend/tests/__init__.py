"""
CaptionCraft AI — Backend Test Suite Package
"""
import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_DIR = _PROJECT_ROOT / "Frontend"

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_FRONTEND_DIR), str(_TESTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
