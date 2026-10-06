"""Per-provider capacity model — observations, decay, velocity, state."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .governance import (
    CAPACITY_STATES,
    GROK_WORKER_ID,
    HARDCODED_GROK_THRESHOLDS,
    append_audit_event,
    fail_closed_policy,
)
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
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt


def _max_state(a: str, b: str) -> str:
    return a if STATE_RANK.get(a, 0) >= STATE_RANK.get(b, 0) else b


def _is_valid_pct(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if not math.isfinite(value):
        return False
    return 0 <= value <= 100


def _load_seed() -> list[dict[str, Any]]:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("observations") or [])


def _load_persisted() -> tuple[list[dict[str, Any]], bool]:
    path = GOVERNANCE_CAPACITY_OBSERVATIONS_PATH
    if not path.exists():
        return [], False
    out: list[dict[str, Any]] = []
    corrupt = False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [], False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            corrupt = True
            append_audit_event(
                "CAPACITY_OBSERVATIONS_CORRUPT",
                {"path": str(path), "error": "json_decode", "line_prefix": line[:80]},
            )
            continue
        if not isinstance(rec, dict):
            corrupt = True
            append_audit_event(
                "CAPACITY_OBSERVATIONS_CORRUPT",
                {"path": str(path), "error": "not_object"},
            )
            continue
        out.append(rec)
    return out, corrupt


_REJECTED_OBS_HASHES: set[str] = set()


def _observation_record_hash(rec: dict[str, Any]) -> str:
    blob = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _audit_observation_rejected(rec: dict[str, Any], detail: dict[str, Any]) -> None:
    key = _observation_record_hash(rec)
    if key in _REJECTED_OBS_HASHES:
        return
    _REJECTED_OBS_HASHES.add(key)
    append_audit_event("CAPACITY_OBSERVATION_REJECTED", detail)


def _validate_observation_record(
    rec: dict[str, Any],
    now: datetime,
) -> tuple[bool, str]:
    observed_at = _parse_dt(rec.get("observed_at"))
    if observed_at is None:
        return False, "invalid_observed_at"
    if observed_at > now:
        return False, "future_observed_at"
    pct_map = rec.get("included_usage_pct")
    if pct_map is not None:
        if not isinstance(pct_map, dict):
            return False, "invalid_pct_map"
        for pool, pct in pct_map.items():
            if not _is_valid_pct(pct):
                return False, f"invalid_pct:{pool}"
    return True, ""


def _merge_pool_observations(
    records: list[dict[str, Any]],
    now: datetime,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Merge per (worker_id, pool); newest valid observed_at per pool wins."""
    merged: dict[str, dict[str, dict[str, Any]]] = {}
    for rec in records:
        wid = rec.get("worker_id")
        if not wid:
            continue
        ok, reason = _validate_observation_record(rec, now)
        if not ok:
            _audit_observation_rejected(
                rec,
                {"worker_id": wid, "reason": reason, "observed_at": rec.get("observed_at")},
            )
            continue
        observed_at = _parse_dt(rec.get("observed_at"))
        if observed_at is None:
            continue
        pct_map = rec.get("included_usage_pct") or {}
        if not isinstance(pct_map, dict):
            continue
        worker_pools = merged.setdefault(wid, {})
        for pool, pct in pct_map.items():
            if not _is_valid_pct(pct):
                _audit_observation_rejected(
                    rec,
                    {
                        "worker_id": wid,
                        "pool": pool,
                        "reason": "invalid_pct",
                        "value": pct,
                    },
                )
                continue
            prev = worker_pools.get(pool)
            if prev is None:
                worker_pools[pool] = {
                    "pct": float(pct),
                    "observed_at": observed_at,
                    "plan": rec.get("plan"),
                    "remaining": rec.get("remaining"),
                    "reset_at": rec.get("reset_at"),
                    "on_demand": rec.get("on_demand"),
                    "source": rec.get("source"),
                }
                continue
            if observed_at >= prev["observed_at"]:
                worker_pools[pool] = {
                    "pct": float(pct),
                    "observed_at": observed_at,
                    "plan": rec.get("plan") or prev.get("plan"),
                    "remaining": rec.get("remaining") if "remaining" in rec else prev.get("remaining"),
                    "reset_at": rec.get("reset_at") or prev.get("reset_at"),
                    "on_demand": rec.get("on_demand") or prev.get("on_demand"),
                    "source": rec.get("source") or prev.get("source"),
                }
    return merged


