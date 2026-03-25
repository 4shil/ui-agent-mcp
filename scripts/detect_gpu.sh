#!/bin/bash
# detect_gpu.sh — Detect GPU and set device config

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Detecting hardware..."

# Check for NVIDIA GPU
HAS_CUDA=false
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$GPU_NAME" ]; then
        HAS_CUDA=true
        echo "✓ NVIDIA GPU: $GPU_NAME ($GPU_MEM)"
    fi
fi

# Check for Apple Silicon
IS_APPLE_SILICON=false
if [ "$(uname)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    IS_APPLE_SILICON=true
    echo "✓ Apple Silicon detected"
fi

# Check PyTorch CUDA
TORCH_CUDA=false
if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    TORCH_CUDA=true
    echo "✓ PyTorch CUDA available"
fi

# Determine device
if [ "$HAS_CUDA" = true ] && [ "$TORCH_CUDA" = true ]; then
    DEVICE="cuda"
    echo "🚀 Using GPU acceleration"
elif [ "$IS_APPLE_SILICON" = true ]; then
    DEVICE="mps"
    echo "🍎 Using Apple MPS"
else
    DEVICE="cpu"
    echo "💻 Using CPU (slower, but works)"
fi

# Save to .env
cat > .env << EOF
DEVICE=$DEVICE
VISION_MODEL=florence-2-base
EOF

echo "✓ Config saved to .env"
echo "✅ Device: $DEVICE"
