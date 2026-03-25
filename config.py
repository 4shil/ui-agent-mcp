# config.py — UI Agent MCP Configuration

import os
from pathlib import Path

# ──── Paths ────
BASE_DIR = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
MODELS_DIR = BASE_DIR / "models"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# ──── Vision Model ────
# Options: "florence-2-base", "florence-2-large", "moondream2"
VISION_MODEL = os.getenv("VISION_MODEL", "florence-2-base")
VISION_MODEL_ID = {
    "florence-2-base": "microsoft/Florence-2-base",
    "florence-2-large": "microsoft/Florence-2-large",
    "moondream2": "vikhyatk/moondream2",
}[VISION_MODEL]

DEVICE = os.getenv("DEVICE", "cpu")  # "cpu" or "cuda"

# ──── OCR (RapidOCR) ────
OCR_USE_ONNX = True

# ──── Safety ────
ACTION_COOLDOWN_MS = 300       # ms between actions
MAX_ACTIONS_PER_MINUTE = 60    # rate limit
EMERGENCY_STOP_KEY = "ctrl+alt+q"

# ──── Screen ────
SCREENSHOT_FORMAT = "png"
SCREENSHOT_QUALITY = 95
