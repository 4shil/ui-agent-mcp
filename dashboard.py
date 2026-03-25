#!/usr/bin/env python3
"""
UI Agent MCP — Interactive TUI Dashboard
"""

import os
import sys
import time
import json
import subprocess
import threading
from pathlib import Path

import pytermgui as ptg

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
LOG_FILE = BASE_DIR / "logs" / "actions.jsonl"


def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return str(e)

def check_gpu():
    out = run_cmd("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null")
    if out and "failed" not in out.lower():
        p = out.split(", ")
        if len(p) >= 4:
            return {"available": True, "name": p[0], "memory": f"{p[1]}/{p[2]}", "util": p[3]}
    return {"available": False, "name": "None", "memory": "N/A", "util": "N/A"}

def get_models():
    mdir = BASE_DIR / "models"
    def sz(p):
        if not p.exists(): return "0MB"
        t = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return f"{t/(1024*1024):.0f}MB"
    return {
        "florence": (mdir / "Florence-2-base").exists(),
        "glm": (mdir / "GLM-OCR").exists(),
        "florence_sz": sz(mdir / "Florence-2-base"),
        "glm_sz": sz(mdir / "GLM-OCR"),
    }

def get_stats():
    if not LOG_FILE.exists():
        return {"total": 0, "last_hour": 0, "errors": 0, "last": "Never"}
    lines = LOG_FILE.read_text().strip().split("\n") if LOG_FILE.read_text().strip() else []
    errors = sum(1 for l in lines if "error" in l.lower())
    one_h = time.time() - 3600
    lh = sum(1 for l in lines if try_json_ts(l) > one_h)
    last = "Never"
    if lines:
        try: last = json.loads(lines[-1]).get("time_iso", "?")
        except: pass
    return {"total": len(lines), "last_hour": lh, "errors": errors, "last": last}

def try_json_ts(l):
    try: return json.loads(l).get("timestamp", 0)
    except: return 0

def get_logs(n=8):
    if not LOG_FILE.exists(): return []
    lines = LOG_FILE.read_text().strip().split("\n") if LOG_FILE.read_text().strip() else []
    out = []
    for l in lines[-n:]:
        try: out.append(json.loads(l))
        except: pass
    return list(reversed(out))


