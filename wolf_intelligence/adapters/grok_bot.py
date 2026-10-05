"""Grok Bot adapter — local-exec / ~/.grokbot. Phase 1 health stub; Phase 2 deepens."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

GROKBOT = Path.home() / ".grokbot"

class GrokBotAdapter(WorkerAdapter):
    worker_id = "grok_bot"
    label = "Grok Bot"
    supports = frozenset({"health", "submit", "status", "result"})

    def health(self) -> AdapterResult:
        daemon = GROKBOT / "local-exec-daemon.json"
        settings = GROKBOT / "settings.json"
        evidence = []
        if settings.exists():
            evidence.append("settings.json present")
        if daemon.exists():
            evidence.append("local-exec-daemon.json present")
        conn = GROKBOT / "local-exec-daemon-connection.json"
        if conn.exists():
            evidence.append("daemon-connection present")
        if evidence:
            return AdapterResult(True, "CONNECTED", "; ".join(evidence), {"path": str(GROKBOT)})
        return AdapterResult(False, "UNAVAILABLE", "~/.grokbot missing key state")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        # Shadow: never spawn a real expensive Grok session from control plane Phase 1
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "non-isolated submit refused in shadow mode")
        return AdapterResult(True, "SHADOW_OK", "shadow recommend-only; no live Grok spawn", {"echo": job.get("prompt", "")[:200]})

    def status(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow status", {"handle": handle, "state": "shadow_idle"})

    def result(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow result placeholder", {"handle": handle, "output": "SHADOW_NO_EXEC"})

register(GrokBotAdapter())
