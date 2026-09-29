#!/usr/bin/env python3
"""Atrium Finance staff desk. Read the books, save a draft, send a decision.

Decision served: owner brief 28 Sep 2026 11:28 WITA (staff access), extended
by ATRIUMFIN-UX-1 and ATRIUMFIN-UX-2 on this same desk. It does not add a
grant, post a journal, pay, or approve.
"""
from __future__ import annotations

import re
from typing import Any

from core import approvals as _approvals
from core import atrium_books as _ledger
from core import fin_accounting_core as _books
from core import ggv_finance_invoice as _invoice
from core import rbac as _rbac
from core.staff_access import ROLE_ATRIUM_FINANCE, ROLE_ATRIUM_FINANCIAL_CONTROLLER

_ATRIUM_FINANCE_ROLES = (ROLE_ATRIUM_FINANCIAL_CONTROLLER, ROLE_ATRIUM_FINANCE)

ENTITY = "ENT-AMG"
ENTITY_LABEL = "Atrium"
CONTROLLER_LINE = "Approvals are handled by the Finance Controller."
BOARD_EMPTY = (
    "The Atrium books are not open yet, so there is no balance to show. "
    "When the books are open, the hotel position will appear here."
)
APPROVAL_EMPTY = (
    "No approval request is waiting. Describe the decision you need and send it."
)

# Built in production, left off this desk because the seat cannot do them safely.
WITHHELD: tuple[dict[str, str], ...] = (
    {
        "id": "cash",
        "grant": "",
        "reason": "Cash, bank, and the card monitor need a bank position or a money movement. Those stay off this seat.",
    },
    {
        "id": "configuration",
        "grant": "finance.policy.admin",
        "reason": "Configuration changes the control file. That permission is not on this seat.",
    },
    {
        "id": "night-audit",
        "grant": "",
        "reason": "Night audit imports revenue and writes a journal. That is a posting path.",
    },
    {
        "id": "procurement",
        "grant": "",
        "reason": "Procurement ends in a payment. Payment is not on this seat.",
    },
    {
        "id": "payment-run",
        "grant": "payment.execute",
        "reason": "A payment run pays vendors. That permission is not on this seat.",
    },
    {
        "id": "payroll",
        "grant": "",
        "reason": "Payroll posts pay and statutory amounts. That is a posting path.",
    },
    {
        "id": "journal-post",
        "grant": "atrium.journal.post",
        "reason": "Journal posting stays ungranted pending Matt policy (HUMFIX-1 open point).",
    },
)

NAVIGATION: tuple[dict[str, str], ...] = (
    {"id": "board", "label": "Board", "href": "/amg/finance"},
    {"id": "ledger", "label": "Ledger", "href": "/amg/finance/ledger"},
    {"id": "chart", "label": "Chart of Accounts", "href": "/amg/finance/accounts"},
    {"id": "journals", "label": "Journals", "href": "/amg/finance/journals"},
    {"id": "reports", "label": "Reports", "href": "/amg/finance/reports"},
    {"id": "approvals", "label": "Approvals", "href": "/amg/finance/approvals"},
)

PAGE_ROUTES: tuple[str, ...] = tuple(row["href"] for row in NAVIGATION)
API_GET_ROUTES: tuple[str, ...] = (
    "/api/amg/finance",
    "/api/amg/finance/ledger",
    "/api/amg/finance/accounts",
    "/api/amg/finance/journals",
    "/api/amg/finance/reports",
    "/api/amg/finance/approvals",
)
API_POST_ROUTES: tuple[str, ...] = (
    "/api/amg/finance",
    "/api/amg/finance/approvals",
    "/api/amg/finance/journals",
)
_JOURNAL_ID = re.compile(r"/api/amg/finance/journals/(JRN-[A-Za-z0-9]{8,32})(?:/(validate|approve|post))?$")

