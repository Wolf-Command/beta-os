"""Live submit gate. Off unless execute=True and WOLF_INTELLIGENCE_LIVE_SUBMIT is set.

Never log secret values. Paid APIs also need a key and pass the spend gate
(enforce_cost_cap): an Owner per-call cap (WOLF_INTELLIGENCE_MAX_COST_USD, a job may
only lower it), an Owner daily metered ceiling (WOLF_INTELLIGENCE_MAX_DAILY_COST_USD,
unset = 0 = blocked), a valid USD price table with an Owner-verified price for the
model, and a worst-case estimate within both. Anything else is GATED with
OWNER_ACTION_REQUIRED. There is no unlimited path.
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


# ---------------------------------------------------------------------------
# Paid spend gate. FAIL-CLOSED: every missing, blank, zero, negative, non-number,
# NaN, infinite, oversized or wrong-type value denies with OWNER_ACTION_REQUIRED.
# There is no path to an unlimited cap.
# ---------------------------------------------------------------------------
OWNER_ACTION_REQUIRED = "OWNER_ACTION_REQUIRED"
DAILY_COST_ENV = "WOLF_INTELLIGENCE_MAX_DAILY_COST_USD"
PER_CALL_SANITY_MAX_USD = 1000.0
DAILY_SANITY_MAX_USD = 1000.0
PRICE_SANITY_MAX_PER_MTOK_USD = 1000.0
REQUIRED_CURRENCY = "USD"
REQUIRED_UNIT_TOKENS = 1_000_000
# Pools whose provider calls are billed (or billable) API spend.
PAID_POOLS = frozenset({"openai_api", "anthropic_api", "gemini_free"})


class SpendDenied(Exception):
    """A paid call is refused. code is machine-readable; str() is the reason."""

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


def parse_usd(raw: Any, *, what: str, sanity_max: float | None) -> float:
    """Parse a positive, finite USD amount or raise SpendDenied. Zero is a denial."""
    if raw is None:
        raise SpendDenied("missing", f"{what} is not set")
    if isinstance(raw, bool):
        raise SpendDenied("wrong_type", f"{what} has the wrong type (bool)")
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise SpendDenied("blank", f"{what} is blank")
        try:
            value = float(text)
        except ValueError:
            raise SpendDenied("not_a_number", f"{what} is not a number") from None
    else:
        raise SpendDenied("wrong_type", f"{what} has the wrong type ({type(raw).__name__})")
    if math.isnan(value):
        raise SpendDenied("nan", f"{what} is NaN")
    if math.isinf(value):
        raise SpendDenied("infinite", f"{what} is infinite or overflows")
    if value < 0:
        raise SpendDenied("negative", f"{what} is negative")
    if value == 0:
        raise SpendDenied("zero", f"{what} is 0 (blocked until the Owner sets it)")
    if sanity_max is not None and value > sanity_max:
        raise SpendDenied("over_sanity_max", f"{what} exceeds the sanity max of {sanity_max:g} USD")
    return value


def per_call_cap(job: dict[str, Any]) -> float:
    """Owner per-call cap from WOLF_INTELLIGENCE_MAX_COST_USD. A job may only lower it."""
    if "max_cost" in job:
        raise SpendDenied("currency_missing", "job cap must declare USD (use max_cost_usd)")
    currency = job.get("max_cost_currency", REQUIRED_CURRENCY)
    if currency != REQUIRED_CURRENCY:
        raise SpendDenied("currency_missing", "job cap currency must be USD")
    owner_cap = parse_usd(os.environ.get(MAX_COST_ENV), what=MAX_COST_ENV, sanity_max=PER_CALL_SANITY_MAX_USD)
    if "max_cost_usd" not in job:
        return owner_cap
    job_cap = parse_usd(job.get("max_cost_usd"), what="job max_cost_usd", sanity_max=PER_CALL_SANITY_MAX_USD)
    return min(owner_cap, job_cap)


def daily_ceiling() -> float:
    """Owner daily metered ceiling. Unset means 0 means blocked."""
    return parse_usd(os.environ.get(DAILY_COST_ENV), what=DAILY_COST_ENV, sanity_max=DAILY_SANITY_MAX_USD)


def cost_cap(job: dict[str, Any]) -> float | None:
    """Effective per-call cap, or None when spend is denied. None always means GATED."""
    try:
        return per_call_cap(job)
    except SpendDenied:
        return None


PRICE_CEILINGS_PATH = CONFIG_DIR / "price-ceilings.json"


def price_ceilings() -> dict[str, Any]:
    """Raw price table, {} when unreadable. Validation happens in load_price_table()."""
    try:
        data = json.loads(PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_price_table() -> dict[str, Any]:
    """Validated price table or SpendDenied. Corrupt JSON, wrong currency or units deny."""
    try:
        data = json.loads(PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        raise SpendDenied("price_config_unreadable", "price-ceilings.json cannot be read") from None
    except (json.JSONDecodeError, ValueError):
        raise SpendDenied("price_config_corrupt", "price-ceilings.json is not valid JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        raise SpendDenied("price_config_corrupt", "price-ceilings.json has no models table")
    if data.get("currency") != REQUIRED_CURRENCY:
        raise SpendDenied("currency_missing", "price-ceilings.json must declare currency USD")
    unit = data.get("unit_tokens")
    if isinstance(unit, bool) or not isinstance(unit, int) or unit != REQUIRED_UNIT_TOKENS:
        raise SpendDenied("units_missing", "price-ceilings.json must declare unit_tokens 1000000")
    for key, lo, hi in (("safety_factor", 1.0, 10.0), ("input_bytes_per_token", 0.5, 8.0)):
        v = data.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise SpendDenied("price_config_invalid", f"price-ceilings.json {key} must be a number in [{lo:g}, {hi:g}]")
    ov = data.get("input_overhead_tokens")
    if isinstance(ov, bool) or not isinstance(ov, int) or not 0 <= ov <= 100_000:
        raise SpendDenied("price_config_invalid", "price-ceilings.json input_overhead_tokens must be an int in [0, 100000]")
    return data


def _match_model(model_id: str, models: dict[str, Any]) -> tuple[str, Any] | None:
    mid = (model_id or "").strip().lower()
    best = None
    for key, entry in models.items():
        k = str(key).lower()
        if (mid == k or mid.startswith(k + "-") or mid.startswith(k + "@")) and (best is None or len(k) > len(best[0])):
            best = (k, entry)
    return best


def _entry_prices(entry: Any) -> dict[str, float]:
    if not isinstance(entry, dict):
        raise SpendDenied("price_config_invalid", "price entry is not an object")
    out = {}
    for side in ("input", "output"):
        out[side] = parse_usd(entry.get(side), what=f"price {side}", sanity_max=PRICE_SANITY_MAX_PER_MTOK_USD)
    return out


def model_price(model_id: str, table: dict[str, Any] | None = None) -> dict[str, float] | None:
    """Longest-prefix match of model_id. None when unknown or the entry is not a valid price."""
    table = price_ceilings() if table is None else table
    models = table.get("models") if isinstance(table.get("models"), dict) else {}
    found = _match_model(model_id, models)
    if found is None:
        return None
    try:
        return _entry_prices(found[1])
    except SpendDenied:
        return None


def _estimate(table: dict[str, Any], price: dict[str, float], prompt: str, max_output_tokens: int) -> float:
    bytes_per_token = float(table["input_bytes_per_token"])
    overhead = int(table["input_overhead_tokens"])
    safety = float(table["safety_factor"])
    input_tokens = math.ceil(len((prompt or "").encode("utf-8")) / bytes_per_token) + overhead
    output_tokens = max(int(max_output_tokens), 1)
    raw = (input_tokens * price["input"] + output_tokens * price["output"]) / REQUIRED_UNIT_TOKENS
    return round(raw * safety, 8)


def estimate_call_cost_usd(model_id: str, prompt: str, max_output_tokens: int) -> float | None:
    """Worst-case cost of one call. None when the table or model price is not usable."""
    try:
        table = load_price_table()
    except SpendDenied:
        return None
    price = model_price(model_id, table)
    if price is None:
        return None
    return _estimate(table, price, prompt, max_output_tokens)


def metered_spend_today_usd(today: str | None = None) -> float:
    """Sum of today's metered paid-pool spend from the ledger. Unknown spend denies."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    day = today or datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%d")
    path = ledger.ledger_file()
    total = 0.0
    if not path.exists():
        return 0.0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise SpendDenied("ledger_unreadable", "spend ledger cannot be read") from None
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            raise SpendDenied("ledger_corrupt", "spend ledger has an unparsable line") from None
        if not isinstance(rec, dict) or rec.get("pool_id") not in PAID_POOLS:
            continue
        if not str(rec.get("at") or "").startswith(day) or not rec.get("provider_called"):
            continue
        metered = rec.get("metered_usd")
        if isinstance(metered, bool) or not isinstance(metered, (int, float)) or not math.isfinite(metered) or metered < 0:
            raise SpendDenied("metered_unknown", "today's metered paid spend is unknown")
        total += float(metered)
    return total


