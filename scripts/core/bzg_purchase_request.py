#!/usr/bin/env python3
"""BZG-P2P-PR-1 — Canonical Purchase Request record (Beta).

PERSON → ASSIGNMENT → ROLE → ENTITY/OUTLET SCOPE → PERMISSION.
Reuses bzg_ops_purchase_requests / bzg_ops_pr_lines (single SoR).
staff_ready / human_commissioned stay false. No invented purchases.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import rbac as _rbac
from core import uma_ops_console as _ops

PACK = "BZG-P2P-PR-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_PR_CREATE = "bzg.pr.create"
PERM_PR_CREATE_ID = "PERM-BZG-PR-CREATE"
AUDIT_SOURCE = "bzg_purchase_request"

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "payment_execution": False,
    "request_is_not_approval": True,
}


class PrError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not exists:
        return set()
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_pr_columns(conn: sqlite3.Connection) -> list[str]:
    """Additive PR columns for BZG-P2P-PR-1. Idempotent."""
    _ops.ensure_schema(conn)
    from core import bzg_xoutlet_foundations as _xout

    _xout.ensure_schema(conn)
    added: list[str] = []
    cols = _table_cols(conn, "bzg_ops_purchase_requests")
    for name, decl in (
        ("entity_id", "TEXT"),
        ("requester_person_id", "TEXT"),
        ("requester_assignment_id", "TEXT"),
        ("department", "TEXT"),
        ("alchemist_pr_order_id", "TEXT"),
        ("submitted_at", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE bzg_ops_purchase_requests ADD COLUMN {name} {decl}")
            added.append(name)
    return added


def resolve_active_assignment(
    person_id: str, conn: sqlite3.Connection
) -> dict[str, Any] | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    row = conn.execute(
        """
        SELECT a.assignment_id, a.person_id, a.position_id, a.is_primary,
               p.role_id, p.entity_id, p.brand_id, p.department_id,
               r.display_name AS role_label
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_roles r ON r.role_id = p.role_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
        ORDER BY a.is_primary DESC, a.assignment_id
        LIMIT 1
        """,
        (pid,),
    ).fetchone()
    return dict(row) if row else None


def outlet_rbac_target(outlet_id: str, conn: sqlite3.Connection) -> dict[str, str]:
    row = _outlets.get_outlet(outlet_id, conn=conn)
    if not row:
        raise PrError("Outlet not found.", code="invalid_outlet", http_status=400)
    target: dict[str, str] = {"entity_id": row["legal_entity_id"]}
    if row.get("brand_id"):
        target["brand_id"] = str(row["brand_id"])
    return target


def person_outlets(person_id: str, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Outlets from org registry covered by the person's active scopes."""
    covered = _outlets.outlets_for_person(person_id, conn=conn)
    if covered:
        return covered
    # Entity-wide scope may cover all ENT-BZG outlets.
    pid = (person_id or "").strip()
    asg = resolve_active_assignment(pid, conn)
    if not asg:
        return []
    target = {"entity_id": LEGAL_ENTITY}
    if _rbac.can(pid, PERM_PR_CREATE, target, conn=conn):
        return _outlets.list_outlets(conn, legal_entity_id=LEGAL_ENTITY)
    return []


def can_create_at_outlet(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    allowed_outlets = {o["outlet_id"] for o in person_outlets(pid, conn)}
    if oid not in allowed_outlets:
        return False, None
    target = outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, PERM_PR_CREATE, target, conn=conn):
        # Migration-era fallback: work.create at entity scope (honest deprecate path).
        if not _rbac.can(pid, "work.create", target, conn=conn):
            return False, None
    return True, resolve_active_assignment(pid, conn)


