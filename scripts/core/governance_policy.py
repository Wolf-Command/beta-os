#!/usr/bin/env python3
"""Wolf Core Governance Policy Binding — deterministic ACTION → REQUIRED CONTROL.

Fail closed: NO MATCHING POLICY ≠ ALLOW for governed evaluate.
Policy ≠ Authority Limits. Policy ≠ Approval Decision. Delegation never rewrites policy.
PROHIBITED cannot be bypassed by Permission.
Live governance policies = 0. No real business thresholds in this module's seed.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
TZ_UTC = timezone.utc

STATUSES = frozenset({"ACTIVE", "INACTIVE"})
RESULTS = frozenset({"REQUIREMENTS", "PROHIBITED", "NO_MATCH", "CONFLICT", "MISSING_AMOUNT"})

# Amount-governed action types (NULL/malformed/negative amount → DENY)
AMOUNT_GOVERNED_ACTIONS = frozenset({"SPEND_APPROVE", "EXCEPTION", "GENERAL_MATERIAL"})

REQUEST_TYPE_TO_ACTION = {
    "SPEND": "SPEND_APPROVE",
    "EXCEPTION": "EXCEPTION",
    "GENERAL": "GENERAL_MATERIAL",
    "ACCESS": "GENERAL_MATERIAL",
    "HR": "GENERAL_MATERIAL",
    "CONTRACT": "GENERAL_MATERIAL",
}

HONESTY = {
    "policy_binding": "BUILT",
    "live_governance_policies": "HABITAT_PILOT_1",
    "exception_override": "NOT_BUILT",
    "ai_policy": False,
}


class GovernancePolicyError(ValueError):
    """Fail-closed governance policy error."""

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
        raise GovernancePolicyError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"governance_policy refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"governance_policy refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"governance_policy refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_policy_id() -> str:
    return f"GPO-{uuid.uuid4()}"


def action_type_for_request_type(request_type: str) -> str:
    rt = (request_type or "").strip().upper()
    return REQUEST_TYPE_TO_ACTION.get(rt, "GENERAL_MATERIAL")


def coerce_policy_amount(raw: Any) -> Decimal | None:
    """Return Decimal amount or None if missing/malformed. Rejects bool/negative."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw if raw >= 0 else None
    if isinstance(raw, (int, float)):
        if raw < 0:
            return None
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            d = Decimal(s)
        except (InvalidOperation, ValueError):
            return None
        if d < 0:
            return None
        return d
    return None


def require_amount_for_governed(
    amount: Any,
    *,
    action_type: str,
    candidates_amount_governed: bool = False,
) -> Decimal:
    """Fail-closed amount coerce for amount-governed actions / bands."""
    at = (action_type or "").strip().upper()
    governed = at in AMOUNT_GOVERNED_ACTIONS or candidates_amount_governed
    parsed = coerce_policy_amount(amount)
    if governed and parsed is None:
        raise GovernancePolicyError(
            "amount required for amount-governed policy evaluate",
            code="missing_amount",
            http_status=400,
        )
    if parsed is None:
        raise GovernancePolicyError(
            "amount missing or malformed",
            code="missing_amount",
            http_status=400,
        )
    return parsed


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


def _effective(pol: dict[str, Any], at: datetime) -> bool:
    start = _parse_iso(pol.get("effective_from"))
    if start is None:
        return False
    if at < start:
        return False
    eto = pol.get("effective_to")
    if eto:
        end = _parse_iso(str(eto))
        if end is None:
            return False
        # effective_to exclusive: as_of < effective_to
        if at >= end:
            return False
    return True


def _band_specificity(pol: dict[str, Any]) -> int:
    """3 = both min/max, 2 = open-ended (one bound), 1 = no band."""
    has_min = pol.get("amount_min") is not None and str(pol.get("amount_min")).strip() != ""
    has_max = pol.get("amount_max") is not None and str(pol.get("amount_max")).strip() != ""
    if has_min and has_max:
        return 3
    if has_min or has_max:
        return 2
    return 1


def _has_amount_band(pol: dict[str, Any]) -> bool:
    return _band_specificity(pol) > 1


