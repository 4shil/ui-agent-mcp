#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style Dashboard
Pure ANSI rendering, no TUI libraries.
Inspired by aristocratos/btop architecture.
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
#  ANSI ESCAPE CODES (btop-style, no library dependency)
# ═══════════════════════════════════════════════════════════

class T:
    """Terminal escape codes."""
    RST   = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"
    ULINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

    # Cursor
    HIDE  = "\033[?25l"
    SHOW  = "\033[?25h"
    HOME  = "\033[H"
    CLEAR = "\033[2J"

    # Colors (foreground)
    BLACK   = "\033[30m"
    RED     = "\033[1;31m"
    GREEN   = "\033[1;32m"
    YELLOW  = "\033[1;33m"
    BLUE    = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    CYAN    = "\033[1;36m"
    WHITE   = "\033[1;37m"
    GRAY    = "\033[2;37m"

    # 256-color
    GOLD    = "\033[1;38;5;220m"
    ORANGE  = "\033[1;38;5;208m"
    PINK    = "\033[1;38;5;213m"
    LIME    = "\033[1;38;5;118m"
    BLUE2   = "\033[1;38;5;39m"
    PURPLE  = "\033[1;38;5;141m"

    @staticmethod
    def goto(r, c):
        return f"\033[{r};{c}H"

    @staticmethod
    def color_pct(pct):
        """Color based on percentage."""
        if pct > 80: return T.RED
        if pct > 60: return T.ORANGE
        if pct > 40: return T.GOLD
        return T.GREEN


# ═══════════════════════════════════════════════════════════
#  DATA COLLECTORS
# ═══════════════════════════════════════════════════════════

class DataCollector:
    """Gathers system data like btop's collectors."""

    def __init__(self):
        self.cpu_history = deque(maxlen=50)
        self.ram_history = deque(maxlen=50)
        self.gpu_history = deque(maxlen=50)

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try:
            pct = max(0, min(100, float(o)))
        except:
            pct = 0.0
        self.cpu_history.append(pct)
        return pct

    def ram(self):
        o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
        p = o.split()
        if len(p) >= 3:
            used, total, pct = int(p[0]), int(p[1]), float(p[2])
        else:
            used, total, pct = 0, 1, 0.0
        self.ram_history.append(pct)

        def fmt(b):
            if b >= 1024**3: return f"{b/1024**3:.1f} GiB"
            if b >= 1024**2: return f"{b/1024**2:.0f} MiB"
            return f"{b/1024:.0f} KiB"
        return fmt(used), fmt(total), pct, used/total

    def gpu(self):
        o = sh("nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,fan.speed --format=csv,noheader 2>/dev/null")
        gpus = []
        for line in o.split("\n"):
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 7:
                try:
                    gpus.append({
                        "idx": p[0],
                        "name": p[1],
                        "mem_used": p[2],
                        "mem_total": p[3],
                        "util": float(p[4]),
                        "temp": float(p[5]),
                        "fan": float(p[6]),
                    })
                except: pass
        return gpus

    def models(self):
        m = BASE / "models"
        def chk(n):
            p = m / n
            if p.exists():
                files = list(p.rglob("*"))
                sz = sum(f.stat().st_size for f in files if f.is_file())
                nf = len([f for f in files if f.is_file()])
                return True, sz, nf
            return False, 0, 0
        return chk("Florence-2-base"), chk("GLM-OCR")

    def logs(self):
        if not LOG.exists():
            return 0, 0, 0, "Never", []
        lines = LOG.read_text().strip().split("\n") if LOG.read_text().strip() else []
        errors = sum(1 for l in lines if "error" in l.lower())
        one_hr = time.time() - 3600
        hr = 0
        actions = {}
        for l in lines:
            try:
                e = json.loads(l)
                if e.get("timestamp", 0) > one_hr: hr += 1
                a = e.get("action", "?")
                actions[a] = actions.get(a, 0) + 1
            except: pass
        last = "Never"
        if lines:
            try: last = json.loads(lines[-1]).get("time_iso","?")
            except: pass
        top = sorted(actions.items(), key=lambda x: -x[1])[:8]
        return len(lines), hr, errors, last, top


# ═══════════════════════════════════════════════════════════
#  RENDERERS (btop-style box drawing)
# ═══════════════════════════════════════════════════════════

def sparkline(history, w=20):
    """Render a sparkline graph like btop."""
    if not history:
        return " " * w
    chars = " ▁▂▃▄▅▆▇█"
    data = list(history)[-w:]
    lo, hi = min(data), max(data)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in data)

