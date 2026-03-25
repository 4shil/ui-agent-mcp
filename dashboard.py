#!/usr/bin/env python3
"""
UI Agent MCP — Interactive TUI Dashboard
Beautiful terminal UI for managing your UI Agent MCP server.
"""

import os
import sys
import time
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import pytermgui as ptg

# ──── Paths ────
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
LOG_FILE = BASE_DIR / "logs" / "actions.jsonl"
STATE_FILE = BASE_DIR / ".install_state"

# ──── Colors ────
COLORS = {
    "primary": "bold #FFCB47",      # Gold
    "secondary": "bold #369EFF",    # Blue
    "success": "bold #47FF87",      # Green
    "danger": "bold #FF4757",       # Red
    "muted": "dim #888888",         # Gray
    "accent": "bold #FF6B9D",       # Pink
    "white": "bold #FFFFFF",
    "bg_dark": "#1A1A2E",
    "bg_card": "#16213E",
}

# ──── Helpers ────

def run_cmd(cmd: str, timeout: int = 10) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return str(e)

def check_gpu() -> dict:
    """Check GPU status."""
    output = run_cmd("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null")
    if output and "failed" not in output.lower():
        parts = output.split(", ")
        if len(parts) >= 4:
            return {
                "available": True,
                "name": parts[0],
                "memory": f"{parts[1]}/{parts[2]}",
                "util": parts[3],
            }
    return {"available": False, "name": "None", "memory": "N/A", "util": "N/A"}

def get_model_status() -> dict:
    """Check which models are downloaded."""
    models_dir = BASE_DIR / "models"
    florence = models_dir / "Florence-2-base"
    glm = models_dir / "GLM-OCR"

    def size_mb(path):
        if not path.exists():
            return 0
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return total / (1024 * 1024)

    return {
        "florence": {"exists": florence.exists(), "size": f"{size_mb(florence):.0f}MB"},
        "glm_ocr": {"exists": glm.exists(), "size": f"{size_mb(glm):.0f}MB"},
    }

def get_action_stats() -> dict:
    """Read action log for stats."""
    if not LOG_FILE.exists():
        return {"total": 0, "last_hour": 0, "errors": 0, "last_action": "Never"}

    lines = LOG_FILE.read_text().strip().split("\n") if LOG_FILE.read_text().strip() else []
    total = len(lines)
    errors = sum(1 for l in lines if '"error"' in l or '"status": "error"' in l)

    one_hour_ago = time.time() - 3600
    last_hour = 0
    for l in lines:
        try:
            entry = json.loads(l)
            if entry.get("timestamp", 0) > one_hour_ago:
                last_hour += 1
        except:
            pass

    last_action = "Never"
    if lines:
        try:
            last = json.loads(lines[-1])
            last_action = last.get("time_iso", "Unknown")
        except:
            last_action = "Unknown"

    return {"total": total, "last_hour": last_hour, "errors": errors, "last_action": last_action}

