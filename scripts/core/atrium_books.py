#!/usr/bin/env python3
"""Atrium books for the Beta finance desk. Chart structure and draft journals.

Decision served: owner brief 28 Sep 2026 11:28 WITA (staff access), extended
on the existing Atrium Finance desk by ATRIUMFIN-UX-2. Storage is Beta-local.
The chart is the Atrium chart from the production book (entity ATRIUM only).
No production journal, balance, bank row, or payment is copied. Drafts are
not posted. Approve and post are not implemented here.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Makassar")
ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = Path(__file__).resolve().parent / "data" / "atrium_coa_seed.json"
DEFAULT_DB = ROOT / "state" / "atrium-books" / "amg.sqlite"
ENTITY = "ENT-AMG"
CURRENCY = "IDR"

LEDGER_EMPTY = (
    "The general ledger has no posted lines. "
    "Save a balanced draft under Journals. "
    "It reaches this ledger only after the Finance Controller posts it."
)
REPORT_EMPTY = (
    "No period has been posted, so these statements have no figures. "
    "A draft journal stays off the statements until the Finance Controller posts it."
)
JOURNAL_EMPTY = (
    "No draft journal is on file. "
    "Enter a balanced entry and save it. "
    "It stays a draft until the Finance Controller posts it."
)

_LOCK = threading.Lock()


class BooksError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_path() -> Path:
    override = os.environ.get("ATRIUM_BOOKS_DB", "").strip()
    if override:
        return Path(override)
    return DEFAULT_DB


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS coa_account (
            account_code TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            account_class TEXT NOT NULL,
            normal_balance TEXT NOT NULL,
            is_control INTEGER NOT NULL DEFAULT 0,
            is_statistical INTEGER NOT NULL DEFAULT 0,
            is_postable INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            usali_line TEXT,
            statutory_line TEXT
        );
        CREATE TABLE IF NOT EXISTS report_definition (
            report_code TEXT PRIMARY KEY,
            report_name TEXT NOT NULL,
            family TEXT NOT NULL,
            statement TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS journal_draft (
            journal_id TEXT PRIMARY KEY,
            memo TEXT NOT NULL,
            journal_date TEXT NOT NULL,
            period_code TEXT NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS journal_line (
            line_id INTEGER PRIMARY KEY,
            journal_id TEXT NOT NULL,
            line_no INTEGER NOT NULL,
            account_code TEXT NOT NULL,
            description TEXT,
            debit_idr INTEGER NOT NULL,
            credit_idr INTEGER NOT NULL,
            FOREIGN KEY (journal_id) REFERENCES journal_draft(journal_id)
        );
        """
    )


