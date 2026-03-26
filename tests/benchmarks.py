import os
import sys
import time
from pathlib import Path
from statistics import mean
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEVICE
from ocr_engine import ocr
from screen_capture import capture
from ui_controller import controller
from vision import vision
from tests._test_utils import get_test_image_path


def _measure(operation, runs: int):
    values = []
    for _ in range(runs):
        t0 = time.perf_counter()
        operation()
        values.append((time.perf_counter() - t0) * 1000)
    return {
        "runs": runs,
        "avg_ms": mean(values),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def _print_table(rows):
    print("\nBenchmark summary (ms)")
    print("-" * 74)
    print(f"{'operation':<22}{'runs':>6}{'avg_ms':>14}{'min_ms':>14}{'max_ms':>14}")
    print("-" * 74)
    for op, stat in rows:
        print(
            f"{op:<22}{stat['runs']:>6}{stat['avg_ms']:>14.1f}"
            f"{stat['min_ms']:>14.1f}{stat['max_ms']:>14.1f}"
        )
    print("-" * 74)


def run_benchmarks() -> list[tuple[str, dict]]:
    image_path = get_test_image_path()
    print(f"[bench] DEVICE={DEVICE} image={image_path}")

    rows = []
    rows.append(("screenshot", _measure(lambda: capture.screenshot(), runs=3)))
    rows.append(("ocr_read_text", _measure(lambda: ocr.read_text(image_path), runs=1)))
    rows.append(("vision_describe", _measure(lambda: vision.describe_ui(image_path), runs=1)))
    rows.append(("vision_locate", _measure(lambda: vision.locate_element(image_path, "button"), runs=1)))

    with patch("ui_controller.pyautogui.click"):
        controller._last_action_time = 0
        rows.append(("click_mock", _measure(lambda: controller.click(100, 100), runs=3)))

    _print_table(rows)
    return rows


if __name__ == "__main__":
    run_benchmarks()
