#!/usr/bin/env python3
"""Wolf Core Evidence Requirement Enforcement — CLAIMED ≠ EVIDENCED ≠ VERIFIED.

Extends Audit/Evidence Spine (does not replace append-only audit events).
Client evidence_present / evidence_required flags are IGNORED.
Cross-Entity / Scope / object evidence never counted.
Cryptographic immutability NOT BUILT. Live evidence requirements = 0.
"""
from __future__ import annotations

import json
import os
import re
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

RECORD_STATUSES = frozenset({"ACTIVE", "INVALIDATED"})
VERIFICATION_STATUSES = frozenset({"SUBMITTED", "VERIFIED", "REJECTED"})
REQUIREMENT_STATUSES = frozenset({"ACTIVE", "INACTIVE"})
SOURCE_TYPES = frozenset({"HUMAN", "SYSTEM", "TEST", "EXTERNAL", "WORK_ITEM"})

SECRET_KEY_RE = re.compile(
    r"(jwt|password|passwd|cookie|api[_-]?key|authorization|secret|token|bearer)",
    re.IGNORECASE,
)
METADATA_MAX_BYTES = 4096
CONTENT_HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")

HONESTY = {
    "evidence_requirements": "BUILT",
    "live_evidence_requirements": 0,
    "claimed_is_not_evidenced": True,
    "evidenced_is_not_verified": True,
    "cryptographic_immutability": "NOT_BUILT",
    "ai_evidence_verify": False,
}


class EvidenceError(ValueError):
    """Fail-closed evidence validation / state error."""

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
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise EvidenceError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"evidence refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"evidence refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"evidence refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_evidence_id() -> str:
    return f"EVD-{uuid.uuid4()}"


def mint_requirement_id() -> str:
    return f"EVR-{uuid.uuid4()}"


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