def _build_worker_obs(
    wid: str,
    pool_data: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any] | None:
    if not pool_data:
        return None
    pool = _primary_pool(wid, policy)
    pct_map = {p: d["pct"] for p, d in pool_data.items()}
    latest_at = max(d["observed_at"] for d in pool_data.values())
    latest_pool = max(pool_data.items(), key=lambda kv: kv[1]["observed_at"])[0]
    meta = pool_data[latest_pool]
    return {
        "worker_id": wid,
        "plan": meta.get("plan"),
        "included_usage_pct": pct_map,
        "remaining": meta.get("remaining"),
        "reset_at": meta.get("reset_at"),
        "on_demand": meta.get("on_demand", "UNKNOWN"),
        "source": meta.get("source"),
        "observed_at": latest_at.isoformat(timespec="seconds"),
        "_primary_pool": pool,
        "_pool_data": pool_data,
    }


def merge_observations(now: datetime | None = None) -> tuple[dict[str, dict[str, Any]], bool]:
    """Merge seed + persisted; newest observed_at per worker/pool wins."""
    now_dt = now or datetime.now(TZ)
    persisted, corrupt = _load_persisted()
    records = _load_seed() + persisted
    pool_merged = _merge_pool_observations(records, now_dt)
    policy = fail_closed_policy()
    merged: dict[str, dict[str, Any]] = {}
    all_workers = set(pool_merged.keys())
    for rec in records:
        wid = rec.get("worker_id")
        if wid:
            all_workers.add(wid)
    for wid in all_workers:
        obs = _build_worker_obs(wid, pool_merged.get(wid, {}), policy)
        if obs is not None:
            merged[wid] = obs
    return merged, corrupt


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
    pct_map = rec.get("included_usage_pct") or {}
    if not isinstance(pct_map, dict):
        append_audit_event(
            "CAPACITY_OBSERVATION_REJECTED",
            {"worker_id": worker_id, "reason": "invalid_pct_map", "observed_at": rec["observed_at"]},
        )
        return rec
    for pool, pct in pct_map.items():
        if not _is_valid_pct(pct):
            append_audit_event(
                "CAPACITY_OBSERVATION_REJECTED",
                {
                    "worker_id": worker_id,
                    "pool": pool,
                    "reason": "invalid_pct",
                    "value": pct,
                    "observed_at": rec["observed_at"],
                },
            )
            return rec
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
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                append_audit_event("LEDGER_CORRUPT", {"path": str(path), "error": "json_decode"})
                continue
            if rec.get("selected_worker") != worker_id or rec.get("decision") != "DISPATCH":
                continue
            ts = _parse_dt(rec.get("recorded_at"))
            if not ts or ts > now:
                continue
            if ts >= cutoff_7:
                counts["7d"] += 1
            if ts >= cutoff_24:
                counts["24h"] += 1
    except OSError:
        pass
    return counts


def _velocity(worker_id: str, pool: str | None, now: datetime) -> dict[str, Any]:
    """pct_per_day only when two observations of the same pool exist."""
    persisted, _ = _load_persisted()
    obs_list = [r for r in persisted + _load_seed() if r.get("worker_id") == worker_id]
    if pool:
        pairs = []
        for rec in obs_list:
            ok, _ = _validate_observation_record(rec, now)
            if not ok:
                continue
            pct_map = rec.get("included_usage_pct") or {}
            if pool in pct_map and _is_valid_pct(pct_map[pool]):
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
    if worker_id == GROK_WORKER_ID:
        th = root.get(GROK_WORKER_ID) or dict(HARDCODED_GROK_THRESHOLDS)
    else:
        th = root.get(worker_id) or root.get("default") or {
            "conserve_at": 70, "reserve_at": 85, "exhausted_at": 100,
        }
    return {
        "conserve_at": float(th["conserve_at"]),
        "reserve_at": float(th["reserve_at"]),
        "exhausted_at": float(th["exhausted_at"]),
    }


def _primary_pool(worker_id: str, policy: dict[str, Any]) -> str | None:
    pools = policy.get("primary_capacity_pool") or {}
    return pools.get(worker_id)


