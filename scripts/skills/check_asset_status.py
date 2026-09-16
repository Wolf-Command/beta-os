"""Check asset availability — Phase 1 library empty ⇒ FILM/PARTIAL honest."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import skill_envelope  # noqa: E402


def run(
    conn,
    brand_id: str,
    feed_result: dict | None = None,
    story_result: dict | None = None,
    **_kwargs: Any,
) -> dict:
    n_assets = conn.execute(
        "SELECT COUNT(*) FROM assets WHERE lower(brand)=?",
        (brand_id.lower(),),
    ).fetchone()[0]
    feed = list(((feed_result or {}).get("result") or {}).get("feed_cards") or [])
    stories = list(((story_result or {}).get("result") or {}).get("story_spine") or [])
    for c in feed + stories:
        if n_assets == 0:
            c["asset_status"] = "FILM"
        elif n_assets < 3:
            c["asset_status"] = c.get("asset_status") or "PARTIAL"
    return skill_envelope(
        {
            "brand_id": brand_id,
            "assets_indexed": n_assets,
            "feed_cards": feed,
            "story_spine": stories,
            "default_status": "FILM" if n_assets == 0 else "PARTIAL",
        },
        evidence=[{"kind": "assets", "count": n_assets}],
        confidence=0.9,
        assumptions=[],
        missing_information=(
            ["No indexed RAW/FINAL media for brand — cards remain FILM with shot lists"]
            if n_assets == 0
            else []
        ),
    )
