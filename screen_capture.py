# screen_capture.py — Screen capture via mss

import base64
import time
from PIL import Image
import mss
import mss.tools
from config import SCREENSHOTS_DIR, DEFAULT_MONITOR, SCREENSHOT_FORMAT


class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()

    def get_monitors(self) -> list[dict]:
        monitors = []
        for i, mon in enumerate(self.sct.monitors):
            monitors.append({"id": i, "left": mon["left"], "top": mon["top"],
                             "width": mon["width"], "height": mon["height"]})
        return monitors

    def get_screen_info(self) -> dict:
        mon = self.sct.monitors[DEFAULT_MONITOR]
        return {"width": mon["width"], "height": mon["height"],
                "monitors": len(self.sct.monitors) - 1}

    def screenshot(self, monitor_id: int | None = None) -> dict:
        mon_id = monitor_id or DEFAULT_MONITOR
        mon = self.sct.monitors[mon_id]
        region = {"left": mon["left"], "top": mon["top"],
                  "width": mon["width"], "height": mon["height"]}
        timestamp = int(time.time() * 1000)
        filepath = SCREENSHOTS_DIR / f"screenshot_{timestamp}.{SCREENSHOT_FORMAT}"
        img = self.sct.grab(region)
        mss.tools.to_png(img.rgb, img.size, output=str(filepath))
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {"path": str(filepath), "base64": b64,
                "width": region["width"], "height": region["height"],
                "timestamp": timestamp}

    def screenshot_region(self, x: int, y: int, width: int, height: int) -> dict:
        region = {"left": x, "top": y, "width": width, "height": height}
        timestamp = int(time.time() * 1000)
        filepath = SCREENSHOTS_DIR / f"region_{timestamp}.{SCREENSHOT_FORMAT}"
        img = self.sct.grab(region)
        mss.tools.to_png(img.rgb, img.size, output=str(filepath))
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {"path": str(filepath), "base64": b64,
                "x": x, "y": y, "width": width, "height": height}


capture = ScreenCapture()
