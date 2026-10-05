#!/usr/bin/env python3
"""FINANCE-CORE-AMG-PROVE-1 — AMG Finance operational desk (entity ENT-AMG).

Reuses Finance Core desk patterns from GGV. Shared code ≠ shared data.
No payment execution, no auto-reconcile. staff_ready=false.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core import atrium_historical as _atrium_hist
from core import audit as _audit
from core import entity_books as _books
from core import finance_core_entity as _fce
from core import ggv_finance_invoice as _inv
from core import rbac as _rbac

ENTITY = "ENT-AMG"
PACK = "FINANCE-CORE-AMG-PROVE-1"
_CFG = _fce.entity_config(ENTITY)

OPERATIONAL_SECTIONS: tuple[dict[str, str], ...] = (
    {"id": "overview", "label": "Overview", "href": "/amg/finance/notas"},
    {"id": "banking", "label": "Banking", "href": "/amg/finance/banking"},
    {"id": "transactions", "label": "Transactions", "href": "/amg/finance/transactions"},
    {"id": "receipts_notas", "label": "Receipts/Notas", "href": "/amg/finance/notas"},
    {"id": "bills", "label": "Bills", "href": "/amg/finance/bills"},
    {"id": "invoices", "label": "Invoices", "href": "/amg/finance/invoices"},
    {"id": "reconciliation", "label": "Reconciliation", "href": "/amg/finance/reconciliation"},
    {"id": "suppliers", "label": "Suppliers", "href": "/amg/finance/vendors"},
    {"id": "missing_evidence", "label": "Missing Evidence", "href": "/amg/finance/missing-evidence"},
    {"id": "reports", "label": "Reports", "href": "/amg/finance/reports"},
    {"id": "audit", "label": "Audit", "href": "/amg/finance/audit"},
)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "auto_reconcile": False,
    "proven": False,
    "entity_id": ENTITY,
    "pack": PACK,
}


class AmgFinanceDeskError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _can_read_finance(person_id: str, conn: sqlite3.Connection) -> bool:
    ctx = {"entity_id": ENTITY}
    return bool(
        _rbac.can(person_id, "finance.nota.read", ctx, conn=conn)
        or _rbac.can(person_id, "atrium.board.read", ctx, conn=conn)
    )


def require_amg_finance(person_id: str | None, conn: sqlite3.Connection) -> None:
    pid = (person_id or "").strip()
    if not pid:
        raise AmgFinanceDeskError("Sign in required.", code="unauthenticated", http_status=401)
    if not _can_read_finance(pid, conn):
        raise AmgFinanceDeskError(
            "AMG Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def historical_notice() -> dict[str, Any]:
    cutover = _atrium_hist.DEFAULT_CUTOVER
    return {
        "has_historical_supplier_po_bill_source": False,
        "cutover_date": cutover,
        "message": (
            "No historical supplier, purchase order, or bill records exist before "
            f"Wolf cutover on {cutover}. Wolf-created uploads and notas appear below."
        ),
    }


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


def list_vendors_readonly(
    person_id: str,
    query: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 30,
) -> dict[str, Any]:
    """Browse Wolf-created AMG vendors without vendor.write permissions."""
    require_amg_finance(person_id, conn)
    from core import ggv_finance_nota as _nota

    q = _nota.norm_name(query)
    lim = max(1, min(int(limit or 30), 200))
    if not q:
        rows = conn.execute(
            """
            SELECT * FROM ggv_vendors
            WHERE entity_id=? AND status='ACTIVE'
            ORDER BY updated_at DESC LIMIT ?
            """,
            (ENTITY, lim),
        ).fetchall()
    else:
        like = f"%{q}%"
        rows = conn.execute(
            """
            SELECT * FROM ggv_vendors
            WHERE entity_id=? AND status='ACTIVE'
              AND (
                name_norm LIKE ? OR ifnull(email_norm,'') LIKE ?
                OR ifnull(phone_norm,'') LIKE ? OR ifnull(tax_norm,'') LIKE ?
              )
            ORDER BY display_name LIMIT ?
            """,
            (ENTITY, like, like, _nota.norm_phone(query), _nota.norm_tax(query), lim),
        ).fetchall()
    return {
        "ok": True,
        "vendors": [_nota._vendor_public(row) for row in rows],
        "historical": historical_notice(),
        **HONESTY,
    }


def reconciliation_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    bank_unmatched = 0
    bank_proposed = 0
    bank_human_review = 0
    if _table_exists(conn, "ggv_bank_transactions"):
        bank_unmatched = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM ggv_bank_transactions
                WHERE entity_id=? AND recon_status IN ('UNIDENTIFIED','NEEDS_RECEIPT')
                  AND human_confirmed=0
                """,
                (ENTITY,),
            ).fetchone()[0]
        )
        bank_proposed = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM ggv_bank_transactions
                WHERE entity_id=? AND match_proposed=1 AND human_confirmed=0
                """,
                (ENTITY,),
            ).fetchone()[0]
        )
        bank_human_review = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM ggv_bank_transactions
                WHERE entity_id=? AND recon_status='NEEDS_REVIEW' AND human_confirmed=0
                """,
                (ENTITY,),
            ).fetchone()[0]
        )
    rx_missing = 0
    if _table_exists(conn, "ggv_receipt_accounting"):
        rx_missing = int(
            conn.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND missing_evidence=1",
                (ENTITY,),
            ).fetchone()[0]
        )
    return {
        "bank_unmatched": bank_unmatched,
        "bank_propose_match": bank_proposed,
        "bank_human_review": bank_human_review,
        "receipt_missing_evidence": rx_missing,
        "auto_reconcile": False,
        "propose_only": True,
    }


