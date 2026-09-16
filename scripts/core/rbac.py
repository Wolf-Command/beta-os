#!/usr/bin/env python3
"""Wolf Core RBAC — deterministic scope-aware permission evaluator (Beta).

WHAT an Assignment may do. WHERE comes from core.scope.
AI/LLM never decides access. Deny by default.
Authority Limits and real CF auth are NOT BUILT.
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
        raise RuntimeError(f"rbac refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"rbac refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def get_permission_by_code(
    code: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    cde = (code or "").strip()
    if not cde:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT permission_id, code, resource, action, description, status
                FROM org_permissions WHERE code=? AND status='ACTIVE'
                """,
                (cde,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def resolve_legacy_to_code(
    legacy_or_code: str, conn: sqlite3.Connection | None = None
) -> str | None:
    """Map can_* → canonical code; pass through if already canonical."""
    raw = (legacy_or_code or "").strip()
    if not raw:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        if get_permission_by_code(raw, conn=c):
            return raw
        row = c.execute(
            """
            SELECT p.code
            FROM org_permission_legacy_map m
            JOIN org_permissions p ON p.permission_id = m.permission_id
            WHERE m.legacy_code=? AND p.status='ACTIVE'
            """,
            (raw,),
        ).fetchone()
        return row[0] if row else None
    finally:
        if own:
            c.close()


def list_permissions(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        return [
            dict(r)
            for r in c.execute(
                """
                SELECT permission_id, code, resource, action, description, status,
                       created_at, updated_at
                FROM org_permissions ORDER BY code
                """
            ).fetchall()
        ]
    finally:
        if own:
            c.close()


def list_role_permission_grants(
    role_id: str | None = None, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        if role_id:
            rows = c.execute(
                """
                SELECT rp.role_id, rp.permission_id, rp.effect, p.code
                FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE rp.role_id=?
                ORDER BY p.code
                """,
                (role_id,),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT rp.role_id, rp.permission_id, rp.effect, p.code
                FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                ORDER BY rp.role_id, p.code
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def _scope_covers_target(
    scope_id: str,
    target: dict[str, Any] | None,
    conn: sqlite3.Connection,
) -> bool:
    """Structural WHERE check. Empty target → require any ACTIVE scope on the assignment path
    that is GGV content-relevant OR any entity/dept/brand/location scope (caller decides).

    Rules:
    - No target keys → True if scope has at least one target (assignment is scoped somewhere).
    - entity_id required → covered if scope targets that entity OR (via entity scope expansion)
      a department/brand/location under that entity is enough ONLY when target also names that
      child; entity target on scope covers entity_id match and children of that entity.
    - brand_id → scope must target that brand OR an entity that owns that brand.
    - location_id → that location OR owning entity.
    - department_id → that department OR owning entity.
    - Never: sibling brand via other brand; never cross legal entity.
    """
    from core import scope as _scope

    ctx = _scope.resolve_effective_scope_context(scope_id, conn=conn)
    if not ctx.get("found"):
        return False
    covered = ctx.get("structurally_covered") or {}
    target = target or {}

    # If caller provided no target context, any valid scope counts as WHERE present
    if not any(target.get(k) for k in ("entity_id", "brand_id", "location_id", "department_id")):
        return bool(ctx.get("targets"))

    eid = (target.get("entity_id") or "").strip()
    bid = (target.get("brand_id") or "").strip()
    lid = (target.get("location_id") or "").strip()
    did = (target.get("department_id") or "").strip()

    ents = set(covered.get("entities") or [])
    brands = set(covered.get("brands") or [])
    locs = set(covered.get("locations") or [])
    deps = set(covered.get("departments") or [])

    # Child checks first
    if bid and bid not in brands:
        return False
    if lid and lid not in locs:
        return False
    if did and did not in deps:
        return False

    if eid:
        if eid in ents:
            pass  # entity scope covers
        else:
            # Department/brand/location scope may cover without listing entity
            # only if a provided child key is covered AND belongs to eid
            child_hit = False
            if did and did in deps:
                row = conn.execute(
                    "SELECT entity_id FROM org_departments WHERE department_id=?", (did,)
                ).fetchone()
                child_hit = bool(row and row[0] == eid)
            if bid and bid in brands:
                row = conn.execute(
                    "SELECT entity_id FROM org_brands WHERE brand_id=?", (bid,)
                ).fetchone()
                child_hit = child_hit or bool(row and row[0] == eid)
            if lid and lid in locs:
                row = conn.execute(
                    "SELECT entity_id FROM org_locations WHERE location_id=?", (lid,)
                ).fetchone()
                child_hit = child_hit or bool(row and row[0] == eid)
            if not child_hit:
                return False

    # If only entity provided (no children), entity must be in covered entities
    if eid and not (bid or lid or did) and eid not in ents:
        return False

    return True


def evaluate(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Canonical evaluator. Returns explainable decision dict. Deny by default.

    Does NOT use AI. Does NOT check Authority Limits (NOT BUILT).
    """
    explanation: dict[str, Any] = {
        "person_id": person_id,
        "permission_code": permission_code,
        "target_context": target_context or {},
        "allowed": False,
        "reason": "deny_by_default",
        "paths": [],
        "authority_limits": "NOT_BUILT",
        "real_authentication": False,
        "evaluator": "core.rbac.evaluate",
    }
    pid = (person_id or "").strip()
    code_in = (permission_code or "").strip()
    if not pid or not code_in:
        explanation["reason"] = "missing_person_or_permission"
        return explanation

    own = conn is None
    c = conn or db_connect()
    try:
        code = resolve_legacy_to_code(code_in, conn=c)
        if not code:
            explanation["reason"] = "unknown_permission"
            return explanation
        explanation["permission_code"] = code
        perm = get_permission_by_code(code, conn=c)
        if not perm:
            explanation["reason"] = "unknown_permission"
            return explanation
        explanation["permission_id"] = perm["permission_id"]

        # Active assignments
        asgs = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.status, a.end_at,
                   p.role_id, p.entity_id AS position_entity_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.person_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            """,
            (pid,),
        ).fetchall()
        if not asgs:
            explanation["reason"] = "no_active_assignment"
            return explanation

        target = target_context or {}
        for asg in asgs:
            role_id = asg["role_id"]
            grant = c.execute(
                """
                SELECT effect FROM org_role_permissions
                WHERE role_id=? AND permission_id=? AND effect='ALLOW'
                """,
                (role_id, perm["permission_id"]),
            ).fetchone()
            if not grant:
                explanation["paths"].append(
                    {
                        "assignment_id": asg["assignment_id"],
                        "role_id": role_id,
                        "permission": False,
                        "scope": None,
                    }
                )
                continue

            # Scopes for this assignment
            scopes = c.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id=?
                  AND status='ACTIVE'
                  AND end_at IS NULL
                """,
                (asg["assignment_id"],),
            ).fetchall()
            if not scopes:
                explanation["paths"].append(
                    {
                        "assignment_id": asg["assignment_id"],
                        "role_id": role_id,
                        "permission": True,
                        "scope": False,
                        "note": "permission_without_scope",
                    }
                )
                continue

            scope_ok = False
            matched_scope = None
            for srow in scopes:
                sid = srow["scope_id"]
                if _scope_covers_target(sid, target, c):
                    scope_ok = True
                    matched_scope = sid
                    break

            explanation["paths"].append(
                {
                    "assignment_id": asg["assignment_id"],
                    "role_id": role_id,
                    "permission": True,
                    "scope": scope_ok,
                    "matched_scope_id": matched_scope,
                }
            )
            if scope_ok:
                explanation["allowed"] = True
                explanation["reason"] = "allow"
                explanation["matched"] = {
                    "assignment_id": asg["assignment_id"],
                    "role_id": role_id,
                    "scope_id": matched_scope,
                    "permission_id": perm["permission_id"],
                }
                return explanation

        if any(p.get("permission") and p.get("scope") is False for p in explanation["paths"]):
            explanation["reason"] = "permission_without_matching_scope"
        elif any(p.get("permission") is False for p in explanation["paths"]):
            explanation["reason"] = "role_lacks_permission"
        else:
            explanation["reason"] = "deny_by_default"
        return explanation
    finally:
        if own:
            c.close()


def can(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> bool:
    return bool(
        evaluate(person_id, permission_code, target_context, conn=conn).get("allowed")
    )


def effective_permissions_for_person(
    person_id: str,
    target_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[str]:
    """Union of permission codes allowed for person under target_context."""
    own = conn is None
    c = conn or db_connect()
    try:
        codes = [r["code"] for r in list_permissions(conn=c) if r["status"] == "ACTIVE"]
        out = []
        for code in codes:
            if can(person_id, code, target_context, conn=c):
                out.append(code)
        return out
    finally:
        if own:
            c.close()


def default_content_target() -> dict[str, str]:
    """Content Machine ops live under GGV Content department structurally."""
    return {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
