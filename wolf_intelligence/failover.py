"""Deterministic worker failover — no LLM in the control loop."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import paths, worker_registry
from .capacity import TZ
from .governance import GROK_WORKER_ID, load_policy, metered_permitted

CAPABILITIES = frozenset(
    {
        "build",
        "debug",
        "test",
        "review_reasoning",
        "review_accounting",
        "review_ux",
        "review_security",
        "review_architecture",
        "review_large_context",
        "redteam",
    }
)

COMMISSIONING_STATES = frozenset({"commissioned", "suspended", "not_commissioned"})

AVAILABILITY_STATES = frozenset(
    {
        "available",
        "session_limit",
        "weekly_limit",
        "capacity_reserve",
        "auth_failure",
        "provider_outage",
        "timeout",
        "unavailable_confirmed",
    }
)

STATE_RANK = {"NORMAL": 0, "CONSERVE": 1, "RESERVE": 2, "EXHAUSTED": 3}

KIND_DEFAULT_CAPABILITY = {
    "build": "build",
    "test": "test",
    "review": "review_reasoning",
}

PREFERRED_BY_CAPABILITY: dict[str, tuple[str, ...]] = {
    "build": ("cursor_sub",),
    "debug": ("cursor_sub",),
    "test": ("cursor_sub",),
    "review_reasoning": ("claude_pro_sub", "codex_sub"),
    "review_accounting": ("claude_pro_sub", "codex_sub"),
    "review_ux": ("claude_pro_sub", "codex_sub"),
    "review_security": ("claude_pro_sub", "codex_sub"),
    "review_architecture": ("claude_pro_sub", "codex_sub"),
    "review_large_context": ("claude_pro_sub", "codex_sub"),
    "redteam": ("claude_pro_sub", "codex_sub"),
}

FALLBACK_BY_CAPABILITY: dict[str, tuple[str, ...]] = {
    "build": ("codex_sub",),
    "debug": ("codex_sub",),
    "test": ("codex_sub",),
    "review_reasoning": ("codex_sub",),
    "review_accounting": ("codex_sub",),
    "review_ux": ("codex_sub",),
    "review_security": ("codex_sub",),
    "review_architecture": ("codex_sub",),
    "review_large_context": ("codex_sub",),
    "redteam": ("codex_sub",),
}

INCLUDED_ENGINEERING = ("cursor_sub", "codex_sub", "ollama_local")

SESSION_LIMIT_PATTERNS = (
    re.compile(r"session\s+limit", re.I),
    re.compile(r"rate\s+limit", re.I),
    re.compile(r"5[- ]?hour", re.I),
    re.compile(r"usage\s+limit\s+reached", re.I),
)
WEEKLY_LIMIT_PATTERNS = (
    re.compile(r"weekly\s+limit", re.I),
    re.compile(r"week(?:ly)?\s+quota", re.I),
    re.compile(r"100%\s+weekly", re.I),
)
AUTH_FAILURE_PATTERNS = (
    re.compile(r"auth(?:entication)?\s+fail", re.I),
    re.compile(r"unauthorized", re.I),
    re.compile(r"invalid\s+(api\s+)?key", re.I),
    re.compile(r"login\s+required", re.I),
)
TIMEOUT_PATTERNS = (
    re.compile(r"timeout", re.I),
    re.compile(r"timed\s+out", re.I),
)
OUTAGE_PATTERNS = (
    re.compile(r"service\s+unavailable", re.I),
    re.compile(r"provider\s+outage", re.I),
    re.compile(r"503", re.I),
)


def _failover_dir() -> Path:
    return paths.STATE_ROOT / "failover"


def _paths() -> dict[str, Path]:
    root = _failover_dir()
    return {
        "dir": root,
        "registry": root / "registry.json",
        "availability": root / "availability.json",
        "config": root / "config.json",
        "audit": root / "audit.jsonl",
        "spend_policy": root / "spend-policy.json",
        "flags": root / "flags.json",
    }


def rebind_failover_paths() -> None:
    """No-op placeholder for symmetry with other path rebind hooks."""
    return


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_audit_fsync(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _billing_class(worker_id: str) -> str:
    meta = worker_registry.WORKERS.get(worker_id) or {}
    bc = meta.get("billing_class") or "not_commissioned"
    if bc == "subscription":
        return "included_subscription"
    if bc == worker_registry.METERED:
        return "metered"
    if bc in ("free", "local"):
        return "included_subscription"
    return "metered" if worker_registry.is_metered(worker_id) else "included_subscription"


def _default_commissioning(worker_id: str) -> str:
    meta = worker_registry.WORKERS.get(worker_id) or {}
    if meta.get("human_commissioned"):
        return "commissioned"
    if meta.get("gated"):
        return "not_commissioned"
    if meta.get("adapter"):
        return "commissioned" if worker_id in ("gemini_free", "ollama_local") else "not_commissioned"
    return "not_commissioned"


def _default_capabilities(worker_id: str) -> list[str]:
    caps: list[str] = []
    if worker_id == "cursor_sub":
        caps = ["build", "debug", "test"]
    elif worker_id == "codex_sub":
        caps = [
            "build",
            "debug",
            "test",
            "review_reasoning",
            "review_accounting",
            "review_ux",
            "review_security",
            "review_architecture",
            "review_large_context",
        ]
    elif worker_id == "claude_pro_sub":
        caps = [
            "review_reasoning",
            "review_accounting",
            "review_ux",
            "review_security",
            "review_architecture",
            "review_large_context",
            "redteam",
        ]
    elif worker_id == "grok_bot_sub":
        caps = []
    elif worker_id == "ollama_local":
        caps = ["build", "debug", "test"]
    return caps


def _default_benchmark_eligibility(worker_id: str) -> dict[str, float]:
    eligible: dict[str, float] = {}
    for cap in _default_capabilities(worker_id):
        eligible[cap] = 0.8 if worker_id in ("cursor_sub", "codex_sub", "claude_pro_sub") else 0.5
    return eligible


def default_registry() -> dict[str, Any]:
    workers: dict[str, Any] = {}
    for wid in worker_registry.WORKERS:
        workers[wid] = {
            "worker_id": wid,
            "capabilities": _default_capabilities(wid),
            "commissioning_state": _default_commissioning(wid),
            "benchmark_eligibility": _default_benchmark_eligibility(wid),
            "billing_class": _billing_class(wid),
            "context_limit": 200_000 if wid in ("claude_pro_sub", "codex_sub", "cursor_sub") else 32_000,
        }
    return {"workers": workers, "version": 1}


def load_registry() -> dict[str, Any]:
    p = _paths()["registry"]
    data = _read_json(p, None)
    if not data or not isinstance(data.get("workers"), dict):
        data = default_registry()
        save_registry(data)
    return data


def save_registry(data: dict[str, Any]) -> None:
    _write_json(_paths()["registry"], data)


def load_availability() -> dict[str, Any]:
    p = _paths()["availability"]
    data = _read_json(p, {"workers": {}})
    if "workers" not in data:
        data["workers"] = {}
    return data


def save_availability(data: dict[str, Any]) -> None:
    _write_json(_paths()["availability"], data)


def load_failover_config() -> dict[str, Any]:
    p = _paths()["config"]
    cfg = _read_json(p, {})
    cfg.setdefault("wait_window_minutes", 90)
    cfg.setdefault("benchmark_delta_threshold", 0.15)
    cfg.setdefault("operational_blocker", False)
    cfg.setdefault("min_benchmark_score", 0.5)
    return cfg


def save_failover_config(cfg: dict[str, Any]) -> None:
    _write_json(_paths()["config"], cfg)


def load_spend_policy() -> dict[str, Any]:
    return _read_json(_paths()["spend_policy"], {"owner_approved": False, "records": []})


def save_spend_policy(data: dict[str, Any]) -> None:
    _write_json(_paths()["spend_policy"], data)


def load_flags() -> dict[str, Any]:
    return _read_json(_paths()["flags"], {"peaches_chat_degraded": False})


def save_flags(flags: dict[str, Any]) -> None:
    _write_json(_paths()["flags"], flags)


def set_peaches_chat_degraded(degraded: bool) -> None:
    flags = load_flags()
    flags["peaches_chat_degraded"] = degraded
    save_flags(flags)


def peaches_chat_degraded() -> bool:
    return bool(load_flags().get("peaches_chat_degraded"))


def _parse_now(now: datetime | str | None) -> datetime:
    if isinstance(now, str):
        return datetime.fromisoformat(now)
    return now or datetime.now(TZ)


def _now_iso(now: datetime | str | None = None) -> str:
    return _parse_now(now).isoformat(timespec="seconds")


def capability_for_item(item: dict[str, Any]) -> str:
    spec = item.get("spec") or {}
    if spec.get("capability") in CAPABILITIES:
        return str(spec["capability"])
    if spec.get("review_type"):
        rt = str(spec["review_type"])
        mapped = f"review_{rt}" if not rt.startswith("review_") else rt
        if mapped in CAPABILITIES:
            return mapped
    kind = str(item.get("kind") or "")
    return KIND_DEFAULT_CAPABILITY.get(kind, "build")


def preferred_workers(capability: str, orch_config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = orch_config or {}
    if capability.startswith("review_") or capability == "redteam":
        if cfg.get("claude_paused"):
            return tuple(w for w in PREFERRED_BY_CAPABILITY.get(capability, ()) if w != "claude_pro_sub")
    return PREFERRED_BY_CAPABILITY.get(capability, ())


def _worker_record(registry: dict[str, Any], worker_id: str) -> dict[str, Any] | None:
    return (registry.get("workers") or {}).get(worker_id)


def _availability_record(avail: dict[str, Any], worker_id: str) -> dict[str, Any]:
    rec = (avail.get("workers") or {}).get(worker_id) or {}
    return {
        "state": rec.get("state", "available"),
        "reset_time": rec.get("reset_time"),
        "evidence": list(rec.get("evidence") or []),
    }


def _capacity_unavailable(worker_id: str, capacity: dict[str, Any]) -> tuple[bool, str | None]:
    workers = capacity.get("workers") or {}
    rec = workers.get(worker_id) or {}
    state = rec.get("state", "NORMAL")
    if state in ("RESERVE", "EXHAUSTED"):
        return True, f"capacity_{state.lower()}"
    if worker_id == GROK_WORKER_ID:
        if state in ("CONSERVE", "RESERVE", "EXHAUSTED") or not rec.get("grok_available", True):
            return True, "grok_unavailable"
    return False, None


def metered_allowed(worker_id: str, spend_policy: dict[str, Any] | None = None) -> bool:
    if not worker_registry.is_metered(worker_id) and _billing_class(worker_id) != "metered":
        return True
    sp = spend_policy or load_spend_policy()
    if not sp.get("owner_approved"):
        return False
    pl = load_policy()
    return metered_permitted(pl)


def _benchmark_score(worker: dict[str, Any], capability: str) -> float:
    elig = worker.get("benchmark_eligibility") or {}
    return float(elig.get(capability, 0.0))


def _builder_lineage(item: dict[str, Any], items: dict[str, dict[str, Any]]) -> set[str]:
    builders: set[str] = set()
    spec = item.get("spec") or {}
    parent_id = spec.get("parent")
    if parent_id and parent_id in items:
        parent = items[parent_id]
        lw = parent.get("last_worker")
        if lw:
            builders.add(str(lw))
        for dep in parent.get("depends_on") or []:
            dep_item = items.get(dep)
            if dep_item and dep_item.get("last_worker"):
                builders.add(str(dep_item["last_worker"]))
    return builders


def _is_eligible(
    worker_id: str,
    capability: str,
    *,
    registry: dict[str, Any],
    availability: dict[str, Any],
    capacity: dict[str, Any],
    spend_policy: dict[str, Any],
    item: dict[str, Any],
    items: dict[str, dict[str, Any]],
    min_score: float,
) -> tuple[bool, list[str]]:
    notes: list[str] = []
    worker = _worker_record(registry, worker_id)
    if not worker:
        return False, ["unknown_worker"]
    if capability not in (worker.get("capabilities") or []):
        return False, ["missing_capability"]
    if worker.get("commissioning_state") != "commissioned":
        return False, [f"commissioning:{worker.get('commissioning_state')}"]
    score = _benchmark_score(worker, capability)
    if score < min_score:
        return False, [f"benchmark:{score:.3f}<{min_score}"]
    av = _availability_record(availability, worker_id)
    if av["state"] != "available":
        return False, [f"availability:{av['state']}"]
    cap_unavail, cap_reason = _capacity_unavailable(worker_id, capacity)
    if cap_unavail:
        return False, [cap_reason or "capacity_unavailable"]
    bc = worker.get("billing_class") or _billing_class(worker_id)
    if bc == "metered" and not metered_allowed(worker_id, spend_policy):
        return False, ["metered_no_approval"]
    if capability.startswith("review_") or capability == "redteam":
        builders = _builder_lineage(item, items)
        if worker_id in builders:
            return False, ["independence_violation"]
    ctx_size = int(item.get("context_size") or (item.get("spec") or {}).get("context_size") or 0)
    limit = int(worker.get("context_limit") or 0)
    if ctx_size and limit and ctx_size > limit:
        return False, [f"context:{ctx_size}>{limit}"]
    notes.append(f"score:{score:.3f}")
    return True, notes


def _rank_eligible(
    candidates: tuple[str, ...],
    capability: str,
    *,
    registry: dict[str, Any],
    availability: dict[str, Any],
    capacity: dict[str, Any],
    spend_policy: dict[str, Any],
    item: dict[str, Any],
    items: dict[str, dict[str, Any]],
    min_score: float,
) -> list[tuple[str, float, list[str]]]:
    ranked: list[tuple[str, float, list[str]]] = []
    for wid in candidates:
        ok, notes = _is_eligible(
            wid,
            capability,
            registry=registry,
            availability=availability,
            capacity=capacity,
            spend_policy=spend_policy,
            item=item,
            items=items,
            min_score=min_score,
        )
        if ok:
            worker = _worker_record(registry, wid) or {}
            ranked.append((wid, _benchmark_score(worker, capability), notes))
    ranked.sort(key=lambda x: (-x[1], x[0]))
    return ranked


def _unavailable_reason(worker_id: str, availability: dict[str, Any], capacity: dict[str, Any]) -> str:
    av = _availability_record(availability, worker_id)
    if av["state"] != "available":
        return av["state"]
    cap_unavail, cap_reason = _capacity_unavailable(worker_id, capacity)
    if cap_unavail:
        return cap_reason or "capacity_unavailable"
    return "unavailable_confirmed"


def _reset_time(worker_id: str, availability: dict[str, Any]) -> str | None:
    return _availability_record(availability, worker_id).get("reset_time")


def _within_wait_window(reset_time: str | None, now: datetime, window_min: int) -> bool:
    if not reset_time:
        return False
    try:
        rt = datetime.fromisoformat(reset_time)
    except ValueError:
        return False
    if rt.tzinfo is None:
        rt = rt.replace(tzinfo=TZ)
    return now < rt <= now + timedelta(minutes=window_min)


def decide_routing(
    item: dict[str, Any],
    *,
    capacity: dict[str, Any],
    orch_config: dict[str, Any] | None = None,
    items: dict[str, dict[str, Any]] | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Return routing decision: worker_id | None, action WAIT|FAILOVER|DISPATCH|WAITING_FOR_CAPACITY."""
    registry = load_registry()
    availability = load_availability()
    fo_cfg = load_failover_config()
    spend_policy = load_spend_policy()
    all_items = items or {}
    capability = capability_for_item(item)
    min_score = float(fo_cfg.get("min_benchmark_score", 0.5))
    preferred = preferred_workers(capability, orch_config)
    now_dt = _parse_now(now)

    preferred_worker = preferred[0] if preferred else None
    pref_ok, pref_notes = (False, ["no_preferred"])
    if preferred_worker:
        pref_ok, pref_notes = _is_eligible(
            preferred_worker,
            capability,
            registry=registry,
            availability=availability,
            capacity=capacity,
            spend_policy=spend_policy,
            item=item,
            items=all_items,
            min_score=min_score,
        )

    if pref_ok:
        audit = _audit_record(
            item,
            preferred_worker=preferred_worker,
            unavailable_reason=None,
            reset_time=None,
            replacement_worker=preferred_worker,
            why_selected=f"preferred_eligible;{';'.join(pref_notes)}",
            wait_or_failover="DISPATCH",
            evidence=pref_notes,
            billing_class=_billing_class(preferred_worker),
            now=now_dt,
        )
        _record_decision(audit)
        return {
            "action": "DISPATCH",
            "worker_id": preferred_worker,
            "capability": capability,
            "audit": audit,
        }

    # Preferred unavailable — evaluate failover candidates
    fallback_order: list[str] = []
    for w in PREFERRED_BY_CAPABILITY.get(capability, ()):
        if w != preferred_worker and w not in fallback_order:
            fallback_order.append(w)
    for w in FALLBACK_BY_CAPABILITY.get(capability, ()):
        if w not in fallback_order:
            fallback_order.append(w)
    for w in INCLUDED_ENGINEERING:
        if w not in fallback_order:
            fallback_order.append(w)
    if spend_policy.get("owner_approved"):
        for wid, worker in sorted((registry.get("workers") or {}).items()):
            if (worker.get("billing_class") == "metered" or worker_registry.is_metered(wid)) and wid not in fallback_order:
                fallback_order.append(wid)

    ranked = _rank_eligible(
        tuple(fallback_order),
        capability,
        registry=registry,
        availability=availability,
        capacity=capacity,
        spend_policy=spend_policy,
        item=item,
        items=all_items,
        min_score=min_score,
    )

    pref_score = 0.0
    if preferred_worker:
        pw = _worker_record(registry, preferred_worker) or {}
        pref_score = _benchmark_score(pw, capability)

    reset_time = _reset_time(preferred_worker, availability) if preferred_worker else None
    urgent = bool(item.get("urgent") or (item.get("spec") or {}).get("urgent"))
    best = ranked[0] if ranked else None
    wait_window = int(fo_cfg.get("wait_window_minutes", 90))
    operational_blocker = bool(fo_cfg.get("operational_blocker"))
    delta_threshold = float(fo_cfg.get("benchmark_delta_threshold", 0.15))

    if best:
        replacement, score, notes = best
        materially_weaker = (pref_score - score) > delta_threshold
        if (
            preferred_worker
            and not pref_ok
            and _within_wait_window(reset_time, now_dt, wait_window)
            and not urgent
            and materially_weaker
            and not operational_blocker
        ):
            audit = _audit_record(
                item,
                preferred_worker=preferred_worker,
                unavailable_reason=_unavailable_reason(preferred_worker, availability, capacity),
                reset_time=reset_time,
                replacement_worker=None,
                why_selected=f"wait_for_preferred_reset;replacement_weaker:{score:.3f}",
                wait_or_failover="WAIT",
                evidence=notes + pref_notes,
                billing_class=_billing_class(preferred_worker),
                now=now_dt,
            )
            _record_decision(audit)
            return {"action": "WAIT", "worker_id": None, "capability": capability, "audit": audit}
        action = "FAILOVER" if preferred_worker and replacement != preferred_worker else "DISPATCH"
        audit = _audit_record(
            item,
            preferred_worker=preferred_worker,
            unavailable_reason=_unavailable_reason(preferred_worker, availability, capacity) if preferred_worker else None,
            reset_time=reset_time,
            replacement_worker=replacement,
            why_selected=f"capability_match;score:{score:.3f};{';'.join(notes)}",
            wait_or_failover=action,
            evidence=notes + pref_notes,
            billing_class=_billing_class(replacement),
            now=now_dt,
        )
        _record_decision(audit)
        return {
            "action": action,
            "worker_id": replacement,
            "capability": capability,
            "audit": audit,
        }

    audit = _audit_record(
        item,
        preferred_worker=preferred_worker,
        unavailable_reason=_unavailable_reason(preferred_worker, availability, capacity) if preferred_worker else "no_workers",
        reset_time=reset_time,
        replacement_worker=None,
        why_selected="no_included_eligible_worker",
        wait_or_failover="WAITING_FOR_CAPACITY",
        evidence=pref_notes,
        billing_class=_billing_class(preferred_worker) if preferred_worker else "included_subscription",
        now=now_dt,
    )
    _record_decision(audit)
    return {
        "action": "WAITING_FOR_CAPACITY",
        "worker_id": None,
        "capability": capability,
        "audit": audit,
        "notify_owner": urgent,
    }


