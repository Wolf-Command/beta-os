#!/usr/bin/env python3
"""Pack 10 — the approval and evidence gate. Read it. Do not invent a limit.

org_authority_limits is empty. A material amount therefore fails closed.
The one live request stays the Uma GENERAL row. Fixture decision rows whose
request is gone are not treated as authority.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core import amg_finance_screens as _finance
from core import authority as _authority
from core import evidence as _evidence
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_REQUEST = "APR-292cc664-f235-4bef-93eb-78a6abbf43bd"
RECEIPT_EVIDENCE = "EVD-372162c1-d0ac-42a6-b5f3-5959c11f4621"
PETTY_EVIDENCE = "EVD-9498bb75-294c-4924-b30b-8cef0cab5351"
PUBLISH_REQUIREMENT = "EVR-HABITAT-CONTENT-PUBLISH"

PEOPLE = (
    "PERS-MATT",
    "PERS-DEVI",
    "PERS-ZAYEN",
    "PERS-AMANDA",
    "PERS-ZENITALFATHAN",
)
ENTITIES = ("ENT-BZG", "ENT-AMG", "ENT-GGV")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _counts(conn: sqlite3.Connection) -> dict[str, int | None]:
    names = (
        "org_authority_limits",
        "core_approval_requests",
        "core_approval_decisions",
        "core_delegations",
        "core_evidence_requirements",
    )
    out: dict[str, int | None] = {}
    for name in names:
        try:
            out[name] = int(conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
        except sqlite3.Error:
            out[name] = None
    return out


def _live_request(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT approval_request_id, request_type, owning_entity_id, requested_by_person_id,
               required_permission_code, material_amount, currency, status, required_decision_count
        FROM core_approval_requests
        WHERE approval_request_id=?
        """,
        (LIVE_REQUEST,),
    ).fetchone()
    if row is None:
        return {
            "present": False,
            "approval_request_id": LIVE_REQUEST,
            "state": "UNKNOWN",
            "why": "The Uma request row was not in core_approval_requests. No replacement was created.",
        }
    decision = conn.execute(
        """
        SELECT approval_decision_id, decision, decided_by_person_id
        FROM core_approval_decisions
        WHERE approval_request_id=?
        """,
        (LIVE_REQUEST,),
    ).fetchall()
    deciders = [item["decided_by_person_id"] for item in decision]
    return {
        "present": True,
        "state": "PARTIAL",
        "approval_request_id": row["approval_request_id"],
        "request_type": row["request_type"],
        "owning_entity_id": row["owning_entity_id"],
        "requested_by_person_id": row["requested_by_person_id"],
        "required_permission_code": row["required_permission_code"],
        "material_amount": row["material_amount"],
        "currency": row["currency"],
        "status": row["status"],
        "required_decision_count": row["required_decision_count"],
        "decisions": [dict(item) for item in decision],
        "decided_by_person_id": deciders[0] if len(deciders) == 1 else None,
        "self_approved": bool(deciders) and all(person == row["requested_by_person_id"] for person in deciders),
        "why": "One GENERAL request. It is not an amount limit and not a new approval.",
    }


