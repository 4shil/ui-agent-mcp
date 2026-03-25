#!/usr/bin/env python3
"""UI Agent MCP — Btop-Style Dashboard v4 — Fixed."""

import sys, os, time, json, subprocess, threading, shutil, select, re
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

# ── ANSI ──
R  = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
HI = "\033[?25l"
SH = "\033[?25h"
HM = "\033[H"
CL = "\033[2J"
ED = "\033[J"  # erase to end of screen

RED = "\033[1;31m"; GRN = "\033[1;32m"; YEL = "\033[1;33m"
CYN = "\033[1;36m"; WHT = "\033[1;37m"; GRY = "\033[2;37m"
GLD = "\033[1;38;5;220m"; ORG = "\033[1;38;5;208m"; PNK = "\033[1;38;5;213m"

def col(p):
    if p > 80: return RED
    if p > 60: return ORG
    if p > 40: return YEL
    return GRN

def bar(pct, w=18):
    f = int(pct / 100 * w)
    c = col(pct)
    return f"{c}{'█' * f}{D}{'░' * (w - f)}{R} {B}{pct:3.0f}%{R}"

def spark(history, w=20):
    if not history: return D + "─" * w + R
    chars = " ▁▂▃▄▅▆▇█"
    d = list(history)[-w:]
    lo, hi = min(d), max(d)
    rng = hi - lo if hi != lo else 1
    return "".join(chars[min(int((v - lo) / rng * 8), 8)] for v in d)

def sep_line(left, right, w):
    """Render one line of two side-by-side boxes."""
    hw = w // 2
    l = f" {left:<{hw-2}}"[:hw-2]
    r = f" {right:<{hw-2}}"[:hw-2]
    return f"│{l} ││{r} │"


# ═══════════════════════════════════════════════════════════
#  DATA
# ═══════════════════════════════════════════════════════════

