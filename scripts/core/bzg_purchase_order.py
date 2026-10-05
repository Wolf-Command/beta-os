#!/usr/bin/env python3
"""BZG-P2P-PO-1 — Purchase order from approved purchase request (Beta).

Persists bzg_ops_purchase_orders / bzg_ops_po_lines. APPROVED → ORDERED only
when a PO row is saved. Not receiving, not payment, not goods receipt.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Callable

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import bzg_purchase_request as _pr
from core import rbac as _rbac
from core import uma_ops_console as _ops

PACK = "BZG-P2P-PO-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_PO_CREATE = "bzg.po.create"
PERM_PO_CREATE_ID = "PERM-BZG-PO-CREATE"
AUDIT_SOURCE = "bzg_purchase_order"
QTY_EPS = 1e-6

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "goods_receipt": False,
    "not_a_payment": True,
    "not_goods_receipt": True,
}

# Tests may replace; production reads Alchemist projection read-only.
_supplier_resolver: Callable[[str], dict[str, Any] | None] | None = None


class PoError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_po_id() -> str:
    return f"PO-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_po_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent PO tables."""
    _ops.ensure_schema(conn)
    _pr.ensure_pr_columns(conn)
    added: list[str] = []
    exists_po = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_purchase_orders'"
    ).fetchone()
    if not exists_po:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_purchase_orders (
              po_id TEXT PRIMARY KEY,
              pr_id TEXT NOT NULL UNIQUE,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              created_by_person_id TEXT NOT NULL,
              created_by_assignment_id TEXT,
              state TEXT NOT NULL DEFAULT 'OPEN',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_po_pr ON bzg_ops_purchase_orders(pr_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_po_outlet ON bzg_ops_purchase_orders(outlet_id);

            CREATE TABLE IF NOT EXISTS bzg_ops_po_lines (
              line_id TEXT PRIMARY KEY,
              po_id TEXT NOT NULL,
              pr_line_id TEXT,
              item TEXT NOT NULL,
              qty REAL NOT NULL,
              unit TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_po_lines_po ON bzg_ops_po_lines(po_id);
            """
        )
        added.extend(["bzg_ops_purchase_orders", "bzg_ops_po_lines"])
    return added


def _default_supplier_lookup(supplier_id: str) -> dict[str, Any] | None:
    from core import uma_real_projection as _real

    sid = (supplier_id or "").strip()
    if not sid:
        return None
    try:
        payload = _real.list_suppliers(limit=500)
    except Exception:
        return None
    for row in payload.get("suppliers") or []:
        if str(row.get("supplier_id")) == sid:
            return {"supplier_id": sid, "name": str(row.get("name") or "").strip()}
    return None


def resolve_supplier(supplier_id: str) -> dict[str, Any] | None:
    resolver = _supplier_resolver or _default_supplier_lookup
    return resolver((supplier_id or "").strip())


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_create_po(
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
    if not _rbac.can(pid, PERM_PO_CREATE, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_create_po(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_create_po(person_id, outlet_id, conn)
    if not ok or not asg:
        raise PoError(
            "You cannot create a purchase order for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _po_row(conn: sqlite3.Connection, po_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_purchase_orders WHERE po_id=?", (po_id,)
    ).fetchone()
    return dict(row) if row else None


def _po_lines(conn: sqlite3.Connection, po_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT line_id, pr_line_id, item, qty, unit
        FROM bzg_ops_po_lines
        WHERE po_id=?
        ORDER BY created_at, line_id
        """,
        (po_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _enrich_po(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, "lines": _po_lines(conn, row["po_id"]), **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    pr_id = (row.get("pr_id") or "").strip()
    if pr_id:
        out["pr_href"] = f"/bzg/uma-blu/pr/{pr_id}"
    return out


def _validate_source_pr(pr_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    key = (pr_id or "").strip()
    if key == "PR-UMA-0E65E353A422":
        raise PoError("This request cannot be ordered.", code="refused_pr", http_status=400)
    row = _ops.get_pr(key, conn=conn)
    if not row:
        raise PoError("Purchase request not found.", code="not_found", http_status=404)
    if row.get("example"):
        raise PoError("Example requests cannot be ordered.", code="example_denied", http_status=400)
    if row.get("state") != "APPROVED":
        raise PoError(
            "Only approved requests can become purchase orders.",
            code="not_approved",
            http_status=400,
        )
    oid = (row.get("outlet_id") or "").strip()
    if not oid:
        raise PoError("Request has no outlet.", code="missing_outlet", http_status=400)
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        raise PoError("Outlet not found in registry.", code="invalid_outlet", http_status=400)
    requester = (row.get("requester_person_id") or "").strip()
    if not requester:
        raise PoError("Request has no requester.", code="missing_requester", http_status=400)
    pr_lines = _ops.list_pr_lines(key, conn=conn)
    if not pr_lines:
        raise PoError("Request has no lines.", code="missing_lines", http_status=400)
    existing = conn.execute(
        "SELECT po_id FROM bzg_ops_purchase_orders WHERE pr_id=?", (key,)
    ).fetchone()
    if existing:
        raise PoError(
            "A purchase order already exists for this request.",
            code="already_ordered",
            http_status=409,
        )
    return {**row, "pr_lines": pr_lines}


def _validate_po_lines(
    requested: list[dict[str, Any]] | None, pr_lines: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not requested:
        raise PoError("At least one line is required.", code="missing_lines")
    by_item: dict[str, dict[str, Any]] = {}
    for pl in pr_lines:
        item = str(pl.get("item") or "").strip()
        if item:
            by_item[item] = pl
    out: list[dict[str, Any]] = []
    for raw in requested:
        if not isinstance(raw, dict):
            raise PoError("Each line must be an object.", code="invalid_line")
        item = str(raw.get("item") or "").strip()
        if not item or item not in by_item:
            raise PoError(
                f"Line item not on request: {item or '(empty)'}",
                code="line_not_on_request",
            )
        try:
            qty = float(raw.get("qty"))
        except (TypeError, ValueError) as exc:
            raise PoError("Line qty must be numeric.", code="invalid_qty") from exc
        if qty <= 0:
            raise PoError("Line qty must be positive.", code="invalid_qty")
        max_qty = float(by_item[item].get("qty") or 0)
        if qty - max_qty > QTY_EPS:
            raise PoError(
                f"Qty for {item} cannot exceed request qty ({max_qty}).",
                code="qty_above_request",
            )
        unit = str(raw.get("unit") or by_item[item].get("unit") or "").strip() or None
        out.append(
            {
                "item": item,
                "qty": qty,
                "unit": unit,
                "pr_line_id": by_item[item].get("source_line_id"),
            }
        )
    return out


def create_purchase_order(
    *,
    person_id: str,
    pr_id: str,
    supplier_id: str,
    lines: list[dict[str, Any]],
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise PoError("Authentication required.", code="unauthenticated", http_status=401)
    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_po_schema(c)
        source = _validate_source_pr(pr_id, c)
        oid = str(source["outlet_id"])
        asg = require_create_po(pid, oid, c)
        supplier = resolve_supplier(supplier_id)
        if not supplier or not supplier.get("name"):
            raise PoError(
                "Supplier not found in read-only supplier list.",
                code="invalid_supplier",
                http_status=400,
            )
        validated = _validate_po_lines(lines, source["pr_lines"])
        ts = _ops.now_utc_iso()
        po_id = mint_po_id()
        c.execute(
            """
            INSERT INTO bzg_ops_purchase_orders (
              po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              created_by_person_id, created_by_assignment_id, state, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
            """,
            (
                po_id,
                source["pr_id"],
                oid,
                LEGAL_ENTITY,
                supplier["supplier_id"],
                supplier["name"],
                pid,
                asg.get("assignment_id"),
                ts,
                ts,
            ),
        )
        for line in validated:
            c.execute(
                """
                INSERT INTO bzg_ops_po_lines (
                  line_id, po_id, pr_line_id, item, qty, unit, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"POL-{uuid.uuid4().hex[:12].upper()}",
                    po_id,
                    line.get("pr_line_id"),
                    line["item"],
                    line["qty"],
                    line.get("unit"),
                    ts,
                ),
            )
        try:
            _ops.transition_pr(
                source["pr_id"],
                "ORDERED",
                verified_person_id=pid,
                actor_type="PERSON",
                identity=identity,
                conn=c,
                commit=False,
            )
        except _ops.UmaOpsError as exc:
            raise PoError(str(exc), code=getattr(exc, "code", "transition_failed")) from exc
        _audit.record_event(
            action="bzg.po.create",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=source.get("venue"),
            resource_type="bzg_purchase_order",
            resource_id=po_id,
            metadata={
                "pr_id": source["pr_id"],
                "outlet_id": oid,
                "supplier_id": supplier["supplier_id"],
                "line_count": len(validated),
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _po_row(c, po_id)
        assert row
        return _enrich_po(row, c)
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


def get_purchase_order(
    po_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_po_schema(c)
        row = _po_row(c, (po_id or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_create_po(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_po(row, c)
    finally:
        if own:
            c.close()


def list_purchase_orders(
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
        ensure_po_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_PO_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        lim = max(1, min(int(limit), 200))
        params.append(lim)
        rows = c.execute(
            f"""
            SELECT * FROM bzg_ops_purchase_orders
            WHERE outlet_id IN ({placeholders})
            ORDER BY updated_at DESC LIMIT ?
            """,
            params,
        ).fetchall()
        return [_enrich_po(dict(r), c) for r in rows]
    finally:
        if own:
            c.close()


def list_awaiting_order(
    person_id: str,
    *,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Approved requests with no PO yet."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_po_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_PO_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        lim = max(1, min(int(limit), 100))
        params.append(lim)
        rows = c.execute(
            f"""
            SELECT pr.*
            FROM bzg_ops_purchase_requests pr
            LEFT JOIN bzg_ops_purchase_orders po ON po.pr_id = pr.pr_id
            WHERE pr.example=0
              AND pr.state='APPROVED'
              AND pr.outlet_id IS NOT NULL
              AND pr.outlet_id IN ({placeholders})
              AND pr.requester_person_id IS NOT NULL
              AND pr.pr_id != 'PR-UMA-0E65E353A422'
              AND po.po_id IS NULL
            ORDER BY pr.updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            oid = str(d.get("outlet_id") or "")
            outlet = _outlets.get_outlet(oid, conn=c)
            if outlet:
                d["outlet_display_name"] = outlet.get("display_name")
            d["lines"] = _ops.list_pr_lines(d["pr_id"], conn=c)
            out.append(d)
        return out
    finally:
        if own:
            c.close()


def workspace(
    person_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    from core import bzg_ap_ready as _ap
    from core import bzg_goods_receiving as _gr
    from core import bzg_supplier_bill as _bill
    from core import bzg_three_way_match as _match

    pid = (person_id or "").strip()
    own = conn is None
    c = conn or db_connect()
    try:
        _gr.ensure_gr_schema(c)
        _bill.ensure_bill_schema(c)
        _match.ensure_match_schema(c)
        _ap.ensure_ap_schema(c)
        can_any = bool(pid) and (
            _rbac.can(pid, PERM_PO_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c)
            or bool(_pr.person_outlets(pid, c))
        )
        orders = list_purchase_orders(pid, conn=c) if pid else []
        enriched_orders = [_gr.enrich_po_lines(o, c) for o in orders]
        can_recv = False
        can_capture_bill = False
        can_run_match = False
        can_accept_difference = False
        can_mark_ap_ready = False
        can_create = False
        if pid:
            for o in enriched_orders:
                oid = str(o.get("outlet_id") or "")
                if oid and _gr.can_receive(pid, oid, c)[0]:
                    can_recv = True
                if oid and _bill.can_capture_bill(pid, oid, c)[0]:
                    can_capture_bill = True
                if oid and _match.can_run_match(pid, oid, c)[0]:
                    can_run_match = True
                if oid and _match.can_accept_difference(pid, oid, c)[0]:
                    can_accept_difference = True
                if oid and _ap.can_mark_ap_ready(pid, oid, c)[0]:
                    can_mark_ap_ready = True
                if can_recv and can_capture_bill and can_run_match and can_accept_difference and can_mark_ap_ready:
                    break
            if bool(_assignment(pid, c)):
                for outlet in _pr.person_outlets(pid, c):
                    oid = str(outlet.get("outlet_id") or "")
                    if oid and can_create_po(pid, oid, c)[0]:
                        can_create = True
                        break
                if not can_create:
                    can_create = _rbac.can(pid, PERM_PO_CREATE, {"entity_id": LEGAL_ENTITY}, conn=c)
        return {
            "ok": True,
            "pack": PACK,
            "can_create_po": can_any and can_create,
            "can_receive": can_recv,
            "can_capture_bill": can_capture_bill,
            "can_run_match": can_run_match,
            "can_accept_difference": can_accept_difference,
            "can_mark_ap_ready": can_mark_ap_ready,
            "receive_permission": _gr.receive_permission(c),
            "bill_capture_permission": _bill.bill_capture_permission(c),
            "match_permission": _match.match_permission(c),
            "match_accept_permission": _match.match_accept_permission(c),
            "ap_mark_ready_permission": _ap.ap_mark_ready_permission(c),
            "orders": enriched_orders,
            "awaiting_order": list_awaiting_order(pid, conn=c) if pid else [],
            "eligible_three_way": _match.list_eligible_trios(pid, conn=c) if pid else [],
            "match_history": _match.list_three_way_matches(pid, conn=c) if pid else [],
            **HONESTY,
        }
    finally:
        if own:
            c.close()
