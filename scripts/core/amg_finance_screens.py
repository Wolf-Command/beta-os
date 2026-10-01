#!/usr/bin/env python3
"""Pack 5 — Atrium finance screens. Read the Beta books. Do not post.

Night audit, flash, cash, close, and the owner pack are reads. Manual revenue
rows stay manual. No bank balance is invented. Xero write and payroll
distribution stay off. A screen review can be approved only by a different
person who can read ENT-AMG. staff_ready stays false.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
BOOKS = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
SOD_JOURNAL = "JRN-ATRIUMSOD1B-COMM1"
SELF_JOURNAL = "JRN-ATRIUMSOD1B-SELF"
PRODUCER = "PERS-ZENITALFATHAN"
APPROVER = "PERS-ZAYEN"
AMANDA = "PERS-AMANDA"

SCREENS = ("night-audit", "flash", "cash", "close", "owner")


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _ro(path: Path | None = None) -> sqlite3.Connection:
    src = path or BOOKS
    conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def _books_facts(path: Path | None = None) -> dict[str, Any]:
    src = path or BOOKS
    if not src.is_file():
        return {"ok": False, "error": "books_missing", "path": str(src)}
    conn = _ro(src)
    try:
        meta = conn.execute("SELECT * FROM books_slot_meta").fetchone()
        journals = [dict(r) for r in conn.execute(
            "SELECT journal_id, status, source_type, preparer_person_id, approved_by, posted_by, legal_entity_id "
            "FROM journal_headers"
        )]
        revenue = [dict(r) for r in conn.execute(
            "SELECT transaction_id, date, source, department_code, account_code, amount, journal_id, legal_entity_id "
            "FROM revenue_transactions"
        )]
        spending = [dict(r) for r in conn.execute(
            "SELECT transaction_id, date, type, vendor_or_employee, amount, journal_id, legal_entity_id "
            "FROM spending_transactions"
        )]
        hist = [dict(r) for r in conn.execute(
            "SELECT batch_id, source_file, period, row_count, status, note, legal_entity_id "
            "FROM historical_import_batches"
        )]
        accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        tax_closed = conn.execute("SELECT COUNT(*) FROM tax_closed_periods").fetchone()[0]
        ap = conn.execute("SELECT COUNT(*) FROM ap_payments").fetchone()[0]
        payroll_cycles = conn.execute("SELECT COUNT(*) FROM service_charge_cycles").fetchone()[0]
        report = conn.execute("SELECT config_id, legal_entity_id FROM report_config").fetchone()
        owner_units = conn.execute("SELECT COUNT(*) FROM owner_pool_units").fetchone()[0]
        owner_drafts = conn.execute("SELECT COUNT(*) FROM owner_email_drafts").fetchone()[0]
    finally:
        conn.close()
    return {
        "ok": True,
        "path": str(src),
        "meta": dict(meta) if meta else None,
        "journals": journals,
        "revenue": revenue,
        "spending": spending,
        "historical": hist,
        "accounts": accounts,
        "tax_closed_periods": tax_closed,
        "ap_payments": ap,
        "payroll_cycles": payroll_cycles,
        "report_config_id": report["config_id"] if report else None,
        "report_entity": report["legal_entity_id"] if report else None,
        "owner_pool_units": owner_units,
        "owner_email_drafts": owner_drafts,
    }


def _screen(screen_id: str, state: str, value: Any, why: str, **extra: Any) -> dict[str, Any]:
    row = {
        "id": screen_id,
        "state": state,
        "value": value,
        "why": why,
        "read": True,
        "xero_write": False,
        "bank_balance": None,
        "staff_ready": False,
    }
    row.update(extra)
    return row


def _night_audit(facts: dict[str, Any]) -> dict[str, Any]:
    rows = facts.get("revenue") or []
    if not facts.get("ok"):
        return _screen("night-audit", "UNKNOWN", None, "Books file could not be read. No night-audit figure was invented.")
    manual = sum(1 for row in rows if str(row.get("source") or "").lower() == "manual")
    return _screen(
        "night-audit",
        "PARTIAL",
        f"{len(rows)} revenue rows, {manual} source Manual",
        "These rows are stored revenue_transactions. Source is Manual, not a PMS night audit. Rooms sold was not derived.",
        lines=[
            {
                "transaction_id": row.get("transaction_id"),
                "date": row.get("date"),
                "source": row.get("source"),
                "amount": row.get("amount"),
                "journal_id": row.get("journal_id"),
                "legal_entity_id": row.get("legal_entity_id"),
            }
            for row in rows
        ],
        pms_night_audit=False,
    )


def _flash(facts: dict[str, Any]) -> dict[str, Any]:
    rows = facts.get("revenue") or []
    return _screen(
        "flash",
        "PARTIAL" if facts.get("ok") else "UNKNOWN",
        None if not facts.get("ok") else f"{len(rows)} manual revenue rows on file",
        "No GM morning flash was generated. The revenue rows are not summed into an ADR or a rooms flash.",
        generated_flash=False,
        adr=None,
        rooms_sold=None,
    )


def _cash(facts: dict[str, Any]) -> dict[str, Any]:
    spends = facts.get("spending") or []
    return _screen(
        "cash",
        "UNKNOWN",
        None,
        "No uploaded bank statement is in this pack. The spending row is a books line, not a statement match. Bank balance stays empty. There is no bank feed.",
        statement_uploaded=False,
        match=None,
        bank_feed=False,
        books_spend_count=len(spends),
        books_spend=[
            {
                "transaction_id": row.get("transaction_id"),
                "date": row.get("date"),
                "type": row.get("type"),
                "amount": row.get("amount"),
                "journal_id": row.get("journal_id"),
                "legal_entity_id": row.get("legal_entity_id"),
            }
            for row in spends
        ],
    )


def _close(facts: dict[str, Any]) -> dict[str, Any]:
    journals = facts.get("journals") or []
    counts: dict[str, int] = {}
    for row in journals:
        key = str(row.get("status") or "")
        counts[key] = counts.get(key, 0) + 1
    hist = (facts.get("historical") or [{}])[0]
    return _screen(
        "close",
        "PARTIAL",
        f"journals {len(journals)} · tax periods closed {facts.get('tax_closed_periods')}",
        "Checklist of what the books file contains. A zero closed-period count is not a finished month.",
        checklist=[
            {"item": "books_file", "state": "READ" if facts.get("ok") else "UNKNOWN"},
            {"item": "xero_write", "state": "BLOCKED"},
            {"item": "payroll_distribution", "state": "BLOCKED", "cycles": facts.get("payroll_cycles")},
            {"item": "tax_periods_closed", "count": facts.get("tax_closed_periods")},
            {"item": "historical_import", "status": hist.get("status"), "row_count": hist.get("row_count")},
            {"item": "ap_payments", "count": facts.get("ap_payments")},
        ],
        journal_status_counts=counts,
        month_closed=False,
    )


def _owner(facts: dict[str, Any]) -> dict[str, Any]:
    return _screen(
        "owner",
        "PARTIAL",
        f"report config {facts.get('report_config_id')} · owner drafts {facts.get('owner_email_drafts')}",
        "A report config row is on file. No owner pack was exported. The config JSON was not rendered as a statement.",
        exported=False,
        owner_pool_units=facts.get("owner_pool_units"),
        owner_email_drafts=facts.get("owner_email_drafts"),
    )


def _sod_read(facts: dict[str, Any]) -> dict[str, Any]:
    journals = {row.get("journal_id"): row for row in facts.get("journals") or []}
    posted = journals.get(SOD_JOURNAL)
    self_row = journals.get(SELF_JOURNAL)
    segregated = bool(
        posted
        and posted.get("status") == "POSTED"
        and posted.get("preparer_person_id")
        and posted.get("preparer_person_id") != "PERS-ZAYEN"
        and posted.get("approved_by")
    )
    return {
        "segregated_journal": SOD_JOURNAL if segregated else None,
        "segregated": segregated,
        "preparer_person_id": (posted or {}).get("preparer_person_id"),
        "approved_by": (posted or {}).get("approved_by"),
        "self_journal": SELF_JOURNAL if self_row else None,
        "self_journal_status": (self_row or {}).get("status"),
        "self_journal_approved_by": (self_row or {}).get("approved_by") or None,
        "xero_write": False,
    }


def seat_matrix(person_id: str) -> dict[str, bool]:
    """Same permissions the entity-isolation repair already checks. Read only."""
    from core import rbac

    conn = rbac.db_connect()
    try:
        return {
            "ENT-AMG": bool(rbac.can(person_id, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=conn)),
            "ENT-BZG": bool(rbac.can(person_id, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=conn)),
            "ENT-GGV": bool(rbac.can(person_id, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=conn)),
        }
    finally:
        conn.close()


def load_screens(path: Path | None = None) -> dict[str, Any]:
    facts = _books_facts(path)
    meta = facts.get("meta") or {}
    screens = [
        _night_audit(facts),
        _flash(facts),
        _cash(facts),
        _close(facts),
        _owner(facts),
    ]
    return {
        "ok": bool(facts.get("ok")),
        "pack": "PACK-05",
        "staff_ready": False,
        "human_proven": False,
        "read_only_books": True,
        "xero_write": False,
        "payroll": "OFF",
        "bank_feed": False,
        "bank_balance": None,
        "as_of_wita": _now(),
        "books": {
            "path": facts.get("path"),
            "legal_entity_id": meta.get("legal_entity_id"),
            "shell_kind": meta.get("shell_kind"),
            "books_enabled": meta.get("books_enabled"),
            "accounts": facts.get("accounts"),
            "staff_ready_flag": meta.get("staff_ready"),
        },
        "screens": screens,
        "withheld": [
            {"id": "payroll", "state": "BLOCKED", "why": "Payroll distribution is the HR boundary. Cycles were counted and not opened."},
            {"id": "xero", "state": "BLOCKED", "why": "No Xero write from this pack."},
        ],
        "sod": _sod_read(facts),
        "writes": {
            "books": False,
            "xero": False,
            "payroll": False,
            "bank": False,
        },
    }


def connect_reviews(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS screen_reviews (
          id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          screen TEXT NOT NULL,
          producer_id TEXT NOT NULL,
          status TEXT NOT NULL,
          approver_id TEXT,
          xero_write INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        )
        """
    )
    return conn


