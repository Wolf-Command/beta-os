#!/usr/bin/env python3
"""BZG / Uma Blu operations console — PR + petty operational record (Beta).

REQUESTED ≠ APPROVED ≠ ORDERED ≠ RECEIVED ≠ BILL ≠ PAYMENT ≠ PAID_CLAIMED ≠ VERIFIED.
PAID_CLAIMED stores human-paid evidence only. Does not move money.
Petty: movements + day-tin states only. Opening float NOT FOUND unless provided.
No invented authority limit / variance threshold. No second history table.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import authority as _authority
from core import evidence as _evidence
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

STATES = frozenset(
    {
        "REQUESTED",
        "APPROVED",
        "ORDERED",
        "RECEIVED",
        "BILL_RECEIVED",
        "PAYMENT_REQUESTED",
        "PAYMENT_APPROVED",
        "PAID_CLAIMED",
        "PAYMENT_VERIFIED",
        "CLOSED",
        "POLICY_REQUIRED",
        "REJECTED",
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "REQUESTED": frozenset({"APPROVED", "REJECTED"}),
    "APPROVED": frozenset({"ORDERED"}),
    "ORDERED": frozenset({"RECEIVED"}),
    "RECEIVED": frozenset({"BILL_RECEIVED"}),
    "BILL_RECEIVED": frozenset({"PAYMENT_REQUESTED"}),
    "PAYMENT_REQUESTED": frozenset({"PAYMENT_APPROVED"}),
    "POLICY_REQUIRED": frozenset({"PAYMENT_APPROVED"}),
    "PAYMENT_APPROVED": frozenset({"PAID_CLAIMED"}),
    "PAID_CLAIMED": frozenset({"PAYMENT_VERIFIED"}),
    "PAYMENT_VERIFIED": frozenset({"CLOSED"}),
    "REJECTED": frozenset(),
    "CLOSED": frozenset(),
}

HONESTY = {
    "payment_execution": "NOT_BUILT",
    "paid_claim_is_not_verified": True,
    "request_is_not_approval": True,
    "authority_limits_invented": False,
    # Opening float baseline not authorised — never OK with a made-up number.
    "float": "NOT_FOUND",
    "petty_cash_page": "BUILT",
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
    if day and day.get("state") in ("COUNTED", "CLOSED_CLAIMED"):
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
    if commit:
        conn.commit()
    out = get_petty_day(biz, conn=conn)
    assert out
    return out


def list_petty(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """GET payload: movements + day summaries + honesty. Float stays NOT_FOUND when absent."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        movements = list_petty_movements(conn=c)
        days = list_petty_days(conn=c)
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
            "fixture_notice": any(m.get("example") for m in movements)
            or any(d.get("example") for d in days),
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
        """
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
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        lim = max(1, min(int(limit), 200))
        if state:
            rows = c.execute(
                """
                SELECT * FROM bzg_ops_purchase_requests
                WHERE venue=? AND state=?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (venue, state.strip().upper(), lim),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM bzg_ops_purchase_requests
                WHERE venue=?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (venue, lim),
            ).fetchall()
        return [_public(dict(r)) for r in rows]
    finally:
        if own:
            c.close()


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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'REQUESTED', ?, ?, ?, ?)
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
                wi["work_item_id"],
                1 if example else 0,
                ts,
                ts,
            ),
        )
        _audit_pr(
            action="bzg.pr.requested",
            result="SUCCEEDED",
            pr_id=pr_id,
            state="REQUESTED",
            verified_person_id=verified_person_id,
            actor_type=actor_type,
            identity=identity,
            conn=c,
            metadata={"status": "REQUESTED", "note": "request_is_not_approval"},
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
    at = actor_type.upper()
    kwargs: dict[str, Any] = {
        "action": action,
        "result": result,
        "source": AUDIT_SOURCE,
        "actor_type": at,
        "entity_id": ENTITY_BZG,
        "brand_id": VENUE_UMA,
        "resource_type": RESOURCE_TYPE,
        "resource_id": pr_id,
        "reason_code": reason_code,
        "metadata": metadata or {"status": state},
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


def _safe_close_for_today(
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read today's close. On path/guard failure → Close not loaded (no fake numbers)."""
    try:
        biz = today_biz_date()
        row = _venue_close.get_close(business_date=biz, conn=conn)
        if not row:
            return {"status": "not_started", "label": "Daily close not started", "business_date": biz}
        st = row.get("state") or ""
        if st == "VERIFIED_CLOSED":
            return {
                "status": "verified",
                "label": "Daily close verified",
                "business_date": biz,
                "close_id": row.get("close_id"),
            }
        if st == "EXCEPTION":
            return {
                "status": "exception",
                "label": "Daily close exception open",
                "business_date": biz,
                "close_id": row.get("close_id"),
            }
        if st == "VARIANCE_REQUIRES_POLICY":
            return {
                "status": "blocked",
                "label": "Daily close blocked — policy needed",
                "business_date": biz,
                "close_id": row.get("close_id"),
            }
        # Quiet for other in-progress states
        return {
            "status": "in_progress",
            "label": None,
            "business_date": biz,
            "close_id": row.get("close_id"),
            "state": st,
        }
    except Exception:  # noqa: BLE001
        return {"status": "not_loaded", "label": "Close not loaded"}


def today_cards(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Human-language Today cards. Quiet cards omitted. Fixtures labelled Example."""
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
            cards.append(
                {
                    "kind": kind,
                    "title": title,
                    "count": len(items),
                    "href": href,
                    "items": [
                        {
                            "label": _pr_human_label(p),
                            "example": bool(p.get("example")),
                            "pr_id": p["pr_id"],  # click-through only
                        }
                        for p in items
                    ],
                }
            )

        waiting = [p for p in prs if p["state"] == "REQUESTED"]
        add_card(
            "prs_waiting_approval",
            "PRs waiting approval",
            waiting,
            href="/bzg/uma-blu/bills",
        )

        ordered = [p for p in prs if p["state"] == "ORDERED"]
        add_card(
            "ordered_not_received",
            "Ordered, not received",
            ordered,
            href="/bzg/uma-blu/bills",
        )

        bills = [p for p in prs if p["state"] in ("BILL_RECEIVED", "PAYMENT_REQUESTED")]
        add_card(
            "bills_waiting_payment_approval",
            "Bills waiting payment approval",
            bills,
            href="/bzg/uma-blu/bills",
        )

        claimed = [p for p in prs if p["state"] == "PAID_CLAIMED"]
        add_card(
            "payment_claimed_not_verified",
            "Payment claimed, not verified",
            claimed,
            href="/bzg/uma-blu/bills",
        )

        policy = [p for p in prs if p["state"] == "POLICY_REQUIRED"]
        add_card(
            "policy_required",
            "Policy required",
            policy,
            href="/bzg/uma-blu/issues",
        )

        close_info = _safe_close_for_today(conn=c)
        if close_info.get("label") and close_info.get("status") in (
            "not_started",
            "blocked",
            "exception",
            "verified",
            "not_loaded",
        ):
            cards.append(
                {
                    "kind": "daily_close",
                    "title": close_info["label"],
                    "count": 1,
                    "href": "/uma-blu-close",
                    "example": False,
                    "items": [],
                    "close": {
                        k: v
                        for k, v in close_info.items()
                        if k in ("status", "business_date")
                    },
                }
            )

        # Petty: quiet when clean; card when open / policy-required / uncounted.
        petty_days = _petty_attention_for_today(conn=c)
        if petty_days:
            items = []
            for d in petty_days:
                st = d.get("state") or "OPEN"
                label = f"Petty tin · {d.get('business_date') or 'date unknown'} · {st}"
                if d.get("example"):
                    label = f"Example — {label}"
                if d.get("opening_float") is None:
                    label = f"{label} (float NOT FOUND)"
                items.append(
                    {
                        "label": label,
                        "example": bool(d.get("example")),
                        "business_date": d.get("business_date"),
                        "state": st,
                    }
                )
            cards.append(
                {
                    "kind": "petty_cash",
                    "title": "Petty cash needs attention",
                    "count": len(items),
                    "href": "/bzg/uma-blu/petty",
                    "items": items,
                }
            )

        return {
            "ok": True,
            "cards": cards,
            "honesty": dict(HONESTY),
            "fixture_notice": any(p.get("example") for p in prs)
            or any(d.get("example") for d in petty_days),
        }
    finally:
        if own:
            c.close()


def _pr_human_label(p: dict[str, Any]) -> str:
    bits = []
    if p.get("supplier_name"):
        bits.append(str(p["supplier_name"]))
    if p.get("purpose"):
        bits.append(str(p["purpose"]))
    label = " · ".join(bits) if bits else "Purchase request"
    if p.get("example"):
        label = f"Example — {label}"
    return label


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
        return {"ok": True, "events": lines, "honesty": dict(HONESTY)}
    finally:
        if own:
            c.close()


def _human_audit_line(e: dict[str, Any]) -> dict[str, Any]:
    action = (e.get("action") or "").strip()
    result = (e.get("result") or "").strip()
    when = e.get("occurred_at") or e.get("recorded_at") or ""
    resource = e.get("resource_id") or ""
    sentence = action.replace(".", " ").replace("_", " ").strip()
    if result == "DENIED":
        sentence = f"{sentence} — not allowed"
    elif result == "SUCCEEDED":
        sentence = f"{sentence} — done"
    if e.get("reason_code") == "POLICY_REQUIRED":
        sentence = "Payment approval needs a policy (authority limit missing)"
    return {
        "when": when,
        "sentence": sentence[:200],
        "resource_id": resource or None,  # detail only; UI may hide
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


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def module_source_path() -> Path:
    return Path(__file__).resolve()
