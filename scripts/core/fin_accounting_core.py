#!/usr/bin/env python3
"""CAP-FIN-01 accounting-core read. Not a second ledger.

Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the
queue test for Wolf Accounting Core. Official books stay in the existing
Atrium app. This module does not open that file, does not type a balance,
and does not write a journal. A green read does not open the books.
CAP-FIN-01 stays BUILT.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
ATRIUM_ROOT = Path("/Users/wolfterminal/atrium-finance")
COMMISSIONED_BOOKS = ATRIUM_ROOT / "data" / "atrium.sqlite"
SAMPLE_BOOKS = ATRIUM_ROOT / "data" / "uncommissioned" / "atrium.sqlite"

CAP_ID = "CAP-FIN-01"
CR_ID = "CR-fd6bf6778c5874ab"
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})


class AccountingCoreError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_balance(_body: dict | None = None) -> None:
    raise AccountingCoreError(
        "A typed balance does not close this row. No amount is parsed into the books.",
        code="balance_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise AccountingCoreError(
        "A payment is not executed on this read. No amount is kept.",
        code="payment_refused",
    )


def refuse_open(_body: dict | None = None) -> None:
    raise AccountingCoreError(
        "Opening the books is an owner act. This read does not open them.",
        code="books_open_refused",
    )


def _typed_money(value: Any) -> bool:
    """A supplied number, including zero. An empty string is not a balance."""
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return str(value).strip() != ""


def _present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return bool(value)
    return str(value).strip() != ""


def _ledger_state(ledger_path: Path) -> str:
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    return state if state in MATURITY else "UNKNOWN"


def _ro(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None
    conn.row_factory = sqlite3.Row
    return conn


def _table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _finance_display() -> dict[str, Any]:
    from core import dashboard_truth as truth

    try:
        stamp = truth.stamp("empire")
    except Exception:  # noqa: BLE001 — a failed probe is unavailable, not a balance
        return {
            "display_state": "UNAVAILABLE",
            "presence": "UNKNOWN",
            "commissioned": False,
            "shown_as_current": False,
            "probe": "UNREAD",
        }
    for source in stamp.get("sources") or []:
        if source.get("source_id") == "finance_ledgers":
            return {
                "display_state": str(source.get("display_state") or "UNKNOWN"),
                "presence": str(source.get("presence") or "UNKNOWN"),
                "commissioned": source.get("commissioned") is True,
                "shown_as_current": source.get("shown_as_current") is True,
                "probe": "READ",
            }
    return {
        "display_state": "MISSING",
        "presence": "UNKNOWN",
        "commissioned": False,
        "shown_as_current": False,
        "probe": "READ",
    }


def _entities(conn: sqlite3.Connection) -> list[dict[str, Any]] | None:
    if not _table(conn, "org_entities"):
        return None
    rows = conn.execute(
        """
        SELECT entity_id, entity_type, status
        FROM org_entities
        ORDER BY entity_id
        """
    ).fetchall()
    out = []
    for row in rows:
        out.append(
            {
                "entity_id": str(row["entity_id"] or ""),
                "entity_type": str(row["entity_type"] or ""),
                "status": str(row["status"] or ""),
                "books_source": "UNAVAILABLE",
                "consolidation_figure": None,
            }
        )
    return out


def _completion(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table(conn, "wolf_completion_items"):
        return {"cr_present": False, "cr_state": None, "cr_id": None}
    row = conn.execute(
        """
        SELECT id, state
        FROM wolf_completion_items
        WHERE capability = ?
        ORDER BY id
        LIMIT 1
        """,
        (CAP_ID,),
    ).fetchone()
    if row is None:
        return {"cr_present": False, "cr_state": None, "cr_id": None}
    return {
        "cr_present": True,
        "cr_state": str(row["state"] or ""),
        "cr_id": str(row["id"] or ""),
    }


def _mapping_stored(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table'
          AND (
            name LIKE '%book%'
            OR name LIKE '%journal%'
            OR name LIKE '%consolidat%'
          )
        """
    ).fetchone()
    return row is not None


def read_accounting_core(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    *,
    balance: Any = None,
    amount: Any = None,
    books: Any = None,
    opening: Any = None,
    closing: Any = None,
    payment: Any = None,
    open_books: Any = None,
) -> dict[str, Any]:
    """Read the stored entity list and the finance display. Open no book.

    A typed balance, including zero, is refused. Asking this function to
    open the books is refused. The uncommissioned sample file is not opened.
    A missing books source stays UNAVAILABLE. That word is not cash.
    """
    if _present(payment):
        refuse_payment({})
    if any(_typed_money(item) for item in (balance, amount, books, opening, closing)):
        refuse_balance({})
    if _present(open_books):
        refuse_open({})

    catalog = Path(catalog_db) if catalog_db else CATALOG_DB
    ledger = Path(ledger_path) if ledger_path else LEDGER_JSON
    # Stat only. sqlite3.connect is not called on either Atrium path.
    commissioned_present = COMMISSIONED_BOOKS.is_file()
    sample_present = SAMPLE_BOOKS.is_file()
    finance = _finance_display()
    state = _ledger_state(ledger)
    conn = _ro(catalog)
    entities: list[dict[str, Any]] | None = None
    completion = {"cr_present": False, "cr_state": None, "cr_id": None}
    mapping = False
    catalog_read = False
    if conn is not None:
        try:
            entities = _entities(conn)
            completion = _completion(conn)
            mapping = _mapping_stored(conn)
            catalog_read = entities is not None
        except sqlite3.Error:
            entities = None
            catalog_read = False
        finally:
            conn.close()

    return {
        "ok": True,
        "cap": CAP_ID,
        "ledger_state": state,
        "catalog_read": catalog_read,
        "entity_count": None if entities is None else len(entities),
        "entities": entities,
        "books_source": "UNAVAILABLE",
        "finance_display": finance["display_state"],
        "finance_presence": finance["presence"],
        "finance_probe": finance["probe"],
        "finance_shown_as_current": finance["shown_as_current"],
        "finance_commissioned": finance["commissioned"],
        "commissioned_books_present": commissioned_present,
        "sample_present": sample_present,
        "sample_opened": False,
        "books_opened": False,
        "green_test_opens_books": False,
        "typed_balance_closes_row": False,
        "amounts_parsed": False,
        "journals_read": False,
        "journal_count": None,
        "consolidation_figure": None,
        "mapping_stored": mapping,
        "mapping_rows": None,
        "balance": None,
        "payment_executed": False,
        "books_written": False,
        "ledger_write": False,
        "cr_id": completion["cr_id"],
        "cr_present": completion["cr_present"],
        "cr_state": completion["cr_state"],
        "cr_resolved": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "proven": False,
        "ready": False,
    }
