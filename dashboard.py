#!/usr/bin/env python3
"""UI Agent MCP — Btop-Style Dashboard v6 — Pure ANSI, no flicker."""

import sys, os, time, json, subprocess, threading, shutil, select, termios, tty
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
        self.cpu_h = deque(maxlen=40)
        self.ram_h = deque(maxlen=40)

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


# ── ANSI colors ──
RST = "\033[0m"; B = "\033[1m"; D = "\033[2m"
RED = "\033[1;31m"; GRN = "\033[1;32m"; YEL = "\033[1;33m"
CYN = "\033[1;36m"; WHT = "\033[1;37m"; PNK = "\033[1;35m"; GLD = "\033[1;38;5;220m"

def bc(pct):
    if pct > 80: return RED
    if pct > 40: return YEL
    return GRN

def bar(pct, w):
    f = int(pct / 100 * w)
    return f"{bc(pct)}{'█' * f}{D}{'░' * (w - f)}{RST}"

def spark(hist, w):
    if not hist: return D + "─" * w + RST
    chars = "▁▂▃▄▅▆▇█"
    d = list(hist)[-w:]
    lo, hi = min(d), max(d)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in d)

def pad(text, w):
    """Pad text to exact width, strip ANSI for length calc."""
    clean = text.replace('\033', '').partition('m')[-1] if '\033' in text else text
    return text + " " * max(0, w - len(clean))


