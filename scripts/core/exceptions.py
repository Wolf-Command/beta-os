#!/usr/bin/env python3
"""Wolf Core Exception / Override Governance — EXCEPTION ≠ COMPLIANCE.

Normal control failure is preserved. Exception is a separate authorised path.
Never rewrite FAIL → PASS. Client override / force / skip flags are IGNORED.
Authorise/revoke: verified Person id == PERS-MATT only. Delegation ignored.
Live exceptions = 0.
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

PERS_MATT = "PERS-MATT"

STATUSES = frozenset(
    {"REQUESTED", "AUTHORISED", "CONSUMED", "REJECTED", "REVOKED", "EXPIRED"}
)
CONTROL_TYPES = frozenset(
    {
        "EVIDENCE_REQUIREMENT",
        "SOD_CONSTRAINT",
        "APPROVAL_REQUIREMENT",
        "AUTHORITY_LIMIT",
    }
)

# Never overridable via this primitive (hard), regardless of registry rows.
NON_EXCEPTIONABLE_CONTROL_TYPES = frozenset(
    {
        "AUTHENTICATION",
        "ENTITY_ISOLATION",
        "AUDIT_RECORDING",
        "ATTRIBUTION_IMMUTABILITY",
        "PRODUCTION_SACRED",
        "CLIENT_OVERRIDE_FLAG",
        "NON_EXCEPTIONABLE",
    }
)

REJECTED_REASONS = frozenset(
    {"n/a", "na", "because", "test", "asdf", "override", "force", "skip"}
)
REASON_MIN_LEN = 12

HONESTY = {
    "exception_override": "BUILT",
    "live_exceptions": 0,
    "exception_is_not_compliance": True,
    "delegation_cannot_authorise": True,
    "ai_exception_authoriser": False,
}


class ExceptionError(ValueError):
    """Fail-closed exception governance error."""

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
        raise ExceptionError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"exceptions refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"exceptions refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"exceptions refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_exception_id() -> str:
    return f"GEX-{uuid.uuid4()}"


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


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


def validate_reason(reason: str | None) -> str:
    stripped = (reason or "").strip()
    if len(stripped) < REASON_MIN_LEN:
        raise ExceptionError(
            f"reason must be at least {REASON_MIN_LEN} meaningful characters",
            code="invalid_reason",
        )
    if stripped.lower() in REJECTED_REASONS:
        raise ExceptionError(
            "reason is a rejected placeholder",
            code="invalid_reason",
        )
    return stripped


def _assert_matt_person(verified_person_id: str) -> str:
    """Hard Matt Person gate. ROLE / email / delegation do not substitute."""
    verified = (verified_person_id or "").strip()
    if verified != PERS_MATT:
        raise ExceptionError(
            "only PERS-MATT may authorise/revoke exceptions",
            code="matt_gate_denied",
            http_status=403,
        )
    return verified


def _assert_permission(
    *,
    verified_person_id: str,
    permission_code: str,
    entity_id: str,
    conn: sqlite3.Connection,
    allow_test_write: bool = False,
) -> None:
    if allow_test_write:
        if not _under_test_process() and (os.environ.get("WOLF_TEST_MODE") or "").strip() != "1":
            raise ExceptionError(
                "allow_test_write refused outside test mode",
                code="permission_denied",
                http_status=403,
            )
        return
    pid = (verified_person_id or "").strip()
    if not pid:
        raise ExceptionError(
            f"{permission_code} denied (no verified person)",
            code="permission_denied",
            http_status=403,
        )
    ev = _rbac.evaluate(
        pid,
        permission_code,
        {"entity_id": entity_id},
        conn=conn,
    )
    if not ev.get("allowed"):
        raise ExceptionError(
            f"{permission_code} denied",
            code="permission_denied",
            http_status=403,
        )


def _audit_exception(
    *,
    action: str,
    result: str,
    exception: dict[str, Any] | None = None,
    evaluation: dict[str, Any] | None = None,
    reason_code: str | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    exception = exception or {}
    evaluation = evaluation or {}
    meta = metadata or {
        "exception_id": exception.get("exception_id") or evaluation.get("exception_id"),
        "control_type": exception.get("control_type") or evaluation.get("control_type"),
        "control_reference": exception.get("control_reference")
        or evaluation.get("control_reference"),
        "governed_object_type": exception.get("governed_object_type")
        or evaluation.get("governed_object_type"),
        "governed_object_id": exception.get("governed_object_id")
        or evaluation.get("governed_object_id"),
        "status": exception.get("status") or evaluation.get("result"),
        "reason": reason_code or evaluation.get("reason_code"),
        "normal_result": evaluation.get("normal_result"),
        "normal_reason_code": evaluation.get("normal_reason_code"),
    }
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "exceptions",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": exception.get("entity_id") or evaluation.get("entity_id"),
        "scope_id": exception.get("scope_id") or evaluation.get("scope_id"),
        "resource_type": "governance_exception",
        "resource_id": exception.get("exception_id") or evaluation.get("exception_id"),
        "reason_code": reason_code or evaluation.get("reason_code"),
        "correlation_id": identity.get("correlation_id") or exception.get("correlation_id"),
        "identity_assurance": identity.get("identity_assurance"),
        "actor_assignment_id": identity.get("assignment_id"),
        "actor_auth_identity_id": identity.get("auth_identity_id"),
        "verified_person_id": verified_person_id,
        "metadata": {k: v for k, v in meta.items() if v is not None},
        "conn": conn,
        "commit": False,
    }
    if verified_person_id:
        kwargs["actor_person_id"] = verified_person_id
    _audit.record_event(**kwargs)


def get_exception(
    exception_id: str, *, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    eid = (exception_id or "").strip()
    if not eid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                "SELECT * FROM core_governance_exceptions WHERE exception_id=?",
                (eid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def get_exceptionable_control(
    control_type: str,
    control_reference: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    ct = (control_type or "").strip().upper()
    cr = (control_reference or "").strip()
    if not ct or not cr:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT * FROM core_exceptionable_controls
                WHERE control_type=? AND control_reference=? AND status='ACTIVE'
                """,
                (ct, cr),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def insert_exceptionable_control_for_test(
    *,
    control_type: str,
    control_reference: str,
    exceptionable: int = 1,
    required_for_authorise: int = 0,
    allow_test_write: bool = False,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """TEST/manage insert for exceptionable registry. Defaults DENY without hook."""
    if not allow_test_write:
        raise ExceptionError(
            "exceptionable control insert denied",
            code="manage_denied",
            http_status=403,
        )
    if not _under_test_process() and (os.environ.get("WOLF_TEST_MODE") or "").strip() != "1":
        raise ExceptionError(
            "allow_test_write refused outside test mode",
            code="permission_denied",
            http_status=403,
        )
    ct = (control_type or "").strip().upper()
    cr = (control_reference or "").strip()
    if ct in NON_EXCEPTIONABLE_CONTROL_TYPES and int(exceptionable) == 1:
        raise ExceptionError(
            f"control_type {ct} is NON_EXCEPTIONABLE",
            code="non_exceptionable",
            http_status=403,
        )
    if not ct or not cr:
        raise ExceptionError("control_type and control_reference required")
    ts = now_utc_iso()
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        c.execute(
            """
            INSERT INTO core_exceptionable_controls (
              control_type, control_reference, exceptionable, required_for_authorise,
              status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(control_type, control_reference) DO UPDATE SET
              exceptionable=excluded.exceptionable,
              required_for_authorise=excluded.required_for_authorise,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (ct, cr, int(exceptionable), int(required_for_authorise), ts, ts),
        )
        if commit:
            c.commit()
        out = get_exceptionable_control(ct, cr, conn=c)
        assert out is not None
        _ = verified_person_id
        return out
    finally:
        if own:
            c.close()


def _control_is_exceptionable(
    control_type: str, control_reference: str, *, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    ct = (control_type or "").strip().upper()
    if ct in NON_EXCEPTIONABLE_CONTROL_TYPES:
        return False, None
    row = get_exceptionable_control(ct, control_reference, conn=conn)
    if not row:
        return False, None
    return bool(int(row.get("exceptionable") or 0)), row


def _evidence_active(
    evidence_id: str, *, entity_id: str, conn: sqlite3.Connection
) -> bool:
    eid = (evidence_id or "").strip()
    if not eid:
        return False
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "core_evidence_records" not in tabs:
        return False
    row = conn.execute(
        """
        SELECT evidence_id, entity_id, status FROM core_evidence_records
        WHERE evidence_id=?
        """,
        (eid,),
    ).fetchone()
    if not row:
        return False
    if (row["entity_id"] or "").strip() != (entity_id or "").strip():
        return False
    return (row["status"] or "").strip().upper() == "ACTIVE"


def request_exception(
    *,
    entity_id: str,
    governed_object_type: str,
    governed_object_id: str,
    control_type: str,
    control_reference: str,
    reason: str,
    verified_person_id: str,
    scope_id: str | None = None,
    evidence_id: str | None = None,
    effective_from: str | None = None,
    expires_at: str | None = None,
    usage_limit: int = 1,
    identity: dict[str, Any] | None = None,
    # Client override claims — IGNORED
    force: Any = None,
    override: Any = None,
    skip_control: Any = None,
    client_exception_id: Any = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Request an exception. Does NOT bypass any control. Status=REQUESTED."""
    _ = (force, override, skip_control, client_exception_id)

    verified = (verified_person_id or "").strip()
    if not verified:
        raise ExceptionError("verified_person_id required", code="missing_verified_person")
    eid = (entity_id or "").strip()
    got = (governed_object_type or "").strip()
    goi = (governed_object_id or "").strip()
    ct = (control_type or "").strip().upper()
    cr = (control_reference or "").strip()
    if not eid or not got or not goi or not ct or not cr:
        raise ExceptionError(
            "entity_id, governed object, and control fields required",
            code="missing_fields",
        )
    if ct in NON_EXCEPTIONABLE_CONTROL_TYPES:
        raise ExceptionError(
            f"control_type {ct} is NON_EXCEPTIONABLE",
            code="non_exceptionable",
            http_status=403,
        )
    if ct not in CONTROL_TYPES:
        raise ExceptionError(f"unsupported control_type: {ct}", code="invalid_control_type")
    reason_ok = validate_reason(reason)
    try:
        ul = int(usage_limit)
    except (TypeError, ValueError) as e:
        raise ExceptionError("usage_limit must be >= 1", code="invalid_usage_limit") from e
    if ul < 1:
        raise ExceptionError("usage_limit must be >= 1", code="invalid_usage_limit")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_permission(
            verified_person_id=verified,
            permission_code="governance.exception.request",
            entity_id=eid,
            conn=c,
            allow_test_write=allow_test_write,
        )
        ok_exc, _ctl = _control_is_exceptionable(ct, cr, conn=c)
        if not ok_exc:
            raise ExceptionError(
                "control is not exceptionable (registry missing or exceptionable=0)",
                code="not_exceptionable",
                http_status=403,
            )

        evid = (evidence_id or "").strip() or None
        if evid and not _evidence_active(evid, entity_id=eid, conn=c):
            raise ExceptionError(
                "evidence_id must reference ACTIVE evidence in same Entity",
                code="invalid_evidence",
                http_status=400,
            )

        ts = now_utc_iso()
        eff = (effective_from or "").strip() or ts
        if _parse_iso(eff) is None:
            raise ExceptionError("invalid effective_from", code="invalid_effective_from")
        exp = (expires_at or "").strip() or None
        if exp and _parse_iso(exp) is None:
            raise ExceptionError("invalid expires_at", code="invalid_expires_at")

        xid = mint_exception_id()
        corr = (identity or {}).get("correlation_id") or _audit.mint_correlation_id()
        c.execute(
            """
            INSERT INTO core_governance_exceptions (
              exception_id, entity_id, scope_id, governed_object_type, governed_object_id,
              control_type, control_reference, requested_by_person_id,
              authorised_by_person_id, reason, evidence_id, effective_from, expires_at,
              status, usage_limit, used_count, created_at, authorised_at, rejected_at,
              revoked_at, consumed_at, correlation_id, revoke_reason, reject_reason
            ) VALUES (
              ?, ?, ?, ?, ?,
              ?, ?, ?,
              NULL, ?, ?, ?, ?,
              'REQUESTED', ?, 0, ?, NULL, NULL,
              NULL, NULL, ?, NULL, NULL
            )
            """,
            (
                xid,
                eid,
                (scope_id or "").strip() or None,
                got,
                goi,
                ct,
                cr,
                verified,
                reason_ok,
                evid,
                eff,
                exp,
                ul,
                ts,
                corr,
            ),
        )
        out = get_exception(xid, conn=c)
        assert out is not None
        _audit_exception(
            action="exception.requested",
            result="SUCCEEDED",
            exception=out,
            reason_code="requested",
            verified_person_id=verified,
            identity=identity,
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(out)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def authorise_exception(
    exception_id: str,
    *,
    verified_person_id: str,
    evidence_id: str | None = None,
    identity: dict[str, Any] | None = None,
    # Delegation / client claims — IGNORED for authorise (Matt Person gate only)
    acting_as_matt: Any = None,
    delegation_id: Any = None,
    delegated_from: Any = None,
    force: Any = None,
    override: Any = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Authorise REQUESTED → AUTHORISED. Matt Person only. Delegation ignored."""
    _ = (acting_as_matt, delegation_id, delegated_from, force, override)

    verified = _assert_matt_person(verified_person_id)
    xid = (exception_id or "").strip()
    if not xid:
        raise ExceptionError("exception_id required", code="missing_exception_id")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_exception(xid, conn=c)
        if not row:
            raise ExceptionError("exception not found", code="not_found", http_status=404)
        if row["status"] != "REQUESTED":
            raise ExceptionError(
                f"cannot authorise status={row['status']}",
                code="invalid_status",
                http_status=409,
            )

        _assert_permission(
            verified_person_id=verified,
            permission_code="governance.exception.authorise",
            entity_id=row["entity_id"],
            conn=c,
            allow_test_write=False,
        )

        ok_exc, ctl = _control_is_exceptionable(
            row["control_type"], row["control_reference"], conn=c
        )
        if not ok_exc:
            raise ExceptionError(
                "control is not exceptionable",
                code="not_exceptionable",
                http_status=403,
            )

        evid = (evidence_id or "").strip() or (row.get("evidence_id") or "").strip() or None
        require_ev = bool(int((ctl or {}).get("required_for_authorise") or 0))
        if require_ev:
            if not evid or not _evidence_active(evid, entity_id=row["entity_id"], conn=c):
                raise ExceptionError(
                    "ACTIVE evidence_id required to authorise this control",
                    code="evidence_required_for_authorise",
                    http_status=403,
                )
        elif evid and not _evidence_active(evid, entity_id=row["entity_id"], conn=c):
            raise ExceptionError(
                "evidence_id must reference ACTIVE evidence in same Entity",
                code="invalid_evidence",
            )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_governance_exceptions
            SET status='AUTHORISED',
                authorised_by_person_id=?,
                authorised_at=?,
                evidence_id=COALESCE(?, evidence_id)
            WHERE exception_id=? AND status='REQUESTED'
            """,
            (verified, ts, evid, xid),
        )
        if c.total_changes != 1:
            raise ExceptionError(
                "concurrent authorise failed",
                code="concurrent_update",
                http_status=409,
            )
        out = get_exception(xid, conn=c)
        assert out is not None
        _audit_exception(
            action="exception.authorised",
            result="SUCCEEDED",
            exception=out,
            reason_code="authorised",
            verified_person_id=verified,
            identity=identity,
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(out)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def reject_exception(
    exception_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    delegation_id: Any = None,
    force: Any = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Reject REQUESTED → REJECTED. Matt Person only."""
    _ = (delegation_id, force)
    verified = _assert_matt_person(verified_person_id)
    xid = (exception_id or "").strip()
    if not xid:
        raise ExceptionError("exception_id required", code="missing_exception_id")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_exception(xid, conn=c)
        if not row:
            raise ExceptionError("exception not found", code="not_found", http_status=404)
        if row["status"] != "REQUESTED":
            raise ExceptionError(
                f"cannot reject status={row['status']}",
                code="invalid_status",
                http_status=409,
            )
        _assert_permission(
            verified_person_id=verified,
            permission_code="governance.exception.revoke",
            entity_id=row["entity_id"],
            conn=c,
        )
        ts = now_utc_iso()
        reject_reason = (reason or "").strip() or None
        c.execute(
            """
            UPDATE core_governance_exceptions
            SET status='REJECTED', rejected_at=?, reject_reason=?
            WHERE exception_id=? AND status='REQUESTED'
            """,
            (ts, reject_reason, xid),
        )
        if c.total_changes != 1:
            raise ExceptionError(
                "concurrent reject failed",
                code="concurrent_update",
                http_status=409,
            )
        out = get_exception(xid, conn=c)
        assert out is not None
        _audit_exception(
            action="exception.rejected",
            result="SUCCEEDED",
            exception=out,
            reason_code="rejected",
            verified_person_id=verified,
            identity=identity,
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(out)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def revoke_exception(
    exception_id: str,
    *,
    verified_person_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    delegation_id: Any = None,
    force: Any = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Revoke AUTHORISED → REVOKED. Matt Person only. Does not erase history."""
    _ = (delegation_id, force)
    verified = _assert_matt_person(verified_person_id)
    xid = (exception_id or "").strip()
    if not xid:
        raise ExceptionError("exception_id required", code="missing_exception_id")
    reason_ok = validate_reason(reason)

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_exception(xid, conn=c)
        if not row:
            raise ExceptionError("exception not found", code="not_found", http_status=404)
        if row["status"] != "AUTHORISED":
            raise ExceptionError(
                f"cannot revoke status={row['status']}",
                code="invalid_status",
                http_status=409,
            )
        _assert_permission(
            verified_person_id=verified,
            permission_code="governance.exception.revoke",
            entity_id=row["entity_id"],
            conn=c,
        )
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_governance_exceptions
            SET status='REVOKED', revoked_at=?, revoke_reason=?
            WHERE exception_id=? AND status='AUTHORISED'
            """,
            (ts, reason_ok, xid),
        )
        if c.total_changes != 1:
            raise ExceptionError(
                "concurrent revoke failed",
                code="concurrent_update",
                http_status=409,
            )
        out = get_exception(xid, conn=c)
        assert out is not None
        _audit_exception(
            action="exception.revoked",
            result="SUCCEEDED",
            exception=out,
            reason_code="revoked",
            verified_person_id=verified,
            identity=identity,
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(out)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def evaluate_exception_for_control(
    *,
    entity_id: str,
    control_type: str,
    control_reference: str,
    governed_object_type: str,
    governed_object_id: str,
    scope_id: str | None = None,
    as_of: str | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    audit: bool = False,
    # Client override claims — IGNORED
    force: Any = None,
    override: Any = None,
    skip_control: Any = None,
    client_exception_authorised: Any = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Find a matching AUTHORISED exception. Does not consume. Client flags ignored."""
    _ = (force, override, skip_control, client_exception_authorised)

    eid = (entity_id or "").strip()
    ct = (control_type or "").strip().upper()
    cr = (control_reference or "").strip()
    got = (governed_object_type or "").strip()
    goi = (governed_object_id or "").strip()
    sc = (scope_id or "").strip() or None

    out: dict[str, Any] = {
        "allowed": False,
        "result": "DENIED",
        "reason_code": "no_authorised_exception",
        "entity_id": eid,
        "scope_id": sc,
        "control_type": ct,
        "control_reference": cr,
        "governed_object_type": got,
        "governed_object_id": goi,
        "exception_id": None,
        "evaluator": "core.exceptions.evaluate_exception_for_control",
        **HONESTY,
    }

    if not eid or not ct or not cr or not got or not goi:
        out["reason_code"] = "missing_evaluate_fields"
        return out

    if ct in NON_EXCEPTIONABLE_CONTROL_TYPES:
        out["reason_code"] = "non_exceptionable"
        return out

    at = _parse_iso(as_of) or datetime.now(TZ_UTC)

    own = conn is None
    c = conn or db_connect()
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_governance_exceptions" not in tabs:
            return out

        ok_exc, _ctl = _control_is_exceptionable(ct, cr, conn=c)
        if not ok_exc:
            out["reason_code"] = "not_exceptionable"
            return out

        rows = c.execute(
            """
            SELECT * FROM core_governance_exceptions
            WHERE entity_id=? AND control_type=? AND control_reference=?
              AND governed_object_type=? AND governed_object_id=?
              AND status='AUTHORISED'
              AND used_count < usage_limit
            ORDER BY created_at ASC
            """,
            (eid, ct, cr, got, goi),
        ).fetchall()

        match = None
        for r in rows:
            d = dict(r)
            row_scope = (d.get("scope_id") or "").strip() or None
            if row_scope is not None and row_scope != sc:
                continue
            eff = _parse_iso(d.get("effective_from"))
            if eff and at < eff:
                continue
            exp = _parse_iso(d.get("expires_at"))
            if exp and at >= exp:
                # Soft-mark expired if past
                continue
            match = d
            break

        if not match:
            if audit:
                _audit_exception(
                    action="exception.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="no_authorised_exception",
                    verified_person_id=verified_person_id,
                    identity=identity,
                    conn=c,
                )
            return out

        out["allowed"] = True
        out["result"] = "AUTHORISED_EXCEPTION"
        out["reason_code"] = "exception_authorised"
        out["exception_id"] = match["exception_id"]
        out["exception"] = {
            "exception_id": match["exception_id"],
            "usage_limit": match["usage_limit"],
            "used_count": match["used_count"],
            "control_type": match["control_type"],
            "control_reference": match["control_reference"],
        }
        if audit:
            _audit_exception(
                action="exception.evaluated",
                result="ALLOWED",
                evaluation=out,
                exception=match,
                reason_code="exception_authorised",
                verified_person_id=verified_person_id,
                identity=identity,
                conn=c,
            )
        return out
    finally:
        if own:
            c.close()


def consume_exception(
    exception_id: str,
    *,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Atomic consume: used_count+1; CONSUMED when used_count >= usage_limit."""
    xid = (exception_id or "").strip()
    if not xid:
        raise ExceptionError("exception_id required", code="missing_exception_id")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ts = now_utc_iso()
        cur = c.execute(
            """
            UPDATE core_governance_exceptions
            SET used_count = used_count + 1,
                status = CASE
                  WHEN used_count + 1 >= usage_limit THEN 'CONSUMED'
                  ELSE status
                END,
                consumed_at = CASE
                  WHEN used_count + 1 >= usage_limit THEN ?
                  ELSE consumed_at
                END
            WHERE exception_id=?
              AND status='AUTHORISED'
              AND used_count < usage_limit
            """,
            (ts, xid),
        )
        if cur.rowcount != 1:
            raise ExceptionError(
                "exception not consumable (missing, not AUTHORISED, or exhausted)",
                code="consume_failed",
                http_status=409,
            )
        out = get_exception(xid, conn=c)
        assert out is not None
        _audit_exception(
            action="exception.consumed",
            result="SUCCEEDED",
            exception=out,
            reason_code="consumed" if out["status"] == "CONSUMED" else "usage_incremented",
            verified_person_id=verified_person_id,
            identity=identity,
            metadata={
                "exception_id": out["exception_id"],
                "control_type": out["control_type"],
                "control_reference": out["control_reference"],
                "used_count": out["used_count"],
                "usage_limit": out["usage_limit"],
                "status": out["status"],
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(out)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def try_allow_under_exception(
    *,
    entity_id: str,
    control_type: str,
    control_reference: str,
    governed_object_type: str,
    governed_object_id: str,
    normal_result: str,
    normal_reason_code: str,
    scope_id: str | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = False,
) -> dict[str, Any] | None:
    """If an AUTHORISED exception matches, consume and return ALLOWED_UNDER_EXCEPTION.

    Returns None when no usable exception. Never rewrites normal_result to PASS.
    """
    ev = evaluate_exception_for_control(
        entity_id=entity_id,
        control_type=control_type,
        control_reference=control_reference,
        governed_object_type=governed_object_type,
        governed_object_id=governed_object_id,
        scope_id=scope_id,
        verified_person_id=verified_person_id,
        identity=identity,
        audit=False,
        conn=conn,
    )
    if not ev.get("allowed") or not ev.get("exception_id"):
        return None
    consumed = consume_exception(
        ev["exception_id"],
        verified_person_id=verified_person_id,
        identity=identity,
        conn=conn,
        commit=commit,
    )
    return {
        "allowed": True,
        "result": "ALLOWED_UNDER_EXCEPTION",
        "reason_code": "allowed_under_exception",
        "normal_result": normal_result,
        "normal_reason_code": normal_reason_code,
        "exception_id": consumed["exception_id"],
        "exception_status": consumed["status"],
        "control_type": control_type,
        "control_reference": control_reference,
        "entity_id": entity_id,
        "governed_object_type": governed_object_type,
        "governed_object_id": governed_object_id,
        **HONESTY,
    }
