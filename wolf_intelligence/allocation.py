"""Worker allocation decisions — pure, deterministic, governance-enforced."""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import worker_registry
from .adapters import live_gate
from .governance import (
    HARDCODED_FAIL_CLOSED_ORDER,
    HARDCODED_GROK_CONSERVE_CONDUCT,
    GROK_WORKER_ID,
    PolicyLoad,
    append_audit_event,
    benchmark_class_for,
    grok_worker_id,
    is_protected_class,
    load_policy,
    metered_permitted,
    task_family,
)
from .paths import (
    CONFIG_DIR,
    GOVERNANCE_AUDIT_PATH,
    GOVERNANCE_DISPATCH_LEDGER_PATH,
    GOVERNANCE_TIGHTENING_PATH,
    ensure_dirs,
)

TZ = ZoneInfo("Asia/Makassar")
ROUTING_POLICY_PATH = CONFIG_DIR / "routing-policy-real.json"

STATE_RANK = {"NORMAL": 0, "CONSERVE": 1, "RESERVE": 2, "EXHAUSTED": 3}
BILLING_COST_RANK = {"subscription": 0, "free": 1, "local": 2, "metered_api": 3}


@dataclass
class Decision:
    decision: str  # DISPATCH | QUEUE | DENY
    selected_worker: str | None
    ranked_candidates: list[dict[str, Any]]
    task_family: str
    delegatable: bool
    protected: bool
    grok_reason_code: str | None
    grok_reason_verdict: str | None
    capacity_states: dict[str, str]
    policy_sha256: str
    policy_mode: str
    grok_routing_penalty: float
    alternatives_available: bool
    owner_action_required: bool
    owner_action_code: str | None
    decision_hash: str
    work_item_id: str
    task_class: str
    exclusion_notes: list[str] = field(default_factory=list)
    quality_floor_waived_reason: str | None = None
    routing_policy_sha256: str | None = None
    requested_worker_rejected: str | None = None
    completion_event_format: str | None = None
    grok_conserve_conduct: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "selected_worker": self.selected_worker,
            "ranked_candidates": self.ranked_candidates,
            "task_family": self.task_family,
            "delegatable": self.delegatable,
            "protected": self.protected,
            "grok_reason_code": self.grok_reason_code,
            "grok_reason_verdict": self.grok_reason_verdict,
            "capacity_states": self.capacity_states,
            "policy_sha256": self.policy_sha256,
            "policy_mode": self.policy_mode,
            "grok_routing_penalty": self.grok_routing_penalty,
            "alternatives_available": self.alternatives_available,
            "owner_action_required": self.owner_action_required,
            "owner_action_code": self.owner_action_code,
            "decision_hash": self.decision_hash,
            "work_item_id": self.work_item_id,
            "task_class": self.task_class,
            "exclusion_notes": self.exclusion_notes,
            "quality_floor_waived_reason": self.quality_floor_waived_reason,
            "routing_policy_sha256": self.routing_policy_sha256,
            "requested_worker_rejected": self.requested_worker_rejected,
            "completion_event_format": self.completion_event_format,
            "grok_conserve_conduct": self.grok_conserve_conduct,
        }


def _routing_policy_sha256() -> str:
    try:
        raw = ROUTING_POLICY_PATH.read_bytes()
        return hashlib.sha256(raw).hexdigest()
    except OSError:
        return ""


def _load_routing_policy() -> dict[str, Any]:
    try:
        return json.loads(ROUTING_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"task_classes": {}}


def _penalty_bounds(policy: dict[str, Any] | None) -> tuple[float, float]:
    p = policy or {}
    default_pen = float(p.get("grok_routing_penalty_default", 0.0))
    imb = p.get("imbalance") or {}
    max_pen = float(imb.get("penalty_max", p.get("grok_routing_penalty_max", 1.0)))
    return default_pen, max_pen


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


def _audit_lines() -> tuple[list[dict[str, Any]], bool]:
    """Return parsed audit records and whether history is usable."""
    if not GOVERNANCE_AUDIT_PATH.exists():
        return [], False
    try:
        raw = GOVERNANCE_AUDIT_PATH.read_bytes()
    except OSError:
        return [], False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [], False
    records: list[dict[str, Any]] = []
    corrupt = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            corrupt = True
            continue
        if not isinstance(rec, dict):
            corrupt = True
            continue
        records.append(rec)
    return records, not corrupt and bool(records)


def _penalty_high_water_mark() -> tuple[float, bool]:
    """Highest audited penalty since the last valid owner reset. (hwm, audit_usable)."""
    records, usable = _audit_lines()
    hwm = 0.0
    for rec in records:
        event = rec.get("event")
        if event == "TIGHTENING_RESET":
            actor = rec.get("actor")
            if not isinstance(actor, str) or not actor.strip():
                continue
            val = rec.get("grok_routing_penalty")
            if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                hwm = float(val)
            continue
        if event in ("TIGHTENING_PENALTY", "ROUTING_IMBALANCE", "TIGHTENING_CORRUPT", "TIGHTENING_SAVE"):
            for key in ("penalty_after", "clamped", "grok_routing_penalty"):
                val = rec.get(key)
                if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                    hwm = max(hwm, float(val))
    return hwm, usable