def require_create(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_create_at_outlet(person_id, outlet_id, conn)
    if not ok or not asg:
        raise PrError(
            "You cannot create a purchase request for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _validate_lines(lines: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not lines:
        raise PrError("At least one line is required.", code="missing_lines")
    out: list[dict[str, Any]] = []
    for raw in lines:
        if not isinstance(raw, dict):
            raise PrError("Each line must be an object.", code="invalid_line")
        item = str(raw.get("item") or "").strip()
        if not item:
            raise PrError("Line item is required.", code="invalid_line")
        try:
            qty = float(raw.get("qty"))
        except (TypeError, ValueError) as exc:
            raise PrError("Line qty must be numeric.", code="invalid_qty") from exc
        if qty <= 0:
            raise PrError("Line qty must be positive.", code="invalid_qty")
        unit = str(raw.get("unit") or "").strip() or None
        out.append({"item": item, "qty": qty, "unit": unit})
    return out


def _person_display(conn: sqlite3.Connection, person_id: str | None) -> str | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    row = conn.execute(
        "SELECT display_name FROM org_persons WHERE person_id=?", (pid,)
    ).fetchone()
    return str(row[0]).strip() if row and row[0] else None


def _enqueue_approval_on_submit(
    *,
    pr_id: str,
    requester_person_id: str,
    requester_assignment_id: str | None,
    outlet_id: str,
    purpose: str | None,
    work_item_id: str | None,
    identity: dict[str, Any] | None,
    conn: sqlite3.Connection,
) -> str | None:
    """Create PENDING core_approval_requests for My Work handoff. Idempotent per PR."""
    from core import approvals as _approvals

    existing = conn.execute(
        """
        SELECT approval_request_id, status
        FROM core_approval_requests
        WHERE source_id=? AND request_type='GENERAL'
        ORDER BY created_at DESC LIMIT 1
        """,
        (pr_id,),
    ).fetchone()
    if existing:
        return str(existing["approval_request_id"])
    outlet = _outlets.get_outlet(outlet_id, conn=conn) or {}
    brand_id = outlet.get("brand_id") or _ops.VENUE_UMA
    title = (purpose or f"Purchase request {pr_id}").strip()[:200]
    try:
        created = _approvals.create_approval_request(
            title=title or f"Purchase request {pr_id}",
            owning_entity_id=LEGAL_ENTITY,
            brand_id=brand_id,
            required_permission_code="work.complete",
            verified_person_id=requester_person_id,
            requested_by_assignment_id=requester_assignment_id,
            request_type="GENERAL",
            description=(
                "Ops approval for one BZG purchase request. "
                "Not a payment. Segregation of duties applies."
            ),
            source_type="HUMAN",
            source_id=pr_id,
            governed_object_type=_ops.RESOURCE_TYPE,
            governed_object_id=pr_id,
            existing_work_item_id=work_item_id,
            link_work_item=False,
            bind_policy=False,
            identity=identity,
            conn=conn,
            commit=False,
        )
    except _approvals.ApprovalError as exc:
        raise PrError(
            str(exc),
            code=getattr(exc, "code", "approval_failed"),
            http_status=int(getattr(exc, "http_status", 400) or 400),
        ) from exc
    return str(created["approval_request_id"])


def create_purchase_request(
    *,
    person_id: str,
    outlet_id: str,
    purpose: str,
    lines: list[dict[str, Any]],
    supplier_name: str | None = None,
    department: str | None = None,
    alchemist_pr_order_id: str | int | None = None,
    expected_value: float | None = None,
    currency: str | None = None,
    requested_date: str | None = None,
    required_by_date: str | None = None,
    submitted: bool = False,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create PR with required outlet, requester binding, lines, audit."""
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    reason = (purpose or "").strip()
    if not pid:
        raise PrError("Authentication required.", code="unauthenticated", http_status=401)
    if not oid:
        raise PrError("Outlet is required.", code="missing_outlet", http_status=400)
    if not reason:
        raise PrError("Reason / purpose is required.", code="missing_purpose")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_pr_columns(c)
        asg = require_create(pid, oid, c)
        validated_lines = _validate_lines(lines)
        outlet = _outlets.get_outlet(oid, conn=c)
        if not outlet:
            raise PrError("Outlet not found.", code="invalid_outlet", http_status=400)
        venue = str(outlet.get("brand_id") or _ops.VENUE_UMA)
        requester_label = _person_display(c, pid)
        ts = _ops.now_utc_iso()

        row = _ops.create_pr(
            requester_label=requester_label,
            supplier_name=supplier_name,
            purpose=reason,
            expected_value=expected_value,
            currency=currency,
            requested_date=requested_date,
            required_by_date=required_by_date,
            lines=validated_lines,
            submitted=submitted,
            example=False,
            verified_person_id=pid,
            actor_type="PERSON",
            identity=identity,
            outlet_id=oid,
            entity_id=LEGAL_ENTITY,
            requester_person_id=pid,
            requester_assignment_id=asg["assignment_id"],
            department=(department or "").strip() or asg.get("department_id"),
            alchemist_pr_order_id=(
                str(alchemist_pr_order_id).strip()
                if alchemist_pr_order_id is not None and str(alchemist_pr_order_id).strip()
                else None
            ),
            venue=venue,
            conn=c,
            commit=False,
        )
        pr_id = row["pr_id"]
        if submitted:
            c.execute(
                "UPDATE bzg_ops_purchase_requests SET submitted_at=? WHERE pr_id=?",
                (ts, pr_id),
            )
            approval_id = _enqueue_approval_on_submit(
                pr_id=pr_id,
                requester_person_id=pid,
                requester_assignment_id=asg["assignment_id"],
                outlet_id=oid,
                purpose=reason,
                work_item_id=row.get("work_item_id"),
                identity=identity,
                conn=c,
            )
            if approval_id:
                row["approval_request_id"] = approval_id

        _audit.record_event(
            action="bzg.pr.create",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=venue,
            resource_type=_ops.RESOURCE_TYPE,
            resource_id=pr_id,
            metadata={
                "outlet_id": oid,
                "assignment_id": asg["assignment_id"],
                "status": row.get("state"),
                "submitted": submitted,
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        enriched = get_purchase_request(pr_id, person_id=pid, conn=c)
        assert enriched
        return enriched
    finally:
        if own:
            c.close()


def get_purchase_request(
    pr_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        row = _ops.get_pr(pr_id, conn=c)
        if not row:
            return None
        lines = _ops.list_pr_lines(pr_id, conn=c)
        out = {**row, "lines": lines, **HONESTY}
        oid = (row.get("outlet_id") or "").strip()
        if oid:
            outlet = _outlets.get_outlet(oid, conn=c)
            if outlet:
                out["outlet_display_name"] = outlet.get("display_name")
        if person_id:
            pid = person_id.strip()
            out["can_edit"] = row.get("state") == "DRAFT" and bool(
                can_create_at_outlet(pid, oid or "", c)[0]
                if oid
                else _rbac.can(pid, PERM_PR_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c)
            )
        return out
    finally:
        if own:
            c.close()


def list_purchase_requests(
    person_id: str,
    *,
    outlet_id: str | None = None,
    state: str | None = None,
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    own = conn is None
    c = conn or db_connect()
    try:
        allowed = {o["outlet_id"] for o in person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_PR_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if outlet_id:
            oid = outlet_id.strip()
            if oid not in allowed:
                return []
            allowed = {oid}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        sql = f"""
            SELECT * FROM bzg_ops_purchase_requests
            WHERE example=0 AND outlet_id IN ({placeholders})
        """
        if state:
            sql += " AND state=?"
            params.append(state.strip().upper())
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 200)))
        rows = c.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["example"] = bool(d.get("example"))
            if d.get("outlet_id"):
                o = _outlets.get_outlet(str(d["outlet_id"]), conn=c)
                if o:
                    d["outlet_display_name"] = o.get("display_name")
            out.append(d)
        return out
    finally:
        if own:
            c.close()


def outlets_for_create(person_id: str, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Outlets the authenticated person may select when creating a PR."""
    pid = (person_id or "").strip()
    rows = person_outlets(pid, conn)
    return [
        {
            "outlet_id": r["outlet_id"],
            "display_name": r["display_name"],
            "status": r["status"],
            "brand_id": r.get("brand_id"),
        }
        for r in rows
    ]