def _prepare_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Size-capped metadata with secret stripping (audit pattern, no allowlist drop)."""
    if not metadata:
        return None
    if not isinstance(metadata, dict):
        raise EvidenceError("metadata must be a dict", code="invalid_metadata")
    cleaned = _audit.strip_secrets(metadata)
    for k in list(cleaned.keys()):
        if SECRET_KEY_RE.search(str(k)):
            raise EvidenceError(f"secret metadata key refused: {k}", code="secret_metadata")
    raw = json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False)
    if len(raw.encode("utf-8")) > METADATA_MAX_BYTES:
        raise EvidenceError(
            f"metadata_json exceeds {METADATA_MAX_BYTES} bytes",
            code="metadata_too_large",
        )
    return raw if cleaned else None


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    meta = d.get("metadata_json")
    if isinstance(meta, str) and meta:
        try:
            d["metadata"] = json.loads(meta)
        except json.JSONDecodeError:
            d["metadata"] = None
    else:
        d["metadata"] = None
    return d


def delete_evidence(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError(
        "core_evidence_records refuses hard delete; use invalidate_evidence"
    )


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
            raise EvidenceError(
                "allow_test_write refused outside test mode",
                code="permission_denied",
                http_status=403,
            )
        return
    pid = (verified_person_id or "").strip()
    if not pid:
        raise EvidenceError(
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
        raise EvidenceError(
            f"{permission_code} denied",
            code="permission_denied",
            http_status=403,
        )


def _audit_evidence(
    *,
    action: str,
    result: str,
    evidence: dict[str, Any] | None = None,
    evaluation: dict[str, Any] | None = None,
    reason_code: str | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    evidence = evidence or {}
    evaluation = evaluation or {}
    meta = metadata or {
        "evidence_type": evidence.get("evidence_type") or evaluation.get("missing"),
        "governed_object_type": evidence.get("governed_object_type"),
        "governed_object_id": evidence.get("governed_object_id"),
        "verification_status": evidence.get("verification_status"),
        "status": evidence.get("status") or evaluation.get("result"),
        "action_type": evaluation.get("action_type"),
        "request_type": evaluation.get("request_type"),
        "reason": reason_code or evaluation.get("reason_code"),
    }
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "evidence",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": evidence.get("entity_id") or evaluation.get("entity_id"),
        "scope_id": evidence.get("scope_id") or evaluation.get("scope_id"),
        "resource_type": "evidence_record"
        if evidence.get("evidence_id")
        else "evidence_requirement",
        "resource_id": evidence.get("evidence_id")
        or (
            (evaluation.get("requirements") or [{}])[0].get("requirement_id")
            if evaluation.get("requirements")
            else None
        ),
        "reason_code": reason_code or evaluation.get("reason_code"),
        "correlation_id": identity.get("correlation_id") or _audit.mint_correlation_id(),
        "evidence_reference": evidence.get("evidence_id"),
        "metadata": meta,
        "conn": conn,
        "commit": False,
    }
    if verified_person_id:
        kwargs["verified_person_id"] = verified_person_id
        kwargs["actor_person_id"] = verified_person_id
        kwargs["actor_auth_identity_id"] = identity.get("auth_identity_id")
        kwargs["identity_assurance"] = identity.get("identity_assurance")
    _audit.safe_record(**kwargs)


def get_evidence(
    evidence_id: str, *, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    eid = (evidence_id or "").strip()
    if not eid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                "SELECT * FROM core_evidence_records WHERE evidence_id=?",
                (eid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def get_evidence_requirement(
    requirement_id: str,
    requirement_version: int | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    rid = (requirement_id or "").strip()
    if not rid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        if requirement_version is not None:
            row = c.execute(
                """
                SELECT * FROM core_evidence_requirements
                WHERE requirement_id=? AND requirement_version=?
                """,
                (rid, int(requirement_version)),
            ).fetchone()
            return dict(row) if row else None
        row = c.execute(
            """
            SELECT * FROM core_evidence_requirements
            WHERE requirement_id=?
            ORDER BY requirement_version DESC
            LIMIT 1
            """,
            (rid,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def ensure_evidence_type(
    evidence_type: str,
    *,
    description: str | None = None,
    verified_person_id: str | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Register or confirm a governed evidence_type (catalog)."""
    et = (evidence_type or "").strip()
    if not et:
        raise EvidenceError("evidence_type required", code="missing_evidence_type")
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        if allow_test_write:
            _assert_permission(
                verified_person_id=verified_person_id or "PERS-TEST",
                permission_code="evidence.requirement.manage",
                entity_id="ENT-GGV",
                conn=c,
                allow_test_write=True,
            )
        ts = now_utc_iso()
        existing = c.execute(
            "SELECT * FROM core_evidence_types WHERE evidence_type=?",
            (et,),
        ).fetchone()
        if existing:
            return dict(existing)
        c.execute(
            """
            INSERT INTO core_evidence_types (
              evidence_type, description, status, created_at, updated_at
            ) VALUES (?, ?, 'ACTIVE', ?, ?)
            """,
            (et, (description or "").strip() or None, ts, ts),
        )
        if commit:
            c.commit()
        row = c.execute(
            "SELECT * FROM core_evidence_types WHERE evidence_type=?",
            (et,),
        ).fetchone()
        assert row is not None
        return dict(row)
    finally:
        if own:
            c.close()


