#!/usr/bin/env python3
"""BZG-P2P-RECV-1 — Goods receiving against a saved purchase order (Beta).

Persists bzg_ops_goods_receipts / bzg_ops_gr_lines. ORDERED → PARTIALLY_RECEIVED
or RECEIVED via uma_ops_console.transition_pr. Not a bill, not payment, no stock ledger.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import bzg_purchase_order as _po
from core import bzg_purchase_request as _pr
from core import rbac as _rbac
from core import uma_devi_p0 as _p0
from core import uma_ops_console as _ops

PACK = "BZG-P2P-RECV-1"
LEGAL_ENTITY = "ENT-BZG"
AUDIT_SOURCE = "bzg_goods_receiving"
QTY_EPS = _po.QTY_EPS
REFUSED_PR = "PR-UMA-0E65E353A422"

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "goods_receipt": True,
    "not_a_payment": True,
    "not_a_bill": True,
    "no_stock_ledger_posting": True,
}


class GrError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_gr_id() -> str:
    return f"GR-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_gr_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent goods-receipt tables for PO-based receiving."""
    _po.ensure_po_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_goods_receipts'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_goods_receipts (
              gr_id TEXT PRIMARY KEY,
              po_id TEXT NOT NULL,
              pr_id TEXT NOT NULL,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              receiver_person_id TEXT NOT NULL,
              receiver_assignment_id TEXT,
              notes TEXT,
              status TEXT NOT NULL CHECK (status IN ('PARTIAL', 'COMPLETE')),
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_gr_po ON bzg_ops_goods_receipts(po_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_gr_pr ON bzg_ops_goods_receipts(pr_id);

            CREATE TABLE IF NOT EXISTS bzg_ops_gr_lines (
              line_id TEXT PRIMARY KEY,
              gr_id TEXT NOT NULL,
              po_line_id TEXT NOT NULL,
              item TEXT NOT NULL,
              received_qty REAL NOT NULL,
              shortfall_reason TEXT,
              unit TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_gr_lines_gr ON bzg_ops_gr_lines(gr_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_gr_lines_po_line ON bzg_ops_gr_lines(po_line_id);
            """
        )
        added.extend(["bzg_ops_goods_receipts", "bzg_ops_gr_lines"])
    return added


def receive_permission(conn: sqlite3.Connection) -> str | None:
    return _p0.discover_receive_permission(conn)


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_receive(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    code = receive_permission(conn)
    if not code:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    target = _pr.outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, code, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_receive(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_receive(person_id, outlet_id, conn)
    if not ok or not asg:
        raise GrError(
            "You cannot record a goods receipt for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _pr_approver_person(conn: sqlite3.Connection, pr_id: str) -> str | None:
    """Person who approved the PR via core_approval_decisions, if recorded."""
    key = (pr_id or "").strip()
    if not key:
        return None
    row = conn.execute(
        """
        SELECT d.decided_by_person_id
        FROM core_approval_decisions d
        JOIN core_approval_requests r ON r.approval_request_id = d.approval_request_id
        WHERE r.source_id = ? AND d.decision = 'APPROVED'
          AND d.decided_by_person_id IS NOT NULL AND d.decided_by_person_id != ''
        ORDER BY d.decided_at DESC, d.created_at DESC
        LIMIT 1
        """,
        (key,),
    ).fetchone()
    if row:
        return str(row[0]).strip() or None
    row = conn.execute(
        """
        SELECT actor_person_id
        FROM core_audit_events
        WHERE resource_type=? AND resource_id=?
          AND action IN ('bzg.pr.approved', 'approval.approve')
          AND actor_person_id IS NOT NULL AND actor_person_id != ''
        ORDER BY occurred_at DESC, created_at DESC
        LIMIT 1
        """,
        (_ops.RESOURCE_TYPE, key),
    ).fetchone()
    if row:
        return str(row[0]).strip() or None
    return None


def _received_by_po_line(conn: sqlite3.Connection, po_id: str) -> dict[str, float]:
    rows = conn.execute(
        """
        SELECT gl.po_line_id, SUM(gl.received_qty) AS qty
        FROM bzg_ops_gr_lines gl
        JOIN bzg_ops_goods_receipts gr ON gr.gr_id = gl.gr_id
        WHERE gr.po_id=?
        GROUP BY gl.po_line_id
        """,
        (po_id,),
    ).fetchall()
    return {str(r["po_line_id"]): float(r["qty"] or 0) for r in rows}


def _gr_row(conn: sqlite3.Connection, gr_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_goods_receipts WHERE gr_id=?", (gr_id,)
    ).fetchone()
    return dict(row) if row else None


def _gr_lines(conn: sqlite3.Connection, gr_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT line_id, po_line_id, item, received_qty, shortfall_reason, unit
        FROM bzg_ops_gr_lines
        WHERE gr_id=?
        ORDER BY created_at, line_id
        """,
        (gr_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _enrich_gr(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, "lines": _gr_lines(conn, row["gr_id"]), **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    try:
        from core import bzg_supplier_bill as _bill

        _bill.ensure_bill_schema(conn)
        out = _bill.enrich_gr_with_bills(out, conn)
    except Exception:
        out["supplier_bills"] = []
    return out


def _receipts_for_po(conn: sqlite3.Connection, po_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM bzg_ops_goods_receipts
        WHERE po_id=?
        ORDER BY created_at DESC, gr_id DESC
        """,
        (po_id,),
    ).fetchall()
    return [_enrich_gr(dict(r), conn) for r in rows]


def enrich_po_lines(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    """Add ordered / received / outstanding per PO line and receipt history."""
    po_id = str(row.get("po_id") or "")
    received = _received_by_po_line(conn, po_id)
    lines_out: list[dict[str, Any]] = []
    for ln in row.get("lines") or []:
        lid = str(ln.get("line_id") or "")
        ordered = float(ln.get("qty") or 0)
        got = received.get(lid, 0.0)
        outstanding = max(0.0, ordered - got)
        lines_out.append(
            {
                **ln,
                "ordered_qty": ordered,
                "received_qty": got,
                "outstanding_qty": outstanding,
            }
        )
    out = {**row, "lines": lines_out, "receipts": _receipts_for_po(conn, po_id)}
    all_done = bool(lines_out) and all(
        ln.get("outstanding_qty", 0) <= QTY_EPS for ln in lines_out
    )
    out["fully_received"] = all_done
    return out


def _validate_source_po(po_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    key = (po_id or "").strip()
    row = conn.execute(
        "SELECT * FROM bzg_ops_purchase_orders WHERE po_id=?", (key,)
    ).fetchone()
    if not row:
        raise GrError("Purchase order not found.", code="not_found", http_status=404)
    po = dict(row)
    pr_id = str(po.get("pr_id") or "")
    if pr_id == REFUSED_PR:
        raise GrError("This order cannot be received.", code="refused_pr", http_status=400)
    pr_row = _ops.get_pr(pr_id, conn=conn)
    if not pr_row:
        raise GrError("Source request not found.", code="not_found", http_status=404)
    if pr_row.get("example"):
        raise GrError("Example orders cannot be received.", code="example_denied", http_status=400)
    state = str(pr_row.get("state") or "")
    if state not in ("ORDERED", "PARTIALLY_RECEIVED"):
        raise GrError(
            "Goods can only be received after the order is placed.",
            code="not_ordered",
            http_status=400,
        )
    po_lines = _po._po_lines(conn, key)
    if not po_lines:
        raise GrError("Order has no lines.", code="missing_lines", http_status=400)
    return {**po, "pr_row": pr_row, "po_lines": po_lines}


def _validate_receive_lines(
    requested: list[dict[str, Any]] | None,
    po_lines: list[dict[str, Any]],
    already: dict[str, float],
    *,
    client_outlet: str | None = None,
    client_supplier: str | None = None,
    stored_outlet: str,
    stored_supplier: str,
) -> list[dict[str, Any]]:
    if client_outlet and client_outlet.strip() != stored_outlet:
        raise GrError(
            "Outlet does not match the purchase order.",
            code="outlet_mismatch",
            http_status=400,
        )
    if client_supplier and client_supplier.strip() != stored_supplier:
        raise GrError(
            "Supplier does not match the purchase order.",
            code="supplier_mismatch",
            http_status=400,
        )
    if not requested:
        raise GrError("At least one line is required.", code="missing_lines")
    by_line: dict[str, dict[str, Any]] = {}
    for pl in po_lines:
        lid = str(pl.get("line_id") or "").strip()
        if lid:
            by_line[lid] = pl
    out: list[dict[str, Any]] = []
    positive = 0
    for raw in requested:
        if not isinstance(raw, dict):
            raise GrError("Each line must be an object.", code="invalid_line")
        lid = str(raw.get("po_line_id") or raw.get("line_id") or "").strip()
        if not lid or lid not in by_line:
            raise GrError(
                "Line is not on this purchase order.",
                code="line_not_on_order",
            )
        try:
            qty = float(raw.get("received_qty", raw.get("qty")))
        except (TypeError, ValueError) as exc:
            raise GrError("Received qty must be numeric.", code="invalid_qty") from exc
        if qty < 0:
            raise GrError("Received qty cannot be negative.", code="invalid_qty")
        if qty > QTY_EPS:
            positive += 1
        ordered = float(by_line[lid].get("qty") or 0)
        prior = already.get(lid, 0.0)
        outstanding = ordered - prior
        if qty - outstanding > QTY_EPS:
            raise GrError(
                f"Received qty for {by_line[lid].get('item')} exceeds outstanding ({outstanding}).",
                code="qty_above_outstanding",
            )
        reason = str(raw.get("shortfall_reason") or raw.get("reason") or "").strip() or None
        out.append(
            {
                "po_line_id": lid,
                "item": by_line[lid]["item"],
                "received_qty": qty,
                "unit": by_line[lid].get("unit"),
                "shortfall_reason": reason,
            }
        )
    if positive == 0:
        raise GrError(
            "Enter a received quantity on at least one line.",
            code="no_qty_received",
        )
    return out


def _po_fully_received(
    po_lines: list[dict[str, Any]], already: dict[str, float], new_lines: list[dict[str, Any]]
) -> bool:
    new_by: dict[str, float] = {}
    for ln in new_lines:
        new_by[ln["po_line_id"]] = new_by.get(ln["po_line_id"], 0.0) + ln["received_qty"]
    for pl in po_lines:
        lid = str(pl.get("line_id") or "")
        ordered = float(pl.get("qty") or 0)
        total = already.get(lid, 0.0) + new_by.get(lid, 0.0)
        if ordered - total > QTY_EPS:
            return False
    return bool(po_lines)


def create_goods_receipt(
    *,
    person_id: str,
    po_id: str,
    lines: list[dict[str, Any]],
    notes: str | None = None,
    outlet_id: str | None = None,
    supplier_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise GrError("Authentication required.", code="unauthenticated", http_status=401)
    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_gr_schema(c)
        source = _validate_source_po(po_id, c)
        oid = str(source["outlet_id"])
        asg = require_receive(pid, oid, c)
        approver = _pr_approver_person(c, str(source["pr_id"]))
        if approver and approver == pid:
            raise GrError(
                "The person who approved this request cannot also receive the goods.",
                code="approver_receive_denied",
                http_status=403,
            )
        already = _received_by_po_line(c, source["po_id"])
        validated = _validate_receive_lines(
            lines,
            source["po_lines"],
            already,
            client_outlet=(outlet_id or "").strip() or None,
            client_supplier=(supplier_id or "").strip() or None,
            stored_outlet=oid,
            stored_supplier=str(source["supplier_id"]),
        )
        complete = _po_fully_received(source["po_lines"], already, validated)
        status = "COMPLETE" if complete else "PARTIAL"
        ts = _ops.now_utc_iso()
        gr_id = mint_gr_id()
        c.execute(
            """
            INSERT INTO bzg_ops_goods_receipts (
              gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              receiver_person_id, receiver_assignment_id, notes, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gr_id,
                source["po_id"],
                source["pr_id"],
                oid,
                source["entity_id"],
                source["supplier_id"],
                source["supplier_name"],
                pid,
                asg.get("assignment_id"),
                (notes or "").strip() or None,
                status,
                ts,
            ),
        )
        for line in validated:
            if line["received_qty"] <= QTY_EPS:
                continue
            c.execute(
                """
                INSERT INTO bzg_ops_gr_lines (
                  line_id, gr_id, po_line_id, item, received_qty, shortfall_reason, unit, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"GRL-{uuid.uuid4().hex[:12].upper()}",
                    gr_id,
                    line["po_line_id"],
                    line["item"],
                    line["received_qty"],
                    line.get("shortfall_reason"),
                    line.get("unit"),
                    ts,
                ),
            )
        pr_state = str(source["pr_row"].get("state") or "")
        dest = "RECEIVED" if complete else "PARTIALLY_RECEIVED"
        if pr_state != dest:
            try:
                _ops.transition_pr(
                    str(source["pr_id"]),
                    dest,
                    verified_person_id=pid,
                    actor_type="PERSON",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _ops.UmaOpsError as exc:
                raise GrError(str(exc), code=getattr(exc, "code", "transition_failed")) from exc
        _audit.record_event(
            action="bzg.receiving.create",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=source["pr_row"].get("venue"),
            resource_type="bzg_goods_receipt",
            resource_id=gr_id,
            metadata={
                "po_id": source["po_id"],
                "pr_id": source["pr_id"],
                "outlet_id": oid,
                "status": status,
                "line_count": len([ln for ln in validated if ln["received_qty"] > QTY_EPS]),
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _gr_row(c, gr_id)
        assert row
        return _enrich_gr(row, c)
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


def get_goods_receipt(
    gr_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_gr_schema(c)
        row = _gr_row(c, (gr_id or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_receive(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_gr(row, c)
    finally:
        if own:
            c.close()


def get_po_for_receiving(
    po_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_gr_schema(c)
        row = _po.get_purchase_order(po_id, person_id=person_id, conn=c)
        if not row:
            return None
        enriched = enrich_po_lines(row, c)
        pr_row = _ops.get_pr(str(row.get("pr_id") or ""), conn=c)
        can_recv = False
        if person_id and pr_row:
            state = str(pr_row.get("state") or "")
            if state in ("ORDERED", "PARTIALLY_RECEIVED") and not pr_row.get("example"):
                can_recv = can_receive(person_id, str(row.get("outlet_id") or ""), c)[0]
        enriched["can_receive"] = can_recv
        enriched["receive_permission"] = receive_permission(c)
        return {**enriched, **HONESTY}
    finally:
        if own:
            c.close()
