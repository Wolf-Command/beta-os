"""AnalyzeMetricoolPerformance — descriptive baselines only; no causal claims."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import content_hash, now_iso, skill_envelope  # noqa: E402

SURFACES = ("post", "reel", "story")


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    return float(statistics.median(vals))


def _quartiles(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"q1": None, "median": None, "q3": None}
    s = sorted(vals)
    n = len(s)
    # Simple quartile indices — descriptive only
    q1 = float(s[max(0, n // 4)])
    q3 = float(s[min(n - 1, (3 * n) // 4)])
    return {"q1": q1, "median": _median(s), "q3": q3}


def _collect(rows: list[dict], field: str) -> list[float]:
    out = []
    for r in rows:
        v = r.get(field)
        if v is None:
            continue  # NULL ≠ 0
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def run(
    conn,
    brand_key: str,
    *,
    data_lane: str = "operational",
    window_days: int | None = 60,
    **_kwargs: Any,
) -> dict:
    """Full contract: result + evidence + confidence + assumptions + missing_information.

    Never compares Story vs Reel with a single score.
    No causal language ("caused", "drove", "because of").
    """
    assumptions = [
        "Metrics describe observed distribution only — not causes.",
        "Surfaces (post/reel/story) are analyzed separately; never blended into one score.",
        "NULL metrics excluded from medians/quartiles (NULL is not zero).",
        f"Default learning/evidence lane={data_lane} (non-operational excluded).",
    ]
    missing: list[str] = []
    sql = """
        SELECT * FROM performance_records
        WHERE brand_key=? AND external_system='metricool' AND data_lane=?
    """
    params: list[Any] = [brand_key, data_lane]
    if window_days:
        sql += """
          AND (
            published_at_utc IS NULL
            OR date(published_at_utc) >= date('now', ?)
          )
        """
        params.append(f"-{int(window_days)} days")
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    if not rows:
        missing.append("No operational performance_records for brand in window")
        return skill_envelope(
            {
                "brand_key": brand_key,
                "available": False,
                "by_surface": {},
                "note": "Performance unavailable",
            },
            evidence=[],
            confidence=0.2,
            assumptions=assumptions,
            missing_information=missing,
        )

    by_surface: dict[str, Any] = {}
    evidence_links: list[dict] = []
    for surface in SURFACES:
        srows = [r for r in rows if r.get("surface") == surface]
        reach_vals = _collect(srows, "reach")
        eng_vals = _collect(srows, "engagement")
        q_reach = _quartiles(reach_vals)
        q_eng = _quartiles(eng_vals)
        # Top / bottom quartile examples by reach within THIS surface only
        ranked = [
            r for r in srows if r.get("reach") is not None
        ]
        ranked.sort(key=lambda r: float(r["reach"]), reverse=True)
        top = ranked[:3]
        bottom = list(reversed(ranked[-3:])) if len(ranked) >= 3 else list(reversed(ranked))
        by_surface[surface] = {
            "n": len(srows),
            "n_with_reach": len(reach_vals),
            "n_with_engagement": len(eng_vals),
            "reach": {
                "median": q_reach["median"],
                "q1": q_reach["q1"],
                "q3": q_reach["q3"],
            },
            "engagement_count": {
                "median": q_eng["median"],
                "q1": q_eng["q1"],
                "q3": q_eng["q3"],
            },
            "reach_outliers_high": [
                {
                    "id": r["id"],
                    "external_post_id": r["external_post_id"],
                    "reach": r["reach"],
                    "permalink": r.get("permalink"),
                }
                for r in top
            ],
            "reach_outliers_low": [
                {
                    "id": r["id"],
                    "external_post_id": r["external_post_id"],
                    "reach": r["reach"],
                    "permalink": r.get("permalink"),
                }
                for r in bottom
            ],
        }
        for r in top[:2] + bottom[:1]:
            evidence_links.append(
                {
                    "type": "performance_record",
                    "source": "metricool",
                    "performance_record_id": r["id"],
                    "permalink": r.get("permalink"),
                    "surface": surface,
                    "external_post_id": r["external_post_id"],
                }
            )

    # Persist evidence_items (sanitized content — no secrets)
    linked_ids = []
    for ev in evidence_links:
        content = json.dumps(ev, sort_keys=True)
        ch = content_hash(content)
        cur = conn.execute(
            """
            INSERT INTO evidence_items (kind, ref, content, content_hash, brand_id, linked_memory_id, created_at)
            VALUES ('performance_record', ?, ?, ?, ?, NULL, ?)
            """,
            (
                f"metricool:{ev['performance_record_id']}",
                content,
                ch,
                brand_key,
                now_iso(),
            ),
        )
        linked_ids.append(int(cur.lastrowid))

    # Best formats = surface with highest median reach among surfaces that have data
    # Descriptive only — not a causal claim
    format_notes = []
    medians = {
        s: (by_surface[s]["reach"]["median"], by_surface[s]["n_with_reach"])
        for s in SURFACES
        if by_surface.get(s) and by_surface[s]["reach"]["median"] is not None
    }
    if medians:
        # report separately, do not invent a blended winner score across story vs reel
        for s, (med, n) in sorted(medians.items(), key=lambda x: (x[1][0] or 0), reverse=True):
            format_notes.append(
                {
                    "surface": s,
                    "median_reach": med,
                    "sample_size": n,
                    "statement": (
                        f"Within {s} surface only, median reach was {med} "
                        f"across {n} items with non-null reach."
                    ),
                }
            )

    result = {
        "brand_key": brand_key,
        "available": True,
        "data_lane": data_lane,
        "row_count": len(rows),
        "by_surface": by_surface,
        "format_patterns": format_notes,
        "evidence_item_ids": linked_ids,
        "disclaimer": (
            "Descriptive statistics only. No causal claims. "
            "Do not compare story vs reel with a single blended score."
        ),
    }
    conf = 0.7 if len(rows) >= 10 else 0.45
    return skill_envelope(
        result,
        evidence=evidence_links,
        confidence=conf,
        assumptions=assumptions,
        missing_information=missing,
    )