def _unknown_state(worker_id: str, policy: dict[str, Any]) -> str:
    decay_cfg = policy.get("capacity_decay") or {}
    unknown_cfg = decay_cfg.get("unknown_state") or {}
    unknown_default = unknown_cfg.get("default", "CONSERVE")
    return unknown_cfg.get(worker_id, unknown_cfg.get(GROK_WORKER_ID, unknown_default))


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

    pool = _primary_pool(worker_id, policy)
    thresholds = _worker_thresholds(worker_id, policy)
    grok_avail = grok_available is True

    if obs is None:
        if worker_id == "ollama_local" and pool is None:
            return {
                "worker_id": worker_id,
                "plan": "local",
                "included_usage_pct": {},
                "remaining": None,
                "reset_at": None,
                "velocity": _velocity(worker_id, pool, now),
                "projected_exhaustion_before_reset": None,
                "on_demand": "UNKNOWN",
                "source": "local",
                "observed_at": None,
                "effective_pct": None,
                "primary_pool": pool,
                "state": "NORMAL",
                "grok_available": grok_avail,
            }
        unk = _unknown_state(worker_id, policy)
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
            "grok_available": grok_avail,
        }

    pct_map = dict(obs.get("included_usage_pct") or {})
    pool_data = obs.get("_pool_data") or {}
    observed_at = _parse_dt(obs.get("observed_at"))

    if pool and pool in pct_map and _is_valid_pct(pct_map[pool]):
        observed_pct = float(pct_map[pool])
        pool_observed_at = (
            pool_data.get(pool, {}).get("observed_at") if pool_data else observed_at
        )
        if isinstance(pool_observed_at, datetime):
            observed_at = pool_observed_at
    elif pool and pool in pool_data:
        observed_pct = float(pool_data[pool]["pct"])
        observed_at = pool_data[pool]["observed_at"]
    elif pool is None and worker_id == "ollama_local":
        return {
            "worker_id": worker_id,
            "plan": obs.get("plan") or "local",
            "included_usage_pct": pct_map,
            "remaining": obs.get("remaining"),
            "reset_at": obs.get("reset_at"),
            "velocity": _velocity(worker_id, pool, now),
            "projected_exhaustion_before_reset": None,
            "on_demand": obs.get("on_demand", "UNKNOWN"),
            "source": obs.get("source") or "local",
            "observed_at": obs.get("observed_at"),
            "effective_pct": None,
            "primary_pool": pool,
            "state": "NORMAL",
            "grok_available": grok_avail,
        }
    else:
        unk = _unknown_state(worker_id, policy)
        return {
            "worker_id": worker_id,
            "plan": obs.get("plan"),
            "included_usage_pct": pct_map,
            "remaining": obs.get("remaining"),
            "reset_at": obs.get("reset_at"),
            "velocity": _velocity(worker_id, pool, now),
            "projected_exhaustion_before_reset": None,
            "on_demand": obs.get("on_demand", "UNKNOWN"),
            "source": obs.get("source"),
            "observed_at": obs.get("observed_at"),
            "effective_pct": None,
            "primary_pool": pool,
            "state": unk,
            "grok_available": grok_avail,
        }

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
    if projected is False:
        pass  # explicit false case preserved

    if worker_id == policy.get("grok_worker_id", GROK_WORKER_ID) and not grok_avail:
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
        "grok_available": grok_avail,
    }


def capacity_snapshot(
    now: datetime | str | None = None,
    policy: dict[str, Any] | None = None,
    *,
    grok_available: bool = True,
    worker_ids: list[str] | None = None,
    policy_mode: str | None = None,
) -> dict[str, Any]:
    effective_policy = policy
    if not effective_policy or policy_mode == "FAIL_CLOSED":
        effective_policy = fail_closed_policy()
    if isinstance(now, str):
        now_dt = _parse_dt(now) or datetime.now(TZ)
    elif now is None:
        now_dt = datetime.now(TZ)
    else:
        now_dt = now

    merged, observations_corrupt = merge_observations(now_dt)

    default_ids = [
        "cursor_sub", "grok_bot_sub", "claude_pro_sub", "codex_sub", "ollama_local", "gemini_free",
    ]
    ids = worker_ids or sorted(set(default_ids) | set(merged.keys()))
    workers = {}
    for wid in ids:
        raw_obs = merged.get(wid)
        if raw_obs:
            obs_for_rec = dict(raw_obs)
        else:
            obs_for_rec = None
        workers[wid] = worker_capacity_record(
            wid, obs_for_rec, effective_policy, now_dt, grok_available=grok_available
        )
    if observations_corrupt:
        grok_id = effective_policy.get("grok_worker_id", GROK_WORKER_ID)
        for wid, rec in workers.items():
            rec["state"] = _max_state(rec.get("state", "NORMAL"), "CONSERVE")
            if wid == grok_id:
                rec["state"] = _max_state(rec["state"], "RESERVE")
        workers[grok_id]["state"] = _max_state(workers.get(grok_id, {}).get("state", "CONSERVE"), "RESERVE")
    grok_id = effective_policy.get("grok_worker_id", GROK_WORKER_ID)
    return {
        "at": now_dt.isoformat(timespec="seconds"),
        "grok_state": workers.get(grok_id, {}).get("state", "UNKNOWN"),
        "grok_available": grok_available is True,
        "workers": workers,
        "observations_corrupt": observations_corrupt,
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
    grok_id = GROK_WORKER_ID
    if grok_id in workers:
        out["grok_state"] = workers[grok_id].get("state")
        out["grok_available"] = workers[grok_id].get("grok_available", True)
    return out
