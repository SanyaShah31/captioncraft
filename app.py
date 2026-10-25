"""
CaptionCraft AI — Root Application Launcher
Delegates execution to the Frontend Streamlit interface (Frontend/app.py).
Preserves backward compatibility with `streamlit run app.py` while supporting `streamlit run Frontend/app.py`.
"""
import sys
import runpy
from pathlib import Path

# Setup paths so root, backend, and Frontend are available on sys.path
_ROOT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _ROOT_DIR / "backend"
_FRONTEND_DIR = _ROOT_DIR / "Frontend"

for _p in [str(_ROOT_DIR), str(_BACKEND_DIR), str(_FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Execute the primary Frontend Streamlit application
_frontend_app = _FRONTEND_DIR / "app.py"
runpy.run_path(str(_frontend_app), run_name="__main__")
