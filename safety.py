# safety.py — Safety layer for UI agent actions

import time
import json
from config import ACTION_COOLDOWN_MS, MAX_ACTIONS_PER_MINUTE, LOGS_DIR


class SafetyController:
    DESTRUCTIVE_PATTERNS = [
        "rm -rf", "format", "shutdown", "reboot", "dd if=",
        "mkfs", "del /f", "taskkill /f", "chmod 777", "sudo rm", "rm -r /",
    ]

    def __init__(self):
        self._last_action_time = 0
        self._action_count = 0
        self._minute_start = time.time()
        self._emergency_stop = False
        self._action_log_path = LOGS_DIR / "actions.jsonl"
        self._total_actions = 0

    def check_cooldown(self) -> dict | None:
        elapsed = (time.time() - self._last_action_time) * 1000
        if elapsed < ACTION_COOLDOWN_MS:
            return {"status": "error", "error": f"Cooldown active. Wait {ACTION_COOLDOWN_MS - elapsed:.0f}ms"}
        return None

    def check_rate_limit(self) -> dict | None:
        now = time.time()
        if now - self._minute_start > 60:
            self._action_count = 0
            self._minute_start = now
        self._action_count += 1
        if self._action_count > MAX_ACTIONS_PER_MINUTE:
            return {"status": "error", "error": f"Rate limit exceeded ({MAX_ACTIONS_PER_MINUTE}/min)"}
        return None

    def check_emergency_stop(self) -> dict | None:
        if self._emergency_stop:
            return {"status": "error", "error": "EMERGENCY STOP ACTIVE"}
        return None

    def check_destructive(self, action: str, **kwargs) -> dict | None:
        action_str = f"{action} {json.dumps(kwargs)}".lower()
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern in action_str:
                return {"status": "error", "error": f"Destructive action detected: '{pattern}'",
                        "confirmation_required": True}
        return None

    def record_action(self, action: str, status: str, details: dict = None):
        self._last_action_time = time.time()
        self._total_actions += 1
        entry = {"timestamp": time.time(), "time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "action": action, "status": status, "details": details or {}}
        with open(self._action_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def trigger_emergency_stop(self):
        self._emergency_stop = True
        self.record_action("EMERGENCY_STOP", "triggered")

    def reset_emergency_stop(self):
        self._emergency_stop = False
        self.record_action("EMERGENCY_STOP", "reset")

    def get_stats(self) -> dict:
        return {"total_actions": self._total_actions, "actions_this_minute": self._action_count,
                "cooldown_ms": ACTION_COOLDOWN_MS, "max_per_minute": MAX_ACTIONS_PER_MINUTE,
                "emergency_stop": self._emergency_stop}


safety = SafetyController()
