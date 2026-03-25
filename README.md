# UI Agent MCP

Give AI agents **complete UI access** — see screens, read text, click, type, scroll, drag.

## 🚀 One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/4shil/ui-agent-mcp/main/quickinstall.sh | bash
```

Or manual:
```bash
git clone https://github.com/4shil/ui-agent-mcp.git
cd ui-agent-mcp
bash install.sh
```

## 🧠 Models

| Model | Size | Purpose |
|-------|------|---------|
| **Florence-2** (Microsoft) | ~0.9GB | UI understanding, element detection |
| **GLM-OCR** (Z.AI) | ~0.7GB | Text, table, formula extraction |

Both auto-download during install. GPU (NVIDIA CUDA) recommended but CPU works.

## 🎮 TUI Dashboard

Launch the interactive dashboard after install:

```bash
cd ~/ui-agent-mcp
source .venv/bin/activate
python dashboard.py
```

Features:
- 🔥 Live GPU monitoring (utilization bar, memory, temperature)
- 💻 System stats (CPU, RAM, uptime)
- 🤖 Model download status
- 📊 Action analytics (total, hourly, errors, top actions)
- 🖥️ Live MCP server log streaming
- 📥 One-click model download
- 🔍 Health check
- ⌨️ `q` = quit, `r` = refresh

## 🔌 MCP Server

Start the MCP server (25 tools for AI agents):

```bash
source .venv/bin/activate
python server.py
```

## 🐳 Docker

Build image:

```bash
docker build -t ui-agent-mcp .
```

Run with NVIDIA GPU + REST port:

```bash
docker run --gpus all -p 8080:8080 ui-agent-mcp
```

Use Docker Compose (includes GPU flag and model cache volume):

```bash
docker compose up --build
```

Use CUDA base image variant (optional):

```bash
BASE_IMAGE=nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 docker compose up --build
```

Notes:
- MCP server runs over stdio (default process in container)
- Optional REST API is available on `http://localhost:8080`
- Models are cached in the `models_cache` named volume
- Set `HF_TOKEN` in your environment if gated model access is required

### MCP Config

```json
{
  "mcpServers": {
    "ui-agent": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/home/USER/ui-agent-mcp"
    }
  }
}
```

## 🛠 25 Tools

### Screen Capture
`screenshot` · `screenshot_region` · `get_screen_info`

### Vision (Florence-2)
`describe_ui` · `describe_ui_detailed` · `locate_element` · `locate_all` · `detect_all`

### OCR (GLM-OCR)
`read_text` · `read_text_region` · `read_table` · `read_formula` · `read_form`

### Mouse
`click` · `double_click` · `right_click` · `hover` · `scroll` · `drag` · `get_mouse_position`

### Keyboard
`type_text` · `press_key` · `hotkey` · `type_and_enter`

### Composite
`find_and_click` · `type_into` · `wait_for_element`

### Apps & Safety
`open_app` · `close_app` · `get_focused_window` · `get_safety_stats`

## 📋 Agent Loop Pattern

```
1. screenshot()                    → see
2. describe_ui() / read_text()     → understand
3. locate_element()                → find
4. click() / type()                → act
5. screenshot()                    → verify
```

## 🔧 Commands

```bash
bash install.sh              # Full install (deps + venv + models + config)
bash scripts/health_check.sh # Verify everything
bash scripts/download_models.sh  # Re-download models
bash scripts/uninstall.sh    # Remove everything
python dashboard.py          # Launch TUI dashboard
python server.py             # Start MCP server
```

## 📁 Project Structure

```
ui-agent-mcp/
├── install.sh              # One-command installer
├── quickinstall.sh         # curl | bash installer
├── server.py               # MCP server (25 tools)
├── dashboard.py            # TUI dashboard
├── vision.py               # Florence-2 vision engine
├── ocr_engine.py           # GLM-OCR text extraction
├── screen_capture.py       # Screenshot via mss
├── ui_controller.py        # Mouse/keyboard actions
├── element_finder.py       # Smart find + click
├── safety.py               # Rate limits, audit log
├── config.py               # Settings
├── requirements.txt        # Python deps
├── requirements-tui.txt    # TUI deps
├── mcp_config.json         # OpenClaw config
├── scripts/
│   ├── setup_deps.sh       # System packages
│   ├── setup_python.sh     # Venv + pip with progress
│   ├── detect_gpu.sh       # GPU detection
│   ├── download_models.sh  # Model downloader
│   ├── setup_mcp.sh        # MCP config generator
│   ├── setup_service.sh    # Systemd service
│   ├── health_check.sh     # Status checker
│   └── uninstall.sh        # Cleanup
├── tests/
│   └── test_all.py
└── models/                 # AI models (downloaded)
```

## 📦 Requirements

- Python 3.10+
- Linux (x11) / macOS / Windows
- GPU optional (NVIDIA CUDA recommended)

## License

MIT
