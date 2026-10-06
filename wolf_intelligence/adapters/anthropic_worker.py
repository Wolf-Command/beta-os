"""Anthropic — Claude subscription vs API separate. Haiku = default not best."""
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
    unsupported,
)

BETA_ENV = Path("/Users/wolfterminal/beta-os/.env")
OPENCLAW = Path.home() / ".openclaw" / "openclaw.json"

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

class AnthropicAPIAdapter(WorkerAdapter):
    worker_id = "anthropic_api"
    label = "Anthropic API"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        has = _env_has("ANTHROPIC_API_KEY")
        evidence = []
        openclaw_holds = False
        if has:
            evidence.append("ANTHROPIC_API_KEY configured in beta .env (value not read)")
        name_present = False
        try:
            env = Path("/Users/wolfterminal/beta-os/.env")
            if env.exists():
                for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip().startswith("ANTHROPIC_API_KEY="):
                        name_present = True
                        break
        except OSError:
            pass
        if name_present and not has:
            evidence.append("ANTHROPIC_API_KEY name present in beta .env but value empty")
        if OPENCLAW.exists():
            try:
                txt = OPENCLAW.read_text(encoding="utf-8", errors="replace")
                if "haiku" in txt.lower():
                    evidence.append("openclaw primary mentions haiku (default not best)")
                if "anthropic" in txt.lower():
                    evidence.append("openclaw references anthropic")
                # Detect credential material WITHOUT copying it
                # Credential material may live in auth profiles — detect presence only
                if "sk-ant-" in txt:
                    openclaw_holds = True
                    evidence.append("openclaw.json appears to embed Anthropic credential material (not copied)")
                auth_roots = [
                    Path.home() / ".openclaw" / "agents",
                    Path.home() / ".openclaw",
                ]
                for root in auth_roots:
                    if not root.exists():
                        continue
                    for ap in root.rglob("auth-profiles.json"):
                        try:
                            at = ap.read_text(encoding="utf-8", errors="replace")
                        except OSError:
                            continue
                        if "anthropic" in at.lower() or "sk-ant-" in at:
                            openclaw_holds = True
                            evidence.append(f"auth-profiles references anthropic ({ap.name})")
                            break
                    if openclaw_holds:
                        break
            except OSError:
                pass
        status = "CONNECTED" if (has or openclaw_holds) else ("PARTIAL" if evidence else "UNAVAILABLE")
        if evidence:
            return AdapterResult(True if status != "UNAVAILABLE" else False, status, "; ".join(evidence),
                                 {"billing": "api", "note": "haiku_is_default_not_best", "openclaw_may_hold_creds": openclaw_holds})
        return AdapterResult(False, "UNAVAILABLE", "no Anthropic API evidence")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            if not env_enabled():
                return live_disabled()
            return self._live(job)
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live Anthropic API in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — no tokens spent", {"billing": "api", "provider_called": False})

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        key = read_secret("ANTHROPIC_API_KEY")
        if not key:
            return AdapterResult(
                False,
                "UNAVAILABLE",
                "ANTHROPIC_API_KEY absent in env. Refusing to read other credential files. No provider call.",
                {"provider_called": False},
            )
        model_id = str(job.get("model") or "claude-3-5-haiku-latest")
        try:
            max_tokens = max(1, min(int(job.get("num_predict") or 64), 128))
        except (TypeError, ValueError):
            max_tokens = 64
        refusal, cap, estimate = enforce_cost_cap(
            job, model_id=model_id, prompt=str(job.get("prompt") or ""), max_output_tokens=max_tokens
        )
        if refusal is not None:
            return refusal
        started = time.perf_counter()
        parsed, raw, err = http_json(
            "https://api.anthropic.com/v1/messages",
            {
                "model": model_id,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": str(job.get("prompt") or "")}],
            },
            {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=float(job.get("timeout_s") or 30),
            secrets=[key],
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if err or not parsed:
            return AdapterResult(False, "ERROR", err or "empty_response", {"provider_called": True, "latency_ms": latency_ms, "mocked": providers_mocked()})
        output = ""
        try:
            output = safe_excerpt(parsed["content"][0]["text"] or "", [key])
        except (KeyError, IndexError, TypeError):
            output = safe_excerpt(raw, [key])
        usage = {
            "pool_id": "anthropic_api",
            "amount_usd": 0.0,
            "metered_usd": "UNKNOWN",
            "max_cost_usd": cap,
            "estimated_max_usd": estimate,
            "note": "haiku_is_default_not_best; separate from claude_sub_25",
        }
        ledger_provider_call(
            worker_id="anthropic_api",
            model_id=model_id,
            work_item_id=job.get("work_item_id"),
            amount_usd=0.0,
            metered_usd="UNKNOWN",
            note="anthropic_api live call; token price not invented; separate from claude_sub_25",
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
            "anthropic messages; haiku is default-fast not best",
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

class ClaudeSubAdapter(WorkerAdapter):
    worker_id = "claude_sub"
    label = "Claude Subscription"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        claude_home = Path.home() / ".claude"
        evidence = []
        if claude_home.exists():
            evidence.append("~/.claude present")
        return AdapterResult(True, "PARTIAL",
                             "Owner-declared Claude sub $25/mo; live plan tier not probed. " + "; ".join(evidence),
                             {"billing": "subscription", "owner_declared_usd_mo": 25})

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            return unsupported(
                "claude_sub is health-only. USD 25/month is a separate pool from anthropic_api. "
                "No subscription submit. CLI API-key auth is not this pool."
            )
        if job.get("shadow_isolated"):
            return AdapterResult(
                True,
                "SHADOW_OK",
                "health-only; shadow ping is not a live submit",
                {"provider_called": False, "billing": "subscription"},
            )
        return unsupported("claude_sub submit is not supported")

register(AnthropicAPIAdapter())
register(ClaudeSubAdapter())
