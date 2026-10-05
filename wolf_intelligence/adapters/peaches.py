"""Peaches / OpenClaw — CoS only, NOT the intelligence brain."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

OPENCLAW = Path.home() / ".openclaw"
PEACHES_CMD = OPENCLAW / "workspace" / "wolf-system" / "scripts" / "peaches-command-bot.py"

class PeachesAdapter(WorkerAdapter):
    worker_id = "peaches"
    label = "Peaches/OpenClaw CoS"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        evidence = []
        if PEACHES_CMD.exists():
            evidence.append("peaches-command-bot.py present")
        # check process without killing
        try:
            import subprocess
            out = subprocess.check_output(["pgrep", "-fl", "peaches-command"], text=True, stderr=subprocess.DEVNULL)
            if out.strip():
                evidence.append("peaches-command process running")
        except Exception:
            pass
        gw = OPENCLAW / "openclaw.json"
        if gw.exists():
            evidence.append("openclaw.json present")
        if evidence:
            return AdapterResult(True, "CONNECTED" if "running" in " ".join(evidence) else "PARTIAL",
                                 "; ".join(evidence) + " | role=CoS_only_not_brain",
                                 {"role": "cos_only_not_brain"})
        return AdapterResult(False, "UNAVAILABLE", "Peaches/OpenClaw not found")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "CoS submit only in shadow isolate")
        return AdapterResult(True, "SHADOW_OK", "shadow CoS recommend path only", {"note": "not brain"})

register(PeachesAdapter())
