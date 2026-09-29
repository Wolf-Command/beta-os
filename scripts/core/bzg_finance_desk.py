#!/usr/bin/env python3
"""CORE-ENT-1 / CORE-BOOKS-1 — thin BZG Finance desk (entity-scoped; books shell)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core import entity_books as _books
from core import ggv_finance_invoice as _inv
from core import rbac as _rbac

ENTITY = "ENT-BZG"
BOARD_PERM = "atrium.board.read"
PAGE_PATHS = frozenset(
    {
        "/bzg/finance",
        "/bzg/finance/",
    }
)
HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "proven": False,
    "entity_id": ENTITY,
    "legal_entity_id": ENTITY,
    "pack": "FC-SHELL-2",
}


class BzgFinanceError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def matches(path: str) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    if trimmed.startswith("/api/bzg/finance"):
        return True
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def require_board(person_id: str | None, conn: sqlite3.Connection) -> None:
    pid = (person_id or "").strip()
    if not pid or not _rbac.can(pid, BOARD_PERM, {"entity_id": ENTITY}, conn=conn):
        raise BzgFinanceError(
            "BZG Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def overview(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    require_board(person_id, conn)
    entities = _inv.finance_entities(person_id, conn)
    try:
        stamp = _books.desk_stamp(ENTITY)
    except Exception:
        stamp = {
            "books_enabled": True,
            "books_opened": True,
            "empty": True,
            "shell_kind": "empty_shell",
            "message": "BZG books shell (unavailable to read right now).",
            "journals": 0,
            "accounts": 0,
            "db_file": "atrium-bzg.sqlite",
        }
    return {
        **HONESTY,
        **{k: stamp[k] for k in (
            "books_enabled",
            "books_opened",
            "empty",
            "shell_kind",
            "journals",
            "accounts",
            "db_file",
            "outlet_id_nullable",
        ) if k in stamp},
        "ok": True,
        "title": "BZG Finance",
        "message": stamp.get("message") or (
            "BZG books shell is open. COA template OK — zero journals. "
            "Outlet registry at /bzg/outlets."
        ),
        "finance_entities": entities,
        "operating_unit_hook": "OU-BZG-RAIN-POOL",
        "outlet_registry": "/bzg/outlets",
    }


def dispatch(
    method: str,
    path: str,
    person_id: str | None,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    raw = (path or "").split("?")[0]
    trimmed = raw.rstrip("/") or "/"
    if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
        require_board(person_id, conn)
        return {"_html": True}
    if not trimmed.startswith("/api/bzg/finance"):
        raise BzgFinanceError("Not found.", code="not_found", http_status=404)
    if method != "GET":
        raise BzgFinanceError(
            "BZG Finance money writes are not opened on this pack.",
            code="method_not_allowed",
            http_status=405,
        )
    rest = trimmed[len("/api/bzg/finance") :] or "/"
    if rest in {"", "/", "/overview"}:
        return overview(person_id or "", conn)
    if rest == "/books":
        require_board(person_id, conn)
        return {**HONESTY, **_books.desk_stamp(ENTITY), "ok": True}
    raise BzgFinanceError("Not found.", code="not_found", http_status=404)


def page_path() -> Path:
    return Path(__file__).resolve().parents[2] / "dashboards" / "bzg-finance.html"
