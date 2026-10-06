#!/usr/bin/env python3
"""FC-RECON-QUEUES-1 — shared bank reconciliation work queues for AMG and BZG.

Propose-only until human confirms. Append-only audit. No journal posting.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from core import audit as _audit
from core import bzg_bank_recon1 as _bzg_recon

PACK = "FC-RECON-QUEUES-1"
TZ8 = timezone(timedelta(hours=8))

AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"

TABS = (
    {"id": "possible", "label": "Possible match"},
    {"id": "unmatched", "label": "Unmatched"},
    {"id": "exception", "label": "Exception"},
    {"id": "matched", "label": "Matched"},
)

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "auto_reconcile": False,
    "propose_only": True,
}

RULE_LABELS = {
    "internal_transfer": "Transfer between own accounts",
    "exact_nota": "Exact nota match",
    "exact_bill": "Exact bill match",
    "exact_upload": "Exact upload match",
    "multi_exact": "Multiple exact matches",
    "amount_date_slack": "Amount match within a week",
    "salary_payment": "Salary payment",
    "tax_payment": "Tax payment",
    "bank_admin_fee": "Bank admin fee",
    "unpaired_internal_transfer": "Unpaired internal transfer",
    "INTER_ACCOUNT_TRANSFER": "Transfer between accounts",
    "EXACT_LEDGER_BILL": "Supplier bill payment",
    "EXACT_LEDGER_AP": "Accounts payable payment",
    "EXACT_LEDGER_PAYMENT": "Recorded supplier payment",
    "EXACT_LEDGER_PETTY": "Petty cash movement",
    "MULTI_EXACT_AMOUNT_DATE": "Several exact matches",
    "AMOUNT_DATE_SLACK": "Amount match within a week",
    "SALARY_PAYMENT": "Salary payment",
    "BANK_ADMIN_FEE": "Bank admin fee",
    "UNPAIRED_INTERNAL_TRANSFER": "Unpaired internal transfer",
}


class ReconQueueError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def public(**extra: Any) -> dict[str, Any]:
    out = {**HONESTY}
    out.update(extra)
    out["staff_ready"] = False
    out["zayen_ready"] = False
    return out


def decode_notes(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"proposal_text": raw}


def proposal_text(row: dict[str, Any], *, entity: str) -> str:
    meta = decode_notes(row.get("notes"))
    if meta.get("proposal_text"):
        return str(meta["proposal_text"])
    rule = meta.get("proposal_rule") or row.get("match_confidence") or ""
    if rule in RULE_LABELS:
        return RULE_LABELS[rule]
    if meta.get("matched_label"):
        return f"Suggested link: {meta['matched_label']}"
    if meta.get("exception_reason"):
        key = str(meta["exception_reason"])
        return RULE_LABELS.get(key, key.replace("_", " ").title())
    if entity == BZG_ENTITY:
        status = str(row.get("recon_status") or "")
        if status == "POSSIBLE MATCH":
            cands = meta.get("candidates") or []
            if cands:
                return f"{len(cands)} possible ledger match{'es' if len(cands) != 1 else ''}"
            return "Possible ledger match — review before confirming"
        if status == "EXCEPTION":
            return RULE_LABELS.get(str(row.get("match_confidence") or ""), "Needs exception note")
        if status == "MATCHED":
            return "Matched to ledger"
        return "No proposal yet"
    if row.get("match_proposed"):
        return "Proposed match — confirm or reject"
    return "Unmatched — no proposal"


def _proposal_by(row: dict[str, Any]) -> str | None:
    meta = decode_notes(row.get("notes"))
    return str(meta.get("proposal_by") or "").strip() or None


def ensure_bzg_queue_schema(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bzg_bank_transactions)").fetchall()}
    if "human_confirmed" not in cols:
        conn.execute(
            "ALTER TABLE bzg_bank_transactions ADD COLUMN human_confirmed INTEGER NOT NULL DEFAULT 0"
        )
    if "match_proposed" not in cols:
        conn.execute(
            "ALTER TABLE bzg_bank_transactions ADD COLUMN match_proposed INTEGER NOT NULL DEFAULT 0"
        )


def _entity_table(entity: str) -> str:
    if entity == AMG_ENTITY:
        return "ggv_bank_transactions"
    if entity == BZG_ENTITY:
        return "bzg_bank_transactions"
    raise ReconQueueError("Entity not supported.", code="forbidden", http_status=403)


def _tab_clause(entity: str, tab: str) -> tuple[str, list[Any]]:
    tab = (tab or "possible").strip().lower()
    if entity == AMG_ENTITY:
        if tab == "possible":
            return "entity_id=? AND match_proposed=1 AND human_confirmed=0", [AMG_ENTITY]
        if tab == "unmatched":
            return (
                "entity_id=? AND match_proposed=0 AND human_confirmed=0 AND recon_status='UNIDENTIFIED'",
                [AMG_ENTITY],
            )
        if tab == "exception":
            return (
                "entity_id=? AND human_confirmed=0 AND match_proposed=0 AND match_confidence IN "
                "('SALARY_PAYMENT','TAX_PAYMENT','BANK_ADMIN_FEE','UNPAIRED_INTERNAL_TRANSFER')",
                [AMG_ENTITY],
            )
        if tab == "matched":
            return "entity_id=? AND human_confirmed=1", [AMG_ENTITY]
    else:
        if tab == "possible":
            return "entity_id=? AND recon_status='POSSIBLE MATCH' AND human_confirmed=0", [BZG_ENTITY]
        if tab == "unmatched":
            return "entity_id=? AND recon_status='UNMATCHED'", [BZG_ENTITY]
        if tab == "exception":
            return "entity_id=? AND recon_status='EXCEPTION'", [BZG_ENTITY]
        if tab == "matched":
            return "entity_id=? AND (recon_status='MATCHED' OR human_confirmed=1)", [BZG_ENTITY]
    raise ReconQueueError(f"Unknown tab {tab!r}.", code="invalid_tab")


def _select_columns(entity: str) -> str:
    base = """
        txn_id, txn_date, description, debit, credit, bank_account,
        recon_status, match_confidence, match_proposed, human_confirmed, notes
    """
    if entity == AMG_ENTITY:
        return base.replace("notes", "matched_receipt_ref, notes")
    return base.replace("notes", "matched_ledger_source_id, notes")


def tab_counts(
    conn: sqlite3.Connection,
    *,
    entity: str,
    month: str | None = None,
) -> dict[str, Any]:
    if entity == BZG_ENTITY:
        ensure_bzg_queue_schema(conn)
    table = _entity_table(entity)
    month_clause = ""
    month_args: list[Any] = []
    if month:
        month_clause = " AND substr(txn_date,1,7)=?"
        month_args = [month.strip()]
    counts: dict[str, int] = {}
    for tab in TABS:
        clause, args = _tab_clause(entity, tab["id"])
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {clause}{month_clause}",
            (*args, *month_args),
        ).fetchone()
        counts[tab["id"]] = int(row[0] if row else 0)
    months_rows = conn.execute(
        f"""
        SELECT substr(txn_date,1,7) AS ym, COUNT(*) AS n
        FROM {table}
        WHERE entity_id=? AND txn_date IS NOT NULL AND length(substr(txn_date,1,7))=7
        GROUP BY ym ORDER BY ym DESC
        """,
        (entity,),
    ).fetchall()
    return {
        "tab_counts": counts,
        "months": [{"month": r["ym"], "count": int(r["n"])} for r in months_rows if r["ym"]],
    }


def list_queue(
    conn: sqlite3.Connection,
    *,
    entity: str,
    tab: str = "possible",
    month: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    if entity == BZG_ENTITY:
        ensure_bzg_queue_schema(conn)
    table = _entity_table(entity)
    clause, args = _tab_clause(entity, tab)
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))
    month_clause = ""
    month_args: list[Any] = []
    if month:
        month_clause = " AND substr(txn_date,1,7)=?"
        month_args = [month.strip()]
    total = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {clause}{month_clause}",
        (*args, *month_args),
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT {_select_columns(entity)}
        FROM {table}
        WHERE {clause}{month_clause}
        ORDER BY txn_date DESC, txn_id DESC
        LIMIT ? OFFSET ?
        """,
        (*args, *month_args, lim, off),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if entity == BZG_ENTITY:
            item = _bzg_recon.enrich_transaction_row(item)
        meta = decode_notes(item.get("notes"))
        item["proposal_text"] = proposal_text(item, entity=entity)
        item["proposal_rule"] = meta.get("proposal_rule") or item.get("match_confidence")
        item["amount"] = float(item["debit"] or 0) or float(item["credit"] or 0)
        item["direction"] = "out" if float(item["debit"] or 0) > 0 else "in"
        item.pop("notes", None)
        items.append(item)
    summary = tab_counts(conn, entity=entity, month=month)
    return public(
        ok=True,
        entity_id=entity,
        tab=tab,
        month=month,
        items=items,
        total=int(total),
        limit=lim,
        offset=off,
        tabs=TABS,
        **summary,
    )


