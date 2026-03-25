# ui-agent-mcp

MCP server that gives AI agents **complete UI access** — see screens, understand elements, click, type, scroll, drag.

## Models

| Model | Size | Purpose | Source |
|-------|------|---------|--------|
| **Florence-2** | 0.23B | UI understanding, element detection, captioning | `microsoft/Florence-2-base` |
| **GLM-OCR** | 0.9B | Text, table, formula, form extraction | `zai-org/GLM-OCR` |

## One-Command Install

```bash
# Clone and install everything
git clone https://github.com/4shil/ui-agent-mcp.git
cd ui-agent-mcp
bash install.sh
```

The installer handles everything:
- System dependencies (python, xdotool, git)
- Python venv + pip packages
- GPU detection (NVIDIA CUDA / Apple MPS / CPU)
- AI model downloads (~2.3GB)
- MCP config generation
- Systemd service setup

## Quick Start

```bash
# After install, start the server:
source .venv/bin/activate
python server.py

# Or use the systemd service:
systemctl --user start ui-agent-mcp
```

## Health Check

```bash
bash scripts/health_check.sh
```

Shows status of all components, models, and dependencies.

## Uninstall

```bash
bash scripts/uninstall.sh
```

## MCP Config

The installer auto-generates config for OpenClaw and Claude Desktop.

Manual config (`mcp_config.json`):
```json
{
  "mcpServers": {
    "ui-agent": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/path/to/ui-agent-mcp",
      "env": {
        "VISION_MODEL": "florence-2-base",
        "DEVICE": "cpu"
      }
    }
  }
}
```

## 25 Tools

### Screen Capture
`screenshot` · `screenshot_region` · `get_screen_info`

### Vision (Florence-2)
`describe_ui` · `describe_ui_detailed` · `locate_element` · `locate_all` · `detect_all`

### OCR (GLM-OCR by Z.AI)
`read_text` · `read_text_region` · `read_table` · `read_formula` · `read_form`

### Mouse
`click` · `double_click` · `right_click` · `hover` · `scroll` · `drag` · `get_mouse_position`

### Keyboard
`type_text` · `press_key` · `hotkey` · `type_and_enter`

### Composite (Smart)
`find_and_click` · `type_into` · `wait_for_element`

### Apps
`open_app` · `close_app` · `get_focused_window`

### Safety
`get_safety_stats`

## Project Structure

```
ui-agent-mcp/
├── install.sh              # One-command installer
├── server.py               # MCP server (25 tools)
├── vision.py               # Florence-2 vision
├── ocr_engine.py           # GLM-OCR text extraction
├── screen_capture.py       # Screenshot via mss
├── ui_controller.py        # Click/type/scroll/drag
├── element_finder.py       # Smart find + click
├── safety.py               # Cooldowns, rate limits
├── config.py               # All settings
├── requirements.txt
├── mcp_config.json
├── scripts/
│   ├── setup_deps.sh       # System dependencies
│   ├── setup_python.sh     # Python venv + packages
│   ├── detect_gpu.sh       # GPU detection
│   ├── download_models.sh  # Model downloads
│   ├── setup_mcp.sh        # MCP config generator
│   ├── setup_service.sh    # Systemd service
│   ├── health_check.sh     # Status checker
│   └── uninstall.sh        # Cleanup
└── tests/
    └── test_all.py
```

## Agent Loop Pattern

```
1. screenshot()                    → see the screen
2. describe_ui() or read_text()    → understand what's there
3. locate_element()                → find target
4. click() / type() / scroll()     → take action
5. screenshot() again              → verify result
```

## Requirements

- Python 3.10+
- Linux (x11) / macOS / Windows
- GPU optional (CUDA recommended for GLM-OCR speed)

## License

MIT
