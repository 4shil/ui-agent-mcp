# element_finder.py — Smart element finding and interaction

import time
from vision import vision
from ui_controller import controller
from screen_capture import capture


class ElementFinder:
    def find_and_click(self, description: str, screenshot_path: str | None = None,
                       button: str = "left", retries: int = 2) -> dict:
        for attempt in range(retries):
            if screenshot_path is None or attempt > 0:
                result = capture.screenshot()
                img_path = result["path"]
            else:
                img_path = screenshot_path
            loc = vision.locate_element(img_path, description)
            if loc["x"] is not None:
                cx = loc["x"] + loc["width"] // 2
                cy = loc["y"] + loc["height"] // 2
                controller.click(cx, cy, button=button)
                return {"status": "ok", "element_found": True, "description": description,
                        "x": cx, "y": cy, "confidence": loc["confidence"], "attempts": attempt + 1}
        return {"status": "error", "element_found": False, "description": description, "attempts": retries}

    def type_into(self, description: str, text: str, screenshot_path: str | None = None,
                  press_enter: bool = False) -> dict:
        result = capture.screenshot()
        loc = vision.locate_element(result["path"], description)
        if loc["x"] is None:
            return {"status": "error", "element_found": False, "description": description}
        cx = loc["x"] + loc["width"] // 2
        cy = loc["y"] + loc["height"] // 2
        controller.click(cx, cy)
        time.sleep(0.1)
        controller.type_text(text)
        if press_enter:
            controller.press_key("enter")
        return {"status": "ok", "element_found": True, "description": description,
                "x": cx, "y": cy, "chars_typed": len(text)}

    def wait_for(self, description: str, timeout: int = 10, interval: float = 0.5) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout:
            result = capture.screenshot()
            loc = vision.locate_element(result["path"], description)
            if loc["x"] is not None:
                return {"status": "ok", "element_found": True, "description": description,
                        "x": loc["x"], "y": loc["y"],
                        "elapsed_ms": int((time.time() - t0) * 1000)}
            time.sleep(interval)
        return {"status": "timeout", "element_found": False, "description": description,
                "elapsed_ms": int((time.time() - t0) * 1000)}


element_finder = ElementFinder()
