#!/usr/bin/env python3
"""FINANCE-CORE-GGV-1 — GGV Finance operational desk (entity ENT-GGV).

Operational browse + reconciliation shell. Shared code ≠ shared data.
No payment execution, no auto-reconcile, no GL posting. staff_ready=false.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core import audit as _audit
from core import ggv_finance_nota as _nota
from core import rbac as _rbac

ENTITY = "ENT-GGV"
PACK = "FINANCE-CORE-GGV-1"

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
    return {
        "ok": True,
        "title": "GGV Finance",
        "entity_id": ENTITY,
        "operational": True,
        "completeness_only": False,
        "operational_sections": list(OPERATIONAL_SECTIONS),
        "counts": counts,
        "reconciliation": recon,
        "matt_test_urls": {
            "nota": "/ggv/finance/notas",
            "bank_statement": "/ggv/finance/banking",
            "reconciliation": "/ggv/finance/reconciliation",
        },
        **HONESTY,
    }


def reconciliation_board(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    require_ggv_finance(person_id, conn)
    from core import ggv_bank_statement1 as _gbs

    imports = _gbs.list_imports(verified_person_id=person_id, conn=conn)
    txns = _gbs.list_transactions(verified_person_id=person_id, limit=100, conn=conn)
    summary = reconciliation_summary(conn)
    return {
        "ok": True,
        "entity_id": ENTITY,
        "summary": summary,
        "imports": imports.get("imports") or [],
        "transactions": txns.get("transactions") or [],
        "propose_only": True,
        "auto_reconcile": False,
        "message": "Propose-only matching. No auto-post. No Reconcile button.",
        **HONESTY,
    }
