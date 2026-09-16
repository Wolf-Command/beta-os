"""Deterministic fortnight strategy from brand memory + cadence + evidence pack."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import fortnight_bounds, skill_envelope  # noqa: E402


def run(
    conn,
    brand_id: str,
    memory_result: dict | None = None,
    evidence_pack: dict | None = None,
    **_kwargs: Any,
) -> dict:
    brand = conn.execute("SELECT * FROM brands WHERE id=?", (brand_id,)).fetchone()
    if not brand:
        return skill_envelope(
            None,
            confidence=0.0,
            missing_information=[f"Brand {brand_id} not found"],
        )
    cadence = {}
    try:
        cadence = json.loads(brand["cadence_json"] or "{}")
    except json.JSONDecodeError:
        cadence = {}
    period_start, period_end = fortnight_bounds()
    mem = (memory_result or {}).get("result") or {}
    pack = (evidence_pack or {}).get("result") or {}
    voice_rules = [r["text"] for r in (mem.get("rules") or [])]
    objectives = [
        "Maintain architectural journal tone; avoid banned clichés",
        "Balance construction proof with lifestyle aspiration",
        "Include developer Friday update when in window",
    ]
    mix = {
        "construction": 0.35,
        "lifestyle": 0.25,
        "founder_investor": 0.20,
        "architecture_location": 0.20,
    }
    ratio_in_memory = any("35%" in (f.get("text") or "") for f in (mem.get("facts") or []))
    assumptions = []
    missing = []
    if not ratio_in_memory:
        assumptions.append(
            "Content mix percentages used as dry planning guide from kit; "
            "not treated as ACTIVE FACT unless present in approved memory"
        )

    important_learnings = list(pack.get("important_learnings") or [])
    perf_section = (pack.get("sections") or {}).get("metricool_evidence") or {}
    perf_available = bool(perf_section.get("available"))

    disconnected = {
        "performance_data": "connected" if perf_available else "Performance unavailable",
        "trend_lane": "not connected",
        "inspiration_library": "not connected",
    }

    strategy = {
        "brand_id": brand_id,
        "display_name": brand["display_name"],
        "period_start": period_start,
        "period_end": period_end,
        "theme": "Considered living — construction honesty meets quiet domestic aspiration",
        "objectives": objectives,
        "voice_rules": voice_rules,
        "cadence": cadence,
        "content_mix_guide": mix,
        "feed_target": int(cadence.get("fortnight_feed_target") or 3),
        "story_target": int(cadence.get("fortnight_story_target") or 14),
        "important_learnings": important_learnings,
        "metricool_evidence_used": perf_available,
        "disconnected": disconnected,
    }
    if not mem.get("facts"):
        missing.append("Brand memory thin — strategy confidence reduced")
    if not perf_available:
        missing.append("Performance unavailable")
    missing.extend(
        [
            "Trend research not connected",
            "Inspiration library / Learning library not connected",
        ]
    )
    conf = 0.75 if mem.get("facts") and mem.get("rules") else 0.45
    if perf_available:
        conf = min(0.9, conf + 0.1)
    return skill_envelope(
        strategy,
        evidence=[
            {"kind": "brands", "id": brand_id},
            {"kind": "memory_facts", "count": len(mem.get("facts") or [])},
            {"kind": "memory_rules", "count": len(mem.get("rules") or [])},
            {"kind": "metricool_evidence", "available": perf_available},
        ],
        confidence=conf,
        assumptions=assumptions,
        missing_information=missing,
    )
