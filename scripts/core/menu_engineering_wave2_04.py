#!/usr/bin/env python3
"""Wave 2.04 — Menu engineering read. No scores.

Recipes and the ESB quantity mix are readable. Line cost is a stored card
cost. Material usage is not joined to those lines, so contribution margin
and star / plowhorse / puzzle / dog classes stay unassigned.
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
        rows = conn.execute(
            "SELECT id, name, target_cos, real_sell, esb_menu FROM recipes"
        ).fetchall()
        line_rows = conn.execute(
            "SELECT recipe_id, unit_cost, cost_source FROM recipe_lines"
        ).fetchall()
    finally:
        conn.close()
    by_recipe: dict[Any, list[sqlite3.Row]] = {}
    source_card = source_manual = source_missing = 0
    line_cost_present = line_cost_missing = line_cost_zero = 0
    for line in line_rows:
        by_recipe.setdefault(line["recipe_id"], []).append(line)
        source = line["cost_source"]
        if source == "card":
            source_card += 1
        elif source == "manual":
            source_manual += 1
        else:
            source_missing += 1
        cost = line["unit_cost"]
        if cost is None:
            line_cost_missing += 1
        elif float(cost) == 0:
            line_cost_zero += 1
        else:
            line_cost_present += 1
    complete = partial = missing = 0
    cards = []
    target_rows = 0
    sell_rows = 0
    esb_links = 0
    for row in rows:
        if row["target_cos"] not in (None, ""):
            target_rows += 1
        if row["real_sell"] not in (None, "", 0, 0.0):
            sell_rows += 1
        if row["esb_menu"] not in (None, ""):
            esb_links += 1
        group = by_recipe.get(row["id"], [])
        priced = [line for line in group if line["unit_cost"] is not None]
        if group and len(priced) == len(group):
            complete += 1
            cost_state = "COMPLETE"
        elif priced:
            partial += 1
            cost_state = "PARTIAL"
        else:
            missing += 1
            cost_state = "MISSING"
        if not group:
            continue
        cards.append(
            {
                "recipe_id": row["id"],
                "name": row["name"],
                "cost_state": cost_state,
            }
        )
    return {
        "ok": True,
        "recipes": recipes,
        "lines": lines,
        "with_lines": with_lines,
        "cost_complete": complete,
        "cost_partial": partial,
        "cost_missing": missing,
        "line_cost_present": line_cost_present,
        "line_cost_zero": line_cost_zero,
        "line_cost_missing": line_cost_missing,
        "cost_source_card": source_card,
        "cost_source_manual": source_manual,
        "cost_source_missing": source_missing,
        "stored_target_cos_rows": target_rows,
        "stored_real_sell_rows": sell_rows,
        "esb_menu_links": esb_links,
        "cards": cards,
        "why": (
            "Recipes are a copy. A stored target or sell column is not a "
            "menu-engineering score."
        ),
    }


def _compare() -> dict[str, Any]:
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
        "why": "recipe_compare has no rows. No stored engineering history was copied.",
    }


def _mix() -> dict[str, Any]:
    if not ESB_DB.is_file():
        return {"real": False, "items": [], "why": "ESB sqlite is missing. The mix was not invented."}
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
        return {"real": False, "items": [], "why": "No Uma Blu sales-menu summary with menu rows was readable."}
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
            "items": [],
            "why": "The sales-menu summary had no numeric quantities.",
        }
    return {
        "real": True,
        "day": day,
        "branch": BRANCH,
        "branch_name": payload.get("branchName"),
        "menu_count": len(items),
        "qty_sum": round(sum(item["qty"] for item in items), 4),
        "amounts_copied": False,
        "items": items,
        "source": "esb.sqlite sales_menu_summary",
        "why": "Quantity mix is readable. Amounts were not copied. This is not a popularity class.",
    }


def _usage(day: str | None) -> dict[str, Any]:
    if not day or not ESB_DB.is_file():
        return {"joined": False, "row_count": None, "why": "No mix day, so usage was not read as a plate cost."}
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
        "why": "Material usage is a branch-day total. It is not a plate cost.",
    }


def _join(cards: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, Any]:
    menu_keys = [_norm(item["name"]) for item in items]
    recipes: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        recipes.setdefault(_norm(card["name"]), []).append(card)
    matched = 0
    ambiguous = 0
    complete = 0
    missing = 0
    matched_keys: set[str] = set()
    for key, group in recipes.items():
        menu_n = menu_keys.count(key)
        if menu_n == 0:
            continue
        if len(group) != 1 or menu_n != 1:
            ambiguous += 1
            continue
        matched += 1
        matched_keys.add(key)
        if group[0].get("cost_state") == "COMPLETE":
            complete += 1
        else:
            missing += 1
    unmatched = len(set(menu_keys) - matched_keys)
    return {
        "matched": matched,
        "ambiguous": ambiguous,
        "matched_cost_complete": complete,
        "matched_cost_missing": missing,
        "unmatched_menus": unmatched,
        "why": (
            "Same normalised-name rule as Pack 8. "
            "Menus with no recipe, and matched recipes with no line cost, stay unmatched."
        ),
    }


def load_engineering() -> dict[str, Any]:
    recipes = _recipes()
    compare = _compare()
    mix = _mix()
    usage = _usage(mix.get("day") if mix.get("real") else None)
    join = (
        _join(recipes.get("cards") or [], mix.get("items") or [])
        if recipes.get("ok") and mix.get("real")
        else {
            "matched": None,
            "ambiguous": None,
            "matched_cost_complete": None,
            "matched_cost_missing": None,
            "unmatched_menus": None,
            "why": "Name join was not run because the recipe copy or the mix is missing.",
        }
    )
    public_recipes = {key: value for key, value in recipes.items() if key != "cards"}
    public_mix = {key: value for key, value in mix.items() if key != "items"}
    return {
        "ok": True,
        "pack": "WAVE2-04",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "scores_written": False,
        "state": "PARTIAL",
        "recipes": public_recipes,
        "recipe_compare": compare,
        "product_mix": public_mix,
        "name_join": join,
        "usage": usage,
        "contribution": {
            "state": "UNAVAILABLE",
            "margin_pct": None,
            "amount": None,
            "why": (
                "Usage is not joined to recipe lines. "
                "A margin from stored line cost and a mix amount would invent a score."
            ),
        },
        "quadrants": {
            "drawn": False,
            "stars": None,
            "plowhorses": None,
            "puzzles": None,
            "dogs": None,
            "why": "No contribution margin, so no class was assigned.",
        },
        "why": "Recipes and the ESB quantity mix are readable. Contribution and menu classes are unavailable.",
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "scores_written": False,
        "message": "Menu engineering does not write a margin, a class, or ESB.",
    }