def _seed(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM coa_account").fetchone()[0]
    if count:
        return
    if not SEED_PATH.is_file():
        raise BooksError("The Atrium chart file is missing.", code="chart_missing", http_status=500)
    blob = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    accounts = blob.get("accounts") or []
    if not accounts:
        raise BooksError("The Atrium chart file has no accounts.", code="chart_missing", http_status=500)
    for row in accounts:
        code = str(row.get("account_code") or "").strip()
        name = str(row.get("account_name") or "").strip()
        if not code or not name:
            continue
        conn.execute(
            """
            INSERT INTO coa_account(
                account_code, account_name, account_class, normal_balance,
                is_control, is_statistical, is_postable, is_active,
                usali_line, statutory_line
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                name,
                str(row.get("account_class") or "").strip(),
                str(row.get("normal_balance") or "").strip(),
                int(row.get("is_control") or 0),
                int(row.get("is_statistical") or 0),
                int(row.get("is_postable") or 0),
                int(row.get("is_active") or 0),
                row.get("usali_line") or None,
                row.get("statutory_line") or None,
            ),
        )
    for row in blob.get("reports") or []:
        code = str(row.get("report_code") or "").strip()
        name = str(row.get("report_name") or "").strip()
        if not code or not name:
            continue
        if str(row.get("entity_scope") or "AMG").strip().upper() not in {"AMG", "ATRIUM"}:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO report_definition(
                report_code, report_name, family, statement, sort_order, is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                name,
                str(row.get("family") or "").strip(),
                str(row.get("statement") or "").strip(),
                int(row.get("sort_order") or 0),
                int(row.get("is_active") or 0),
            ),
        )


def ensure() -> None:
    with _LOCK:
        conn = _connect()
        try:
            _schema(conn)
            _seed(conn)
            conn.commit()
        finally:
            conn.close()


def summary() -> dict[str, Any]:
    ensure()
    conn = _connect()
    try:
        chart = int(conn.execute("SELECT COUNT(*) FROM coa_account WHERE is_active=1").fetchone()[0])
        drafts = int(conn.execute("SELECT COUNT(*) FROM journal_draft WHERE status='DRAFT'").fetchone()[0])
    finally:
        conn.close()
    return {
        "chart_count": chart,
        "draft_count": drafts,
        "posted": False,
    }


def list_accounts() -> dict[str, Any]:
    ensure()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT account_code, account_name, account_class, normal_balance,
                   is_control, is_statistical, is_postable, is_active,
                   usali_line, statutory_line
            FROM coa_account
            ORDER BY account_code
            """
        ).fetchall()
    finally:
        conn.close()
    accounts = []
    for row in rows:
        accounts.append(
            {
                "account_code": row["account_code"],
                "account_name": row["account_name"],
                "account_class": row["account_class"],
                "normal_balance": row["normal_balance"],
                "is_control": int(row["is_control"] or 0),
                "is_statistical": int(row["is_statistical"] or 0),
                "is_postable": int(row["is_postable"] or 0),
                "is_active": int(row["is_active"] or 0),
                "usali_line": row["usali_line"],
                "statutory_line": row["statutory_line"],
            }
        )
    return {
        "accounts": accounts,
        "count": len(accounts),
        "currency_note": "Account names only. No balance is stored on the chart.",
    }


def list_reports() -> dict[str, Any]:
    ensure()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT report_code, report_name, family, statement, sort_order
            FROM report_definition
            WHERE is_active=1
            ORDER BY sort_order, report_code
            """
        ).fetchall()
    finally:
        conn.close()
    reports = [
        {
            "report_code": row["report_code"],
            "report_name": row["report_name"],
            "family": row["family"],
            "statement": row["statement"],
            "figure": None,
            "lines": None,
        }
        for row in rows
    ]
    return {
        "reports": reports,
        "count": len(reports),
        "figure": None,
        "message": REPORT_EMPTY,
    }


def ledger() -> dict[str, Any]:
    """Posted general ledger. Drafts are not lines on this ledger."""
    return {
        "lines": [],
        "figure": None,
        "posted": False,
        "message": LEDGER_EMPTY,
    }


def _rupiah(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or value is None:
        raise BooksError(f"Enter the {label} as a whole rupiah amount.")
    text = str(value).strip().replace(",", "")
    if text == "":
        return 0
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise BooksError(f"Enter the {label} as a whole rupiah amount.") from exc
    if amount != amount.to_integral_value():
        raise BooksError(f"Enter the {label} as a whole rupiah amount.")
    if amount < 0:
        raise BooksError("An amount on a draft cannot be negative.")
    if amount > Decimal("1000000000000000"):
        raise BooksError("That amount is too large for a draft.")
    return int(amount)


def _clean_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise BooksError("Use the journal date as YYYY-MM-DD.")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise BooksError("Use the journal date as YYYY-MM-DD.") from exc
    return text


def _refused(payload: dict[str, Any]) -> None:
    blocked = {
        "approve",
        "post",
        "payment",
        "pay",
        "bank",
        "account_number",
        "iban",
        "material_amount",
    }
    found = [key for key in payload if str(key).lower() in blocked]
    if found:
        raise BooksError(
            "A draft does not approve, post, pay, or change a bank account.",
            code="forbidden",
            http_status=403,
        )
    entity = str(payload.get("entity") or payload.get("owning_entity_id") or ENTITY).strip()
    if entity not in {ENTITY, "AMG", "ATRIUM"}:
        raise BooksError("This draft is for Atrium only.", code="forbidden", http_status=403)
    currency = str(payload.get("currency") or CURRENCY).strip().upper()
    if currency != CURRENCY:
        raise BooksError("Atrium drafts are in rupiah.", code="forbidden", http_status=403)
    status = str(payload.get("status") or "DRAFT").strip().upper()
    if status != "DRAFT":
        raise BooksError(
            "This desk saves a draft. It does not approve or post.",
            code="forbidden",
            http_status=403,
        )


def _lines(conn: sqlite3.Connection, payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("lines")
    if not isinstance(raw, list) or len(raw) < 2:
        raise BooksError("A draft needs at least two lines.")
    if len(raw) > 40:
        raise BooksError("Keep a draft to forty lines.")
    cleaned: list[dict[str, Any]] = []
    debit_total = 0
    credit_total = 0
    for index, line in enumerate(raw, start=1):
        if not isinstance(line, dict):
            raise BooksError("Each line needs an account.")
        code = str(line.get("account_code") or "").strip()
        row = conn.execute(
            """
            SELECT account_code, is_active, is_postable
            FROM coa_account WHERE account_code=?
            """,
            (code,),
        ).fetchone()
        if row is None or int(row["is_active"] or 0) != 1:
            raise BooksError("Each line needs an account from the Atrium chart.")
        if int(row["is_postable"] or 0) != 1:
            raise BooksError(f"{code} is a heading. Choose an account that takes a posting.")
        debit = _rupiah(line.get("debit", line.get("debit_idr", 0)), label="debit")
        credit = _rupiah(line.get("credit", line.get("credit_idr", 0)), label="credit")
        if debit and credit:
            raise BooksError("Enter the debit or the credit on each line, not both.")
        if not debit and not credit:
            raise BooksError("Each line needs a debit or a credit.")
        description = str(line.get("description") or "").strip()
        if len(description) > 180:
            raise BooksError("Shorten the line description.")
        debit_total += debit
        credit_total += credit
        cleaned.append(
            {
                "line_no": index,
                "account_code": code,
                "description": description or None,
                "debit_idr": debit,
                "credit_idr": credit,
            }
        )
    if debit_total != credit_total:
        raise BooksError("The debits and credits do not match. A draft must balance before it is saved.")
    if debit_total <= 0:
        raise BooksError("A draft needs an amount on the lines.")
    return cleaned


def _public(conn: sqlite3.Connection, journal_id: str) -> dict[str, Any]:
    header = conn.execute(
        """
        SELECT journal_id, memo, journal_date, period_code, currency, status,
               created_by, created_at, updated_at
        FROM journal_draft WHERE journal_id=?
        """,
        (journal_id,),
    ).fetchone()
    if header is None:
        raise BooksError("That draft is not on file.", code="not_found", http_status=404)
    lines = conn.execute(
        """
        SELECT line_no, account_code, description, debit_idr, credit_idr
        FROM journal_line WHERE journal_id=? ORDER BY line_no
        """,
        (journal_id,),
    ).fetchall()
    return {
        "journal_id": header["journal_id"],
        "memo": header["memo"],
        "journal_date": header["journal_date"],
        "period_code": header["period_code"],
        "currency": header["currency"],
        "status": header["status"],
        "created_by": header["created_by"],
        "created_at": header["created_at"],
        "updated_at": header["updated_at"],
        "posted": False,
        "lines": [
            {
                "line_no": int(line["line_no"]),
                "account_code": line["account_code"],
                "description": line["description"],
                "debit_idr": int(line["debit_idr"]),
                "credit_idr": int(line["credit_idr"]),
            }
            for line in lines
        ],
    }


def list_drafts(person_id: str) -> dict[str, Any]:
    ensure()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT journal_id, memo, journal_date, status, updated_at
            FROM journal_draft
            WHERE created_by=? AND status='DRAFT'
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            (person_id,),
        ).fetchall()
    finally:
        conn.close()
    items = [
        {
            "journal_id": row["journal_id"],
            "memo": row["memo"],
            "journal_date": row["journal_date"],
            "status": row["status"],
            "updated_at": row["updated_at"],
            "posted": False,
        }
        for row in rows
    ]
    return {
        "journals": items,
        "count": len(items),
        "message": None if items else JOURNAL_EMPTY,
    }


def get_draft(person_id: str, journal_id: str) -> dict[str, Any]:
    ensure()
    conn = _connect()
    try:
        item = _public(conn, journal_id)
    finally:
        conn.close()
    if item["created_by"] != person_id:
        raise BooksError("That draft is not on this assignment.", code="forbidden", http_status=403)
    return item


def save_draft(person_id: str, payload: dict[str, Any] | None, journal_id: str | None = None) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    _refused(body)
    memo = str(body.get("memo") or body.get("description") or "").strip()
    if not memo:
        raise BooksError("Add a memo so the draft can be recognised.")
    if len(memo) > 180:
        raise BooksError("Keep the memo to one short line.")
    journal_date = _clean_date(body.get("journal_date") or body.get("date"))
    period = journal_date[:7]
    ensure()
    with _LOCK:
        conn = _connect()
        try:
            lines = _lines(conn, body)
            now = _now()
            if journal_id:
                current = conn.execute(
                    "SELECT created_by, status FROM journal_draft WHERE journal_id=?",
                    (journal_id,),
                ).fetchone()
                if current is None:
                    raise BooksError("That draft is not on file.", code="not_found", http_status=404)
                if current["created_by"] != person_id or current["status"] != "DRAFT":
                    raise BooksError(
                        "That draft cannot be changed from this desk.",
                        code="forbidden",
                        http_status=403,
                    )
                conn.execute(
                    """
                    UPDATE journal_draft
                    SET memo=?, journal_date=?, period_code=?, updated_at=?
                    WHERE journal_id=?
                    """,
                    (memo, journal_date, period, now, journal_id),
                )
                conn.execute("DELETE FROM journal_line WHERE journal_id=?", (journal_id,))
            else:
                journal_id = "JRN-" + uuid.uuid4().hex[:12]
                conn.execute(
                    """
                    INSERT INTO journal_draft(
                        journal_id, memo, journal_date, period_code, currency, status,
                        created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?)
                    """,
                    (journal_id, memo, journal_date, period, CURRENCY, person_id, now, now),
                )
            conn.executemany(
                """
                INSERT INTO journal_line(
                    journal_id, line_no, account_code, description, debit_idr, credit_idr
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        journal_id,
                        line["line_no"],
                        line["account_code"],
                        line["description"],
                        line["debit_idr"],
                        line["credit_idr"],
                    )
                    for line in lines
                ],
            )
            item = _public(conn, journal_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return item


def validate_draft(person_id: str, payload: dict[str, Any] | None, journal_id: str | None = None) -> dict[str, Any]:
    """Check that a draft balances. Does not approve, post, or change status."""
    body = payload if isinstance(payload, dict) else {}
    if body:
        _refused(body)
    ensure()
    conn = _connect()
    try:
        if body.get("lines"):
            _lines(conn, body)
        elif journal_id:
            item = _public(conn, journal_id)
            if item["created_by"] != person_id:
                raise BooksError("That draft is not on this assignment.", code="forbidden", http_status=403)
            if item["status"] != "DRAFT":
                raise BooksError(
                    "This desk saves a draft. It does not approve or post.",
                    code="forbidden",
                    http_status=403,
                )
        else:
            raise BooksError("Add the lines to check, or choose a saved draft.")
    finally:
        conn.close()
    return {"status": "DRAFT", "balanced": True, "posted": False}


def refuse_decision(action: str) -> None:
    if action == "approve":
        raise BooksError(
            "Approving a journal is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    if action == "post":
        raise BooksError(
            "Posting a journal is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    raise BooksError("That action is not on this desk.", code="forbidden", http_status=403)
