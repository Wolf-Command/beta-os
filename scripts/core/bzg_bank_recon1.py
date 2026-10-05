#!/usr/bin/env python3
"""BZG-BANK-RECON-1 — deterministic bank reconciliation states for imported BZG history.

Read-only browse surfaces; apply_recon_states updates recon_status on existing txns only.
No manufactured matches. staff_ready stays false.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from core import bzg_history_import1 as _hist

PACK = "BZG-BANK-RECON-1"
MIGRATION_ID = "bzg_bank_recon1_20261005"
ENTITY = _hist.ENTITY
SCHEMA = "bzg.bank.recon.v1"
TZ8 = timezone(timedelta(hours=8))

STATES = frozenset({"MATCHED", "POSSIBLE MATCH", "UNMATCHED", "EXCEPTION"})

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "payment_execute": False,
    "read_only": True,
    "entity_id": ENTITY,
    "auto_reconciled": False,
}

# Authorised BZG accounts — start months per shareholder README (not treated as missing).
ACCOUNTS = (
    {
        "account_label": "Mandiri-1610555335558",
        "bank_label": "MANDIRI",
        "start_month": "2026-03",
    },
    {
        "account_label": "BRI-19101003489305",
        "bank_label": "BRI",
        "start_month": "2026-04",
    },
    {
        "account_label": "BNI-2177177110",
        "bank_label": "BNI",
        "start_month": "2026-04",
    },
)

DATE_SLACK_DAYS = 7
AMOUNT_TOLERANCE = 1.0


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


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _iter_months(start: str, end: str) -> list[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    cur = date(sy, sm, 1)
    stop = date(ey, em, 1)
    out: list[str] = []
    while cur <= stop:
        out.append(_month_key(cur))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return out


def txn_amount(row: sqlite3.Row | dict[str, Any]) -> float:
    debit = float(row["debit"] or 0)
    credit = float(row["credit"] or 0)
    return debit if debit > 0 else credit


def _notes_payload(
    *,
    candidates: list[dict[str, Any]] | None = None,
    exception_reason: str | None = None,
    matched_kind: str | None = None,
    matched_label: str | None = None,
) -> str | None:
    payload: dict[str, Any] = {}
    if candidates:
        payload["candidates"] = candidates
    if exception_reason:
        payload["exception_reason"] = exception_reason
    if matched_kind:
        payload["matched_kind"] = matched_kind
    if matched_label:
        payload["matched_label"] = matched_label
    return json.dumps(payload, separators=(",", ":")) if payload else None


def _decode_notes(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"exception_reason": raw}


def import_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT import_id, bank_label, account_label, original_filename, txn_count,
               parse_status, period_start, period_end
        FROM bzg_bank_statement_imports
        WHERE entity_id=?
        ORDER BY account_label, original_filename
        """,
        (ENTITY,),
    ).fetchall()
    imports = [dict(r) for r in rows]
    parsed = [r for r in imports if int(r.get("txn_count") or 0) > 0]
    exceptions = [r for r in imports if str(r.get("parse_status") or "") == "EXCEPTION"]
    txn_total = conn.execute(
        "SELECT COUNT(*) FROM bzg_bank_transactions WHERE entity_id=?",
        (ENTITY,),
    ).fetchone()[0]
    return {
        "import_total": len(imports),
        "parsed_import_count": len(parsed),
        "parse_exception_import_count": len(exceptions),
        "transaction_count": int(txn_total),
        "imports": imports,
        "parsed_imports": parsed,
        "parse_exception_imports": exceptions,
    }


def _months_from_filename(fname: str) -> set[str]:
    months: set[str] = set()
    span = re.search(
        r"(20\d{2}-\d{2}-\d{2})_(20\d{2}-\d{2}-\d{2})",
        fname,
    )
    if span:
        start = _parse_date(span.group(1))
        end = _parse_date(span.group(2))
        if start and end:
            months.update(_iter_months(_month_key(start), _month_key(end)))
    compact = re.search(
        r"(20\d{2})(\d{2})(\d{2})_(20\d{2})(\d{2})(\d{2})",
        fname,
    )
    if compact:
        start = date(
            int(compact.group(1)),
            int(compact.group(2)),
            int(compact.group(3)),
        )
        end = date(
            int(compact.group(4)),
            int(compact.group(5)),
            int(compact.group(6)),
        )
        months.update(_iter_months(_month_key(start), _month_key(end)))
    bni = re.search(r"(20\d{2})-(\d{2})\.xls", fname, re.IGNORECASE)
    if bni:
        months.add(f"{bni.group(1)}-{bni.group(2)}")
    return months


