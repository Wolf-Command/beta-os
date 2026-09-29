#!/usr/bin/env python3
"""Wolf Core Work Items — task primitive (Beta).

Work Item ≠ Organisation Assignment (org_assignments).
COMPLETED = completion claimed; VERIFIED = separate verify step.
No DELETE — cancel instead. No Evidence File Store / Kanban / LLM this slice.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import organisation as _org
from core import scope as _scope

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
TZ_UTC = timezone.utc

WORK_TYPES = frozenset(
    {
        "GENERAL",
        "FOLLOW_UP",
        "EXCEPTION",
        "MAINTENANCE",
        "APPROVAL_REQUIRED",
        "AUDIT_FINDING",
        "CONTENT",
        "SYSTEM",
    }
)
SOURCE_TYPES = frozenset(
    {
        "HUMAN",
        "SYSTEM",
        "AUDIT",
        "ROUTINE",
        "RECOMMENDATION_ACCEPTED",
        "EXTERNAL",
    }
)
STATUSES = frozenset(
    {
        "OPEN",
        "IN_PROGRESS",
        "BLOCKED",
        "WAITING",
        "RETURNED",
        "REASSIGNED",
        "COMPLETED",
        "VERIFIED",
        "CANCELLED",
    }
)
TERMINAL = frozenset({"VERIFIED", "CANCELLED"})
ACTOR_TYPES = frozenset({"PERSON", "SYSTEM"})

# Explicit legal transitions (CLAIMED COMPLETED ≠ VERIFIED).
# Presentation aliases: OPEN=ASSIGNED, COMPLETED=DONE.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "OPEN": frozenset({"IN_PROGRESS", "WAITING", "REASSIGNED", "CANCELLED"}),
    "IN_PROGRESS": frozenset(
        {"BLOCKED", "WAITING", "RETURNED", "COMPLETED", "REASSIGNED", "CANCELLED"}
    ),
    "BLOCKED": frozenset({"IN_PROGRESS", "CANCELLED"}),
    "WAITING": frozenset({"IN_PROGRESS", "CANCELLED"}),
    "RETURNED": frozenset({"IN_PROGRESS", "COMPLETED", "CANCELLED"}),
    "REASSIGNED": frozenset({"OPEN", "IN_PROGRESS", "CANCELLED"}),
    "COMPLETED": frozenset({"VERIFIED", "RETURNED", "CANCELLED"}),
    "VERIFIED": frozenset(),
    "CANCELLED": frozenset(),
}

PROVENANCE_FIELDS = frozenset(
    {
        "source_type",
        "source_id",
        "created_by_actor_type",
        "created_by_person_id",
        "owning_entity_id",
        "work_type",
    }
)
PATCHABLE_FIELDS = frozenset({"title", "description", "priority", "due_at"})


class WorkItemError(ValueError):
    """Fail-closed validation / transition error."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"work_items refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"work_items refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"work_items refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_work_item_id() -> str:
    return f"WI-{uuid.uuid4()}"


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def visible_entity_ids_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> set[str]:
    """Entities covered by the person's active Assignment scopes (incl. parent of dept/brand/loc)."""
    pid = (person_id or "").strip()
    if not pid:
        return set()
    own = conn is None
    c = conn or db_connect()
    try:
        ents: set[str] = set()
        for s in _scope.list_active_scopes_for_person(pid, conn=c):
            ctx = _scope.resolve_effective_scope_context(s["scope_id"], conn=c)
            covered = ctx.get("structurally_covered") or {}
            for eid in covered.get("entities") or []:
                ents.add(eid)
            for did in covered.get("departments") or []:
                row = c.execute(
                    "SELECT entity_id FROM org_departments WHERE department_id=?",
                    (did,),
                ).fetchone()
                if row and row[0]:
                    ents.add(row[0])
            for bid in covered.get("brands") or []:
                row = c.execute(
                    "SELECT entity_id FROM org_brands WHERE brand_id=?",
                    (bid,),
                ).fetchone()
                if row and row[0]:
                    ents.add(row[0])
            for lid in covered.get("locations") or []:
                row = c.execute(
                    "SELECT entity_id FROM org_locations WHERE location_id=?",
                    (lid,),
                ).fetchone()
                if row and row[0]:
                    ents.add(row[0])
        return ents
    finally:
        if own:
            c.close()


