#!/bin/bash
# health_check.sh — Verify installation and show status

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
PY="$PROJECT_DIR/.venv/bin/python3"

echo "╔══════════════════════════════════════════════╗"
echo "║         UI Agent MCP — Health Check          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

PASS=0; FAIL=0; WARN=0

check() { [ $? -eq 0 ] && { echo "  ✅ $1"; PASS=$((PASS+1)); } || { echo "  ❌ $1"; FAIL=$((FAIL+1)); }; }
warn() { echo "  ⚠️  $1"; WARN=$((WARN+1)); }

echo "📁 Project files:"
for f in server.py vision.py ocr_engine.py screen_capture.py ui_controller.py safety.py config.py dashboard.py; do
    [ -f "$f" ] && check "$f" || check "$f MISSING"
done

echo ""
echo "🐍 Python:"
command -v python3 &> /dev/null && check "python3 installed" || check "python3 MISSING"

echo ""
echo "📦 Virtual environment:"
[ -d ".venv" ] && check "venv exists" || warn "venv not found"

if [ -d ".venv" ] && [ -x "$PY" ]; then
    $PY -c "import torch" 2>/dev/null && check "PyTorch" || check "PyTorch MISSING"
    $PY -c "import transformers" 2>/dev/null && check "Transformers" || check "Transformers MISSING"
    $PY -c "import mss" 2>/dev/null && check "mss (screen capture)" || check "mss MISSING"
    $PY -c "import importlib.util; s=importlib.util.find_spec('pyautogui'); assert s" 2>/dev/null && check "pyautogui (actions)" || check "pyautogui MISSING"
    $PY -c "import mcp" 2>/dev/null && check "mcp SDK" || check "mcp SDK MISSING"
    $PY -c "import pytermgui" 2>/dev/null && check "pytermgui (TUI)" || check "pytermgui MISSING"
fi

echo ""
echo "🤖 AI Models:"
if [ -d "models/Florence-2-base" ] && [ "$(ls models/Florence-2-base 2>/dev/null | wc -l)" -gt 3 ]; then
    SIZE=$(du -sh models/Florence-2-base 2>/dev/null | cut -f1)
    check "Florence-2-base ($SIZE)"
else
    warn "Florence-2-base not downloaded (run download_models.sh)"
fi
if [ -d "models/GLM-OCR" ] && [ "$(ls models/GLM-OCR 2>/dev/null | wc -l)" -gt 3 ]; then
    SIZE=$(du -sh models/GLM-OCR 2>/dev/null | cut -f1)
    check "GLM-OCR ($SIZE)"
else
    warn "GLM-OCR not downloaded (run download_models.sh)"
fi

echo ""
echo "🖥️  Hardware:"
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    check "NVIDIA GPU: $GPU_NAME"
else
    warn "No NVIDIA GPU (CPU mode)"
fi

echo ""
echo "⚙️  Configuration:"
[ -f ".env" ] && check ".env config" || warn ".env not found"
[ -f "mcp_config.json" ] && check "MCP config" || warn "MCP config not generated"

echo ""
echo "🔧 System tools:"
command -v xdotool &> /dev/null && check "xdotool" || warn "xdotool (optional)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ $PASS passed | ❌ $FAIL failed | ⚠️  $WARN warnings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🚀 Ready! Start: source .venv/bin/activate && python server.py"
    echo "   Dashboard: python dashboard.py"
    exit 0
else
    echo ""
    echo "⚠️  Run: bash install.sh to fix missing deps"
    exit 1
fi
