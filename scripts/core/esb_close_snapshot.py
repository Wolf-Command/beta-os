#!/usr/bin/env python3
"""Read-only ESB warehouse snapshot for Uma Blu daily close.

PROVENANCE: salesPayments payment lines — NOT settlement report.
settlement_api: UNAVAILABLE
esb_cash_basis: PAYMENT_LINES_NOT_SETTLEMENT

Never writes to esb.sqlite. Path configurable for test isolation.

BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1:
- Classify QRIS/EDC from paymentMethodName when TypeName is CARD (Uma).
- Bank-split EDC/QRIS (BNI/Mandiri/…).
- Bill-level export for forensic dual-source (live ≠ overwrite receipt).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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

_BANK_TOKENS = (
    "BNI",
    "MANDIRI",
    "BCA",
    "BRI",
    "CIMB",
    "PERMATA",
    "DANAMON",
    "BTN",
)


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


def _classify_pay_type(
    type_name: str | None,
    method_name: str | None = None,
) -> str:
    """Bucket payment lines. Method name wins when TypeName mislabels QRIS as CARD."""
    t = (type_name or "").strip().upper()
    m = (method_name or "").strip().upper()
    # QRIS never merges into CARD — check name + type before CARD bucket.
    if "QRIS" in m or "QRIS" in t:
        return "QRIS"
    if t == "CASH" or m == "CASH":
        return "CASH"
    if "EDC" in m or t == "CARD":
        return "CARD"
    if t in {"OTHER COST", "OTHER"} or "COMPLIMENT" in m or "CHEF" in m:
        return "OTHER"
    if t:
        return "OTHER"
    return "OTHER"


def _bank_from_method(method_name: str | None) -> str | None:
    m = (method_name or "").strip().upper()
    if not m:
        return None
    for tok in _BANK_TOKENS:
        if tok in m:
            if tok == "MANDIRI":
                return "Mandiri"
            return tok
    return None


def _slug_method(method_name: str | None) -> str:
    raw = (method_name or "UNKNOWN").strip()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").upper()
    return slug or "UNKNOWN"


def payment_line_key(
    bucket: str,
    *,
    method_name: str | None,
    type_name: str | None = None,
) -> str:
    """Canonical dual-source key: EDC_BNI / QRIS_Mandiri / Cash / ROB_FAMILY …"""
    m = (method_name or "").strip()
    bank = _bank_from_method(m)
    if bucket == "CASH":
        return "Cash"
    if bucket == "CARD":
        if bank:
            return f"EDC_{bank if bank != 'Mandiri' else 'Mandiri'}"
        return f"EDC_{_slug_method(m)}" if m else "EDC_UNKNOWN"
    if bucket == "QRIS":
        if bank:
            return f"QRIS_{bank if bank != 'Mandiri' else 'Mandiri'}"
        return f"QRIS_{_slug_method(m)}" if m else "QRIS_UNKNOWN"
    # Non-bank / OTHER — preserve human method label as slug
    if m:
        # Align with Owner receipt labels where known
        mu = m.upper()
        if "ROB" in mu and "FAMILY" in mu:
            return "ROB_FAMILY"
        if "SCOTT" in mu:
            return "SCOTT_ETIK"
        if "ROOM" in mu and "CHARGE" in mu:
            return "ROOM_CHARGE_112" if "112" in mu else f"ROOM_CHARGE_{_slug_method(m)}"
        if "COMPLIMENT" in mu:
            return "COMPLIMENT"
        if "CHEF" in mu or "EXECUTIFE" in mu or "EXECUTIVE" in mu:
            return "EXECUTIVE_CHEF"
        return _slug_method(m)
    return _slug_method(type_name)


def snapshot_day(
    business_date: str,
    *,
    branch_code: str = BRANCH_CODE,
    esb_path: Path | str | None = None,
    include_bills: bool = False,
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
    qris_from_payments = 0.0
    other_from_payments = 0.0
    cash_sales_grand = 0.0  # grandTotal of bills with CASH tender (excl change semantics)
    pay_mix: dict[str, float] = {}
    pay_by_name: dict[str, float] = {}
    pay_by_bank_split: dict[str, float] = {}
    pax_total = 0.0
    other_cost_bill_count = 0
    cash_change_overpay = 0.0

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
        pax_total += _num(bill.get("paxTotal"))
        pays = bill.get("salesPayments") or []
        pay_sig = []
        bill_cash = 0.0
        bill_buckets: set[str] = set()
        bill_pay_rows: list[dict[str, Any]] = []
        for p in pays:
            ptype_raw = p.get("paymentMethodTypeName")
            pname_raw = p.get("paymentMethodName")
            bucket = _classify_pay_type(ptype_raw, pname_raw)
            amt = _num(p.get("paymentAmount"))
            line_key = payment_line_key(
                bucket, method_name=str(pname_raw or ""), type_name=str(ptype_raw or "")
            )
            # Type-level mix kept for backward compat; name + bank-split are authoritative.
            type_key = str(ptype_raw or bucket)
            pay_mix[type_key] = pay_mix.get(type_key, 0.0) + amt
            name_key = str(pname_raw or type_key)
            pay_by_name[name_key] = pay_by_name.get(name_key, 0.0) + amt
            pay_by_bank_split[line_key] = pay_by_bank_split.get(line_key, 0.0) + amt
            bill_buckets.add(bucket)
            if bucket == "CASH":
                cash_from_payments += amt
                bill_cash += amt
            elif bucket == "CARD":
                card_from_payments += amt
            elif bucket == "QRIS":
                qris_from_payments += amt
            else:
                other_from_payments += amt
            pay_sig.append(f"{pname_raw or ptype_raw}:{amt}")
            bill_pay_rows.append(
                {
                    "method_name": pname_raw,
                    "type_name": ptype_raw,
                    "bucket": bucket,
                    "line_key": line_key,
                    "amount": round(amt, 2),
                    "bank": _bank_from_method(str(pname_raw or "")),
                }
            )
        if bill_cash > 0:
            cash_sales_grand += gt
            if bill_cash > gt + 0.009:
                cash_change_overpay += bill_cash - gt
        if "OTHER" in bill_buckets and not (bill_buckets - {"OTHER"}):
            other_cost_bill_count += 1
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
                "pax_total": _num(bill.get("paxTotal")),
                "sales_date_out": bill.get("salesDateOut"),
                "cash_tendered": round(bill_cash, 2),
                "is_other_cost_only": "OTHER" in bill_buckets
                and not (bill_buckets - {"OTHER"}),
                "payments": bill_pay_rows if include_bills else None,
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

    sales_bill_count = finished_count - other_cost_bill_count
    sales_pax = round(
        sum(b["pax_total"] for b in finished if not b.get("is_other_cost_only")), 2
    )
    sales_grand = round(
        sum(b["grand_total"] for b in finished if not b.get("is_other_cost_only")), 2
    )

    totals = {
        "grand_total": round(grand_total, 2),
        "payment_total": round(payment_total, 2),
        "cash_from_payments": round(cash_from_payments, 2),
        "cash_sales_grand": round(cash_sales_grand, 2),
        "cash_change_overpay": round(cash_change_overpay, 2),
        "card_from_payments": round(card_from_payments, 2),
        "qris_from_payments": round(qris_from_payments, 2),
        "other_from_payments": round(other_from_payments, 2),
        "finished_count": finished_count,
        "sales_bill_count_excl_other_cost": sales_bill_count,
        "other_cost_bill_count": other_cost_bill_count,
        "pax_total": round(pax_total, 2),
        "sales_pax_excl_other_cost": sales_pax,
        "sales_grand_excl_other_cost": sales_grand,
        "cancelled_count": cancelled_count,
        "other_status_count": other_status,
        "payment_mix": {k: round(v, 2) for k, v in sorted(pay_mix.items())},
        "payment_by_method_name": {
            k: round(v, 2) for k, v in sorted(pay_by_name.items())
        },
        "payments_by_bank_split": {
            k: round(v, 2) for k, v in sorted(pay_by_bank_split.items())
        },
        "cash_label": "ESB_CASH_FROM_PAYMENTS",
        "card_label": "ESB_CARD_FROM_PAYMENTS",
        "qris_label": "ESB_QRIS_FROM_PAYMENTS",
        "cash_provenance": "ESB payment lines (salesPayments) — not settlement",
        "cash_tendered_includes_change": True,
        "qris_never_merged_into_card": True,
        "classify_uses_payment_method_name": True,
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
    out: dict[str, Any] = {
        "fingerprint_sha256": digest,
        "esb_pulled_at": max_pulled,
        "query_meta": meta,
        "totals": totals,
        "incomplete": incomplete,
        "incomplete_reason": incomplete_reason,
        **HONESTY,
    }
    if include_bills:
        out["finished_bills"] = [
            {k: v for k, v in b.items() if v is not None} for b in finished
        ]
    return out


def current_fingerprint(
    business_date: str,
    *,
    branch_code: str = BRANCH_CODE,
    esb_path: Path | str | None = None,
) -> str:
    snap = snapshot_day(business_date, branch_code=branch_code, esb_path=esb_path)
    return snap["fingerprint_sha256"]