def insert_evidence_requirement_for_test(
    *,
    entity_id: str,
    action_type: str,
    evidence_type: str,
    requirement_id: str | None = None,
    requirement_version: int = 1,
    scope_id: str | None = None,
    request_type: str | None = None,
    min_count: int = 1,
    verification_needed: int = 0,
    effective_from: str | None = None,
    effective_to: str | None = None,
    status: str = "ACTIVE",
    created_by_person_id: str | None = None,
    verified_person_id: str | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """TEST/manage insert for requirements. Defaults DENY without hook or manage perm."""
    eid = (entity_id or "").strip()
    if not eid:
        raise EvidenceError("entity_id required", code="missing_entity")
    act = (action_type or "").strip()
    if not act:
        raise EvidenceError("action_type required", code="missing_action_type")
    et = (evidence_type or "").strip()
    if not et:
        raise EvidenceError("evidence_type required", code="missing_evidence_type")
    st = (status or "").strip().upper()
    if st not in REQUIREMENT_STATUSES:
        raise EvidenceError(f"invalid status: {status!r}", code="invalid_status")
    mc = int(min_count)
    if mc < 1:
        raise EvidenceError("min_count must be >= 1", code="invalid_min_count")
    vn = 1 if int(verification_needed) else 0

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_permission(
            verified_person_id=verified_person_id or "",
            permission_code="evidence.requirement.manage",
            entity_id=eid,
            conn=c,
            allow_test_write=allow_test_write,
        )
        ensure_evidence_type(et, allow_test_write=True, conn=c, commit=False)
        rid = (requirement_id or "").strip() or mint_requirement_id()
        ts = now_utc_iso()
        eff_from = (effective_from or "").strip() or ts
        c.execute(
            """
            INSERT INTO core_evidence_requirements (
              requirement_id, requirement_version, entity_id, scope_id,
              action_type, request_type, evidence_type, min_count,
              verification_needed, effective_from, effective_to, status,
              created_at, updated_at, created_by_person_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                int(requirement_version),
                eid,
                (scope_id or "").strip() or None,
                act,
                (request_type or "").strip().upper() or None,
                et,
                mc,
                vn,
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
        out = get_evidence_requirement(rid, int(requirement_version), conn=c)
        assert out is not None
        return out
    finally:
        if own:
            c.close()


def submit_evidence(
    *,
    entity_id: str,
    evidence_type: str,
    governed_object_type: str,
    governed_object_id: str,
    verified_person_id: str,
    source_type: str = "HUMAN",
    source_reference: str | None = None,
    scope_id: str | None = None,
    object_ref: str | None = None,
    content_hash: str | None = None,
    submitted_by_assignment_id: str | None = None,
    submitted_by_person_id: str | None = None,
    captured_at: str | None = None,
    classification: str | None = None,
    metadata: dict[str, Any] | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Submit ACTIVE evidence. Person from verified_person_id only; forged ignored."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise EvidenceError("verified_person_id required", code="missing_verified_person")
    if submitted_by_person_id and submitted_by_person_id.strip() != verified:
        raise EvidenceError(
            "submitted_by_person_id must match verified identity; client spoof refused",
            code="forged_submitter",
            http_status=400,
        )

    eid = (entity_id or "").strip()
    if not eid:
        raise EvidenceError("entity_id required", code="missing_entity")
    et = (evidence_type or "").strip()
    if not et:
        raise EvidenceError("evidence_type required", code="missing_evidence_type")
    got = (governed_object_type or "").strip()
    goi = (governed_object_id or "").strip()
    if not got or not goi:
        raise EvidenceError(
            "governed_object_type and governed_object_id required",
            code="missing_governed_object",
        )
    src = (source_type or "").strip().upper()
    if src not in SOURCE_TYPES:
        raise EvidenceError(f"invalid source_type: {source_type!r}", code="invalid_source_type")

    # object_ref = string only; refuse bytes/blob-like
    if object_ref is not None and not isinstance(object_ref, str):
        raise EvidenceError(
            "object_ref must be a string (no SQLite blobs)",
            code="invalid_object_ref",
        )
    oref = (object_ref or "").strip() or None
    ch = (content_hash or "").strip() or None
    if ch and not CONTENT_HASH_RE.match(ch):
        raise EvidenceError(
            "content_hash must be 64-char hex SHA-256 when set",
            code="invalid_content_hash",
        )

    meta_json = _prepare_metadata(metadata)
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_permission(
            verified_person_id=verified,
            permission_code="evidence.record.submit",
            entity_id=eid,
            conn=c,
            allow_test_write=allow_test_write,
        )
        trow = c.execute(
            "SELECT evidence_type, status FROM core_evidence_types WHERE evidence_type=?",
            (et,),
        ).fetchone()
        if not trow or trow["status"] != "ACTIVE":
            raise EvidenceError(
                f"unknown or inactive evidence_type: {et}",
                code="unknown_evidence_type",
            )

        evid = mint_evidence_id()
        ts = now_utc_iso()
        c.execute(
            """
            INSERT INTO core_evidence_records (
              evidence_id, entity_id, scope_id, evidence_type, source_type,
              source_reference, object_ref, content_hash,
              submitted_by_person_id, submitted_by_assignment_id, submitted_at,
              captured_at, status, verification_status,
              verified_by_person_id, verified_at, verification_reason,
              governed_object_type, governed_object_id, classification,
              metadata_json, created_at, updated_at,
              invalidated_at, invalidate_reason
            ) VALUES (
              ?, ?, ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              ?, 'ACTIVE', 'SUBMITTED',
              NULL, NULL, NULL,
              ?, ?, ?,
              ?, ?, ?,
              NULL, NULL
            )
            """,
            (
                evid,
                eid,
                (scope_id or "").strip() or None,
                et,
                src,
                (source_reference or "").strip() or None,
                oref,
                ch,
                verified,
                (submitted_by_assignment_id or "").strip() or None,
                ts,
                (captured_at or "").strip() or None,
                got,
                goi,
                (classification or "").strip() or None,
                meta_json,
                ts,
                ts,
            ),
        )
        row = get_evidence(evid, conn=c)
        assert row is not None
        _audit_evidence(
            action="evidence.submitted",
            result="SUCCEEDED",
            evidence=row,
            verified_person_id=verified,
            identity=identity,
            reason_code="submitted",
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(row)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def invalidate_evidence(
    evidence_id: str,
    *,
    verified_person_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Mark evidence INVALIDATED. Hard delete refused."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise EvidenceError("verified_person_id required", code="missing_verified_person")
    rid = (evidence_id or "").strip()
    why = (reason or "").strip()
    if not why:
        raise EvidenceError("invalidate reason required", code="missing_invalidate_reason")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_evidence(rid, conn=c)
        if not row:
            raise EvidenceError("evidence not found", code="not_found", http_status=404)
        if row["status"] == "INVALIDATED":
            raise EvidenceError("evidence already invalidated", code="already_invalidated")
        _assert_permission(
            verified_person_id=verified,
            permission_code="evidence.requirement.manage",
            entity_id=row["entity_id"],
            conn=c,
            allow_test_write=allow_test_write,
        )
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_evidence_records
            SET status='INVALIDATED', invalidated_at=?, invalidate_reason=?, updated_at=?
            WHERE evidence_id=?
            """,
            (ts, why, ts, rid),
        )
        out = get_evidence(rid, conn=c)
        assert out is not None
        _audit_evidence(
            action="evidence.invalidated",
            result="SUCCEEDED",
            evidence=out,
            verified_person_id=verified,
            identity=identity,
            reason_code="invalidated",
            metadata={"reason": why, "status": "INVALIDATED"},
            conn=c,
        )
        if commit:
            c.commit()
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def verify_evidence(
    evidence_id: str,
    *,
    verified_person_id: str,
    decision: str = "VERIFIED",
    reason: str | None = None,
    require_independent_verify: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Verify or reject submitted evidence. Person from verified id only."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise EvidenceError("verified_person_id required", code="missing_verified_person")
    eid = (evidence_id or "").strip()
    dec = (decision or "").strip().upper()
    if dec not in ("VERIFIED", "REJECTED"):
        raise EvidenceError(f"invalid verify decision: {decision!r}", code="invalid_decision")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_evidence(eid, conn=c)
        if not row:
            raise EvidenceError("evidence not found", code="not_found", http_status=404)
        if row["status"] != "ACTIVE":
            raise EvidenceError(
                "cannot verify invalidated evidence",
                code="invalidated",
                http_status=409,
            )
        if row["verification_status"] in ("VERIFIED", "REJECTED"):
            raise EvidenceError(
                f"evidence already {row['verification_status']}",
                code="already_verified",
                http_status=409,
            )
        _assert_permission(
            verified_person_id=verified,
            permission_code="evidence.requirement.manage",
            entity_id=row["entity_id"],
            conn=c,
            allow_test_write=allow_test_write,
        )
        if require_independent_verify and verified == row["submitted_by_person_id"]:
            _audit_evidence(
                action="evidence.verify_denied",
                result="DENIED",
                evidence=row,
                verified_person_id=verified,
                identity=identity,
                reason_code="self_verify_denied",
                conn=c,
            )
            if commit:
                c.commit()
            raise EvidenceError(
                "submitter cannot verify own evidence",
                code="self_verify_denied",
                http_status=403,
            )

        # Optional SoD when ACTIVE fixture exists (evidence.submit vs evidence.verify)
        try:
            from core import sod as _sod

            sod_ev = _sod.evaluate_sod(
                verified,
                row["entity_id"],
                "EVIDENCE",
                "evidence.verify",
                eid,
                scope_id=row.get("scope_id"),
                identity=identity,
                audit=False,
                conn=c,
            )
            if not sod_ev.get("allowed") and sod_ev.get("reason_code") not in (
                "sod_not_applicable",
                None,
            ):
                reason_sod = sod_ev.get("reason_code") or "sod_same_person_conflict"
                _audit_evidence(
                    action="evidence.verify_denied",
                    result="DENIED",
                    evidence=row,
                    verified_person_id=verified,
                    identity=identity,
                    reason_code=reason_sod,
                    conn=c,
                )
                if commit:
                    c.commit()
                raise EvidenceError(
                    f"segregation of duties denied: {reason_sod}",
                    code=reason_sod,
                    http_status=403,
                )
        except ImportError:
            pass

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_evidence_records
            SET verification_status=?, verified_by_person_id=?, verified_at=?,
                verification_reason=?, updated_at=?
            WHERE evidence_id=?
            """,
            (
                dec,
                verified,
                ts,
                (reason or "").strip() or None,
                ts,
                eid,
            ),
        )
        out = get_evidence(eid, conn=c)
        assert out is not None
        _audit_evidence(
            action="evidence.verified" if dec == "VERIFIED" else "evidence.rejected",
            result="SUCCEEDED",
            evidence=out,
            verified_person_id=verified,
            identity=identity,
            reason_code=dec.lower(),
            conn=c,
        )
        if commit:
            c.commit()
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def _specificity_key(row: dict[str, Any]) -> tuple[int, int, int]:
    """Higher wins: (scope_exact, request_type_exact, requirement_version)."""
    scope_exact = 1 if row.get("scope_id") else 0
    rt_exact = 1 if row.get("request_type") else 0
    return (scope_exact, rt_exact, int(row.get("requirement_version") or 0))


def _count_matching_evidence(
    *,
    conn: sqlite3.Connection,
    entity_id: str,
    scope_id: str | None,
    evidence_type: str,
    governed_object_type: str,
    governed_object_id: str,
    verification_needed: bool,
) -> int:
    clauses = [
        "entity_id=?",
        "evidence_type=?",
        "governed_object_type=?",
        "governed_object_id=?",
        "status='ACTIVE'",
    ]
    params: list[Any] = [entity_id, evidence_type, governed_object_type, governed_object_id]
    # Scope: requirement scope_id NULL matches any; exact scope requires equal scope on evidence
    if scope_id:
        clauses.append("scope_id=?")
        params.append(scope_id)
    if verification_needed:
        clauses.append("verification_status='VERIFIED'")
    sql = f"SELECT COUNT(*) FROM core_evidence_records WHERE {' AND '.join(clauses)}"
    return int(conn.execute(sql, params).fetchone()[0])


def evaluate_evidence_requirements(
    entity_id: str,
    action_type: str,
    *,
    scope_id: str | None = None,
    request_type: str | None = None,
    governed_object_type: str | None = None,
    governed_object_id: str | None = None,
    as_of: str | None = None,
    # Client flags — IGNORED
    evidence_present: Any = None,
    evidence_required: Any = None,
    client_evidence_count: Any = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    audit: bool = True,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Fail-closed evidence requirement evaluator.

    Zero ACTIVE matching requirements → satisfied (legacy paths green).
    Conflicts at equal specificity → DENY requirement_conflict.
    Missing/insufficient → DENY missing_required_evidence with missing list.
    """
    # Explicitly ignore client override claims
    _ = evidence_present, evidence_required, client_evidence_count

    eid = (entity_id or "").strip()
    act = (action_type or "").strip()
    if not eid or not act:
        raise EvidenceError(
            "entity_id and action_type required",
            code="missing_evaluate_fields",
        )
    got = (governed_object_type or "").strip() or None
    goi = (governed_object_id or "").strip() or None
    rt = (request_type or "").strip().upper() or None
    sc = (scope_id or "").strip() or None

    at = _parse_iso(as_of) or datetime.now(TZ_UTC)

    out: dict[str, Any] = {
        "allowed": False,
        "satisfied": False,
        "result": "DENIED",
        "reason_code": "missing_required_evidence",
        "entity_id": eid,
        "scope_id": sc,
        "action_type": act,
        "request_type": rt,
        "governed_object_type": got,
        "governed_object_id": goi,
        "requirements": [],
        "missing": [],
        "candidates": [],
        "evaluator": "core.evidence.evaluate_evidence_requirements",
        **HONESTY,
    }

    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_evidence_requirements
            WHERE entity_id=? AND action_type=? AND status='ACTIVE'
              AND (scope_id IS NULL OR scope_id=?)
            """,
            (eid, act, sc),
        ).fetchall()
        candidates = [dict(r) for r in rows if _effective(dict(r), at)]
        if rt:
            candidates = [
                r
                for r in candidates
                if r.get("request_type") is None
                or (r.get("request_type") or "").upper() == rt
            ]
        out["candidates"] = [
            {
                "requirement_id": r["requirement_id"],
                "requirement_version": r["requirement_version"],
                "scope_id": r.get("scope_id"),
                "request_type": r.get("request_type"),
                "evidence_type": r["evidence_type"],
            }
            for r in candidates
        ]

        if not candidates:
            out["allowed"] = True
            out["satisfied"] = True
            out["result"] = "NO_REQUIREMENTS"
            out["reason_code"] = "no_evidence_requirements"
            if audit:
                _audit_evidence(
                    action="evidence.requirement_evaluated",
                    result="ALLOWED",
                    evaluation=out,
                    verified_person_id=verified_person_id,
                    identity=identity,
                    reason_code="no_evidence_requirements",
                    conn=c,
                )
            return out

        # Precedence: group by evidence_type; within type pick max specificity.
        # Equal top specificity across different requirement_ids → conflict.
        by_type: dict[str, list[dict[str, Any]]] = {}
        for r in candidates:
            by_type.setdefault(r["evidence_type"], []).append(r)

        winners: list[dict[str, Any]] = []
        for etype, group in by_type.items():
            ranked = sorted(group, key=_specificity_key, reverse=True)
            best_key = _specificity_key(ranked[0])
            tops = [r for r in ranked if _specificity_key(r) == best_key]
            # Distinct requirement_id at same specificity = conflict
            top_ids = {r["requirement_id"] for r in tops}
            if len(top_ids) > 1:
                out["allowed"] = False
                out["satisfied"] = False
                out["result"] = "CONFLICT"
                out["reason_code"] = "requirement_conflict"
                out["requirements"] = tops
                if audit:
                    _audit_evidence(
                        action="evidence.requirement_evaluated",
                        result="DENIED",
                        evaluation=out,
                        verified_person_id=verified_person_id,
                        identity=identity,
                        reason_code="requirement_conflict",
                        conn=c,
                    )
                return out
            winners.append(tops[0])

        if not got or not goi:
            out["allowed"] = False
            out["satisfied"] = False
            out["result"] = "DENIED"
            out["reason_code"] = "missing_governed_object"
            out["missing"] = [
                {
                    "requirement_id": w["requirement_id"],
                    "evidence_type": w["evidence_type"],
                    "needed": int(w["min_count"]),
                    "have": 0,
                }
                for w in winners
            ]
            if audit:
                _audit_evidence(
                    action="evidence.requirement_evaluated",
                    result="DENIED",
                    evaluation=out,
                    verified_person_id=verified_person_id,
                    identity=identity,
                    reason_code="missing_governed_object",
                    conn=c,
                )
            return out

        missing: list[dict[str, Any]] = []
        req_out: list[dict[str, Any]] = []
        for w in winners:
            need_v = bool(int(w.get("verification_needed") or 0))
            have = _count_matching_evidence(
                conn=c,
                entity_id=eid,
                scope_id=w.get("scope_id"),
                evidence_type=w["evidence_type"],
                governed_object_type=got,
                governed_object_id=goi,
                verification_needed=need_v,
            )
            need = int(w["min_count"])
            entry = {
                "requirement_id": w["requirement_id"],
                "requirement_version": w["requirement_version"],
                "evidence_type": w["evidence_type"],
                "min_count": need,
                "verification_needed": need_v,
                "have": have,
                "satisfied": have >= need,
            }
            req_out.append(entry)
            if have < need:
                missing.append(
                    {
                        "requirement_id": w["requirement_id"],
                        "evidence_type": w["evidence_type"],
                        "needed": need,
                        "have": have,
                        "verification_needed": need_v,
                    }
                )

        out["requirements"] = req_out
        out["missing"] = missing
        if missing:
            out["allowed"] = False
            out["satisfied"] = False
            out["result"] = "DENIED"
            out["reason_code"] = "missing_required_evidence"
            if audit:
                _audit_evidence(
                    action="evidence.requirement_evaluated",
                    result="DENIED",
                    evaluation=out,
                    verified_person_id=verified_person_id,
                    identity=identity,
                    reason_code="missing_required_evidence",
                    metadata={
                        "action_type": act,
                        "request_type": rt,
                        "status": "DENIED",
                        "reason": "missing_required_evidence",
                    },
                    conn=c,
                )
            return out

        out["allowed"] = True
        out["satisfied"] = True
        out["result"] = "SATISFIED"
        out["reason_code"] = "evidence_satisfied"
        if audit:
            _audit_evidence(
                action="evidence.requirement_evaluated",
                result="ALLOWED",
                evaluation=out,
                verified_person_id=verified_person_id,
                identity=identity,
                reason_code="evidence_satisfied",
                conn=c,
            )
        return out
    finally:
        if own:
            c.close()
