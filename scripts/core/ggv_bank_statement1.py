#!/usr/bin/env python3
"""GGV bank statement file import — original kept + normalised txns.

Decision served: Finance Control Repair 2026-10-03 Part B (extend) +
2026-08-02 bank statement / delayed FILE_IMPORT_ONLY truth (no live bank feed).

Reuses Indonesian CSV shapes from wolf-system bzg_bank_ingest parsers (copied
minimal parsers — no second receipt pipeline, no Xero, no money movement).
Matching proposes only; weak matches never auto-reconcile.
Entity scope: ENT-GGV only. staff_ready stays false.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import finance_core_entity as _fce
from core import ggv_finance_nota as _nota
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ORIGINALS_DIR = BETA_ROOT / "state" / "ggv-bank-statements" / "originals"
ENTITY_GGV = "ENT-GGV"


def _eid() -> str:
    return _fce.active_entity()


def _originals_dir() -> Path:
    rel = Path(str(_fce.entity_config(_eid())["bank_originals"]))
    return BETA_ROOT / rel

HONESTY = {
    "staff_ready": False,
    "eng_proved": False,
    "proven": False,
    "file_import_only": True,
    "live_bank_feed": False,
    "auto_reconcile": False,
    "weak_match_never_auto": True,
    "money_movement": False,
    "xero": False,
    "entity_id": ENTITY_GGV,
    "amg_bzg_isolated": True,
}

DATE_SLACK_DAYS = 7
AMOUNT_TOLERANCE = 1.0
MANUAL_AMOUNT_TOLERANCE = 50000.0  # wider band for manual search (e.g. PPh 23 net)

BILL_MATCH_STATUSES = ("AUTHORISED", "PAID", "SUBMITTED")
BILL_EXCLUDED_STATUSES = frozenset({"DRAFT", "DELETED", "VOID", "VOIDED"})
INVOICE_MATCH_STATUSES = frozenset({"ISSUED", "PAID_CLAIMED", "PAYMENT_VERIFIED", "PART_PAID"})

MATCH_LABELS = {
    "MATCHED": "Matched",
    "PROPOSE MATCH": "Possible match",
    "POSSIBLE MATCH": "Possible match",
    "HUMAN REVIEW": "Possible match",
    "UNMATCHED": "Unmatched",
    "UNIDENTIFIED": "Unmatched",
    "NEEDS_REVIEW": "Possible match",
    "NEEDS_RECEIPT": "Unmatched",
    "EXCEPTION": "Exception",
}

EVIDENCE_STATUS_LABELS = {
    "ORIGINAL_KEPT": "Original kept",
    "PARTIAL_PDF_EXTRACTION": "Partial PDF — original kept",
    "PARSE FAILED — ORIGINAL KEPT": "Parse failed — original kept",
    "SCAN_NOT_E_STATEMENT": "Scanned statement — original kept",
}

RECON_STATUS_LABELS = {
    "UNRECONCILED": "Not reconciled yet",
    "MATCHED": "Matched",
    "NEEDS_REVIEW": "Needs your review",
    "NEEDS_RECEIPT": "Missing receipt",
    "UNIDENTIFIED": "Unmatched",
    "EXCEPTION": "Exception",
}


class GgvBankStatementError(ValueError):
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _num(s: Any) -> float:
    val, err = _parse_amount(s)
    if err:
        return 0.0
    return float(val or 0)


def _parse_amount(s: Any) -> tuple[float | None, str | None]:
    """Parse monetary amount with explicit IDR/locale rules. Returns (value, error_code)."""
    raw = str(s or "").strip()
    if not raw:
        return 0.0, None
    negative = raw.startswith("-") or raw.startswith("(")
    cleaned = raw.lstrip("-(").rstrip(")").strip()
    if not cleaned:
        return None, "empty_amount"
    # Comma thousands integer: 1,234 or 1,234,567
    if re.match(r"^[\d,]+$", cleaned) and "," in cleaned:
        parts = cleaned.split(",")
        if (
            len(parts) > 1
            and all(len(p) == 3 and p.isdigit() for p in parts[1:])
            and parts[0].isdigit()
            and len(parts[0]) <= 3
        ):
            try:
                val = float(cleaned.replace(",", ""))
                return (-val if negative else val), None
            except ValueError:
                return None, "invalid_amount"
    # Dot thousands integer: 1.234, 12.000, 500.000, 1.234.567
    if re.match(r"^\d{1,3}(\.\d{3})+$", cleaned):
        try:
            val = float(cleaned.replace(".", ""))
            return (-val if negative else val), None
        except ValueError:
            return None, "invalid_amount"
    # European decimal: 1.234,56
    if re.match(r"^[\d.]+,\d+$", cleaned):
        try:
            val = float(cleaned.replace(".", "").replace(",", "."))
            return (-val if negative else val), None
        except ValueError:
            return None, "invalid_amount"
    # US decimal with comma thousands: 1,234.56
    if re.match(r"^[\d,]+\.\d+$", cleaned) and "," in cleaned:
        try:
            val = float(cleaned.replace(",", ""))
            return (-val if negative else val), None
        except ValueError:
            return None, "invalid_amount"
    # Plain bank decimal (Mandiri/Livin exports): 500000.00
    if re.match(r"^\d+\.\d{1,2}$", cleaned):
        try:
            val = float(cleaned)
            return (-val if negative else val), None
        except ValueError:
            return None, "invalid_amount"
    # Plain integer
    if re.match(r"^\d+$", cleaned):
        try:
            val = float(cleaned)
            return (-val if negative else val), None
        except ValueError:
            return None, "invalid_amount"
    if "." in cleaned or "," in cleaned:
        return None, "ambiguous_amount"
    return None, "invalid_amount"


def _valid_iso_date(s: str | None) -> bool:
    if not s or len(s) < 10:
        return False
    try:
        datetime.strptime(s[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def ensure_schema(conn: sqlite3.Connection, *, run_backfill: bool = True) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ggv_bank_statement_imports (
          import_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          bank_label TEXT NOT NULL,
          account_label TEXT NULL,
          original_filename TEXT NOT NULL,
          original_path TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          uploaded_by_person_id TEXT NOT NULL,
          uploaded_at TEXT NOT NULL,
          period_start TEXT NULL,
          period_end TEXT NULL,
          txn_count INTEGER NOT NULL DEFAULT 0,
          parse_status TEXT NOT NULL,
          parse_notes TEXT NULL,
          UNIQUE (entity_id, content_sha256)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ggv_bank_transactions (
          txn_id TEXT PRIMARY KEY,
          import_id TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          txn_date TEXT NULL,
          value_date TEXT NULL,
          description TEXT NULL,
          reference TEXT NULL,
          debit REAL NOT NULL DEFAULT 0,
          credit REAL NOT NULL DEFAULT 0,
          running_balance REAL NULL,
          bank_account TEXT NULL,
          raw_json TEXT NULL,
          recon_status TEXT NOT NULL DEFAULT 'UNIDENTIFIED',
          matched_receipt_ref TEXT NULL,
          match_confidence TEXT NULL,
          match_proposed INTEGER NOT NULL DEFAULT 0,
          human_confirmed INTEGER NOT NULL DEFAULT 0,
          notes TEXT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY (import_id) REFERENCES ggv_bank_statement_imports(import_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ggv_bank_txn_entity_date
          ON ggv_bank_transactions(entity_id, txn_date)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ggv_finance_deploy_flags (
          flag_key TEXT PRIMARY KEY,
          done_at TEXT NOT NULL,
          detail_json TEXT NULL
        )
        """
    )
    # Backfill runs once via scripts/migrations/migrate_ggv_bank_recon_backfill_20261006.py — not on page load.


