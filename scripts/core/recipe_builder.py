#!/usr/bin/env python3
"""BZG Recipe Builder (Beta) — real V1 recipes + create/edit, no invented costs.

Decision served: 2026-09-29 PICK HEADCHEF-1 (extends CAP-BZG-06 / UMAREAL-1).
Historical wolf-system recipes.sqlite is read-only import source.
Beta store is the write surface. Missing purchase/card cost → "cost missing",
never 0 or a guess. Selling price is read-only for the chef (no edit policy).
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

from core import uma_real_projection as uma

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "bzg_recipes.sqlite"
V1_RECIPES_DB = (
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "uma-blu" / "recipes.sqlite"
)
V1_EXPORT = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "wolf-system"
    / "uma-blu"
    / "recipes-export.json"
)
TZ8 = timezone(timedelta(hours=8))
PROVENANCE_SOURCE = "wolf-system/uma-blu/recipes.sqlite"
ENTITY_BZG = "ENT-BZG"


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def db_path() -> Path:
    raw = (os.environ.get("RECIPE_BUILDER_DB") or "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_DB


def _refuse_path(path: Path) -> str | None:
    s = str(path.resolve())
    if "wolf-system" in s and "bzg_recipes" not in s:
        return "wolf-system-write-refused"
    if "/Production" in s or s.endswith(":8787"):
        return "production-refused"
    if "beta-os" not in s and "RECIPE_BUILDER_DB" not in os.environ:
        return "not-beta-os"
    return None


def connect(*, writable: bool = True) -> sqlite3.Connection:
    path = db_path()
    if writable:
        bad = _refuse_path(path)
        if bad:
            raise RuntimeError(f"recipe_builder refuses path ({bad}): {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if writable:
        _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS recipes (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          kind TEXT,
          group_name TEXT,
          time_range TEXT,
          yield_n REAL,
          yield_unit TEXT,
          dish_type TEXT,
          description TEXT,
          plating TEXT,
          method TEXT,
          photo_name TEXT,
          target_cos REAL,
          prod_pct REAL,
          fluct_pct REAL,
          waste_pct REAL,
          waste_fixed REAL,
          real_sell REAL,
          suggested_override REAL,
          esb_menu TEXT,
          status TEXT,
          source TEXT,
          created_at TEXT,
          updated_at TEXT,
          updated_by TEXT,
          prep TEXT,
          cook TEXT,
          plate TEXT,
          garnish TEXT,
          category TEXT,
          photo_x REAL,
          photo_y REAL,
          photo_zoom REAL,
          entity_id TEXT NOT NULL DEFAULT 'ENT-BZG',
          brand_id TEXT,
          provenance_source TEXT,
          provenance_source_id TEXT,
          provenance_imported_at TEXT,
          origin TEXT NOT NULL DEFAULT 'beta'
        );
        CREATE TABLE IF NOT EXISTS recipe_lines (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          recipe_id TEXT NOT NULL,
          sort INTEGER,
          line_kind TEXT,
          name TEXT,
          unit TEXT,
          qty REAL,
          unit_cost REAL,
          cost_source TEXT,
          goods_key TEXT,
          subrecipe_id TEXT,
          notes TEXT,
          FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_recipe_lines_recipe
          ON recipe_lines(recipe_id, sort, id);
        CREATE INDEX IF NOT EXISTS idx_recipes_brand ON recipes(brand_id);
        CREATE TABLE IF NOT EXISTS recipe_import_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        """
    )


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return (base or "recipe")[:80]


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def import_v1_recipes(*, force: bool = False) -> dict[str, Any]:
    """Idempotent import from V1 recipes.sqlite (preferred) or export JSON."""
    conn = connect(writable=True)
    try:
        existing = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        meta = conn.execute(
            "SELECT value FROM recipe_import_meta WHERE key='v1_import_complete'"
        ).fetchone()
        if existing and meta and not force:
            return {
                "ok": True,
                "imported": 0,
                "skipped": True,
                "existing": existing,
                "source": PROVENANCE_SOURCE,
                "message": "already imported",
            }

        src = V1_RECIPES_DB if V1_RECIPES_DB.is_file() else None
        imported = 0
        updated = 0
        ts = now_iso()
        recipes: list[Any] = []
        lines_by: dict[str, list[Any]] = {}
        source_label = ""
        used_sqlite = False
        if src is not None and not (os.environ.get("WOLF_TEST_MODE") or "").strip():
            try:
                ro = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
                ro.row_factory = sqlite3.Row
                try:
                    recipes = list(
                        ro.execute("SELECT * FROM recipes ORDER BY id COLLATE NOCASE")
                    )
                    for line in ro.execute(
                        "SELECT * FROM recipe_lines ORDER BY recipe_id, sort, id"
                    ):
                        lines_by.setdefault(line["recipe_id"], []).append(line)
                finally:
                    ro.close()
                used_sqlite = True
                source_label = str(src)
            except Exception:
                used_sqlite = False
                recipes = []
                lines_by = {}

        if used_sqlite:
            for recipe in recipes:
                rid = recipe["id"]
                was = conn.execute(
                    "SELECT id FROM recipes WHERE id=?", (rid,)
                ).fetchone()
                _upsert_recipe_from_v1(conn, recipe, lines_by.get(rid, []), ts)
                if was:
                    updated += 1
                else:
                    imported += 1
        elif V1_EXPORT.is_file():
            payload = json.loads(V1_EXPORT.read_text(encoding="utf-8"))
            for recipe in payload.get("recipes") or []:
                rid = recipe.get("id") or _slug(recipe.get("name") or "")
                was = conn.execute(
                    "SELECT id FROM recipes WHERE id=?", (rid,)
                ).fetchone()
                _upsert_recipe_from_export(conn, recipe, ts)
                if was:
                    updated += 1
                else:
                    imported += 1
            source_label = str(V1_EXPORT)
        else:
            # Last resort in tests: copy from Beta catalog store if already imported
            catalog_store = DEFAULT_DB
            if catalog_store.is_file() and catalog_store.resolve() != db_path().resolve():
                src_conn = sqlite3.connect(f"file:{catalog_store}?mode=ro", uri=True)
                src_conn.row_factory = sqlite3.Row
                try:
                    for recipe in src_conn.execute("SELECT * FROM recipes"):
                        rid = recipe["id"]
                        was = conn.execute(
                            "SELECT id FROM recipes WHERE id=?", (rid,)
                        ).fetchone()
                        lines = list(
                            src_conn.execute(
                                "SELECT * FROM recipe_lines WHERE recipe_id=? ORDER BY sort, id",
                                (rid,),
                            )
                        )
                        _upsert_recipe_from_v1(conn, recipe, lines, ts)
                        if was:
                            updated += 1
                        else:
                            imported += 1
                finally:
                    src_conn.close()
                source_label = str(catalog_store)
            else:
                return {
                    "ok": False,
                    "error": "v1_source_missing",
                    "message": "Neither recipes.sqlite nor recipes-export.json found",
                }

        conn.execute(
            """
            INSERT INTO recipe_import_meta(key, value, updated_at)
            VALUES ('v1_import_complete', '1', ?)
            ON CONFLICT(key) DO UPDATE SET value='1', updated_at=excluded.updated_at
            """,
            (ts,),
        )
        conn.execute(
            """
            INSERT INTO recipe_import_meta(key, value, updated_at)
            VALUES ('v1_import_source', ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (source_label, ts),
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        return {
            "ok": True,
            "imported": imported,
            "updated": updated,
            "total": total,
            "source": source_label,
            "provenance_kept": True,
            "skipped": False,
        }
    finally:
        conn.close()


def _upsert_recipe_from_v1(
    conn: sqlite3.Connection,
    recipe: sqlite3.Row,
    lines: list[sqlite3.Row],
    ts: str,
) -> None:
    rid = recipe["id"]
    # brand_id is provenance of the historical Uma store — not a hardcoded grant.
    brand_id = "BZG-UMA"
    cols = (
        rid,
        recipe["name"],
        recipe["kind"],
        recipe["group_name"],
        recipe["time_range"],
        recipe["yield_n"],
        recipe["yield_unit"],
        recipe["dish_type"],
        recipe["description"],
        recipe["plating"],
        recipe["method"],
        recipe["photo_name"],
        recipe["target_cos"],
        recipe["prod_pct"],
        recipe["fluct_pct"],
        recipe["waste_pct"],
        recipe["waste_fixed"],
        recipe["real_sell"],
        recipe["suggested_override"],
        recipe["esb_menu"],
        recipe["status"],
        recipe["source"],
        recipe["created_at"],
        recipe["updated_at"],
        recipe["updated_by"],
        recipe["prep"],
        recipe["cook"],
        recipe["plate"],
        recipe["garnish"],
        recipe["category"],
        recipe["photo_x"],
        recipe["photo_y"],
        recipe["photo_zoom"],
        ENTITY_BZG,
        brand_id,
        PROVENANCE_SOURCE,
        f"recipes:{rid}",
        ts,
        "v1_import",
    )
    conn.execute(
        """
        INSERT INTO recipes (
          id, name, kind, group_name, time_range, yield_n, yield_unit, dish_type,
          description, plating, method, photo_name, target_cos, prod_pct, fluct_pct,
          waste_pct, waste_fixed, real_sell, suggested_override, esb_menu, status,
          source, created_at, updated_at, updated_by, prep, cook, plate, garnish,
          category, photo_x, photo_y, photo_zoom, entity_id, brand_id,
          provenance_source, provenance_source_id, provenance_imported_at, origin
        ) VALUES (
          ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          kind=excluded.kind,
          group_name=excluded.group_name,
          yield_n=excluded.yield_n,
          yield_unit=excluded.yield_unit,
          real_sell=CASE
            WHEN recipes.origin='beta_edit' THEN recipes.real_sell
            ELSE excluded.real_sell
          END,
          status=CASE
            WHEN recipes.origin='beta_edit' THEN recipes.status
            ELSE excluded.status
          END,
          updated_at=excluded.updated_at,
          provenance_source=excluded.provenance_source,
          provenance_source_id=excluded.provenance_source_id,
          provenance_imported_at=excluded.provenance_imported_at,
          brand_id=COALESCE(recipes.brand_id, excluded.brand_id)
        """,
        cols,
    )
    # Only refresh lines when not locally edited
    origin = conn.execute(
        "SELECT origin FROM recipes WHERE id=?", (rid,)
    ).fetchone()
    if origin and origin[0] == "beta_edit":
        return
    conn.execute("DELETE FROM recipe_lines WHERE recipe_id=?", (rid,))
    for line in lines:
        conn.execute(
            """
            INSERT INTO recipe_lines (
              recipe_id, sort, line_kind, name, unit, qty, unit_cost,
              cost_source, goods_key, subrecipe_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                line["sort"],
                line["line_kind"],
                line["name"],
                line["unit"],
                line["qty"],
                line["unit_cost"],
                line["cost_source"],
                line["goods_key"],
                line["subrecipe_id"],
                line["notes"],
            ),
        )


def _upsert_recipe_from_export(
    conn: sqlite3.Connection, recipe: dict[str, Any], ts: str
) -> None:
    rid = recipe.get("id") or _slug(str(recipe.get("name") or "recipe"))
    conn.execute(
        """
        INSERT INTO recipes (
          id, name, kind, group_name, time_range, yield_n, yield_unit, dish_type,
          description, plating, method, photo_name, target_cos, prod_pct, fluct_pct,
          waste_pct, waste_fixed, real_sell, suggested_override, esb_menu, status,
          source, created_at, updated_at, updated_by, prep, cook, plate, garnish,
          category, photo_x, photo_y, photo_zoom, entity_id, brand_id,
          provenance_source, provenance_source_id, provenance_imported_at, origin
        ) VALUES (
          ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        ON CONFLICT(id) DO NOTHING
        """,
        (
            rid,
            recipe.get("name"),
            recipe.get("kind"),
            recipe.get("group_name"),
            recipe.get("time_range"),
            recipe.get("yield_n"),
            recipe.get("yield_unit"),
            recipe.get("dish_type"),
            recipe.get("description"),
            recipe.get("plating"),
            recipe.get("method"),
            recipe.get("photo_name"),
            recipe.get("target_cos"),
            recipe.get("prod_pct"),
            recipe.get("fluct_pct"),
            recipe.get("waste_pct"),
            recipe.get("waste_fixed"),
            recipe.get("real_sell"),
            recipe.get("suggested_override"),
            recipe.get("esb_menu"),
            recipe.get("status"),
            recipe.get("source"),
            recipe.get("created_at"),
            recipe.get("updated_at"),
            recipe.get("updated_by"),
            recipe.get("prep"),
            recipe.get("cook"),
            recipe.get("plate"),
            recipe.get("garnish"),
            recipe.get("category"),
            recipe.get("photo_x"),
            recipe.get("photo_y"),
            recipe.get("photo_zoom"),
            ENTITY_BZG,
            "BZG-UMA",
            str(V1_EXPORT),
            f"export:{rid}",
            ts,
            "v1_import",
        ),
    )
    if conn.execute("SELECT COUNT(*) FROM recipe_lines WHERE recipe_id=?", (rid,)).fetchone()[
        0
    ]:
        return
    for i, line in enumerate(recipe.get("lines") or []):
        conn.execute(
            """
            INSERT INTO recipe_lines (
              recipe_id, sort, line_kind, name, unit, qty, unit_cost,
              cost_source, goods_key, subrecipe_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                i + 1,
                line.get("line_kind") or "ingredient",
                line.get("name"),
                line.get("unit"),
                line.get("qty"),
                line.get("unit_cost"),
                line.get("cost_source"),
                line.get("goods_key"),
                line.get("subrecipe_id"),
                line.get("notes"),
            ),
        )


class _LineProxy:
    """Duck-type sqlite Row for uma_real_projection._cost_line."""

    def __init__(self, d: dict[str, Any]):
        self._d = d

    def __getitem__(self, key: str) -> Any:
        return self._d.get(key)


def _cost_recipe(recipe: dict[str, Any], lines: list[dict[str, Any]]) -> dict[str, Any]:
    recipe_row = _LineProxy(recipe)
    priced = [
        uma._cost_line(recipe_row, _LineProxy(line))  # noqa: SLF001 — shared costing
        for line in lines
        if (line.get("name") or "").strip()
    ]
    # Re-stamp source as Beta store while keeping applied costs honest
    for row in priced:
        if row.get("cost_badge") == "MISSING COST":
            row["cost_badge"] = "cost missing"
            row["applied_unit_cost"] = None
            row["extended_cost"] = None
        elif row.get("cost_badge") is None and row.get("extended_cost") is not None:
            row["cost_badge"] = None
    rollup = uma.rollup_food_cost(
        [
            {
                **line,
                "cost_badge": (
                    "MISSING COST"
                    if line.get("cost_badge") == "cost missing"
                    else line.get("cost_badge")
                ),
            }
            for line in priced
        ]
    )
    status = rollup["food_cost_status"]
    yield_n = recipe.get("yield_n")
    portion = None
    if rollup["food_cost"] is not None and yield_n:
        portion = round(float(rollup["food_cost"]) / float(yield_n), 4)
    sell = recipe.get("real_sell")
    margin = None
    food_cost_pct = None
    if portion is not None and sell:
        margin = round(float(sell) - portion, 4)
        if float(sell) != 0:
            food_cost_pct = round(portion / float(sell) * 100.0, 4)
    if status != "COMPLETE":
        portion = None
        margin = None
        food_cost_pct = None
        # Never show 0 or a partial guess
        food_cost = None
        food_cost_status = "cost missing" if priced else "INCOMPLETE"
    else:
        food_cost = rollup["food_cost"]
        food_cost_status = "COMPLETE"
    return {
        "recipe_id": recipe["id"],
        "name": recipe["name"],
        "kind": recipe.get("kind"),
        "group_name": recipe.get("group_name"),
        "status": recipe.get("status"),
        "brand_id": recipe.get("brand_id"),
        "entity_id": recipe.get("entity_id") or ENTITY_BZG,
        "yield_n": yield_n,
        "yield_unit": recipe.get("yield_unit"),
        "target_cos": recipe.get("target_cos"),
        "real_sell": sell,
        "sell_price_editable": False,
        "sell_price_policy": "read_only_propose_via_approval",
        "method": recipe.get("method"),
        "plating": recipe.get("plating"),
        "description": recipe.get("description"),
        "line_count": len(priced),
        "missing_cost_lines": sum(
            1 for line in priced if line.get("cost_badge") == "cost missing"
        ),
        "food_cost": food_cost,
        "food_cost_status": food_cost_status,
        "portion_cost": portion,
        "margin": margin,
        "food_cost_pct": food_cost_pct,
        "provenance": {
            "source": recipe.get("provenance_source"),
            "source_id": recipe.get("provenance_source_id"),
            "imported_at": recipe.get("provenance_imported_at"),
            "origin": recipe.get("origin"),
        },
        "lines": priced,
        "staff_ready": False,
        "human_commissioned": False,
    }


def list_recipes(
    *,
    brand_ids: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    conn = connect(writable=True)
    try:
        import_v1_recipes()  # no-op if already done
        params: list[Any] = []
        where = "1=1"
        if brand_ids is not None:
            if not brand_ids:
                return {
                    "ok": True,
                    "count": 0,
                    "offset": offset,
                    "limit": limit,
                    "recipes": [],
                    "brands_in_scope": [],
                    "staff_ready": False,
                    "human_commissioned": False,
                }
            placeholders = ",".join("?" for _ in brand_ids)
            where = f"(brand_id IN ({placeholders}) OR brand_id IS NULL)"
            params.extend(brand_ids)
        total = conn.execute(
            f"SELECT COUNT(*) FROM recipes WHERE {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM recipes
            WHERE {where}
            ORDER BY group_name COLLATE NOCASE, name COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            [*params, max(1, min(int(limit), 500)), max(0, int(offset))],
        ).fetchall()
        out = []
        for recipe in rows:
            lines = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM recipe_lines WHERE recipe_id=? ORDER BY sort, id",
                    (recipe["id"],),
                )
            ]
            dish = _cost_recipe(dict(recipe), lines)
            dish.pop("lines", None)
            out.append(dish)
        return {
            "ok": True,
            "count": total,
            "offset": offset,
            "limit": limit,
            "recipes": out,
            "brands_in_scope": list(brand_ids) if brand_ids is not None else None,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        conn.close()


def get_recipe(recipe_id: str) -> dict[str, Any] | None:
    conn = connect(writable=True)
    try:
        import_v1_recipes()
        recipe = conn.execute(
            "SELECT * FROM recipes WHERE id=?", (recipe_id,)
        ).fetchone()
        if recipe is None:
            return None
        lines = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM recipe_lines WHERE recipe_id=? ORDER BY sort, id",
                (recipe_id,),
            )
        ]
        return _cost_recipe(dict(recipe), lines)
    finally:
        conn.close()


def list_cost_exceptions(*, brand_ids: list[str] | None = None) -> dict[str, Any]:
    pack = list_recipes(brand_ids=brand_ids, limit=500, offset=0)
    exceptions = []
    for recipe in pack.get("recipes") or []:
        if recipe.get("missing_cost_lines") or recipe.get("food_cost_status") != "COMPLETE":
            exceptions.append(
                {
                    "recipe_id": recipe["recipe_id"],
                    "name": recipe["name"],
                    "brand_id": recipe.get("brand_id"),
                    "missing_cost_lines": recipe.get("missing_cost_lines"),
                    "food_cost_status": recipe.get("food_cost_status"),
                    "exception": "cost missing",
                }
            )
    return {
        "ok": True,
        "count": len(exceptions),
        "exceptions": exceptions,
        "staff_ready": False,
        "human_commissioned": False,
        "invented_costs": False,
    }


def create_recipe(
    payload: dict[str, Any],
    *,
    created_by: str | None,
    brand_id: str | None = None,
) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name required")
    # Selling price may be recorded for display from source, but chef create
    # must not invent a sell price. Omit or null only.
    if payload.get("real_sell") not in (None, ""):
        raise PermissionError(
            "Selling price is read-only for the chef. Propose a change via approval."
        )
    conn = connect(writable=True)
    try:
        rid = (payload.get("id") or "").strip() or f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        if conn.execute("SELECT 1 FROM recipes WHERE id=?", (rid,)).fetchone():
            rid = f"{rid}-{uuid.uuid4().hex[:4]}"
        ts = now_iso()
        bid = (brand_id or payload.get("brand_id") or "").strip() or None
        conn.execute(
            """
            INSERT INTO recipes (
              id, name, kind, group_name, yield_n, yield_unit, description,
              plating, method, status, source, created_at, updated_at, updated_by,
              entity_id, brand_id, provenance_source, provenance_source_id,
              provenance_imported_at, origin, real_sell
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 'beta-recipe-builder', ?, ?, ?,
                      ?, ?, 'wolf-beta', ?, ?, 'beta', NULL)
            """,
            (
                rid,
                name,
                (payload.get("kind") or "dish").strip(),
                (payload.get("group_name") or "").strip() or None,
                payload.get("yield_n"),
                (payload.get("yield_unit") or "").strip() or None,
                (payload.get("description") or "").strip() or None,
                (payload.get("plating") or "").strip() or None,
                (payload.get("method") or "").strip() or None,
                ts,
                ts,
                created_by,
                ENTITY_BZG,
                bid,
                f"beta:{rid}",
                ts,
            ),
        )
        _replace_lines(conn, rid, payload.get("lines") or [])
        conn.commit()
        return get_recipe(rid) or {"recipe_id": rid, "ok": True}
    finally:
        conn.close()


def update_recipe(
    recipe_id: str,
    payload: dict[str, Any],
    *,
    updated_by: str | None,
) -> dict[str, Any]:
    if "real_sell" in payload and payload.get("real_sell") is not None:
        # Explicit refuse — current policy: chef cannot edit selling price
        raise PermissionError(
            "Selling price is read-only for the chef. Propose a change via approval."
        )
    conn = connect(writable=True)
    try:
        existing = conn.execute(
            "SELECT * FROM recipes WHERE id=?", (recipe_id,)
        ).fetchone()
        if existing is None:
            raise KeyError(recipe_id)
        ts = now_iso()
        fields = {
            "name": payload.get("name", existing["name"]),
            "kind": payload.get("kind", existing["kind"]),
            "group_name": payload.get("group_name", existing["group_name"]),
            "yield_n": payload.get("yield_n", existing["yield_n"]),
            "yield_unit": payload.get("yield_unit", existing["yield_unit"]),
            "description": payload.get("description", existing["description"]),
            "plating": payload.get("plating", existing["plating"]),
            "method": payload.get("method", existing["method"]),
            "status": payload.get("status", existing["status"]),
        }
        conn.execute(
            """
            UPDATE recipes SET
              name=?, kind=?, group_name=?, yield_n=?, yield_unit=?,
              description=?, plating=?, method=?, status=?,
              updated_at=?, updated_by=?, origin='beta_edit'
            WHERE id=?
            """,
            (
                (fields["name"] or "").strip(),
                fields["kind"],
                fields["group_name"],
                fields["yield_n"],
                fields["yield_unit"],
                fields["description"],
                fields["plating"],
                fields["method"],
                fields["status"],
                ts,
                updated_by,
                recipe_id,
            ),
        )
        if "lines" in payload:
            _replace_lines(conn, recipe_id, payload.get("lines") or [])
        conn.commit()
        return get_recipe(recipe_id) or {"recipe_id": recipe_id, "ok": True}
    finally:
        conn.close()


def _replace_lines(
    conn: sqlite3.Connection, recipe_id: str, lines: list[dict[str, Any]]
) -> None:
    conn.execute("DELETE FROM recipe_lines WHERE recipe_id=?", (recipe_id,))
    for i, line in enumerate(lines):
        name = (line.get("name") or "").strip()
        if not name:
            continue
        # Never accept a client-invented unit_cost as truth — store card cost
        # only when explicitly provided from a known source field; otherwise null.
        unit_cost = line.get("unit_cost")
        cost_source = (line.get("cost_source") or "").strip() or None
        if unit_cost is not None and not cost_source:
            # Refuse silent invented costs
            unit_cost = None
        conn.execute(
            """
            INSERT INTO recipe_lines (
              recipe_id, sort, line_kind, name, unit, qty, unit_cost,
              cost_source, goods_key, subrecipe_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_id,
                int(line.get("sort") or i + 1),
                (line.get("line_kind") or "ingredient").strip(),
                name,
                (line.get("unit") or "").strip() or None,
                line.get("qty"),
                unit_cost,
                cost_source,
                line.get("goods_key"),
                line.get("subrecipe_id"),
                (line.get("notes") or "").strip() or None,
            ),
        )


def honesty() -> dict[str, Any]:
    return {
        "staff_ready": False,
        "human_commissioned": False,
        "invented_costs": False,
        "sell_price_editable": False,
        "bound": "beta-bzg-recipe-builder",
        "v1_source_readonly": True,
    }
