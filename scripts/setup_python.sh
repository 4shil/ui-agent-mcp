#!/bin/bash
# setup_python.sh — Create venv and install Python packages

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Setting up Python environment..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip -q 2>/dev/null

echo "Installing Python packages (this may take a few minutes)..."
pip install -r requirements.txt -q 2>&1 | tail -5

echo "Verifying installations..."
python3 -c "import torch; print(f'✓ PyTorch {torch.__version__}')" 2>/dev/null || echo "⚠ PyTorch"
python3 -c "import transformers; print(f'✓ Transformers {transformers.__version__}')" 2>/dev/null || echo "⚠ Transformers"
python3 -c "import mss; print('✓ mss')" 2>/dev/null || echo "⚠ mss"
python3 -c "import pyautogui; print('✓ pyautogui')" 2>/dev/null || echo "⚠ pyautogui"
python3 -c "import mcp; print('✓ mcp SDK')" 2>/dev/null || echo "⚠ mcp"

echo "✅ Python environment ready"
