#!/usr/bin/env python3
"""Read-through projection of authorised Uma Blu history onto Beta.

UMAREAL-1. Historical stores stay where they are. This module opens them
mode=ro. The only write is a Wolf draft recipe version in a Beta sqlite,
and that draft never updates the historical recipe row.

ESB is not called. Alchemist is not written. No secret values are read.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
BETA_ROOT = Path(__file__).resolve().parents[2]
RECIPES_DB = Path.home() / ".openclaw" / "workspace" / "wolf-system" / "uma-blu" / "recipes.sqlite"
ALCHEMIST_DB = Path.home() / ".openclaw" / "workspace" / "alchemist" / "data" / "alchemist.db"
ESB_DB = Path.home() / ".openclaw" / "data" / "esb.sqlite"
NOTAS_DIR = Path.home() / ".openclaw" / "workspace" / "alchemist" / "notas"
INLINE_LOG = Path.home() / ".openclaw" / "logs" / "esb-inline.log"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
CLOSE_BACKUPS = BETA_ROOT / "catalog" / "backups"
ATRIUM_FINANCE_DB = (
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "atrium-finance" / "atrium_finance.sqlite"
)
DRAFT_DB = BETA_ROOT / "state" / "bzg" / "uma-recipe-drafts.sqlite"
REGISTER_JSON = BETA_ROOT / "state" / "bzg" / "data-source-register.json"
REGISTER_MD = BETA_ROOT / "docs" / "wolf" / "bzg" / "UMA-BLU-DATA-SOURCE-REGISTER.md"

BRANCH = "BLZ"
PROVENANCE_KEYS = (
    "source_system",
    "source_id",
    "source_timestamp",
    "import_timestamp",
    "verified_by_wolf",
    "origin",
)

_UNIT_TO_G = {"kg": 1000.0, "kilogram": 1000.0, "g": 1.0, "gr": 1.0, "gram": 1.0, "grams": 1.0}
_UNIT_TO_ML = {"l": 1000.0, "ltr": 1000.0, "liter": 1000.0, "litre": 1000.0, "ml": 1.0}
_PCS = {"pcs", "pc", "piece", "pieces", "ea", "each", "pax", "loaf", "pack"}
_PRICE_CACHE: dict[str, Any] | None = None
_MENU_CACHE: list[dict[str, Any]] | None = None

CUT_LINES = (
    {
        "domain": "recipes",
        "historical_source": "wolf-system uma-blu/recipes.sqlite",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "not commissioned — historical recipe store stays the record",
    },
    {
        "domain": "suppliers",
        "historical_source": "Alchemist suppliers",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (Alchemist)",
    },
    {
        "domain": "purchasing/PO",
        "historical_source": "Alchemist pr_orders",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (Alchemist)",
    },
    {
        "domain": "receiving",
        "historical_source": "Alchemist pr_receipt_lines",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (Alchemist)",
    },
    {
        "domain": "notas/evidence",
        "historical_source": "Alchemist notas directory and PO photo refs",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (Alchemist files)",
    },
    {
        "domain": "inventory",
        "historical_source": "Alchemist par_levels; ESB material_usage is usage history",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (ESB for stock; stock-branch not called)",
    },
    {
        "domain": "sales",
        "historical_source": "ESB warehouse esb.sqlite sales",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "external stays authoritative (ESB)",
    },
    {
        "domain": "daily close",
        "historical_source": "NONE FOUND",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "not commissioned — venue close module exists, no historical rows",
    },
    {
        "domain": "costs",
        "historical_source": "recipe card unit_cost plus Alchemist vendor last_price",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "not commissioned — card and Alchemist prices stay the record",
    },
    {
        "domain": "menu mapping",
        "historical_source": "no stored recipe-to-ESB map (recipes.esb_menu empty)",
        "wolf_commissioning_date": None,
        "wolf_authoritative_going_forward": "not commissioned — exact name match is a report, not a confirmed map unless 1:1",
    },
)


def now_iso() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def provenance(
    *,
    source_system: str,
    source_id: str,
    source_timestamp: str | None,
    import_timestamp: str | None,
    origin: str = "historical",
) -> dict[str, Any]:
    return {
        "source_system": source_system,
        "source_id": str(source_id),
        "source_timestamp": source_timestamp,
        "import_timestamp": import_timestamp,
        "verified_by_wolf": False,
        "origin": origin,
    }


def stamp(row: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    row.update(provenance(**kwargs))
    return row


def cut_lines() -> dict[str, Any]:
    return {
        "ok": True,
        "staff_ready": False,
        "human_commissioned": False,
        "banner": (
            "Historical source stays authoritative. Wolf commissioning date is not set. "
            "ESB stays authoritative for sales. Alchemist stays authoritative for purchasing."
        ),
        "cut_lines": [dict(row) for row in CUT_LINES],
    }


def _connect_ro(path: Path) -> sqlite3.Connection:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    conn = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _norm(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _unit_key(unit: str | None) -> str:
    raw = (unit or "").strip().lower().replace(".", "")
    if raw in _UNIT_TO_G:
        return "g"
    if raw in _UNIT_TO_ML:
        return "ml"
    if raw in _PCS:
        return raw or "pcs"
    return raw


def unit_cost_in(qty_unit: str | None, cost_per: float | None, cost_unit: str | None) -> float | None:
    """Cost of one recipe qty unit. None when the units do not convert."""
    if cost_per is None:
        return None
    qk, ck = _unit_key(qty_unit), _unit_key(cost_unit)
    if not qk or not ck or qk != ck:
        return None
    if qk == "g":
        qf = _UNIT_TO_G.get((qty_unit or "").strip().lower().replace(".", ""), 1.0)
        cf = _UNIT_TO_G.get((cost_unit or "").strip().lower().replace(".", ""), 1.0)
        return float(cost_per) * qf / cf
    if qk == "ml":
        qf = _UNIT_TO_ML.get((qty_unit or "").strip().lower().replace(".", ""), 1.0)
        cf = _UNIT_TO_ML.get((cost_unit or "").strip().lower().replace(".", ""), 1.0)
        return float(cost_per) * qf / cf
    return float(cost_per)


def rollup_food_cost(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """A missing line cost makes the dish total INCOMPLETE. No partial sum."""
    if not lines:
        return {"food_cost": None, "food_cost_status": "INCOMPLETE", "portion_cost": None}
    incomplete = False
    total = 0.0
    for line in lines:
        badge = line.get("cost_badge")
        extended = line.get("extended_cost")
        if badge in {"MISSING COST", "INCOMPLETE COST"} or extended is None:
            incomplete = True
            continue
        total += float(extended)
    if incomplete:
        return {"food_cost": None, "food_cost_status": "INCOMPLETE", "portion_cost": None}
    return {
        "food_cost": round(total, 4),
        "food_cost_status": "COMPLETE",
        "portion_cost": None,
    }


def _day(value: str | None) -> str:
    text = (value or "").strip()
    return text[:10] if len(text) >= 10 else text


def _price_index() -> dict[str, dict[str, Any]]:
    global _PRICE_CACHE
    if _PRICE_CACHE is not None:
        return _PRICE_CACHE
    index: dict[str, dict[str, Any]] = {}
    latest_order: dict[str, str] = {}
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        for row in conn.execute(
            """
            SELECT l.item AS item, MAX(o.order_date) AS order_date
            FROM pr_order_lines l
            JOIN pr_orders o ON o.id = l.pr_id
            GROUP BY l.item
            """
        ):
            key = _norm(row["item"])
            if key:
                latest_order[key] = row["order_date"] or ""
        for row in conn.execute(
            """
            SELECT vendor, item, unit, last_price, last_seen
            FROM pr_vendor_items
            WHERE last_price IS NOT NULL AND TRIM(CAST(last_price AS TEXT)) != ''
            """
        ):
            key = _norm(row["item"])
            if not key:
                continue
            hit = {
                "vendor": row["vendor"],
                "item": row["item"],
                "unit": row["unit"] or "",
                "last_price": float(row["last_price"]),
                "last_seen": row["last_seen"],
            }
            bucket = index.setdefault(key, {"hits": []})
            bucket["hits"].append(hit)
            bucket["latest_order_date"] = latest_order.get(key)
    finally:
        conn.close()
    _PRICE_CACHE = index
    return index


def _choose_price(name: str) -> dict[str, Any]:
    key = _norm(name)
    bucket = _price_index().get(key)
    if not bucket:
        return {
            "match_status": "unmatched",
            "match_method": None,
            "confidence": None,
            "unit_cost": None,
            "unit": None,
            "cost_date": None,
            "source_id": None,
        }
    hits = list(bucket["hits"])
    hits.sort(key=lambda item: (item.get("last_seen") or "", item.get("vendor") or ""))
    newest = hits[-1]["last_seen"] or ""
    tied = [hit for hit in hits if (hit.get("last_seen") or "") == newest]
    prices = {hit["last_price"] for hit in tied}
    if len(prices) != 1:
        return {
            "match_status": "ambiguous",
            "match_method": "alchemist_vendor_last_price_exact_name",
            "confidence": "not_confirmed",
            "unit_cost": None,
            "unit": None,
            "cost_date": newest or None,
            "source_id": None,
            "candidate_count": len(tied),
        }
    chosen = tied[-1]
    order_day = _day(bucket.get("latest_order_date"))
    cost_day = _day(chosen.get("last_seen"))
    stale = bool(order_day and cost_day and cost_day < order_day)
    return {
        "match_status": "matched",
        "match_method": "alchemist_vendor_last_price_exact_name",
        "confidence": "confirmed",
        "unit_cost": chosen["last_price"],
        "unit": chosen.get("unit") or "",
        "cost_date": chosen.get("last_seen"),
        "source_id": f"pr_vendor_items:{key}",
        "vendor": chosen.get("vendor"),
        "stale": stale,
        "latest_order_date": bucket.get("latest_order_date"),
    }


def _menus() -> list[dict[str, Any]]:
    global _MENU_CACHE
    if _MENU_CACHE is not None:
        return _MENU_CACHE
    conn = _connect_ro(ESB_DB)
    try:
        out = []
        for row in conn.execute("SELECT nk, raw, pulled_at FROM menus"):
            try:
                payload = json.loads(row["raw"] or "{}")
            except json.JSONDecodeError:
                continue
            name = (payload.get("menuName") or "").strip()
            if not name:
                continue
            prices = []
            for template in payload.get("menuTemplates") or []:
                if template.get("price") is not None:
                    prices.append(str(template.get("price")))
            out.append(
                {
                    "menu_id": str(payload.get("menuID") or row["nk"]),
                    "menu_code": payload.get("menuCode") or "",
                    "menu_name": name,
                    "norm": _norm(name),
                    "price": prices[0] if prices else None,
                    "pulled_at": row["pulled_at"],
                    "active": payload.get("flagActive"),
                }
            )
    finally:
        conn.close()
    _MENU_CACHE = out
    return out


def _recipe_rows() -> tuple[list[sqlite3.Row], dict[str, list[sqlite3.Row]]]:
    conn = _connect_ro(RECIPES_DB)
    try:
        recipes = list(conn.execute("SELECT * FROM recipes ORDER BY group_name, name COLLATE NOCASE"))
        lines: dict[str, list[sqlite3.Row]] = {}
        for row in conn.execute("SELECT * FROM recipe_lines ORDER BY recipe_id, sort, id"):
            lines.setdefault(row["recipe_id"], []).append(row)
    finally:
        conn.close()
    return recipes, lines


def _cost_line(recipe: sqlite3.Row, line: sqlite3.Row) -> dict[str, Any]:
    purchase = _choose_price(line["name"] or "")
    card_cost = line["unit_cost"]
    card_date = recipe["updated_at"]
    applied = None
    applied_unit = None
    cost_date = None
    stale = False
    badge = None
    method = purchase.get("match_method")
    confidence = purchase.get("confidence")
    match_status = purchase.get("match_status")
    if match_status == "matched":
        converted = unit_cost_in(line["unit"], purchase.get("unit_cost"), purchase.get("unit"))
        if converted is None:
            match_status = "unit_mismatch"
            confidence = "not_confirmed"
            method = purchase.get("match_method")
        else:
            applied = converted
            applied_unit = line["unit"]
            cost_date = purchase.get("cost_date")
            stale = bool(purchase.get("stale"))
    if applied is None and card_cost is not None:
        applied = float(card_cost)
        applied_unit = line["unit"]
        cost_date = card_date
        if match_status == "unit_mismatch":
            stale = True
        method = method or "recipe_card_unit_cost"
        if match_status == "unmatched":
            confidence = "card"
            method = "recipe_card_unit_cost"
    qty = line["qty"]
    extended = None
    if applied is None or qty is None:
        badge = "MISSING COST"
    else:
        extended = round(float(qty) * float(applied), 4)
        if stale:
            badge = "STALE"
    row = {
        "line_id": line["id"],
        "recipe_id": line["recipe_id"],
        "sort": line["sort"],
        "line_kind": line["line_kind"],
        "name": line["name"],
        "unit": line["unit"],
        "qty": qty,
        "card_unit_cost": card_cost,
        "card_cost_source": line["cost_source"],
        "applied_unit_cost": None if badge == "MISSING COST" else applied,
        "applied_unit": applied_unit,
        "extended_cost": None if badge == "MISSING COST" else extended,
        "cost_badge": badge,
        "cost_date": cost_date,
        "stale": stale,
        "subrecipe_id": line["subrecipe_id"],
        "purchase_match": {
            "match_status": match_status,
            "match_method": method if match_status != "unmatched" else None,
            "confidence": confidence if match_status != "unmatched" else None,
            "source_id": purchase.get("source_id"),
            "cost_date": purchase.get("cost_date"),
            "vendor": purchase.get("vendor"),
        },
    }
    return stamp(
        row,
        source_system="recipes.sqlite",
        source_id=f"recipe_lines:{line['id']}",
        source_timestamp=recipe["created_at"],
        import_timestamp=recipe["updated_at"] or recipe["created_at"],
    )


def _dish_payload(recipe: sqlite3.Row, lines: list[sqlite3.Row], *, drafts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    priced = [_cost_line(recipe, line) for line in lines if (line["name"] or "").strip()]
    rollup = rollup_food_cost(priced)
    yield_n = recipe["yield_n"]
    portion = None
    if rollup["food_cost"] is not None and yield_n:
        portion = round(float(rollup["food_cost"]) / float(yield_n), 4)
    sell = recipe["real_sell"]
    margin = None
    food_cost_pct = None
    if portion is not None and sell:
        margin = round(float(sell) - portion, 4)
        if float(sell) != 0:
            food_cost_pct = round(portion / float(sell) * 100.0, 4)
    status = rollup["food_cost_status"]
    if status != "COMPLETE":
        portion = None
        margin = None
        food_cost_pct = None
    row = {
        "recipe_id": recipe["id"],
        "name": recipe["name"],
        "kind": recipe["kind"],
        "group_name": recipe["group_name"],
        "status": recipe["status"],
        "recipe_source": recipe["source"],
        "yield_n": yield_n,
        "yield_unit": recipe["yield_unit"],
        "target_cos": recipe["target_cos"],
        "real_sell": sell,
        "esb_menu_stored": (recipe["esb_menu"] or "").strip() or None,
        "line_count": len(priced),
        "missing_cost_lines": sum(1 for line in priced if line.get("cost_badge") == "MISSING COST"),
        "food_cost": rollup["food_cost"] if status == "COMPLETE" else None,
        "food_cost_status": status if status == "COMPLETE" else "INCOMPLETE",
        "portion_cost": portion,
        "margin": margin,
        "food_cost_pct": food_cost_pct,
        "historical_version": {
            "version": recipe["source"] or "historical",
            "origin": "historical",
            "verified_by_wolf": False,
        },
        "drafts": drafts or [],
        "lines": priced,
        "staff_ready": False,
        "human_commissioned": False,
        "label": "THEORETICAL" if False else None,
    }
    return stamp(
        row,
        source_system="recipes.sqlite",
        source_id=f"recipes:{recipe['id']}",
        source_timestamp=recipe["created_at"],
        import_timestamp=recipe["updated_at"] or recipe["created_at"],
    )


def list_recipes(*, limit: int = 40, offset: int = 0) -> dict[str, Any]:
    recipes, lines = _recipe_rows()
    start = max(0, int(offset))
    size = max(1, min(int(limit), 200))
    page = []
    for recipe in recipes[start : start + size]:
        dish = _dish_payload(recipe, lines.get(recipe["id"], []))
        dish.pop("lines", None)
        page.append(dish)
    return {
        "ok": True,
        "count": len(recipes),
        "offset": start,
        "limit": size,
        "example_rows_included": False,
        "staff_ready": False,
        "human_commissioned": False,
        "banner": cut_lines()["banner"],
        "recipes": page,
    }


def get_recipe(recipe_id: str) -> dict[str, Any] | None:
    recipes, lines = _recipe_rows()
    found = next((row for row in recipes if row["id"] == recipe_id), None)
    if found is None:
        return None
    return _dish_payload(found, lines.get(found["id"], []), drafts=list_drafts(recipe_id))


def draft_db_path() -> Path:
    raw = (os.environ.get("UMA_REAL_DRAFT_DB") or "").strip()
    return Path(raw).expanduser() if raw else DRAFT_DB


def _draft_conn() -> sqlite3.Connection:
    path = draft_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recipe_drafts (
          draft_id TEXT PRIMARY KEY,
          recipe_id TEXT NOT NULL,
          version_n INTEGER NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL,
          created_by TEXT,
          source_system TEXT NOT NULL,
          source_id TEXT NOT NULL,
          source_timestamp TEXT,
          import_timestamp TEXT NOT NULL,
          verified_by_wolf INTEGER NOT NULL,
          origin TEXT NOT NULL
        )
        """
    )
    return conn


