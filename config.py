# config.py — UI Agent MCP Configuration

import os
from pathlib import Path

# ──── Paths ────
BASE_DIR = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ──── Vision Model (Florence-2) ────
VISION_MODEL = os.getenv("VISION_MODEL", "florence-2-base")
VISION_MODEL_ID = {
    "florence-2-base": "microsoft/Florence-2-base",
    "florence-2-large": "microsoft/Florence-2-large",
}[VISION_MODEL]

# ──── OCR Model (GLM-OCR from Z.AI) ────
OCR_MODEL_ID = "zai-org/GLM-OCR"

# ──── Device ────
DEVICE = os.getenv("DEVICE", "cpu")
DEVICE_MAP = "auto" if DEVICE == "cuda" else None
TORCH_DTYPE = "auto"

# ──── Safety ────
ACTION_COOLDOWN_MS = 300
MAX_ACTIONS_PER_MINUTE = 60
EMERGENCY_STOP_KEY = "ctrl+alt+q"

# ──── Screen ────
SCREENSHOT_FORMAT = "png"
DEFAULT_MONITOR = 0

# ──── MCP Server ────
SERVER_NAME = "ui-agent"
SERVER_VERSION = "1.0.0"
