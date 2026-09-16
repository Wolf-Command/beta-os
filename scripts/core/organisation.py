#!/usr/bin/env python3
"""Organisation Registry repository — Entity / Brand / Location / Department.

Read-first. No Person / Auth / RBAC. Identity is out of scope for this module.
Beta SQLite only: /Users/wolfterminal/beta-os/catalog/content_library.sqlite
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    # Soft guard: never open outside beta-os
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"org registry refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"org registry refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_entities(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT entity_id, legal_name, display_name, entity_type, status, saleable,
                   created_at, updated_at
            FROM org_entities
            ORDER BY entity_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_entity(entity_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    eid = (entity_id or "").strip()
    if not eid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT entity_id, legal_name, display_name, entity_type, status, saleable,
                       created_at, updated_at
                FROM org_entities WHERE entity_id=?
                """,
                (eid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_brands_by_entity(
    entity_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    eid = (entity_id or "").strip()
    if not eid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
            FROM org_brands WHERE entity_id=? ORDER BY brand_id
            """,
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_brand(brand_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    bid = (brand_id or "").strip()
    if not bid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
                FROM org_brands WHERE brand_id=?
                """,
                (bid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_locations_by_entity(
    entity_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    eid = (entity_id or "").strip()
    if not eid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT location_id, entity_id, display_name, location_type, status, created_at, updated_at
            FROM org_locations WHERE entity_id=? ORDER BY location_id
            """,
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_location(
    location_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    lid = (location_id or "").strip()
    if not lid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT location_id, entity_id, display_name, location_type, status,
                       created_at, updated_at
                FROM org_locations WHERE location_id=?
                """,
                (lid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_departments_by_entity(
    entity_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Entity-owned departments for this entity (SHARED ownership not included here)."""
    eid = (entity_id or "").strip()
    if not eid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT department_id, entity_id, ownership, display_name, status,
                   created_at, updated_at
            FROM org_departments
            WHERE ownership='ENTITY' AND entity_id=?
            ORDER BY department_id
            """,
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()
