#!/usr/bin/env python3
"""FC-RECON-QUEUES-1 — AMG bank reconciliation proposals (entity ENT-AMG only).

Writes proposal fields only: match_proposed, match_confidence, notes, recon_status.
human_confirmed stays 0. No journals posted. Idempotent.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

ENTITY = "ENT-AMG"
PACK = "FC-RECON-QUEUES-1"
MIGRATION_ID = "fc_recon_queues1_amg_proposals_20261005"
SCHEMA = "amg.bank.recon.proposals.v1"
TZ8 = timezone(timedelta(hours=8))

DATE_SLACK_DAYS = 7
AMOUNT_TOLERANCE = 1.0
PROPOSAL_BY = "SYSTEM"

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "auto_reconcile": False,
    "entity_id": ENTITY,
}


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def public(**extra: Any) -> dict[str, Any]:
    out = {**HONESTY}
    out.update(extra)
    out["staff_ready"] = False
    out["zayen_ready"] = False
    return out


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def txn_amount(row: sqlite3.Row | dict[str, Any]) -> float:
    debit = float(row["debit"] or 0)
    credit = float(row["credit"] or 0)
    return debit if debit > 0 else credit


def _notes_payload(**fields: Any) -> str:
    payload = {k: v for k, v in fields.items() if v is not None}
    payload.setdefault("proposal_by", PROPOSAL_BY)
    return json.dumps(payload, separators=(",", ":"))


def _decode_notes(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"exception_reason": raw}


def _ledger_pools(conn: sqlite3.Connection) -> tuple[dict[tuple[date, float], list[dict[str, str]]], dict[float, list[dict[str, Any]]]]:
    exact: dict[tuple[date, float], list[dict[str, str]]] = defaultdict(list)
    by_amount: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for table, kind, id_col, amt_col, date_col in (
        ("ggv_notas", "nota", "nota_id", "total_amount", "nota_date"),
        ("ggv_bills", "bill", "bill_id", "total_amount", "bill_date"),
        ("ggv_uploads", "upload", "upload_id", "NULL", "uploaded_at"),
    ):
        try:
            rows = conn.execute(
                f"""
                SELECT {id_col} AS ref_id,
                       {amt_col if amt_col != 'NULL' else '0'} AS amount,
                       {date_col} AS business_date
                FROM {table}
                WHERE entity_id=?
                """,
                (ENTITY,),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            amount = float(row["amount"] or 0)
            if amount <= 0:
                continue
            d = _parse_date(str(row["business_date"] or "")[:10])
            ref = {"kind": kind, "ref": str(row["ref_id"])}
            if d:
                exact[(d, amount)].append(ref)
            by_amount[amount].append({**ref, "date": d})
    return exact, by_amount


def _find_transfer_pairs(txns: list[sqlite3.Row]) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[date, float], list[sqlite3.Row]] = defaultdict(list)
    for row in txns:
        amount = txn_amount(row)
        d = _parse_date(row["txn_date"])
        if amount <= 0 or not d:
            continue
        grouped[(d, amount)].append(row)
    matched: dict[str, dict[str, Any]] = {}
    for (_d, amount), group in grouped.items():
        debits = [g for g in group if float(g["debit"] or 0) > 0]
        credits = [g for g in group if float(g["credit"] or 0) > 0]
        if len(debits) != 1 or len(credits) != 1:
            continue
        if str(debits[0]["bank_account"]) == str(credits[0]["bank_account"]):
            continue
        for side, other in ((debits[0], credits[0]), (credits[0], debits[0])):
            matched[str(side["txn_id"])] = {
                "match_proposed": 1,
                "recon_status": "NEEDS_REVIEW",
                "matched_receipt_ref": str(other["txn_id"]),
                "match_confidence": "PROPOSE MATCH",
                "notes": _notes_payload(
                    matched_kind="internal_transfer",
                    matched_label=f"Transfer with account ending {str(other['bank_account'])[-4:]}",
                    proposal_rule="internal_transfer",
                    proposal_text=f"Transfer between AMG accounts on same day for {amount:,.0f}",
                ),
            }
    return matched


def classify_transaction(
    row: sqlite3.Row,
    *,
    transfer_matches: dict[str, dict[str, Any]],
    exact_pool: dict[tuple[date, float], list[dict[str, str]]],
    amount_pool: dict[float, list[dict[str, Any]]],
) -> dict[str, Any]:
    txn_id = str(row["txn_id"])
    if txn_id in transfer_matches:
        return transfer_matches[txn_id]

    amount = txn_amount(row)
    txn_date = _parse_date(row["txn_date"])
    description = str(row["description"] or "")
    desc_lower = description.lower()

    exact_hits = exact_pool.get((txn_date, amount), []) if txn_date else []
    if len(exact_hits) == 1:
        hit = exact_hits[0]
        return {
            "match_proposed": 1,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": hit["ref"],
            "match_confidence": "PROPOSE MATCH",
            "notes": _notes_payload(
                matched_kind=hit["kind"],
                matched_label=hit["ref"],
                proposal_rule=f"exact_{hit['kind']}",
                proposal_text=f"Exact amount and date match to {hit['kind']}",
            ),
        }
    if len(exact_hits) > 1:
        return {
            "match_proposed": 1,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "PROPOSE MATCH",
            "notes": _notes_payload(
                candidates=exact_hits,
                proposal_rule="multi_exact",
                proposal_text="Several records share this amount and date — pick one",
            ),
        }

    slack_candidates: list[dict[str, Any]] = []
    if txn_date:
        for hit in amount_pool.get(amount, []):
            hit_date = hit.get("date")
            if not hit_date:
                continue
            if abs((txn_date - hit_date).days) <= DATE_SLACK_DAYS:
                slack_candidates.append(
                    {"kind": hit["kind"], "ref": hit["ref"], "date": hit_date.isoformat()}
                )
    if slack_candidates:
        return {
            "match_proposed": 1,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "PROPOSE MATCH",
            "notes": _notes_payload(
                candidates=slack_candidates,
                proposal_rule="amount_date_slack",
                proposal_text="Amount matches within a week — review suggested links",
            ),
        }

    if "salary" in desc_lower or "gaji" in desc_lower:
        return {
            "match_proposed": 0,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "SALARY_PAYMENT",
            "notes": _notes_payload(
                exception_reason="salary_payment",
                proposal_rule="salary_payment",
                proposal_text="Salary payment — mark exception or link payroll evidence",
            ),
        }
    if "pajak" in desc_lower or "tax" in desc_lower or "pph" in desc_lower:
        return {
            "match_proposed": 0,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "TAX_PAYMENT",
            "notes": _notes_payload(
                exception_reason="tax_payment",
                proposal_rule="tax_payment",
                proposal_text="Tax payment — needs tax evidence or exception note",
            ),
        }
    if "admin" in desc_lower and "fee" in desc_lower:
        return {
            "match_proposed": 0,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "BANK_ADMIN_FEE",
            "notes": _notes_payload(
                exception_reason="bank_admin_fee",
                proposal_rule="bank_admin_fee",
                proposal_text="Bank admin fee — usually expensed as bank charges",
            ),
        }
    if float(row["debit"] or 0) > 0 and abs(amount - 1500.0) < AMOUNT_TOLERANCE:
        return {
            "match_proposed": 0,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "BANK_ADMIN_FEE",
            "notes": _notes_payload(
                exception_reason="bank_admin_fee",
                proposal_rule="bank_admin_fee",
                proposal_text="Small bank charge — likely admin fee",
            ),
        }
    if "inhouse" in desc_lower or "trf" in desc_lower or "transfer" in desc_lower:
        return {
            "match_proposed": 0,
            "recon_status": "NEEDS_REVIEW",
            "matched_receipt_ref": None,
            "match_confidence": "UNPAIRED_INTERNAL_TRANSFER",
            "notes": _notes_payload(
                exception_reason="unpaired_internal_transfer",
                proposal_rule="unpaired_internal_transfer",
                proposal_text="Internal transfer with no paired line on another account",
            ),
        }

    return {
        "match_proposed": 0,
        "recon_status": "UNIDENTIFIED",
        "matched_receipt_ref": None,
        "match_confidence": "UNMATCHED",
        "notes": None,
    }


def apply_proposals(conn: sqlite3.Connection, *, commit: bool = True) -> dict[str, Any]:
    txns = conn.execute(
        """
        SELECT * FROM ggv_bank_transactions
        WHERE entity_id=? AND human_confirmed=0
        ORDER BY txn_id
        """,
        (ENTITY,),
    ).fetchall()
    exact_pool, amount_pool = _ledger_pools(conn)
    transfer_matches = _find_transfer_pairs(txns)
    counts = {"proposed": 0, "exception": 0, "unmatched": 0, "unchanged_confirmed": 0}
    for row in txns:
        if int(row["human_confirmed"] or 0):
            counts["unchanged_confirmed"] += 1
            continue
        result = classify_transaction(
            row,
            transfer_matches=transfer_matches,
            exact_pool=exact_pool,
            amount_pool=amount_pool,
        )
        if result["match_proposed"]:
            counts["proposed"] += 1
        elif result.get("match_confidence") in {
            "SALARY_PAYMENT",
            "TAX_PAYMENT",
            "BANK_ADMIN_FEE",
            "UNPAIRED_INTERNAL_TRANSFER",
        }:
            counts["exception"] += 1
        else:
            counts["unmatched"] += 1
        conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET recon_status=?, matched_receipt_ref=?, match_confidence=?, match_proposed=?, notes=?
            WHERE txn_id=? AND entity_id=? AND human_confirmed=0
            """,
            (
                result["recon_status"],
                result.get("matched_receipt_ref"),
                result.get("match_confidence"),
                int(result.get("match_proposed") or 0),
                result.get("notes"),
                row["txn_id"],
                ENTITY,
            ),
        )
    if commit:
        conn.commit()
    proposed_total = conn.execute(
        "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=? AND match_proposed=1 AND human_confirmed=0",
        (ENTITY,),
    ).fetchone()[0]
    return public(
        ok=True,
        schema=SCHEMA,
        applied_at=now_iso(),
        transaction_count=len(txns),
        counts=counts,
        proposed_total=int(proposed_total),
        transfer_pair_count=len(transfer_matches) // 2,
    )


def proposal_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT
          SUM(CASE WHEN match_proposed=1 AND human_confirmed=0 THEN 1 ELSE 0 END) AS proposed,
          SUM(CASE WHEN human_confirmed=1 THEN 1 ELSE 0 END) AS matched,
          SUM(CASE WHEN match_proposed=0 AND human_confirmed=0
                    AND match_confidence IN ('SALARY_PAYMENT','TAX_PAYMENT','BANK_ADMIN_FEE','UNPAIRED_INTERNAL_TRANSFER')
               THEN 1 ELSE 0 END) AS exception,
          SUM(CASE WHEN match_proposed=0 AND human_confirmed=0 AND recon_status='UNIDENTIFIED' THEN 1 ELSE 0 END) AS unmatched
        FROM ggv_bank_transactions WHERE entity_id=?
        """,
        (ENTITY,),
    ).fetchone()
    return {
        "proposed": int(rows["proposed"] or 0),
        "matched": int(rows["matched"] or 0),
        "exception": int(rows["exception"] or 0),
        "unmatched": int(rows["unmatched"] or 0),
    }