def _established_install() -> bool:
    if not GOVERNANCE_DISPATCH_LEDGER_PATH.exists():
        return False
    try:
        for line in GOVERNANCE_DISPATCH_LEDGER_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("decision"):
                return True
    except OSError:
        return False
    return False


def _latest_valid_reset() -> tuple[float | None, datetime | None]:
    """Penalty and timestamp from the latest owner TIGHTENING_RESET audit record."""
    records, _ = _audit_lines()
    reset_pen: float | None = None
    reset_at: datetime | None = None
    for rec in records:
        if rec.get("event") != "TIGHTENING_RESET":
            continue
        actor = rec.get("actor")
        if not isinstance(actor, str) or not actor.strip():
            continue
        val = rec.get("grok_routing_penalty")
        if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
            reset_pen = float(val)
        ts = _parse_dt(rec.get("at") or rec.get("timestamp"))
        if ts is not None:
            reset_at = ts
    return reset_pen, reset_at


def _penalty_from_ledger() -> float:
    _, reset_at = _latest_valid_reset()
    hwm = 0.0
    for rec in LedgerView().decisions():
        ts = _parse_dt(rec.get("recorded_at"))
        if reset_at is not None and ts is not None and ts <= reset_at:
            continue
        pen = rec.get("grok_routing_penalty")
        if isinstance(pen, (int, float)) and not isinstance(pen, bool) and math.isfinite(pen):
            hwm = max(hwm, float(pen))
    return hwm


def _atomic_write_tightening(data: dict[str, Any]) -> None:
    ensure_dirs()
    tmp = GOVERNANCE_TIGHTENING_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, GOVERNANCE_TIGHTENING_PATH)


def load_tightening(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_dirs()
    default_pen, max_pen = _penalty_bounds(policy)
    hwm, audit_usable = _penalty_high_water_mark()
    hwm = max(hwm, _penalty_from_ledger())
    established = _established_install()
    audit_exists = GOVERNANCE_AUDIT_PATH.exists()

    def _effective(pen: float) -> float:
        clamped = max(default_pen, min(pen, max_pen))
        return max(clamped, hwm)

    def _hard_block() -> dict[str, Any]:
        return {"grok_routing_penalty": _effective(max_pen)}

    def _ledger_dispatch_count() -> int:
        return sum(1 for r in LedgerView().decisions() if r.get("decision") == "DISPATCH")

    def _needs_audit_recovery() -> bool:
        if not established or audit_usable:
            return False
        if audit_exists:
            return True
        imb = (policy or {}).get("imbalance") or {}
        min_samples = int(imb.get("min_samples", 5))
        if hwm > default_pen:
            return True
        if _ledger_dispatch_count() >= min_samples:
            return True
        return False

    if not GOVERNANCE_TIGHTENING_PATH.exists():
        if _needs_audit_recovery():
            return _hard_block()
        return {"grok_routing_penalty": _effective(default_pen)}

    try:
        raw_text = GOVERNANCE_TIGHTENING_PATH.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError) as exc:
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": str(exc), "action": "use_penalty_max"},
        )
        if _needs_audit_recovery():
            return _hard_block()
        return {"grok_routing_penalty": _effective(max_pen)}

    if not isinstance(data, dict):
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": "not_object", "action": "use_penalty_max"},
        )
        if _needs_audit_recovery():
            return _hard_block()
        return {"grok_routing_penalty": _effective(max_pen)}

    raw_pen = data.get("grok_routing_penalty", default_pen)
    if not isinstance(raw_pen, (int, float)) or isinstance(raw_pen, bool) or not math.isfinite(raw_pen):
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {
                "path": str(GOVERNANCE_TIGHTENING_PATH),
                "error": "invalid_penalty",
                "raw": raw_pen,
                "action": "use_penalty_max",
            },
        )
        if _needs_audit_recovery():
            return _hard_block()
        return {"grok_routing_penalty": _effective(max_pen)}

    pen = float(raw_pen)
    if pen < 0:
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": "negative_penalty", "raw": pen},
        )
        if _needs_audit_recovery():
            return _hard_block()
        return {"grok_routing_penalty": _effective(max_pen)}

    effective = _effective(pen)
    if _needs_audit_recovery() and effective < max_pen:
        return _hard_block()
    data["grok_routing_penalty"] = effective
    return data


def save_tightening(data: dict[str, Any], policy: dict[str, Any] | None = None) -> None:
    ensure_dirs()
    default_pen, max_pen = _penalty_bounds(policy)
    out = dict(data)
    raw_pen = out.get("grok_routing_penalty", default_pen)
    if not isinstance(raw_pen, (int, float)) or isinstance(raw_pen, bool) or not math.isfinite(raw_pen):
        pen = max_pen
    else:
        pen = float(raw_pen)
    pen = max(default_pen, min(pen, max_pen))
    hwm, _ = _penalty_high_water_mark()
    effective = max(pen, hwm)
    out["grok_routing_penalty"] = effective
    append_audit_event(
        "TIGHTENING_SAVE",
        {
            "reason": "save",
            "raw": raw_pen,
            "grok_routing_penalty": effective,
            "high_water_mark": hwm,
        },
    )
    _atomic_write_tightening(out)