def list_drafts(recipe_id: str) -> list[dict[str, Any]]:
    if not draft_db_path().is_file() and not (os.environ.get("UMA_REAL_DRAFT_DB") or "").strip():
        return []
    conn = _draft_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM recipe_drafts
            WHERE recipe_id=?
            ORDER BY version_n
            """,
            (recipe_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) | {"verified_by_wolf": False, "origin": "wolf_draft"} for row in rows]


def create_draft(recipe_id: str, note: str, *, created_by: str | None) -> dict[str, Any]:
    """Insert a Wolf draft. Does not open the historical recipe database for write."""
    if get_recipe(recipe_id) is None:
        raise KeyError(recipe_id)
    conn = _draft_conn()
    try:
        current = conn.execute(
            "SELECT COALESCE(MAX(version_n), 0) FROM recipe_drafts WHERE recipe_id=?",
            (recipe_id,),
        ).fetchone()[0]
        version_n = int(current) + 1
        draft_id = f"UMADRAFT-{uuid.uuid4().hex[:12]}"
        created = now_iso()
        conn.execute(
            """
            INSERT INTO recipe_drafts (
              draft_id, recipe_id, version_n, note, created_at, created_by,
              source_system, source_id, source_timestamp, import_timestamp,
              verified_by_wolf, origin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'wolf_draft')
            """,
            (
                draft_id,
                recipe_id,
                version_n,
                (note or "").strip()[:500],
                created,
                created_by,
                "wolf-beta",
                draft_id,
                created,
                created,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return stamp(
        {
            "draft_id": draft_id,
            "recipe_id": recipe_id,
            "version_n": version_n,
            "note": (note or "").strip()[:500],
            "staff_ready": False,
            "human_commissioned": False,
            "historical_overwritten": False,
        },
        source_system="wolf-beta",
        source_id=draft_id,
        source_timestamp=created,
        import_timestamp=created,
        origin="wolf_draft",
    )


def list_suppliers(*, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, name, location_id, order_method, nota_type, cod, delivery_days, payment_terms
            FROM suppliers
            ORDER BY name COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            (max(1, min(int(limit), 500)), max(0, int(offset))),
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        items.append(
            stamp(
                {
                    "supplier_id": row["id"],
                    "name": row["name"],
                    "location_id": row["location_id"],
                    "order_method": row["order_method"],
                    "nota_type": row["nota_type"],
                    "label": "Alchemist historical",
                },
                source_system="alchemist.db",
                source_id=f"suppliers:{row['id']}",
                source_timestamp=None,
                import_timestamp=None,
            )
        )
    return {
        "ok": True,
        "count": total,
        "example_rows_included": False,
        "label": "Alchemist historical",
        "banner": cut_lines()["banner"],
        "staff_ready": False,
        "human_commissioned": False,
        "suppliers": items,
    }


def list_orders(*, limit: int = 40, offset: int = 0) -> dict[str, Any]:
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM pr_orders").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, pr_num, department, requested_by, vendor, order_date, status,
                   created_at, invoice_total, receipt_photo_url
            FROM pr_orders
            ORDER BY COALESCE(created_at, order_date) DESC
            LIMIT ? OFFSET ?
            """,
            (max(1, min(int(limit), 200)), max(0, int(offset))),
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        photo = (row["receipt_photo_url"] or "").strip()
        drive = _drive_id(photo)
        items.append(
            stamp(
                {
                    "order_id": row["id"],
                    "pr_num": row["pr_num"],
                    "department": row["department"],
                    "requested_by": row["requested_by"],
                    "vendor": row["vendor"],
                    "order_date": row["order_date"],
                    "status": row["status"],
                    "invoice_total": row["invoice_total"],
                    "label": "Alchemist historical",
                    "photo": {
                        "recoverable": False,
                        "source_path_id": drive,
                        "message": "EVIDENCE FILE NOT RECOVERABLE" if drive else None,
                    },
                },
                source_system="alchemist.db",
                source_id=f"pr_orders:{row['id']}",
                source_timestamp=row["created_at"] or row["order_date"],
                import_timestamp=row["created_at"],
            )
        )
    return {
        "ok": True,
        "count": total,
        "offset": max(0, int(offset)),
        "example_rows_included": False,
        "label": "Alchemist historical",
        "banner": cut_lines()["banner"],
        "staff_ready": False,
        "human_commissioned": False,
        "orders": items,
    }


