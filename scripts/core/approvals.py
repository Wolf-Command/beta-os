#!/usr/bin/env python3
"""Wolf Core Approval Engine — deterministic REQUEST → decide (Beta).

REQUESTED ≠ APPROVED ≠ EXECUTED ≠ OUTCOME.
Authority = capacity; Approval = specific decision evidence.
Approval never creates Authority. Completing a linked Work Item ≠ approving.
Dual / SoD / UI / LLM = NOT BUILT. Delegation evaluator = BUILT (identity never delegates).
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import authority as _authority
from core import organisation as _org
from core import rbac as _rbac
from core import work_items as _work_items
from core import delegation as _delegation

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
TZ_UTC = timezone.utc

REQUEST_TYPES = frozenset({"GENERAL", "SPEND", "EXCEPTION", "ACCESS", "HR", "CONTRACT"})
SOURCE_TYPES = frozenset({"HUMAN", "SYSTEM", "WORK_ITEM", "EXTERNAL"})
STATUSES = frozenset({"PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"})
TERMINAL = frozenset({"APPROVED", "REJECTED", "CANCELLED", "EXPIRED"})
DECISIONS = frozenset({"APPROVED", "REJECTED"})
MATERIAL_TYPES = frozenset({"SPEND", "EXCEPTION"})

# Policy flag — readable at decide time; default ON (deny self-approval on material).
ENV_DENY_SELF = "BETA_APPROVAL_DENY_SELF_APPROVAL"

IMMUTABLE_FIELDS = frozenset(
    {
        "owning_entity_id",
        "brand_id",
        "location_id",
        "department_id",
        "required_permission_code",
        "required_permission_id",
        "material_amount",
        "currency",
        "source_type",
        "source_id",
    }
)

HONESTY = {
    "dual_approval": "NOT_BUILT",
    "segregation_of_duties": "NOT_BUILT",
    "delegation": "BUILT",
    "approval_ui": "NOT_BUILT",
    "ai_approver": False,
    "requested_is_not_approved": True,
    "approved_is_not_executed": True,
}

PERS_MATT = "PERS-MATT"


class ApprovalError(ValueError):
    """Fail-closed validation / state error."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def deny_self_approval_enabled() -> bool:
    """Later policy can flip without schema rewrite."""
    raw = (os.environ.get(ENV_DENY_SELF) or "1").strip()
    return raw not in ("0", "false", "False", "no", "off")


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    import sys

    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path) -> None:
    """Refuse accidental live catalog writes from tests (same pattern as audit)."""
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise ApprovalError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"approvals refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"approvals refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"approvals refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_request_id() -> str:
    return f"APR-{uuid.uuid4()}"


def mint_decision_id() -> str:
    return f"APD-{uuid.uuid4()}"


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


