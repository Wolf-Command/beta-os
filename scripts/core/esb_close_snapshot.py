#!/usr/bin/env python3
"""Read-only ESB warehouse snapshot for Uma Blu daily close.

PROVENANCE: salesPayments payment lines — NOT settlement report.
settlement_api: UNAVAILABLE
esb_cash_basis: PAYMENT_LINES_NOT_SETTLEMENT

Never writes to esb.sqlite. Path configurable for test isolation.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_ESB_PATH = Path("/Users/wolfterminal/.openclaw/data/esb.sqlite")
BRANCH_CODE = "BLZ"
FINISHED = "Finished"
CANCELLED = "Cancelled"

HONESTY = {
    "settlement_api": "UNAVAILABLE",
    "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
    "live_variance_threshold": 0,
    "live_monetary_authority": 0,
}


class EsbSnapshotError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def resolve_esb_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path).resolve()
    env = (os.environ.get("WOLF_ESB_SQLITE") or "").strip()
    if env:
        return Path(env).resolve()
    return DEFAULT_ESB_PATH.resolve()


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    resolved = Path(db_path).resolve()
    # Refuse obvious write targets that are Production money DBs; warehouse is read-only URI.
    if str(resolved).endswith("money.sqlite") or "/Production" in str(resolved):
        raise EsbSnapshotError(
            f"refuses production path: {resolved}",
            code="production_refused",
            http_status=500,
        )
    if not resolved.is_file():
        raise EsbSnapshotError(
            f"esb warehouse missing: {resolved}",
            code="esb_missing",
            http_status=503,
        )
    uri = f"file:{resolved}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _classify_pay_type(name: str | None) -> str:
    n = (name or "").strip().upper()
    if n == "CASH":
        return "CASH"
    if n == "CARD":
        return "CARD"
    return "OTHER"


def snapshot_day(
    business_date: str,
    *,
    branch_code: str = BRANCH_CODE,
    esb_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build read-only day snapshot for Finished bills + payment mix.

    Empty / incomplete day raises with code esb_empty_day (blocks close).
    """
    date = (business_date or "").strip()
    if not date or len(date) < 10:
        raise EsbSnapshotError("business_date required (YYYY-MM-DD)", code="missing_date")
    branch = (branch_code or BRANCH_CODE).strip().upper() or BRANCH_CODE
    path = resolve_esb_path(esb_path)

    conn = _connect_ro(path)
    try:
        rows = conn.execute(
            """
            SELECT nk, biz_date, raw, pulled_at
            FROM sales
            WHERE biz_date=?
            ORDER BY nk
            """,
            (date,),
        ).fetchall()
    finally:
        conn.close()

    finished: list[dict[str, Any]] = []
    cancelled_count = 0
    other_status = 0
    max_pulled: str | None = None
    fingerprint_parts: list[str] = []

    grand_total = 0.0
    payment_total = 0.0
    cash_from_payments = 0.0
    card_from_payments = 0.0
    other_from_payments = 0.0
    pay_mix: dict[str, float] = {}

    for r in rows:
        raw_s = r["raw"] or "{}"
        try:
            bill = json.loads(raw_s)
        except json.JSONDecodeError:
            raise EsbSnapshotError(
                f"corrupt sales raw for nk={r['nk']}",
                code="esb_corrupt",
                http_status=500,
            ) from None
        bc = (bill.get("branchCode") or "").strip().upper()
        # Fail-closed: blank/missing branchCode is NOT included in Uma (BLZ) totals
        if bc != branch:
            continue
        status = (bill.get("statusName") or "").strip()
        pulled = r["pulled_at"]
        if pulled and (max_pulled is None or str(pulled) > max_pulled):
            max_pulled = str(pulled)

        if status == CANCELLED:
            cancelled_count += 1
            fingerprint_parts.append(f"C|{r['nk']}|{bill.get('salesNum')}|{status}")
            continue
        if status != FINISHED:
            other_status += 1
            fingerprint_parts.append(f"O|{r['nk']}|{bill.get('salesNum')}|{status}")
            continue

        gt = _num(bill.get("grandTotal"))
        pt = _num(bill.get("paymentTotal"))
        grand_total += gt
        payment_total += pt
        pays = bill.get("salesPayments") or []
        pay_sig = []
        for p in pays:
            ptype_raw = p.get("paymentMethodTypeName")
            bucket = _classify_pay_type(ptype_raw)
            amt = _num(p.get("paymentAmount"))
            pay_mix[str(ptype_raw or bucket)] = pay_mix.get(str(ptype_raw or bucket), 0.0) + amt
            if bucket == "CASH":
                cash_from_payments += amt
            elif bucket == "CARD":
                card_from_payments += amt
            else:
                other_from_payments += amt
            pay_sig.append(f"{ptype_raw}:{amt}")
        fingerprint_parts.append(
            f"F|{r['nk']}|{bill.get('salesNum')}|{gt}|{pt}|{'+'.join(sorted(pay_sig))}|{pulled}"
        )
        finished.append(
            {
                "nk": r["nk"],
                "sales_num": bill.get("salesNum"),
                "bill_num": bill.get("billNum"),
                "grand_total": gt,
                "payment_total": pt,
            }
        )

    finished_count = len(finished)
    incomplete = False
    incomplete_reason = None
    if finished_count == 0:
        incomplete = True
        incomplete_reason = "esb_empty_day"
    # No bills at all for branch/date also empty
    if not rows:
        incomplete = True
        incomplete_reason = "esb_empty_day"

    canon = "\n".join(fingerprint_parts) + f"\nMAX_PULL|{max_pulled or ''}"
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    totals = {
        "grand_total": round(grand_total, 2),
        "payment_total": round(payment_total, 2),
        "cash_from_payments": round(cash_from_payments, 2),
        "card_from_payments": round(card_from_payments, 2),
        "other_from_payments": round(other_from_payments, 2),
        "finished_count": finished_count,
        "cancelled_count": cancelled_count,
        "other_status_count": other_status,
        "payment_mix": {k: round(v, 2) for k, v in sorted(pay_mix.items())},
        "cash_label": "ESB_CASH_FROM_PAYMENTS",
        "cash_provenance": "ESB payment lines (salesPayments) — not settlement",
    }
    meta = {
        "branch": branch,
        "business_date": date,
        "bill_count": finished_count + cancelled_count + other_status,
        "finished_count": finished_count,
        "cancelled_count": cancelled_count,
        "warehouse_path": str(path),
        "max_pulled_at": max_pulled,
        "incomplete": incomplete,
        "incomplete_reason": incomplete_reason,
        **HONESTY,
    }
    return {
        "fingerprint_sha256": digest,
        "esb_pulled_at": max_pulled,
        "query_meta": meta,
        "totals": totals,
        "incomplete": incomplete,
        "incomplete_reason": incomplete_reason,
        **HONESTY,
    }


def current_fingerprint(
    business_date: str,
    *,
    branch_code: str = BRANCH_CODE,
    esb_path: Path | str | None = None,
) -> str:
    snap = snapshot_day(business_date, branch_code=branch_code, esb_path=esb_path)
    return snap["fingerprint_sha256"]