def get_recent_logs(n: int = 10) -> list:
    """Get recent log entries."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text().strip().split("\n") if LOG_FILE.read_text().strip() else []
    entries = []
    for l in lines[-n:]:
        try:
            entries.append(json.loads(l))
        except:
            pass
    return list(reversed(entries))


# ════════════════════════════════════════════════════════════
#  BUILD UI
# ════════════════════════════════════════════════════════════

def build_header() -> ptg.Container:
    """Build animated header."""
    return ptg.Container(
        ptg.Label(
            "[bold #FFCB47]╔══════════════════════════════════════════════════════╗[/]",
            parent_align=ptg.HorizontalAlignment.CENTER,
        ),
        ptg.Label(
            "[bold #FFCB47]║    🖥️  UI Agent MCP — Dashboard                     ║[/]",
            parent_align=ptg.HorizontalAlignment.CENTER,
        ),
        ptg.Label(
            "[bold #FFCB47]║    Vision: Florence-2 | OCR: GLM-OCR (Z.AI)       ║[/]",
            parent_align=ptg.HorizontalAlignment.CENTER,
        ),
        ptg.Label(
            "[bold #FFCB47]╚══════════════════════════════════════════════════════╝[/]",
            parent_align=ptg.HorizontalAlignment.CENTER,
        ),
        box="EMPTY",
    )

def build_system_status() -> ptg.Container:
    """Build system status card."""
    gpu = check_gpu()
    models = get_model_status()
    stats = get_action_stats()

    gpu_icon = "🟢" if gpu["available"] else "⚪"
    florence_icon = "✅" if models["florence"]["exists"] else "❌"
    glm_icon = "✅" if models["glm_ocr"]["exists"] else "❌"

    return ptg.Container(
        ptg.Label(f"[bold #369EFF]System Status[/]"),
        ptg.HorizontalRule(),
        ptg.Label(f"{gpu_icon} GPU: {gpu['name']}"),
        ptg.Label(f"   Memory: {gpu['memory']}  Util: {gpu['util']}"),
        ptg.Label(""),
        ptg.Label(f"{florence_icon} Florence-2: {'Downloaded' if models['florence']['exists'] else 'Missing'} ({models['florence']['size']})"),
        ptg.Label(f"{glm_icon} GLM-OCR: {'Downloaded' if models['glm_ocr']['exists'] else 'Missing'} ({models['glm_ocr']['size']})"),
        ptg.Label(""),
        ptg.Label(f"📊 Actions: {stats['total']} total | {stats['last_hour']} this hour | {stats['errors']} errors"),
        ptg.Label(f"🕐 Last: {stats['last_action']}"),
        box="DOUBLE",
        width=50,
    )

def build_quick_actions(manager: ptg.WindowManager) -> ptg.Container:
    """Build quick actions card with interactive buttons."""

    status_label = ptg.Label("[dim]Ready[/]")

    def on_health_check():
        status_label.value = "[dim yellow]Running health check...[/]"
        def run():
            output = run_cmd(f"cd {BASE_DIR} && bash scripts/health_check.sh")
            status_label.value = f"[dim green]Health check done[/]"
        threading.Thread(target=run, daemon=True).start()

    def on_start_server():
        status_label.value = "[dim yellow]Starting MCP server...[/]"
        def run():
            output = run_cmd(f"cd {BASE_DIR} && source .venv/bin/activate && python server.py &", timeout=2)
            status_label.value = f"[dim green]Server starting...[/]"
        threading.Thread(target=run, daemon=True).start()

    def on_download_models():
        status_label.value = "[dim yellow]Downloading models (this takes a while)...[/]"
        def run():
            output = run_cmd(f"cd {BASE_DIR} && source .venv/bin/activate && python scripts/download_models.sh", timeout=300)
            status_label.value = f"[dim green]Models download complete[/]"
        threading.Thread(target=run, daemon=True).start()

    def on_view_logs():
        logs = get_recent_logs(5)
        log_text = "\n".join([f"  {e.get('time_iso','?')[:19]} | {e.get('action','?')}" for e in logs]) or "  No logs yet"
        status_label.value = f"[dim]{log_text}[/]"

    def on_refresh(manager):
        manager.toast("[bold]Refreshing...[/]")

    return ptg.Container(
        ptg.Label("[bold #FF6B9D]Quick Actions[/]"),
        ptg.HorizontalRule(),
        ptg.Button("🔍 Health Check", on_click=lambda _: on_health_check()),
        ptg.Button("🚀 Start Server", on_click=lambda _: on_start_server()),
        ptg.Button("📥 Download Models", on_click=lambda _: on_download_models()),
        ptg.Button("📋 View Recent Logs", on_click=lambda _: on_view_logs()),
        ptg.Button("🔄 Refresh", on_click=lambda _: on_refresh(manager)),
        ptg.HorizontalRule(),
        status_label,
        box="DOUBLE",
        width=50,
    )

def build_server_controls(manager: ptg.WindowManager) -> ptg.Container:
    """Build server control panel."""
    server_status = ptg.Label("[dim]Not running[/]")
    log_area = ptg.Label("[dim]Logs will appear here...[/]")

    def start_server():
        server_status.value = "[bold green]● Running[/]"
        log_area.value = "[dim]Starting server...\n"
        def run():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE_DIR} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                log_area.value += f"  {line.strip()}\n"
                if len(log_area.value) > 2000:
                    log_area.value = log_area.value[-1000:]
        threading.Thread(target=run, daemon=True).start()

    def stop_server():
        run_cmd("pkill -f 'python server.py' || true")
        server_status.value = "[dim]Stopped[/]"
        log_area.value += "\n[dim]Server stopped[/]"

    def restart_server():
        stop_server()
        time.sleep(1)
        start_server()

    return ptg.Container(
        ptg.Label("[bold #369EFF]Server Control[/]"),
        ptg.HorizontalRule(),
        server_status,
        ptg.Splitter(
            ptg.Button("▶ Start", on_click=lambda _: start_server()),
            ptg.Button("⏹ Stop", on_click=lambda _: stop_server()),
            ptg.Button("🔄 Restart", on_click=lambda _: restart_server()),
        ),
        ptg.Label("[dim]── Logs ──[/]"),
        log_area,
        box="DOUBLE",
    )

def build_config_display() -> ptg.Container:
    """Show current configuration."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().split("\n"):
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    device = env.get("DEVICE", "cpu").upper()
    vision = env.get("VISION_MODEL", "florence-2-base")

    return ptg.Container(
        ptg.Label("[bold #47FF87]Configuration[/]"),
        ptg.HorizontalRule(),
        ptg.Label(f"🖥️  Device: [bold]{device}[/]"),
        ptg.Label(f"👁️  Vision Model: [bold]{vision}[/]"),
        ptg.Label(f"🔤 OCR Model: [bold]GLM-OCR (Z.AI)[/]"),
        ptg.Label(f"📁 Project: [dim]{BASE_DIR}[/]"),
        box="DOUBLE",
        width=50,
    )

