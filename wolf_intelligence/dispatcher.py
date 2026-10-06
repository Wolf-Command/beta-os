"""Single dispatcher — SHADOW MODE.

Recommend routing; safe isolated test jobs only; no Production mutation;
no duplicate actual expensive dispatch; never kill workers.
"""
from __future__ import annotations

from typing import Any

from . import events, ledger, work_items
from .adapters import get_adapter
from .router import recommend

SHADOW_MODE = True
PRODUCTION_TOUCHED = False  # invariant


def dispatch(work_item_id: str, *, force_isolated: bool = True) -> dict[str, Any]:
    item = work_items.get(work_item_id)
    if not item:
        raise KeyError(work_item_id)

    # Route + recommend
    if item["state"] == "QUEUED":
        work_items.transition(work_item_id, "ROUTING", reason="shadow dispatcher")
    item = work_items.get(work_item_id)

    scored = recommend(item)
    work_items.update_fields(
        work_item_id,
        recommendation=scored["recommendation"],
        scores=scored["scores"],
    )
    work_items.transition(
        work_item_id,
        "RECOMMENDED",
        reason="router scored",
        extra={"recommendation": scored["recommendation"], "scores": scored["scores"]},
    )

    rec = scored["recommendation"]
    worker_id = rec.get("recommended_worker")
    adapter = get_adapter(worker_id) if worker_id else None

    # Shadow gate: only isolated_safe jobs may "submit" and even then adapters noop expensive
    isolated = bool(item.get("isolated_safe")) or force_isolated
    allow_expensive = bool(item.get("allow_expensive"))
    if allow_expensive and SHADOW_MODE:
        events.emit(
            "dispatch.shadow_skipped_expensive",
            {"reason": "SHADOW_MODE blocks expensive execute", "worker": worker_id},
            work_item_id=work_item_id,
        )
        return {
            "ok": True,
            "mode": "SHADOW",
            "action": "RECOMMEND_ONLY",
            "recommendation": rec,
            "production_touched": False,
            "duplicate_expensive_dispatch": False,
        }

    if not adapter:
        work_items.transition(work_item_id, "EXCEPTION", reason="no adapter for recommendation")
        return {"ok": False, "mode": "SHADOW", "error": "no adapter", "recommendation": rec}

    if not isolated:
        events.emit(
            "dispatch.shadow_skipped_expensive",
            {"reason": "not isolated_safe"},
            work_item_id=work_item_id,
        )
        work_items.transition(work_item_id, "NEEDS_YOU", reason="non-isolated job needs Owner decision")
        return {"ok": True, "mode": "SHADOW", "action": "NEEDS_YOU", "recommendation": rec}

    work_items.transition(work_item_id, "DISPATCHED_SHADOW", reason="shadow isolated submit")
    job = {
        "shadow_isolated": True,
        "prompt": (item.get("payload") or {}).get("prompt") or item.get("title"),
        "work_item_id": work_item_id,
    }
    events.emit("dispatch.shadow_submitted", {"worker": worker_id}, work_item_id=work_item_id)
    work_items.transition(work_item_id, "RUNNING", reason="shadow running")
    result = adapter.submit(job)

    if result.ok:
        events.emit(
            "dispatch.shadow_completed",
            {"worker": worker_id, "status": result.status, "message": result.message},
            work_item_id=work_item_id,
        )
        # Record zero-cost shadow usage against preferred pool if known
        pool = rec.get("recommended_model_id") and next(
            (s.get("pool_id") for s in scored["scores"] if s["model_id"] == rec["recommended_model_id"]),
            None,
        )
        if pool:
            try:
                ledger.record_usage(
                    pool_id=pool,
                    amount_usd=0.0,
                    work_item_id=work_item_id,
                    worker_id=worker_id,
                    model_id=rec.get("recommended_model_id"),
                    note="shadow isolated zero-cost",
                    shadow=True,
                )
            except KeyError:
                pass
        work_items.transition(
            work_item_id,
            "READY_TO_TEST",
            reason="shadow submit ok",
            extra={"dispatch": {"worker": worker_id, "result": result.__dict__}, "result": result.data},
        )
    else:
        events.emit(
            "dispatch.shadow_failed",
            {"worker": worker_id, "status": result.status, "message": result.message},
            work_item_id=work_item_id,
        )
        work_items.transition(work_item_id, "EXCEPTION", reason=result.message)

    return {
        "ok": result.ok,
        "mode": "SHADOW",
        "action": "ISOLATED_SHADOW_SUBMIT",
        "recommendation": rec,
        "adapter_status": result.status,
        "adapter_message": result.message,
        "production_touched": PRODUCTION_TOUCHED,
        "duplicate_expensive_dispatch": False,
        "workers_killed": False,
    }

# REAL worker path (2026-10-06): dispatch_real records to the REAL evidence store, never live state.
from .real_dispatch import collect_pull, dispatch_real  # noqa: E402,F401
