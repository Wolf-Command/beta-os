#!/usr/bin/env python3
"""Wolf Core Venue Daily Close — Uma Blu (Beta).

SUBMITTED ≠ RECONCILED ≠ VERIFIED
EXCEPTION ≠ RESOLVED ≠ VERIFIED_CLOSED
DECLARED cash ≠ VERIFIED cash

No hard-coded person gates (no if Devi). Role / assignment / scope only.
Client cannot submit expected totals, variance, or state.
Live variance thresholds = 0 → non-zero variance → VARIANCE_REQUIRES_POLICY.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import evidence as _evidence
from core import esb_close_snapshot as _esb
from core import rbac as _rbac
from core import work_items as _work_items

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
TZ_UTC = timezone.utc

ENTITY_BZG = "ENT-BZG"
BRAND_UMA = "BZG-UMA"
ROLE_HFB = "ROLE-BZG-HFB"
ROLE_FB_OPS_LEAD = "ROLE-BZG-FB-OPS-LEAD"
ROLE_CLOSER = "ROLE-BZG-CLOSER"
EVIDENCE_CASH = "cash_count"

STATES = frozenset(
    {
        "OPEN",
        "DATA_CAPTURED",
        "EVIDENCE_SUBMITTED",
        "RECONCILED",
        "VARIANCE_REQUIRES_POLICY",
        "EXCEPTION",
        "RESOLVED",
        "VERIFIED_CLOSED",
        "CANCELLED",
    }
)
TERMINAL = frozenset({"VERIFIED_CLOSED", "CANCELLED"})

HONESTY = {
    "settlement_api": "UNAVAILABLE",
    "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
    "live_variance_threshold": 0,
    "live_monetary_authority": 0,
    "declared_cash_is_not_verified": True,
    "closer_commissioning": "WAITING FOR VERIFIED CLOSING OPERATOR",
}


class VenueCloseError(ValueError):
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
        raise VenueCloseError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"venue_close refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"venue_close refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"venue_close refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_close_id() -> str:
    return f"VDC-{uuid.uuid4()}"


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def _loads(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _rbac_target() -> dict[str, Any]:
    return {"entity_id": ENTITY_BZG, "brand_id": BRAND_UMA}


def _assert_perm(
    *,
    verified_person_id: str,
    permission_code: str,
    conn: sqlite3.Connection,
) -> None:
    decision = _rbac.evaluate(
        verified_person_id,
        permission_code,
        _rbac_target(),
        conn=conn,
    )
    if not decision.get("allowed"):
        raise VenueCloseError(
            f"permission denied: {permission_code} ({decision.get('reason')})",
            code="forbidden",
            http_status=403,
        )


def _public(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["esb_query_meta"] = _loads(out.pop("esb_query_meta_json", None))
    out["esb_totals"] = _loads(out.pop("esb_totals_json", None))
    out["honesty"] = dict(HONESTY)
    # Commissioning flag from live closer assignment count
    return out


def get_close(
    close_id: str | None = None,
    *,
    business_date: str | None = None,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        if close_id:
            row = _row(
                c.execute(
                    "SELECT * FROM venue_daily_closes WHERE close_id=?",
                    (close_id.strip(),),
                ).fetchone()
            )
        else:
            date = (business_date or "").strip()
            if not date:
                return None
            row = _row(
                c.execute(
                    """
                    SELECT * FROM venue_daily_closes
                    WHERE entity_id=? AND venue_brand_id=? AND business_date=?
                    """,
                    (entity_id, venue_brand_id, date),
                ).fetchone()
            )
        return _public(row) if row else None
    finally:
        if own:
            c.close()


def list_closes(
    *,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    state: str | None = None,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 200))
        if state:
            rows = c.execute(
                """
                SELECT * FROM venue_daily_closes
                WHERE entity_id=? AND venue_brand_id=? AND state=?
                ORDER BY business_date DESC LIMIT ?
                """,
                (entity_id, venue_brand_id, state.strip().upper(), lim),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM venue_daily_closes
                WHERE entity_id=? AND venue_brand_id=?
                ORDER BY business_date DESC LIMIT ?
                """,
                (entity_id, venue_brand_id, lim),
            ).fetchall()
        return [_public(dict(r)) for r in rows]
    finally:
        if own:
            c.close()


