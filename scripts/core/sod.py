#!/usr/bin/env python3
"""Wolf Core Segregation of Duties — Person-based independence constraints.

AUTHORISED ≠ PERMITTED TO PERFORM EVERY STEP.
Dual Approval ≠ SoD. Authority / Permission / Delegation / Policy Binding
cannot override SoD deny. Missing required participation evidence → FAIL CLOSED.
Client-supplied independence / forged participation claims are IGNORED.
Live SoD constraints = 0.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
TZ_UTC = timezone.utc

STATUSES = frozenset({"ACTIVE", "INACTIVE"})
RELATIONSHIPS = frozenset({"SAME_PERSON_FORBIDDEN"})
SOURCE_TYPES = frozenset({"SYSTEM", "TEST"})

# Known APPROVAL-family actions resolved from canonical tables
APPROVAL_REQUEST_ACTION = "approval.request"
APPROVAL_DECIDE_ACTION = "approval.decide"
PROCESS_APPROVAL = "APPROVAL"

HONESTY = {
    "segregation_of_duties": "BUILT",
    "live_sod_constraints": 0,
    "exception_override": "BUILT",
    "ai_sod": False,
}


class SodError(ValueError):
    """Fail-closed SoD error."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    import sys

    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise SodError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"sod refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"sod refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"sod refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_constraint_id() -> str:
    return f"SOD-{uuid.uuid4()}"


def mint_participation_id() -> str:
    return f"SODP-{uuid.uuid4()}"


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_UTC)
    return dt


def _effective(row: dict[str, Any], at: datetime) -> bool:
    start = _parse_iso(row.get("effective_from"))
    if start is None:
        return False
    if at < start:
        return False
    eto = row.get("effective_to")
    if eto:
        end = _parse_iso(str(eto))
        if end is None:
            return False
        if at >= end:
            return False
    return True


def _specificity_key(row: dict[str, Any]) -> tuple[int, int]:
    """Higher tuple wins. (scope_exact, constraint_version)."""
    scope_exact = 1 if row.get("scope_id") else 0
    return (scope_exact, int(row.get("constraint_version") or 0))


def _base_result(
    *,
    verified_person_id: str,
    entity_id: str,
    scope_id: str | None,
    process_family: str,
    proposed_action: str,
    subject_id: str,
) -> dict[str, Any]:
    return {
        "allowed": False,
        "result": "NOT_APPLICABLE",
        "reason_code": "sod_not_applicable",
        "verified_person_id": verified_person_id,
        "entity_id": entity_id,
        "scope_id": scope_id,
        "process_family": process_family,
        "proposed_action": proposed_action,
        "subject_id": subject_id,
        "matched_constraint_id": None,
        "matched_constraint_version": None,
        "prior_action": None,
        "prior_participants": [],
        "conflicting_person_id": None,
        "candidates": [],
        "evaluator": "core.sod.evaluate_sod",
        **HONESTY,
    }


def _audit_sod(
    *,
    action: str,
    result: str,
    evaluation: dict[str, Any],
    reason_code: str | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "sod",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": evaluation.get("entity_id"),
        "resource_type": "sod_constraint",
        "resource_id": evaluation.get("matched_constraint_id"),
        "reason_code": reason_code or evaluation.get("reason_code"),
        "correlation_id": identity.get("correlation_id") or _audit.mint_correlation_id(),
        "metadata": metadata
        or {
            "process_family": evaluation.get("process_family"),
            "proposed_action": evaluation.get("proposed_action"),
            "prior_action": evaluation.get("prior_action"),
            "subject_id": evaluation.get("subject_id"),
            "result": evaluation.get("result"),
            "constraint_id": evaluation.get("matched_constraint_id"),
            "constraint_version": evaluation.get("matched_constraint_version"),
            "prior_participants": evaluation.get("prior_participants"),
            "conflicting_person_id": evaluation.get("conflicting_person_id"),
        },
        "conn": conn,
        "commit": False,
    }
    if verified_person_id:
        kwargs["verified_person_id"] = verified_person_id
        kwargs["actor_person_id"] = verified_person_id
        kwargs["actor_auth_identity_id"] = identity.get("auth_identity_id")
        kwargs["identity_assurance"] = identity.get("identity_assurance")
    _audit.safe_record(**kwargs)


