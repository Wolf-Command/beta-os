#!/usr/bin/env python3
"""Pack 9 — pre-open outlet config. Read the registry. Blank close only.

No sales, till, or close figures are invented. The restaurant board title
comes from the standing Blu Zone name. The stored registry display name is
reported beside it and is not used as the board title.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
CLAUDE_MD = Path("/Users/wolfterminal/.openclaw/CLAUDE.md")
BRAND_CONFIG = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/state/brand-config.json")

PREOPEN = (
    {"outlet_id": "OU-BZG-RAIN-POOL", "role": "Pool Bar"},
    {"outlet_id": "BZG-MERAH", "role": "Merah"},
    {"outlet_id": "BZG-ROOF", "role": "Rooftop"},
    {"outlet_id": "BZG-RS", "role": "Room Service"},
    {"outlet_id": "BZG-CAT", "role": "Catering"},
    {"outlet_id": "BZG-RAIN", "role": "restaurant"},
)


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def standing_restaurant_name() -> dict[str, Any]:
    """Read B3. Do not substitute the stored Rainforest label."""
    if not CLAUDE_MD.is_file():
        return {
            "title": None,
            "resolved": False,
            "source": str(CLAUDE_MD),
            "why": "Standing preferences file is missing. No restaurant board title was invented.",
        }
    text = CLAUDE_MD.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("| B3 |"):
            continue
        if "Rainforest Restaurant" not in line or "dead" not in line:
            continue
        titles = [part.strip() for part in re.findall(r"\*\*([^*]+)\*\*", line)]
        title = next((part for part in titles if part == "Blu Zone Restaurant"), None)
        if title != "Blu Zone Restaurant":
            return {
                "title": None,
                "resolved": False,
                "source": "CLAUDE.md B3",
                "why": "B3 did not name Blu Zone Restaurant. No board title was invented.",
            }
        return {
            "title": title,
            "resolved": True,
            "source": "CLAUDE.md B3",
            "rainforest_restaurant_dead": True,
            "why": "Standing name is Blu Zone Restaurant. Rainforest Restaurant is dead.",
        }
    return {
        "title": None,
        "resolved": False,
        "source": "CLAUDE.md B3",
        "why": "B3 row was not found. No restaurant board title was invented.",
    }


def brand_config_label() -> dict[str, Any]:
    if not BRAND_CONFIG.is_file():
        return {"present": False, "label": None, "why": "brand-config.json is missing."}
    try:
        data = json.loads(BRAND_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"present": False, "label": None, "why": f"brand-config unreadable: {type(exc).__name__}"}
    brands = data.get("brands") if isinstance(data.get("brands"), dict) else {}
    row = brands.get("Rainforest") if isinstance(brands, dict) else None
    label = row.get("label") if isinstance(row, dict) else None
    return {
        "present": isinstance(row, dict),
        "key": "Rainforest" if isinstance(row, dict) else None,
        "label": label,
        "path": str(BRAND_CONFIG),
        "why": "Asset config still uses this label. It is not the board title.",
    }


def blank_close_template() -> dict[str, Any]:
    return {
        "kind": "blank",
        "inserted": False,
        "business_date": None,
        "sales": None,
        "covers": None,
        "till": None,
        "declared_cash": None,
        "esb_totals": None,
        "state": "BLANK",
        "fake_sales": False,
        "why": "Blank template only. No close row and no sales were written.",
    }


def _registry() -> dict[str, dict[str, Any]]:
    if not CATALOG_DB.is_file():
        return {}
    conn = _ro(CATALOG_DB)
    try:
        rows = conn.execute(
            """
            SELECT outlet_id, display_name, status, outlet_kind, parent_outlet_id, brand_id
            FROM org_outlet_registry
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    return {row["outlet_id"]: dict(row) for row in rows}


def _close_count(outlet_id: str) -> int | None:
    if not CATALOG_DB.is_file():
        return None
    conn = _ro(CATALOG_DB)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM venue_daily_closes
            WHERE outlet_id=? OR venue_brand_id=?
            """,
            (outlet_id, outlet_id),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return int(row[0]) if row else None


def _card(spec: dict[str, str], row: dict[str, Any] | None, standing: dict[str, Any]) -> dict[str, Any]:
    template = blank_close_template()
    if row is None:
        return {
            "outlet_id": spec["outlet_id"],
            "role": spec["role"],
            "state": "UNKNOWN",
            "ui_title": None,
            "stored_display_name": None,
            "status": None,
            "sales": None,
            "till": None,
            "close_count": None,
            "close_template": template,
            "why": "Registry row is missing. No outlet and no sales were invented.",
        }
    stored = row.get("display_name")
    if spec["role"] == "restaurant":
        ui_title = standing.get("title")
        state = "PARTIAL" if ui_title else "UNKNOWN"
        why = (
            "Stored registry display_name stays "
            f"{stored}. Board title is the standing name. No sales were invented."
            if ui_title
            else standing.get("why")
        )
    else:
        ui_title = stored
        state = "PARTIAL" if row.get("status") == "PRE-OPENING" else "UNKNOWN"
        why = "Registry row is PRE-OPENING. No desk sales and no close figures were invented."
    return {
        "outlet_id": spec["outlet_id"],
        "role": spec["role"],
        "state": state,
        "ui_title": ui_title,
        "stored_display_name": stored,
        "status": row.get("status"),
        "outlet_kind": row.get("outlet_kind"),
        "parent_outlet_id": row.get("parent_outlet_id"),
        "brand_id": row.get("brand_id"),
        "sales": None,
        "covers": None,
        "till": None,
        "close_count": _close_count(spec["outlet_id"]),
        "close_template": template,
        "why": why,
    }


def load_preopen() -> dict[str, Any]:
    standing = standing_restaurant_name()
    registry = _registry()
    cards = [_card(spec, registry.get(spec["outlet_id"]), standing) for spec in PREOPEN]
    restaurant = next(card for card in cards if card["role"] == "restaurant")
    pool = next(card for card in cards if card["outlet_id"] == "OU-BZG-RAIN-POOL")
    return {
        "ok": True,
        "pack": "PACK-09",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "fake_sales": False,
        "sales": None,
        "till": None,
        "covers": None,
        "standing_name": standing,
        "brand_config": brand_config_label(),
        "name_resolution": {
            "state": "PARTIAL" if standing.get("resolved") else "UNKNOWN",
            "ui_title": standing.get("title"),
            "stored_display_name": restaurant.get("stored_display_name"),
            "board_title_is_rainforest": False,
            "why": (
                "UI title is Blu Zone Restaurant. "
                "org_outlet_registry and brand-config still say Rainforest. "
                "Those stored labels were not overwritten."
            ),
        },
        "cards": cards,
        "pool_bar_parent": {
            "outlet_id": pool.get("parent_outlet_id"),
            "stored_display_name": restaurant.get("stored_display_name"),
            "ui_title": standing.get("title"),
        },
        "close_template": blank_close_template(),
        "uma_left_open": (registry.get("BZG-UMA") or {}).get("status"),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "fake_sales": False,
        "message": "Pre-open config does not write sales, a close, or ESB.",
    }
