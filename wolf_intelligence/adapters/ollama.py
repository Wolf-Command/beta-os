"""Ollama local :11434 — RETIRE CANDIDATE; do not delete. Live generate is gated."""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from .base import AdapterResult, WorkerAdapter, register
from .live_gate import (
    env_enabled,
    execute_requested,
    ledger_provider_call,
    live_disabled,
    providers_mocked,
    safe_excerpt,
)


class OllamaAdapter(WorkerAdapter):
    worker_id = "ollama"
    label = "Ollama"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as resp:
                data = json.loads(resp.read().decode())
            models = [m.get("name") for m in data.get("models") or []]
            return AdapterResult(
                True,
                "CONNECTED",
                f"ollama :11434 up; models={models}",
                {"models": models, "retire_candidate": "PENDING_PHASE2_CALLER_AUDIT"},
            )
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(False, "UNAVAILABLE", f"ollama :11434 not reachable: {type(exc).__name__}")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            if not env_enabled():
                return live_disabled()
            return self._live(job)
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "shadow only")
        return AdapterResult(True, "SHADOW_OK", "shadow — no generate invoked", {"billing": "local", "provider_called": False})

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        model_id = str(job.get("model") or "llama3.2:3b")
        try:
            num_predict = int(job.get("num_predict") or 64)
        except (TypeError, ValueError):
            num_predict = 64
        num_predict = max(1, min(num_predict, 256))
        payload = {
            "model": model_id,
            "prompt": str(job.get("prompt") or ""),
            "stream": False,
            "options": {"num_predict": num_predict},
        }
        raw = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=float(job.get("timeout_s") or 60)) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(False, "ERROR", type(exc).__name__, {"provider_called": True, "mocked": providers_mocked()})
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        output = safe_excerpt(str(body.get("response") or ""))
        usage = {
            "pool_id": "ollama_local",
            "amount_usd": 0.0,
            "metered_usd": 0.0,
            "prompt_eval_count": body.get("prompt_eval_count"),
            "eval_count": body.get("eval_count"),
        }
        ledger_provider_call(
            worker_id="ollama",
            model_id=model_id,
            work_item_id=job.get("work_item_id"),
            amount_usd=0.0,
            metered_usd=0.0,
            note=str(job.get("ledger_note") or "ollama local generate; cost USD 0"),
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
            "ollama /api/generate",
            {
                "output": output,
                "latency_ms": latency_ms,
                "model_id": model_id,
                "provider_called": True,
                "mocked": providers_mocked(),
                "usage": usage,
                "took_action": False,
                "billing": "local",
            },
            usage=usage,
        )


register(OllamaAdapter())
