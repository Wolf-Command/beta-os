"""Capacity / credit ledger. Subscription vs API kept strictly separate."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events
from .paths import CONFIG_DIR, LEDGER_DIR, ensure_dirs
from . import paths

TZ = ZoneInfo("Asia/Makassar")
_lock = threading.Lock()
CAPACITY_PATH = CONFIG_DIR / "capacity.json"
LEDGER_PATH = LEDGER_DIR / "ledger.jsonl"
SNAPSHOT_PATH = LEDGER_DIR / "snapshot.json"
_UNSET = object()

# Subscription pool ids are never fungible with API pool ids.
WORKER_POOLS = {
    "cursor": "cursor_sub_300",
    "claude_sub": "claude_sub_25",
    "grok_bot": "grok_sub",
    "openai_chatgpt": "chatgpt_sub",
    "openai_api": "openai_api",
    "anthropic_api": "anthropic_api",
    "gemini": "gemini_free",
    "ollama": "ollama_local",
}
SUBSCRIPTION_POOLS = frozenset({"cursor_sub_300", "claude_sub_25", "grok_sub", "chatgpt_sub"})
API_POOLS = frozenset({"openai_api", "anthropic_api", "xai_api"})


def ledger_file() -> Path:
    return paths.LEDGER_DIR / "ledger.jsonl"


def executions_file() -> Path:
    return paths.LEDGER_DIR / "executions.jsonl"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_capacity() -> dict[str, Any]:
    ensure_dirs()
    if not CAPACITY_PATH.exists():
        return {"pools": []}
    return json.loads(CAPACITY_PATH.read_text(encoding="utf-8"))


def snapshot() -> dict[str, Any]:
    ensure_dirs()
    cap = load_capacity()
    # overlay usage from ledger
    used: dict[str, float] = {}
    path = ledger_file()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pool = rec.get("pool_id")
                if not pool:
                    continue
                used[pool] = used.get(pool, 0.0) + float(rec.get("amount_usd") or 0.0)
    pools_out = []
    for p in cap.get("pools") or []:
        pid = p["id"]
        monthly = p.get("monthly_usd")
        entry = dict(p)
        entry["used_usd_period"] = round(used.get(pid, 0.0), 4)
        if monthly is not None:
            entry["remaining_usd_estimate"] = round(float(monthly) - used.get(pid, 0.0), 4)
        else:
            entry["remaining_usd_estimate"] = "UNKNOWN"
        pools_out.append(entry)
    snap = {"at": now_iso(), "pools": pools_out}
    SNAPSHOT_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return snap


def pool_for_worker(worker_id: str | None) -> str | None:
    if not worker_id:
        return None
    return WORKER_POOLS.get(worker_id)


def capacity_for_worker(worker_id: str | None) -> dict[str, Any]:
    """Known pool capacity for a worker. Unknown plan USD stays UNKNOWN."""
    pool_id = pool_for_worker(worker_id)
    if not pool_id:
        return {
            "amount_usd": "UNKNOWN",
            "metered_usd": "UNKNOWN",
            "pool_id": None,
            "capacity_monthly_usd": "UNKNOWN",
            "billing": None,
            "known": False,
        }
    pools = {p["id"]: p for p in (load_capacity().get("pools") or [])}
    pool = pools.get(pool_id) or {}
    monthly = pool.get("monthly_usd")
    billing = pool.get("billing")
    known = monthly is not None
    return {
        "amount_usd": "UNKNOWN",
        "metered_usd": "UNKNOWN",
        "pool_id": pool_id,
        "capacity_monthly_usd": monthly if monthly is not None else "UNKNOWN",
        "billing": billing,
        "prepaid": bool(pool.get("prepaid")),
        "plan_name": pool.get("plan_name"),
        "known": known,
    }


def record_usage(
    *,
    pool_id: str,
    amount_usd: float,
    work_item_id: str | None = None,
    worker_id: str | None = None,
    model_id: str | None = None,
    note: str = "",
    shadow: bool = True,
    metered_usd: float | str | None = _UNSET,  # type: ignore[assignment]
    provider_called: bool = False,
    took_action: bool = False,
    counts_as_current_system: bool = False,
) -> dict[str, Any]:
    """Record usage. Shadow isolated tests should use amount_usd=0 or tiny.

    Per-call metered USD is stored only when the caller measured it.
    Pass metered_usd='UNKNOWN' rather than inventing a price.
    Subscription pool ids are refused for a worker that maps to a different pool.
    """
    ensure_dirs()
    expected = pool_for_worker(worker_id) if worker_id else None
    if expected and pool_id != expected:
        raise KeyError(f"pool {pool_id} is not the pool for worker {worker_id}")
    if pool_id in SUBSCRIPTION_POOLS and pool_id in API_POOLS:
        raise KeyError(f"pool {pool_id} cannot be both subscription and API")
    cap = load_capacity()
    pools = {p["id"]: p for p in (cap.get("pools") or [])}
    if pool_id not in pools:
        raise KeyError(f"unknown pool: {pool_id}")
    pool = pools[pool_id]
    billing = pool.get("billing")
    rec: dict[str, Any] = {
        "at": now_iso(),
        "pool_id": pool_id,
        "billing": billing,
        "amount_usd": float(amount_usd),
        "work_item_id": work_item_id,
        "worker_id": worker_id,
        "model_id": model_id,
        "note": note,
        "shadow": bool(shadow),
        "provider_called": bool(provider_called),
        "took_action": bool(took_action),
        "counts_as_current_system": bool(counts_as_current_system),
    }
    if metered_usd is not _UNSET:
        if metered_usd == "UNKNOWN" or metered_usd is None:
            rec["metered_usd"] = "UNKNOWN"
        else:
            rec["metered_usd"] = float(metered_usd)
    with _lock:
        with ledger_file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    events.emit("usage.recorded", rec, work_item_id=work_item_id)
    events.emit("capacity.updated", {"pool_id": pool_id}, work_item_id=work_item_id)
    return rec


def record_execution(
    *,
    worker_id: str,
    model_id: str | None = None,
    work_item_id: str | None = None,
    pool_id: str | None = None,
    latency_ms: float | None = None,
    status: str = "",
    ok: bool = False,
    output_excerpt: str = "",
    shadow: bool = False,
    label: str = "",
    mocked: bool = False,
    took_action: bool = False,
    provider_called: bool = False,
    note: str = "",
) -> dict[str, Any]:
    """Append a live/shadow execution row. Never store secrets."""
    ensure_dirs()
    excerpt = (output_excerpt or "")[:800]
    rec = {
        "at": now_iso(),
        "worker_id": worker_id,
        "model_id": model_id or "UNKNOWN",
        "work_item_id": work_item_id,
        "pool_id": pool_id,
        "latency_ms": latency_ms,
        "status": status,
        "ok": bool(ok),
        "output_excerpt": excerpt,
        "shadow": bool(shadow),
        "label": label,
        "mocked": bool(mocked),
        "took_action": bool(took_action),
        "provider_called": bool(provider_called),
        "counts_as_current_system": False,
        "note": note,
    }
    with _lock:
        with executions_file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def prefer_paid_capacity_order() -> list[str]:
    """Prefer already-paid capacity when quality sufficient (Owner rule)."""
    snap = snapshot()
    # Prefer subscription pools with remaining capacity, then free/local, then API
    sub = []
    free = []
    api = []
    for p in snap["pools"]:
        billing = p.get("billing")
        if billing == "subscription":
            sub.append(p["id"])
        elif billing in ("free", "local"):
            free.append(p["id"])
        else:
            api.append(p["id"])
    return sub + free + api
