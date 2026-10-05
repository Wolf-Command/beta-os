"""Ollama local :11434 — mark RETIRE CANDIDATE if unused/poor; do not delete."""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

class OllamaAdapter(WorkerAdapter):
    worker_id = "ollama"
    label = "Ollama"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as resp:
                data = json.loads(resp.read().decode())
            models = [m.get("name") for m in data.get("models") or []]
            return AdapterResult(True, "CONNECTED",
                                 f"ollama :11434 up; models={models}",
                                 {"models": models, "retire_candidate": "PENDING_PHASE2_CALLER_AUDIT"})
        except Exception as e:
            return AdapterResult(False, "UNAVAILABLE", f"ollama :11434 not reachable: {type(e).__name__}")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "shadow only")
        # Safe isolated: tags ping only, no generate (avoid GPU burn)
        return AdapterResult(True, "SHADOW_OK", "shadow — no generate invoked", {"billing": "local"})

register(OllamaAdapter())