def _audit_action(
    conn: sqlite3.Connection,
    *,
    entity: str,
    person_id: str,
    txn_id: str,
    action: str,
    note: str | None = None,
    rule: str | None = None,
) -> None:
    _audit.record_event(
        action=action,
        result="SUCCEEDED",
        source="fc_recon_queues1",
        actor_type="PERSON",
        actor_person_id=person_id,
        verified_person_id=person_id,
        entity_id=entity,
        resource_type="bank_transaction",
        resource_id=txn_id,
        metadata={"note": note, "proposal_rule": rule, "entity_id": entity},
        conn=conn,
        commit=False,
    )


def _load_row(conn: sqlite3.Connection, entity: str, txn_id: str) -> sqlite3.Row:
    table = _entity_table(entity)
    row = conn.execute(
        f"SELECT * FROM {table} WHERE txn_id=? AND entity_id=?",
        (txn_id.strip(), entity),
    ).fetchone()
    if not row:
        raise ReconQueueError("Bank line not found.", code="not_found", http_status=404)
    return row


def _deny_self_confirm(row: sqlite3.Row, person_id: str) -> None:
    creator = _proposal_by(dict(row))
    if creator and creator not in {"", "SYSTEM"} and creator == person_id:
        raise ReconQueueError(
            "You cannot confirm a match you created yourself.",
            code="segregation",
            http_status=403,
        )


