# tests/test_all.py — Integration and feature tests

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    from config import DEVICE, OCR_MODEL_ID, VISION_MODEL_ID

    assert VISION_MODEL_ID.startswith("microsoft/")
    assert OCR_MODEL_ID.startswith("zai-org/")
    assert DEVICE in {"cpu", "cuda"}
    print(f"[core] Config OK (DEVICE={DEVICE})")


def test_safety():
    from safety import safety

    stats = safety.get_stats()
    assert "total_actions" in stats
    result = safety.check_destructive("rm -rf", path="/")
    assert result is not None
    print("[core] Safety OK")


def test_screen_capture():
    from screen_capture import capture

    info = capture.get_screen_info()
    assert info["width"] > 0
    assert info["height"] > 0
    shot = capture.screenshot()
    assert "path" in shot
    print(f"[core] Screen capture OK ({info['width']}x{info['height']})")


def test_server():
    from server import TOOLS

    names = [t.name for t in TOOLS]
    assert "screenshot" in names
    assert "click" in names
    assert "read_text" in names
    print(f"[core] MCP server tools OK ({len(names)})")


def test_feature_suites():
    from tests.test_actions import run_suite as run_actions
    from tests.test_ocr import run_suite as run_ocr
    from tests.test_vision import run_suite as run_vision

    run_actions()
    run_vision()
    run_ocr()
    print("[suite] vision/ocr/actions OK")


if __name__ == "__main__":
    print("=" * 56)
    print("  UI Agent MCP — Full Test Suite")
    print("=" * 56)
    test_config()
    test_safety()
    test_screen_capture()
    test_server()
    test_feature_suites()

    if os.getenv("RUN_BENCHMARKS", "0") == "1":
        from tests.benchmarks import run_benchmarks

        run_benchmarks()

    print("=" * 56)
    print("  DONE")
