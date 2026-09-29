#!/usr/bin/env python3
"""BZG-XOUTLET-1 — Cross-outlet shared foundations for BZG.

Makes LEGAL ENTITY → OUTLET → cost/revenue centre usable across outlets for
shared foundations only (vendors / purchase-request hooks / close hooks).

`outlet_id` is nullable and, when set, must resolve against org_outlet_registry.
Cost/revenue centre IDs remain nullable hooks — no invented multi-outlet P&L,
sales, costs, covers, allocations, or go-live numbers.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_outlet_registry as _outlets

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK = "BZG-XOUTLET-1"
LEGAL_ENTITY = "ENT-BZG"

# Shared foundation hooks — schema + outlet_id carriage only. Empty OK.
HOOK_IDS = (
    "vendors",
    "purchase_requests",
    "daily_close",
    "books_journal_lines",
)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "invented_sales": False,
    "invented_costs": False,
    "invented_covers": False,
    "invented_pnl": False,
    "invented_multi_outlet_totals": False,
    "invented_allocations": False,
    "invented_go_live_numbers": False,
    "money_movement": False,
    "proven": False,
    "legal_entity_id": LEGAL_ENTITY,
    "pack": PACK,
}


class BzgXoutletError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    return _outlets.db_connect(db_path)


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not exists:
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_nullable_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cols = _table_cols(conn, table)
    if not cols or col in cols:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    return True


def ensure_schema(conn: sqlite3.Connection) -> dict[str, Any]:
    """DDL for shared cross-outlet foundations. Read paths must not call under RO."""
    added: list[str] = []

    # Shared vendors — entity-scoped; outlet_id null = shared across outlets.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bzg_shared_vendors (
          vendor_id TEXT PRIMARY KEY,
          legal_entity_id TEXT NOT NULL,
          outlet_id TEXT,
          cost_centre_id TEXT,
          revenue_centre_id TEXT,
          display_name TEXT NOT NULL,
          name_norm TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'HOOK',
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          CHECK (legal_entity_id = 'ENT-BZG'),
          CHECK (status IN ('HOOK','ACTIVE','INACTIVE'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bzg_shared_vendors_outlet
        ON bzg_shared_vendors(outlet_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bzg_shared_vendors_norm
        ON bzg_shared_vendors(legal_entity_id, name_norm)
        """
    )

    for table, cols in (
        ("bzg_ops_purchase_requests", ("outlet_id", "cost_centre_id", "revenue_centre_id")),
        ("venue_daily_closes", ("outlet_id", "cost_centre_id", "revenue_centre_id")),
    ):
        for col in cols:
            if _add_nullable_col(conn, table, col):
                added.append(f"{table}.{col}")

    # Index outlet_id when present (idempotent name).
    pr_cols = _table_cols(conn, "bzg_ops_purchase_requests")
    if "outlet_id" in pr_cols:
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_pr_outlet
            ON bzg_ops_purchase_requests(outlet_id)
            """
        )
    close_cols = _table_cols(conn, "venue_daily_closes")
    if "outlet_id" in close_cols:
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_outlet
            ON venue_daily_closes(outlet_id)
            """
        )

    return {"added_columns": added, "vendors_table": "bzg_shared_vendors"}


