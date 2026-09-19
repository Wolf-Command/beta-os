#!/usr/bin/env python3
"""Read-only Alchemist projection for Uma Blu (Beta).

Slice BF-uma-legacy-projection-20260919.

Alchemist stays in place. Nothing here inserts into bzg_ops_* or invents
an opening float. Paid in Alchemist is not a Wolf-verified payment.
cutover_at() stays None while state/uma/cutover.json keeps cutover_at null.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

BETA_ROOT = Path(__file__).resolve().parents[2]
CUTOVER_PATH = BETA_ROOT / "state" / "uma" / "cutover.json"
DEFAULT_DB = Path.home() / ".openclaw" / "workspace" / "alchemist" / "data" / "alchemist.db"

_STATUS = "INACCESSIBLE"
_MISS = object()

_ATTENTION_STATUSES = ("Awaiting Devi", "Received")

_PR_STATUS: dict[str, dict[str, Any]] = {
    "awaiting devi": {
        "state": "REQUESTED",
        "display_status": "Waiting approval",
        "needs_attention": True,
    },
    "received": {
        "state": "RECEIVED",
        "display_status": "Received",
        "needs_attention": True,
    },
    "paid": {
        "state": "CLOSED",
        "display_status": "Recorded as paid in Alchemist",
        "needs_attention": False,
        "payment_label": "Recorded as paid in Alchemist",
    },
    "cancelled": {
        "state": "CLOSED",
        "display_status": "Cancelled",
        "needs_attention": False,
    },
    "canceled": {
        "state": "CLOSED",
        "display_status": "Cancelled",
        "needs_attention": False,
    },
    "rejected": {
        "state": "REJECTED",
        "display_status": "Rejected",
        "needs_attention": False,
    },
}

_PR_COLS = (
    "id, pr_num, department, requested_by, vendor, order_date, status, "
    "notes, created_at, invoice_total"
)
_PETTY_COLS = (
    "id, entry_date, flow, category, description, amount, logged_by_name, created_at"
)


def source_status() -> str:
    return _STATUS


def cutover_at() -> str | None:
    """Return the cutover instant. This slice leaves it unset (None)."""
    try:
        data = json.loads(CUTOVER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get("cutover_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def resolve_db_path() -> Path | None:
    """WOLF_ALCHEMIST_DB, else the live Alchemist file.

    Unrelated Wolf tests (WOLF_TEST_MODE / scripts/tests) do not attach the
    live file unless WOLF_ALCHEMIST_DB is set. Beta serve does.
    """
    raw = (os.environ.get("WOLF_ALCHEMIST_DB") or "").strip()
    if raw:
        return Path(raw).expanduser()
    if _under_test_process():
        return None
    return DEFAULT_DB


def connect_readonly(path: Path) -> sqlite3.Connection:
    """Open SQLite mode=ro + query_only. Raises if the file is missing."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    uri = resolved.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def project_prs(limit: int = 100, attention_only: bool = False) -> list[dict[str, Any]]:
    """Normalised purchase requests. Attention statuses come first."""
    lim = _cap(limit)

    def run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        if attention_only:
            rows = _query(
                conn,
                f"""
                SELECT {_PR_COLS}
                FROM pr_orders
                WHERE status IN ('Awaiting Devi', 'Received')
                ORDER BY COALESCE(created_at, order_date) DESC
                LIMIT ?
                """,
                (lim,),
            )
            return [_map_pr(r) for r in rows]
        attention = _query(
            conn,
            f"""
            SELECT {_PR_COLS}
            FROM pr_orders
            WHERE status IN ('Awaiting Devi', 'Received')
            ORDER BY CASE status WHEN 'Awaiting Devi' THEN 0 ELSE 1 END,
                     COALESCE(created_at, order_date) DESC
            LIMIT ?
            """,
            (lim,),
        )
        rest = _query(
            conn,
            f"""
            SELECT {_PR_COLS}
            FROM pr_orders
            WHERE status IS NULL OR status NOT IN ('Awaiting Devi', 'Received')
            ORDER BY COALESCE(created_at, order_date) DESC
            LIMIT ?
            """,
            (lim,),
        )
        return [_map_pr(r) for r in list(attention) + list(rest)][:lim]

    out = _with_conn(run)
    return [] if out is _MISS else out