def _covered_months(conn: sqlite3.Connection) -> dict[str, set[str]]:
    covered: dict[str, set[str]] = defaultdict(set)
    for row in conn.execute(
        """
        SELECT import_id, account_label, original_filename, txn_count, period_start, period_end
        FROM bzg_bank_statement_imports
        WHERE entity_id=?
        """,
        (ENTITY,),
    ):
        acct = str(row["account_label"] or "").strip()
        if not acct:
            continue
        months = _months_from_filename(str(row["original_filename"] or ""))
        if row["period_start"] and row["period_end"]:
            ps = _parse_date(row["period_start"])
            pe = _parse_date(row["period_end"])
            if ps and pe:
                months.update(_iter_months(_month_key(ps), _month_key(pe)))
        if int(row["txn_count"] or 0) > 0:
            for (m,) in conn.execute(
                """
                SELECT DISTINCT substr(txn_date, 1, 7) AS ym
                FROM bzg_bank_transactions
                WHERE import_id=? AND txn_date IS NOT NULL
                """,
                (row["import_id"],),
            ):
                if m:
                    months.add(str(m))
        covered[acct].update(months)
    return covered


def missing_statement_months(
    conn: sqlite3.Connection,
    *,
    as_of_month: str = "2026-10",
) -> list[dict[str, Any]]:
    covered = _covered_months(conn)
    missing: list[dict[str, Any]] = []
    for acct in ACCOUNTS:
        label = acct["account_label"]
        start = acct["start_month"]
        for month in _iter_months(start, as_of_month):
            if month not in covered.get(label, set()):
                missing.append(
                    {
                        "account_label": label,
                        "bank_label": acct["bank_label"],
                        "month": month,
                        "status": "NEEDS FROM MATT",
                        "message": f"No statement on file for {label} {month}",
                    }
                )
    missing.sort(key=lambda r: (r["account_label"], r["month"]))
    return missing