def get_sod_constraint(
    constraint_id: str,
    constraint_version: int | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    cid = (constraint_id or "").strip()
    if not cid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        if constraint_version is not None:
            row = c.execute(
                """
                SELECT * FROM core_sod_constraints
                WHERE constraint_id=? AND constraint_version=?
                """,
                (cid, int(constraint_version)),
            ).fetchone()
            return dict(row) if row else None
        row = c.execute(
            """
            SELECT * FROM core_sod_constraints
            WHERE constraint_id=?
            ORDER BY constraint_version DESC
            LIMIT 1
            """,
            (cid,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def _assert_manage_or_test_hook(
    *,
    verified_person_id: str | None,
    allow_test_write: bool,
    entity_id: str,
    conn: sqlite3.Connection,
) -> None:
    if allow_test_write:
        if not _under_test_process() and (os.environ.get("WOLF_TEST_MODE") or "").strip() != "1":
            raise SodError(
                "allow_test_write refused outside test mode",
                code="manage_denied",
                http_status=403,
            )
        return
    pid = (verified_person_id or "").strip()
    if not pid:
        raise SodError(
            "sod.constraint.manage denied (no verified person)",
            code="manage_denied",
            http_status=403,
        )
    ev = _rbac.evaluate(
        pid,
        "sod.constraint.manage",
        {"entity_id": entity_id},
        conn=conn,
    )
    if not ev.get("allowed"):
        raise SodError(
            "sod.constraint.manage denied",
            code="manage_denied",
            http_status=403,
        )


def insert_sod_constraint_for_test(
    *,
    entity_id: str,
    process_family: str,
    prior_action: str,
    proposed_action: str,
    constraint_id: str | None = None,
    constraint_version: int = 1,
    scope_id: str | None = None,
    relationship: str = "SAME_PERSON_FORBIDDEN",
    effective_from: str | None = None,
    effective_to: str | None = None,
    status: str = "ACTIVE",
    created_by_person_id: str | None = None,
    verified_person_id: str | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """TEST/manage insert. Defaults DENY without allow_test_write or manage permission."""
    eid = (entity_id or "").strip()
    if not eid:
        raise SodError("entity_id required", code="missing_entity")
    fam = (process_family or "").strip().upper()
    if not fam:
        raise SodError("process_family required", code="missing_process_family")
    prior = (prior_action or "").strip()
    proposed = (proposed_action or "").strip()
    if not prior or not proposed:
        raise SodError("prior_action and proposed_action required", code="missing_action")
    rel = (relationship or "").strip().upper()
    if rel not in RELATIONSHIPS:
        raise SodError(f"unsupported relationship: {relationship!r}", code="invalid_relationship")
    st = (status or "").strip().upper()
    if st not in STATUSES:
        raise SodError(f"invalid status: {status!r}", code="invalid_status")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_manage_or_test_hook(
            verified_person_id=verified_person_id,
            allow_test_write=allow_test_write,
            entity_id=eid,
            conn=c,
        )
        cid = (constraint_id or "").strip() or mint_constraint_id()
        ts = now_utc_iso()
        eff_from = (effective_from or "").strip() or ts
        c.execute(
            """
            INSERT INTO core_sod_constraints (
              constraint_id, constraint_version, entity_id, scope_id,
              process_family, prior_action, proposed_action, relationship,
              effective_from, effective_to, status,
              created_at, updated_at, created_by_person_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                int(constraint_version),
                eid,
                (scope_id or "").strip() or None,
                fam,
                prior,
                proposed,
                rel,
                eff_from,
                (effective_to or "").strip() or None,
                st,
                ts,
                ts,
                (created_by_person_id or verified_person_id or "").strip() or None,
            ),
        )
        if commit:
            c.commit()
        out = get_sod_constraint(cid, int(constraint_version), conn=c)
        assert out is not None
        return out
    finally:
        if own:
            c.close()


def insert_sod_participation_for_test(
    *,
    person_id: str,
    action: str,
    subject_id: str,
    entity_id: str,
    scope_id: str | None = None,
    source_type: str = "TEST",
    recorded_at: str | None = None,
    participation_id: str | None = None,
    verified_person_id: str | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """TEST/fixture participation row. Client independence claims never use this path."""
    pid = (person_id or "").strip()
    act = (action or "").strip()
    sid = (subject_id or "").strip()
    eid = (entity_id or "").strip()
    if not pid or not act or not sid or not eid:
        raise SodError(
            "person_id, action, subject_id, entity_id required",
            code="missing_participation_fields",
        )
    src = (source_type or "").strip().upper()
    if src not in SOURCE_TYPES:
        raise SodError(f"invalid source_type: {source_type!r}", code="invalid_source_type")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_manage_or_test_hook(
            verified_person_id=verified_person_id,
            allow_test_write=allow_test_write,
            entity_id=eid,
            conn=c,
        )
        ppid = (participation_id or "").strip() or mint_participation_id()
        ts = (recorded_at or "").strip() or now_utc_iso()
        c.execute(
            """
            INSERT INTO core_sod_participation (
              participation_id, person_id, action, subject_id,
              entity_id, scope_id, recorded_at, source_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ppid,
                pid,
                act,
                sid,
                eid,
                (scope_id or "").strip() or None,
                ts,
                src,
            ),
        )
        if commit:
            c.commit()
        row = c.execute(
            "SELECT * FROM core_sod_participation WHERE participation_id=?",
            (ppid,),
        ).fetchone()
        assert row is not None
        return dict(row)
    finally:
        if own:
            c.close()


def resolve_prior_participants(
    *,
    process_family: str,
    prior_action: str,
    subject_id: str,
    entity_id: str,
    conn: sqlite3.Connection,
) -> tuple[list[str] | None, str | None]:
    """Return (person_ids, error_code).

    None person_ids + error means evidence unavailable (fail closed).
    Empty list means resolved with no participants (rare; still not unavailable).
    """
    fam = (process_family or "").strip().upper()
    action = (prior_action or "").strip()
    sid = (subject_id or "").strip()
    eid = (entity_id or "").strip()
    if not sid:
        return None, "sod_evidence_unavailable"

    persons: list[str] = []

    if fam == PROCESS_APPROVAL and action == APPROVAL_REQUEST_ACTION:
        row = conn.execute(
            """
            SELECT requested_by_person_id, owning_entity_id
            FROM core_approval_requests
            WHERE approval_request_id=?
            """,
            (sid,),
        ).fetchone()
        if not row:
            return None, "sod_evidence_unavailable"
        if (row["owning_entity_id"] or "").strip() != eid:
            return None, "sod_evidence_unavailable"
        req_pid = (row["requested_by_person_id"] or "").strip()
        if not req_pid:
            return None, "sod_evidence_unavailable"
        persons.append(req_pid)
        return persons, None

    if fam == PROCESS_APPROVAL and action == APPROVAL_DECIDE_ACTION:
        row = conn.execute(
            """
            SELECT owning_entity_id FROM core_approval_requests
            WHERE approval_request_id=?
            """,
            (sid,),
        ).fetchone()
        if not row:
            return None, "sod_evidence_unavailable"
        if (row["owning_entity_id"] or "").strip() != eid:
            return None, "sod_evidence_unavailable"
        rows = conn.execute(
            """
            SELECT DISTINCT decided_by_person_id
            FROM core_approval_decisions
            WHERE approval_request_id=? AND decision='APPROVED'
            """,
            (sid,),
        ).fetchall()
        for r in rows:
            p = (r["decided_by_person_id"] or "").strip()
            if p:
                persons.append(p)
        return persons, None

    # EVIDENCE family: derive submitter from canonical evidence record
    if fam == "EVIDENCE" and action == "evidence.submit":
        tabs_ev = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "core_evidence_records" not in tabs_ev:
            return None, "sod_evidence_unavailable"
        row = conn.execute(
            """
            SELECT submitted_by_person_id, entity_id, status
            FROM core_evidence_records
            WHERE evidence_id=?
            """,
            (sid,),
        ).fetchone()
        if not row:
            return None, "sod_evidence_unavailable"
        if (row["entity_id"] or "").strip() != eid:
            return None, "sod_evidence_unavailable"
        submitter = (row["submitted_by_person_id"] or "").strip()
        if not submitter:
            return None, "sod_evidence_unavailable"
        persons.append(submitter)
        return persons, None

    # Generic / fixture ledger (SYSTEM|TEST rows written by trusted path only)
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "core_sod_participation" not in tabs:
        return None, "sod_evidence_unavailable"
    rows = conn.execute(
        """
        SELECT DISTINCT person_id FROM core_sod_participation
        WHERE subject_id=? AND action=? AND entity_id=?
          AND source_type IN ('SYSTEM', 'TEST')
        """,
        (sid, action, eid),
    ).fetchall()
    if not rows:
        # Required evidence missing for constrained evaluate → fail closed
        return None, "sod_evidence_unavailable"
    for r in rows:
        p = (r["person_id"] or "").strip()
        if p:
            persons.append(p)
    if not persons:
        return None, "sod_evidence_unavailable"
    return persons, None


def evaluate_sod(
    verified_person_id: str,
    entity_id: str,
    process_family: str,
    proposed_action: str,
    subject_id: str,
    *,
    scope_id: str | None = None,
    as_of: str | datetime | None = None,
    identity: dict[str, Any] | None = None,
    audit: bool = True,
    conn: sqlite3.Connection | None = None,
    # Explicitly ignored — client independence / forged claims never trusted
    requester_is_different: Any = None,
    forged_participation: Any = None,
    client_prior_participants: Any = None,
    **_ignored: Any,
) -> dict[str, Any]:
    """Fail-closed SoD evaluator. Person-based; AuthIdentity/Role/Delegation do not multiply.

    Returns explainable dict. Does not grant Permission or Authority.
    """
    # Silence unused client-claim parameters (must not affect outcome)
    _ = (requester_is_different, forged_participation, client_prior_participants)

    verified = (verified_person_id or "").strip()
    eid = (entity_id or "").strip()
    fam = (process_family or "").strip().upper()
    proposed = (proposed_action or "").strip()
    sid = (subject_id or "").strip()
    if not verified:
        raise SodError("verified_person_id required", code="missing_verified_person")
    if not eid:
        raise SodError("entity_id required", code="missing_entity")
    if not fam:
        raise SodError("process_family required", code="missing_process_family")
    if not proposed:
        raise SodError("proposed_action required", code="missing_proposed_action")
    if not sid:
        raise SodError("subject_id required", code="missing_subject")

    scope = (scope_id or "").strip() or None

    if isinstance(as_of, datetime):
        at_dt = as_of if as_of.tzinfo else as_of.replace(tzinfo=TZ_UTC)
    else:
        at_dt = _parse_iso(str(as_of)) if as_of else datetime.now(TZ_UTC)
        if at_dt is None:
            at_dt = datetime.now(TZ_UTC)

    out = _base_result(
        verified_person_id=verified,
        entity_id=eid,
        scope_id=scope,
        process_family=fam,
        proposed_action=proposed,
        subject_id=sid,
    )

    own = conn is None
    c = conn or db_connect()
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_sod_constraints" not in tabs:
            out["allowed"] = True
            out["result"] = "NOT_APPLICABLE"
            out["reason_code"] = "sod_not_applicable"
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="ALLOWED",
                    evaluation=out,
                    reason_code="sod_not_applicable",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        rows = c.execute(
            """
            SELECT * FROM core_sod_constraints
            WHERE entity_id=? AND process_family=? AND proposed_action=? AND status='ACTIVE'
            """,
            (eid, fam, proposed),
        ).fetchall()
        constraints = [dict(r) for r in rows]

        scoped: list[dict[str, Any]] = []
        for con in constraints:
            if not _effective(con, at_dt):
                continue
            con_scope = (con.get("scope_id") or "").strip() or None
            # Match: entity-wide (NULL) OR exact scope match
            if con_scope is not None and con_scope != scope:
                continue
            scoped.append(con)

        out["candidates"] = [
            {
                "constraint_id": x["constraint_id"],
                "constraint_version": x["constraint_version"],
                "scope_id": x.get("scope_id"),
                "prior_action": x.get("prior_action"),
                "relationship": x.get("relationship"),
            }
            for x in scoped
        ]

        if not scoped:
            out["allowed"] = True
            out["result"] = "NOT_APPLICABLE"
            out["reason_code"] = "sod_not_applicable"
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="ALLOWED",
                    evaluation=out,
                    reason_code="sod_not_applicable",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        # Collapse same constraint_id to highest version, then precedence by scope exactness
        by_id: dict[str, dict[str, Any]] = {}
        for con in scoped:
            cid = con["constraint_id"]
            prev = by_id.get(cid)
            if prev is None or int(con["constraint_version"]) > int(prev["constraint_version"]):
                by_id[cid] = con
        distinct = list(by_id.values())

        best_scope = max(1 if d.get("scope_id") else 0 for d in distinct)
        winners = [d for d in distinct if (1 if d.get("scope_id") else 0) == best_scope]

        if len(winners) > 1:
            out["allowed"] = False
            out["result"] = "CONSTRAINT_CONFLICT"
            out["reason_code"] = "sod_constraint_conflict"
            out["candidates"] = [
                {
                    "constraint_id": w["constraint_id"],
                    "constraint_version": w["constraint_version"],
                    "scope_id": w.get("scope_id"),
                    "prior_action": w.get("prior_action"),
                }
                for w in winners
            ]
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="sod_constraint_conflict",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        winner = winners[0]
        out["matched_constraint_id"] = winner["constraint_id"]
        out["matched_constraint_version"] = int(winner["constraint_version"])
        out["prior_action"] = winner.get("prior_action")
        rel = (winner.get("relationship") or "").strip().upper()
        if rel not in RELATIONSHIPS:
            out["allowed"] = False
            out["result"] = "CONSTRAINT_CONFLICT"
            out["reason_code"] = "sod_constraint_conflict"
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="sod_constraint_conflict",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        participants, err = resolve_prior_participants(
            process_family=fam,
            prior_action=str(winner.get("prior_action") or ""),
            subject_id=sid,
            entity_id=eid,
            conn=c,
        )
        if err or participants is None:
            out["allowed"] = False
            out["result"] = "EVIDENCE_UNAVAILABLE"
            out["reason_code"] = "sod_evidence_unavailable"
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="sod_evidence_unavailable",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        out["prior_participants"] = list(participants)
        if verified in participants:
            out["allowed"] = False
            out["result"] = "CONFLICT"
            out["reason_code"] = "sod_same_person_conflict"
            out["conflicting_person_id"] = verified
            if audit:
                _audit_sod(
                    action="sod.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="sod_same_person_conflict",
                    verified_person_id=verified,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        out["allowed"] = True
        out["result"] = "OK"
        out["reason_code"] = "sod_ok"
        if audit:
            _audit_sod(
                action="sod.evaluated",
                result="ALLOWED",
                evaluation=out,
                reason_code="sod_ok",
                verified_person_id=verified,
                identity=identity,
                conn=c,
            )
            if own:
                c.commit()
        return out
    finally:
        if own:
            c.close()