def bar(pct, w=20):
    """Colored bar like btop."""
    filled = int(pct / 100 * w)
    c = T.color_pct(pct)
    return f"{c}{'█' * filled}{T.DIM}{'░' * (w - filled)}{T.RST} {T.BOLD}{pct:3.0f}%{T.RST}"

def box_top(title, w):
    """╭─ Title ──────────╮"""
    tl = len(title) + 4
    pad = max(0, w - tl - 2)
    return f"╭─ {T.BOLD}{title}{T.RST} {'─' * pad}╮"

def box_bot(w):
    return f"╰{'─' * w}╯"

def box_line(content, w):
    inner = w - 2
    return f"│ {content:<{inner}}│"


# ═══════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════

class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.collector = DataCollector()
        self.server_logs = deque(maxlen=25)
        self.t0 = time.time()
        self.last_keys = []

    def draw(self, W):
        """Render full dashboard. W = terminal width."""
        H = shutil.get_terminal_size((80, 40)).lines
        hw = (W - 5) // 2  # half width inside boxes

        # Collect data
        cpu_pct = self.collector.cpu()
        ram_used, ram_total, ram_pct, ram_ratio = self.collector.ram()
        gpus = self.collector.gpu()
        (fl_ok, fl_sz, fl_n), (glm_ok, glm_sz, glm_n) = self.collector.models()
        tot, hr, err, last, top = self.collector.logs()

        elapsed = int(time.time() - self.t0)
        eh, er = divmod(elapsed, 3600)
        em, es = divmod(er, 60)

        running = self.proc and self.proc.poll() is None

        L = []  # output lines
        r = 1   # current row

        # ── HEADER ──
        L.append(f"{T.GOLD}{T.BOLD}  ╦═╗╔═╗╔╗ ╦  ╔═╗╔═╗╔═╗╔╦╗  ╔═╗╔═╗╔═╗╔╦╗╦ ╦╦═╗╔╦╗{T.RST}")
        L.append(f"{T.GOLD}{T.BOLD}  ╠╦╝║╣ ╠╩╗║  ╠═╣║ ╦╚═╗ ║   ╠═╣║ ╦╚═╗ ║ ║ ║╠╦╝ ║ {T.RST}")
        L.append(f"{T.GOLD}{T.BOLD}  ╩╚═╚═╝╚═╝╩═╝╩ ╩╚═╝╚═╝ ╩   ╩ ╩╚═╝╚═╝ ╩ ╚═╝╩╚═ ╩ {T.RST}")
        L.append(f"{T.CYAN}  Florence-2 + GLM-OCR (Z.AI){T.RST}   {T.DIM}Ui:{eh:02d}:{em:02d}:{es:02d}{T.RST}")
        L.append(f"{T.GOLD}{'═' * W}{T.RST}")
        L.append("")

        # ── CPU ──
        L.append(box_top("CPU", hw))
        L.append(box_line(f"{T.BOLD}Processor:{T.RST}  {bar(cpu_pct, hw - 16)}", hw))
        L.append(box_line(f"{T.DIM}History:  {T.RST}{sparkline(self.collector.cpu_history, hw - 14)}", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── RAM ──
        L.append(box_top("MEMORY", hw))
        L.append(box_line(f"{T.BOLD}RAM:      {T.RST}  {bar(ram_pct, hw - 16)}", hw))
        L.append(box_line(f"{T.DIM}Used:{T.RST} {ram_used} {T.DIM}/{T.RST} {ram_total}  {T.DIM}History:{T.RST} {sparkline(self.collector.ram_history, hw - 28)}", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── GPU ──
        L.append(box_top("GPU", hw))
        if gpus:
            for g in gpus:
                name = g['name'][:hw - 8]
                L.append(box_line(f"{T.GREEN}{name}{T.RST}", hw))
                L.append(box_line(f"  Util {bar(g['util'], hw - 14)}", hw))
                L.append(box_line(f"  Mem  {T.CYAN}{g['mem_used']}/{g['mem_total']}{T.RST}", hw))
                tc = T.RED if g['temp'] > 70 else T.WHITE
                L.append(box_line(f"  Temp {tc}{g['temp']:.0f}°C{T.RST}  Fan {g['fan']:.0f}%", hw))
        else:
            L.append(box_line(f"{T.DIM}No GPU detected{T.RST}", hw))
            L.append(box_line("", hw))
            L.append(box_line("", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── Models ──
        L.append(box_top("AI MODELS", hw))
        fl = f"{T.GREEN}● Ready{T.RST} ({fl_sz/1024**3:.1f}GB, {fl_n} files)" if fl_ok else f"{T.RED}○ Missing{T.RST}"
        glm = f"{T.GREEN}● Ready{T.RST} ({glm_sz/1024**3:.1f}GB, {glm_n} files)" if glm_ok else f"{T.RED}○ Missing{T.RST}"
        L.append(box_line(f"  Florence-2  {fl}", hw))
        L.append(box_line(f"  GLM-OCR     {glm}", hw))
        L.append(box_line(f"  {T.DIM}Device: {'GPU' if any(self.collector.gpu()) else 'CPU'}{T.RST}", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── Stats ──
        L.append(box_top("ACTION STATISTICS", hw))
        L.append(box_line(f"  {T.BOLD}Total:{T.RST} {tot}   {T.CYAN}Hour:{T.RST} {hr}   {T.RED if err else T.GREEN}Errors:{T.RST} {err}", hw))
        L.append(box_line(f"  {T.DIM}Last: {last}{T.RST}", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── Top Actions ──
        L.append(box_top("TOP ACTIONS", hw))
        if top:
            for name, cnt in top[:6]:
                dots = max(2, hw - len(name) - len(str(cnt)) - 10)
                L.append(box_line(f"  {T.CYAN}{name}{T.RST} {'·' * dots} {T.BOLD}{cnt}{T.RST}", hw))
        else:
            L.append(box_line(f"  {T.DIM}No actions yet{T.RST}", hw))
        L.append(box_bot(hw))
        L.append("")

        # ── Server Log ──
        L.append(box_top("SERVER LOG", W - 2))
        log_list = list(self.server_logs)[-7:] if self.server_logs else []
        for i in range(7):
            if i < len(log_list):
                ln = log_list[i][:W - 6]
                L.append(f"│ {T.DIM}{ln}{T.RST}{' ' * max(0, W - 5 - len(ln))}│")
            else:
                L.append(f"│{' ' * (W - 3)}│")
        L.append(box_bot(W - 2))
        L.append("")

        # ── Status bar ──
        sc = f"{T.GREEN}● RUNNING{T.RST}" if running else f"{T.DIM}○ STOPPED{T.RST}"
        L.append(f"{T.GOLD}{'═' * W}{T.RST}")
        L.append(f"{sc}  {T.DIM}q:quit  r:refresh  s:start  x:stop  h:health  d:download models{T.RST}")

        return "\n".join(L)

    def start_server(self):
        self.server_logs.append(f"[{datetime.now():%H:%M:%S}] Starting MCP server...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    self.server_logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()}")
        threading.Thread(target=t, daemon=True).start()

    def stop_server(self):
        sh("pkill -f 'python server.py' || true")
        self.server_logs.append(f"[{datetime.now():%H:%M:%S}] Server stopped")

    def run(self):
        # Save terminal state
        fd = sys.stdin.fileno()
        old_term = None
        try:
            import termios
            old_term = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSANOW, new)
        except: pass

        def cleanup():
            sys.stdout.write(T.SHOW + T.HOME + T.CLEAR)
            sys.stdout.flush()
            if old_term:
                try:
                    import termios
                    termios.tcsetattr(fd, termios.TCSANOW, old_term)
                except: pass

        # Initial render
        sys.stdout.write(T.CLEAR + T.HOME + T.HIDE)
        sys.stdout.flush()

        # Refresher
        def refresh_loop():
            while self.running:
                time.sleep(2)
                self.render()

        threading.Thread(target=refresh_loop, daemon=True).start()
        self.render()

        # Input loop
        try:
            while self.running:
                if select.select([sys.stdin], [], [], 0.3)[0]:
                    ch = sys.stdin.read(1)
                    if ch == 'q':
                        break
                    elif ch == 'r':
                        self.render()
                    elif ch == 's':
                        self.start_server()
                        time.sleep(0.3)
                        self.render()
                    elif ch == 'x':
                        self.stop_server()
                        time.sleep(0.3)
                        self.render()
                    elif ch == 'h':
                        self.server_logs.append(f"[{datetime.now():%H:%M:%S}] Running health check...")
                        self.render()
                        threading.Thread(
                            target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh"),
                            daemon=True
                        ).start()
                    elif ch == 'd':
                        self.server_logs.append(f"[{datetime.now():%H:%M:%S}] Downloading models...")
                        self.render()
                        threading.Thread(
                            target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"),
                            daemon=True
                        ).start()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if self.proc:
                self.proc.terminate()
            cleanup()
            print(f"\n{T.GREEN}Dashboard closed. Goodbye!{T.RST}\n")

    def render(self):
        W = shutil.get_terminal_size((80, 40)).columns
        output = self.draw(W)
        sys.stdout.write(T.HOME + output + T.RST)
        # Clear rest of screen
        sys.stdout.write(T.RST)
        sys.stdout.flush()


if __name__ == "__main__":
    Dashboard().run()
