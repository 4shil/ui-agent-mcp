#!/bin/bash
# download_models.sh — Download Florence-2 and GLM-OCR models

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODELS_DIR="$PROJECT_DIR/models"
mkdir -p "$MODELS_DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

export MODELS_DIR

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" scripts/download_models.py