def compute_snapshot_hash(
    *,
    owning_entity_id: str,
    brand_id: str | None,
    location_id: str | None,
    department_id: str | None,
    required_permission_code: str,
    required_permission_id: str,
    material_amount: str | None,
    currency: str | None,
    source_type: str,
    source_id: str | None,
) -> str:
    parts = [
        owning_entity_id or "",
        brand_id or "",
        location_id or "",
        department_id or "",
        required_permission_code or "",
        required_permission_id or "",
        material_amount or "",
        currency or "",
        source_type or "",
        source_id or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def is_material_request(req: dict[str, Any]) -> bool:
    amt = req.get("material_amount")
    if amt is not None and str(amt).strip() != "":
        return True
    return (req.get("request_type") or "").upper() in MATERIAL_TYPES


def target_context_for_request(req: dict[str, Any]) -> dict[str, Any]:
    ctx: dict[str, Any] = {"entity_id": req.get("owning_entity_id")}
    for k_src, k_dst in (
        ("brand_id", "brand_id"),
        ("location_id", "location_id"),
        ("department_id", "department_id"),
    ):
        v = req.get(k_src)
        if v:
            ctx[k_dst] = v
    return ctx


def _audit_approval(
    *,
    action: str,
    result: str,
    request: dict[str, Any] | None,
    verified_person_id: str | None,
    identity: dict[str, Any] | None = None,
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    identity = identity or {}
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": "approvals",
        "actor_type": "PERSON" if verified_person_id else "SYSTEM",
        "entity_id": (request or {}).get("owning_entity_id"),
        "brand_id": (request or {}).get("brand_id"),
        "location_id": (request or {}).get("location_id"),
        "department_id": (request or {}).get("department_id"),
        "resource_type": "approval_request",
        "resource_id": (request or {}).get("approval_request_id"),
        "reason_code": reason_code,
        "correlation_id": identity.get("correlation_id")
        or (request or {}).get("correlation_id")
        or _audit.mint_correlation_id(),
        "metadata": metadata,
        "conn": conn,
        "commit": False,
    }
    if verified_person_id:
        kwargs["verified_person_id"] = verified_person_id
        kwargs["actor_person_id"] = verified_person_id
        kwargs["actor_auth_identity_id"] = identity.get("auth_identity_id")
        kwargs["identity_assurance"] = identity.get("identity_assurance")
    _audit.safe_record(**kwargs)


def _maybe_expire(req: dict[str, Any], conn: sqlite3.Connection, *, now: str | None = None) -> dict[str, Any]:
    """Lazy expire PENDING when expires_at <= now. Mutates DB."""
    if req.get("status") != "PENDING":
        return req
    exp = _parse_iso(req.get("expires_at"))
    if exp is None:
        return req
    ts = now or now_utc_iso()
    now_dt = _parse_iso(ts) or datetime.now(TZ_UTC)
    if now_dt < exp:
        return req
    conn.execute(
        """
        UPDATE core_approval_requests
        SET status='EXPIRED', updated_at=?, decided_at=?
        WHERE approval_request_id=? AND status='PENDING'
        """,
        (ts, ts, req["approval_request_id"]),
    )
    updated = get_approval_request(req["approval_request_id"], conn=conn, expire=False)
    assert updated is not None
    _audit_approval(
        action="approval.expired",
        result="SUCCEEDED",
        request=updated,
        verified_person_id=None,
        reason_code="expired",
        metadata={"status": "EXPIRED"},
        conn=conn,
    )
    return updated


def get_approval_request(
    approval_request_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    expire: bool = True,
) -> dict[str, Any] | None:
    rid = (approval_request_id or "").strip()
    if not rid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        row = _row(
            c.execute(
                "SELECT * FROM core_approval_requests WHERE approval_request_id=?",
                (rid,),
            ).fetchone()
        )
        if not row:
            return None
        if expire:
            row = _maybe_expire(row, c)
            if own:
                c.commit()
        return row
    finally:
        if own:
            c.close()


def list_approval_requests(
    person_id: str,
    *,
    status: str | None = None,
    owning_entity_id: str | None = None,
    requested_by_person_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """List requests visible via the person's Assignment entity scopes."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        visible = _work_items.visible_entity_ids_for_person(pid, conn=c)
        if not visible:
            return []
        if owning_entity_id:
            eid = owning_entity_id.strip()
            if eid not in visible:
                return []
            entities = [eid]
        else:
            entities = sorted(visible)

        # Lazy-expire matching PENDING rows first
        pending = c.execute(
            f"""
            SELECT * FROM core_approval_requests
            WHERE status='PENDING'
              AND expires_at IS NOT NULL
              AND owning_entity_id IN ({','.join('?' * len(entities))})
            """,
            entities,
        ).fetchall()
        for prow in pending:
            _maybe_expire(dict(prow), c)

        clauses = [f"owning_entity_id IN ({','.join('?' * len(entities))})"]
        params: list[Any] = list(entities)
        if status:
            st = status.strip().upper()
            if st not in STATUSES:
                raise ApprovalError(f"invalid status filter: {status!r}")
            clauses.append("status=?")
            params.append(st)
        if requested_by_person_id:
            clauses.append("requested_by_person_id=?")
            params.append(requested_by_person_id.strip())

        lim = max(1, min(int(limit or 50), 200))
        off = max(0, int(offset or 0))
        rows = c.execute(
            f"""
            SELECT * FROM core_approval_requests
            WHERE {' AND '.join(clauses)}
            ORDER BY requested_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, lim, off),
        ).fetchall()
        if own:
            c.commit()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_decisions(
    approval_request_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    rid = (approval_request_id or "").strip()
    if not rid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        return [
            dict(r)
            for r in c.execute(
                """
                SELECT * FROM core_approval_decisions
                WHERE approval_request_id=?
                ORDER BY decided_at ASC, created_at ASC
                """,
                (rid,),
            ).fetchall()
        ]
    finally:
        if own:
            c.close()


def refuse_immutable_mutation(fields: dict[str, Any]) -> None:
    """Any attempt to change immutable material fields → 400."""
    hit = [k for k in fields if k in IMMUTABLE_FIELDS]
    if hit:
        raise ApprovalError(
            f"immutable fields cannot change: {hit}; cancel and create new with prior_request_id",
            code="immutable_fields",
            http_status=400,
        )


def create_approval_request(
    *,
    title: str,
    owning_entity_id: str,
    required_permission_code: str,
    verified_person_id: str,
    request_type: str = "GENERAL",
    description: str | None = None,
    brand_id: str | None = None,
    location_id: str | None = None,
    department_id: str | None = None,
    requested_by_assignment_id: str | None = None,
    material_amount: str | None = None,
    currency: str | None = None,
    source_type: str = "HUMAN",
    source_id: str | None = None,
    evidence_reference: str | None = None,
    expires_at: str | None = None,
    prior_request_id: str | None = None,
    link_work_item: bool = False,
    review_owner_person_id: str | None = None,
    # Client-supplied actor fields ignored (spoof refused)
    requested_by_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create PENDING approval request. Identity from verified_person_id only."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ApprovalError("verified_person_id required", code="missing_verified_person")
    if requested_by_person_id and requested_by_person_id.strip() != verified:
        raise ApprovalError(
            "requested_by_person_id must match verified identity; client spoof refused",
            code="forged_requester",
            http_status=400,
        )

    t = (title or "").strip()
    if not t:
        raise ApprovalError("title required", code="missing_title")
    eid = (owning_entity_id or "").strip()
    if not eid:
        raise ApprovalError("owning_entity_id required", code="missing_entity")
    rt = (request_type or "").strip().upper()
    if rt not in REQUEST_TYPES:
        raise ApprovalError(f"invalid request_type: {request_type!r}", code="invalid_request_type")
    st = (source_type or "").strip().upper()
    if st not in SOURCE_TYPES:
        raise ApprovalError(f"invalid source_type: {source_type!r}", code="invalid_source_type")
    code = (required_permission_code or "").strip()
    if not code:
        raise ApprovalError(
            "required_permission_code required", code="missing_permission_code"
        )

    amt = (str(material_amount).strip() if material_amount is not None else None) or None
    cur = (currency or "").strip().upper() or None
    if rt in MATERIAL_TYPES:
        if amt is None:
            raise ApprovalError(
                "material_amount required for SPEND/EXCEPTION",
                code="missing_amount",
            )
        if not cur:
            raise ApprovalError(
                "currency required for SPEND/EXCEPTION",
                code="missing_currency",
            )
    if amt is not None:
        parsed = _authority._coerce_amount(amt)
        if parsed is None or parsed < 0:
            raise ApprovalError("material_amount must be a non-negative decimal string", code="invalid_amount")
        if not cur:
            raise ApprovalError("currency required when material_amount set", code="missing_currency")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))

        ent = _org.get_entity(eid, conn=c)
        if not ent:
            raise ApprovalError(f"unknown owning_entity_id: {eid}", code="unknown_entity")
        if not _work_items.person_can_see_entity(verified, eid, conn=c):
            raise ApprovalError(
                f"entity out of scope: {eid}",
                code="entity_out_of_scope",
                http_status=403,
            )

        perm = _rbac.get_permission_by_code(code, conn=c)
        if not perm:
            # Allow inactive catalog codes to be stored only if ACTIVE — required at decide
            row = c.execute(
                "SELECT permission_id, code, status FROM org_permissions WHERE code=?",
                (code,),
            ).fetchone()
            if not row:
                raise ApprovalError(
                    f"unknown required_permission_code: {code}",
                    code="unknown_permission",
                )
            if row["status"] != "ACTIVE":
                raise ApprovalError(
                    f"required_permission_code not ACTIVE: {code}",
                    code="inactive_permission",
                )
            perm = dict(row)
        perm_id = perm["permission_id"]

        asg = (requested_by_assignment_id or "").strip() or None
        if asg:
            arow = c.execute(
                """
                SELECT assignment_id, person_id, status, end_at
                FROM org_assignments WHERE assignment_id=?
                """,
                (asg,),
            ).fetchone()
            if not arow:
                raise ApprovalError("unknown requested_by_assignment_id", code="unknown_assignment")
            if arow["person_id"] != verified:
                raise ApprovalError(
                    "requested_by_assignment_id must belong to requester",
                    code="assignment_person_mismatch",
                )
            if arow["status"] != "ACTIVE" or arow["end_at"] is not None:
                raise ApprovalError(
                    "requested_by_assignment_id must be ACTIVE",
                    code="inactive_assignment",
                )

        prior = (prior_request_id or "").strip() or None
        if prior:
            prow = get_approval_request(prior, conn=c, expire=False)
            if not prow:
                raise ApprovalError("prior_request_id not found", code="unknown_prior")

        rid = mint_request_id()
        ts = now_utc_iso()
        corr = (identity or {}).get("correlation_id") or _audit.mint_correlation_id()
        brand = (brand_id or "").strip() or None
        loc = (location_id or "").strip() or None
        dept = (department_id or "").strip() or None
        snap = compute_snapshot_hash(
            owning_entity_id=eid,
            brand_id=brand,
            location_id=loc,
            department_id=dept,
            required_permission_code=code,
            required_permission_id=perm_id,
            material_amount=amt,
            currency=cur,
            source_type=st,
            source_id=(source_id or "").strip() or None,
        )

        c.execute(
            """
            INSERT INTO core_approval_requests (
              approval_request_id, request_type, title, description,
              owning_entity_id, brand_id, location_id, department_id,
              requested_by_person_id, requested_by_assignment_id,
              required_permission_code, required_permission_id,
              material_amount, currency, source_type, source_id,
              evidence_reference, status, requested_at, decided_at, expires_at,
              created_at, updated_at, correlation_id, linked_work_item_id,
              prior_request_id, snapshot_hash
            ) VALUES (
              ?, ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?,
              ?, ?,
              ?, ?, ?, ?,
              ?, 'PENDING', ?, NULL, ?,
              ?, ?, ?, NULL,
              ?, ?
            )
            """,
            (
                rid,
                rt,
                t,
                (description or "").strip() or None,
                eid,
                brand,
                loc,
                dept,
                verified,
                asg,
                code,
                perm_id,
                amt,
                cur,
                st,
                (source_id or "").strip() or None,
                (evidence_reference or "").strip() or None,
                ts,
                (expires_at or "").strip() or None,
                ts,
                ts,
                corr,
                prior,
                snap,
            ),
        )

        linked_wi = None
        if link_work_item or review_owner_person_id:
            wi = _work_items.create_work_item(
                title=t,
                description=(description or "").strip() or None,
                work_type="APPROVAL_REQUIRED",
                owning_entity_id=eid,
                source_type="SYSTEM",
                source_id=rid,
                created_by_actor_type="SYSTEM",
                owner_person_id=(review_owner_person_id or "").strip() or None,
                identity=identity,
                conn=c,
                commit=False,
            )
            linked_wi = wi["work_item_id"]
            c.execute(
                """
                UPDATE core_approval_requests
                SET linked_work_item_id=?, updated_at=?
                WHERE approval_request_id=?
                """,
                (linked_wi, ts, rid),
            )

        req = get_approval_request(rid, conn=c, expire=False)
        assert req is not None
        _audit_approval(
            action="approval.requested",
            result="SUCCEEDED",
            request=req,
            verified_person_id=verified,
            identity=identity,
            metadata={
                "status": "PENDING",
                "request_type": rt,
                "amount": amt,
                "currency": cur,
                "required_permission": code,
                "linked_work_item_id": linked_wi,
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = dict(req)
        out.update(HONESTY)
        return out
    finally:
        if own:
            c.close()


def _require_active_assignment(person_id: str, conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        """
        SELECT assignment_id FROM org_assignments
        WHERE person_id=? AND status='ACTIVE' AND end_at IS NULL
        ORDER BY assignment_id LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    return row[0] if row else None


def _decide(
    approval_request_id: str,
    *,
    decision: str,
    verified_person_id: str,
    reason: str | None = None,
    decided_by_assignment_id: str | None = None,
    decided_by_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Approve or reject. First successful decision wins. Does not execute source."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ApprovalError("verified_person_id required", code="missing_verified_person")
    if decided_by_person_id and decided_by_person_id.strip() != verified:
        raise ApprovalError(
            "decided_by_person_id must match verified identity; client spoof refused",
            code="forged_decider",
            http_status=400,
        )
    dec = (decision or "").strip().upper()
    if dec not in DECISIONS:
        raise ApprovalError(f"invalid decision: {decision!r}", code="invalid_decision")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        req = get_approval_request(approval_request_id, conn=c, expire=True)
        if not req:
            raise ApprovalError("approval request not found", code="not_found", http_status=404)

        if req["status"] == "EXPIRED":
            _audit_approval(
                action="approval.decide_attempt",
                result="DENIED",
                request=req,
                verified_person_id=verified,
                identity=identity,
                reason_code="expired",
                metadata={"decision": dec, "status": "EXPIRED"},
                conn=c,
            )
            if commit:
                c.commit()
            raise ApprovalError(
                "approval request expired",
                code="expired",
                http_status=409,
            )
        if req["status"] != "PENDING":
            _audit_approval(
                action="approval.decide_attempt",
                result="DENIED",
                request=req,
                verified_person_id=verified,
                identity=identity,
                reason_code="not_pending",
                metadata={"decision": dec, "status": req.get("status")},
                conn=c,
            )
            if commit:
                c.commit()
            raise ApprovalError(
                f"request not PENDING (status={req['status']})",
                code="not_pending",
                http_status=409,
            )

        # DLG-RT-001 / APR-RT-001: material APPROVE requires amount (native + delegation)
        if dec == "APPROVED" and is_material_request(req):
            raw_amt = req.get("material_amount")
            if raw_amt is None or str(raw_amt).strip() == "":
                _audit_approval(
                    action="approval.decide_attempt",
                    result="DENIED",
                    request=req,
                    verified_person_id=verified,
                    identity=identity,
                    reason_code="missing_amount",
                    metadata={"decision": dec, "status": req.get("status")},
                    conn=c,
                )
                if commit:
                    c.commit()
                raise ApprovalError(
                    "material_amount required to approve material request",
                    code="missing_amount",
                    http_status=400,
                )

        # Self-approval (material only when flag on)
        if (
            deny_self_approval_enabled()
            and is_material_request(req)
            and verified == req["requested_by_person_id"]
        ):
            _audit_approval(
                action="approval.self_denied",
                result="DENIED",
                request=req,
                verified_person_id=verified,
                identity=identity,
                reason_code="self_approval_denied",
                metadata={"decision": dec},
                conn=c,
            )
            if commit:
                c.commit()
            raise ApprovalError(
                "self-approval denied on material request",
                code="self_approval_denied",
                http_status=403,
            )

        target = target_context_for_request(req)
        req_code = req["required_permission_code"]
        # Always include amount key for material evaluate_delegation (None → fail-closed)
        amount_ctx = None
        if is_material_request(req):
            amount_ctx = {
                "amount": req.get("material_amount"),
                "currency": req.get("currency"),
            }

        # Permission gates: native RBAC, else evaluate_delegation (identity stays verified)
        used_delegation = False
        decide_dlg_id = None
        req_dlg_id = None

        ev_decide = _rbac.evaluate(verified, "approval.decide", target, conn=c)
        if not ev_decide.get("allowed"):
            dlg_decide = _delegation.evaluate_delegation(
                verified, "approval.decide", target, None, conn=c
            )
            if dlg_decide.get("allowed"):
                used_delegation = True
                decide_dlg_id = dlg_decide.get("delegation_id")
            else:
                _audit_approval(
                    action="approval.decide_attempt",
                    result="DENIED",
                    request=req,
                    verified_person_id=verified,
                    identity=identity,
                    reason_code="rbac_denied",
                    metadata={
                        "decision": dec,
                        "permission": "approval.decide",
                        "reason": ev_decide.get("reason"),
                    },
                    conn=c,
                )
                if dlg_decide.get("delegation_id") or dlg_decide.get("reason") not in (
                    "no_valid_delegation",
                    "deny_by_default",
                    "missing_entity",
                ):
                    _delegation._audit_delegation(
                        action="delegation.denied",
                        result="DENIED",
                        delegation={"delegation_id": dlg_decide.get("delegation_id"), "entity_id": target.get("entity_id"), "permission_code": "approval.decide", "correlation_id": (identity or {}).get("correlation_id")},
                        verified_person_id=verified,
                        identity=identity,
                        reason_code=dlg_decide.get("reason") or "delegation_denied",
                        metadata={"permission_code": "approval.decide", "decision": dec},
                        conn=c,
                    )
                if commit:
                    c.commit()
                raise ApprovalError(
                    "approval.decide denied",
                    code="rbac_denied",
                    http_status=403,
                )

        ev_req = _rbac.evaluate(verified, req_code, target, conn=c)
        req_via_dlg = False
        if not ev_req.get("allowed"):
            dlg_req = _delegation.evaluate_delegation(
                verified, req_code, target, amount_ctx, conn=c
            )
            if dlg_req.get("allowed"):
                used_delegation = True
                req_via_dlg = True
                req_dlg_id = dlg_req.get("delegation_id")
            else:
                _audit_approval(
                    action="approval.decide_attempt",
                    result="DENIED",
                    request=req,
                    verified_person_id=verified,
                    identity=identity,
                    reason_code="required_permission_denied",
                    metadata={
                        "decision": dec,
                        "required_permission": req_code,
                        "reason": dlg_req.get("reason") or ev_req.get("reason"),
                        "delegation_id": dlg_req.get("delegation_id"),
                    },
                    conn=c,
                )
                if dlg_req.get("delegation_id") or dlg_req.get("reason") not in (
                    "no_valid_delegation",
                    "deny_by_default",
                    "missing_entity",
                ):
                    _delegation._audit_delegation(
                        action="delegation.denied",
                        result="DENIED",
                        delegation={
                            "delegation_id": dlg_req.get("delegation_id"),
                            "entity_id": target.get("entity_id"),
                            "permission_code": req_code,
                            "correlation_id": (identity or {}).get("correlation_id"),
                        },
                        verified_person_id=verified,
                        identity=identity,
                        reason_code=dlg_req.get("reason") or "delegation_denied",
                        metadata={
                            "permission_code": req_code,
                            "decision": dec,
                            "amount": (amount_ctx or {}).get("amount"),
                            "currency": (amount_ctx or {}).get("currency"),
                        },
                        conn=c,
                    )
                if commit:
                    c.commit()
                raise ApprovalError(
                    f"required permission denied: {req_code}",
                    code="required_permission_denied",
                    http_status=403,
                )

        basis_type = "DELEGATION" if used_delegation else "NATIVE"
        basis_dlg_id = req_dlg_id or decide_dlg_id if used_delegation else None

        asg_id = (decided_by_assignment_id or "").strip() or None
        if asg_id:
            arow = c.execute(
                """
                SELECT assignment_id, person_id, status, end_at
                FROM org_assignments WHERE assignment_id=?
                """,
                (asg_id,),
            ).fetchone()
            if (
                not arow
                or arow["person_id"] != verified
                or arow["status"] != "ACTIVE"
                or arow["end_at"] is not None
            ):
                raise ApprovalError(
                    "decided_by_assignment_id invalid",
                    code="inactive_assignment",
                    http_status=403,
                )
        else:
            asg_id = _require_active_assignment(verified, c)
            if not asg_id:
                raise ApprovalError(
                    "active Assignment required",
                    code="no_active_assignment",
                    http_status=403,
                )

        authority_allowed = 1
        authority_reason = None
        authority_matched = None
        if dec == "APPROVED" and is_material_request(req):
            if req_via_dlg or (used_delegation and not ev_req.get("allowed")):
                # Via delegation: amount must pass evaluate_delegation cap rules
                # (already checked above when amount_ctx set). Do NOT treat
                # delegate as owning the Authority Limit.
                dlg_auth = _delegation.evaluate_delegation(
                    verified, req_code, target, amount_ctx, conn=c
                )
                if not dlg_auth.get("allowed"):
                    _audit_approval(
                        action="approval.authority_denied",
                        result="DENIED",
                        request=req,
                        verified_person_id=verified,
                        identity=identity,
                        reason_code=dlg_auth.get("reason") or "authority_denied",
                        metadata={
                            "decision": dec,
                            "amount": req.get("material_amount"),
                            "currency": req.get("currency"),
                            "reason": dlg_auth.get("reason"),
                            "required_permission": req_code,
                            "delegation_id": dlg_auth.get("delegation_id"),
                            "authority_basis_type": "DELEGATION",
                        },
                        conn=c,
                    )
                    _delegation._audit_delegation(
                        action="delegation.denied",
                        result="DENIED",
                        delegation={
                            "delegation_id": dlg_auth.get("delegation_id"),
                            "entity_id": target.get("entity_id"),
                            "permission_code": req_code,
                            "correlation_id": (identity or {}).get("correlation_id"),
                        },
                        verified_person_id=verified,
                        identity=identity,
                        reason_code=dlg_auth.get("reason") or "authority_denied",
                        metadata={
                            "permission_code": req_code,
                            "amount": req.get("material_amount"),
                            "currency": req.get("currency"),
                        },
                        conn=c,
                    )
                    if commit:
                        c.commit()
                    raise ApprovalError(
                        f"authority denied: {dlg_auth.get('reason')}",
                        code="authority_denied",
                        http_status=403,
                    )
                authority_allowed = 1
                authority_reason = dlg_auth.get("reason") or "delegation_cap_ok"
                authority_matched = None
                basis_type = "DELEGATION"
                basis_dlg_id = dlg_auth.get("delegation_id") or basis_dlg_id
            else:
                auth = _authority.within_authority(
                    verified,
                    req_code,
                    target,
                    {
                        "amount": req.get("material_amount"),
                        "currency": req.get("currency"),
                    },
                    conn=c,
                )
                if not auth.get("allowed"):
                    _audit_approval(
                        action="approval.authority_denied",
                        result="DENIED",
                        request=req,
                        verified_person_id=verified,
                        identity=identity,
                        reason_code=auth.get("reason") or "authority_denied",
                        metadata={
                            "decision": dec,
                            "amount": req.get("material_amount"),
                            "currency": req.get("currency"),
                            "reason": auth.get("reason"),
                            "required_permission": req_code,
                        },
                        conn=c,
                    )
                    if commit:
                        c.commit()
                    raise ApprovalError(
                        f"authority denied: {auth.get('reason')}",
                        code="authority_denied",
                        http_status=403,
                    )
                authority_allowed = 1
                authority_reason = auth.get("reason")
                matched = auth.get("matched_limit") or {}
                authority_matched = matched.get("authority_limit_id")
        elif dec == "REJECTED":
            # Authority not required for reject
            authority_allowed = 0
            authority_reason = "not_required_for_reject"

        # First successful APPROVED/REJECTED wins — re-check PENDING under write
        existing = c.execute(
            """
            SELECT COUNT(*) FROM core_approval_decisions
            WHERE approval_request_id=? AND decision IN ('APPROVED','REJECTED')
            """,
            (req["approval_request_id"],),
        ).fetchone()[0]
        if existing:
            if commit:
                c.commit()
            raise ApprovalError(
                "already decided",
                code="already_decided",
                http_status=409,
            )

        ts = now_utc_iso()
        did = mint_decision_id()
        corr = (identity or {}).get("correlation_id") or req.get("correlation_id") or _audit.mint_correlation_id()
        c.execute(
            """
            INSERT INTO core_approval_decisions (
              approval_decision_id, approval_request_id, decision,
              decided_by_person_id, decided_by_assignment_id, identity_assurance,
              reason, decided_at, authority_allowed, authority_reason,
              authority_matched_limit_id, authority_basis_type,
              authority_basis_delegation_id, correlation_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                did,
                req["approval_request_id"],
                dec,
                verified,
                asg_id,
                (identity or {}).get("identity_assurance"),
                (reason or "").strip() or None,
                ts,
                authority_allowed,
                authority_reason,
                authority_matched,
                basis_type,
                basis_dlg_id,
                corr,
                ts,
            ),
        )
        new_status = "APPROVED" if dec == "APPROVED" else "REJECTED"
        c.execute(
            """
            UPDATE core_approval_requests
            SET status=?, decided_at=?, updated_at=?
            WHERE approval_request_id=? AND status='PENDING'
            """,
            (new_status, ts, ts, req["approval_request_id"]),
        )
        if c.total_changes == 0:
            raise ApprovalError("already decided", code="already_decided", http_status=409)

        updated = get_approval_request(req["approval_request_id"], conn=c, expire=False)
        assert updated is not None
        audit_action = "approval.granted" if dec == "APPROVED" else "approval.rejected"
        _audit_approval(
            action=audit_action,
            result="SUCCEEDED",
            request=updated,
            verified_person_id=verified,
            identity=identity,
            metadata={
                "status": new_status,
                "decision": dec,
                "amount": updated.get("material_amount"),
                "currency": updated.get("currency"),
                "required_permission": updated.get("required_permission_code"),
                "authority_basis_type": basis_type,
                "delegation_id": basis_dlg_id,
            },
            conn=c,
        )
        if basis_type == "DELEGATION" and basis_dlg_id:
            _delegation._audit_delegation(
                action="delegation.used",
                result="SUCCEEDED",
                delegation={
                    "delegation_id": basis_dlg_id,
                    "entity_id": updated.get("owning_entity_id"),
                    "permission_code": updated.get("required_permission_code"),
                    "correlation_id": corr,
                },
                verified_person_id=verified,
                identity=identity,
                metadata={
                    "decision": dec,
                    "delegation_id": basis_dlg_id,
                    "authority_basis_type": "DELEGATION",
                    "required_permission": updated.get("required_permission_code"),
                },
                conn=c,
            )
        if commit:
            c.commit()

        # HARD RULE: do not execute source; do not complete/verify linked work item
        out = {
            "ok": True,
            "request": updated,
            "decision": dict(
                c.execute(
                    "SELECT * FROM core_approval_decisions WHERE approval_decision_id=?",
                    (did,),
                ).fetchone()
            ),
            "executed_source": False,
            "work_item_completed": False,
            **HONESTY,
        }
        return out
    finally:
        if own:
            c.close()


def approve_request(
    approval_request_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    decided_by_assignment_id: str | None = None,
    decided_by_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return _decide(
        approval_request_id,
        decision="APPROVED",
        verified_person_id=verified_person_id,
        reason=reason,
        decided_by_assignment_id=decided_by_assignment_id,
        decided_by_person_id=decided_by_person_id,
        identity=identity,
        conn=conn,
        commit=commit,
    )


def reject_request(
    approval_request_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    decided_by_assignment_id: str | None = None,
    decided_by_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return _decide(
        approval_request_id,
        decision="REJECTED",
        verified_person_id=verified_person_id,
        reason=reason,
        decided_by_assignment_id=decided_by_assignment_id,
        decided_by_person_id=decided_by_person_id,
        identity=identity,
        conn=conn,
        commit=commit,
    )


def cancel_request(
    approval_request_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Cancel PENDING. Requester (own) or Matt. No decision row required."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ApprovalError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        req = get_approval_request(approval_request_id, conn=c, expire=True)
        if not req:
            raise ApprovalError("approval request not found", code="not_found", http_status=404)
        if req["status"] != "PENDING":
            raise ApprovalError(
                f"request not PENDING (status={req['status']})",
                code="not_pending",
                http_status=409,
            )

        target = target_context_for_request(req)
        ev = _rbac.evaluate(verified, "approval.cancel", target, conn=c)
        if not ev.get("allowed"):
            raise ApprovalError(
                "approval.cancel denied",
                code="rbac_denied",
                http_status=403,
            )

        is_owner = verified == req["requested_by_person_id"]
        is_matt = verified == PERS_MATT
        if not is_owner and not is_matt:
            raise ApprovalError(
                "only requester or Matt may cancel",
                code="cancel_forbidden",
                http_status=403,
            )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE core_approval_requests
            SET status='CANCELLED', updated_at=?, decided_at=?
            WHERE approval_request_id=? AND status='PENDING'
            """,
            (ts, ts, req["approval_request_id"]),
        )
        updated = get_approval_request(req["approval_request_id"], conn=c, expire=False)
        assert updated is not None
        _audit_approval(
            action="approval.cancelled",
            result="SUCCEEDED",
            request=updated,
            verified_person_id=verified,
            identity=identity,
            reason_code=(reason or "").strip() or None,
            metadata={"status": "CANCELLED", "note": reason},
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


def update_decision(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError("core_approval_decisions is append-only")


def delete_decision(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError("core_approval_decisions is append-only")
