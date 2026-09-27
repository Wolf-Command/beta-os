#!/usr/bin/env python3
"""Classify stored ledger rows as valid operational or invalid/test.

Read-only. Rows stay in the append-only tables. INVALIDATED history,
P4 test actors, fixture evidence, and the rejected P4 exceptions are
not valid operational records.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core.canonical_guard import BETA_CATALOG

VALID = "VALID"
INVALID_TEST = "INVALID_TEST"

_EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
_THIRD_EXCEPTION = "GEX-41967006-311f-4ab0-9802-1e6db54ce18e"


def _blob(*parts: Any) -> str:
    return " ".join(str(part or "") for part in parts).upper()


def _p4_person(value: Any) -> bool:
    return str(value or "").upper().startswith("PERS-P4-")


def is_invalid_or_test(table: str, row: dict[str, Any] | sqlite3.Row) -> bool:
    data = dict(row)
    if table == "core_evidence_records":
        if str(data.get("evidence_id") or "") == _EVIDENCE_ID:
            return True
        if str(data.get("status") or "") == "INVALIDATED":
            return True
        if str(data.get("source_type") or "").upper() == "TEST":
            return True
        if _p4_person(data.get("submitted_by_person_id")):
            return True
        blob = _blob(
            data.get("evidence_id"),
            data.get("invalidate_reason"),
            data.get("source_reference"),
        )
        return "P4-TEST" in blob or "FIXTURE" in blob or "DEMO" in blob
    if table == "core_governance_exceptions":
        if str(data.get("exception_id") or "") == _THIRD_EXCEPTION:
            return True
        if _p4_person(data.get("requested_by_person_id")):
            return True
        blob = _blob(data.get("reject_reason"), data.get("control_reference"), data.get("exception_id"))
        return "P4-TEST" in blob or "DEMO" in blob or "FIXTURE" in blob
    if table == "core_approval_decisions":
        if _p4_person(data.get("decided_by_person_id")):
            return True
        blob = _blob(data.get("reason"))
        return "P4-TEST" in blob
    if table == "core_audit_events":
        return _p4_person(data.get("actor_person_id"))
    return False


def record_class(table: str, row: dict[str, Any] | sqlite3.Row) -> str:
    return INVALID_TEST if is_invalid_or_test(table, row) else VALID


def _split(table: str, rows: list[sqlite3.Row]) -> dict[str, Any]:
    invalid_ids: list[str] = []
    valid_ids: list[str] = []
    id_col = {
        "core_evidence_records": "evidence_id",
        "core_governance_exceptions": "exception_id",
        "core_approval_decisions": "approval_decision_id",
        "core_audit_events": "audit_event_id",
    }[table]
    for row in rows:
        ident = str(row[id_col])
        if is_invalid_or_test(table, row):
            invalid_ids.append(ident)
        else:
            valid_ids.append(ident)
    return {
        "total": len(rows),
        "valid_operational": len(valid_ids),
        "invalid_test": len(invalid_ids),
        "valid_ids": valid_ids,
        "invalid_test_ids": invalid_ids,
    }


def summarize(conn: sqlite3.Connection) -> dict[str, Any]:
    """Counts for the three ledgers. Does not write."""
    evidence = conn.execute(
        """
        SELECT evidence_id, status, source_type, source_reference,
               invalidate_reason, submitted_by_person_id
        FROM core_evidence_records
        """
    ).fetchall()
    exceptions = conn.execute(
        """
        SELECT exception_id, status, reject_reason, control_reference,
               requested_by_person_id
        FROM core_governance_exceptions
        """
    ).fetchall()
    decisions = conn.execute(
        """
        SELECT approval_decision_id, decided_by_person_id, reason
        FROM core_approval_decisions
        """
    ).fetchall()
    return {
        "read": "READ",
        "evidence": _split("core_evidence_records", list(evidence)),
        "exceptions": _split("core_governance_exceptions", list(exceptions)),
        "approval_decisions": _split("core_approval_decisions", list(decisions)),
        "preserved_invalid_evidence": _EVIDENCE_ID,
        "third_exception": _THIRD_EXCEPTION,
        "deleted": False,
    }


def summarize_live() -> dict[str, Any]:
    uri = BETA_CATALOG.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return summarize(conn)
    except sqlite3.Error as exc:
        return {"read": "UNAVAILABLE", "why": type(exc).__name__}
    finally:
        conn.close()


def live_path() -> Path:
    return BETA_CATALOG
