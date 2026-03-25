#!/bin/bash
# One-liner installer for UI Agent MCP
# Usage: curl -fsSL https://raw.githubusercontent.com/4shil/ui-agent-mcp/main/quickinstall.sh | bash

set -e

REPO="https://github.com/4shil/ui-agent-mcp.git"
INSTALL_DIR="$HOME/ui-agent-mcp"

echo "╔══════════════════════════════════════════════╗"
echo "║     UI Agent MCP — One-Click Installer       ║"
echo "║     Florence-2 + GLM-OCR (Z.AI)              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ──── Check deps ────
for cmd in python3 git curl; do
    if ! command -v $cmd &>/dev/null; then
        echo "❌ $cmd required. Install it first."
        exit 1
    fi
done
echo "✓ python3, git, curl found"

# ──── Clone or update ────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "📁 Updating existing install..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "📥 Cloning UI Agent MCP..."
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ──── Run full installer ────
echo ""
bash install.sh

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           ✅ READY TO USE                    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "cd $INSTALL_DIR"
echo "source .venv/bin/activate"
echo "python server.py        # start MCP server"
echo "python dashboard.py     # launch TUI dashboard"
