#!/bin/bash
# install.sh — One command to set up everything
# Usage: curl -fsSL <url> | bash  OR  bash install.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════╗"
echo "║     UI Agent MCP — Full Installer            ║"
echo "║     Vision: Florence-2 | OCR: GLM-OCR        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

STEPS=9
STEP=0

next_step() {
    STEP=$((STEP + 1))
    echo ""
    echo "━━━ [$STEP/$STEPS] $1 ━━━"
}

# Step 1: System dependencies
next_step "Installing system dependencies"
bash "$PROJECT_DIR/scripts/setup_deps.sh"

# Step 2: Python venv + pip packages
next_step "Setting up Python environment"
bash "$PROJECT_DIR/scripts/setup_python.sh"

# Step 3: GPU detection + config
next_step "Detecting hardware and configuring"
bash "$PROJECT_DIR/scripts/detect_gpu.sh"

# Step 4: Download AI models
next_step "Downloading AI models (Florence-2 + GLM-OCR)"
bash "$PROJECT_DIR/scripts/download_models.sh"

# Step 5: Generate MCP config
next_step "Generating MCP configuration"
bash "$PROJECT_DIR/scripts/setup_mcp.sh"

# Step 6: Setup systemd service (optional)
next_step "Setting up background service"
bash "$PROJECT_DIR/scripts/setup_service.sh"

# Step 7: Run health check
next_step "Running health check"
bash "$PROJECT_DIR/scripts/health_check.sh"

# Step 8: Save install state
next_step "Saving install state"
echo "installed_at=$(date -Iseconds)" > .install_state
echo "version=1.0.0" >> .install_state
echo "device=$DEVICE" >> .install_state
echo "✅ Install state saved"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           ✅ INSTALLATION COMPLETE           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Start the MCP server:"
echo "  cd $PROJECT_DIR"
echo "  source .venv/bin/activate"
echo "  python server.py"
echo ""
echo "Or use the service:"
echo "  systemctl --user start ui-agent-mcp"
echo ""
echo "Check status:"
echo "  bash scripts/health_check.sh"
echo ""