def _denied(err: SpendDenied, **extra: Any) -> AdapterResult:
    data = {"provider_called": False, "owner_action_required": True, "reason_code": err.code}
    data.update(extra)
    return AdapterResult(False, "GATED", f"{OWNER_ACTION_REQUIRED}: {err.reason}. No provider call.", data)


def enforce_cost_cap(
    job: dict[str, Any], *, model_id: str, prompt: str, max_output_tokens: int
) -> tuple[AdapterResult | None, float | None, float | None]:
    """Return (refusal, cap, estimate). refusal is None only when every spend check passes.

    Order: Owner per-call cap (job may only lower it) -> daily ceiling -> price table
    (USD, per 1M tokens, valid numbers) -> model price verified -> estimate <= cap ->
    today's metered spend + estimate <= daily ceiling.
    """
    cap = None
    estimate = None
    try:
        cap = per_call_cap(job)
        daily = daily_ceiling()
        table = load_price_table()
        found = _match_model(model_id, table["models"])
        if found is None:
            raise SpendDenied("unknown_model", "no price ceiling for this model")
        entry = found[1]
        if not isinstance(entry, dict) or entry.get("verified") is not True:
            raise SpendDenied("price_unverified", "model price is not verified by the Owner")
        price = _entry_prices(entry)
        estimate = _estimate(table, price, prompt, max_output_tokens)
        if not math.isfinite(estimate) or estimate <= 0:
            raise SpendDenied("estimate_invalid", "cost estimate is not a positive finite number")
        if estimate > cap:
            raise SpendDenied(
                "over_cap",
                f"estimated worst-case cost {estimate:.6f} USD exceeds per-call cap {cap:.6f} USD",
            )
        spent = metered_spend_today_usd()
        if spent + estimate > daily:
            raise SpendDenied(
                "over_daily",
                f"today's metered spend {spent:.6f} USD + estimate {estimate:.6f} USD exceeds daily ceiling {daily:.6f} USD",
            )
    except SpendDenied as err:
        extra: dict[str, Any] = {}
        if cap is not None:
            extra["max_cost_usd"] = cap
        if estimate is not None:
            extra["estimated_max_usd"] = estimate
        return _denied(err, **extra), cap, estimate
    return None, cap, estimate