def _txn_amount(row: sqlite3.Row | dict[str, Any]) -> float:
    debit = float(row["debit"] or 0)
    credit = float(row["credit"] or 0)
    return debit if debit > 0 else credit


def _amg_internal_transfer_pair(source: sqlite3.Row, other: sqlite3.Row) -> bool:
    source_debit = float(source["debit"] or 0)
    source_credit = float(source["credit"] or 0)
    other_debit = float(other["debit"] or 0)
    other_credit = float(other["credit"] or 0)
    if source_debit > 0 and other_credit <= 0:
        return False
    if source_credit > 0 and other_debit <= 0:
        return False
    if str(source["txn_date"])[:10] != str(other["txn_date"])[:10]:
        return False
    if abs(_txn_amount(source) - _txn_amount(other)) > 1.0:
        return False
    if str(source["bank_account"]) == str(other["bank_account"]):
        return False
    return True


def _amg_ref_exists(
    conn: sqlite3.Connection,
    ref: str,
    *,
    source_row: sqlite3.Row | None = None,
) -> bool:
    if conn.execute(
        "SELECT 1 FROM ggv_bills WHERE bill_id=? AND entity_id=?",
        (ref, AMG_ENTITY),
    ).fetchone():
        return True
    if conn.execute(
        "SELECT 1 FROM ggv_notas WHERE nota_id=? AND entity_id=?",
        (ref, AMG_ENTITY),
    ).fetchone():
        return True
    if conn.execute(
        "SELECT 1 FROM ggv_invoices WHERE invoice_id=? AND entity_id=?",
        (ref, AMG_ENTITY),
    ).fetchone():
        return True
    other = conn.execute(
        "SELECT * FROM ggv_bank_transactions WHERE txn_id=? AND entity_id=?",
        (ref, AMG_ENTITY),
    ).fetchone()
    if not other:
        return False
    if source_row is None:
        return True
    return _amg_internal_transfer_pair(source_row, other)


