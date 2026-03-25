#!/bin/bash
# setup_mcp.sh — Generate MCP config for OpenClaw / Claude / Cursor

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Generating MCP configurations..."

# Read device from .env
DEVICE="cpu"
if [ -f "$PROJECT_DIR/.env" ]; then
    DEVICE=$(grep "^DEVICE=" "$PROJECT_DIR/.env" | cut -d= -f2)
fi

# OpenClaw MCP config
OPENCLAW_DIR="$HOME/.openclaw"
if [ -d "$OPENCLAW_DIR" ]; then
    cat > "$PROJECT_DIR/mcp_config.json" << EOF
{
  "mcpServers": {
    "ui-agent": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "$PROJECT_DIR",
      "env": {
        "VISION_MODEL": "florence-2-base",
        "DEVICE": "$DEVICE"
      }
    }
  }
}
EOF
    echo "✓ OpenClaw MCP config: $PROJECT_DIR/mcp_config.json"
    echo "  Copy to OpenClaw config to enable"
fi

# Claude Desktop config
CLAUDE_CONFIG_DIR="$HOME/.config/claude"  # Linux
if [ "$(uname)" = "Darwin" ]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
fi
CLAUDE_CONFIG="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

mkdir -p "$CLAUDE_CONFIG_DIR" 2>/dev/null || true

if [ -d "$CLAUDE_CONFIG_DIR" ] || [ -f "$CLAUDE_CONFIG" ]; then
    if [ -f "$CLAUDE_CONFIG" ]; then
        # Merge with existing config
        echo "⚠ Claude config exists at $CLAUDE_CONFIG — merge manually"
    else
        cat > "$CLAUDE_CONFIG" << EOF
{
  "mcpServers": {
    "ui-agent": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "$PROJECT_DIR",
      "env": {
        "VISION_MODEL": "florence-2-base",
        "DEVICE": "$DEVICE"
      }
    }
  }
}
EOF
        echo "✓ Claude Desktop config: $CLAUDE_CONFIG"
    fi
fi

# Cursor config (if project has .cursor)
if [ -d "$PROJECT_DIR/.cursor" ] || [ -f "$PROJECT_DIR/.cursorrules" ]; then
    echo "ℹ Cursor: Add MCP server manually via settings"
fi

echo ""
echo "✅ MCP configs generated"
echo "   Device: $DEVICE"
echo ""
echo "Next steps:"
echo "  1. Copy mcp_config.json to your agent's config"
echo "  2. Restart your agent"
echo "  3. The 25 UI tools will be available"
