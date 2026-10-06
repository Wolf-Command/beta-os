"""Worker allocation decisions — pure, deterministic, governance-enforced."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import worker_registry
from .adapters import live_gate
from .governance import (
    HARDCODED_FAIL_CLOSED_ORDER,
    PolicyLoad,
    append_audit_event,
    benchmark_class_for,
    grok_worker_id,
    is_protected_class,
    load_policy,
    metered_permitted,
    task_family,
)
from .paths import CONFIG_DIR, GOVERNANCE_DISPATCH_LEDGER_PATH, GOVERNANCE_TIGHTENING_PATH, ensure_dirs

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
        }


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


def load_tightening(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_dirs()
    default_pen, max_pen = _penalty_bounds(policy)
    if not GOVERNANCE_TIGHTENING_PATH.exists():
        return {"grok_routing_penalty": default_pen}
    try:
        raw = GOVERNANCE_TIGHTENING_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": str(exc), "action": "use_penalty_max"},
        )
        return {"grok_routing_penalty": max_pen}
    if not isinstance(data, dict):
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": "not_object", "action": "use_penalty_max"},
        )
        return {"grok_routing_penalty": max_pen}
    try:
        pen = float(data.get("grok_routing_penalty", default_pen))
    except (TypeError, ValueError):
        append_audit_event(
            "TIGHTENING_CORRUPT",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "error": "invalid_penalty", "action": "use_penalty_max"},
        )
        return {"grok_routing_penalty": max_pen}
    clamped = max(default_pen, min(pen, max_pen))
    if clamped != pen:
        append_audit_event(
            "TIGHTENING_CLAMPED",
            {"path": str(GOVERNANCE_TIGHTENING_PATH), "raw": pen, "clamped": clamped},
        )
    data["grok_routing_penalty"] = clamped
    return data


def save_tightening(data: dict[str, Any], policy: dict[str, Any] | None = None) -> None:
    ensure_dirs()
    default_pen, max_pen = _penalty_bounds(policy)
    out = dict(data)
    try:
        pen = float(out.get("grok_routing_penalty", default_pen))
    except (TypeError, ValueError):
        pen = max_pen
    out["grok_routing_penalty"] = max(default_pen, min(pen, max_pen))
    GOVERNANCE_TIGHTENING_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


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
    wrec = worker_registry.WORKERS.get(worker) or {}
    if wrec.get("billing_status") == "UNVERIFIED":
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
        text = (justification or "").strip()
        if len(text) < min_len:
            return "REJECTED", "GROK_JUSTIFICATION_INVALID:justification_too_short"
        return "ACCEPTED", ""

    return "REJECTED", "GROK_JUSTIFICATION_INVALID:unknown"


def _canonical_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    raw_class = work_item.get("task_class") or work_item.get("kind")
    requested = work_item.get("requested_worker")
    grok_code = work_item.get("grok_reason_code")
    grok_just = work_item.get("grok_justification")

    policy = policy_load.policy or {}
    effective_policy = policy if policy_load.mode == "ENFORCED" else None
    routing = _load_routing_policy()
    tightening = load_tightening(effective_policy)
    default_pen, _ = _penalty_bounds(effective_policy)
    penalty = float(tightening.get("grok_routing_penalty", default_pen))
    imb = policy.get("imbalance") or {}
    hard_block_at = float(imb.get("penalty_hard_block_at", 0.6))

    # Unclassified task class -> QUEUE, never Grok
    if not raw_class or task_family(raw_class, effective_policy) == "unknown":
        task_class = raw_class or ""
        bench_class = None
        family = "unknown"
        protected = False
        delegatable = False
        owner_action = policy_load.mode == "FAIL_CLOSED"
        owner_code = "OWNER_ACTION_REQUIRED" if owner_action else None
        dec = Decision(
            decision="QUEUE",
            selected_worker=None,
            ranked_candidates=[],
            task_family=family,
            delegatable=delegatable,
            protected=protected,
            grok_reason_code=grok_code,
            grok_reason_verdict=None,
            capacity_states={},
            policy_sha256=policy_load.sha256,
            policy_mode=policy_load.mode,
            grok_routing_penalty=penalty,
            alternatives_available=False,
            owner_action_required=owner_action,
            owner_action_code=owner_code,
            decision_hash=_canonical_hash({
                "work_item_id": wi_id,
                "task_class": task_class,
                "decision": "QUEUE",
                "selected_worker": None,
                "policy_sha256": policy_load.sha256,
                "policy_mode": policy_load.mode,
                "exclusion_notes": ["unclassified"],
            }),
            work_item_id=wi_id,
            task_class=task_class,
            exclusion_notes=["unclassified"],
        )
        if record:
            record_decision(dec, now=now)
        return dec

    task_class = raw_class
    bench_class = benchmark_class_for(task_class, effective_policy)
    if bench_class is None:
        bench_class = task_class

    family = task_family(task_class, effective_policy)
    protected = is_protected_class(task_class, effective_policy)
    delegatable = not protected
    grok_id = grok_worker_id(effective_policy)
    workers_cap = capacity.get("workers") or {}
    capacity_states = {w: (workers_cap.get(w) or {}).get("state", "UNKNOWN") for w in workers_cap}
    grok_rec = workers_cap.get(grok_id) or {}
    grok_state = grok_rec.get("state", "CONSERVE")
    grok_avail = grok_rec.get("grok_available", capacity.get("grok_available", True))

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

    eligible_non_grok: list[str] = []
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
        if ok and worker != grok_id:
            eligible_non_grok.append(worker)
        if not ok:
            candidates_scored.append(scored)
            continue

        if worker == grok_id:
            if not grok_avail:
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_unavailable"
                candidates_scored.append(scored)
                continue
            if protected:
                if grok_state == "EXHAUSTED":
                    scored["eligible"] = False
                    scored["exclusion_reason"] = "grok_exhausted_protected_queue"
                else:
                    scored["eligible"] = True
                    if raw_q is None:
                        quality_floor_waived_reason = "protected_class_no_benchmark"
                candidates_scored.append(scored)
                continue
            if policy_load.mode == "FAIL_CLOSED":
                scored["eligible"] = False
                scored["exclusion_reason"] = "policy_fail_closed"
                candidates_scored.append(scored)
                continue
            if grok_state == "EXHAUSTED":
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_exhausted"
                candidates_scored.append(scored)
                continue
            if grok_state == "RESERVE":
                scored["eligible"] = False
                scored["exclusion_reason"] = "grok_reserve_substantive_blocked"
                candidates_scored.append(scored)
                continue
            verdict, detail = _verify_grok_reason(
                grok_code, grok_just, bench_class, policy, routing,
                eligible_non_grok, grok_state, allowed_codes, penalty, hard_block_at,
            )
            if verdict == "REJECTED":
                scored["eligible"] = False
                scored["exclusion_reason"] = detail
                candidates_scored.append(scored)
                continue
            if raw_q is None:
                quality_floor_waived_reason = f"grok_substantive:{grok_code}"

        candidates_scored.append(scored)

    ranked_eligible = [c for c in candidates_scored if c.get("eligible")]
    alternatives = any(c["worker"] != grok_id for c in ranked_eligible)

    def effective_quality(c: dict[str, Any]) -> float:
        w = c["worker"]
        q = c.get("quality")
        base = float(q) if q is not None else 0.0
        if w == grok_id:
            return base - penalty
        return base

    def sort_key(c: dict[str, Any]) -> tuple:
        w = c["worker"]
        cap_rec = workers_cap.get(w) or {}
        eq = effective_quality(c)
        spec = _specialisation_rank(w, family, policy if effective_policy else {}, wi_id, cap_rec)
        cap_rank = STATE_RANK.get(cap_rec.get("state", "CONSERVE"), 1)
        lat = _latency_for(w, bench_class, routing)
        cost = _marginal_cost_rank(w, policy if effective_policy else {})
        return (-eq, spec, cap_rank, lat, cost, w)

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
    elif requested:
        req_c = next((c for c in candidates_scored if c["worker"] == requested and c.get("eligible")), None)
        if req_c:
            selected = requested
            decision_type = "DISPATCH"
    elif ranked_eligible:
        selected = ranked_eligible[0]["worker"]
        decision_type = "DISPATCH"

    if protected:
        grok_verdict = "NOT_APPLICABLE"
    elif grok_code:
        grok_verdict, _ = _verify_grok_reason(
            grok_code, grok_just, bench_class, policy, routing,
            eligible_non_grok, grok_state, allowed_codes, penalty, hard_block_at,
        )

    if policy_load.mode == "FAIL_CLOSED" and selected == grok_id and not protected:
        selected = None
        decision_type = "QUEUE"
        owner_action = True
        owner_code = "OWNER_ACTION_REQUIRED"

    if selected and worker_registry.is_metered(selected):
        selected = None
        decision_type = "QUEUE"
        owner_action = True
        owner_code = "OWNER_ACTION_REQUIRED"

    final_ranked = ranked_eligible + [c for c in candidates_scored if not c.get("eligible")]
    for i, c in enumerate(ranked_eligible):
        c["rank"] = i + 1
        c["scores"] = {
            "quality": c.get("quality"),
            "effective_quality": effective_quality(c),
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
    )

    if record:
        record_decision(dec, now=now)
    return dec


def record_decision(decision: Decision, now: datetime | str | None = None) -> dict[str, Any]:
    ensure_dirs()
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
    return rec


def metered_permitted_with_gate(policy_load: PolicyLoad | None = None) -> bool:
    """Consult governance paid_spend and live_gate — always False in this build."""
    if not metered_permitted(policy_load):
        return False
    try:
        cap = live_gate.cost_cap({})
        return cap is not None and cap > 0
    except Exception:
        return False


class LedgerView:
    """Read-only view of dispatch ledger for imbalance checks."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or GOVERNANCE_DISPATCH_LEDGER_PATH

    def decisions(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
        return out


def new_orchestrator_session(now: datetime | str | None = None) -> dict[str, Any]:
    """Fresh orchestrator context built purely from files — no prior memory."""
    from .capacity import capacity_snapshot
    from .imbalance import check_imbalance

    pl = load_policy()
    cap = capacity_snapshot(now)
    tightening = load_tightening(pl.policy)
    return {
        "policy_load": pl,
        "capacity": cap,
        "tightening": tightening,
        "routing_policy_path": str(ROUTING_POLICY_PATH),
        "now": cap.get("at"),
        "imbalance_checked": check_imbalance(pl, LedgerView(), now=now),
    }


def decide_and_record(
    work_item: dict[str, Any],
    now: datetime | str | None = None,
) -> Decision:
    from .capacity import capacity_snapshot

    ctx = new_orchestrator_session(now)
    return decide(
        work_item,
        policy_load=ctx["policy_load"],
        capacity=ctx["capacity"],
        ledger_view=LedgerView(),
        now=now,
        record=True,
    )
