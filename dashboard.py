#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style TUI Dashboard
Single-window layout, proper rendering.
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

W  = "bold white"
G  = "bold lime_green"
Y  = "bold gold1"
R  = "bold red"
CY = "bold deep_sky_blue1"
PK = "bold hot_pink"
DM = "dim"
GL = "bold green"
OR = "bold orange1"


def bar(pct, width=20):
    filled = int(pct / 100 * width)
    if pct > 80:   c = R
    elif pct > 60: c = OR
    elif pct > 40: c = Y
    else:          c = G
    return f"[{c}]{'█' * filled}{'░' * (width - filled)}[/] [{W}]{pct:3.0f}%[/]"


class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.log_lines = deque(maxlen=30)
        self.t0 = time.time()
        self.label = None

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try: return float(o)
        except: return 0.0

    def ram(self):
        o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
        p = o.split()
        if len(p) >= 3:
            used, total, pct = int(p[0]), int(p[1]), float(p[2])
            fmt = lambda b: f"{b/1024**3:.1f}GiB" if b > 1024**3 else f"{b/1024**2:.0f}MiB"
            return fmt(used), fmt(total), pct
        return "?", "?", 0

    def gpu(self):
        o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
        if o and "fail" not in o.lower():
            p = o.split(", ")
            if len(p) >= 5:
                try:
                    return {"name": p[0], "mem": p[1], "mem_t": p[2],
                            "util": float(p[3]), "temp": float(p[4])}
                except: pass
        return None

    def models(self):
        m = BASE / "models"
        def chk(n):
            p = m / n
            if p.exists():
                sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                return True, f"{sz/1024**3:.1f}GB"
            return False, "—"
        return chk("Florence-2-base"), chk("GLM-OCR")

    def stats(self):
        if not LOG.exists():
            return 0, 0, 0, "Never", []
        lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
        errors = sum(1 for l in lines if '"error"' in l or '"status": "error"' in l)
        one_hr = time.time() - 3600
        hr = sum(1 for l in lines if (lambda x: json.loads(x).get("timestamp",0) if x else 0)(l) > one_hr)
        last = "Never"
        if lines:
            try: last = json.loads(lines[-1]).get("time_iso","?")[:19]
            except: pass
        actions = {}
        for l in lines:
            try:
                a = json.loads(l).get("action","?")
                actions[a] = actions.get(a, 0) + 1
            except: pass
        top = sorted(actions.items(), key=lambda x: -x[1])[:5]
        return len(lines), hr, errors, last, top

    def render(self):
        elapsed = int(time.time() - self.t0)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        W_ = shutil.get_terminal_size((80, 40)).columns

        # Gather data
        cpu_pct = self.cpu()
        ram_used, ram_total, ram_pct = self.ram()
        g = self.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.models()
        tot, hr_cnt, err, last, top = self.stats()

        lines = []

        # ── Header ──
        lines.append(f"[{Y}]{'═' * W_}[/]")
        lines.append(f"[{Y}]  ╦ ╦╔═╗╔╗   ╔═╗╔═╗╔═╗╔╦╗╦ ╦╦═╗╔╦╗   ╔╦╗╔═╗╔╗╔╦╔╦╗╔═╗╦═╗[/]")
        lines.append(f"[{Y}]  ║║║║╣ ╠╩╗  ╠═╣║ ╦╚═╗ ║ ║ ║╠╦╝ ║     ║ ║ ║║║║║ ║ ║╣ ╠╦╝[/]")
        lines.append(f"[{Y}]  ╚╩╝╚═╝╚═╝  ╩ ╩╚═╝╚═╝ ╩ ╚═╝╩╚═ ╩     ╩ ╚═╝╝╚╝╩ ╩ ╚═╝╩╚═[/]")
        lines.append(f"[{CY}]  Ui:{h:02d}:{m:02d}:{s:02d}   Florence-2 + GLM-OCR (Z.AI)[/]")
        lines.append(f"[{Y}]{'═' * W_}[/]")

        hw = (W_ - 6) // 2  # half width

        # ── Row 1: CPU + RAM ──
        lines.append("")
        lines.append(f"[{CY}]╭─{'─' * hw}╮[/][{CY}]╭─{'─' * hw}╮[/]")
        lines.append(f"[{CY}]│[/] [{W}]CPU Usage{' ' * (hw - 11)}[/][{CY}]│[/][{CY}]│[/] [{W}]RAM Usage{' ' * (hw - 11)}[/][{CY}]│[/]")
        lines.append(f"[{CY}]│[/] {bar(cpu_pct, hw - 4)}  [{CY}]│[/][{CY}]│[/] {bar(ram_pct, hw - 4)}  [{CY}]│[/]")
        lines.append(f"[{CY}]│[/] [{DM}]{' ' * (hw - 2)}[/][{CY}]│[/][{CY}]│[/] [{W}]{ram_used}/{ram_total}{' ' * max(0, hw - len(ram_used) - len(ram_total) - 5)}[/][{CY}]│[/]")
        lines.append(f"[{CY}]╰─{'─' * hw}╯[/][{CY}]╰─{'─' * hw}╯[/]")

        # ── Row 2: GPU + Models ──
        lines.append("")
        lines.append(f"[{GL}]╭─{'─' * hw}╮[/][{PK}]╭─{'─' * hw}╮[/]")

        if g:
            gpu_line = f"{g['name']}"
            lines.append(f"[{GL}]│[/] [{GL}]{gpu_line}{' ' * max(0, hw - len(gpu_line) - 2)}[/][{GL}]│[/][{PK}]│[/] [{W}]AI Models{' ' * (hw - 11)}[/][{PK}]│[/]")
            lines.append(f"[{GL}]│[/] Util  {bar(g['util'], hw - 12)}[{GL}]│[/][{PK}]│[/]")

            fl_str = f"[{G}]● Ready ({fl_s})" if fl_ok else f"[{R}]○ Missing"
            glm_str = f"[{G}]● Ready ({glm_s})" if glm_ok else f"[{R}]○ Missing"
            lines.append(f"[{GL}]│[/] Mem   [{CY}]{g['mem']}/{g['mem_t']}{' ' * max(0, hw - len(g['mem']) - len(g['mem_t']) - 14)}[/][{GL}]│[/][{PK}]│[/] Florence-2  {fl_str}[/]")
            t = g['temp']
            tc = Y if t > 70 else W
            lines.append(f"[{GL}]│[/] Temp  [{tc}]{t:.0f}°C[/]  {bar(min(t,100), hw - 16)}[{GL}]│[/][{PK}]│[/] GLM-OCR     {glm_str}[/]")
        else:
            lines.append(f"[{GL}]│[/] [{DM}]No GPU detected{' ' * (hw - 18)}[/][{GL}]│[/][{PK}]│[/] [{W}]AI Models{' ' * (hw - 11)}[/][{PK}]│[/]")
            lines.append(f"[{GL}]│[/] [{DM}]—{' ' * (hw - 5)}[/][{GL}]│[/][{PK}]│[/] Florence-2  [{DM}]—[/]")
            lines.append(f"[{GL}]│[/] [{DM}]—{' ' * (hw - 5)}[/][{GL}]│[/][{PK}]│[/] GLM-OCR     [{DM}]—[/]")

        lines.append(f"[{GL}]╰─{'─' * hw}╯[/][{PK}]╰─{'─' * hw}╯[/]")

        # ── Row 3: Stats + Top Actions ──
        lines.append("")
        lines.append(f"[{Y}]╭─{'─' * hw}╮[/][{PK}]╭─{'─' * hw}╮[/]")
        lines.append(f"[{Y}]│[/] [{W}]Statistics{' ' * (hw - 12)}[/][{Y}]│[/][{PK}]│[/] [{W}]Top Actions{' ' * (hw - 13)}[/][{PK}]│[/]")
        lines.append(f"[{Y}]│[/] [{W}]Total:[/] {tot}  [{CY}]Hour:[/] {hr_cnt}  [{R if err else G}]Err:[/] {err}{' ' * max(0, hw - 30 - len(str(tot)) - len(str(hr_cnt)) - len(str(err)))}[/][{Y}]│[/]")
        if top:
            for i, (name, cnt) in enumerate(top[:4]):
                padding = hw - len(name) - len(str(cnt)) - 7
                lines.append(f"[{Y}]│[/] [{CY}]{name}[/] {'·' * max(1, padding)} [{W}]{cnt}[/][{Y}]│[/]")
        else:
            lines.append(f"[{Y}]│[/] [{DM}]No actions yet{' ' * (hw - 18)}[/][{Y}]│[/]")
        lines.append(f"[{Y}]│[/] [{DM}]Last: {last}{' ' * max(0, hw - len(last) - 9)}[/][{Y}]│[/]")
        lines.append(f"[{Y}]╰─{'─' * hw}╯[/][{PK}]╰─{'─' * hw}╯[/]")

        # ── Row 4: Server Log + Controls ──
        lines.append("")
        lines.append(f"[{G}]╭─{'─' * hw}╮[/][{GL}]╭─{'─' * hw}╮[/]")
        lines.append(f"[{G}]│[/] [{W}]Server Log{' ' * (hw - 12)}[/][{G}]│[/][{GL}]│[/] [{W}]Controls{' ' * (hw - 10)}[/][{GL}]│[/]")

        # Log lines (fill from right side)
        log_list = list(self.log_lines)[-5:] if self.log_lines else []
        for i in range(5):
            if i < len(log_list):
                ln = log_list[i][:hw - 4]
                lines.append(f"[{G}]│[/] [{DM}]{ln}{' ' * max(0, hw - len(ln) - 3)}[/][{G}]│[/]")
            else:
                lines.append(f"[{G}]│[/] [{' ' * (hw - 2)}[/][{G}]│[/]")

        lines.append(f"[{G}]╰─{'─' * hw}╯[/][{GL}]│[/]  [{W}]s[/] Start Server        [{GL}]│[/]")
        lines.append(f"[{GL}]│[/]  [{W}]x[/] Stop Server         [{GL}]│[/]")
        lines.append(f"[{GL}]│[/]  [{W}]h[/] Health Check        [{GL}]│[/]")
        lines.append(f"[{GL}]│[/]  [{W}]d[/] Download Models     [{GL}]│[/]")
        lines.append(f"[{GL}]│[/]  [{W}]q[/] Quit               [{GL}]│[/]")
        lines.append(f"[{GL}]╰─{'─' * hw}╯[/]")

        # ── Status bar ──
        lines.append(f"[{Y}]{'═' * W_}[/]")
        status = "● Running" if self.proc and self.proc.poll() is None else "○ Stopped"
        sc = G if self.proc and self.proc.poll() is None else DM
        lines.append(f"[{sc}]{status}[/]  [{DM}]q:quit  r:refresh  s:start  x:stop  h:health[/]  [{CY}]Last: {last}[/]")

        return "\n".join(lines)

    def start_server(self):
        self.log_lines.append("Starting server...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    self.log_lines.append(ln.rstrip())
        threading.Thread(target=t, daemon=True).start()

    def stop_server(self):
        sh("pkill -f 'python server.py' || true")

    def run(self):
        db = self

        with ptg.WindowManager() as mgr:
            db.label = ptg.Label(db.render())

            win = ptg.Window(db.label, box="EMPTY")

            mgr.add(win)

            mgr.bind("q", "Quit", lambda: mgr.stop())
            mgr.bind("r", "Refresh", lambda: setattr(db.label, "value", db.render()))
            mgr.bind("s", "Start", lambda: db.start_server())
            mgr.bind("x", "Stop", lambda: db.stop_server())
            mgr.bind("h", "Health", lambda: sh(f"cd {BASE} && bash scripts/health_check.sh &"))
            mgr.bind("d", "Download", lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh &"))

            def updater():
                while True:
                    time.sleep(2)
                    try:
                        db.label.value = db.render()
                    except: pass
            threading.Thread(target=updater, daemon=True).start()

            mgr.run()

        print(f"\n[{G}]Dashboard closed[{/}]\n")


if __name__ == "__main__":
    Dashboard().run()