class Data:
    def __init__(self):
        self.cpu_h = deque(maxlen=40)
        self.ram_h = deque(maxlen=40)

    def cpu(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try:
            p = max(0, min(100, float(o)))
        except:
            p = 0.0
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


# ═══════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════

class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.data = Data()
        self.srv_logs = deque(maxlen=20)
        self.t0 = time.time()

    def draw(self, W):
        hw = W // 2  # half width for each column

        cpu = self.data.cpu()
        ru, rt, rpct = self.data.ram()
        gpus = self.data.gpu()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.data.models()
        tot, hrs, err, last, top = self.data.stats()
        running = self.proc and self.proc.poll() is None

        el = int(time.time() - self.t0)
        eh, er = divmod(el, 3600)
        em, es = divmod(er, 60)

        out = []

        # ── HEADER (simple, no fancy unicode) ──
        out.append(f"{GLD}{B}  UI Agent MCP Dashboard{R}")
        out.append(f"{CYN}  Florence-2 + GLM-OCR (Z.AI){R}  {D}Uptime: {eh:02d}:{em:02d}:{es:02d}{R}")
        out.append(f"{GLD}{'═' * W}{R}")
        out.append("")

        # ── ROW 1: CPU | MEMORY ──
        out.append(f"{'╭─ CPU ─' + '─' * (hw - 8)}╮{'╭─ MEMORY ─' + '─' * (hw - 11)}╮")
        out.append(sep_line(f"  Use {bar(cpu, hw - 18)}", f"  Use {bar(rpct, hw - 18)}", W))
        out.append(sep_line(f"  Hist {spark(self.data.cpu_h, hw - 16)}", f"  {ru}/{rt}", W))
        out.append(sep_line(f"  {D}Cpu{R}", f"  Hist {spark(self.data.ram_h, hw - 16)}", W))
        out.append(f"{'╰' + '─' * (hw - 1)}╯{'╰' + '─' * (hw - 1)}╯")
        out.append("")

        # ── ROW 2: GPU | MODELS ──
        if gpus:
            g = gpus[0]
            g1 = f"  {GRN}{g['name'][:hw-12]}{R}"
            g2 = f"  Use {bar(g['util'], hw - 18)}"
            tc = RED if g['temp'] > 70 else WHT
            g3 = f"  Mem: {CYN}{g['mu']}/{g['mt']}{R}  {tc}{g['temp']:.0f}°C{R}"
        else:
            g1 = f"  {D}No GPU detected{R}"
            g2 = f"  {D}—{R}"
            g3 = f"  {D}—{R}"

        m1 = f"  Florence-2  {GRN}●{R} Ready ({fl_s})" if fl_ok else f"  Florence-2  {RED}○{R} Missing"
        m2 = f"  GLM-OCR     {GRN}●{R} Ready ({glm_s})" if glm_ok else f"  GLM-OCR     {RED}○{R} Missing"
        m3 = f"  {D}Device: {'GPU' if gpus else 'CPU'}{R}"

        out.append(f"{'╭─ GPU ─' + '─' * (hw - 8)}╮{'╭─ AI MODELS ─' + '─' * (hw - 13)}╮")
        out.append(sep_line(g1, m1, W))
        out.append(sep_line(g2, m2, W))
        out.append(sep_line(g3, m3, W))
        out.append(f"{'╰' + '─' * (hw - 1)}╯{'╰' + '─' * (hw - 1)}╯")
        out.append("")

        # ── ROW 3: STATS | TOP ACTIONS ──
        s1 = f"  {B}Total:{R} {tot}  {CYN}Hr:{R} {hrs}  {RED if err else GRN}Err:{R} {err}"
        s2 = f"  {D}Last: {last}{R}"
        s3 = ""
        s4 = ""

        out.append(f"{'╭─ STATISTICS ─' + '─' * (hw - 14)}╮{'╭─ TOP ACTIONS ─' + '─' * (hw - 15)}╮")
        out.append(sep_line(s1, top[0][0] + f"  {B}{top[0][1]}{R}" if top else "No actions", W))

        t2 = f"{D}·{R} ".join(f"{CYN}{n}{R} {B}{c}{R}" for n, c in top[1:3]) if len(top) > 1 else ""
        out.append(sep_line(s2, t2[:hw-6], W))

        t3 = f"{D}·{R} ".join(f"{CYN}{n}{R} {B}{c}{R}" for n, c in top[3:5]) if len(top) > 3 else ""
        out.append(sep_line(s3, t3[:hw-6], W))
        out.append(sep_line(s4, "", W))
        out.append(f"{'╰' + '─' * (hw - 1)}╯{'╰' + '─' * (hw - 1)}╯")
        out.append("")

        # ── ROW 4: CONTROLS | SERVER LOG ──
        out.append(f"{'╭─ CONTROLS ─' + '─' * (hw - 13)}╮{'╭─ SERVER LOG ─' + '─' * (hw - 14)}╮")
        out.append(sep_line(f"  {B}s{R} Start Server", "", W))

        log_list = list(self.srv_logs)[-5:]
        for i, line in enumerate(log_list):
            ln = line[:hw - 8]
            out.append(sep_line(
                f"  {B}x{R} Stop Server" if i == 0 else "",
                f"{D}{ln}{R}",
                W
            ))

        # Pad remaining log lines
        for i in range(max(0, 4 - len(log_list))):
            out.append(sep_line(
                f"  {B}h{R} Health Check" if i == 0 else (f"  {B}d{R} Download" if i == 1 else ""),
                "",
                W
            ))

        out.append(f"{'╰' + '─' * (hw - 1)}╯{'╰' + '─' * (hw - 1)}╯")
        out.append("")

        # ── STATUS BAR ──
        sc = f"{GRN}● RUNNING{R}" if running else f"{D}○ STOPPED{R}"
        out.append(f"{GLD}{'═' * W}{R}")
        out.append(f"{sc}  {D}q:quit  r:refresh  s:start  x:stop  h:health  d:download{R}  {CYN}{last}{R}")

        return "\n".join(out)

    def start(self):
        self.srv_logs.append(f"[{datetime.now():%H:%M:%S}] Starting...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln and ln.strip():
                    self.srv_logs.append(f"[{datetime.now():%H:%M:%S}] {ln.rstrip()[:60]}")
        threading.Thread(target=t, daemon=True).start()

    def stop(self):
        sh("pkill -f 'python server.py' || true")
        self.srv_logs.append(f"[{datetime.now():%H:%M:%S}] Stopped")

    def render(self):
        W = shutil.get_terminal_size((80, 40)).columns
        H = shutil.get_terminal_size((80, 40)).lines
        sys.stdout.write(HM + CL + self.draw(W))
        sys.stdout.flush()

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
            sys.stdout.write(SH + HM + CL + R)
            sys.stdout.flush()
            if old:
                try:
                    import termios
                    termios.tcsetattr(fd, termios.TCSANOW, old)
                except: pass

        sys.stdout.write(CL)
        sys.stdout.flush()

        def refresher():
            while self.running:
                time.sleep(2)
                try: self.render()
                except: pass
        threading.Thread(target=refresher, daemon=True).start()
        self.render()

        try:
            while self.running:
                if select.select([sys.stdin], [], [], 0.3)[0]:
                    ch = sys.stdin.read(1)
                    if ch == 'q': break
                    elif ch == 'r': self.render()
                    elif ch == 's': self.start(); time.sleep(0.5); self.render()
                    elif ch == 'x': self.stop(); time.sleep(0.5); self.render()
                    elif ch == 'h':
                        self.srv_logs.append(f"[{datetime.now():%H:%M:%S}] Health check...")
                        self.render()
                        threading.Thread(target=lambda: sh(f"cd {BASE} && bash scripts/health_check.sh 2>&1 | tail -5"), daemon=True).start()
                    elif ch == 'd':
                        self.srv_logs.append(f"[{datetime.now():%H:%M:%S}] Downloading models...")
                        self.render()
                        threading.Thread(target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"), daemon=True).start()
        except KeyboardInterrupt: pass
        finally:
            self.running = False
            if self.proc: self.proc.terminate()
            cleanup()
            print(f"\n{GRN}Dashboard closed{R}\n")


if __name__ == "__main__":
    Dashboard().run()
