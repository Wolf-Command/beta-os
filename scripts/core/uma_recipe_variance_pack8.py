#!/usr/bin/env python3
"""Pack 8 — Uma recipe variance. Read only.

Recipes that already have lines are read from the Beta recipe copy.
The ESB sales-menu summary is the product mix. Actual material usage is
not allocated onto those lines, so the variance amount stays unknown.
Yield is not rescaled. ESB is not written.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
RECIPES_DB = BETA_ROOT / "catalog" / "bzg_recipes.sqlite"
V1_RECIPES_DB = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/uma-blu/recipes.sqlite")
ESB_DB = Path("/Users/wolfterminal/.openclaw/data/esb.sqlite")
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK2_CLOSE = "VDC-25a3123a-3e26-43db-8085-10c6f208bbcd"
BRANCH = "BLZ"


def _norm(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _recipes() -> dict[str, Any]:
    if not RECIPES_DB.is_file():
        return {"ok": False, "why": "Beta recipe sqlite is missing."}
    conn = _ro(RECIPES_DB)
    try:
        recipes = int(conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0])
        lines = int(conn.execute("SELECT COUNT(*) FROM recipe_lines").fetchone()[0])
        with_lines = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM recipes r
                WHERE EXISTS (SELECT 1 FROM recipe_lines l WHERE l.recipe_id=r.id)
                """
            ).fetchone()[0]
        )
        rows = conn.execute("SELECT id, name FROM recipes ORDER BY name").fetchall()
        line_counts = {
            row[0]: int(row[1])
            for row in conn.execute(
                "SELECT recipe_id, COUNT(*) FROM recipe_lines GROUP BY recipe_id"
            )
        }
        first_line = {}
        for row in conn.execute(
            """
            SELECT recipe_id, name, unit, qty
            FROM recipe_lines
            ORDER BY recipe_id, sort, id
            """
        ):
            first_line.setdefault(
                row["recipe_id"],
                {"name": row["name"], "unit": row["unit"], "qty": row["qty"]},
            )
    finally:
        conn.close()
    cards = []
    for row in rows:
        count = line_counts.get(row["id"], 0)
        if count < 1:
            continue
        cards.append(
            {
                "recipe_id": row["id"],
                "name": row["name"],
                "line_count": count,
                "first_line": first_line.get(row["id"]),
            }
        )
    return {
        "ok": True,
        "path": str(RECIPES_DB),
        "recipes": recipes,
        "lines": lines,
        "with_lines": with_lines,
        "cards": cards,
    }


def _compare_count() -> dict[str, Any]:
    if not V1_RECIPES_DB.is_file():
        return {"present": False, "count": None, "why": "V1 recipe sqlite is missing."}
    conn = _ro(V1_RECIPES_DB)
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "recipe_compare" not in names:
            return {"present": False, "count": None, "why": "recipe_compare is not in the V1 recipe sqlite."}
        count = int(conn.execute("SELECT COUNT(*) FROM recipe_compare").fetchone()[0])
    finally:
        conn.close()
    return {
        "present": True,
        "count": count,
        "path": str(V1_RECIPES_DB),
        "why": "recipe_compare has no rows. No stored theoretical-versus-actual history was copied.",
    }


def _product_mix() -> dict[str, Any]:
    if not ESB_DB.is_file():
        return {"real": False, "why": "ESB sqlite is missing. Product mix was not invented."}
    conn = _ro(ESB_DB)
    try:
        rows = conn.execute(
            "SELECT biz_date, raw FROM sales_menu_summary ORDER BY biz_date DESC"
        ).fetchall()
    finally:
        conn.close()
    chosen = None
    for row in rows:
        try:
            payload = json.loads(row["raw"] or "{}")
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if (payload.get("branchCode") or "").strip().upper() != BRANCH:
            continue
        menus = payload.get("menus")
        if isinstance(menus, list) and menus:
            chosen = (row["biz_date"], payload)
            break
    if chosen is None:
        return {
            "real": False,
            "why": "No Uma Blu sales-menu summary with menu rows was readable. Variance stays UNKNOWN.",
        }
    day, payload = chosen
    items = []
    for menu in payload.get("menus") or []:
        if not isinstance(menu, dict):
            continue
        try:
            qty = float(menu.get("qty"))
        except (TypeError, ValueError):
            continue
        name = str(menu.get("menuName") or "").strip()
        if not name:
            continue
        items.append({"name": name, "qty": qty})
    if not items:
        return {
            "real": False,
            "day": day,
            "why": "The sales-menu summary had no numeric quantities. Variance stays UNKNOWN.",
        }
    return {
        "real": True,
        "day": day,
        "branch": BRANCH,
        "branch_name": payload.get("branchName"),
        "source": "esb.sqlite sales_menu_summary",
        "menu_count": len(items),
        "qty_sum": round(sum(item["qty"] for item in items), 4),
        "items": items,
        "why": "Product mix is the ESB sales-menu summary. Amounts and tax were not copied.",
    }


