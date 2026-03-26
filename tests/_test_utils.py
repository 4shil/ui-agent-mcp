import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_test_image_path() -> str:
    from config import SCREENSHOTS_DIR
    from screen_capture import capture

    try:
        shot = capture.screenshot()
        path = shot.get("path")
        if path and Path(path).exists():
            return str(path)
    except Exception:
        pass

    # Fallback for headless environments: generate a deterministic local image.
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS_DIR / f"test_fallback_{int(time.time() * 1000)}.png"
    image = Image.new("RGB", (1280, 720), color=(246, 246, 246))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 1240, 140), fill=(220, 230, 255), outline=(90, 120, 200), width=2)
    draw.text((60, 80), "UI Agent MCP test screenshot", fill=(20, 20, 20))
    draw.rectangle((80, 220, 360, 320), outline=(60, 60, 60), width=2)
    draw.text((95, 260), "Submit", fill=(30, 30, 30))
    image.save(path)
    return str(path)


def print_case(name: str, payload: dict):
    status = payload.get("status", "ok") if isinstance(payload, dict) else "ok"
    print(f"[test] {name}: {status}")