def person_can_see_entity(
    person_id: str, entity_id: str, conn: sqlite3.Connection | None = None
) -> bool:
    eid = (entity_id or "").strip()
    if not eid:
        return False
    return eid in visible_entity_ids_for_person(person_id, conn=conn)


def _validate_owner_assignment(
    owner_person_id: str | None,
    owner_org_assignment_id: str | None,
    conn: sqlite3.Connection,
) -> None:
    aid = (owner_org_assignment_id or "").strip() or None
    if not aid:
        return
    oid = (owner_person_id or "").strip() or None
    if not oid:
        raise WorkItemError(
            "owner_org_assignment_id requires owner_person_id",
            code="owner_assignment_without_person",
        )
    row = conn.execute(
        """
        SELECT assignment_id, person_id, status, end_at
        FROM org_assignments WHERE assignment_id=?
        """,
        (aid,),
    ).fetchone()
    if not row:
        raise WorkItemError(
            f"owner_org_assignment_id not found: {aid}",
            code="unknown_assignment",
        )
    if row["person_id"] != oid:
        raise WorkItemError(
            "owner_org_assignment_id must belong to owner_person_id",
            code="assignment_person_mismatch",
        )
    if row["status"] != "ACTIVE" or row["end_at"] is not None:
        raise WorkItemError(
            "owner_org_assignment_id must be ACTIVE",
            code="inactive_assignment",
        )


def _audit_work(
    *,
    action: str,
    result: str,
    work_item: dict[str, Any],
    verified_person_id: str | None,
    actor_type: str,
    identity: dict[str, Any] | None = None,
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    at = (actor_type or "").strip().upper()
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "work_items",
        "actor_type": at,
        "entity_id": work_item.get("owning_entity_id"),
        "resource_type": "work_item",
        "resource_id": work_item.get("work_item_id"),
        "reason_code": reason_code,
        "correlation_id": identity.get("correlation_id") or _audit.mint_correlation_id(),
        "metadata": metadata,
        "conn": conn,
        "commit": False,
    }
    if at == "PERSON":
        pid = (verified_person_id or "").strip()
        if not pid:
            raise WorkItemError(
                "PERSON audit requires verified_person_id",
                code="missing_verified_person",
            )
        kwargs["verified_person_id"] = pid
        kwargs["actor_person_id"] = pid
        kwargs["actor_auth_identity_id"] = identity.get("auth_identity_id")
        kwargs["identity_assurance"] = identity.get("identity_assurance")
    _audit.safe_record(**kwargs)


