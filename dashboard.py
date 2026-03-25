#!/usr/bin/env python3
"""UI Agent MCP — Interactive TUI Dashboard"""

import os, sys, time, json, subprocess, threading
from pathlib import Path
import pytermgui as ptg

BASE = Path(__file__).parent
ENV = BASE / ".env"
LOG = BASE / "logs" / "actions.jsonl"


def cmd(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return r.stdout.strip() or r.stderr.strip()
    except: return ""

def gpu():
    o = cmd("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null")
    if o and "failed" not in o.lower():
        p = o.split(", ")
        if len(p) >= 3: return {"ok": True, "name": p[0], "mem": f"{p[1]}/{p[2]}"}
    return {"ok": False, "name": "None", "mem": "N/A"}

def models():
    m = BASE / "models"
    def sz(p):
        if not p.exists(): return "0MB"
        return f"{sum(f.stat().st_size for f in p.rglob('*') if f.is_file())/(1024*1024):.0f}MB"
    return {
        "fl": (m / "Florence-2-base").exists(),
        "glm": (m / "GLM-OCR").exists(),
        "fl_s": sz(m / "Florence-2-base"),
        "glm_s": sz(m / "GLM-OCR"),
    }

def stats():
    if not LOG.exists(): return {"tot": 0, "hr": 0, "err": 0, "last": "Never"}
    ls = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    err = sum(1 for l in ls if "error" in l.lower())
    now = time.time()
    hr = 0
    for l in ls:
        try:
            if json.loads(l).get("timestamp", 0) > now - 3600: hr += 1
        except: pass
    last = "Never"
    if ls:
        try: last = json.loads(ls[-1]).get("time_iso", "?")
        except: pass
    return {"tot": len(ls), "hr": hr, "err": err, "last": last}

def recent_logs(n=6):
    if not LOG.exists(): return []
    ls = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    out = []
    for l in ls[-n:]:
        try: out.append(json.loads(l))
        except: pass
    return list(reversed(out))


def main():
    srv = [None]

    # ── Gather data ──
    g = gpu()
    m = models()
    s = stats()

    gi = "[green]●[/]" if g["ok"] else "[dim]○[/]"
    fi = "[green]✓[/]" if m["fl"] else "[red]✗[/]"
    li = "[green]✓[/]" if m["glm"] else "[red]✗[/]"

    # ── Widgets ──
    hdr = ptg.Container(
        ptg.Label("[bold gold1]╔══ UI Agent MCP Dashboard ══╗[/]", parent_align=ptg.HorizontalAlignment.CENTER),
        ptg.Label("[dim]Florence-2 + GLM-OCR (Z.AI)[/]", parent_align=ptg.HorizontalAlignment.CENTER),
        box="DOUBLE",
    )

    sys_card = ptg.Container(
        ptg.Label("[bold deep_sky_blue1]■ System[/]"),
        ptg.Label(f"{gi} GPU: {g['name']}"),
        ptg.Label(f"   Memory: {g['mem']}"),
        ptg.Label(""),
        ptg.Label(f"{fi} Florence-2: {'OK' if m['fl'] else 'Missing'} ({m['fl_s']})"),
        ptg.Label(f"{li} GLM-OCR: {'OK' if m['glm'] else 'Missing'} ({m['glm_s']})"),
        ptg.Label(""),
        ptg.Label(f"Actions: {s['tot']} total | {s['hr']}/hr | {s['err']} errors"),
        ptg.Label(f"Last: {s['last']}"),
        box="SINGLE",
        width=42,
    )

    st = ptg.Label("[dim]Ready[/]")

    def do_start():
        st.value = "[yellow]Starting...[/]"
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            srv[0] = proc
            st.value = "[green]● Server Running[/]"
        threading.Thread(target=t, daemon=True).start()

    def do_stop():
        cmd("pkill -f 'python server.py' || true")
        st.value = "[dim]● Stopped[/]"

    def do_health():
        st.value = "[yellow]Running health check...[/]"
        def t():
            cmd(f"cd {BASE} && bash scripts/health_check.sh")
            st.value = "[green]Done ✓[/]"
        threading.Thread(target=t, daemon=True).start()

    def do_logs():
        ls = recent_logs()
        if not ls:
            st.value = "[dim]No logs yet[/]"
            return
        st.value = "\n".join(f"[dim]{l.get('time_iso','?')[:19]} {l.get('action','?')}[/]" for l in ls)

    act_card = ptg.Container(
        ptg.Label("[bold hot_pink]■ Actions[/]"),
        ptg.Button("🔍 Health Check", on_click=lambda _: do_health()),
        ptg.Button("▶ Start Server", on_click=lambda _: do_start()),
        ptg.Button("⏹ Stop Server", on_click=lambda _: do_stop()),
        ptg.Button("📋 View Logs", on_click=lambda _: do_logs()),
        ptg.Label("─" * 36),
        st,
        box="SINGLE",
        width=42,
    )

    log_lb = ptg.Label("[dim]Click Start Server[/]")
    srv_card = ptg.Container(
        ptg.Label("[bold lime_green]■ Server Logs[/]"),
        ptg.Label("─" * 60),
        log_lb,
        box="SINGLE",
    )

    def start_logs():
        log_lb.value = "[dim]Starting...[/]\n"
        st.value = "[yellow]Starting...[/]"
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            srv[0] = proc
            st.value = "[green]● Running[/]"
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    log_lb.value += f"[dim]{ln.rstrip()}[/]\n"
                if len(log_lb.value) > 3000:
                    log_lb.value = log_lb.value[-1500:]
        threading.Thread(target=t, daemon=True).start()

    act_card += ptg.Button("▶ Start + Live Logs", on_click=lambda _: start_logs())

    dev = "CPU"
    if ENV.exists():
        for ln in ENV.read_text().split("\n"):
            if ln.startswith("DEVICE="): dev = ln.split("=")[1].strip().upper()

    cfg_card = ptg.Container(
        ptg.Label("[bold yellow]■ Config[/]"),
        ptg.Label(f"Device: [bold]{dev}[/]"),
        ptg.Label("Vision: [bold]florence-2-base[/]"),
        ptg.Label("OCR: [bold]GLM-OCR[/]"),
        ptg.Label(f"Path: [dim]{BASE}[/]"),
        box="SINGLE",
        width=42,
    )

    ftr = ptg.Label("[dim]q=quit | r=refresh[/]", parent_align=ptg.HorizontalAlignment.CENTER)

    # ── Layout (simple stacking) ──
    top = ptg.Splitter(sys_card, act_card)
    bot = ptg.Splitter(srv_card, cfg_card)

    mgr = ptg.WindowManager()
    mgr.add(hdr)
    mgr.add(top)
    mgr.add(bot)
    mgr.add(ftr)

    @mgr.bind("q", "quit")
    def _():
        if srv[0]: srv[0].terminate()
        mgr.stop()

    @mgr.bind("r", "refresh")
    def _():
        mgr.toast("Refreshed")

    mgr.run()

    print("\n👋 Dashboard closed\n")


if __name__ == "__main__":
    main()
