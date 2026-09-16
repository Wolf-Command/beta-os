"""Load Metricool evidence for a brand from performance_records (operational lane)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import skill_envelope  # noqa: E402

from . import analyze_metricool_performance  # noqa: E402


def run(conn, brand_id: str, **kwargs: Any) -> dict:
    """Alias brand_id → brand_key; soft-fail empty when no data."""
    brand_key = brand_id
    try:
        analysis = analyze_metricool_performance.run(conn, brand_key, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return skill_envelope(
            {"brand_key": brand_key, "available": False, "note": "Performance unavailable"},
            confidence=0.1,
            assumptions=["Analyzer soft-failed"],
            missing_information=[f"Performance load error: {type(exc).__name__}"],
        )
    return analysis
