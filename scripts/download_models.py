#!/usr/bin/env python3
"""Download Florence-2 and GLM-OCR models into the local models directory."""

from __future__ import annotations

import os
import sys
from pathlib import Path


MODELS_DIR = Path(os.environ.get("MODELS_DIR", "models")).resolve()
MODELS_DIR.mkdir(parents=True, exist_ok=True)
HF_TOKEN = os.environ.get("HF_TOKEN", "") or None


try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("Installing huggingface_hub...")
    os.system(f"{sys.executable} -m pip install huggingface_hub -q")
    from huggingface_hub import snapshot_download


def _is_downloaded(path: Path) -> bool:
    return path.exists() and len(list(path.iterdir())) > 3


def _download(repo_id: str, target: Path, label: str) -> None:
    print(f"\nDownloading {label} ({repo_id})...")
    if _is_downloaded(target):
        print("  Already exists, skipping")
        return

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        token=HF_TOKEN,
    )
    print("  Downloaded")


def _dir_size_gb(path: Path) -> float:
    total_size = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size / (1024**3)


def main() -> int:
    print("This will download approximately 2.3GB of models.")
    if HF_TOKEN is None:
        print("No HF_TOKEN set. If a model requires auth, set HF_TOKEN=hf_xxxxx")

    florence_path = MODELS_DIR / "Florence-2-base"
    ocr_path = MODELS_DIR / "GLM-OCR"

    _download("microsoft/Florence-2-base", florence_path, "Florence-2-base")
    _download("zai-org/GLM-OCR", ocr_path, "GLM-OCR")

    print(f"\nModels ready: {_dir_size_gb(MODELS_DIR):.1f}GB")
    print(f"Location: {MODELS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
