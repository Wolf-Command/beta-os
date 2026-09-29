#!/usr/bin/env python3
"""Atrium Financial Controller journal authority — approve / reject with SoD.

HUMFIX-1. Matrix silent on FC approve → implement approve + reject/return for
journals prepared by someone else. POST stays denied (open policy for Matt).
Writes the live Beta atrium.sqlite used by the sidecar. Sidecar in-memory
state refreshes on next load/restart.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core import rbac
from core.staff_access import ROLE_ATRIUM_FINANCIAL_CONTROLLER

TZ = ZoneInfo("Asia/Makassar")
ENTITY = "ENT-AMG"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")

# Self-approve denial — preparer display names / person ids that mean Zayen.
ZAYEN_PREPARER_MARKERS = frozenset(
    {
        "pers-zayen",
        "zayen",
        "zayen (controller)",
        "zayen (financial controller)",
        "laluzayen@gmail.com",
    }
)


class FcAuthorityError(ValueError):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _norm_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def is_self_prepare(created_by: str | None, person_id: str, display_name: str | None = None) -> bool:
    """True when the journal preparer is the same human as the actor."""
    created = _norm_name(created_by)
    pid = _norm_name(person_id)
    names = {_norm_name(display_name), pid}
    if person_id == "PERS-ZAYEN":
        names |= ZAYEN_PREPARER_MARKERS
    if not created:
        return False
    if created in names:
        return True
    if pid and pid in created:
        return True
    for marker in names:
        if marker and marker in created:
            return True
    return False


def _open_atrium(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or ATRIUM_DB)
    if not path.is_file():
        raise FcAuthorityError("Atrium books file is missing.", code="unavailable", http_status=503)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _require_fc_grant(person_id: str, code: str, wolf_conn) -> None:
    if not rbac.can(person_id, code, {"entity_id": ENTITY}, conn=wolf_conn):
        raise FcAuthorityError(
            f"{code} is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _get_journal(atrium: sqlite3.Connection, journal_id: str) -> dict[str, Any]:
    row = atrium.execute(
        "SELECT * FROM journal_headers WHERE journal_id=?",
        (journal_id,),
    ).fetchone()
    if not row:
        raise FcAuthorityError("Journal not found.", code="not_found", http_status=404)
    return dict(row)


def approve_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    approver_name: str | None = None,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """Approve a VALIDATED journal prepared by someone else. Not post."""
    _require_fc_grant(person_id, "atrium.journal.approve", wolf_conn)
    name = (approver_name or "").strip() or "Financial Controller"
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        if str(journal.get("status") or "") != "VALIDATED":
            raise FcAuthorityError(
                f"Journal must be VALIDATED before approval. Current: {journal.get('status')}.",
                code="invalid_status",
                http_status=400,
            )
        if is_self_prepare(journal.get("created_by"), person_id, name):
            raise FcAuthorityError(
                "Segregation of duties: you cannot approve a journal you prepared. "
                "A different preparer is required.",
                code="sod_self_approve",
                http_status=403,
            )
        atrium.execute(
            """
            UPDATE journal_headers
            SET status='APPROVED', approved_by=?
            WHERE journal_id=?
            """,
            (name, journal_id),
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        return {
            "ok": True,
            "journal": out,
            "action": "approve",
            "sod": "preparer_ne_approver",
            "post_allowed": False,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        atrium.close()


def reject_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    note: str | None = None,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """Return a VALIDATED journal to DRAFT. SoD: not own prepare."""
    _require_fc_grant(person_id, "atrium.journal.reject", wolf_conn)
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status not in {"VALIDATED", "APPROVED"}:
            raise FcAuthorityError(
                f"Only VALIDATED or APPROVED journals can be returned. Current: {status}.",
                code="invalid_status",
                http_status=400,
            )
        if is_self_prepare(journal.get("created_by"), person_id):
            raise FcAuthorityError(
                "Segregation of duties: you cannot reject/return a journal you prepared.",
                code="sod_self_reject",
                http_status=403,
            )
        ref = str(journal.get("source_reference") or "")
        if note:
            stamp = f"[returned {now_iso()}] {note.strip()}"
            ref = f"{ref} {stamp}".strip() if ref else stamp
        atrium.execute(
            """
            UPDATE journal_headers
            SET status='DRAFT', approved_by='', source_reference=?
            WHERE journal_id=?
            """,
            (ref, journal_id),
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        return {
            "ok": True,
            "journal": out,
            "action": "reject",
            "sod": "preparer_ne_approver",
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        atrium.close()


def fc_may_approve_path(wolf_role: str, method: str, api_path: str) -> bool:
    """True when Wolf should allow FC through the product proxy for approve/reject."""
    if wolf_role != ROLE_ATRIUM_FINANCIAL_CONTROLLER:
        return False
    if method.upper() != "POST":
        return False
    return bool(
        api_path.endswith("/approve")
        or api_path.endswith("/reject")
        or api_path.endswith("/return")
    )


def still_denied_sensitive(method: str, api_path: str) -> bool:
    """Post, pay, bank, admin stay denied for FC on the product mount."""
    api = api_path or ""
    if api == "/api/admin" or api.startswith("/api/admin/"):
        return True
    if "/bank" in api:
        return True
    if method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    if api.endswith("/post") or api.endswith("/reverse"):
        return True
    if api in {"/api/ap/payments", "/api/tax/payment", "/api/auth/login"}:
        return True
    if "owner-pool/email" in api:
        return True
    return False
