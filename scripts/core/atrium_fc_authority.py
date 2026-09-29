#!/usr/bin/env python3
"""Atrium Financial Controller journal authority — SoD workflow (ATRIUM-SOD-1).

Decision: Matt APPROVED 29 Sep 13:32 WITA (ATRIUM-SOD-1).
Workflow (no skips): DRAFT → VALIDATED → SUBMITTED → APPROVED|RETURNED → POSTED.
FC may approve and post journals prepared by someone else (preparer_person_id).
FC may not approve or post own prepare. Post of non-APPROVED is refused.
Writes the live Beta atrium.sqlite used by the sidecar. Sidecar in-memory
state refreshes on next load/restart.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core import rbac
from core.staff_access import ROLE_ATRIUM_FINANCIAL_CONTROLLER

TZ = ZoneInfo("Asia/Makassar")
ENTITY = "ENT-AMG"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")

ZAYEN_PREPARER_MARKERS = frozenset(
    {
        "pers-zayen",
        "zayen",
        "zayen (controller)",
        "zayen (financial controller)",
        "laluzayen@gmail.com",
    }
)

WORKING_QUEUE = frozenset({"DRAFT", "VALIDATED", "SUBMITTED", "APPROVED", "RETURNED"})
ARCHIVE_REASON = "automated test artifact"


class FcAuthorityError(ValueError):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_wita_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _norm_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def is_self_prepare(
    created_by: str | None,
    person_id: str,
    display_name: str | None = None,
    preparer_person_id: str | None = None,
) -> bool:
    """True when the journal preparer is the same human as the actor.

    Prefer preparer_person_id (canonical). Fall back to created_by markers.
    """
    prep = (preparer_person_id or "").strip()
    if prep:
        return prep == person_id
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
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_headers)").fetchall()}
    alters = []
    if "preparer_person_id" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN preparer_person_id TEXT NOT NULL DEFAULT ''")
    if "posted_by" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN posted_by TEXT NOT NULL DEFAULT ''")
    if "return_reason" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN return_reason TEXT NOT NULL DEFAULT ''")
    if "wolf_created" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN wolf_created INTEGER NOT NULL DEFAULT 0")
    if "historical_import" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN historical_import INTEGER NOT NULL DEFAULT 0")
    if "verified" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")
    if "archived_reason" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN archived_reason TEXT NOT NULL DEFAULT ''")
    if "evidence_ref" not in cols:
        alters.append("ALTER TABLE journal_headers ADD COLUMN evidence_ref TEXT NOT NULL DEFAULT ''")
    for sql in alters:
        conn.execute(sql)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_workflow_audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          at_utc TEXT NOT NULL,
          at_wita TEXT NOT NULL,
          journal_id TEXT NOT NULL,
          from_status TEXT NOT NULL,
          to_status TEXT NOT NULL,
          actor_person_id TEXT NOT NULL,
          evidence_ref TEXT NOT NULL DEFAULT '',
          note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_evidence (
          evidence_id TEXT PRIMARY KEY,
          journal_id TEXT NOT NULL,
          filename TEXT NOT NULL,
          content_type TEXT NOT NULL,
          label TEXT NOT NULL,
          path TEXT NOT NULL,
          created_at_utc TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_import_batches (
          batch_id TEXT PRIMARY KEY,
          source_file TEXT NOT NULL,
          source_hash TEXT NOT NULL,
          period TEXT NOT NULL,
          imported_at TEXT NOT NULL,
          row_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Cutover setting on system_settings if the live table exists
    ss_cols = {r[1] for r in conn.execute("PRAGMA table_info(system_settings)").fetchall()}
    if ss_cols and "wolf_cutover_date" not in ss_cols:
        conn.execute(
            "ALTER TABLE system_settings ADD COLUMN wolf_cutover_date TEXT NOT NULL DEFAULT '2026-09-29'"
        )
    conn.commit()


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


def _audit_transition(
    atrium: sqlite3.Connection,
    *,
    journal_id: str,
    from_status: str,
    to_status: str,
    actor_person_id: str,
    evidence_ref: str = "",
    note: str = "",
) -> None:
    atrium.execute(
        """
        INSERT INTO journal_workflow_audit (
          at_utc, at_wita, journal_id, from_status, to_status,
          actor_person_id, evidence_ref, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_utc_iso(),
            now_wita_iso(),
            journal_id,
            from_status,
            to_status,
            actor_person_id,
            evidence_ref or "",
            note or "",
        ),
    )