def build_footer() -> ptg.Container:
    """Build footer."""
    return ptg.Container(
        ptg.Label(
            "[dim]UI Agent MCP v1.0.0 | Press Ctrl+C to quit | ESC to go back[/]",
            parent_align=ptg.HorizontalAlignment.CENTER,
        ),
        box="EMPTY",
    )


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════

def main():
    with ptg.WindowManager() as manager:
        # Set dark theme
        ptg.Colorsystem().set_default("border", "#369EFF")
        ptg.Colorsystem().set_default("corner", "#FFCB47")

        # Layout: Top to bottom
        manager.layout.add_slot("header")
        manager.layout.add_slot("body", size=0.7)
        manager.layout.add_slot("footer", size=3)

        # Header
        manager.add(build_header(), slot="header")

        # Body: Left column + Right column
        left = build_system_status()
        right = build_quick_actions(manager)
        server = build_server_controls(manager)
        config = build_config_display()

        body = ptg.Splitter(left, right)
        body2 = ptg.Splitter(server, config)

        manager.add(ptg.Container(body, box="EMPTY"), slot="body")
        manager.add(ptg.Container(body2, box="EMPTY"), slot="body")

        # Footer
        manager.add(build_footer(), slot="footer")

        # Keybindings
        @manager.bind("q", "quit")
        def _():
            manager.stop()

        @manager.bind("r", "refresh")
        def _():
            manager.toast("[bold]Refreshing dashboard...[/]")

    print("\n👋 Thanks for using UI Agent MCP!\n")


if __name__ == "__main__":
    print("\n🚀 Starting UI Agent MCP Dashboard...\n")
    main()
