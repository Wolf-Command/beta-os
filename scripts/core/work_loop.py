#!/usr/bin/env python3
"""My Work → approval → evidence → outcome.

Decision served: 2026-09-24 People Are Not Roles, on the Wolf Core governance
spine. Not a new task or approval database.

Canonical rows stay in core_work_items, core_approval_requests,
core_evidence_records, core_governance_exceptions, and core_audit_events.
Derived pages read those rows. A mismatch is marked STALE.
"""
from __future__ import annotations

from typing import Any

from core import approvals as _approvals
from core import evidence as _evidence
from core import exceptions as _exceptions
from core import rbac as _rbac
from core import work_items as wi

BOUND = "beta-work-loop"
EVIDENCE_TYPE = "work_note"
EVIDENCE_ACTION = "work.loop.submit"
GOVERNED_TYPE = "WORK_ITEM"
TAG = "P4-TEST"

_REFUSED = {
    "/api/work-loop/proven": "proven",
    "/api/work-loop/ready": "ready",
    "/api/work-loop/money": "money",
    "/api/work-loop/payment": "money",
    "/api/work-loop/bank": "money",
    "/api/work-loop/production": "production",
}


class WorkLoopError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.exception: dict[str, Any] | None = None


def refuse_code(path: str) -> str | None:
    return _REFUSED.get(path)


def founder_dependency() -> dict[str, str]:
    return {
        "role_queue": "ELIMINATE",
        "evidence_gate": "AUTOMATE",
        "approval_route": "AUTOMATE",
        "delegated_decision": "ELIMINATE",
        "exception_authorise": "RETAIN",
        "payment": "RETAIN",
        "bank_change": "RETAIN",
    }


def _allow(conn, person_id: str, code: str, entity_id: str) -> bool:
    ev = _rbac.evaluate(person_id, code, {"entity_id": entity_id}, conn=conn)
    return bool(ev.get("allowed"))


def _holds_owner_role(conn, person_id: str) -> bool:
    rows = conn.execute(
        """
        SELECT r.display_name AS role_label, r.role_type
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_roles r ON r.role_id = p.role_id
        WHERE a.person_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        """,
        (person_id,),
    ).fetchall()
    for row in rows:
        label = str(row["role_label"] or "").lower()
        kind = str(row["role_type"] or "").upper()
        if kind == "EXECUTIVE" and "owner" in label:
            return True
    return False


def resolve_role_holder(
    conn,
    *,
    role_id: str,
    scope_id: str,
    entity_id: str,
) -> tuple[str, str]:
    """Current person on this role and scope. The name is not an input."""
    role = (role_id or "").strip()
    scope = (scope_id or "").strip()
    entity = (entity_id or "").strip()
    if not role or not scope or not entity:
        raise WorkLoopError("role, scope, and entity are required", code="missing_fields")
    rows = conn.execute(
        """
        SELECT a.assignment_id, a.person_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_assignment_scopes s ON s.assignment_id = a.assignment_id
        WHERE p.role_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
          AND s.scope_id = ?
          AND s.status = 'ACTIVE'
          AND s.end_at IS NULL
        ORDER BY a.is_primary DESC, a.assignment_id
        """,
        (role, scope),
    ).fetchall()
    for row in rows:
        pid = str(row["person_id"])
        if wi.person_can_see_entity(pid, entity, conn=conn):
            return pid, str(row["assignment_id"])
    raise WorkLoopError(
        "Nobody active holds this role in this scope.",
        code="no_active_holder",
        http_status=409,
    )


def inherited_work_item_ids(conn, person_id: str) -> list[str]:
    """Open seat inherits work whose previous assignment for the same role has ended."""
    roles = conn.execute(
        """
        SELECT DISTINCT p.role_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE a.person_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        """,
        (person_id,),
    ).fetchall()
    role_ids = [str(r["role_id"]) for r in roles if r["role_id"]]
    if not role_ids:
        return []
    marks = ",".join("?" for _ in role_ids)
    rows = conn.execute(
        f"""
        SELECT w.work_item_id
        FROM core_work_items w
        JOIN org_assignments oa ON oa.assignment_id = w.owner_org_assignment_id
        JOIN org_positions op ON op.position_id = oa.position_id
        WHERE (oa.status != 'ACTIVE' OR oa.end_at IS NOT NULL)
          AND op.role_id IN ({marks})
          AND w.status != 'CANCELLED'
        """,
        role_ids,
    ).fetchall()
    return [str(r["work_item_id"]) for r in rows]


