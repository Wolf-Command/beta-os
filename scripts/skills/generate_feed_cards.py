"""Generate ~3 feed cards for fortnight from strategy + memory (deterministic dry)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import SHOT_LIST_NOTE, skill_envelope  # noqa: E402

TEMPLATES = [
    {
        "title": "Construction honesty — materials in progress",
        "hook": "Concrete curing. Timber waiting. The quiet work before the reveal.",
        "pillar": "construction",
        "asset_status": "FILM",
        "shots": [
            "Facade clean sky / no scaffolding if possible",
            "Material close-up: concrete, timber, stone",
            "Progress establishing wide",
        ],
    },
    {
        "title": "Weekend morning energy",
        "hook": "Slow light. Open thresholds. A morning that doesn't rush you.",
        "pillar": "lifestyle",
        "asset_status": "FILM",
        "shots": [
            "Interior-to-exterior morning frame",
            "Quiet domestic detail (handle, reveal, shadow line)",
            "Aspirational unhurried lifestyle beat",
        ],
    },
    {
        "title": "Friday developer update",
        "hook": "On site this week: what moved, who joined, what's next.",
        "pillar": "founder_investor",
        "asset_status": "FILM",
        "shots": [
            "Matt talking-head or sit-down (lav is not a walk)",
            "Named owner familiarity beat if available",
            "One honest construction progress cutaway",
        ],
    },
]


def run(conn, brand_id: str, strategy_result: dict | None = None, **_kwargs: Any) -> dict:
    strat = (strategy_result or {}).get("result") or {}
    target = int(strat.get("feed_target") or 3)
    cards = []
    for i, t in enumerate(TEMPLATES[:target]):
        cards.append(
            {
                "card_type": "feed",
                "sequence": i + 1,
                "title": t["title"],
                "hook": t["hook"],
                "pillar": t["pillar"],
                "platform": "IG_Reels",
                "asset_status": t["asset_status"],
                "shot_list": t["shots"],
                "shot_list_note": SHOT_LIST_NOTE,
                "caption_draft": t["hook"],
                "status": "AI_PROPOSAL",
            }
        )
    return skill_envelope(
        {"brand_id": brand_id, "feed_cards": cards, "count": len(cards)},
        evidence=[{"kind": "strategy", "theme": strat.get("theme")}],
        confidence=0.7 if strat else 0.4,
        assumptions=["Dry templates derived from brand voice rules + cadence targets"],
        missing_information=["Asset MATCH not connected — cards default FILM"],
    )
