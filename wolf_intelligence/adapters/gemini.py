"""Gemini — beta configured, free; no paid without Owner policy."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import AdapterResult, WorkerAdapter, register
from .live_gate import (
    enforce_cost_cap,
    env_enabled,
    execute_requested,
    http_json,
    ledger_provider_call,
    live_disabled,
    providers_mocked,
    read_secret,
    safe_excerpt,
)

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
        if k.strip() == name and v.strip().strip("\"'"):
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
            return AdapterResult(
                True,
                "CONNECTED",
                "GEMINI_API_KEY configured; Owner policy=no paid without approval",
                {"billing": "free", "paid_allowed": False},
            )
        if name_present:
            return AdapterResult(
                False,
                "UNAVAILABLE",
                "GEMINI_API_KEY name present in beta .env but value empty; no paid without Owner policy",
                {"billing": "free", "paid_allowed": False, "key_name_present": True},
            )
        return AdapterResult(False, "UNAVAILABLE", "GEMINI_API_KEY not configured")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            if not env_enabled():
                return live_disabled()
            return self._live(job)
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live Gemini call in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — free path only", {"billing": "free", "provider_called": False})

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        key = read_secret("GEMINI_API_KEY") or read_secret("GOOGLE_API_KEY")
        if not key:
            return AdapterResult(False, "UNAVAILABLE", "GEMINI_API_KEY absent. No provider call.", {"provider_called": False})
        model_id = str(job.get("model") or "gemini-2.0-flash")
        if any(token in model_id.lower() for token in ("pro", "ultra", "paid")):
            return AdapterResult(False, "GATED", "paid Gemini model blocked", {"provider_called": False})
        try:
            max_tokens = max(1, min(int(job.get("num_predict") or 64), 128))
        except (TypeError, ValueError):
            max_tokens = 64
        # Free tier is expected, but a billed key would be charged: the cap still applies.
        refusal, cap, estimate = enforce_cost_cap(
            job, model_id=model_id, prompt=str(job.get("prompt") or ""), max_output_tokens=max_tokens
        )
        if refusal is not None:
            return refusal
        started = time.perf_counter()
        parsed, raw, err = http_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
            {
                "contents": [{"parts": [{"text": str(job.get("prompt") or "")}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
            {"x-goog-api-key": key, "Content-Type": "application/json"},
            timeout=float(job.get("timeout_s") or 30),
            secrets=[key],
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if err or not parsed:
            return AdapterResult(False, "ERROR", err or "empty_response", {"provider_called": True, "latency_ms": latency_ms, "mocked": providers_mocked()})
        output = ""
        try:
            output = safe_excerpt(parsed["candidates"][0]["content"]["parts"][0]["text"] or "", [key])
        except (KeyError, IndexError, TypeError):
            output = safe_excerpt(raw, [key])
        usage = {"pool_id": "gemini_free", "amount_usd": 0.0, "metered_usd": 0.0, "max_cost_usd": cap, "estimated_max_usd": estimate}
        ledger_provider_call(
            worker_id="gemini",
            model_id=model_id,
            work_item_id=job.get("work_item_id"),
            amount_usd=0.0,
            metered_usd=0.0,
            note="gemini free tier; no paid model",
            shadow_mode=bool(job.get("shadow_mode")),
            latency_ms=latency_ms,
            status="LIVE_OK",
            ok=True,
            output_excerpt=output,
            label=str(job.get("label") or "LIVE_SUBMIT"),
        )
        return AdapterResult(
            True,
            "LIVE_OK",
            "gemini generateContent free tier",
            {
                "output": output,
                "latency_ms": latency_ms,
                "model_id": model_id,
                "provider_called": True,
                "mocked": providers_mocked(),
                "usage": usage,
                "took_action": False,
                "billing": "free",
            },
            usage=usage,
        )


register(GeminiAdapter())
