"""Cursor adapter — wraps bf_cursor_launch paths. Shadow: no live cursor-agent spawn."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

BETA = Path("/Users/wolfterminal/beta-os")
LAUNCH = BETA / "scripts" / "build-factory" / "bf_cursor_launch.sh"

class CursorAdapter(WorkerAdapter):
    worker_id = "cursor"
    label = "Cursor"
    supports = frozenset({"health", "submit", "status", "cancel", "result"})

    def health(self) -> AdapterResult:
        evidence = []
        if LAUNCH.exists():
            evidence.append("bf_cursor_launch.sh present")
        cursor_home = Path.home() / ".cursor"
        if cursor_home.exists():
            evidence.append("~/.cursor present")
        # which cursor-agent?
        import shutil
        ca = shutil.which("cursor-agent")
        if ca:
            evidence.append(f"cursor-agent on PATH: {ca}")
        if evidence:
            status = "CONNECTED" if LAUNCH.exists() else "PARTIAL"
            return AdapterResult(True, status, "; ".join(evidence), {"launch": str(LAUNCH)})
        return AdapterResult(False, "UNAVAILABLE", "no cursor launch path")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "refusing live cursor-agent in shadow mode")
        return AdapterResult(True, "SHADOW_OK", "shadow only — would have used bf_cursor_launch", {"prompt_chars": len(job.get("prompt") or "")})

    def status(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow", {"handle": handle})

    def cancel(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow cancel noop — never kills workers", {"handle": handle})

    def result(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow result", {"handle": handle, "output": "SHADOW_NO_EXEC"})

register(CursorAdapter())
