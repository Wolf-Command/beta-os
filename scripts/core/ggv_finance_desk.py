#!/usr/bin/env python3
"""FINANCE-CORE-GGV-1 — GGV Finance operational desk (entity ENT-GGV).

Operational browse + reconciliation shell. Shared code ≠ shared data.
No payment execution, no auto-reconcile, no GL posting. staff_ready=false.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from core import audit as _audit
from core import ggv_finance_nota as _nota
from core import rbac as _rbac

ENTITY = "ENT-GGV"
PACK = "FINANCE-CORE-GGV-1"

# Bills imported from Xero money.sqlite — only non-draft, non-deleted rows count as payable.
BILL_EXCLUDED_STATUSES = frozenset({"DRAFT", "DELETED", "VOID", "VOIDED"})
BILL_STATUS_LABELS = {
    "DRAFT": "Draft — not approved",
    "DELETED": "Deleted",
    "VOID": "Void",
    "VOIDED": "Void",
    "AUTHORISED": "Approved",
    "PAID": "Paid",
    "SUBMITTED": "Submitted",
}

OPERATIONAL_SECTIONS: tuple[dict[str, str], ...] = (
    {"id": "overview", "label": "Overview", "href": "/ggv/finance"},
    {"id": "banking", "label": "Banking", "href": "/ggv/finance/banking"},
    {"id": "transactions", "label": "Transactions", "href": "/ggv/finance/transactions"},
    {"id": "receipts_notas", "label": "Receipts/Notas", "href": "/ggv/finance/notas"},
    {"id": "bills", "label": "Bills", "href": "/ggv/finance/bills"},
    {"id": "invoices", "label": "Invoices", "href": "/ggv/finance/invoices"},
    {"id": "reconciliation", "label": "Reconciliation", "href": "/ggv/finance/reconciliation"},
    {"id": "suppliers", "label": "Suppliers", "href": "/ggv/finance/vendors"},
    {"id": "missing_evidence", "label": "Missing Evidence", "href": "/ggv/finance/missing-evidence"},
    {"id": "reports", "label": "Reports", "href": "/ggv/finance/reports"},
    {"id": "audit", "label": "Audit", "href": "/ggv/finance/audit"},
)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "auto_reconcile": False,
    "proven": False,
    "entity_id": ENTITY,
    "pack": PACK,
}


class GgvFinanceDeskError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def require_ggv_finance(person_id: str | None, conn: sqlite3.Connection) -> None:
    pid = (person_id or "").strip()
    if not pid:
        raise GgvFinanceDeskError("Sign in required.", code="unauthenticated", http_status=401)
    if not _rbac.can(pid, "finance.nota.read", {"entity_id": ENTITY}, conn=conn):
        raise GgvFinanceDeskError(
            "GGV Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
    )


def desk_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    entity_tables = (
        ("invoices", "ggv_invoices"),
        ("notas", "ggv_notas"),
        ("bills", "ggv_bills"),
        ("bank_imports", "ggv_bank_statement_imports"),
        ("bank_transactions", "ggv_bank_transactions"),
        ("receipt_accounting", "ggv_receipt_accounting"),
        ("uploads", "ggv_uploads"),
    )
    for key, table in entity_tables:
        if _table_exists(conn, table):
            row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE entity_id=?", (ENTITY,)).fetchone()
            counts[key] = int(row[0] if row else 0)
        else:
            counts[key] = 0
    if _table_exists(conn, "ggv_nota_files"):
        row = conn.execute(
            """
            SELECT COUNT(*) FROM ggv_nota_files f
            JOIN ggv_uploads u ON u.upload_id = f.upload_id
            WHERE u.entity_id=?
            """,
            (ENTITY,),
        ).fetchone()
        counts["nota_files"] = int(row[0] if row else 0)
    else:
        counts["nota_files"] = 0
    if _table_exists(conn, "ggv_vendors"):
        row = conn.execute(
            "SELECT COUNT(*) FROM ggv_vendors WHERE entity_id=? AND status='ACTIVE'",
            (ENTITY,),
        ).fetchone()
        counts["suppliers"] = int(row[0] if row else 0)
    else:
        counts["suppliers"] = 0
    return counts


def _txn_fixture_join() -> str:
    return """
        FROM ggv_bank_transactions t
        JOIN ggv_bank_statement_imports i ON i.import_id = t.import_id
        WHERE t.entity_id=? AND COALESCE(i.is_test_fixture,0)=0
    """


def reconciliation_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    matched = possible = unmatched = exception = total = 0
    if _table_exists(conn, "ggv_bank_transactions") and _table_exists(
        conn, "ggv_bank_statement_imports"
    ):
        row = conn.execute(
            f"""
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN t.human_confirmed=1 THEN 1 ELSE 0 END) AS matched,
              SUM(CASE WHEN t.human_confirmed=0 AND t.match_proposed=1 THEN 1 ELSE 0 END) AS possible,
              SUM(CASE WHEN t.human_confirmed=0 AND t.recon_status='EXCEPTION' THEN 1 ELSE 0 END) AS exception,
              SUM(CASE WHEN t.human_confirmed=0 AND t.match_proposed=0
                        AND t.recon_status NOT IN ('EXCEPTION','MATCHED') THEN 1 ELSE 0 END) AS unmatched
            {_txn_fixture_join()}
            """,
            (ENTITY,),
        ).fetchone()
        total = int(row["total"] or 0)
        matched = int(row["matched"] or 0)
        possible = int(row["possible"] or 0)
        exception = int(row["exception"] or 0)
        unmatched = int(row["unmatched"] or 0)
    rx_missing = 0
    if _table_exists(conn, "ggv_receipt_accounting"):
        rx_missing = int(
            conn.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND missing_evidence=1",
                (ENTITY,),
            ).fetchone()[0]
        )
    return {
        "bank_total": total,
        "bank_matched": matched,
        "bank_possible_match": possible,
        "bank_unmatched": unmatched,
        "bank_exception": exception,
        "bank_unmatched_legacy": unmatched,
        "bank_propose_match": possible,
        "bank_human_review": possible,
        "receipt_missing_evidence": rx_missing,
        "auto_reconcile": False,
        "propose_only": True,
    }


def _money_flow_this_month(conn: sqlite3.Connection) -> dict[str, str]:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    label = month
    note = ""
    if _table_exists(conn, "ggv_bank_statement_imports"):
        latest = conn.execute(
            """
            SELECT MAX(period_end) AS end_date
            FROM ggv_bank_statement_imports
            WHERE entity_id=? AND COALESCE(is_test_fixture,0)=0
            """,
            (ENTITY,),
        ).fetchone()
        end_date = str(latest["end_date"] or "")[:10] if latest else ""
        if end_date and len(end_date) >= 7:
            stmt_month = end_date[:7]
            if stmt_month < month:
                label = stmt_month
                note = f"No {month} statement uploaded yet — showing {stmt_month}."
    row = conn.execute(
        f"""
        SELECT COALESCE(SUM(t.credit),0) AS money_in, COALESCE(SUM(t.debit),0) AS money_out
        {_txn_fixture_join()} AND substr(t.txn_date,1,7)=?
        """,
        (ENTITY, label),
    ).fetchone()
    money_in = Decimal(str(row["money_in"] or 0))
    money_out = Decimal(str(row["money_out"] or 0))
    return {
        "month": label,
        "money_in_idr": str(money_in.quantize(Decimal("1"))),
        "money_out_idr": str(money_out.quantize(Decimal("1"))),
        "money_flow_note": note,
    }


def _confirmed_bill_refs(conn: sqlite3.Connection) -> set[str]:
    if not _table_exists(conn, "ggv_bank_transactions"):
        return set()
    return {
        str(r[0])
        for r in conn.execute(
            """
            SELECT DISTINCT matched_receipt_ref FROM ggv_bank_transactions
            WHERE entity_id=? AND human_confirmed=1 AND matched_receipt_ref IS NOT NULL
            """,
            (ENTITY,),
        ).fetchall()
        if r[0]
    }


def _bill_duplicate_groups(conn: sqlite3.Connection) -> tuple[int, int]:
    """Return (duplicate_group_count, duplicate_bill_row_count)."""
    if not _table_exists(conn, "ggv_bills"):
        return 0, 0
    rows = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM ggv_bills
        WHERE entity_id=? AND COALESCE(status,'') NOT IN ('DELETED')
        GROUP BY COALESCE(contact_name,''), COALESCE(amount,''), COALESCE(issued_on,'')
        HAVING COUNT(*) > 1
        """,
        (ENTITY,),
    ).fetchall()
    groups = len(rows)
    extras = sum(int(r[0]) - 1 for r in rows)
    return groups, extras


