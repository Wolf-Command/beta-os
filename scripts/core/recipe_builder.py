#!/usr/bin/env python3
"""BZG Recipe Builder (Beta) — multi-outlet, real V1 recipes, no invented costs.

Decision served: 2026-09-29 PICK HEADCHEF-1 (extends CAP-BZG-06 / UMAREAL-1)
+ 2026-10-02 BZG-RECIPE-MULTI-OUTLET-1 (Haryanto multi-outlet menus).

One builder with outlet context — not seven apps. Recipes store once and
associate to one / multi / all-BZG outlets. Menu items are outlet-specific.
Shared ingredient master. Missing purchase/card cost → INCOMPLETE COST,
never 0 or a guess. Uma Blu 127/756 preserved (brand_id BZG-UMA provenance;
not relabelled BZG-wide). Outlets come from org_outlet_registry — never
hardcoded. Recipe.real_sell stays chef-read-only; outlet menu sell prices
are separate per-outlet menu rows.
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

from core import bzg_outlet_registry as _outlets
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
ALL_BZG = "ALL_BZG"
UMA_OUTLET_ID = "BZG-UMA"
INCOMPLETE_COST = "INCOMPLETE COST"
PACK_MULTI = "BZG-RECIPE-MULTI-OUTLET-1"


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
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if writable:
        _ensure_schema(conn)
        conn.commit()
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
        -- BZG-RECIPE-MULTI-OUTLET-1: associate once; menus outlet-specific
        CREATE TABLE IF NOT EXISTS recipe_outlet_links (
          recipe_id TEXT NOT NULL,
          outlet_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY (recipe_id, outlet_id),
          FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_recipe_outlet_links_outlet
          ON recipe_outlet_links(outlet_id, recipe_id);
        CREATE TABLE IF NOT EXISTS recipe_all_bzg (
          recipe_id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        );
        CREATE TABLE IF NOT EXISTS outlet_menu_items (
          id TEXT PRIMARY KEY,
          outlet_id TEXT NOT NULL,
          recipe_id TEXT NOT NULL,
          menu_name TEXT NOT NULL,
          category TEXT,
          portion_n REAL,
          portion_unit TEXT,
          sell_price REAL,
          status TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          updated_by TEXT,
          FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_outlet_menu_items_outlet
          ON outlet_menu_items(outlet_id, recipe_id);
        CREATE TABLE IF NOT EXISTS ingredient_master (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          default_unit TEXT,
          purchase_unit TEXT,
          purchase_cost REAL,
          cost_source TEXT,
          goods_key TEXT,
          entity_id TEXT NOT NULL DEFAULT 'ENT-BZG',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredient_master_name
          ON ingredient_master(entity_id, name COLLATE NOCASE);
        """
    )
    _migrate_multi_outlet(conn)


