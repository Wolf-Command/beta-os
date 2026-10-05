"""Single router: scores workers/models and RECOMMENDS. Does not execute expensive work."""
from __future__ import annotations

from typing import Any

from . import events, ledger, registry
from .adapters import ADAPTER_REGISTRY


CAPABILITIES = (
    "code_debug",
    "review",
    "security",
    "data_recon",
    "ui_ux",
    "large_context",
    "vision",
    "research",
)


def _job_capability(work_item: dict[str, Any]) -> str:
    kind = (work_item.get("kind") or "generic").lower()
    mapping = {
        "code_debug": "code_debug",
        "debug": "code_debug",
        "review": "review",
        "security": "security",
        "data_recon": "data_recon",
        "recon": "data_recon",
        "ui_ux": "ui_ux",
        "ui": "ui_ux",
        "large_context": "large_context",
        "vision": "vision",
        "research": "research",
        "generic": "code_debug",
    }
    return mapping.get(kind, "code_debug")


def score_candidates(work_item: dict[str, Any]) -> list[dict[str, Any]]:
    """Score without inventing capability numbers — UNKNOWN stays UNKNOWN."""
    cap = _job_capability(work_item)
    prefer = ledger.prefer_paid_capacity_order()
    models = registry.list_models()
    scored: list[dict[str, Any]] = []
    for m in models:
        mid = m["id"]
        worker = m.get("worker")
        adapter = ADAPTER_REGISTRY.get(worker) if worker else None
        health = adapter.health() if adapter else None
        health_status = health.status if health else "UNAVAILABLE"
        cap_score = registry.capability_score(mid, cap)
        # Ranking: connected health > partial; prefer paid/sub pools; UNKNOWN quality = neutral
        health_rank = {"CONNECTED": 3, "PARTIAL": 2, "UNAVAILABLE": 0}.get(health_status, 0)
        pool_id = m.get("pool_id") or ""
        prefer_rank = 100 - prefer.index(pool_id) if pool_id in prefer else 0
        billing = m.get("billing")
        # Prefer subscription/local/free over API when quality UNKNOWN (Owner: prefer already-paid)
        billing_rank = {"subscription": 3, "local": 2, "free": 2, "api": 1}.get(billing or "", 0)
        # Numeric sort key only from known facts — never invent capability
        sort_key = (health_rank, billing_rank, prefer_rank)
        scored.append(
            {
                "model_id": mid,
                "worker": worker,
                "provider": m.get("provider"),
                "billing": billing,
                "pool_id": pool_id or None,
                "capability": cap,
                "capability_score": cap_score,
                "health": health_status,
                "health_message": (health.message if health else "no adapter"),
                "sort_key": list(sort_key),
                "notes": m.get("note") or m.get("role"),
            }
        )
    scored.sort(key=lambda r: tuple(r["sort_key"]), reverse=True)
    events.emit(
        "routing.scored",
        {"capability": cap, "n": len(scored), "top": [s["model_id"] for s in scored[:3]]},
        work_item_id=work_item.get("id"),
    )
    return scored


def recommend(work_item: dict[str, Any]) -> dict[str, Any]:
    scores = score_candidates(work_item)
    # Pick first CONNECTED/PARTIAL with non-api preference when scores UNKNOWN
    pick = None
    for s in scores:
        if s["health"] in ("CONNECTED", "PARTIAL"):
            pick = s
            break
    if not pick and scores:
        pick = scores[0]
    rec = {
        "mode": "SHADOW",
        "recommended_model_id": pick["model_id"] if pick else None,
        "recommended_worker": pick["worker"] if pick else None,
        "reason": (
            "Prefer already-paid/connected capacity; capability scores UNKNOWN until benchmarked"
            if pick
            else "no candidates"
        ),
        "capability_score": pick["capability_score"] if pick else "UNKNOWN",
        "execute": False,
        "shadow_only": True,
    }
    events.emit("routing.recommended", rec, work_item_id=work_item.get("id"))
    return {"recommendation": rec, "scores": scores}