def list_receipts(*, limit: int = 40, offset: int = 0) -> dict[str, Any]:
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM pr_receipt_lines").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, pr_id, line_no, item_raw, qty, unit, line_price, match_confidence, source
            FROM pr_receipt_lines
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (max(1, min(int(limit), 200)), max(0, int(offset))),
        ).fetchall()
    finally:
        conn.close()
    items = [
        stamp(
            {
                "receipt_line_id": row["id"],
                "pr_id": row["pr_id"],
                "line_no": row["line_no"],
                "item_raw": row["item_raw"],
                "qty": row["qty"],
                "unit": row["unit"],
                "line_price": row["line_price"],
                "match_confidence": row["match_confidence"],
                "label": "Alchemist historical",
            },
            source_system="alchemist.db",
            source_id=f"pr_receipt_lines:{row['id']}",
            source_timestamp=None,
            import_timestamp=None,
        )
        for row in rows
    ]
    return {
        "ok": True,
        "count": total,
        "example_rows_included": False,
        "label": "Alchemist historical",
        "staff_ready": False,
        "human_commissioned": False,
        "receipts": items,
    }


def _drive_id(url: str) -> str | None:
    match = re.search(r"/d/([A-Za-z0-9_-]+)", url or "")
    if not match:
        return None
    return f"drive:{match.group(1)}"