def submit_review(producer_id: str, screen: str, db: Path, entity_id: str = "ENT-AMG") -> dict[str, Any]:
    if screen not in SCREENS:
        return {"ok": False, "error": "unknown_screen", "staff_ready": False, "xero_write": False}
    seats = seat_matrix(producer_id)
    if entity_id == "ENT-GGV" or not seats.get(entity_id):
        return {
            "ok": False,
            "error": "entity_denied",
            "entity_id": entity_id,
            "seats": seats,
            "staff_ready": False,
            "xero_write": False,
        }
    review_id = "FSR-" + uuid.uuid4().hex[:12].upper()
    conn = connect_reviews(db)
    try:
        conn.execute(
            """
            INSERT INTO screen_reviews (
              id, entity_id, screen, producer_id, status, approver_id, xero_write, created_at
            ) VALUES (?, ?, ?, ?, 'PENDING', NULL, 0, ?)
            """,
            (review_id, entity_id, screen, producer_id, _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "id": review_id,
        "status": "PENDING",
        "producer_id": producer_id,
        "entity_id": entity_id,
        "xero_write": False,
        "amount": None,
        "staff_ready": False,
    }


def approve_review(actor_id: str, review_id: str, db: Path) -> dict[str, Any]:
    conn = connect_reviews(db)
    try:
        row = conn.execute("SELECT * FROM screen_reviews WHERE id=?", (review_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": "not_found", "xero_write": False, "staff_ready": False}
        if str(row["producer_id"]) == actor_id:
            return {
                "ok": False,
                "error": "self_approval_denied",
                "id": review_id,
                "xero_write": False,
                "posted": False,
                "staff_ready": False,
            }
        seats = seat_matrix(actor_id)
        if not seats.get(str(row["entity_id"])):
            return {
                "ok": False,
                "error": "entity_denied",
                "id": review_id,
                "entity_id": row["entity_id"],
                "xero_write": False,
                "staff_ready": False,
            }
        conn.execute(
            "UPDATE screen_reviews SET status='APPROVED', approver_id=?, xero_write=0 WHERE id=?",
            (actor_id, review_id),
        )
        conn.commit()
        saved = dict(conn.execute("SELECT * FROM screen_reviews WHERE id=?", (review_id,)).fetchone())
    finally:
        conn.close()
    return {
        "ok": True,
        "id": review_id,
        "status": saved["status"],
        "producer_id": saved["producer_id"],
        "approver_id": saved["approver_id"],
        "xero_write": False,
        "posted": False,
        "amount": None,
        "staff_ready": False,
    }


def refuse_xero() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "xero_write_blocked",
        "pack": "PACK-05",
        "xero_write": False,
        "posted": False,
        "staff_ready": False,
        "human_proven": False,
    }


def refuse_payroll() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "payroll_blocked",
        "pack": "PACK-05",
        "payroll": "OFF",
        "staff_ready": False,
    }