def _audit_record(
    item: dict[str, Any],
    *,
    preferred_worker: str | None,
    unavailable_reason: str | None,
    reset_time: str | None,
    replacement_worker: str | None,
    why_selected: str,
    wait_or_failover: str,
    evidence: list[str],
    billing_class: str,
    now: datetime,
) -> dict[str, Any]:
    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "work_item_id": item.get("id"),
        "PREFERRED_WORKER": preferred_worker,
        "UNAVAILABLE_REASON": unavailable_reason,
        "RESET_TIME": reset_time,
        "REPLACEMENT_WORKER": replacement_worker,
        "WHY_SELECTED": why_selected,
        "WAIT_OR_FAILOVER": wait_or_failover,
        "EVIDENCE": evidence,
        "BILLING_CLASS": billing_class,
    }


def _record_decision(rec: dict[str, Any]) -> None:
    _append_audit_fsync(_paths()["audit"], rec)


def record_availability_from_dispatch(
    worker_id: str,
    *,
    exit_code: int | None,
    stderr: str = "",
    stdout: str = "",
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Derive availability state from worker exit codes/stderr patterns."""
    text = f"{stderr}\n{stdout}"
    state = "available"
    evidence: list[str] = []
    reset_time: str | None = None
    now_dt = _parse_now(now)

    if exit_code is None or any(p.search(text) for p in TIMEOUT_PATTERNS):
        state = "timeout"
        evidence.append(f"exit_code:{exit_code}")
        reset_time = (now_dt + timedelta(minutes=30)).isoformat(timespec="seconds")
    elif any(p.search(text) for p in AUTH_FAILURE_PATTERNS):
        state = "auth_failure"
        evidence.append("stderr:auth_pattern")
    elif any(p.search(text) for p in WEEKLY_LIMIT_PATTERNS):
        state = "weekly_limit"
        evidence.append("stderr:weekly_limit_pattern")
        reset_time = (now_dt + timedelta(hours=24)).isoformat(timespec="seconds")
    elif any(p.search(text) for p in SESSION_LIMIT_PATTERNS):
        state = "session_limit"
        evidence.append("stderr:session_limit_pattern")
        reset_time = (now_dt + timedelta(minutes=60)).isoformat(timespec="seconds")
    elif any(p.search(text) for p in OUTAGE_PATTERNS):
        state = "provider_outage"
        evidence.append("stderr:outage_pattern")
    elif exit_code != 0:
        state = "unavailable_confirmed"
        evidence.append(f"exit_code:{exit_code}")

    if state == "available":
        return {"worker_id": worker_id, "state": state, "updated": False}

    avail = load_availability()
    workers = avail.setdefault("workers", {})
    workers[worker_id] = {
        "state": state,
        "reset_time": reset_time,
        "evidence": evidence,
        "updated_at": _now_iso(now_dt),
    }
    save_availability(avail)

    if worker_id == GROK_WORKER_ID:
        set_peaches_chat_degraded(True)

    return {"worker_id": worker_id, "state": state, "reset_time": reset_time, "evidence": evidence, "updated": True}


def set_worker_availability(
    worker_id: str,
    state: str,
    *,
    reset_time: str | None = None,
    evidence: list[str] | None = None,
    now: datetime | str | None = None,
) -> None:
    if state not in AVAILABILITY_STATES:
        raise ValueError(f"invalid availability state: {state}")
    avail = load_availability()
    avail.setdefault("workers", {})[worker_id] = {
        "state": state,
        "reset_time": reset_time,
        "evidence": list(evidence or []),
        "updated_at": _now_iso(now),
    }
    save_availability(avail)
    if worker_id == GROK_WORKER_ID and state != "available":
        set_peaches_chat_degraded(True)
    elif worker_id == GROK_WORKER_ID and state == "available":
        set_peaches_chat_degraded(False)


def update_grok_capacity_flag(capacity: dict[str, Any]) -> None:
    workers = capacity.get("workers") or {}
    grok = workers.get(GROK_WORKER_ID) or {}
    grok_state = grok.get("state", "NORMAL")
    unavailable = grok_state in ("CONSERVE", "RESERVE", "EXHAUSTED") or not grok.get("grok_available", True)
    set_peaches_chat_degraded(unavailable)


def select_worker(
    kind: str,
    config: dict[str, Any],
    capacity: dict[str, Any],
    item: dict[str, Any] | None = None,
    items: dict[str, dict[str, Any]] | None = None,
    now: datetime | str | None = None,
) -> str | None:
    """Orchestrator-facing selector."""
    update_grok_capacity_flag(capacity)
    stub = item or {"id": f"route-{kind}", "kind": kind, "spec": {}}
    decision = decide_routing(stub, capacity=capacity, orch_config=config, items=items, now=now)
    if decision["action"] in ("DISPATCH", "FAILOVER"):
        return decision.get("worker_id")
    return None


# ---------------------------------------------------------------------------
# Proof harness (CLI)
# ---------------------------------------------------------------------------

def _proof_state_setup(state_root: str) -> None:
    os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = state_root
    paths.rebind_state_paths()
    from . import orchestrator as orch

    orch.rebind_orchestrator_paths()
    _failover_dir().mkdir(parents=True, exist_ok=True)


def _proof_registry(
    *,
    claude_state: str = "available",
    cursor_state: str = "available",
    codex_state: str = "available",
    grok_state: str = "available",
    claude_reset: str | None = None,
    claude_score: float = 0.95,
    codex_review_score: float = 0.85,
    codex_build_score: float = 0.80,
    cursor_score: float = 0.90,
    metered_present: bool = True,
    spend_approved: bool = False,
) -> None:
    reg = default_registry()
    workers = reg["workers"]
    workers["claude_pro_sub"]["commissioning_state"] = "commissioned"
    workers["codex_sub"]["commissioning_state"] = "commissioned"
    workers["cursor_sub"]["commissioning_state"] = "commissioned"
    if "ollama_local" in workers:
        workers["ollama_local"]["commissioning_state"] = "not_commissioned"
    workers["claude_pro_sub"]["benchmark_eligibility"]["review_reasoning"] = claude_score
    workers["codex_sub"]["benchmark_eligibility"]["review_reasoning"] = codex_review_score
    workers["codex_sub"]["benchmark_eligibility"]["build"] = codex_build_score
    workers["cursor_sub"]["benchmark_eligibility"]["build"] = cursor_score
    if metered_present:
        workers["anthropic_api"] = {
            "worker_id": "anthropic_api",
            "capabilities": list(CAPABILITIES),
            "commissioning_state": "commissioned",
            "benchmark_eligibility": {c: 1.0 for c in CAPABILITIES},
            "billing_class": "metered",
            "context_limit": 200_000,
        }
        workers["openai_api"] = {
            "worker_id": "openai_api",
            "capabilities": list(CAPABILITIES),
            "commissioning_state": "commissioned",
            "benchmark_eligibility": {c: 1.0 for c in CAPABILITIES},
            "billing_class": "metered",
            "context_limit": 200_000,
        }
    save_registry(reg)
    avail = {"workers": {}}
    for wid, st, rt in (
        ("claude_pro_sub", claude_state, claude_reset),
        ("cursor_sub", cursor_state, None),
        ("codex_sub", codex_state, None),
        (GROK_WORKER_ID, grok_state, None),
    ):
        if st != "available":
            avail["workers"][wid] = {"state": st, "reset_time": rt, "evidence": [f"proof:{st}"]}
    save_availability(avail)
    save_spend_policy({"owner_approved": spend_approved, "records": []})
    save_failover_config(
        {
            "wait_window_minutes": 90,
            "benchmark_delta_threshold": 0.15,
            "operational_blocker": False,
            "min_benchmark_score": 0.5,
        }
    )
    save_flags({"peaches_chat_degraded": False})


def _proof_capacity(
    *,
    claude_cap: str = "NORMAL",
    cursor_cap: str = "NORMAL",
    codex_cap: str = "NORMAL",
    grok_cap: str = "NORMAL",
    grok_available: bool = True,
) -> dict[str, Any]:
    return {
        "workers": {
            "claude_pro_sub": {"state": claude_cap},
            "cursor_sub": {"state": cursor_cap},
            "codex_sub": {"state": codex_cap},
            GROK_WORKER_ID: {"state": grok_cap, "grok_available": grok_available},
        }
    }


def run_proof_scenario(name: str, state_root: str) -> dict[str, Any]:
    import shutil

    root = Path(state_root) / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    _proof_state_setup(str(root))

    cap = _proof_capacity()
    item_review = {
        "id": f"proof-{name}-review",
        "kind": "review",
        "spec": {"parent": "proof-build", "review_type": "reasoning"},
    }
    item_build = {"id": f"proof-{name}-build", "kind": "build", "spec": {"prompt": "x"}}
    items = {
        "proof-build": {"id": "proof-build", "kind": "build", "last_worker": "cursor_sub", "depends_on": []},
    }

    if name == "claude_limit_codex_inherits_review":
        _proof_registry(claude_state="session_limit", claude_reset="2026-10-06T13:00:00+08:00")
        d = decide_routing(item_review, capacity=cap, items=items, now="2026-10-06T12:00:00+08:00")
        ok = d["action"] == "FAILOVER" and d["worker_id"] == "codex_sub"
        return {"scenario": name, "pass": ok, "worker": d.get("worker_id"), "action": d["action"]}

    if name == "cursor_limit_engineering_replacement":
        _proof_registry(cursor_state="weekly_limit", codex_build_score=0.82)
        cap = _proof_capacity(cursor_cap="EXHAUSTED")
        d = decide_routing(item_build, capacity=cap, now="2026-10-06T12:00:00+08:00")
        ok = d["action"] == "FAILOVER" and d["worker_id"] == "codex_sub"
        return {"scenario": name, "pass": ok, "worker": d.get("worker_id"), "action": d["action"]}

    if name == "grok_exhaustion_wolf_continues":
        _proof_registry(grok_state="weekly_limit")
        cap = _proof_capacity(grok_cap="EXHAUSTED", grok_available=False)
        update_grok_capacity_flag(cap)
        d_build = decide_routing(item_build, capacity=cap, now="2026-10-06T12:00:00+08:00")
        d_review = decide_routing(item_review, capacity=cap, items=items, now="2026-10-06T12:00:00+08:00")
        ok = (
            d_build.get("worker_id") == "cursor_sub"
            and d_review.get("worker_id") in ("claude_pro_sub", "codex_sub")
            and peaches_chat_degraded()
        )
        return {
            "scenario": name,
            "pass": ok,
            "build_worker": d_build.get("worker_id"),
            "review_worker": d_review.get("worker_id"),
            "peaches_chat_degraded": peaches_chat_degraded(),
        }

    if name == "claude_codex_unavailable_no_paid_fallback":
        _proof_registry(
            claude_state="weekly_limit",
            codex_state="session_limit",
            metered_present=True,
            spend_approved=False,
        )
        cap = _proof_capacity(claude_cap="EXHAUSTED", codex_cap="EXHAUSTED")
        d = decide_routing(item_review, capacity=cap, items=items, now="2026-10-06T12:00:00+08:00")
        ok = d["action"] == "WAITING_FOR_CAPACITY" and d.get("worker_id") is None
        audit_path = _paths()["audit"]
        metered_selected = False
        if audit_path.exists():
            for line in audit_path.read_text().splitlines():
                rec = json.loads(line)
                if rec.get("REPLACEMENT_WORKER") in ("anthropic_api", "openai_api"):
                    metered_selected = True
        ok = ok and not metered_selected
        return {"scenario": name, "pass": ok, "action": d["action"], "metered_selected": metered_selected}

    if name == "all_unavailable_waiting_for_capacity":
        _proof_registry(claude_state="weekly_limit", cursor_state="weekly_limit", codex_state="weekly_limit")
        cap = _proof_capacity(claude_cap="EXHAUSTED", cursor_cap="EXHAUSTED", codex_cap="EXHAUSTED")
        d = decide_routing(item_build, capacity=cap, now="2026-10-06T12:00:00+08:00")
        ok = d["action"] == "WAITING_FOR_CAPACITY"
        return {"scenario": name, "pass": ok, "action": d["action"]}

    if name == "restart_policy_persists":
        _proof_registry(claude_state="session_limit", claude_reset="2026-10-06T13:30:00+08:00")
        set_worker_availability("claude_pro_sub", "session_limit", reset_time="2026-10-06T13:30:00+08:00", evidence=["persist"])
        reg_before = load_registry()
        avail_before = load_availability()
        # Simulate restart by rebind only
        _proof_state_setup(str(root))
        reg_after = load_registry()
        avail_after = load_availability()
        ok = reg_before == reg_after and avail_before == avail_after
        return {"scenario": name, "pass": ok}

    return {"scenario": name, "pass": False, "error": "unknown_scenario"}


PROOF_SCENARIOS = (
    "claude_limit_codex_inherits_review",
    "cursor_limit_engineering_replacement",
    "grok_exhaustion_wolf_continues",
    "claude_codex_unavailable_no_paid_fallback",
    "all_unavailable_waiting_for_capacity",
    "restart_policy_persists",
)


def run_proof(state_root: str) -> dict[str, Any]:
    results = [run_proof_scenario(name, state_root) for name in PROOF_SCENARIOS]
    out = {
        "scenarios": {r["scenario"]: ("PASS" if r.get("pass") else "FAIL") for r in results},
        "details": results,
    }
    proof_path = Path(state_root) / "failover-proof.json"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
