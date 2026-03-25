#!/usr/bin/env python3
"""UI Agent MCP — Interactive TUI Dashboard"""

import time, json, subprocess, threading
from pathlib import Path
import pytermgui as ptg

BASE = Path(__file__).parent
ENV = BASE / ".env"
LOG = BASE / "logs" / "actions.jsonl"


def cmd(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return r.stdout.strip() or r.stderr.strip()
    except:
        return ""


def gpu():
    o = cmd("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null")
    if o and "fail" not in o.lower():
        p = o.split(", ")
        if len(p) >= 3:
            return True, p[0], f"{p[1]}/{p[2]}"
    return False, "None", "N/A"


def models():
    m = BASE / "models"
    def sz(p):
        if not p.exists(): return "0MB"
        return f"{sum(f.stat().st_size for f in p.rglob('*') if f.is_file())/(1024*1024):.0f}MB"
    return (m / "Florence-2-base").exists(), (m / "GLM-OCR").exists(), sz(m / "Florence-2-base"), sz(m / "GLM-OCR")


def stats():
    if not LOG.exists():
        return 0, 0, 0, "Never"
    ls = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    err = sum(1 for l in ls if "error" in l.lower())
    hr = sum(1 for l in ls if (lambda x: json.loads(x).get("timestamp", 0) if x else 0)(l) > time.time() - 3600)
    last = "Never"
    if ls:
        try: last = json.loads(ls[-1]).get("time_iso", "?")
        except: pass
    return len(ls), hr, err, last


def recent_logs(n=5):
    if not LOG.exists(): return "No logs"
    ls = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    if not ls: return "No logs"
    out = []
    for l in ls[-n:]:
        try:
            e = json.loads(l)
            out.append(f"{e.get('time_iso','?')[:19]} | {e.get('action','?')}")
        except: pass
    return "\n".join(out) if out else "No logs"


def main():
    g_ok, g_name, g_mem = gpu()
    fl_ok, glm_ok, fl_s, glm_s = models()
    tot, hr, err, last = stats()

    gi = "●" if g_ok else "○"
    fi = "✓" if fl_ok else "✗"
    li = "✓" if glm_ok else "✗"

    dev = "CPU"
    if ENV.exists():
        for ln in ENV.read_text().split("\n"):
            if ln.startswith("DEVICE="): dev = ln.split("=")[1].strip().upper()

    srv = [None]
    status = ptg.Label("[dim]Ready[/]")

    # ── Server start with live logs ──
    log_text = ptg.Label("[dim]Click Start Server to see logs[/]")

    def start_srv():
        log_text.value = "[dim]Starting...[/]\n"
        status.value = "[yellow]Starting...[/]"

        def run():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            srv[0] = proc
            status.value = "[green]● Running[/]"
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    log_text.value += f"[dim]{ln.rstrip()}[/]\n"
                if len(log_text.value) > 4000:
                    log_text.value = log_text.value[-2000:]

        threading.Thread(target=run, daemon=True).start()

    def stop_srv():
        cmd("pkill -f 'python server.py' || true")
        status.value = "[dim]● Stopped[/]"

    def do_health():
        status.value = "[yellow]Checking...[/]"
        def run():
            cmd(f"cd {BASE} && bash scripts/health_check.sh")
            status.value = "[green]Done ✓[/]"
        threading.Thread(target=run, daemon=True).start()

    # ── Build windows ──
    with ptg.WindowManager() as mgr:

        # Header
        mgr.add(ptg.Window(
            "[bold gold1]╔══ UI Agent MCP Dashboard ══╗[/]",
            "[dim]Florence-2 Vision + GLM-OCR (Z.AI) — Terminal UI[/]",
            box="DOUBLE",
        ))

        # System + Config
        mgr.add(ptg.Window(
            f"[bold deep_sky_blue1]System[/]",
            f"  {gi} GPU: {g_name}",
            f"      Memory: {g_mem}",
            f"  {fi} Florence-2: {'OK' if fl_ok else 'Missing'} ({fl_s})",
            f"  {li} GLM-OCR: {'OK' if glm_ok else 'Missing'} ({glm_s})",
            f"  Device: {dev}",
            f"",
            f"  Actions: {tot} | {hr}/hr | {err} err",
            f"  Last: {last}",
            box="DOUBLE",
        ))

        # Actions
        mgr.add(ptg.Window(
            "[bold hot_pink]Actions[/]",
            ptg.Button("🔍 Health Check", on_click=lambda _: do_health()),
            ptg.Button("▶ Start Server", on_click=lambda _: start_srv()),
            ptg.Button("⏹ Stop Server", on_click=lambda _: stop_srv()),
            ptg.Button("📋 Refresh Logs", on_click=lambda _: setattr(log_text, "value", f"[dim]{recent_logs()}[/]")),
            "",
            status,
            box="DOUBLE",
        ))

        # Server Logs
        mgr.add(ptg.Window(
            "[bold lime_green]Server Logs[/]",
            log_text,
            box="DOUBLE",
        ))

        @mgr.bind("q", "quit")
        def _():
            if srv[0]:
                srv[0].terminate()
            mgr.stop()

    print("\n👋 Dashboard closed\n")


if __name__ == "__main__":
    main()