def _amount_in_band(pol: dict[str, Any], amount: Decimal | None, currency: str | None) -> bool:
    """Inclusive [min, max]. No band → True (amount-agnostic). Currency required if band set."""
    if not _has_amount_band(pol):
        return True
    pol_cur = (pol.get("currency") or "").strip().upper() or None
    cur = (currency or "").strip().upper() or None
    if not pol_cur or not cur or pol_cur != cur:
        return False
    if amount is None:
        return False
    amin = coerce_policy_amount(pol.get("amount_min")) if pol.get("amount_min") not in (None, "") else None
    amax = coerce_policy_amount(pol.get("amount_max")) if pol.get("amount_max") not in (None, "") else None
    # Open-ended: missing bound is unbounded on that side
    if pol.get("amount_min") not in (None, "") and amin is None:
        return False  # malformed min
    if pol.get("amount_max") not in (None, "") and amax is None:
        return False
    if amin is not None and amount < amin:
        return False
    if amax is not None and amount > amax:
        return False
    return True


def _specificity_key(pol: dict[str, Any]) -> tuple[int, int, int]:
    """Higher tuple wins. (scope_exact, band_spec, policy_version)."""
    scope_exact = 1 if pol.get("scope_id") else 0
    return (scope_exact, _band_specificity(pol), int(pol.get("policy_version") or 0))


def _base_result(
    *,
    entity_id: str,
    scope_id: str | None,
    action_type: str,
    request_type: str | None,
    amount: Any,
    currency: str | None,
) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "scope_id": scope_id,
        "action_type": action_type,
        "request_type": request_type,
        "amount": amount,
        "currency": currency,
        "matched_policy_id": None,
        "matched_policy_version": None,
        "permission_required": None,
        "authority_required": 0,
        "approvals_required": 0,
        "evidence_required": 0,
        "result": "NO_MATCH",
        "reason_code": "no_matching_policy",
        "candidates": [],
        "evaluator": "core.governance_policy.evaluate_governance_policy",
        **HONESTY,
    }


