#!/usr/bin/env python3
"""P2P-PAYMENT-RECORD-1 — Record outside-Wolf payments against Ready-to-Pay bills (Beta).

Recording only — no payment execution, no bank API, no disbursement.
Segregation: recorder cannot be AP-ready or Ready-to-Pay marker on the same bill.
Bank recon confirm verifies claimed payments and closes fully paid bills.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import bzg_purchase_request as _pr
from core import bzg_ready_to_pay as _rtp
from core import rbac as _rbac
from core import uma_ops_console as _ops
from core import wolf_evidence_guard as _weg

PACK = "P2P-PAYMENT-RECORD-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_PAY_RECORD = "bzg.pay.record"
PERM_PAY_RECORD_ID = "PERM-BZG-PAY-RECORD"
AUDIT_SOURCE = "bzg_payment_record"
PROOF_SCHEME = "bzg-payment-proof://"
PROOF_DIR = _weg.resolve_payment_proof_dir()
AMOUNT_TOLERANCE = 0.01

STATUS_CLAIMED = "claimed"
STATUS_VERIFIED = "verified"
STATUS_CLOSED = "closed"

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "payment_execution": False,
    "payment_approve": False,
    "money_movement": False,
    "recording_only": True,
    "no_bank_api": True,
    "no_payment_file": True,
}


class PaymentRecordError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_payment_record_id() -> str:
    return f"PAY-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_payment_record_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent payment-record table."""
    _rtp.ensure_ready_to_pay_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_payment_records'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_payment_records (
              payment_record_id TEXT PRIMARY KEY,
              ready_to_pay_id TEXT NOT NULL,
              bill_id TEXT NOT NULL,
              ap_ready_id TEXT NOT NULL,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              nota_number TEXT NOT NULL,
              stated_total REAL NOT NULL,
              paid_date TEXT NOT NULL,
              amount REAL NOT NULL,
              from_account TEXT NOT NULL,
              bank_reference TEXT NOT NULL,
              proof_object_ref TEXT,
              status TEXT NOT NULL DEFAULT 'claimed',
              recorded_by_person_id TEXT NOT NULL,
              recorded_by_assignment_id TEXT,
              verified_at TEXT,
              verified_by_person_id TEXT,
              bank_txn_id TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(bank_reference, bill_id)
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_payment_records_bill
              ON bzg_ops_payment_records(bill_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_payment_records_rtp
              ON bzg_ops_payment_records(ready_to_pay_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_payment_records_status
              ON bzg_ops_payment_records(status);
            """
        )
        added.append("bzg_ops_payment_records")
    return added


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_record_payment(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    target = _pr.outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, PERM_PAY_RECORD, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_record_payment(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_record_payment(person_id, outlet_id, conn)
    if not ok or not asg:
        raise PaymentRecordError(
            "You cannot record a payment for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def recorder_segregation_deny(
    person_id: str, bill_id: str, conn: sqlite3.Connection
) -> str | None:
    """Recorder cannot be AP-ready or Ready-to-Pay marker on this bill."""
    pid = (person_id or "").strip()
    bid = (bill_id or "").strip()
    if not pid or not bid:
        return None
    ap_row = conn.execute(
        "SELECT marked_by_person_id FROM bzg_ops_ap_ready WHERE bill_id=?", (bid,)
    ).fetchone()
    if ap_row and str(ap_row["marked_by_person_id"]) == pid:
        return "ap_marker_cannot_record_payment"
    rtp_row = conn.execute(
        "SELECT marked_by_person_id FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bid,)
    ).fetchone()
    if rtp_row and str(rtp_row["marked_by_person_id"]) == pid:
        return "pay_ready_marker_cannot_record_payment"
    return None


def save_proof_bytes(
    *,
    data: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    if not data:
        raise PaymentRecordError("Payment proof required.", code="missing_proof")
    if len(data) > 8_000_000:
        raise PaymentRecordError("Proof file too large.", code="proof_too_large", http_status=413)
    _weg.assert_live_evidence_writable(PROOF_DIR, label="payment proof")
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".png") or "png" in ctype:
        ext = ".png"
    elif name.endswith(".pdf") or "pdf" in ctype:
        ext = ".pdf"
    eid = f"EVD-PAY-{uuid.uuid4().hex[:12].upper()}"
    dest = PROOF_DIR / f"{eid}{ext}"
    dest.write_bytes(data)
    ch = hashlib.sha256(data).hexdigest()
    ref = f"{PROOF_SCHEME}{eid}{ext}"
    return {
        "ok": True,
        "proof_object_ref": ref,
        "content_hash": ch,
        "bytes": len(data),
        "mime_type": content_type or f"image/{ext.lstrip('.')}",
        "filename": filename or dest.name,
    }


def resolve_proof_path(object_ref: str | None) -> Path | None:
    ref = (object_ref or "").strip()
    if not ref.startswith(PROOF_SCHEME):
        return None
    token = ref[len(PROOF_SCHEME) :].strip()
    if not token or "/" in token or "\\" in token or ".." in token:
        return None
    path = (PROOF_DIR / token).resolve()
    try:
        path.relative_to(PROOF_DIR.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _row(conn: sqlite3.Connection, payment_record_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_payment_records WHERE payment_record_id=?",
        (payment_record_id,),
    ).fetchone()
    return dict(row) if row else None


def _by_bank_ref(conn: sqlite3.Connection, bill_id: str, bank_reference: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM bzg_ops_payment_records
        WHERE bill_id=? AND bank_reference=?
        """,
        (bill_id, bank_reference),
    ).fetchone()
    return dict(row) if row else None


def bill_payment_summary(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any]:
    bid = (bill_id or "").strip()
    rtp = conn.execute(
        "SELECT stated_total FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bid,)
    ).fetchone()
    stated = float(rtp["stated_total"]) if rtp else 0.0
    rows = conn.execute(
        """
        SELECT status, amount FROM bzg_ops_payment_records
        WHERE bill_id=? AND status != 'void'
        """,
        (bid,),
    ).fetchall()
    claimed = verified = 0.0
    has_unverified_claim = False
    for row in rows:
        amt = float(row["amount"] or 0)
        st = str(row["status"] or "")
        if st in {STATUS_CLAIMED, STATUS_VERIFIED, STATUS_CLOSED}:
            claimed += amt
        if st in {STATUS_VERIFIED, STATUS_CLOSED}:
            verified += amt
        if st == STATUS_CLAIMED:
            has_unverified_claim = True
    remaining = max(0.0, stated - claimed)
    fully_verified = stated > 0 and verified >= stated - AMOUNT_TOLERANCE
    return {
        "stated_total": stated,
        "claimed_total": claimed,
        "verified_total": verified,
        "remaining_balance": remaining,
        "has_unverified_claim": has_unverified_claim,
        "fully_verified": fully_verified,
        "fully_closed": fully_verified and not has_unverified_claim,
    }


def _status_labels(summary: dict[str, Any]) -> dict[str, str | None]:
    if summary.get("fully_closed"):
        return {
            "paid_claimed_label": "Paid (claimed)",
            "verified_label": "Verified",
            "payment_status_label": "Closed",
        }
    if summary.get("fully_verified"):
        return {
            "paid_claimed_label": "Paid (claimed)",
            "verified_label": "Verified",
            "payment_status_label": "Verified",
        }
    if summary.get("has_unverified_claim"):
        rem = summary.get("remaining_balance") or 0
        if rem > AMOUNT_TOLERANCE:
            return {
                "paid_claimed_label": "Paid (claimed)",
                "verified_label": "Not yet seen in bank",
                "payment_status_label": f"Partial paid · Rp{int(rem):,} remaining",
            }
        return {
            "paid_claimed_label": "Paid (claimed)",
            "verified_label": "Not yet seen in bank",
            "payment_status_label": "Claimed, not yet seen in bank",
        }
    if (summary.get("claimed_total") or 0) > 0:
        rem = summary.get("remaining_balance") or 0
        return {
            "paid_claimed_label": "Paid (claimed)",
            "verified_label": "Partial verified",
            "payment_status_label": f"Partial paid · Rp{int(rem):,} remaining",
        }
    return {
        "paid_claimed_label": None,
        "verified_label": None,
        "payment_status_label": None,
    }


def enrich_payment(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, **HONESTY}
    st = str(row.get("status") or "")
    if st == STATUS_CLAIMED:
        out["status_label"] = "Paid (claimed)"
    elif st == STATUS_VERIFIED:
        out["status_label"] = "Verified"
    elif st == STATUS_CLOSED:
        out["status_label"] = "Closed"
    else:
        out["status_label"] = st.replace("_", " ").title() if st else "Unknown"
    oid = str(row.get("outlet_id") or "")
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    return out


def record_payment(
    *,
    person_id: str,
    bill_id: str,
    paid_date: str,
    amount: float,
    from_account: str,
    bank_reference: str,
    proof_object_ref: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise PaymentRecordError("Authentication required.", code="unauthenticated", http_status=401)
    bid = (bill_id or "").strip()
    if not bid:
        raise PaymentRecordError("Supplier nota is required.", code="missing_bill")
    paid = (paid_date or "").strip()
    if not paid:
        raise PaymentRecordError("Paid date is required.", code="missing_paid_date")
    ref = (bank_reference or "").strip()
    if not ref:
        raise PaymentRecordError("Bank reference is required.", code="missing_bank_reference")
    acct = (from_account or "").strip()
    if not acct:
        raise PaymentRecordError("From account is required.", code="missing_from_account")
    try:
        pay_amt = float(amount)
    except (TypeError, ValueError):
        raise PaymentRecordError("Amount is required.", code="missing_amount")
    if pay_amt <= 0:
        raise PaymentRecordError("Amount must be greater than zero.", code="invalid_amount")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_payment_record_schema(c)
        existing = _by_bank_ref(c, bid, ref)
        if existing:
            sod = recorder_segregation_deny(pid, bid, c)
            if sod:
                raise PaymentRecordError(
                    "You cannot record payment on a bill you marked AP-ready or ready to pay.",
                    code=sod,
                    http_status=403,
                )
            rtp_row = c.execute(
                "SELECT * FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bid,)
            ).fetchone()
            if not rtp_row:
                raise PaymentRecordError(
                    "Bill must be on Ready to Pay before recording payment.",
                    code="not_ready_to_pay",
                    http_status=400,
                )
            oid = str(rtp_row["outlet_id"])
            require_record_payment(pid, oid, c)
            return enrich_payment(existing, c)

        rtp_row = c.execute(
            "SELECT * FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bid,)
        ).fetchone()
        if not rtp_row:
            raise PaymentRecordError(
                "Bill must be on Ready to Pay before recording payment.",
                code="not_ready_to_pay",
                http_status=400,
            )
        rtp = dict(rtp_row)
        oid = str(rtp["outlet_id"])
        sod = recorder_segregation_deny(pid, bid, c)
        if sod:
            raise PaymentRecordError(
                "You cannot record payment on a bill you marked AP-ready or ready to pay.",
                code=sod,
                http_status=403,
            )
        asg = require_record_payment(pid, oid, c)
        summary = bill_payment_summary(c, bid)
        remaining = float(summary.get("remaining_balance") or 0)
        stated = float(rtp.get("stated_total") or 0)
        if remaining <= 0 and stated > 0:
            raise PaymentRecordError(
                "This bill is already fully paid.",
                code="already_fully_paid",
                http_status=400,
            )
        if pay_amt > remaining + AMOUNT_TOLERANCE and stated > 0:
            raise PaymentRecordError(
                f"Amount exceeds remaining balance (Rp{int(remaining):,}).",
                code="overpayment",
                http_status=400,
            )

        ts = _ops.now_utc_iso()
        payment_record_id = mint_payment_record_id()
        c.execute(
            """
            INSERT INTO bzg_ops_payment_records (
              payment_record_id, ready_to_pay_id, bill_id, ap_ready_id,
              outlet_id, entity_id, supplier_id, supplier_name, nota_number,
              stated_total, paid_date, amount, from_account, bank_reference,
              proof_object_ref, status, recorded_by_person_id,
              recorded_by_assignment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_record_id,
                rtp["ready_to_pay_id"],
                bid,
                rtp["ap_ready_id"],
                oid,
                rtp["entity_id"],
                rtp["supplier_id"],
                rtp["supplier_name"],
                rtp["nota_number"],
                stated,
                paid,
                pay_amt,
                acct,
                ref,
                (proof_object_ref or "").strip() or None,
                STATUS_CLAIMED,
                pid,
                asg.get("assignment_id"),
                ts,
            ),
        )
        _audit.record_event(
            action="bzg.pay.record",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id="BZG-UMA",
            resource_type="bzg_payment_record",
            resource_id=payment_record_id,
            metadata={
                "bill_id": bid,
                "ready_to_pay_id": rtp["ready_to_pay_id"],
                "amount": pay_amt,
                "bank_reference": ref,
                "from_account": acct,
                "paid_date": paid,
                "status": STATUS_CLAIMED,
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _row(c, payment_record_id)
        assert row
        out = enrich_payment(row, c)
        out.update(bill_payment_summary(c, bid))
        out.update(_status_labels(bill_payment_summary(c, bid)))
        return out
    except Exception:
        if own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()


def verify_from_bank_match(
    conn: sqlite3.Connection,
    *,
    payment_record_id: str,
    bank_txn_id: str,
    person_id: str,
    commit: bool = True,
) -> dict[str, Any] | None:
    """Mark payment verified when bank line is confirmed. Returns None if not a payment ref."""
    prid = (payment_record_id or "").strip()
    if not prid:
        return None
    row = _row(conn, prid)
    if not row:
        return None
    if str(row.get("status") or "") != STATUS_CLAIMED:
        return enrich_payment(row, conn)
    ts = _ops.now_utc_iso()
    conn.execute(
        """
        UPDATE bzg_ops_payment_records
        SET status=?, verified_at=?, verified_by_person_id=?, bank_txn_id=?
        WHERE payment_record_id=?
        """,
        (STATUS_VERIFIED, ts, person_id, bank_txn_id, prid),
    )
    _audit.record_event(
        action="bzg.pay.verify",
        result="SUCCEEDED",
        source=AUDIT_SOURCE,
        actor_type="PERSON",
        verified_person_id=person_id,
        actor_person_id=person_id,
        entity_id=LEGAL_ENTITY,
        brand_id="BZG-UMA",
        resource_type="bzg_payment_record",
        resource_id=prid,
        metadata={
            "bill_id": row["bill_id"],
            "bank_txn_id": bank_txn_id,
            "status": STATUS_VERIFIED,
        },
        conn=conn,
        commit=False,
    )
    summary = bill_payment_summary(conn, str(row["bill_id"]))
    if summary.get("fully_verified"):
        conn.execute(
            """
            UPDATE bzg_ops_payment_records
            SET status=?
            WHERE bill_id=? AND status=?
            """,
            (STATUS_CLOSED, row["bill_id"], STATUS_VERIFIED),
        )
        _audit.record_event(
            action="bzg.pay.close",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=person_id,
            actor_person_id=person_id,
            entity_id=LEGAL_ENTITY,
            brand_id="BZG-UMA",
            resource_type="bzg_payment_record",
            resource_id=prid,
            metadata={"bill_id": row["bill_id"], "status": STATUS_CLOSED},
            conn=conn,
            commit=False,
        )
    if commit:
        conn.commit()
    updated = _row(conn, prid)
    return enrich_payment(updated, conn) if updated else None


def list_payments_for_bill(
    bill_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    bid = (bill_id or "").strip()
    if not bid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_payment_record_schema(c)
        rtp = c.execute(
            "SELECT outlet_id FROM bzg_ops_ready_to_pay WHERE bill_id=?", (bid,)
        ).fetchone()
        if not rtp:
            return []
        oid = str(rtp["outlet_id"])
        if person_id and not can_record_payment(person_id, oid, c)[0]:
            if not _rtp.can_list_ready_to_pay(person_id, oid, c)[0]:
                return []
        rows = c.execute(
            """
            SELECT * FROM bzg_ops_payment_records
            WHERE bill_id=?
            ORDER BY created_at DESC
            """,
            (bid,),
        ).fetchall()
        return [enrich_payment(dict(r), c) for r in rows]
    finally:
        if own:
            c.close()


def ap_payment_columns(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any]:
    summary = bill_payment_summary(conn, bill_id)
    labels = _status_labels(summary)
    return {**summary, **labels}


def list_bank_accounts(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT bank_account FROM bzg_bank_transactions
        WHERE entity_id=? AND bank_account IS NOT NULL AND bank_account != ''
        ORDER BY bank_account
        """,
        (LEGAL_ENTITY,),
    ).fetchall()
    return [str(r["bank_account"]) for r in rows if r["bank_account"]]