def main():
    server_proc = [None]

    with ptg.WindowManager() as manager:
        # ──── Header ────
        header = ptg.Container(
            ptg.Label("[bold gold1]UI Agent MCP — Dashboard[/]", parent_align=ptg.HorizontalAlignment.CENTER),
            ptg.Label("[dim]Florence-2 Vision + GLM-OCR (Z.AI)[/]", parent_align=ptg.HorizontalAlignment.CENTER),
            box="DOUBLE",
        )

        # ──── System Status ────
        gpu = check_gpu()
        mdl = get_models()
        stats = get_stats()

        gpu_icon = "[green]●[/]" if gpu["available"] else "[dim]○[/]"
        fl_icon = "[green]✓[/]" if mdl["florence"] else "[red]✗[/]"
        glm_icon = "[green]✓[/]" if mdl["glm"] else "[red]✗[/]"

        sys_card = ptg.Container(
            ptg.Label("[bold deep_sky_blue1]System[/]"),
            ptg.Label("─" * 40),
            ptg.Label(f"{gpu_icon} GPU: {gpu['name']}"),
            ptg.Label(f"   Mem: {gpu['memory']}  Util: {gpu['util']}"),
            ptg.Label(""),
            ptg.Label(f"{fl_icon} Florence-2: {'OK' if mdl['florence'] else 'Missing'} ({mdl['florence_sz']})"),
            ptg.Label(f"{glm_icon} GLM-OCR: {'OK' if mdl['glm'] else 'Missing'} ({mdl['glm_sz']})"),
            ptg.Label(""),
            ptg.Label(f"Actions: {stats['total']} | {stats['last_hour']}/hr | {stats['errors']} err"),
            ptg.Label(f"Last: {stats['last']}"),
            box="SINGLE",
            width=42,
        )

        # ──── Quick Actions ────
        status_lb = ptg.Label("[dim]Ready[/]")

        def do_health():
            status_lb.value = "[yellow]Running...[/]"
            def t():
                run_cmd(f"cd {BASE_DIR} && bash scripts/health_check.sh")
                status_lb.value = "[green]Done ✓[/]"
            threading.Thread(target=t, daemon=True).start()

        def do_start():
            status_lb.value = "[yellow]Starting server...[/]"
            def t():
                proc = subprocess.Popen(
                    ["bash", "-c", f"cd {BASE_DIR} && source .venv/bin/activate && python server.py"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                server_proc[0] = proc
                status_lb.value = "[green]● Server Running[/]"
            threading.Thread(target=t, daemon=True).start()

        def do_stop():
            run_cmd("pkill -f 'python server.py' || true")
            status_lb.value = "[dim]● Stopped[/]"

        def do_logs():
            logs = get_logs(6)
            if not logs:
                status_lb.value = "[dim]No logs yet[/]"
                return
            txt = "\n".join(f"[dim]{l.get('time_iso','?')[:19]} | {l.get('action','?')}[/]" for l in logs)
            status_lb.value = txt

        actions_card = ptg.Container(
            ptg.Label("[bold hot_pink]Actions[/]"),
            ptg.Label("─" * 40),
            ptg.Button("🔍 Health Check", on_click=lambda _: do_health()),
            ptg.Button("▶ Start Server", on_click=lambda _: do_start()),
            ptg.Button("⏹ Stop Server", on_click=lambda _: do_stop()),
            ptg.Button("📋 Recent Logs", on_click=lambda _: do_logs()),
            ptg.Label("─" * 40),
            status_lb,
            box="SINGLE",
            width=42,
        )

        # ──── Server Log Panel ────
        log_lb = ptg.Label("[dim]Click Start Server to see logs...[/]")

        server_card = ptg.Container(
            ptg.Label("[bold lime_green]Server Logs[/]"),
            ptg.Label("─" * 80),
            log_lb,
            box="SINGLE",
        )

        def start_with_log():
            log_lb.value = "[dim]Starting...[/]\n"
            status_lb.value = "[yellow]Starting...[/]"
            def t():
                proc = subprocess.Popen(
                    ["bash", "-c", f"cd {BASE_DIR} && source .venv/bin/activate && python server.py"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )
                server_proc[0] = proc
                status_lb.value = "[green]● Running[/]"
                for line in iter(proc.stdout.readline, ''):
                    if line:
                        log_lb.value += f"[dim]{line.rstrip()}[/]\n"
                    if len(log_lb.value) > 3000:
                        log_lb.value = log_lb.value[-1500:]
            threading.Thread(target=t, daemon=True).start()

        # Override start button
        actions_card += ptg.Button("▶ Start + Logs", on_click=lambda _: start_with_log())

        # ──── Config Card ────
        dev = "CPU"
        if ENV_FILE.exists():
            for ln in ENV_FILE.read_text().split("\n"):
                if ln.startswith("DEVICE="):
                    dev = ln.split("=")[1].strip().upper()

        cfg_card = ptg.Container(
            ptg.Label("[bold yellow]Config[/]"),
            ptg.Label("─" * 40),
            ptg.Label(f"Device: [bold]{dev}[/]"),
            ptg.Label("Vision: [bold]florence-2-base[/]"),
            ptg.Label("OCR: [bold]GLM-OCR[/]"),
            ptg.Label(f"Path: [dim]{BASE_DIR}[/]"),
            box="SINGLE",
            width=42,
        )

        # ──── Footer ────
        footer = ptg.Container(
            ptg.Label("[dim]q = quit | r = refresh[/]", parent_align=ptg.HorizontalAlignment.CENTER),
            box="EMPTY",
        )

        # ──── Layout ────
        top_row = ptg.Splitter(sys_card, actions_card)
        bottom_row = ptg.Splitter(server_card, cfg_card)

        manager.layout.add_slot("header")
        manager.layout.add_slot("body")
        manager.layout.add_slot("footer", size=3)

        manager.add(header, slot="header")
        manager.add(ptg.Container(top_row, box="EMPTY"), slot="body")
        manager.add(ptg.Container(bottom_row, box="EMPTY"), slot="body")
        manager.add(footer, slot="footer")

        @manager.bind("q", "quit")
        def _():
            if server_proc[0]:
                server_proc[0].terminate()
            manager.stop()

        @manager.bind("r", "refresh")
        def _():
            manager.toast("[bold]Refreshed[/]")

    print("\n👋 Dashboard closed\n")


if __name__ == "__main__":
    main()