def confirm_match(
    conn: sqlite3.Connection,
    *,
    entity: str,
    txn_id: str,
    person_id: str,
    matched_ref: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    row = _load_row(conn, entity, txn_id)
    _deny_self_confirm(row, person_id)
    meta = decode_notes(row["notes"])
    rule = meta.get("proposal_rule") or row["match_confidence"]
    if entity == AMG_ENTITY:
        if not int(row["match_proposed"] or 0) and not int(row["human_confirmed"] or 0):
            raise ReconQueueError("No proposed match to confirm.", code="not_proposed")
        candidates = meta.get("candidates") or []
        candidate_refs = {str(c.get("ref")) for c in candidates if c.get("ref")}
        proposed_ref = str(row["matched_receipt_ref"] or "")
        body_ref = str(matched_ref or "").strip()
        if body_ref:
            ref = body_ref
            allowed = candidate_refs or ({proposed_ref} if proposed_ref else set())
            if allowed and ref not in allowed:
                raise ReconQueueError(
                    "That reference is not among the proposed candidates.",
                    code="invalid_ref",
                    http_status=400,
                )
        elif proposed_ref:
            ref = proposed_ref
        elif len(candidates) == 1:
            ref = str(candidates[0].get("ref") or "")
        else:
            raise ReconQueueError(
                "Pick which record to match — several candidates may share this amount and date.",
                code="ambiguous_match",
                http_status=409,
            )
        if not ref or not _amg_ref_exists(conn, ref, source_row=row):
            raise ReconQueueError(
                "That record does not exist for this company.",
                code="invalid_ref",
                http_status=400,
            )
        taken = conn.execute(
            """
            SELECT txn_id FROM ggv_bank_transactions
            WHERE entity_id=? AND human_confirmed=1 AND matched_receipt_ref=? AND txn_id<>?
            """,
            (AMG_ENTITY, ref, txn_id),
        ).fetchone()
        if taken:
            raise ReconQueueError(
                "That record is already matched to another bank line.",
                code="duplicate_match",
                http_status=409,
            )
        conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET human_confirmed=1, match_proposed=0, matched_receipt_ref=?, recon_status='NEEDS_REVIEW'
            WHERE txn_id=? AND entity_id=?
            """,
            (ref, txn_id, AMG_ENTITY),
        )
    else:
        ensure_bzg_queue_schema(conn)
        if str(row["recon_status"] or "") not in {"POSSIBLE MATCH", "MATCHED"}:
            raise ReconQueueError("Only possible matches can be confirmed.", code="not_proposed")
        ref = matched_ref or row["matched_ledger_source_id"]
        if not ref:
            cands = meta.get("candidates") or []
            if len(cands) == 1:
                ref = cands[0].get("ref")
        conn.execute(
            """
            UPDATE bzg_bank_transactions
            SET human_confirmed=1, match_proposed=0, recon_status='MATCHED', matched_ledger_source_id=?
            WHERE txn_id=? AND entity_id=?
            """,
            (ref, txn_id, BZG_ENTITY),
        )
    _audit_action(conn, entity=entity, person_id=person_id, txn_id=txn_id, action="bank_recon.confirm", rule=rule)
    payment_verified = None
    if entity == BZG_ENTITY and ref:
        from core import bzg_payment_record as _pay_rec

        try:
            payment_verified = _pay_rec.verify_from_bank_match(
                conn,
                payment_record_id=str(ref),
                bank_txn_id=txn_id,
                person_id=person_id,
                commit=False,
            )
        except Exception:
            payment_verified = None
    if commit:
        conn.commit()
    out = public(ok=True, txn_id=txn_id, action="confirm", human_confirmed=True)
    if payment_verified:
        out["payment_verified"] = payment_verified
    return out


def reject_match(
    conn: sqlite3.Connection,
    *,
    entity: str,
    txn_id: str,
    person_id: str,
    reason: str,
    commit: bool = True,
) -> dict[str, Any]:
    reason = (reason or "").strip()
    if not reason:
        raise ReconQueueError("A reason is required to reject.", code="missing_reason")
    row = _load_row(conn, entity, txn_id)
    meta = decode_notes(row["notes"])
    rule = meta.get("proposal_rule") or row["match_confidence"]
    if entity == AMG_ENTITY:
        conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET match_proposed=0, matched_receipt_ref=NULL, match_confidence='UNMATCHED',
                recon_status='UNIDENTIFIED', notes=?
            WHERE txn_id=? AND entity_id=? AND human_confirmed=0
            """,
            (
                json.dumps(
                    {"reject_reason": reason, "proposal_by": meta.get("proposal_by")},
                    separators=(",", ":"),
                ),
                txn_id,
                AMG_ENTITY,
            ),
        )
    else:
        ensure_bzg_queue_schema(conn)
        conn.execute(
            """
            UPDATE bzg_bank_transactions
            SET recon_status='UNMATCHED', match_proposed=0, human_confirmed=0,
                matched_ledger_source_id=NULL, match_confidence=NULL, notes=?
            WHERE txn_id=? AND entity_id=?
            """,
            (
                json.dumps({"reject_reason": reason}, separators=(",", ":")),
                txn_id,
                BZG_ENTITY,
            ),
        )
    _audit_action(
        conn,
        entity=entity,
        person_id=person_id,
        txn_id=txn_id,
        action="bank_recon.reject",
        note=reason,
        rule=rule,
    )
    if commit:
        conn.commit()
    return public(ok=True, txn_id=txn_id, action="reject")