def _scope_for_assignment(conn, assignment_id: str | None) -> str | None:
    aid = (assignment_id or "").strip()
    if not aid:
        return None
    row = conn.execute(
        """
        SELECT scope_id FROM org_assignment_scopes
        WHERE assignment_id = ?
        ORDER BY status = 'ACTIVE' DESC, scope_id
        LIMIT 1
        """,
        (aid,),
    ).fetchone()
    return str(row["scope_id"]) if row and row["scope_id"] else None


def _latest_approval(conn, work_item_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM core_approval_requests
        WHERE linked_work_item_id = ?
        ORDER BY requested_at DESC
        LIMIT 1
        """,
        (work_item_id,),
    ).fetchone()
    return dict(row) if row else None


def _latest_decision(conn, approval_request_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM core_approval_decisions
        WHERE approval_request_id = ?
        ORDER BY decided_at DESC
        LIMIT 1
        """,
        (approval_request_id,),
    ).fetchone()
    return dict(row) if row else None


def _in_queue(conn, person_id: str, item: dict[str, Any]) -> bool:
    if str(item.get("owner_person_id") or "") == person_id:
        return True
    return str(item.get("work_item_id") or "") in set(inherited_work_item_ids(conn, person_id))


def can_open(conn, person_id: str, item: dict[str, Any]) -> bool:
    entity = str(item.get("owning_entity_id") or "")
    if not wi.person_can_see_entity(person_id, entity, conn=conn):
        return False
    if _in_queue(conn, person_id, item):
        return True
    if _holds_owner_role(conn, person_id):
        return True
    approval = _latest_approval(conn, str(item["work_item_id"]))
    if not approval or str(approval.get("status") or "") != "PENDING":
        return False
    if not _allow(conn, person_id, "approval.decide", entity):
        return False
    needed = str(approval.get("required_permission_code") or "")
    return (not needed) or _allow(conn, person_id, needed, entity)


def _ensure_note_type(conn) -> None:
    row = conn.execute(
        "SELECT evidence_type FROM core_evidence_types WHERE evidence_type=?",
        (EVIDENCE_TYPE,),
    ).fetchone()
    if row:
        return
    ts = wi.now_utc_iso()
    conn.execute(
        """
        INSERT INTO core_evidence_types (
          evidence_type, description, status, created_at, updated_at
        ) VALUES (?, 'Note attached to a work item', 'ACTIVE', ?, ?)
        """,
        (EVIDENCE_TYPE, ts, ts),
    )


def evidence_state(conn, item: dict[str, Any]) -> dict[str, Any]:
    scope = _scope_for_assignment(conn, item.get("owner_org_assignment_id"))
    ev = _evidence.evaluate_evidence_requirements(
        str(item["owning_entity_id"]),
        EVIDENCE_ACTION,
        scope_id=scope,
        governed_object_type=GOVERNED_TYPE,
        governed_object_id=str(item["work_item_id"]),
        audit=False,
        conn=conn,
    )
    return {
        "satisfied": bool(ev.get("satisfied")),
        "reason_code": ev.get("reason_code"),
        "missing": ev.get("missing") or [],
        "action_type": EVIDENCE_ACTION,
    }


