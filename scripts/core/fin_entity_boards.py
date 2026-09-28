#!/usr/bin/env python3
"""CAP-FIN-03 entity finance boards. One read across the stored entities.

Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the
queue test for Entity Finance Boards. The desks already exist. This
module does not open a book, type a balance, or seat a person.
POS-GGV-EXT-ACCT stays empty unless an assignment is already stored.
A content-management assignment is not that seat. CAP-FIN-03 stays BUILT.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import fin_accounting_core as books
from core.ggv_finance_nota import (
    ENTITY_GGV,
    POSITION_EXTERNAL_ACCOUNTANT,
    ROLE_EXTERNAL_ACCOUNTANT,
)

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CAP_ID = "CAP-FIN-03"
ENGINEERING_CR = "CR-671ef246d8d850b2"
CONTENT_ROLE = "ROLE-CONTENT-MGMT"
CLOSER_POSITION = "POS-BZG-CLOSER-UMA-1"
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

# Existing desks. Uma is a venue of ENT-BZG, not a fourth legal entity.
BOARDS: tuple[dict[str, str], ...] = (
    {
        "board_id": "GGV",
        "entity_id": ENTITY_GGV,
        "href": "/ggv/finance",
        "page": "dashboards/ggv-finance.html",
        "sentence": "Not paid from this screen",
        "kind": "notes",
    },
    {
        "board_id": "ATRIUM",
        "entity_id": "ENT-AMG",
        "href": "/amg-ops-pack",
        "page": "dashboards/amg-ops-pack.html",
        "sentence": "Hotel books are not open on this desk.",
        "kind": "closed_desk",
    },
    {
        "board_id": "UMA",
        "entity_id": "ENT-BZG",
        "href": "/bzg/uma-blu",
        "page": "dashboards/bzg-uma-blu.html",
        "sentence": "No stock count is on this screen. Stock stays in ESB.",
        "kind": "operations",
    },
)


class EntityBoardError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_balance(_body: dict | None = None) -> None:
    raise EntityBoardError(
        "A typed balance does not close this row. No amount is parsed.",
        code="balance_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise EntityBoardError(
        "A payment is not executed on this read. No amount is kept.",
        code="payment_refused",
    )


def refuse_open(_body: dict | None = None) -> None:
    raise EntityBoardError(
        "Opening the books is an owner act. This read does not open them.",
        code="books_open_refused",
    )


def refuse_seat(_body: dict | None = None) -> None:
    raise EntityBoardError(
        "An empty seat is not filled from this read. No person row is written.",
        code="seat_refused",
    )


def _typed_money(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return str(value).strip() != ""


def _present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return bool(value)
    return str(value).strip() != ""


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


def _count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int | None:
    try:
        return int(conn.execute(sql, params).fetchone()[0])
    except sqlite3.Error:
        return None


def _page(spec: dict[str, str]) -> dict[str, Any]:
    path = BETA_ROOT / spec["page"]
    if not path.is_file():
        return {"page_present": False, "sentence_present": False}
    text = path.read_text(encoding="utf-8")
    return {
        "page_present": True,
        "sentence_present": spec["sentence"] in text,
    }


def _active_on_position(conn: sqlite3.Connection, position_id: str) -> int | None:
    if not _table(conn, "org_assignments"):
        return None
    return _count(
        conn,
        """
        SELECT COUNT(*) FROM org_assignments
        WHERE position_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (position_id,),
    )


