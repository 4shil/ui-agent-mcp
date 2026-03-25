#!/bin/bash
# setup_python.sh — Create venv and install Python packages with progress display

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════╗"
echo "║     Python Environment Setup                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ──── Detect GPU and force CUDA torch ────
echo "🔍 Detecting hardware..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "✓ NVIDIA GPU found: $GPU_NAME"
    USE_CUDA=true
else
    echo "ℹ No NVIDIA GPU — using CPU"
    USE_CUDA=false
fi
echo ""

# ──── Create venv ────
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Created .venv"
else
    echo "✓ Virtual environment exists"
fi

source .venv/bin/activate

# ──── Upgrade pip ────
echo ""
echo "⬆️ Upgrading pip..."
pip install --upgrade pip 2>&1 | grep -E "Successfully|Requirement" || true
echo "✓ pip upgraded: $(pip --version | cut -d' ' -f1-2)"

# ──── Install PyTorch (with CUDA if available) ────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Installing PyTorch..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$USE_CUDA" = true ]; then
    echo "🔥 Installing PyTorch with CUDA 12.1 support..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 2>&1 | tail -5
else
    echo "💻 Installing PyTorch (CPU)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -5
fi

# Verify torch
TORCH_VER=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "FAILED")
TORCH_CUDA=$(python3 -c "import torch; print('CUDA ' + torch.version.cuda if torch.cuda.is_available() else 'CPU')" 2>/dev/null || echo "?")
echo "✓ PyTorch $TORCH_VER ($TORCH_CUDA)"

# ──── Install other packages with progress ────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Installing packages from requirements.txt..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Read requirements and install one by one for progress display
TOTAL=$(grep -cve '^\s*$\|^\s*#' requirements.txt || echo 0)
CURRENT=0

while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    CURRENT=$((CURRENT + 1))
    PKG_NAME=$(echo "$line" | sed 's/[>=<].*//' | xargs)
    
    echo -n "  [$CURRENT/$TOTAL] $PKG_NAME ... "
    
    # Check if already installed
    if pip show "$PKG_NAME" &>/dev/null; then
        INSTALLED_VER=$(pip show "$PKG_NAME" 2>/dev/null | grep "^Version:" | cut -d' ' -f2)
        echo "✓ already installed ($INSTALLED_VER)"
    else
        # Install with spinner
        (pip install "$line" -q 2>&1) &
        PID=$!
        SPINNER='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        i=0
        while kill -0 $PID 2>/dev/null; do
            printf "\r  [$CURRENT/$TOTAL] $PKG_NAME ... ${SPINNER:i%${#SPINNER}:1}"
            i=$((i+1))
            sleep 0.1
        done
        wait $PID
        RESULT=$?
        
        if [ $RESULT -eq 0 ]; then
            INSTALLED_VER=$(pip show "$PKG_NAME" 2>/dev/null | grep "^Version:" | cut -d' ' -f2)
            printf "\r  [$CURRENT/$TOTAL] $PKG_NAME ... ✅ installed ($INSTALLED_VER)\n"
        else
            printf "\r  [$CURRENT/$TOTAL] $PKG_NAME ... ⚠️ failed (optional)\n"
        fi
    fi
done < requirements.txt

# ──── Summary ────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "🐍 Python: $(python3 --version)"
echo "🔥 PyTorch: $TORCH_VER ($TORCH_CUDA)"

echo ""
echo "Verifying key imports:"
python3 -c "import torch; print(f'  ✓ PyTorch {torch.__version__}')" 2>/dev/null && OK=1 || OK=0
python3 -c "import transformers; print(f'  ✓ Transformers {transformers.__version__}')" 2>/dev/null && OK=$((OK+1)) || echo "  ⚠ Transformers missing"
python3 -c "import mss; print(f'  ✓ mss (screen capture)')" 2>/dev/null && OK=$((OK+1)) || echo "  ⚠ mss missing"
python3 -c "import pyautogui; print(f'  ✓ pyautogui (actions)')" 2>/dev/null && OK=$((OK+1)) || echo "  ⚠ pyautogui missing"
python3 -c "import mcp; print(f'  ✓ mcp SDK')" 2>/dev/null && OK=$((OK+1)) || echo "  ⚠ mcp missing"

echo ""
echo "✅ Python environment ready!"
echo "   Location: $PROJECT_DIR/.venv"
echo "   Activate: source .venv/bin/activate"