def audit_tail(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    require_amg_finance(person_id, conn)
    lim = max(1, min(int(limit or 50), 200))
    sources = ("ggv_finance_nota", "ggv_bank_statement1", "ggv_receipt_accounting1")
    events: list[dict[str, Any]] = []
    for src in sources:
        try:
            rows = _audit.list_events(source=src, limit=lim, entity_id=ENTITY, conn=conn)
        except Exception:
            rows = []
        for row in rows:
            if str(row.get("entity_id") or "") != ENTITY:
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
    require_amg_finance(person_id, conn)
    counts = desk_counts(conn)
    recon = reconciliation_summary(conn)
    entities = _inv.finance_entities(person_id, conn)
    try:
        stamp = _books.desk_stamp(ENTITY)
    except Exception:
        stamp = {
            "books_enabled": True,
            "books_opened": True,
            "empty": False,
            "shell_kind": "live",
            "accounts": 0,
            "journals": 0,
            "db_file": "atrium.sqlite",
            "message": "Atrium books are unavailable to read right now.",
        }
    return {
        "ok": True,
        "title": str(_CFG.get("title") or "AMG Finance"),
        "entity_id": ENTITY,
        "operational": True,
        "completeness_only": False,
        "operational_sections": list(OPERATIONAL_SECTIONS),
        "counts": counts,
        "reconciliation": recon,
        "finance_entities": entities,
        "active_entity": {"id": "AMG", "label": "AMG / ATRIUM", "entity_id": ENTITY},
        "books_shell": stamp,
        "db_file": stamp.get("db_file"),
        "shell_kind": stamp.get("shell_kind"),
        "accounts": stamp.get("accounts"),
        "journals": stamp.get("journals"),
        "matt_test_urls": {
            "nota": "/amg/finance/notas",
            "bank_statement": "/amg/finance/banking",
            "reconciliation": "/amg/finance/reconciliation",
        },
        "historical": historical_notice(),
        **HONESTY,
    }


def reconciliation_board(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    tab: str = "possible",
    month: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    require_amg_finance(person_id, conn)
    from core import amg_bank_recon1 as _amg_recon
    from core import fc_recon_queues1 as _queue

    queue = _queue.list_queue(
        conn,
        entity=ENTITY,
        tab=tab,
        month=month,
        limit=limit,
        offset=offset,
    )
    summary = reconciliation_summary(conn)
    counts = _amg_recon.proposal_counts(conn)
    return {
        **queue,
        "summary": summary,
        "proposal_counts": counts,
        "message": "Propose-only matching. Confirm, reject, or mark exception — nothing auto-posts.",
        **HONESTY,
    }


def reconciliation_action(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    action: str,
    txn_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_amg_finance(person_id, conn)
    from core import fc_recon_queues1 as _queue

    body = body or {}
    act = (action or "").strip().lower()
    try:
        if act == "confirm":
            return _queue.confirm_match(conn, entity=ENTITY, txn_id=txn_id, person_id=person_id)
        if act == "reject":
            return _queue.reject_match(
                conn,
                entity=ENTITY,
                txn_id=txn_id,
                person_id=person_id,
                reason=str(body.get("reason") or ""),
            )
        if act == "exception":
            return _queue.mark_exception(
                conn,
                entity=ENTITY,
                txn_id=txn_id,
                person_id=person_id,
                note=str(body.get("note") or body.get("reason") or ""),
            )
        if act == "bulk_confirm":
            return _queue.bulk_confirm(
                conn,
                entity=ENTITY,
                person_id=person_id,
                txn_ids=list(body.get("txn_ids") or []),
                rule=str(body.get("rule") or ""),
            )
    except _queue.ReconQueueError as exc:
        raise AmgFinanceDeskError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    raise AmgFinanceDeskError("Unknown reconciliation action.", code="invalid", http_status=400)
