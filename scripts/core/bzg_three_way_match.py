#!/usr/bin/env python3
"""BZG-P2P-THREE-WAY-1 — Three-way match: PO, goods receipt, supplier nota (Beta).

Persists bzg_ops_three_way_matches. Read-and-record only — not AP, not payment.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from core import audit as _audit
from core import bzg_goods_receiving as _gr
from core import bzg_outlet_registry as _outlets
from core import bzg_purchase_order as _po
from core import bzg_purchase_request as _pr
from core import bzg_supplier_bill as _bill
from core import rbac as _rbac
from core import uma_ops_console as _ops

PACK = "BZG-P2P-THREE-WAY-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_MATCH_RUN = "bzg.match.run"
PERM_MATCH_RUN_ID = "PERM-BZG-MATCH-RUN"
PERM_MATCH_ACCEPT = "bzg.match.accept"
PERM_MATCH_ACCEPT_ID = "PERM-BZG-MATCH-ACCEPT"
AUDIT_SOURCE = "bzg_three_way_match"
HISTORICAL_MATCH_PREFIX = "MATCH-HIST-"
PREVIOUS_SYSTEM_MATCH_LABEL = "Matched in the previous system"
QTY_EPS = _po.QTY_EPS
PRICE_EPS = _bill.PRICE_EPS
REFUSED_PR = _gr.REFUSED_PR

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "three_way_comparison": True,
    "not_ap": True,
    "not_a_payment": True,
    "no_payment_state_change": True,
}


class MatchError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_match_id() -> str:
    return f"M3W-UMA-{uuid.uuid4().hex[:12].upper()}"


def _match_table_columns(conn: sqlite3.Connection) -> set[str]:
    return {str(r[1]) for r in conn.execute("PRAGMA table_info(bzg_ops_three_way_matches)").fetchall()}


def ensure_match_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent three-way match table."""
    _bill.ensure_bill_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_three_way_matches'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_three_way_matches (
              match_id TEXT PRIMARY KEY,
              bill_id TEXT NOT NULL UNIQUE,
              gr_id TEXT NOT NULL,
              po_id TEXT NOT NULL,
              pr_id TEXT NOT NULL,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              result TEXT NOT NULL CHECK (result IN ('MATCH', 'DIFFERENCE')),
              summary TEXT NOT NULL,
              line_details_json TEXT NOT NULL,
              matcher_person_id TEXT NOT NULL,
              matcher_assignment_id TEXT,
              created_at TEXT NOT NULL,
              exception_accepted_by_person_id TEXT,
              exception_accepted_by_assignment_id TEXT,
              exception_accept_reason TEXT,
              exception_accepted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_3wm_po ON bzg_ops_three_way_matches(po_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_3wm_gr ON bzg_ops_three_way_matches(gr_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_3wm_outlet ON bzg_ops_three_way_matches(outlet_id);
            """
        )
        added.append("bzg_ops_three_way_matches")
    else:
        cols = _match_table_columns(conn)
        for col, typ in (
            ("exception_accepted_by_person_id", "TEXT"),
            ("exception_accepted_by_assignment_id", "TEXT"),
            ("exception_accept_reason", "TEXT"),
            ("exception_accepted_at", "TEXT"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE bzg_ops_three_way_matches ADD COLUMN {col} {typ}")
                added.append(f"bzg_ops_three_way_matches.{col}")
    return added


def is_historical_match_id(match_id: str | None) -> bool:
    return str(match_id or "").strip().startswith(HISTORICAL_MATCH_PREFIX)


def historical_match_label(match_id: str | None) -> str | None:
    return PREVIOUS_SYSTEM_MATCH_LABEL if is_historical_match_id(match_id) else None


def match_permission(conn: sqlite3.Connection) -> str:
    return PERM_MATCH_RUN


def match_accept_permission(conn: sqlite3.Connection) -> str:
    return PERM_MATCH_ACCEPT


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_run_match(
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
    if not _rbac.can(pid, PERM_MATCH_RUN, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_run_match(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_run_match(person_id, outlet_id, conn)
    if not ok or not asg:
        raise MatchError(
            "You cannot run a three-way match for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def can_accept_difference(
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
    if not _rbac.can(pid, PERM_MATCH_ACCEPT, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_accept_difference(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_accept_difference(person_id, outlet_id, conn)
    if not ok or not asg:
        raise MatchError(
            "You cannot accept a match difference for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def _match_row(conn: sqlite3.Connection, match_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_three_way_matches WHERE match_id=?", (match_id,)
    ).fetchone()
    return dict(row) if row else None


def _match_by_bill(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_three_way_matches WHERE bill_id=?", (bill_id,)
    ).fetchone()
    return dict(row) if row else None


def _exception_accepted(row: dict[str, Any]) -> bool:
    return bool((row.get("exception_accepted_by_person_id") or "").strip())


def _ap_eligible(row: dict[str, Any]) -> bool:
    result = str(row.get("result") or "")
    if result == "MATCH":
        return True
    if result == "DIFFERENCE":
        return _exception_accepted(row)
    return False


def _enrich_match(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    try:
        out["line_details"] = json.loads(row.get("line_details_json") or "[]")
    except json.JSONDecodeError:
        out["line_details"] = []
    out["is_match"] = str(row.get("result") or "") == "MATCH"
    out["is_difference"] = str(row.get("result") or "") == "DIFFERENCE"
    out["exception_accepted"] = _exception_accepted(row)
    out["difference_pending_acceptance"] = out["is_difference"] and not out["exception_accepted"]
    out["ap_eligible"] = _ap_eligible(row)
    hist_label = historical_match_label(str(row.get("match_id") or ""))
    if hist_label:
        out["match_label"] = hist_label
    if out["exception_accepted"]:
        out["acceptance_display"] = (row.get("exception_accept_reason") or "").strip() or None
    return out


def _validate_chain(
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
        raise MatchError("Supplier nota not found.", code="not_found", http_status=404)
    bill = dict(bill_row)
    pr_id = str(bill.get("pr_id") or "")
    if pr_id == REFUSED_PR:
        raise MatchError("This nota cannot be matched.", code="refused_pr", http_status=400)
    pr_row = _ops.get_pr(pr_id, conn=conn)
    if not pr_row:
        raise MatchError("Source request not found.", code="not_found", http_status=404)
    if pr_row.get("example"):
        raise MatchError("Example notas cannot be matched.", code="example_denied", http_status=400)

    stored_gr = str(bill.get("gr_id") or "")
    stored_po = str(bill.get("po_id") or "")
    stored_outlet = str(bill.get("outlet_id") or "")
    stored_supplier = str(bill.get("supplier_id") or "")

    if client_gr_id and client_gr_id.strip() != stored_gr:
        raise MatchError(
            "Receipt does not match this nota.",
            code="gr_mismatch",
            http_status=400,
        )
    if client_po_id and client_po_id.strip() != stored_po:
        raise MatchError(
            "Order does not match this nota.",
            code="po_mismatch",
            http_status=400,
        )
    if client_outlet and client_outlet.strip() != stored_outlet:
        raise MatchError(
            "Outlet does not match the saved documents.",
            code="outlet_mismatch",
            http_status=400,
        )
    if client_supplier and client_supplier.strip() != stored_supplier:
        raise MatchError(
            "Supplier does not match the saved documents.",
            code="supplier_mismatch",
            http_status=400,
        )

    gr_row = conn.execute(
        "SELECT * FROM bzg_ops_goods_receipts WHERE gr_id=?", (stored_gr,)
    ).fetchone()
    if not gr_row:
        raise MatchError("Goods receipt not found.", code="not_found", http_status=404)
    gr = dict(gr_row)
    if str(gr.get("po_id") or "") != stored_po:
        raise MatchError(
            "Receipt is not on the same order as this nota.",
            code="chain_mismatch",
            http_status=400,
        )
    if str(gr.get("pr_id") or "") != pr_id:
        raise MatchError(
            "Receipt is not on the same request as this nota.",
            code="chain_mismatch",
            http_status=400,
        )

    po_row = conn.execute(
        "SELECT * FROM bzg_ops_purchase_orders WHERE po_id=?", (stored_po,)
    ).fetchone()
    if not po_row:
        raise MatchError("Purchase order not found.", code="not_found", http_status=404)
    po = dict(po_row)
    if str(po.get("pr_id") or "") != pr_id:
        raise MatchError(
            "Order is not on the same request as this nota.",
            code="chain_mismatch",
            http_status=400,
        )

    po_lines = _po._po_lines(conn, stored_po)  # noqa: SLF001
    gr_lines = _gr._gr_lines(conn, stored_gr)  # noqa: SLF001
    bill_lines = _bill._bill_lines(conn, bid)  # noqa: SLF001
    if not po_lines or not gr_lines or not bill_lines:
        raise MatchError("Documents are missing line detail.", code="missing_lines", http_status=400)

    return {
        "bill": bill,
        "gr": gr,
        "po": po,
        "pr_row": pr_row,
        "po_lines": po_lines,
        "gr_lines": gr_lines,
        "bill_lines": bill_lines,
    }


def _compare_documents(source: dict[str, Any]) -> dict[str, Any]:
    po_by_line: dict[str, dict[str, Any]] = {}
    for pl in source["po_lines"]:
        lid = str(pl.get("line_id") or "").strip()
        if lid:
            po_by_line[lid] = pl

    gr_by_po_line: dict[str, dict[str, Any]] = {}
    for gl in source["gr_lines"]:
        plid = str(gl.get("po_line_id") or "").strip()
        if plid:
            gr_by_po_line[plid] = gl

    bill_by_po_line: dict[str, dict[str, Any]] = {}
    for bl in source["bill_lines"]:
        plid = str(bl.get("po_line_id") or "").strip()
        if plid:
            bill_by_po_line[plid] = bl

    line_details: list[dict[str, Any]] = []
    differences: list[str] = []

    for po_line_id, pl in po_by_line.items():
        item = str(pl.get("item") or "").strip()
        ordered = float(pl.get("qty") or 0)
        unit = pl.get("unit")
        gl = gr_by_po_line.get(po_line_id)
        bl = bill_by_po_line.get(po_line_id)
        received = float(gl.get("received_qty") or 0) if gl else 0.0
        billed_qty = float(bl.get("billed_qty") or 0) if bl else 0.0
        billed_price = float(bl.get("billed_unit_price") or 0) if bl else 0.0
        line_amount = float(bl.get("line_amount") or 0) if bl else 0.0

        line_entry: dict[str, Any] = {
            "item": item,
            "unit": unit,
            "ordered_qty": ordered,
            "received_qty": received,
            "billed_qty": billed_qty,
            "billed_unit_price": billed_price,
            "line_amount": line_amount,
            "differences": [],
        }

        if abs(received - ordered) > QTY_EPS:
            if received < ordered:
                msg = f"{item}: received short — ordered {ordered:g}, received {received:g}"
            else:
                msg = f"{item}: received over — ordered {ordered:g}, received {received:g}"
            line_entry["differences"].append(msg)
            differences.append(msg)

        if bl is None and received > QTY_EPS:
            msg = f"{item}: not billed — received {received:g}, billed 0"
            line_entry["differences"].append(msg)
            differences.append(msg)
        elif abs(billed_qty - received) > QTY_EPS:
            if billed_qty < received:
                msg = f"{item}: billed short — received {received:g}, billed {billed_qty:g}"
            else:
                msg = f"{item}: billed over — received {received:g}, billed {billed_qty:g}"
            line_entry["differences"].append(msg)
            differences.append(msg)

        if abs(billed_qty - ordered) > QTY_EPS and not line_entry["differences"]:
            if billed_qty < ordered:
                msg = f"{item}: billed short vs order — ordered {ordered:g}, billed {billed_qty:g}"
            else:
                msg = f"{item}: billed over vs order — ordered {ordered:g}, billed {billed_qty:g}"
            line_entry["differences"].append(msg)
            differences.append(msg)

        line_details.append(line_entry)

    bill = source["bill"]
    total_diff = float(bill.get("total_difference") or 0)
    if abs(total_diff) > PRICE_EPS:
        stated = float(bill.get("stated_total") or 0)
        computed = float(bill.get("computed_total") or 0)
        msg = (
            f"nota total difference — written Rp {stated:,.0f}, "
            f"lines Rp {computed:,.0f}"
        ).replace(",", ".")
        differences.append(msg)

    result = "MATCH" if not differences else "DIFFERENCE"
    summary = "match" if result == "MATCH" else "; ".join(differences)
    return {
        "result": result,
        "summary": summary,
        "line_details": line_details,
        "differences": differences,
    }


def run_three_way_match(
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
        raise MatchError("Authentication required.", code="unauthenticated", http_status=401)
    bid = (bill_id or "").strip()
    if not bid:
        raise MatchError("Supplier nota is required.", code="missing_bill")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_match_schema(c)
        existing = _match_by_bill(c, bid)
        if existing:
            return _enrich_match(existing, c)

        source = _validate_chain(
            c,
            bill_id=bid,
            client_gr_id=(gr_id or "").strip() or None,
            client_po_id=(po_id or "").strip() or None,
            client_outlet=(outlet_id or "").strip() or None,
            client_supplier=(supplier_id or "").strip() or None,
        )
        oid = str(source["bill"]["outlet_id"])
        asg = require_run_match(pid, oid, c)
        comparison = _compare_documents(source)
        ts = _ops.now_utc_iso()
        match_id = mint_match_id()
        c.execute(
            """
            INSERT INTO bzg_ops_three_way_matches (
              match_id, bill_id, gr_id, po_id, pr_id, outlet_id, entity_id,
              supplier_id, supplier_name, result, summary, line_details_json,
              matcher_person_id, matcher_assignment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id,
                bid,
                source["bill"]["gr_id"],
                source["bill"]["po_id"],
                source["bill"]["pr_id"],
                oid,
                source["bill"]["entity_id"],
                source["bill"]["supplier_id"],
                source["bill"]["supplier_name"],
                comparison["result"],
                comparison["summary"],
                json.dumps(comparison["line_details"], sort_keys=True),
                pid,
                asg.get("assignment_id"),
                ts,
            ),
        )
        _audit.record_event(
            action="bzg.three_way_match.run",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=source["pr_row"].get("venue"),
            resource_type="bzg_three_way_match",
            resource_id=match_id,
            metadata={
                "bill_id": bid,
                "gr_id": source["bill"]["gr_id"],
                "po_id": source["bill"]["po_id"],
                "pr_id": source["bill"]["pr_id"],
                "outlet_id": oid,
                "match_result": comparison["result"],
                "difference_count": len(comparison["differences"]),
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _match_row(c, match_id)
        assert row
        return _enrich_match(row, c)
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


def accept_match_difference(
    *,
    person_id: str,
    bill_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise MatchError("Authentication required.", code="unauthenticated", http_status=401)
    bid = (bill_id or "").strip()
    if not bid:
        raise MatchError("Supplier nota is required.", code="missing_bill")
    note = (reason or "").strip()
    if not note:
        raise MatchError(
            "A reason is required to accept the difference.",
            code="missing_reason",
        )

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_match_schema(c)
        row = _match_by_bill(c, bid)
        if not row:
            raise MatchError(
                "Three-way match not found for this nota.",
                code="not_matched",
                http_status=404,
            )
        if str(row.get("result") or "") != "DIFFERENCE":
            raise MatchError(
                "Only a difference can be accepted.",
                code="not_difference",
                http_status=400,
            )
        if _exception_accepted(row):
            return _enrich_match(row, c)
        matcher = str(row.get("matcher_person_id") or "")
        if matcher and matcher == pid:
            raise MatchError(
                "The person who ran the match cannot accept the difference.",
                code="sod_matcher",
                http_status=403,
            )
        oid = str(row.get("outlet_id") or "")
        asg = require_accept_difference(pid, oid, c)
        ts = _ops.now_utc_iso()
        c.execute(
            """
            UPDATE bzg_ops_three_way_matches
            SET exception_accepted_by_person_id=?,
                exception_accepted_by_assignment_id=?,
                exception_accept_reason=?,
                exception_accepted_at=?
            WHERE bill_id=?
            """,
            (pid, asg.get("assignment_id"), note, ts, bid),
        )
        pr_row = _ops.get_pr(str(row.get("pr_id") or ""), conn=c)
        _audit.record_event(
            action="bzg.three_way_match.accept_difference",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=pr_row.get("venue") if pr_row else None,
            resource_type="bzg_three_way_match",
            resource_id=str(row.get("match_id") or ""),
            metadata={
                "bill_id": bid,
                "match_id": row.get("match_id"),
                "reason": note,
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        updated = _match_by_bill(c, bid)
        assert updated
        return _enrich_match(updated, c)
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


def get_three_way_match(
    match_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_match_schema(c)
        row = _match_row(c, (match_id or "").strip())
        if not row:
            row = _match_by_bill(c, (match_id or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_run_match(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_match(row, c)
    finally:
        if own:
            c.close()


def list_three_way_matches(
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
        ensure_match_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_MATCH_RUN, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params: list[Any] = list(sorted(allowed))
        lim = max(1, min(int(limit), 200))
        params.append(lim)
        rows = c.execute(
            f"""
            SELECT * FROM bzg_ops_three_way_matches
            WHERE outlet_id IN ({placeholders})
            ORDER BY created_at DESC LIMIT ?
            """,
            params,
        ).fetchall()
        return [_enrich_match(dict(r), c) for r in rows]
    finally:
        if own:
            c.close()


def match_for_bill(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any] | None:
    row = _match_by_bill(conn, (bill_id or "").strip())
    return _enrich_match(row, conn) if row else None


def list_eligible_trios(
    person_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Saved bill+receipt+order chains with no match yet."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_match_schema(c)
        allowed = {o["outlet_id"] for o in _pr.person_outlets(pid, c)}
        if not allowed and _rbac.can(pid, PERM_MATCH_RUN, {"entity_id": LEGAL_ENTITY}, conn=c):
            allowed = {o["outlet_id"] for o in _outlets.list_outlets(c)}
        if not allowed:
            return []
        placeholders = ",".join("?" * len(allowed))
        params = list(sorted(allowed))
        rows = c.execute(
            f"""
            SELECT b.bill_id, b.gr_id, b.po_id, b.pr_id, b.outlet_id,
                   b.supplier_id, b.supplier_name, b.nota_number, b.nota_date,
                   b.created_at AS bill_created_at
            FROM bzg_ops_supplier_bills b
            JOIN bzg_ops_goods_receipts g ON g.gr_id = b.gr_id AND g.po_id = b.po_id
            JOIN bzg_ops_purchase_orders p ON p.po_id = b.po_id AND p.pr_id = b.pr_id
            JOIN bzg_ops_purchase_requests pr ON pr.pr_id = b.pr_id
            LEFT JOIN bzg_ops_three_way_matches m ON m.bill_id = b.bill_id
            WHERE b.outlet_id IN ({placeholders})
              AND pr.example = 0
              AND pr.pr_id != ?
              AND m.match_id IS NULL
            ORDER BY b.created_at DESC
            """,
            (*params, REFUSED_PR),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            oid = str(d.get("outlet_id") or "")
            outlet = _outlets.get_outlet(oid, conn=c)
            if outlet:
                d["outlet_display_name"] = outlet.get("display_name")
            out.append(d)
        return out
    finally:
        if own:
            c.close()
