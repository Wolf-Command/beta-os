#!/usr/bin/env python3
"""Organisation Role / Position / Assignment repository (Beta).

Uses org_roles / org_positions / org_assignments — not LLM routing "role".
Permission engines are out of scope for this module. Scope lives in core.scope.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"staffing refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"staffing refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_roles(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT role_id, display_name, department_id, role_type, status,
                   created_at, updated_at
            FROM org_roles ORDER BY role_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_role(role_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    rid = (role_id or "").strip()
    if not rid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT role_id, display_name, department_id, role_type, status,
                       created_at, updated_at
                FROM org_roles WHERE role_id=?
                """,
                (rid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_positions(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions ORDER BY position_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_positions_by_entity(
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
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions WHERE entity_id=? ORDER BY position_id
            """,
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_positions_by_role(
    role_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    rid = (role_id or "").strip()
    if not rid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions WHERE role_id=? ORDER BY position_id
            """,
            (rid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_position(position_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    pid = (position_id or "").strip()
    if not pid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                       position_label, status, fte, created_at, updated_at
                FROM org_positions WHERE position_id=?
                """,
                (pid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_active_assignments_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   p.position_label, p.entity_id, p.role_id, r.display_name AS org_role_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_assignments_for_person(
    person_id: str, *, include_ended: bool = True, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        sql = """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   p.position_label, p.entity_id, p.role_id, r.display_name AS org_role_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id=?
        """
        if not include_ended:
            sql += " AND a.status='ACTIVE' AND a.end_at IS NULL"
        sql += " ORDER BY a.start_at DESC, a.assignment_id"
        return [dict(r) for r in c.execute(sql, (pid,)).fetchall()]
    finally:
        if own:
            c.close()


def list_assignments_for_position(
    position_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (position_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   per.display_name AS person_display_name
            FROM org_assignments a
            JOIN org_persons per ON per.person_id = a.person_id
            WHERE a.position_id=?
            ORDER BY a.start_at DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_current_occupants(
    position_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (position_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.is_primary, a.start_at,
                   per.display_name AS person_display_name
            FROM org_assignments a
            JOIN org_persons per ON per.person_id = a.person_id
            WHERE a.position_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def resolve_org_context_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Active Assignment → Position → org Role + Assignment Scopes (not LLM role)."""
    active = list_active_assignments_for_person(person_id, conn=conn)
    # Import locally to avoid circular import at module load
    from core import scope as _scope  # type: ignore
    scopes = _scope.list_active_scopes_for_person(person_id, conn=conn)
    return {
        "person_id": person_id,
        "active_assignments": active,
        "scopes": scopes,
        "scope": scopes,  # transitional alias; was "NOT_BUILT"
        "rbac": "NOT_BUILT",
    }