def _assert_ggv_finance(person_id: str, conn: sqlite3.Connection) -> None:
    eid = _eid()
    ctx = {"entity_id": eid}
    if eid == "ENT-AMG":
        if _rbac.can(person_id, "finance.nota.read", ctx, conn=conn) or _rbac.can(
            person_id, "atrium.board.read", ctx, conn=conn
        ):
            return
        raise GgvBankStatementError(
            "AMG finance denied for this person (entity scope).",
            code="forbidden",
            http_status=403,
            details={"entity_id": eid},
        )
    _nota.require(person_id, "finance.nota.read", conn)
    # Extra entity-scope check — shared finance perm must not leak other entities.
    decision = _rbac.evaluate(person_id, "finance.nota.read", ctx, conn=conn)
    if not decision.get("allowed"):
        raise GgvBankStatementError(
            "GGV finance denied for this person (entity scope).",
            code="forbidden",
            http_status=403,
            details={"reason": decision.get("reason"), "entity_id": eid},
        )


def _parse_mandiri_rows(text: str) -> list[dict[str, Any]]:
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=";") if r and len(r) >= 8]
    if not rows or "AccountNo" not in (rows[0][0] or ""):
        return []
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    def pdate(s: str) -> str | None:
        m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", str(s))
        if not m:
            return None
        mon = months.get(m.group(2)[:3].lower())
        if not mon:
            return None
        return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"

    out: list[dict[str, Any]] = []
    for r in rows[1:]:
        if not str(r[0]).strip().isdigit():
            continue
        out.append(
            {
                "txn_date": pdate(r[2]),
                "value_date": pdate(r[2]),
                "description": f"{r[3]} {r[4]}".strip(),
                "reference": str(r[0]).strip(),
                "credit": _num(r[5]),
                "debit": _num(r[6]),
                "running_balance": _num(r[7]),
                "bank_account": "MANDIRI",
                "raw": {"cols": r[:8]},
            }
        )
    return out


def _parse_bri_rows(text: str) -> list[dict[str, Any]]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    idx = {h.strip(): i for i, h in enumerate(rows[0])}
    if "MUTASI_KREDIT" not in idx or "MUTASI_DEBET" not in idx:
        return []
    out: list[dict[str, Any]] = []
    for r in rows[1:]:
        if len(r) <= max(idx.values()):
            continue
        norek_i = idx.get("NOREK", 1)
        if not str(r[norek_i]).strip():
            continue
        tgl = str(r[idx.get("TGL_TRAN", 0)])[:10]
        desc_parts = []
        for key in ("KETERANGAN", "DESKRIPSI", "REMARK", "KET"):
            if key in idx and idx[key] < len(r):
                desc_parts.append(str(r[idx[key]]))
        out.append(
            {
                "txn_date": tgl or None,
                "value_date": tgl or None,
                "description": " ".join(desc_parts).strip() or None,
                "reference": str(r[norek_i]).strip(),
                "credit": _num(r[idx["MUTASI_KREDIT"]]),
                "debit": _num(r[idx["MUTASI_DEBET"]]),
                "running_balance": _num(r[idx["SALDO_AKHIR_MUTASI"]])
                if "SALDO_AKHIR_MUTASI" in idx
                else None,
                "bank_account": "BRI",
                "raw": {"cols": r},
            }
        )
    return out


_NON_TXN_RE = re.compile(
    r"^(total|saldo|balance|opening|closing|subtotal|grand total|summary)\s*$",
    re.I,
)


def _is_non_transaction(description: str, debit: float, credit: float) -> bool:
    desc = (description or "").strip()
    if not desc:
        return debit == 0 and credit == 0
    if debit != 0 or credit != 0:
        return False
    return bool(_NON_TXN_RE.match(desc))


def _parse_generic_csv(text: str) -> list[dict[str, Any]]:
    """Fallback: date, description, debit, credit [, balance] header row."""
    rows, _audit = _parse_generic_csv_audited(text)
    return rows


