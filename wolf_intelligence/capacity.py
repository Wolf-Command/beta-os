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
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return 0 <= value <= 100
    if not math.isfinite(value):
        return False
    return 0.0 <= float(value) <= 100.0


def _load_seed() -> list[dict[str, Any]]:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("observations") or [])


_PERSISTED_CACHE: tuple[int, list[dict[str, Any]], bool] | None = None
_CORRUPT_AUDITED_MTIME: int | None = None


def _load_persisted() -> tuple[list[dict[str, Any]], bool]:
    global _PERSISTED_CACHE, _CORRUPT_AUDITED_MTIME
    path = GOVERNANCE_CAPACITY_OBSERVATIONS_PATH
    if not path.exists():
        _PERSISTED_CACHE = (0, [], False)
        return [], False
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return [], False
    if _PERSISTED_CACHE is not None and _PERSISTED_CACHE[0] == mtime:
        return _PERSISTED_CACHE[1], _PERSISTED_CACHE[2]
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
            continue
        if not isinstance(rec, dict):
            corrupt = True
            continue
        out.append(rec)
    if corrupt and _CORRUPT_AUDITED_MTIME != mtime:
        _CORRUPT_AUDITED_MTIME = mtime
        append_audit_event(
            "CAPACITY_OBSERVATIONS_CORRUPT",
            {"path": str(path), "error": "corrupt_lines"},
        )
    _PERSISTED_CACHE = (mtime, out, corrupt)
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
            if observed_at > prev["observed_at"]:
                worker_pools[pool] = {
                    "pct": float(pct),
                    "observed_at": observed_at,
                    "plan": rec.get("plan") or prev.get("plan"),
                    "remaining": rec.get("remaining") if "remaining" in rec else prev.get("remaining"),
                    "reset_at": rec.get("reset_at") or prev.get("reset_at"),
                    "on_demand": rec.get("on_demand") or prev.get("on_demand"),
                    "source": rec.get("source") or prev.get("source"),
                }
            elif observed_at == prev["observed_at"]:
                worker_pools[pool] = {
                    "pct": max(float(pct), float(prev["pct"])),
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


def _seed_latest_pool_observation(worker_id: str, pool: str) -> tuple[datetime | None, float | None]:
    latest_at: datetime | None = None
    latest_pct: float | None = None
    for rec in _load_seed():
        if rec.get("worker_id") != worker_id:
            continue
        pct_map = rec.get("included_usage_pct") or {}
        if pool not in pct_map or not _is_valid_pct(pct_map[pool]):
            continue
        observed = _parse_dt(rec.get("observed_at"))
        if observed is None:
            continue
        if latest_at is None or observed > latest_at:
            latest_at = observed
            latest_pct = float(pct_map[pool])
    return latest_at, latest_pct


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
    observed_at_s = observed_at or datetime.now(TZ).isoformat(timespec="seconds")
    pct_map_in = included_usage_pct or {}
    if isinstance(pct_map_in, dict):
        obs_dt = _parse_dt(observed_at_s)
        if obs_dt is not None:
            thresholds = _worker_thresholds(worker_id, fail_closed_policy())
            exhausted_at = thresholds["exhausted_at"]
            for pool, pct in pct_map_in.items():
                if not _is_valid_pct(pct):
                    continue
                seed_at, seed_pct = _seed_latest_pool_observation(worker_id, pool)
                if (
                    seed_at is not None
                    and seed_pct is not None
                    and seed_at > obs_dt
                    and float(pct) >= exhausted_at
                    and float(pct) > seed_pct
                ):
                    observed_at_s = datetime.now(TZ).isoformat(timespec="seconds")
                    break
    rec = {
        "worker_id": worker_id,
        "plan": plan,
        "included_usage_pct": included_usage_pct or {},
        "remaining": remaining,
        "reset_at": reset_at,
        "on_demand": on_demand,
        "source": source,
        "observed_at": observed_at_s,
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


def _velocity_config(policy: dict[str, Any]) -> dict[str, Any]:
    from .governance import HARDCODED_VELOCITY

    cfg = policy.get("velocity") or {}
    if not isinstance(cfg, dict):
        cfg = {}
    return {
        "window_hours": float(cfg.get("window_hours", HARDCODED_VELOCITY["window_hours"])),
        "min_points": int(cfg.get("min_points", HARDCODED_VELOCITY["min_points"])),
        "min_span_minutes": float(cfg.get("min_span_minutes", HARDCODED_VELOCITY["min_span_minutes"])),
        "reserve_if_exhaustion_within_hours": float(
            cfg.get("reserve_if_exhaustion_within_hours", HARDCODED_VELOCITY["reserve_if_exhaustion_within_hours"])
        ),
        "assumed_reset_hours_if_unknown": float(
            cfg.get("assumed_reset_hours_if_unknown", HARDCODED_VELOCITY["assumed_reset_hours_if_unknown"])
        ),
        "short_slope_window_hours": float(
            cfg.get(
                "short_slope_window_hours",
                min(24.0, float(cfg.get("window_hours", HARDCODED_VELOCITY["window_hours"]))),
            )
        ),
    }


def _pool_velocity_pairs(
    worker_id: str,
    pool: str,
    now: datetime,
    window_hours: float,
) -> list[tuple[datetime, float]]:
    cutoff = now - timedelta(hours=window_hours)
    persisted, _ = _load_persisted()
    worker_persisted = [r for r in persisted if r.get("worker_id") == worker_id]
    if worker_persisted:
        obs_list = worker_persisted
    else:
        obs_list = [r for r in _load_seed() if r.get("worker_id") == worker_id]
    pairs: list[tuple[datetime, float]] = []
    for rec in obs_list:
        ok, _ = _validate_observation_record(rec, now)
        if not ok:
            continue
        pct_map = rec.get("included_usage_pct") or {}
        if pool not in pct_map or not _is_valid_pct(pct_map[pool]):
            continue
        t = _parse_dt(rec.get("observed_at"))
        if t is None or t < cutoff:
            continue
        pairs.append((t, float(pct_map[pool])))
    pairs.sort(key=lambda x: x[0])
    deduped: list[tuple[datetime, float]] = []
    for t, p in pairs:
        if deduped and deduped[-1][0] == t:
            deduped[-1] = (t, max(deduped[-1][1], p))
        else:
            deduped.append((t, p))
    return deduped


def _record_observed_dt(rec: dict[str, Any]) -> datetime | None:
    return _parse_dt(rec.get("observed_at"))


def _newest_pool_record_issue(
    worker_id: str,
    pool: str,
    now: datetime,
    max_age_h: float,
) -> tuple[bool, str]:
    """Fail closed only on timestamp issues inside the freshness window."""
    persisted, _ = _load_persisted()
    records = [
        r
        for r in persisted + _load_seed()
        if r.get("worker_id") == worker_id and pool in (r.get("included_usage_pct") or {})
    ]
    if not records:
        return False, ""

    window_cutoff = now - timedelta(hours=max_age_h)
    newest: dict[str, Any] | None = None
    newest_at: datetime | None = None
    earliest_at: datetime | None = None
    valid_times: list[datetime] = []

    for rec in records:
        ok, reason = _validate_observation_record(rec, now)
        observed_at = _record_observed_dt(rec)
        if not ok:
            if observed_at is not None and observed_at < window_cutoff:
                continue
            append_audit_event(
                "CAPACITY_OBSERVATION_REJECTED",
                {
                    "worker_id": worker_id,
                    "pool": pool,
                    "reason": reason,
                    "observed_at": rec.get("observed_at"),
                    "fail_closed": True,
                },
            )
            return True, reason
        if observed_at is None:
            continue
        valid_times.append(observed_at)
        if newest_at is None or observed_at > newest_at:
            newest_at = observed_at
            newest = rec
        if earliest_at is None or observed_at < earliest_at:
            earliest_at = observed_at

    if newest is None or newest_at is None:
        return True, "invalid_observed_at"

    newest_age_h = (now - newest_at).total_seconds() / 3600.0
    if newest_age_h > max_age_h:
        append_audit_event(
            "CAPACITY_OBSERVATION_STALE",
            {
                "worker_id": worker_id,
                "pool": pool,
                "observed_at": newest.get("observed_at"),
                "age_hours": round(newest_age_h, 4),
                "max_age_hours": max_age_h,
            },
        )
        return True, "stale_observation"

    if earliest_at is None:
        return False, ""

    newest_pct = float((newest.get("included_usage_pct") or {}).get(pool, 0))

    for rec in records:
        observed_at = _record_observed_dt(rec)
        if observed_at is None:
            append_audit_event(
                "CAPACITY_OBSERVATION_REJECTED",
                {
                    "worker_id": worker_id,
                    "pool": pool,
                    "observed_at": rec.get("observed_at"),
                    "reason": "invalid_observed_at",
                    "fail_closed": True,
                },
            )
            return True, "invalid_observed_at"
        if observed_at >= newest_at:
            continue
        age_h = (now - observed_at).total_seconds() / 3600.0
        if age_h <= max_age_h:
            continue
        older_pct = (rec.get("included_usage_pct") or {}).get(pool)
        if not _is_valid_pct(older_pct):
            continue
        if float(older_pct) < newest_pct:
            continue
        intervening_drop = False
        for other in records:
            other_at = _record_observed_dt(other)
            if other_at is None or other_at <= observed_at or other_at >= newest_at:
                continue
            other_pct = (other.get("included_usage_pct") or {}).get(pool)
            if _is_valid_pct(other_pct) and float(other_pct) < float(older_pct):
                intervening_drop = True
                break
        if intervening_drop:
            continue
        append_audit_event(
            "CAPACITY_OBSERVATION_STALE",
            {
                "worker_id": worker_id,
                "pool": pool,
                "observed_at": rec.get("observed_at"),
                "age_hours": round(age_h, 4),
                "max_age_hours": max_age_h,
                "stale_pollution": True,
            },
        )
        return True, "stale_pollution"

    return False, ""


def _reset_at_for_worker(worker_id: str, pool: str, pairs: list[tuple[datetime, float]]) -> datetime | None:
    newest_at: datetime | None = None
    reset_dt: datetime | None = None
    persisted, _ = _load_persisted()
    for rec in persisted + _load_seed():
        if rec.get("worker_id") != worker_id:
            continue
        pct_map = rec.get("included_usage_pct") or {}
        if pool not in pct_map:
            continue
        observed = _record_observed_dt(rec)
        if observed is None:
            continue
        candidate = _parse_dt(rec.get("reset_at"))
        if candidate is None:
            continue
        if newest_at is None or observed > newest_at:
            newest_at = observed
            reset_dt = candidate
    return reset_dt


def _split_pairs_at_drops(pairs: list[tuple[datetime, float]]) -> list[list[tuple[datetime, float]]]:
    if not pairs:
        return []
    segments: list[list[tuple[datetime, float]]] = [[pairs[0]]]
    for i in range(1, len(pairs)):
        t, p = pairs[i]
        _, prev_p = pairs[i - 1]
        if p < prev_p:
            segments.append([(t, p)])
        else:
            segments[-1].append((t, p))
    return segments


def _steepest_slope(
    pairs: list[tuple[datetime, float]],
    min_span_minutes: float,
    *,
    enforce_min_span: bool = True,
    min_significant_pct_delta: float = 5.0,
) -> tuple[float | None, float | None]:
    """Return (max_pct_per_hour, span_hours) from steepest valid pairwise slope."""
    if len(pairs) < 2:
        return None, None
    best_slope: float | None = None
    best_span_h: float | None = None
    n = len(pairs)
    for i in range(n):
        t0, p0 = pairs[i]
        for j in range(i + 1, n):
            t1, p1 = pairs[j]
            span_h = (t1 - t0).total_seconds() / 3600.0
            if span_h <= 0:
                continue
            delta = p1 - p0
            if enforce_min_span and span_h * 60.0 < min_span_minutes:
                if delta < min_significant_pct_delta:
                    continue
            slope = delta / span_h
            if best_slope is None or slope > best_slope:
                best_slope = slope
                best_span_h = span_h
    return best_slope, best_span_h


def _velocity_projection(
    worker_id: str,
    pool: str | None,
    now: datetime,
    policy: dict[str, Any],
    thresholds: dict[str, float],
    latest_pct: float | None,
    reset_at: str | None,
) -> tuple[dict[str, Any], bool | None, float | None]:
    """Compute velocity metrics, projected_exhaustion_before_reset, hours_to_exhaustion."""
    disp = _dispatch_counts(worker_id, now)
    vel: dict[str, Any] = {
        "dispatch_24h": disp["24h"],
        "dispatch_7d": disp["7d"],
        "pct_per_hour": None,
        "pct_per_day": None,
        "hours_to_exhaustion": None,
        "points_in_window": 0,
    }
    if not pool or latest_pct is None:
        return vel, None, None

    cfg = _velocity_config(policy)
    pairs = _pool_velocity_pairs(worker_id, pool, now, cfg["window_hours"])
    vel["points_in_window"] = len(pairs)
    if len(pairs) < cfg["min_points"]:
        return vel, None, None

    segments = _split_pairs_at_drops(pairs)
    active = segments[-1] if segments else pairs
    if len(active) < cfg["min_points"]:
        active = pairs

    post_drop_recovery_h = float(cfg.get("post_drop_recovery_hours", 24.0))
    post_drop_recovery = False
    if len(segments) > 1 and len(active) >= cfg["min_points"]:
        active_span_h = (active[-1][0] - active[0][0]).total_seconds() / 3600.0
        if active_span_h < post_drop_recovery_h:
            post_drop_recovery = True

    recent_cutoff = now - timedelta(hours=cfg["short_slope_window_hours"])
    recent_active = [(t, p) for t, p in active if t >= recent_cutoff]
    slope_pairs = recent_active if len(recent_active) >= cfg["min_points"] else []
    short_slope, _ = _steepest_slope(
        slope_pairs,
        cfg["min_span_minutes"],
        enforce_min_span=True,
    )
    long_slope: float | None = None
    if len(active) >= cfg["min_points"]:
        t0, p0 = active[0]
        t1, p1 = active[-1]
        span_h = (t1 - t0).total_seconds() / 3600.0
        if span_h > 0 and span_h * 60.0 >= cfg["min_span_minutes"]:
            long_slope = (p1 - p0) / span_h

    pct_per_hour = short_slope
    if long_slope is not None and (pct_per_hour is None or long_slope > pct_per_hour):
        pct_per_hour = long_slope
    if pct_per_hour is None:
        return vel, False, None

    vel["pct_per_hour"] = round(pct_per_hour, 4)
    vel["pct_per_day"] = round(pct_per_hour * 24.0, 4)

    exhausted_at = float(thresholds["exhausted_at"])
    reset_dt = _parse_dt(reset_at) or _reset_at_for_worker(worker_id, pool, pairs)

    def _hours_for_slope(slope: float | None) -> float | None:
        if slope is None or slope <= 0:
            return None
        hte = (exhausted_at - latest_pct) / slope
        return hte if hte > 0 else None

    def _projected_for_slope(slope: float | None) -> bool | None:
        if slope is None:
            return None
        if slope <= 0:
            return False
        hte = _hours_for_slope(slope)
        if hte is None:
            return False
        if reset_dt is None or reset_dt <= now:
            return True
        exhaustion_at = now + timedelta(hours=hte)
        return exhaustion_at < reset_dt

    projected_short = _projected_for_slope(short_slope)
    projected_long = _projected_for_slope(long_slope)
    if projected_short is None and projected_long is None:
        projected = None
    elif projected_short is True or projected_long is True:
        projected = True
    elif projected_short is False and projected_long is False:
        projected = False
    else:
        projected = projected_short if projected_long is None else projected_long

    if post_drop_recovery:
        projected = False

    short_hours = _hours_for_slope(short_slope)
    long_hours = _hours_for_slope(long_slope)
    hour_candidates = [h for h in (short_hours, long_hours) if h is not None]
    hours_to_exhaustion = min(hour_candidates) if hour_candidates else None
    if hours_to_exhaustion is not None:
        vel["hours_to_exhaustion"] = round(hours_to_exhaustion, 4)

    if post_drop_recovery:
        vel["velocity_state"] = "NORMAL"
    else:
        vel["velocity_state"] = _max_state(
            _velocity_state_from_projection(projected_short, short_hours, policy),
            _velocity_state_from_projection(projected_long, long_hours, policy),
        )

    return vel, projected, hours_to_exhaustion


def _velocity_state_from_projection(
    projected: bool | None,
    hours_to_exhaustion: float | None,
    policy: dict[str, Any],
) -> str:
    cfg = _velocity_config(policy)
    state = "NORMAL"
    if projected is True:
        state = _max_state(state, "CONSERVE")
    if (
        hours_to_exhaustion is not None
        and hours_to_exhaustion > 0
        and hours_to_exhaustion <= cfg["reserve_if_exhaustion_within_hours"]
    ):
        state = _max_state(state, "RESERVE")
    return state


def _velocity(worker_id: str, pool: str | None, now: datetime, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    effective_policy = policy or fail_closed_policy()
    thresholds = _worker_thresholds(worker_id, effective_policy)
    vel, _, _ = _velocity_projection(worker_id, pool, now, effective_policy, thresholds, None, None)
    return vel


def _observation_records_for_worker(worker_id: str) -> list[dict[str, Any]]:
    persisted, _ = _load_persisted()
    worker_persisted = [r for r in persisted if r.get("worker_id") == worker_id]
    if worker_persisted:
        return worker_persisted
    return [r for r in _load_seed() if r.get("worker_id") == worker_id]


def _peak_raw_pct(
    worker_id: str,
    pool: str,
    now: datetime,
    window_hours: float,
) -> float | None:
    pairs = _pool_velocity_pairs(worker_id, pool, now, window_hours)
    if not pairs:
        return None
    segments = _split_pairs_at_drops(pairs)
    active = segments[-1] if segments else pairs
    active_peak = max(p for _, p in active)
    if len(active) == 1 and len(segments) > 1:
        prev_peak = max(p for _, p in segments[-2])
        active_t, active_p = active[0]
        drop_span_h = (active_t - segments[-2][-1][0]).total_seconds() / 3600.0
        if drop_span_h < 24.0 and (prev_peak - active_p) >= 5.0:
            return max(active_peak, prev_peak)
    return active_peak


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
                "velocity": _velocity(worker_id, pool, now, policy),
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
            "velocity": _velocity(worker_id, pool, now, policy),
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
            "velocity": _velocity(worker_id, pool, now, policy),
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
            "velocity": _velocity(worker_id, pool, now, policy),
            "projected_exhaustion_before_reset": None,
            "on_demand": obs.get("on_demand", "UNKNOWN"),
            "source": obs.get("source"),
            "observed_at": obs.get("observed_at"),
            "effective_pct": None,
            "primary_pool": pool,
            "state": unk,
            "grok_available": grok_avail,
        }

    timestamp_issue = False
    if pool:
        timestamp_issue, _ = _newest_pool_record_issue(worker_id, pool, now, max_age_h)

    effective = _effective_pct(observed_pct, observed_at, now, decay_rate)
    vel_cfg = _velocity_config(policy)
    peak_raw = _peak_raw_pct(worker_id, pool, now, vel_cfg["window_hours"]) if pool else None
    state_pct = max(effective, peak_raw) if peak_raw is not None else effective
    state = _state_from_pct(state_pct, thresholds)

    if observed_at:
        age_h = (now - observed_at).total_seconds() / 3600.0
        if age_h > max_age_h:
            state = _max_state(state, "CONSERVE")

    if timestamp_issue:
        state = _max_state(state, "CONSERVE")

    vel, projected, hours_to_exhaustion = _velocity_projection(
        worker_id,
        pool,
        now,
        policy,
        thresholds,
        effective,
        obs.get("reset_at"),
    )
    vel_state = vel.pop("velocity_state", None) or _velocity_state_from_projection(
        projected, hours_to_exhaustion, policy
    )
    state = _max_state(state, vel_state)

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
        grok_rec = workers.get(grok_id)
        if grok_rec is not None:
            grok_rec["state"] = _max_state(grok_rec.get("state", "CONSERVE"), "RESERVE")
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
