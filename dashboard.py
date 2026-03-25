#!/usr/bin/env python3
"""
UI Agent MCP — Btop-Style TUI Dashboard
Raw terminal rendering, no floating windows.
"""

import sys, os, time, json, subprocess, threading, shutil
from pathlib import Path
from collections import deque

BASE = Path(__file__).parent
LOG = BASE / "logs" / "actions.jsonl"

def sh(c, t=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr).strip()
    except:
        return ""

# ── ANSI Colors ──
class C:
    RST = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    # Colors
    GOLD = "\033[1;38;5;220m"
    CYAN = "\033[1;38;5;39m"
    GREEN = "\033[1;38;5;46m"
    RED = "\033[1;38;5;196m"
    PINK = "\033[1;38;5;213m"
    ORANGE = "\033[1;38;5;208m"
    WHITE = "\033[1;37m"
    DIMW = "\033[2;37m"
    RESET = "\033[0m"

def color(pct):
    if pct > 80: return C.RED
    elif pct > 60: return C.ORANGE
    elif pct > 40: return C.GOLD
    else: return C.GREEN

def bar(pct, w=20):
    filled = int(pct / 100 * w)
    c = color(pct)
    return f"{c}{'█' * filled}{C.DIMW}{'░' * (w - filled)}{C.RESET} {C.BOLD}{pct:3.0f}%{C.RESET}"

def bline(label, pct, w=20):
    return f"  {C.BOLD}{label:>5}{C.RESET} {bar(pct, w)}"


