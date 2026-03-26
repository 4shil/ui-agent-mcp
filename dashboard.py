#!/usr/bin/env python3
"""UI Agent MCP — Btop-Style Dashboard v5 — No wrap, no spawn."""

import curses
import time
import json
import subprocess
import threading
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


# ── Safe write: clips to bounds, NEVER wraps ──
def sw(scr, y, x, text, attr=0, maxw=None):
    """Write text at position, clipped to screen bounds."""
    H, W = scr.getmaxyx()
    if y < 0 or y >= H or x >= W - 1:
        return
    if maxw:
        avail = min(maxw, W - x - 1)
    else:
        avail = W - x - 1
    if avail <= 0:
        return
    text = text[:avail]  # CLIP — no wrapping
    try:
        scr.addnstr(y, x, text, avail, attr)
    except curses.error:
        pass


def bar_str(pct, w):
    """Build bar string."""
    f = int(pct / 100 * w)
    if pct > 80:
        return "█" * f + "░" * (w - f), curses.color_pair(3) | curses.A_BOLD
    elif pct > 40:
        return "█" * f + "░" * (w - f), curses.color_pair(4) | curses.A_BOLD
    else:
        return "█" * f + "░" * (w - f), curses.color_pair(2) | curses.A_BOLD


def spark_str(history, w):
    """Build sparkline string."""
    if not history or w <= 0:
        return ""
    chars = "▁▂▃▄▅▆▇█"
    d = list(history)[-w:]
    lo, hi = min(d), max(d)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in d)


