#!/usr/bin/env python3
"""005 Organisation Registry — idempotent Beta-only migration.

Seeds Entity / Brand / Location / Department from approved canon CSVs.
Does NOT invent GGV-owned client brands. Does NOT model Wolf IP as Entity.
Does NOT touch production / wolf-system.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "005_org_registry.sql"
MIGRATION_ID = "005_org_registry"

# Forbidden paths — refuse if somehow pointed elsewhere
FORBIDDEN_DB_FRAGMENTS = ("wolf-system", "money.sqlite", "/Production")

TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return col in {r[1] for r in rows}


def add_col(conn: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    if not col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        print(f"  + {table}.{col}")
    else:
        print(f"  = {table}.{col} exists")


def upsert_entity(conn, entity_id, legal_name, display_name, entity_type, status, saleable, ts):
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(entity_id) DO UPDATE SET
          legal_name=excluded.legal_name,
          display_name=excluded.display_name,
          entity_type=excluded.entity_type,
          status=excluded.status,
          saleable=excluded.saleable,
          updated_at=excluded.updated_at
        """,
        (entity_id, legal_name, display_name, entity_type, status, saleable, ts, ts),
    )


def upsert_brand(conn, brand_id, entity_id, display_name, brand_type, status, ts):
    conn.execute(
        """
        INSERT INTO org_brands (
          brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand_id) DO UPDATE SET
          entity_id=excluded.entity_id,
          display_name=excluded.display_name,
          brand_type=excluded.brand_type,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (brand_id, entity_id, display_name, brand_type, status, ts, ts),
    )


def upsert_location(conn, location_id, entity_id, display_name, location_type, status, ts):
    conn.execute(
        """
        INSERT INTO org_locations (
          location_id, entity_id, display_name, location_type, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(location_id) DO UPDATE SET
          entity_id=excluded.entity_id,
          display_name=excluded.display_name,
          location_type=excluded.location_type,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (location_id, entity_id, display_name, location_type, status, ts, ts),
    )


def upsert_brand_location(conn, brand_id, location_id, ts):
    conn.execute(
        """
        INSERT INTO org_brand_locations (brand_id, location_id, status, created_at)
        VALUES (?, ?, 'ACTIVE', ?)
        ON CONFLICT(brand_id, location_id) DO UPDATE SET status='ACTIVE'
        """,
        (brand_id, location_id, ts),
    )


def upsert_department(conn, department_id, entity_id, ownership, display_name, status, ts):
    conn.execute(
        """
        INSERT INTO org_departments (
          department_id, entity_id, ownership, display_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(department_id) DO UPDATE SET
          entity_id=excluded.entity_id,
          ownership=excluded.ownership,
          display_name=excluded.display_name,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (department_id, entity_id, ownership, display_name, status, ts, ts),
    )


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN_DB_FRAGMENTS:
        if frag in s:
            print(f"REFUSE: DB path looks like production ({frag}): {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: DB must live under beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        ddl = SQL.read_text(encoding="utf-8")
        conn.executescript(ddl)
        print("DDL applied")

        # --- Entities (Organisation.csv; NO IP-WOLF) ---
        upsert_entity(conn, "ENT-GGV", "Goss Group Ventures", "GGV", "LEGAL_ENTITY", "LIVE", 1, ts)
        upsert_entity(conn, "ENT-AMG", "Atrium Management Group", "AMG", "LEGAL_ENTITY", "LIVE", 1, ts)
        upsert_entity(conn, "ENT-BZG", "Blu Zone Group", "BZG", "LEGAL_ENTITY", "LIVE", 1, ts)

        # --- Brands (Brands_Locations.csv Unit IDs only; no client brands) ---
        brands = [
            ("BZG-UMA", "ENT-BZG", "Uma Blu Brunch Cafe", "VENUE", "LIVE"),
            ("BZG-RAIN", "ENT-BZG", "Blu Zone Rainforest Restaurant & Bar", "VENUE", "APPROVED"),
            ("BZG-MERAH", "ENT-BZG", "Merah Underground Nightclub and Bar", "VENUE", "APPROVED"),
            ("BZG-ROOF", "ENT-BZG", "Rooftop Bar - name TBD", "VENUE", "APPROVED"),
            ("BZG-CAT", "ENT-BZG", "Catering", "BUSINESS_UNIT", "SPECIFIED"),
            ("BZG-RS", "ENT-BZG", "Room Service", "BUSINESS_UNIT", "SPECIFIED"),
            ("AMG-ATR", "ENT-AMG", "Atrium Lombok", "HOTEL_PROPERTY", "LIVE"),
        ]
        for row in brands:
            upsert_brand(conn, *row, ts)

        # --- Location (primary steward AMG) ---
        upsert_location(conn, "LOC-ATRIUM-LOMBOK", "ENT-AMG", "Atrium Lombok", "PROPERTY", "LIVE", ts)
        for bid, *_ in brands:
            upsert_brand_location(conn, bid, "LOC-ATRIUM-LOMBOK", ts)

        # --- Departments (separate ENG rows; shared services later) ---
        upsert_department(conn, "DEPT-AMG-EXEC", "ENT-AMG", "ENTITY", "Executive", "ACTIVE", ts)
        upsert_department(conn, "DEPT-BZG-FB", "ENT-BZG", "ENTITY", "F&B", "ACTIVE", ts)
        upsert_department(conn, "DEPT-GGV-CONTENT", "ENT-GGV", "ENTITY", "Content", "ACTIVE", ts)
        upsert_department(conn, "DEPT-AMG-ENG", "ENT-AMG", "ENTITY", "Engineering", "ACTIVE", ts)
        upsert_department(conn, "DEPT-BZG-ENG", "ENT-BZG", "ENTITY", "Engineering", "ACTIVE", ts)

        # --- Content Machine compatibility columns ---
        add_col(conn, "brands", "org_brand_id", "TEXT")
        add_col(conn, "brand_external_ids", "org_brand_id", "TEXT")

        # Map only legally owned Metricool keys → org brands
        # habitat / selo / tropik remain NULL (client brands — not GGV-owned)
        conn.execute(
            "UPDATE brand_external_ids SET org_brand_id='BZG-UMA' WHERE brand_key='umablu'"
        )
        conn.execute(
            "UPDATE brand_external_ids SET org_brand_id='AMG-ATR' WHERE brand_key='atrium'"
        )
        # Explicitly clear client keys if previously wrong (idempotent safety)
        conn.execute(
            """
            UPDATE brand_external_ids
            SET org_brand_id=NULL
            WHERE brand_key IN ('habitat', 'selo', 'tropik')
            """
        )
        # Content brands.habitat stays; org_brand_id NULL (client)
        if col_exists(conn, "brands", "org_brand_id"):
            conn.execute(
                "UPDATE brands SET org_brand_id=NULL WHERE id='habitat' AND org_brand_id IS NOT NULL"
            )

        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, "Organisation Registry Entity/Brand/Location/Department"),
        )
        conn.commit()

        print("--- counts ---")
        for t in (
            "org_entities",
            "org_brands",
            "org_locations",
            "org_brand_locations",
            "org_departments",
            "brands",
            "brand_external_ids",
            "permissions",
            "assets",
        ):
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}={n}")
        print("--- brand ownership ---")
        for r in conn.execute(
            "SELECT brand_id, entity_id, display_name, status FROM org_brands ORDER BY brand_id"
        ):
            print(f"  {r['brand_id']} → {r['entity_id']} | {r['display_name']} | {r['status']}")
        print("--- external map ---")
        for r in conn.execute(
            "SELECT brand_key, org_brand_id FROM brand_external_ids ORDER BY brand_key"
        ):
            print(f"  {r['brand_key']} → {r['org_brand_id']}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
