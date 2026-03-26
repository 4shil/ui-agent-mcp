#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style Dashboard v5
Single curses session, no restarts, proper signal handling.
"""

import curses
import time
import json
import subprocess
import threading
import signal
from pathlib import Path
from collections import deque
from datetime import datetime

BASE = Path(__file__).parent
LOG = BASE / "logs" / "actions.jsonl"

def sh(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr).strip()
    except: return ""


class Data:
    def __init__(self):
        self.cpu_h = deque(maxlen=50)
        self.ram_h = deque(maxlen=50)

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try: p = max(0, min(100, float(o)))
        except: p = 0.0
        self.cpu_h.append(p)
        return p

    def ram(self):
        o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
        p = o.split()
        if len(p) >= 3:
            u, t, pct = int(p[0]), int(p[1]), float(p[2])
        else:
            u, t, pct = 0, 1, 0.0
        self.ram_h.append(pct)
        fmt = lambda b: f"{b/1024**3:.1f}GiB" if b >= 1024**3 else f"{b/1024**2:.0f}MiB"
        return fmt(u), fmt(t), pct

    def gpu(self):
        o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
        if not o or "fail" in o.lower(): return []
        gpus = []
        for ln in o.split("\n"):
            p = [x.strip() for x in ln.split(",")]
            if len(p) >= 5:
                try: gpus.append({"name": p[0], "mu": p[1], "mt": p[2], "util": float(p[3]), "temp": float(p[4])})
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


# ── Safe string write ──
def sa(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h - 1 or x < 0 or x >= w - 1: return
    text = text[:w - x - 1]
    try: win.addstr(y, x, text, attr)
    except: pass


def bar(pct, w=18):
    """Return (filled, empty, pct_string) for drawing."""
    f = int(pct / 100 * w)
    return f, w - f, f"{pct:3.0f}%"


def spark(history, w=30):
    """Return sparkline string."""
    if not history: return " " * w
    chars = " ▁▂▃▄▅▆▇█"
    d = list(history)[-w:]
    lo, hi = min(d), max(d)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in d)


def col(pct):
    if pct > 80: return curses.color_pair(3)  # red
    if pct > 60: return curses.color_pair(4)  # yellow
    return curses.color_pair(2)               # green


def draw_box(win, y, x, w, h, title, title_color):
    """Draw a box border."""
    # Top border
    sa(win, y, x, "╭" + "─" * (w - 2) + "╮", title_color)
    if title:
        sa(win, y, x + 1, f" {title} ", title_color | curses.A_BOLD)
    # Sides
    for i in range(1, h - 1):
        sa(win, y + i, x, "│", title_color)
        sa(win, y + i, x + w - 1, "│", title_color)
    # Bottom border
    sa(win, y + h - 1, x, "╰" + "─" * (w - 2) + "╮", title_color)


class Dashboard:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.proc = None
        self.data = Data()
        self.logs = deque(maxlen=20)
        self.t0 = time.time()
        self.status_msg = ""

        # Colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # info
        curses.init_pair(2, curses.COLOR_GREEN, -1)     # good
        curses.init_pair(3, curses.COLOR_RED, -1)       # bad
        curses.init_pair(4, curses.COLOR_YELLOW, -1)    # warn
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)   # pink
        curses.init_pair(6, curses.COLOR_WHITE, -1)     # white

        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(500)
        stdscr.keypad(True)

    def start_server(self):
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Starting...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()[:50]}")
        threading.Thread(target=t, daemon=True).start()

    def stop_server(self):
        sh("pkill -f 'python server.py' || true")
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Stopped")

    def draw(self):
        stdscr = self.stdscr
        stdscr.erase()

        H, W = stdscr.getmaxyx()

        # Collect
        cpu = self.data.cpu()
        ru, rt, rpct = self.data.ram()
        gpus = self.data.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.data.models()
        tot, hr, err, last, top = self.data.stats()
        running = self.proc and self.proc.poll() is None

        elapsed = time.time() - self.t0
        eh, er = divmod(int(elapsed), 3600)
        em, es = divmod(er, 60)

        # Layout
        hw = W // 2
        row_h = max(5, (H - 5) // 4)

        # ── HEADER (always full width, no box) ──
        title = "UI Agent MCP Dashboard"
        sa(stdscr, 0, (W - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD | curses.A_UNDERLINE)
        sub = f"Florence-2 + GLM-OCR (Z.AI)  |  Uptime: {eh:02d}:{em:02d}:{es:02d}"
        sa(stdscr, 1, (W - len(sub)) // 2, sub, curses.color_pair(1))

        # ── CPU ──
        cy, cx = 3, 0
        draw_box(stdscr, cy, cx, hw, row_h, "CPU", curses.color_pair(1))
        sa(stdscr, cy+1, cx+2, "Use:", curses.A_DIM)
        f, e, ps = bar(cpu, hw - 15)
        sa(stdscr, cy+1, cx+7, "█" * f, col(cpu) | curses.A_BOLD)
        sa(stdscr, cy+1, cx+7+f, "░" * e, curses.A_DIM)
        sa(stdscr, cy+1, cx+7+hw-15+1, ps, curses.A_BOLD)
        sa(stdscr, cy+2, cx+2, spark(self.data.cpu_h, hw - 6), curses.color_pair(2))

        # ── MEMORY ──
        draw_box(stdscr, cy, hw, hw, row_h, "MEMORY", curses.color_pair(1))
        sa(stdscr, cy+1, hw+2, "Use:", curses.A_DIM)
        f, e, ps = bar(rpct, hw - 15)
        sa(stdscr, cy+1, hw+7, "█" * f, col(rpct) | curses.A_BOLD)
        sa(stdscr, cy+1, hw+7+f, "░" * e, curses.A_BOLD)
        sa(stdscr, cy+1, hw+7+hw-15+1, ps, curses.A_BOLD)
        sa(stdscr, cy+2, hw+2, f"{ru} / {rt}", curses.color_pair(1))
        sa(stdscr, cy+3, hw+2, spark(self.data.ram_h, hw - 6), curses.color_pair(2))

        # ── GPU ──
        gy = cy + row_h
        draw_box(stdscr, gy, 0, hw, row_h, "GPU", curses.color_pair(2))
        if gpus:
            g = gpus[0]
            sa(stdscr, gy+1, 2, g['name'][:hw-4], curses.color_pair(2) | curses.A_BOLD)
            sa(stdscr, gy+2, 2, "Use:", curses.A_DIM)
            f, e, ps = bar(g['util'], hw - 15)
            sa(stdscr, gy+2, 7, "█" * f, col(g['util']) | curses.A_BOLD)
            sa(stdscr, gy+2, 7+f, "░" * e, curses.A_DIM)
            sa(stdscr, gy+2, 7+hw-15+1, ps, curses.A_BOLD)
            tc = curses.color_pair(3) if g['temp'] > 70 else curses.color_pair(6)
            sa(stdscr, gy+3, 2, f"Mem: {g['mu']}/{g['mt']}", curses.color_pair(1))
            sa(stdscr, gy+4, 2, f"Temp: {g['temp']:.0f}°C", tc)
        else:
            sa(stdscr, gy+1, 2, "No GPU detected", curses.A_DIM)

        # ── MODELS ──
        draw_box(stdscr, gy, hw, hw, row_h, "AI MODELS", curses.color_pair(5))
        fc = curses.color_pair(2) if fl_ok else curses.color_pair(3)
        sa(stdscr, gy+1, hw+2, "Florence-2: ", curses.A_DIM)
        sa(stdscr, gy+1, hw+14, f"{'● Ready' if fl_ok else '○ Missing'}", fc)
        if fl_ok: sa(stdscr, gy+1, hw+24, f"({fl_s})", curses.A_DIM)

        gc = curses.color_pair(2) if glm_ok else curses.color_pair(3)
        sa(stdscr, gy+2, hw+2, "GLM-OCR:    ", curses.A_DIM)
        sa(stdscr, gy+2, hw+14, f"{'● Ready' if glm_ok else '○ Missing'}", gc)
        if glm_ok: sa(stdscr, gy+2, hw+24, f"({glm_s})", curses.A_DIM)

        sa(stdscr, gy+3, hw+2, f"Device: {'GPU' if gpus else 'CPU'}", curses.A_DIM)

        # ── STATS ──
        sy = gy + row_h
        draw_box(stdscr, sy, 0, hw, row_h, "STATISTICS", curses.color_pair(4))
        sa(stdscr, sy+1, 2, f"Total: {tot}  Hour: {hr}  Err: {err}", curses.color_pair(6))
        sa(stdscr, sy+2, 2, f"Last: {last}", curses.A_DIM)

        # ── TOP ACTIONS ──
        draw_box(stdscr, sy, hw, hw, row_h, "TOP ACTIONS", curses.color_pair(5))
        for i, (name, cnt) in enumerate(top[:row_h - 2]):
            sa(stdscr, sy+1+i, hw+2, name[:hw-10], curses.color_pair(1))
            sa(stdscr, sy+1+i, hw+hw-6, str(cnt), curses.A_BOLD)

        # ── CONTROLS ──
        cy2 = sy + row_h
        draw_box(stdscr, cy2, 0, hw, row_h, "CONTROLS", curses.color_pair(2))
        keys = [("s", "Start"), ("x", "Stop"), ("h", "Health"), ("d", "Download"), ("r", "Refresh"), ("q", "Quit")]
        for i, (k, d) in enumerate(keys):
            sa(stdscr, cy2+1+i, 2, f" {k}  {d}", curses.A_BOLD if i < 2 else curses.A_DIM)

        # ── SERVER LOG ──
        draw_box(stdscr, cy2, hw, hw, row_h, "SERVER LOG", curses.color_pair(2))
        log_list = list(self.logs)[-(row_h-2):]
        for i, ln in enumerate(log_list):
            sa(stdscr, cy2+1+i, hw+2, ln[:hw-5], curses.A_DIM)

        # ── STATUS BAR ──
        sc = curses.color_pair(2) if running else curses.A_DIM
        sa(stdscr, H-2, 2, "● RUNNING" if running else "○ STOPPED", sc | curses.A_BOLD)
        sa(stdscr, H-2, 16, "q:quit  s:start  x:stop  r:refresh", curses.A_DIM)

        stdscr.noutrefresh()
        curses.doupdate()

    def run(self):
        try:
            while self.running:
                self.draw()
                key = self.stdscr.getch()
                if key == ord('q'): break
                elif key == ord('s'): self.start_server()
                elif key == ord('x'): self.stop_server()
                elif key == ord('h'):
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
                    threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1"), daemon=True).start()
                elif key == ord('d'):
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] Downloading...")
                    threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()
        except KeyboardInterrupt:
            pass


def main(stdscr):
    dash = Dashboard(stdscr)
    dash.run()


if __name__ == "__main__":
    curses.wrapper(main)
