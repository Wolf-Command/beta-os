"""Per-provider capacity model — observations, decay, velocity, state."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .governance import CAPACITY_STATES
from .paths import (
    CONFIG_DIR,
    GOVERNANCE_CAPACITY_OBSERVATIONS_PATH,
    GOVERNANCE_DISPATCH_LEDGER_PATH,
    ensure_dirs,
)

TZ = ZoneInfo("Asia/Makassar")
SEED_PATH = CONFIG_DIR / "governance" / "capacity-observed.json"

STATE_RANK = {s: i for i, s in enumerate(CAPACITY_STATES)}


def _parse_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def _max_state(a: str, b: str) -> str:
    return a if STATE_RANK.get(a, 0) >= STATE_RANK.get(b, 0) else b


def _load_seed() -> list[dict[str, Any]]:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("observations") or [])


def _load_persisted() -> list[dict[str, Any]]:
    path = GOVERNANCE_CAPACITY_OBSERVATIONS_PATH
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if isinstance(rec, dict):
                out.append(rec)
    except (OSError, json.JSONDecodeError):
        pass
    return out


def merge_observations(now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """Merge seed + persisted; newest observed_at per worker wins."""
    merged: dict[str, dict[str, Any]] = {}
    for rec in _load_seed() + _load_persisted():
        wid = rec.get("worker_id")
        if not wid:
            continue
        prev = merged.get(wid)
        if prev is None:
            merged[wid] = rec
            continue
        t_new = _parse_dt(rec.get("observed_at"))
        t_old = _parse_dt(prev.get("observed_at"))
        if t_new and t_old and t_new >= t_old:
            merged[wid] = rec
        elif t_new and not t_old:
            merged[wid] = rec
    return merged


def record_observation(
    *,
    worker_id: str,
    plan: str = "",
    included_usage_pct: dict[str, float] | None = None,
    remaining: float | None = None,
    reset_at: str | None = None,
    on_demand: str = "UNKNOWN",
    source: str = "owner_observed",
    observed_at: str | None = None,
) -> dict[str, Any]:
    ensure_dirs()
    rec = {
        "worker_id": worker_id,
        "plan": plan,
        "included_usage_pct": included_usage_pct or {},
        "remaining": remaining,
        "reset_at": reset_at,
        "on_demand": on_demand,
        "source": source,
        "observed_at": observed_at or datetime.now(TZ).isoformat(timespec="seconds"),
    }
    with GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _dispatch_counts(worker_id: str, now: datetime) -> dict[str, int]:
    counts = {"24h": 0, "7d": 0}
    path = GOVERNANCE_DISPATCH_LEDGER_PATH
    if not path.exists():
        return counts
    cutoff_24 = now - timedelta(hours=24)
    cutoff_7 = now - timedelta(days=7)
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("selected_worker") != worker_id or rec.get("decision") != "DISPATCH":
                continue
            ts = _parse_dt(rec.get("recorded_at"))
            if not ts:
                continue
            if ts >= cutoff_7:
                counts["7d"] += 1
            if ts >= cutoff_24:
                counts["24h"] += 1
    except (OSError, json.JSONDecodeError):
        pass
    return counts


def _velocity(worker_id: str, pool: str | None, now: datetime) -> dict[str, Any]:
    """pct_per_day only when two observations of the same pool exist."""
    obs_list = [r for r in _load_persisted() + _load_seed() if r.get("worker_id") == worker_id]
    if pool:
        pairs = []
        for rec in obs_list:
            pct_map = rec.get("included_usage_pct") or {}
            if pool in pct_map:
                t = _parse_dt(rec.get("observed_at"))
                if t:
                    pairs.append((t, float(pct_map[pool])))
        pairs.sort(key=lambda x: x[0])
        pct_per_day = None
        if len(pairs) >= 2:
            t0, p0 = pairs[-2]
            t1, p1 = pairs[-1]
            days = max((t1 - t0).total_seconds() / 86400.0, 1e-6)
            pct_per_day = round((p1 - p0) / days, 4)
    else:
        pct_per_day = None
    disp = _dispatch_counts(worker_id, now)
    return {
        "dispatch_24h": disp["24h"],
        "dispatch_7d": disp["7d"],
        "pct_per_day": pct_per_day,
    }


def _effective_pct(
    observed_pct: float,
    observed_at: datetime | None,
    now: datetime,
    decay_pct_per_hour: float,
) -> float:
    if observed_at is None:
        return observed_pct
    hours = max((now - observed_at).total_seconds() / 3600.0, 0.0)
    return min(100.0, observed_pct + decay_pct_per_hour * hours)


def _state_from_pct(pct: float, thresholds: dict[str, float]) -> str:
    if pct >= thresholds["exhausted_at"]:
        return "EXHAUSTED"
    if pct >= thresholds["reserve_at"]:
        return "RESERVE"
    if pct >= thresholds["conserve_at"]:
        return "CONSERVE"
    return "NORMAL"


def _worker_thresholds(worker_id: str, policy: dict[str, Any]) -> dict[str, float]:
    root = policy.get("capacity_thresholds") or {}
    th = root.get(worker_id) or root.get("default") or {"conserve_at": 70, "reserve_at": 85, "exhausted_at": 100}
    return {
        "conserve_at": float(th["conserve_at"]),
        "reserve_at": float(th["reserve_at"]),
        "exhausted_at": float(th["exhausted_at"]),
    }


def _primary_pool(worker_id: str, policy: dict[str, Any]) -> str | None:
    pools = policy.get("primary_capacity_pool") or {}
    return pools.get(worker_id)


def _projected_exhaustion(
    effective_pct: float | None,
    velocity_pct_per_day: float | None,
    reset_at: datetime | None,
    now: datetime,
) -> bool | None:
    if effective_pct is None or velocity_pct_per_day is None or reset_at is None:
        return None
    if velocity_pct_per_day <= 0:
        return False
    hours_to_reset = max((reset_at - now).total_seconds() / 3600.0, 0.0)
    days_to_reset = hours_to_reset / 24.0
    projected = effective_pct + velocity_pct_per_day * days_to_reset
    return projected >= 100.0


def worker_capacity_record(
    worker_id: str,
    obs: dict[str, Any] | None,
    policy: dict[str, Any],
    now: datetime,
    *,
    grok_available: bool = True,
) -> dict[str, Any]:
    decay_cfg = policy.get("capacity_decay") or {}
    decay_rate = float(decay_cfg.get("decay_pct_per_hour", 0.5))
    max_age_h = float(decay_cfg.get("max_observation_age_hours", 24))
    unknown_cfg = decay_cfg.get("unknown_state") or {}
    unknown_default = unknown_cfg.get("default", "CONSERVE")
    unknown_grok = unknown_cfg.get("grok_worker_id", unknown_cfg.get("grok_bot_sub", unknown_default))

    pool = _primary_pool(worker_id, policy)
    thresholds = _worker_thresholds(worker_id, policy)

    if obs is None:
        unk = unknown_grok if worker_id == policy.get("grok_worker_id") else unknown_default
        return {
            "worker_id": worker_id,
            "plan": None,
            "included_usage_pct": {},
            "remaining": None,
            "reset_at": None,
            "velocity": _velocity(worker_id, pool, now),
            "projected_exhaustion_before_reset": None,
            "on_demand": "UNKNOWN",
            "source": None,
            "observed_at": None,
            "effective_pct": None,
            "state": unk,
            "grok_available": grok_available,
        }

    pct_map = dict(obs.get("included_usage_pct") or {})
    observed_pct = float(pct_map.get(pool, 0.0)) if pool and pool in pct_map else (
        max(pct_map.values()) if pct_map else 0.0
    )
    observed_at = _parse_dt(obs.get("observed_at"))
    effective = _effective_pct(observed_pct, observed_at, now, decay_rate)
    state = _state_from_pct(effective, thresholds)

    if observed_at:
        age_h = (now - observed_at).total_seconds() / 3600.0
        if age_h > max_age_h:
            state = _max_state(state, "CONSERVE")

    vel = _velocity(worker_id, pool, now)
    reset_dt = _parse_dt(obs.get("reset_at"))
    projected = _projected_exhaustion(effective, vel.get("pct_per_day"), reset_dt, now)
    if projected is True:
        state = _max_state(state, "CONSERVE")

    if worker_id == policy.get("grok_worker_id") and not grok_available:
        state = "EXHAUSTED"

    return {
        "worker_id": worker_id,
        "plan": obs.get("plan"),
        "included_usage_pct": pct_map,
        "remaining": obs.get("remaining"),
        "reset_at": obs.get("reset_at"),
        "velocity": vel,
        "projected_exhaustion_before_reset": projected,
        "on_demand": obs.get("on_demand", "UNKNOWN"),
        "source": obs.get("source"),
        "observed_at": obs.get("observed_at"),
        "effective_pct": round(effective, 4) if observed_at else None,
        "primary_pool": pool,
        "state": state,
        "grok_available": grok_available,
    }


def capacity_snapshot(
    now: datetime | str | None = None,
    policy: dict[str, Any] | None = None,
    *,
    grok_available: bool = True,
    worker_ids: list[str] | None = None,
) -> dict[str, Any]:
    if policy is None:
        from .governance import load_policy
        pl = load_policy()
        policy = pl.policy or {}
    if isinstance(now, str):
        now_dt = _parse_dt(now) or datetime.now(TZ)
    elif now is None:
        now_dt = datetime.now(TZ)
    else:
        now_dt = now

    merged = merge_observations(now_dt)
    ids = worker_ids or list(merged.keys()) or [
        "cursor_sub", "grok_bot_sub", "claude_pro_sub", "codex_sub", "ollama_local", "gemini_free"
    ]
    workers = {}
    for wid in ids:
        workers[wid] = worker_capacity_record(wid, merged.get(wid), policy, now_dt, grok_available=grok_available)
    grok_id = policy.get("grok_worker_id", "grok_bot_sub")
    return {
        "at": now_dt.isoformat(timespec="seconds"),
        "grok_state": workers.get(grok_id, {}).get("state", "UNKNOWN"),
        "grok_available": grok_available,
        "workers": workers,
    }


def set_capacity_override(
    worker_id: str,
    *,
    effective_pct: float | None = None,
    state: str | None = None,
    grok_available: bool | None = None,
) -> None:
    """Test helper: inject overrides via a module-level dict (not persisted)."""
    if not hasattr(set_capacity_override, "_overrides"):
        set_capacity_override._overrides = {}  # type: ignore[attr-defined]
    set_capacity_override._overrides[worker_id] = {  # type: ignore[attr-defined]
        "effective_pct": effective_pct,
        "state": state,
        "grok_available": grok_available,
    }


def clear_capacity_overrides() -> None:
    if hasattr(set_capacity_override, "_overrides"):
        set_capacity_override._overrides.clear()  # type: ignore[attr-defined]


def apply_test_overrides(snapshot: dict[str, Any]) -> dict[str, Any]:
    overrides = getattr(set_capacity_override, "_overrides", {})
    if not overrides:
        return snapshot
    out = dict(snapshot)
    workers = dict(out.get("workers") or {})
    for wid, ov in overrides.items():
        rec = dict(workers.get(wid) or {"worker_id": wid})
        if ov.get("effective_pct") is not None:
            rec["effective_pct"] = ov["effective_pct"]
        if ov.get("state") is not None:
            rec["state"] = ov["state"]
        if ov.get("grok_available") is not None:
            rec["grok_available"] = ov["grok_available"]
        workers[wid] = rec
    out["workers"] = workers
    grok_id = "grok_bot_sub"
    if grok_id in workers:
        out["grok_state"] = workers[grok_id].get("state")
        out["grok_available"] = workers[grok_id].get("grok_available", True)
    return out