def placement(item: dict[str, Any], approval: dict[str, Any] | None) -> dict[str, Any]:
    status = str(item.get("status") or "")
    ap_status = str((approval or {}).get("status") or "")
    if ap_status == "APPROVED" and status not in {"COMPLETED", "VERIFIED"}:
        freshness = "STALE"
    else:
        freshness = "LIVE"
    if status in {"COMPLETED", "VERIFIED"}:
        mine = "completed"
        pulse = "improving"
    elif ap_status == "PENDING":
        mine = "waiting"
        pulse = "authority"
    elif status == "BLOCKED":
        mine = "attention"
        pulse = "blocked"
    elif status in {"OPEN", "IN_PROGRESS"}:
        mine = "today"
        pulse = "happening"
    else:
        mine = status.lower() or "unknown"
        pulse = mine
    queue = "pending" if ap_status == "PENDING" else (ap_status.lower() or "none")
    return {
        "my_work": mine,
        "approver_queue": queue,
        "owner_pulse": pulse,
        "progress": {"freshness": freshness, "status": status, "source": "core_work_items"},
    }


def _bundle(conn, item: dict[str, Any]) -> dict[str, Any]:
    approval = _latest_approval(conn, str(item["work_item_id"]))
    decision = _latest_decision(conn, str(approval["approval_request_id"])) if approval else None
    place = placement(item, approval)
    return {
        "ok": True,
        "bound": BOUND,
        "work_item": item,
        "approval": approval,
        "decision": decision,
        "evidence": evidence_state(conn, item),
        "placement": place,
        "founder_dependency": founder_dependency(),
        "staff_ready": False,
        "human_commissioned": False,
        "money_movement": False,
    }


