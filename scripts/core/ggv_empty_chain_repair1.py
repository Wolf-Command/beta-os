#!/usr/bin/env python3
"""GGV-EMPTY-CHAIN-REPAIR — import money.sqlite rows into Beta catalog GGV tables.

Read-only source: wolf-system ggv-finance money.sqlite.
Preserves source ids and amounts. Idempotent on invoice_id / nota_id.
Does not move money, write bank rows, or call Xero. staff_ready stays false.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import ggv_finance_invoice as inv
from core import ggv_finance_nota as fin

BETA_ROOT = Path(__file__).resolve().parents[2]
LIVE_CATALOG = BETA_ROOT / "catalog" / "content_library.sqlite"
SOURCE_DB = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/ggv-finance/money.sqlite"
)
PACK = "GGV-EMPTY-CHAIN-REPAIR"
MIGRATION_ID = "ggv_empty_chain_repair_20261004"
IMPORT_ACTOR = "PERS-MATT"
TZ8 = timezone(timedelta(hours=8))
ROUNDING_JSON = json.dumps(inv.ROUNDING)

INVOICE_STATUS_MAP: dict[str, str] = {
    "DRAFT": "DRAFT",
    "ISSUED": "ISSUED",
    "AUTHORISED": "ISSUED",
    "PAID": "PAID_CLAIMED",
    "REPORTED_PAID": "PAID_CLAIMED",
    "VOIDED": "VOID",
    "DELETED": "VOID",
}

NOTA_WORKFLOW_MAP: dict[str, str] = {
    "learned": "needs_review",
    "needs_review": "needs_review",
    "ready": "ready",
    "waiting_approval": "waiting_approval",
    "approved": "approved",
    "paid_claimed": "paid_claimed",
    "payment_verified": "payment_verified",
}

BILL_TARGET_TABLES = ("ggv_bills", "fin_bills", "ggv_ap_bills")


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def source_counts(source_conn: sqlite3.Connection) -> dict[str, int | None]:
    tables = ("sales_invoice", "bill", "ggv_nota", "bank_txn", "contact")
    out: dict[str, int | None] = {}
    for name in tables:
        if not _table(source_conn, name):
            out[name] = None
            continue
        out[name] = int(source_conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
    return out


def source_invoice_status_split(source_conn: sqlite3.Connection) -> dict[str, int]:
    rows = source_conn.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(status), ''), 'UNKNOWN') AS status, COUNT(*) AS n
        FROM sales_invoice
        GROUP BY COALESCE(NULLIF(TRIM(status), ''), 'UNKNOWN')
        ORDER BY status
        """
    ).fetchall()
    return {str(row["status"]): int(row["n"]) for row in rows}