def _migrate_multi_outlet(conn: sqlite3.Connection) -> None:
    """Preserve Uma Blu 127/756 — assign existing recipes to BZG-UMA only.

    Does not relabel brand_id to BZG-wide. Idempotent.
    """
    ts = now_iso()
    meta = conn.execute(
        "SELECT value FROM recipe_import_meta WHERE key='multi_outlet_v1'"
    ).fetchone()
    # Always ensure Uma links for any recipe with brand_id BZG-UMA that lacks links
    # and is not marked all_bzg — safe to re-run.
    uma_ids = [
        r[0]
        for r in conn.execute(
            """
            SELECT id FROM recipes
            WHERE brand_id=? OR provenance_source=?
            """,
            (UMA_OUTLET_ID, PROVENANCE_SOURCE),
        ).fetchall()
    ]
    # Also cover every existing recipe that has zero outlet links and is not all_bzg
    orphan_ids = [
        r[0]
        for r in conn.execute(
            """
            SELECT r.id FROM recipes r
            WHERE NOT EXISTS (
              SELECT 1 FROM recipe_outlet_links l WHERE l.recipe_id=r.id
            )
            AND NOT EXISTS (
              SELECT 1 FROM recipe_all_bzg a WHERE a.recipe_id=r.id
            )
            """
        ).fetchall()
    ]
    # Prefer Uma assignment for provenance Uma rows; orphans without brand default Uma
    # only when brand_id is BZG-UMA or null with v1 provenance — never invent Rainforest.
    for rid in set(uma_ids) | set(orphan_ids):
        row = conn.execute(
            "SELECT brand_id, provenance_source, origin FROM recipes WHERE id=?",
            (rid,),
        ).fetchone()
        if row is None:
            continue
        brand_id, prov, origin = row[0], row[1], row[2]
        is_uma = (
            brand_id == UMA_OUTLET_ID
            or prov == PROVENANCE_SOURCE
            or origin == "v1_import"
        )
        # Never invent Uma assignment for new beta recipes without Uma provenance
        if not is_uma:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO recipe_outlet_links(recipe_id, outlet_id, created_at)
            VALUES (?, ?, ?)
            """,
            (rid, UMA_OUTLET_ID, ts),
        )
    # Shared ingredient master from distinct line names (one master, not seven)
    for name, unit, unit_cost, cost_source, goods_key in conn.execute(
        """
        SELECT name, MAX(unit), MAX(unit_cost), MAX(cost_source), MAX(goods_key)
        FROM recipe_lines
        WHERE name IS NOT NULL AND TRIM(name) != ''
        GROUP BY name COLLATE NOCASE
        """
    ):
        existing = conn.execute(
            """
            SELECT id FROM ingredient_master
            WHERE entity_id=? AND name=? COLLATE NOCASE
            """,
            (ENTITY_BZG, name),
        ).fetchone()
        if existing:
            continue
        iid = f"ing-{_slug(name)}-{uuid.uuid4().hex[:6]}"
        conn.execute(
            """
            INSERT INTO ingredient_master (
              id, name, default_unit, purchase_unit, purchase_cost,
              cost_source, goods_key, entity_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                iid,
                name,
                unit,
                unit,
                unit_cost,
                cost_source,
                goods_key,
                ENTITY_BZG,
                ts,
                ts,
            ),
        )
    if not meta:
        conn.execute(
            """
            INSERT INTO recipe_import_meta(key, value, updated_at)
            VALUES ('multi_outlet_v1', ?, ?)
            """,
            (PACK_MULTI, ts),
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
    # Re-stamp: missing → INCOMPLETE COST (never silent zero)
    for row in priced:
        if row.get("cost_badge") in {"MISSING COST", "INCOMPLETE COST", "cost missing"}:
            row["cost_badge"] = INCOMPLETE_COST
            row["applied_unit_cost"] = None
            row["extended_cost"] = None
        elif row.get("cost_badge") is None and row.get("extended_cost") is None:
            row["cost_badge"] = INCOMPLETE_COST
        elif row.get("cost_badge") is None and row.get("extended_cost") is not None:
            row["cost_badge"] = None
    rollup = uma.rollup_food_cost(
        [
            {
                **line,
                "cost_badge": (
                    "INCOMPLETE COST"
                    if line.get("cost_badge") == INCOMPLETE_COST
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
        food_cost_status = INCOMPLETE_COST if priced else INCOMPLETE_COST
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
            1 for line in priced if line.get("cost_badge") == INCOMPLETE_COST
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


def _registry_outlets() -> list[dict[str, Any]]:
    """Canonical outlets — never hardcode seven names."""
    return _outlets.list_outlets()


def _outlet_index() -> dict[str, dict[str, Any]]:
    return {o["outlet_id"]: o for o in _registry_outlets()}


def preserve_counts() -> dict[str, Any]:
    """Uma Blu store truth — 127 recipes / 756 lines must hold."""
    import_v1_recipes()
    conn = connect(writable=True)
    try:
        recipes = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        lines = conn.execute("SELECT COUNT(*) FROM recipe_lines").fetchone()[0]
        uma_assigned = conn.execute(
            """
            SELECT COUNT(DISTINCT r.id) FROM recipes r
            JOIN recipe_outlet_links l ON l.recipe_id=r.id
            WHERE l.outlet_id=?
            """,
            (UMA_OUTLET_ID,),
        ).fetchone()[0]
        uma_brand = conn.execute(
            "SELECT COUNT(*) FROM recipes WHERE brand_id=?",
            (UMA_OUTLET_ID,),
        ).fetchone()[0]
        all_bzg_uma = conn.execute(
            """
            SELECT COUNT(*) FROM recipe_all_bzg a
            JOIN recipes r ON r.id=a.recipe_id
            WHERE r.brand_id=? AND r.origin='v1_import'
            """,
            (UMA_OUTLET_ID,),
        ).fetchone()[0]
        return {
            "ok": True,
            "recipes": recipes,
            "lines": lines,
            "uma_outlet_assigned": uma_assigned,
            "uma_brand_id_count": uma_brand,
            "v1_import_relabelled_all_bzg": all_bzg_uma,
            "preserved": recipes >= 127 and lines >= 756 and uma_brand >= 127,
            "relabelled_bzg_wide": all_bzg_uma > 0,
        }
    finally:
        conn.close()


def builder_context(
    *,
    outlet_id: str | None = None,
    person_id: str | None = None,
) -> dict[str, Any]:
    """Outlet selector payload. Default sensible (OPEN Uma) but never silent wrong."""
    import_v1_recipes()
    registry = _registry_outlets()
    covered = (
        _outlets.outlets_for_person(person_id) if person_id else list(registry)
    )
    covered_ids = {o["outlet_id"] for o in covered}
    outlets = []
    for row in registry:
        if covered_ids and row["outlet_id"] not in covered_ids:
            continue
        outlets.append(
            {
                "outlet_id": row["outlet_id"],
                "display_name": row["display_name"],
                "brand_id": row["brand_id"],
                "parent_outlet_id": row.get("parent_outlet_id"),
                "outlet_kind": row["outlet_kind"],
                "status": row["status"],
                "registry_source": "org_outlet_registry",
            }
        )
    requested = (outlet_id or "").strip() or None
    default = next((o for o in outlets if o["status"] == "OPEN"), None)
    if default is None and outlets:
        default = outlets[0]
    selected = None
    silent_wrong = False
    needs_explicit = False
    if requested == ALL_BZG:
        selected = {
            "outlet_id": ALL_BZG,
            "display_name": "All BZG",
            "mode": "catalogue_assignments",
            "not_merged_menu": True,
        }
    elif requested:
        hit = next((o for o in outlets if o["outlet_id"] == requested), None)
        if hit is None:
            needs_explicit = True
            silent_wrong = False
        else:
            selected = {**hit, "mode": "outlet"}
    else:
        # Sensible default = OPEN outlet, but surface it explicitly (never silent)
        if default:
            selected = {**default, "mode": "outlet", "defaulted": True}
        else:
            needs_explicit = True
    return {
        "ok": True,
        "pack": PACK_MULTI,
        "outlets": outlets,
        "all_bzg": {
            "outlet_id": ALL_BZG,
            "display_name": "All BZG",
            "mode": "catalogue_assignments",
            "not_merged_menu": True,
            "note": "Catalogue + assignments for Head Chef — not a fake merged menu.",
        },
        "selected_outlet": selected,
        "default_outlet_id": default["outlet_id"] if default else None,
        "needs_explicit_outlet": needs_explicit,
        "silent_wrong_outlet": silent_wrong,
        "registry_driven": True,
        "hardcoded_outlet_list": False,
        "rainforest_registry_name": next(
            (
                o["display_name"]
                for o in registry
                if o["outlet_id"] == "BZG-RAIN"
            ),
            None,
        ),
        "staff_ready": False,
        "human_commissioned": False,
    }


def _recipe_outlet_payload(conn: sqlite3.Connection, recipe_id: str) -> dict[str, Any]:
    links = [
        r[0]
        for r in conn.execute(
            "SELECT outlet_id FROM recipe_outlet_links WHERE recipe_id=? ORDER BY outlet_id",
            (recipe_id,),
        ).fetchall()
    ]
    all_bzg = (
        conn.execute(
            "SELECT 1 FROM recipe_all_bzg WHERE recipe_id=?", (recipe_id,)
        ).fetchone()
        is not None
    )
    idx = _outlet_index()
    return {
        "outlet_ids": links,
        "all_bzg": all_bzg,
        "outlets": [
            {
                "outlet_id": oid,
                "display_name": (idx.get(oid) or {}).get("display_name") or oid,
            }
            for oid in links
        ],
    }


def set_recipe_outlets(
    recipe_id: str,
    *,
    outlet_ids: list[str] | None = None,
    all_bzg: bool = False,
) -> dict[str, Any]:
    """Associate recipe to one / multi / all-BZG without duplicating the recipe row."""
    registry_ids = {o["outlet_id"] for o in _registry_outlets()}
    conn = connect(writable=True)
    try:
        if conn.execute("SELECT 1 FROM recipes WHERE id=?", (recipe_id,)).fetchone() is None:
            raise KeyError(recipe_id)
        ts = now_iso()
        if all_bzg:
            conn.execute(
                """
                INSERT OR IGNORE INTO recipe_all_bzg(recipe_id, created_at)
                VALUES (?, ?)
                """,
                (recipe_id, ts),
            )
            # Keep explicit links optional; all_bzg means catalogue-wide
        else:
            conn.execute("DELETE FROM recipe_all_bzg WHERE recipe_id=?", (recipe_id,))
        if outlet_ids is not None:
            wanted = []
            for oid in outlet_ids:
                oid = (oid or "").strip()
                if not oid or oid == ALL_BZG:
                    continue
                if oid not in registry_ids:
                    raise ValueError(f"unknown outlet_id (not in registry): {oid}")
                wanted.append(oid)
            conn.execute(
                "DELETE FROM recipe_outlet_links WHERE recipe_id=?", (recipe_id,)
            )
            for oid in wanted:
                conn.execute(
                    """
                    INSERT INTO recipe_outlet_links(recipe_id, outlet_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (recipe_id, oid, ts),
                )
        conn.commit()
        return {"ok": True, "recipe_id": recipe_id, **_recipe_outlet_payload(conn, recipe_id)}
    finally:
        conn.close()


def list_recipes(
    *,
    brand_ids: list[str] | None = None,
    outlet_id: str | None = None,
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
                    "outlet_id": outlet_id,
                    "staff_ready": False,
                    "human_commissioned": False,
                }
            placeholders = ",".join("?" for _ in brand_ids)
            where = f"(brand_id IN ({placeholders}) OR brand_id IS NULL)"
            params.extend(brand_ids)
        oid = (outlet_id or "").strip() or None
        catalogue_mode = False
        if oid == ALL_BZG:
            catalogue_mode = True
            # Catalogue + assignments — every recipe in scope (not a merged menu)
        elif oid:
            where = (
                f"({where}) AND ("
                "EXISTS (SELECT 1 FROM recipe_all_bzg a WHERE a.recipe_id=recipes.id) "
                "OR EXISTS (SELECT 1 FROM recipe_outlet_links l "
                "WHERE l.recipe_id=recipes.id AND l.outlet_id=?)"
                ")"
            )
            params.append(oid)
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
            dish["outlet_assignment"] = _recipe_outlet_payload(conn, recipe["id"])
            out.append(dish)
        return {
            "ok": True,
            "count": total,
            "offset": offset,
            "limit": limit,
            "recipes": out,
            "brands_in_scope": list(brand_ids) if brand_ids is not None else None,
            "outlet_id": oid,
            "catalogue_mode": catalogue_mode,
            "not_merged_menu": catalogue_mode,
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
        dish = _cost_recipe(dict(recipe), lines)
        dish["outlet_assignment"] = _recipe_outlet_payload(conn, recipe_id)
        dish["menu_items"] = [
            dict(r)
            for r in conn.execute(
                """
                SELECT * FROM outlet_menu_items
                WHERE recipe_id=?
                ORDER BY outlet_id, menu_name COLLATE NOCASE
                """,
                (recipe_id,),
            )
        ]
        return dish
    finally:
        conn.close()


def list_cost_exceptions(
    *,
    brand_ids: list[str] | None = None,
    outlet_id: str | None = None,
) -> dict[str, Any]:
    pack = list_recipes(brand_ids=brand_ids, outlet_id=outlet_id, limit=500, offset=0)
    exceptions = []
    for recipe in pack.get("recipes") or []:
        if recipe.get("missing_cost_lines") or recipe.get("food_cost_status") != "COMPLETE":
            exceptions.append(
                {
                    "recipe_id": recipe["recipe_id"],
                    "name": recipe["name"],
                    "brand_id": recipe.get("brand_id"),
                    "outlet_assignment": recipe.get("outlet_assignment"),
                    "missing_cost_lines": recipe.get("missing_cost_lines"),
                    "food_cost_status": recipe.get("food_cost_status"),
                    "exception": INCOMPLETE_COST,
                }
            )
    return {
        "ok": True,
        "count": len(exceptions),
        "exceptions": exceptions,
        "outlet_id": outlet_id,
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
    outlet_ids = payload.get("outlet_ids")
    all_bzg = bool(payload.get("all_bzg"))
    single_outlet = (payload.get("outlet_id") or "").strip() or None
    if single_outlet and single_outlet != ALL_BZG:
        outlet_ids = list(outlet_ids or []) + [single_outlet]
    registry_ids = {o["outlet_id"]: o for o in _registry_outlets()}
    bid = (brand_id or payload.get("brand_id") or "").strip() or None
    # Legacy HEADCHEF-1: explicit brand_id maps to that brand's BRAND outlet — not silent.
    if not all_bzg and not outlet_ids and bid:
        if bid in registry_ids:
            outlet_ids = [bid]
        else:
            match = next(
                (
                    o["outlet_id"]
                    for o in registry_ids.values()
                    if o.get("brand_id") == bid and o.get("outlet_kind") == "BRAND"
                ),
                None,
            )
            if match:
                outlet_ids = [match]
    if not all_bzg and not outlet_ids:
        raise ValueError(
            "Explicit outlet_ids, outlet_id, all_bzg, or brand_id required — "
            "never create with a silent outlet."
        )
    cleaned: list[str] = []
    for oid in outlet_ids or []:
        oid = (oid or "").strip()
        if not oid or oid == ALL_BZG:
            continue
        if oid not in registry_ids:
            raise ValueError(f"unknown outlet_id (not in registry): {oid}")
        if oid not in cleaned:
            cleaned.append(oid)
    if not all_bzg and not cleaned:
        raise ValueError("At least one registry outlet_id required")
    # brand_id is provenance / primary brand — prefer first outlet's brand, else caller
    if not bid and cleaned:
        bid = registry_ids[cleaned[0]].get("brand_id")
    conn = connect(writable=True)
    try:
        rid = (payload.get("id") or "").strip() or f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        if conn.execute("SELECT 1 FROM recipes WHERE id=?", (rid,)).fetchone():
            rid = f"{rid}-{uuid.uuid4().hex[:4]}"
        ts = now_iso()
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
    finally:
        conn.close()
    set_recipe_outlets(rid, outlet_ids=cleaned, all_bzg=all_bzg)
    return get_recipe(rid) or {"recipe_id": rid, "ok": True}


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


def list_menu_items(*, outlet_id: str) -> dict[str, Any]:
    """Outlet-specific menu — RECIPE ≠ MENU ITEM ≠ OUTLET MENU."""
    oid = (outlet_id or "").strip()
    if not oid or oid == ALL_BZG:
        return {
            "ok": False,
            "error": "outlet_required",
            "message": "All BZG is catalogue/assignments — not a merged menu.",
            "menu_items": [],
            "staff_ready": False,
            "human_commissioned": False,
        }
    if oid not in {o["outlet_id"] for o in _registry_outlets()}:
        raise ValueError(f"unknown outlet_id (not in registry): {oid}")
    import_v1_recipes()
    conn = connect(writable=True)
    try:
        rows = [
            dict(r)
            for r in conn.execute(
                """
                SELECT * FROM outlet_menu_items
                WHERE outlet_id=?
                ORDER BY category COLLATE NOCASE, menu_name COLLATE NOCASE
                """,
                (oid,),
            )
        ]
        return {
            "ok": True,
            "outlet_id": oid,
            "count": len(rows),
            "menu_items": rows,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        conn.close()


def upsert_menu_item(
    payload: dict[str, Any],
    *,
    updated_by: str | None,
) -> dict[str, Any]:
    """Create/update outlet menu item for a shared recipe (price/portion may differ)."""
    oid = (payload.get("outlet_id") or "").strip()
    rid = (payload.get("recipe_id") or "").strip()
    menu_name = (payload.get("menu_name") or "").strip()
    if not oid or not rid or not menu_name:
        raise ValueError("outlet_id, recipe_id, menu_name required")
    if oid == ALL_BZG:
        raise ValueError("Cannot attach a menu item to All BZG (not a menu)")
    if oid not in {o["outlet_id"] for o in _registry_outlets()}:
        raise ValueError(f"unknown outlet_id (not in registry): {oid}")
    conn = connect(writable=True)
    try:
        if conn.execute("SELECT 1 FROM recipes WHERE id=?", (rid,)).fetchone() is None:
            raise KeyError(rid)
        ts = now_iso()
        mid = (payload.get("id") or "").strip() or f"mi-{_slug(menu_name)}-{uuid.uuid4().hex[:6]}"
        existing = conn.execute(
            "SELECT id FROM outlet_menu_items WHERE id=?", (mid,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE outlet_menu_items SET
                  outlet_id=?, recipe_id=?, menu_name=?, category=?,
                  portion_n=?, portion_unit=?, sell_price=?, status=?,
                  updated_at=?, updated_by=?
                WHERE id=?
                """,
                (
                    oid,
                    rid,
                    menu_name,
                    (payload.get("category") or "").strip() or None,
                    payload.get("portion_n"),
                    (payload.get("portion_unit") or "").strip() or None,
                    payload.get("sell_price"),
                    (payload.get("status") or "draft").strip(),
                    ts,
                    updated_by,
                    mid,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO outlet_menu_items (
                  id, outlet_id, recipe_id, menu_name, category, portion_n,
                  portion_unit, sell_price, status, created_at, updated_at, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    oid,
                    rid,
                    menu_name,
                    (payload.get("category") or "").strip() or None,
                    payload.get("portion_n"),
                    (payload.get("portion_unit") or "").strip() or None,
                    payload.get("sell_price"),
                    (payload.get("status") or "draft").strip(),
                    ts,
                    ts,
                    updated_by,
                ),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM outlet_menu_items WHERE id=?", (mid,)
        ).fetchone()
        return {"ok": True, "menu_item": dict(row) if row else {"id": mid}}
    finally:
        conn.close()


def list_ingredients() -> dict[str, Any]:
    """Shared ingredient master — one master for all BZG outlets."""
    import_v1_recipes()
    conn = connect(writable=True)
    try:
        rows = []
        for r in conn.execute(
            """
            SELECT * FROM ingredient_master
            WHERE entity_id=?
            ORDER BY name COLLATE NOCASE
            """,
            (ENTITY_BZG,),
        ):
            d = dict(r)
            if d.get("purchase_cost") is None:
                d["cost_status"] = INCOMPLETE_COST
            else:
                d["cost_status"] = "KNOWN"
            # Never coerce null cost to 0
            if d.get("purchase_cost") == 0 and not d.get("cost_source"):
                d["purchase_cost"] = None
                d["cost_status"] = INCOMPLETE_COST
            rows.append(d)
        return {
            "ok": True,
            "count": len(rows),
            "ingredients": rows,
            "shared_master": True,
            "per_outlet_masters": False,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        conn.close()


def reporting_foundation(*, outlet_id: str | None = None) -> dict[str, Any]:
    """Reporting foundation only — refuse fake Rainforest FC / ESB / inventory."""
    oid = (outlet_id or "").strip() or None
    registry = _outlet_index()
    outlet = registry.get(oid) if oid and oid != ALL_BZG else None
    commissioned = False
    # No outlet has commissioned FC/ESB theoretical/inventory variance in this pack
    reasons = []
    if oid == "BZG-RAIN" or (outlet and outlet.get("outlet_id") == "BZG-RAIN"):
        reasons.append(
            "Rainforest food-cost reporting is not human-commissioned — "
            "registry status is PRE-OPENING; refusing invented FC numbers."
        )
    reasons.append(
        "ESB theoretical usage variance is not commissioned on this builder surface."
    )
    reasons.append(
        "Inventory variance is not commissioned on this builder surface."
    )
    return {
        "ok": True,
        "pack": PACK_MULTI,
        "outlet_id": oid,
        "outlet_display_name": (outlet or {}).get("display_name"),
        "outlet_status": (outlet or {}).get("status"),
        "reporting": {
            "rainforest_food_cost": {
                "state": "REFUSED_UNCOMMISSIONED",
                "value": None,
                "invented": False,
            },
            "esb_theoretical": {
                "state": "REFUSED_UNCOMMISSIONED",
                "value": None,
                "invented": False,
            },
            "inventory_variance": {
                "state": "REFUSED_UNCOMMISSIONED",
                "value": None,
                "invented": False,
            },
        },
        "commissioned": commissioned,
        "refused_reasons": reasons,
        "staff_ready": False,
        "human_commissioned": False,
        "foundation_only": True,
    }


def honesty() -> dict[str, Any]:
    return {
        "staff_ready": False,
        "human_commissioned": False,
        "invented_costs": False,
        "sell_price_editable": False,
        "bound": "beta-bzg-recipe-builder",
        "v1_source_readonly": True,
        "multi_outlet": True,
        "pack": PACK_MULTI,
        "incomplete_cost_label": INCOMPLETE_COST,
        "registry_driven_outlets": True,
    }
