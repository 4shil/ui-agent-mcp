import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_controller import controller


def _reset_controller_state() -> None:
    controller._action_count = 0
    controller._minute_start = time.time()
    controller._last_action_time = 0


def test_click_mock() -> dict:
    _reset_controller_state()
    with patch("ui_controller.pyautogui.click") as click_mock:
        result = controller.click(120, 220)
        click_mock.assert_called_once_with(120, 220, button="left")
    assert result["status"] == "ok"
    return result


def test_type_mock() -> dict:
    _reset_controller_state()
    with patch("ui_controller.pyautogui.typewrite") as type_mock:
        result = controller.type_text("hello world", interval=0)
        type_mock.assert_called_once_with("hello world", interval=0)
    assert result["status"] == "ok"
    return result


def test_scroll_mock() -> dict:
    _reset_controller_state()
    with patch("ui_controller.pyautogui.moveTo") as move_mock, patch("ui_controller.pyautogui.scroll") as scroll_mock:
        result = controller.scroll(200, 300, direction="down", amount=5)
        move_mock.assert_called_once_with(200, 300)
        scroll_mock.assert_called_once_with(-5)
    assert result["status"] == "ok"
    return result


def test_drag_mock() -> dict:
    _reset_controller_state()
    with patch("ui_controller.pyautogui.moveTo") as move_mock, patch("ui_controller.pyautogui.drag") as drag_mock:
        result = controller.drag(50, 60, 250, 300, duration=0.2)
        move_mock.assert_called_once_with(50, 60)
        drag_mock.assert_called_once_with(200, 240, duration=0.2)
    assert result["status"] == "ok"
    return result


def run_suite() -> dict:
    click = test_click_mock()
    typed = test_type_mock()
    scroll = test_scroll_mock()
    drag = test_drag_mock()
    print("[actions] click/type/scroll/drag mock tests OK")
    return {"click": click, "type": typed, "scroll": scroll, "drag": drag}


if __name__ == "__main__":
    run_suite()
    print("[actions] OK")
