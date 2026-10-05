"""OpenAI — ChatGPT subscription vs API kept as separate workers."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

BETA_ENV = Path("/Users/wolfterminal/beta-os/.env")

def _env_has(name: str) -> bool:
    if not BETA_ENV.exists():
        return False
    for line in BETA_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name and v.strip():
            return True
    return False

class OpenAIChatGPTAdapter(WorkerAdapter):
    worker_id = "openai_chatgpt"
    label = "OpenAI ChatGPT (subscription)"
    supports = frozenset({"health"})

    def health(self) -> AdapterResult:
        # ChatGPT sub is app-side; we cannot prove plan without secrets UI.
        codex = Path.home() / ".codex"
        evidence = []
        if codex.exists():
            evidence.append("~/.codex present (may be API/Codex, not ChatGPT sub)")
        return AdapterResult(True, "PARTIAL",
                             "ChatGPT subscription status UNKNOWN without account UI; separate from API. " + "; ".join(evidence),
                             {"billing": "subscription"})

class OpenAIAPIAdapter(WorkerAdapter):
    worker_id = "openai_api"
    label = "OpenAI API"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        has = _env_has("OPENAI_API_KEY")
        dry = _env_has("BETA_LLM_DRY_RUN")
        if has:
            return AdapterResult(True, "CONNECTED",
                                 f"OPENAI_API_KEY configured (value not read); BETA_LLM_DRY_RUN={'yes' if dry else 'no'}",
                                 {"billing": "api", "key_configured": True, "dry_run_flag": dry})
        return AdapterResult(False, "UNAVAILABLE", "OPENAI_API_KEY not configured")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live OpenAI API call in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — no tokens spent", {"billing": "api"})

register(OpenAIChatGPTAdapter())
register(OpenAIAPIAdapter())
