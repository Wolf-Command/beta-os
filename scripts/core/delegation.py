#!/usr/bin/env python3
"""Wolf Core Delegation — deterministic grant evaluator (Beta).

IDENTITY NEVER DELEGATES. Actor = authenticated Person always.
Delegation does not create power; grant ≤ what delegator currently holds.
NO RE-DELEGATION. No dual/SoD/UI/LLM. Live Authority Limits stay 0.
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
from core import authority as _authority
from core import rbac as _rbac
from core import work_items as _work_items

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
TZ_UTC = timezone.utc

STATUSES = frozenset({"SCHEDULED", "ACTIVE", "EXPIRED", "REVOKED"})
PERS_MATT = "PERS-MATT"

HONESTY = {
    "redelegation": "DENIED",
    "impersonation": "BLOCKED",
    "dual_approval": "BUILT",
    "segregation_of_duties": "NOT_BUILT",
    "delegation_ui": "NOT_BUILT",
    "ai_delegate": False,
    "identity_never_delegates": True,
}


class DelegationError(ValueError):
    """Fail-closed validation / state error."""

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
        raise DelegationError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"delegation refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"delegation refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"delegation refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_delegation_id() -> str:
    return f"DLG-{uuid.uuid4()}"


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


def _parse_amount(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return Decimal(s)
        except InvalidOperation:
            return None
    return None


def _amount_str(d: Decimal | None) -> str | None:
    if d is None:
        return None
    # Normalize without scientific notation
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _audit_delegation(
    *,
    action: str,
    result: str,
    delegation: dict[str, Any] | None,
    verified_person_id: str | None,
    identity: dict[str, Any] | None = None,
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    meta = dict(metadata or {})
    if delegation:
        meta.setdefault("delegation_id", delegation.get("delegation_id"))
        meta.setdefault("permission_code", delegation.get("permission_code"))
        meta.setdefault("status", delegation.get("status"))
        if delegation.get("delegated_cap_amount") is not None:
            meta.setdefault("amount", delegation.get("delegated_cap_amount"))
        if delegation.get("currency"):
            meta.setdefault("currency", delegation.get("currency"))
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "delegation",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": (delegation or {}).get("entity_id"),
        "resource_type": "delegation",
        "resource_id": (delegation or {}).get("delegation_id"),
        "reason_code": reason_code,
        "correlation_id": identity.get("correlation_id")
        or (delegation or {}).get("correlation_id")
        or _audit.mint_correlation_id(),
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


def _assignment_active(conn: sqlite3.Connection, assignment_id: str, person_id: str) -> bool:
    row = conn.execute(
        """
        SELECT assignment_id, person_id, status, end_at
        FROM org_assignments WHERE assignment_id=?
        """,
        (assignment_id,),
    ).fetchone()
    return bool(
        row
        and row["person_id"] == person_id
        and row["status"] == "ACTIVE"
        and row["end_at"] is None
    )


def _lazy_status(row: dict[str, Any], conn: sqlite3.Connection, *, now: str | None = None) -> dict[str, Any]:
    """SCHEDULED→ACTIVE / ACTIVE→EXPIRED. REVOKED sticky. Mutates DB."""
    if row.get("status") == "REVOKED":
        return row
    ts = now or now_utc_iso()
    now_dt = _parse_iso(ts) or datetime.now(TZ_UTC)
    ef = _parse_iso(row.get("effective_from"))
    et = _parse_iso(row.get("effective_to"))
    if ef is None or et is None:
        return row
    desired = row.get("status")
    if now_dt >= et:
        desired = "EXPIRED"
    elif now_dt >= ef:
        desired = "ACTIVE"
    else:
        desired = "SCHEDULED"
    if desired != row.get("status") and row.get("status") != "REVOKED":
        conn.execute(
            "UPDATE core_delegations SET status=? WHERE delegation_id=? AND status != 'REVOKED'",
            (desired, row["delegation_id"]),
        )
        row = _row(
            conn.execute(
                "SELECT * FROM core_delegations WHERE delegation_id=?",
                (row["delegation_id"],),
            ).fetchone()
        ) or row
    return row


def get_delegation(
    delegation_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    lazy: bool = True,
) -> dict[str, Any] | None:
    did = (delegation_id or "").strip()
    if not did:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        row = _row(
            c.execute("SELECT * FROM core_delegations WHERE delegation_id=?", (did,)).fetchone()
        )
        if not row:
            return None
        if lazy:
            row = _lazy_status(row, c)
            if own:
                c.commit()
        return row
    finally:
        if own:
            c.close()


def list_delegations(
    person_id: str,
    *,
    status: str | None = None,
    entity_id: str | None = None,
    delegator_person_id: str | None = None,
    delegate_person_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        visible = _work_items.visible_entity_ids_for_person(pid, conn=c)
        if not visible:
            return []
        if entity_id:
            eid = entity_id.strip()
            if eid not in visible:
                return []
            entities = [eid]
        else:
            entities = sorted(visible)

        # Lazy-refresh rows in window
        rows = c.execute(
            f"""
            SELECT * FROM core_delegations
            WHERE entity_id IN ({",".join("?" * len(entities))})
              AND status IN ('SCHEDULED','ACTIVE')
            """,
            entities,
        ).fetchall()
        for r in rows:
            _lazy_status(dict(r), c)

        clauses = [f"entity_id IN ({','.join('?' * len(entities))})"]
        params: list[Any] = list(entities)
        if status:
            st = status.strip().upper()
            if st not in STATUSES:
                raise DelegationError(f"invalid status filter: {status!r}")
            clauses.append("status=?")
            params.append(st)
        if delegator_person_id:
            clauses.append("delegator_person_id=?")
            params.append(delegator_person_id.strip())
        if delegate_person_id:
            clauses.append("delegate_person_id=?")
            params.append(delegate_person_id.strip())
        lim = max(1, min(int(limit), 200))
        off = max(0, int(offset))
        params.extend([lim, off])
        out = c.execute(
            f"""
            SELECT * FROM core_delegations
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        if own:
            c.commit()
        return [dict(r) for r in out]
    finally:
        if own:
            c.close()



