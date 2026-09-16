"""Build Evidence Pack: Brand Memory + Previous Plans + Metricool Evidence + Asset State."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import content_hash, now_iso, skill_envelope  # noqa: E402


def run(
    conn,
    brand_id: str,
    *,
    memory_result: dict | None = None,
    recent_plans_result: dict | None = None,
    metricool_result: dict | None = None,
    asset_result: dict | None = None,
    **_kwargs: Any,
) -> dict:
    mem = (memory_result or {}).get("result") or {}
    plans = (recent_plans_result or {}).get("result") or {}
    perf = (metricool_result or {}).get("result") or {}
    assets = (asset_result or {}).get("result") or {}

    missing = []
    if not mem:
        missing.append("Brand memory empty or not loaded")
    if not (plans.get("recent_plans")):
        missing.append("No previous plans")
    if not perf.get("available"):
        missing.append("Performance unavailable")
    # Trend / Learning honestly not connected
    missing.append("Trend research not connected")
    missing.append("Learning library not connected")

    pack = {
        "brand_id": brand_id,
        "sections": {
            "brand_memory": {
                "facts": len(mem.get("facts") or []),
                "rules": len(mem.get("rules") or []),
                "decisions": len(mem.get("decisions") or []),
            },
            "previous_plans": {
                "count": len(plans.get("recent_plans") or []),
                "ids": [p.get("id") for p in (plans.get("recent_plans") or [])],
            },
            "metricool_evidence": {
                "available": bool(perf.get("available")),
                "row_count": perf.get("row_count") or 0,
                "format_patterns": perf.get("format_patterns") or [],
                "by_surface_summary": {
                    s: {
                        "n": (perf.get("by_surface") or {}).get(s, {}).get("n"),
                        "median_reach": (
                            ((perf.get("by_surface") or {}).get(s) or {})
                            .get("reach") or {}
                        ).get("median"),
                    }
                    for s in ("post", "reel", "story")
                },
                "evidence_item_ids": perf.get("evidence_item_ids") or [],
            },
            "asset_state": {
                "assets_indexed": assets.get("assets_indexed"),
                "default_status": assets.get("default_status"),
            },
            "trend": {"status": "not connected"},
            "learning_library": {"status": "not connected"},
        },
        "important_learnings": [],
    }
    # Honest learnings from performance only when available — descriptive
    for pat in perf.get("format_patterns") or []:
        pack["important_learnings"].append(
            {
                "source": "performance",
                "surface": pat.get("surface"),
                "text": pat.get("statement"),
            }
        )
    if not pack["important_learnings"] and not perf.get("available"):
        pack["important_learnings"].append(
            {"source": "performance", "text": "Performance unavailable"}
        )

    conf = 0.65
    if perf.get("available"):
        conf = 0.8
    elif missing:
        conf = 0.4

    return skill_envelope(
        pack,
        evidence=[
            {"kind": "evidence_pack", "brand_id": brand_id, "hash": content_hash(json.dumps(pack, sort_keys=True))},
        ],
        confidence=conf,
        assumptions=[
            "Evidence pack freezes inputs known at build time.",
            "Trend and Learning Library remain not connected.",
        ],
        missing_information=missing,
    )


def freeze_planning_context_snapshot(
    conn,
    *,
    brand_key: str,
    plan_id: int,
    plan_revision_id: int | None,
    subject: str,
    memory_result: dict,
    recent_plans_result: dict,
    metricool_result: dict,
    asset_result: dict,
    evidence_pack: dict,
    data_lane: str = "operational",
) -> int:
    """Immutable snapshot of what was known — never overwrite with later re-query."""
    mem_ids = []
    mem = (memory_result or {}).get("result") or {}
    for bucket in ("facts", "rules", "decisions", "items"):
        for it in mem.get(bucket) or []:
            if isinstance(it, dict) and it.get("id"):
                mem_ids.append(it["id"])

    perf = (metricool_result or {}).get("result") or {}
    perf_ids = []
    for ev in (metricool_result or {}).get("evidence") or []:
        if ev.get("performance_record_id"):
            perf_ids.append(ev["performance_record_id"])
    # Also hash window
    hashes = []
    if perf_ids:
        rows = conn.execute(
            f"SELECT id, content_hash FROM performance_records WHERE id IN ({','.join('?'*len(perf_ids))})",
            perf_ids,
        ).fetchall()
        hashes = [r["content_hash"] for r in rows if r["content_hash"]]

    snap_body = {
        "brand_key": brand_key,
        "plan_id": plan_id,
        "frozen_at": now_iso(),
        "memory_ids": mem_ids,
        "prior_plan_ids": [
            p.get("id") for p in ((recent_plans_result or {}).get("result") or {}).get("recent_plans") or []
        ],
        "performance_record_ids": perf_ids,
        "performance_content_hashes": hashes,
        "metricool_available": bool(perf.get("available")),
        "asset_state": (asset_result or {}).get("result"),
        "evidence_pack_hash": content_hash(
            json.dumps((evidence_pack or {}).get("result") or {}, sort_keys=True, default=str)
        ),
        "disconnected": {
            "trend": "not connected",
            "learning_library": "not connected",
        },
    }
    blob = json.dumps(snap_body, sort_keys=True, default=str)
    ch = content_hash(blob)
    cur = conn.execute(
        """
        INSERT INTO planning_context_snapshots (
          brand_key, plan_id, plan_revision_id, created_at, created_by_subject,
          snapshot_json, content_hash, data_lane
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_key,
            plan_id,
            plan_revision_id,
            now_iso(),
            subject,
            blob,
            ch,
            data_lane,
        ),
    )
    snap_id = int(cur.lastrowid)

    def add_ref(ref_type: str, ref_id: Any, version_or_hash: str | None = None, meta: dict | None = None):
        conn.execute(
            """
            INSERT INTO planning_context_refs (snapshot_id, ref_type, ref_id, version_or_hash, meta_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                snap_id,
                ref_type,
                str(ref_id) if ref_id is not None else None,
                version_or_hash,
                json.dumps(meta or {}),
            ),
        )

    for mid in mem_ids:
        add_ref("brand_memory", mid)
    for pid in snap_body["prior_plan_ids"]:
        add_ref("prior_plan", pid)
    for prid, h in zip(perf_ids, hashes or [None] * len(perf_ids)):
        add_ref("metricool_performance", prid, h)
    add_ref(
        "asset_state",
        brand_key,
        meta={"assets_indexed": ((asset_result or {}).get("result") or {}).get("assets_indexed")},
    )
    # Enums prepared but unused until connected
    # trend / learning_item intentionally not written
    # decisions from memory
    for it in mem.get("decisions") or []:
        if isinstance(it, dict) and it.get("id"):
            add_ref("decision", it["id"])

    return snap_id
