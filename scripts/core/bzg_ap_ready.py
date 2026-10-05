#!/usr/bin/env python3
"""BZG-P2P-AP-1 — Matched bill sits AP-ready for controller review (Beta).

Persists bzg_ops_ap_ready beside the supplier bill. Controller visibility only —
not payment, not approval to pay, no money movement, no ggv_* writes.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import bzg_p2p_grants as _grants
from core import bzg_purchase_request as _pr
from core import bzg_supplier_bill as _bill
from core import bzg_three_way_match as _match
from core import rbac as _rbac
from core import uma_ops_console as _ops

PACK = "BZG-P2P-AP-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_AP_VIEW = "bzg.ap.view"
PERM_AP_VIEW_ID = "PERM-BZG-AP-VIEW"
PERM_AP_MARK_READY = "bzg.ap.mark_ready"
PERM_AP_MARK_READY_ID = "PERM-BZG-AP-MARK-READY"
AUDIT_SOURCE = "bzg_ap_ready"
REFUSED_PR = _match.REFUSED_PR

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "ap_controller_visibility": True,
    "not_a_payment": True,
    "not_approval_to_pay": True,
    "no_money_movement": True,
    "no_ggv_writes": True,
}


class ApReadyError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_ap_ready_id() -> str:
    return f"APR-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_ap_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent AP-ready table."""
    _match.ensure_match_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_ap_ready'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_ap_ready (
              ap_ready_id TEXT PRIMARY KEY,
              bill_id TEXT NOT NULL UNIQUE,
              match_id TEXT NOT NULL,
              gr_id TEXT NOT NULL,
              po_id TEXT NOT NULL,
              pr_id TEXT NOT NULL,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              nota_number TEXT NOT NULL,
              nota_date TEXT NOT NULL,
              stated_total REAL NOT NULL,
              match_result TEXT NOT NULL,
              marked_by_person_id TEXT NOT NULL,
              marked_by_assignment_id TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_ap_ready_outlet
              ON bzg_ops_ap_ready(outlet_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_ap_ready_match
              ON bzg_ops_ap_ready(match_id);
            """
        )
        added.append("bzg_ops_ap_ready")
    return added


def ap_view_permission(conn: sqlite3.Connection) -> str:
    return PERM_AP_VIEW


def ap_mark_ready_permission(conn: sqlite3.Connection) -> str:
    return PERM_AP_MARK_READY


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_view_ap(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    target = _pr.outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, PERM_AP_VIEW, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def can_mark_ap_ready(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    target = _pr.outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, PERM_AP_MARK_READY, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_view_ap(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_view_ap(person_id, outlet_id, conn)
    if not ok or not asg:
        raise ApReadyError(
            "You cannot view AP-ready bills for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def require_mark_ap_ready(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_mark_ap_ready(person_id, outlet_id, conn)
    if not ok or not asg:
        raise ApReadyError(
            "You cannot mark a bill AP-ready for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _ap_row(conn: sqlite3.Connection, ap_ready_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_ap_ready WHERE ap_ready_id=?", (ap_ready_id,)
    ).fetchone()
    return dict(row) if row else None


def _ap_by_bill(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_ap_ready WHERE bill_id=?", (bill_id,)
    ).fetchone()
    return dict(row) if row else None


def _enrich_ap(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    hist_label = _match.historical_match_label(str(row.get("match_id") or ""))
    if hist_label:
        out["match_label"] = hist_label
    out["controller_ready"] = True
    out["not_a_payment"] = True
    out["not_approval_to_pay"] = True
    return out


def _validate_eligible_match(
    conn: sqlite3.Connection,
    *,
    bill_id: str,
    client_gr_id: str | None = None,
    client_po_id: str | None = None,
    client_outlet: str | None = None,
    client_supplier: str | None = None,
) -> dict[str, Any]:
    bid = (bill_id or "").strip()
    bill_row = conn.execute(
        "SELECT * FROM bzg_ops_supplier_bills WHERE bill_id=?", (bid,)
    ).fetchone()
    if not bill_row:
        raise ApReadyError("Supplier nota not found.", code="not_found", http_status=404)
    bill = dict(bill_row)
    pr_id = str(bill.get("pr_id") or "")
    if pr_id == REFUSED_PR:
        raise ApReadyError("This nota cannot be marked AP-ready.", code="refused_pr", http_status=400)
    pr_row = _ops.get_pr(pr_id, conn=conn)
    if not pr_row:
        raise ApReadyError("Source request not found.", code="not_found", http_status=404)
    if pr_row.get("example"):
        raise ApReadyError("Example notas cannot be marked AP-ready.", code="example_denied", http_status=400)

    stored_gr = str(bill.get("gr_id") or "")
    stored_po = str(bill.get("po_id") or "")
    stored_outlet = str(bill.get("outlet_id") or "")
    stored_supplier = str(bill.get("supplier_id") or "")

    if client_gr_id and client_gr_id.strip() != stored_gr:
        raise ApReadyError(
            "Receipt does not match this nota.",
            code="gr_mismatch",
            http_status=400,
        )
    if client_po_id and client_po_id.strip() != stored_po:
        raise ApReadyError(
            "Order does not match this nota.",
            code="po_mismatch",
            http_status=400,
        )
    if client_outlet and client_outlet.strip() != stored_outlet:
        raise ApReadyError(
            "Outlet does not match the saved documents.",
            code="outlet_mismatch",
            http_status=400,
        )
    if client_supplier and client_supplier.strip() != stored_supplier:
        raise ApReadyError(
            "Supplier does not match the saved documents.",
            code="supplier_mismatch",
            http_status=400,
        )

    match_row = _match.match_for_bill(conn, bid)
    if not match_row:
        raise ApReadyError(
            "Three-way match must be completed before AP-ready.",
            code="not_matched",
            http_status=400,
        )
    result = str(match_row.get("result") or "")
    if result == "MATCH":
        pass
    elif result == "DIFFERENCE":
        if not match_row.get("exception_accepted"):
            raise ApReadyError(
                "A match difference must be accepted by another person before AP-ready.",
                code="difference_not_accepted",
                http_status=400,
            )
    else:
        raise ApReadyError(
            "Only a matched bill can sit AP-ready. Differences must be resolved first.",
            code="not_eligible_match",
            http_status=400,
        )

    return {"bill": bill, "match": match_row, "pr_row": pr_row}


def mark_ap_ready(
    *,
    person_id: str,
    bill_id: str,
    gr_id: str | None = None,
    po_id: str | None = None,
    outlet_id: str | None = None,
    supplier_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise ApReadyError("Authentication required.", code="unauthenticated", http_status=401)
    bid = (bill_id or "").strip()
    if not bid:
        raise ApReadyError("Supplier nota is required.", code="missing_bill")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_ap_schema(c)
        existing = _ap_by_bill(c, bid)
        if existing:
            oid = str(existing["outlet_id"])
            sod = _grants.p2p_pay_ready_segregation_deny(pid, bid, c, stage="ap")
            if sod:
                msg = (
                    "You cannot mark both AP-ready and ready to pay on the same bill."
                    if sod == "same_person_cannot_mark_both_stages"
                    else "You cannot mark pay-ready on a document you created or recorded."
                )
                raise ApReadyError(msg, code=sod, http_status=403)
            require_mark_ap_ready(pid, oid, c)
            return _enrich_ap(existing, c)

        source = _validate_eligible_match(
            c,
            bill_id=bid,
            client_gr_id=(gr_id or "").strip() or None,
            client_po_id=(po_id or "").strip() or None,
            client_outlet=(outlet_id or "").strip() or None,
            client_supplier=(supplier_id or "").strip() or None,
        )
        bill = source["bill"]
        match_row = source["match"]
        oid = str(bill["outlet_id"])
        sod = _grants.p2p_pay_ready_segregation_deny(pid, bid, c, stage="ap")
        if sod:
            msg = (
                "You cannot mark both AP-ready and ready to pay on the same bill."
                if sod == "same_person_cannot_mark_both_stages"
                else "You cannot mark pay-ready on a document you created or recorded."
            )
            raise ApReadyError(msg, code=sod, http_status=403)
        asg = require_mark_ap_ready(pid, oid, c)
        ts = _ops.now_utc_iso()
        ap_ready_id = mint_ap_ready_id()
        c.execute(
            """
            INSERT INTO bzg_ops_ap_ready (
              ap_ready_id, bill_id, match_id, gr_id, po_id, pr_id, outlet_id,
              entity_id, supplier_id, supplier_name, nota_number, nota_date,
              stated_total, match_result, marked_by_person_id,
              marked_by_assignment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ap_ready_id,
                bid,
                match_row["match_id"],
                bill["gr_id"],
                bill["po_id"],
                bill["pr_id"],
                oid,
                bill["entity_id"],
                bill["supplier_id"],
                bill["supplier_name"],
                bill["nota_number"],
                bill["nota_date"],
                float(bill.get("stated_total") or 0),
                match_row["result"],
                pid,
                asg.get("assignment_id"),
                ts,
            ),
        )
        _audit.record_event(
            action="bzg.ap.mark_ready",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=source["pr_row"].get("venue"),
            resource_type="bzg_ap_ready",
            resource_id=ap_ready_id,
            metadata={
                "bill_id": bid,
                "match_id": match_row["match_id"],
                "gr_id": bill["gr_id"],
                "po_id": bill["po_id"],
                "pr_id": bill["pr_id"],
                "outlet_id": oid,
                "match_result": match_row["result"],
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _ap_row(c, ap_ready_id)
        assert row
        return _enrich_ap(row, c)
    except Exception:
        if own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()


def get_ap_ready(
    key: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_ap_schema(c)
        row = _ap_row(c, (key or "").strip())
        if not row:
            row = _ap_by_bill(c, (key or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_view_ap(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_ap(row, c)
    finally:
        if own:
            c.close()


def list_ap_ready(
    person_id: str,
    *,
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_ap_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_AP_VIEW, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        lim = max(1, min(int(limit), 200))
        params.append(lim)
        rows = c.execute(
            f"""
            SELECT * FROM bzg_ops_ap_ready
            WHERE outlet_id IN ({placeholders})
            ORDER BY created_at DESC LIMIT ?
            """,
            params,
        ).fetchall()
        return [_enrich_ap(dict(r), c) for r in rows]
    finally:
        if own:
            c.close()


def workspace(
    person_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_ap_schema(c)
        can_view_any = False
        can_mark_any = False
        if pid:
            outlets = _pr.person_outlets(pid, c)
            if not outlets and _rbac.can(pid, PERM_AP_VIEW, {"entity_id": LEGAL_ENTITY}, conn=c):
                outlets = _outlets.list_outlets(c)
            for o in outlets:
                oid = str(o.get("outlet_id") or "")
                if oid and can_view_ap(pid, oid, c)[0]:
                    can_view_any = True
                if oid and can_mark_ap_ready(pid, oid, c)[0]:
                    can_mark_any = True
                if can_view_any and can_mark_any:
                    break
        return {
            "ok": True,
            "pack": PACK,
            "can_view_ap": can_view_any,
            "can_mark_ap_ready": can_mark_any,
            "ap_view_permission": ap_view_permission(c),
            "ap_mark_ready_permission": ap_mark_ready_permission(c),
            "ap_ready": list_ap_ready(pid, conn=c) if pid and can_view_any else [],
            **HONESTY,
        }
    finally:
        if own:
            c.close()
