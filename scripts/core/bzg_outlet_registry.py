#!/usr/bin/env python3
"""BZG-OUTLET-1 — Canonical BZG Outlet Registry + hierarchy helpers.

LEGAL ENTITY → OUTLET (brand / operating unit) → cost/revenue centre hooks.
Statuses are explicit registry truth only — never invent sales, costs, covers,
or go-live numbers. Pool Bar is OU-BZG-RAIN-POOL under BZG-RAIN (not a brand).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core import rbac as _rbac
from core import scope as _scope

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

LEGAL_ENTITY = "ENT-BZG"
PACK = "BZG-OUTLET-1"

ALLOWED_STATUSES = frozenset(
    {
        "OPEN",
        "PRE-OPENING",
        "COMMISSIONING",
        "TEMPORARILY CLOSED",
        "CLOSED",
    }
)

OUTLET_KINDS = frozenset({"BRAND", "OPERATING_UNIT"})

PAGE_PATHS = frozenset(
    {
        "/bzg/outlets",
        "/bzg/outlets/",
        "/bzg-outlets",
        "/bzg-outlets.html",
        "/dashboards/bzg-outlets.html",
    }
)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "invented_sales": False,
    "invented_costs": False,
    "invented_covers": False,
    "invented_pnl": False,
    "invented_go_live_numbers": False,
    "money_movement": False,
    "proven": False,
    "legal_entity_id": LEGAL_ENTITY,
    "pack": PACK,
}

# Seed rows — statuses chosen honestly (see RESULT). No ops metrics.
SEED: tuple[dict[str, Any], ...] = (
    {
        "outlet_id": "BZG-UMA",
        "display_name": "Uma Blu",
        "brand_id": "BZG-UMA",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "OPEN",
        "note": "Primary operating outlet. Brand status LIVE maps to registry OPEN.",
    },
    {
        "outlet_id": "BZG-RAIN",
        "display_name": "Rainforest",
        "brand_id": "BZG-RAIN",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "PRE-OPENING",
        "note": (
            "Target ~7 Oct 2026. PRE-OPENING — no human F&B commissioning evidence "
            "for this outlet; do not invent live ops."
        ),
    },
    {
        "outlet_id": "OU-BZG-RAIN-POOL",
        "display_name": "Pool Bar",
        "brand_id": "BZG-RAIN",
        "operating_unit_id": "OU-BZG-RAIN-POOL",
        "parent_outlet_id": "BZG-RAIN",
        "outlet_kind": "OPERATING_UNIT",
        "status": "PRE-OPENING",
        "note": (
            "Measurable operating unit under Rainforest. Not a second brand_id. "
            "PRE-OPENING until human confirm."
        ),
    },
    {
        "outlet_id": "BZG-MERAH",
        "display_name": "Merah",
        "brand_id": "BZG-MERAH",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "PRE-OPENING",
        "note": "Future config row (brand APPROVED). Not OPEN. No fake ops.",
    },
    {
        "outlet_id": "BZG-ROOF",
        "display_name": "Rooftop",
        "brand_id": "BZG-ROOF",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "PRE-OPENING",
        "note": "Future config row (brand APPROVED). Not OPEN. No fake ops.",
    },
    {
        "outlet_id": "BZG-RS",
        "display_name": "Room Service",
        "brand_id": "BZG-RS",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "PRE-OPENING",
        "note": "Future config row (brand SPECIFIED). Not OPEN. No fake ops.",
    },
    {
        "outlet_id": "BZG-CAT",
        "display_name": "Catering",
        "brand_id": "BZG-CAT",
        "operating_unit_id": None,
        "parent_outlet_id": None,
        "outlet_kind": "BRAND",
        "status": "PRE-OPENING",
        "note": "Future config row (brand SPECIFIED). Not OPEN. No fake ops.",
    },
)


class BzgOutletError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"bzg_outlet_registry refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"bzg_outlet_registry refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _has_registry(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='org_outlet_registry'"
        ).fetchone()
        is not None
    )


def ensure_schema(conn: sqlite3.Connection) -> None:
    """DDL — migrate / write paths only. Read paths must not call this under RO authorizers."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS org_outlet_registry (
          outlet_id TEXT PRIMARY KEY,
          legal_entity_id TEXT NOT NULL,
          brand_id TEXT,
          operating_unit_id TEXT,
          parent_outlet_id TEXT,
          display_name TEXT NOT NULL,
          outlet_kind TEXT NOT NULL,
          status TEXT NOT NULL,
          cost_centre_id TEXT,
          revenue_centre_id TEXT,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          CHECK (status IN (
            'OPEN','PRE-OPENING','COMMISSIONING','TEMPORARILY CLOSED','CLOSED'
          )),
          CHECK (outlet_kind IN ('BRAND','OPERATING_UNIT'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_org_outlet_registry_entity
        ON org_outlet_registry(legal_entity_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_org_outlet_registry_brand
        ON org_outlet_registry(brand_id)
        """
    )


def seed_registry(conn: sqlite3.Connection, ts: str) -> int:
    """Idempotent seed. Does not invent ops metrics."""
    ensure_schema(conn)
    n = 0
    for row in SEED:
        status = row["status"]
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"illegal status {status}")
        if row["outlet_kind"] not in OUTLET_KINDS:
            raise ValueError(f"illegal kind {row['outlet_kind']}")
        conn.execute(
            """
            INSERT INTO org_outlet_registry (
              outlet_id, legal_entity_id, brand_id, operating_unit_id,
              parent_outlet_id, display_name, outlet_kind, status,
              cost_centre_id, revenue_centre_id, note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
            ON CONFLICT(outlet_id) DO UPDATE SET
              legal_entity_id=excluded.legal_entity_id,
              brand_id=excluded.brand_id,
              operating_unit_id=excluded.operating_unit_id,
              parent_outlet_id=excluded.parent_outlet_id,
              display_name=excluded.display_name,
              outlet_kind=excluded.outlet_kind,
              status=excluded.status,
              note=excluded.note,
              updated_at=excluded.updated_at
            """,
            (
                row["outlet_id"],
                LEGAL_ENTITY,
                row["brand_id"],
                row["operating_unit_id"],
                row["parent_outlet_id"],
                row["display_name"],
                row["outlet_kind"],
                status,
                row["note"],
                ts,
                ts,
            ),
        )
        n += 1
    return n


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_outlets(
    conn: sqlite3.Connection | None = None,
    *,
    legal_entity_id: str = LEGAL_ENTITY,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_registry(c):
            return []
        rows = c.execute(
            """
            SELECT outlet_id, legal_entity_id, brand_id, operating_unit_id,
                   parent_outlet_id, display_name, outlet_kind, status,
                   cost_centre_id, revenue_centre_id, note,
                   created_at, updated_at
            FROM org_outlet_registry
            WHERE legal_entity_id=?
            ORDER BY
              CASE status
                WHEN 'OPEN' THEN 0
                WHEN 'COMMISSIONING' THEN 1
                WHEN 'PRE-OPENING' THEN 2
                WHEN 'TEMPORARILY CLOSED' THEN 3
                WHEN 'CLOSED' THEN 4
                ELSE 5
              END,
              outlet_kind ASC,
              outlet_id ASC
            """,
            (legal_entity_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_outlet(
    outlet_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    oid = (outlet_id or "").strip()
    if not oid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_registry(c):
            return None
        return _row(
            c.execute(
                """
                SELECT outlet_id, legal_entity_id, brand_id, operating_unit_id,
                       parent_outlet_id, display_name, outlet_kind, status,
                       cost_centre_id, revenue_centre_id, note,
                       created_at, updated_at
                FROM org_outlet_registry WHERE outlet_id=?
                """,
                (oid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def hierarchy_for_outlet(
    outlet_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    """LEGAL ENTITY → OUTLET → cost/revenue centre hooks (nullable)."""
    row = get_outlet(outlet_id, conn=conn)
    if not row:
        return None
    return {
        "legal_entity_id": row["legal_entity_id"],
        "outlet_id": row["outlet_id"],
        "brand_id": row["brand_id"],
        "operating_unit_id": row["operating_unit_id"],
        "parent_outlet_id": row["parent_outlet_id"],
        "outlet_kind": row["outlet_kind"],
        "status": row["status"],
        "cost_centre_id": row["cost_centre_id"],
        "revenue_centre_id": row["revenue_centre_id"],
        "display_name": row["display_name"],
    }


def outlets_for_brands(
    brand_ids: list[str] | set[str],
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    bids = [b for b in brand_ids if b]
    if not bids:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_registry(c):
            return []
        placeholders = ",".join("?" * len(bids))
        rows = c.execute(
            f"""
            SELECT outlet_id, legal_entity_id, brand_id, operating_unit_id,
                   parent_outlet_id, display_name, outlet_kind, status,
                   cost_centre_id, revenue_centre_id, note,
                   created_at, updated_at
            FROM org_outlet_registry
            WHERE brand_id IN ({placeholders})
            ORDER BY outlet_id
            """,
            tuple(bids),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def outlets_covered_by_scope(
    scope_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Resolve outlets via scope → entity/brand hierarchy — no outlet name lists."""
    own = conn is None
    c = conn or db_connect()
    try:
        ctx = _scope.resolve_effective_scope_context(scope_id, conn=c)
        if not ctx.get("found"):
            return []
        covered = ctx.get("structurally_covered") or {}
        # Prefer outlets already expanded by scope.py; fall back to brand join.
        outlet_ids = list(covered.get("outlets") or [])
        if outlet_ids:
            out: list[dict[str, Any]] = []
            for oid in outlet_ids:
                row = get_outlet(oid, conn=c)
                if row:
                    out.append(row)
            return out
        brands = list(covered.get("brands") or [])
        entities = list(covered.get("entities") or [])
        if LEGAL_ENTITY in entities or any(
            b.startswith("BZG-") for b in brands
        ):
            if LEGAL_ENTITY in entities:
                return list_outlets(c, legal_entity_id=LEGAL_ENTITY)
            return outlets_for_brands(brands, conn=c)
        return outlets_for_brands(brands, conn=c)
    finally:
        if own:
            c.close()


def outlets_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Hariyanto / Devi / any seated person: outlets via active scope hierarchy."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        scopes = _scope.list_active_scopes_for_person(pid, conn=c)
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for s in scopes:
            for row in outlets_covered_by_scope(s["scope_id"], conn=c):
                oid = row["outlet_id"]
                if oid not in seen:
                    seen.add(oid)
                    out.append(row)
        return out
    finally:
        if own:
            c.close()


def person_may_read_registry(
    person_id: str | None, conn: sqlite3.Connection
) -> bool:
    pid = (person_id or "").strip()
    if not pid:
        return False
    if _rbac.can(pid, "progress.read", {}, conn=conn):
        return True
    # Any active BZG hierarchy membership (entity / brand / FB / finance).
    return len(outlets_for_person(pid, conn=conn)) > 0


def matches(path: str) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    if trimmed.startswith("/api/bzg/outlets"):
        return True
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def require_read(person_id: str | None, conn: sqlite3.Connection) -> None:
    if not person_may_read_registry(person_id, conn):
        raise BzgOutletError(
            "BZG Outlet Registry is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def overview(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    require_read(person_id, conn)
    outlets = list_outlets(conn)
    covered = outlets_for_person(person_id, conn)
    covered_ids = {o["outlet_id"] for o in covered}
    # Owner sees all; others see hierarchy-covered subset with full registry list
    # marked for membership (honest — no fake totals).
    # BZG-XOUTLET-1: shared foundations panel (vendors / PR / close hooks).
    from core import bzg_xoutlet_foundations as _xout  # local import avoids cycle

    foundations = _xout.foundations_panel(conn)
    from core import bzg_venue_pnl as _vpnl

    venue_pnl = _vpnl.rollup_panel_for_outlets()
    return {
        **HONESTY,
        "ok": True,
        "title": "BZG Outlet Registry",
        "message": (
            "Canonical BZG outlets under ENT-BZG. Statuses only — no invented "
            "sales, costs, covers, or P&L. Pool Bar is OU-BZG-RAIN-POOL under BZG-RAIN. "
            "Cross-outlet shared foundations carry nullable outlet_id (honest empty OK). "
            "Venue P&L rollup at /bzg/venue-pnl (facts only; UNKNOWN when absent)."
        ),
        "hierarchy": "LEGAL_ENTITY → OUTLET → cost_centre_id / revenue_centre_id (nullable)",
        "allowed_statuses": sorted(ALLOWED_STATUSES),
        "outlets": outlets,
        "covered_outlet_ids": sorted(covered_ids),
        "open_count": sum(1 for o in outlets if o["status"] == "OPEN"),
        "non_open_count": sum(1 for o in outlets if o["status"] != "OPEN"),
        "empty_ops_metrics": True,
        "pool_bar_operating_unit_id": "OU-BZG-RAIN-POOL",
        "pool_bar_parent_brand_id": "BZG-RAIN",
        "cross_outlet_foundations": foundations,
        "venue_pnl_rollup": venue_pnl,
        "pack_xoutlet": "BZG-XOUTLET-1",
        "pack_venuepl": "BZG-VENUEPL-1",
    }


def dispatch(
    method: str,
    path: str,
    person_id: str | None,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    raw = (path or "").split("?")[0]
    trimmed = raw.rstrip("/") or "/"
    if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
        require_read(person_id, conn)
        return {"_html": True}
    if not trimmed.startswith("/api/bzg/outlets"):
        raise BzgOutletError("Not found.", code="not_found", http_status=404)
    if method != "GET":
        raise BzgOutletError(
            "Outlet registry writes are not opened on this pack.",
            code="method_not_allowed",
            http_status=405,
        )
    rest = trimmed[len("/api/bzg/outlets") :] or "/"
    if rest in {"", "/", "/overview", "/list"}:
        return overview(person_id or "", conn)
    if rest in {"/foundations", "/foundations/"}:
        require_read(person_id, conn)
        from core import bzg_xoutlet_foundations as _xout

        return {**_xout.foundations_panel(conn), "ok": True}
    if rest.startswith("/"):
        oid = rest.strip("/")
        if "/" not in oid and oid and oid != "foundations":
            require_read(person_id, conn)
            row = get_outlet(oid, conn=conn)
            if not row:
                raise BzgOutletError("Outlet not found.", code="not_found", http_status=404)
            return {
                **HONESTY,
                "ok": True,
                "outlet": row,
                "hierarchy": hierarchy_for_outlet(oid, conn=conn),
            }
    raise BzgOutletError("Not found.", code="not_found", http_status=404)


def page_path() -> Path:
    return BETA_ROOT / "dashboards" / "bzg-outlets.html"