def create_assigned(
    *,
    title: str,
    owning_entity_id: str,
    role_id: str,
    scope_id: str,
    verified_person_id: str,
    description: str | None = None,
    work_type: str = "GENERAL",
    identity: dict[str, Any] | None = None,
    conn=None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        if not _allow(c, verified_person_id, "work.create", owning_entity_id):
            raise WorkLoopError("work.create denied", code="rbac_denied", http_status=403)
        holder, assignment_id = resolve_role_holder(
            c, role_id=role_id, scope_id=scope_id, entity_id=owning_entity_id
        )
        item = wi.create_work_item(
            title=title,
            description=description,
            work_type=work_type,
            owning_entity_id=owning_entity_id,
            source_type="HUMAN",
            source_id=TAG,
            verified_person_id=verified_person_id,
            owner_person_id=holder,
            owner_org_assignment_id=assignment_id,
            identity=identity,
            conn=c,
            commit=False,
        )
        if own:
            c.commit()
        return _bundle(c, item)
    finally:
        if own:
            c.close()


def open_item(work_item_id: str, *, verified_person_id: str, conn=None) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise WorkLoopError("Work item not found.", code="not_found", http_status=404)
        if not can_open(c, verified_person_id, item):
            raise WorkLoopError("This work is outside your assignment.", code="forbidden", http_status=403)
        return _bundle(c, item)
    finally:
        if own:
            c.close()


def attach_evidence(
    work_item_id: str,
    *,
    note: str,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn=None,
) -> dict[str, Any]:
    text = (note or "").strip()
    if len(text) < 3:
        raise WorkLoopError("A short note is required.", code="missing_evidence")
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise WorkLoopError("Work item not found.", code="not_found", http_status=404)
        if not can_open(c, verified_person_id, item):
            raise WorkLoopError("This work is outside your assignment.", code="forbidden", http_status=403)
        entity = str(item["owning_entity_id"])
        if not _allow(c, verified_person_id, "evidence.record.submit", entity):
            raise WorkLoopError("evidence.record.submit denied", code="rbac_denied", http_status=403)
        _ensure_note_type(c)
        scope = _scope_for_assignment(c, item.get("owner_org_assignment_id"))
        _evidence.submit_evidence(
            entity_id=entity,
            evidence_type=EVIDENCE_TYPE,
            governed_object_type=GOVERNED_TYPE,
            governed_object_id=str(item["work_item_id"]),
            verified_person_id=verified_person_id,
            source_reference=text[:240],
            object_ref=text[:500],
            scope_id=scope,
            identity=identity,
            conn=c,
            commit=False,
        )
        if own:
            c.commit()
        fresh = wi.get_work_item(work_item_id, conn=c)
        assert fresh is not None
        return _bundle(c, fresh)
    finally:
        if own:
            c.close()


def _move(item_id: str, dest: str, person_id: str, identity, conn, outcome: str | None = None) -> dict[str, Any]:
    return wi.transition_status(
        item_id,
        dest,
        verified_person_id=person_id,
        outcome=outcome,
        identity=identity,
        conn=conn,
        commit=False,
    )


def submit_item(
    work_item_id: str,
    *,
    verified_person_id: str,
    required_permission_code: str = "approval.decide",
    request_type: str = "GENERAL",
    material_amount: str | None = None,
    currency: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise WorkLoopError("Work item not found.", code="not_found", http_status=404)
        if not _in_queue(c, verified_person_id, item):
            raise WorkLoopError("Only the assigned role can submit this.", code="forbidden", http_status=403)
        if str(item.get("status") or "") not in {"OPEN", "IN_PROGRESS"}:
            raise WorkLoopError(
                f"Cannot submit from {item.get('status')}.",
                code="illegal_transition",
                http_status=409,
            )
        entity = str(item["owning_entity_id"])
        if not _allow(c, verified_person_id, "approval.request", entity):
            raise WorkLoopError("approval.request denied", code="rbac_denied", http_status=403)
        gate = evidence_state(c, item)
        if not gate["satisfied"]:
            raise WorkLoopError(
                "Required evidence is missing. Submit is blocked.",
                code="missing_required_evidence",
                http_status=403,
            )
        code = (required_permission_code or "").strip() or "approval.decide"
        perm = _rbac.get_permission_by_code(code, conn=c)
        if not perm or str(perm.get("status") or "").upper() != "ACTIVE":
            raise WorkLoopError("Unknown approval permission.", code="unknown_permission")
        approval = _approvals.create_approval_request(
            title=str(item["title"]),
            description=item.get("description"),
            request_type=request_type or "GENERAL",
            owning_entity_id=entity,
            required_permission_code=code,
            material_amount=material_amount,
            currency=currency,
            source_type="WORK_ITEM",
            source_id=str(item["work_item_id"]),
            existing_work_item_id=str(item["work_item_id"]),
            verified_person_id=verified_person_id,
            identity=identity,
            conn=c,
            commit=False,
        )
        current = item
        if current["status"] == "OPEN":
            current = _move(str(item["work_item_id"]), "IN_PROGRESS", verified_person_id, identity, c)
        if current["status"] == "IN_PROGRESS":
            current = _move(str(item["work_item_id"]), "BLOCKED", verified_person_id, identity, c)
        if own:
            c.commit()
        out = _bundle(c, current)
        out["approval"] = approval
        out["placement"] = placement(current, approval)
        return out
    finally:
        if own:
            c.close()


def _request_sod_exception(conn, approval: dict[str, Any], person_id: str, identity, constraint_id: str) -> dict[str, Any] | None:
    if not constraint_id:
        return None
    if not _allow(conn, person_id, "governance.exception.request", str(approval.get("owning_entity_id") or "")):
        return None
    try:
        return _exceptions.request_exception(
            entity_id=str(approval["owning_entity_id"]),
            governed_object_type="approval_request",
            governed_object_id=str(approval["approval_request_id"]),
            control_type="SOD_CONSTRAINT",
            control_reference=constraint_id,
            reason="Separation of duties blocked this approval.",
            verified_person_id=person_id,
            identity=identity,
            conn=conn,
            commit=False,
        )
    except _exceptions.ExceptionError:
        return None


def decide_item(
    work_item_id: str,
    *,
    decision: str,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
) -> dict[str, Any]:
    choice = (decision or "").strip().upper()
    if choice not in {"APPROVE", "REJECT"}:
        raise WorkLoopError("decision must be APPROVE or REJECT", code="invalid_decision")
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise WorkLoopError("Work item not found.", code="not_found", http_status=404)
        approval = _latest_approval(c, str(item["work_item_id"]))
        if not approval or str(approval.get("status") or "") != "PENDING":
            raise WorkLoopError("Nothing is waiting for a decision.", code="not_pending", http_status=409)
        entity = str(item["owning_entity_id"])
        if not wi.person_can_see_entity(verified_person_id, entity, conn=c):
            raise WorkLoopError("This work is outside your assignment.", code="forbidden", http_status=403)
        rid = str(approval["approval_request_id"])
        try:
            if choice == "APPROVE":
                result = _approvals.approve_request(
                    rid,
                    verified_person_id=verified_person_id,
                    reason=reason,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            else:
                result = _approvals.reject_request(
                    rid,
                    verified_person_id=verified_person_id,
                    reason=reason or "Returned to the assigned role.",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
        except _approvals.ApprovalError as exc:
            recorded = None
            if str(exc.code).startswith("sod_"):
                hit = c.execute(
                    """
                    SELECT constraint_id FROM core_sod_constraints
                    WHERE entity_id = ? AND status = 'ACTIVE' AND proposed_action = 'approval.decide'
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (entity,),
                ).fetchone()
                if hit:
                    recorded = _request_sod_exception(
                        c, approval, verified_person_id, identity, str(hit["constraint_id"])
                    )
            if own:
                c.commit()
            err = WorkLoopError(str(exc), code=str(exc.code), http_status=int(exc.http_status))
            err.exception = recorded
            raise err from exc
        current = wi.get_work_item(work_item_id, conn=c) or item
        terminal = str((result.get("request") or {}).get("status") or "")
        if choice == "REJECT" or terminal == "REJECTED":
            if current["status"] == "BLOCKED":
                current = _move(
                    str(item["work_item_id"]),
                    "IN_PROGRESS",
                    verified_person_id,
                    identity,
                    c,
                )
        elif terminal == "APPROVED":
            if current["status"] == "BLOCKED":
                current = _move(str(item["work_item_id"]), "IN_PROGRESS", verified_person_id, identity, c)
            if current["status"] == "IN_PROGRESS":
                current = _move(
                    str(item["work_item_id"]),
                    "COMPLETED",
                    verified_person_id,
                    identity,
                    c,
                    outcome="Approved",
                )
        if own:
            c.commit()
        out = _bundle(c, current)
        decision = result.get("decision") or {}
        out["decision_result"] = {
            "status": terminal,
            "authority_basis_type": decision.get("authority_basis_type"),
            "delegation_id": decision.get("authority_basis_delegation_id"),
        }
        out["decision"] = decision
        out["approval"] = result.get("request") or out.get("approval")
        out["placement"] = placement(current, out["approval"] if isinstance(out["approval"], dict) else None)
        out["executed_source"] = False
        return out
    except WorkLoopError:
        if own:
            try:
                c.commit()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()


def live_outcomes(*, conn=None, limit: int = 20) -> dict[str, Any]:
    """Progress slice. Read at request time from core_work_items."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT work_item_id, title, status, completed_at, updated_at
            FROM core_work_items
            WHERE status IN ('OPEN', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'VERIFIED')
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 40)),),
        ).fetchall()
        items = [
            {
                "id": str(r["work_item_id"]),
                "title": str(r["title"] or ""),
                "status": str(r["status"] or ""),
            }
            for r in rows
            if "DEMO" not in str(r["title"] or "").upper() and "FIXTURE" not in str(r["title"] or "").upper()
        ]
        done = [i for i in items if i["status"] in {"COMPLETED", "VERIFIED"}]
        return {
            "ok": True,
            "freshness": "LIVE",
            "stale": False,
            "source": "core_work_items",
            "as_of": wi.now_utc_iso(),
            "completed": done,
            "open": [i for i in items if i["status"] not in {"COMPLETED", "VERIFIED"}],
            "empty": not items,
            "empty_message": None if items else "No work outcomes are on record.",
            "staff_ready": False,
            "human_commissioned": False,
            "note": "Read from Wolf Core at this request. The percent projection is a separate ledger.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "freshness": "STALE",
            "stale": True,
            "source": "core_work_items",
            "completed": [],
            "open": [],
            "empty": True,
            "empty_message": "Work outcomes could not be read. Marked STALE.",
            "message": str(exc),
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        if own:
            c.close()


def audit_count_for(resource_id: str, *, conn=None) -> int:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM core_audit_events WHERE resource_id=?",
            (resource_id,),
        ).fetchone()
        return int(row["n"] if row else 0)
    finally:
        if own:
            c.close()

