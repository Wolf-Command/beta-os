#!/usr/bin/env python3
"""Atrium Finance staff desk. Board read and a general approval request.

Decision served: owner brief 28 Sep 2026 11:28 WITA (staff access), extended
by ATRIUMFIN-UX-1 after the 14:16 placeholder fail. This is the existing
Atrium Finance desk. It does not add a grant, open the books, or pay.
"""
from __future__ import annotations

from typing import Any

from core import approvals as _approvals
from core import fin_accounting_core as _books
from core import ggv_finance_invoice as _invoice
from core import rbac as _rbac
from core.staff_access import ROLE_ATRIUM_FINANCE

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

# Routes named on the role grants that are not implemented in Beta.
# Navigation must not include these.
WITHHELD: tuple[dict[str, str], ...] = (
    {
        "id": "ledger",
        "grant": "atrium.ledger.read",
        "reason": (
            "The grant is stored. Beta has no journal table and no "
            "/api/journals, /api/ledger, or /api/trial-balance route."
        ),
    },
    {
        "id": "chart",
        "grant": "atrium.coa.read",
        "reason": "The grant is stored. Beta has no chart table and no /api/accounts route.",
    },
    {
        "id": "reports",
        "grant": "atrium.report.read",
        "reason": (
            "The grant is stored. The named statement routes are not in Beta. "
            "/api/fin/mgmt-reporting is Owner only."
        ),
    },
    {
        "id": "journal",
        "grant": "atrium.journal.draft",
        "reason": (
            "The grant is stored. Beta has no journal table and no "
            "POST /api/journals route. Approve and post stay ungranted."
        ),
    },
)

NAVIGATION: tuple[dict[str, str], ...] = (
    {"id": "board", "label": "Board", "href": "/amg/finance"},
    {"id": "approvals", "label": "Approvals", "href": "/amg/finance/approvals"},
)

BANNED_UI = (
    "Hotel books are not open on this desk.",
    "No report figure is on this page.",
    "Do not type an amount.",
    "You cannot approve a payment",
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


def _assignment_id(conn, person_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT a.assignment_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND p.role_id=? AND p.status='ACTIVE'
        ORDER BY a.is_primary DESC, a.assignment_id
        LIMIT 1
        """,
        (person_id, ROLE_ATRIUM_FINANCE),
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
    return {
        "ok": True,
        "entity": {"id": ENTITY, "label": ENTITY_LABEL},
        "finance_entities": entities,
        "navigation": navigation(),
        "withheld": withheld(),
        "board": board,
        "report": {
            "empty": True,
            "figure": None,
            "message": "No Atrium statement is available until the books are open.",
        },
        "approvals": {
            "items": approvals,
            "count": len(approvals),
            "empty": not approvals,
            "empty_message": APPROVAL_EMPTY,
            "controller": CONTROLLER_LINE,
        },
        "books_opened": False,
        "journal_saved": False,
        "money_movement": False,
        "staff_ready": False,
        "human_commissioned": False,
    }


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
