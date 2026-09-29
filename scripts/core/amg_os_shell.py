#!/usr/bin/env python3
"""AMG-OS-SHELL-1 — AMG operating shell without Yanolja live (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OS-SHELL-1
(armed 2026-09-30) — structure toward CAP-AMG-02 / CAP-AMG-04 / MB-008 only.
Does NOT unblock CAP-AMG-01 (Yanolja). PMS-dependent tiles stamp
BLOCKED_EXTERNAL and point at /ops/integrations-status. Never invents
occupancy, arrivals, room status, folio, or PMS numbers. Never flips
staff_ready / human_commissioned.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK = "AMG-OS-SHELL-1"
SCHEMA_ID = "wolf.amg-os-shell.v1"
BOUND = "beta-amg-ops-safe"
HONESTY_BOARD = "/ops/integrations-status"
YANOLJA_ID = "INT-YAN-WOLF"

PAGE_PATHS = frozenset(
    {
        "/amg/os-shell",
        "/amg/os-shell/",
        "/amg-os-shell",
        "/amg-os-shell/",
        "/amg-os-shell.html",
        "/dashboards/amg-os-shell.html",
    }
)

WITA = timezone(timedelta(hours=8))

# Day-ops structure slots that require live PMS / Yanolja — always blocked here.
_PMS_TILE_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "arrivals",
        "Arrivals",
        "Waiting on Yanolja PMS. Not an arrival list. Not zeros-as-success.",
    ),
    (
        "departures",
        "Departures",
        "Waiting on Yanolja PMS. Not a departure list. Not proof of hotel ops.",
    ),
    (
        "rooms",
        "Rooms / room status",
        "Waiting on Yanolja PMS. Not a room status board. Not occupancy.",
    ),
    (
        "guest_requests",
        "Guest requests",
        "Waiting on Yanolja PMS. Not a live guest-request queue.",
    ),
    (
        "occupancy",
        "Occupancy",
        "Waiting on Yanolja PMS. UNKNOWN — never invent a percent or count.",
    ),
)


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == "/api/amg/os-shell"


def _pms_tile(tile_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": tile_id,
        "label": label,
        "kind": "pms_dependent",
        "status": "BLOCKED_EXTERNAL",
        "blocked_external": True,
        "value": None,
        "display": "UNKNOWN",
        "count": None,
        "occupancy_pct": None,
        "yanolja_live": False,
        "pms_connected": False,
        "integration_id": YANOLJA_ID,
        "honesty_board_href": HONESTY_BOARD,
        "why": why,
    }


def _commissioning_holds() -> dict[str, Any]:
    """Real commissioning OPEN hold count from catalog — not PMS data."""
    if not CATALOG_DB.is_file():
        return {
            "origin": "commissioning",
            "open_holds": None,
            "status": "UNKNOWN",
            "source": None,
            "note": "Catalog absent — commissioning hold count not invented.",
        }
    try:
        conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
        try:
            open_n = conn.execute(
                "SELECT COUNT(*) FROM core_work_items "
                "WHERE origin='commissioning' AND status='OPEN'"
            ).fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return {
            "origin": "commissioning",
            "open_holds": None,
            "status": "UNKNOWN",
            "source": str(CATALOG_DB.relative_to(BETA_ROOT)),
            "note": "Catalog read failed — hold count not invented.",
        }
    return {
        "origin": "commissioning",
        "open_holds": int(open_n),
        "status": "OPEN" if open_n else "EMPTY",
        "source": str(CATALOG_DB.relative_to(BETA_ROOT)),
        "note": "Non-PMS structure from core_work_items. Not hotel occupancy.",
    }


def _structure_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "my_work",
            "label": "My Work",
            "href": "/my-work",
            "kind": "non_pms",
            "note": "Universal work loop — not PMS occupancy.",
        },
        {
            "id": "amg_today",
            "label": "AMG Today desk",
            "href": "/amg-ops-pack",
            "kind": "non_pms",
            "note": "Day-loop / Needs-You structure — not live hotel facts.",
        },
        {
            "id": "finance_desk",
            "label": "Atrium finance desk",
            "href": "/amg/finance",
            "kind": "non_pms",
            "note": "FC-SHELL / ATRIUM books path — not Yanolja folio.",
        },
        {
            "id": "daily_ops_framework",
            "label": "Daily ops framework",
            "href": "/amg-daily-ops-state",
            "kind": "non_pms",
            "note": "CAP-AMG-04 empty slot names — not live ops.",
        },
        {
            "id": "integrations_honesty",
            "label": "Integrations honesty board",
            "href": HONESTY_BOARD,
            "kind": "honesty",
            "note": "INT-YAN-WOLF BLOCKED_EXTERNAL — CAP-AMG-01 stays blocked.",
        },
    ]


def build_shell(*, refresh_board: bool = False) -> dict[str, Any]:
    """Public AMG OS shell payload. Auth gating is caller's responsibility."""
    board = _intg.build_board(persist_audit=False)
    connectors = list(board.get("connectors") or [])
    yan = next(
        (c for c in connectors if c.get("integration_id") == YANOLJA_ID),
        None,
    )
    yanolja_blocked = bool(
        yan
        and yan.get("audit_status") == "BLOCKED_EXTERNAL"
        and yan.get("blocked_external") is True
        and yan.get("last_success") is None
    )
    pms_tiles = [_pms_tile(*spec) for spec in _PMS_TILE_SPECS]
    holds = _commissioning_holds()
    payload = {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "cap_amg_01_unblocked": False,
        "yanolja_live": False,
        "fake_pms_data": False,
        "invented_occupancy": False,
        "invented_arrivals": False,
        "pms_tiles": pms_tiles,
        "structure_links": _structure_links(),
        "commissioning": {
            **holds,
            "staff_ready": False,
            "human_commissioned": False,
        },
        "yanolja": {
            "integration_id": YANOLJA_ID,
            "audit_status": (yan or {}).get("audit_status") or "BLOCKED_EXTERNAL",
            "blocked_external": True,
            "probe_status": (yan or {}).get("probe_status"),
            "last_success": None,
            "honesty_board_href": HONESTY_BOARD,
            "blocked_confirmed": yanolja_blocked,
        },
        "honesty": {
            "yanolja": "BLOCKED_EXTERNAL",
            "pms_tiles": "BLOCKED_EXTERNAL",
            "display_policy": "UNKNOWN_or_BLOCKED_never_zero_as_success",
            "cap_amg_01": "BLOCKED_EXTERNAL",
            "cap_amg_02": "STRUCTURE_ONLY",
            "cap_amg_04": "STRUCTURE_ONLY",
            "mb_008": "STRUCTURE_ONLY_NOT_LIVE",
            "honesty_board_href": HONESTY_BOARD,
        },
        "closes_toward": ["CAP-AMG-02", "CAP-AMG-04", "MB-008"],
        "does_not_unblock": ["CAP-AMG-01", "Yanolja"],
        "cursor_did_not_auto_start_next_pack": True,
        "intg_board_pack": board.get("pack"),
        "intg_board_ok": board.get("ok") is True,
    }
    if refresh_board:
        # No-op hook for symmetry with truth board; shell never persists audit.
        pass
    return payload


def public_payload() -> dict[str, Any]:
    return build_shell()


def all_pms_tiles_blocked(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_shell()
    tiles = pack.get("pms_tiles") or []
    if not tiles:
        return False
    return all(
        t.get("status") == "BLOCKED_EXTERNAL"
        and t.get("value") is None
        and t.get("display") == "UNKNOWN"
        and t.get("count") is None
        and t.get("occupancy_pct") is None
        for t in tiles
    )