def _evidence_files() -> list[Path]:
    if not NOTAS_DIR.is_dir():
        return []
    return sorted(path for path in NOTAS_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".jpg")


def list_evidence(*, limit: int = 40, offset: int = 0) -> dict[str, Any]:
    files = _evidence_files()
    start = max(0, int(offset))
    size = max(1, min(int(limit), 200))
    items = []
    for path in files[start : start + size]:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, WITA).isoformat(timespec="seconds")
        items.append(
            stamp(
                {
                    "evidence_id": path.name,
                    "prefix": path.name.split("_", 1)[0],
                    "recoverable": True,
                    "message": None,
                    "label": "Alchemist historical",
                },
                source_system="alchemist/notas",
                source_id=path.name,
                source_timestamp=mtime,
                import_timestamp=mtime,
            )
        )
    drive_rows = _unrecoverable_drive_refs(limit=20)
    return {
        "ok": True,
        "count": len(files),
        "prefix_counts": _prefix_counts(files),
        "example_rows_included": False,
        "label": "Alchemist historical",
        "staff_ready": False,
        "human_commissioned": False,
        "files": items,
        "unrecoverable": drive_rows,
    }


def _prefix_counts(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        prefix = path.name.split("_", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def _unrecoverable_drive_refs(*, limit: int) -> list[dict[str, Any]]:
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        rows = conn.execute(
            """
            SELECT id, pr_num, receipt_photo_url, created_at
            FROM pr_orders
            WHERE receipt_photo_url IS NOT NULL AND TRIM(receipt_photo_url) != ''
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        total = conn.execute(
            """
            SELECT COUNT(*) FROM pr_orders
            WHERE receipt_photo_url IS NOT NULL AND TRIM(receipt_photo_url) != ''
            """
        ).fetchone()[0]
    finally:
        conn.close()
    items = []
    for row in rows:
        source_id = _drive_id(row["receipt_photo_url"]) or f"pr_orders:{row['id']}:photo"
        items.append(
            stamp(
                {
                    "evidence_id": source_id,
                    "pr_num": row["pr_num"],
                    "recoverable": False,
                    "message": "EVIDENCE FILE NOT RECOVERABLE",
                    "label": "Alchemist historical",
                },
                source_system="alchemist.db",
                source_id=source_id,
                source_timestamp=row["created_at"],
                import_timestamp=row["created_at"],
            )
        )
    return items


def resolve_evidence_file(evidence_id: str) -> Path | None:
    name = Path(evidence_id or "").name
    if not name or name != evidence_id or name.startswith("."):
        return None
    root = NOTAS_DIR.resolve()
    target = (root / name).resolve()
    if target.parent != root or not target.is_file():
        return None
    if target.suffix.lower() != ".jpg":
        return None
    return target


def evidence_meta(evidence_id: str) -> dict[str, Any]:
    path = resolve_evidence_file(evidence_id)
    if path is None:
        return stamp(
            {
                "ok": True,
                "evidence_id": evidence_id,
                "recoverable": False,
                "message": "EVIDENCE FILE NOT RECOVERABLE",
                "label": "Alchemist historical",
                "staff_ready": False,
                "human_commissioned": False,
            },
            source_system="alchemist/notas",
            source_id=evidence_id,
            source_timestamp=None,
            import_timestamp=None,
        )
    mtime = datetime.fromtimestamp(path.stat().st_mtime, WITA).isoformat(timespec="seconds")
    return stamp(
        {
            "ok": True,
            "evidence_id": path.name,
            "recoverable": True,
            "message": None,
            "prefix": path.name.split("_", 1)[0],
            "label": "Alchemist historical",
            "staff_ready": False,
            "human_commissioned": False,
        },
        source_system="alchemist/notas",
        source_id=path.name,
        source_timestamp=mtime,
        import_timestamp=mtime,
    )


def _inline_status() -> dict[str, Any]:
    """Read the existing inline log. Does not call ESB."""
    if not INLINE_LOG.is_file():
        return {"inline_log": "missing", "inline_call_issued": False}
    last = ""
    try:
        lines = INLINE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {"inline_log": "unreadable", "inline_call_issued": False}
    for line in reversed(lines):
        if "daily(" in line and " OK " in line:
            last = line.strip()
            break
    match = re.search(r"daily\((\d{4}-\d{2}-\d{2})\) OK", last)
    bills = re.search(r"bills=(\d+)", last)
    covers = re.search(r"covers=(\d+)", last)
    stamp_match = re.match(r"^(\S+)", last)
    return {
        "inline_call_issued": False,
        "inline_log_last_biz_date": match.group(1) if match else None,
        "inline_log_bills": int(bills.group(1)) if bills else None,
        "inline_log_covers": int(covers.group(1)) if covers else None,
        "inline_log_at": stamp_match.group(1) if stamp_match else None,
    }


def list_sales(*, date_from: str | None = None, date_to: str | None = None, limit: int = 30) -> dict[str, Any]:
    conn = _connect_ro(ESB_DB)
    try:
        bounds = conn.execute("SELECT MIN(biz_date), MAX(biz_date), COUNT(*) FROM sales").fetchone()
        clauses = ["1=1"]
        args: list[Any] = []
        if date_from:
            clauses.append("biz_date>=?")
            args.append(date_from)
        if date_to:
            clauses.append("biz_date<=?")
            args.append(date_to)
        where = " AND ".join(clauses)
        total = conn.execute(f"SELECT COUNT(*) FROM sales WHERE {where}", args).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT nk, biz_date, raw, pulled_at
            FROM sales
            WHERE {where}
            ORDER BY biz_date DESC, nk DESC
            LIMIT ?
            """,
            [*args, max(1, min(int(limit), 100))],
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        try:
            bill = json.loads(row["raw"] or "{}")
        except json.JSONDecodeError:
            bill = {}
        menus = []
        for menu in (bill.get("salesMenus") or [])[:12]:
            menus.append(
                {
                    "menu_name": menu.get("menuName"),
                    "qty": menu.get("qty"),
                    "menu_id": menu.get("menuID"),
                }
            )
        items.append(
            stamp(
                {
                    "sales_num": bill.get("salesNum"),
                    "biz_date": row["biz_date"],
                    "branch_code": bill.get("branchCode"),
                    "status": bill.get("statusName"),
                    "grand_total": bill.get("grandTotal"),
                    "pax_total": bill.get("paxTotal"),
                    "menus": menus,
                    "label": "ESB read-only",
                },
                source_system="esb.sqlite",
                source_id=f"sales:{row['nk']}",
                source_timestamp=bill.get("salesDate") or row["biz_date"],
                import_timestamp=row["pulled_at"],
            )
        )
    payload = {
        "ok": True,
        "count": bounds[2],
        "filtered_count": total,
        "biz_date_min": bounds[0],
        "biz_date_max": bounds[1],
        "example_rows_included": False,
        "banner": cut_lines()["banner"],
        "staff_ready": False,
        "human_commissioned": False,
        "sales": items,
    }
    payload.update(_inline_status())
    return payload


def menu_map_report() -> dict[str, Any]:
    recipes, _lines = _recipe_rows()
    menus = _menus()
    by_menu: dict[str, list[dict[str, Any]]] = {}
    for menu in menus:
        by_menu.setdefault(menu["norm"], []).append(menu)
    by_recipe: dict[str, list[sqlite3.Row]] = {}
    for recipe in recipes:
        by_recipe.setdefault(_norm(recipe["name"]), []).append(recipe)
    mapped = []
    ambiguous = []
    recipes_without = []
    used_menu_norms: set[str] = set()
    for recipe in recipes:
        key = _norm(recipe["name"])
        menu_hits = by_menu.get(key) or []
        recipe_hits = by_recipe.get(key) or []
        if not menu_hits:
            recipes_without.append(
                stamp(
                    {"recipe_id": recipe["id"], "name": recipe["name"], "map_status": "no_esb_item"},
                    source_system="recipes.sqlite",
                    source_id=f"recipes:{recipe['id']}",
                    source_timestamp=recipe["created_at"],
                    import_timestamp=recipe["updated_at"] or recipe["created_at"],
                )
            )
            continue
        used_menu_norms.add(key)
        confirmed = len(menu_hits) == 1 and len(recipe_hits) == 1
        row = stamp(
            {
                "recipe_id": recipe["id"],
                "recipe_name": recipe["name"],
                "menu_names": [item["menu_name"] for item in menu_hits],
                "menu_ids": [item["menu_id"] for item in menu_hits],
                "match_method": "exact_normalised_name",
                "confidence": "confirmed" if confirmed else "not_confirmed",
                "map_status": "mapped" if confirmed else "ambiguous",
            },
            source_system="recipes.sqlite+esb.sqlite",
            source_id=f"map:{recipe['id']}",
            source_timestamp=recipe["created_at"],
            import_timestamp=menu_hits[0]["pulled_at"],
        )
        if confirmed:
            mapped.append(row)
        else:
            ambiguous.append(row)
    unmapped_esb = []
    for menu in menus:
        if menu["norm"] in used_menu_norms:
            continue
        unmapped_esb.append(
            stamp(
                {
                    "menu_id": menu["menu_id"],
                    "menu_name": menu["menu_name"],
                    "map_status": "unmapped_esb",
                    "confidence": None,
                },
                source_system="esb.sqlite",
                source_id=f"menus:{menu['menu_id']}",
                source_timestamp=None,
                import_timestamp=menu["pulled_at"],
            )
        )
    return {
        "ok": True,
        "match_method": "exact_normalised_name",
        "guessed_confirmed": 0,
        "mapped": len(mapped),
        "ambiguous": len(ambiguous),
        "recipes_without_esb_item": len(recipes_without),
        "unmapped_esb_items": len(unmapped_esb),
        "menu_count": len(menus),
        "recipe_count": len(recipes),
        "stored_esb_menu_links": sum(1 for recipe in recipes if (recipe["esb_menu"] or "").strip()),
        "mapped_rows": mapped,
        "ambiguous_rows": ambiguous,
        "recipes_without_rows": recipes_without,
        "unmapped_esb_rows": unmapped_esb,
        "banner": cut_lines()["banner"],
        "staff_ready": False,
        "human_commissioned": False,
    }


def theoretical_consumption(*, date_from: str, date_to: str) -> dict[str, Any]:
    report = menu_map_report()
    confirmed = {
        _norm(row["recipe_name"]): row["recipe_id"]
        for row in report["mapped_rows"]
        if row.get("confidence") == "confirmed"
    }
    _recipes, line_map = _recipe_rows()
    conn = _connect_ro(ESB_DB)
    try:
        rows = conn.execute(
            """
            SELECT nk, biz_date, raw, pulled_at
            FROM sales
            WHERE biz_date>=? AND biz_date<=?
            """,
            (date_from, date_to),
        ).fetchall()
    finally:
        conn.close()
    usage: dict[str, dict[str, Any]] = {}
    sold_unmapped: dict[str, float] = {}
    bills = 0
    for row in rows:
        try:
            bill = json.loads(row["raw"] or "{}")
        except json.JSONDecodeError:
            continue
        if (bill.get("branchCode") or "").strip().upper() != BRANCH:
            continue
        if (bill.get("statusName") or "").strip() != "Finished":
            continue
        bills += 1
        for menu in bill.get("salesMenus") or []:
            name = menu.get("menuName") or ""
            qty = menu.get("qty")
            try:
                qty_n = float(qty)
            except (TypeError, ValueError):
                continue
            recipe_id = confirmed.get(_norm(name))
            if not recipe_id:
                sold_unmapped[name] = sold_unmapped.get(name, 0.0) + qty_n
                continue
            for line in line_map.get(recipe_id, []):
                ingredient = line["name"] or ""
                line_qty = line["qty"]
                if line_qty is None:
                    continue
                key = f"{ingredient}|{line['unit'] or ''}"
                bucket = usage.setdefault(
                    key,
                    {
                        "ingredient": ingredient,
                        "unit": line["unit"],
                        "qty": 0.0,
                        "label": "THEORETICAL",
                    },
                )
                bucket["qty"] = round(bucket["qty"] + qty_n * float(line_qty), 4)
    lines = []
    for bucket in sorted(usage.values(), key=lambda item: item["ingredient"].lower()):
        lines.append(
            stamp(
                bucket,
                source_system="esb.sqlite*recipes.sqlite",
                source_id=f"theoretical:{date_from}:{date_to}:{_norm(bucket['ingredient'])}",
                source_timestamp=date_from,
                import_timestamp=date_to,
            )
        )
    return {
        "ok": True,
        "label": "THEORETICAL",
        "date_from": date_from,
        "date_to": date_to,
        "finished_bills": bills,
        "mapped_menu_items_used": len(confirmed),
        "lines": lines,
        "unmapped_qty": [
            stamp(
                {"menu_name": name, "qty": qty, "label": "THEORETICAL", "map_status": "unmapped"},
                source_system="esb.sqlite",
                source_id=f"theoretical-unmapped:{date_from}:{date_to}:{_norm(name) or 'blank'}",
                source_timestamp=date_from,
                import_timestamp=date_to,
            )
            for name, qty in sorted(sold_unmapped.items())
        ],
        "staff_ready": False,
        "human_commissioned": False,
        "banner": cut_lines()["banner"],
    }


def _table_count(path: Path, table: str) -> int | None:
    if not path.is_file():
        return None
    try:
        conn = _connect_ro(path)
    except (OSError, sqlite3.Error):
        return None
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if table not in names:
            return None
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    finally:
        conn.close()


def daily_close_history() -> dict[str, Any]:
    searched = []
    live = _table_count(CATALOG_DB, "venue_daily_closes")
    searched.append({"where": str(CATALOG_DB), "table": "venue_daily_closes", "count": live})
    policies = _table_count(CATALOG_DB, "venue_close_variance_policies")
    searched.append({"where": str(CATALOG_DB), "table": "venue_close_variance_policies", "count": policies})
    cash = _table_count(ALCHEMIST_DB, "cash_count")
    searched.append({"where": str(ALCHEMIST_DB), "table": "cash_count", "count": cash})
    deliveries = _table_count(ALCHEMIST_DB, "deliveries")
    searched.append({"where": str(ALCHEMIST_DB), "table": "deliveries", "count": deliveries})
    atrium = _table_count(ATRIUM_FINANCE_DB, "close_checklist_item")
    searched.append(
        {
            "where": str(ATRIUM_FINANCE_DB),
            "table": "close_checklist_item",
            "count": atrium,
            "excluded": "hotel finance checklist, not an Uma Blu daily close",
        }
    )
    backup_counts = []
    if CLOSE_BACKUPS.is_dir():
        for path in sorted(CLOSE_BACKUPS.glob("pre-uma-blu-daily-close-*.sqlite")):
            count = _table_count(path, "venue_daily_closes")
            backup_counts.append(count)
    searched.append(
        {
            "where": str(CLOSE_BACKUPS),
            "table": "venue_daily_closes",
            "files": len(backup_counts),
            "count": sum(item or 0 for item in backup_counts),
        }
    )
    uma_rows = (live or 0) + (cash or 0) + sum(item or 0 for item in backup_counts)
    return {
        "ok": True,
        "status": "NONE FOUND" if uma_rows == 0 else "FOUND",
        "rows": [],
        "policy": "NONE — no variance threshold is stored. Matt decides.",
        "threshold": None,
        "searched": searched,
        "staff_ready": False,
        "human_commissioned": False,
        "banner": cut_lines()["banner"],
    }


def list_inventory() -> dict[str, Any]:
    conn = _connect_ro(ALCHEMIST_DB)
    try:
        rows = conn.execute(
            "SELECT id, item_name, location_id, par_qty, unit FROM par_levels ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    esb = _connect_ro(ESB_DB)
    try:
        usage = esb.execute("SELECT COUNT(*), MIN(biz_date), MAX(biz_date) FROM material_usage").fetchone()
        products = esb.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        goods = esb.execute("SELECT COUNT(*) FROM goods_receipts").fetchone()[0]
    finally:
        esb.close()
    items = [
        stamp(
            {
                "par_id": row["id"],
                "item_name": row["item_name"],
                "par_qty": row["par_qty"],
                "unit": row["unit"],
                "on_hand": None,
                "label": "par level — not an on-hand count",
            },
            source_system="alchemist.db",
            source_id=f"par_levels:{row['id']}",
            source_timestamp=None,
            import_timestamp=None,
        )
        for row in rows
    ]
    return {
        "ok": True,
        "par_count": len(items),
        "material_usage_count": usage[0],
        "material_usage_from": usage[1],
        "material_usage_to": usage[2],
        "products": products,
        "goods_receipts": goods,
        "stock_branch_called": False,
        "items": items,
        "staff_ready": False,
        "human_commissioned": False,
    }


def _count(path: Path, sql: str) -> int:
    conn = _connect_ro(path)
    try:
        return int(conn.execute(sql).fetchone()[0])
    finally:
        conn.close()


def dataset_rows() -> list[dict[str, Any]]:
    """One register row per dataset. Counts are live query results."""
    files = _evidence_files()
    prefixes = _prefix_counts(files)
    sales_bounds = None
    esb = _connect_ro(ESB_DB)
    try:
        sales_bounds = esb.execute("SELECT MIN(biz_date), MAX(biz_date) FROM sales").fetchone()
        menu_pulled = esb.execute("SELECT MIN(pulled_at), MAX(pulled_at) FROM menus").fetchone()
        mu = esb.execute("SELECT MIN(biz_date), MAX(biz_date) FROM material_usage").fetchone()
        gl = esb.execute("SELECT MIN(biz_date), MAX(biz_date) FROM gl_journal").fetchone()
        sms = esb.execute("SELECT MIN(biz_date), MAX(biz_date) FROM sales_menu_summary").fetchone()
    finally:
        esb.close()
    alc = _connect_ro(ALCHEMIST_DB)
    try:
        pr_dates = alc.execute("SELECT MIN(order_date), MAX(order_date) FROM pr_orders").fetchone()
        ledger_dates = alc.execute("SELECT MIN(invoice_date), MAX(invoice_date) FROM ledger").fetchone()
        petty_dates = alc.execute("SELECT MIN(entry_date), MAX(entry_date) FROM petty_cash").fetchone()
        drive_n = alc.execute(
            "SELECT COUNT(*) FROM pr_orders WHERE receipt_photo_url IS NOT NULL AND TRIM(receipt_photo_url)!=''"
        ).fetchone()[0]
        vendor_price_blank = alc.execute(
            "SELECT COUNT(*) FROM pr_vendor_items WHERE last_price IS NULL OR TRIM(CAST(last_price AS TEXT))=''"
        ).fetchone()[0]
    finally:
        alc.close()
    rec = _connect_ro(RECIPES_DB)
    try:
        rec_dates = rec.execute("SELECT MIN(created_at), MAX(updated_at) FROM recipes").fetchone()
    finally:
        rec.close()
    closes = daily_close_history()
    imported = now_iso()

    def row(**kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("read_access_verified", "y")
        kwargs.setdefault("read_access_how", "sqlite mode=ro query_only")
        kwargs["provenance"] = "source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical"
        return kwargs

    nota_count = len(files)
    return [
        row(
            source="wolf-system/uma-blu/recipes.sqlite recipes",
            contains="Uma Blu dishes",
            date_range=f"{rec_dates[0]} .. {rec_dates[1]}",
            record_count=_count(RECIPES_DB, "SELECT COUNT(*) FROM recipes"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="read-through; costing badges; no rewrite",
            conflicts="1 archived dish; esb_menu column empty on every row",
        ),
        row(
            source="wolf-system/uma-blu/recipes.sqlite recipe_lines",
            contains="ingredient lines",
            date_range=f"{rec_dates[0]} .. {rec_dates[1]}",
            record_count=_count(RECIPES_DB, "SELECT COUNT(*) FROM recipe_lines"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="unit conversion g/ml only; missing unit_cost stays MISSING COST",
            conflicts=f"null unit_cost {_count(RECIPES_DB, 'SELECT COUNT(*) FROM recipe_lines WHERE unit_cost IS NULL')}; subrecipe_id 0; cost_source null {_count(RECIPES_DB, 'SELECT COUNT(*) FROM recipe_lines WHERE cost_source IS NULL')}",
        ),
        row(
            source="wolf-system/uma-blu/recipes.sqlite recipe_compare",
            contains="stored actual-versus-target rows",
            date_range="n/a",
            record_count=_count(RECIPES_DB, "SELECT COUNT(*) FROM recipe_compare"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none — empty",
            conflicts="empty; margin is calculated at read time, not stored here",
        ),
        row(
            source="alchemist.db suppliers",
            contains="supplier names",
            date_range="n/a — no created_at column",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM suppliers"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="read-through, label Alchemist historical",
            conflicts="contact column not projected; location_id null on part of the table",
        ),
        row(
            source="alchemist.db pr_orders",
            contains="purchase orders",
            date_range=f"{pr_dates[0]} .. {pr_dates[1]}",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_orders"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="read-through; example Beta PRs are not included",
            conflicts=f"{drive_n} rows point at a Drive photo that is not a local file",
        ),
        row(
            source="alchemist.db pr_order_lines",
            contains="PO lines",
            date_range=f"{pr_dates[0]} .. {pr_dates[1]}",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_order_lines"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="names used for stale-price dates only",
            conflicts="price column is null on every row",
        ),
        row(
            source="alchemist.db pr_receipt_lines",
            contains="receipt lines",
            date_range="no date column; parent PO dates apply",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_receipt_lines"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="shown as receipt evidence; not used as a confirmed unit cost",
            conflicts="item_raw is an unparsed nota line; line_price is a line total; 30 rows have null line_price",
        ),
        row(
            source="alchemist.db pr_vendor_items",
            contains="vendor item last price",
            date_range="last_seen on the row",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_vendor_items"),
            role="REFERENCE",
            safe_to_project="y",
            transformation="exact normalised name match only",
            conflicts=f"last_price empty on {vendor_price_blank} rows",
        ),
        row(
            source="alchemist/notas jpg files",
            contains="local evidence photos",
            date_range="file mtime",
            record_count=nota_count,
            role="HISTORICAL",
            safe_to_project="y",
            read_access_how="directory listing, files opened only by exact filename under the notas directory",
            transformation="serve the file if it resolves; otherwise EVIDENCE FILE NOT RECOVERABLE",
            conflicts=f"prefixes {prefixes}; earlier note said 448 jpg; this query counted {nota_count}",
        ),
        row(
            source="alchemist.db pr_orders receipt_photo_url",
            contains="Drive photo references",
            date_range=f"{pr_dates[0]} .. {pr_dates[1]}",
            record_count=int(drive_n),
            role="HISTORICAL",
            safe_to_project="y",
            transformation="source path id only; file not fetched",
            conflicts="not on local disk",
        ),
        row(
            source="alchemist.db ledger",
            contains="supplier bills",
            date_range=f"{ledger_dates[0]} .. {ledger_dates[1]}",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM ledger"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="counted; bill page already reads Alchemist via the existing projection",
            conflicts="deliveries table is 0 so ledger.delivery_id does not join a delivery row",
        ),
        row(
            source="alchemist.db petty_cash",
            contains="petty movements",
            date_range=f"{petty_dates[0]} .. {petty_dates[1]}",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM petty_cash"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="existing Beta petty projection",
            conflicts="none found in this count",
        ),
        row(
            source="alchemist.db par_levels",
            contains="par quantities",
            date_range="n/a",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM par_levels"),
            role="REFERENCE",
            safe_to_project="y",
            transformation="shown as par, not on-hand",
            conflicts="no on-hand column",
        ),
        row(
            source="alchemist.db cash_count",
            contains="cash counts",
            date_range="n/a",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM cash_count"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none — empty",
            conflicts="empty",
        ),
        row(
            source="alchemist.db unit_map",
            contains="unit conversions",
            date_range="n/a",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM unit_map"),
            role="REFERENCE",
            safe_to_project="n",
            transformation="none — empty; g/ml map is code",
            conflicts="empty",
        ),
        row(
            source="alchemist.db item_prices",
            contains="item price history",
            date_range="n/a",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM item_prices"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none — empty",
            conflicts="empty; prices live on pr_vendor_items.last_price",
        ),
        row(
            source="alchemist.db deliveries",
            contains="structured deliveries",
            date_range="n/a",
            record_count=_count(ALCHEMIST_DB, "SELECT COUNT(*) FROM deliveries"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none — empty",
            conflicts="empty while receipt lines and photos exist",
        ),
        row(
            source="esb.sqlite sales",
            contains="ESB bills",
            date_range=f"{sales_bounds[0]} .. {sales_bounds[1]}",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM sales"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="read-through; customer phone, email, and member fields are not projected",
            conflicts="warehouse max biz_date is 2026-09-27; inline log latest OK day is the same; no new ESB call",
        ),
        row(
            source="esb.sqlite menus",
            contains="ESB menu master",
            date_range=f"{menu_pulled[0]} .. {menu_pulled[1]}",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM menus"),
            role="AUTHORITATIVE",
            safe_to_project="y",
            transformation="exact normalised name match to recipes",
            conflicts="recipes.esb_menu is empty, so there is no stored confirmed link",
        ),
        row(
            source="esb.sqlite products",
            contains="ESB products",
            date_range="pulled_at on the row",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM products"),
            role="REFERENCE",
            safe_to_project="y",
            transformation="count only in this pack",
            conflicts="goods_receipts is 0 so product price is not a receipt price",
        ),
        row(
            source="esb.sqlite material_usage",
            contains="ESB material usage",
            date_range=f"{mu[0]} .. {mu[1]}",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM material_usage"),
            role="REFERENCE",
            safe_to_project="y",
            transformation="count only; theoretical consumption is calculated from sales x recipe lines",
            conflicts="not a stock-on-hand figure",
        ),
        row(
            source="esb.sqlite goods_receipts",
            contains="ESB goods receipts",
            date_range="n/a",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM goods_receipts"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none — empty",
            conflicts="empty; Felix 19 Jul said goods receipt is ERP-only",
        ),
        row(
            source="esb.sqlite gl_journal",
            contains="ESB journal",
            date_range=f"{gl[0]} .. {gl[1]}",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM gl_journal"),
            role="REFERENCE",
            safe_to_project="n",
            transformation="counted only; not a Beta finance book",
            conflicts="not opened as Atrium books",
        ),
        row(
            source="esb.sqlite sales_menu_summary",
            contains="ESB menu sales summary",
            date_range=f"{sms[0]} .. {sms[1]}",
            record_count=_count(ESB_DB, "SELECT COUNT(*) FROM sales_menu_summary"),
            role="REFERENCE",
            safe_to_project="y",
            transformation="count only; line qty comes from sales.raw",
            conflicts="summary is not the bill line",
        ),
        row(
            source="catalog content_library.sqlite bzg_ops_purchase_requests example=1",
            contains="Beta example purchase requests",
            date_range="2026-09-18",
            record_count=_count(CATALOG_DB, "SELECT COUNT(*) FROM bzg_ops_purchase_requests WHERE example=1"),
            role="HISTORICAL",
            safe_to_project="n",
            read_access_how="sqlite mode=ro",
            transformation="kept as fixtures; excluded from operational projection",
            conflicts="must not render as real Uma Blu purchasing",
        ),
        row(
            source="catalog content_library.sqlite venue_daily_closes",
            contains="Uma Blu daily close rows",
            date_range="n/a",
            record_count=_count(CATALOG_DB, "SELECT COUNT(*) FROM venue_daily_closes"),
            role="HISTORICAL",
            safe_to_project="n",
            transformation="none",
            conflicts=closes["status"],
        ),
        row(
            source="projection_generated_at",
            contains="timestamp of this register build",
            date_range=imported,
            record_count=1,
            role="REFERENCE",
            safe_to_project="n",
            read_access_how="clock",
            transformation="none",
            conflicts="none",
        ),
    ]


def write_register() -> dict[str, Any]:
    datasets = dataset_rows()
    payload = {
        "generated_at": now_iso(),
        "pack": "UMAREAL-1",
        "staff_ready": False,
        "human_commissioned": False,
        "cut_lines": [dict(row) for row in CUT_LINES],
        "datasets": datasets,
    }
    REGISTER_JSON.parent.mkdir(parents=True, exist_ok=True)
    REGISTER_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Uma Blu data source register",
        "",
        f"Pack UMAREAL-1. Generated {payload['generated_at']}. Counts are live queries from this run.",
        "Wolf commissioning date is null on every domain. `verified_by_wolf` stays false. `staff_ready` and `human_commissioned` stay false.",
        "",
        "## Cut lines",
        "",
        "| Domain | Historical source | Wolf commissioning date | Wolf authoritative going forward |",
        "| --- | --- | --- | --- |",
    ]
    for cut in CUT_LINES:
        lines.append(
            f"| {cut['domain']} | {cut['historical_source']} | null | {cut['wolf_authoritative_going_forward']} |"
        )
    lines.extend(
        [
            "",
            "## Datasets",
            "",
            "| SOURCE | WHAT IT CONTAINS | DATE RANGE | RECORD COUNT | ROLE | READ ACCESS VERIFIED | SAFE TO PROJECT | TRANSFORMATION | CONFLICTS | PROVENANCE |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in datasets:
        if item["source"] == "projection_generated_at":
            continue
        lines.append(
            "| {source} | {contains} | {date_range} | {record_count} | {role} | {read} | {safe} | {transformation} | {conflicts} | {provenance} |".format(
                source=item["source"],
                contains=item["contains"],
                date_range=item["date_range"],
                record_count=item["record_count"],
                role=item["role"],
                read=f"{item['read_access_verified']} — {item['read_access_how']}",
                safe=item["safe_to_project"],
                transformation=item["transformation"],
                conflicts=item["conflicts"],
                provenance=item["provenance"],
            )
        )
    lines.extend(
        [
            "",
            "## Daily close search",
            "",
            f"Status: {closes_status(payload)}",
            "",
        ]
    )
    # closes searched is not in payload datasets; call again would double-scan backups.
    # The status string is already on the venue_daily_closes conflict. Repeat the search
    # record from the function so the markdown has the paths.
    history = daily_close_history()
    lines[-2] = f"Status: {history['status']}"
    for item in history["searched"]:
        lines.append(f"- `{item['where']}` {item['table']}: {item.get('count')} {item.get('excluded') or ''}".rstrip())
    lines.append("")
    lines.append("No cash-variance threshold was inserted.")
    lines.append("")
    REGISTER_MD.parent.mkdir(parents=True, exist_ok=True)
    REGISTER_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def closes_status(payload: dict[str, Any]) -> str:
    for item in payload.get("datasets") or []:
        if item.get("source", "").endswith("venue_daily_closes"):
            return str(item.get("conflicts") or "NONE FOUND")
    return "NONE FOUND"