def create_work_item(
    *,
    title: str,
    owning_entity_id: str,
    work_type: str = "GENERAL",
    source_type: str = "HUMAN",
    created_by_actor_type: str = "PERSON",
    verified_person_id: str | None = None,
    description: str | None = None,
    priority: int = 3,
    source_id: str | None = None,
    created_by_person_id: str | None = None,
    owner_person_id: str | None = None,
    owner_org_assignment_id: str | None = None,
    due_at: str | None = None,
    parent_work_item_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create a work item. PERSON creator requires verified identity match."""
    t = (title or "").strip()
    if not t:
        raise WorkItemError("title required", code="missing_title")
    eid = (owning_entity_id or "").strip()
    if not eid:
        raise WorkItemError("owning_entity_id required", code="missing_entity")
    wt = (work_type or "").strip().upper()
    if wt not in WORK_TYPES:
        raise WorkItemError(f"invalid work_type: {work_type!r}", code="invalid_work_type")
    st = (source_type or "").strip().upper()
    if st not in SOURCE_TYPES:
        raise WorkItemError(f"invalid source_type: {source_type!r}", code="invalid_source_type")
    at = (created_by_actor_type or "").strip().upper()
    if at not in ACTOR_TYPES:
        raise WorkItemError(f"invalid created_by_actor_type: {created_by_actor_type!r}")
    try:
        pr = int(priority)
    except (TypeError, ValueError) as exc:
        raise WorkItemError("priority must be 1..5", code="invalid_priority") from exc
    if pr < 1 or pr > 5:
        raise WorkItemError("priority must be 1..5", code="invalid_priority")

    verified = (verified_person_id or "").strip() or None
    client_creator = (created_by_person_id or "").strip() or None
    if at == "SYSTEM":
        if client_creator is not None:
            raise WorkItemError(
                "SYSTEM creator cannot carry created_by_person_id",
                code="system_person_forbidden",
            )
        creator_person = None
    else:
        if not verified:
            raise WorkItemError(
                "PERSON creator requires verified_person_id",
                code="missing_verified_person",
            )
        if client_creator and client_creator != verified:
            raise WorkItemError(
                "created_by_person_id must match verified identity; client spoof refused",
                code="forged_creator",
            )
        creator_person = verified

    owner = (owner_person_id or "").strip() or None
    if owner and owner.startswith("PERS-"):
        pass  # shape ok; existence checked below
    # Refuse forged owner without being the verified actor unless assign path later
    # On create, owner may be set to self or another person (requires work.create, not assign).

    own = conn is None
    c = conn or db_connect()
    try:
        ent = _org.get_entity(eid, conn=c)
        if not ent:
            raise WorkItemError(f"unknown owning_entity_id: {eid}", code="unknown_entity")

        if at == "PERSON" and creator_person:
            if not person_can_see_entity(creator_person, eid, conn=c):
                raise WorkItemError(
                    f"entity out of scope: {eid}",
                    code="entity_out_of_scope",
                    http_status=403,
                )

        if owner:
            person = c.execute(
                "SELECT person_id FROM org_persons WHERE person_id=?", (owner,)
            ).fetchone()
            if not person:
                raise WorkItemError(f"unknown owner_person_id: {owner}", code="unknown_owner")

        _validate_owner_assignment(owner, owner_org_assignment_id, c)

        parent = (parent_work_item_id or "").strip() or None
        if parent:
            prow = c.execute(
                "SELECT work_item_id FROM core_work_items WHERE work_item_id=?",
                (parent,),
            ).fetchone()
            if not prow:
                raise WorkItemError(
                    f"parent_work_item_id not found: {parent}",
                    code="unknown_parent",
                )

        wid = mint_work_item_id()
        ts = now_utc_iso()
        # accountable/executor default to owner (MYWORK-1); columns may be absent pre-migration.
        cols = {str(r[1]) for r in c.execute("PRAGMA table_info(core_work_items)")}
        if "accountable_person_id" in cols:
            c.execute(
                """
                INSERT INTO core_work_items (
                  work_item_id, title, description, work_type, status, priority,
                  owning_entity_id, source_type, source_id,
                  created_by_actor_type, created_by_person_id,
                  owner_person_id, owner_org_assignment_id,
                  accountable_person_id, executor_person_id, requested_by_person_id,
                  due_at, started_at, completed_at, verified_at, outcome,
                  completion_evidence_reference, parent_work_item_id,
                  created_at, updated_at
                ) VALUES (
                  ?, ?, ?, ?, 'OPEN', ?,
                  ?, ?, ?,
                  ?, ?,
                  ?, ?,
                  ?, ?, ?,
                  ?, NULL, NULL, NULL, NULL,
                  NULL, ?,
                  ?, ?
                )
                """,
                (
                    wid,
                    t,
                    (description or "").strip() or None,
                    wt,
                    pr,
                    eid,
                    st,
                    (source_id or "").strip() or None,
                    at,
                    creator_person,
                    owner,
                    (owner_org_assignment_id or "").strip() or None,
                    owner,
                    owner,
                    creator_person,
                    (due_at or "").strip() or None,
                    parent,
                    ts,
                    ts,
                ),
            )
        else:
            c.execute(
                """
                INSERT INTO core_work_items (
                  work_item_id, title, description, work_type, status, priority,
                  owning_entity_id, source_type, source_id,
                  created_by_actor_type, created_by_person_id,
                  owner_person_id, owner_org_assignment_id, due_at,
                  started_at, completed_at, verified_at, outcome,
                  completion_evidence_reference, parent_work_item_id,
                  created_at, updated_at
                ) VALUES (
                  ?, ?, ?, ?, 'OPEN', ?,
                  ?, ?, ?,
                  ?, ?,
                  ?, ?, ?,
                  NULL, NULL, NULL, NULL,
                  NULL, ?,
                  ?, ?
                )
                """,
                (
                    wid,
                    t,
                    (description or "").strip() or None,
                    wt,
                    pr,
                    eid,
                    st,
                    (source_id or "").strip() or None,
                    at,
                    creator_person,
                    owner,
                    (owner_org_assignment_id or "").strip() or None,
                    (due_at or "").strip() or None,
                    parent,
                    ts,
                    ts,
                ),
            )
        item = get_work_item(wid, conn=c)
        assert item is not None
        _audit_work(
            action="work.create",
            result="SUCCEEDED",
            work_item=item,
            verified_person_id=verified if at == "PERSON" else None,
            actor_type=at,
            identity=identity,
            metadata={"status": "OPEN", "work_type": wt},
            conn=c,
        )
        if commit:
            c.commit()
        return item
    finally:
        if own:
            c.close()


def get_work_item(
    work_item_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    wid = (work_item_id or "").strip()
    if not wid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                "SELECT * FROM core_work_items WHERE work_item_id=?",
                (wid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_work_items(
    person_id: str,
    *,
    status: str | None = None,
    owning_entity_id: str | None = None,
    owner_person_id: str | None = None,
    work_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """List work items visible via the person's Assignment entity scopes."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        visible = visible_entity_ids_for_person(pid, conn=c)
        if not visible:
            return []
        if owning_entity_id:
            eid = owning_entity_id.strip()
            if eid not in visible:
                return []
            entities = [eid]
        else:
            entities = sorted(visible)

        clauses = [f"owning_entity_id IN ({','.join('?' * len(entities))})"]
        params: list[Any] = list(entities)
        if status:
            st = status.strip().upper()
            if st not in STATUSES:
                raise WorkItemError(f"invalid status filter: {status!r}")
            clauses.append("status=?")
            params.append(st)
        if owner_person_id:
            clauses.append("owner_person_id=?")
            params.append(owner_person_id.strip())
        if work_type:
            wt = work_type.strip().upper()
            if wt not in WORK_TYPES:
                raise WorkItemError(f"invalid work_type filter: {work_type!r}")
            clauses.append("work_type=?")
            params.append(wt)

        lim = max(1, min(int(limit or 50), 200))
        off = max(0, int(offset or 0))
        rows = c.execute(
            f"""
            SELECT * FROM core_work_items
            WHERE {' AND '.join(clauses)}
            ORDER BY priority ASC, due_at IS NULL, due_at ASC, created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, lim, off),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def update_work_item_fields(
    work_item_id: str,
    *,
    verified_person_id: str,
    title: str | None = None,
    description: Any = ...,
    priority: int | None = None,
    due_at: Any = ...,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """PATCH allowed fields only — not status, owner, or provenance."""
    wid = (work_item_id or "").strip()
    verified = (verified_person_id or "").strip()
    if not verified:
        raise WorkItemError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        item = get_work_item(wid, conn=c)
        if not item:
            raise WorkItemError("work item not found", code="not_found", http_status=404)
        if item["status"] in TERMINAL:
            raise WorkItemError(
                f"cannot update terminal status {item['status']}",
                code="terminal",
            )
        if not person_can_see_entity(verified, item["owning_entity_id"], conn=c):
            raise WorkItemError(
                "entity out of scope",
                code="entity_out_of_scope",
                http_status=403,
            )

        sets: list[str] = []
        params: list[Any] = []
        if title is not None:
            t = title.strip()
            if not t:
                raise WorkItemError("title cannot be empty", code="missing_title")
            sets.append("title=?")
            params.append(t)
        if description is not ...:
            sets.append("description=?")
            params.append((str(description).strip() if description is not None else "") or None)
        if priority is not None:
            try:
                pr = int(priority)
            except (TypeError, ValueError) as exc:
                raise WorkItemError("priority must be 1..5") from exc
            if pr < 1 or pr > 5:
                raise WorkItemError("priority must be 1..5")
            sets.append("priority=?")
            params.append(pr)
        if due_at is not ...:
            sets.append("due_at=?")
            params.append((str(due_at).strip() if due_at is not None else "") or None)

        if not sets:
            return item

        ts = now_utc_iso()
        sets.append("updated_at=?")
        params.append(ts)
        params.append(wid)
        c.execute(
            f"UPDATE core_work_items SET {', '.join(sets)} WHERE work_item_id=?",
            params,
        )
        updated = get_work_item(wid, conn=c)
        assert updated is not None
        _audit_work(
            action="work.update",
            result="SUCCEEDED",
            work_item=updated,
            verified_person_id=verified,
            actor_type="PERSON",
            identity=identity,
            metadata={"status": updated["status"]},
            conn=c,
        )
        if commit:
            c.commit()
        return updated
    finally:
        if own:
            c.close()


def reassign_owner(
    work_item_id: str,
    *,
    verified_person_id: str,
    owner_person_id: str | None,
    owner_org_assignment_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    wid = (work_item_id or "").strip()
    verified = (verified_person_id or "").strip()
    if not verified:
        raise WorkItemError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        item = get_work_item(wid, conn=c)
        if not item:
            raise WorkItemError("work item not found", code="not_found", http_status=404)
        if item["status"] in TERMINAL:
            raise WorkItemError(
                f"cannot assign terminal status {item['status']}",
                code="terminal",
            )
        if not person_can_see_entity(verified, item["owning_entity_id"], conn=c):
            raise WorkItemError(
                "entity out of scope",
                code="entity_out_of_scope",
                http_status=403,
            )

        owner = (owner_person_id or "").strip() or None
        if owner:
            person = c.execute(
                "SELECT person_id FROM org_persons WHERE person_id=?", (owner,)
            ).fetchone()
            if not person:
                raise WorkItemError(f"unknown owner_person_id: {owner}", code="unknown_owner")
        _validate_owner_assignment(owner, owner_org_assignment_id, c)

        before_owner = item.get("owner_person_id")
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_work_items
            SET owner_person_id=?, owner_org_assignment_id=?, updated_at=?
            WHERE work_item_id=?
            """,
            (
                owner,
                (owner_org_assignment_id or "").strip() or None,
                ts,
                wid,
            ),
        )
        updated = get_work_item(wid, conn=c)
        assert updated is not None
        _audit_work(
            action="work.assign",
            result="SUCCEEDED",
            work_item=updated,
            verified_person_id=verified,
            actor_type="PERSON",
            identity=identity,
            metadata={
                "status": updated["status"],
                "owner_person_id": owner,
                "note": f"from={before_owner}",
            },
            conn=c,
        )
        if commit:
            c.commit()
        return updated
    finally:
        if own:
            c.close()


def transition_status(
    work_item_id: str,
    to_status: str,
    *,
    verified_person_id: str | None,
    actor_type: str = "PERSON",
    outcome: str | None = None,
    completion_evidence_reference: str | None = None,
    identity: dict[str, Any] | None = None,
    audit_action: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    wid = (work_item_id or "").strip()
    dest = (to_status or "").strip().upper()
    if dest not in STATUSES:
        raise WorkItemError(f"invalid status: {to_status!r}", code="invalid_status")
    at = (actor_type or "").strip().upper()
    if at not in ACTOR_TYPES:
        raise WorkItemError(f"invalid actor_type: {actor_type!r}")
    verified = (verified_person_id or "").strip() or None
    if at == "PERSON" and not verified:
        raise WorkItemError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        item = get_work_item(wid, conn=c)
        if not item:
            raise WorkItemError("work item not found", code="not_found", http_status=404)
        cur = item["status"]
        if dest not in ALLOWED_TRANSITIONS.get(cur, frozenset()):
            raise WorkItemError(
                f"illegal transition {cur} → {dest}",
                code="illegal_transition",
            )
        if at == "PERSON" and verified:
            if not person_can_see_entity(verified, item["owning_entity_id"], conn=c):
                raise WorkItemError(
                    "entity out of scope",
                    code="entity_out_of_scope",
                    http_status=403,
                )

        ts = now_utc_iso()
        sets = ["status=?", "updated_at=?"]
        params: list[Any] = [dest, ts]
        if dest == "IN_PROGRESS" and not item.get("started_at"):
            sets.append("started_at=?")
            params.append(ts)
        if dest == "COMPLETED":
            sets.append("completed_at=?")
            params.append(ts)
            if outcome is not None:
                sets.append("outcome=?")
                params.append((outcome or "").strip() or None)
            if completion_evidence_reference is not None:
                sets.append("completion_evidence_reference=?")
                params.append((completion_evidence_reference or "").strip() or None)
        if dest == "VERIFIED":
            sets.append("verified_at=?")
            params.append(ts)
        if outcome is not None and dest == "CANCELLED":
            sets.append("outcome=?")
            params.append((outcome or "").strip() or None)

        params.append(wid)
        c.execute(
            f"UPDATE core_work_items SET {', '.join(sets)} WHERE work_item_id=?",
            params,
        )
        updated = get_work_item(wid, conn=c)
        assert updated is not None

        action = audit_action or f"work.{dest.lower()}"
        _audit_work(
            action=action,
            result="SUCCEEDED",
            work_item=updated,
            verified_person_id=verified,
            actor_type=at,
            identity=identity,
            metadata={"status": dest, "note": f"from={cur}"},
            conn=c,
        )
        if commit:
            c.commit()
        return updated
    finally:
        if own:
            c.close()


def start_work_item(
    work_item_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return transition_status(
        work_item_id,
        "IN_PROGRESS",
        verified_person_id=verified_person_id,
        identity=identity,
        audit_action="work.start",
        conn=conn,
        commit=commit,
    )


def block_work_item(
    work_item_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return transition_status(
        work_item_id,
        "BLOCKED",
        verified_person_id=verified_person_id,
        identity=identity,
        audit_action="work.block",
        conn=conn,
        commit=commit,
    )


def claim_complete(
    work_item_id: str,
    *,
    verified_person_id: str,
    outcome: str | None = None,
    completion_evidence_reference: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Claim COMPLETED — does NOT mean Wolf verified reality."""
    return transition_status(
        work_item_id,
        "COMPLETED",
        verified_person_id=verified_person_id,
        outcome=outcome,
        completion_evidence_reference=completion_evidence_reference,
        identity=identity,
        audit_action="work.complete",
        conn=conn,
        commit=commit,
    )


def verify_work_item(
    work_item_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """VERIFIED — only from COMPLETED via this helper (not raw status update)."""
    return transition_status(
        work_item_id,
        "VERIFIED",
        verified_person_id=verified_person_id,
        identity=identity,
        audit_action="work.verify",
        conn=conn,
        commit=commit,
    )


def cancel_work_item(
    work_item_id: str,
    *,
    verified_person_id: str,
    outcome: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return transition_status(
        work_item_id,
        "CANCELLED",
        verified_person_id=verified_person_id,
        outcome=outcome,
        identity=identity,
        audit_action="work.cancel",
        conn=conn,
        commit=commit,
    )


def delete_work_item(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError("work items are not deleted; use cancel_work_item")