def mark_exception(
    conn: sqlite3.Connection,
    *,
    entity: str,
    txn_id: str,
    person_id: str,
    note: str,
    commit: bool = True,
) -> dict[str, Any]:
    note = (note or "").strip()
    if not note:
        raise ReconQueueError("A note is required to mark exception.", code="missing_note")
    _load_row(conn, entity, txn_id)
    payload = json.dumps({"exception_note": note, "marked_by": person_id}, separators=(",", ":"))
    if entity == AMG_ENTITY:
        conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET match_proposed=0, recon_status='NEEDS_REVIEW', notes=?
            WHERE txn_id=? AND entity_id=? AND human_confirmed=0
            """,
            (payload, txn_id, AMG_ENTITY),
        )
    else:
        ensure_bzg_queue_schema(conn)
        conn.execute(
            """
            UPDATE bzg_bank_transactions
            SET recon_status='EXCEPTION', match_proposed=0, notes=?
            WHERE txn_id=? AND entity_id=?
            """,
            (payload, txn_id, BZG_ENTITY),
        )
    _audit_action(
        conn,
        entity=entity,
        person_id=person_id,
        txn_id=txn_id,
        action="bank_recon.exception",
        note=note,
    )
    if commit:
        conn.commit()
    return public(ok=True, txn_id=txn_id, action="exception")


def bulk_confirm(
    conn: sqlite3.Connection,
    *,
    entity: str,
    person_id: str,
    txn_ids: list[str],
    rule: str,
    commit: bool = True,
) -> dict[str, Any]:
    rule = (rule or "").strip()
    if not rule:
        raise ReconQueueError("rule is required for bulk confirm.", code="missing_rule")
    ids = [i.strip() for i in txn_ids if i and i.strip()]
    if len(ids) < 2:
        raise ReconQueueError("Select at least two rows in the same rule group.", code="too_few")
    confirmed: list[str] = []
    for txn_id in ids:
        row = _load_row(conn, entity, txn_id)
        meta = decode_notes(row["notes"])
        row_rule = meta.get("proposal_rule") or row["match_confidence"]
        if str(row_rule or "") != rule:
            raise ReconQueueError(
                f"All selected rows must share rule {rule!r}.",
                code="rule_mismatch",
            )
        confirm_match(conn, entity=entity, txn_id=txn_id, person_id=person_id, commit=False)
        confirmed.append(txn_id)
    _audit_action(
        conn,
        entity=entity,
        person_id=person_id,
        txn_id=",".join(confirmed[:5]),
        action="bank_recon.bulk_confirm",
        note=f"{len(confirmed)} rows",
        rule=rule,
    )
    if commit:
        conn.commit()
    return public(ok=True, confirmed_count=len(confirmed), rule=rule)