def _record_wolf_audit(
    wolf_conn,
    *,
    person_id: str,
    action: str,
    journal_id: str,
    result: str,
    reason_code: str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        from core import audit as core_audit

        meta = dict(metadata or {})
        meta["actor_person_id"] = person_id
        core_audit.record_event(
            conn=wolf_conn,
            actor_type="SYSTEM",
            action=action,
            resource_type="atrium_journal",
            resource_id=journal_id,
            result="SUCCEEDED" if result in {"OK", "SUCCEEDED", "ALLOWED"} else "FAILED",
            reason_code=reason_code,
            entity_id=ENTITY,
            source="atrium_fc_authority",
            metadata=meta,
            commit=False,
        )
    except Exception:
        # Catalog may be temp / missing columns in unit fixtures — do not block books write.
        pass


def validate_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """DRAFT|RETURNED → VALIDATED. Preparer / draft grant."""
    _require_fc_grant(person_id, "atrium.journal.draft", wolf_conn)
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status not in {"DRAFT", "RETURNED"}:
            raise FcAuthorityError(
                f"Only DRAFT or RETURNED journals can be validated. Current: {status}.",
                code="invalid_status",
                http_status=400,
            )
        atrium.execute(
            "UPDATE journal_headers SET status='VALIDATED', return_reason='' WHERE journal_id=?",
            (journal_id,),
        )
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="VALIDATED",
            actor_person_id=person_id,
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        _record_wolf_audit(
            wolf_conn,
            person_id=person_id,
            action="atrium.journal.validate",
            journal_id=journal_id,
            result="OK",
            metadata={"from": status, "to": "VALIDATED"},
        )
        return {"ok": True, "journal": out, "action": "validate"}
    finally:
        atrium.close()


def submit_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """VALIDATED → SUBMITTED. Preparer grant."""
    _require_fc_grant(person_id, "atrium.journal.draft", wolf_conn)
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status != "VALIDATED":
            raise FcAuthorityError(
                f"Journal must be VALIDATED before submit. Current: {status}.",
                code="invalid_status",
                http_status=400,
            )
        atrium.execute(
            "UPDATE journal_headers SET status='SUBMITTED' WHERE journal_id=?",
            (journal_id,),
        )
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="SUBMITTED",
            actor_person_id=person_id,
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        _record_wolf_audit(
            wolf_conn,
            person_id=person_id,
            action="atrium.journal.submit",
            journal_id=journal_id,
            result="OK",
        )
        return {"ok": True, "journal": out, "action": "submit"}
    finally:
        atrium.close()


def approve_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    approver_name: str | None = None,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """Approve a SUBMITTED journal prepared by someone else. Not post."""
    _require_fc_grant(person_id, "atrium.journal.approve", wolf_conn)
    name = (approver_name or "").strip() or "Financial Controller"
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status != "SUBMITTED":
            raise FcAuthorityError(
                f"Journal must be SUBMITTED before approval. Current: {status}.",
                code="invalid_status",
                http_status=400,
            )
        if is_self_prepare(
            journal.get("created_by"),
            person_id,
            name,
            journal.get("preparer_person_id"),
        ):
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
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="APPROVED",
            actor_person_id=person_id,
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        _record_wolf_audit(
            wolf_conn,
            person_id=person_id,
            action="atrium.journal.approve",
            journal_id=journal_id,
            result="OK",
            metadata={"sod": "preparer_ne_approver"},
        )
        return {
            "ok": True,
            "journal": out,
            "action": "approve",
            "sod": "preparer_ne_approver",
            "post_allowed": True,
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
    """Return a SUBMITTED journal to RETURNED with a required reason. SoD."""
    _require_fc_grant(person_id, "atrium.journal.reject", wolf_conn)
    reason = (note or "").strip()
    if not reason:
        raise FcAuthorityError(
            "Return requires a reason.",
            code="reason_required",
            http_status=400,
        )
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status not in {"SUBMITTED", "APPROVED"}:
            raise FcAuthorityError(
                f"Only SUBMITTED or APPROVED journals can be returned. Current: {status}.",
                code="invalid_status",
                http_status=400,
            )
        if is_self_prepare(
            journal.get("created_by"),
            person_id,
            preparer_person_id=journal.get("preparer_person_id"),
        ):
            raise FcAuthorityError(
                "Segregation of duties: you cannot reject/return a journal you prepared.",
                code="sod_self_reject",
                http_status=403,
            )
        stamp = f"[returned {now_wita_iso()} WITA] {reason}"
        ref = str(journal.get("source_reference") or "")
        ref = f"{ref} {stamp}".strip() if ref else stamp
        atrium.execute(
            """
            UPDATE journal_headers
            SET status='RETURNED', approved_by='', return_reason=?, source_reference=?
            WHERE journal_id=?
            """,
            (reason, ref, journal_id),
        )
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="RETURNED",
            actor_person_id=person_id,
            note=reason,
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        _record_wolf_audit(
            wolf_conn,
            person_id=person_id,
            action="atrium.journal.return",
            journal_id=journal_id,
            result="OK",
            metadata={"reason": reason},
        )
        return {
            "ok": True,
            "journal": out,
            "action": "return",
            "sod": "preparer_ne_approver",
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        atrium.close()


def post_journal(
    person_id: str,
    journal_id: str,
    *,
    wolf_conn,
    poster_name: str | None = None,
    atrium_db: Path | None = None,
) -> dict[str, Any]:
    """Post an APPROVED journal prepared by someone else. No auto-approve."""
    _require_fc_grant(person_id, "atrium.journal.post", wolf_conn)
    name = (poster_name or "").strip() or "Financial Controller"
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status != "APPROVED":
            raise FcAuthorityError(
                f"Journal must be APPROVED before posting. Current: {status}. "
                "Validate → submit → approve before post; no skips.",
                code="invalid_status",
                http_status=400,
            )
        if is_self_prepare(
            journal.get("created_by"),
            person_id,
            name,
            journal.get("preparer_person_id"),
        ):
            raise FcAuthorityError(
                "Segregation of duties: you cannot post a journal you prepared.",
                code="sod_self_post",
                http_status=403,
            )
        posted_at = now_utc_iso()
        atrium.execute(
            """
            UPDATE journal_headers
            SET status='POSTED', posted_at=?, posted_by=?, wolf_created=1
            WHERE journal_id=?
            """,
            (posted_at, name, journal_id),
        )
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="POSTED",
            actor_person_id=person_id,
        )
        atrium.commit()
        out = _get_journal(atrium, journal_id)
        _record_wolf_audit(
            wolf_conn,
            person_id=person_id,
            action="atrium.journal.post",
            journal_id=journal_id,
            result="OK",
            metadata={"sod": "preparer_ne_poster", "wolf_created": True},
        )
        return {
            "ok": True,
            "journal": out,
            "action": "post",
            "sod": "preparer_ne_poster",
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        atrium.close()


def archive_test_artifact(
    journal_id: str,
    *,
    atrium_db: Path | None = None,
    reason: str = ARCHIVE_REASON,
    actor_person_id: str = "SYSTEM",
) -> dict[str, Any]:
    """Mark a test journal ARCHIVED so it leaves the working queue. History kept."""
    atrium = _open_atrium(atrium_db)
    try:
        journal = _get_journal(atrium, journal_id)
        status = str(journal.get("status") or "")
        if status == "ARCHIVED":
            return {"ok": True, "journal_id": journal_id, "already": True, "status": status}
        atrium.execute(
            """
            UPDATE journal_headers
            SET status='ARCHIVED', archived_reason=?
            WHERE journal_id=?
            """,
            (reason, journal_id),
        )
        _audit_transition(
            atrium,
            journal_id=journal_id,
            from_status=status,
            to_status="ARCHIVED",
            actor_person_id=actor_person_id,
            note=reason,
        )
        atrium.commit()
        return {"ok": True, "journal_id": journal_id, "already": False, "status": "ARCHIVED"}
    finally:
        atrium.close()


def fc_may_approve_path(wolf_role: str, method: str, api_path: str) -> bool:
    """True when Wolf should allow FC through the product proxy for workflow verbs."""
    if wolf_role != ROLE_ATRIUM_FINANCIAL_CONTROLLER:
        return False
    if method.upper() != "POST":
        return False
    return bool(
        api_path.endswith("/approve")
        or api_path.endswith("/reject")
        or api_path.endswith("/return")
        or api_path.endswith("/post")
        or api_path.endswith("/submit")
        or api_path.endswith("/validate")
    )


def still_denied_sensitive(method: str, api_path: str) -> bool:
    """Pay, bank, admin, reverse stay denied for FC on the product mount."""
    api = api_path or ""
    if api == "/api/admin" or api.startswith("/api/admin/"):
        return True
    if "/bank" in api:
        return True
    if method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    if api.endswith("/reverse"):
        return True
    if api in {"/api/ap/payments", "/api/tax/payment", "/api/auth/login"}:
        return True
    if "owner-pool/email" in api:
        return True
    return False


def new_evidence_id() -> str:
    return f"EV-ATRIUM-{uuid.uuid4().hex[:12].upper()}"
