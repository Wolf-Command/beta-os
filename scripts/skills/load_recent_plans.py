"""Load recent content_plans for a brand (history context)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import skill_envelope  # noqa: E402


def run(
    conn,
    brand_id: str,
    limit: int = 5,
    *,
    include_test_lane: bool = False,
    for_learning: bool = True,
    **_kwargs: Any,
) -> dict:
    """By default, learning/evidence ignores non-operational lanes."""
    if for_learning and not include_test_lane:
        rows = conn.execute(
            """
            SELECT id, title, period_start, period_end, status, created_at, created_by, data_lane
            FROM content_plans
            WHERE brand_id=? AND ifnull(data_lane,'operational')='operational'
            ORDER BY id DESC LIMIT ?
            """,
            (brand_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, title, period_start, period_end, status, created_at, created_by,
                   ifnull(data_lane,'operational') AS data_lane
            FROM content_plans WHERE brand_id=? ORDER BY id DESC LIMIT ?
            """,
            (brand_id, limit),
        ).fetchall()
    plans = [dict(r) for r in rows]
    missing = []
    if not plans:
        missing.append("No prior operational content_plans for brand — first Working Draft")
    return skill_envelope(
        {"brand_id": brand_id, "recent_plans": plans, "lane_filter": "operational" if for_learning else "all"},
        evidence=[{"kind": "content_plans", "count": len(plans), "lane": "operational"}],
        confidence=0.85 if plans else 0.4,
        assumptions=["Test-lane plans excluded from learning/evidence by default"],
        missing_information=missing,
    )
