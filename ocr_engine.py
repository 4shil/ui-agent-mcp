# ocr_engine.py — GLM-OCR from Z.AI for text, table, and formula extraction

import time
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from config import OCR_MODEL_ID, DEVICE


class OCREngine:
    def __init__(self):
        self.model = None
        self.processor = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        print(f"[OCR] Loading {OCR_MODEL_ID} on {DEVICE}...")
        t0 = time.time()
        self.processor = AutoProcessor.from_pretrained(OCR_MODEL_ID, trust_remote_code=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            OCR_MODEL_ID,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            trust_remote_code=True,
            device_map="auto" if DEVICE == "cuda" else None,
        )
        if DEVICE == "cpu":
            self.model = self.model.to(DEVICE)
        print(f"[OCR] Loaded in {time.time() - t0:.1f}s")
        self._loaded = True

    def _run(self, image_path: str, prompt: str) -> str:
        self.load()
        messages = [{"role": "user", "content": [
            {"type": "image", "url": image_path},
            {"type": "text", "text": prompt},
        ]}]
        inputs = self.processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        ).to(self.model.device)
        inputs.pop("token_type_ids", None)
        with torch.no_grad():
            ids = self.model.generate(**inputs, max_new_tokens=8192)
        return self.processor.decode(ids[0], skip_special_tokens=True)

    def read_text(self, image_path: str) -> dict:
        t0 = time.time()
        result = self._run(image_path, "Text Recognition:")
        lines = [l.strip() for l in result.split("\n") if l.strip()]
        return {"text": result, "lines": lines, "line_count": len(lines),
                "time_ms": int((time.time() - t0) * 1000)}

    def read_text_region(self, image_path: str, x: int, y: int, w: int, h: int) -> dict:
        image = Image.open(image_path).convert("RGB")
        crop = image.crop((x, y, x + w, y + h))
        crop_path = Path(image_path).parent / "crop_temp.png"
        crop.save(str(crop_path))
        return self.read_text(str(crop_path))

    def read_table(self, image_path: str) -> dict:
        t0 = time.time()
        result = self._run(image_path, "Table Recognition:")
        return {"markdown_table": result, "raw": result,
                "time_ms": int((time.time() - t0) * 1000)}

    def read_formula(self, image_path: str) -> dict:
        t0 = time.time()
        result = self._run(image_path, "Formula Recognition:")
        return {"latex": result, "raw": result,
                "time_ms": int((time.time() - t0) * 1000)}

    def read_form(self, image_path: str) -> dict:
        t0 = time.time()
        result = self._run(image_path, "Form Recognition:")
        fields = []
        for line in result.split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                fields.append({"label": parts[0].strip(),
                               "value": parts[1].strip() if len(parts) > 1 else ""})
        return {"fields": fields, "raw": result,
                "time_ms": int((time.time() - t0) * 1000)}

    def ocr_info(self, image_path: str) -> dict:
        t0 = time.time()
        text = self.read_text(image_path)
        table = self.read_table(image_path)
        formula = self.read_formula(image_path)
        return {
            "summary": {"text_lines": text["line_count"],
                        "has_tables": len(table["raw"]) > 50,
                        "has_formulas": len(formula["raw"]) > 10},
            "text": text["text"], "table": table["markdown_table"],
            "formula": formula["latex"],
            "time_ms": int((time.time() - t0) * 1000),
        }


ocr = OCREngine()
