#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style Dashboard v3
Pure ANSI, properly aligned two-column layout.
"""

import sys, os, time, json, subprocess, threading, shutil, select
from pathlib import Path
from collections import deque
from datetime import datetime

BASE = Path(__file__).parent
LOG = BASE / "logs" / "actions.jsonl"

def sh(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr).strip()
    except:
        return ""

# ═══════════════════════════════════════════════════════════
#  ANSI ESCAPE CODES
# ═══════════════════════════════════════════════════════════

class T:
    RST  = "\033[0m"
    BOLD = "\033[1m"
    DIM  = "\033[2m"
    HIDE = "\033[?25l"
    SHOW = "\033[?25h"
    HOME = "\033[H"
    CLR  = "\033[2J"

    RED    = "\033[1;31m"
    GREEN  = "\033[1;32m"
    YELLOW = "\033[1;33m"
    BLUE   = "\033[1;34m"
    CYAN   = "\033[1;36m"
    WHITE  = "\033[1;37m"
    GRAY   = "\033[2;37m"

    GOLD   = "\033[1;38;5;220m"
    ORANGE = "\033[1;38;5;208m"
    PINK   = "\033[1;38;5;213m"
    LIME   = "\033[1;38;5;118m"

    @staticmethod
    def col(pct):
        if pct > 80: return T.RED
        if pct > 60: return T.ORANGE
        if pct > 40: return T.YELLOW
        return T.GREEN


# ═══════════════════════════════════════════════════════════
#  DATA COLLECTORS
# ═══════════════════════════════════════════════════════════

class Data:
    def __init__(self):
        self.cpu_hist = deque(maxlen=40)
        self.ram_hist = deque(maxlen=40)

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try: p = max(0, min(100, float(o)))
        except: p = 0.0
        self.cpu_hist.append(p)
        return p

    def ram(self):
        o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
        p = o.split()
        if len(p) >= 3:
            u, t, pct = int(p[0]), int(p[1]), float(p[2])
        else:
            u, t, pct = 0, 1, 0.0
        self.ram_hist.append(pct)
        fmt = lambda b: f"{b/1024**3:.1f}GiB" if b >= 1024**3 else f"{b/1024**2:.0f}MiB"
        return fmt(u), fmt(t), pct

    def gpu(self):
        o = sh("nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
        if not o or "fail" in o.lower(): return []
        gpus = []
        for ln in o.split("\n"):
            p = [x.strip() for x in ln.split(",")]
            if len(p) >= 6:
                try:
                    gpus.append({"name": p[1], "mu": p[2], "mt": p[3], "util": float(p[4]), "temp": float(p[5])})
                except: pass
        return gpus

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
        if not LOG.exists(): return 0, 0, 0, "Never", []
        lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
        err = sum(1 for l in lines if "error" in l.lower())
        hr = sum(1 for l in lines if (lambda x: json.loads(x).get("timestamp",0) if x else 0)(l) > time.time()-3600)
        last = "Never"
        if lines:
            try: last = json.loads(lines[-1]).get("time_iso","?")[:19]
            except: pass
        acts = {}
        for l in lines:
            try:
                a = json.loads(l).get("action","?")
                acts[a] = acts.get(a, 0) + 1
            except: pass
        return len(lines), hr, err, last, sorted(acts.items(), key=lambda x: -x[1])[:6]


# ═══════════════════════════════════════════════════════════
#  RENDER HELPERS
# ═══════════════════════════════════════════════════════════

def spark(h, w=20):
    if not h: return " " * w
    chars = " ▁▂▃▄▅▆▇█"
    d = list(h)[-w:]
    lo, hi = min(d), max(d)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in d)

def bar(pct, w=18):
    f = int(pct / 100 * w)
    c = T.col(pct)
    return f"{c}{'█' * f}{T.DIM}{'░' * (w - f)}{T.RST} {T.BOLD}{pct:3.0f}%{T.RST}"

def bline(label, pct, w=18):
    return f"  {label:>4}  {bar(pct, w)}"

# ── Box drawing: all boxes in a pair MUST have same line count ──

def box_pair(left_lines, right_lines, w):
    """Render two boxes side by side, padding to equal height."""
    hw = w  # each box width
    max_lines = max(len(left_lines), len(right_lines))
    left_padded = left_lines + [""] * (max_lines - len(left_lines))
    right_padded = right_lines + [""] * (max_lines - len(right_lines))

    out = []
    for i, (l, r) in enumerate(zip(left_padded, right_padded)):
        out.append(f"│ {l:<{hw-3}}││ {r:<{hw-3}}│")
    return out

def box_top(name, w):
    return f"╭─ {name} {'─' * max(0, w - len(name) - 4)}╮"

def box_bot(w):
    return f"╰{'─' * w}╯"


# ═══════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════

class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.data = Data()
        self.logs = deque(maxlen=20)
        self.t0 = time.time()

    def draw(self, W):
        hw = (W - 4) // 2  # half width for each box in a pair

        cpu = self.data.cpu()
        ru, rt, rpct = self.data.ram()
        gpus = self.data.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.data.models()
        tot, hr, err, last, top = self.data.stats()
        running = self.proc and self.proc.poll() is None

        el = int(time.time() - self.t0)
        eh, er = divmod(el, 3600)
        em, es = divmod(er, 60)

        L = []  # lines

        # ── HEADER ──
        L.append(f"{T.GOLD}{T.BOLD}  ╦═╗╔═╗╔╗ ╦  ╔═╗╔═╗╔═╗╔╦╗  ╔═╗╔═╗╔═╗╔╦╗╦ ╦╦═╗╔╦╗{T.RST}")
        L.append(f"{T.GOLD}{T.BOLD}  ╠╦╝║╣ ╠╩╗║  ╠═╣║ ╦╚═╗ ║   ╠═╣║ ╦╚═╗ ║ ║ ║╠╦╝ ║ {T.RST}")
        L.append(f"{T.GOLD}{T.BOLD}  ╩╚═╚═╝╚═╝╩═╝╩ ╩╚═╝╚═╝ ╩   ╩ ╩╚═╝╚═╝ ╩ ╚═╝╩╚═ ╩ {T.RST}")
        L.append(f"{T.CYAN}  Ui:{eh:02d}:{em:02d}:{es:02d}  Florence-2 + GLM-OCR (Z.AI){T.RST}")
        L.append(f"{T.GOLD}{'═' * (W-1)}{T.RST}")
        L.append("")

        # ── Row 1: CPU + RAM ──
        cpu_lines = [
            box_top("CPU", hw),
            bline("Use", cpu, hw - 12),
            f"  {T.DIM}Hist{T.RST} {spark(self.data.cpu_hist, hw - 14)}",
            f"  {T.DIM}User:{sh(\"top -bn1 | awk '/Cpu/{print $2}'\")}%  Sys:{sh(\"top -bn1 | awk '/Cpu/{print $4}'\")}%{T.RST}",
            box_bot(hw),
        ]
        ram_lines = [
            box_top("MEMORY", hw),
            bline("Use", rpct, hw - 12),
            f"  {ru}/{rt}",
            f"  {T.DIM}Hist{T.RST} {spark(self.data.ram_hist, hw - 14)}",
            box_bot(hw),
        ]
        L.append(f"╭{'─' * hw}╮╭{'─' * hw}╮")
        for row in zip(cpu_lines, ram_lines):
            L.append(f"│ {row[0]:<{hw-3}}││ {row[1]:<{hw-3}}│")
        L.append(f"╰{'─' * hw}╯╰{'─' * hw}╯")
        L.append("")

        # ── Row 2: GPU + Models ──
        gpu_lines = [box_top("GPU", hw)]
        if gpus:
            for g in gpus:
                name = g['name'][:hw - 10]
                gpu_lines.append(f"  {T.GREEN}{name}{T.RST}")
                gpu_lines.append(bline("Use", g['util'], hw - 12))
                tc = T.RED if g['temp'] > 70 else T.WHITE
                gpu_lines.append(f"  Mem: {T.CYAN}{g['mu']}/{g['mt']}{T.RST}  Temp: {tc}{g['temp']:.0f}°C{T.RST}")
        else:
            gpu_lines.append(f"  {T.DIM}No GPU detected{T.RST}")
            gpu_lines.append(f"  {T.DIM}—{T.RST}")
            gpu_lines.append(f"  {T.DIM}—{T.RST}")
        gpu_lines.append(box_bot(hw))

        model_lines = [
            box_top("AI MODELS", hw),
            f"  Florence-2  {T.GREEN}●{T.RST} Ready ({fl_s})" if fl_ok else f"  Florence-2  {T.RED}○{T.RST} Missing",
            f"  GLM-OCR     {T.GREEN}●{T.RST} Ready ({glm_s})" if glm_ok else f"  GLM-OCR     {T.RED}○{T.RST} Missing",
            f"  {T.DIM}Device: {'GPU' if gpus else 'CPU'}{T.RST}",
            box_bot(hw),
        ]

        # Pad to same height
        max_h = max(len(gpu_lines), len(model_lines))
        gpu_lines += [""] * (max_h - len(gpu_lines))
        model_lines += [""] * (max_h - len(model_lines))

        L.append(f"╭{'─' * hw}╮╭{'─' * hw}╮")
        for g, m in zip(gpu_lines, model_lines):
            L.append(f"│ {g:<{hw-3}}││ {m:<{hw-3}}│")
        L.append(f"╰{'─' * hw}╯╰{'─' * hw}╯")
        L.append("")

        # ── Row 3: Stats + Top Actions ──
        stat_lines = [
            box_top("STATISTICS", hw),
            f"  {T.BOLD}Total:{T.RST} {tot}  {T.CYAN}Hr:{T.RST} {hr}  {T.RED if err else T.GREEN}Err:{T.RST} {err}",
            f"  {T.DIM}Last: {last}{T.RST}",
            "",
            box_bot(hw),
        ]
        top_lines = [box_top("TOP ACTIONS", hw)]
        if top:
            for name, cnt in top[:4]:
                dots = max(1, hw - len(name) - len(str(cnt)) - 12)
                top_lines.append(f"  {T.CYAN}{name}{T.RST} {'·' * dots} {T.BOLD}{cnt}{T.RST}")
        else:
            top_lines.append(f"  {T.DIM}No actions yet{T.RST}")
            top_lines.append("")
        top_lines.append(box_bot(hw))

        max_h = max(len(stat_lines), len(top_lines))
        stat_lines += [""] * (max_h - len(stat_lines))
        top_lines += [""] * (max_h - len(top_lines))

        L.append(f"╭{'─' * hw}╮╭{'─' * hw}╮")
        for s, t in zip(stat_lines, top_lines):
            L.append(f"│ {s:<{hw-3}}││ {t:<{hw-3}}│")
        L.append(f"╰{'─' * hw}╯╰{'─' * hw}╯")
        L.append("")

        # ── Row 4: Server Log (full width) ──
        log_w = W - 4
        L.append(box_top("SERVER LOG", log_w))
        log_list = list(self.logs)[-6:]
        for i in range(6):
            if i < len(log_list):
                ln = log_list[i][:log_w - 4]
                L.append(f"│ {T.DIM}{ln}{T.RST}{' ' * max(0, log_w - 3 - len(ln))}│")
            else:
                L.append(f"│{' ' * (log_w - 1)}│")
        L.append(box_bot(log_w))
        L.append("")

        # ── STATUS BAR ──
        sc = f"{T.GREEN}● RUNNING{T.RST}" if running else f"{T.DIM}○ STOPPED{T.RST}"
        L.append(f"{T.GOLD}{'═' * (W-1)}{T.RST}")
        L.append(f"{sc}  {T.DIM}q:quit  r:refresh  s:start  x:stop  h:health  d:download{T.RST}  {T.CYAN}{last}{T.RST}")

        return "\n".join(L)

    def start(self):
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Starting MCP server...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()}")
        threading.Thread(target=t, daemon=True).start()

    def stop(self):
        sh("pkill -f 'python server.py' || true")
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Stopped")

    def run(self):
        fd = sys.stdin.fileno()
        old = None
        try:
            import termios
            old = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSANOW, new)
        except: pass

        def cleanup():
            sys.stdout.write(T.SHOW + T.HOME + T.CLR)
            sys.stdout.flush()
            if old:
                try:
                    import termios
                    termios.tcsetattr(fd, termios.TCSANOW, old)
                except: pass

        sys.stdout.write(T.CLR + T.HOME + T.HIDE)
        sys.stdout.flush()

        def refresher():
            while self.running:
                time.sleep(2)
                self.render()
        threading.Thread(target=refresher, daemon=True).start()
        self.render()

        try:
            while self.running:
                if select.select([sys.stdin], [], [], 0.3)[0]:
                    ch = sys.stdin.read(1)
                    if ch == 'q': break
                    elif ch == 'r': self.render()
                    elif ch == 's': self.start(); time.sleep(0.3); self.render()
                    elif ch == 'x': self.stop(); time.sleep(0.3); self.render()
                    elif ch == 'h':
                        self.logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
                        self.render()
                        threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh"), daemon=True).start()
                    elif ch == 'd':
                        self.logs.append(f"[{datetime.now():%H:%M:%S}] Downloading models...")
                        self.render()
                        threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()
        except KeyboardInterrupt: pass
        finally:
            self.running = False
            if self.proc: self.proc.terminate()
            cleanup()
            print(f"\n{T.GREEN}Dashboard closed{T.RST}\n")

    def render(self):
        W = shutil.get_terminal_size((80, 40)).columns
        sys.stdout.write(T.HOME + self.draw(W) + T.RST)
        sys.stdout.flush()


if __name__ == "__main__":
    Dashboard().run()
