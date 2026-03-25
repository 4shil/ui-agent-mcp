#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style Dashboard v5
Python curses (ncurses) — proper window management like real btop.
"""

import curses
import time
import json
import subprocess
import threading
import shutil
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
#  COLOR PAIRS
# ═══════════════════════════════════════════════════════════

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)      # info
    curses.init_pair(2, curses.COLOR_GREEN, -1)      # good
    curses.init_pair(3, curses.COLOR_RED, -1)         # bad
    curses.init_pair(4, curses.COLOR_YELLOW, -1)      # warn
    curses.init_pair(5, curses.COLOR_BLUE, -1)        # accent
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)     # pink
    curses.init_pair(7, curses.COLOR_WHITE, -1)        # white
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # bar bg


CP = {
    "cyan": curses.color_pair(1),
    "green": curses.color_pair(2),
    "red": curses.color_pair(3),
    "yellow": curses.color_pair(4),
    "blue": curses.color_pair(5),
    "pink": curses.color_pair(6),
    "white": curses.color_pair(7),
    "dim": curses.color_pair(7) | curses.A_DIM,
    "bold": curses.color_pair(7) | curses.A_BOLD,
    "gold": curses.color_pair(4) | curses.A_BOLD,
}


# ═══════════════════════════════════════════════════════════
#  DATA
# ═══════════════════════════════════════════════════════════

class Data:
    def __init__(self):
        self.cpu_hist = deque(maxlen=50)
        self.ram_hist = deque(maxlen=50)
        self.gpu_hist = deque(maxlen=50)

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try:
            p = max(0, min(100, float(o)))
        except:
            p = 0.0
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
        o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
        if not o or "fail" in o.lower():
            return []
        gpus = []
        for ln in o.split("\n"):
            p = [x.strip() for x in ln.split(",")]
            if len(p) >= 5:
                try:
                    gpus.append({
                        "name": p[0], "mu": p[1], "mt": p[2],
                        "util": float(p[3]), "temp": float(p[4]),
                    })
                except:
                    pass
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
        if not LOG.exists():
            return 0, 0, 0, "Never", []
        lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
        err = sum(1 for l in lines if "error" in l.lower())
        one_hr = time.time() - 3600
        hr = 0
        actions = {}
        for l in lines:
            try:
                e = json.loads(l)
                if e.get("timestamp", 0) > one_hr:
                    hr += 1
                a = e.get("action", "?")
                actions[a] = actions.get(a, 0) + 1
            except:
                pass
        last = "Never"
        if lines:
            try:
                last = json.loads(lines[-1]).get("time_iso", "?")[:19]
            except:
                pass
        top = sorted(actions.items(), key=lambda x: -x[1])[:6]
        return len(lines), hr, err, last, top


# ═══════════════════════════════════════════════════════════
#  RENDER HELPERS
# ═══════════════════════════════════════════════════════════

def draw_bar(win, y, x, pct, w=20, label=""):
    """Draw a colored bar in a curses window."""
    filled = int(pct / 100 * w)
    if pct > 80:
        col = curses.color_pair(3)
    elif pct > 60:
        col = curses.color_pair(4)
    elif pct > 40:
        col = curses.color_pair(4)
    else:
        col = curses.color_pair(2)

    # Draw filled part
    win.addstr(y, x, "█" * filled, col | curses.A_BOLD)
    # Draw empty part
    win.addstr(y, x + filled, "░" * (w - filled), curses.A_DIM)
    # Percentage
    if label:
        win.addstr(y, x + w + 1, f"{label}{pct:3.0f}%", CP["white"])
    else:
        win.addstr(y, x + w + 1, f"{pct:3.0f}%", CP["white"])


def draw_spark(win, y, x, history, w=30):
    """Draw a sparkline graph."""
    if not history:
        return
    chars = " ▁▂▃▄▅▆▇█"
    data = list(history)[-w:]
    lo, hi = min(data), max(data)
    rng = hi - lo if hi != lo else 1
    for i, v in enumerate(data):
        idx = min(int((v - lo) / rng * 8), 8)
        c = chars[idx]
        color = curses.color_pair(2) if v < 50 else (curses.color_pair(4) if v < 80 else curses.color_pair(3))
        if x + i < curses.getmaxyx(win)[1] - 1:
            win.addstr(y, x + i, c, color)


def safe_add(win, y, x, text, attr=0):
    """Add string safely (clips at window bounds)."""
    h, w = curses.getmaxyx(win)
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    text = text[:w - x - 1]
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


# ═══════════════════════════════════════════════════════════
#  WINDOW RENDERERS
# ═══════════════════════════════════════════════════════════

def draw_cpu(win, cpu_pct, cpu_hist):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " CPU ", CP["cyan"] | curses.A_BOLD)
    safe_add(win, 1, 2, "Usage: ", CP["dim"])
    draw_bar(win, 1, 9, cpu_pct, w - 15)
    draw_spark(win, 2, 2, cpu_hist, w - 5)


def draw_memory(win, ram_used, ram_total, ram_pct, ram_hist):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " MEMORY ", CP["cyan"] | curses.A_BOLD)
    safe_add(win, 1, 2, "Usage: ", CP["dim"])
    draw_bar(win, 1, 9, ram_pct, w - 15)
    safe_add(win, 2, 2, f"{ram_used} / {ram_total}", CP["dim"])
    draw_spark(win, 3, 2, ram_hist, w - 5)


def draw_gpu(win, gpus):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " GPU ", CP["green"] | curses.A_BOLD)

    if not gpus:
        safe_add(win, 1, 2, "No GPU detected", CP["dim"])
        return

    g = gpus[0]
    name = g['name'][:w - 6]
    safe_add(win, 1, 2, name, CP["green"] | curses.A_BOLD)
    safe_add(win, 2, 2, "Util: ", CP["dim"])
    draw_bar(win, 2, 8, g['util'], w - 14)
    safe_add(win, 3, 2, f"Mem: {g['mu']} / {g['mt']}", CP["cyan"])
    temp_color = CP["red"] if g['temp'] > 70 else CP["white"]
    safe_add(win, 4, 2, f"Temp: {g['temp']:.0f}°C", temp_color)


def draw_models(win, fl_ok, fl_s, glm_ok, glm_s, gpus):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " AI MODELS ", CP["pink"] | curses.A_BOLD)

    fl = "● Ready" if fl_ok else "○ Missing"
    fl_c = CP["green"] if fl_ok else CP["red"]
    safe_add(win, 1, 2, "Florence-2  ", CP["dim"])
    safe_add(win, 1, 15, fl, fl_c)
    if fl_ok:
        safe_add(win, 1, 24, f"({fl_s})", CP["dim"])

    glm = "● Ready" if glm_ok else "○ Missing"
    glm_c = CP["green"] if glm_ok else CP["red"]
    safe_add(win, 2, 2, "GLM-OCR     ", CP["dim"])
    safe_add(win, 2, 15, glm, glm_c)
    if glm_ok:
        safe_add(win, 2, 24, f"({glm_s})", CP["dim"])

    device = "GPU" if gpus else "CPU"
    safe_add(win, 3, 2, f"Device: {device}", CP["dim"])


def draw_stats(win, tot, hr, err, last):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " STATISTICS ", CP["gold"] | curses.A_BOLD)
    safe_add(win, 1, 2, "Total:", CP["dim"])
    safe_add(win, 1, 8, str(tot), CP["white"])
    safe_add(win, 1, 14, "Hour:", CP["cyan"])
    safe_add(win, 1, 19, str(hr), CP["white"])
    err_c = CP["green"] if err == 0 else CP["red"]
    safe_add(win, 1, 23, "Err:", err_c)
    safe_add(win, 1, 27, str(err), err_c)
    safe_add(win, 2, 2, f"Last: {last}", CP["dim"])


def draw_top(win, top):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " TOP ACTIONS ", CP["pink"] | curses.A_BOLD)

    if not top:
        safe_add(win, 1, 2, "No actions yet", CP["dim"])
        return

    for i, (name, cnt) in enumerate(top[:h - 2]):
        safe_add(win, i + 1, 2, name[:w - 12], CP["cyan"])
        dots = max(1, w - len(name) - 10)
        safe_add(win, i + 1, 2 + len(name) + 1, "·" * dots, CP["dim"])
        safe_add(win, i + 1, w - 4, str(cnt), CP["white"])


def draw_controls(win):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " CONTROLS ", CP["green"] | curses.A_BOLD)
    keys = [
        ("s", "Start Server"),
        ("x", "Stop Server"),
        ("h", "Health Check"),
        ("d", "Download Models"),
        ("r", "Refresh"),
        ("q", "Quit"),
    ]
    for i, (k, desc) in enumerate(keys):
        safe_add(win, i + 1, 2, k, CP["white"] | curses.A_BOLD)
        safe_add(win, i + 1, 4, f"  {desc}", CP["dim"])


def draw_logs(win, logs, status):
    h, w = curses.getmaxyx(win)
    win.erase()
    win.box()
    safe_add(win, 0, 2, " SERVER LOG ", CP["green"] | curses.A_BOLD)

    log_list = list(logs)[-(h - 3):] if logs else []
    for i, ln in enumerate(log_list):
        safe_add(win, i + 1, 2, ln[:w - 5], CP["dim"])

    # Status bar at bottom of log window
    safe_add(win, h - 2, 2, status, CP["white"] | curses.A_BOLD)


def draw_header(win, elapsed):
    h, w = curses.getmaxyx(win)
    win.erase()
    eh, er = divmod(int(elapsed), 3600)
    em, es = divmod(er, 60)
    title = "UI Agent MCP Dashboard"
    safe_add(win, 0, (w - len(title)) // 2, title, CP["gold"] | curses.A_BOLD | curses.A_UNDERLINE)
    sub = f"Florence-2 + GLM-OCR (Z.AI)  Uptime: {eh:02d}:{em:02d}:{es:02d}"
    safe_add(win, 1, (w - len(sub)) // 2, sub, CP["cyan"])


def draw_statusbar(win, running, last):
    h, w = curses.getmaxyx(win)
    win.erase()
    status = "● RUNNING" if running else "○ STOPPED"
    sc = CP["green"] if running else CP["dim"]
    safe_add(win, 0, 2, status, sc)
    safe_add(win, 0, 16, "q:quit  r:refresh  s:start  x:stop  h:health  d:download", CP["dim"])
    safe_add(win, 0, w - 22, f"Last: {last[:19]}", CP["cyan"])


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def main(stdscr):
    init_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(500)  # 500ms input timeout = refresh rate

    data = Data()
    server_proc = [None]
    server_logs = deque(maxlen=20)
    t0 = time.time()

    def start_server():
        server_logs.append(f"[{datetime.now():%H:%M:%S}] Starting MCP server...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            server_proc[0] = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    server_logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()[:50]}")
        threading.Thread(target=t, daemon=True).start()

    def stop_server():
        sh("pkill -f 'python server.py' || true")
        server_logs.append(f"[{datetime.now():%H:%M:%S}] Server stopped")

    while True:
        # ── Get terminal size ──
        H, W = stdscr.getmaxyx()

        # ── Create windows ──
        # Layout (btop-style grid):
        # Row 0: Header (2 lines)
        # Row 1: CPU | MEMORY
        # Row 2: GPU | AI MODELS
        # Row 3: STATISTICS | TOP ACTIONS
        # Row 4: CONTROLS | SERVER LOG
        # Row 5: Status bar (1 line)

        hw = W // 2
        row_h = (H - 4) // 4  # height per row (minus header 2 + status 2)

        if row_h < 3:
            row_h = 3

        try:
            # Header
            header = curses.newwin(2, W, 0, 0)

            # Row 1: CPU | Memory
            cpu_win = curses.newwin(row_h, hw, 2, 0)
            mem_win = curses.newwin(row_h, hw, 2, hw)

            # Row 2: GPU | Models
            gpu_win = curses.newwin(row_h, hw, 2 + row_h, 0)
            model_win = curses.newwin(row_h, hw, 2 + row_h, hw)

            # Row 3: Stats | Top Actions
            stats_win = curses.newwin(row_h, hw, 2 + row_h * 2, 0)
            top_win = curses.newwin(row_h, hw, 2 + row_h * 2, hw)

            # Row 4: Controls | Logs
            ctrl_win = curses.newwin(row_h, hw, 2 + row_h * 3, 0)
            log_win = curses.newwin(row_h, hw, 2 + row_h * 3, hw)

            # Status bar
            status_win = curses.newwin(2, W, H - 2, 0)

            # ── Draw all windows ──
            draw_header(header, time.time() - t0)

            cpu_pct = data.cpu()
            ru, rt, rpct = data.ram()
            gpus = data.gpu()
            (fl_ok, fl_s), (glm_ok, glm_s) = data.models()
            tot, hr, err, last, top = data.stats()
            running = server_proc[0] and server_proc[0].poll() is None

            draw_cpu(cpu_win, cpu_pct, data.cpu_hist)
            draw_memory(mem_win, ru, rt, rpct, data.ram_hist)
            draw_gpu(gpu_win, gpus)
            draw_models(model_win, fl_ok, fl_s, glm_ok, glm_s, gpus)
            draw_stats(stats_win, tot, hr, err, last)
            draw_top(top_win, top)
            draw_controls(ctrl_win)
            draw_logs(log_win, server_logs, "● Running" if running else "○ Stopped")
            draw_statusbar(status_win, running, last)

            # ── Refresh all at once (flicker-free) ──
            header.noutrefresh()
            cpu_win.noutrefresh()
            mem_win.noutrefresh()
            gpu_win.noutrefresh()
            model_win.noutrefresh()
            stats_win.noutrefresh()
            top_win.noutrefresh()
            ctrl_win.noutrefresh()
            log_win.noutrefresh()
            status_win.noutrefresh()
            curses.doupdate()

        except curses.error:
            pass

        # ── Handle input ──
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord('s'):
            start_server()
        elif key == ord('x'):
            stop_server()
        elif key == ord('r'):
            pass  # auto-refreshes anyway
        elif key == ord('h'):
            server_logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
            threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1"), daemon=True).start()
        elif key == ord('d'):
            server_logs.append(f"[{datetime.now():%H:%M:%S}] Downloading models...")
            threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()

    if server_proc[0]:
        server_proc[0].terminate()


if __name__ == "__main__":
    curses.wrapper(main)
