import sys
from pathlib import Path

# =====================================================
# 🔥 PATH HELPERS (PYINSTALLER SAFE)
# =====================================================

def app_path() -> Path:
    """Read-only path (bundled files)"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def run_path() -> Path:
    """Writable path"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


# =====================================================
# 🔥 BASE DIRECTORIES
# =====================================================

APP_DIR = app_path()   # read-only
RUN_DIR = run_path()   # writable

# Optional: create main runtime folder
RUN_DIR = RUN_DIR / "ThreadI_data"
RUN_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# 🔥 CLASSES (READ ONLY)
# =====================================================

CLASSES_DIR = APP_DIR / "classes"



# =====================================================
# 🔥 TEMPLATES (READ ONLY)
# =====================================================

TEMPLATES_DIR = APP_DIR / "templates"
INVOICE_PDF = APP_DIR / "templates" / "belt-invoice.pdf"
INDEX_PAGE = TEMPLATES_DIR / "index.html"
TRAINING_PAGE = TEMPLATES_DIR / "training.html"
CONTROLLER_PAGE = TEMPLATES_DIR / "controller.html"
REPORT_PAGE = TEMPLATES_DIR / "report.html"


# =====================================================
# 🔥 DATA / STORAGE (WRITE)
# =====================================================

DATA_DIR = RUN_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TRAINING_IMAGES_DIR = DATA_DIR / "training_images"
TRAINING_IMAGES_DIR.mkdir(exist_ok=True)

PREDICTION_IMAGES_DIR = DATA_DIR / "prediction_images"
PREDICTION_IMAGES_DIR.mkdir(exist_ok=True)


# =====================================================
# 🔥 MODELS (WRITE)
# =====================================================

MODELS_DIR = RUN_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = MODELS_DIR / "best.pt"


# =====================================================
# 🔥 SETTINGS FILES (WRITE)
# =====================================================

SETTINGS_FILE = RUN_DIR / "settings.json"
TRAINING_SETTINGS_FILE = RUN_DIR / "training_settings.json"
CONTROLLER_SETTINGS_FILE = RUN_DIR / "controller_setting.json"


# =====================================================
# 🔥 PLC SIGNAL FILES (WRITE)
# =====================================================

SIGNAL_FILE = RUN_DIR / "signal.txt"
COUNT_FILE = RUN_DIR / "count.txt"


# =====================================================
# 🔥 SDK / CONFIG (READ ONLY)
# =====================================================

CONFIG_DIR = APP_DIR / "camera_sdk"


# =====================================================
# 🔥 INITIAL FILE CREATION
# =====================================================

if not SIGNAL_FILE.exists():
    SIGNAL_FILE.write_text("0", encoding="utf-8")

if not COUNT_FILE.exists():
    COUNT_FILE.write_text("0", encoding="utf-8")