def bills_payable_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Approved bills still owing — excludes drafts, duplicates, and bank-confirmed matches."""
    out: dict[str, Any] = {
        "needs_paying_idr": "0",
        "needs_paying_count": 0,
        "draft_bills_count": 0,
        "draft_bills_idr": "0",
        "possible_duplicate_groups": 0,
        "possible_duplicate_bills": 0,
    }
    if not _table_exists(conn, "ggv_bills"):
        return out
    confirmed = _confirmed_bill_refs(conn)
    dup_groups, dup_bills = _bill_duplicate_groups(conn)
    out["possible_duplicate_groups"] = dup_groups
    out["possible_duplicate_bills"] = dup_bills
    draft_due = Decimal("0")
    draft_count = 0
    payable_due = Decimal("0")
    payable_count = 0
    dup_keys: set[tuple[str, str, str]] = {
        (
            str(r[0] or ""),
            str(r[1] or ""),
            str(r[2] or "")[:10],
        )
        for r in conn.execute(
            """
            SELECT contact_name, amount, issued_on
            FROM ggv_bills
            WHERE entity_id=? AND COALESCE(status,'') NOT IN ('DELETED')
            GROUP BY COALESCE(contact_name,''), COALESCE(amount,''), COALESCE(issued_on,'')
            HAVING COUNT(*) > 1
            """,
            (ENTITY,),
        ).fetchall()
    }
    for row in conn.execute(
        """
        SELECT bill_id, status, contact_name, amount, amount_due, issued_on
        FROM ggv_bills WHERE entity_id=?
        """,
        (ENTITY,),
    ).fetchall():
        status = str(row["status"] or "").upper()
        due_val = Decimal(str(row["amount_due"] or row["amount"] or 0))
        key = (
            str(row["contact_name"] or ""),
            str(row["amount"] or ""),
            str(row["issued_on"] or "")[:10],
        )
        if status in BILL_EXCLUDED_STATUSES:
            if status == "DRAFT" and due_val > 0:
                draft_count += 1
                draft_due += due_val
            continue
        if str(row["bill_id"]) in confirmed:
            continue
        if key in dup_keys:
            continue
        if due_val <= 0:
            continue
        payable_count += 1
        payable_due += due_val
    out["needs_paying_idr"] = str(payable_due.quantize(Decimal("1")))
    out["needs_paying_count"] = payable_count
    out["draft_bills_count"] = draft_count
    out["draft_bills_idr"] = str(draft_due.quantize(Decimal("1")))
    return out


def _needs_paying_idr(conn: sqlite3.Connection) -> str:
    return bills_payable_summary(conn)["needs_paying_idr"]


def _parse_exception_count(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "ggv_bank_statement_imports"):
        return 0
    total = 0
    for row in conn.execute(
        "SELECT parse_notes FROM ggv_bank_statement_imports WHERE entity_id=?",
        (ENTITY,),
    ).fetchall():
        try:
            meta = json.loads(row["parse_notes"] or "{}")
            rc = meta.get("row_counts") if isinstance(meta, dict) else {}
            total += len((rc or {}).get("exceptions") or [])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return total


def audit_tail(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    require_ggv_finance(person_id, conn)
    lim = max(1, min(int(limit or 50), 200))
    sources = ("ggv_finance_nota", "ggv_bank_statement1", "ggv_receipt_accounting1")
    events: list[dict[str, Any]] = []
    for src in sources:
        try:
            rows = _audit.list_events(source=src, limit=lim, conn=conn)
        except Exception:
            rows = []
        for row in rows:
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if str(meta.get("entity_id") or ENTITY) != ENTITY:
                continue
            events.append(row)
    events.sort(key=lambda r: str(r.get("occurred_at") or ""), reverse=True)
    events = events[:lim]
    return {
        "ok": True,
        "entity_id": ENTITY,
        "events": events,
        "count": len(events),
        **HONESTY,
    }


def desk_overview(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    require_ggv_finance(person_id, conn)
    counts = desk_counts(conn)
    recon = reconciliation_summary(conn)
    flow = _money_flow_this_month(conn) if _table_exists(conn, "ggv_bank_transactions") else {}
    payable = bills_payable_summary(conn)
    missing_evidence = int(recon.get("receipt_missing_evidence") or 0) + int(
        recon.get("bank_unmatched") or 0
    )
    return {
        "ok": True,
        "title": "GGV Finance",
        "entity_id": ENTITY,
        "operational": True,
        "completeness_only": False,
        "operational_sections": list(OPERATIONAL_SECTIONS),
        "counts": counts,
        "reconciliation": recon,
        "needs_reconciling": int(recon.get("bank_unmatched") or 0) + int(
            recon.get("bank_possible_match") or 0
        ),
        "missing_evidence": missing_evidence,
        "needs_paying_idr": payable["needs_paying_idr"],
        "needs_paying_count": payable["needs_paying_count"],
        "draft_bills_count": payable["draft_bills_count"],
        "draft_bills_idr": payable["draft_bills_idr"],
        "possible_duplicate_groups": payable["possible_duplicate_groups"],
        "possible_duplicate_bills": payable["possible_duplicate_bills"],
        "money_in_this_month_idr": flow.get("money_in_idr", "0"),
        "money_out_this_month_idr": flow.get("money_out_idr", "0"),
        "money_flow_month": flow.get("month", ""),
        "money_flow_note": flow.get("money_flow_note", ""),
        "unresolved_exceptions": int(recon.get("bank_exception") or 0) + _parse_exception_count(conn),
        "links": {
            "reconciliation": "/ggv/finance/reconciliation",
            "missing_evidence": "/ggv/finance/missing-evidence",
            "bills": "/ggv/finance/bills",
            "banking": "/ggv/finance/banking",
            "notas": "/ggv/finance/notas",
        },
        "matt_test_urls": {
            "nota": "/ggv/finance/notas",
            "bank_statement": "/ggv/finance/banking",
            "reconciliation": "/ggv/finance/reconciliation",
        },
        **HONESTY,
    }


def reconciliation_board(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    import_id: str | None = None,
    month: str | None = None,
    match_status: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    require_ggv_finance(person_id, conn)
    from core import ggv_bank_statement1 as _gbs

    imports = _gbs.list_imports(verified_person_id=person_id, conn=conn)
    txns = _gbs.list_transactions(
        verified_person_id=person_id,
        import_id=import_id,
        month=month,
        match_status=match_status,
        offset=offset,
        limit=limit,
        conn=conn,
    )
    summary = reconciliation_summary(conn)
    return {
        "ok": True,
        "entity_id": ENTITY,
        "summary": summary,
        "imports": imports.get("imports") or [],
        "transactions": txns.get("transactions") or [],
        "transaction_total": txns.get("total_count", 0),
        "transaction_offset": txns.get("offset", 0),
        "transaction_limit": txns.get("limit", limit),
        "filters": {
            "import_id": import_id,
            "month": month,
            "match_status": match_status,
        },
        "propose_only": True,
        "auto_reconcile": False,
        "message": "Propose-only matching. No auto-post. No Reconcile button.",
        **HONESTY,
    }
