"""OpenAI — ChatGPT subscription vs API kept as separate workers."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import AdapterResult, WorkerAdapter, register
from .live_gate import (
    cost_cap,
    env_enabled,
    execute_requested,
    http_json,
    ledger_provider_call,
    live_disabled,
    providers_mocked,
    read_secret,
    safe_excerpt,
    unsupported,
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


class OpenAIChatGPTAdapter(WorkerAdapter):
    worker_id = "openai_chatgpt"
    label = "OpenAI ChatGPT (subscription)"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        codex = Path.home() / ".codex"
        evidence = []
        if codex.exists():
            evidence.append("~/.codex present (may be API/Codex, not ChatGPT sub)")
        return AdapterResult(
            True,
            "PARTIAL",
            "ChatGPT subscription status UNKNOWN without account UI; separate from API. "
            + "; ".join(evidence),
            {"billing": "subscription"},
        )

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            return unsupported(
                "openai_chatgpt is health-only. ChatGPT plan USD is UNKNOWN. "
                "No subscription submit. Not the openai_api pool."
            )
        if job.get("shadow_isolated"):
            return AdapterResult(
                True,
                "SHADOW_OK",
                "health-only; shadow ping is not a live submit",
                {"provider_called": False, "billing": "subscription"},
            )
        return unsupported("openai_chatgpt submit is not supported")


class OpenAIAPIAdapter(WorkerAdapter):
    worker_id = "openai_api"
    label = "OpenAI API"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        has = _env_has("OPENAI_API_KEY")
        dry = _env_has("BETA_LLM_DRY_RUN")
        name_present = _env_name_present("OPENAI_API_KEY")
        if has:
            return AdapterResult(
                True,
                "CONNECTED",
                f"OPENAI_API_KEY configured (value not read); BETA_LLM_DRY_RUN={'yes' if dry else 'no'}",
                {"billing": "api", "key_configured": True, "dry_run_flag": dry},
            )
        if name_present:
            return AdapterResult(
                False,
                "UNAVAILABLE",
                "OPENAI_API_KEY name present in beta .env but value empty; ChatGPT sub is separate pool",
                {"billing": "api", "key_name_present": True, "key_configured": False, "dry_run_flag": dry},
            )
        return AdapterResult(False, "UNAVAILABLE", "OPENAI_API_KEY not configured")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            if not env_enabled():
                return live_disabled()
            return self._live(job)
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live OpenAI API call in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — no tokens spent", {"billing": "api", "provider_called": False})

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        key = read_secret("OPENAI_API_KEY")
        if not key:
            return AdapterResult(False, "UNAVAILABLE", "OPENAI_API_KEY absent. No provider call.", {"provider_called": False})
        cap = cost_cap(job)
        if cap is None:
            return AdapterResult(False, "GATED", "per-call cost cap not configured. No provider call.", {"provider_called": False})
        if cap == 0:
            return AdapterResult(False, "GATED", "per-call cost cap is 0. Refusing paid API call.", {"provider_called": False})
        model_id = str(job.get("model") or "gpt-4o-mini")
        try:
            max_tokens = max(1, min(int(job.get("num_predict") or 64), 128))
        except (TypeError, ValueError):
            max_tokens = 64
        started = time.perf_counter()
        parsed, raw, err = http_json(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": model_id,
                "messages": [{"role": "user", "content": str(job.get("prompt") or "")}],
                "max_tokens": max_tokens,
            },
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=float(job.get("timeout_s") or 30),
            secrets=[key],
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if err or not parsed:
            return AdapterResult(False, "ERROR", err or "empty_response", {"provider_called": True, "latency_ms": latency_ms, "mocked": providers_mocked()})
        output = ""
        try:
            output = safe_excerpt(parsed["choices"][0]["message"]["content"] or "", [key])
        except (KeyError, IndexError, TypeError):
            output = safe_excerpt(raw, [key])
        usage = {"pool_id": "openai_api", "amount_usd": 0.0, "metered_usd": "UNKNOWN", "max_cost_usd": cap}
        ledger_provider_call(
            worker_id="openai_api",
            model_id=model_id,
            work_item_id=job.get("work_item_id"),
            amount_usd=0.0,
            metered_usd="UNKNOWN",
            note="openai_api live call; token price not invented; separate from chatgpt_sub",
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
            "openai chat.completions",
            {
                "output": output,
                "latency_ms": latency_ms,
                "model_id": model_id,
                "provider_called": True,
                "mocked": providers_mocked(),
                "usage": usage,
                "took_action": False,
                "billing": "api",
            },
            usage=usage,
        )


register(OpenAIChatGPTAdapter())
register(OpenAIAPIAdapter())
