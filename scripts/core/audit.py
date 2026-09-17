#!/usr/bin/env python3
"""Wolf Core Audit / Evidence Spine — append-only INSERT service (Beta).

Tamper-*evidence* via structured rows + optional before/after hashes.
NOT a cryptographic hash-chain. NOT court-grade immutability.
Never stores jwt/password/cookie/api_key/authorization/token.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
TZ_UTC = timezone.utc

RESULTS = frozenset({"ALLOWED", "DENIED", "SUCCEEDED", "FAILED", "ERROR"})
ACTOR_TYPES = frozenset({"PERSON", "SYSTEM"})

SECRET_KEY_RE = re.compile(
    r"(jwt|password|passwd|cookie|api[_-]?key|authorization|secret|token|bearer)",
    re.IGNORECASE,
)

# Allowlisted metadata keys (non-secret extras only). Unknown keys dropped.
METADATA_ALLOWLIST = frozenset(
    {
        "permission",
        "permission_code",
        "required_permission",
        "error",
        "reason",
        "auth_mode",
        "brand",
        "slot_id",
        "plan_id",
        "amount",
        "currency",
        "note",
        "path",
        "status",
        "email_domain",
        "http_status",
        "work_type",
        "owner_person_id",
        "request_type",
        "decision",
        "linked_work_item_id",
        "delegation_id",
        "authority_basis_type",
        "delegator_person_id",
        "delegate_person_id",
        "required_decision_count",
        "valid_approve_count",
        "approvals_remaining",
        "terminal",
        "action_type",
        "policy_id",
        "policy_version",
        "approvals_required",
        "governing_policy_id",
        "governing_policy_version",
        "bind_policy",
        "evidence_type",
        "governed_object_type",
        "governed_object_id",
        "verification_status",
        "missing",
        "enforce_evidence",
        "evidence_result",
        "requirement_id",
        "requirement_version",
        "exception_id",
        "control_type",
        "control_reference",
        "normal_result",
        "normal_reason_code",
        "exception_result",
        "usage_limit",
        "used_count",
    }
)
METADATA_MAX_BYTES = 4096


class AuditValidationError(ValueError):
    """Fail-closed validation for audit writes."""


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path) -> None:
    """Fail closed: refuse accidental live catalog writes from tests.

    Prefer explicit temp CATALOG_DB wiring. Override only with WOLF_ALLOW_LIVE_AUDIT=1.
    """
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise AuditValidationError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy"
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"audit refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"audit refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"audit refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_correlation_id() -> str:
    return str(uuid.uuid4())


def strip_secrets(obj: Any) -> Any:
    """Recursively drop secret-named keys; never return credential material."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key = str(k)
            if SECRET_KEY_RE.search(key):
                continue
            out[key] = strip_secrets(v)
        return out
    if isinstance(obj, list):
        return [strip_secrets(x) for x in obj]
    if isinstance(obj, str) and len(obj) > 512 and obj.count(".") >= 2:
        # Heuristic: long dotted strings look like JWTs — redact.
        return "[redacted]"
    return obj


