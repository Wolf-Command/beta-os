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
import sys
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
OWNER_CONTROL_PERM = "venue.close.owner_control"

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
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.details = dict(details or {})


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
    include_cancelled: bool = False,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Load one close. By business_date, returns the current (non-CANCELLED) row.

    CANCELLED rows stay in history but do not block restart. Pass
    include_cancelled=True only when you intentionally want a cancelled row
    (e.g. Owner Control on that specific close_id — use close_id for that).
    """
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
            if include_cancelled:
                row = _row(
                    c.execute(
                        """
                        SELECT * FROM venue_daily_closes
                        WHERE entity_id=? AND venue_brand_id=? AND business_date=?
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (entity_id, venue_brand_id, date),
                    ).fetchone()
                )
            else:
                # Current close only — CANCELLED history must not block restart.
                row = _row(
                    c.execute(
                        """
                        SELECT * FROM venue_daily_closes
                        WHERE entity_id=? AND venue_brand_id=? AND business_date=?
                          AND state != 'CANCELLED'
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (entity_id, venue_brand_id, date),
                    ).fetchone()
                )
        return _public(row) if row else None
    finally:
        if own:
            c.close()


def _trail_before_after(meta: dict[str, Any] | None) -> tuple[Any, Any]:
    """Extract before/after recorded on a venue-close audit row."""
    m = meta or {}
    before: Any = m.get("before_state") if "before_state" in m else m.get("before")
    after: Any = m.get("after_state") if "after_state" in m else m.get("after")
    note = m.get("note")
    if (before is None or after is None) and note:
        try:
            parsed = json.loads(note) if isinstance(note, str) else note
            if isinstance(parsed, dict):
                if before is None:
                    before = parsed.get("before")
                if after is None:
                    after = parsed.get("after")
        except (json.JSONDecodeError, TypeError):
            pass
    return before, after


def audit_trail(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Ordered audit trail for one close from core_audit_events (append-only).

    Each entry: action, actor from the caller, occurred_at, before/after as recorded.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        cid = (close_id or "").strip()
        if not cid:
            return []
        rows = c.execute(
            """
            SELECT audit_event_id, action, actor_type, actor_person_id,
                   occurred_at, recorded_at, result, metadata_json
            FROM core_audit_events
            WHERE resource_type='venue_daily_close' AND resource_id=?
            ORDER BY occurred_at ASC, recorded_at ASC, rowid ASC
            """,
            (cid,),
        ).fetchall()
        trail: list[dict[str, Any]] = []
        for raw in rows:
            meta_raw = raw["metadata_json"]
            meta: dict[str, Any] | None = None
            if isinstance(meta_raw, str) and meta_raw:
                try:
                    meta = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta = None
            before, after = _trail_before_after(meta)
            trail.append(
                {
                    "audit_event_id": str(raw["audit_event_id"]),
                    "action": str(raw["action"] or ""),
                    "actor_type": str(raw["actor_type"] or ""),
                    "actor_person_id": (raw["actor_person_id"] or "").strip() or None,
                    "occurred_at": str(raw["occurred_at"] or ""),
                    "result": str(raw["result"] or ""),
                    "before": before,
                    "after": after,
                }
            )
        return trail
    finally:
        if own:
            c.close()


def list_closes(
    *,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    state: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    outlet_id: str | None = None,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Saved closes only — never recomputes from today's live ESB."""
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 200))
        sql = [
            "SELECT * FROM venue_daily_closes",
            "WHERE entity_id=? AND venue_brand_id=?",
        ]
        args: list[Any] = [entity_id, venue_brand_id]
        if state:
            sql.append("AND state=?")
            args.append(state.strip().upper())
        df = (date_from or "").strip()
        dt = (date_to or "").strip()
        if df:
            sql.append("AND business_date>=?")
            args.append(df)
        if dt:
            sql.append("AND business_date<=?")
            args.append(dt)
        oid = (outlet_id or "").strip()
        if oid:
            sql.append("AND outlet_id=?")
            args.append(oid)
        sql.append("ORDER BY business_date DESC LIMIT ?")
        args.append(lim)
        rows = c.execute(" ".join(sql), tuple(args)).fetchall()
        return [_public(dict(r)) for r in rows]
    finally:
        if own:
            c.close()