def project_petty_movements(limit: int = 100) -> list[dict[str, Any]]:
    """Petty movements. Never derives an opening float."""
    lim = _cap(limit)

    def run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        return _fetch_petty(conn, lim)

    out = _with_conn(run)
    return [] if out is _MISS else out


def project_history_events(limit: int = 40) -> list[dict[str, Any]]:
    """Human chronology. Sentences stay '{date} · … · Alchemist'."""
    lim = _cap(limit, hard=200)

    def run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in _query(
            conn,
            f"""
            SELECT {_PR_COLS}
            FROM pr_orders
            ORDER BY COALESCE(created_at, order_date) DESC
            LIMIT ?
            """,
            (lim,),
        ):
            events.append(_history_pr(row))
        for row in _query(
            conn,
            f"""
            SELECT {_PETTY_COLS}
            FROM petty_cash
            ORDER BY COALESCE(created_at, entry_date) DESC
            LIMIT ?
            """,
            (lim,),
        ):
            events.append(_history_petty(row))
        events.sort(key=lambda e: str(e.get("when") or ""), reverse=True)
        return events[:lim]

    out = _with_conn(run)
    return [] if out is _MISS else out


def project_attention_summary() -> dict[str, Any]:
    """Awaiting Devi, Received, recent petty, unpaid ledger. No float."""

    def run(conn: sqlite3.Connection) -> dict[str, Any]:
        counts = _query(
            conn,
            """
            SELECT
              SUM(CASE WHEN status = 'Awaiting Devi' THEN 1 ELSE 0 END),
              SUM(CASE WHEN status = 'Received' THEN 1 ELSE 0 END)
            FROM pr_orders
            """,
            (),
        )
        awaiting = int(counts[0][0] or 0) if counts else 0
        received = int(counts[0][1] or 0) if counts else 0
        unpaid = _query(
            conn,
            """
            SELECT COUNT(*), SUM(amount)
            FROM ledger
            WHERE lower(IFNULL(payment_status, '')) = 'unpaid'
              AND IFNULL(hold, 0) = 0
            """,
            (),
        )
        unpaid_count = int(unpaid[0][0] or 0) if unpaid else 0
        unpaid_sum = unpaid[0][1] if unpaid else None
        if unpaid_count == 0:
            unpaid_sum = None
        elif unpaid_sum is not None:
            unpaid_sum = float(unpaid_sum)
        return {
            "awaiting_devi_count": awaiting,
            "received_count": received,
            "recent_petty": _fetch_petty(conn, 5),
            "unpaid_ledger_count": unpaid_count,
            "unpaid_ledger_sum": unpaid_sum,
            "source_status": "OK",
            "legacy": True,
            "record_origin": "alchemist",
            "provenance": {
                "source": "alchemist",
                "table": "pr_orders",
                "source_id": "attention-summary",
            },
        }

    out = _with_conn(run)
    if out is _MISS:
        return _empty_summary()
    return out


def _empty_summary() -> dict[str, Any]:
    return {
        "awaiting_devi_count": 0,
        "received_count": 0,
        "recent_petty": [],
        "unpaid_ledger_count": 0,
        "unpaid_ledger_sum": None,
        "source_status": "INACCESSIBLE",
        "legacy": True,
        "record_origin": "alchemist",
    }


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _cap(limit: int, *, hard: int = 500) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 100
    return max(1, min(n, hard))


def _set_status(value: str) -> None:
    global _STATUS
    _STATUS = value


def _with_conn(fn: Callable[[sqlite3.Connection], Any]) -> Any:
    path = resolve_db_path()
    if path is None or not path.is_file():
        _set_status("INACCESSIBLE")
        return _MISS
    try:
        conn = connect_readonly(path)
    except (OSError, sqlite3.Error):
        _set_status("INACCESSIBLE")
        return _MISS
    ok = False
    try:
        try:
            out = fn(conn)
            ok = True
            return out
        except (sqlite3.Error, KeyError, TypeError, ValueError):
            return _MISS
    finally:
        conn.close()
        _set_status("OK" if ok else "INACCESSIBLE")


def _query(
    conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]
) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params).fetchall())


