#!/bin/bash
# download_models.sh — Download Florence-2 and GLM-OCR models

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

source .venv/bin/activate

echo "This will download ~2.3GB of models."
echo ""

MODELS_DIR="$PROJECT_DIR/models"
mkdir -p "$MODELS_DIR"

python3 << 'PYEOF'
import os
import sys

models_dir = os.environ.get("MODELS_DIR", "models")

# Check HF token
hf_token = os.environ.get("HF_TOKEN", "")
if not hf_token:
    print("⚠ No HF_TOKEN set. Some models may need authentication.")
    print("  Set it: export HF_TOKEN=hf_xxxxx")
    print("  Get one: https://huggingface.co/settings/tokens")
    print("")

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("Installing huggingface_hub...")
    os.system(f"{sys.executable} -m pip install huggingface_hub -q")
    from huggingface_hub import snapshot_download

# Download Florence-2-base
print("📥 Downloading Florence-2-base (~470MB)...")
florence_path = os.path.join(models_dir, "Florence-2-base")
if os.path.exists(florence_path) and len(os.listdir(florence_path)) > 3:
    print("  ✓ Already exists, skipping")
else:
    snapshot_download(
        repo_id="microsoft/Florence-2-base",
        local_dir=florence_path,
        token=hf_token or None,
    )
    print("  ✅ Downloaded")

# Download GLM-OCR
print("\n📥 Downloading GLM-OCR (~1.8GB)...")
ocr_path = os.path.join(models_dir, "GLM-OCR")
if os.path.exists(ocr_path) and len(os.listdir(ocr_path)) > 3:
    print("  ✓ Already exists, skipping")
else:
    snapshot_download(
        repo_id="zai-org/GLM-OCR",
        local_dir=ocr_path,
        token=hf_token or None,
    )
    print("  ✅ Downloaded")

# Summary
total_size = 0
for dirpath, dirnames, filenames in os.walk(models_dir):
    for f in filenames:
        fp = os.path.join(dirpath, f)
        total_size += os.path.getsize(fp)

print(f"\n✅ Models downloaded: {total_size / (1024**3):.1f}GB total")
print(f"   Location: {models_dir}")
PYEOF