class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.data = Data()
        self.logs = deque(maxlen=8)
        self.t0 = time.time()

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
                    self.logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()[:35]}")
        threading.Thread(target=t, daemon=True).start()

    def stop(self):
        sh("pkill -f 'python server.py' || true")
        self.logs.append(f"[{datetime.now():%H:%M:%S}] Stopped")

    def draw(self):
        W = shutil.get_terminal_size((100, 40)).columns
        hw = W // 2
        bar_w = min(20, hw - 15)
        spark_w = hw - 12

        cpu = self.data.cpu()
        ru, rt, rpct = self.data.ram()
        gpus = self.data.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.data.models()
        tot, hr, err, last, top = self.data.stats()
        running = self.proc and self.proc.poll() is None
        el = time.time() - self.t0
        eh, er = divmod(int(el), 3600); em, es = divmod(er, 60)

        L = []

        # Header
        L.append(f"{GLD}{'═' * W}{RST}")
        L.append(f"{GLD}{'UI Agent MCP Dashboard':^{W}}{RST}")
        L.append(f"{CYN}{'Florence-2 + GLM-OCR (Z.AI)  |  Up: ' + f'{eh:02d}:{em:02d}:{es:02d}':^{W}}{RST}")
        L.append(f"{GLD}{'═' * W}{RST}")
        L.append("")

        # ── Row 1: CPU + RAM ──
        L.append(f"{'╭─ CPU ─' + '─' * (hw - 8)}╮{'╭─ MEMORY ─' + '─' * (hw - 11)}╮")
        L.append(f"│ Use: {pad(bar(cpu, bar_w), hw - 12)}%││ Use: {pad(bar(rpct, bar_w), hw - 12)}%│")
        L.append(f"│ Hist {pad(spark(self.data.cpu_h, spark_w), hw - 8)}││ {pad(f'{ru} / {rt}', hw - 4)}│")
        L.append(f"│ Hist {pad(spark(self.data.ram_h, spark_w), hw - 8)}││{' ' * (hw - 2)}│")
        L.append(f"│{' ' * (hw - 2)}││{' ' * (hw - 2)}│")
        L.append(f"╰{'─' * (hw - 2)}╯╰{'─' * (hw - 2)}╯")
        L.append("")

        # ── Row 2: GPU + Models ──
        L.append(f"{'╭─ GPU ─' + '─' * (hw - 8)}╮{'╭─ AI MODELS ─' + '─' * (hw - 13)}╮")
        if gpus:
            g = gpus[0]
            L.append(f"│ {pad(g['name'][:hw-4], hw-3)}│")
            L.append(f"│ Use: {pad(bar(g['util'], bar_w), hw - 12)}%│")
            tc = RED if g['temp'] > 70 else WHT
            L.append(f"│ Mem: {pad(f\"{g['mu']}/{g['mt']}\", hw - 10)}│")
            L.append(f"│ Temp:{tc} {g['temp']:.0f}°C{RST}{' ' * max(0, hw - 16)}│")
        else:
            L.append(f"│ {pad('No GPU detected', hw - 3)}│")
            L.append(f"│{pad('', hw - 2)}│")
            L.append(f"│{pad('', hw - 2)}│")
            L.append(f"│{pad('', hw - 2)}│")

        fl = f"{GRN}● Ready{RST} ({fl_s})" if fl_ok else f"{RED}○ Missing{RST}"
        glm = f"{GRN}● Ready{RST} ({glm_s})" if glm_ok else f"{RED}○ Missing{RST}"
        L.append(f"│ Florence-2: {pad(fl, hw - 16)}││ GLM-OCR:    {pad(glm, hw - 16)}│")
        L.append(f"│ Device: {pad('GPU' if gpus else 'CPU', hw - 11)}││{' ' * (hw - 2)}│")
        L.append(f"╰{'─' * (hw - 2)}╯╰{'─' * (hw - 2)}╯")
        L.append("")

        # ── Row 3: Stats + Top Actions ──
        L.append(f"{'╭─ STATISTICS ─' + '─' * (hw - 14)}╮{'╭─ TOP ACTIONS ─' + '─' * (hw - 15)}╮")
        L.append(f"│ {pad(f'Total: {tot}  Hour: {hr}  Err: {err}', hw - 3)}││{' ' * (hw - 2)}│")
        L.append(f"│ {pad(f'Last: {last}', hw - 3)}││{' ' * (hw - 2)}│")
        for i in range(3):
            if i < len(top):
                n, c = top[i]
                dots = max(1, hw - len(n) - len(str(c)) - 8)
                L.append(f"│{' ' * (hw - 2)}││ {n} {'·' * dots} {c}{' ' * max(0, hw - len(n) - len(str(c)) - dots - 8)}│")
            else:
                L.append(f"│{' ' * (hw - 2)}││{' ' * (hw - 2)}│")
        L.append(f"│{' ' * (hw - 2)}││{' ' * (hw - 2)}│")
        L.append(f"╰{'─' * (hw - 2)}╯╰{'─' * (hw - 2)}╯")
        L.append("")

        # ── Row 4: Controls + Logs ──
        L.append(f"{'╭─ CONTROLS ─' + '─' * (hw - 13)}╮{'╭─ SERVER LOG ─' + '─' * (hw - 14)}╮")
        keys = [("s","Start"),("x","Stop"),("h","Health"),("d","Download"),("r","Refresh"),("q","Quit")]
        log_list = list(self.logs)
        for i in range(6):
            k, d = keys[i] if i < len(keys) else ("", "")
            ll = log_list[i] if i < len(log_list) else ""
            L.append(f"│ {k}  {d:<{hw - 6}}││ {ll:<{hw - 4}}│")
        L.append(f"╰{'─' * (hw - 2)}╯╰{'─' * (hw - 2)}╯")
        L.append("")

        # Status bar
        sc = f"{GRN}● RUNNING{RST}" if running else f"{D}○ STOPPED{RST}"
        L.append(f"{GLD}{'═' * W}{RST}")
        L.append(f"{sc}  {D}q:quit  s:start  x:stop  h:health{RST}  {CYN}{last}{RST}")

        return "\n".join(L)

    def run(self):
        old = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdout.write("\033[?25l")  # hide cursor
            sys.stdout.flush()

            while True:
                # Draw
                W = shutil.get_terminal_size((100, 40)).columns
                output = self.draw()
                sys.stdout.write(f"\033[H{output}\033[J")  # HOME + erase to end
                sys.stdout.flush()

                # Wait for input or 2s timeout
                r, _, _ = select.select([sys.stdin], [], [], 2.0)
                if r:
                    ch = sys.stdin.read(1)
                    if ch == 'q': break
                    elif ch == 's': self.start()
                    elif ch == 'x': self.stop()
                    elif ch == 'h':
                        self.logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
                        threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1"), daemon=True).start()
                    elif ch == 'd':
                        self.logs.append(f"[{datetime.now():%H:%M:%S}] Downloading...")
                        threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?25h")  # show cursor
            sys.stdout.write("\033[2J\033[H")  # clear + home
            sys.stdout.flush()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)


if __name__ == "__main__":
    Dashboard().run()
