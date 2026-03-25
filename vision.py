# vision.py — Florence-2 vision model for UI understanding

import time
import re
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from config import VISION_MODEL_ID, DEVICE


class VisionEngine:
    def __init__(self):
        self.model = None
        self.processor = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        print(f"[Vision] Loading {VISION_MODEL_ID} on {DEVICE}...")
        t0 = time.time()
        self.processor = AutoProcessor.from_pretrained(VISION_MODEL_ID, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            VISION_MODEL_ID,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            trust_remote_code=True,
        ).to(DEVICE)
        print(f"[Vision] Loaded in {time.time() - t0:.1f}s")
        self._loaded = True

    def _run(self, image: Image.Image, prompt: str) -> str:
        self.load()
        inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            ids = self.model.generate(**inputs, max_new_tokens=1024, do_sample=False)
        return self.processor.batch_decode(ids, skip_special_tokens=True)[0]

    def describe_ui(self, image_path: str) -> dict:
        image = Image.open(image_path).convert("RGB")
        t0 = time.time()
        desc = self._run(image, "<CAPTION>")
        return {"description": desc, "time_ms": int((time.time() - t0) * 1000)}

    def describe_detailed(self, image_path: str) -> dict:
        image = Image.open(image_path).convert("RGB")
        t0 = time.time()
        desc = self._run(image, "<DETAILED_CAPTION>")
        return {"description": desc, "time_ms": int((time.time() - t0) * 1000)}

    def locate_element(self, image_path: str, description: str) -> dict:
        image = Image.open(image_path).convert("RGB")
        t0 = time.time()
        result = self._run(image, f"<OD> {description}")
        boxes = self._parse_boxes(result, image.size)
        if boxes:
            best = boxes[0]
            return {"x": best["x"], "y": best["y"], "width": best["width"],
                    "height": best["height"], "confidence": best["confidence"],
                    "all_matches": boxes, "time_ms": int((time.time() - t0) * 1000)}
        return {"x": None, "y": None, "width": None, "height": None,
                "confidence": 0, "all_matches": [],
                "time_ms": int((time.time() - t0) * 1000)}

    def locate_all(self, image_path: str, description: str) -> dict:
        image = Image.open(image_path).convert("RGB")
        t0 = time.time()
        result = self._run(image, f"<OD> {description}")
        boxes = self._parse_boxes(result, image.size)
        return {"matches": boxes, "count": len(boxes),
                "time_ms": int((time.time() - t0) * 1000)}

    def detect_all(self, image_path: str) -> dict:
        image = Image.open(image_path).convert("RGB")
        t0 = time.time()
        result = self._run(image, "<OD>")
        boxes = self._parse_boxes(result, image.size)
        return {"objects": boxes, "count": len(boxes),
                "time_ms": int((time.time() - t0) * 1000)}

    def _parse_boxes(self, raw: str, img_size: tuple) -> list[dict]:
        boxes = []
        img_w, img_h = img_size
        parts = re.split(r'(<loc_\d+>)', raw)
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if part.startswith('<loc_'):
                try:
                    y1 = int(part.replace('<loc_', '').replace('>', ''))
                    vals = []
                    for j in range(3):
                        i += 1
                        if i < len(parts):
                            vals.append(int(parts[i].replace('<loc_', '').replace('>', '').strip()))
                    if len(vals) == 3:
                        x1, y2, x2 = vals
                        i += 1
                        label = parts[i].strip() if i < len(parts) else "unknown"
                        boxes.append({
                            "label": label,
                            "x": int((x1 / 1000) * img_w),
                            "y": int((y1 / 1000) * img_h),
                            "width": int(((x2 - x1) / 1000) * img_w),
                            "height": int(((y2 - y1) / 1000) * img_h),
                            "confidence": 0.85,
                        })
                except (ValueError, IndexError):
                    pass
            i += 1
        return boxes


vision = VisionEngine()