BANNED_UI = (
    "Hotel books are not open on this desk.",
    "No report figure is on this page.",
    "Do not type an amount.",
    "You cannot approve a payment",
)
PAGE_BANNED = BANNED_UI + (
    "EMPTY",
    "staff_ready",
    "not invented",
    "Not PROVEN",
)

_REFUSED_KEYS = frozenset(
    {
        "amount",
        "material_amount",
        "payment",
        "pay",
        "bank",
        "account_number",
        "iban",
        "approve",
        "post",
        "journal",
    }
)


class DeskError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def navigation() -> list[dict[str, str]]:
    return [dict(row) for row in NAVIGATION]


def withheld() -> list[dict[str, str]]:
    return [dict(row) for row in WITHHELD]


def registered_routes() -> list[tuple[str, str]]:
    """Routes the desk registers. Journal id routes use a sample id."""
    rows = [("GET", href) for href in PAGE_ROUTES]
    rows.extend(("GET", href) for href in API_GET_ROUTES)
    rows.extend(("POST", href) for href in API_POST_ROUTES)
    sample = "/api/amg/finance/journals/JRN-sample0001"
    rows.append(("GET", sample))
    rows.append(("POST", sample))
    rows.append(("POST", sample + "/validate"))
    rows.append(("POST", sample + "/approve"))
    rows.append(("POST", sample + "/post"))
    return rows


def _norm(path: str) -> str:
    base = (path or "").split("?")[0]
    if not base.startswith("/"):
        base = "/" + base
    return base.rstrip("/") or "/"


def route_kind(method: str, path: str) -> str | None:
    """Return the desk action for a registered route, or None when it is not ours."""
    verb = (method or "GET").upper()
    base = _norm(path)
    if verb == "GET" and base in PAGE_ROUTES:
        return "page"
    if verb == "GET" and base == "/api/amg/finance":
        return "workspace"
    if verb == "GET" and base == "/api/amg/finance/approvals":
        return "workspace"
    if verb == "GET" and base == "/api/amg/finance/ledger":
        return "ledger"
    if verb == "GET" and base == "/api/amg/finance/accounts":
        return "accounts"
    if verb == "GET" and base == "/api/amg/finance/journals":
        return "journals"
    if verb == "GET" and base == "/api/amg/finance/reports":
        return "reports"
    if verb == "POST" and base == "/api/amg/finance":
        return "board-write"
    if verb == "POST" and base == "/api/amg/finance/approvals":
        return "approval"
    if verb == "POST" and base == "/api/amg/finance/journals":
        return "journal-create"
    match = _JOURNAL_ID.fullmatch(base)
    if not match:
        return None
    action = match.group(2) or ""
    if verb == "GET" and not action:
        return "journal-read"
    if verb == "POST" and not action:
        return "journal-save"
    if verb == "POST" and action == "validate":
        return "journal-validate"
    if verb == "POST" and action in {"approve", "post"}:
        return "journal-" + action
    return None


def _require(person_id: str, code: str, conn, message: str) -> None:
    if not _rbac.can(person_id, code, {"entity_id": ENTITY}, conn=conn):
        raise DeskError(message, code="forbidden", http_status=403)


def _assignment_id(conn, person_id: str) -> str | None:
    marks = ",".join("?" for _ in _ATRIUM_FINANCE_ROLES)
    row = conn.execute(
        f"""
        SELECT a.assignment_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND p.role_id IN ({marks}) AND p.status='ACTIVE'
        ORDER BY a.is_primary DESC, a.assignment_id
        LIMIT 1
        """,
        (person_id, *_ATRIUM_FINANCE_ROLES),
    ).fetchone()
    if row is None:
        return None
    return str(row[0] or "") or None