def open_or_get(
    business_date: str,
    *,
    verified_person_id: str,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Idempotent open by (entity, brand, date). Client cannot set state."""
    date = (business_date or "").strip()
    if not date or len(date) != 10:
        raise VenueCloseError("business_date must be YYYY-MM-DD", code="invalid_date")
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        existing = get_close(
            business_date=date,
            entity_id=entity_id,
            venue_brand_id=venue_brand_id,
            conn=c,
        )
        if existing:
            return {**existing, "created": False, **HONESTY}

        cid = mint_close_id()
        ts = now_utc_iso()
        c.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              fingerprint_stale, submitted_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'OPEN', 0, ?, ?, ?)
            """,
            (cid, entity_id, venue_brand_id, date, verified, ts, ts),
        )
        _audit.safe_record(
            action="venue_close.open",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=cid,
            reason_code="opened",
            metadata={"business_date": date, "venue_brand_id": venue_brand_id},
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(cid, conn=c)
        assert out
        return {**out, "created": True, **HONESTY}
    finally:
        if own:
            c.close()


def capture_esb_snapshot(
    close_id: str,
    *,
    verified_person_id: str,
    esb_path: Path | str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] in TERMINAL:
            raise VenueCloseError(
                f"close is terminal ({row['state']})",
                code="terminal_state",
            )
        if row["state"] not in ("OPEN", "DATA_CAPTURED"):
            raise VenueCloseError(
                f"cannot capture ESB from state {row['state']}",
                code="invalid_transition",
            )

        snap = _esb.snapshot_day(row["business_date"], esb_path=esb_path)
        if snap.get("incomplete"):
            raise VenueCloseError(
                "ESB data incomplete / empty day — close blocked",
                code=snap.get("incomplete_reason") or "esb_empty_day",
                http_status=409,
            )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes SET
              state='DATA_CAPTURED',
              esb_fingerprint_sha256=?,
              esb_pulled_at=?,
              esb_query_meta_json=?,
              esb_totals_json=?,
              fingerprint_stale=0,
              variance_cash_amount=NULL,
              variance_policy_id=NULL,
              updated_at=?
            WHERE close_id=?
            """,
            (
                snap["fingerprint_sha256"],
                snap.get("esb_pulled_at"),
                json.dumps(snap["query_meta"], sort_keys=True),
                json.dumps(snap["totals"], sort_keys=True),
                ts,
                close_id,
            ),
        )
        _audit.safe_record(
            action="venue_close.esb_captured",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="esb_snapshot",
            metadata={
                "fingerprint": snap["fingerprint_sha256"],
                "finished_count": snap["totals"]["finished_count"],
                "cash_from_payments": snap["totals"]["cash_from_payments"],
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, **HONESTY}
    finally:
        if own:
            c.close()


def attach_declared_cash(
    close_id: str,
    *,
    declared_cash_amount: float,
    verified_person_id: str,
    object_ref: str | None = None,
    content_hash: str | None = None,
    notes: str | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Attach DECLARED cash evidence. Amount is operator declaration — not verified cash."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    try:
        amount = float(declared_cash_amount)
    except (TypeError, ValueError) as exc:
        raise VenueCloseError("declared_cash_amount must be numeric", code="invalid_amount") from exc
    if amount < 0:
        raise VenueCloseError("declared_cash_amount cannot be negative", code="invalid_amount")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] not in ("DATA_CAPTURED", "EVIDENCE_SUBMITTED"):
            raise VenueCloseError(
                f"cannot attach cash from state {row['state']}",
                code="invalid_transition",
            )

        evid = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_CASH,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=object_ref,
            content_hash=content_hash,
            brand_id=row.get("venue_brand_id") or BRAND_UMA,
            metadata={
                "declared_cash_amount": amount,
                "verification_status_note": "DECLARED_NOT_VERIFIED",
                "notes": (notes or "").strip() or None,
            },
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes SET
              state='EVIDENCE_SUBMITTED',
              declared_cash_amount=?,
              declared_cash_evidence_id=?,
              submitted_by_person_id=?,
              updated_at=?
            WHERE close_id=?
            """,
            (amount, evid["evidence_id"], verified, ts, close_id),
        )
        _audit.safe_record(
            action="venue_close.declared_cash",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="declared_cash",
            metadata={
                "declared_cash_amount": amount,
                "evidence_id": evid["evidence_id"],
                "declared_is_not_verified": True,
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, "evidence": evid, **HONESTY}
    finally:
        if own:
            c.close()


def _active_variance_policy(
    conn: sqlite3.Connection,
    *,
    entity_id: str,
    venue_brand_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM venue_close_variance_policies
        WHERE status='ACTIVE'
          AND entity_id=?
          AND (venue_brand_id IS NULL OR venue_brand_id=?)
        ORDER BY
          CASE WHEN venue_brand_id IS NULL THEN 1 ELSE 0 END,
          abs_threshold_amount ASC
        LIMIT 1
        """,
        (entity_id, venue_brand_id),
    ).fetchone()
    return dict(row) if row else None


def _refresh_stale_flag(
    row: dict[str, Any],
    *,
    esb_path: Path | str | None,
    conn: sqlite3.Connection,
) -> bool:
    """Return True if fingerprint is stale vs warehouse."""
    if not row.get("esb_fingerprint_sha256"):
        return False
    live = _esb.current_fingerprint(row["business_date"], esb_path=esb_path)
    stale = live != row["esb_fingerprint_sha256"]
    if stale != bool(row.get("fingerprint_stale")):
        conn.execute(
            "UPDATE venue_daily_closes SET fingerprint_stale=?, updated_at=? WHERE close_id=?",
            (1 if stale else 0, now_utc_iso(), row["close_id"]),
        )
    return stale


def reconcile(
    close_id: str,
    *,
    verified_person_id: str,
    esb_path: Path | str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Server-side variance only. Never ACCEPT without approved policy when variance≠0."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] not in ("EVIDENCE_SUBMITTED", "RECONCILED", "VARIANCE_REQUIRES_POLICY"):
            raise VenueCloseError(
                f"cannot reconcile from state {row['state']}",
                code="invalid_transition",
            )
        if row.get("declared_cash_amount") is None:
            raise VenueCloseError("declared cash missing", code="missing_declared_cash")
        totals = row.get("esb_totals") or {}
        if "cash_from_payments" not in totals:
            raise VenueCloseError("ESB totals missing", code="missing_esb_totals")

        if _refresh_stale_flag(row, esb_path=esb_path, conn=c):
            raise VenueCloseError(
                "ESB fingerprint stale — recalculate / re-capture required",
                code="fingerprint_stale",
                http_status=409,
            )

        declared = float(row["declared_cash_amount"])
        esb_cash = float(totals["cash_from_payments"])
        variance = round(declared - esb_cash, 2)
        policy = _active_variance_policy(
            c, entity_id=row["entity_id"], venue_brand_id=row["venue_brand_id"]
        )
        ts = now_utc_iso()

        if abs(variance) < 1e-9:
            # Clean path: RECONCILED then system VERIFIED_CLOSED (honesty: SUBMITTED ≠ RECONCILED ≠ VERIFIED)
            c.execute(
                """
                UPDATE venue_daily_closes SET
                  state='RECONCILED',
                  variance_cash_amount=?,
                  variance_policy_id=NULL,
                  updated_at=?
                WHERE close_id=?
                """,
                (0.0, ts, close_id),
            )
            _audit.safe_record(
                action="venue_close.reconcile",
                result="ALLOWED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=close_id,
                reason_code="zero_variance_reconciled",
                metadata={
                    "variance_cash_amount": 0.0,
                    "state": "RECONCILED",
                    **HONESTY,
                },
                conn=c,
            )
            c.execute(
                """
                UPDATE venue_daily_closes SET
                  state='VERIFIED_CLOSED',
                  variance_cash_amount=?,
                  variance_policy_id=NULL,
                  verified_at=?,
                  verified_by_person_id=NULL,
                  updated_at=?
                WHERE close_id=?
                """,
                (0.0, ts, ts, close_id),
            )
            _audit.safe_record(
                action="venue_close.verify",
                result="ALLOWED",
                source="venue_close",
                actor_type="SYSTEM",
                verified_person_id=None,
                reason_code="zero_variance_system_close",
                resource_type="venue_daily_close",
                resource_id=close_id,
                metadata={"variance_cash_amount": 0.0, "prior_state": "RECONCILED", **HONESTY},
                conn=c,
            )
        else:
            # Non-zero without approved threshold → NEVER ACCEPT
            if policy is None:
                new_state = "VARIANCE_REQUIRES_POLICY"
                policy_id = None
            else:
                # Policy exists (tests may seed) — still never auto-ACCEPT; route to policy state
                # Real ACCEPT path is NOT BUILT (would need Matt-approved threshold semantics).
                thr = float(policy["abs_threshold_amount"])
                within = abs(variance) <= thr
                if within:
                    # Still require exception/verify — no silent ACCEPT of till variance
                    new_state = "VARIANCE_REQUIRES_POLICY"
                else:
                    new_state = "VARIANCE_REQUIRES_POLICY"
                policy_id = policy["variance_policy_id"]
            c.execute(
                """
                UPDATE venue_daily_closes SET
                  state=?,
                  variance_cash_amount=?,
                  variance_policy_id=?,
                  updated_at=?
                WHERE close_id=?
                """,
                (new_state, variance, policy_id, ts, close_id),
            )
            _audit.safe_record(
                action="venue_close.reconcile",
                result="ALLOWED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=close_id,
                reason_code="variance_requires_policy" if policy is None else "variance_flagged",
                metadata={
                    "variance_cash_amount": variance,
                    "esb_cash_from_payments": esb_cash,
                    "declared_cash_amount": declared,
                    "policy_id": policy_id,
                    **HONESTY,
                },
                conn=c,
            )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, **HONESTY}
    finally:
        if own:
            c.close()


def find_hfb_assignee(
    *,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Resolve F&B exception owner by role + ACTIVE assignment + brand scope.

    Prefers ROLE-BZG-HFB, then ROLE-BZG-FB-OPS-LEAD.
    Never hard-codes PERS-DEVI.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, p.position_id, p.role_id, p.brand_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE p.role_id IN (?, ?)
              AND p.entity_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            ORDER BY CASE p.role_id WHEN ? THEN 0 ELSE 1 END, a.assignment_id
            """,
            (ROLE_HFB, ROLE_FB_OPS_LEAD, entity_id, ROLE_HFB),
        ).fetchall()
        for r in rows:
            # Prefer brand-matched position; else require assignment scope covering brand
            if r["brand_id"] == venue_brand_id:
                return dict(r)
            scopes = c.execute(
                """
                SELECT s.scope_id, t.target_type, t.target_id
                FROM org_assignment_scopes s
                JOIN org_scope_targets t ON t.scope_id = s.scope_id
                WHERE s.assignment_id=? AND s.status='ACTIVE' AND s.end_at IS NULL
                """,
                (r["assignment_id"],),
            ).fetchall()
            for s in scopes:
                if s["target_type"] == "brand" and s["target_id"] == venue_brand_id:
                    return dict(r)
                if s["target_type"] == "entity" and s["target_id"] == entity_id:
                    return dict(r)
        return None
    finally:
        if own:
            c.close()


def open_exception(
    close_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """VARIANCE_REQUIRES_POLICY → EXCEPTION + Work Item owned by HFB assignee."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        # Submitter or resolver may open the exception handoff
        try:
            _assert_perm(
                verified_person_id=verified,
                permission_code="venue.close.submit",
                conn=c,
            )
        except VenueCloseError:
            _assert_perm(
                verified_person_id=verified,
                permission_code="venue.close.resolve_exception",
                conn=c,
            )

        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] != "VARIANCE_REQUIRES_POLICY":
            raise VenueCloseError(
                f"cannot open exception from state {row['state']}",
                code="invalid_transition",
            )
        if row.get("work_item_id"):
            out = get_close(close_id, conn=c)
            assert out
            return {**out, "created": False, **HONESTY}

        owner = find_hfb_assignee(
            entity_id=row["entity_id"],
            venue_brand_id=row["venue_brand_id"],
            conn=c,
        )
        if not owner:
            raise VenueCloseError(
                "no ACTIVE Head of F&B assignment in scope for exception owner",
                code="missing_hfb_assignee",
                http_status=409,
            )

        wi = _work_items.create_work_item(
            title=f"Uma Blu close variance {row['business_date']}",
            owning_entity_id=row["entity_id"],
            work_type="EXCEPTION",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            description=(
                f"Cash variance {row.get('variance_cash_amount')} "
                f"(declared − ESB_CASH_FROM_PAYMENTS). Settlement API unavailable."
            ),
            priority=2,
            source_id=close_id,
            owner_person_id=owner["person_id"],
            owner_org_assignment_id=owner["assignment_id"],
            identity=identity,
            conn=c,
            commit=False,
        )
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes SET
              state='EXCEPTION',
              work_item_id=?,
              updated_at=?
            WHERE close_id=?
            """,
            (wi["work_item_id"], ts, close_id),
        )
        _audit.safe_record(
            action="venue_close.exception_opened",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="exception_wi",
            metadata={
                "work_item_id": wi["work_item_id"],
                "owner_person_id": owner["person_id"],
                "owner_role_id": owner["role_id"],
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, "work_item": wi, "created": True, **HONESTY}
    finally:
        if own:
            c.close()


def resolve_exception(
    close_id: str,
    *,
    verified_person_id: str,
    resolution_notes: str,
    object_ref: str | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    notes = (resolution_notes or "").strip()
    if len(notes) < 8:
        raise VenueCloseError(
            "resolution_notes required (≥8 chars)",
            code="missing_resolution_notes",
        )
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.resolve_exception",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] != "EXCEPTION":
            raise VenueCloseError(
                f"cannot resolve from state {row['state']}",
                code="invalid_transition",
            )

        evid = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_CASH,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=object_ref,
            brand_id=row.get("venue_brand_id") or BRAND_UMA,
            metadata={"resolution_notes": notes, "kind": "exception_resolution"},
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes SET
              state='RESOLVED',
              resolved_at=?,
              resolved_by_person_id=?,
              resolve_evidence_id=?,
              updated_at=?
            WHERE close_id=?
            """,
            (ts, verified, evid["evidence_id"], ts, close_id),
        )
        _audit.safe_record(
            action="venue_close.exception_resolved",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="resolved",
            metadata={"evidence_id": evid["evidence_id"]},
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, "evidence": evid, **HONESTY}
    finally:
        if own:
            c.close()


def verify_close(
    close_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Verify RESOLVED (or already clean) close. SoD: verifier ≠ resolver on exception path."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.verify",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        if row["state"] == "VERIFIED_CLOSED":
            return {**row, "created": False, **HONESTY}
        if row["state"] != "RESOLVED":
            raise VenueCloseError(
                f"cannot verify from state {row['state']} (exception path requires RESOLVED)",
                code="invalid_transition",
            )
        resolver = (row.get("resolved_by_person_id") or "").strip()
        if resolver and resolver == verified:
            raise VenueCloseError(
                "SoD: resolver cannot be sole verifier on own exception",
                code="sod_self_verify",
                http_status=403,
            )
        submitter = (row.get("submitted_by_person_id") or "").strip()
        # Independent of resolver SoD: submitter cannot verify own exception close
        if submitter and submitter == verified:
            raise VenueCloseError(
                "SoD: closer cannot self-verify own exception",
                code="sod_self_close",
                http_status=403,
            )

        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes SET
              state='VERIFIED_CLOSED',
              verified_at=?,
              verified_by_person_id=?,
              updated_at=?
            WHERE close_id=?
            """,
            (ts, verified, ts, close_id),
        )
        _audit.safe_record(
            action="venue_close.verify",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="verified",
            metadata={"resolved_by_person_id": resolver},
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {**out, **HONESTY}
    finally:
        if own:
            c.close()


def honesty_flags(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or db_connect()
    try:
        n_pol = c.execute("SELECT COUNT(*) FROM venue_close_variance_policies").fetchone()[0]
        n_auth = c.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        closer_n = c.execute(
            """
            SELECT COUNT(*) FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            WHERE p.role_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
            """,
            (ROLE_CLOSER,),
        ).fetchone()[0]
        policy_rows = int(n_pol)
        return {
            **HONESTY,
            # Row count. Zero rows is not a tolerance of 0.
            "live_variance_threshold": policy_rows,
            "variance_policy_display": (
                "BLOCKED BY BUSINESS POLICY"
                if policy_rows == 0
                else "POLICY_ON_FILE"
            ),
            "live_monetary_authority": int(n_auth),
            "closer_active_assignments": int(closer_n),
            "closer_commissioning": (
                "WAITING FOR VERIFIED CLOSING OPERATOR"
                if closer_n == 0
                else "CLOSER_ASSIGNED"
            ),
        }
    finally:
        if own:
            c.close()
