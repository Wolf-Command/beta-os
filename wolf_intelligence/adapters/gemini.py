"""Gemini — beta configured, free; no paid without Owner policy."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

BETA_ENV = Path("/Users/wolfterminal/beta-os/.env")

def _env_name_present(name: str) -> bool:
    if not BETA_ENV.exists():
        return False
    for line in BETA_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, _v = line.partition("=")
        if k.strip() == name:
            return True
    return False

def _env_has(name: str) -> bool:
    if not BETA_ENV.exists():
        return False
    for line in BETA_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name and v.strip().strip("\"'"'):
            return True
    return False

class GeminiAdapter(WorkerAdapter):
    worker_id = "gemini"
    label = "Gemini"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        has = _env_has("GEMINI_API_KEY")
        name_present = _env_name_present("GEMINI_API_KEY")
        if has:
            return AdapterResult(True, "CONNECTED",
                                 "GEMINI_API_KEY configured; Owner policy=no paid without approval",
                                 {"billing": "free", "paid_allowed": False})
        if name_present:
            return AdapterResult(False, "UNAVAILABLE",
                                 "GEMINI_API_KEY name present in beta .env but value empty; no paid without Owner policy",
                                 {"billing": "free", "paid_allowed": False, "key_name_present": True})
        return AdapterResult(False, "UNAVAILABLE", "GEMINI_API_KEY not configured")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live Gemini call in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — free path only", {"billing": "free"})

register(GeminiAdapter())
