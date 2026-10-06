"""Routing imbalance alarm — auto-tighten Grok penalty when delegatable share is too high."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .allocation import LedgerView, load_tightening, save_tightening
from .governance import PolicyLoad, append_audit_event, grok_worker_id
from .paths import ensure_dirs

TZ = ZoneInfo("Asia/Makassar")


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


def check_imbalance(
    policy_load: PolicyLoad,
    ledger_view: LedgerView | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Check delegatable DISPATCH decisions; raise penalty if Grok share exceeds threshold."""
    if policy_load.mode != "ENFORCED" or not policy_load.policy:
        return {"triggered": False, "reason": "policy_not_enforced"}

    policy = policy_load.policy
    imb = policy.get("imbalance") or {}
    window_h = float(imb.get("window_hours", 24))
    window_n = int(imb.get("window_decisions", 50))
    min_samples = int(imb.get("min_samples", 5))
    max_share = float(imb.get("max_grok_share_delegatable", 0.4))
    step = float(imb.get("penalty_step", 0.15))
    max_pen = float(imb.get("penalty_max", 1.0))

    if isinstance(now, str):
        now_dt = _parse_dt(now) or datetime.now(TZ)
    elif now is None:
        now_dt = datetime.now(TZ)
    else:
        now_dt = now

    grok = grok_worker_id(policy)
    lv = ledger_view or LedgerView()
    cutoff = now_dt - timedelta(hours=window_h)

    relevant: list[dict[str, Any]] = []
    for rec in reversed(lv.decisions(now=now_dt)):
        if rec.get("decision") != "DISPATCH":
            continue
        if rec.get("protected"):
            continue
        if not rec.get("delegatable"):
            continue
        if not rec.get("alternatives_available"):
            continue
        ts = _parse_dt(rec.get("recorded_at"))
        if ts is None or ts > now_dt or ts < cutoff:
            continue
        relevant.append(rec)
        if len(relevant) >= window_n:
            break

    if len(relevant) < min_samples:
        return {"triggered": False, "reason": "insufficient_samples", "samples": len(relevant)}

    grok_count = sum(1 for r in relevant if r.get("selected_worker") == grok)
    share = grok_count / len(relevant)

    if share <= max_share:
        return {"triggered": False, "grok_share": share, "samples": len(relevant)}

    tightening = load_tightening(policy)
    current = float(tightening.get("grok_routing_penalty", 0.0))
    new_penalty = min(current + step, max_pen)
    tightening["grok_routing_penalty"] = new_penalty
    tightening["last_imbalance_at"] = now_dt.isoformat(timespec="seconds")
    tightening["last_grok_share"] = round(share, 4)
    save_tightening(tightening, policy)

    append_audit_event(
        "ROUTING_IMBALANCE",
        {
            "grok_share": round(share, 4),
            "samples": len(relevant),
            "threshold": max_share,
            "penalty_before": current,
            "penalty_after": new_penalty,
        },
    )

    return {
        "triggered": True,
        "grok_share": share,
        "samples": len(relevant),
        "penalty_before": current,
        "penalty_after": new_penalty,
    }