def _date_part(value: str | None) -> str:
    text = (value or "").strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def _stamp(row: dict[str, Any], table: str, source_id: Any) -> dict[str, Any]:
    row["record_origin"] = "alchemist"
    row["legacy"] = True
    row["example"] = False
    row["provenance"] = {
        "source": "alchemist",
        "table": table,
        "source_id": source_id,
    }
    return row


def _map_pr(row: sqlite3.Row) -> dict[str, Any]:
    status = (row["status"] or "").strip()
    mapped = _PR_STATUS.get(
        status.casefold(),
        {
            "state": "CLOSED",
            "display_status": status or "Recorded in Alchemist",
            "needs_attention": False,
        },
    )
    pr_num = (row["pr_num"] or "").strip() or None
    notes = (row["notes"] or "").strip() or None
    department = (row["department"] or "").strip() or None
    total = row["invoice_total"]
    out: dict[str, Any] = {
        "pr_id": pr_num or "Existing purchase",
        "pr_num": pr_num,
        "state": mapped["state"],
        "display_status": mapped["display_status"],
        "alchemist_status": status or None,
        "needs_attention": bool(mapped["needs_attention"]),
        "supplier_name": (row["vendor"] or "").strip() or None,
        "purpose": notes or department,
        "requester_label": (row["requested_by"] or "").strip() or None,
        "expected_value": None if total is None else float(total),
        "currency": None,
        "requested_date": _date_part(row["order_date"]) or None,
        "venue": "BZG-UMA",
        "payment_evidence_id": None,
        "payment_label": mapped.get("payment_label"),
        "when": (row["created_at"] or "").strip() or _date_part(row["order_date"]),
    }
    return _stamp(out, "pr_orders", row["id"])


def _direction(flow: str | None) -> tuple[str, str]:
    low = (flow or "").casefold()
    if "cash in" in low or "top-up" in low or "topup" in low:
        return "IN", "Cash in"
    if "cash out" in low or "spend" in low:
        return "OUT", "Cash out"
    return "ADJUSTMENT", "Adjustment"


def _map_petty(row: sqlite3.Row) -> dict[str, Any]:
    direction, label = _direction(row["flow"])
    description = (row["description"] or "").strip() or None
    category = (row["category"] or "").strip() or None
    amount = row["amount"]
    out: dict[str, Any] = {
        "movement_id": f"ALC-PETTY-{row['id']}",
        "business_date": _date_part(row["entry_date"]) or None,
        "direction": direction,
        "direction_label": label,
        "flow": (row["flow"] or "").strip() or None,
        "category": category,
        "purpose": description or category or label,
        "amount": None if amount is None else float(amount),
        "currency": None,
        "logged_by": (row["logged_by_name"] or "").strip() or None,
        "venue": "BZG-UMA",
        "when": (row["created_at"] or "").strip() or _date_part(row["entry_date"]),
    }
    # opening_float is intentionally absent — never summed from movements.
    return _stamp(out, "petty_cash", row["id"])


def _fetch_petty(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = _query(
        conn,
        f"""
        SELECT {_PETTY_COLS}
        FROM petty_cash
        ORDER BY COALESCE(created_at, entry_date) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [_map_petty(r) for r in rows]


def _history_pr(row: sqlite3.Row) -> dict[str, Any]:
    mapped = _map_pr(row)
    when = mapped.get("when") or ""
    day = _date_part(str(when)) or "date unknown"
    out = {
        "when": when,
        "sentence": f"{day} · Purchase request recorded · Alchemist",
        "pr_num": mapped.get("pr_num"),
        "detail": None,
    }
    return _stamp(out, "pr_orders", row["id"])


def _history_petty(row: sqlite3.Row) -> dict[str, Any]:
    mapped = _map_petty(row)
    when = mapped.get("when") or ""
    day = _date_part(str(when)) or mapped.get("business_date") or "date unknown"
    detail = mapped.get("purpose") if mapped.get("purpose") != mapped.get("direction_label") else None
    out = {
        "when": when,
        "sentence": f"{day} · Petty movement recorded · Alchemist",
        "pr_num": None,
        "detail": detail,
    }
    return _stamp(out, "petty_cash", row["id"])