def _own_approvals(conn, person_id: str) -> list[dict[str, str]]:
    try:
        rows = conn.execute(
            """
            SELECT approval_request_id, title, status, request_type, requested_at
            FROM core_approval_requests
            WHERE owning_entity_id=? AND requested_by_person_id=?
              AND IFNULL(title, '') NOT LIKE '%DEMO%'
              AND IFNULL(source_type, '') != 'TEST'
            ORDER BY requested_at DESC
            LIMIT 20
            """,
            (ENTITY, person_id),
        ).fetchall()
    except Exception:
        return []
    out = []
    for row in rows:
        out.append(
            {
                "approval_request_id": str(row[0] or ""),
                "title": str(row[1] or ""),
                "status": str(row[2] or ""),
                "request_type": str(row[3] or ""),
                "requested_at": str(row[4] or ""),
            }
        )
    return out


def _board_figure() -> dict[str, Any]:
    """Honest board. A missing book is not zero and not a balance."""
    core = _books.read_accounting_core()
    entities = core.get("entities") or []
    amg = next((row for row in entities if row.get("entity_id") == ENTITY), None)
    figure = None if amg is None else amg.get("consolidation_figure")
    if figure is not None:
        return {"empty": False, "figure": figure, "message": None}
    return {
        "empty": True,
        "figure": None,
        "message": BOARD_EMPTY,
        "books_source": "UNAVAILABLE",
        "books_opened": False,
    }


def workspace(person_id: str, conn) -> dict[str, Any]:
    entities = [
        dict(row)
        for row in _invoice.finance_entities(person_id, conn)
        if row.get("id") == "AMG" or row.get("entity_id") == ENTITY
    ]
    approvals = _own_approvals(conn, person_id)
    board = _board_figure()
    try:
        books = _ledger.summary()
    except _ledger.BooksError:
        books = {"chart_count": 0, "draft_count": 0, "posted": False}
    return {
        "ok": True,
        "entity": {"id": ENTITY, "label": ENTITY_LABEL},
        "finance_entities": entities,
        "navigation": navigation(),
        "board": board,
        "chart": {"count": books.get("chart_count") or 0},
        "drafts": {"count": books.get("draft_count") or 0},
        "report": {
            "figure": None,
            "message": _ledger.REPORT_EMPTY,
        },
        "ledger": {
            "figure": None,
            "message": _ledger.LEDGER_EMPTY,
        },
        "approvals": {
            "items": approvals,
            "count": len(approvals),
            "empty_message": APPROVAL_EMPTY,
            "controller": CONTROLLER_LINE,
        },
        "books_opened": False,
        "journal_saved": False,
        "posted": False,
        "money_movement": False,
        "staff_ready": False,
        "human_commissioned": False,
    }


def _guard_books(person_id: str, conn) -> None:
    _require(
        person_id,
        "atrium.board.read",
        conn,
        "Atrium Finance is not on this assignment.",
    )