def target_counts(target_conn: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for name in ("ggv_invoices", "ggv_bills", "ggv_notas", "ggv_vendors", "fin_counterparties"):
        if not _table(target_conn, name):
            out[name] = 0
            continue
        out[name] = int(target_conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
    return out


def _amount_parts(amount: str | None, currency: str | None) -> tuple[str, str, str, list[dict[str, str]]]:
    cur = (currency or "IDR").strip().upper() or "IDR"
    raw = (amount or "0").strip() or "0"
    try:
        value = str(int(float(raw)))
    except ValueError:
        value = "0"
    line = {
        "description": "Imported from money.sqlite (source amount preserved)",
        "qty": "1",
        "unit_price": value,
        "tax_rate": "0",
    }
    return value, "0", value, [line]


def _invoice_notes(row: sqlite3.Row, mapped_status: str) -> str | None:
    parts: list[str] = []
    if row["notes"]:
        parts.append(str(row["notes"]))
    source_status = str(row["status"] or "").strip()
    if source_status and source_status.upper() != mapped_status:
        parts.append(f"source_status={source_status}")
    if row["source"]:
        parts.append(f"source={row['source']}")
    return "; ".join(parts) if parts else None


def _ensure_customer(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    contact_id: str | None,
    contact_name: str | None,
    ts: str,
) -> str:
    cid = (contact_id or "").strip()
    name = (contact_name or "").strip()
    if cid:
        existing = target.execute(
            "SELECT counterparty_id FROM fin_counterparties WHERE counterparty_id=?",
            (cid,),
        ).fetchone()
        if existing is not None:
            return cid
        if _table(source, "contact"):
            contact = source.execute("SELECT * FROM contact WHERE id=?", (cid,)).fetchone()
            if contact is not None and contact["name"]:
                name = str(contact["name"]).strip()
    if not name:
        name = f"Unknown customer ({cid or 'no-id'})"
    name_norm = fin.norm_name(name)
    hit = target.execute(
        """
        SELECT counterparty_id FROM fin_counterparties
        WHERE entity_id=? AND kind='customer' AND name_norm=?
        """,
        (fin.ENTITY_GGV, name_norm),
    ).fetchone()
    if hit is not None:
        return str(hit["counterparty_id"])
    counterparty_id = cid or fin._mint("CUST")
    target.execute(
        """
        INSERT INTO fin_counterparties (
          counterparty_id, entity_id, kind, legal_name, trading_name, tax_id, company_id,
          billing_address, contact_name, email, phone, default_terms, notes,
          crm_customer_id, name_norm, tax_norm, status, created_by_person_id, created_at, updated_at
        ) VALUES (?, ?, 'customer', ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL, ?, NULL, 'ACTIVE', ?, ?, ?)
        """,
        (
            counterparty_id,
            fin.ENTITY_GGV,
            name,
            "imported from money.sqlite contact",
            name_norm,
            IMPORT_ACTOR,
            ts,
            ts,
        ),
    )
    return counterparty_id


def _ensure_vendor(target: sqlite3.Connection, supplier: str | None, ts: str) -> str | None:
    name = (supplier or "").strip()
    if not name:
        return None
    name_norm = fin.norm_name(name)
    hit = target.execute(
        """
        SELECT vendor_id FROM ggv_vendors
        WHERE entity_id=? AND name_norm=?
        """,
        (fin.ENTITY_GGV, name_norm),
    ).fetchone()
    if hit is not None:
        return str(hit["vendor_id"])
    vendor_id = fin._mint("VEND")
    target.execute(
        """
        INSERT INTO ggv_vendors (
          vendor_id, entity_id, display_name, name_norm, category, contact_name,
          phone, phone_norm, email, email_norm, tax_id, tax_norm, address, notes,
          status, created_by_person_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, 'ACTIVE', ?, ?, ?)
        """,
        (
            vendor_id,
            fin.ENTITY_GGV,
            name,
            name_norm,
            "imported from money.sqlite ggv_nota",
            IMPORT_ACTOR,
            ts,
            ts,
        ),
    )
    return vendor_id


def _advance_sequence(target: sqlite3.Connection, numbers: list[str]) -> int | None:
    best: int | None = None
    for number in numbers:
        match = re.fullmatch(r"(\d+)[A-Z]?", (number or "").strip().upper())
        if not match:
            continue
        series = int(match.group(1))
        best = series if best is None else max(best, series)
    if best is None:
        return None
    rendered = f"{best:03d}A"
    inv._advance_past_import(target, rendered, IMPORT_ACTOR)
    row = target.execute(
        "SELECT next_value FROM fin_invoice_sequences WHERE entity_id=?",
        (fin.ENTITY_GGV,),
    ).fetchone()
    return int(row[0]) if row is not None else None


def import_invoices(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    imported = 0
    skipped: dict[str, int] = {}
    mapped_status_counts: dict[str, int] = {}
    source_status_counts: dict[str, int] = {}
    imported_numbers: list[str] = []
    ts = now_iso()

    rows = source.execute(
        """
        SELECT *
        FROM sales_invoice
        WHERE COALESCE(entity, '') IN ('GGV', 'ENT-GGV')
        ORDER BY issued_on, created_at, id
        """
    ).fetchall()

    for row in rows:
        invoice_id = str(row["id"])
        source_status = str(row["status"] or "UNKNOWN").strip().upper() or "UNKNOWN"
        source_status_counts[source_status] = source_status_counts.get(source_status, 0) + 1

        if target.execute(
            "SELECT 1 FROM ggv_invoices WHERE invoice_id=?",
            (invoice_id,),
        ).fetchone():
            skipped["already_exists"] = skipped.get("already_exists", 0) + 1
            continue

        number = (row["number"] or "").strip() or None
        if number and target.execute(
            """
            SELECT 1 FROM ggv_invoices
            WHERE entity_id=? AND invoice_number=? AND invoice_id<>?
            """,
            (fin.ENTITY_GGV, number, invoice_id),
        ).fetchone():
            skipped["duplicate_number"] = skipped.get("duplicate_number", 0) + 1
            continue

        mapped = INVOICE_STATUS_MAP.get(source_status, "ISSUED")
        mapped_status_counts[mapped] = mapped_status_counts.get(mapped, 0) + 1
        customer_id = _ensure_customer(
            target,
            source,
            row["contact_id"],
            row["contact_name"],
            ts,
        )
        subtotal, tax_total, grand_total, lines = _amount_parts(row["amount"], row["currency"])
        invoice_date = (row["issued_on"] or row["created_at"] or ts)[:10]
        due_date = (row["due_on"] or "")[:10] or None
        terms = "Imported" if due_date else None
        issued_at = ts if mapped != "DRAFT" else None

        target.execute(
            """
            INSERT INTO ggv_invoices (
              invoice_id, entity_id, customer_id, invoice_number, invoice_date, due_date, terms,
              currency, notes, reference, payment_method, payment_reference, lines_json,
              subtotal, tax_total, grand_total, rounding_json, status, number_source,
              created_by_person_id, finalised_by_person_id, created_at, updated_at, issued_at,
              draft_email_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, 'imported', ?, ?, ?, ?, ?, NULL)
            """,
            (
                invoice_id,
                fin.ENTITY_GGV,
                customer_id,
                number,
                invoice_date,
                due_date,
                terms,
                (row["currency"] or "IDR").strip().upper() or "IDR",
                _invoice_notes(row, mapped),
                row["reference"],
                json.dumps(lines),
                subtotal,
                tax_total,
                grand_total,
                ROUNDING_JSON,
                mapped,
                IMPORT_ACTOR,
                IMPORT_ACTOR if mapped != "DRAFT" else None,
                (row["created_at"] or ts),
                ts,
                issued_at,
            ),
        )
        if number:
            imported_numbers.append(number)
        imported += 1

    next_value = _advance_sequence(target, imported_numbers)
    return {
        "source_rows": len(rows),
        "imported": imported,
        "skipped": skipped,
        "source_status_split": source_status_counts,
        "mapped_status_split": mapped_status_counts,
        "sequence_next_value": next_value,
    }


def import_notas(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    imported = 0
    skipped: dict[str, int] = {}
    source_status_counts: dict[str, int] = {}
    ts = now_iso()

    rows = source.execute("SELECT * FROM ggv_nota ORDER BY uploaded_at, id").fetchall()
    for row in rows:
        nota_id = str(row["id"])
        source_status = str(row["status"] or "unknown").strip().lower() or "unknown"
        source_status_counts[source_status] = source_status_counts.get(source_status, 0) + 1

        if target.execute("SELECT 1 FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone():
            skipped["already_exists"] = skipped.get("already_exists", 0) + 1
            continue

        workflow = NOTA_WORKFLOW_MAP.get(source_status, "needs_review")
        vendor_id = _ensure_vendor(target, row["supplier"], ts)
        amount = None
        if row["total_idr"] is not None:
            amount = str(int(row["total_idr"]))
        notes_parts = []
        if row["note"]:
            notes_parts.append(str(row["note"]))
        if row["source"]:
            notes_parts.append(f"source={row['source']}")
        if source_status not in NOTA_WORKFLOW_MAP:
            notes_parts.append(f"source_status={source_status}")

        target.execute(
            """
            INSERT INTO ggv_notas (
              nota_id, entity_id, vendor_id, invoice_no, nota_date, currency, amount, tax,
              category, items_json, notes, workflow_state, amount_confirmed, date_confirmed,
              vendor_confirmed, proposals_json, confidence_json, created_by_person_id,
              created_at, updated_at, submitted_at, approval_request_id,
              duplicate_of_nota_id, duplicate_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, NULL, NULL, NULL, NULL)
            """,
            (
                nota_id,
                fin.ENTITY_GGV,
                vendor_id,
                row["nota_number"],
                row["nota_date"],
                (row["currency"] or "IDR").strip().upper() or "IDR",
                amount,
                row["coa_name"] or row["company"],
                "; ".join(notes_parts) if notes_parts else None,
                workflow,
                1 if amount else 0,
                1 if row["nota_date"] else 0,
                1 if vendor_id else 0,
                IMPORT_ACTOR,
                row["uploaded_at"] or ts,
                row["learned_at"] or row["uploaded_at"] or ts,
            ),
        )
        imported += 1

    return {
        "source_rows": len(rows),
        "imported": imported,
        "skipped": skipped,
        "source_status_split": source_status_counts,
    }


def import_bills(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    from core import ggv_bills_import1 as _bills

    _bills.ensure_schema(target)
    return _bills.import_bills(target, source, source_path=SOURCE_DB)


def run_import(
    target_db: Path,
    *,
    source_db: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    target_path = Path(target_db).resolve()
    source_path = Path(source_db or SOURCE_DB).resolve()
    fin.assert_catalog_writable(target_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"source missing: {source_path}")

    source = _ro(source_path)
    target = sqlite3.connect(str(target_path), timeout=60)
    target.row_factory = sqlite3.Row
    try:
        before = target_counts(target)
        src_counts = source_counts(source)
        invoice_status_split = source_invoice_status_split(source)

        fin.ensure_schema(target)
        inv.ensure_schema(target)

        if dry_run:
            return {
                "pack": PACK,
                "dry_run": True,
                "source_db": str(source_path),
                "target_db": str(target_path),
                "source_counts": src_counts,
                "source_invoice_status_split": invoice_status_split,
                "target_counts_before": before,
            }

        invoices = import_invoices(target, source)
        notas = import_notas(target, source)
        bills = import_bills(target, source)
        target.commit()

        after = target_counts(target)
        return {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": now_iso(),
            "source_db": str(source_path),
            "target_db": str(target_path),
            "source_counts": src_counts,
            "source_invoice_status_split": invoice_status_split,
            "target_counts_before": before,
            "target_counts_after": after,
            "invoices": invoices,
            "notas": notas,
            "bills": bills,
            "staff_ready": False,
            "human_commissioned": False,
        }
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()

def honesty_payload(result: dict[str, Any]) -> dict[str, Any]:
    return fin.public_payload(
        {
            "ok": True,
            "pack": PACK,
            "staff_ready": False,
            "human_commissioned": False,
            "proven": False,
            "ready": False,
            "commissioned": False,
            "import": result,
        }
    )