GEMINI_STATE = "CONNECTED / BILLING UNVERIFIED / SPEND BLOCKED"


def gemini_spend_gate(
    job: dict[str, Any], *, model_id: str, prompt: str, max_output_tokens: int
) -> tuple[AdapterResult | None, float | None, float | None]:
    """THE single gate every Gemini execution path must pass before any provider call (Owner order 09:39, Vesper B4-1).

    It is the canonical f7c78f2 spend policy (enforce_cost_cap) with no bypass: a "free" declaration in the
    registry does not skip it. While the key's billing is unverified, every price entry ships verified=false,
    so every call is DENIED with OWNER_ACTION_REQUIRED and no provider call. Retries and fallbacks re-enter
    the adapter and therefore this gate. Returns (refusal, cap, estimate).
    """
    # 1) Independent billing check (red-team 09:55): the Owner's SPEND BLOCKED state is enforced here directly,
    #    not only through the price catalogue. Unless the registry carries a VERIFIED billing status WITH evidence,
    #    deny before the cost cap is even consulted, so a future verified=true price row cannot re-open spend.
    from .. import worker_registry  # lazy: worker_registry imports the adapters package

    if not worker_registry.gemini_billing_verified():
        return AdapterResult(False, "GATED", f"OWNER_ACTION_REQUIRED: Gemini {GEMINI_STATE}. No provider call.",
                             {"provider_called": False, "owner_action_required": True, "gemini_state": GEMINI_STATE,
                              "gate": "gemini_spend_gate", "denied_by": "billing_unverified", "reason_code": "billing_unverified",
                              "model_id": model_id}), None, None
    # 2) The canonical f7c78f2 spend policy, unchanged and with no bypass.
    refusal, cap, estimate = enforce_cost_cap(job, model_id=model_id, prompt=prompt, max_output_tokens=max_output_tokens)
    if refusal is None:
        return None, cap, estimate
    data = dict(refusal.data or {})
    data.update({"provider_called": False, "owner_action_required": True, "gemini_state": GEMINI_STATE,
                 "gate": "gemini_spend_gate", "denied_by": "spend_cap"})
    return AdapterResult(False, "GATED", f"{refusal.message} [Gemini {GEMINI_STATE}]", data), None, None


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