class Dashboard:
    def __init__(self):
        self.running = True
        self.proc = None
        self.logs = deque(maxlen=30)
        self.t0 = time.time()
        self.screen_h = 35

    def cpu_pct(self):
        o = sh("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        try: return max(0, min(100, float(o)))
        except: return 0.0

    def ram_info(self):
        o = sh("free -b | awk '/Mem:/{print $3, $2, $3/$2*100}'")
        p = o.split()
        if len(p) >= 3:
            used, total, pct = int(p[0]), int(p[1]), float(p[2])
            fmt = lambda b: f"{b/1024**3:.1f}GiB" if b > 1024**3 else f"{b/1024**2:.0f}MiB"
            return fmt(used), fmt(total), pct
        return "?", "?", 0.0

    def gpu_info(self):
        o = sh("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null")
        if o and "fail" not in o.lower():
            p = o.split(", ")
            if len(p) >= 5:
                try:
                    return {"name": p[0], "mem": p[1], "mem_t": p[2],
                            "util": float(p[3]), "temp": float(p[4])}
                except: pass
        return None

    def model_info(self):
        m = BASE / "models"
        def chk(n):
            p = m / n
            if p.exists():
                sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                return True, f"{sz/1024**3:.1f}GB"
            return False, "—"
        return chk("Florence-2-base"), chk("GLM-OCR")

    def action_info(self):
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
            try: last = json.loads(lines[-1]).get("time_iso","?")[:19]
            except: pass
        top = sorted(actions.items(), key=lambda x: -x[1])[:5]
        return len(lines), hr, errors, last, top

    def draw(self, W):
        """Render the full dashboard as a string."""
        hw = (W - 5) // 2  # half width for two columns
        elapsed = int(time.time() - self.t0)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)

        # Gather
        cpu = self.cpu_pct()
        ram_used, ram_total, ram_pct = self.ram_info()
        g = self.gpu_info()
        (fl_ok, fl_s), (glm_ok, glm_s) = self.model_info()
        tot, hr_cnt, err, last, top = self.action_info()

        running = self.proc and self.proc.poll() is None
        sep = "─"

        L = []  # lines

        # ── Header ──
        L.append(f"{C.GOLD}{'═' * W}{C.RESET}")
        L.append(f"{C.GOLD}  ╦ ╦╔═╗╔╗   ╔═╗╔═╗╔═╗╔╦╗╦ ╦╦═╗╔╦╗   ╔╦╗╔═╗╔╗╔╦╔╦╗╔═╗╦═╗{C.RESET}")
        L.append(f"{C.GOLD}  ║║║║╣ ╠╩╗  ╠═╣║ ╦╚═╗ ║ ║ ║╠╦╝ ║     ║ ║ ║║║║║ ║ ║╣ ╠╦╝{C.RESET}")
        L.append(f"{C.GOLD}  ╚╩╝╚═╝╚═╝  ╩ ╩╚═╝╚═╝ ╩ ╚═╝╩╚═ ╩     ╩ ╚═╝╝╚╝╩ ╩ ╚═╝╩╚═{C.RESET}")
        L.append(f"{C.CYAN}  Ui:{h:02d}:{m:02d}:{s:02d}   Florence-2 + GLM-OCR (Z.AI){C.RESET}")
        L.append(f"{C.GOLD}{'═' * W}{C.RESET}")
        L.append("")

        # ── CPU + RAM ──
        L.append(f"{C.CYAN}╭{sep * (hw+1)}╮{C.CYAN}╭{sep * (hw+1)}╮{C.RESET}")
        L.append(f"{C.CYAN}│{C.RESET} {C.BOLD}CPU Usage{' ' * max(0, hw - 11)}{C.RESET} {C.CYAN}│{C.RESET} {C.CYAN}│{C.RESET} {C.BOLD}RAM Usage{' ' * max(0, hw - 11)}{C.RESET} {C.CYAN}│{C.RESET}")
        L.append(f"{C.CYAN}│{C.RESET} {bline('', cpu, hw - 8)}  {C.CYAN}│{C.RESET} {C.CYAN}│{C.RESET} {bline('', ram_pct, hw - 8)}  {C.CYAN}│{C.RESET}")
        L.append(f"{C.CYAN}│{C.RESET} {C.DIMW}{' ' * hw}{C.RESET}{C.CYAN}│{C.RESET} {C.CYAN}│{C.RESET} {C.WHITE}{ram_used}/{ram_total}{' ' * max(0, hw - len(ram_used) - len(ram_total) - 3)}{C.RESET} {C.CYAN}│{C.RESET}")
        L.append(f"{C.CYAN}╰{sep * (hw+1)}╯{C.CYAN}╰{sep * (hw+1)}╯{C.RESET}")
        L.append("")

        # ── GPU + Models ──
        L.append(f"{C.GREEN}╭{sep * (hw+1)}╮{C.PINK}╭{sep * (hw+1)}╮{C.RESET}")
        if g:
            gpu_name = g['name'][:hw - 6]
            L.append(f"{C.GREEN}│{C.RESET} {C.GREEN}{gpu_name}{' ' * max(0, hw - len(gpu_name) - 2)}{C.RESET} {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} {C.BOLD}AI Models{' ' * max(0, hw - 12)}{C.RESET} {C.PINK}│{C.RESET}")
            L.append(f"{C.GREEN}│{C.RESET} {bline('Util', g['util'], hw - 8)}  {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET}")

            fl_sfx = f"{C.GREEN}● Ready ({fl_s})" if fl_ok else f"{C.RED}○ Missing"
            glm_sfx = f"{C.GREEN}● Ready ({glm_s})" if glm_ok else f"{C.RED}○ Missing"
            L.append(f"{C.GREEN}│{C.RESET} {bline('Mem', min(100, int(g['mem'].replace('MiB','').replace('GiB','')) / int(g['mem_t'].replace('MiB','').replace('GiB','')) * 100) if g['mem_t'].replace('MiB','').replace('GiB','').isdigit() else 0, hw - 8)}  {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} Florence-2  {fl_sfx}{C.RESET}")

            t = g['temp']
            tc = C.RED if t > 70 else C.WHITE
            L.append(f"{C.GREEN}│{C.RESET} {bline('Temp', min(t, 100), hw - 8)}  {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} GLM-OCR     {glm_sfx}{C.RESET}")
        else:
            L.append(f"{C.GREEN}│{C.RESET} {C.DIMW}No GPU detected{' ' * max(0, hw - 18)}{C.RESET} {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} {C.BOLD}AI Models{' ' * max(0, hw - 12)}{C.RESET} {C.PINK}│{C.RESET}")
            L.append(f"{C.GREEN}│{C.RESET} {C.DIMW}{'—' * hw}{C.RESET} {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} Florence-2  {C.DIMW}—{C.RESET}")
            L.append(f"{C.GREEN}│{C.RESET} {C.DIMW}{'—' * hw}{C.RESET} {C.GREEN}│{C.RESET} {C.PINK}│{C.RESET} GLM-OCR     {C.DIMW}—{C.RESET}")
        L.append(f"{C.GREEN}╰{sep * (hw+1)}╯{C.PINK}╰{sep * (hw+1)}╯{C.RESET}")
        L.append("")

        # ── Stats + Top Actions ──
        L.append(f"{C.GOLD}╭{sep * (hw+1)}╮{C.PINK}╭{sep * (hw+1)}╮{C.RESET}")
        L.append(f"{C.GOLD}│{C.RESET} {C.BOLD}Statistics{' ' * max(0, hw - 12)}{C.RESET} {C.GOLD}│{C.RESET} {C.PINK}│{C.RESET} {C.BOLD}Top Actions{' ' * max(0, hw - 13)}{C.RESET} {C.PINK}│{C.RESET}")

        stat_line = f"Total: {tot}  Hour: {hr_cnt}  Err: {err}"
        padding = max(0, hw - len(stat_line) - 4)
        L.append(f"{C.GOLD}│{C.RESET} {C.WHITE}Total:{C.RESET} {tot}  {C.CYAN}Hour:{C.RESET} {hr_cnt}  {C.RED if err else C.GREEN}Err:{C.RESET} {err}{' ' * padding}{C.GOLD}│{C.RESET}")

        if top:
            for i, (name, cnt) in enumerate(top[:4]):
                dots = max(1, hw - len(name) - len(str(cnt)) - 8)
                L.append(f"{C.GOLD}│{C.RESET} {C.CYAN}{name}{C.RESET} {'·' * dots} {C.WHITE}{cnt}{C.RESET} {C.GOLD}│{C.RESET}")
        else:
            L.append(f"{C.GOLD}│{C.RESET} {C.DIMW}No actions yet{' ' * max(0, hw - 16)}{C.RESET} {C.GOLD}│{C.RESET}")

        L.append(f"{C.GOLD}│{C.RESET} {C.DIMW}Last: {last}{' ' * max(0, hw - len(last) - 8)}{C.RESET} {C.GOLD}│{C.RESET}")
        L.append(f"{C.GOLD}╰{sep * (hw+1)}╯{C.PINK}╰{sep * (hw+1)}╯{C.RESET}")
        L.append("")

        # ── Server Log + Controls ──
        L.append(f"{C.GREEN}╭{sep * (hw+1)}╮{C.GREEN}╭{sep * (hw+1)}╮{C.RESET}")
        L.append(f"{C.GREEN}│{C.RESET} {C.BOLD}Server Log{' ' * max(0, hw - 12)}{C.RESET} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET} {C.BOLD}Controls{' ' * max(0, hw - 10)}{C.RESET} {C.GREEN}│{C.RESET}")

        log_list = list(self.logs)[-5:] if self.logs else []
        for i in range(6):
            if i < len(log_list):
                ln = log_list[i][:hw - 4]
                L.append(f"{C.GREEN}│{C.RESET} {C.DIMW}{ln}{' ' * max(0, hw - len(ln) - 3)}{C.RESET} {C.GREEN}│{C.RESET}")
            else:
                L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET}")

        L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET}  {C.WHITE}s{C.RESET}  Start Server       {C.GREEN}│{C.RESET}")
        L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET}  {C.WHITE}x{C.RESET}  Stop Server        {C.GREEN}│{C.RESET}")
        L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET}  {C.WHITE}h{C.RESET}  Health Check       {C.GREEN}│{C.RESET}")
        L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET}  {C.WHITE}d{C.RESET}  Download Models    {C.GREEN}│{C.RESET}")
        L.append(f"{C.GREEN}│{C.RESET} {' ' * hw} {C.GREEN}│{C.RESET} {C.GREEN}│{C.RESET}  {C.WHITE}q{C.RESET}  Quit               {C.GREEN}│{C.RESET}")
        L.append(f"{C.GREEN}╰{sep * (hw+1)}╯{C.GREEN}╰{sep * (hw+1)}╯{C.RESET}")

        # ── Status bar ──
        L.append(f"{C.GOLD}{'═' * W}{C.RESET}")
        sc = f"{C.GREEN}● Running{C.RESET}" if running else f"{C.DIMW}○ Stopped{C.RESET}"
        L.append(f"{sc}  {C.DIMW}q:quit  r:refresh  s:start  x:stop  h:health{C.RESET}  {C.CYAN}Last: {last}{C.RESET}")

        return "\n".join(L)

    def start_server(self):
        self.logs.append("Starting...")
        def t():
            proc = subprocess.Popen(
                ["bash", "-c", f"cd {BASE} && source .venv/bin/activate && python server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            self.proc = proc
            for ln in iter(proc.stdout.readline, ''):
                if ln:
                    self.logs.append(ln.rstrip())
        threading.Thread(target=t, daemon=True).start()

    def stop_server(self):
        sh("pkill -f 'python server.py' || true")
        self.logs.append("Server stopped")

    def run(self):
        # Raw terminal mode
        fd = sys.stdin.fileno()
        old = None
        try:
            import termios
            old = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSANOW, new)
        except: pass

        # Clear screen
        sys.stdout.write("\033[2J\033[H\033[?25l")
        sys.stdout.flush()

        def cleanup():
            sys.stdout.write("\033[?25h\033[2J\033[H")
            sys.stdout.flush()
            if old:
                try:
                    import termios
                    termios.tcsetattr(fd, termios.TCSANOW, old)
                except: pass

        # Auto-refresh thread
        def refresher():
            while self.running:
                time.sleep(2)
                self.refresh()

        threading.Thread(target=refresher, daemon=True).start()
        self.refresh()

        try:
            while self.running:
                ch = self.getch()
                if ch == 'q':
                    break
                elif ch == 'r':
                    self.refresh()
                elif ch == 's':
                    self.start_server()
                    self.refresh()
                elif ch == 'x':
                    self.stop_server()
                    self.refresh()
                elif ch == 'h':
                    self.logs.append("Health check running...")
                    self.refresh()
                    sh(f"cd {BASE} && bash scripts/health_check.sh &")
                elif ch == 'd':
                    self.logs.append("Downloading models...")
                    self.refresh()
                    threading.Thread(
                        target=lambda: sh(f"cd {BASE} && source .venv/bin/activate && python scripts/download_models.sh"),
                        daemon=True
                    ).start()
        except KeyboardInterrupt:
            pass
        finally:
            cleanup()
            self.running = False
            if self.proc:
                self.proc.terminate()
            print(f"\n{C.GREEN}Dashboard closed{C.RESET}\n")

    def refresh(self):
        W = shutil.get_terminal_size((80, 35)).columns
        H = shutil.get_terminal_size((80, 35)).lines
        output = self.draw(W)
        sys.stdout.write(f"\033[H{output}\033[K")
        sys.stdout.flush()

    def getch(self):
        """Read a single keypress."""
        try:
            import select
            if select.select([sys.stdin], [], [], 0.5)[0]:
                return sys.stdin.read(1)
        except: pass
        return ''


if __name__ == "__main__":
    Dashboard().run()
