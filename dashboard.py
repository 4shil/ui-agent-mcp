#!/usr/bin/env python3
"""
UI Agent MCP — TUI Dashboard v2
Beautiful, interactive terminal UI with live monitoring.
"""

import os, sys, time, json, subprocess, threading, shutil
from pathlib import Path
from datetime import datetime
from collections import deque

import pytermgui as ptg

# ──── Paths ────
BASE = Path(__file__).parent
ENV = BASE / ".env"
LOG = BASE / "logs" / "actions.jsonl"

# ──── Theme ────
C = {
    "gold": "bold gold1",
    "blue": "bold deep_sky_blue1",
    "green": "bold lime_green",
    "red": "bold red",
    "pink": "bold hot_pink",
    "cyan": "bold cyan",
    "dim": "dim",
    "white": "bold white",
}

# ──── Helpers ────
def sh(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except: return ""

def gpu_info():
    o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
    if o and "fail" not in o.lower():
        p = o.split(", ")
        if len(p) >= 5:
            return {"ok": True, "name": p[0], "used": p[1], "total": p[2], "util": p[3], "temp": p[4]}
    return {"ok": False, "name": "N/A", "used": "0", "total": "0", "util": "0", "temp": "0"}

def model_status():
    m = BASE / "models"
    def info(name, path):
        p = path / name
        if p.exists():
            sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / (1024**3)
            return True, f"{sz:.1f}GB"
        return False, "0GB"
    fl = info("Florence-2-base", m)
    glm = info("GLM-OCR", m)
    return {"florence": {"ok": fl[0], "size": fl[1]}, "glm": {"ok": glm[0], "size": glm[1]}}

def action_stats():
    if not LOG.exists():
        return {"total": 0, "hr": 0, "err": 0, "last": "Never", "top_actions": []}
    lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    total = len(lines)
    errors = 0
    actions = {}
    one_hr = time.time() - 3600
    hr_count = 0
    for l in lines:
        try:
            e = json.loads(l)
            if e.get("status") == "error": errors += 1
            a = e.get("action", "?")
            actions[a] = actions.get(a, 0) + 1
            if e.get("timestamp", 0) > one_hr: hr_count += 1
        except: pass
    top = sorted(actions.items(), key=lambda x: -x[1])[:5]
    last = "Never"
    if lines:
        try: last = json.loads(lines[-1]).get("time_iso", "?")
        except: pass
    return {"total": total, "hr": hr_count, "err": errors, "last": last, "top_actions": top}

def recent_logs(n=8):
    if not LOG.exists(): return []
    lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    out = []
    for l in lines[-n:]:
        try: out.append(json.loads(l))
        except: pass
    return list(reversed(out))

def sys_info():
    """Get system information."""
    cpu = sh("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'") or "0"
    ram = sh("free -h | awk '/Mem:/{print $3 \"/\" $2}'") or "N/A"
    uptime = sh("uptime -p") or "N/A"
    return {"cpu": f"{float(cpu):.1f}%" if cpu.replace('.','').isdigit() else "0%", "ram": ram, "uptime": uptime}


# ═══════════════════════════════════════════════════════════
#  PROGRESS BAR HELPER
# ═══════════════════════════════════════════════════════════
def progress_bar(pct, width=20, fill_char="█", empty_char="░"):
    filled = int(pct / 100 * width)
    bar = fill_char * filled + empty_char * (width - filled)
    if pct > 75: color = "lime_green"
    elif pct > 50: color = "gold1"
    elif pct > 25: color = "orange1"
    else: color = "red"
    return f"[{color}]{bar}[/] {pct:.0f}%"


# ═══════════════════════════════════════════════════════════
#  DASHBOARD v2
# ═══════════════════════════════════════════════════════════

def build_dashboard():
    """Main dashboard builder."""

    # ── Shared state ──
    state = {
        "server_proc": None,
        "server_running": False,
        "logs": deque(maxlen=100),
        "status": "[dim]Ready[/]",
        "log_refresh": True,
    }

    # ── Status labels (will be updated live) ──
    gpu_lb = ptg.Label("")
    model_lb = ptg.Label("")
    sys_lb = ptg.Label("")
    action_lb = ptg.Label("")
    status_lb = ptg.Label("[dim]Ready[/]")
    log_lb = ptg.Label("")
    log_scroll = [0]

    # ── Update functions ──
    def update_gpu():
        g = gpu_info()
        if g["ok"]:
            bar = progress_bar(float(g["util"].replace("%","")))
            gpu_lb.value = (
                f"[{C['green']}]● GPU: {g['name']}[/]\n"
                f"  Util: {bar}\n"
                f"  Mem: {g['used']}/{g['total']}  Temp: {g['temp']}°C"
            )
        else:
            gpu_lb.value = f"[{C['dim']}]○ No GPU detected[/]\n  Using CPU mode"

    def update_models():
        m = model_status()
        f = m["florence"]
        g = m["glm"]
        fi = f"[{C['green']}]✓" if f["ok"] else f"[{C['red']}]✗"
        gi = f"[{C['green']}]✓" if g["ok"] else f"[{C['red']}]✗"
        model_lb.value = (
            f"{fi} Florence-2: {'Ready' if f['ok'] else 'Download'} ({f['size']})[/]\n"
            f"{gi} GLM-OCR: {'Ready' if g['ok'] else 'Download'} ({g['size']})[/]"
        )

    def update_sys():
        s = sys_info()
        cpu_bar = progress_bar(float(s["cpu"].replace("%","")))
        sys_lb.value = (
            f"CPU: {cpu_bar}\n"
            f"RAM: {s['ram']}\n"
            f"Up: {s['uptime']}"
        )

    def update_actions():
        a = action_stats()
        top3 = "\n".join(f"  {name}: {cnt}" for name, cnt in a["top_actions"][:3]) or "  No actions yet"
        action_lb.value = (
            f"Total: {a['total']} | Hour: {a['hr']} | Err: {a['err']}\n"
            f"Last: {a['last'][:19] if a['last'] != 'Never' else 'Never'}\n"
            f"Top:\n{top3}"
        )

    def update_log_display():
        logs = recent_logs(10)
        if not logs:
            log_lb.value = "[dim]No actions logged yet[/]"
            return
        lines = []
        for l in logs:
            t = l.get("time_iso", "?")[:19]
            a = l.get("action", "?")
            s = l.get("status", "?")
            icon = f"[{C['green']}]✓" if s == "ok" else f"[{C['red']}]✗"
            lines.append(f"{icon} {t[11:]} {a}[/]")
        log_lb.value = "\n".join(lines)

    def full_refresh():
        update_gpu()
        update_models()
        update_sys()
        update_actions()
        update_log_display()

    # ── Background updater ──
    def bg_updater():
        while state["log_refresh"]:
            time.sleep(3)
            try:
                full_refresh()
            except: pass

    threading.Thread(target=bg_updater, daemon=True).start()

    # ── Actions ──
    def do_health():
        status_lb.value = f"[{C['gold']}]Running health check...[/]"
        def t():
            sh(f"cd {BASE} && bash scripts/health_check.sh")
            status_lb.value = f"[{C['green']}]Health check complete ✓[/]"
            full_refresh()
        threading.Thread(target=t, daemon=True).start()

    def do_start():
        status_lb.value = f"[{C['gold']}]Starting MCP server...[/]"
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            state["server_proc"] = proc
            state["server_running"] = True
            status_lb.value = f"[{C['green']}]● MCP Server Running[/]"
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    state["logs"].append(ln.rstrip())
                    if len(state["logs"]) > 50:
                        state["logs"].popleft()
                    log_lb.value = "\n".join(f"[dim]{l}[/]" for l in list(state["logs"])[-15:])
        threading.Thread(target=t, daemon=True).start()

    def do_stop():
        sh("pkill -f 'python server.py' || true")
        state["server_running"] = False
        status_lb.value = f"[{C['dim']}]● Server Stopped[/]"

    def do_download():
        status_lb.value = f"[{C['gold']}]Downloading models (~2.3GB, this takes a while)...[/]"
        def t():
            sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh")
            status_lb.value = f"[{C['green']}]Models downloaded ✓[/]"
            full_refresh()
        threading.Thread(target=t, daemon=True).start()

    def do_logs():
        update_log_display()
        status_lb.value = f"[{C['cyan']}]Logs refreshed[/]"

    def do_clear_logs():
        state["logs"].clear()
        log_lb.value = f"[dim]Logs cleared[/]"

    # ── Create windows ──
    windows = []

    # 1. Header
    windows.append(ptg.Window(
        f"[{C['gold']}]╔══════════════════════════════════════════════════╗[/]",
        f"[{C['gold']}]║   🖥️  UI Agent MCP — Dashboard v2                ║[/]",
        f"[{C['gold']}]║   Florence-2 + GLM-OCR (Z.AI) • PyTermGUI       ║[/]",
        f"[{C['gold']}]╚══════════════════════════════════════════════════╝[/]",
        box="EMPTY",
    ))

    # 2. GPU & System
    windows.append(ptg.Window(
        f"[{C['blue']}]━━━ Hardware ━━━[/]",
        gpu_lb,
        "",
        f"[{C['cyan']}]━━━ System ━━━[/]",
        sys_lb,
        box="DOUBLE",
        width=50,
    ))

    # 3. Models
    windows.append(ptg.Window(
        f"[{C['pink']}]━━━ AI Models ━━━[/]",
        model_lb,
        "",
        ptg.Button("📥 Download Models", on_click=lambda _: do_download()),
        box="DOUBLE",
        width=50,
    ))

    # 4. Action Stats
    windows.append(ptg.Window(
        f"[{C['green']}]━━━ Action Statistics ━━━[/]",
        action_lb,
        box="DOUBLE",
        width=50,
    ))

    # 5. Controls
    windows.append(ptg.Window(
        f"[{C['gold']}]━━━ Server Controls ━━━[/]",
        "",
        ptg.Button("▶  Start Server", on_click=lambda _: do_start()),
        ptg.Button("⏹  Stop Server", on_click=lambda _: do_stop()),
        ptg.Button("🔍 Health Check", on_click=lambda _: do_health()),
        ptg.Button("📋 Refresh Logs", on_click=lambda _: do_logs()),
        ptg.Button("🗑  Clear Log View", on_click=lambda _: do_clear_logs()),
        "",
        status_lb,
        box="DOUBLE",
        width=50,
    ))

    # 6. Live Server Log
    windows.append(ptg.Window(
        f"[{C['green']}]━━━ Live Server Log ━━━[/]",
        log_lb,
        box="DOUBLE",
    ))

    # ── Build layout ──
    mgr = ptg.WindowManager()

    # Header (full width)
    mgr.add(windows[0])

    # Two-column rows
    row1 = ptg.Splitter(windows[1], windows[2])
    row2 = ptg.Splitter(windows[3], windows[4])
    mgr.add(row1)
    mgr.add(row2)

    # Log panel (full width)
    mgr.add(windows[5])

    # ── Keybindings ──
    def quit_fn():
        state["log_refresh"] = False
        if state["server_proc"]:
            state["server_proc"].terminate()
        mgr.stop()

    mgr.bind("q", "Quit", quit_fn)
    mgr.bind("r", "Refresh", lambda: full_refresh())

    # ── Initial data load ──
    full_refresh()

    return mgr


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════

def main():
    print(f"\n🚀 Loading UI Agent MCP Dashboard v2...\n")
    mgr = build_dashboard()
    mgr.run()
    print("\n👋 Dashboard closed\n")


if __name__ == "__main__":
    main()
