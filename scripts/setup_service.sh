#!/bin/bash
# setup_service.sh — Create systemd user service for background operation

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up background service..."

# Only works on Linux with systemd
if [ "$(uname)" != "Linux" ]; then
    echo "⚠ Service setup only supported on Linux"
    echo "  On macOS, use launchd or just run manually"
    exit 0
fi

if ! command -v systemctl &> /dev/null; then
    echo "⚠ systemctl not found"
    exit 0
fi

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_DIR/ui-agent-mcp.service" << EOF
[Unit]
Description=UI Agent MCP Server
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python3 $PROJECT_DIR/server.py
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=default.target
EOF

# Reload systemd
systemctl --user daemon-reload 2>/dev/null || true

echo "✓ Service created: ui-agent-mcp.service"
echo ""
echo "Commands:"
echo "  Start:   systemctl --user start ui-agent-mcp"
echo "  Stop:    systemctl --user stop ui-agent-mcp"
echo "  Status:  systemctl --user status ui-agent-mcp"
echo "  Enable:  systemctl --user enable ui-agent-mcp  (auto-start on login)"
echo ""
echo "✅ Service ready (not started automatically)"
