#!/bin/bash
# health_check.sh — Verify installation and show status

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════╗"
echo "║         UI Agent MCP — Health Check          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0
WARN=0

check() {
    if [ $? -eq 0 ]; then
        echo "  ✅ $1"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $1"
        FAIL=$((FAIL + 1))
    fi
}

warn() {
    echo "  ⚠️  $1"
    WARN=$((WARN + 1))
}

# ──── Core Files ────
echo "📁 Project files:"
[ -f "server.py" ] && check "server.py" || check "server.py MISSING"
[ -f "vision.py" ] && check "vision.py" || check "vision.py MISSING"
[ -f "ocr_engine.py" ] && check "ocr_engine.py" || check "ocr_engine.py MISSING"
[ -f "screen_capture.py" ] && check "screen_capture.py" || check "screen_capture.py MISSING"
[ -f "ui_controller.py" ] && check "ui_controller.py" || check "ui_controller.py MISSING"
[ -f "safety.py" ] && check "safety.py" || check "safety.py MISSING"
[ -f "config.py" ] && check "config.py" || check "config.py MISSING"

# ──── Python ────
echo ""
echo "🐍 Python:"
command -v python3 &> /dev/null && check "python3 installed" || check "python3 MISSING"

# ──── Venv ────
echo ""
echo "📦 Virtual environment:"
[ -d ".venv" ] && check "venv exists" || warn "venv not found (run install.sh)"

if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null
    python3 -c "import torch" 2>/dev/null && check "PyTorch" || check "PyTorch MISSING"
    python3 -c "import transformers" 2>/dev/null && check "Transformers" || check "Transformers MISSING"
    python3 -c "import mss" 2>/dev/null && check "mss (screen capture)" || check "mss MISSING"
    python3 -c "import pyautogui" 2>/dev/null && check "pyautogui (actions)" || check "pyautogui MISSING"
    python3 -c "import mcp" 2>/dev/null && check "mcp SDK" || check "mcp SDK MISSING"
fi

# ──── Models ────
echo ""
echo "🤖 AI Models:"
if [ -d "models/Florence-2-base" ] && [ "$(ls models/Florence-2-base 2>/dev/null | wc -l)" -gt 3 ]; then
    FLORENCE_SIZE=$(du -sh models/Florence-2-base 2>/dev/null | cut -f1)
    check "Florence-2-base ($FLORENCE_SIZE)"
else
    warn "Florence-2-base not downloaded (run download_models.sh)"
fi

if [ -d "models/GLM-OCR" ] && [ "$(ls models/GLM-OCR 2>/dev/null | wc -l)" -gt 3 ]; then
    OCR_SIZE=$(du -sh models/GLM-OCR 2>/dev/null | cut -f1)
    check "GLM-OCR ($OCR_SIZE)"
else
    warn "GLM-OCR not downloaded (run download_models.sh)"
fi

# ──── Hardware ────
echo ""
echo "🖥️  Hardware:"
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    check "NVIDIA GPU: $GPU_NAME"
else
    warn "No NVIDIA GPU (CPU mode)"
fi

# ──── Config ────
echo ""
echo "⚙️  Configuration:"
[ -f ".env" ] && check ".env config" || warn ".env not found"
[ -f "mcp_config.json" ] && check "MCP config" || warn "MCP config not generated"

# ──── System ────
echo ""
echo "🔧 System tools:"
command -v xdotool &> /dev/null && check "xdotool" || warn "xdotool (optional, for window mgmt)"

# ──── Service ────
echo ""
echo "🔧 Service:"
if [ -f "$HOME/.config/systemd/user/ui-agent-mcp.service" ]; then
    check "systemd service installed"
    if systemctl --user is-active ui-agent-mcp &>/dev/null; then
        echo "  🟢 Service running"
    else
        echo "  ⚪ Service not running"
    fi
else
    warn "systemd service not installed"
fi

# ──── Summary ────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ $PASS passed | ❌ $FAIL failed | ⚠️  $WARN warnings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🚀 Ready to run: source .venv/bin/activate && python server.py"
    exit 0
else
    echo ""
    echo "⚠️  Some checks failed. Run install.sh to fix."
    exit 1
fi
