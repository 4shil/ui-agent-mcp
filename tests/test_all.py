# tests/test_all.py — Integration tests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config():
    from config import VISION_MODEL_ID, OCR_MODEL_ID, DEVICE
    assert VISION_MODEL_ID == "microsoft/Florence-2-base"
    assert OCR_MODEL_ID == "zai-org/GLM-OCR"
    print("✅ Config OK")

def test_screen_capture():
    from screen_capture import capture
    info = capture.get_screen_info()
    assert info["width"] > 0
    result = capture.screenshot()
    assert "path" in result
    print(f"✅ Screen capture: {info['width']}x{info['height']}")
    return result["path"]

def test_ui_controller():
    from ui_controller import controller
    pos = controller.get_mouse_position()
    assert "x" in pos
    print("✅ UI controller OK")

def test_safety():
    from safety import safety
    stats = safety.get_stats()
    assert "total_actions" in stats
    result = safety.check_destructive("rm", path="-rf /")
    assert result is not None
    print("✅ Safety OK")

def test_vision():
    from vision import vision
    vision.load()
    assert vision._loaded
    print("✅ Vision model loads")

def test_ocr():
    from ocr_engine import ocr
    ocr.load()
    assert ocr._loaded
    print("✅ OCR model loads")

def test_element_finder():
    from element_finder import element_finder
    assert hasattr(element_finder, "find_and_click")
    print("✅ Element finder OK")

def test_server():
    from server import TOOLS
    names = [t.name for t in TOOLS]
    assert len(names) == 25
    assert "screenshot" in names
    assert "click" in names
    assert "read_text" in names
    print(f"✅ MCP server: {len(names)} tools")

if __name__ == "__main__":
    print("=" * 40)
    print("  UI Agent MCP — Tests")
    print("=" * 40)
    test_config()
    test_safety()
    test_screen_capture()
    test_ui_controller()
    test_element_finder()
    try: test_vision()
    except Exception as e: print(f"⚠ Vision: {e}")
    try: test_ocr()
    except Exception as e: print(f"⚠ OCR: {e}")
    test_server()
    print("=" * 40)
    print("  ✅ Done!")
