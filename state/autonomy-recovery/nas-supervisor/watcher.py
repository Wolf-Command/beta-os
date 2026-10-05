#!/usr/bin/env python3
"""NAS-side autonomy supervisor (runs on always-on NAS, NOT on Studio/Grok/Peaches).

Design (Owner P0 2026-10-06):
  heartbeat miss threshold (default 3 misses @ 60s)
  → recovery attempt via forced command (status then recover-watchdog)
  → exponential backoff (no restart loops)
  → escalation record only when auto recovery failed AND no safe alt worker path

This module is safe to unit-test on the box with a fake transport.
Deploy target (when NAS reachable): 
  /var/services/homes/Mr Wolf/.ssh/wolf-recovery/watcher_v2.py
Invoked by existing DSM task or a tighter 60s schedule.

Never prints secrets. Never opens public ports. Never touches Prod.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Makassar")

DEFAULT_MISS_THRESHOLD = 3
DEFAULT_INTERVAL_SEC = 60
BACKOFF_SCHEDULE = (60, 180, 600, 1800)  # exp backoff after recover attempts


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


@dataclass
class SupervisorState:
    armed: bool = True
    consecutive_misses: int = 0
    last_status_ok: Optional[str] = None
    last_recovery_at: Optional[str] = None
    recovery_attempts: int = 0
    last_backoff_sec: int = 0
    next_eligible_at_epoch: float = 0.0
    last_event: str = "init"
    escalate_human: bool = False
    escalate_reason: Optional[str] = None


class Transport:
    """Abstract NAS→Studio forced-command client."""

    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    def recover_watchdog(self) -> dict[str, Any]:
        raise NotImplementedError


class FakeTransport(Transport):
    """In-memory transport for unit tests / drills without touching Studio."""

    def __init__(self):
        self.grok_up = True
        self.status_calls = 0
        self.recover_calls = 0
        self.fail_status = False

    def status(self) -> dict[str, Any]:
        self.status_calls += 1
        if self.fail_status:
            return {"ok": False, "error": "STATUS_FAIL"}
        return {
            "ok": True,
            "GROK_APP": "UP" if self.grok_up else "NONE",
            "keepalive": "UP" if self.grok_up else "DOWN",
        }

    def recover_watchdog(self) -> dict[str, Any]:
        self.recover_calls += 1
        # Simulate recovery success after first recover
        self.grok_up = True
        return {"ok": True, "result": "RECOVER_WATCHDOG_DONE"}


def parse_control_up(status: dict[str, Any]) -> bool:
    if not status.get("ok"):
        return False
    grok = str(status.get("GROK_APP") or "").upper()
    keep = str(status.get("keepalive") or "").upper()
    if grok in ("NONE", "DOWN", ""):
        return False
    if keep == "DOWN":
        return False
    return True


class NasSupervisor:
    def __init__(
        self,
        transport: Transport,
        state_path: Path,
        audit_path: Path,
        *,
        miss_threshold: int = DEFAULT_MISS_THRESHOLD,
        interval_sec: int = DEFAULT_INTERVAL_SEC,
        alt_worker_available: Callable[[], bool] | None = None,
    ):
        self.transport = transport
        self.state_path = state_path
        self.audit_path = audit_path
        self.miss_threshold = miss_threshold
        self.interval_sec = interval_sec
        self.alt_worker_available = alt_worker_available or (lambda: False)
        self.state = self._load()

    def _load(self) -> SupervisorState:
        if self.state_path.exists():
            try:
                d = json.loads(self.state_path.read_text())
                return SupervisorState(**{k: v for k, v in d.items() if k in SupervisorState.__dataclass_fields__})
            except Exception:
                pass
        return SupervisorState()

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(self.state), indent=2) + "\n")

    def _audit(self, event: str, detail: dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts_wita": now_iso(), "event": event, **detail}
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def tick(self, *, now_epoch: float | None = None) -> SupervisorState:
        now = now_epoch if now_epoch is not None else time.time()
        status = self.transport.status()
        up = parse_control_up(status)

        if up:
            was_down = self.state.consecutive_misses > 0 or not self.state.armed
            self.state.consecutive_misses = 0
            self.state.last_status_ok = now_iso()
            self.state.armed = True
            self.state.escalate_human = False
            self.state.escalate_reason = None
            self.state.last_event = "status_up"
            self._audit("status_up", {"status": status, "rearmed": was_down})
            self._save()
            return self.state

        # miss
        self.state.consecutive_misses += 1
        self.state.last_event = "status_miss"
        self._audit("status_miss", {"misses": self.state.consecutive_misses, "status": status})

        if self.state.consecutive_misses < self.miss_threshold:
            self._save()
            return self.state

        # threshold reached — attempt recover if armed and backoff elapsed
        if not self.state.armed:
            self.state.last_event = "latched_wait_rearm"
            self._audit("latched_wait_rearm", {"misses": self.state.consecutive_misses})
            self._maybe_escalate()
            self._save()
            return self.state

        if now < self.state.next_eligible_at_epoch:
            self.state.last_event = "backoff_hold"
            self._audit("backoff_hold", {"next_eligible_at_epoch": self.state.next_eligible_at_epoch})
            self._save()
            return self.state

        # fire recover once, then latch until status_up
        result = self.transport.recover_watchdog()
        self.state.recovery_attempts += 1
        self.state.last_recovery_at = now_iso()
        self.state.armed = False  # latch
        idx = min(self.state.recovery_attempts - 1, len(BACKOFF_SCHEDULE) - 1)
        backoff = BACKOFF_SCHEDULE[idx]
        self.state.last_backoff_sec = backoff
        self.state.next_eligible_at_epoch = now + backoff
        self.state.last_event = "recover_fired"
        self._audit("recover_fired", {"result": result, "backoff_sec": backoff, "attempt": self.state.recovery_attempts})
        self._maybe_escalate()
        self._save()
        return self.state

    def _maybe_escalate(self) -> None:
        # Escalate to human ONLY if auto recovery latched AND no safe alt worker path
        if self.alt_worker_available():
            self.state.escalate_human = False
            self.state.escalate_reason = "alt_worker_available_no_human"
            self._audit("no_human_escalate", {"reason": self.state.escalate_reason})
            return
        if self.state.recovery_attempts >= len(BACKOFF_SCHEDULE) and not self.state.armed:
            self.state.escalate_human = True
            self.state.escalate_reason = "auto_recovery_exhausted_no_alt_worker"
            self._audit("escalate_human", {"reason": self.state.escalate_reason})


def main() -> None:
    # Production entry on NAS would wire real SSH transport here.
    # On box, refuse real Studio contact — no key/route.
    root = Path(os.environ.get("WOLF_RECOVERY_ROOT", "/tmp/wolf-recovery-sim"))
    root.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"error": "REAL_TRANSPORT_NOT_WIRED_ON_BOX", "hint": "run unit tests / FakeTransport drill"}))


if __name__ == "__main__":
    main()
