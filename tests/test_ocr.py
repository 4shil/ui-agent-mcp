import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEVICE
from ocr_engine import ocr
from tests._test_utils import get_test_image_path


def test_read_text(image_path: str) -> dict:
    result = ocr.read_text(image_path)
    for key in ["text", "lines", "line_count", "time_ms"]:
        assert key in result
    assert isinstance(result["text"], str)
    assert isinstance(result["lines"], list)
    return result


def test_read_table(image_path: str) -> dict:
    result = ocr.read_table(image_path)
    for key in ["markdown_table", "raw", "time_ms"]:
        assert key in result
    return result


def test_read_form(image_path: str) -> dict:
    result = ocr.read_form(image_path)
    for key in ["fields", "raw", "time_ms"]:
        assert key in result
    assert isinstance(result["fields"], list)
    return result


def test_read_formula(image_path: str) -> dict:
    result = ocr.read_formula(image_path)
    for key in ["latex", "raw", "time_ms"]:
        assert key in result
    return result


def run_suite() -> dict:
    image_path = get_test_image_path()
    print(f"[ocr] DEVICE={DEVICE} image={image_path}")
    text = test_read_text(image_path)
    table = test_read_table(image_path)
    form = test_read_form(image_path)
    formula = test_read_formula(image_path)
    print(
        f"[ocr] text_ms={text['time_ms']} table_ms={table['time_ms']} "
        f"form_ms={form['time_ms']} formula_ms={formula['time_ms']}"
    )
    return {"text": text, "table": table, "form": form, "formula": formula}


if __name__ == "__main__":
    run_suite()
    print("[ocr] OK")
