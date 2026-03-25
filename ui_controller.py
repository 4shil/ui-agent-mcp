# ui_controller.py — Mouse, keyboard, and app actions

import time
import subprocess
import platform
import pyautogui
from config import ACTION_COOLDOWN_MS

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True


class UIController:
    def __init__(self):
        self._last_action_time = 0
        self._action_count = 0
        self._minute_start = time.time()

    def _cooldown(self):
        elapsed = (time.time() - self._last_action_time) * 1000
        if elapsed < ACTION_COOLDOWN_MS:
            time.sleep((ACTION_COOLDOWN_MS - elapsed) / 1000)
        self._last_action_time = time.time()

    def _rate_limit_check(self) -> bool:
        now = time.time()
        if now - self._minute_start > 60:
            self._action_count = 0
            self._minute_start = now
        self._action_count += 1
        return self._action_count <= 60

    def click(self, x: int, y: int, button: str = "left") -> dict:
        if not self._rate_limit_check():
            return {"status": "error", "error": "Rate limit exceeded"}
        self._cooldown()
        pyautogui.click(x, y, button=button)
        return {"status": "ok", "action": "click", "x": x, "y": y, "button": button}

    def double_click(self, x: int, y: int) -> dict:
        if not self._rate_limit_check():
            return {"status": "error", "error": "Rate limit exceeded"}
        self._cooldown()
        pyautogui.doubleClick(x, y)
        return {"status": "ok", "action": "double_click", "x": x, "y": y}

    def right_click(self, x: int, y: int) -> dict:
        self._cooldown()
        pyautogui.rightClick(x, y)
        return {"status": "ok", "action": "right_click", "x": x, "y": y}

    def hover(self, x: int, y: int) -> dict:
        self._cooldown()
        pyautogui.moveTo(x, y)
        return {"status": "ok", "action": "hover", "x": x, "y": y}

    def get_mouse_position(self) -> dict:
        x, y = pyautogui.position()
        return {"status": "ok", "x": x, "y": y}

    def type_text(self, text: str, interval: float = 0.02) -> dict:
        if not self._rate_limit_check():
            return {"status": "error", "error": "Rate limit exceeded"}
        self._cooldown()
        pyautogui.typewrite(text, interval=interval)
        return {"status": "ok", "action": "type", "chars": len(text)}

    def press_key(self, key: str) -> dict:
        self._cooldown()
        pyautogui.press(key)
        return {"status": "ok", "action": "press_key", "key": key}

    def hotkey(self, *keys: str) -> dict:
        self._cooldown()
        pyautogui.hotkey(*keys)
        return {"status": "ok", "action": "hotkey", "keys": list(keys)}

    def type_and_enter(self, text: str) -> dict:
        self._cooldown()
        pyautogui.typewrite(text, interval=0.02)
        pyautogui.press("enter")
        return {"status": "ok", "action": "type_and_enter", "chars": len(text)}

    def scroll(self, x: int, y: int, direction: str = "down", amount: int = 3) -> dict:
        self._cooldown()
        pyautogui.moveTo(x, y)
        pyautogui.scroll(-amount if direction == "down" else amount)
        return {"status": "ok", "action": "scroll", "direction": direction, "amount": amount}

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> dict:
        self._cooldown()
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return {"status": "ok", "action": "drag", "from": [x1, y1], "to": [x2, y2]}

    def open_app(self, app_name: str) -> dict:
        self._cooldown()
        system = platform.system()
        try:
            if system == "Linux":
                subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            elif system == "Windows":
                subprocess.Popen(["start", app_name], shell=True)
            time.sleep(2)
            return {"status": "ok", "action": "open_app", "app": app_name}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def close_app(self, app_name: str) -> dict:
        system = platform.system()
        try:
            if system == "Linux":
                subprocess.Popen(["pkill", "-f", app_name])
            elif system == "Darwin":
                subprocess.Popen(["osascript", "-e", f'quit app "{app_name}"'])
            elif system == "Windows":
                subprocess.Popen(["taskkill", "/IM", f"{app_name}.exe", "/F"], shell=True)
            return {"status": "ok", "action": "close_app", "app": app_name}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_focused_window(self) -> dict:
        try:
            if platform.system() == "Linux":
                result = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                                        capture_output=True, text=True)
                return {"status": "ok", "title": result.stdout.strip()}
            return {"status": "ok", "note": "Platform not fully supported"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_screen_info(self) -> dict:
        size = pyautogui.size()
        return {"status": "ok", "width": size[0], "height": size[1]}


controller = UIController()
