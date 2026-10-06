"""Live submit gate. Off unless execute=True and WOLF_INTELLIGENCE_LIVE_SUBMIT is set.

Never log secret values. Paid APIs also need a key and a per-call cost cap.
The cap is a real ceiling: a paid call is refused unless its worst-case
estimated cost (prompt + max output tokens at config/price-ceilings.json
prices, times the safety factor) is at or below the cap.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from .. import ledger
from ..paths import BETA_ROOT, CONFIG_DIR, LIVE_SUBMIT_ENV, MAX_COST_ENV, PROVIDER_MOCK_ENV
from .base import AdapterResult

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_SECRET_LINE = re.compile(r"(?i)(api[_-]?key|token|authorization|secret)\s*[:=]\s*\S+")


def env_enabled(name: str = LIVE_SUBMIT_ENV) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def providers_mocked() -> bool:
    return env_enabled(PROVIDER_MOCK_ENV)


def execute_requested(job: dict[str, Any]) -> bool:
    return job.get("execute") is True


def live_disabled() -> AdapterResult:
    return AdapterResult(
        False,
        "LIVE_DISABLED",
        f"{LIVE_SUBMIT_ENV} is off (default). No provider call.",
        {"provider_called": False},
    )


def unsupported(message: str) -> AdapterResult:
    return AdapterResult(False, "UNSUPPORTED", message, {"provider_called": False})


def cost_cap(job: dict[str, Any]) -> float | None:
    """Per-call paid cap. Unset means the cap is on: callers must refuse, not spend.

    There is no unlimited default. A missing job cap and a missing
    WOLF_INTELLIGENCE_MAX_COST_USD both return None, and paid adapters treat
    None as GATED.
    """
    raw = job.get("max_cost_usd")
    if raw is None or raw == "":
        raw = os.environ.get(MAX_COST_ENV)
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


PRICE_CEILINGS_PATH = CONFIG_DIR / "price-ceilings.json"


def price_ceilings() -> dict[str, Any]:
    try:
        data = json.loads(PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def model_price(model_id: str, table: dict[str, Any] | None = None) -> dict[str, float] | None:
    """Longest-prefix match of model_id against the price table. None means unknown."""
    table = price_ceilings() if table is None else table
    models = table.get("models") if isinstance(table.get("models"), dict) else {}
    mid = (model_id or "").strip().lower()
    best = None
    for key, price in models.items():
        k = str(key).lower()
        if (mid == k or mid.startswith(k + "-") or mid.startswith(k + "@")) and (best is None or len(k) > len(best[0])):
            best = (k, price)
    if best is None:
        return None
    try:
        return {"input": float(best[1]["input"]), "output": float(best[1]["output"])}
    except (KeyError, TypeError, ValueError):
        return None


def estimate_call_cost_usd(model_id: str, prompt: str, max_output_tokens: int) -> float | None:
    """Worst-case cost of one call. None when the model has no price ceiling."""
    table = price_ceilings()
    price = model_price(model_id, table)
    if price is None:
        return None
    bytes_per_token = float(table.get("input_bytes_per_token") or 2)
    overhead = int(table.get("input_overhead_tokens") or 32)
    safety = float(table.get("safety_factor") or 1.5)
    input_tokens = math.ceil(len((prompt or "").encode("utf-8")) / max(bytes_per_token, 1.0)) + overhead
    output_tokens = max(int(max_output_tokens), 1)
    raw = (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
    return round(raw * max(safety, 1.0), 8)


def enforce_cost_cap(
    job: dict[str, Any], *, model_id: str, prompt: str, max_output_tokens: int
) -> tuple[AdapterResult | None, float | None, float | None]:
    """Return (refusal, cap, estimate). refusal is None only when estimate <= cap."""
    cap = cost_cap(job)
    if cap is None:
        return AdapterResult(False, "GATED", "per-call cost cap not configured. No provider call.", {"provider_called": False}), None, None
    if cap == 0:
        return AdapterResult(False, "GATED", "per-call cost cap is 0. Refusing paid API call.", {"provider_called": False}), cap, None
    estimate = estimate_call_cost_usd(model_id, prompt, max_output_tokens)
    if estimate is None:
        return (
            AdapterResult(False, "GATED", "no price ceiling for this model. No provider call.", {"provider_called": False, "max_cost_usd": cap}),
            cap,
            None,
        )
    if estimate > cap:
        return (
            AdapterResult(
                False,
                "GATED",
                f"estimated worst-case cost {estimate:.6f} USD exceeds per-call cap {cap:.6f} USD. No provider call.",
                {"provider_called": False, "max_cost_usd": cap, "estimated_max_usd": estimate},
            ),
            cap,
            estimate,
        )
    return None, cap, estimate


def read_secret(name: str) -> str:
    """Return a secret for a request. Callers must not put it on a result."""
    value = os.environ.get(name, "")
    if value.strip():
        return value.strip().strip("\"'")
    env_path = BETA_ROOT / ".env"
    if not env_path.is_file():
        return ""
    try:
        lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    prefix = name + "="
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        return stripped[len(prefix):].strip().strip("\"'")
    return ""


def secret_present(names: list[str]) -> bool:
    return any(read_secret(name) for name in names)


def safe_excerpt(text: str, secrets: list[str] | None = None) -> str:
    out = text or ""
    for secret in secrets or []:
        if secret and len(secret) >= 8:
            out = out.replace(secret, "[REDACTED]")
    out = _SECRET_LINE.sub(r"\1=[REDACTED]", out)
    out = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "[REDACTED]", out)
    return out[:800]


def http_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: float,
    secrets: list[str],
) -> tuple[dict[str, Any] | None, str, str | None]:
    """POST JSON. Error text is the exception type only, never the secret."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_full = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 — provider failures stay typed, not dumped
        return None, "", type(exc).__name__
    excerpt = safe_excerpt(raw_full, secrets)
    try:
        parsed = json.loads(raw_full)
    except json.JSONDecodeError:
        return None, excerpt, None
    if not isinstance(parsed, dict):
        return None, excerpt, None
    return parsed, excerpt, None


def ledger_provider_call(
    *,
    worker_id: str,
    model_id: str | None,
    work_item_id: str | None,
    amount_usd: float,
    metered_usd: float | str,
    note: str,
    shadow_mode: bool,
    latency_ms: float | None,
    status: str,
    ok: bool,
    output_excerpt: str,
    label: str,
) -> None:
    pool_id = ledger.pool_for_worker(worker_id)
    if pool_id:
        try:
            ledger.record_usage(
                pool_id=pool_id,
                amount_usd=amount_usd,
                work_item_id=work_item_id,
                worker_id=worker_id,
                model_id=model_id,
                note=note,
                shadow=shadow_mode,
                metered_usd=metered_usd,
                provider_called=True,
                took_action=False,
                counts_as_current_system=False,
            )
        except KeyError:
            pass
    ledger.record_execution(
        worker_id=worker_id,
        model_id=model_id,
        work_item_id=work_item_id,
        pool_id=pool_id,
        latency_ms=latency_ms,
        status=status,
        ok=ok,
        output_excerpt=safe_excerpt(output_excerpt),
        shadow=shadow_mode,
        label=label,
        mocked=providers_mocked(),
        took_action=False,
        provider_called=True,
        note=note,
    )


def cursor_selected_model() -> str:
    path = Path.home() / ".cursor" / "cli-config.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return "UNKNOWN"
    if not isinstance(data, dict):
        return "UNKNOWN"
    selected = data.get("selectedModel")
    if isinstance(selected, str) and selected.strip() and "@" not in selected:
        return selected.strip()[:80]
    return "UNKNOWN"