def _scope_covers_entity(scope_id: str, entity_id: str, conn: sqlite3.Connection) -> bool:
    """True if scope targets entity directly or any child under that entity."""
    from core import scope as _scope

    eid = (entity_id or "").strip()
    if not eid:
        return False
    if _rbac._scope_covers_target(scope_id, {"entity_id": eid}, conn):
        return True
    ctx = _scope.resolve_effective_scope_context(scope_id, conn=conn)
    covered = ctx.get("structurally_covered") or {}
    for did in covered.get("departments") or []:
        row = conn.execute(
            "SELECT entity_id FROM org_departments WHERE department_id=?", (did,)
        ).fetchone()
        if row and row[0] == eid:
            return True
    for bid in covered.get("brands") or []:
        row = conn.execute(
            "SELECT entity_id FROM org_brands WHERE brand_id=?", (bid,)
        ).fetchone()
        if row and row[0] == eid:
            return True
    for lid in covered.get("locations") or []:
        row = conn.execute(
            "SELECT entity_id FROM org_locations WHERE location_id=?", (lid,)
        ).fetchone()
        if row and row[0] == eid:
            return True
    return False


def create_delegation(
    *,
    verified_person_id: str,
    delegate_person_id: str,
    delegator_assignment_id: str,
    delegate_assignment_id: str,
    entity_id: str,
    scope_id: str,
    permission_code: str,
    effective_from: str,
    effective_to: str,
    delegator_person_id: str | None = None,
    delegated_cap_amount: str | None = None,
    currency: str | None = None,
    authority_limit_id: str | None = None,
    reason: str | None = None,
    linked_work_item_id: str | None = None,
    allow_redelegation: int = 0,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create a delegation. Identity never rewritten; actor = verified."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise DelegationError("verified_person_id required", code="missing_verified_person")

    # Client cannot forge delegator: must be verified or Matt creating for another
    requested_delegator = (delegator_person_id or "").strip() or verified
    if requested_delegator != verified and verified != PERS_MATT:
        raise DelegationError(
            "delegator_person_id must match verified identity; client spoof refused",
            code="forged_delegator",
            http_status=400,
        )
    # This slice: creator must be delegator or Matt
    if verified != requested_delegator and verified != PERS_MATT:
        raise DelegationError(
            "only delegator or Matt may create",
            code="create_forbidden",
            http_status=403,
        )
    delegator = requested_delegator

    delegate = (delegate_person_id or "").strip()
    if not delegate:
        raise DelegationError("delegate_person_id required", code="missing_delegate")
    if delegator == delegate:
        raise DelegationError(
            "delegator cannot equal delegate",
            code="self_delegation",
            http_status=400,
        )

    if int(allow_redelegation or 0) != 0:
        raise DelegationError(
            "re-delegation denied (allow_redelegation must be 0)",
            code="redelegation_denied",
            http_status=403,
        )

    eid = (entity_id or "").strip()
    sid = (scope_id or "").strip()
    code = (permission_code or "").strip()
    asg_delegator = (delegator_assignment_id or "").strip()
    asg_delegate = (delegate_assignment_id or "").strip()
    if not eid or not sid or not code or not asg_delegator or not asg_delegate:
        raise DelegationError("entity_id, scope_id, permission_code, and both assignment_ids required")

    ef = _parse_iso(effective_from)
    et = _parse_iso(effective_to)
    if ef is None or et is None:
        raise DelegationError("effective_from/effective_to must be ISO timestamps", code="invalid_window")
    if not (et > ef):
        raise DelegationError("effective_to must be > effective_from", code="invalid_window")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))

        # RBAC gate: verified needs delegation.create (Matt governance path)
        create_ev = _rbac.evaluate(verified, "delegation.create", {"entity_id": eid}, conn=c)
        if not create_ev.get("allowed"):
            raise DelegationError(
                "delegation.create denied",
                code="rbac_denied",
                http_status=403,
            )

        ent = c.execute(
            "SELECT entity_id FROM org_entities WHERE entity_id=?", (eid,)
        ).fetchone()
        if not ent:
            raise DelegationError(f"unknown entity: {eid}", code="unknown_entity", http_status=404)

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?", (sid,)
        ).fetchone()
        if not scope_row or scope_row["status"] != "ACTIVE":
            raise DelegationError(f"unknown or inactive scope: {sid}", code="unknown_scope", http_status=404)

        # Scope must be bound to delegator assignment and cover entity
        bound = c.execute(
            """
            SELECT 1 FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (asg_delegator, sid),
        ).fetchone()
        if not bound:
            raise DelegationError(
                "scope not bound to delegator assignment",
                code="scope_not_bound",
                http_status=403,
            )
        # Scope must cover the entity (direct entity target OR child dept/brand/loc under it)
        if not _scope_covers_entity(sid, eid, c):
            raise DelegationError(
                "scope does not cover entity",
                code="scope_mismatch",
                http_status=403,
            )

        if not _assignment_active(c, asg_delegator, delegator):
            raise DelegationError(
                "delegator assignment not ACTIVE",
                code="inactive_assignment",
                http_status=403,
            )
        if not _assignment_active(c, asg_delegate, delegate):
            raise DelegationError(
                "delegate assignment not ACTIVE",
                code="inactive_assignment",
                http_status=403,
            )

        perm = _rbac.get_permission_by_code(code, conn=c)
        if not perm or perm.get("status") != "ACTIVE":
            raise DelegationError(f"unknown or inactive permission: {code}", code="unknown_permission")
        perm_id = perm["permission_id"]
        if perm.get("code") != code:
            raise DelegationError("permission_code mismatch", code="permission_mismatch")

        # Delegator must NATIVE-hold the permission (no re-delegation of delegated power)
        target = {"entity_id": eid}
        native = _rbac.evaluate(delegator, code, target, conn=c)
        if not native.get("allowed"):
            raise DelegationError(
                "delegator does not hold permission natively",
                code="delegator_lacks_permission",
                http_status=403,
            )

        cap_raw = (str(delegated_cap_amount).strip() if delegated_cap_amount is not None else None) or None
        cur = (currency or "").strip() or None
        cap_amt = _parse_amount(cap_raw) if cap_raw is not None else None
        if cap_raw is not None:
            if cap_amt is None:
                raise DelegationError("malformed delegated_cap_amount", code="malformed_amount")
            if cap_amt < 0:
                raise DelegationError("delegated_cap_amount must be >= 0", code="negative_amount")
            if not cur:
                raise DelegationError("currency required when delegated_cap_amount set", code="missing_currency")
            # Delegator must within_authority for at least that amount
            auth = _authority.within_authority(
                delegator,
                code,
                target,
                {"amount": _amount_str(cap_amt), "currency": cur},
                conn=c,
            )
            if not auth.get("allowed"):
                raise DelegationError(
                    f"delegator lacks authority for cap: {auth.get('reason')}",
                    code="authority_exceeded",
                    http_status=403,
                )

        # Initial status from window
        ts = now_utc_iso()
        now_dt = _parse_iso(ts) or datetime.now(TZ_UTC)
        if now_dt >= et:
            raise DelegationError("effective_to already passed", code="already_expired")
        if now_dt >= ef:
            status = "ACTIVE"
        else:
            status = "SCHEDULED"

        did = mint_delegation_id()
        corr = (identity or {}).get("correlation_id") or _audit.mint_correlation_id()
        c.execute(
            """
            INSERT INTO core_delegations (
              delegation_id, delegator_person_id, delegator_assignment_id,
              delegate_person_id, delegate_assignment_id,
              entity_id, scope_id, permission_id, permission_code,
              authority_limit_id, delegated_cap_amount, currency,
              effective_from, effective_to, status, reason,
              created_at, created_by_person_id, correlation_id,
              allow_redelegation, linked_work_item_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                did,
                delegator,
                asg_delegator,
                delegate,
                asg_delegate,
                eid,
                sid,
                perm_id,
                code,
                (authority_limit_id or "").strip() or None,
                _amount_str(cap_amt) if cap_amt is not None else None,
                cur,
                effective_from if "T" in str(effective_from) else ef.isoformat(),
                effective_to if "T" in str(effective_to) else et.isoformat(),
                status,
                (reason or "").strip() or None,
                ts,
                verified,
                corr,
                (linked_work_item_id or "").strip() or None,
            ),
        )
        row = get_delegation(did, conn=c, lazy=False)
        assert row is not None
        _audit_delegation(
            action="delegation.created",
            result="SUCCEEDED",
            delegation=row,
            verified_person_id=verified,
            identity=identity,
            metadata={"status": status, "permission_code": code},
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


def revoke_delegation(
    delegation_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise DelegationError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_delegation(delegation_id, conn=c, lazy=True)
        if not row:
            raise DelegationError("delegation not found", code="not_found", http_status=404)
        if row["status"] == "REVOKED":
            raise DelegationError("already revoked", code="already_revoked", http_status=409)

        ev = _rbac.evaluate(
            verified, "delegation.revoke", {"entity_id": row["entity_id"]}, conn=c
        )
        if not ev.get("allowed"):
            raise DelegationError(
                "delegation.revoke denied",
                code="rbac_denied",
                http_status=403,
            )
        is_delegator = verified == row["delegator_person_id"]
        is_matt = verified == PERS_MATT
        if not is_delegator and not is_matt:
            raise DelegationError(
                "only delegator or Matt may revoke",
                code="revoke_forbidden",
                http_status=403,
            )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_delegations
            SET status='REVOKED', revoked_at=?, revoked_by_person_id=?, revoke_reason=?
            WHERE delegation_id=? AND status != 'REVOKED'
            """,
            (ts, verified, (reason or "").strip() or None, row["delegation_id"]),
        )
        updated = get_delegation(row["delegation_id"], conn=c, lazy=False)
        assert updated is not None
        _audit_delegation(
            action="delegation.revoked",
            result="SUCCEEDED",
            delegation=updated,
            verified_person_id=verified,
            identity=identity,
            reason_code=(reason or "").strip() or None,
            metadata={"status": "REVOKED"},
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(updated)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def evaluate_delegation(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    amount_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Fail-closed use-time evaluator. No re-delegation chains."""
    out: dict[str, Any] = {
        "allowed": False,
        "reason": "deny_by_default",
        "delegation_id": None,
        "delegator_person_id": None,
        "effective_cap_amount": None,
        "currency": None,
        "evaluator": "core.delegation.evaluate_delegation",
        **HONESTY,
    }
    pid = (person_id or "").strip()
    code = (permission_code or "").strip()
    if not pid or not code:
        out["reason"] = "missing_person_or_permission"
        return out

    own = conn is None
    c = conn or db_connect()
    try:
        target = target_context or {}
        eid = (target.get("entity_id") or "").strip()
        if not eid:
            out["reason"] = "missing_entity"
            return out

        rows = c.execute(
            """
            SELECT * FROM core_delegations
            WHERE delegate_person_id=?
              AND permission_code=?
              AND entity_id=?
              AND status IN ('SCHEDULED','ACTIVE')
            ORDER BY created_at DESC
            """,
            (pid, code, eid),
        ).fetchall()

        amt_ctx = amount_context or {}
        amount = _parse_amount(amt_ctx.get("amount")) if "amount" in amt_ctx else None
        currency = (str(amt_ctx.get("currency")).strip() if amt_ctx.get("currency") else None) or None

        for raw in rows:
            row = _lazy_status(dict(raw), c)
            if row.get("status") != "ACTIVE":
                continue

            # Scope covers target — no widen
            if not _rbac._scope_covers_target(row["scope_id"], target, c):
                continue

            # Delegate assignment still ACTIVE
            if not _assignment_active(c, row["delegate_assignment_id"], pid):
                out["reason"] = "delegate_assignment_inactive"
                continue

            # Delegator assignment still ACTIVE
            if not _assignment_active(
                c, row["delegator_assignment_id"], row["delegator_person_id"]
            ):
                out["reason"] = "delegator_assignment_inactive"
                continue

            # Delegator still holds NATIVE RBAC
            native = _rbac.evaluate(row["delegator_person_id"], code, target, conn=c)
            if not native.get("allowed"):
                out["reason"] = "delegator_lost_permission"
                continue

            # Amount / cap rules
            grant_cap = _parse_amount(row.get("delegated_cap_amount"))
            grant_cur = (row.get("currency") or "").strip() or None
            effective_cap: Decimal | None = None
            eff_cur = grant_cur

            if amount is not None or ("amount" in amt_ctx and amt_ctx.get("amount") is not None):
                if amount is None:
                    out["reason"] = "malformed_amount"
                    continue
                if amount < 0:
                    out["reason"] = "negative_amount"
                    continue

                # Need delegator capacity via within_authority (probe threshold)
                probe_cur = currency or grant_cur
                if not probe_cur:
                    out["reason"] = "missing_currency"
                    continue
                auth = _authority.within_authority(
                    row["delegator_person_id"],
                    code,
                    target,
                    {"amount": _amount_str(amount), "currency": probe_cur},
                    conn=c,
                )
                matched = auth.get("matched_limit") or {}
                threshold = auth.get("threshold_value")
                if threshold is None and matched.get("threshold_value") is not None:
                    threshold = matched.get("threshold_value")
                thresh_dec = _parse_amount(threshold) if threshold is not None else None

                if grant_cap is not None:
                    if grant_cur and currency and grant_cur != currency:
                        out["reason"] = "currency_mismatch"
                        continue
                    if thresh_dec is not None:
                        effective_cap = min(grant_cap, thresh_dec)
                    else:
                        # No live limit for delegator → fail closed
                        out["reason"] = "delegator_authority_invalid"
                        continue
                    if amount > effective_cap:
                        out["reason"] = "above_delegated_cap"
                        out["delegation_id"] = row["delegation_id"]
                        out["delegator_person_id"] = row["delegator_person_id"]
                        out["effective_cap_amount"] = _amount_str(effective_cap)
                        out["currency"] = grant_cur or probe_cur
                        continue
                else:
                    # No grant cap: fall through to within_authority on delegator
                    if not auth.get("allowed"):
                        out["reason"] = auth.get("reason") or "delegator_authority_denied"
                        out["delegation_id"] = row["delegation_id"]
                        continue
                    effective_cap = thresh_dec
                    eff_cur = probe_cur

            out["allowed"] = True
            out["reason"] = "delegation_allow"
            out["delegation_id"] = row["delegation_id"]
            out["delegator_person_id"] = row["delegator_person_id"]
            out["effective_cap_amount"] = _amount_str(effective_cap) if effective_cap is not None else (
                _amount_str(grant_cap) if grant_cap is not None else None
            )
            out["currency"] = eff_cur or grant_cur
            if own:
                c.commit()
            return out

        if out["reason"] == "deny_by_default":
            out["reason"] = "no_valid_delegation"
        if own:
            c.commit()
        return out
    finally:
        if own:
            c.close()


def effective_permission(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    amount_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Native RBAC first; else valid delegation; else deny."""
    own = conn is None
    c = conn or db_connect()
    try:
        native = _rbac.evaluate(person_id, permission_code, target_context, conn=c)
        if native.get("allowed"):
            return {
                "allowed": True,
                "basis": "NATIVE",
                "reason": native.get("reason") or "allow",
                "delegation_id": None,
                "rbac": native,
                "delegation": None,
            }
        dlg = evaluate_delegation(
            person_id, permission_code, target_context, amount_context, conn=c
        )
        if dlg.get("allowed"):
            return {
                "allowed": True,
                "basis": "DELEGATION",
                "reason": dlg.get("reason") or "delegation_allow",
                "delegation_id": dlg.get("delegation_id"),
                "rbac": native,
                "delegation": dlg,
            }
        return {
            "allowed": False,
            "basis": None,
            "reason": dlg.get("reason") or native.get("reason") or "deny",
            "delegation_id": None,
            "rbac": native,
            "delegation": dlg,
        }
    finally:
        if own:
            c.close()