class Dashboard:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.proc = None
        self.data = Data()
        self.logs = deque(maxlen=10)
        self.t0 = time.time()

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_WHITE, -1)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_CYAN)

        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(2000)  # 2s refresh
        stdscr.keypad(True)

    def start(self):
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Starting...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()[:40]}")
        threading.Thread(target=t, daemon=True).start()

    def stop(self):
        sh("pkill -f 'python server.py' || true")
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Stopped")

    def draw(self):
        scr = self.stdscr
        H, W = scr.getmaxyx()

        # Collect data
        cpu = self.data.cpu()
        ru, rt, rpct = self.data.ram()
        gpus = self.data.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.data.models()
        tot, hr, err, last, top = self.data.stats()
        running = self.proc and self.proc.poll() is None
        el = time.time() - self.t0
        eh, er = divmod(int(el), 3600)
        em, es = divmod(er, 60)

        hw = W // 2  # half width
        B = curses.color_pair  # shorthand

        # ═══ CLEAR ONCE ═══
        scr.erase()

        # ═══ HEADER ═══
        sw(scr, 0, 0, "═" * W, B(4))
        t = "UI Agent MCP Dashboard"
        sw(scr, 1, (W - len(t)) // 2, t, B(4) | curses.A_BOLD)
        s = f"Florence-2 + GLM-OCR (Z.AI)  |  Up: {eh:02d}:{em:02d}:{es:02d}"
        sw(scr, 2, (W - len(s)) // 2, s, B(1))
        sw(scr, 3, 0, "═" * W, B(4))

        # ═══ ROW 1: CPU | RAM ═══
        R = 5  # row start

        # CPU box top
        sw(scr, R, 0, "╭─ CPU " + "─" * (hw - 8) + "╮", B(1))
        # CPU content
        bar_s = hw - 16
        btxt, battr = bar_str(cpu, bar_s)
        sw(scr, R+1, 0, "│ Use: ", B(1))
        sw(scr, R+1, 7, btxt, battr)
        sw(scr, R+1, 7 + bar_s + 1, f"{cpu:3.0f}%", curses.A_BOLD)
        sw(scr, R+1, hw - 1, "│", B(1))

        spark_s = hw - 12
        sp = spark_str(self.data.cpu_h, spark_s)
        sw(scr, R+2, 0, "│ Hist ", B(1))
        sw(scr, R+2, 6, sp, B(2))
        sw(scr, R+2, hw - 1, "│", B(1))

        sw(scr, R+3, 0, "│" + " " * (hw - 2) + "│", B(1))
        sw(scr, R+4, 0, "╰" + "─" * (hw - 2) + "╯", B(1))

        # RAM box
        sw(scr, R, hw, "╭─ MEMORY " + "─" * (hw - 11) + "╮", B(1))
        btxt, battr = bar_str(rpct, bar_s)
        sw(scr, R+1, hw, "│ Use: ", B(1))
        sw(scr, R+1, hw + 7, btxt, battr)
        sw(scr, R+1, hw + 7 + bar_s + 1, f"{rpct:3.0f}%", curses.A_BOLD)
        sw(scr, R+1, W - 1, "│", B(1))

        sp = spark_str(self.data.ram_h, spark_s)
        sw(scr, R+2, hw, "│ Hist ", B(1))
        sw(scr, R+2, hw + 6, sp, B(2))
        sw(scr, R+2, W - 1, "│", B(1))

        ram_info = f"{ru} / {rt}"
        sw(scr, R+3, hw, f"│ {ram_info}" + " " * max(0, W - hw - len(ram_info) - 3) + "│", B(6))
        sw(scr, R+4, hw, "╰" + "─" * (hw - 2) + "╯", B(1))

        # ═══ ROW 2: GPU | MODELS ═══
        R2 = R + 5

        # GPU
        sw(scr, R2, 0, "╭─ GPU " + "─" * (hw - 8) + "╮", B(2))
        if gpus:
            g = gpus[0]
            sw(scr, R2+1, 0, f"│ {g['name'][:hw-4]}", B(2) | curses.A_BOLD)
            sw(scr, R2+1, hw - 1, "│", B(2))

            btxt, battr = bar_str(g['util'], bar_s)
            sw(scr, R2+2, 0, "│ Use: ", B(2))
            sw(scr, R2+2, 7, btxt, battr)
            sw(scr, R2+2, 7 + bar_s + 1, f"{g['util']:3.0f}%", curses.A_BOLD)
            sw(scr, R2+2, hw - 1, "│", B(2))

            sw(scr, R2+3, 0, f"│ Mem: {g['mu']}/{g['mt']}" + " " * max(0, hw - len(g['mu']) - len(g['mt']) - 12) + "│", B(1))

            tc = B(3) if g['temp'] > 70 else B(6)
            sw(scr, R2+4, 0, f"│ Temp: {g['temp']:.0f}°C", tc)
            sw(scr, R2+4, hw - 1, "│", B(2))
        else:
            sw(scr, R2+1, 0, "│ No GPU detected", B(6))
            for i in range(2, 5):
                sw(scr, R2+i, 0, "│" + " " * (hw - 2) + "│", B(1))
        sw(scr, R2+5, 0, "╰" + "─" * (hw - 2) + "╯", B(2))

        # Models
        sw(scr, R2, hw, "╭─ AI MODELS " + "─" * (hw - 13) + "╮", B(5))
        fc = B(2) if fl_ok else B(3)
        sw(scr, R2+1, hw, f"│ Florence-2: {'● Ready' if fl_ok else '○ Missing'}" + " " * max(0, hw - 22) + "│", fc)
        if fl_ok:
            sw(scr, R2+2, hw, f"│   {fl_s}" + " " * max(0, hw - len(fl_s) - 5) + "│", B(6))

        gc = B(2) if glm_ok else B(3)
        sw(scr, R2+3, hw, f"│ GLM-OCR:    {'● Ready' if glm_ok else '○ Missing'}" + " " * max(0, hw - 22) + "│", gc)
        if glm_ok:
            sw(scr, R2+4, hw, f"│   {glm_s}" + " " * max(0, hw - len(glm_s) - 5) + "│", B(6))

        sw(scr, R2+5, hw, "╰" + "─" * (hw - 2) + "╯", B(5))

        # ═══ ROW 3: STATS + TOP ACTIONS ═══
        R3 = R2 + 6

        sw(scr, R3, 0, "╭─ STATISTICS " + "─" * (hw - 13) + "╮", B(4))
        sw(scr, R3+1, 0, f"│ Total: {tot}  Hour: {hr}  Err: {err}" + " " * max(0, hw - 38) + "│", B(6))
        sw(scr, R3+2, 0, f"│ Last: {last}" + " " * max(0, hw - len(last) - 8) + "│", B(6))
        for i in range(3, 5):
            sw(scr, R3+i, 0, "│" + " " * (hw - 2) + "│", B(1))
        sw(scr, R3+5, 0, "╰" + "─" * (hw - 2) + "╯", B(4))

        sw(scr, R3, hw, "╭─ TOP ACTIONS " + "─" * (hw - 15) + "╮", B(5))
        for i, (name, cnt) in enumerate(top[:5]):
            dots = max(1, hw - len(name) - len(str(cnt)) - 10)
            sw(scr, R3+1+i, hw, f"│ {name}" + " " * dots + f"{cnt}" + " " * 1 + "│", B(1))
        for i in range(max(0, 5 - len(top))):
            sw(scr, R3+1+len(top)+i, hw, "│" + " " * (hw - 2) + "│", B(1))
        sw(scr, R3+5, hw, "╰" + "─" * (hw - 2) + "╯", B(5))

        # ═══ ROW 4: CONTROLS + LOG ═══
        R4 = R3 + 6

        sw(scr, R4, 0, "╭─ CONTROLS " + "─" * (hw - 12) + "╮", B(2))
        keys = [("s", "Start Server"), ("x", "Stop Server"), ("h", "Health Check"), ("d", "Download Models"), ("r", "Refresh"), ("q", "Quit")]
        for i, (k, d) in enumerate(keys):
            sw(scr, R4+1+i, 0, f"│ {k}  {d}" + " " * max(0, hw - len(d) - 6) + "│", B(2))
        sw(scr, R4+6, 0, "╰" + "─" * (hw - 2) + "╯", B(2))

        sw(scr, R4, hw, "╭─ SERVER LOG " + "─" * (hw - 14) + "╮", B(2))
        log_list = list(self.logs)[-5:]
        for i, ln in enumerate(log_list):
            sw(scr, R4+1+i, hw, f"│ {ln}" + " " * max(0, hw - len(ln) - 3) + "│", B(6))
        for i in range(max(0, 5 - len(log_list))):
            sw(scr, R4+1+len(log_list)+i, hw, "│" + " " * (hw - 2) + "│", B(1))
        sw(scr, R4+5, hw, "╰" + "─" * (hw - 2) + "╯", B(2))

        # ═══ STATUS BAR ═══
        sw(scr, H-1, 0, "═" * W, B(4))
        sc = B(2) if running else B(6)
        sw(scr, H-1, 1, "● Running" if running else "○ Stopped", sc)
        sw(scr, H-1, 14, "q:quit s:start x:stop h:health d:download", B(6))
        sw(scr, H-1, W - 22, f"Last: {last[:19]}", B(1))

        # ═══ FLIP ═══
        scr.noutrefresh()
        curses.doupdate()

    def run(self):
        try:
            while True:
                self.draw()
                key = self.stdscr.getch()
                if key == ord('q'): break
                elif key == ord('s'): self.start()
                elif key == ord('x'): self.stop()
                elif key == ord('h'):
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
                    threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1"), daemon=True).start()
                elif key == ord('d'):
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] Downloading...")
                    threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()
        except KeyboardInterrupt:
            pass


def main(stdscr):
    Dashboard(stdscr).run()


if __name__ == "__main__":
    curses.wrapper(main)
