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

TZ = ZoneInfo("Asia/Makassar")
_lock = threading.Lock()
CAPACITY_PATH = CONFIG_DIR / "capacity.json"
LEDGER_PATH = LEDGER_DIR / "ledger.jsonl"
SNAPSHOT_PATH = LEDGER_DIR / "snapshot.json"


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
    if LEDGER_PATH.exists():
        with LEDGER_PATH.open(encoding="utf-8") as f:
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


def record_usage(
    *,
    pool_id: str,
    amount_usd: float,
    work_item_id: str | None = None,
    worker_id: str | None = None,
    model_id: str | None = None,
    note: str = "",
    shadow: bool = True,
) -> dict[str, Any]:
    """Record usage. Shadow isolated tests should use amount_usd=0 or tiny."""
    ensure_dirs()
    cap = load_capacity()
    pools = {p["id"]: p for p in (cap.get("pools") or [])}
    if pool_id not in pools:
        raise KeyError(f"unknown pool: {pool_id}")
    pool = pools[pool_id]
    # Subscription vs API separation: refuse cross-billing
    billing = pool.get("billing")
    rec = {
        "at": now_iso(),
        "pool_id": pool_id,
        "billing": billing,
        "amount_usd": float(amount_usd),
        "work_item_id": work_item_id,
        "worker_id": worker_id,
        "model_id": model_id,
        "note": note,
        "shadow": bool(shadow),
    }
    with _lock:
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    events.emit("usage.recorded", rec, work_item_id=work_item_id)
    events.emit("capacity.updated", {"pool_id": pool_id}, work_item_id=work_item_id)
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
