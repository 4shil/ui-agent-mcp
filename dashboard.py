#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style TUI Dashboard
Clean, colorful, box-drawn terminal UI with live monitoring.
"""

import time, json, subprocess, threading, shutil
from pathlib import Path
from collections import deque

import pytermgui as ptg

BASE = Path(__file__).parent
LOG = BASE / "logs" / "actions.jsonl"

def sh(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr).strip()
    except: return ""

def term_width():
    return shutil.get_terminal_size((80, 24)).columns

# ═══════ COLORS ═══════
W  = "bold white"
G  = "bold lime_green"     # good/green
Y  = "bold gold1"          # warning/yellow
R  = "bold red"            # bad/red
CY = "bold deep_sky_blue1" # info/cyan
PK = "bold hot_pink"       # accent
DM = "dim"                 # muted
GL = "bold green"          # GPU green
OR = "bold orange1"        # mid/warning

def bar(pct, width=20):
    """Render a colored bar like btop."""
    filled = int(pct / 100 * width)
    if pct > 80:   c = R
    elif pct > 60: c = OR
    elif pct > 40: c = Y
    else:          c = G
    return f"[{c}]{'█' * filled}{'░' * (width - filled)}[/] [{W}]{pct:3.0f}%[/]"

def mini_bar(pct, width=10):
    filled = int(pct / 100 * width)
    if pct > 80:   c = R
    elif pct > 60: c = OR
    elif pct > 40: c = Y
    else:          c = G
    return f"[{c}]{'█' * filled}{'░' * (width - filled)}[/]"


# ═══════ DATA FETCHERS ═══════

def get_gpu():
    o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
    if o and "fail" not in o.lower():
        p = o.split(", ")
        if len(p) >= 5:
            try:
                util = float(p[3].replace("%",""))
                temp = float(p[4])
                return {"ok": True, "name": p[0], "mem": p[1], "mem_total": p[2], "util": util, "temp": temp}
            except: pass
    return {"ok": False, "name": "N/A", "mem": "0", "mem_total": "0", "util": 0, "temp": 0}

def get_cpu():
    o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
    try: return float(o)
    except: return 0.0

def get_ram():
    o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
    parts = o.split()
    if len(parts) >= 3:
        used = int(parts[0])
        total = int(parts[1])
        pct = float(parts[2])
        def fmt(b):
            if b < 1024**3: return f"{b/1024**2:.0f}MiB"
            return f"{b/1024**3:.1f}GiB"
        return {"used": fmt(used), "total": fmt(total), "pct": pct}
    return {"used": "0", "total": "0", "pct": 0}

def get_models():
    m = BASE / "models"
    def chk(name):
        p = m / name
        if p.exists():
            sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            if sz > 1024**3: return True, f"{sz/1024**3:.1f}GB"
            return True, f"{sz/1024**2:.0f}MB"
        return False, "—"
    return chk("Florence-2-base"), chk("GLM-OCR")

def get_stats():
    if not LOG.exists():
        return 0, 0, 0, "Never", []
    lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    total = len(lines)
    errors = 0
    actions = {}
    one_hr = time.time() - 3600
    hr = 0
    for l in lines:
        try:
            e = json.loads(l)
            if e.get("status") == "error": errors += 1
            a = e.get("action", "?")
            actions[a] = actions.get(a, 0) + 1
            if e.get("timestamp", 0) > one_hr: hr += 1
        except: pass
    last = "Never"
    if lines:
        try: last = json.loads(lines[-1]).get("time_iso", "?")[:19]
        except: pass
    top = sorted(actions.items(), key=lambda x: -x[1])[:6]
    return total, hr, errors, last, top

def get_logs(n=6):
    if not LOG.exists(): return []
    lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
    out = []
    for l in lines[-n:]:
        try: out.append(json.loads(l))
        except: pass
    return list(reversed(out))


# ═══════════════════════════════════════════════════════════
#  BTOP-STYLE DASHBOARD
# ═══════════════════════════════════════════════════════════

def main():
    state = {"running": True, "proc": None, "log_lines": deque(maxlen=60)}

    def quit_fn():
        state["running"] = False
        if state["proc"]:
            state["proc"].terminate()
        mgr.stop()

    def start_fn():
        log_box.value = f"[{DM}]Starting...[/]\n"
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            state["proc"] = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    state["log_lines"].append(ln.rstrip())
                    log_box.value = "\n".join(f"[{DM}]{l}[/]" for l in list(state["log_lines"])[-20:])
        threading.Thread(target=t, daemon=True).start()

    def stop_fn():
        sh("pkill -f 'python server.py' || true")

    def health_fn():
        def t():
            sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1")
        threading.Thread(target=t, daemon=True).start()

    def dl_fn():
        def t():
            sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh 2>&1")
        threading.Thread(target=t, daemon=True).start()

    # ── Live labels ──
    cpu_label = ptg.Label("")
    ram_label = ptg.Label("")
    gpu_label = ptg.Label("")
    temp_label = ptg.Label("")
    model_label = ptg.Label("")
    stats_label = ptg.Label("")
    top_label = ptg.Label("")
    log_box = ptg.Label(f"[{DM}]Waiting for server...[/]")
    status_bar = ptg.Label(f"[{DM}]q:quit  r:refresh  s:start  x:stop[/]")
    uptime_lb = ptg.Label("")

    t0 = time.time()

    def refresh():
        elapsed = int(time.time() - t0)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        uptime_lb.value = f"[{CY}]Ui:{h:02d}:{m:02d}:{s:02d}[/]"

        # CPU
        cpu = get_cpu()
        cpu_label.value = f"  {bar(cpu, 30)}"
        ram_label.value = f"  {bar(get_ram()['pct'], 30)}"

        # RAM detail
        r = get_ram()
        ram_label.value = f"  {bar(r['pct'], 22)}  [{W}]{r['used']}/{r['total']}[/]"

        # GPU
        g = get_gpu()
        if g["ok"]:
            gpu_label.value = f"  [{GL}]{g['name']}[/]"
            temp_c = g['temp']
            temp_label.value = (
                f"  Util  {bar(g['util'], 22)}\n"
                f"  Mem   [{CY}]{g['mem']}/{g['mem_total']}[/]\n"
                f"  Temp  [{Y if temp_c > 70 else W}]{temp_c:.0f}°C[/]  {mini_bar(min(temp_c, 100), 10)}"
            )
        else:
            gpu_label.value = f"  [{DM}]No GPU[/]"
            temp_label.value = f"  [{DM}]—[/]"

        # Models
        (fl_ok, fl_s), (glm_ok, glm_s) = get_models()
        fi = f"[{G}]●[/] Ready ({fl_s})" if fl_ok else f"[{R}]○[/] Missing"
        gi = f"[{G}]●[/] Ready ({glm_s})" if glm_ok else f"[{R}]○[/] Missing"
        model_label.value = f"  Florence-2  {fi}\n  GLM-OCR     {gi}"

        # Stats
        tot, hr, err, last, top = get_stats()
        stats_label.value = (
            f"  [{W}]Total:[/] {tot}  [{CY}]Hr:[/] {hr}  "
            f"[{R if err else G}]Err:[/] {err}\n"
            f"  [{DM}]Last:[/] {last}"
        )

        # Top actions
        if top:
            lines = []
            for name, cnt in top[:5]:
                lines.append(f"  [{CY}]{name:20s}[/] [{W}]{cnt}[/]")
            top_label.value = "\n".join(lines)
        else:
            top_label.value = f"  [{DM}]No actions yet[/]"

    # ── Background refresher ──
    def refresher():
        while state["running"]:
            try: refresh()
            except: pass
            time.sleep(2)
    threading.Thread(target=refresher, daemon=True).start()

    # ── BUILD UI ──
    with ptg.WindowManager() as mgr:
        # Title
        mgr.add(ptg.Window(
            f"[{Y}]   ╦ ╦╔═╗╔╗   ╔═╗╔═╗╔═╗╔╦╗╦ ╦╦═╗╔╦╗   ╔╦╗╔═╗╔╗╔╦╔╦╗╔═╗╦═╗  ══[/]",
            f"[{Y}]   ║║║║╣ ╠╩╗  ╠═╣║ ╦╚═╗ ║ ║ ║╠╦╝ ║     ║ ║ ║║║║║ ║ ║╣ ╠╦╝[/]",
            f"[{Y}]   ╚╩╝╚═╝╚═╝  ╩ ╩╚═╝╚═╝ ╩ ╚═╝╩╚═ ╩     ╩ ╚═╝╝╚╝╩ ╩ ╚═╝╩╚═[/]",
            box="EMPTY",
        ))

        # ── Row 1: CPU + RAM ──
        cpu_box = ptg.Window(
            f"[{CY}]╭─ CPU ────────────────────────────╮[/]",
            f"  [{W}]Processor Usage[/]",
            cpu_label,
            f"[{CY}]╰──────────────────────────────────╯[/]",
            box="EMPTY",
        )

        ram_box = ptg.Window(
            f"[{CY}]╭─ MEMORY ─────────────────────────╮[/]",
            f"  [{W}]RAM Usage[/]",
            ram_label,
            f"[{CY}]╰──────────────────────────────────╯[/]",
            box="EMPTY",
        )

        mgr.add(ptg.Splitter(cpu_box, ram_box))

        # ── Row 2: GPU + Models ──
        gpu_box = ptg.Window(
            f"[{GL}]╭─ GPU ─────────────────────────────╮[/]",
            gpu_label,
            temp_label,
            f"[{GL}]╰───────────────────────────────────╯[/]",
            box="EMPTY",
        )

        model_box = ptg.Window(
            f"[{PK}]╭─ AI MODELS ─────────────────────╮[/]",
            model_label,
            f"",
            f"[{PK}]╰────────────────────────────────╯[/]",
            box="EMPTY",
        )

        mgr.add(ptg.Splitter(gpu_box, model_box))

        # ── Row 3: Stats + Actions ──
        stats_box = ptg.Window(
            f"[{Y}]╭─ STATISTICS ──────────────────────╮[/]",
            stats_label,
            f"[{Y}]╰───────────────────────────────────╯[/]",
            box="EMPTY",
        )

        top_box = ptg.Window(
            f"[{PK}]╭─ TOP ACTIONS ────────────────────╮[/]",
            top_label,
            f"[{PK}]╰──────────────────────────────────╯[/]",
            box="EMPTY",
        )

        mgr.add(ptg.Splitter(stats_box, top_box))

        # ── Row 4: Controls + Logs ──
        ctrl_box = ptg.Window(
            f"[{G}]╭─ CONTROLS ──────────────────────╮[/]",
            "",
            f"  [{W}]s[/] Start Server",
            f"  [{W}]x[/] Stop Server",
            f"  [{W}]h[/] Health Check",
            f"  [{W}]d[/] Download Models",
            "",
            f"[{G}]╰────────────────────────────────╯[/]",
            box="EMPTY",
        )

        log_window = ptg.Window(
            f"[{G}]╭─ SERVER LOG ──────────────────────────────────────╮[/]",
            log_box,
            f"[{G}]╰──────────────────────────────────────────────────╯[/]",
            box="EMPTY",
        )

        mgr.add(ptg.Splitter(ctrl_box, log_window))

        # ── Status bar ──
        mgr.add(status_bar)

        # ── Keybindings ──
        mgr.bind("q", "Quit", quit_fn)
        mgr.bind("r", "Refresh", refresh)
        mgr.bind("s", "Start", lambda: start_fn())
        mgr.bind("x", "Stop", lambda: stop_fn())
        mgr.bind("h", "Health", lambda: health_fn())
        mgr.bind("d", "Download", lambda: dl_fn())

        refresh()
        mgr.run()

    print(f"\n[{G}]👋 Dashboard closed[{/}]\n")


if __name__ == "__main__":
    main()