def _parse_generic_csv_audited(text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse generic CSV and return row-count audit (parsed + exceptions + non-transaction)."""
    audit: dict[str, Any] = {
        "source_rows": 0,
        "parsed": 0,
        "exceptions": [],
        "non_transaction": [],
    }
    sample = text.lstrip()[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    all_rows = list(csv.reader(io.StringIO(text), dialect=dialect))
    if not all_rows or not all_rows[0]:
        return [], audit
    header = [(f or "").strip() for f in all_rows[0]]
    fields = {(f.lower()): f for f in header if f}

    def pick(*names: str) -> str | None:
        for n in names:
            if n in fields:
                return fields[n]
        return None

    dcol = pick("date", "txn_date", "posting date", "tanggal", "tgl")
    desc = pick("description", "remarks", "keterangan", "narration", "memo")
    debit = pick("debit", "debet", "withdrawal", "mutasi_debet")
    credit = pick("credit", "kredit", "deposit", "mutasi_kredit")
    bal = pick("balance", "running_balance", "saldo")
    ref = pick("reference", "ref", "check", "norek")
    if not dcol or (not debit and not credit):
        return [], audit
    out: list[dict[str, Any]] = []
    seen: dict[tuple[Any, ...], int] = {}
    for line_no, cells in enumerate(all_rows[1:], start=2):
        audit["source_rows"] += 1
        if not cells or not any(str(c or "").strip() for c in cells):
            audit["exceptions"].append({"line": line_no, "reason": "blank_row", "text": ""})
            continue
        if len(cells) != len(header):
            audit["exceptions"].append(
                {
                    "line": line_no,
                    "reason": "column_count_mismatch",
                    "text": ",".join(str(c or "") for c in cells)[:120],
                    "expected": len(header),
                    "got": len(cells),
                }
            )
            continue
        row = {header[i]: cells[i] for i in range(len(header))}
        raw_date = str(row.get(dcol) or "").strip()
        description = (str(row.get(desc) or "").strip() if desc else "") or ""
        debit_raw = str(row.get(debit) or "").strip() if debit else ""
        credit_raw = str(row.get(credit) or "").strip() if credit else ""
        if debit and credit and not debit_raw and not credit_raw:
            audit["exceptions"].append(
                {
                    "line": line_no,
                    "reason": "missing_amount",
                    "text": description[:120] or raw_date[:40],
                }
            )
            continue
        debit_val, debit_err = _parse_amount(row.get(debit)) if debit else (0.0, None)
        credit_val, credit_err = _parse_amount(row.get(credit)) if credit else (0.0, None)
        debit_val = float(debit_val or 0)
        credit_val = float(credit_val or 0)
        if debit_err or credit_err:
            audit["exceptions"].append(
                {
                    "line": line_no,
                    "reason": "invalid_amount",
                    "text": description[:120] or raw_date[:40],
                }
            )
            continue
        if _is_non_transaction(description, debit_val, credit_val):
            audit["non_transaction"].append(
                {"line": line_no, "reason": "header_or_total", "text": description[:120]}
            )
            continue
        if not raw_date and debit_val == 0 and credit_val == 0:
            audit["exceptions"].append(
                {"line": line_no, "reason": "missing_date_and_amount", "text": description[:120]}
            )
            continue
        txn_date = None
        if re.match(r"\d{4}-\d{2}-\d{2}", raw_date):
            txn_date = raw_date[:10]
            if not _valid_iso_date(txn_date):
                audit["exceptions"].append(
                    {"line": line_no, "reason": "invalid_date", "text": raw_date[:40]}
                )
                continue
        else:
            m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw_date)
            if m:
                txn_date = f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
                if not _valid_iso_date(txn_date):
                    audit["exceptions"].append(
                        {"line": line_no, "reason": "invalid_date", "text": raw_date[:40]}
                    )
                    continue
        if not txn_date:
            if debit_val == 0 and credit_val == 0:
                audit["exceptions"].append(
                    {"line": line_no, "reason": "unparseable_row", "text": description[:120] or raw_date[:40]}
                )
            else:
                audit["exceptions"].append(
                    {"line": line_no, "reason": "invalid_date", "text": raw_date[:40] or description[:120]}
                )
            continue
        ref_val = (str(row.get(ref) or "").strip() if ref else "") or ""
        fp = (txn_date, round(debit_val, 2), round(credit_val, 2), description, ref_val)
        if fp in seen:
            audit["exceptions"].append(
                {"line": line_no, "reason": "duplicate_row", "text": description[:120], "first_line": seen[fp]}
            )
            continue
        seen[fp] = line_no
        bal_val, bal_err = _parse_amount(row.get(bal)) if bal else (None, None)
        out.append(
            {
                "txn_date": txn_date,
                "value_date": txn_date,
                "description": description or None,
                "reference": (str(row.get(ref) or "").strip() if ref else None) or None,
                "debit": debit_val,
                "credit": credit_val,
                "running_balance": float(bal_val) if bal_val is not None and not bal_err else None,
                "bank_account": "UNKNOWN",
                "raw": dict(row),
            }
        )
        audit["parsed"] += 1
    audit["reconciled"] = (
        int(audit["parsed"]) + len(audit["exceptions"]) + len(audit["non_transaction"])
    ) == int(audit["source_rows"])
    return out, audit


def parse_statement_bytes(data: bytes, filename: str) -> tuple[str, list[dict[str, Any]], str]:
    """Return (bank_label, normalised_rows, parse_notes). Delegates to finance_core_statements."""
    from core import finance_core_statements as _fcs

    try:
        meta, rows, notes = _fcs.parse_statement_bytes(data, filename)
    except _fcs.FinanceStatementError as exc:
        raise GgvBankStatementError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    bank = str(meta.get("bank_label") or "UNKNOWN")
    return bank, rows, notes


def import_statement(
    *,
    verified_person_id: str,
    filename: str,
    content: bytes,
    bank_label: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    from core import finance_core_statements as _fcs

    try:
        return _fcs.import_statement(
            verified_person_id=verified_person_id,
            filename=filename,
            content=content,
            bank_label=bank_label,
            conn=conn,
            commit=commit,
            entity_id=_eid(),
        )
    except _fcs.FinanceStatementError as exc:
        raise GgvBankStatementError(
            str(exc), code=exc.code, http_status=exc.http_status, details=exc.details
        ) from exc


def _parse_date_obj(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _dates_within(tdate: str, hdate: str, slack: int = DATE_SLACK_DAYS) -> bool:
    td = _parse_date_obj(tdate)
    hd = _parse_date_obj(hdate)
    if not td or not hd:
        return False
    return abs((td - hd).days) <= slack


def _txn_direction(debit: float, credit: float) -> str:
    if float(credit or 0) > 0:
        return "in"
    if float(debit or 0) > 0:
        return "out"
    return "none"


def _kind_allowed_for_direction(kind: str, direction: str) -> bool:
    if direction == "in":
        return kind == "invoice"
    if direction == "out":
        return kind in ("bill", "nota", "receipt")
    return False


def _bill_matchable(status: str | None) -> bool:
    return str(status or "").upper() not in ("DELETED", "VOID", "VOIDED")


def _invoice_matchable(status: str | None) -> bool:
    return str(status or "").upper() in INVOICE_MATCH_STATUSES


def _match_href(kind: str, ref: str) -> str:
    routes = {
        "bill": f"/ggv/finance/bills?open={ref}",
        "nota": f"/ggv/finance/notas?open={ref}",
        "invoice": f"/ggv/finance/invoices?open={ref}",
        "receipt": f"/ggv/finance/receipts?open={ref}",
    }
    return routes.get(kind, "")


def _apply_bill_payment(
    conn: sqlite3.Connection,
    bill_id: str,
    payment_amount: float,
    *,
    reverse: bool = False,
) -> None:
    row = conn.execute(
        "SELECT amount, amount_paid, amount_due FROM ggv_bills WHERE bill_id=? AND entity_id=?",
        (bill_id, _eid()),
    ).fetchone()
    if not row:
        return
    total = float(row["amount"] or 0)
    paid = float(row["amount_paid"] or 0)
    if reverse:
        paid = max(0.0, paid - payment_amount)
    else:
        paid = paid + payment_amount
    due = max(0.0, total - paid)
    conn.execute(
        """
        UPDATE ggv_bills SET amount_paid=?, amount_due=?
        WHERE bill_id=? AND entity_id=?
        """,
        (str(int(round(paid))), str(int(round(due))), bill_id, _eid()),
    )


def _receipt_amount_date(row: sqlite3.Row) -> tuple[float | None, str | None]:
    for blob in (row["human_confirmed_json"], row["extraction_json"]):
        if not blob:
            continue
        try:
            meta = json.loads(blob)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict):
            continue
        amt = meta.get("amount") or meta.get("total") or meta.get("idr")
        dt = meta.get("receipt_date") or meta.get("date") or meta.get("nota_date")
        try:
            amount = float(amt) if amt is not None else None
        except (TypeError, ValueError):
            amount = None
        if amount and amount > 0:
            return amount, (str(dt or "")[:10] or None)
    return None, None


def _candidate_amounts(h: dict[str, Any]) -> list[float]:
    amounts: list[float] = []
    base = h.get("amount")
    if base is not None:
        try:
            amounts.append(float(base))
        except (TypeError, ValueError):
            pass
    alt = h.get("net_amount")
    if alt is not None:
        try:
            amounts.append(float(alt))
        except (TypeError, ValueError):
            pass
    out: list[float] = []
    for val in amounts:
        if val > 0 and all(abs(val - seen) > 0.01 for seen in out):
            out.append(val)
    return out


def _display_label(h: dict[str, Any]) -> str:
    kind = str(h.get("kind") or "")
    party = h.get("party") or h.get("label") or ""
    number = h.get("number") or ""
    amt = h.get("amount")
    d = (h.get("date") or "")[:10]
    parts = [p for p in (party, number, d) if p]
    head = " · ".join(parts) if parts else str(h.get("ref") or kind)
    if amt is not None:
        try:
            head = f"{head} · Rp {int(round(float(amt))):,}".replace(",", ".")
        except (TypeError, ValueError):
            pass
    return head


def maybe_backfill_propose_matches(
    conn: sqlite3.Connection,
    *,
    entity_id: str = "ENT-GGV",
    commit: bool = True,
) -> dict[str, Any]:
    """One-time audited backfill: run propose_matches on every existing import."""
    if entity_id != "ENT-GGV":
        return {"ok": True, "skipped": True, "reason": "not_ggv"}
    row = conn.execute(
        "SELECT 1 FROM ggv_finance_deploy_flags WHERE flag_key=?",
        ("propose_matches_backfill_v1",),
    ).fetchone()
    if row:
        return {"ok": True, "skipped": True, "reason": "already_done"}
    imports = [
        str(r[0])
        for r in conn.execute(
            """
            SELECT import_id FROM ggv_bank_statement_imports
            WHERE entity_id=? AND COALESCE(is_test_fixture,0)=0
            ORDER BY uploaded_at
            """,
            (entity_id,),
        ).fetchall()
    ]
    totals = {"imports": len(imports), "proposed": 0}
    ensure_schema(conn, run_backfill=False)
    for import_id in imports:
        with _fce.entity_scope(entity_id):
            result = propose_matches(import_id, conn=conn, commit=False)
        totals["proposed"] += int(result.get("proposed_count") or 0)
    ts = _now()
    conn.execute(
        """
        INSERT INTO ggv_finance_deploy_flags (flag_key, done_at, detail_json)
        VALUES (?, ?, ?)
        """,
        ("propose_matches_backfill_v1", ts, json.dumps(totals, separators=(",", ":"))),
    )
    _audit.record_event(
        action="ggv.bank_recon.backfill_propose",
        result="SUCCEEDED",
        source="ggv_bank_statement1",
        actor_type="SYSTEM",
        entity_id=entity_id,
        resource_type="bank_statement_import",
        resource_id="*",
        metadata=totals,
        conn=conn,
        commit=False,
    )
    if commit:
        conn.commit()
    return {"ok": True, "backfill": totals}


def _load_match_candidates(c: sqlite3.Connection) -> list[dict[str, Any]]:
    """Collect bills, notas, invoices, and vault receipts for GGV reconciliation."""
    eid = _eid()
    hints: list[dict[str, Any]] = []
    if eid == "ENT-GGV" and c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ggv_receipt_accounting'"
    ).fetchone():
        for row in c.execute(
            """
            SELECT receipt_key, vault_filename, extraction_json, human_confirmed_json
            FROM ggv_receipt_accounting
            WHERE entity_id=?
            ORDER BY updated_at DESC
            LIMIT 500
            """,
            (eid,),
        ).fetchall():
            amount, rdate = _receipt_amount_date(row)
            if not amount:
                continue
            hints.append(
                {
                    "kind": "receipt",
                    "ref": row["receipt_key"],
                    "amount": amount,
                    "date": rdate,
                    "label": _display_label(
                        {
                            "kind": "receipt",
                            "party": row["vault_filename"],
                            "number": row["receipt_key"],
                            "date": rdate,
                            "amount": amount,
                        }
                    ),
                    "party": row["vault_filename"],
                    "number": row["receipt_key"],
                }
            )
    for row in c.execute(
        """
        SELECT bill_id, amount, issued_on, contact_name, bill_number, reference, status
        FROM ggv_bills WHERE entity_id=?
        """,
        (eid,),
    ).fetchall():
        if not _bill_matchable(row["status"]):
            continue
        try:
            amount = float(row["amount"] or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        hints.append(
            {
                "kind": "bill",
                "ref": row["bill_id"],
                "amount": amount,
                "date": (row["issued_on"] or "")[:10] or None,
                "label": _display_label(
                    {
                        "kind": "bill",
                        "party": row["contact_name"],
                        "number": row["bill_number"] or row["reference"],
                        "date": (row["issued_on"] or "")[:10],
                        "amount": amount,
                    }
                ),
                "party": row["contact_name"],
                "number": row["bill_number"] or row["reference"],
            }
        )
    for row in c.execute(
        """
        SELECT n.nota_id, n.amount, n.nota_date, n.invoice_no, v.display_name AS vendor_name
        FROM ggv_notas n
        LEFT JOIN ggv_vendors v ON v.vendor_id = n.vendor_id AND v.entity_id = n.entity_id
        WHERE n.entity_id=?
        """,
        (eid,),
    ).fetchall():
        try:
            amount = float(row["amount"] or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        hints.append(
            {
                "kind": "nota",
                "ref": row["nota_id"],
                "amount": amount,
                "date": (row["nota_date"] or "")[:10] or None,
                "label": _display_label(
                    {
                        "kind": "nota",
                        "party": row["vendor_name"],
                        "number": row["invoice_no"],
                        "date": (row["nota_date"] or "")[:10],
                        "amount": amount,
                    }
                ),
                "party": row["vendor_name"],
                "number": row["invoice_no"],
            }
        )
    inv_cols = {r[1] for r in c.execute("PRAGMA table_info(ggv_invoices)").fetchall()}
    withholding_col = "withholding_amount" if "withholding_amount" in inv_cols else None
    inv_sql = """
        SELECT i.invoice_id, i.grand_total, i.invoice_date, i.invoice_number,
               i.rounding_json, i.status, c.legal_name, c.trading_name
        """
    if withholding_col:
        inv_sql = inv_sql.replace("i.status", f"i.status, i.{withholding_col}")
    inv_sql += """
        FROM ggv_invoices i
        LEFT JOIN fin_counterparties c
          ON c.counterparty_id = i.customer_id AND c.entity_id = i.entity_id
        WHERE i.entity_id=?
    """
    for row in c.execute(inv_sql, (eid,)).fetchall():
        if not _invoice_matchable(row["status"]):
            continue
        try:
            amount = float(row["grand_total"] or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        net_amount = None
        withholding = None
        if withholding_col:
            withholding = row[withholding_col]
        try:
            rounding = json.loads(row["rounding_json"] or "{}")
            if withholding is None:
                withholding = rounding.get("withholding") or rounding.get("pph23")
            if withholding is not None:
                net_amount = amount - float(withholding)
        except (TypeError, ValueError, json.JSONDecodeError):
            net_amount = None
        customer = row["trading_name"] or row["legal_name"] or ""
        hints.append(
            {
                "kind": "invoice",
                "ref": row["invoice_id"],
                "amount": amount,
                "net_amount": net_amount,
                "date": (row["invoice_date"] or "")[:10] or None,
                "label": _display_label(
                    {
                        "kind": "invoice",
                        "party": customer,
                        "number": row["invoice_number"],
                        "date": (row["invoice_date"] or "")[:10],
                        "amount": amount,
                    }
                ),
                "party": customer,
                "number": row["invoice_number"],
            }
        )
    return hints


def _match_candidates_for_txn(
    amount: float,
    tdate: str,
    hints: list[dict[str, Any]],
    *,
    confirmed_refs: set[str],
    direction: str,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for h in hints:
        kind = str(h.get("kind") or "")
        if not _kind_allowed_for_direction(kind, direction):
            continue
        if not _candidate_amounts(h):
            continue
        if not any(abs(val - amount) <= AMOUNT_TOLERANCE for val in _candidate_amounts(h)):
            continue
        hdate = (h.get("date") or "")[:10]
        if not hdate:
            continue
        if tdate and not _dates_within(tdate, hdate):
            continue
        ref = str(h.get("ref") or "")
        if ref in confirmed_refs:
            continue
        hit = dict(h)
        hit["label"] = hit.get("label") or _display_label(hit)
        hits.append(hit)
    return hits


def _notes_payload(**extra: Any) -> str:
    return json.dumps(extra, separators=(",", ":"))


def propose_matches(
    import_id: str,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Propose amount+date matches to bills, notas, invoices, receipts. Never auto-reconcile."""
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c, run_backfill=False)
        if verified_person_id:
            _assert_ggv_finance(verified_person_id, c)
        hints = _load_match_candidates(c)
        confirmed_refs = {
            str(r[0])
            for r in c.execute(
                """
                SELECT matched_receipt_ref FROM ggv_bank_transactions
                WHERE entity_id=? AND human_confirmed=1 AND matched_receipt_ref IS NOT NULL
                """,
                (_eid(),),
            ).fetchall()
        }
        txns = c.execute(
            """
            SELECT txn_id, txn_date, debit, credit, description, recon_status
            FROM ggv_bank_transactions
            WHERE import_id=? AND entity_id=? AND human_confirmed=0
            """,
            (import_id, _eid()),
        ).fetchall()
        proposed = 0
        missing_evidence = 0
        for t in txns:
            credit = float(t["credit"] or 0)
            debit = float(t["debit"] or 0)
            amount = credit if credit > 0 else debit
            direction = _txn_direction(debit, credit)
            if amount <= 0 or direction == "none":
                continue
            tdate = (t["txn_date"] or "")[:10]
            hits = _match_candidates_for_txn(
                amount, tdate, hints, confirmed_refs=confirmed_refs, direction=direction
            )
            if len(hits) == 1:
                ref = hits[0]["ref"]
                c.execute(
                    """
                    UPDATE ggv_bank_transactions
                    SET recon_status='NEEDS_REVIEW', matched_receipt_ref=?,
                        match_confidence='PROPOSE MATCH', match_proposed=1,
                        notes=?
                    WHERE txn_id=?
                    """,
                    (
                        ref,
                        _notes_payload(
                            candidates=hits,
                            proposal_rule=f"possible_{hits[0]['kind']}",
                            proposal_text=f"Possible match to {hits[0].get('label') or hits[0]['kind']}",
                        ),
                        t["txn_id"],
                    ),
                )
                proposed += 1
            elif len(hits) > 1:
                c.execute(
                    """
                    UPDATE ggv_bank_transactions
                    SET recon_status='NEEDS_REVIEW', matched_receipt_ref=NULL,
                        match_confidence='PROPOSE MATCH', match_proposed=1,
                        notes=?
                    WHERE txn_id=?
                    """,
                    (
                        _notes_payload(
                            candidates=hits,
                            proposal_rule="multi_possible",
                            proposal_text="Several possible matches — pick one",
                        ),
                        t["txn_id"],
                    ),
                )
                proposed += 1
            else:
                c.execute(
                    """
                    UPDATE ggv_bank_transactions
                    SET recon_status='UNIDENTIFIED', match_confidence='UNMATCHED', match_proposed=0,
                        matched_receipt_ref=NULL, notes=NULL
                    WHERE txn_id=? AND human_confirmed=0 AND match_proposed=1
                    """,
                    (t["txn_id"],),
                )
                if str(t["recon_status"] or "").upper() in ("UNIDENTIFIED", "NEEDS_REVIEW"):
                    missing_evidence += 1
        if commit:
            c.commit()
        return {
            "ok": True,
            "import_id": import_id,
            "proposed_count": proposed,
            "missing_evidence_count": missing_evidence,
            "auto_reconciled": False,
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def list_imports(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    from core import finance_core_statements as _fcs

    try:
        lib = _fcs.list_library(
            verified_person_id=verified_person_id, conn=conn, entity_id=_eid()
        )
        imports = lib.get("statements") or []
        own = conn is None
        c = conn or _nota._open_ready()
        try:
            missing = c.execute(
                """
                SELECT COUNT(*) AS n FROM ggv_bank_transactions
                WHERE entity_id=? AND recon_status IN ('NEEDS_RECEIPT','UNIDENTIFIED')
                  AND import_id IN (
                    SELECT import_id FROM ggv_bank_statement_imports
                    WHERE entity_id=? AND COALESCE(is_test_fixture,0)=0
                  )
                """,
                (_eid(), _eid()),
            ).fetchone()
        finally:
            if own:
                c.close()
        return {
            "ok": True,
            "entity_id": _eid(),
            "imports": imports,
            "statements": imports,
            "count": len(imports),
            "missing_evidence_txns": int(missing["n"] if missing else 0),
            "completeness": lib.get("completeness"),
            **HONESTY,
        }
    except _fcs.FinanceStatementError as exc:
        raise GgvBankStatementError(
            str(exc), code=exc.code, http_status=exc.http_status, details=exc.details
        ) from exc


def _ref_kind(conn: sqlite3.Connection, ref: str) -> str | None:
    eid = _eid()
    if conn.execute(
        "SELECT 1 FROM ggv_bills WHERE bill_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone():
        return "bill"
    if conn.execute(
        "SELECT 1 FROM ggv_notas WHERE nota_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone():
        return "nota"
    if conn.execute(
        "SELECT 1 FROM ggv_invoices WHERE invoice_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone():
        return "invoice"
    if eid == "ENT-GGV" and conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ggv_receipt_accounting'"
    ).fetchone():
        if conn.execute(
            "SELECT 1 FROM ggv_receipt_accounting WHERE receipt_key=? AND entity_id=?",
            (ref, eid),
        ).fetchone():
            return "receipt"
    return None


def _direction_ok_for_ref(conn: sqlite3.Connection, ref: str, debit: float, credit: float) -> bool:
    kind = _ref_kind(conn, ref)
    if not kind:
        return False
    return _kind_allowed_for_direction(kind, _txn_direction(debit, credit))


def _ref_exists(conn: sqlite3.Connection, ref: str) -> bool:
    eid = _eid()
    bill = conn.execute(
        "SELECT status FROM ggv_bills WHERE bill_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone()
    if bill and _bill_matchable(bill["status"]):
        return True
    if conn.execute(
        "SELECT 1 FROM ggv_notas WHERE nota_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone():
        return True
    inv = conn.execute(
        "SELECT status FROM ggv_invoices WHERE invoice_id=? AND entity_id=?",
        (ref, eid),
    ).fetchone()
    if inv and _invoice_matchable(inv["status"]):
        return True
    if eid == "ENT-GGV" and conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ggv_receipt_accounting'"
    ).fetchone():
        if conn.execute(
            "SELECT 1 FROM ggv_receipt_accounting WHERE receipt_key=? AND entity_id=?",
            (ref, eid),
        ).fetchone():
            return True
    return False


def list_transactions(
    *,
    verified_person_id: str,
    import_id: str | None = None,
    recon_status: str | None = None,
    month: str | None = None,
    match_status: str | None = None,
    offset: int = 0,
    limit: int = 200,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c, run_backfill=False)
        _assert_ggv_finance(verified_person_id, c)
        lim = max(1, min(int(limit or 200), 500))
        off = max(0, int(offset or 0))
        sql = [
            """
            SELECT t.* FROM ggv_bank_transactions t
            JOIN ggv_bank_statement_imports i ON i.import_id = t.import_id
            WHERE t.entity_id=? AND COALESCE(i.is_test_fixture,0)=0
            """,
        ]
        args: list[Any] = [_eid()]
        if import_id:
            sql.append("AND t.import_id=?")
            args.append(import_id.strip())
        if recon_status:
            sql.append("AND t.recon_status=?")
            args.append(recon_status.strip().upper())
        if month:
            sql.append("AND substr(t.txn_date,1,7)=?")
            args.append(str(month).strip()[:7])
        ms = str(match_status or "").strip().upper()
        if ms == "MATCHED":
            sql.append("AND t.human_confirmed=1")
        elif ms in ("PROPOSE", "PROPOSED", "POSSIBLE"):
            sql.append("AND t.human_confirmed=0 AND t.match_proposed=1")
        elif ms == "UNMATCHED":
            sql.append("AND t.human_confirmed=0 AND t.match_proposed=0")
        count_sql = " ".join(sql).replace("SELECT t.*", "SELECT COUNT(*)")
        total_count = int(c.execute(count_sql, tuple(args)).fetchone()[0])
        sql.append("ORDER BY t.txn_date DESC, t.created_at DESC LIMIT ? OFFSET ?")
        args.extend([lim, off])
        rows = [dict(r) for r in c.execute(" ".join(sql), tuple(args)).fetchall()]
        label_by_ref = {str(h.get("ref")): h.get("label") for h in _load_match_candidates(c) if h.get("ref")}
        for r in rows:
            r.pop("raw_json", None)  # keep payload lean; original file is evidence
            credit = float(r.get("credit") or 0)
            debit = float(r.get("debit") or 0)
            r["money_in"] = credit if credit > 0 else 0
            r["money_out"] = debit if debit > 0 else 0
            notes_meta: dict[str, Any] = {}
            try:
                notes_meta = json.loads(r.get("notes") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                notes_meta = {}
            candidates = notes_meta.get("candidates") or []
            for cand in candidates:
                if isinstance(cand, dict) and not cand.get("label"):
                    cand["label"] = _display_label(cand)
            r["match_candidates"] = candidates
            r["proposal_text"] = notes_meta.get("proposal_text")
            if r.get("matched_receipt_ref"):
                ref_key = str(r["matched_receipt_ref"])
                r["matched_display"] = label_by_ref.get(ref_key) or notes_meta.get("matched_label") or ref_key
                kind = _ref_kind(c, ref_key)
                r["matched_kind"] = kind
                r["matched_href"] = _match_href(kind or "", ref_key) if kind else ""
            r["proposed_not_confirmed"] = bool(r.get("match_proposed")) and not bool(
                r.get("human_confirmed")
            )
            r["can_unmatch"] = bool(r.get("human_confirmed"))
            conf = str(r.get("match_confidence") or "").upper()
            status = str(r.get("recon_status") or "").upper()
            if int(r.get("human_confirmed") or 0):
                code = "MATCHED"
            elif status == "EXCEPTION":
                code = "EXCEPTION"
            elif conf == "PROPOSE MATCH" or (r.get("match_proposed") and not r.get("human_confirmed")):
                code = "PROPOSE MATCH"
            elif status == "NEEDS_REVIEW":
                code = "HUMAN REVIEW"
            else:
                # Canonical codes only — recon_status values like NEEDS_RECEIPT stay on the row.
                code = "UNMATCHED"
            r["match_code"] = code
            r["match_label"] = MATCH_LABELS.get(code, MATCH_LABELS["UNMATCHED"])
        return {
            "ok": True,
            "entity_id": _eid(),
            "transactions": rows,
            "count": len(rows),
            "total_count": total_count,
            "offset": off,
            "limit": lim,
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def confirm_match(
    *,
    verified_person_id: str,
    txn_id: str,
    body: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Human confirms a proposed bank match. Never auto-confirms."""
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c, run_backfill=False)
        _assert_ggv_finance(verified_person_id, c)
        row = c.execute(
            "SELECT * FROM ggv_bank_transactions WHERE txn_id=? AND entity_id=?",
            (txn_id.strip(), _eid()),
        ).fetchone()
        if not row:
            raise GgvBankStatementError("Bank line not found.", code="not_found", http_status=404)
        if int(row["human_confirmed"] or 0):
            raise GgvBankStatementError("Already matched.", code="already_matched", http_status=409)
        pay_amount = float(row["credit"] or 0) or float(row["debit"] or 0)
        body_ref = str((body or {}).get("matched_receipt_ref") or "").strip()
        manual = bool(body_ref) and not int(row["match_proposed"] or 0)
        if not int(row["match_proposed"] or 0) and not body_ref:
            raise GgvBankStatementError(
                "No proposed match to confirm — pick a record or run Find matches first.",
                code="not_proposed",
                http_status=409,
            )
        notes_meta: dict[str, Any] = {}
        try:
            notes_meta = json.loads(row["notes"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            notes_meta = {}
        candidates = notes_meta.get("candidates") or []
        candidate_refs = {str(c.get("ref")) for c in candidates if c.get("ref")}
        proposed_ref = str(row["matched_receipt_ref"] or "")
        if body_ref:
            ref = body_ref
            allowed_refs = candidate_refs or ({proposed_ref} if proposed_ref else set())
            if allowed_refs and ref not in allowed_refs and not manual:
                raise GgvBankStatementError(
                    "That reference is not among the proposed candidates.",
                    code="invalid_ref",
                    http_status=400,
                )
            if not _ref_exists(c, ref):
                raise GgvBankStatementError(
                    "That record does not exist for this company.",
                    code="invalid_ref",
                    http_status=400,
                )
        elif proposed_ref:
            if not _ref_exists(c, proposed_ref):
                raise GgvBankStatementError(
                    "That record does not exist for this company.",
                    code="invalid_ref",
                    http_status=400,
                )
            ref = proposed_ref
        elif len(candidates) == 1:
            ref = str(candidates[0].get("ref") or "")
            if not ref or not _ref_exists(c, ref):
                raise GgvBankStatementError(
                    "That record does not exist for this company.",
                    code="invalid_ref",
                    http_status=400,
                )
        else:
            raise GgvBankStatementError(
                "Pick which record to match — several candidates share this amount and date.",
                code="ambiguous_match",
                http_status=409,
            )
        if not ref:
            raise GgvBankStatementError(
                "No match reference provided.",
                code="missing_ref",
                http_status=400,
            )
        if not _direction_ok_for_ref(
            c, ref, float(row["debit"] or 0), float(row["credit"] or 0)
        ):
            raise GgvBankStatementError(
                "That record does not match the money direction on this bank line.",
                code="direction_mismatch",
                http_status=400,
            )
        ref_kind = _ref_kind(c, ref)
        if ref_kind == "bill":
            bill_row = c.execute(
                "SELECT status FROM ggv_bills WHERE bill_id=? AND entity_id=?",
                (ref, _eid()),
            ).fetchone()
            if not bill_row or not _bill_matchable(bill_row["status"]):
                raise GgvBankStatementError(
                    "That bill cannot be matched (deleted or void).",
                    code="invalid_ref",
                    http_status=400,
                )
        elif ref_kind == "invoice":
            inv_row = c.execute(
                "SELECT status FROM ggv_invoices WHERE invoice_id=? AND entity_id=?",
                (ref, _eid()),
            ).fetchone()
            if not inv_row or not _invoice_matchable(inv_row["status"]):
                raise GgvBankStatementError(
                    "That invoice cannot be matched (not issued or paid).",
                    code="invalid_ref",
                    http_status=400,
                )
        taken = c.execute(
            """
            SELECT txn_id FROM ggv_bank_transactions
            WHERE entity_id=? AND human_confirmed=1 AND matched_receipt_ref=? AND txn_id<>?
            """,
            (_eid(), ref, txn_id),
        ).fetchone()
        if taken:
            raise GgvBankStatementError(
                "That record is already matched to another bank line.",
                code="duplicate_match",
                http_status=409,
            )
        ts = _now()
        c.execute(
            """
            UPDATE ggv_bank_transactions
            SET human_confirmed=1, match_proposed=0, recon_status='MATCHED',
                matched_receipt_ref=?, match_confidence='MATCHED'
            WHERE txn_id=? AND entity_id=?
            """,
            (ref, txn_id, _eid()),
        )
        if ref_kind == "bill" and pay_amount > 0:
            _apply_bill_payment(c, ref, pay_amount)
        _audit.record_event(
            action="ggv.bank_recon.confirm",
            result="SUCCEEDED",
            source="ggv_bank_statement1",
            actor_type="PERSON",
            actor_person_id=verified_person_id,
            verified_person_id=verified_person_id,
            entity_id=_eid(),
            resource_type="bank_transaction",
            resource_id=txn_id,
            metadata={
                "matched_receipt_ref": ref,
                "auto_reconcile": False,
                "manual_match": manual and not int(row["match_proposed"] or 0),
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "txn_id": txn_id,
            "match_label": MATCH_LABELS["MATCHED"],
            "matched_receipt_ref": ref,
            "auto_reconcile": False,
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def unmatch(
    *,
    verified_person_id: str,
    txn_id: str,
    body: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Human removes a match — audited."""
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c, run_backfill=False)
        _assert_ggv_finance(verified_person_id, c)
        row = c.execute(
            "SELECT * FROM ggv_bank_transactions WHERE txn_id=? AND entity_id=?",
            (txn_id.strip(), _eid()),
        ).fetchone()
        if not row:
            raise GgvBankStatementError("Bank line not found.", code="not_found", http_status=404)
        prior_ref = row["matched_receipt_ref"]
        prior_status = row["recon_status"]
        pay_amount = float(row["credit"] or 0) or float(row["debit"] or 0)
        reason = str((body or {}).get("reason") or "").strip()
        if not reason:
            raise GgvBankStatementError(
                "Say why you are removing this match.",
                code="reason_required",
                http_status=400,
            )
        ts = _now()
        c.execute(
            """
            UPDATE ggv_bank_transactions
            SET human_confirmed=0, match_proposed=0, recon_status='UNIDENTIFIED',
                matched_receipt_ref=NULL, match_confidence='UNMATCHED'
            WHERE txn_id=? AND entity_id=?
            """,
            (txn_id, _eid()),
        )
        if (
            prior_ref
            and int(row["human_confirmed"] or 0)
            and _ref_kind(c, str(prior_ref)) == "bill"
            and pay_amount > 0
        ):
            _apply_bill_payment(c, str(prior_ref), pay_amount, reverse=True)
        _audit.record_event(
            action="ggv.bank_recon.unmatch",
            result="SUCCEEDED",
            source="ggv_bank_statement1",
            actor_type="PERSON",
            actor_person_id=verified_person_id,
            verified_person_id=verified_person_id,
            entity_id=_eid(),
            resource_type="bank_transaction",
            resource_id=txn_id,
            metadata={
                "reason": reason,
                "prior_receipt_ref": prior_ref,
                "prior_status": prior_status,
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "txn_id": txn_id,
            "match_label": MATCH_LABELS["UNMATCHED"],
            "reason": reason,
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def search_manual_match_targets(
    *,
    verified_person_id: str,
    txn_id: str,
    query: str = "",
    limit: int = 20,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c, run_backfill=False)
        _assert_ggv_finance(verified_person_id, c)
        row = c.execute(
            "SELECT * FROM ggv_bank_transactions WHERE txn_id=? AND entity_id=?",
            (txn_id.strip(), _eid()),
        ).fetchone()
        if not row:
            raise GgvBankStatementError("Bank line not found.", code="not_found", http_status=404)
        credit = float(row["credit"] or 0)
        debit = float(row["debit"] or 0)
        amount = credit if credit > 0 else debit
        direction = _txn_direction(debit, credit)
        q = (query or "").strip().lower()
        lim = max(1, min(int(limit or 20), 50))
        tol = MANUAL_AMOUNT_TOLERANCE if q else AMOUNT_TOLERANCE
        hits: list[dict[str, Any]] = []
        for h in _load_match_candidates(c):
            if not _kind_allowed_for_direction(str(h.get("kind") or ""), direction):
                continue
            label = str(h.get("label") or "")
            party = str(h.get("party") or "")
            number = str(h.get("number") or "")
            if q and q not in label.lower() and q not in party.lower() and q not in number.lower():
                continue
            if amount > 0 and not any(abs(val - amount) <= tol for val in _candidate_amounts(h)):
                if not q:
                    continue
            kind = str(h.get("kind") or "")
            ref = str(h.get("ref") or "")
            hits.append(
                {
                    "kind": kind,
                    "ref": ref,
                    "label": label or _display_label(h),
                    "amount": h.get("amount"),
                    "net_amount": h.get("net_amount"),
                    "date": h.get("date"),
                    "href": _match_href(kind, ref),
                }
            )
            if len(hits) >= lim:
                break
        return {
            "ok": True,
            "txn_id": txn_id,
            "targets": hits,
            "count": len(hits),
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def deny_if_not_ggv_entity(person_id: str) -> dict[str, Any] | None:
    """Helper for Zayen / cross-entity prove — returns deny payload or None if allowed."""
    c = _nota._open_ready()
    try:
        _assert_ggv_finance(person_id, c)
        return None
    except GgvBankStatementError as exc:
        return {
            "ok": False,
            "error": exc.code,
            "message": str(exc),
            "entity_id": _eid(),
            **HONESTY,
        }
    except _nota.FinanceNotaError as exc:
        return {
            "ok": False,
            "error": getattr(exc, "code", "forbidden"),
            "message": str(exc),
            "entity_id": _eid(),
            **HONESTY,
        }
    finally:
        c.close()
