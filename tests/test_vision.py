import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEVICE
from vision import vision
from tests._test_utils import get_test_image_path


def test_describe_ui(image_path: str) -> dict:
    result = vision.describe_ui(image_path)
    assert "description" in result
    assert isinstance(result["description"], str)
    assert "time_ms" in result
    return result


def test_locate_element(image_path: str) -> dict:
    result = vision.locate_element(image_path, "button")
    for key in ["x", "y", "width", "height", "confidence", "all_matches", "time_ms"]:
        assert key in result
    assert isinstance(result["all_matches"], list)
    return result


def test_detect_all(image_path: str) -> dict:
    result = vision.detect_all(image_path)
    assert "objects" in result
    assert "count" in result
    assert isinstance(result["objects"], list)
    assert isinstance(result["count"], int)
    return result


def run_suite() -> dict:
    image_path = get_test_image_path()
    print(f"[vision] DEVICE={DEVICE} image={image_path}")
    describe = test_describe_ui(image_path)
    locate = test_locate_element(image_path)
    detect = test_detect_all(image_path)
    print(f"[vision] describe_ms={describe['time_ms']} locate_ms={locate['time_ms']} detect_ms={detect['time_ms']}")
    return {"describe": describe, "locate": locate, "detect": detect}


if __name__ == "__main__":
    run_suite()
    print("[vision] OK")
