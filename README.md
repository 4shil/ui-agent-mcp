# ui-agent-mcp

MCP server that gives AI agents complete UI access — see screens, understand elements, click, type, scroll, drag.

## Models

| Model | Purpose | Source |
|-------|---------|--------|
| Florence-2 | UI understanding, element detection | `microsoft/Florence-2-base` |
| GLM-OCR | Text, table, formula extraction | `zai-org/GLM-OCR` |

## Architecture

```
Agent → MCP Protocol → MCP Server
                         ├── Screen Capture (mss)
                         ├── Vision (Florence-2)
                         ├── OCR (GLM-OCR)
                         └── Actions (pyautogui)
```

## Install

```bash
pip install -r requirements.txt
# Models auto-download on first run
```

## Run

```bash
python server.py
```

## MCP Config (OpenClaw)

```json
{
  "mcpServers": {
    "ui-agent": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/home/ashil/openclaw/workspace/ui-agent-mcp"
    }
  }
}
```

## Tools

- `screenshot()` — capture screen
- `describe_ui()` — AI describes screen
- `locate_element()` — find UI element
- `read_text()` — OCR text extraction
- `click()`, `type()`, `scroll()`, `drag()` — UI actions
- `find_and_click()` — locate + click in one step
- `open_app()`, `close_app()` — launch apps

## License

MIT
