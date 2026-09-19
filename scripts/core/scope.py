#!/usr/bin/env python3
"""Organisation Scope repository (Beta).

WHERE an Assignment applies. Structural context only.
Permission decisions, RBAC, and Authority Limits are out of scope.
Scopes attach to Assignments — never directly to Person.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

ALLOWED_TARGET_TYPES = frozenset({"entity", "brand", "location", "department"})


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"scope refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"scope refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_scopes(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT scope_id, scope_type, display_name, status, created_at, updated_at
            FROM org_scopes ORDER BY scope_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_scope(scope_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    sid = (scope_id or "").strip()
    if not sid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT scope_id, scope_type, display_name, status, created_at, updated_at
                FROM org_scopes WHERE scope_id=?
                """,
                (sid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_scope_targets(
    scope_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    sid = (scope_id or "").strip()
    if not sid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT scope_id, target_type, target_id, created_at
            FROM org_scope_targets
            WHERE scope_id=?
            ORDER BY target_type, target_id
            """,
            (sid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_scopes_for_assignment(
    assignment_id: str,
    *,
    include_ended: bool = False,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    aid = (assignment_id or "").strip()
    if not aid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        sql = """
            SELECT asg.assignment_id, asg.scope_id, asg.start_at, asg.end_at, asg.status,
                   asg.created_at, asg.updated_at,
                   s.scope_type, s.display_name AS scope_display_name, s.status AS scope_status
            FROM org_assignment_scopes asg
            JOIN org_scopes s ON s.scope_id = asg.scope_id
            WHERE asg.assignment_id=?
        """
        if not include_ended:
            sql += " AND asg.status='ACTIVE' AND asg.end_at IS NULL"
        sql += " ORDER BY asg.scope_id"
        return [dict(r) for r in c.execute(sql, (aid,)).fetchall()]
    finally:
        if own:
            c.close()


def list_active_scopes_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Via active Assignments only — no Person-direct scope table."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT DISTINCT s.scope_id, s.scope_type, s.display_name, s.status,
                   a.assignment_id
            FROM org_assignments a
            JOIN org_assignment_scopes asg ON asg.assignment_id = a.assignment_id
            JOIN org_scopes s ON s.scope_id = asg.scope_id
            WHERE a.person_id=?
              AND a.status='ACTIVE' AND a.end_at IS NULL
              AND asg.status='ACTIVE' AND asg.end_at IS NULL
              AND s.status='ACTIVE'
            ORDER BY s.scope_id, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def resolve_effective_scope_context(
    scope_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Structural WHERE context only. Does NOT grant permissions.

    Hierarchy intent (documented, not permission-eval):
    - entity target: may later cover that entity's brands/locations/departments
    - brand target: NEVER auto-includes sibling brands
    - location target: NEVER auto-includes unrelated locations
    - department target: that department only
    Legal entities never cross-mix.
    """
    sid = (scope_id or "").strip()
    own = conn is None
    c = conn or db_connect()
    try:
        scope = get_scope(sid, conn=c)
        if not scope:
            return {
                "scope_id": sid,
                "found": False,
                "permission_decision": "NOT_BUILT",
                "inheritance_not_permission": True,
            }
        targets = list_scope_targets(sid, conn=c)
        covered: dict[str, list[str]] = {
            "entities": [],
            "brands": [],
            "locations": [],
            "departments": [],
        }
        notes: list[str] = []

        for t in targets:
            tt = t["target_type"]
            tid = t["target_id"]
            if tt == "entity":
                covered["entities"].append(tid)
                brands = [
                    r[0]
                    for r in c.execute(
                        "SELECT brand_id FROM org_brands WHERE entity_id=? ORDER BY brand_id",
                        (tid,),
                    ).fetchall()
                ]
                locs = [
                    r[0]
                    for r in c.execute(
                        "SELECT location_id FROM org_locations WHERE entity_id=? ORDER BY location_id",
                        (tid,),
                    ).fetchall()
                ]
                deps = [
                    r[0]
                    for r in c.execute(
                        "SELECT department_id FROM org_departments WHERE entity_id=? ORDER BY department_id",
                        (tid,),
                    ).fetchall()
                ]
                covered["brands"].extend(brands)
                covered["locations"].extend(locs)
                covered["departments"].extend(deps)
                notes.append(
                    f"entity {tid}: structural children listed; not a permission grant"
                )
            elif tt == "brand":
                covered["brands"].append(tid)
                # Explicitly do NOT add sibling brands
                row = c.execute(
                    "SELECT entity_id FROM org_brands WHERE brand_id=?", (tid,)
                ).fetchone()
                if row:
                    siblings = [
                        r[0]
                        for r in c.execute(
                            "SELECT brand_id FROM org_brands WHERE entity_id=? AND brand_id!=?",
                            (row[0], tid),
                        ).fetchall()
                    ]
                    notes.append(
                        f"brand {tid}: siblings excluded ({len(siblings)} siblings not covered)"
                    )
                else:
                    notes.append(f"brand {tid}: no sibling expansion")
            elif tt == "location":
                covered["locations"].append(tid)
                notes.append(f"location {tid}: unrelated locations not covered")
            elif tt == "department":
                covered["departments"].append(tid)
                notes.append(f"department {tid}: department only")
            else:
                notes.append(f"unknown target_type {tt} ignored structurally")

        # Dedupe preserve order
        for k in covered:
            seen: set[str] = set()
            out: list[str] = []
            for x in covered[k]:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            covered[k] = out

        return {
            "scope_id": sid,
            "found": True,
            "scope": scope,
            "targets": targets,
            "structurally_covered": covered,
            "inheritance_not_permission": True,
            "permission_decision": "NOT_BUILT",
            "rbac": "NOT_BUILT",
            "authority_limits": "NOT_BUILT",
            "notes": notes,
        }
    finally:
        if own:
            c.close()


def upsert_assignment_scope(
    conn: sqlite3.Connection,
    assignment_id: str,
    scope_id: str,
    start_at: str,
    ts: str,
    *,
    end_at: str | None = None,
    status: str = "ACTIVE",
    revive: bool = False,
) -> None:
    """Insert an assignment-scope. Default: do not revive an ended row.

    On conflict, if the existing row is ENDED or end_at is set, status and
    end_at stay as they are. revive=True forces ACTIVE and clears end_at.
    That flag is Owner-only tooling. Migrate, seed, and test helpers must
    leave it False.
    """
    if revive:
        end_at = None
        status = "ACTIVE"
        conflict = "end_at=NULL, status='ACTIVE', updated_at=excluded.updated_at"
    else:
        conflict = """
          end_at=CASE
            WHEN org_assignment_scopes.status='ENDED'
              OR org_assignment_scopes.end_at IS NOT NULL
            THEN org_assignment_scopes.end_at
            ELSE excluded.end_at
          END,
          status=CASE
            WHEN org_assignment_scopes.status='ENDED'
              OR org_assignment_scopes.end_at IS NOT NULL
            THEN org_assignment_scopes.status
            ELSE excluded.status
          END,
          updated_at=CASE
            WHEN org_assignment_scopes.status='ENDED'
              OR org_assignment_scopes.end_at IS NOT NULL
            THEN org_assignment_scopes.updated_at
            ELSE excluded.updated_at
          END
        """
    conn.execute(
        f"""
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assignment_id, scope_id, start_at) DO UPDATE SET
          {conflict}
        """,
        (assignment_id, scope_id, start_at, end_at, status, ts, ts),
    )
