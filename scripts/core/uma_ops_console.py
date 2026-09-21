#!/usr/bin/env python3
"""BZG / Uma Blu operations console — PR + petty operational record (Beta).

REQUESTED ≠ APPROVED ≠ ORDERED ≠ RECEIVED ≠ BILL ≠ PAYMENT ≠ PAID_CLAIMED ≠ VERIFIED.
PAID_CLAIMED stores human-paid evidence only. Does not move money.
Petty: movements + day-tin states only. Opening float NOT FOUND unless provided.
No invented authority limit / variance threshold. No second history table.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import authority as _authority
from core.blocker_explain import (
    CLASSIFICATION_LABELS,
    explain_operating_blocker,
)
from core import evidence as _evidence
from core import uma_alchemist_ro as _legacy_alc
from core import venue_close as _venue_close
from core import work_items as _work_items

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
TZ8 = timezone(timedelta(hours=8))

ENTITY_BZG = "ENT-BZG"
VENUE_UMA = "BZG-UMA"
AUDIT_SOURCE = "uma_ops_console"
RESOURCE_TYPE = "bzg_purchase_request"
RESOURCE_PETTY = "bzg_petty_movement"
RESOURCE_PETTY_DAY = "bzg_petty_day"
PAYMENT_PERM = "bzg.pr.payment_approve"

PETTY_DIRECTIONS = frozenset({"OUT", "IN"})
PETTY_DAY_STATES = frozenset(
    {
        "OPEN",
        "COUNTED",
        "VARIANCE_NOTED",
        "CLOSED_CLAIMED",
        "POLICY_REQUIRED",
    }
)
# Day states that need a human Today card (omit when clean).
PETTY_TODAY_ATTENTION = frozenset({"OPEN", "POLICY_REQUIRED", "VARIANCE_NOTED"})

# Attention-first ranks. Lower sorts earlier inside the same attention tier.
TODAY_RANK = {
    "policy_required": 10,
    "opening_balance_required": 20,
    "petty_policy_required": 30,
    "close_exception": 40,
    "close_policy_required": 50,
    "missing_payment_evidence": 60,
    "bill_waiting_payment": 70,
    "legacy_unpaid_ledger": 72,
    "pr_waiting_approval": 80,
    "received_follow_up": 85,
    "ordered_not_received": 90,
    "partial_receive": 88,
    "draft_not_submitted": 84,
    "petty_variance_noted": 100,
    "petty_open_uncounted": 110,
    "petty_attention": 120,
    "close_not_started": 130,
    "close_not_loaded": 140,
    "daily_close": 150,
    "issues": 160,
    "history": 900,
}
BLOCKED_EXPLAIN_KINDS = frozenset(
    {
        "policy_required",
        "opening_balance_required",
        "petty_policy_required",
        "missing_payment_evidence",
        "close_exception",
        "close_policy_required",
        "petty_variance_noted",
    }
)
PR_CARD_EXPLAIN = {
    "prs_waiting_approval": "pr_waiting_approval",
    "draft_pr": "draft_not_submitted",
    "ordered_not_received": "ordered_not_received",
    "awaiting_remainder": "partial_receive",
    "bills_waiting_payment_approval": "bill_waiting_payment",
    "payment_claimed_not_verified": "missing_payment_evidence",
    "policy_required": "policy_required",
}
COMMISSIONING_READY_NAME = "uma-today-commissioning-2026-09-19.json"

STATES = frozenset(
    {
        "DRAFT",
        "REQUESTED",
        "APPROVED",
        "ORDERED",
        "PARTIALLY_RECEIVED",
        "RECEIVED",
        "BILL_RECEIVED",
        "PAYMENT_REQUESTED",
        "PAYMENT_APPROVED",
        "PAID_CLAIMED",
        "PAYMENT_VERIFIED",
        "CLOSED",
        "POLICY_REQUIRED",
        "REJECTED",
        "OPS_CLOSED",
    }
)

# Operational close is not a payment. These destinations stay off the phone pack.
PAYMENT_EXECUTION_STATES = frozenset(
    {
        "PAYMENT_REQUESTED",
        "PAYMENT_APPROVED",
        "PAID_CLAIMED",
        "PAYMENT_VERIFIED",
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"REQUESTED", "REJECTED"}),
    "REQUESTED": frozenset({"APPROVED", "REJECTED"}),
    "APPROVED": frozenset({"ORDERED"}),
    "ORDERED": frozenset({"RECEIVED", "PARTIALLY_RECEIVED"}),
    "PARTIALLY_RECEIVED": frozenset({"RECEIVED", "OPS_CLOSED"}),
    "RECEIVED": frozenset({"BILL_RECEIVED", "OPS_CLOSED"}),
    "BILL_RECEIVED": frozenset({"PAYMENT_REQUESTED"}),
    "PAYMENT_REQUESTED": frozenset({"PAYMENT_APPROVED"}),
    "POLICY_REQUIRED": frozenset({"PAYMENT_APPROVED"}),
    "PAYMENT_APPROVED": frozenset({"PAID_CLAIMED"}),
    "PAID_CLAIMED": frozenset({"PAYMENT_VERIFIED"}),
    "PAYMENT_VERIFIED": frozenset({"CLOSED"}),
    "REJECTED": frozenset(),
    "CLOSED": frozenset(),
    "OPS_CLOSED": frozenset(),
}

HONESTY = {
    "payment_execution": "NOT_BUILT",
    "paid_claim_is_not_verified": True,
    "request_is_not_approval": True,
    "authority_limits_invented": False,
    # Opening float baseline not authorised — never OK with a made-up number.
    "float": "NOT_FOUND",
    "petty_cash_page": "BUILT",
    "stock_perpetual_inventory": "NOT_BUILT",
    "empty_stock_is_not_a_count": True,
    "ops_close_is_not_payment": True,
    "human_commissioning": "NOT_DONE",
    "proven": False,
    "ready": False,
    "cap_bzg_03_rewritten": False,
}


class UmaOpsError(ValueError):
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
        raise UmaOpsError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"uma_ops_console refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"uma_ops_console refuses wolf-system path: {resolved}")
    if str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"uma_ops_console refuses money path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def today_biz_date() -> str:
    return datetime.now(TZ8).date().isoformat()


def mint_pr_id() -> str:
    return f"PR-UMA-{uuid.uuid4().hex[:12].upper()}"


def mint_petty_id() -> str:
    return f"PETTY-UMA-{uuid.uuid4().hex[:10].upper()}"


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def _petty_variance_policy_exists(conn: sqlite3.Connection) -> bool:
    """True only when an authorised petty variance policy row exists. Never invent one."""
    try:
        row = conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='bzg_ops_petty_variance_policies'
            """
        ).fetchone()
        if not row:
            return False
        n = conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_petty_variance_policies WHERE venue=?",
            (VENUE_UMA,),
        ).fetchone()[0]
        return int(n) > 0
    except sqlite3.Error:
        return False