def resolve_outlet_ref(
    outlet_id: str | None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Null outlet_id is valid (entity-shared). Non-null must be in registry."""
    if outlet_id is None or str(outlet_id).strip() == "":
        return None
    oid = str(outlet_id).strip()
    hier = _outlets.hierarchy_for_outlet(oid, conn=conn)
    if not hier:
        raise BzgXoutletError(
            f"outlet_id {oid!r} is not in org_outlet_registry.",
            code="invalid_outlet",
            http_status=400,
        )
    if hier["legal_entity_id"] != LEGAL_ENTITY:
        raise BzgXoutletError(
            f"outlet_id {oid!r} is not under ENT-BZG.",
            code="invalid_outlet",
            http_status=400,
        )
    return hier


def hierarchy_usable(
    outlet_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """ENTITY → OUTLET → centres — usable shape for shared foundations."""
    own = conn is None
    c = conn or db_connect()
    try:
        if outlet_id:
            hier = resolve_outlet_ref(outlet_id, conn=c)
            assert hier is not None
            return {
                "legal_entity_id": hier["legal_entity_id"],
                "outlet_id": hier["outlet_id"],
                "brand_id": hier.get("brand_id"),
                "operating_unit_id": hier.get("operating_unit_id"),
                "parent_outlet_id": hier.get("parent_outlet_id"),
                "status": hier.get("status"),
                "cost_centre_id": hier.get("cost_centre_id"),
                "revenue_centre_id": hier.get("revenue_centre_id"),
                "centres_are_hooks": True,
                "centres_populated": False,
            }
        return {
            "legal_entity_id": LEGAL_ENTITY,
            "outlet_id": None,
            "brand_id": None,
            "operating_unit_id": None,
            "parent_outlet_id": None,
            "status": None,
            "cost_centre_id": None,
            "revenue_centre_id": None,
            "centres_are_hooks": True,
            "centres_populated": False,
            "note": "Entity-shared foundation row — outlet_id nullable.",
        }
    finally:
        if own:
            c.close()


def _count(conn: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, args).fetchone()
    return int(row[0]) if row else 0


def hook_status(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Honest inventory of shared hooks — counts only; no money totals."""
    pr_cols = _table_cols(conn, "bzg_ops_purchase_requests")
    close_cols = _table_cols(conn, "venue_daily_closes")
    vendor_cols = _table_cols(conn, "bzg_shared_vendors")

    vendors_n = (
        _count(
            conn,
            "SELECT COUNT(*) FROM bzg_shared_vendors WHERE legal_entity_id=?",
            (LEGAL_ENTITY,),
        )
        if vendor_cols
        else 0
    )
    pr_n = (
        _count(conn, "SELECT COUNT(*) FROM bzg_ops_purchase_requests WHERE example=0")
        if pr_cols
        else 0
    )
    pr_example_n = (
        _count(conn, "SELECT COUNT(*) FROM bzg_ops_purchase_requests WHERE example=1")
        if pr_cols
        else 0
    )
    close_n = (
        _count(conn, "SELECT COUNT(*) FROM venue_daily_closes") if close_cols else 0
    )

    return [
        {
            "hook_id": "vendors",
            "table": "bzg_shared_vendors",
            "outlet_id_nullable": "outlet_id" in vendor_cols,
            "cost_centre_id_nullable": "cost_centre_id" in vendor_cols,
            "revenue_centre_id_nullable": "revenue_centre_id" in vendor_cols,
            "row_count": vendors_n,
            "empty_ok": True,
            "message": (
                "Shared BZG vendors across outlets. outlet_id null = entity-shared. "
                "Empty OK — no invented suppliers."
            ),
        },
        {
            "hook_id": "purchase_requests",
            "table": "bzg_ops_purchase_requests",
            "outlet_id_nullable": "outlet_id" in pr_cols,
            "cost_centre_id_nullable": "cost_centre_id" in pr_cols,
            "revenue_centre_id_nullable": "revenue_centre_id" in pr_cols,
            "row_count_operational": pr_n,
            "row_count_example": pr_example_n,
            "empty_ok": True,
            "message": (
                "Purchase-request rows may carry nullable outlet_id from "
                "org_outlet_registry. No multi-outlet spend totals."
            ),
        },
        {
            "hook_id": "daily_close",
            "table": "venue_daily_closes",
            "outlet_id_nullable": "outlet_id" in close_cols,
            "cost_centre_id_nullable": "cost_centre_id" in close_cols,
            "revenue_centre_id_nullable": "revenue_centre_id" in close_cols,
            "row_count": close_n,
            "empty_ok": True,
            "message": (
                "Daily close hooks may carry nullable outlet_id. Uma close remains "
                "the live path; Rainforest/Pool Bar stay PRE-OPENING."
            ),
        },
        {
            "hook_id": "books_journal_lines",
            "table": "journal_lines (atrium-bzg.sqlite)",
            "outlet_id_nullable": True,
            "cost_centre_id_nullable": False,
            "revenue_centre_id_nullable": False,
            "row_count": None,
            "empty_ok": True,
            "message": (
                "BZG books shell already carries nullable journal_lines.outlet_id "
                "(CORE-BOOKS-1). No fake journals."
            ),
        },
    ]


def foundations_panel(conn: sqlite3.Connection) -> dict[str, Any]:
    """Payload for /bzg/outlets overview — registry + which hooks exist."""
    outlets = _outlets.list_outlets(conn)
    by_status: dict[str, int] = {}
    for o in outlets:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
    hooks = hook_status(conn)
    return {
        **HONESTY,
        "title": "Cross-outlet foundations",
        "hierarchy": (
            "LEGAL_ENTITY → OUTLET → cost_centre_id / revenue_centre_id (nullable hooks)"
        ),
        "hierarchy_usable": True,
        "centres_populated": False,
        "hooks": hooks,
        "hook_ids": list(HOOK_IDS),
        "outlet_count": len(outlets),
        "status_counts": by_status,
        "uma_open": any(
            o["outlet_id"] == "BZG-UMA" and o["status"] == "OPEN" for o in outlets
        ),
        "rainforest_pre_opening": any(
            o["outlet_id"] == "BZG-RAIN" and o["status"] == "PRE-OPENING"
            for o in outlets
        ),
        "pool_bar_pre_opening": any(
            o["outlet_id"] == "OU-BZG-RAIN-POOL" and o["status"] == "PRE-OPENING"
            for o in outlets
        ),
        "sample_hierarchy_uma": hierarchy_usable("BZG-UMA", conn=conn),
        "sample_hierarchy_shared": hierarchy_usable(None, conn=conn),
        "no_multi_outlet_pnl": True,
        "ready": False,
        "message": (
            "Shared foundations can carry outlet_id across BZG outlets. "
            "Honest empty OK — no invented multi-outlet totals."
        ),
    }


def backfill_example_pr_outlet_ids(conn: sqlite3.Connection) -> int:
    """When venue already equals a registry outlet_id, copy into outlet_id.

    Does not invent mappings — only copies identity when already present.
    """
    cols = _table_cols(conn, "bzg_ops_purchase_requests")
    if "outlet_id" not in cols or "venue" not in cols:
        return 0
    known = {o["outlet_id"] for o in _outlets.list_outlets(conn)}
    rows = conn.execute(
        "SELECT pr_id, venue, outlet_id FROM bzg_ops_purchase_requests"
    ).fetchall()
    n = 0
    for pr_id, venue, existing in rows:
        if existing:
            continue
        if venue in known:
            resolve_outlet_ref(venue, conn=conn)
            conn.execute(
                "UPDATE bzg_ops_purchase_requests SET outlet_id=? WHERE pr_id=?",
                (venue, pr_id),
            )
            n += 1
    return n