def _prepare_metadata(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    if not isinstance(metadata, dict):
        raise AuditValidationError("metadata must be a dict")
    cleaned = strip_secrets(metadata)
    # Allowlist + reject residual secret-shaped keys
    filtered: dict[str, Any] = {}
    for k, v in cleaned.items():
        key = str(k)
        if SECRET_KEY_RE.search(key):
            raise AuditValidationError(f"secret metadata key refused: {key}")
        if key not in METADATA_ALLOWLIST:
            continue
        filtered[key] = v
    raw = json.dumps(filtered, separators=(",", ":"), ensure_ascii=False)
    if len(raw.encode("utf-8")) > METADATA_MAX_BYTES:
        raise AuditValidationError(
            f"metadata_json exceeds {METADATA_MAX_BYTES} bytes"
        )
    return raw if filtered else None


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


def update_event(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError("core_audit_events is append-only; use correct_event")


def delete_event(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError("core_audit_events is append-only; corrections are INSERTs")


def record_event(
    *,
    action: str,
    result: str,
    source: str,
    actor_type: str,
    actor_person_id: str | None = None,
    actor_auth_identity_id: str | None = None,
    actor_assignment_id: str | None = None,
    identity_assurance: str | None = None,
    entity_id: str | None = None,
    brand_id: str | None = None,
    location_id: str | None = None,
    department_id: str | None = None,
    scope_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    reason_code: str | None = None,
    correlation_id: str | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
    evidence_reference: str | None = None,
    corrects_event_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: str | None = None,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """INSERT one audit event. Fail closed on validation errors.

    PERSON actors require verified_person_id (from request_auth / identity path).
    Client-supplied actor_person_id alone is refused unless it matches verified_person_id.
    """
    at = (actor_type or "").strip().upper()
    if at not in ACTOR_TYPES:
        raise AuditValidationError(f"invalid actor_type: {actor_type!r}")
    res = (result or "").strip().upper()
    if res not in RESULTS:
        raise AuditValidationError(f"invalid result: {result!r}")
    act = (action or "").strip()
    if not act:
        raise AuditValidationError("action required")
    src = (source or "").strip()
    if not src:
        raise AuditValidationError("source required")

    # Refuse secret field names at top-level kwargs (defense)
    for forbidden in (
        "jwt",
        "password",
        "cookie",
        "api_key",
        "authorization",
        "token",
    ):
        if metadata and forbidden in {str(k).lower() for k in metadata}:
            raise AuditValidationError(f"secret field refused: {forbidden}")

    person = (actor_person_id or "").strip() or None
    verified = (verified_person_id or "").strip() or None

    if at == "SYSTEM":
        if person is not None:
            raise AuditValidationError("SYSTEM actor cannot carry actor_person_id")
    else:  # PERSON
        if not verified:
            raise AuditValidationError(
                "PERSON actor requires verified_person_id from identity path"
            )
        if person and person != verified:
            raise AuditValidationError(
                "actor_person_id must match verified identity; client spoof refused"
            )
        person = verified

    meta_json = _prepare_metadata(metadata)
    corr = (correlation_id or "").strip() or mint_correlation_id()
    ts = now_utc_iso()
    occurred = (occurred_at or "").strip() or ts
    event_id = str(uuid.uuid4())

    own = conn is None
    c = conn or db_connect()
    try:
        # Refuse accidental live writes from test processes (explicit temp wiring preferred).
        assert_catalog_writable(Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB))
        if corrects_event_id:
            prior = c.execute(
                "SELECT audit_event_id FROM core_audit_events WHERE audit_event_id=?",
                (corrects_event_id,),
            ).fetchone()
            if not prior:
                raise AuditValidationError(
                    f"corrects_event_id not found: {corrects_event_id}"
                )

        c.execute(
            """
            INSERT INTO core_audit_events (
              audit_event_id, occurred_at, recorded_at, created_at,
              actor_type, actor_person_id, actor_auth_identity_id, actor_assignment_id,
              identity_assurance, entity_id, brand_id, location_id, department_id, scope_id,
              action, resource_type, resource_id, result, reason_code, correlation_id, source,
              before_hash, after_hash, evidence_reference, corrects_event_id, metadata_json
            ) VALUES (
              ?, ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?
            )
            """,
            (
                event_id,
                occurred,
                ts,
                ts,
                at,
                person,
                (actor_auth_identity_id or "").strip() or None,
                (actor_assignment_id or "").strip() or None,
                (identity_assurance or "").strip() or None,
                (entity_id or "").strip() or None,
                (brand_id or "").strip() or None,
                (location_id or "").strip() or None,
                (department_id or "").strip() or None,
                (scope_id or "").strip() or None,
                act,
                (resource_type or "").strip() or None,
                (resource_id or "").strip() or None,
                res,
                (reason_code or "").strip() or None,
                corr,
                src,
                (before_hash or "").strip() or None,
                (after_hash or "").strip() or None,
                (evidence_reference or "").strip() or None,
                (corrects_event_id or "").strip() or None,
                meta_json,
            ),
        )
        if commit and own:
            c.commit()
        elif commit and not own:
            c.commit()
        return get_event(event_id, conn=c) or {"audit_event_id": event_id}
    finally:
        if own:
            c.close()


def correct_event(
    prior_id: str,
    *,
    action: str,
    result: str,
    source: str,
    actor_type: str,
    verified_person_id: str | None = None,
    actor_person_id: str | None = None,
    reason_code: str | None = None,
    correlation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    identity_assurance: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """INSERT a correction row referencing a prior event (append-only)."""
    return record_event(
        action=action,
        result=result,
        source=source,
        actor_type=actor_type,
        actor_person_id=actor_person_id,
        verified_person_id=verified_person_id,
        reason_code=reason_code or "correction",
        correlation_id=correlation_id,
        metadata=metadata,
        identity_assurance=identity_assurance,
        corrects_event_id=prior_id,
        conn=conn,
    )


def get_event(
    audit_event_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    eid = (audit_event_id or "").strip()
    if not eid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                "SELECT * FROM core_audit_events WHERE audit_event_id=?",
                (eid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_events(
    *,
    entity_id: str | None = None,
    scope_id: str | None = None,
    actor_person_id: str | None = None,
    action: str | None = None,
    result: str | None = None,
    source: str | None = None,
    correlation_id: str | None = None,
    occurred_from: str | None = None,
    occurred_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if entity_id:
            clauses.append("entity_id=?")
            params.append(entity_id)
        if scope_id:
            clauses.append("scope_id=?")
            params.append(scope_id)
        if actor_person_id:
            clauses.append("actor_person_id=?")
            params.append(actor_person_id)
        if action:
            clauses.append("action=?")
            params.append(action)
        if result:
            clauses.append("result=?")
            params.append(result)
        if source:
            clauses.append("source=?")
            params.append(source)
        if correlation_id:
            clauses.append("correlation_id=?")
            params.append(correlation_id)
        if occurred_from:
            clauses.append("occurred_at>=?")
            params.append(occurred_from)
        if occurred_to:
            clauses.append("occurred_at<=?")
            params.append(occurred_to)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        lim = max(1, min(int(limit or 50), 200))
        off = max(0, int(offset or 0))
        rows = c.execute(
            f"""
            SELECT * FROM core_audit_events
            {where}
            ORDER BY occurred_at DESC, recorded_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, lim, off),
        ).fetchall()
        return [_row(r) for r in rows if r is not None]  # type: ignore[misc]
    finally:
        if own:
            c.close()


def safe_record(handler_or_none=None, **kwargs) -> dict[str, Any] | None:
    """Best-effort record: never crash the caller deny/success path.

    Returns the event dict or None on failure. Surfaces ERROR via stderr only.
    Under WOLF_TEST_MODE (or scripts/tests argv), live catalog writes fail closed
    inside record_event/db_connect — still swallowed here so request paths stay up.
    """
    try:
        # Prefer caller's conn; otherwise assert current CATALOG_DB is writable.
        if kwargs.get("conn") is None:
            assert_catalog_writable(Path(CATALOG_DB))
        return record_event(**kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"audit.safe_record failed: {exc}", file=sys.stderr)
        return None