def _position(conn: sqlite3.Connection, position_id: str) -> dict[str, Any] | None:
    if not _table(conn, "org_positions"):
        return None
    row = conn.execute(
        """
        SELECT position_id, role_id, entity_id, status
        FROM org_positions WHERE position_id=?
        """,
        (position_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "position_id": str(row["position_id"] or ""),
        "role_id": str(row["role_id"] or ""),
        "entity_id": str(row["entity_id"] or ""),
        "status": str(row["status"] or ""),
    }


def _content_assignments(conn: sqlite3.Connection) -> list[dict[str, str]] | None:
    if not (_table(conn, "org_assignments") and _table(conn, "org_positions")):
        return None
    rows = conn.execute(
        """
        SELECT a.assignment_id, a.position_id, p.role_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
        ORDER BY a.assignment_id
        """,
        (CONTENT_ROLE,),
    ).fetchall()
    return [
        {
            "assignment_id": str(row["assignment_id"] or ""),
            "position_id": str(row["position_id"] or ""),
            "role_id": str(row["role_id"] or ""),
        }
        for row in rows
    ]


def _completion(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table(conn, "wolf_completion_items"):
        return {"cr_rows": None, "cr_open": None, "cr_resolved_count": None, "engineering_state": None}
    rows = conn.execute(
        """
        SELECT id, state, blocker_class
        FROM wolf_completion_items
        WHERE capability=?
        ORDER BY id
        """,
        (CAP_ID,),
    ).fetchall()
    listed = [
        {
            "id": str(row["id"] or ""),
            "state": str(row["state"] or ""),
            "blocker_class": str(row["blocker_class"] or ""),
        }
        for row in rows
    ]
    engineering = next((row for row in listed if row["id"] == ENGINEERING_CR), None)
    return {
        "cr_rows": listed,
        "cr_open": sum(1 for row in listed if row["state"] == "OPEN"),
        "cr_resolved_count": sum(1 for row in listed if row["state"] == "RESOLVED"),
        "engineering_state": None if engineering is None else engineering["state"],
    }


def _board_row(
    spec: dict[str, str],
    stored: set[str],
    conn: sqlite3.Connection | None,
    core: dict[str, Any],
) -> dict[str, Any]:
    page = _page(spec)
    present = spec["entity_id"] in stored
    row: dict[str, Any] = {
        "board_id": spec["board_id"],
        "entity_id": spec["entity_id"],
        "href": spec["href"],
        "kind": spec["kind"],
        "entity_stored": present,
        "page_present": page["page_present"],
        "sentence_present": page["sentence_present"],
        "books_source": "UNAVAILABLE" if present else None,
        "money": None,
        "cash_figure": None,
        "staff_ready": False,
        "human_commissioned": False,
    }
    if not present or conn is None:
        return row
    if spec["board_id"] == "GGV":
        notas = _count(conn, "SELECT COUNT(*) FROM ggv_notas") if _table(conn, "ggv_notas") else None
        vendors = _count(conn, "SELECT COUNT(*) FROM ggv_vendors") if _table(conn, "ggv_vendors") else None
        row["nota_rows"] = notas
        row["vendor_rows"] = vendors
        row["nota_rows_are_cash"] = False
    if spec["board_id"] == "ATRIUM":
        row["commissioned_books_present"] = core.get("commissioned_books_present") is True
        row["sample_opened"] = False
    if spec["board_id"] == "UMA":
        closer = _active_on_position(conn, CLOSER_POSITION)
        row["closer_position_id"] = CLOSER_POSITION
        row["closer_active_assignments"] = closer
        row["closer_seated_by_this_read"] = False
        row["bills_href"] = "/bzg/uma-blu/bills"
    return row


def read_entity_finance_boards(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    *,
    balance: Any = None,
    amount: Any = None,
    books_figure: Any = None,
    payment: Any = None,
    open_books: Any = None,
    seat: Any = None,
    person: Any = None,
    assign: Any = None,
) -> dict[str, Any]:
    """Read the three stored entity desks and the accountant seat.

    A typed balance, including zero, is refused. Asking this function to
    seat a person is refused. The content-management assignment is reported
    only so it can be told apart from the accountant position. No person
    row is written. A missing books source stays UNAVAILABLE.
    """
    if any(_present(item) for item in (seat, person, assign)):
        refuse_seat({})
    if _present(payment):
        refuse_payment({})
    if any(_typed_money(item) for item in (balance, amount, books_figure)):
        refuse_balance({})
    if _present(open_books):
        refuse_open({})

    catalog = Path(catalog_db) if catalog_db else CATALOG_DB
    ledger = Path(ledger_path) if ledger_path else LEDGER_JSON
    core = books.read_accounting_core(catalog, ledger, balance="")
    state = _ledger_state(ledger)
    conn = _ro(catalog)
    stored = {
        str(row.get("entity_id") or "")
        for row in (core.get("entities") or [])
        if row.get("entity_id")
    }
    completion = {"cr_rows": None, "cr_open": None, "cr_resolved_count": None, "engineering_state": None}
    seat_row = None
    occupants: int | None = None
    content: list[dict[str, str]] | None = None
    try:
        if conn is not None:
            completion = _completion(conn)
            seat_row = _position(conn, POSITION_EXTERNAL_ACCOUNTANT)
            occupants = _active_on_position(conn, POSITION_EXTERNAL_ACCOUNTANT)
            content = _content_assignments(conn)
            boards = [_board_row(spec, stored, conn, core) for spec in BOARDS]
        else:
            boards = [_board_row(spec, stored, None, core) for spec in BOARDS]
    finally:
        if conn is not None:
            conn.close()

    content_rows = content or []
    content_is_seat = any(row["position_id"] == POSITION_EXTERNAL_ACCOUNTANT for row in content_rows)
    content_is_role = any(row["role_id"] == ROLE_EXTERNAL_ACCOUNTANT for row in content_rows)
    covered = [row["entity_id"] for row in boards if row["entity_stored"]]
    return {
        "ok": True,
        "cap": CAP_ID,
        "ledger_state": state,
        "shared": True,
        "board_count": len(boards),
        "entities_covered": covered,
        "entities_missing": [spec["entity_id"] for spec in BOARDS if spec["entity_id"] not in stored],
        "boards": boards,
        "books_source": core.get("books_source"),
        "books_opened": False,
        "sample_opened": False,
        "green_test_opens_books": False,
        "green_test_seats_accountant": False,
        "typed_balance_closes_row": False,
        "amounts_parsed": False,
        "payment_executed": False,
        "person_created": False,
        "assignment_created": False,
        "accountant_position_id": POSITION_EXTERNAL_ACCOUNTANT,
        "accountant_role_id": ROLE_EXTERNAL_ACCOUNTANT,
        "accountant_entity_id": None if seat_row is None else seat_row["entity_id"],
        "accountant_position_stored": seat_row is not None,
        "accountant_active_assignments": occupants,
        "accountant_seat_empty": occupants == 0 and seat_row is not None,
        "content_role_id": CONTENT_ROLE,
        "content_assignments": content_rows,
        "content_assignment_is_accountant_seat": content_is_seat,
        "content_assignment_is_accountant_role": content_is_role,
        "finance_display": core.get("finance_display"),
        "commissioned_books_present": core.get("commissioned_books_present") is True,
        "cr_id": ENGINEERING_CR,
        "cr_rows": completion["cr_rows"],
        "cr_open": completion["cr_open"],
        "cr_resolved_count": completion["cr_resolved_count"],
        "engineering_state": completion["engineering_state"],
        "cr_resolved": False,
        "ledger_write": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "proven": False,
        "ready": False,
        "money": None,
    }
