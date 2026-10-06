#!/usr/bin/env python3
"""Server-side read gate for Owner cockpit, God Mode, AMG state, and person records.

Client hiding is not authorization. Decisions use Person → Assignment → Role →
Scope → Permission. A missing catalog fails closed.

Owner cockpit and God Mode reuse the Owner Command rule: PERS-MATT and
progress.read on the default GGV content target. That target is not a blanket
for reading arbitrary people.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

OWNER_PERSON = "PERS-MATT"
ENTITY_AMG = "ENT-AMG"
OWNER_PERMISSION = "progress.read"
PERSON_PERMISSION = "organisation.person.read"
AMG_PERMISSIONS = ("atrium.board.read", "amg.day.operator")

_OWNER_PAGES = frozenset(
    {
        "/owner/trading",
        "/owner/fitness",
        "/owner/radar",
        "/owner/god-mode",
        "/owner/travel",
        "/owner/learning",
        "/god-mode-completion",
    }
)
_AMG_PREFIXES = (
    "/api/amg/sales-desk",
    "/amg/sales-desk",
    "/amg-sales-desk",
    "/api/amg/guest-stay",
    "/amg/guest-stay",
    "/amg-guest-stay",
)


def _norm(path: str | None) -> str:
    raw = (path or "").split("?", 1)[0].rstrip("/")
    return raw or "/"


def classify_open_route(path: str | None) -> str | None:
    """Return owner_cockpit, god_mode, or amg_state when the route was historically open."""
    p = _norm(path)
    for prefix in _AMG_PREFIXES:
        base = prefix.rstrip("/")
        if p == base or p.startswith(base + "/"):
            return "amg_state"
    if "god-mode" in p:
        return "god_mode"
    if p.startswith("/api/owner/") or p in _OWNER_PAGES:
        return "owner_cockpit"
    return None


def _person_id(identity: dict[str, Any] | None) -> str:
    if not identity or not identity.get("ok"):
        return ""
    return str(identity.get("person_id") or "").strip()


def open_decision_conn():
    """Catalog connection for a pure decision. BETA_SCOPED_AUTH_DB overrides the default."""
    from core import identity as ident

    raw = (os.environ.get("BETA_SCOPED_AUTH_DB") or "").strip()
    if raw:
        return ident.db_connect(Path(raw))
    return ident.db_connect()


def is_owner(person_id: str | None, conn) -> bool:
    """PERS-MATT and progress.read on the same target Owner Command already uses.

    An empty target would allow any scoped grant. That is wider than
    has_permission(progress.read), which uses the GGV content target.
    """
    pid = (person_id or "").strip()
    if pid != OWNER_PERSON:
        return False
    from core import rbac

    return bool(rbac.can(pid, OWNER_PERMISSION, rbac.default_content_target(), conn=conn))


def amg_state_allowed(person_id: str | None, conn) -> bool:
    pid = (person_id or "").strip()
    if not pid:
        return False
    if is_owner(pid, conn):
        return True
    from core import rbac

    target = {"entity_id": ENTITY_AMG}
    return any(rbac.can(pid, code, target, conn=conn) for code in AMG_PERMISSIONS)


def assignment_entities(person_id: str, conn) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT p.entity_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE a.person_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        """,
        ((person_id or "").strip(),),
    ).fetchall()
    out: list[str] = []
    for row in rows:
        eid = row["entity_id"] if hasattr(row, "keys") else row[0]
        if eid and str(eid) not in out:
            out.append(str(eid))
    return out


def person_record_allowed(actor_id: str | None, target_id: str | None, conn) -> bool:
    """Self, Owner, or organisation.person.read on one of the target's assignment entities."""
    actor = (actor_id or "").strip()
    target = (target_id or "").strip()
    if not actor or not target:
        return False
    if actor == target:
        return True
    if is_owner(actor, conn):
        return True
    entities = assignment_entities(target, conn)
    if not entities:
        return False
    from core import rbac

    return any(
        rbac.can(actor, PERSON_PERMISSION, {"entity_id": eid}, conn=conn) for eid in entities
    )


def visible_persons(actor_id: str | None, persons: list[dict[str, Any]], conn) -> list[dict[str, Any]] | None:
    """None means the actor may see the full list. A list is the scoped subset.

    An empty list with the caller not allowed to hold the permission is signalled
    by person_list_allowed() == False. This function assumes the caller already
    passed that check or is the owner.
    """
    actor = (actor_id or "").strip()
    if is_owner(actor, conn):
        return None
    return [row for row in persons if person_record_allowed(actor, str(row.get("person_id") or ""), conn)]


def person_list_allowed(actor_id: str | None, conn) -> bool:
    actor = (actor_id or "").strip()
    if not actor:
        return False
    if is_owner(actor, conn):
        return True
    from core import rbac

    # Any entity the actor themselves is assigned to. Not the GGV content default.
    for eid in assignment_entities(actor, conn):
        if rbac.can(actor, PERSON_PERMISSION, {"entity_id": eid}, conn=conn):
            return True
    return False


def decide(kind: str, identity: dict[str, Any] | None, *, conn=None) -> dict[str, Any]:
    """Allow or deny. Opens the catalog when conn is omitted. Errors fail closed."""
    own = conn is None
    opened = None
    try:
        if own:
            opened = open_decision_conn()
            conn = opened
        pid = _person_id(identity)
        if kind in {"owner_cockpit", "god_mode"}:
            allowed = bool(pid) and is_owner(pid, conn)
        elif kind == "amg_state":
            allowed = bool(pid) and amg_state_allowed(pid, conn)
        else:
            allowed = False
        return {
            "allowed": allowed,
            "kind": kind,
            "person_id": pid or None,
            "server_side": True,
            "client_hiding_sufficient": False,
        }
    except Exception:
        return {
            "allowed": False,
            "kind": kind,
            "person_id": None,
            "server_side": True,
            "reason": "auth_unavailable",
            "client_hiding_sufficient": False,
        }
    finally:
        if opened is not None:
            opened.close()