def _build_ledger_pools(conn: sqlite3.Connection) -> tuple[dict[tuple[date, float], list[dict[str, str]]], dict[float, list[dict[str, Any]]]]:
    exact: dict[tuple[date, float], list[dict[str, str]]] = defaultdict(list)
    by_amount: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in conn.execute(
        "SELECT bill_id, stated_total, nota_date FROM bzg_ops_supplier_bills"
    ):
        amount = float(row["stated_total"] or 0)
        d = _parse_date(row["nota_date"])
        ref = {"kind": "bill", "ref": str(row["bill_id"])}
        if d:
            exact[(d, amount)].append(ref)
        by_amount[amount].append({**ref, "date": d})
    for row in conn.execute(
        "SELECT ap_ready_id, bill_id, stated_total, nota_date FROM bzg_ops_ap_ready"
    ):
        amount = float(row["stated_total"] or 0)
        d = _parse_date(row["nota_date"])
        ref = {"kind": "ap", "ref": str(row["ap_ready_id"]), "bill_id": str(row["bill_id"])}
        if d:
            exact[(d, amount)].append(ref)
        by_amount[amount].append({**ref, "date": d})
    for row in conn.execute(
        """
        SELECT movement_id, amount, business_date
        FROM bzg_ops_petty_movements
        WHERE source_system=?
        """,
        (_hist.SOURCE_SYSTEM,),
    ):
        amount = float(row["amount"] or 0)
        d = _parse_date(row["business_date"])
        ref = {"kind": "petty", "ref": str(row["movement_id"])}
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
    for (_d, _a), group in grouped.items():
        debits = [g for g in group if float(g["debit"] or 0) > 0]
        credits = [g for g in group if float(g["credit"] or 0) > 0]
        if len(debits) != 1 or len(credits) != 1:
            continue
        if str(debits[0]["bank_account"]) == str(credits[0]["bank_account"]):
            continue
        for side, other in ((debits[0], credits[0]), (credits[0], debits[0])):
            matched[str(side["txn_id"])] = {
                "status": "MATCHED",
                "matched_ledger_source_id": str(other["txn_id"]),
                "match_confidence": "INTER_ACCOUNT_TRANSFER",
                "notes": _notes_payload(
                    matched_kind="known_transfer",
                    matched_label=f"{other['bank_account']}:{other['txn_id']}",
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
            "status": "MATCHED",
            "matched_ledger_source_id": hit["ref"],
            "match_confidence": f"EXACT_LEDGER_{hit['kind'].upper()}",
            "notes": _notes_payload(
                matched_kind=hit["kind"],
                matched_label=hit["ref"],
            ),
        }
    if len(exact_hits) > 1:
        return {
            "status": "POSSIBLE MATCH",
            "matched_ledger_source_id": None,
            "match_confidence": "MULTI_EXACT_AMOUNT_DATE",
            "notes": _notes_payload(candidates=exact_hits),
        }

    slack_candidates: list[dict[str, Any]] = []
    if txn_date:
        for hit in amount_pool.get(amount, []):
            hit_date = hit.get("date")
            if not hit_date:
                continue
            if abs((txn_date - hit_date).days) <= DATE_SLACK_DAYS:
                slack_candidates.append(
                    {
                        "kind": hit["kind"],
                        "ref": hit["ref"],
                        "date": hit_date.isoformat(),
                    }
                )
    if slack_candidates:
        return {
            "status": "POSSIBLE MATCH",
            "matched_ledger_source_id": None,
            "match_confidence": "AMOUNT_DATE_SLACK",
            "notes": _notes_payload(candidates=slack_candidates),
        }

    if "salary" in desc_lower:
        return {
            "status": "EXCEPTION",
            "matched_ledger_source_id": None,
            "match_confidence": "SALARY_PAYMENT",
            "notes": _notes_payload(exception_reason="SALARY_PAYMENT_NO_LEDGER"),
        }
    if "biaya adm" in desc_lower or (float(row["debit"] or 0) > 0 and abs(amount - 1500.0) < AMOUNT_TOLERANCE):
        return {
            "status": "EXCEPTION",
            "matched_ledger_source_id": None,
            "match_confidence": "BANK_ADMIN_FEE",
            "notes": _notes_payload(exception_reason="BANK_ADMIN_FEE"),
        }
    if "inhouse" in desc_lower:
        return {
            "status": "EXCEPTION",
            "matched_ledger_source_id": None,
            "match_confidence": "UNPAIRED_INTERNAL_TRANSFER",
            "notes": _notes_payload(exception_reason="UNPAIRED_INTERNAL_TRANSFER"),
        }

    return {
        "status": "UNMATCHED",
        "matched_ledger_source_id": None,
        "match_confidence": None,
        "notes": None,
    }


def apply_recon_states(
    conn: sqlite3.Connection,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    txns = conn.execute(
        "SELECT * FROM bzg_bank_transactions WHERE entity_id=? ORDER BY txn_id",
        (ENTITY,),
    ).fetchall()
    exact_pool, amount_pool = _build_ledger_pools(conn)
    transfer_matches = _find_transfer_pairs(txns)
    counts: dict[str, int] = {s: 0 for s in STATES}
    matched_ids: list[str] = []
    for row in txns:
        result = classify_transaction(
            row,
            transfer_matches=transfer_matches,
            exact_pool=exact_pool,
            amount_pool=amount_pool,
        )
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
        if status == "MATCHED":
            matched_ids.append(str(row["txn_id"]))
        conn.execute(
            """
            UPDATE bzg_bank_transactions
            SET recon_status=?, matched_ledger_source_id=?, match_confidence=?, notes=?
            WHERE txn_id=?
            """,
            (
                status,
                result.get("matched_ledger_source_id"),
                result.get("match_confidence"),
                result.get("notes"),
                row["txn_id"],
            ),
        )
    if commit:
        conn.commit()
    return public(
        ok=True,
        schema=SCHEMA,
        applied_at=now_iso(),
        transaction_count=len(txns),
        state_counts=counts,
        matched_txn_ids=sorted(matched_ids),
        transfer_pair_count=len(transfer_matches) // 2,
    )


def state_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT recon_status, COUNT(*) AS n
        FROM bzg_bank_transactions
        WHERE entity_id=?
        GROUP BY recon_status
        """,
        (ENTITY,),
    ).fetchall()
    return {str(r["recon_status"]): int(r["n"]) for r in rows}


def recon_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    stats = import_stats(conn)
    counts = state_counts(conn)
    missing = missing_statement_months(conn)
    txn_total = stats["transaction_count"]
    state_sum = sum(counts.values())
    return public(
        ok=True,
        schema=SCHEMA,
        import_stats=stats,
        state_counts=counts,
        state_sum=state_sum,
        transaction_count=txn_total,
        counts_match_transactions=state_sum == txn_total,
        missing_statement_months=missing,
        missing_statement_month_count=len(missing),
        parsed_import_count=stats["parsed_import_count"],
        covered_months_span="2026-03..2026-08",
    )


def matched_snapshot(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT txn_id, recon_status, matched_ledger_source_id, match_confidence, notes
        FROM bzg_bank_transactions
        WHERE entity_id=? AND recon_status='MATCHED'
        ORDER BY txn_id
        """,
        (ENTITY,),
    ).fetchall()
    return [dict(r) for r in rows]


def enrich_transaction_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    meta = _decode_notes(out.get("notes"))
    out["match_candidates"] = meta.get("candidates") or []
    out["exception_reason"] = meta.get("exception_reason")
    out["matched_kind"] = meta.get("matched_kind")
    out["matched_label"] = meta.get("matched_label")
    out["proposed_not_confirmed"] = out.get("recon_status") == "POSSIBLE MATCH"
    return out
