#!/usr/bin/env python3
"""WORKFLOW-NAS-B2-DESK-STAMP-1 — honest NAS/B2 inventory glance for Owner/Content.

Surfaces Media/editable/stock shallow counts + B2 freshness + 00/02 denied
from PROVE-NAS-B2-INVENTORY-1-DEEPEN stamp. Never invents full_tree_indexed
or restore success. No NAS write / no B2 restore.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")
PACK = "WORKFLOW-NAS-B2-DESK-STAMP-1"
SCHEMA = "wolf.nas-b2-desk-stamp-1.v1"

BETA_ROOT = Path(__file__).resolve().parents[2]
STAMP_CANDIDATES = [
    BETA_ROOT / "state" / "content-engine" / "nas-b2-desk-stamp.json",
    BETA_ROOT / "state" / "final-completion" / "beta-house-20261001" / "nas-b2-desk-stamp.json",
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


def load_nas_b2_desk() -> dict[str, Any]:
    """Owner/Content desk payload — READ stamp only."""
    stamp = _read_stamp()
    if not stamp:
        return {
            "ok": False,
            "pack": PACK,
            "schema": SCHEMA,
            "as_of_wita": _now(),
            "staff_ready": False,
            "full_tree_indexed": False,
            "restore": "NOT_RUN",
            "invented_counts": False,
            "why": "nas-b2-desk-stamp.json missing — refused greenwash.",
        }
    nas = stamp.get("nas") or {}
    counts = nas.get("counts") or {}
    b2 = stamp.get("b2") or {}
    lib = stamp.get("library_db_honesty") or {}
    value = stamp.get("value_line") or (
        f"Media {counts.get('media_01_maxdepth3')} · "
        f"editable-3 {counts.get('editable_00_3_maxdepth3')} · "
        f"stock-1 {counts.get('stock_02_1_maxdepth3')} · "
        f"B2 {b2.get('freshness_headline_wita') or 'freshness stamped'} · "
        "00/02 denied · full_tree_indexed=false"
    )
    return {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA,
        "as_of_wita": stamp.get("as_of_wita") or _now(),
        "source_pack": stamp.get("source_pack") or "PROVE-NAS-B2-INVENTORY-1-DEEPEN",
        "staff_ready": False,
        "full_tree_indexed": False,
        "write": False,
        "restore": stamp.get("restore") or "NOT_RUN",
        "invented_counts": False,
        "nas": nas,
        "b2": b2,
        "library_db_honesty": lib,
        "value_line": value,
        "honesty": (
            "Shallow timed mount counts + B2 ModTime freshness. "
            "00/02 bare volumes Permission denied (honest). "
            "Library sqlite ≠ NAS tree. Restore NOT_RUN. full_tree_indexed=false."
        ),
        "href_content": "/content-2.0",
        "href_backup": "/ops/backup-health-1",
        "_stamp_path": stamp.get("_stamp_path"),
    }


if __name__ == "__main__":
    print(json.dumps(load_nas_b2_desk(), indent=2, default=str)[:3000])
