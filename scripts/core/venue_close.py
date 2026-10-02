#!/usr/bin/env python3
"""Wolf Core Venue Daily Close — BZG reusable engine (Uma pilot).

SUBMITTED ≠ RECONCILED ≠ VERIFIED
EXCEPTION ≠ RESOLVED ≠ VERIFIED_CLOSED
DECLARED cash ≠ VERIFIED cash

BZG-DAILY-CLOSE-TILL-EDC-1 extends this module (one engine — not seven apps).
No hard-coded person gates (no if Devi). Role / assignment / scope only.
Client cannot submit expected totals, variance, or state.
Live variance thresholds = 0 → non-zero variance → VARIANCE_REQUIRES_POLICY.
Till declare refuses ESB-copy. Settlement API UNAVAILABLE.
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
ROLE_CAPTAIN = "ROLE-BZG-CAPTAIN"
ROLE_CASHIER = "ROLE-BZG-CASHIER"
ROLE_MATT = "ROLE-MATT"
ROLE_OWNER = "ROLE-OWNER"
EVIDENCE_CASH = "cash_count"

# Oversight may open the Uma close desk without a Daily Close roster row.
CLOSE_OVERSIGHT_ROLES = frozenset(
    {ROLE_HFB, ROLE_FB_OPS_LEAD, ROLE_MATT, ROLE_OWNER}
)
# Floor closer seats authorised via venue_closer_roster + active Assignment.
CLOSE_ROSTER_ROLES = frozenset({ROLE_CLOSER, ROLE_CAPTAIN, ROLE_CASHIER})

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
    "settlement_status": "PENDING_BANK",
    "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
    "esb_payments_are_not_edc_settlement": True,
    "live_variance_threshold": 0,
    "live_monetary_authority": 0,
    "declared_cash_is_not_verified": True,
    "invented_tolerance": False,
    "staff_ready": False,
    "human_commissioned": False,
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

        biz = row["business_date"]
        try:
            snap = _esb.snapshot_day(biz, esb_path=esb_path)
        except _esb.EsbSnapshotError as exc:
            # Warehouse missing / unreadable → explicit UNAVAILABLE (never fake zeros).
            raise VenueCloseError(
                f"ESB DATA UNAVAILABLE — cannot read live sales for {biz}. "
                "Empty is not zero sales. Retry after ESB pull; photographed "
                "closing receipt stays a separate dual source.",
                code="esb_data_unavailable",
                http_status=getattr(exc, "http_status", 503) or 503,
            ) from exc
        if snap.get("incomplete"):
            # Do not write zero totals as a successful live pull.
            raise VenueCloseError(
                f"ESB DATA UNAVAILABLE — no live sales for {biz}. "
                "Empty is not zero sales. Retry after ESB pull; photographed "
                "closing receipt stays a separate dual source.",
                code="esb_data_unavailable",
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
                "esb_live_status": "AVAILABLE",
                "esb_source": "warehouse_payment_lines",
                "business_date": biz,
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        return {
            **out,
            **HONESTY,
            "esb_live_status": "AVAILABLE",
            "esb_source": "warehouse_payment_lines",
            "esb_source_label": (
                "Live ESB payment lines for this business date "
                "(warehouse) — not settlement; not prior-day history"
            ),
            "esb_empty_is_not_zero_sales": True,
        }
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
    source: str | None = None,
    copy_from_esb: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Attach DECLARED cash evidence. Amount is operator declaration — not verified cash.

    Refuses copying ESB payment-line cash into declared till (declared ≠ ESB source).
    """
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    src = (source or "").strip().lower()
    if copy_from_esb or src in (
        "esb",
        "esb_cash",
        "esb_cash_from_payments",
        "copy_esb",
        "esb_copy",
    ):
        raise VenueCloseError(
            "refuses copying ESB cash into declared till",
            code="esb_copy_refused",
            http_status=400,
        )
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

        brand = row.get("venue_brand_id") or BRAND_UMA
        outlet_tag = (row.get("outlet_id") or brand).strip()
        wi = _work_items.create_work_item(
            title=f"BZG close variance {outlet_tag} {row['business_date']}",
            owning_entity_id=row["entity_id"],
            work_type="EXCEPTION",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            description=(
                f"Cash variance {row.get('variance_cash_amount')} "
                f"(declared − ESB_CASH_FROM_PAYMENTS) for outlet {outlet_tag}. "
                f"Settlement API unavailable. ESB payments ≠ EDC settlement."
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


def ensure_take_attribution_columns(conn: sqlite3.Connection) -> None:
    """Attribution columns for multi-closer take (not person-per-day invent)."""
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(venue_daily_closes)")}
    if "taken_by_person_id" not in cols:
        conn.execute(
            "ALTER TABLE venue_daily_closes ADD COLUMN taken_by_person_id TEXT NULL"
        )
    if "taken_at" not in cols:
        conn.execute("ALTER TABLE venue_daily_closes ADD COLUMN taken_at TEXT NULL")


def _active_role_ids(person_id: str, conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND pos.status='ACTIVE'
        """,
        (person_id,),
    ).fetchall()
    return {str(r[0]) for r in rows}


def _assignment_covers_brand(
    conn: sqlite3.Connection,
    *,
    assignment_id: str,
    position_brand_id: str | None,
    venue_brand_id: str,
    entity_id: str = ENTITY_BZG,
) -> bool:
    if (position_brand_id or "").strip() == venue_brand_id:
        return True
    rows = conn.execute(
        """
        SELECT t.target_type, t.target_id
        FROM org_assignment_scopes s
        JOIN org_scope_targets t ON t.scope_id = s.scope_id
        WHERE s.assignment_id=? AND s.status='ACTIVE' AND s.end_at IS NULL
        """,
        (assignment_id,),
    ).fetchall()
    for r in rows:
        ttype = str(r["target_type"] if isinstance(r, sqlite3.Row) else r[0])
        tid = str(r["target_id"] if isinstance(r, sqlite3.Row) else r[1])
        if ttype == "brand" and tid == venue_brand_id:
            return True
        if ttype == "entity" and tid == entity_id:
            return True
    return False


def person_authorised_for_venue_close(
    person_id: str | None,
    *,
    venue_brand_id: str = BRAND_UMA,
    entity_id: str = ENTITY_BZG,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Reusable authorisation: active Assignment → closer roster → tonight's open close.

    Distinguishes (1) authorised to perform the venue close from (2) who took/submitted
    tonight's close (attribution). Multi-closer = multiple ACTIVE roster rows.
    No email special-case. No person-per-day invent as the only path.
    Does not loosen RBAC permission grants — page/desk gate only.
    """
    pid = (person_id or "").strip()
    brand = (venue_brand_id or "").strip() or BRAND_UMA
    ent = (entity_id or "").strip() or ENTITY_BZG
    deny = {
        "allowed": False,
        "reason": "not_on_assignment",
        "message": "This close is not on your assignment.",
        "person_id": pid or None,
        "venue_brand_id": brand,
        "roster_id": None,
        "assignment_id": None,
        "role_id": None,
        "via": None,
    }
    if not pid:
        return {**deny, "reason": "anonymous"}

    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_roster_table(c):
            return {**deny, "reason": "roster_unavailable"}

        roles = _active_role_ids(pid, c)
        oversight = sorted(roles & CLOSE_OVERSIGHT_ROLES)
        if oversight:
            return {
                "allowed": True,
                "reason": "oversight_role",
                "message": None,
                "person_id": pid,
                "venue_brand_id": brand,
                "roster_id": None,
                "assignment_id": None,
                "role_id": oversight[0],
                "via": "oversight",
                "oversight_roles": oversight,
            }

        rows = c.execute(
            """
            SELECT r.roster_id, r.brand_id, r.position_id, r.person_id, r.assignment_id,
                   r.status AS roster_status,
                   a.status AS asg_status, a.end_at AS asg_end_at,
                   p.role_id, p.status AS pos_status, p.brand_id AS pos_brand,
                   p.entity_id AS pos_entity
            FROM venue_closer_roster r
            JOIN org_assignments a ON a.assignment_id = r.assignment_id
            JOIN org_positions p ON p.position_id = r.position_id
            WHERE r.brand_id=?
              AND r.person_id=?
              AND r.status='ACTIVE'
            ORDER BY r.roster_id
            """,
            (brand, pid),
        ).fetchall()
        if not rows:
            return {**deny, "reason": "not_on_roster"}

        for r in rows:
            d = dict(r)
            if str(d.get("asg_status") or "") != "ACTIVE" or d.get("asg_end_at") is not None:
                continue
            if str(d.get("pos_status") or "") != "ACTIVE":
                continue
            role_id = str(d.get("role_id") or "")
            if role_id not in CLOSE_ROSTER_ROLES:
                continue
            pos_ent = str(d.get("pos_entity") or "").strip()
            if pos_ent and pos_ent != ent:
                continue
            if not _assignment_covers_brand(
                c,
                assignment_id=str(d["assignment_id"]),
                position_brand_id=d.get("pos_brand"),
                venue_brand_id=brand,
                entity_id=ent,
            ):
                continue
            return {
                "allowed": True,
                "reason": "closer_roster",
                "message": None,
                "person_id": pid,
                "venue_brand_id": brand,
                "roster_id": str(d["roster_id"]),
                "assignment_id": str(d["assignment_id"]),
                "role_id": role_id,
                "via": "roster",
            }

        # Roster row(s) exist but assignment/scope/role inactive or wrong outlet.
        return {**deny, "reason": "inactive_or_unscoped_assignment"}
    finally:
        if own:
            c.close()


def _has_roster_table(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='venue_closer_roster'"
        ).fetchone()
        is not None
    )


def take_open_venue_close(
    close_id: str,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Claim attribution on an open close. Multi-closer authorised; concurrent take denied.

    Preserves first successful take. Does not invent a person-per-day close row.
    """
    cid = (close_id or "").strip()
    verified = (verified_person_id or "").strip()
    if not cid:
        raise VenueCloseError("close_id required", code="missing_close_id")
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_take_attribution_columns(c)
        row = get_close(cid, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)

        authz = person_authorised_for_venue_close(
            verified,
            venue_brand_id=str(row.get("venue_brand_id") or BRAND_UMA),
            entity_id=str(row.get("entity_id") or ENTITY_BZG),
            conn=c,
        )
        if not authz.get("allowed"):
            _audit.safe_record(
                action="venue_close.take",
                result="DENIED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code=str(authz.get("reason") or "not_on_assignment"),
                metadata={"authz": authz},
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                authz.get("message") or "This close is not on your assignment.",
                code="forbidden",
                http_status=403,
            )

        if row.get("state") in TERMINAL:
            raise VenueCloseError(
                f"close is terminal ({row['state']})",
                code="invalid_transition",
            )

        taken_by = (row.get("taken_by_person_id") or "").strip()
        ts = now_utc_iso()
        if taken_by and taken_by != verified:
            _audit.safe_record(
                action="venue_close.take",
                result="DENIED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code="concurrent_take",
                metadata={
                    "taken_by_person_id": taken_by,
                    "state": row.get("state"),
                    "authz": authz,
                },
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                "This close is already taken by another authorised closer.",
                code="concurrent_take",
                http_status=409,
            )

        if not taken_by:
            c.execute(
                """
                UPDATE venue_daily_closes
                SET taken_by_person_id=?, taken_at=?, updated_at=?
                WHERE close_id=? AND (taken_by_person_id IS NULL OR taken_by_person_id='')
                """,
                (verified, ts, ts, cid),
            )
            # Re-read under race: another closer may have won the update.
            refreshed = get_close(cid, conn=c)
            assert refreshed
            won = (refreshed.get("taken_by_person_id") or "").strip()
            if won != verified:
                _audit.safe_record(
                    action="venue_close.take",
                    result="DENIED",
                    source="venue_close",
                    actor_type="PERSON",
                    verified_person_id=verified,
                    actor_person_id=verified,
                    identity_assurance=(identity or {}).get("identity_assurance"),
                    resource_type="venue_daily_close",
                    resource_id=cid,
                    reason_code="concurrent_take",
                    metadata={"taken_by_person_id": won, "race": True, "authz": authz},
                    conn=c,
                )
                if commit:
                    c.commit()
                raise VenueCloseError(
                    "This close is already taken by another authorised closer.",
                    code="concurrent_take",
                    http_status=409,
                )
            _audit.safe_record(
                action="venue_close.take",
                result="ALLOWED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code="taken",
                metadata={"authz": authz, "taken_at": ts},
                conn=c,
            )
            row = refreshed
        else:
            # Idempotent re-take by same person
            _audit.safe_record(
                action="venue_close.take",
                result="ALLOWED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=verified,
                actor_person_id=verified,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code="take_idempotent",
                metadata={"authz": authz, "taken_at": row.get("taken_at")},
                conn=c,
            )

        if commit:
            c.commit()
        out = get_close(cid, conn=c)
        assert out
        return {
            **out,
            "taken": True,
            "authz": authz,
            **HONESTY,
        }
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
        active_pol = int(
            c.execute(
                "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        return {
            **HONESTY,
            # Row count. Zero rows is not a tolerance of 0.
            "live_variance_threshold": policy_rows,
            "active_variance_policies": active_pol,
            "variance_policy_display": (
                "BLOCKED BY BUSINESS POLICY"
                if active_pol == 0
                else "POLICY_ON_FILE"
            ),
            "cash_variance_tolerance": "UNSET" if active_pol == 0 else "SET",
            "live_monetary_authority": int(n_auth),
            "closer_active_assignments": int(closer_n),
            "closer_commissioning": (
                "WAITING FOR VERIFIED CLOSING OPERATOR"
                if closer_n == 0
                else "CLOSER_ASSIGNED"
            ),
            "staff_ready": False,
            "human_commissioned": False,
            "invented_tolerance": False,
            "alchemist_soft_gap_not_policy": True,
        }
    finally:
        if own:
            c.close()