def closing_history(
    *,
    entity_id: str = ENTITY_BZG,
    venue_brand_id: str = BRAND_UMA,
    state: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    outlet_id: str | None = None,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """History board: each saved day + consolidated totals from CURRENT/final rows.

    Reads venue_daily_closes only. Does not call live ESB. SUPERSEDED EDC attempts
    are never double-counted here (totals come from close-row saved fields).
    """
    own = conn is None
    c = conn or db_connect()
    try:
        rows = list_closes(
            entity_id=entity_id,
            venue_brand_id=venue_brand_id,
            state=state,
            date_from=date_from,
            date_to=date_to,
            outlet_id=outlet_id,
            limit=limit,
            conn=c,
        )
        # Range totals: finalized/current saved states only — not CANCELLED/OPEN drafts.
        # SUPERSEDED EDC attempts live on evidence rows and are never summed here.
        _RANGE_EXCLUDE = frozenset({"CANCELLED", "OPEN"})
        countable = [
            r
            for r in rows
            if str(r.get("state") or "").upper() not in _RANGE_EXCLUDE
        ]
        cash_vals = [
            float(r["declared_cash_amount"])
            for r in countable
            if r.get("declared_cash_amount") is not None
        ]
        gross_vals: list[float] = []
        api_cash_vals: list[float] = []
        for r in countable:
            totals = r.get("esb_totals") or {}
            g = (
                totals.get("gross")
                or totals.get("gross_sales")
                or totals.get("GROSS")
                or totals.get("sales_grand_excl_other_cost")
                or totals.get("grand_total")
            )
            if g is not None:
                try:
                    gross_vals.append(float(g))
                except (TypeError, ValueError):
                    pass
            ac = totals.get("cash_from_payments")
            if ac is not None:
                try:
                    api_cash_vals.append(float(ac))
                except (TypeError, ValueError):
                    pass
        # Attach three-object labels on saved rows (no live ESB read).
        enriched = []
        for r in rows:
            item = dict(r)
            item["three_objects"] = three_close_objects(r)
            item["snapshot_frozen"] = bool(r.get("esb_fingerprint_sha256"))
            enriched.append(item)
        return {
            "ok": True,
            "source": "venue_daily_closes_saved",
            "live_esb_used": False,
            "closes": enriched,
            "count": len(enriched),
            "range": {
                "date_from": (date_from or "").strip() or None,
                "date_to": (date_to or "").strip() or None,
                "outlet_id": (outlet_id or "").strip() or None,
                "state": (state or "").strip().upper() or None,
            },
            "consolidated": {
                "days_counted": len(countable),
                "days_listed": len(enriched),
                "declared_cash_sum": round(sum(cash_vals), 2) if cash_vals else None,
                "api_cash_sum_from_saved_snapshot": (
                    round(sum(api_cash_vals), 2) if api_cash_vals else None
                ),
                "gross_sum_from_saved_esb": round(sum(gross_vals), 2) if gross_vals else None,
                "excludes_cancelled_and_open": True,
                "excludes_superseded_edc_attempts": True,
                "unavailable_when_null": True,
                "note": (
                    "Totals use saved close fields / CURRENT states only. "
                    "SUPERSEDED evidence excluded. Missing figures stay unavailable — never zero-filled. "
                    "Cancel unfinished does not rewrite these totals."
                ),
            },
            **HONESTY,
        }
    finally:
        if own:
            c.close()


_UNFINISHED_CANCEL_STATES = frozenset(
    {"OPEN", "DATA_CAPTURED", "EVIDENCE_SUBMITTED"}
)


def cancel_unfinished_close(
    close_id: str,
    *,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Staff/holder cancel of an unfinished draft. No history rewrite of VERIFIED_CLOSED.

    Abandons draft → CANCELLED. Evidence/photos/audit retained. No accounting entry.
    """
    cid = (close_id or "").strip()
    actor = (verified_person_id or "").strip()
    why = (reason or "").strip()
    if not cid:
        raise VenueCloseError("close_id required", code="missing_close_id")
    if not actor:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_take_attribution_columns(c)
        _assert_perm(
            verified_person_id=actor,
            permission_code="venue.close.submit",
            conn=c,
        )
        row = get_close(cid, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        state = str(row.get("state") or "").upper()
        if state == "VERIFIED_CLOSED":
            raise VenueCloseError(
                "Cannot cancel a completed close — manager/finance reopen required.",
                code="invalid_transition",
            )
        if state not in _UNFINISHED_CANCEL_STATES:
            raise VenueCloseError(
                f"Cancel unfinished only from {sorted(_UNFINISHED_CANCEL_STATES)} — current {state}.",
                code="invalid_transition",
            )
        holder = (row.get("taken_by_person_id") or "").strip()
        is_owner = False
        try:
            _assert_perm(
                verified_person_id=actor,
                permission_code=OWNER_CONTROL_PERM,
                conn=c,
            )
            is_owner = True
        except VenueCloseError:
            is_owner = False
        if holder and holder != actor and not is_owner:
            raise VenueCloseError(
                "Only the current closer (or Owner Control) can cancel this unfinished close.",
                code="forbidden",
                http_status=403,
            )

        before = close_work_snapshot(row, conn=c)
        ts = now_utc_iso()
        c.execute(
            """
            UPDATE venue_daily_closes
            SET state='CANCELLED', taken_by_person_id=NULL, taken_at=NULL, updated_at=?
            WHERE close_id=?
            """,
            (ts, cid),
        )
        _audit.safe_record(
            action="venue_close.cancel_unfinished",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=actor,
            actor_person_id=actor,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=cid,
            reason_code="cancel_unfinished",
            metadata={
                "reason": why or None,
                "business_date": row.get("business_date"),
                "before_state": state,
                "after_state": "CANCELLED",
                "before": before,
                "evidence_retained": True,
                "accounting_entry": False,
            },
            conn=c,
        )
        if commit:
            c.commit()
        refreshed = get_close(cid, conn=c)
        return {
            "ok": True,
            "close": refreshed,
            "cancelled": True,
            "evidence_retained": True,
            "accounting_entry": False,
            **HONESTY,
        }
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
        ensure_take_attribution_columns(c)
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
            # Current (non-CANCELLED) close already exists — do not open a second.
            return {
                **existing,
                "created": False,
                "restarted_after_cancel": False,
                "idempotent": True,
                **HONESTY,
            }

        # Race-safe insert: concurrent opens for the same date must not duplicate rows.
        c.execute("BEGIN IMMEDIATE")
        try:
            existing = get_close(
                business_date=date,
                entity_id=entity_id,
                venue_brand_id=venue_brand_id,
                conn=c,
            )
            if existing:
                c.rollback()
                return {
                    **existing,
                    "created": False,
                    "restarted_after_cancel": False,
                    "idempotent": True,
                    **HONESTY,
                }

            # Any CANCELLED rows for this date stay in history; we open a clean restart.
            prior_cancelled = c.execute(
                """
                SELECT close_id FROM venue_daily_closes
                WHERE entity_id=? AND venue_brand_id=? AND business_date=? AND state='CANCELLED'
                ORDER BY created_at DESC LIMIT 1
                """,
                (entity_id, venue_brand_id, date),
            ).fetchone()
            restarted = bool(prior_cancelled)

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
                reason_code="restarted_after_cancel" if restarted else "opened",
                metadata={
                    "business_date": date,
                    "venue_brand_id": venue_brand_id,
                    "restarted_after_cancel": restarted,
                    "prior_cancelled_close_id": (
                        str(prior_cancelled["close_id"]) if prior_cancelled else None
                    ),
                    "clean_dated_snapshot": True,
                    "before_state": None,
                    "after_state": "OPEN",
                },
                conn=c,
            )
            if commit:
                c.commit()
            else:
                c.rollback()
        except sqlite3.Error:
            c.rollback()
            raced = get_close(
                business_date=date,
                entity_id=entity_id,
                venue_brand_id=venue_brand_id,
                conn=c,
            )
            if raced:
                return {
                    **raced,
                    "created": False,
                    "restarted_after_cancel": False,
                    "idempotent": True,
                    **HONESTY,
                }
            raise
        out = get_close(cid, conn=c)
        assert out
        return {
            **out,
            "created": True,
            "restarted_after_cancel": restarted,
            "idempotent": False,
            **HONESTY,
        }
    finally:
        if own:
            c.close()



def _refresh_esb_warehouse_for_date(business_date: str) -> dict[str, Any]:
    """Pull live ESB for one business date into the warehouse (same-day close).

    Nightly ingest only loads *yesterday*, so evening Daily Close would otherwise
    always see an empty day. Idempotent. Never invents totals.
    """
    import subprocess
    script = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/esb_ingest.py")
    py = Path("/opt/homebrew/bin/python3")
    if not script.is_file():
        return {"ok": False, "error": "esb_ingest_missing", "path": str(script)}
    if not py.is_file():
        py = Path(sys.executable)
    try:
        proc = subprocess.run(
            [str(py), str(script), "--date", str(business_date).strip()],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 — surface as refresh failure
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}
    out = (proc.stdout or "")[-800:]
    err = (proc.stderr or "")[-400:]
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": out,
        "stderr_tail": err,
    }

def latest_final_history(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Most recent immutable FINAL freeze for a close (survives reopen)."""
    cid = (close_id or "").strip()
    if not cid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_final_history_table(c)
        row = c.execute(
            """
            SELECT * FROM venue_close_final_history
            WHERE close_id=?
            ORDER BY frozen_at DESC LIMIT 1
            """,
            (cid,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["esb_totals"] = _loads(d.pop("esb_totals_json", None))
        d["snapshot"] = _loads(d.pop("snapshot_json", None))
        d["immutable"] = True
        return d
    finally:
        if own:
            c.close()


def three_close_objects(
    row: dict[str, Any],
    *,
    live_totals: dict[str, Any] | None = None,
    live_meta: dict[str, Any] | None = None,
    final_history: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Three different objects: live ESB, dated closing snapshot, final historical close.

    Live operational data must never overwrite the dated snapshot or final record.
    Printed receipt figures are a separate retained source (see dual-source board).
    """
    state = str(row.get("state") or "").upper()
    stored = row.get("esb_totals") if isinstance(row.get("esb_totals"), dict) else {}
    fingerprint = (row.get("esb_fingerprint_sha256") or "").strip() or None
    frozen = bool(fingerprint)
    is_final = state == "VERIFIED_CLOSED"
    hist = final_history
    if hist is None and row.get("close_id"):
        hist = latest_final_history(str(row["close_id"]), conn=conn)
    final_payload: dict[str, Any] = {
        "object": "FINAL_HISTORICAL_CLOSE",
        "is_final": is_final or bool(hist),
        "state": state or None,
        "close_id": row.get("close_id"),
        "immutable_history_present": bool(hist),
        "note": (
            "Historical evidence after VERIFIED_CLOSED. "
            "Reopen freezes the original into venue_close_final_history; "
            "the working row may reopen but the freeze is immutable."
        ),
    }
    if hist:
        final_payload["history_id"] = hist.get("history_id")
        final_payload["frozen_at"] = hist.get("frozen_at")
        final_payload["frozen_by_person_id"] = hist.get("frozen_by_person_id")
        final_payload["state_at_freeze"] = hist.get("state_at_freeze")
        final_payload["esb_fingerprint_sha256"] = hist.get("esb_fingerprint_sha256")
        final_payload["totals"] = hist.get("esb_totals")
        final_payload["immutable"] = True
    elif is_final:
        final_payload["totals"] = stored if frozen else None
        final_payload["esb_fingerprint_sha256"] = fingerprint
        final_payload["immutable"] = True
    return {
        "live_esb_operational": {
            "object": "LIVE_ESB_OPERATIONAL",
            "mutates_close": False,
            "totals": live_totals,
            "meta": live_meta or {"source": "not_read"},
            "note": "Operational warehouse/API for the business date. Independent of the close draft.",
        },
        "dated_closing_snapshot": {
            "object": "DATED_CLOSING_SNAPSHOT",
            "frozen": frozen,
            "business_date": row.get("business_date"),
            "esb_fingerprint_sha256": fingerprint,
            "esb_pulled_at": row.get("esb_pulled_at"),
            "totals": stored if frozen else None,
            "immutable_while_open": True,
            "note": (
                "Working snapshot for this business date. Live ESB sync must not overwrite. "
                "Backdated closes use this date — never today's live sales."
            ),
        },
        "final_historical_close": final_payload,
        "api_and_receipt_are_separate_sources": True,
        "silent_overwrite": False,
    }


def _side_read_live_esb(
    business_date: str,
    *,
    stored_fingerprint: str | None,
    esb_path: Path | str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Read-only live warehouse view. Never writes close rows."""
    biz = (business_date or "").strip()
    if not biz:
        return None, {"source": "missing_business_date"}
    try:
        snap = _esb.snapshot_day(biz, esb_path=esb_path)
    except _esb.EsbSnapshotError as exc:
        return None, {
            "source": "live_read_failed",
            "live_read_error": str(exc)[:240],
            "live_read_code": getattr(exc, "code", None),
        }
    totals = dict(snap.get("totals") or {})
    live_fp = snap.get("fingerprint_sha256")
    return totals, {
        "source": "warehouse_payment_lines_live",
        "esb_pulled_at": snap.get("esb_pulled_at"),
        "fingerprint_sha256": live_fp,
        "stored_fingerprint_sha256": stored_fingerprint,
        "fingerprint_matches_stored": bool(
            stored_fingerprint and live_fp == stored_fingerprint
        ),
        "business_date": biz,
        "mutates_close": False,
    }


def capture_esb_snapshot(
    close_id: str,
    *,
    verified_person_id: str,
    business_date: str | None = None,
    esb_path: Path | str | None = None,
    identity: dict[str, Any] | None = None,
    force_recapture: bool = False,
    force_reason: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    own = conn is None
    c = conn or db_connect()
    try:
        _assert_perm(
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        row = get_close(close_id, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)
        try:
            from core import uma_hist_close_queue1 as _hist_q

            prot = _hist_q.mutation_block_reason(
                close_id, row, verified_person_id=verified, conn=c
            )
            if prot:
                raise VenueCloseError(prot, code="protected_close", http_status=403)
        except ImportError:
            pass
        _assert_close_business_date(row, business_date, action="capture ESB")
        _assert_holder_allows(
            row, verified_person_id=verified, conn=c, identity=identity
        )
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
        existing_fp = (row.get("esb_fingerprint_sha256") or "").strip() or None

        # Frozen dated snapshot: live sync must not overwrite stored API figures.
        if existing_fp and not force_recapture:
            live_totals, live_meta = _side_read_live_esb(
                biz, stored_fingerprint=existing_fp, esb_path=esb_path
            )
            stale = bool(live_meta.get("fingerprint_matches_stored") is False) and bool(
                live_meta.get("fingerprint_sha256")
            )
            # Stale flag only — never rewrite esb_totals / fingerprint.
            if stale != bool(row.get("fingerprint_stale")):
                assert_catalog_writable(Path(CATALOG_DB))
                c.execute(
                    "UPDATE venue_daily_closes SET fingerprint_stale=?, updated_at=? WHERE close_id=?",
                    (1 if stale else 0, now_utc_iso(), close_id),
                )
                if commit:
                    c.commit()
            out = get_close(close_id, conn=c)
            assert out
            objects = three_close_objects(
                out, live_totals=live_totals, live_meta=live_meta
            )
            return {
                **out,
                **HONESTY,
                "ok": True,
                "idempotent": True,
                "snapshot_frozen": True,
                "mutated": False,
                "recaptured": False,
                "fingerprint_stale": bool(out.get("fingerprint_stale")),
                "esb_live_status": "AVAILABLE" if live_totals is not None else "UNAVAILABLE",
                "esb_source": "dated_closing_snapshot",
                "esb_source_label": (
                    "Dated closing snapshot retained — live ESB side-read did not overwrite"
                ),
                "esb_empty_is_not_zero_sales": True,
                "live_esb_operational_side_read": {
                    "totals": live_totals,
                    "meta": live_meta,
                },
                "three_objects": objects,
                "api_and_receipt_are_separate_sources": True,
            }

        assert_catalog_writable(Path(CATALOG_DB))

        if existing_fp and force_recapture:
            why = (force_reason or "").strip()
            if not why:
                raise VenueCloseError(
                    "force_reason required to replace a frozen dated snapshot",
                    code="missing_force_reason",
                )
            _assert_perm(
                verified_person_id=verified,
                permission_code=OWNER_CONTROL_PERM,
                conn=c,
            )

        refresh_meta: dict[str, Any] | None = None
        try:
            snap = _esb.snapshot_day(biz, esb_path=esb_path)
        except _esb.EsbSnapshotError as exc:
            # Warehouse missing / unreadable → try same-day live pull once.
            refresh_meta = _refresh_esb_warehouse_for_date(biz)
            if refresh_meta.get("ok"):
                try:
                    snap = _esb.snapshot_day(biz, esb_path=esb_path)
                except _esb.EsbSnapshotError as exc2:
                    raise VenueCloseError(
                        f"ESB DATA UNAVAILABLE — cannot read live sales for {biz}. "
                        "Empty is not zero sales. Retry after ESB pull; photographed "
                        "closing receipt stays a separate dual source.",
                        code="esb_data_unavailable",
                        http_status=getattr(exc2, "http_status", 503) or 503,
                    ) from exc2
            else:
                raise VenueCloseError(
                    f"ESB DATA UNAVAILABLE — cannot read live sales for {biz}. "
                    "Empty is not zero sales. Retry after ESB pull; photographed "
                    "closing receipt stays a separate dual source.",
                    code="esb_data_unavailable",
                    http_status=getattr(exc, "http_status", 503) or 503,
                ) from exc
        if snap.get("incomplete"):
            # Nightly ingest is T+1 (yesterday only). Same-day close must live-pull.
            refresh_meta = refresh_meta or _refresh_esb_warehouse_for_date(biz)
            if refresh_meta.get("ok"):
                snap = _esb.snapshot_day(biz, esb_path=esb_path)
            if snap.get("incomplete"):
                # Do not write zero totals as a successful live pull.
                raise VenueCloseError(
                    f"ESB DATA UNAVAILABLE — no live sales for {biz}. "
                    "Empty is not zero sales. Retry after ESB pull; photographed "
                    "closing receipt stays a separate dual source.",
                    code="esb_data_unavailable",
                    http_status=409,
                )

        _assert_esb_snapshot_matches_close(row, snap)

        before_fp = existing_fp
        before_state = str(row.get("state") or "")
        before_work = close_work_snapshot(row, conn=c)
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
        after_row = get_close(close_id, conn=c)
        assert after_row
        record_reopen_working_change(
            close_id,
            actor_person_id=verified,
            action="esb_capture",
            before=before_work,
            after=close_work_snapshot(after_row, conn=c),
            conn=c,
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
            reason_code="esb_snapshot_force_recapture" if force_recapture else "esb_snapshot",
            metadata={
                "fingerprint": snap["fingerprint_sha256"],
                "prior_fingerprint": before_fp,
                "force_recapture": bool(force_recapture),
                "force_reason": (force_reason or "").strip() or None,
                "finished_count": snap["totals"]["finished_count"],
                "cash_from_payments": snap["totals"]["cash_from_payments"],
                "esb_live_status": "AVAILABLE",
                "esb_source": "warehouse_payment_lines",
                "business_date": biz,
                "before_state": before_state,
                "after_state": "DATA_CAPTURED",
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        out = get_close(close_id, conn=c)
        assert out
        objects = three_close_objects(
            out,
            live_totals=dict(snap.get("totals") or {}),
            live_meta={
                "source": "warehouse_payment_lines",
                "fingerprint_sha256": snap.get("fingerprint_sha256"),
                "esb_pulled_at": snap.get("esb_pulled_at"),
                "just_captured": True,
                "mutates_close": False,
            },
        )
        ret = {
            **out,
            **HONESTY,
            "ok": True,
            "snapshot_frozen": True,
            "mutated": True,
            "recaptured": bool(force_recapture and before_fp),
            "esb_live_status": "AVAILABLE",
            "esb_source": "warehouse_payment_lines",
            "esb_source_label": (
                "Dated closing snapshot from ESB payment lines for this business date "
                "(warehouse) — not settlement; not prior-day history"
            ),
            "esb_empty_is_not_zero_sales": True,
            "three_objects": objects,
            "api_and_receipt_are_separate_sources": True,
        }
        if refresh_meta is not None:
            ret["esb_same_day_refresh"] = {
                "ok": bool(refresh_meta.get("ok")),
                "returncode": refresh_meta.get("returncode"),
            }
        return ret
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
        try:
            from core import uma_hist_close_queue1 as _hist_q

            prot = _hist_q.mutation_block_reason(
                close_id, row, verified_person_id=verified, conn=c
            )
            if prot:
                raise VenueCloseError(prot, code="protected_close", http_status=403)
        except ImportError:
            pass
        _assert_holder_allows(
            row, verified_person_id=verified, conn=c, identity=identity
        )
        if row["state"] not in ("DATA_CAPTURED", "EVIDENCE_SUBMITTED"):
            raise VenueCloseError(
                f"cannot attach cash from state {row['state']}",
                code="invalid_transition",
            )

        existing = row.get("declared_cash_amount")
        if existing is not None and round(float(existing), 2) == round(amount, 2):
            out = get_close(close_id, conn=c)
            assert out
            return {
                **out,
                "idempotent": True,
                "evidence": None,
                "declared_cash_is_not_verified": True,
                **HONESTY,
            }

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

        before_work = close_work_snapshot(row, conn=c)
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
        after_row = get_close(close_id, conn=c)
        assert after_row
        record_reopen_working_change(
            close_id,
            actor_person_id=verified,
            action="declared_cash",
            before=before_work,
            after=close_work_snapshot(after_row, conn=c),
            conn=c,
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
        _assert_holder_allows(
            row, verified_person_id=verified, conn=c, identity=identity
        )
        if row["state"] == "VERIFIED_CLOSED":
            return {**row, "idempotent": True, **HONESTY}
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
        staff_expected: float | None = None
        try:
            from core import bzg_daily_close as _bzg_dc

            basis_ack = _bzg_dc.get_workflow_ack(
                close_id, "cash_expected_basis", conn=c
            )
            if basis_ack and basis_ack.get("expected_cash_in_till") is not None:
                staff_expected = round(float(basis_ack["expected_cash_in_till"]), 2)
        except Exception:  # noqa: BLE001
            staff_expected = None
        basis_cash = staff_expected if staff_expected is not None else esb_cash
        variance = round(declared - basis_cash, 2)
        policy = _active_variance_policy(
            c, entity_id=row["entity_id"], venue_brand_id=row["venue_brand_id"]
        )
        ts = now_utc_iso()

        if abs(variance) < 1e-9:
            # Clean path: RECONCILED then system VERIFIED_CLOSED (honesty: SUBMITTED ≠ RECONCILED ≠ VERIFIED)
            before_work = close_work_snapshot(row, conn=c)
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
            reconciled_row = get_close(close_id, conn=c)
            assert reconciled_row
            record_reopen_working_change(
                close_id,
                actor_person_id=verified,
                action="reconcile",
                before=before_work,
                after=close_work_snapshot(reconciled_row, conn=c),
                conn=c,
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
            _record_reopen_new_approval(
                close_id,
                approved_by_person_id=verified,
                approval_type="zero_variance_reconcile",
                conn=c,
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
            before_work = close_work_snapshot(row, conn=c)
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
            after_row = get_close(close_id, conn=c)
            assert after_row
            record_reopen_working_change(
                close_id,
                actor_person_id=verified,
                action="reconcile",
                before=before_work,
                after=close_work_snapshot(after_row, conn=c),
                conn=c,
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
        _record_reopen_new_approval(
            close_id,
            approved_by_person_id=verified,
            approval_type="verify_close",
            conn=c,
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
    ensure_current_close_unique(conn)
    ensure_final_history_table(conn)


def ensure_final_history_table(conn: sqlite3.Connection) -> None:
    """Immutable FINAL historical close copies (reopen never edits these)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS venue_close_final_history (
          history_id TEXT PRIMARY KEY,
          close_id TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          venue_brand_id TEXT NOT NULL,
          business_date TEXT NOT NULL,
          state_at_freeze TEXT NOT NULL,
          frozen_at TEXT NOT NULL,
          frozen_by_person_id TEXT NOT NULL,
          reason TEXT NULL,
          esb_fingerprint_sha256 TEXT NULL,
          esb_pulled_at TEXT NULL,
          esb_totals_json TEXT NULL,
          snapshot_json TEXT NOT NULL,
          FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_venue_close_final_history_close
          ON venue_close_final_history(close_id, frozen_at)
        """
    )
    ensure_reopen_chain_tables(conn)


def ensure_reopen_chain_tables(conn: sqlite3.Connection) -> None:
    """Reopen chain: REOPEN EVENT → CHANGES → NEW APPROVAL (ORIGINAL = final_history)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS venue_close_reopen_events (
          reopen_event_id TEXT PRIMARY KEY,
          close_id TEXT NOT NULL,
          final_history_id TEXT NOT NULL,
          actor_person_id TEXT NOT NULL,
          reason TEXT NOT NULL,
          reopened_at TEXT NOT NULL,
          prior_state TEXT NOT NULL,
          FOREIGN KEY (close_id) REFERENCES venue_daily_closes(close_id),
          FOREIGN KEY (final_history_id) REFERENCES venue_close_final_history(history_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_venue_close_reopen_events_close
          ON venue_close_reopen_events(close_id, reopened_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS venue_close_reopen_changes (
          change_id TEXT PRIMARY KEY,
          reopen_event_id TEXT NOT NULL,
          close_id TEXT NOT NULL,
          actor_person_id TEXT NOT NULL,
          changed_at TEXT NOT NULL,
          action TEXT NOT NULL,
          before_json TEXT NULL,
          after_json TEXT NULL,
          FOREIGN KEY (reopen_event_id) REFERENCES venue_close_reopen_events(reopen_event_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_venue_close_reopen_changes_event
          ON venue_close_reopen_changes(reopen_event_id, changed_at ASC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS venue_close_reopen_approvals (
          approval_id TEXT PRIMARY KEY,
          reopen_event_id TEXT NOT NULL,
          close_id TEXT NOT NULL,
          approved_by_person_id TEXT NOT NULL,
          approved_at TEXT NOT NULL,
          approval_type TEXT NOT NULL,
          FOREIGN KEY (reopen_event_id) REFERENCES venue_close_reopen_events(reopen_event_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_venue_close_reopen_approvals_event
          ON venue_close_reopen_approvals(reopen_event_id)
        """
    )


def _latest_open_reopen_event(
    close_id: str,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    """Most recent reopen on this close that has not yet received NEW APPROVAL."""
    ensure_reopen_chain_tables(conn)
    cid = (close_id or "").strip()
    if not cid:
        return None
    row = conn.execute(
        """
        SELECT e.*
        FROM venue_close_reopen_events e
        WHERE e.close_id=?
          AND NOT EXISTS (
            SELECT 1 FROM venue_close_reopen_approvals a
            WHERE a.reopen_event_id = e.reopen_event_id
          )
        ORDER BY e.reopened_at DESC
        LIMIT 1
        """,
        (cid,),
    ).fetchone()
    return dict(row) if row else None


def record_reopen_working_change(
    close_id: str,
    *,
    actor_person_id: str,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    conn: sqlite3.Connection,
) -> str | None:
    """Record a working-close mutation after an open REOPEN EVENT."""
    evt = _latest_open_reopen_event(close_id, conn=conn)
    if not evt:
        return None
    change_id = f"VCRCh-{uuid.uuid4()}"
    ts = now_utc_iso()
    conn.execute(
        """
        INSERT INTO venue_close_reopen_changes (
          change_id, reopen_event_id, close_id, actor_person_id,
          changed_at, action, before_json, after_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            change_id,
            evt["reopen_event_id"],
            close_id,
            (actor_person_id or "").strip(),
            ts,
            (action or "").strip(),
            json.dumps(before or {}, separators=(",", ":"), ensure_ascii=False),
            json.dumps(after or {}, separators=(",", ":"), ensure_ascii=False),
        ),
    )
    return change_id


def _record_reopen_new_approval(
    close_id: str,
    *,
    approved_by_person_id: str | None,
    approval_type: str,
    conn: sqlite3.Connection,
) -> str | None:
    """Record NEW APPROVAL — distinct from the REOPEN EVENT itself."""
    evt = _latest_open_reopen_event(close_id, conn=conn)
    if not evt:
        return None
    approval_id = f"VCRAp-{uuid.uuid4()}"
    ts = now_utc_iso()
    actor = (approved_by_person_id or "").strip() or "SYSTEM"
    conn.execute(
        """
        INSERT INTO venue_close_reopen_approvals (
          approval_id, reopen_event_id, close_id,
          approved_by_person_id, approved_at, approval_type
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            evt["reopen_event_id"],
            close_id,
            actor,
            ts,
            (approval_type or "").strip(),
        ),
    )
    return approval_id


def reopen_chain(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Four-stage chain: ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_reopen_chain_tables(c)
        cid = (close_id or "").strip()
        original = latest_final_history(cid, conn=c)
        evt_row = c.execute(
            """
            SELECT e.* FROM venue_close_reopen_events e
            WHERE e.close_id=?
            ORDER BY e.reopened_at DESC LIMIT 1
            """,
            (cid,),
        ).fetchone()
        reopen_event = dict(evt_row) if evt_row else None
        changes: list[dict[str, Any]] = []
        approval: dict[str, Any] | None = None
        if reopen_event:
            rid = str(reopen_event["reopen_event_id"])
            ch_rows = c.execute(
                """
                SELECT * FROM venue_close_reopen_changes
                WHERE reopen_event_id=?
                ORDER BY changed_at ASC
                """,
                (rid,),
            ).fetchall()
            for raw in ch_rows:
                ch = dict(raw)
                ch["before"] = _loads(ch.pop("before_json", None))
                ch["after"] = _loads(ch.pop("after_json", None))
                changes.append(ch)
            appr_row = c.execute(
                """
                SELECT * FROM venue_close_reopen_approvals
                WHERE reopen_event_id=?
                LIMIT 1
                """,
                (rid,),
            ).fetchone()
            approval = dict(appr_row) if appr_row else None
        return {
            "close_id": cid,
            "original": original,
            "reopen_event": reopen_event,
            "changes": changes,
            "new_approval": approval,
            "chain_complete": bool(
                original and reopen_event and changes and approval
            ),
        }
    finally:
        if own:
            c.close()


def ensure_current_close_unique(conn: sqlite3.Connection) -> None:
    """One CURRENT close per outlet+date; CANCELLED history may coexist for restart.

    Rebuilds the table once to drop the old table-level UNIQUE that blocked
    restart after cancel. Partial unique index enforces the safety rule.
    """
    existing = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        ("ux_venue_daily_closes_current",),
    ).fetchone()
    if existing:
        return
    table_sql_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='venue_daily_closes'"
    ).fetchone()
    table_sql = str(table_sql_row[0] or "") if table_sql_row else ""
    needs_rebuild = (
        "UNIQUE (entity_id, venue_brand_id, business_date)" in table_sql
        or "UNIQUE(entity_id, venue_brand_id, business_date)" in table_sql
    )
    if needs_rebuild:
        cols = [
            str(r[1])
            for r in conn.execute("PRAGMA table_info(venue_daily_closes)").fetchall()
        ]
        col_list = ", ".join(cols)
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            """
            CREATE TABLE venue_daily_closes__restart (
              close_id TEXT PRIMARY KEY,
              entity_id TEXT NOT NULL,
              venue_brand_id TEXT NOT NULL,
              business_date TEXT NOT NULL,
              state TEXT NOT NULL CHECK (
                state IN (
                  'OPEN',
                  'DATA_CAPTURED',
                  'EVIDENCE_SUBMITTED',
                  'RECONCILED',
                  'VARIANCE_REQUIRES_POLICY',
                  'EXCEPTION',
                  'RESOLVED',
                  'VERIFIED_CLOSED',
                  'CANCELLED'
                )
              ),
              esb_fingerprint_sha256 TEXT NULL,
              esb_pulled_at TEXT NULL,
              esb_query_meta_json TEXT NULL,
              esb_totals_json TEXT NULL,
              declared_cash_amount REAL NULL,
              declared_cash_evidence_id TEXT NULL,
              variance_cash_amount REAL NULL,
              variance_policy_id TEXT NULL,
              work_item_id TEXT NULL,
              fingerprint_stale INTEGER NOT NULL DEFAULT 0 CHECK (fingerprint_stale IN (0, 1)),
              submitted_by_person_id TEXT NULL,
              resolved_at TEXT NULL,
              resolved_by_person_id TEXT NULL,
              resolve_evidence_id TEXT NULL,
              verified_at TEXT NULL,
              verified_by_person_id TEXT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              outlet_id TEXT,
              cost_centre_id TEXT,
              revenue_centre_id TEXT,
              taken_by_person_id TEXT NULL,
              taken_at TEXT NULL
            )
            """
        )
        # Copy only columns that exist on both sides.
        dest_cols = [
            str(r[1])
            for r in conn.execute("PRAGMA table_info(venue_daily_closes__restart)").fetchall()
        ]
        shared = [c for c in dest_cols if c in cols]
        shared_sql = ", ".join(shared)
        conn.execute(
            f"INSERT INTO venue_daily_closes__restart ({shared_sql}) "
            f"SELECT {shared_sql} FROM venue_daily_closes"
        )
        conn.execute("DROP TABLE venue_daily_closes")
        conn.execute(
            "ALTER TABLE venue_daily_closes__restart RENAME TO venue_daily_closes"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_state "
            "ON venue_daily_closes(state)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_brand_date "
            "ON venue_daily_closes(venue_brand_id, business_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_work_item "
            "ON venue_daily_closes(work_item_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_venue_daily_closes_outlet "
            "ON venue_daily_closes(outlet_id)"
        )
        conn.execute("PRAGMA foreign_keys=ON")
        _ = col_list  # kept for readability / debug
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_venue_daily_closes_current
          ON venue_daily_closes(entity_id, venue_brand_id, business_date)
          WHERE state != 'CANCELLED'
        """
    )


def _person_display_name(conn: sqlite3.Connection, person_id: str | None) -> str | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    try:
        row = conn.execute(
            "SELECT display_name FROM org_persons WHERE person_id=?",
            (pid,),
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row:
        return None
    name = str(row["display_name"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
    return name or None


def _count_if_table(conn: sqlite3.Connection, table: str, close_id: str) -> int:
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if not exists:
            return 0
        return int(
            conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE close_id=?",
                (close_id,),
            ).fetchone()[0]
        )
    except sqlite3.Error:
        return 0


def close_work_snapshot(
    row: dict[str, Any],
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Preserved-work fingerprint for takeover audit (no wipe, no delete)."""
    cid = str(row.get("close_id") or "")
    return {
        "close_id": cid,
        "business_date": row.get("business_date"),
        "state": row.get("state"),
        "taken_by_person_id": row.get("taken_by_person_id"),
        "taken_at": row.get("taken_at"),
        "submitted_by_person_id": row.get("submitted_by_person_id"),
        "declared_cash_amount": row.get("declared_cash_amount"),
        "declared_cash_evidence_id": row.get("declared_cash_evidence_id"),
        "esb_fingerprint_sha256": row.get("esb_fingerprint_sha256"),
        "esb_pulled_at": row.get("esb_pulled_at"),
        "variance_cash_amount": row.get("variance_cash_amount"),
        "work_item_id": row.get("work_item_id"),
        "edc_receipt_count": _count_if_table(conn, "venue_close_edc_receipts", cid),
        "edc_line_count": _count_if_table(conn, "venue_close_edc_lines", cid),
        "esb_closing_receipt_count": _count_if_table(
            conn, "venue_close_esb_closing_receipts", cid
        ),
        "till_evidence_count": _count_if_table(conn, "venue_close_till_evidence", cid),
        "vision_event_count": _count_if_table(conn, "venue_close_vision_events", cid),
    }


def close_governance_info(
    row: dict[str, Any] | None,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    """Original closer vs current holder; latest takeover audit when holder changed."""
    if not row:
        return None
    cid = str(row.get("close_id") or "")
    submitted = (row.get("submitted_by_person_id") or "").strip() or None
    taken_by = (row.get("taken_by_person_id") or "").strip() or None
    original = submitted or taken_by
    taken_over = bool(original and taken_by and taken_by != original)

    takeover_reason = None
    takeover_at = None
    takeover_actor = None
    if taken_over and cid:
        try:
            ev = conn.execute(
                """
                SELECT actor_person_id, occurred_at, metadata_json
                FROM core_audit_events
                WHERE resource_id=? AND action='venue_close.takeover' AND result='ALLOWED'
                ORDER BY occurred_at DESC LIMIT 1
                """,
                (cid,),
            ).fetchone()
        except sqlite3.Error:
            ev = None
        if ev:
            takeover_actor = str(ev["actor_person_id"] or "").strip() or None
            takeover_at = ev["occurred_at"]
            try:
                meta = json.loads(ev["metadata_json"] or "{}")
            except json.JSONDecodeError:
                meta = {}
            takeover_reason = (meta.get("reason") or "").strip() or None

    return {
        "close_id": cid,
        "business_date": row.get("business_date"),
        "outlet_id": row.get("outlet_id") or row.get("venue_brand_id"),
        "original_closer_person_id": original,
        "original_closer_display_name": _person_display_name(conn, original),
        "current_holder_person_id": taken_by,
        "current_holder_display_name": _person_display_name(conn, taken_by),
        "taken_over": taken_over,
        "taken_over_by_person_id": taken_by if taken_over else None,
        "taken_over_by_display_name": _person_display_name(conn, taken_by) if taken_over else None,
        "taken_over_at": (takeover_at or row.get("taken_at")) if taken_over else None,
        "takeover_reason": takeover_reason,
        "takeover_actor_person_id": takeover_actor,
        "takeover_actor_display_name": _person_display_name(conn, takeover_actor),
        "started_by_person_id": submitted,
        "started_at": row.get("created_at"),
    }


def close_holder_info(
    row: dict[str, Any] | None,
    *,
    conn: sqlite3.Connection,
    viewer_person_id: str | None = None,
) -> dict[str, Any] | None:
    """Public holder payload for concurrent-lock UI / takeover."""
    if not row:
        return None
    taken_by = (row.get("taken_by_person_id") or "").strip() or None
    viewer = (viewer_person_id or "").strip() or None
    held_by_other = bool(taken_by and viewer and taken_by != viewer)
    return {
        "close_id": row.get("close_id"),
        "business_date": row.get("business_date"),
        "state": row.get("state"),
        "taken_by_person_id": taken_by,
        "taken_by_display_name": _person_display_name(conn, taken_by),
        "taken_at": row.get("taken_at"),
        "held_by_other": held_by_other,
        "held_by_self": bool(taken_by and viewer and taken_by == viewer),
        "work": close_work_snapshot(row, conn=conn),
    }


def _assert_close_business_date(
    row: dict[str, Any],
    business_date: str | None,
    *,
    action: str = "mutate",
) -> None:
    """Reject when caller pins a business_date that does not match the close row."""
    claimed = (business_date or "").strip()
    if not claimed:
        return
    actual = (row.get("business_date") or "").strip()
    if claimed != actual:
        raise VenueCloseError(
            f"business_date {claimed} does not match close date {actual}; "
            f"cannot {action} on a different day",
            code="wrong_business_date",
            http_status=409,
            details={
                "claimed_business_date": claimed,
                "close_business_date": actual,
                "close_id": row.get("close_id"),
            },
        )


def _assert_esb_snapshot_matches_close(
    row: dict[str, Any],
    snap: dict[str, Any],
) -> None:
    """Fail closed if warehouse snapshot is not for this close's business date."""
    close_biz = (row.get("business_date") or "").strip()
    meta = snap.get("query_meta") or {}
    snap_biz = (meta.get("business_date") or "").strip()
    if snap_biz and close_biz and snap_biz != close_biz:
        raise VenueCloseError(
            f"ESB snapshot is for {snap_biz} but close is for {close_biz}; "
            "will not copy another day's totals onto this close",
            code="wrong_business_date",
            http_status=409,
            details={
                "snapshot_business_date": snap_biz,
                "close_business_date": close_biz,
                "close_id": row.get("close_id"),
            },
        )


def _assert_holder_allows(
    row: dict[str, Any],
    *,
    verified_person_id: str,
    conn: sqlite3.Connection,
    identity: dict[str, Any] | None = None,
) -> None:
    """Block mutations while another authorised closer holds the take lock."""
    verified = (verified_person_id or "").strip()
    taken_by = (row.get("taken_by_person_id") or "").strip()
    if not taken_by or taken_by == verified:
        return
    holder = close_holder_info(row, conn=conn, viewer_person_id=verified)
    cid = str(row.get("close_id") or "")
    _audit.safe_record(
        action="venue_close.mutate",
        result="DENIED",
        source="venue_close",
        actor_type="PERSON",
        verified_person_id=verified,
        actor_person_id=verified,
        identity_assurance=(identity or {}).get("identity_assurance"),
        resource_type="venue_daily_close",
        resource_id=cid,
        reason_code="concurrent_take",
        metadata={"taken_by_person_id": taken_by, "holder": holder},
        conn=conn,
    )
    raise VenueCloseError(
        "This close is already taken by another authorised closer.",
        code="concurrent_take",
        http_status=409,
        details={
            "holder": holder,
            "governed_takeover": True,
            "requires_permission": "venue.close.reassign",
            "requires_reason": True,
        },
    )


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
            holder = close_holder_info(row, conn=c, viewer_person_id=verified)
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
                    "holder": holder,
                },
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                "This close is already taken by another authorised closer.",
                code="concurrent_take",
                http_status=409,
                details={
                    "holder": holder,
                    "governed_takeover": True,
                    "requires_permission": "venue.close.reassign",
                    "requires_reason": True,
                },
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
                holder = close_holder_info(refreshed, conn=c, viewer_person_id=verified)
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
                        "taken_by_person_id": won,
                        "race": True,
                        "authz": authz,
                        "holder": holder,
                    },
                    conn=c,
                )
                if commit:
                    c.commit()
                raise VenueCloseError(
                    "This close is already taken by another authorised closer.",
                    code="concurrent_take",
                    http_status=409,
                    details={
                        "holder": holder,
                        "governed_takeover": True,
                        "requires_permission": "venue.close.reassign",
                        "requires_reason": True,
                    },
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


def reassign_venue_close(
    close_id: str,
    *,
    verified_person_id: str,
    new_holder_person_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    mode: str = "reassign",
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Governed reassign / take-over. Preserves work. Does not delete the close.

    Requires venue.close.reassign (Captain / HFB / FB-Ops / Owner — not cashier).
    New holder must be authorised for the venue close (roster or oversight).
    Reason required. Full audit with before/after work snapshot.
    """
    cid = (close_id or "").strip()
    actor = (verified_person_id or "").strip()
    new_holder = (new_holder_person_id or "").strip()
    why = (reason or "").strip()
    mode_norm = (mode or "reassign").strip().lower()
    if mode_norm not in {"reassign", "takeover"}:
        mode_norm = "reassign"
    if not cid:
        raise VenueCloseError("close_id required", code="missing_close_id")
    if not actor:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    if not new_holder:
        raise VenueCloseError(
            "new_holder_person_id required",
            code="missing_new_holder",
        )
    if not why:
        raise VenueCloseError(
            "Reason required for take over / reassign.",
            code="missing_reason",
            http_status=400,
        )

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_take_attribution_columns(c)
        row = get_close(cid, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)

        brand = str(row.get("venue_brand_id") or BRAND_UMA)
        entity = str(row.get("entity_id") or ENTITY_BZG)

        _assert_perm(
            verified_person_id=actor,
            permission_code="venue.close.reassign",
            conn=c,
        )

        actor_authz = person_authorised_for_venue_close(
            actor,
            venue_brand_id=brand,
            entity_id=entity,
            conn=c,
        )
        if not actor_authz.get("allowed"):
            _audit.safe_record(
                action=f"venue_close.{mode_norm}",
                result="DENIED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=actor,
                actor_person_id=actor,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code=str(actor_authz.get("reason") or "not_on_assignment"),
                metadata={"authz": actor_authz, "reason": why},
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                actor_authz.get("message") or "This close is not on your assignment.",
                code="forbidden",
                http_status=403,
            )

        new_authz = person_authorised_for_venue_close(
            new_holder,
            venue_brand_id=brand,
            entity_id=entity,
            conn=c,
        )
        if not new_authz.get("allowed"):
            _audit.safe_record(
                action=f"venue_close.{mode_norm}",
                result="DENIED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=actor,
                actor_person_id=actor,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code="new_holder_not_authorised",
                metadata={
                    "new_holder_person_id": new_holder,
                    "new_holder_authz": new_authz,
                    "reason": why,
                },
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                "New closer is not authorised for this venue close.",
                code="new_holder_forbidden",
                http_status=403,
                details={"new_holder_person_id": new_holder, "authz": new_authz},
            )

        if row.get("state") in TERMINAL:
            raise VenueCloseError(
                f"close is terminal ({row['state']})",
                code="invalid_transition",
            )

        before = close_work_snapshot(row, conn=c)
        prior_holder = (row.get("taken_by_person_id") or "").strip() or None
        ts = now_utc_iso()

        if prior_holder == new_holder:
            _audit.safe_record(
                action=f"venue_close.{mode_norm}",
                result="ALLOWED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=actor,
                actor_person_id=actor,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code=f"{mode_norm}_idempotent",
                metadata={
                    "reason": why,
                    "mode": mode_norm,
                    "prior_holder_person_id": prior_holder,
                    "new_holder_person_id": new_holder,
                    "prior_holder_display_name": _person_display_name(c, prior_holder),
                    "new_holder_display_name": _person_display_name(c, new_holder),
                    "before_state": str(before.get("state") or ""),
                    "after_state": str(before.get("state") or ""),
                    "work_preserved": True,
                    "governed_object_id": cid,
                    "note": json.dumps(
                        {"before": before, "after": before},
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )[:3500],
                },
                conn=c,
            )
            if commit:
                c.commit()
            out = get_close(cid, conn=c)
            assert out
            return {
                **out,
                "reassigned": True,
                "takeover": mode_norm == "takeover",
                "mode": mode_norm,
                "reason": why,
                "prior_holder_person_id": prior_holder,
                "prior_holder_display_name": _person_display_name(c, prior_holder),
                "new_holder_person_id": new_holder,
                "new_holder_display_name": _person_display_name(c, new_holder),
                "before": before,
                "after": before,
                "work_preserved": True,
                "holder": close_holder_info(out, conn=c, viewer_person_id=actor),
                **HONESTY,
            }

        c.execute(
            """
            UPDATE venue_daily_closes
            SET taken_by_person_id=?, taken_at=?, updated_at=?
            WHERE close_id=?
            """,
            (new_holder, ts, ts, cid),
        )
        refreshed = get_close(cid, conn=c)
        assert refreshed
        after = close_work_snapshot(refreshed, conn=c)
        # Work fields other than holder attribution must be unchanged.
        work_keys = (
            "state",
            "declared_cash_amount",
            "declared_cash_evidence_id",
            "esb_fingerprint_sha256",
            "esb_pulled_at",
            "variance_cash_amount",
            "work_item_id",
            "edc_receipt_count",
            "edc_line_count",
            "esb_closing_receipt_count",
            "till_evidence_count",
            "vision_event_count",
        )
        for key in work_keys:
            if before.get(key) != after.get(key):
                raise VenueCloseError(
                    f"work preservation failed on {key}",
                    code="work_not_preserved",
                    http_status=500,
                )

        _audit.safe_record(
            action=f"venue_close.{mode_norm}",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=actor,
            actor_person_id=actor,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=cid,
            reason_code=mode_norm,
            metadata={
                "reason": why,
                "mode": mode_norm,
                "prior_holder_person_id": prior_holder,
                "prior_holder_display_name": _person_display_name(c, prior_holder),
                "new_holder_person_id": new_holder,
                "new_holder_display_name": _person_display_name(c, new_holder),
                "before_state": str(before.get("state") or ""),
                "after_state": str(after.get("state") or ""),
                "work_preserved": True,
                "taken_at": ts,
                "governed_object_id": cid,
                "note": json.dumps(
                    {"before": before, "after": after},
                    separators=(",", ":"),
                    ensure_ascii=False,
                )[:3500],
            },
            conn=c,
        )
        if commit:
            c.commit()
        return {
            **refreshed,
            "reassigned": True,
            "takeover": mode_norm == "takeover",
            "mode": mode_norm,
            "reason": why,
            "prior_holder_person_id": prior_holder,
            "prior_holder_display_name": _person_display_name(c, prior_holder),
            "new_holder_person_id": new_holder,
            "new_holder_display_name": _person_display_name(c, new_holder),
            "before": before,
            "after": after,
            "work_preserved": True,
            "holder": close_holder_info(refreshed, conn=c, viewer_person_id=actor),
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def take_over_venue_close(
    close_id: str,
    *,
    verified_person_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Actor becomes holder. Same gates as reassign; reason required."""
    return reassign_venue_close(
        close_id,
        verified_person_id=verified_person_id,
        new_holder_person_id=verified_person_id,
        reason=reason,
        identity=identity,
        mode="takeover",
        conn=conn,
        commit=commit,
    )


# Owner Control / Break Glass — assignment-derived (ROLE-MATT), not email.
# Reversible ops controls only — never money movement / bank execution.
OWNER_CONTROL_ACTIONS = frozenset(
    {
        "reopen",
        "cancel",
        "unlock_abandoned",
        "override_lock",
        "return_for_correction",
        "correct_assignment",
    }
)
# States that may rewind to DATA_CAPTURED for correction (evidence kept).
_RETURN_FROM = frozenset(
    {
        "EVIDENCE_SUBMITTED",
        "RECONCILED",
        "VARIANCE_REQUIRES_POLICY",
        "EXCEPTION",
        "RESOLVED",
    }
)


def owner_control_venue_close(
    close_id: str,
    *,
    verified_person_id: str,
    action: str,
    reason: str,
    new_holder_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Canonical Owner Control for Daily Close (Break Glass).

    Authority: org Assignment → ROLE-MATT (or role granted venue.close.owner_control).
    Not hardcoded email. Every intervention audited with before/after.
    Does not move money or execute bank settlement.
    """
    cid = (close_id or "").strip()
    actor = (verified_person_id or "").strip()
    act = (action or "").strip().lower()
    why = (reason or "").strip()
    if not cid:
        raise VenueCloseError("close_id required", code="missing_close_id")
    if not actor:
        raise VenueCloseError("verified_person_id required", code="missing_verified_person")
    if act not in OWNER_CONTROL_ACTIONS:
        raise VenueCloseError(
            f"unknown owner action: {action}",
            code="invalid_owner_action",
            http_status=400,
            details={"allowed": sorted(OWNER_CONTROL_ACTIONS)},
        )
    if not why:
        raise VenueCloseError(
            "Reason required for Owner Control.",
            code="missing_reason",
            http_status=400,
        )

    # correct_assignment delegates to governed reassign (same audit surface).
    if act == "correct_assignment":
        target = (new_holder_person_id or "").strip()
        if not target:
            raise VenueCloseError(
                "new_holder_person_id required for correct_assignment",
                code="missing_new_holder",
            )
        # Owner control perm required in addition to reassign path.
        own_gate = conn is None
        c_gate = conn or db_connect()
        try:
            _assert_perm(
                verified_person_id=actor,
                permission_code=OWNER_CONTROL_PERM,
                conn=c_gate,
            )
        finally:
            if own_gate:
                c_gate.close()
        out = reassign_venue_close(
            cid,
            verified_person_id=actor,
            new_holder_person_id=target,
            reason=why,
            identity=identity,
            mode="reassign",
            conn=conn,
            commit=commit,
        )
        return {
            **out,
            "owner_control": True,
            "owner_action": act,
            "reversible_ops_control": True,
            "money_movement": False,
        }

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_take_attribution_columns(c)
        row = get_close(cid, conn=c)
        if not row:
            raise VenueCloseError("close not found", code="not_found", http_status=404)

        brand = str(row.get("venue_brand_id") or BRAND_UMA)
        entity = str(row.get("entity_id") or ENTITY_BZG)

        _assert_perm(
            verified_person_id=actor,
            permission_code=OWNER_CONTROL_PERM,
            conn=c,
        )
        actor_authz = person_authorised_for_venue_close(
            actor,
            venue_brand_id=brand,
            entity_id=entity,
            conn=c,
        )
        if not actor_authz.get("allowed"):
            _audit.safe_record(
                action=f"venue_close.owner_{act}",
                result="DENIED",
                source="venue_close",
                actor_type="PERSON",
                verified_person_id=actor,
                actor_person_id=actor,
                identity_assurance=(identity or {}).get("identity_assurance"),
                resource_type="venue_daily_close",
                resource_id=cid,
                reason_code=str(actor_authz.get("reason") or "not_on_assignment"),
                metadata={
                    "reason": why,
                    "owner_action": act,
                    "entity_id": entity,
                    "venue_brand_id": brand,
                    "reversible_ops_control": True,
                },
                conn=c,
            )
            if commit:
                c.commit()
            raise VenueCloseError(
                actor_authz.get("message") or "Owner Control not on your assignment.",
                code="forbidden",
                http_status=403,
            )

        before = close_work_snapshot(row, conn=c)
        prior_holder = (row.get("taken_by_person_id") or "").strip() or None
        prior_state = str(row.get("state") or "")
        ts = now_utc_iso()
        target_state = prior_state
        clear_holder = False
        set_holder_to_actor = False
        final_history_id: str | None = None
        reopen_event_id: str | None = None

        if act == "cancel":
            if prior_state == "VERIFIED_CLOSED":
                raise VenueCloseError(
                    "Cannot cancel a verified-closed day — reopen first if correction needed.",
                    code="invalid_transition",
                )
            target_state = "CANCELLED"
        elif act == "reopen":
            if prior_state not in TERMINAL:
                raise VenueCloseError(
                    "reopen applies to VERIFIED_CLOSED or CANCELLED — use return_for_correction otherwise.",
                    code="invalid_transition",
                )
            # If a restarted current close already exists for this date, do not revive CANCELLED.
            if prior_state == "CANCELLED":
                current = get_close(
                    business_date=str(row.get("business_date") or ""),
                    entity_id=entity,
                    venue_brand_id=brand,
                    conn=c,
                )
                if current and str(current.get("close_id")) != cid:
                    raise VenueCloseError(
                        "A current close already exists for this outlet and business date. "
                        f"Use {current.get('close_id')} — cancelled history stays immutable.",
                        code="current_close_exists",
                        http_status=409,
                        details={
                            "current_close_id": current.get("close_id"),
                            "cancelled_close_id": cid,
                        },
                    )
            # Freeze VERIFIED_CLOSED original before working-row reopen (immutable history).
            if prior_state == "VERIFIED_CLOSED":
                ensure_final_history_table(c)
                final_history_id = f"VCFH-{uuid.uuid4()}"
                c.execute(
                    """
                    INSERT INTO venue_close_final_history (
                      history_id, close_id, entity_id, venue_brand_id, business_date,
                      state_at_freeze, frozen_at, frozen_by_person_id, reason,
                      esb_fingerprint_sha256, esb_pulled_at, esb_totals_json, snapshot_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        final_history_id,
                        cid,
                        entity,
                        brand,
                        str(row.get("business_date") or ""),
                        prior_state,
                        ts,
                        actor,
                        why,
                        row.get("esb_fingerprint_sha256"),
                        row.get("esb_pulled_at"),
                        json.dumps(row.get("esb_totals") or {}, separators=(",", ":")),
                        json.dumps(before, separators=(",", ":"), ensure_ascii=False),
                    ),
                )
                ensure_reopen_chain_tables(c)
                reopen_event_id = f"VCRE-{uuid.uuid4()}"
                c.execute(
                    """
                    INSERT INTO venue_close_reopen_events (
                      reopen_event_id, close_id, final_history_id,
                      actor_person_id, reason, reopened_at, prior_state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reopen_event_id,
                        cid,
                        final_history_id,
                        actor,
                        why,
                        ts,
                        prior_state,
                    ),
                )
            target_state = "OPEN"
            set_holder_to_actor = True
        elif act in {"unlock_abandoned", "override_lock"}:
            if prior_state in TERMINAL:
                raise VenueCloseError(
                    f"cannot unlock holder on terminal close ({prior_state})",
                    code="invalid_transition",
                )
            clear_holder = bool(prior_holder)
            target_state = prior_state
        elif act == "return_for_correction":
            if prior_state not in _RETURN_FROM:
                raise VenueCloseError(
                    f"return_for_correction not allowed from {prior_state}",
                    code="invalid_transition",
                    details={"allowed_from": sorted(_RETURN_FROM)},
                )
            target_state = "DATA_CAPTURED"
            set_holder_to_actor = True
        else:
            raise VenueCloseError(
                f"unhandled owner action: {act}",
                code="invalid_owner_action",
            )

        # Apply mutation — never delete evidence / audit / receipts.
        if clear_holder and target_state == prior_state:
            c.execute(
                """
                UPDATE venue_daily_closes
                SET taken_by_person_id=NULL, taken_at=NULL, updated_at=?
                WHERE close_id=?
                """,
                (ts, cid),
            )
        elif set_holder_to_actor:
            c.execute(
                """
                UPDATE venue_daily_closes
                SET state=?, taken_by_person_id=?, taken_at=?, updated_at=?
                WHERE close_id=?
                """,
                (target_state, actor, ts, ts, cid),
            )
        elif target_state != prior_state:
            c.execute(
                """
                UPDATE venue_daily_closes
                SET state=?, updated_at=?
                WHERE close_id=?
                """,
                (target_state, ts, cid),
            )

        refreshed = get_close(cid, conn=c)
        assert refreshed
        after = close_work_snapshot(refreshed, conn=c)

        # Evidence / receipt counts must be preserved (no wipe).
        for key in (
            "declared_cash_amount",
            "declared_cash_evidence_id",
            "esb_fingerprint_sha256",
            "edc_receipt_count",
            "edc_line_count",
            "esb_closing_receipt_count",
            "till_evidence_count",
            "vision_event_count",
        ):
            if before.get(key) != after.get(key):
                raise VenueCloseError(
                    f"work preservation failed on {key}",
                    code="work_not_preserved",
                    http_status=500,
                )

        roles = sorted(_active_role_ids(actor, c) & CLOSE_OVERSIGHT_ROLES)
        _audit.safe_record(
            action=f"venue_close.owner_{act}",
            result="ALLOWED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id=actor,
            actor_person_id=actor,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=cid,
            reason_code=act,
            metadata={
                "reason": why,
                "owner_action": act,
                "mode": act,
                "prior_holder_person_id": prior_holder,
                "prior_holder_display_name": _person_display_name(c, prior_holder),
                "new_holder_person_id": refreshed.get("taken_by_person_id"),
                "new_holder_display_name": _person_display_name(
                    c, refreshed.get("taken_by_person_id")
                ),
                "before_state": prior_state,
                "after_state": str(after.get("state") or ""),
                "target_state": target_state,
                "work_preserved": True,
                "final_history_id": final_history_id,
                "reopen_event_id": reopen_event_id,
                "original_immutable": bool(final_history_id),
                "reversible_ops_control": True,
                "entity_id": entity,
                "venue_brand_id": brand,
                "actor_role_basis": ",".join(roles) or "assignment",
                "governed_object_id": cid,
                "taken_at": ts,
                "note": json.dumps(
                    {"before": before, "after": after},
                    separators=(",", ":"),
                    ensure_ascii=False,
                )[:3500],
            },
            conn=c,
        )
        if commit:
            c.commit()
        return {
            **refreshed,
            "owner_control": True,
            "owner_action": act,
            "reason": why,
            "prior_holder_person_id": prior_holder,
            "prior_holder_display_name": _person_display_name(c, prior_holder),
            "before": before,
            "after": after,
            "work_preserved": True,
            "final_history_id": final_history_id,
            "reopen_event_id": reopen_event_id,
            "original_immutable": bool(final_history_id),
            "reopen_chain": reopen_chain(cid, conn=c) if reopen_event_id else None,
            "three_close_objects": three_close_objects(refreshed, conn=c),
            "reversible_ops_control": True,
            "money_movement": False,
            "holder": close_holder_info(refreshed, conn=c, viewer_person_id=actor),
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
                "Variance policy needs approval"
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