def _usage_count(day: str | None) -> dict[str, Any]:
    if not day or not ESB_DB.is_file():
        return {"joined": False, "row_count": None, "why": "No mix day, so usage was not read as an actual."}
    conn = _ro(ESB_DB)
    try:
        rows = conn.execute(
            "SELECT raw FROM material_usage WHERE biz_date=?",
            (day,),
        ).fetchall()
    finally:
        conn.close()
    count = 0
    for row in rows:
        try:
            payload = json.loads(row["raw"] or "{}")
        except json.JSONDecodeError:
            continue
        if (payload.get("branchCode") or "").strip().upper() == BRANCH:
            count += 1
    return {
        "joined": False,
        "row_count": count,
        "day": day,
        "source": "esb.sqlite material_usage",
        "why": (
            "Material usage rows exist for the mix day. "
            "They are branch-day product totals, not recipe-line actuals."
        ),
    }


def _close() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {"present": False, "why": "Beta catalog is missing."}
    conn = _ro(CATALOG_DB)
    try:
        policies = int(conn.execute("SELECT COUNT(*) FROM venue_close_variance_policies").fetchone()[0])
        row = conn.execute(
            """
            SELECT close_id, business_date, state, venue_brand_id, esb_totals_json,
                   declared_cash_evidence_id
            FROM venue_daily_closes WHERE close_id=?
            """,
            (PACK2_CLOSE,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {
            "present": False,
            "policies": policies,
            "why": "The Pack 2 close row was not in venue_daily_closes.",
        }
    try:
        totals = json.loads(row["esb_totals_json"] or "{}")
    except json.JSONDecodeError:
        totals = {}
    return {
        "present": True,
        "close_id": row["close_id"],
        "business_date": row["business_date"],
        "state": row["state"],
        "venue_brand_id": row["venue_brand_id"],
        "finished_count": totals.get("finished_count") if isinstance(totals, dict) else None,
        "declared_cash_evidence_id": row["declared_cash_evidence_id"],
        "policies": policies,
        "href": "/bzg/uma-blu/recipes",
        "why": "Pack 2 captured this close. That capture is not a recipe variance.",
    }


def _match(cards: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, Any]:
    menus: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        menus.setdefault(_norm(item["name"]), []).append(item)
    recipes: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        recipes.setdefault(_norm(card["name"]), []).append(card)
    matched = []
    ambiguous = 0
    for key, group in recipes.items():
        menu_group = menus.get(key) or []
        if len(group) != 1 or len(menu_group) != 1:
            if menu_group:
                ambiguous += 1
            continue
        sold = menu_group[0]["qty"]
        card = group[0]
        line = card.get("first_line") or {}
        theoretical = None
        try:
            if line.get("qty") is not None:
                theoretical = round(float(sold) * float(line["qty"]), 4)
        except (TypeError, ValueError):
            theoretical = None
        matched.append(
            {
                "recipe_id": card["recipe_id"],
                "name": card["name"],
                "line_count": card["line_count"],
                "sold_qty": sold,
                "example_ingredient": line.get("name"),
                "example_unit": line.get("unit"),
                "example_line_qty": line.get("qty"),
                "example_theoretical_qty": theoretical,
                "variance_qty": None,
            }
        )
    matched.sort(key=lambda item: (item["name"] or "").lower())
    return {"matched": matched, "ambiguous": ambiguous}


def load_variance() -> dict[str, Any]:
    recipes = _recipes()
    compare = _compare_count()
    mix = _product_mix()
    close = _close()
    usage = _usage_count(mix.get("day") if mix.get("real") else None)
    matched: list[dict[str, Any]] = []
    ambiguous = 0
    if recipes.get("ok") and mix.get("real"):
        found = _match(recipes.get("cards") or [], mix.get("items") or [])
        matched = found["matched"]
        ambiguous = found["ambiguous"]
    mix_public = {key: value for key, value in mix.items() if key != "items"}
    theoretical_state = "PARTIAL" if matched else "UNKNOWN"
    variance_why = (
        "Product mix is readable, and some recipe names match it. "
        "Material usage is not joined to recipe lines. "
        "A day total minus a partial recipe explosion would invent a variance. "
        "Stored yield was not used to rescale quantities."
        if mix.get("real")
        else mix.get("why") or "Product mix is not readable. Variance stays UNKNOWN."
    )
    return {
        "ok": True,
        "pack": "PACK-08",
        "staff_ready": False,
        "human_proven": False,
        "esb_write": False,
        "yield_invented": False,
        "recipes": {
            "path": recipes.get("path"),
            "recipes": recipes.get("recipes"),
            "lines": recipes.get("lines"),
            "with_lines": recipes.get("with_lines"),
            "ok": recipes.get("ok"),
        },
        "recipe_compare": compare,
        "product_mix": mix_public,
        "theoretical": {
            "state": theoretical_state,
            "matched_recipes": len(matched),
            "ambiguous": ambiguous,
            "sample": matched[:8],
            "label": "THEORETICAL",
        },
        "actual": usage,
        "variance": {
            "state": "UNKNOWN",
            "amount": None,
            "qty": None,
            "yield_invented": False,
            "why": variance_why,
        },
        "pack2_close": close,
        "desk_href": "/bzg/uma-blu/recipes",
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "esb_write": False,
        "yield_invented": False,
        "message": "Recipe variance does not write ESB, yield, or a variance amount.",
    }
