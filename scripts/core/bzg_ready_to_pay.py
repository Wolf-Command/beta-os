#!/usr/bin/env python3
"""BZG-P2P-READY-TO-PAY-1 — Matched AP-ready bills allowed to be paid later (Beta).

Persists bzg_ops_ready_to_pay beside AP-ready rows. Controller visibility only —
not payment, not approval to pay, no money movement, no ggv_* writes.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from core import audit as _audit
from core import bzg_ap_ready as _ap
from core import bzg_outlet_registry as _outlets
from core import bzg_p2p_grants as _grants
from core import bzg_purchase_request as _pr
from core import rbac as _rbac
from core import uma_ops_console as _ops

PACK = "BZG-P2P-READY-TO-PAY-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_PAY_LIST = "bzg.pay.list_ready"
PERM_PAY_LIST_ID = "PERM-BZG-PAY-LIST-READY"
PERM_PAY_MARK = "bzg.pay.mark_ready"
PERM_PAY_MARK_ID = "PERM-BZG-PAY-MARK-READY"
AUDIT_SOURCE = "bzg_ready_to_pay"
REFUSED_PR = _ap.REFUSED_PR

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "allowed_to_pay_later": True,
    "not_a_payment": True,
    "not_approval_to_pay": True,
    "no_money_movement": True,
    "no_ggv_writes": True,
    "no_bank_fields_required": True,
}


class ReadyToPayError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_ready_to_pay_id() -> str:
    return f"RTP-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_ready_to_pay_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent ready-to-pay table."""
    _ap.ensure_ap_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_ready_to_pay'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_ready_to_pay (
              ready_to_pay_id TEXT PRIMARY KEY,
              ap_ready_id TEXT NOT NULL UNIQUE,
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
              marked_by_person_id TEXT NOT NULL,
              marked_by_assignment_id TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_ready_to_pay_outlet
              ON bzg_ops_ready_to_pay(outlet_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_ready_to_pay_ap
              ON bzg_ops_ready_to_pay(ap_ready_id);
            """
        )
        added.append("bzg_ops_ready_to_pay")
    return added


def pay_list_permission(conn: sqlite3.Connection) -> str:
    return PERM_PAY_LIST


def pay_mark_permission(conn: sqlite3.Connection) -> str:
    return PERM_PAY_MARK


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_list_ready_to_pay(
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
    if not _rbac.can(pid, PERM_PAY_LIST, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def can_mark_ready_to_pay(
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
    if not _rbac.can(pid, PERM_PAY_MARK, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_list_ready_to_pay(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_list_ready_to_pay(person_id, outlet_id, conn)
    if not ok or not asg:
        raise ReadyToPayError(
            "You cannot view the Ready to Pay list for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def require_mark_ready_to_pay(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_mark_ready_to_pay(person_id, outlet_id, conn)
    if not ok or not asg:
        raise ReadyToPayError(
            "You cannot mark a bill allowed to pay later for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _rtp_row(conn: sqlite3.Connection, ready_to_pay_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_ready_to_pay WHERE ready_to_pay_id=?", (ready_to_pay_id,)
    ).fetchone()
    return dict(row) if row else None


def _rtp_by_bill(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bill_id,)
    ).fetchone()
    return dict(row) if row else None


def _enrich_rtp(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    out["status"] = "allowed_to_pay_later"
    out["may_be_paid_later"] = True
    return out


def _validate_eligible_ap_ready(
    conn: sqlite3.Connection,
    *,
    bill_id: str,
    client_gr_id: str | None = None,
    client_po_id: str | None = None,
    client_outlet: str | None = None,
    client_supplier: str | None = None,
) -> dict[str, Any]:
    bid = (bill_id or "").strip()
    row = conn.execute(
        "SELECT * FROM bzg_ops_ap_ready WHERE bill_id=?", (bid,)
    ).fetchone()
    ap_row = dict(row) if row else None
    if not ap_row:
        raise ReadyToPayError(
            "Bill must sit AP-ready before it can appear on Ready to Pay.",
            code="not_ap_ready",
            http_status=400,
        )

    stored_gr = str(ap_row.get("gr_id") or "")
    stored_po = str(ap_row.get("po_id") or "")
    stored_outlet = str(ap_row.get("outlet_id") or "")
    stored_supplier = str(ap_row.get("supplier_id") or "")
    pr_id = str(ap_row.get("pr_id") or "")

    if pr_id == REFUSED_PR:
        raise ReadyToPayError("This nota cannot be marked ready to pay.", code="refused_pr", http_status=400)

    if client_gr_id and client_gr_id.strip() != stored_gr:
        raise ReadyToPayError(
            "Receipt does not match this nota.",
            code="gr_mismatch",
            http_status=400,
        )
    if client_po_id and client_po_id.strip() != stored_po:
        raise ReadyToPayError(
            "Order does not match this nota.",
            code="po_mismatch",
            http_status=400,
        )
    if client_outlet and client_outlet.strip() != stored_outlet:
        raise ReadyToPayError(
            "Outlet does not match the saved documents.",
            code="outlet_mismatch",
            http_status=400,
        )
    if client_supplier and client_supplier.strip() != stored_supplier:
        raise ReadyToPayError(
            "Supplier does not match the saved documents.",
            code="supplier_mismatch",
            http_status=400,
        )

    if str(ap_row.get("match_result") or "") != "MATCH":
        raise ReadyToPayError(
            "Only a matched AP-ready bill can appear on Ready to Pay.",
            code="not_eligible_match",
            http_status=400,
        )

    return {"ap_ready": ap_row}


def mark_ready_to_pay(
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
        raise ReadyToPayError("Authentication required.", code="unauthenticated", http_status=401)
    bid = (bill_id or "").strip()
    if not bid:
        raise ReadyToPayError("Supplier nota is required.", code="missing_bill")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_ready_to_pay_schema(c)
        existing = _rtp_by_bill(c, bid)
        if existing:
            oid = str(existing["outlet_id"])
            sod = _grants.p2p_pay_ready_segregation_deny(pid, bid, c, stage="pay")
            if sod:
                msg = (
                    "You cannot mark both AP-ready and ready to pay on the same bill."
                    if sod == "same_person_cannot_mark_both_stages"
                    else "You cannot mark pay-ready on a document you created or recorded."
                )
                raise ReadyToPayError(msg, code=sod, http_status=403)
            require_mark_ready_to_pay(pid, oid, c)
            return _enrich_rtp(existing, c)

        source = _validate_eligible_ap_ready(
            c,
            bill_id=bid,
            client_gr_id=(gr_id or "").strip() or None,
            client_po_id=(po_id or "").strip() or None,
            client_outlet=(outlet_id or "").strip() or None,
            client_supplier=(supplier_id or "").strip() or None,
        )
        ap_row = source["ap_ready"]
        oid = str(ap_row["outlet_id"])
        sod = _grants.p2p_pay_ready_segregation_deny(pid, bid, c, stage="pay")
        if sod:
            msg = (
                "You cannot mark both AP-ready and ready to pay on the same bill."
                if sod == "same_person_cannot_mark_both_stages"
                else "You cannot mark pay-ready on a document you created or recorded."
            )
            raise ReadyToPayError(msg, code=sod, http_status=403)
        asg = require_mark_ready_to_pay(pid, oid, c)
        ts = _ops.now_utc_iso()
        ready_to_pay_id = mint_ready_to_pay_id()
        c.execute(
            """
            INSERT INTO bzg_ops_ready_to_pay (
              ready_to_pay_id, ap_ready_id, bill_id, match_id, gr_id, po_id, pr_id,
              outlet_id, entity_id, supplier_id, supplier_name, nota_number, nota_date,
              stated_total, marked_by_person_id, marked_by_assignment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ready_to_pay_id,
                ap_row["ap_ready_id"],
                bid,
                ap_row["match_id"],
                ap_row["gr_id"],
                ap_row["po_id"],
                ap_row["pr_id"],
                oid,
                ap_row["entity_id"],
                ap_row["supplier_id"],
                ap_row["supplier_name"],
                ap_row["nota_number"],
                ap_row["nota_date"],
                float(ap_row.get("stated_total") or 0),
                pid,
                asg.get("assignment_id"),
                ts,
            ),
        )
        _audit.record_event(
            action="bzg.pay.mark_ready",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id="BZG-UMA",
            resource_type="bzg_ready_to_pay",
            resource_id=ready_to_pay_id,
            metadata={
                "bill_id": bid,
                "ap_ready_id": ap_row["ap_ready_id"],
                "match_id": ap_row["match_id"],
                "gr_id": ap_row["gr_id"],
                "po_id": ap_row["po_id"],
                "pr_id": ap_row["pr_id"],
                "outlet_id": oid,
                "status": "allowed_to_pay_later",
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _rtp_row(c, ready_to_pay_id)
        assert row
        return _enrich_rtp(row, c)
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


def get_ready_to_pay(
    key: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_ready_to_pay_schema(c)
        row = _rtp_row(c, (key or "").strip())
        if not row:
            row = _rtp_by_bill(c, (key or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_list_ready_to_pay(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_rtp(row, c)
    finally:
        if own:
            c.close()


def list_ready_to_pay(
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
        ensure_ready_to_pay_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_PAY_LIST, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        lim = max(1, min(int(limit), 200))
        params.append(lim)
        rows = c.execute(
            f"""
            SELECT * FROM bzg_ops_ready_to_pay
            WHERE outlet_id IN ({placeholders})
            ORDER BY created_at DESC LIMIT ?
            """,
            params,
        ).fetchall()
        return [_enrich_rtp(dict(r), c) for r in rows]
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
        ensure_ready_to_pay_schema(c)
        can_list_any = False
        can_mark_any = False
        if pid:
            outlets = _pr.person_outlets(pid, c)
            if not outlets and _rbac.can(pid, PERM_PAY_LIST, {"entity_id": LEGAL_ENTITY}, conn=c):
                outlets = _outlets.list_outlets(c)
            for o in outlets:
                oid = str(o.get("outlet_id") or "")
                if oid and can_list_ready_to_pay(pid, oid, c)[0]:
                    can_list_any = True
                if oid and can_mark_ready_to_pay(pid, oid, c)[0]:
                    can_mark_any = True
                if can_list_any and can_mark_any:
                    break
        return {
            "ok": True,
            "pack": PACK,
            "can_list_ready_to_pay": can_list_any,
            "can_mark_ready_to_pay": can_mark_any,
            "pay_list_permission": pay_list_permission(c),
            "pay_mark_permission": pay_mark_permission(c),
            "ready_to_pay": list_ready_to_pay(pid, conn=c) if pid and can_list_any else [],
            **HONESTY,
        }
    finally:
        if own:
            c.close()
