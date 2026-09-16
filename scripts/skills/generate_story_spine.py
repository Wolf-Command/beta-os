"""Generate ~14 story spine items for fortnight (deterministic dry)."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import SHOT_LIST_NOTE, skill_envelope  # noqa: E402

BEATS = [
    "Morning light detail",
    "Material close-up",
    "Facade / street context",
    "Construction progress still",
    "Lifestyle quiet moment",
    "Threshold / doorway frame",
    "Community / shared space hint",
    "Founder note (text or talking-head)",
    "Owner familiarity (if cleared)",
    "Architecture location beat",
    "Before/after progress pair",
    "Golden hour exterior",
    "Interior proportion / volume",
    "Friday wrap teaser",
]


def run(conn, brand_id: str, strategy_result: dict | None = None, **_kwargs: Any) -> dict:
    strat = (strategy_result or {}).get("result") or {}
    target = int(strat.get("story_target") or 14)
    start = strat.get("period_start")
    try:
        d0 = date.fromisoformat(start) if start else date.today()
    except ValueError:
        d0 = date.today()
    stories = []
    for i in range(target):
        day = d0 + timedelta(days=i)
        beat = BEATS[i % len(BEATS)]
        stories.append(
            {
                "card_type": "story",
                "sequence": i + 1,
                "title": f"Day {i + 1}: {beat}",
                "scheduled_date": day.isoformat(),
                "hook": beat,
                "asset_status": "FILM",
                "shot_list": [beat, "B-roll support if available"],
                "shot_list_note": SHOT_LIST_NOTE,
                "status": "AI_PROPOSAL",
            }
        )
    return skill_envelope(
        {"brand_id": brand_id, "story_spine": stories, "count": len(stories)},
        evidence=[{"kind": "strategy", "period": [strat.get("period_start"), strat.get("period_end")]}],
        confidence=0.65,
        assumptions=["One story beat per day across 14-day window"],
        missing_information=["Story asset library not indexed for MATCH"],
    )