class ResetPenaltyError(Exception):
    """Owner reset refused or failed before any state change."""


def reset_penalty(
    actor: str,
    policy: dict[str, Any] | None = None,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    """Owner reset of grok routing penalty to default. Audit-first transaction."""
    actor_s = actor.strip() if isinstance(actor, str) else ""
    if not actor_s:
        raise ResetPenaltyError("actor_required")
    reason_s = (reason or "owner_reset").strip() if reason is not None else "owner_reset"
    if not reason_s:
        raise ResetPenaltyError("reason_required")
    default_pen, _ = _penalty_bounds(policy)
    data = {"grok_routing_penalty": default_pen}
    try:
        append_audit_event(
            "TIGHTENING_RESET",
            {"actor": actor_s, "reason": reason_s, "grok_routing_penalty": default_pen},
            fsync=True,
        )
        append_audit_event(
            "TIGHTENING_PENALTY",
            {"reason": "owner_reset", "grok_routing_penalty": default_pen, "actor": actor_s},
            fsync=True,
        )
    except OSError as exc:
        raise ResetPenaltyError(f"audit_write_failed:{exc}") from exc
    _atomic_write_tightening(data)
    return data


def _quality_for(worker: str, bench_class: str, routing: dict[str, Any]) -> float | None:
    entry = (routing.get("task_classes") or {}).get(bench_class) or {}
    for row in entry.get("ranking") or []:
        if row.get("worker") == worker and "mean_quality" in row:
            return float(row["mean_quality"])
    return None


def _tie_band_workers(bench_class: str, routing: dict[str, Any], delta: float) -> set[str]:
    entry = (routing.get("task_classes") or {}).get(bench_class) or {}
    ranked = [r for r in entry.get("ranking") or [] if "mean_quality" in r]
    if not ranked:
        return set()
    top_q = max(float(r["mean_quality"]) for r in ranked)
    return {r["worker"] for r in ranked if top_q - float(r["mean_quality"]) <= delta}


def _latency_for(worker: str, bench_class: str, routing: dict[str, Any]) -> float:
    entry = (routing.get("task_classes") or {}).get(bench_class) or {}
    for row in entry.get("ranking") or []:
        if row.get("worker") == worker:
            lat = row.get("median_latency_ms")
            return float(lat) if isinstance(lat, (int, float)) else 9e12
    return 9e12


def _marginal_cost_rank(worker: str, policy: dict[str, Any]) -> int:
    billing = (worker_registry.WORKERS.get(worker) or {}).get("billing_class", "metered_api")
    order = policy.get("marginal_cost_order") or list(BILLING_COST_RANK.keys())
    try:
        return order.index(billing)
    except ValueError:
        return 99


def _specialisation_rank(
    worker: str,
    family: str,
    policy: dict[str, Any],
    work_item_id: str,
    capacity_rec: dict[str, Any],
) -> int:
    spec = (policy.get("specialisation") or {}).get(family) or {}
    prefer = spec.get("prefer_workers") or []
    if worker not in prefer:
        return 1
    if family == "engineering":
        if spec.get("require_included_capacity") and capacity_rec.get("state") == "EXHAUSTED":
            return 1
        return 0
    if family == "reasoning_review" and spec.get("tie_break") == "work_item_id_hash":
        idx = prefer.index(worker)
        h = int(hashlib.sha256(work_item_id.encode()).hexdigest(), 16)
        rotation = h % len(prefer)
        rotated = prefer[rotation:] + prefer[:rotation]
        return rotated.index(worker)
    return prefer.index(worker)


def _is_eligible_base(
    worker: str,
    task_class: str,
    bench_class: str,
    policy: dict[str, Any],
    routing: dict[str, Any],
    capacity_rec: dict[str, Any],
) -> tuple[bool, str]:
    if worker_registry.is_metered(worker):
        return False, "metered"
    if worker_registry.billing_unverified(worker):
        return False, "billing_unverified"
    if capacity_rec.get("state") == "EXHAUSTED":
        return False, "exhausted"
    gid = grok_worker_id(policy)
    if worker == gid:
        return True, ""
    floors = policy.get("quality_floors") or {}
    floor = float((floors.get("by_task_class") or {}).get(task_class, floors.get("default", 0.5)))
    q = _quality_for(worker, bench_class, routing)
    if q is None:
        if worker == "ollama_local":
            return False, "no_benchmark"
        return False, "no_benchmark"
    if q < floor:
        return False, "below_quality_floor"
    return True, ""


def _resolve_task_class(work_item: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (task_class, exclusion_note). Exact match only; no silent normalization."""
    task_class = work_item.get("task_class")
    kind = work_item.get("kind")
    if task_class is not None and kind is not None and task_class != kind:
        return None, "unclassified"
    if task_class is None:
        return None, "unclassified"
    if not isinstance(task_class, str):
        return None, "unclassified"
    if task_class != task_class.strip() or not task_class:
        return None, "unclassified"
    return task_class, None


def _grok_conserve_conduct(policy: dict[str, Any] | None) -> dict[str, Any]:
    conduct = (policy or {}).get("grok_conserve_conduct") or {}
    if not isinstance(conduct, dict):
        conduct = {}
    return {
        "no_grok_when_other_qualified": conduct.get(
            "no_grok_when_other_qualified",
            HARDCODED_GROK_CONSERVE_CONDUCT["no_grok_when_other_qualified"],
        ),
        "polling": conduct.get("polling", HARDCODED_GROK_CONSERVE_CONDUCT["polling"]),
        "completion_events": conduct.get(
            "completion_events",
            HARDCODED_GROK_CONSERVE_CONDUCT["completion_events"],
        ),
        "vesper_reserved_for": list(
            conduct.get("vesper_reserved_for", HARDCODED_GROK_CONSERVE_CONDUCT["vesper_reserved_for"])
        ),
    }


def _verify_grok_reason(
    code: str | None,
    justification: str | None,
    bench_class: str,
    policy: dict[str, Any],
    routing: dict[str, Any],
    eligible_non_grok: list[str],
    grok_state: str,
    allowed_codes: list[str],
    penalty: float,
    hard_block_at: float,
    *,
    conduct: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (verdict, detail). verdict: ACCEPTED | REJECTED | NOT_APPLICABLE."""
    min_len = int(policy.get("grok_justification_min_length", 20))
    delta = float(policy.get("tie_band_quality_delta", 0.05))
    grok = grok_worker_id(policy)

    if not code:
        return "REJECTED", "GROK_JUSTIFICATION_INVALID:missing_code"
    if code not in (policy.get("grok_reason_codes") or []):
        return "REJECTED", "GROK_JUSTIFICATION_INVALID:invalid_code"
    if code not in allowed_codes:
        return "REJECTED", f"GROK_JUSTIFICATION_INVALID:not_allowed_in_{grok_state}"

    if penalty >= hard_block_at and code != "OTHERS_UNAVAILABLE":
        return "REJECTED", "GROK_JUSTIFICATION_INVALID:penalty_hard_block"

    if code == "BENCHMARK_SELECTED":
        band = _tie_band_workers(bench_class, routing, delta)
        if grok not in band:
            return "REJECTED", "GROK_JUSTIFICATION_INVALID:benchmark_unverifiable"
        return "ACCEPTED", ""

    if code == "OTHERS_UNAVAILABLE":
        if eligible_non_grok:
            return "REJECTED", "GROK_JUSTIFICATION_INVALID:others_available"
        return "ACCEPTED", ""

    if code in ("REQUIRES_GROK_ENVIRONMENT", "EXPLICIT_JUSTIFIED"):
        text = justification.strip() if isinstance(justification, str) else ""
        if len(text) < min_len:
            return "REJECTED", "GROK_JUSTIFICATION_INVALID:justification_too_short"
        return "ACCEPTED", ""

    return "REJECTED", "GROK_JUSTIFICATION_INVALID:unknown"


def _canonical_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _k2_fallback_allowed(exclusion_reason: str | None) -> bool:
    """K2 dispatch only when canonical Grok was blocked by conserve conduct or reserve pressure."""
    if not exclusion_reason:
        return False
    if exclusion_reason.startswith("GROK_JUSTIFICATION_INVALID:"):
        return False
    return exclusion_reason.startswith("GROK_CONSERVE_CONDUCT:") or exclusion_reason in (
        "grok_reserve_substantive_blocked",
        "grok_exhausted",
        "grok_conserve_polling_forbidden",
        "grok_conserve_routine_review",
    )


def _audit_grok_rejection(
    work_item_id: str,
    task_class: str,
    code: str | None,
    detail: str,
) -> None:
    append_audit_event(
        "GROK_JUSTIFICATION_INVALID",
        {
            "work_item_id": work_item_id,
            "task_class": task_class,
            "grok_reason_code": code,
            "detail": detail,
        },
    )


def decide(
    work_item: dict[str, Any],
    *,
    policy_load: PolicyLoad,
    capacity: dict[str, Any],
    ledger_view: Any = None,
    now: datetime | str | None = None,
    record: bool = True,
) -> Decision:
    """Pure allocation decision. Optionally records to dispatch ledger."""
    wi_id = work_item.get("id") or work_item.get("work_item_id") or "anonymous"
    task_class, class_note = _resolve_task_class(work_item)
    requested = work_item.get("requested_worker")
    grok_code = work_item.get("grok_reason_code")
    grok_just = work_item.get("grok_justification")
    routing_sha = _routing_policy_sha256()

    policy = policy_load.policy or {}
    effective_policy = policy if policy_load.mode == "ENFORCED" else None
    routing = _load_routing_policy()
    tightening = load_tightening(effective_policy)
    default_pen, _ = _penalty_bounds(effective_policy)
    penalty = float(tightening.get("grok_routing_penalty", default_pen))
    imb = policy.get("imbalance") or {}
    hard_block_at = float(imb.get("penalty_hard_block_at", 0.6))

    if task_class is None or task_family(task_class, effective_policy) == "unknown":
        note = class_note or "unclassified"
        family = "unknown"
        protected = False
        delegatable = False
        owner_action = policy_load.mode == "FAIL_CLOSED"
        owner_code = "OWNER_ACTION_REQUIRED" if owner_action else None
        grok_verdict = "REJECTED" if grok_code or requested == grok_worker_id(effective_policy) else None
        dec = Decision(
            decision="QUEUE",
            selected_worker=None,
            ranked_candidates=[],
            task_family=family,
            delegatable=delegatable,
            protected=protected,
            grok_reason_code=grok_code,
            grok_reason_verdict=grok_verdict,
            capacity_states={},
            policy_sha256=policy_load.sha256,
            policy_mode=policy_load.mode,
            grok_routing_penalty=penalty,
            alternatives_available=False,
            owner_action_required=owner_action,
            owner_action_code=owner_code,
            decision_hash=_canonical_hash({
                "work_item_id": wi_id,
                "task_class": task_class or "",
                "decision": "QUEUE",
                "selected_worker": None,
                "policy_sha256": policy_load.sha256,
                "policy_mode": policy_load.mode,
                "exclusion_notes": [note],
            }),
            work_item_id=wi_id,
            task_class=task_class or "",
            exclusion_notes=[note],
            routing_policy_sha256=routing_sha,
        )
        if record:
            record_decision(dec, now=datetime.now(TZ))
        return dec

    bench_class = benchmark_class_for(task_class, effective_policy)
    if bench_class is None:
        bench_class = task_class

    family = task_family(task_class, effective_policy)
    conduct_cfg = _grok_conserve_conduct(effective_policy)
    grok_id = grok_worker_id(effective_policy)
    workers_cap = capacity.get("workers") or {}
    capacity_states = {w: (workers_cap.get(w) or {}).get("state", "UNKNOWN") for w in workers_cap}
    grok_rec = workers_cap.get(grok_id) or {}
    grok_state = grok_rec.get("state", "CONSERVE")
    grok_avail = grok_rec.get("grok_available") is True
    grok_conserve_or_stricter = STATE_RANK.get(grok_state, 0) >= STATE_RANK["CONSERVE"]
    vesper_reserved = set(conduct_cfg.get("vesper_reserved_for") or [])
    final_gate_reserved = task_class == "final_gate" and "final_gate" in vesper_reserved
    protected = is_protected_class(task_class, effective_policy) or (
        final_gate_reserved and grok_state not in ("EXHAUSTED",) and grok_avail
    )
    delegatable = not protected
    completion_event_format: str | None = None
    decision_conduct: dict[str, Any] | None = None
    if grok_conserve_or_stricter:
        decision_conduct = conduct_cfg
        if conduct_cfg.get("completion_events") == "COMPACT":
            completion_event_format = "COMPACT"

    reserve_cfg = policy.get("grok_reserve") or {}
    allowed_by_state = reserve_cfg.get("allowed_reason_codes_by_state") or {}
    allowed_codes = list(allowed_by_state.get(grok_state, []))

    owner_action = policy_load.mode == "FAIL_CLOSED"
    owner_code = "OWNER_ACTION_REQUIRED" if owner_action else None
    exclusions: list[str] = []
    quality_floor_waived_reason: str | None = None

    all_workers = set(worker_registry.WORKERS.keys()) - {
        w for w in worker_registry.WORKERS if worker_registry.is_metered(w)
    }
    candidates_scored: list[dict[str, Any]] = []

    # Pass 1: base eligibility for all workers (non-Grok alternatives computed first).
    base_eligible: dict[str, bool] = {}
    for worker in sorted(all_workers):
        cap_rec = workers_cap.get(worker) or {"state": "CONSERVE", "worker_id": worker}
        ok, reason = _is_eligible_base(
            worker, task_class, bench_class, policy if effective_policy else {}, routing, cap_rec
        )
        raw_q = _quality_for(worker, bench_class, routing)
        scored: dict[str, Any] = {
            "worker": worker,
            "eligible": ok,
            "exclusion_reason": reason if not ok else None,
            "capacity_state": cap_rec.get("state"),
            "quality": raw_q,
            "benchmark_class": bench_class,
        }
        base_eligible[worker] = ok
        if not ok:
            candidates_scored.append(scored)

    eligible_non_grok = [
        w for w in sorted(all_workers)
        if w != grok_id and base_eligible.get(w)
    ]

    # Pass 2: Grok-specific gates and remaining workers.
    for worker in sorted(all_workers):
        if not base_eligible.get(worker):
            continue
        cap_rec = workers_cap.get(worker) or {"state": "CONSERVE", "worker_id": worker}
        raw_q = _quality_for(worker, bench_class, routing)
        scored = next((c for c in candidates_scored if c["worker"] == worker), None)
        if scored is None:
            scored = {
                "worker": worker,
                "eligible": True,
                "exclusion_reason": None,
                "capacity_state": cap_rec.get("state"),
                "quality": raw_q,
                "benchmark_class": bench_class,
            }

        if worker == grok_id:
            if (
                grok_conserve_or_stricter
                and conduct_cfg.get("polling") == "FORBIDDEN"
                and task_class in ("polling", "status_poll")
            ):
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_conserve_polling_forbidden"
            elif grok_conserve_or_stricter and task_class == "routine_review":
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_conserve_routine_review"
            elif not grok_avail:
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_unavailable"
            elif protected:
                if grok_state == "EXHAUSTED":
                    scored["eligible"] = False
                    scored["exclusion_reason"] = "grok_exhausted_protected_queue"
                else:
                    scored["eligible"] = True
                    if raw_q is None:
                        quality_floor_waived_reason = "protected_class_no_benchmark"
            elif policy_load.mode == "FAIL_CLOSED":
                scored["eligible"] = False
                scored["exclusion_reason"] = "policy_fail_closed"
            elif grok_state == "EXHAUSTED":
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_exhausted"
            elif grok_state == "RESERVE":
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_reserve_substantive_blocked"
            elif (
                grok_conserve_or_stricter
                and conduct_cfg.get("no_grok_when_other_qualified")
                and eligible_non_grok
                and grok_code != "OTHERS_UNAVAILABLE"
            ):
                scored["eligible"] = False
                scored["exclusion_reason"] = "GROK_CONSERVE_CONDUCT:no_grok_when_other_qualified"
            else:
                verdict, detail = _verify_grok_reason(
                    grok_code, grok_just, bench_class, policy, routing,
                    eligible_non_grok, grok_state, allowed_codes, penalty, hard_block_at,
                    conduct=conduct_cfg,
                )
                if verdict == "REJECTED":
                    scored["eligible"] = False
                    scored["exclusion_reason"] = detail
                else:
                    if raw_q is None:
                        quality_floor_waived_reason = f"grok_substantive:{grok_code}"
        if scored not in candidates_scored:
            candidates_scored.append(scored)

    ranked_eligible = [c for c in candidates_scored if c.get("eligible")]
    alternatives = any(c["worker"] != grok_id for c in ranked_eligible)

    delta = float((policy if effective_policy else {}).get("tie_band_quality_delta", 0.05))

    def effective_quality(c: dict[str, Any]) -> float:
        w = c["worker"]
        q = c.get("quality")
        base = float(q) if q is not None else 0.0
        if w == grok_id:
            return base - penalty
        return base

    top_q = max((effective_quality(c) for c in ranked_eligible), default=0.0)

    def quality_band(c: dict[str, Any]) -> int:
        eq = effective_quality(c)
        if delta <= 0:
            return 0
        return int((top_q - eq) / delta + 1e-12)

    def sort_key(c: dict[str, Any]) -> tuple:
        w = c["worker"]
        cap_rec = workers_cap.get(w) or {}
        band = quality_band(c)
        spec = _specialisation_rank(w, family, policy if effective_policy else {}, wi_id, cap_rec)
        cap_rank = STATE_RANK.get(cap_rec.get("state", "CONSERVE"), 1)
        lat = _latency_for(w, bench_class, routing)
        cost = _marginal_cost_rank(w, policy if effective_policy else {})
        return (band, spec, cap_rank, lat, cost, w)

    ranked_eligible.sort(key=sort_key)

    if policy_load.mode == "FAIL_CLOSED":
        conservative = list(HARDCODED_FAIL_CLOSED_ORDER)
        ranked_eligible = [
            c for c in candidates_scored
            if c.get("eligible") and c["worker"] != grok_id and c["worker"] in conservative
        ]
        ranked_eligible.sort(key=lambda c: conservative.index(c["worker"]))

    selected = None
    decision_type = "QUEUE"
    grok_verdict = None
    requested_worker_rejected: str | None = None

    substantive_grok_requested = (
        not protected
        and (requested == grok_id or grok_code)
    )

    canonical_requested = None
    if requested:
        if requested in worker_registry.WORKERS:
            canonical_requested = requested
        else:
            requested_worker_rejected = "unknown"

    if protected:
        grok_eligible = next(
            (c for c in candidates_scored if c["worker"] == grok_id and c.get("eligible")),
            None,
        )
        if grok_eligible:
            selected = grok_id
            decision_type = "DISPATCH"
        else:
            decision_type = "QUEUE"
            exclusions.append("protected_grok_queued_recovery")
    elif canonical_requested:
        if worker_registry.is_metered(canonical_requested):
            requested_worker_rejected = "metered"
            decision_type = "QUEUE"
        elif canonical_requested == grok_id:
            req_c = next(
                (c for c in candidates_scored if c["worker"] == grok_id and c.get("eligible")),
                None,
            )
            if req_c:
                selected = grok_id
                decision_type = "DISPATCH"
            else:
                req_row = next((c for c in candidates_scored if c["worker"] == grok_id), None)
                excl = (req_row or {}).get("exclusion_reason") or "grok_ineligible"
                requested_worker_rejected = excl
                if ranked_eligible and _k2_fallback_allowed(excl):
                    selected = ranked_eligible[0]["worker"]
                    decision_type = "DISPATCH"
                    requested_worker_rejected = excl
                else:
                    decision_type = "QUEUE"
        elif policy_load.mode == "FAIL_CLOSED" and canonical_requested not in HARDCODED_FAIL_CLOSED_ORDER:
            requested_worker_rejected = requested_worker_rejected or "policy_fail_closed"
            decision_type = "QUEUE"
        else:
            req_c = next(
                (c for c in candidates_scored if c["worker"] == canonical_requested and c.get("eligible")),
                None,
            )
            if req_c:
                selected = canonical_requested
                decision_type = "DISPATCH"
            else:
                req_row = next((c for c in candidates_scored if c["worker"] == canonical_requested), None)
                requested_worker_rejected = (
                    requested_worker_rejected
                    or (req_row or {}).get("exclusion_reason")
                    or "ineligible"
                )
                decision_type = "QUEUE"
    elif requested:
        requested_worker_rejected = requested_worker_rejected or "unknown"
        decision_type = "QUEUE"
    elif ranked_eligible:
        selected = ranked_eligible[0]["worker"]
        decision_type = "DISPATCH"

    if protected:
        grok_verdict = "NOT_APPLICABLE"
    elif grok_code or requested == grok_id:
        grok_row = next((c for c in candidates_scored if c["worker"] == grok_id), None)
        grok_excl = (grok_row or {}).get("exclusion_reason")
        grok_rec = workers_cap.get(grok_id) or {}
        velocity_pressure = (
            grok_excl
            and grok_excl.startswith("GROK_CONSERVE_CONDUCT:")
            and (grok_rec.get("velocity") or {}).get("pct_per_hour") is not None
            and decision_type == "DISPATCH"
            and selected != grok_id
            and requested == grok_id
        )
        if velocity_pressure:
            grok_verdict = "REJECTED"
        elif grok_verdict is None:
            grok_verdict, detail = _verify_grok_reason(
                grok_code, grok_just, bench_class, policy, routing,
                eligible_non_grok, grok_state, allowed_codes, penalty, hard_block_at,
                conduct=conduct_cfg,
            )
    elif requested == grok_id and not grok_code:
        grok_verdict = "REJECTED"

    if policy_load.mode == "FAIL_CLOSED" and substantive_grok_requested:
        selected = None
        decision_type = "DENY"
        owner_action = True
        owner_code = "OWNER_ACTION_REQUIRED"
        if grok_verdict is None:
            grok_verdict = "REJECTED"

    if selected and worker_registry.is_metered(selected):
        selected = None
        decision_type = "QUEUE"
        owner_action = True
        owner_code = "OWNER_ACTION_REQUIRED"

    grok_substantive = requested == grok_id or bool(grok_code)
    if record and grok_substantive and not protected:
        audit_detail = None
        if grok_verdict == "REJECTED":
            _, audit_detail = _verify_grok_reason(
                grok_code, grok_just, bench_class, policy, routing,
                eligible_non_grok, grok_state, allowed_codes, penalty, hard_block_at,
                conduct=conduct_cfg,
            )
            if not audit_detail:
                audit_detail = "GROK_JUSTIFICATION_INVALID:missing_code"
        elif decision_type in ("QUEUE", "DENY") and selected != grok_id:
            grok_row = next((c for c in candidates_scored if c["worker"] == grok_id), None)
            audit_detail = (grok_row or {}).get("exclusion_reason") or f"grok_state:{grok_state}"
        elif decision_type == "DISPATCH" and selected != grok_id and requested == grok_id:
            grok_row = next((c for c in candidates_scored if c["worker"] == grok_id), None)
            audit_detail = (grok_row or {}).get("exclusion_reason") or requested_worker_rejected
        if audit_detail:
            _audit_grok_rejection(wi_id, task_class, grok_code, audit_detail)

    final_ranked = ranked_eligible + [c for c in candidates_scored if not c.get("eligible")]
    for i, c in enumerate(ranked_eligible):
        c["rank"] = i + 1
        c["scores"] = {
            "quality": c.get("quality"),
            "effective_quality": effective_quality(c),
            "quality_band": quality_band(c),
            "specialisation": _specialisation_rank(
                c["worker"], family, policy if effective_policy else {},
                wi_id, workers_cap.get(c["worker"]) or {}
            ),
            "capacity_state": c.get("capacity_state"),
        }

    hash_input = {
        "work_item_id": wi_id,
        "task_class": task_class,
        "benchmark_class": bench_class,
        "requested_worker": requested,
        "grok_reason_code": grok_code,
        "grok_justification": grok_just,
        "policy_sha256": policy_load.sha256,
        "policy_mode": policy_load.mode,
        "capacity_states": capacity_states,
        "grok_routing_penalty": penalty,
        "protected": protected,
        "decision": decision_type,
        "selected_worker": selected,
    }
    dhash = _canonical_hash(hash_input)

    dec = Decision(
        decision=decision_type,
        selected_worker=selected,
        ranked_candidates=final_ranked,
        task_family=family,
        delegatable=delegatable,
        protected=protected,
        grok_reason_code=grok_code,
        grok_reason_verdict=grok_verdict,
        capacity_states=capacity_states,
        policy_sha256=policy_load.sha256,
        policy_mode=policy_load.mode,
        grok_routing_penalty=penalty,
        alternatives_available=alternatives,
        owner_action_required=owner_action,
        owner_action_code=owner_code,
        decision_hash=dhash,
        work_item_id=wi_id,
        task_class=task_class,
        exclusion_notes=exclusions,
        quality_floor_waived_reason=quality_floor_waived_reason,
        routing_policy_sha256=routing_sha,
        requested_worker_rejected=requested_worker_rejected,
        completion_event_format=completion_event_format,
        grok_conserve_conduct=decision_conduct,
    )

    if record:
        record_decision(dec, now=datetime.now(TZ))
    return dec


def _ensure_tightening_baseline(policy: dict[str, Any] | None) -> None:
    """Persist default penalty on first decision so restart sees consistent state."""
    if GOVERNANCE_TIGHTENING_PATH.exists():
        return
    if _established_install():
        return
    default_pen, _ = _penalty_bounds(policy)
    data = {"grok_routing_penalty": default_pen}
    append_audit_event(
        "TIGHTENING_SAVE",
        {
            "reason": "first_decision_baseline",
            "grok_routing_penalty": default_pen,
        },
    )
    _atomic_write_tightening(data)


def record_decision(decision: Decision, now: datetime | str | None = None) -> dict[str, Any]:
    ensure_dirs()
    pl = load_policy()
    _ensure_tightening_baseline(pl.policy if pl.mode == "ENFORCED" else None)
    if isinstance(now, datetime):
        ts = now.isoformat(timespec="seconds")
    elif isinstance(now, str):
        ts = now
    else:
        ts = datetime.now(TZ).isoformat(timespec="seconds")
    rec = decision.to_dict()
    rec["recorded_at"] = ts
    with GOVERNANCE_DISPATCH_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    if decision.completion_event_format == "COMPACT":
        try:
            from . import events

            payload = {
                "decision": decision.decision,
                "selected_worker": decision.selected_worker,
                "task_class": decision.task_class,
                "format": "COMPACT",
            }
            events.emit("governance.decision_recorded", payload, work_item_id=decision.work_item_id)
        except ValueError:
            pass
    return rec


class LedgerView:
    """Read-only view of dispatch ledger for imbalance checks."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or GOVERNANCE_DISPATCH_LEDGER_PATH
        self._corrupt_logged = False

    def _audit_corrupt_once(self, error: str) -> None:
        if self._corrupt_logged:
            return
        self._corrupt_logged = True
        append_audit_event("LEDGER_CORRUPT", {"path": str(self.path), "error": error})

    def _valid_record(self, rec: Any, now: datetime | None = None) -> bool:
        if not isinstance(rec, dict):
            return False
        ts_raw = rec.get("recorded_at")
        if ts_raw is None:
            return False
        if isinstance(ts_raw, (int, float)):
            return False
        ts = _parse_dt(ts_raw if isinstance(ts_raw, str) else None)
        if ts is None:
            return False
        if now is not None and ts > now:
            return False
        return True

    def decisions(self, now: datetime | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    self._audit_corrupt_once("json_decode")
                    continue
                if not self._valid_record(rec, now=now):
                    self._audit_corrupt_once("invalid_record")
                    continue
                out.append(rec)
        except OSError:
            pass
        return out


def metered_permitted_with_gate(policy_load: PolicyLoad | None = None) -> bool:
    """Consult governance paid_spend and live_gate."""
    if not metered_permitted(policy_load):
        return False
    try:
        cap = live_gate.cost_cap({})
        return cap is not None and cap > 0
    except Exception:
        return False


def new_orchestrator_session(now: datetime | str | None = None) -> dict[str, Any]:
    """Fresh orchestrator context built purely from files — read-only, no tightening writes."""
    from .capacity import capacity_snapshot

    pl = load_policy()
    cap = capacity_snapshot(
        now,
        policy=pl.policy,
        policy_mode=pl.mode,
    )
    tightening = load_tightening(pl.policy)
    return {
        "policy_load": pl,
        "capacity": cap,
        "tightening": tightening,
        "routing_policy_path": str(ROUTING_POLICY_PATH),
        "routing_policy_sha256": _routing_policy_sha256(),
        "now": cap.get("at"),
    }


def decide_and_record(
    work_item: dict[str, Any],
    now: datetime | str | None = None,
) -> tuple[Decision, dict[str, Any]]:
    from .capacity import capacity_snapshot
    from .imbalance import check_imbalance

    pl = load_policy()
    server_now = datetime.now(TZ)
    cap = capacity_snapshot(server_now, policy=pl.policy, policy_mode=pl.mode)
    dec = decide(
        work_item,
        policy_load=pl,
        capacity=cap,
        ledger_view=LedgerView(),
        now=server_now,
        record=True,
    )
    check_imbalance(pl, LedgerView(), now=server_now)
    meta = {"clock": "test"} if now is not None else {"clock": "server"}
    return dec, meta