def _orphan_decisions(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT d.approval_decision_id, d.approval_request_id, d.decided_by_person_id
        FROM core_approval_decisions d
        LEFT JOIN core_approval_requests r ON r.approval_request_id = d.approval_request_id
        WHERE r.approval_request_id IS NULL
        """
    ).fetchall()
    people = sorted({row["decided_by_person_id"] for row in rows})
    known = set()
    if people:
        found = conn.execute(
            f"SELECT person_id FROM org_persons WHERE person_id IN ({','.join('?' * len(people))})",
            people,
        ).fetchall()
        known = {row["person_id"] for row in found}
    return {
        "count": len(rows),
        "state": "UNKNOWN",
        "decided_by_person_ids": people,
        "people_in_org_persons": sorted(known),
        "treated_as_authority": False,
        "why": "Decision rows whose request is gone are leftover fixtures. They are not who-can-approve.",
    }


def _decide_matrix(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for person_id in PEOPLE:
        allowed = []
        denied = []
        for entity_id in ENTITIES:
            ev = _rbac.evaluate(person_id, "approval.decide", {"entity_id": entity_id}, conn=conn)
            seat = {"entity_id": entity_id, "reason": ev.get("reason")}
            if ev.get("allowed"):
                allowed.append(seat)
            else:
                denied.append(seat)
        rows.append({"person_id": person_id, "allowed": allowed, "denied": denied})
    return rows


def _amount_gate(conn: sqlite3.Connection) -> dict[str, Any]:
    petty = conn.execute(
        """
        SELECT movement_id, amount, currency
        FROM bzg_ops_petty_movements
        WHERE movement_id='PETTY-UMA-2321496C6D'
        """
    ).fetchone()
    amount = petty["amount"] if petty else None
    currency = petty["currency"] if petty else None
    auth = _authority.within_authority(
        "PERS-MATT",
        "work.complete",
        {"entity_id": "ENT-BZG"},
        {"amount": amount, "currency": currency},
        conn=conn,
    )
    return {
        "allowed": bool(auth.get("allowed")),
        "reason": auth.get("reason"),
        "detail": auth.get("detail"),
        "matched_limit": auth.get("matched_limit"),
        "threshold_invented": False,
        "probe_amount": amount,
        "probe_currency": currency,
        "probe_source": "PETTY-UMA-2321496C6D" if petty else None,
        "why": "No matching authority limit. The petty amount was not turned into a limit.",
    }


def _evidence_read(conn: sqlite3.Connection) -> dict[str, Any]:
    closes = [
        dict(row)
        for row in conn.execute(
            """
            SELECT close_id, business_date, state, declared_cash_evidence_id
            FROM venue_daily_closes
            WHERE venue_brand_id='BZG-UMA'
            ORDER BY business_date
            """
        )
    ]
    receipt = conn.execute(
        "SELECT evidence_id, evidence_type, status, governed_object_id FROM core_evidence_records WHERE evidence_id=?",
        (RECEIPT_EVIDENCE,),
    ).fetchone()
    petty = conn.execute(
        "SELECT evidence_id, evidence_type, status, governed_object_id FROM core_evidence_records WHERE evidence_id=?",
        (PETTY_EVIDENCE,),
    ).fetchone()
    requirement = conn.execute(
        """
        SELECT requirement_id, entity_id, action_type, evidence_type, min_count, status
        FROM core_evidence_requirements
        WHERE requirement_id=?
        """,
        (PUBLISH_REQUIREMENT,),
    ).fetchone()
    publish = _evidence.evaluate_evidence_requirements(
        "ENT-GGV",
        "HABITAT.CONTENT.PUBLISH",
        scope_id="SCOPE-GGV-CONTENT",
        request_type="GENERAL",
        governed_object_type="content_card",
        governed_object_id="PACK10-NO-CARD",
        verified_person_id="PERS-MATT",
        audit=False,
        conn=conn,
    )
    cash_attached = any(row.get("declared_cash_evidence_id") for row in closes)
    return {
        "receipt": dict(receipt) if receipt else None,
        "petty_photo": dict(petty) if petty else None,
        "declared_cash_closes": closes,
        "declared_cash_attached": cash_attached,
        "declared_cash_state": "ATTACHED" if cash_attached else "FAIL_CLOSED",
        "publish_requirement": dict(requirement) if requirement else None,
        "publish_gate": {
            "allowed": publish.get("allowed"),
            "reason_code": publish.get("reason_code"),
            "missing": publish.get("missing"),
            "publish_executed": False,
        },
        "why": "Receipt and petty photo rows exist. Declared cash is null. The publish rule denies a missing draft. Nothing was attached by this pack.",
    }


def _finance_sod() -> dict[str, Any]:
    try:
        data = _finance.load_screens()
    except Exception as exc:
        return {"state": "UNKNOWN", "why": f"Books read failed: {type(exc).__name__}"}
    sod = data.get("sod") or {}
    return {
        "state": "PARTIAL" if sod.get("segregated") else "UNKNOWN",
        "segregated": sod.get("segregated"),
        "segregated_journal": sod.get("segregated_journal"),
        "preparer_person_id": sod.get("preparer_person_id"),
        "approved_by": sod.get("approved_by"),
        "self_journal": sod.get("self_journal"),
        "self_journal_approved_by": sod.get("self_journal_approved_by"),
        "seats": {
            "PERS-ZAYEN": _finance.seat_matrix(_finance.APPROVER),
            "PERS-AMANDA": _finance.seat_matrix(_finance.AMANDA),
        },
        "xero_write": False,
        "why": "Pack 5 books read. A self-approved journal is not posted. This is not a new approval row.",
    }


def load_gate() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {
            "ok": False,
            "pack": "PACK-10",
            "staff_ready": False,
            "human_proven": False,
            "error": "catalog_missing",
            "authority_limit_invented": False,
        }
    conn = _ro(CATALOG_DB)
    try:
        counts = _counts(conn)
        request = _live_request(conn)
        orphans = _orphan_decisions(conn)
        matrix = _decide_matrix(conn)
        amount = _amount_gate(conn)
        evidence = _evidence_read(conn)
    finally:
        conn.close()
    limit_count = counts.get("org_authority_limits")
    return {
        "ok": True,
        "pack": "PACK-10",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "fake_approval": False,
        "authority_limit_invented": False,
        "authority_limits": {
            "count": limit_count,
            "active_threshold": None,
            "state": "FAIL_CLOSED" if limit_count == 0 else "UNKNOWN",
            "why": "The limit table was read. No threshold above zero was written.",
        },
        "counts": counts,
        "live_request": request,
        "orphan_decisions": orphans,
        "who_can_decide": matrix,
        "amount_gate": amount,
        "evidence": evidence,
        "finance_sod": _finance_sod(),
        "delegations": counts.get("core_delegations"),
        "human_residual": {
            "state": "NOT_HUMAN_PROVEN",
            "staff_must_click": True,
            "why": "A named person still has to click. This read did not click.",
        },
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "fake_approval": False,
        "authority_limit_invented": False,
        "message": "The approval gate does not create a request, a limit, or an evidence row.",
    }
