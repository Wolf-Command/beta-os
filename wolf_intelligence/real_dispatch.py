"""WI dispatcher for REAL worker calls (commissioning + benchmark).

Rules enforced here, not by convention:
* Unknown worker → refused.
* Metered worker (billing_class=metered_api) → GATED unless an unexpired Owner
  approval record exists. Never selected by routing; never a fallback.
* No fallback at all: if the chosen worker fails, the failure is recorded and
  returned. The caller (or the Owner) decides what happens next.
* WOLF_INTELLIGENCE_LIVE_SUBMIT must be on (adapters enforce it too).
* Every call is appended to the REAL evidence store (records/dispatch.jsonl) with
  full raw output saved as an artifact. Live Beta WI state is never written.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from . import real_evidence, worker_registry
from .adapters import ADAPTER_REGISTRY


def dispatch_real(worker_id: str, prompt: str, *, purpose: str, task_class: str | None = None,
                  files: list[str] | None = None, timeout_s: float = 300, request_id: str | None = None,
                  extra: dict[str, Any] | None = None) -> dict[str, Any]:
    rid = request_id or f"rq-{uuid.uuid4().hex[:12]}"
    desc = worker_registry.WORKERS.get(worker_id)
    base = {"request_id": rid, "worker": worker_id, "purpose": purpose, "task_class": task_class,
            "timestamp": real_evidence.now_wita(),
            "request_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "request_excerpt": real_evidence.redact(prompt[:400]), "request_chars": len(prompt)}
    if desc is None:
        rec = {**base, "ok": False, "status": "REFUSED", "message": "unknown worker"}
        return real_evidence.append("dispatch", rec)
    base["billing_class"] = desc["billing_class"]
    base["execution_path"] = desc["execution_path"]
    if worker_registry.is_metered(worker_id):
        approval = real_evidence.owner_approved(worker_id)
        if not approval:
            rec = {**base, "ok": False, "status": "GATED", "provider_called": False,
                   "message": "metered worker; no unexpired Owner approval. No provider call, no fallback."}
            return real_evidence.append("dispatch", rec)
    adapter = ADAPTER_REGISTRY.get(desc.get("adapter") or "")
    if adapter is None:
        rec = {**base, "ok": False, "status": "NOT_CONFIGURED", "provider_called": False, "message": "no adapter"}
        return real_evidence.append("dispatch", rec)
    job = {"execute": True, "prompt": prompt, "files": files or [], "timeout_s": timeout_s, "request_id": rid,
           "work_item_id": rid, **(extra or {})}
    res = adapter.submit(job)
    data = dict(res.data or {})
    output = str(data.pop("output", "") or "")
    art = real_evidence.write_artifact(f"raw/{worker_id}/{rid}.txt", output) if output else None
    rec = {**base, "ok": bool(res.ok), "status": res.status, "message": real_evidence.redact(res.message)[:300],
           "latency_ms": data.get("latency_ms"), "model_observed": data.get("model_observed"),
           "provider_called": data.get("provider_called"), "limit_hit": bool(data.get("limit_hit")),
           "billing_preflight": data.get("billing_preflight"),
           "notional_cost_usd_reported_by_cli": data.get("notional_cost_usd_reported_by_cli"),
           "usage": data.get("usage"), "error_excerpt": real_evidence.redact(str(data.get("error_excerpt") or ""))[:600] or None,
           "response_excerpt": real_evidence.redact(output[:600]), "response_artifact": art,
           "fallback_used": False}
    stored = real_evidence.append("dispatch", rec)
    stored["_output"] = real_evidence.redact(output)
    return stored


def collect_pull(worker_id: str, request_id: str, *, purpose: str, task_class: str | None = None) -> dict[str, Any]:
    """Collect a pull-mode answer (Grok Bot). Records PENDING or the answer; never fakes success."""
    desc = worker_registry.WORKERS.get(worker_id) or {}
    adapter = ADAPTER_REGISTRY.get(desc.get("adapter") or "")
    if adapter is None:
        return real_evidence.append("dispatch", {"request_id": request_id, "worker": worker_id, "ok": False,
                                                 "status": "NOT_CONFIGURED", "timestamp": real_evidence.now_wita()})
    res = adapter.result(request_id)
    data = dict(res.data or {})
    output = str(data.pop("output", "") or "")
    art = real_evidence.write_artifact(f"raw/{worker_id}/{request_id}-answer.txt", output) if output else None
    rec = {"request_id": request_id, "worker": worker_id, "purpose": purpose, "task_class": task_class,
           "timestamp": real_evidence.now_wita(), "billing_class": desc.get("billing_class"),
           "execution_path": desc.get("execution_path"), "ok": bool(res.ok), "status": res.status,
           "message": res.message, "answered_at": data.get("answered_at"), "answered_by": data.get("answered_by"),
           "model_observed": data.get("model_observed"), "response_excerpt": real_evidence.redact(output[:600]),
           "response_artifact": art, "fallback_used": False, "mode": "PULL"}
    stored = real_evidence.append("dispatch", rec)
    stored["_output"] = output
    return stored