def _audit_policy(
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
        "source": "governance_policy",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": evaluation.get("entity_id"),
        "resource_type": "governance_policy",
        "resource_id": evaluation.get("matched_policy_id"),
        "reason_code": reason_code or evaluation.get("reason_code"),
        "correlation_id": identity.get("correlation_id") or _audit.mint_correlation_id(),
        "metadata": metadata
        or {
            "action_type": evaluation.get("action_type"),
            "result": evaluation.get("result"),
            "policy_id": evaluation.get("matched_policy_id"),
            "policy_version": evaluation.get("matched_policy_version"),
            "approvals_required": evaluation.get("approvals_required"),
            "amount": evaluation.get("amount"),
            "currency": evaluation.get("currency"),
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


def get_governance_policy(
    policy_id: str,
    policy_version: int | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Read helper. No manage/write."""
    pid = (policy_id or "").strip()
    if not pid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        if policy_version is not None:
            row = c.execute(
                """
                SELECT * FROM core_governance_policies
                WHERE policy_id=? AND policy_version=?
                """,
                (pid, int(policy_version)),
            ).fetchone()
            return dict(row) if row else None
        row = c.execute(
            """
            SELECT * FROM core_governance_policies
            WHERE policy_id=?
            ORDER BY policy_version DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own:
            c.close()


def list_governance_policies(
    *,
    entity_id: str | None = None,
    action_type: str | None = None,
    status: str | None = "ACTIVE",
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Read helper. No manage/write."""
    own = conn is None
    c = conn or db_connect()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if entity_id:
            clauses.append("entity_id=?")
            params.append(entity_id.strip())
        if action_type:
            clauses.append("action_type=?")
            params.append(action_type.strip().upper())
        if status:
            st = status.strip().upper()
            if st not in STATUSES:
                raise GovernancePolicyError(f"invalid status filter: {status!r}")
            clauses.append("status=?")
            params.append(st)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        lim = max(1, min(int(limit or 100), 500))
        rows = c.execute(
            f"""
            SELECT * FROM core_governance_policies
            {where}
            ORDER BY entity_id, action_type, policy_id, policy_version DESC
            LIMIT ?
            """,
            (*params, lim),
        ).fetchall()
        return [dict(r) for r in rows]
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
    """Insert/manage defaults DENY. Tests must pass allow_test_write=True under WOLF_TEST_MODE."""
    if allow_test_write:
        if not _under_test_process() and (os.environ.get("WOLF_TEST_MODE") or "").strip() != "1":
            raise GovernancePolicyError(
                "allow_test_write refused outside test mode",
                code="manage_denied",
                http_status=403,
            )
        return
    pid = (verified_person_id or "").strip()
    if not pid:
        raise GovernancePolicyError(
            "governance.policy.manage denied (no verified person)",
            code="manage_denied",
            http_status=403,
        )
    ev = _rbac.evaluate(
        pid,
        "governance.policy.manage",
        {"entity_id": entity_id},
        conn=conn,
    )
    if not ev.get("allowed"):
        raise GovernancePolicyError(
            "governance.policy.manage denied",
            code="manage_denied",
            http_status=403,
        )


def insert_governance_policy_for_test(
    *,
    entity_id: str,
    action_type: str,
    policy_id: str | None = None,
    policy_version: int = 1,
    scope_id: str | None = None,
    request_type: str | None = None,
    required_permission_code: str | None = None,
    authority_required: int = 0,
    approval_required: int = 1,
    required_decision_count: int = 1,
    evidence_required: int = 0,
    prohibited: int = 0,
    amount_min: str | None = None,
    amount_max: str | None = None,
    currency: str | None = None,
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
        raise GovernancePolicyError("entity_id required", code="missing_entity")
    at = (action_type or "").strip().upper()
    if not at:
        raise GovernancePolicyError("action_type required", code="missing_action_type")
    st = (status or "").strip().upper()
    if st not in STATUSES:
        raise GovernancePolicyError(f"invalid status: {status!r}", code="invalid_status")
    ar = int(approval_required)
    rdc = int(required_decision_count)
    if ar and rdc < 1:
        raise GovernancePolicyError(
            "required_decision_count must be >=1 when approval_required=1",
            code="invalid_required_decision_count",
        )
    amin = (str(amount_min).strip() if amount_min is not None else None) or None
    amax = (str(amount_max).strip() if amount_max is not None else None) or None
    cur = (currency or "").strip().upper() or None
    if (amin is not None or amax is not None) and not cur:
        raise GovernancePolicyError(
            "currency required when amount band set",
            code="missing_currency",
        )
    if amin is not None and coerce_policy_amount(amin) is None:
        raise GovernancePolicyError("amount_min malformed/negative", code="invalid_amount")
    if amax is not None and coerce_policy_amount(amax) is None:
        raise GovernancePolicyError("amount_max malformed/negative", code="invalid_amount")

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
        pid = (policy_id or "").strip() or mint_policy_id()
        ts = now_utc_iso()
        eff_from = (effective_from or "").strip() or ts
        c.execute(
            """
            INSERT INTO core_governance_policies (
              policy_id, policy_version, entity_id, scope_id, action_type, request_type,
              required_permission_code, authority_required, approval_required,
              required_decision_count, evidence_required, prohibited,
              amount_min, amount_max, currency,
              effective_from, effective_to, status,
              created_at, updated_at, created_by_person_id
            ) VALUES (
              ?, ?, ?, ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?
            )
            """,
            (
                pid,
                int(policy_version),
                eid,
                (scope_id or "").strip() or None,
                at,
                (request_type or "").strip().upper() or None,
                (required_permission_code or "").strip() or None,
                int(authority_required),
                ar,
                rdc,
                int(evidence_required),
                int(prohibited),
                amin,
                amax,
                cur,
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
        out = get_governance_policy(pid, int(policy_version), conn=c)
        assert out is not None
        return out
    finally:
        if own:
            c.close()


def evaluate_governance_policy(
    entity_id: str,
    action_type: str,
    *,
    scope_id: str | None = None,
    request_type: str | None = None,
    amount: Any = None,
    currency: str | None = None,
    as_of: str | datetime | None = None,
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    audit: bool = True,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Fail-closed matcher + precedence + conflict.

    Returns explainable dict. Does not grant Permission or Authority.
    """
    eid = (entity_id or "").strip()
    at = (action_type or "").strip().upper()
    if not eid:
        raise GovernancePolicyError("entity_id required", code="missing_entity")
    if not at:
        raise GovernancePolicyError("action_type required", code="missing_action_type")

    sid = (scope_id or "").strip() or None
    rt = (request_type or "").strip().upper() or None
    cur = (currency or "").strip().upper() or None

    if isinstance(as_of, datetime):
        at_dt = as_of if as_of.tzinfo else as_of.replace(tzinfo=TZ_UTC)
    else:
        at_dt = _parse_iso(str(as_of)) if as_of else datetime.now(TZ_UTC)
        if at_dt is None:
            at_dt = datetime.now(TZ_UTC)

    out = _base_result(
        entity_id=eid,
        scope_id=sid,
        action_type=at,
        request_type=rt,
        amount=amount,
        currency=cur,
    )

    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_governance_policies
            WHERE entity_id=? AND action_type=? AND status='ACTIVE'
            """,
            (eid, at),
        ).fetchall()
        policies = [dict(r) for r in rows]

        # Scope + effective + optional request_type filter
        scoped: list[dict[str, Any]] = []
        for pol in policies:
            if not _effective(pol, at_dt):
                continue
            pol_scope = (pol.get("scope_id") or "").strip() or None
            if pol_scope is not None and pol_scope != sid:
                continue
            pol_rt = (pol.get("request_type") or "").strip().upper() or None
            if pol_rt is not None and rt is not None and pol_rt != rt:
                continue
            if pol_rt is not None and rt is None:
                continue
            scoped.append(pol)

        # Amount-governed gate: material action OR any scoped candidate has amount band
        any_band = any(_has_amount_band(p) for p in scoped)
        amount_governed = at in AMOUNT_GOVERNED_ACTIONS or any_band
        parsed_amount: Decimal | None = None
        if amount_governed:
            parsed_amount = coerce_policy_amount(amount)
            if parsed_amount is None:
                out["result"] = "MISSING_AMOUNT"
                out["reason_code"] = "missing_amount"
                out["candidates"] = [
                    {"policy_id": p["policy_id"], "policy_version": p["policy_version"]}
                    for p in scoped
                ]
                if audit:
                    _audit_policy(
                        action="policy.evaluated",
                        result="DENIED",
                        evaluation=out,
                        reason_code="missing_amount",
                        verified_person_id=verified_person_id,
                        identity=identity,
                        conn=c,
                    )
                    if own:
                        c.commit()
                return out

        # Amount/currency band filter
        matched: list[dict[str, Any]] = []
        for pol in scoped:
            if _amount_in_band(pol, parsed_amount, cur):
                matched.append(pol)

        out["candidates"] = [
            {
                "policy_id": p["policy_id"],
                "policy_version": p["policy_version"],
                "scope_id": p.get("scope_id"),
                "band_specificity": _band_specificity(p),
            }
            for p in matched
        ]

        if not matched:
            out["result"] = "NO_MATCH"
            out["reason_code"] = "no_matching_policy"
            if audit:
                _audit_policy(
                    action="policy.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="no_matching_policy",
                    verified_person_id=verified_person_id,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        # Precedence: keep only top specificity; same policy_id collapse to highest version first
        by_id: dict[str, dict[str, Any]] = {}
        for pol in matched:
            pid = pol["policy_id"]
            prev = by_id.get(pid)
            if prev is None or int(pol["policy_version"]) > int(prev["policy_version"]):
                by_id[pid] = pol
        distinct = list(by_id.values())

        best_key = max(_specificity_key(p) for p in distinct)
        winners = [p for p in distinct if _specificity_key(p) == best_key]

        if len(winners) > 1:
            out["result"] = "CONFLICT"
            out["reason_code"] = "policy_conflict"
            out["candidates"] = [
                {
                    "policy_id": p["policy_id"],
                    "policy_version": p["policy_version"],
                    "scope_id": p.get("scope_id"),
                    "band_specificity": _band_specificity(p),
                }
                for p in winners
            ]
            if audit:
                _audit_policy(
                    action="policy.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="policy_conflict",
                    verified_person_id=verified_person_id,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        winner = winners[0]
        if int(winner.get("prohibited") or 0):
            out["matched_policy_id"] = winner["policy_id"]
            out["matched_policy_version"] = int(winner["policy_version"])
            out["permission_required"] = winner.get("required_permission_code")
            out["authority_required"] = int(winner.get("authority_required") or 0)
            out["approvals_required"] = int(winner.get("required_decision_count") or 0)
            out["evidence_required"] = int(winner.get("evidence_required") or 0)
            out["result"] = "PROHIBITED"
            out["reason_code"] = "action_prohibited"
            if audit:
                _audit_policy(
                    action="policy.evaluated",
                    result="DENIED",
                    evaluation=out,
                    reason_code="action_prohibited",
                    verified_person_id=verified_person_id,
                    identity=identity,
                    conn=c,
                )
                if own:
                    c.commit()
            return out

        out["matched_policy_id"] = winner["policy_id"]
        out["matched_policy_version"] = int(winner["policy_version"])
        out["permission_required"] = winner.get("required_permission_code")
        out["authority_required"] = int(winner.get("authority_required") or 0)
        out["approvals_required"] = int(winner.get("required_decision_count") or 0)
        out["evidence_required"] = int(winner.get("evidence_required") or 0)
        out["result"] = "REQUIREMENTS"
        out["reason_code"] = "policy_matched"
        if audit:
            _audit_policy(
                action="policy.evaluated",
                result="ALLOWED",
                evaluation=out,
                reason_code="policy_matched",
                verified_person_id=verified_person_id,
                identity=identity,
                conn=c,
            )
            if own:
                c.commit()
        return out
    finally:
        if own:
            c.close()