def read_ledger(person_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.ledger.read", conn, "Reading the ledger is not on this assignment.")
    payload = _ledger.ledger()
    payload["money_movement"] = False
    payload["posted"] = False
    return payload


def read_accounts(person_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.coa.read", conn, "Reading the chart of accounts is not on this assignment.")
    payload = _ledger.list_accounts()
    payload["money_movement"] = False
    return payload


def read_journals(person_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.journal.draft", conn, "Draft journals are not on this assignment.")
    payload = _ledger.list_drafts(person_id)
    payload["money_movement"] = False
    payload["posted"] = False
    return payload


def read_journal(person_id: str, journal_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.journal.draft", conn, "Draft journals are not on this assignment.")
    try:
        item = _ledger.get_draft(person_id, journal_id)
    except _ledger.BooksError as exc:
        raise DeskError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    return {"journal": item, "posted": False, "money_movement": False}


def read_reports(person_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.report.read", conn, "Reading the statements is not on this assignment.")
    payload = _ledger.list_reports()
    payload["money_movement"] = False
    payload["posted"] = False
    return payload


def save_journal(person_id: str, body: dict[str, Any] | None, conn, journal_id: str | None = None) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.journal.draft", conn, "Saving a draft journal is not on this assignment.")
    try:
        item = _ledger.save_draft(person_id, body, journal_id)
    except _ledger.BooksError as exc:
        raise DeskError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    return {
        "journal": item,
        "draft_saved": True,
        "journal_saved": False,
        "posted": False,
        "money_movement": False,
    }


def validate_journal(person_id: str, body: dict[str, Any] | None, journal_id: str, conn) -> dict[str, Any]:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.journal.draft", conn, "Saving a draft journal is not on this assignment.")
    try:
        result = _ledger.validate_draft(person_id, body, journal_id)
    except _ledger.BooksError as exc:
        raise DeskError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    result["money_movement"] = False
    result["journal_saved"] = False
    return result


def journal_id_from(path: str) -> str | None:
    match = _JOURNAL_ID.fullmatch(_norm(path))
    if not match:
        return None
    return match.group(1)


def refuse_journal_decision(person_id: str, action: str, conn) -> None:
    _guard_books(person_id, conn)
    _require(person_id, "atrium.journal.draft", conn, "Draft journals are not on this assignment.")
    try:
        _ledger.refuse_decision(action)
    except _ledger.BooksError as exc:
        raise DeskError(str(exc), code=exc.code, http_status=exc.http_status) from exc


def submit_approval(
    person_id: str,
    body: dict[str, Any] | None,
    conn,
    *,
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """General decision request for Atrium. Not a payment, journal, or bank change."""
    payload = body if isinstance(body, dict) else {}
    if not _rbac.can(person_id, "approval.request", {"entity_id": ENTITY}, conn=conn):
        raise DeskError(
            "Sending an approval request is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    if not _rbac.can(person_id, "atrium.board.read", {"entity_id": ENTITY}, conn=conn):
        raise DeskError(
            "Atrium Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    refused = [key for key in payload if str(key).lower() in _REFUSED_KEYS]
    if refused:
        raise DeskError(
            "This desk does not take an amount, a payment, a journal post, or a bank change.",
            code="forbidden",
            http_status=403,
        )
    entity = str(payload.get("owning_entity_id") or ENTITY).strip()
    if entity != ENTITY:
        raise DeskError(
            "This desk is Atrium only.",
            code="forbidden",
            http_status=403,
        )
    request_type = str(payload.get("request_type") or "GENERAL").strip().upper()
    if request_type != "GENERAL":
        raise DeskError(
            "This desk sends a general decision request.",
            code="forbidden",
            http_status=403,
        )
    wanted = str(payload.get("required_permission_code") or "approval.decide").strip()
    if wanted != "approval.decide":
        raise DeskError(
            "This desk cannot ask for payment, posting, or a bank change.",
            code="forbidden",
            http_status=403,
        )
    title = str(payload.get("title") or "").strip()
    if not title:
        raise DeskError("Add what needs a decision.", code="missing_title", http_status=400)
    if len(title) > 180:
        raise DeskError("Keep the request to one short line.", code="title_too_long", http_status=400)
    description = str(payload.get("description") or "").strip() or None
    if description and len(description) > 2000:
        raise DeskError("Shorten the note.", code="note_too_long", http_status=400)
    assignment_id = _assignment_id(conn, person_id)
    if not assignment_id:
        raise DeskError(
            "Atrium Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    try:
        item = _approvals.create_approval_request(
            title=title,
            description=description,
            request_type="GENERAL",
            owning_entity_id=ENTITY,
            required_permission_code="approval.decide",
            source_type="HUMAN",
            requested_by_assignment_id=assignment_id,
            material_amount=None,
            currency=None,
            requested_by_person_id=None,
            verified_person_id=person_id,
            identity=identity,
            conn=conn,
        )
    except _approvals.ApprovalError as exc:
        status = int(getattr(exc, "http_status", 400) or 400)
        if status < 400:
            status = 400
        raise DeskError("That request was not sent.", code=exc.code, http_status=status) from exc
    return {
        "approval_request_id": item.get("approval_request_id"),
        "title": item.get("title") or title,
        "status": item.get("status") or "PENDING",
        "owning_entity_id": ENTITY,
        "money_movement": False,
    }
