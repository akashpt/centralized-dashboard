import sys
from pathlib import Path
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
# =====================================================
# CORE PATH HELPERS
# =====================================================

def app_path() -> Path:
    """
    Read-only application path
    - Normal run   → project root
    - PyInstaller  → _MEIPASS
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def run_path() -> Path:
    """
    Read/write runtime path
    - Normal run   → project root
    - PyInstaller  → exe folder
    """
    if IS_WINDOWS:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path.cwd()

    elif IS_LINUX:
        path = Path.home() / "Documents"
        path.mkdir(parents=True, exist_ok=True)
        return path

    return Path.cwd()


# =====================================================
# 🔥 BASE DIRECTORIES
# =====================================================

APP_DIR = app_path()   # read-only
RUN_DIR = run_path()   # writable

# Optional: create main runtime folder
RUN_DIR = RUN_DIR / "ThreadI_dashboard"
RUN_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# 🔥 TEMPLATES (READ ONLY)
# =====================================================

TEMPLATES_DIR = APP_DIR / "templates"
INDEX_PAGE = TEMPLATES_DIR / "index.html"
TRAINING_PAGE = TEMPLATES_DIR / "machine-details.html"
REPORT_PAGE = TEMPLATES_DIR / "report.html"
SLIDER_MACHINE = TEMPLATES_DIR / "slider-machine.html"


# =====================================================
# 🔥 DATA / STORAGE (WRITE)
# =====================================================

DB_PATH = RUN_DIR / "dashboard.db"