def _public_petty_movement(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    out["example"] = bool(out.get("example"))
    return out


def _public_petty_day(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    out["example"] = bool(out.get("example"))
    # Never present missing float as 0.
    if out.get("opening_float") is None:
        out["opening_float_status"] = "NOT_FOUND"
    else:
        out["opening_float_status"] = "PROVIDED"
    return out


def get_petty_day(
    business_date: str,
    *,
    venue: str = VENUE_UMA,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    biz = (business_date or "").strip()
    if not biz:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        row = _row(
            c.execute(
                """
                SELECT * FROM bzg_ops_petty_days
                WHERE venue=? AND business_date=?
                """,
                (venue, biz),
            ).fetchone()
        )
        return _public_petty_day(row) if row else None
    finally:
        if own:
            c.close()


def list_petty_movements(
    *,
    venue: str = VENUE_UMA,
    business_date: str | None = None,
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 200))
        if business_date:
            rows = c.execute(
                """
                SELECT * FROM bzg_ops_petty_movements
                WHERE venue=? AND business_date=?
                ORDER BY created_at DESC LIMIT ?
                """,
                (venue, business_date.strip(), lim),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM bzg_ops_petty_movements
                WHERE venue=?
                ORDER BY business_date DESC, created_at DESC LIMIT ?
                """,
                (venue, lim),
            ).fetchall()
        return [_public_petty_movement(dict(r)) for r in rows]  # type: ignore[misc]
    finally:
        if own:
            c.close()


def list_petty_days(
    *,
    venue: str = VENUE_UMA,
    limit: int = 40,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 100))
        rows = c.execute(
            """
            SELECT * FROM bzg_ops_petty_days
            WHERE venue=?
            ORDER BY business_date DESC LIMIT ?
            """,
            (venue, lim),
        ).fetchall()
        return [_public_petty_day(dict(r)) for r in rows]  # type: ignore[misc]
    finally:
        if own:
            c.close()


def _ensure_petty_day(
    conn: sqlite3.Connection,
    business_date: str,
    *,
    example: bool = False,
    opening_float: float | None = None,
) -> dict[str, Any]:
    """Create OPEN day row if missing. Never default opening_float to 0."""
    existing = get_petty_day(business_date, conn=conn)
    if existing:
        return existing
    ts = now_utc_iso()
    # Only store float when caller explicitly provided one (not None).
    conn.execute(
        """
        INSERT INTO bzg_ops_petty_days (
          venue, business_date, state, opening_float, counted_amount,
          expected_amount, note, example, created_at, updated_at
        ) VALUES (?, ?, 'OPEN', ?, NULL, NULL, NULL, ?, ?, ?)
        """,
        (
            VENUE_UMA,
            business_date,
            opening_float,
            1 if example else 0,
            ts,
            ts,
        ),
    )
    out = get_petty_day(business_date, conn=conn)
    assert out
    return out


def _compute_expected_from_float_and_movements(
    conn: sqlite3.Connection,
    business_date: str,
    opening_float: float | None,
) -> float | None:
    """Expected tin = float + IN − OUT. Returns None when float unknown — never invent 0."""
    if opening_float is None:
        return None
    rows = conn.execute(
        """
        SELECT direction, amount FROM bzg_ops_petty_movements
        WHERE venue=? AND business_date=?
        """,
        (VENUE_UMA, business_date),
    ).fetchall()
    total = float(opening_float)
    for r in rows:
        amt = float(r["amount"])
        if r["direction"] == "IN":
            total += amt
        else:
            total -= amt
    return total


def insert_petty_movement(
    *,
    business_date: str,
    direction: str,
    amount: float,
    currency: str | None = None,
    purpose: str | None = None,
    example: bool = False,
    work_item_id: str | None = None,
    evidence_id: str | None = None,
    opening_float: float | None = None,
    movement_id: str | None = None,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Insert a movement. Currency blank stays NULL — never guessed."""
    ensure_schema(conn)
    biz = (business_date or "").strip()
    if not biz:
        raise UmaOpsError("business_date required", code="missing_business_date")
    direc = (direction or "").strip().upper()
    if direc not in PETTY_DIRECTIONS:
        raise UmaOpsError(f"invalid direction: {direction!r}", code="invalid_direction")
    try:
        amt = float(amount)
    except (TypeError, ValueError) as exc:
        raise UmaOpsError("amount must be numeric", code="invalid_amount") from exc
    if amt < 0:
        raise UmaOpsError("amount must be non-negative", code="invalid_amount")

    cur = (currency or "").strip() or None
    mid = (movement_id or "").strip() or mint_petty_id()
    ts = now_utc_iso()
    prior_day = get_petty_day(biz, conn=conn)
    day_was_new = prior_day is None
    _ensure_petty_day(
        conn,
        biz,
        example=example,
        opening_float=opening_float,
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_petty_movements (
          movement_id, venue, business_date, direction, amount, currency,
          purpose, example, work_item_id, evidence_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mid,
            VENUE_UMA,
            biz,
            direc,
            amt,
            cur,
            (purpose or "").strip() or None,
            1 if example else 0,
            (work_item_id or "").strip() or None,
            (evidence_id or "").strip() or None,
            ts,
        ),
    )
    day = get_petty_day(biz, conn=conn)
    reopened = bool(day and day.get("state") in ("COUNTED", "CLOSED_CLAIMED"))
    if reopened:
        # New movement re-opens attention until re-counted.
        conn.execute(
            """
            UPDATE bzg_ops_petty_days
            SET state='OPEN', updated_at=?, counted_amount=NULL, expected_amount=NULL
            WHERE venue=? AND business_date=?
            """,
            (ts, VENUE_UMA, biz),
        )
    row = _row(
        conn.execute(
            "SELECT * FROM bzg_ops_petty_movements WHERE movement_id=?",
            (mid,),
        ).fetchone()
    )
    purpose_note = (purpose or "").strip()
    if example:
        purpose_note = f"Example — {purpose_note}" if purpose_note else "Example"
    move_meta: dict[str, Any] = {"status": direc, "amount": amt}
    if purpose_note:
        move_meta["note"] = purpose_note
    if cur:
        move_meta["currency"] = cur
    _audit_ops(
        action="bzg.petty.movement",
        result="SUCCEEDED",
        resource_type=RESOURCE_PETTY,
        resource_id=mid,
        conn=conn,
        metadata=move_meta,
    )
    if day_was_new or reopened:
        day_note = "reopened" if reopened else "opened"
        if example:
            day_note = f"Example — {day_note}"
        _audit_ops(
            action="bzg.petty.day_state",
            result="SUCCEEDED",
            resource_type=RESOURCE_PETTY_DAY,
            resource_id=biz,
            conn=conn,
            metadata={"status": "OPEN", "note": day_note},
        )
    out = _public_petty_movement(row)
    assert out
    return out


def note_petty_count(
    business_date: str,
    counted_amount: float,
    *,
    conn: sqlite3.Connection,
    commit: bool = True,
) -> dict[str, Any]:
    """Record a tin count. Missing float or missing variance policy → POLICY_REQUIRED."""
    biz = (business_date or "").strip()
    if not biz:
        raise UmaOpsError("business_date required", code="missing_business_date")
    try:
        counted = float(counted_amount)
    except (TypeError, ValueError) as exc:
        raise UmaOpsError("counted_amount must be numeric", code="invalid_amount") from exc

    ensure_schema(conn)
    day = get_petty_day(biz, conn=conn) or _ensure_petty_day(conn, biz)
    opening = day.get("opening_float")
    expected = _compute_expected_from_float_and_movements(conn, biz, opening)
    ts = now_utc_iso()

    if opening is None or expected is None:
        # Float unknown — cannot honestly compare. Block without inventing 0.
        state = "POLICY_REQUIRED"
        note = "Opening float NOT FOUND — count cannot be reconciled"
    elif counted == expected:
        state = "COUNTED"
        note = None
    elif _petty_variance_policy_exists(conn):
        state = "VARIANCE_NOTED"
        note = "Count differs from expected — variance noted under policy"
    else:
        # No policy row → blocked honesty, never invent a threshold number.
        state = "POLICY_REQUIRED"
        note = "Count differs from expected — variance policy required (none authorised)"

    conn.execute(
        """
        UPDATE bzg_ops_petty_days
        SET state=?, counted_amount=?, expected_amount=?, note=?, updated_at=?
        WHERE venue=? AND business_date=?
        """,
        (state, counted, expected, note, ts, VENUE_UMA, biz),
    )
    count_note = note or ""
    if day.get("example"):
        count_note = f"Example — {count_note}" if count_note else "Example"
    count_meta: dict[str, Any] = {"status": state}
    if count_note:
        count_meta["note"] = count_note
    _audit_ops(
        action="bzg.petty.count",
        result="SUCCEEDED",
        resource_type=RESOURCE_PETTY_DAY,
        resource_id=biz,
        conn=conn,
        metadata=count_meta,
        reason_code="POLICY_REQUIRED" if state == "POLICY_REQUIRED" else None,
    )
    if commit:
        conn.commit()
    out = get_petty_day(biz, conn=conn)
    assert out
    return out


def _live_legacy(rows: list[dict[str, Any]] | None) -> bool:
    return any(isinstance(r, dict) and r.get("legacy") for r in (rows or []))


def fixture_notice_for(*groups: list[dict[str, Any]] | None) -> bool:
    """False when a live legacy row is present — examples must not dominate."""
    if any(_live_legacy(g) for g in groups):
        return False
    return any(
        isinstance(r, dict) and r.get("example") for g in groups for r in (g or [])
    )


def _provenance_key(row: dict[str, Any]) -> tuple[str, str, str] | None:
    prov = row.get("provenance")
    if isinstance(prov, dict) and prov.get("source_id") is not None:
        return (
            str(prov.get("source") or ""),
            str(prov.get("table") or ""),
            str(prov.get("source_id")),
        )
    return None


def _merge_wolf_legacy(
    wolf: list[dict[str, Any]],
    legacy: list[dict[str, Any]],
    *,
    limit: int,
    id_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Wolf non-example first, then legacy. Drop examples when legacy is live.

    Dedupe by provenance id and by the public id fields (pr_id / pr_num).
    """
    if not legacy:
        return wolf[:limit]
    seen_ids: set[str] = set()
    seen_prov: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []

    def push(row: dict[str, Any]) -> bool:
        ids = [str(row.get(field)) for field in id_fields if row.get(field)]
        prov = _provenance_key(row)
        if prov and prov in seen_prov:
            return False
        if any(i in seen_ids for i in ids):
            return False
        seen_ids.update(ids)
        if prov:
            seen_prov.add(prov)
        out.append(row)
        return len(out) >= limit

    for row in wolf:
        if row.get("example"):
            continue
        if push(row):
            return out
    for row in legacy:
        if push(row):
            return out
    return out


def _safe_legacy_prs(limit: int) -> list[dict[str, Any]]:
    try:
        rows = _legacy_alc.project_prs(limit=limit, attention_only=False)
    except Exception:  # noqa: BLE001 — missing Alchemist must not crash Today
        return []
    return list(rows or [])


def _safe_legacy_petty(limit: int) -> list[dict[str, Any]]:
    try:
        rows = _legacy_alc.project_petty_movements(limit=limit)
    except Exception:  # noqa: BLE001
        return []
    return list(rows or [])


def _safe_legacy_history(limit: int) -> list[dict[str, Any]]:
    try:
        rows = _legacy_alc.project_history_events(limit=limit)
    except Exception:  # noqa: BLE001
        return []
    return list(rows or [])


def _safe_legacy_summary() -> dict[str, Any]:
    try:
        summary = _legacy_alc.project_attention_summary()
    except Exception:  # noqa: BLE001
        return {"source_status": "INACCESSIBLE", "recent_petty": [], "unpaid_ledger_count": 0}
    return summary if isinstance(summary, dict) else {"source_status": "INACCESSIBLE"}


def list_petty(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """GET payload: movements + day summaries + honesty. Float stays NOT_FOUND when absent."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        movements = list_petty_movements(conn=c, limit=200)
        legacy_moves = _safe_legacy_petty(200)
        if legacy_moves:
            movements = _merge_wolf_legacy(
                movements,
                legacy_moves,
                limit=200,
                id_fields=("movement_id",),
            )
        days = list_petty_days(conn=c)
        # Float comes only from a Wolf day row. Legacy amounts never become one.
        any_float = any(d.get("opening_float") is not None for d in days)
        float_status = "PROVIDED" if any_float else "NOT_FOUND"
        honesty = dict(HONESTY)
        # Per-response float stays NOT_FOUND unless a day actually stores one.
        if float_status == "NOT_FOUND":
            honesty["float"] = "NOT_FOUND"
        attention = [
            d
            for d in days
            if d.get("state") in PETTY_TODAY_ATTENTION
            or (
                d.get("state") == "OPEN"
            )
        ]
        return {
            "ok": True,
            "movements": movements,
            "days": days,
            "attention_count": len(attention),
            "float_status": float_status,
            "opening_float": None if float_status == "NOT_FOUND" else "see_days",
            "honesty": honesty,
            "fixture_notice": fixture_notice_for(movements, days),
        }
    finally:
        if own:
            c.close()


def create_petty_movement_test_mode(
    *,
    business_date: str | None = None,
    direction: str = "OUT",
    amount: float = 1.0,
    currency: str | None = None,
    purpose: str | None = None,
    example: bool = True,
    opening_float: float | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Fixture/demo insert — refused unless WOLF_TEST_MODE (or test argv)."""
    if not _under_test_process():
        raise UmaOpsError(
            "petty write only allowed in test mode",
            code="test_mode_required",
            http_status=403,
        )
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_schema(c)
        biz = (business_date or "").strip() or today_biz_date()
        out = insert_petty_movement(
            business_date=biz,
            direction=direction,
            amount=amount,
            currency=currency,
            purpose=purpose or "Example petty movement",
            example=example,
            opening_float=opening_float,
            conn=c,
        )
        if commit:
            c.commit()
        return out
    finally:
        if own:
            c.close()


def seed_fixture_petty(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """At most 3 example movements. Does not invent opening float."""
    ensure_schema(conn)
    fixtures = [
        {
            "movement_id": "PETTY-UMA-EXAMPLE-1",
            "business_date": "2026-09-18",
            "direction": "OUT",
            "amount": 75000.0,
            "currency": "IDR",
            "purpose": "Ice top-up",
        },
        {
            "movement_id": "PETTY-UMA-EXAMPLE-2",
            "business_date": "2026-09-18",
            "direction": "OUT",
            "amount": 42000.0,
            "currency": "IDR",
            "purpose": "Market herbs",
        },
        {
            "movement_id": "PETTY-UMA-EXAMPLE-3",
            "business_date": "2026-09-17",
            "direction": "IN",
            "amount": 100000.0,
            "currency": None,  # blank — never guess
            "purpose": "Owner top-up (currency not recorded)",
        },
    ]
    out = []
    for f in fixtures:
        existing = _row(
            conn.execute(
                "SELECT * FROM bzg_ops_petty_movements WHERE movement_id=?",
                (f["movement_id"],),
            ).fetchone()
        )
        if existing:
            out.append(_public_petty_movement(existing))
            continue
        out.append(
            insert_petty_movement(
                movement_id=f["movement_id"],
                business_date=f["business_date"],
                direction=f["direction"],
                amount=f["amount"],
                currency=f.get("currency"),
                purpose=f.get("purpose"),
                example=True,
                # opening_float omitted → NOT FOUND on day row
                conn=conn,
            )
        )
    return out


def _petty_human_label(m: dict[str, Any]) -> str:
    bits = []
    direc = m.get("direction") or ""
    if direc:
        bits.append(direc)
    if m.get("purpose"):
        bits.append(str(m["purpose"]))
    label = " · ".join(bits) if bits else "Petty movement"
    if m.get("example"):
        label = f"Example — {label}"
    return label


def _petty_attention_for_today(
    *,
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Days needing a human: OPEN / POLICY_REQUIRED / VARIANCE_NOTED (uncounted)."""
    days = list_petty_days(conn=conn, limit=60)
    return [d for d in days if d.get("state") in PETTY_TODAY_ATTENTION]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bzg_ops_purchase_requests (
          pr_id TEXT PRIMARY KEY,
          venue TEXT NOT NULL,
          requester_label TEXT,
          supplier_name TEXT,
          purpose TEXT,
          expected_value REAL,
          currency TEXT,
          requested_date TEXT,
          required_by_date TEXT,
          quote_evidence_id TEXT,
          bill_reference TEXT,
          payment_evidence_id TEXT,
          state TEXT NOT NULL,
          work_item_id TEXT,
          example INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_bzg_ops_pr_state
          ON bzg_ops_purchase_requests(state);
        CREATE INDEX IF NOT EXISTS idx_bzg_ops_pr_venue
          ON bzg_ops_purchase_requests(venue);

        CREATE TABLE IF NOT EXISTS bzg_ops_petty_movements (
          movement_id TEXT PRIMARY KEY,
          venue TEXT NOT NULL,
          business_date TEXT NOT NULL,
          direction TEXT NOT NULL,
          amount REAL NOT NULL,
          currency TEXT,
          purpose TEXT,
          example INTEGER NOT NULL DEFAULT 0,
          work_item_id TEXT,
          evidence_id TEXT,
          created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_bzg_ops_petty_mov_date
          ON bzg_ops_petty_movements(venue, business_date);
        CREATE INDEX IF NOT EXISTS idx_bzg_ops_petty_mov_example
          ON bzg_ops_petty_movements(example);

        CREATE TABLE IF NOT EXISTS bzg_ops_petty_days (
          venue TEXT NOT NULL,
          business_date TEXT NOT NULL,
          state TEXT NOT NULL,
          opening_float REAL,
          counted_amount REAL,
          expected_amount REAL,
          note TEXT,
          example INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (venue, business_date)
        );

        CREATE INDEX IF NOT EXISTS idx_bzg_ops_petty_day_state
          ON bzg_ops_petty_days(state);

        CREATE TABLE IF NOT EXISTS bzg_ops_pr_lines (
          line_id TEXT PRIMARY KEY,
          pr_id TEXT NOT NULL,
          item TEXT NOT NULL,
          qty REAL NOT NULL,
          unit TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_ops_pr_lines_pr
          ON bzg_ops_pr_lines(pr_id);

        CREATE TABLE IF NOT EXISTS bzg_ops_operator_issues (
          issue_id TEXT PRIMARY KEY,
          venue TEXT NOT NULL,
          source_kind TEXT NOT NULL,
          source_id TEXT,
          note TEXT NOT NULL,
          status TEXT NOT NULL,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bzg_ops_pr_close_slots (
          pr_id TEXT PRIMARY KEY,
          evidence_note_id TEXT,
          evidence_photo_id TEXT,
          closed_by TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )


def list_pr_lines(pr_id: str, *, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Wolf order lines. Interpretable only when qty was stored. No invented qty."""
    pid = (pr_id or "").strip()
    if not pid:
        return []
    ensure_schema(conn)
    rows = conn.execute(
        """
        SELECT line_id, item, qty, unit
        FROM bzg_ops_pr_lines
        WHERE pr_id=?
        ORDER BY created_at, line_id
        """,
        (pid,),
    ).fetchall()
    out = []
    for row in rows:
        qty = row["qty"]
        out.append(
            {
                "source_line_id": row["line_id"],
                "item": row["item"],
                "qty": qty,
                "unit": row["unit"],
                "interpretable": qty is not None,
            }
        )
    return out


def _insert_pr_lines(
    conn: sqlite3.Connection,
    pr_id: str,
    lines: list[dict[str, Any]],
    ts: str,
) -> None:
    ensure_schema(conn)
    for raw in lines:
        if not isinstance(raw, dict):
            raise UmaOpsError("line must be an object", code="invalid_line")
        item = str(raw.get("item") or "").strip()
        if not item:
            raise UmaOpsError("line item required", code="invalid_line")
        try:
            qty = float(raw.get("qty"))
        except (TypeError, ValueError) as exc:
            raise UmaOpsError("line qty must be numeric", code="invalid_qty") from exc
        if qty <= 0:
            raise UmaOpsError("line qty must be positive", code="invalid_qty")
        unit = str(raw.get("unit") or "").strip() or None
        conn.execute(
            """
            INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"PRL-{uuid.uuid4().hex[:12].upper()}", pr_id, item, qty, unit, ts),
        )


def assert_not_payment_execution(to_state: str) -> None:
    """Phone pack refuses payment destinations. Does not move money."""
    dest = (to_state or "").strip().upper()
    if dest in PAYMENT_EXECUTION_STATES:
        raise UmaOpsError(
            "Payment execution is not available on this screen.",
            code="payment_execution_refused",
            http_status=403,
        )


def stock_framework(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Read model only. Empty on-hand is not a live perpetual inventory.

    Variance hooks are receipt shortfalls. They are not verified stock counts.
    ESB remains the stock system of record. This function does not write ESB.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bzg_ops_receipt_slots (
              receipt_id TEXT PRIMARY KEY,
              evidence_note_id TEXT,
              evidence_photo_id TEXT,
              variance_flag INTEGER NOT NULL DEFAULT 0,
              shortfall_json TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        rows = c.execute(
            """
            SELECT receipt_id, shortfall_json, created_at
            FROM bzg_ops_receipt_slots
            WHERE variance_flag=1
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()
        hooks = []
        for row in rows:
            shortfall: dict[str, Any] = {}
            raw = row["shortfall_json"]
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        shortfall = parsed
                except json.JSONDecodeError:
                    shortfall = {}
            hooks.append(
                {
                    "receipt_id": row["receipt_id"],
                    "shortfall": shortfall,
                    "verified_stock_count": False,
                    "note": "Receipt shortfall only. Not an on-hand count.",
                }
            )
        return {
            "ok": True,
            "framework": True,
            "live_perpetual_inventory": False,
            "on_hand": None,
            "on_hand_status": "EMPTY",
            "empty_is_not_live_inventory": True,
            "verified_stock_count": False,
            "esb_remains_stock_sot": True,
            "esb_mutated": False,
            "variance_hooks": hooks,
            "honesty": dict(HONESTY),
            "proven": False,
            "ready": False,
        }
    finally:
        if own:
            c.close()


def _require_ops_permission(
    conn: sqlite3.Connection,
    person_id: str,
    code: str,
) -> None:
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        raise UmaOpsError("verified_person_id required", code="missing_verified_person", http_status=403)
    target = {"entity_id": ENTITY_BZG, "brand_id": VENUE_UMA}
    if not _rbac.can(pid, code, target, conn=conn):
        raise UmaOpsError(
            f"permission denied: {code}",
            code="forbidden",
            http_status=403,
        )


def record_petty_ops(
    *,
    person_id: str,
    business_date: str | None = None,
    direction: str = "OUT",
    amount: float,
    currency: str | None = None,
    purpose: str | None = None,
    evidence_note_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record a tin movement for an operator who can create work. No bank write."""
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_schema(c)
        _require_ops_permission(c, person_id, "work.create")
        note = (purpose or "").strip()
        if not note:
            raise UmaOpsError("purpose required", code="missing_purpose")
        biz = (business_date or "").strip() or today_biz_date()
        out = insert_petty_movement(
            business_date=biz,
            direction=direction,
            amount=amount,
            currency=currency,
            purpose=note,
            example=False,
            evidence_id=(evidence_note_id or "").strip() or None,
            conn=c,
        )
        _audit_ops(
            action="bzg.petty.movement",
            result="SUCCEEDED",
            resource_type=RESOURCE_PETTY,
            resource_id=str(out.get("movement_id") or biz),
            conn=c,
            metadata={"status": direction, "note": note, "actor": "operator"},
            actor_type="PERSON",
            verified_person_id=person_id,
            identity=identity,
        )
        if commit:
            c.commit()
        return out
    finally:
        if own:
            c.close()


def count_petty_ops(
    *,
    person_id: str,
    business_date: str,
    counted_amount: float,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Count the tin. Missing float stays POLICY_REQUIRED. No invented opening."""
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        _require_ops_permission(c, person_id, "work.update")
        out = note_petty_count(
            business_date,
            counted_amount,
            conn=c,
            commit=False,
        )
        _audit_ops(
            action="bzg.petty.count",
            result="SUCCEEDED",
            resource_type=RESOURCE_PETTY_DAY,
            resource_id=(business_date or "").strip(),
            conn=c,
            metadata={"status": out.get("state"), "note": "operator count"},
            actor_type="PERSON",
            verified_person_id=person_id,
            identity=identity,
        )
        if commit:
            c.commit()
        return out
    finally:
        if own:
            c.close()


def create_operator_issue(
    *,
    person_id: str,
    source_kind: str,
    note: str,
    source_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Open an ops issue from an exception. Does not resolve a completion row."""
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_schema(c)
        _require_ops_permission(c, person_id, "work.create")
        kind = (source_kind or "").strip() or "issues_open"
        text = (note or "").strip()
        if not text:
            raise UmaOpsError("note required", code="missing_note")
        ts = now_utc_iso()
        issue_id = f"ISS-UMA-{uuid.uuid4().hex[:10].upper()}"
        c.execute(
            """
            INSERT INTO bzg_ops_operator_issues (
              issue_id, venue, source_kind, source_id, note, status, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?)
            """,
            (
                issue_id,
                VENUE_UMA,
                kind,
                (source_id or "").strip() or None,
                text,
                person_id.strip(),
                ts,
            ),
        )
        _audit_ops(
            action="bzg.issue.opened",
            result="SUCCEEDED",
            resource_type="bzg_ops_issue",
            resource_id=issue_id,
            conn=c,
            metadata={"status": "OPEN", "note": text, "kind": kind, "cr_resolved": False},
            actor_type="PERSON",
            verified_person_id=person_id,
            identity=identity,
        )
        if commit:
            c.commit()
        return {
            "issue_id": issue_id,
            "kind": kind,
            "note": text,
            "status": "OPEN",
            "cr_resolved": False,
            "payment_execution": False,
        }
    finally:
        if own:
            c.close()


def save_pr_close_slot(
    conn: sqlite3.Connection,
    *,
    pr_id: str,
    evidence_note_id: str | None,
    evidence_photo_id: str | None,
    closed_by: str,
) -> None:
    ensure_schema(conn)
    note = (evidence_note_id or "").strip() or None
    photo = (evidence_photo_id or "").strip() or None
    if not note and not photo:
        raise UmaOpsError(
            "A note id or photo id is required to close this request.",
            code="missing_evidence",
        )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_close_slots (
          pr_id, evidence_note_id, evidence_photo_id, closed_by, created_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(pr_id) DO UPDATE SET
          evidence_note_id=excluded.evidence_note_id,
          evidence_photo_id=excluded.evidence_photo_id,
          closed_by=excluded.closed_by,
          created_at=excluded.created_at
        """,
        (pr_id, note, photo, closed_by, now_utc_iso()),
    )


def get_pr(pr_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    pid = (pr_id or "").strip()
    if not pid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        row = _row(
            c.execute(
                "SELECT * FROM bzg_ops_purchase_requests WHERE pr_id=?",
                (pid,),
            ).fetchone()
        )
        return _public(row) if row else None
    finally:
        if own:
            c.close()


def list_prs(
    *,
    venue: str = VENUE_UMA,
    state: str | None = None,
    limit: int = 200,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Wolf non-example first, then Alchemist projection. No canonical insert."""
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 200))
        wolf = _wolf_prs(c, venue=venue, state=state, limit=lim)
        legacy = _safe_legacy_prs(lim)
        if state:
            want = state.strip().upper()
            legacy = [r for r in legacy if (r.get("state") or "").upper() == want]
        if not legacy:
            return wolf
        return _merge_wolf_legacy(
            wolf, legacy, limit=lim, id_fields=("pr_id", "pr_num")
        )
    finally:
        if own:
            c.close()


def _wolf_prs(
    conn: sqlite3.Connection,
    *,
    venue: str,
    state: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if state:
        rows = conn.execute(
            """
            SELECT * FROM bzg_ops_purchase_requests
            WHERE venue=? AND state=?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (venue, state.strip().upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM bzg_ops_purchase_requests
            WHERE venue=?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (venue, limit),
        ).fetchall()
    return [_public(dict(r)) for r in rows]


def _public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    out["example"] = bool(out.get("example"))
    out["honesty"] = dict(HONESTY)
    return out


def create_pr(
    *,
    requester_label: str | None = None,
    supplier_name: str | None = None,
    purpose: str | None = None,
    expected_value: float | None = None,
    currency: str | None = None,
    requested_date: str | None = None,
    required_by_date: str | None = None,
    quote_evidence_id: str | None = None,
    bill_reference: str | None = None,
    lines: list[dict[str, Any]] | None = None,
    submitted: bool = True,
    example: bool = False,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create PR in REQUESTED. Does not approve."""
    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        ensure_schema(c)
        ts = now_utc_iso()
        pr_id = mint_pr_id()
        initial = "REQUESTED" if submitted else "DRAFT"
        cur = (currency or "").strip() or None
        val = expected_value
        if val is not None:
            val = float(val)

        wi = _work_items.create_work_item(
            title=(purpose or "Uma Blu purchase request").strip()[:200] or "Uma Blu purchase request",
            owning_entity_id=ENTITY_BZG,
            work_type="APPROVAL_REQUIRED",
            source_type="SYSTEM" if actor_type.upper() == "SYSTEM" else "HUMAN",
            created_by_actor_type=actor_type.upper(),
            verified_person_id=verified_person_id,
            description=f"PR {pr_id}",
            source_id=pr_id,
            identity=identity,
            conn=c,
            commit=False,
        )

        c.execute(
            """
            INSERT INTO bzg_ops_purchase_requests (
              pr_id, venue, requester_label, supplier_name, purpose,
              expected_value, currency, requested_date, required_by_date,
              quote_evidence_id, bill_reference, payment_evidence_id,
              state, work_item_id, example, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (
                pr_id,
                VENUE_UMA,
                (requester_label or "").strip() or None,
                (supplier_name or "").strip() or None,
                (purpose or "").strip() or None,
                val,
                cur,
                (requested_date or "").strip() or None,
                (required_by_date or "").strip() or None,
                (quote_evidence_id or "").strip() or None,
                (bill_reference or "").strip() or None,
                initial,
                wi["work_item_id"],
                1 if example else 0,
                ts,
                ts,
            ),
        )
        _insert_pr_lines(c, pr_id, lines or [], ts)
        _audit_pr(
            action="bzg.pr.requested" if submitted else "bzg.pr.draft",
            result="SUCCEEDED",
            pr_id=pr_id,
            state=initial,
            verified_person_id=verified_person_id,
            actor_type=actor_type,
            identity=identity,
            conn=c,
            metadata={"status": initial, "note": "request_is_not_approval"},
        )
        if commit:
            c.commit()
        out = get_pr(pr_id, conn=c)
        assert out
        return out
    finally:
        if own:
            c.close()


def insert_pr_row(
    *,
    pr_id: str,
    state: str,
    requester_label: str | None = None,
    supplier_name: str | None = None,
    purpose: str | None = None,
    expected_value: float | None = None,
    currency: str | None = None,
    requested_date: str | None = None,
    required_by_date: str | None = None,
    quote_evidence_id: str | None = None,
    bill_reference: str | None = None,
    payment_evidence_id: str | None = None,
    work_item_id: str | None = None,
    example: bool = True,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Direct insert for fixtures / migration. No approval side effects."""
    st = state.strip().upper()
    if st not in STATES:
        raise UmaOpsError(f"invalid state: {state!r}", code="invalid_state")
    ensure_schema(conn)
    ts = now_utc_iso()
    conn.execute(
        """
        INSERT OR REPLACE INTO bzg_ops_purchase_requests (
          pr_id, venue, requester_label, supplier_name, purpose,
          expected_value, currency, requested_date, required_by_date,
          quote_evidence_id, bill_reference, payment_evidence_id,
          state, work_item_id, example, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pr_id,
            VENUE_UMA,
            requester_label,
            supplier_name,
            purpose,
            expected_value,
            (currency or "").strip() or None,
            requested_date,
            required_by_date,
            quote_evidence_id,
            bill_reference,
            payment_evidence_id,
            st,
            work_item_id,
            1 if example else 0,
            ts,
            ts,
        ),
    )
    out = get_pr(pr_id, conn=conn)
    assert out
    return out


def transition_pr(
    pr_id: str,
    to_state: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "PERSON",
    payment_evidence_id: str | None = None,
    bill_reference: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Advance PR. PAYMENT_APPROVED checks authority; missing limit → POLICY_REQUIRED."""
    pid = (pr_id or "").strip()
    dest = (to_state or "").strip().upper()
    if dest not in STATES:
        raise UmaOpsError(f"invalid state: {to_state!r}", code="invalid_state")
    at = (actor_type or "").strip().upper()
    if at not in ("PERSON", "SYSTEM"):
        raise UmaOpsError(f"invalid actor_type: {actor_type!r}")
    verified = (verified_person_id or "").strip() or None
    if at == "PERSON" and not verified:
        raise UmaOpsError("verified_person_id required", code="missing_verified_person")

    own = conn is None
    c = conn or db_connect()
    try:
        assert_catalog_writable(Path(CATALOG_DB))
        row = get_pr(pid, conn=c)
        if not row:
            raise UmaOpsError("PR not found", code="not_found", http_status=404)
        cur = row["state"]
        if dest not in ALLOWED_TRANSITIONS.get(cur, frozenset()):
            raise UmaOpsError(
                f"illegal transition {cur} → {dest}",
                code="illegal_transition",
            )

        final_state = dest
        auth_meta: dict[str, Any] = {}

        if dest == "PAYMENT_APPROVED":
            amt = row.get("expected_value")
            cur_code = row.get("currency")
            amount_context: dict[str, Any] = {}
            if amt is not None:
                amount_context["amount"] = amt
            if cur_code:
                amount_context["currency"] = cur_code
            person_for_auth = verified or ""
            ev = _authority.within_authority(
                person_for_auth,
                PAYMENT_PERM,
                {"entity_id": ENTITY_BZG, "brand_id": VENUE_UMA},
                amount_context,
                conn=c,
            )
            auth_meta = {
                "reason": ev.get("reason"),
                "allowed": bool(ev.get("allowed")),
                "detail": ev.get("detail"),
            }
            if not ev.get("allowed"):
                # No covering limit (or above threshold) → policy, not approved.
                final_state = "POLICY_REQUIRED"

        if dest == "PAID_CLAIMED":
            evid = (payment_evidence_id or row.get("payment_evidence_id") or "").strip()
            if not evid:
                raise UmaOpsError(
                    "payment_evidence_id required for paid claim",
                    code="missing_payment_evidence",
                )
            payment_evidence_id = evid
            # Claim stores evidence only — never sets PAYMENT_VERIFIED.

        if dest == "PAYMENT_VERIFIED":
            evid = (row.get("payment_evidence_id") or "").strip()
            if not evid:
                raise UmaOpsError(
                    "payment evidence missing; cannot verify",
                    code="missing_payment_evidence",
                )
            evd = _evidence.get_evidence(evid, conn=c)
            if not evd or evd.get("verification_status") != "VERIFIED":
                raise UmaOpsError(
                    "payment evidence is not verified",
                    code="evidence_not_verified",
                )

        ts = now_utc_iso()
        sets = ["state=?", "updated_at=?"]
        params: list[Any] = [final_state, ts]
        if bill_reference is not None:
            sets.append("bill_reference=?")
            params.append((bill_reference or "").strip() or None)
        if payment_evidence_id is not None:
            sets.append("payment_evidence_id=?")
            params.append((payment_evidence_id or "").strip() or None)
        params.append(pid)
        c.execute(
            f"UPDATE bzg_ops_purchase_requests SET {', '.join(sets)} WHERE pr_id=?",
            params,
        )

        action = f"bzg.pr.{final_state.lower()}"
        result = "SUCCEEDED" if final_state == dest else "DENIED"
        meta: dict[str, Any] = {
            "status": final_state,
            "note": f"from={cur}",
        }
        if row.get("expected_value") is not None:
            meta["amount"] = row["expected_value"]
        if row.get("currency"):
            meta["currency"] = row["currency"]
        if auth_meta:
            meta["reason"] = str(auth_meta.get("reason") or "")
        _audit_pr(
            action=action,
            result=result,
            pr_id=pid,
            state=final_state,
            verified_person_id=verified,
            actor_type=at,
            identity=identity,
            conn=c,
            metadata=meta,
            reason_code="POLICY_REQUIRED" if final_state == "POLICY_REQUIRED" else None,
        )
        if commit:
            c.commit()
        out = get_pr(pid, conn=c)
        assert out
        if final_state == "POLICY_REQUIRED" and dest == "PAYMENT_APPROVED":
            out = {**out, "transition_denied": True, "authority": auth_meta}
        return out
    finally:
        if own:
            c.close()


def _audit_ops(
    *,
    action: str,
    result: str,
    resource_type: str,
    resource_id: str,
    conn: sqlite3.Connection,
    metadata: dict[str, Any] | None = None,
    reason_code: str | None = None,
    actor_type: str = "SYSTEM",
    verified_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
) -> None:
    """Append one uma_ops_console audit row. Same spine as PR transitions. No second store."""
    at = (actor_type or "SYSTEM").strip().upper()
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": AUDIT_SOURCE,
        "actor_type": at,
        "entity_id": ENTITY_BZG,
        "brand_id": VENUE_UMA,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "reason_code": reason_code,
        "metadata": metadata or {},
        "conn": conn,
        "commit": False,
    }
    if at == "PERSON":
        kwargs["verified_person_id"] = verified_person_id
        kwargs["actor_person_id"] = verified_person_id
        if identity:
            kwargs["actor_auth_identity_id"] = identity.get("auth_identity_id")
            kwargs["identity_assurance"] = identity.get("assurance")
    _audit.record_event(**kwargs)


def _audit_pr(
    *,
    action: str,
    result: str,
    pr_id: str,
    state: str,
    verified_person_id: str | None,
    actor_type: str,
    identity: dict[str, Any] | None,
    conn: sqlite3.Connection,
    metadata: dict[str, Any] | None = None,
    reason_code: str | None = None,
) -> None:
    _audit_ops(
        action=action,
        result=result,
        resource_type=RESOURCE_TYPE,
        resource_id=pr_id,
        conn=conn,
        metadata=metadata or {"status": state},
        reason_code=reason_code,
        actor_type=actor_type,
        verified_person_id=verified_person_id,
        identity=identity,
    )


def _item_counts(items: list[dict[str, Any]]) -> tuple[int, int]:
    attention = sum(1 for i in items if not i.get("example"))
    example = sum(1 for i in items if i.get("example"))
    return attention, example


def _apply_explain(
    card: dict[str, Any],
    explain_kind: str | None,
    *,
    label: str,
    float_status: str | None = None,
) -> None:
    """Attach why + classification from the blocker helper. No invented numbers."""
    if not explain_kind:
        return
    explained = explain_operating_blocker(
        explain_kind,
        {"label": label, "opening_float_status": float_status},
    )
    card["explain_kind"] = explain_kind
    card["why"] = explained.get("why") or ""
    card["classification"] = explained.get("classification") or ""
    human = CLASSIFICATION_LABELS.get(card["classification"])
    if human:
        card["classification_label"] = human
    card["explain"] = {
        k: v for k, v in explained.items() if v not in (None, "", [], {})
    }


def _safe_close_for_today(
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read today's close state only. No closer name. No variance threshold."""
    try:
        biz = today_biz_date()
        row = _venue_close.get_close(business_date=biz, conn=conn)
        if not row:
            return {
                "status": "not_started",
                "label": "Daily close not started",
                "business_date": biz,
                "attention": True,
                "blocked": False,
                "explain_kind": "close_not_started",
            }
        st = row.get("state") or ""
        base = {"business_date": biz, "state": st}
        if st == "VERIFIED_CLOSED":
            return {
                **base,
                "status": "verified",
                "label": "Daily close verified",
                "attention": False,
                "blocked": False,
                "explain_kind": None,
            }
        if st == "EXCEPTION":
            return {
                **base,
                "status": "exception",
                "label": "Daily close exception open",
                "attention": True,
                "blocked": True,
                "explain_kind": "close_exception",
            }
        if st == "VARIANCE_REQUIRES_POLICY":
            return {
                **base,
                "status": "blocked",
                "label": "Daily close blocked — policy needed",
                "attention": True,
                "blocked": True,
                "explain_kind": "close_policy_required",
            }
        if st == "CANCELLED":
            return {
                **base,
                "status": "cancelled",
                "label": "Daily close cancelled",
                "attention": False,
                "blocked": False,
                "explain_kind": None,
            }
        progress_labels = {
            "OPEN": "Daily close open",
            "DATA_CAPTURED": "Daily close data captured",
            "EVIDENCE_SUBMITTED": "Daily close evidence submitted",
            "RECONCILED": "Daily close reconciled",
            "RESOLVED": "Daily close resolved",
        }
        return {
            **base,
            "status": "in_progress",
            "label": progress_labels.get(st, "Daily close in progress"),
            "attention": False,
            "blocked": False,
            "explain_kind": None,
        }
    except Exception:  # noqa: BLE001
        return {
            "status": "not_loaded",
            "label": "Close not loaded",
            "attention": True,
            "blocked": False,
            "explain_kind": "close_not_loaded",
        }


def _petty_today_card(days: list[dict[str, Any]]) -> dict[str, Any] | None:
    """One petty card. Float missing stays OPENING BALANCE REQUIRED, not a number."""
    if not days:
        return None
    items: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_key = 10**9
    for d in days:
        issue = _petty_day_issue(d)
        item = {
            "label": issue["label"],
            "example": bool(issue.get("example")),
            "business_date": issue.get("business_date"),
            "state": d.get("state") or "OPEN",
            "kind": issue.get("kind"),
        }
        items.append(item)
        rank = TODAY_RANK.get(str(issue.get("kind") or ""), 120)
        live_penalty = 0 if not item["example"] else 1000
        key = live_penalty + rank
        if key < best_key:
            best_key = key
            best = issue
    explain_kind = str((best or {}).get("kind") or "petty_attention")
    attention_count, example_count = _item_counts(items)
    title = "Petty cash needs attention"
    if explain_kind == "opening_balance_required":
        title = "OPENING BALANCE REQUIRED"
    elif explain_kind == "petty_policy_required":
        title = "Petty count needs a variance policy"
    elif explain_kind in ("petty_open_uncounted", "petty_variance_noted"):
        title = "Petty cash count gap"
    blocked = explain_kind in BLOCKED_EXPLAIN_KINDS
    card: dict[str, Any] = {
        "kind": "petty_cash",
        "title": title,
        "count": len(items),
        "attention_count": attention_count,
        "example_count": example_count,
        "href": "/bzg/uma-blu/petty",
        "items": items,
        "attention": attention_count > 0,
        "blocked": blocked,
        "rank": TODAY_RANK.get(explain_kind, 120),
        "example": attention_count == 0 and example_count > 0,
    }
    if card["attention"] or blocked:
        _apply_explain(
            card,
            explain_kind,
            label=title,
            float_status="NOT_FOUND" if explain_kind == "opening_balance_required" else None,
        )
    return card


def _issues_today_card(issues: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        {
            "label": i.get("label") or "Issue",
            "example": bool(i.get("example")),
            "kind": i.get("kind"),
        }
        for i in issues
    ]
    attention_count, example_count = _item_counts(items)
    live = [i for i in issues if isinstance(i, dict) and not i.get("example")]
    card: dict[str, Any] = {
        "kind": "issues",
        "title": "Issues",
        "count": len(items),
        "attention_count": attention_count,
        "example_count": example_count,
        "href": "/bzg/uma-blu/issues",
        "items": items,
        "attention": attention_count > 0,
        "blocked": attention_count > 0,
        "rank": TODAY_RANK["issues"],
        "example": attention_count == 0 and example_count > 0,
    }
    if live:
        lead = live[0]
        card["why"] = lead.get("why") or ""
        card["classification"] = lead.get("classification") or ""
        human = CLASSIFICATION_LABELS.get(card["classification"])
        if human:
            card["classification_label"] = human
        if lead.get("explain"):
            card["explain"] = lead["explain"]
        card["explain_kind"] = lead.get("kind")
    return card


def _legacy_opening_card(history_note: str) -> dict[str, Any]:
    """Opening-balance blocker when only legacy movements exist. No invented float."""
    card: dict[str, Any] = {
        "kind": "petty_cash",
        "title": "OPENING BALANCE REQUIRED",
        "count": 1,
        "attention_count": 1,
        "example_count": 0,
        "href": "/bzg/uma-blu/petty",
        "items": [
            {
                "label": (
                    "Existing tin movements are listed on Petty. "
                    "They do not set an opening balance."
                ),
                "example": False,
                "legacy": True,
                "record_origin": "alchemist",
            }
        ],
        "attention": True,
        "blocked": True,
        "rank": TODAY_RANK["opening_balance_required"],
        "example": False,
        "legacy": True,
        "record_origin": "alchemist",
    }
    _apply_explain(
        card,
        "opening_balance_required",
        label="OPENING BALANCE REQUIRED",
        float_status="NOT_FOUND",
    )
    card["why"] = ((card.get("why") or "") + history_note).strip()
    return card


def _legacy_unpaid_card(summary: dict[str, Any]) -> dict[str, Any]:
    n = int(summary.get("unpaid_ledger_count") or 0)
    recorded = summary.get("unpaid_ledger_sum")
    why = (
        f"{n} bills are still recorded unpaid in the existing ledger. "
        "This is not a verified Wolf payment."
    )
    if recorded is not None:
        why = (
            f"{n} bills are still recorded unpaid in the existing ledger "
            f"(recorded sum {recorded}). This is not a verified Wolf payment "
            "and it is not an opening balance."
        )
    prov = {"source": "alchemist", "table": "ledger", "source_id": "unpaid-summary"}
    return {
        "kind": "legacy_unpaid_ledger",
        "title": "Unpaid bills in the existing record",
        "count": n,
        "attention_count": n,
        "example_count": 0,
        "href": "/bzg/uma-blu/bills",
        "items": [
            {
                "label": why,
                "example": False,
                "legacy": True,
                "record_origin": "alchemist",
                "provenance": prov,
            }
        ],
        "attention": True,
        "blocked": False,
        "rank": TODAY_RANK["legacy_unpaid_ledger"],
        "example": False,
        "legacy": True,
        "record_origin": "alchemist",
        "why": why,
        "classification": "NEEDS_STAFF",
        "classification_label": CLASSIFICATION_LABELS.get("NEEDS_STAFF"),
        "provenance": prov,
    }


def _history_teaser(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        hist = list_history(limit=3, conn=conn)
        lines = hist.get("events") or []
    except Exception:  # noqa: BLE001
        lines = []
    teaser = [
        {
            "when": ln.get("when"),
            "sentence": ln.get("sentence"),
            "legacy": bool(ln.get("legacy")),
            "pr_num": ln.get("pr_num"),
        }
        for ln in lines[:3]
        if isinstance(ln, dict)
    ]
    return {
        "kind": "history",
        "title": "Recent history",
        "count": len(teaser),
        "attention_count": 0,
        "example_count": 0,
        "href": "/bzg/uma-blu#history",
        "items": [],
        "teaser": teaser,
        "attention": False,
        "blocked": False,
        "rank": TODAY_RANK["history"],
        "example": False,
    }


def today_cards(
    *,
    conn: sqlite3.Connection | None = None,
    person_id: str | None = None,
) -> dict[str, Any]:
    """Attention-first Today cards. example:true never counts as live attention.

    Quiet PR/petty cards stay omitted. Daily Close, Issues count, and a History
    teaser always surface. Why comes from the blocker helper. No invented float
    or closer.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        prs = list_prs(conn=c)
        cards: list[dict[str, Any]] = []

        def add_card(
            kind: str,
            title: str,
            items: list[dict[str, Any]],
            *,
            href: str,
        ) -> None:
            if not items:
                return
            public = [
                {
                    "label": _pr_human_label(p),
                    "example": bool(p.get("example")),
                    "pr_id": p.get("pr_id"),  # click-through only; UI shows pr_num
                    "legacy": bool(p.get("legacy")),
                    "pr_num": p.get("pr_num"),
                    "record_origin": p.get("record_origin"),
                    "provenance": p.get("provenance"),
                    "display_status": p.get("display_status"),
                }
                for p in items
            ]
            attention_count, example_count = _item_counts(public)
            explain_kind = PR_CARD_EXPLAIN.get(kind, kind)
            blocked = explain_kind in BLOCKED_EXPLAIN_KINDS
            card: dict[str, Any] = {
                "kind": kind,
                "title": title,
                "count": len(public),
                "attention_count": attention_count,
                "example_count": example_count,
                "href": href,
                "items": public,
                "attention": attention_count > 0,
                "blocked": blocked,
                "rank": TODAY_RANK.get(explain_kind, 200),
                "example": attention_count == 0 and example_count > 0,
            }
            if card["attention"] or blocked:
                _apply_explain(card, explain_kind, label=title)
            cards.append(card)

        add_card(
            "draft_pr",
            "Purchase requests not submitted",
            [p for p in prs if p["state"] == "DRAFT"],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "prs_waiting_approval",
            "PRs waiting approval",
            [p for p in prs if p["state"] == "REQUESTED"],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "ordered_not_received",
            "Ordered, not received",
            [p for p in prs if p["state"] == "ORDERED"],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "awaiting_remainder",
            "Part received, rest still out",
            [p for p in prs if p["state"] == "PARTIALLY_RECEIVED"],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "bills_waiting_payment_approval",
            "Bills waiting payment approval",
            [p for p in prs if p["state"] in ("BILL_RECEIVED", "PAYMENT_REQUESTED")],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "payment_claimed_not_verified",
            "Payment claimed, not verified",
            [p for p in prs if p["state"] == "PAID_CLAIMED"],
            href="/bzg/uma-blu/bills",
        )
        add_card(
            "policy_required",
            "Policy required",
            [p for p in prs if p["state"] == "POLICY_REQUIRED"],
            href="/bzg/uma-blu/issues",
        )
        received = [
            p
            for p in prs
            if p.get("legacy") and p.get("needs_attention") and p.get("state") == "RECEIVED"
        ]
        add_card(
            "received_follow_up",
            "Received, needs follow-up",
            received,
            href="/bzg/uma-blu/bills",
        )
        if cards and cards[-1].get("kind") == "received_follow_up":
            cards[-1]["why"] = (
                "Goods were marked received in the existing Uma record and still "
                "need a follow-up. This is not a Wolf payment check."
            )
            cards[-1]["classification"] = "NEEDS_STAFF"
            cards[-1]["classification_label"] = CLASSIFICATION_LABELS.get("NEEDS_STAFF")
            cards[-1]["legacy"] = True
            cards[-1]["record_origin"] = "alchemist"

        close_info = _safe_close_for_today(conn=c)
        explain_kind = close_info.get("explain_kind")
        attention = bool(close_info.get("attention"))
        blocked = bool(close_info.get("blocked"))
        close_pub = {
            k: close_info[k]
            for k in ("status", "business_date", "state")
            if close_info.get(k) not in (None, "")
        }
        close_card: dict[str, Any] = {
            "kind": "daily_close",
            "title": close_info.get("label") or "Daily close",
            "count": 1,
            "attention_count": 1 if attention else 0,
            "example_count": 0,
            "href": "/uma-blu-close",
            "example": False,
            "items": [],
            "attention": attention,
            "blocked": blocked,
            "rank": TODAY_RANK.get(explain_kind or "daily_close", TODAY_RANK["daily_close"]),
            "close": close_pub,
        }
        if attention or blocked:
            _apply_explain(close_card, explain_kind, label=close_card["title"])
        cards.append(close_card)

        petty_days = _petty_attention_for_today(conn=c)
        petty_card = _petty_today_card(petty_days)
        if petty_card:
            cards.append(petty_card)

        try:
            issues_payload = list_issues(conn=c)
            issue_rows = issues_payload.get("issues") or []
        except Exception:  # noqa: BLE001
            issue_rows = []
        cards.append(_issues_today_card(issue_rows))
        cards.append(_history_teaser(c))

        legacy_moves = _safe_legacy_petty(5)
        legacy_summary = _safe_legacy_summary()
        history_note = (
            " Past tin movements still show on Petty. They do not set an opening balance."
        )
        if legacy_moves:
            petty_live = next((card for card in cards if card.get("kind") == "petty_cash"), None)
            if petty_live:
                why = str(petty_live.get("why") or "")
                if "do not set an opening balance" not in why:
                    petty_live["why"] = (why + history_note).strip()
                petty_live["legacy"] = True
            else:
                cards.append(_legacy_opening_card(history_note))
        unpaid_n = int(legacy_summary.get("unpaid_ledger_count") or 0)
        if unpaid_n > 0:
            cards.append(_legacy_unpaid_card(legacy_summary))

        cards.sort(
            key=lambda card: (
                0 if card.get("attention") else 1,
                int(card.get("rank") or 500),
                str(card.get("kind") or ""),
            )
        )
        lead = next((card for card in cards if card.get("attention")), None)
        now = None
        if lead:
            now = {
                "title": lead.get("title"),
                "why": lead.get("why") or "",
                "classification": lead.get("classification") or "",
                "classification_label": lead.get("classification_label") or "",
                "href": lead.get("href"),
                "kind": lead.get("kind"),
            }
        all_days = list_petty_days(conn=c)
        float_status = (
            "PROVIDED"
            if any(d.get("opening_float") is not None for d in all_days)
            else "NOT_FOUND"
        )
        honesty = dict(HONESTY)
        honesty["float"] = "NOT_FOUND" if float_status == "NOT_FOUND" else "PROVIDED"
        try:
            stock = stock_framework(conn=c)
        except Exception:  # noqa: BLE001
            stock = {
                "ok": False,
                "on_hand": None,
                "on_hand_status": "EMPTY",
                "empty_is_not_live_inventory": True,
                "live_perpetual_inventory": False,
                "verified_stock_count": False,
            }
        payload = {
            "ok": True,
            "cards": cards,
            "now": now,
            "order": [card.get("kind") for card in cards],
            "honesty": honesty,
            "float_status": float_status,
            "opening_float": None if float_status == "NOT_FOUND" else "see_days",
            "fixture_notice": fixture_notice_for(prs, petty_days, issue_rows, legacy_moves),
            "legacy_projection": legacy_summary,
            "stock": stock,
            "payment_execution": False,
            "human_commissioning": "NOT_DONE",
        }
        if (person_id or "").strip():
            from core import uma_devi_p0 as _p0

            try:
                payload["previous_closes"] = _p0.previous_closes(
                    exclude_business_date=today_biz_date(),
                    limit=8,
                    conn=c,
                )
            except Exception:  # noqa: BLE001
                payload["previous_closes"] = {
                    "ok": False,
                    "closes": [],
                    "empty": True,
                    "empty_message": "Earlier closes could not be loaded. No figures were invented.",
                }
            payload["permissions"] = _p0.operator_view(person_id.strip(), conn=c)
            payload = _p0.annotate_today(payload, person_id=person_id.strip(), conn=c)
        else:
            payload["previous_closes"] = {
                "ok": True,
                "closes": [],
                "empty": True,
                "empty_message": "Sign in to see earlier closes.",
            }
        return payload
    finally:
        if own:
            c.close()


def _pr_human_label(p: dict[str, Any]) -> str:
    bits = []
    if p.get("legacy") and p.get("pr_num"):
        bits.append(str(p["pr_num"]))
    if p.get("supplier_name"):
        bits.append(str(p["supplier_name"]))
    if p.get("purpose"):
        bits.append(str(p["purpose"]))
    label = " · ".join(bits) if bits else "Purchase request"
    if p.get("example"):
        label = f"Example — {label}"
    return label


def _petty_day_issue(d: dict[str, Any]) -> dict[str, Any]:
    """Same attention states as Today. Omit COUNTED / CLOSED_CLAIMED (quiet when clean)."""
    st = d.get("state") or "OPEN"
    label = f"Petty tin · {d.get('business_date') or 'date unknown'} · {st}"
    if d.get("example"):
        label = f"Example — {label}"
    float_missing = d.get("opening_float") is None or d.get("opening_float_status") == "NOT_FOUND"
    if float_missing:
        label = f"{label} (float NOT FOUND)"
        kind = "opening_balance_required"
    else:
        kind = {
            "POLICY_REQUIRED": "petty_policy_required",
            "OPEN": "petty_open_uncounted",
            "VARIANCE_NOTED": "petty_variance_noted",
        }.get(st, "petty_attention")
    return {
        "kind": kind,
        "label": label,
        "example": bool(d.get("example")),
        "business_date": d.get("business_date"),
        "href": "/bzg/uma-blu/petty",
    }


def _annotate_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Attach deterministic why / classification / explain. No raw-id headline."""
    row = dict(issue)
    label = str(row.get("label") or "")
    kind = str(row.get("kind") or "")
    float_status = row.get("opening_float_status")
    if kind == "opening_balance_required" or "float NOT FOUND" in label:
        float_status = float_status or "NOT_FOUND"
    explained = explain_operating_blocker(
        kind,
        {
            "label": label,
            "example": bool(row.get("example")),
            "opening_float_status": float_status,
        },
    )
    row["why"] = explained.get("why") or ""
    row["classification"] = explained.get("classification") or ""
    label_human = CLASSIFICATION_LABELS.get(row["classification"])
    if label_human:
        row["classification_label"] = label_human
    row["explain"] = {
        k: v
        for k, v in explained.items()
        if v not in (None, "", [], {})
    }
    return row


def list_issues(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Exception rows only. Empty when nothing is wrong."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        issues: list[dict[str, Any]] = []
        for p in list_prs(conn=c):
            if p["state"] == "POLICY_REQUIRED":
                issues.append(
                    {
                        "kind": "policy_required",
                        "label": _pr_human_label(p),
                        "example": bool(p.get("example")),
                        "pr_id": p["pr_id"],
                        "href": "/bzg/uma-blu/bills",
                    }
                )
            elif p["state"] == "PAID_CLAIMED" and not p.get("payment_evidence_id"):
                issues.append(
                    {
                        "kind": "missing_payment_evidence",
                        "label": _pr_human_label(p),
                        "example": bool(p.get("example")),
                        "pr_id": p["pr_id"],
                        "href": "/bzg/uma-blu/bills",
                    }
                )
            elif p["state"] in ("PAYMENT_APPROVED", "PAID_CLAIMED", "PAYMENT_VERIFIED"):
                evid = p.get("payment_evidence_id")
                if p["state"] != "PAYMENT_APPROVED" and not evid:
                    issues.append(
                        {
                            "kind": "missing_payment_evidence",
                            "label": _pr_human_label(p),
                            "example": bool(p.get("example")),
                            "pr_id": p["pr_id"],
                            "href": "/bzg/uma-blu/bills",
                        }
                    )

        for d in _petty_attention_for_today(conn=c):
            issues.append(_petty_day_issue(d))

        try:
            closes = _venue_close.list_closes(state="EXCEPTION", limit=20, conn=c)
            for cl in closes:
                issues.append(
                    {
                        "kind": "close_exception",
                        "label": f"Close exception · {cl.get('business_date') or 'date unknown'}",
                        "example": False,
                        "close_id": cl.get("close_id"),
                        "href": "/uma-blu-close",
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        try:
            extra = c.execute(
                """
                SELECT issue_id, source_kind, source_id, note, status
                FROM bzg_ops_operator_issues
                WHERE venue=? AND status='OPEN'
                ORDER BY created_at DESC
                LIMIT 30
                """,
                (VENUE_UMA,),
            ).fetchall()
            for row in extra:
                kind = str(row["source_kind"] or "issues_open")
                issues.append(
                    {
                        "kind": kind if kind else "issues_open",
                        "label": str(row["note"] or "Issue"),
                        "example": False,
                        "issue_id": row["issue_id"],
                        "href": "/bzg/uma-blu/issues",
                    }
                )
        except sqlite3.OperationalError:
            pass

        issues = [_annotate_issue(i) for i in issues]
        return {"ok": True, "issues": issues, "empty": len(issues) == 0, "honesty": dict(HONESTY)}
    finally:
        if own:
            c.close()


def list_history(
    *,
    limit: int = 40,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Timeline from audit.list_events. Human sentences. No new store."""
    own = conn is None
    c = conn or db_connect()
    try:
        events = _audit.list_events(
            entity_id=ENTITY_BZG,
            source=AUDIT_SOURCE,
            limit=limit,
            conn=c,
        )
        # Also include venue-close audit for Uma if present under same entity
        close_events = _audit.list_events(
            entity_id=ENTITY_BZG,
            source="venue_close",
            limit=limit,
            conn=c,
        )
        merged = sorted(
            list(events) + list(close_events),
            key=lambda e: (e.get("occurred_at") or "", e.get("recorded_at") or ""),
            reverse=True,
        )[:limit]
        lines = [_human_audit_line(e) for e in merged]
        legacy_lines = _safe_legacy_history(limit)
        combined = list(lines) + list(legacy_lines)
        seen_prov: set[tuple[str, str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for row in combined:
            prov = _provenance_key(row)
            if prov and prov in seen_prov:
                continue
            if prov:
                seen_prov.add(prov)
            deduped.append(row)
        deduped.sort(key=lambda e: str(e.get("when") or ""), reverse=True)
        return {
            "ok": True,
            "events": deduped[:limit],
            "honesty": dict(HONESTY),
            "fixture_notice": fixture_notice_for(deduped),
        }
    finally:
        if own:
            c.close()


_PR_HUMAN = {
    "bzg.pr.draft": "Purchase draft saved",
    "bzg.pr.requested": "Purchase requested",
    "bzg.pr.approved": "Purchase approved",
    "bzg.pr.ordered": "Purchase ordered",
    "bzg.pr.partially_received": "Part of the order received",
    "bzg.pr.received": "Goods received",
    "bzg.pr.ops_closed": "Purchase closed for operations. Payment was not executed.",
    "bzg.pr.bill_received": "Bill received",
    "bzg.pr.payment_requested": "Payment requested",
    "bzg.pr.payment_approved": "Payment approved",
    "bzg.pr.paid_claimed": "Payment claimed, not yet verified",
    "bzg.pr.payment_verified": "Payment verified",
    "bzg.pr.closed": "Purchase closed",
    "bzg.pr.rejected": "Purchase rejected",
    "bzg.pr.policy_required": "Payment approval needs a policy (authority limit missing)",
}
_ENG_ID_PREFIXES = ("PR-", "PETTY-", "PERS-", "WI-", "ENT-", "EVD-", "ASG-", "PERM-", "ROLE-")


def _detail_not_id(text: str | None) -> str:
    t = (text or "").strip()
    if not t or t.startswith(_ENG_ID_PREFIXES):
        return ""
    return t


def _human_audit_line(e: dict[str, Any]) -> dict[str, Any]:
    action = (e.get("action") or "").strip()
    result = (e.get("result") or "").strip()
    when = e.get("occurred_at") or e.get("recorded_at") or ""
    resource = e.get("resource_id") or ""
    meta = e.get("metadata") if isinstance(e.get("metadata"), dict) else {}
    note = _detail_not_id(str(meta.get("note") or ""))
    status = str(meta.get("status") or "").strip()
    reason = (e.get("reason_code") or "").strip()

    if action.startswith("bzg.pr.") or e.get("resource_type") == RESOURCE_TYPE:
        if action == "bzg.pr.policy_required" or reason == "POLICY_REQUIRED":
            sentence = _PR_HUMAN["bzg.pr.policy_required"]
        else:
            sentence = _PR_HUMAN.get(action) or "Purchase request updated"
            if result == "DENIED":
                sentence = f"{sentence} — not allowed"
    elif action == "bzg.petty.movement" or e.get("resource_type") == RESOURCE_PETTY:
        if status == "IN":
            sentence = "Petty cash in recorded"
        elif status == "OUT":
            sentence = "Petty cash out recorded"
        else:
            sentence = "Petty cash movement recorded"
        if note:
            sentence = f"{sentence} — {note}"
    elif action == "bzg.petty.count":
        if reason == "POLICY_REQUIRED" or status == "POLICY_REQUIRED":
            if "NOT FOUND" in (meta.get("note") or ""):
                sentence = "Petty tin count blocked — opening float NOT FOUND"
            else:
                sentence = "Petty tin count needs a variance policy"
        elif status == "COUNTED":
            sentence = "Petty tin counted"
        elif status == "VARIANCE_NOTED":
            sentence = "Petty tin variance noted"
        else:
            sentence = "Petty tin count recorded"
        if note.startswith("Example") and not sentence.startswith("Example"):
            sentence = f"Example — {sentence}"
    elif action == "bzg.petty.day_state":
        if "reopen" in note.lower():
            sentence = "Petty tin reopened after a new movement"
        else:
            sentence = "Petty tin opened"
        if note.startswith("Example") and not sentence.startswith("Example"):
            sentence = f"Example — {sentence}"
    elif action == "bzg.issue.opened":
        sentence = "Issue opened from an exception"
        if note:
            sentence = f"{sentence} — {note}"
    else:
        words = action.replace(".", " ").replace("_", " ").strip()
        if words.startswith("venue close"):
            words = ("Daily close " + words[len("venue close") :].strip()).strip()
        sentence = (words[:1].upper() + words[1:]) if words else "Recorded"
        if result == "DENIED":
            sentence = f"{sentence} — not allowed"
        elif result == "SUCCEEDED":
            sentence = f"{sentence} — done"

    if resource and sentence.strip() == resource:
        sentence = "Uma Blu record updated"
    if sentence.startswith(_ENG_ID_PREFIXES):
        sentence = "Uma Blu record updated"
    return {
        "when": when,
        "sentence": sentence[:200],
        "resource_id": resource or None,  # detail only; UI shows sentence
    }


def seed_fixture_prs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """At most 3 example PRs: waiting approval, policy required, paid-claim unverified."""
    ensure_schema(conn)
    fixtures = [
        {
            "pr_id": "PR-UMA-EXAMPLE-WAIT",
            "state": "REQUESTED",
            "requester_label": "Example requester",
            "supplier_name": "Example produce supplier",
            "purpose": "Weekend greens",
            "expected_value": 450000.0,
            "currency": "IDR",
            "requested_date": "2026-09-18",
        },
        {
            "pr_id": "PR-UMA-EXAMPLE-POLICY",
            "state": "POLICY_REQUIRED",
            "requester_label": "Example requester",
            "supplier_name": "Example equipment hire",
            "purpose": "Fridge compressor service",
            "expected_value": 12500000.0,
            "currency": "IDR",
            "requested_date": "2026-09-17",
            "bill_reference": "EXAMPLE-BILL-1",
        },
        {
            "pr_id": "PR-UMA-EXAMPLE-CLAIM",
            "state": "PAID_CLAIMED",
            "requester_label": "Example requester",
            "supplier_name": "Example dairy",
            "purpose": "Milk and cream top-up",
            "expected_value": 780000.0,
            "currency": "IDR",
            "requested_date": "2026-09-16",
            "bill_reference": "EXAMPLE-BILL-2",
            "payment_evidence_id": "EVD-EXAMPLE-PAID-CLAIM",
        },
    ]
    out = []
    for f in fixtures:
        existing = get_pr(f["pr_id"], conn=conn)
        if existing:
            out.append(existing)
            continue
        out.append(insert_pr_row(conn=conn, example=True, **f))
    return out


def commissioning_readiness() -> dict[str, Any]:
    """Readiness only. Does not grant a seat, invent a float, or name a closer."""
    float_ex = explain_operating_blocker(
        "opening_balance_required",
        {"opening_float_status": "NOT_FOUND", "label": "OPENING BALANCE REQUIRED"},
    )
    policy_ex = explain_operating_blocker("policy_required", {})
    closer_ex = explain_operating_blocker("closer_required", {})
    closer_status = str(
        _venue_close.HONESTY.get("closer_commissioning")
        or "WAITING FOR VERIFIED CLOSING OPERATOR"
    )
    return {
        "date": "2026-09-19",
        "artifact": "commissioning_readiness",
        "system": "uma-blu-today",
        "beta_only": True,
        "human_commissioning": "NOT_DONE",
        "staff_grant": False,
        "devi_auto_commission": False,
        "invented_float": False,
        "invented_closer": False,
        "intended_operator_role": "Uma Blu ops lead",
        "intended_operator_note": (
            "The intended operator is the Uma Blu ops lead. This slice does not "
            "grant that seat, does not insert a person, and does not auto-commission anyone."
        ),
        "permissions_required": [
            {
                "code": "bzg.pr.payment_approve",
                "granted_live": False,
                "note": "Permission may exist. No live role grant and no authority limit.",
            },
            {
                "code": "venue.close.read",
                "note": "Read the existing Daily Close. Do not rebuild it.",
            },
            {
                "code": "venue.close.submit",
                "note": "ROLE-BZG-CLOSER and ROLE-MATT only. Closer is not commissioned.",
            },
            {
                "code": "venue.close.resolve_exception",
                "note": "ROLE-BZG-HFB. Not widened in this slice.",
            },
            {
                "code": "venue.close.verify",
                "note": "ROLE-BZG-HFB. Submitter is not the verifier.",
            },
        ],
        "can": [
            "Open Today and see attention-ordered cards with why and classification.",
            "Open PR and bills as an operational record.",
            "Record petty movements while the opening float is NOT_FOUND.",
            "Open Daily Close at /uma-blu-close.",
            "Read Issues and History.",
        ],
        "cannot": [
            "Execute a payment.",
            "Approve a payment without an authorised monetary limit.",
            "Invent or display an opening float.",
            "Submit a close as a named closer.",
            "Set a variance threshold.",
            "Grant live staff or auto-commission an ops lead.",
        ],
        "remaining_blockers": [
            {
                "id": "opening_float",
                "status": "NOT_FOUND",
                "classification": float_ex.get("classification"),
                "why": float_ex.get("why"),
            },
            {
                "id": "monetary_authority",
                "status": "NOT_SEEDED",
                "classification": policy_ex.get("classification"),
                "why": policy_ex.get("why"),
            },
            {
                "id": "closer",
                "status": closer_status,
                "classification": closer_ex.get("classification"),
                "why": closer_ex.get("why"),
            },
            {
                "id": "variance_policy",
                "status": "NOT_CONFIGURED",
                "classification": "NEEDS_POLICY",
                "why": (
                    "No authorised variance policy exists. "
                    "No threshold was invented."
                ),
            },
        ],
        "commissioning_test_steps": [
            "Confirm staff_grant is false: no new person row and no new live role assignment.",
            "Open /bzg/uma-blu. Cards are attention-first. Each blocked card shows why and classification. attention_count excludes example:true.",
            "Open /bzg/uma-blu/petty. float_status is NOT_FOUND and the page says OPENING BALANCE REQUIRED. Movements still list.",
            "Open /uma-blu-close. The existing Daily Close loads. The Today card href is /uma-blu-close. No closer name was added.",
            "Open /bzg/uma-blu/issues. Exception rows only, with why from the blocker helper.",
            "Do not grant bzg.pr.payment_approve to a live person. Do not seed an authority limit. Do not seed an opening float.",
        ],
        "routes": [
            "/bzg/uma-blu",
            "/bzg/uma-blu/petty",
            "/bzg/uma-blu/issues",
            "/uma-blu-close",
        ],
    }


def commissioning_ready_path() -> Path:
    return BETA_ROOT / "state" / "build-claims" / COMMISSIONING_READY_NAME


def write_commissioning_readiness(path: Path | None = None) -> Path:
    """Write the readiness artifact. Does not grant staff or touch Production."""
    target = path or commissioning_ready_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = commissioning_readiness()
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def module_source_path() -> Path:
    return Path(__file__).resolve()
