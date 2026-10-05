#!/usr/bin/env python3
"""WORKFLOW-METRICOOL-SCHEDULE-GLANCE-1 — brands/list/schedule freshness READ only.

No Metricool WRITE. No engagement invent. Stamp from authorised MCP READ
(getBrandSettings + getScheduledPosts) frozen into state JSON for Beta desks.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")
PACK = "WORKFLOW-METRICOOL-SCHEDULE-GLANCE-1"
SCHEMA = "wolf.metricool-schedule-glance-1.v1"

BETA_ROOT = Path(__file__).resolve().parents[2]
STAMP_CANDIDATES = [
    BETA_ROOT / "state" / "content-engine" / "metricool-schedule-glance.json",
    BETA_ROOT / "state" / "final-completion" / "beta-house-20261001" / "metricool-schedule-glance.json",
]


def _now() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def _read_stamp() -> dict[str, Any] | None:
    for path in STAMP_CANDIDATES:
        try:
            if not path.is_file():
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("ok") is True:
                raw["_stamp_path"] = str(path)
                return raw
        except Exception:  # noqa: BLE001
            continue
    return None


def load_schedule_glance() -> dict[str, Any]:
    stamp = _read_stamp()
    if not stamp:
        return {
            "ok": False,
            "pack": PACK,
            "schema": SCHEMA,
            "as_of_wita": _now(),
            "metricool_write": False,
            "invented_engagement": False,
            "engagement": None,
            "why": "metricool-schedule-glance.json missing — refused invent.",
        }
    brands = stamp.get("brands") or {}
    sched = stamp.get("schedule_read") or {}
    value = stamp.get("value_line") or (
        f"brands {brands.get('count')} · schedule READ stamped · WRITE OFF"
    )
    return {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA,
        "as_of_wita": stamp.get("as_of_wita") or _now(),
        "metricool_write": False,
        "invented_engagement": False,
        "engagement": None,
        "brands": brands,
        "schedule_read": sched,
        "value_line": value,
        "honesty": (
            "Brands list + schedule window post counts (PENDING/PUBLISHED status only). "
            "Engagement/likes/reach NOT invented. Metricool WRITE OFF."
        ),
        "href_ggv_social": "/ggv-ops-pack#social",
        "_stamp_path": stamp.get("_stamp_path"),
    }


if __name__ == "__main__":
    print(json.dumps(load_schedule_glance(), indent=2, default=str)[:3000])
