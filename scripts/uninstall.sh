#!/bin/bash
# uninstall.sh — Remove UI Agent MCP

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "╔══════════════════════════════════════════════╗"
echo "║        UI Agent MCP — Uninstall              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Stop service if running
if systemctl --user is-active ui-agent-mcp &>/dev/null; then
    echo "Stopping service..."
    systemctl --user stop ui-agent-mcp
    systemctl --user disable ui-agent-mcp
fi

# Remove service file
if [ -f "$HOME/.config/systemd/user/ui-agent-mcp.service" ]; then
    echo "Removing service..."
    rm "$HOME/.config/systemd/user/ui-agent-mcp.service"
    systemctl --user daemon-reload 2>/dev/null || true
fi

# Clean temp files
echo "Cleaning temp files..."
rm -rf "$PROJECT_DIR/screenshots"/*.png 2>/dev/null || true
rm -rf "$PROJECT_DIR/logs"/*.log 2>/dev/null || true
rm -rf "$PROJECT_DIR/.env" 2>/dev/null || true

echo ""
echo "What to remove?"
echo "  [1] Keep models (~2.3GB) — reinstall faster"
echo "  [2] Keep venv — no reinstall needed"
echo "  [3] Remove EVERYTHING including models"
echo "  [4] Cancel"
echo ""
read -p "Choice [1]: " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
    1)
        echo "Keeping models"
        ;;
    2)
        echo "Keeping venv"
        ;;
    3)
        echo "Removing venv..."
        rm -rf "$PROJECT_DIR/.venv"
        echo "Removing models..."
        rm -rf "$PROJECT_DIR/models"
        echo "✅ Everything removed"
        ;;
    4)
        echo "Cancelled"
        exit 0
        ;;
esac

echo "✅ Uninstall complete"
echo "   Project files still at: $PROJECT_DIR"
echo "   Delete manually: rm -rf $PROJECT_DIR"
