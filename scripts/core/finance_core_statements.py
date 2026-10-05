#!/usr/bin/env python3
"""FINANCE-CORE-STATEMENTS-1 — shared bank statement library + upload for all entities.

One product capability; entity rows stay isolated (GGV/AMG in ggv_bank_* tables, BZG in bzg_bank_*).
staff_ready=false · file_import_only · no money movement.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import sqlite3
import subprocess
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from core import audit as _audit
from core import finance_core_entity as _fce
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PDFTOTEXT = Path("/opt/homebrew/bin/pdftotext")
PACK = "FINANCE-CORE-STATEMENTS-1"
HISTORICAL_ACTOR = "PERS-MATT"

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "file_import_only": True,
    "live_bank_feed": False,
    "auto_reconcile": False,
    "money_movement": False,
    "pack": PACK,
}

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}

ENTITY_ACCOUNTS: dict[str, tuple[dict[str, Any], ...]] = {
    "ENT-GGV": (
        {
            "bank_label": "MANDIRI",
            "account_number": "1610015100972",
            "account_label": "Mandiri-1610015100972",
            "start_month": "2026-01",
        },
    ),
    "ENT-AMG": (
        {"bank_label": "CIMB", "account_number": "800203739400", "account_label": "CKM-800203739400", "start_month": "2025-12", "pt": "Cipta Karya"},
        {"bank_label": "CIMB", "account_number": "800203720100", "account_label": "PPL-800203720100", "start_month": "2025-12", "pt": "Pasir Putih"},
        {"bank_label": "CIMB", "account_number": "800203718200", "account_label": "FRJ-800203718200", "start_month": "2025-12", "pt": "Fortuna Rinjani"},
        {"bank_label": "CIMB", "account_number": "800203745100", "account_label": "KAS-800203745100", "start_month": "2025-12", "pt": "Karya Anak Sasak"},
        {"bank_label": "CIMB", "account_number": "800203774400", "account_label": "PLI-800203774400", "start_month": "2025-12", "pt": "Pesona Lombok"},
    ),
    "ENT-BZG": (
        {"bank_label": "MANDIRI", "account_number": "1610555335558", "account_label": "Mandiri-1610555335558", "start_month": "2026-03"},
        {"bank_label": "BRI", "account_number": "19101003489305", "account_label": "BRI-19101003489305", "start_month": "2026-04"},
        {"bank_label": "BNI", "account_number": "2177177110", "account_label": "BNI-2177177110", "start_month": "2026-04"},
    ),
}

HISTORICAL_SOURCES: dict[str, tuple[Path, ...]] = {
    "ENT-GGV": (
        Path("~/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/GGV/Mandiri-1610015100972").expanduser(),
        Path("~/.openclaw/state/bank/_sources/GGV").expanduser(),
    ),
    "ENT-AMG": (
        Path("~/.openclaw/workspace/wolf-system/atrium/statements").expanduser(),
    ),
    "ENT-BZG": (
        BETA_ROOT / "state" / "bzg-bank-statements" / "originals",
        Path("~/.openclaw/state/bank/_sources/BZG").expanduser(),
        Path("~/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/BZG").expanduser(),
    ),
}

SKIP_FILENAMES = frozenset({
    "README.txt",
    "ggv_jan_jun_ledger_export.txt",
})
SKIP_PATTERNS = (
    re.compile(r"account_balances_.*\.xlsx$", re.I),
    re.compile(r"ledger_export", re.I),
)


class FinanceStatementError(ValueError):
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
    try:
        return float(str(s or "").strip().replace(",", "") or 0)
    except (TypeError, ValueError):
        return 0.0


def _eid() -> str:
    return _fce.active_entity()


def _entity_tables(entity_id: str | None = None) -> tuple[str, str]:
    eid = entity_id or _eid()
    if eid == "ENT-BZG":
        return "bzg_bank_statement_imports", "bzg_bank_transactions"
    return "ggv_bank_statement_imports", "ggv_bank_transactions"


def _originals_dir(entity_id: str | None = None) -> Path:
    eid = entity_id or _eid()
    if eid == "ENT-BZG":
        return BETA_ROOT / "state" / "bzg-bank-statements" / "originals"
    rel = Path(str(_fce.entity_config(eid)["bank_originals"]))
    return BETA_ROOT / rel


def _mask_account(acct: str | None) -> str | None:
    if not acct:
        return None
    digits = re.sub(r"\D", "", str(acct))
    if len(digits) < 4:
        return acct
    return f"••••{digits[-4:]}"


def _norm_desc(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())[:120]


def _parse_iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s)
    if m:
        mon = MONTHS.get(m.group(2)[:3].lower()) or MONTHS.get(m.group(2).lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s, re.I)
    if m:
        mon = MONTHS.get(m.group(2)[:3].lower()) or MONTHS.get(m.group(2).lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
    return None


def _parse_period_text(text: str) -> tuple[str | None, str | None]:
    """Extract period start/end from header text."""
    m = re.search(
        r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*[-–]\s*(\d{1,2})\s+(\w+)\s+(\d{4})",
        text,
        re.I,
    )
    if m:
        sm = MONTHS.get(m.group(2)[:3].lower()) or MONTHS.get(m.group(2).lower())
        em = MONTHS.get(m.group(5)[:3].lower()) or MONTHS.get(m.group(5).lower())
        if sm and em:
            return (
                f"{int(m.group(3)):04d}-{sm:02d}-{int(m.group(1)):02d}",
                f"{int(m.group(6)):04d}-{em:02d}-{int(m.group(4)):02d}",
            )
    m = re.search(r"(\d{2})\s+(\w{3})\s+(\d{4})\s*[-–]\s*(\d{2})\s+(\w{3})\s+(\d{4})", text, re.I)
    if m:
        sm = MONTHS.get(m.group(2).lower())
        em = MONTHS.get(m.group(5).lower())
        if sm and em:
            return (
                f"{int(m.group(3)):04d}-{sm:02d}-{int(m.group(1)):02d}",
                f"{int(m.group(6)):04d}-{em:02d}-{int(m.group(4)):02d}",
            )
    return None, None


def _iter_months(start: str, end: str) -> list[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    cur = date(sy, sm, 1)
    stop = date(ey, em, 1)
    out: list[str] = []
    while cur <= stop:
        out.append(f"{cur.year:04d}-{cur.month:02d}")
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return out


def _month_key_from_date(d: str | None) -> str | None:
    if not d or len(d) < 7:
        return None
    return d[:7]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    if col not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    from core import ggv_bank_statement1 as _gbs
    from core import bzg_history_import1 as _bhi

    _gbs.ensure_schema(conn)
    _bhi.ensure_history_schema(conn)
    for table in ("ggv_bank_statement_imports", "bzg_bank_statement_imports"):
        if table not in {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}:
            continue
        _add_column(conn, table, "opening_balance", "REAL NULL")
        _add_column(conn, table, "closing_balance", "REAL NULL")
        _add_column(conn, table, "account_number", "TEXT NULL")
        _add_column(conn, table, "evidence_status", "TEXT NULL")
        _add_column(conn, table, "reconciliation_status", "TEXT NULL")
        _add_column(conn, table, "statement_signature", "TEXT NULL")
        _add_column(conn, table, "is_test_fixture", "INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, table, "duplicate_of_import_id", "TEXT NULL")
        _add_column(conn, table, "overlap_txn_count", "INTEGER NULL")


def _permission_for_entity(entity_id: str) -> tuple[str, dict[str, str]]:
    if entity_id == "ENT-BZG":
        return "atrium.board.read", {"entity_id": entity_id}
    if entity_id == "ENT-AMG":
        return "finance.nota.read", {"entity_id": entity_id}
    return "finance.nota.read", {"entity_id": entity_id}


def _assert_finance_read(person_id: str, conn: sqlite3.Connection, entity_id: str | None = None) -> None:
    eid = entity_id or _eid()
    pid = (person_id or "").strip()
    if not pid:
        raise FinanceStatementError("Sign in required.", code="unauthenticated", http_status=401)
    perm, scope = _permission_for_entity(eid)
    if eid in ("ENT-AMG", "ENT-BZG"):
        allowed = _rbac.can(pid, "finance.nota.read", scope, conn=conn) or _rbac.can(
            pid, "atrium.board.read", scope, conn=conn
        )
    else:
        allowed = _rbac.can(pid, perm, scope, conn=conn)
    if not allowed:
        raise FinanceStatementError(
            f"{_fce.entity_config(eid)['label']} finance denied for this person.",
            code="forbidden",
            http_status=403,
            details={"entity_id": eid},
        )


def _pdf_text(data: bytes) -> str:
    if not PDFTOTEXT.is_file():
        return ""
    proc = subprocess.run(
        [str(PDFTOTEXT), "-layout", "-", "-"],
        input=data,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", "replace")


def _parse_mandiri_csv(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=";") if r and len(r) >= 8]
    if not rows or "AccountNo" not in (rows[0][0] or ""):
        return {}, [], ""
    meta: dict[str, Any] = {"bank_label": "MANDIRI"}
    acct = str(rows[1][0]).strip() if len(rows) > 1 else None
    if acct and acct.isdigit():
        meta["account_number"] = acct
    out: list[dict[str, Any]] = []
    for r in rows[1:]:
        if not str(r[0]).strip().isdigit():
            continue
        out.append(
            {
                "txn_date": _parse_iso_date(r[2]),
                "value_date": _parse_iso_date(r[2]),
                "description": f"{r[3]} {r[4]}".strip(),
                "reference": str(r[0]).strip(),
                "credit": _num(r[5]),
                "debit": _num(r[6]),
                "running_balance": _num(r[7]),
                "bank_account": acct or "MANDIRI",
                "raw": {"cols": r[:8]},
            }
        )
    if out:
        dates = [t["txn_date"] for t in out if t.get("txn_date")]
        meta["period_start"] = min(dates)
        meta["period_end"] = max(dates)
        meta["closing_balance"] = out[-1].get("running_balance")
    return meta, out, "mandiri_semicolon_csv"


def _parse_bri_csv(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {}, [], ""
    idx = {h.strip(): i for i, h in enumerate(rows[0])}
    if "MUTASI_KREDIT" not in idx or "MUTASI_DEBET" not in idx:
        return {}, [], ""
    meta: dict[str, Any] = {"bank_label": "BRI"}
    out: list[dict[str, Any]] = []
    for r in rows[1:]:
        if len(r) <= max(idx.values()):
            continue
        norek_i = idx.get("NOREK", 1)
        if not str(r[norek_i]).strip():
            continue
        acct = str(r[norek_i]).strip()
        meta.setdefault("account_number", acct)
        tgl = str(r[idx.get("TGL_TRAN", 0)])[:10]
        desc_parts = []
        for key in ("KETERANGAN", "DESKRIPSI", "REMARK", "KET"):
            if key in idx and idx[key] < len(r):
                desc_parts.append(str(r[idx[key]]))
        out.append(
            {
                "txn_date": _parse_iso_date(tgl),
                "value_date": _parse_iso_date(tgl),
                "description": " ".join(desc_parts).strip() or None,
                "reference": acct,
                "credit": _num(r[idx["MUTASI_KREDIT"]]),
                "debit": _num(r[idx["MUTASI_DEBET"]]),
                "running_balance": _num(r[idx["SALDO_AKHIR_MUTASI"]])
                if "SALDO_AKHIR_MUTASI" in idx
                else None,
                "bank_account": acct,
                "raw": {"cols": r},
            }
        )
    if out:
        dates = [t["txn_date"] for t in out if t.get("txn_date")]
        meta["period_start"] = min(dates)
        meta["period_end"] = max(dates)
    return meta, out, "bri_internet_banking_csv"


def _parse_mandiri_pdf(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    meta: dict[str, Any] = {"bank_label": "MANDIRI"}
    m_acct = re.search(r"Account No\s+(\d{10,16})", text)
    if m_acct:
        meta["account_number"] = m_acct.group(1)
    ps, pe = _parse_period_text(text)
    meta["period_start"], meta["period_end"] = ps, pe
    m_open = re.search(r"Opening Balance\s+([\d,]+\.\d{2})", text)
    m_close = re.search(r"Closing Balance\s+([\d,]+\.\d{2})", text)
    if m_open:
        meta["opening_balance"] = _num(m_open.group(1))
    if m_close:
        meta["closing_balance"] = _num(m_close.group(1))
    blocks = re.split(r"\nDetails:\s*\n", text)
    out: list[dict[str, Any]] = []
    for block in blocks[1:]:
        m_date = re.search(r"Posting Date\s+(\d{2}/\d{2}/\d{4})", block)
        m_amt = re.search(r"Amount\s+IDR\s+([\d,]+\.\d{2})", block)
        m_desc = re.search(r"Transaction Description\s+(.+?)(?:\nReference No|\nCheque)", block, re.S)
        if not m_date or not m_amt:
            continue
        amt = _num(m_amt.group(1))
        desc = re.sub(r"\s+", " ", (m_desc.group(1) if m_desc else "").strip())
        is_credit = "Credit Account" in block or "credit account" in block.lower()
        out.append(
            {
                "txn_date": _parse_iso_date(m_date.group(1)),
                "value_date": _parse_iso_date(m_date.group(1)),
                "description": desc or None,
                "reference": None,
                "credit": amt if is_credit else 0.0,
                "debit": 0.0 if is_credit else amt,
                "running_balance": None,
                "bank_account": meta.get("account_number") or "MANDIRI",
                "raw": {"block": block[:500]},
            }
        )
    return meta, out, "mandiri_livin_pdf"


def _parse_cimb_pdf(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    meta: dict[str, Any] = {"bank_label": "CIMB"}
    m_acct = re.search(r"Account Number\s*:\s*(\d{10,16})", text)
    if m_acct:
        meta["account_number"] = m_acct.group(1)
    ps, pe = _parse_period_text(text)
    meta["period_start"], meta["period_end"] = ps, pe
    m_open = re.search(r"SALDO AWAL\s+([\d,]+\.\d{2})", text)
    m_close = re.search(r"SALDO AKHIR\s+([\d,]+\.\d{2})", text)
    if m_open:
        meta["opening_balance"] = _num(m_open.group(1))
    if m_close:
        meta["closing_balance"] = _num(m_close.group(1))
    out: list[dict[str, Any]] = []
    year = (meta.get("period_end") or meta.get("period_start") or "2026-01-01")[:4]
    for line in text.splitlines():
        m = re.match(r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+)$", line.strip())
        if not m:
            continue
        rest = m.group(3).strip()
        if rest.upper().startswith("SALDO"):
            continue
        amounts = re.findall(r"[\d,]+\.\d{2}", rest)
        if not amounts:
            continue
        desc = re.sub(r"[\d,]+\.\d{2}", "", rest).strip()
        debit = credit = 0.0
        balance = None
        if len(amounts) >= 3:
            debit, credit, balance = _num(amounts[0]), _num(amounts[1]), _num(amounts[2])
        elif len(amounts) == 2:
            debit, balance = _num(amounts[0]), _num(amounts[1])
        else:
            continue
        if debit == 0 and credit == 0:
            continue
        out.append(
            {
                "txn_date": _parse_iso_date(f"{m.group(1)}/{year}"),
                "value_date": _parse_iso_date(f"{m.group(2)}/{year}"),
                "description": desc or None,
                "reference": None,
                "debit": debit,
                "credit": credit,
                "running_balance": balance,
                "bank_account": meta.get("account_number") or "CIMB",
                "raw": {"line": line.strip()},
            }
        )
    evidence = "cimb_e_statement_pdf"
    if "_juli.pdf" in text.lower() or "scan" in text.lower():
        meta["evidence_status"] = "SCAN_NOT_E_STATEMENT"
    return meta, out, evidence


def _parse_generic_csv(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    from core import ggv_bank_statement1 as _gbs

    rows = _gbs._parse_generic_csv(text)
    meta: dict[str, Any] = {}
    if rows:
        dates = [r.get("txn_date") for r in rows if r.get("txn_date")]
        if dates:
            meta["period_start"] = min(dates)
            meta["period_end"] = max(dates)
    return meta, rows, "generic_csv_header"


def parse_statement_bytes(data: bytes, filename: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Return (meta, normalised_rows, parse_notes). meta includes bank_label, account, period, balances."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = _pdf_text(data)
        if not text:
            raise FinanceStatementError(
                "Could not read PDF — original will be kept.",
                code="parse_failed",
            )
        if "account statement" in text.lower() and "cimb" in text.lower() or "cimb niaga" in text.lower():
            meta, rows, notes = _parse_cimb_pdf(text)
            if rows:
                return meta, rows, notes
        if "account statement" in text.lower() or "livin" in text.lower():
            meta, rows, notes = _parse_mandiri_pdf(text)
            if rows:
                return meta, rows, notes
        meta, rows, notes = _parse_cimb_pdf(text)
        if rows:
            return meta, rows, notes
        meta, rows, notes = _parse_mandiri_pdf(text)
        if rows:
            return meta, rows, notes
        raise FinanceStatementError("Could not parse PDF statement.", code="parse_failed")
    if name.endswith((".xls", ".xlsx")):
        raise FinanceStatementError(
            "BNI spreadsheet format not parsed — original kept.",
            code="parse_failed",
        )
    text = data.decode("utf-8", "replace")
    meta, rows, notes = _parse_mandiri_csv(text)
    if rows:
        return meta, rows, notes
    meta, rows, notes = _parse_bri_csv(text)
    if rows:
        return meta, rows, notes
    meta, rows, notes = _parse_generic_csv(text)
    if rows:
        bank = "BNI" if "bni" in name else ("MANDIRI" if "mandiri" in name else "GENERIC")
        meta["bank_label"] = bank
        return meta, rows, notes
    raise FinanceStatementError(
        "Could not parse statement — original kept.",
        code="parse_failed",
    )


def overlap_signature(row: dict[str, Any]) -> str:
    """Weaker txn key for partial-overlap duplicate detection (date + direction + amount)."""
    debit = float(row.get("debit") or 0)
    credit = float(row.get("credit") or 0)
    direction = "C" if credit > 0 else "D"
    amount = credit if credit > 0 else debit
    return f"{row.get('txn_date') or ''}|{direction}|{amount:.2f}"


def txn_signature(row: dict[str, Any]) -> str:
    debit = float(row.get("debit") or 0)
    credit = float(row.get("credit") or 0)
    direction = "C" if credit > 0 else "D"
    amount = credit if credit > 0 else debit
    bal = row.get("running_balance")
    bal_s = f"{float(bal):.2f}" if bal is not None else ""
    return "|".join(
        [
            str(row.get("txn_date") or ""),
            direction,
            f"{amount:.2f}",
            _norm_desc(row.get("description")),
            _norm_desc(row.get("reference")),
            bal_s,
        ]
    )


def _statement_signature(
    entity_id: str,
    bank: str,
    account: str | None,
    period_start: str | None,
    period_end: str | None,
    content_sha256: str,
    rows: list[dict[str, Any]],
) -> str:
    sigs = sorted(txn_signature(r) for r in rows)
    payload = json.dumps(
        {
            "entity_id": entity_id,
            "bank": bank,
            "account": account or "",
            "period_start": period_start,
            "period_end": period_end,
            "sha256": content_sha256,
            "txn_sigs": sigs[:500],
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _library_filter_sql() -> str:
    return " AND COALESCE(is_test_fixture, 0) = 0"


def _public_import(row: dict[str, Any]) -> dict[str, Any]:
    acct = row.get("account_number") or row.get("account_label")
    return {
        "statement_id": row["import_id"],
        "bank": row.get("bank_label"),
        "account": _mask_account(str(acct) if acct else None),
        "period_start": row.get("period_start"),
        "period_end": row.get("period_end"),
        "opening_balance": row.get("opening_balance"),
        "closing_balance": row.get("closing_balance"),
        "txn_count": row.get("txn_count"),
        "reconciliation_status": row.get("reconciliation_status") or "UNRECONCILED",
        "evidence_status": row.get("evidence_status")
        or ("PARSE FAILED — ORIGINAL KEPT" if str(row.get("parse_status")) in ("EXCEPTION", "PARSE_FAILED") else "ORIGINAL_KEPT"),
        "parse_status": row.get("parse_status"),
        "uploaded_at": row.get("uploaded_at"),
        "open_href": f"{_fce.entity_config(row['entity_id'])['page_prefix']}/statements/{row['import_id']}",
    }


def _find_overlap(
    conn: sqlite3.Connection,
    entity_id: str,
    bank: str,
    account: str | None,
    new_sigs: set[str],
    imp_table: str,
    txn_table: str,
) -> dict[str, Any] | None:
    if not new_sigs:
        return None
    imports = conn.execute(
        f"""
        SELECT import_id, period_start, period_end, txn_count, original_filename
        FROM {imp_table}
        WHERE entity_id=? AND bank_label=? AND COALESCE(is_test_fixture,0)=0
          AND (account_number=? OR account_label=? OR ? IS NULL)
        """,
        (entity_id, bank, account, account, account),
    ).fetchall()
    best: dict[str, Any] | None = None
    best_count = 0
    for imp in imports:
        existing = conn.execute(
            f"SELECT txn_date, debit, credit, description, reference, running_balance FROM {txn_table} WHERE import_id=?",
            (imp["import_id"],),
        ).fetchall()
        overlap = 0
        for t in existing:
            if overlap_signature(dict(t)) in new_sigs:
                overlap += 1
        if overlap > best_count:
            best_count = overlap
            best = {
                "import_id": imp["import_id"],
                "overlap_txn_count": overlap,
                "period_start": imp["period_start"],
                "period_end": imp["period_end"],
                "prior_filename": imp["original_filename"],
            }
    if best_count > 0:
        return best
    return None


def import_statement(
    *,
    verified_person_id: str,
    filename: str,
    content: bytes,
    bank_label: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
    entity_id: str | None = None,
) -> dict[str, Any]:
    from core import ggv_bank_statement1 as _gbs

    eid = entity_id or _eid()
    imp_table, txn_table = _entity_tables(eid)
    actor = (verified_person_id or "").strip()
    if not actor:
        raise FinanceStatementError("verified_person_id required", code="missing_person")
    if not content:
        raise FinanceStatementError("empty statement file", code="empty_file")
    if len(content) > 12_000_000:
        raise FinanceStatementError("statement too large", code="too_large", http_status=413)

    own = conn is None
    from core import ggv_finance_nota as _nota

    c = conn or _nota._open_ready()
    try:
        with _fce.entity_scope(eid):
            ensure_schema(c)
            _assert_finance_read(actor, c, eid)
            sha = hashlib.sha256(content).hexdigest()
            dup = c.execute(
                f"SELECT import_id FROM {imp_table} WHERE entity_id=? AND content_sha256=?",
                (eid, sha),
            ).fetchone()
            if dup:
                raise FinanceStatementError(
                    "ALREADY IMPORTED — this exact statement file was imported before.",
                    code="already_imported",
                    http_status=409,
                    details={
                        "import_id": dup["import_id"],
                        "status": "ALREADY IMPORTED",
                        "existing_statement_href": f"{_fce.entity_config(eid)['page_prefix']}/statements/{dup['import_id']}",
                    },
                )

            parse_failed = False
            meta: dict[str, Any] = {}
            rows: list[dict[str, Any]] = []
            notes = ""
            try:
                meta, rows, notes = parse_statement_bytes(content, filename)
            except FinanceStatementError:
                parse_failed = True
                meta = {"bank_label": (bank_label or "UNKNOWN").strip().upper()}
                notes = "parse_failed_original_kept"

            bank = (bank_label or meta.get("bank_label") or "UNKNOWN").strip().upper()
            account = meta.get("account_number") or meta.get("account_label")
            period_start = meta.get("period_start")
            period_end = meta.get("period_end")
            new_sigs = {overlap_signature(r) for r in rows}
            overlap = None
            if rows and not parse_failed:
                overlap = _find_overlap(c, eid, bank, account, new_sigs, imp_table, txn_table)
                if overlap:
                    raise FinanceStatementError(
                        "POSSIBLE DUPLICATE IMPORT — overlapping transactions with a prior statement.",
                        code="possible_duplicate_import",
                        http_status=409,
                        details={
                            "status": "POSSIBLE DUPLICATE IMPORT",
                            "import_id": overlap["import_id"],
                            "overlap_txn_count": overlap["overlap_txn_count"],
                            "overlapping_period_start": overlap.get("period_start"),
                            "overlapping_period_end": overlap.get("period_end"),
                            "existing_statement_href": f"{_fce.entity_config(eid)['page_prefix']}/statements/{overlap['import_id']}",
                        },
                    )

            originals = _originals_dir(eid)
            originals.mkdir(parents=True, exist_ok=True)
            prefix = "GBSI" if eid != "ENT-BZG" else "BZG-BANK"
            import_id = f"{prefix}-{uuid.uuid4()}" if eid != "ENT-BZG" else f"BZG-BANK-{uuid.uuid4().hex[:12].upper()}"
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename or "statement").name)[:180]
            dest = originals / f"{import_id}__{safe_name}" if eid != "ENT-BZG" else originals / safe_name
            dest.write_bytes(content)

            if not period_start and rows:
                dates = [r.get("txn_date") for r in rows if r.get("txn_date")]
                period_start = min(dates) if dates else None
                period_end = max(dates) if dates else None

            stmt_sig = _statement_signature(eid, bank, account, period_start, period_end, sha, rows)
            parse_status = "PARSE_FAILED" if parse_failed else ("PARSED" if rows else "EXCEPTION")
            evidence_status = meta.get("evidence_status") or (
                "PARSE FAILED — ORIGINAL KEPT" if parse_failed else "ORIGINAL_KEPT"
            )
            ts = _now()
            c.execute(
                f"""
                INSERT INTO {imp_table} (
                  import_id, entity_id, bank_label, account_label, original_filename,
                  original_path, content_sha256, uploaded_by_person_id, uploaded_at,
                  period_start, period_end, txn_count, parse_status, parse_notes,
                  opening_balance, closing_balance, account_number, evidence_status,
                  reconciliation_status, statement_signature, is_test_fixture
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    import_id,
                    eid,
                    bank,
                    meta.get("account_label") or account,
                    safe_name,
                    str(dest),
                    sha,
                    actor,
                    ts,
                    period_start,
                    period_end,
                    len(rows),
                    parse_status,
                    notes,
                    meta.get("opening_balance"),
                    meta.get("closing_balance"),
                    account,
                    evidence_status,
                    "UNRECONCILED",
                    stmt_sig,
                ),
            )
            for r in rows:
                txn_id = f"{'GBT' if eid != 'ENT-BZG' else 'BZT'}-{uuid.uuid4()}"
                recon_default = "UNIDENTIFIED" if eid != "ENT-BZG" else "UNMATCHED"
                if eid == "ENT-BZG":
                    c.execute(
                        f"""
                        INSERT INTO {txn_table} (
                          txn_id, import_id, entity_id, txn_date, value_date, description,
                          reference, debit, credit, running_balance, bank_account, raw_json,
                          recon_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            txn_id, import_id, eid, r.get("txn_date"), r.get("value_date"),
                            r.get("description"), r.get("reference"),
                            float(r.get("debit") or 0), float(r.get("credit") or 0),
                            r.get("running_balance"), r.get("bank_account") or bank,
                            json.dumps(r.get("raw") or {}, separators=(",", ":")),
                            recon_default, ts,
                        ),
                    )
                else:
                    c.execute(
                        f"""
                        INSERT INTO {txn_table} (
                          txn_id, import_id, entity_id, txn_date, value_date, description,
                          reference, debit, credit, running_balance, bank_account, raw_json,
                          recon_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            txn_id, import_id, eid, r.get("txn_date"), r.get("value_date"),
                            r.get("description"), r.get("reference"),
                            float(r.get("debit") or 0), float(r.get("credit") or 0),
                            r.get("running_balance"), r.get("bank_account") or bank,
                            json.dumps(r.get("raw") or {}, separators=(",", ":")),
                            recon_default, ts,
                        ),
                    )

            proposed: dict[str, Any] = {}
            if eid != "ENT-BZG" and rows and not parse_failed:
                proposed = _gbs.propose_matches(import_id, conn=c, commit=False)

            _audit.safe_record(
                action="finance_core_statement.import",
                result="ALLOWED",
                source="finance_core_statements",
                actor_type="PERSON",
                verified_person_id=actor,
                actor_person_id=actor,
                resource_type="bank_statement_import",
                resource_id=import_id,
                reason_code="file_import",
                metadata={
                    "entity_id": eid,
                    "bank_label": bank,
                    "txn_count": len(rows),
                    "parse_status": parse_status,
                    "content_sha256": sha,
                },
                conn=c,
            )
            if commit:
                c.commit()
            return {
                "ok": True,
                "import_id": import_id,
                "statement_id": import_id,
                "bank_label": bank,
                "account": _mask_account(str(account) if account else None),
                "original_filename": safe_name,
                "original_retrievable": dest.is_file(),
                "content_sha256": sha,
                "txn_count": len(rows),
                "period_start": period_start,
                "period_end": period_end,
                "opening_balance": meta.get("opening_balance"),
                "closing_balance": meta.get("closing_balance"),
                "parse_status": parse_status,
                "parse_notes": notes,
                "evidence_status": evidence_status,
                "proposed_matches": proposed,
                "entity_id": eid,
                **HONESTY,
            }
    finally:
        if own:
            c.close()


def list_library(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    eid = entity_id or _eid()
    imp_table, _ = _entity_tables(eid)
    own = conn is None
    from core import ggv_finance_nota as _nota

    c = conn or _nota._open_ready()
    try:
        with _fce.entity_scope(eid):
            ensure_schema(c)
            _assert_finance_read(verified_person_id, c, eid)
            rows = [
                dict(r)
                for r in c.execute(
                    f"""
                    SELECT * FROM {imp_table}
                    WHERE entity_id=? {_library_filter_sql()}
                    ORDER BY COALESCE(period_end, uploaded_at) DESC, uploaded_at DESC
                    LIMIT 200
                    """,
                    (eid,),
                ).fetchall()
            ]
            statements = [_public_import(r) for r in rows]
            completeness = month_completeness(verified_person_id=verified_person_id, conn=c, entity_id=eid)
            return {
                "ok": True,
                "entity_id": eid,
                "statements": statements,
                "count": len(statements),
                "completeness": completeness.get("accounts", []),
                **HONESTY,
            }
    finally:
        if own:
            c.close()


def get_statement(
    *,
    verified_person_id: str,
    import_id: str,
    conn: sqlite3.Connection | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    eid = entity_id or _eid()
    imp_table, txn_table = _entity_tables(eid)
    own = conn is None
    from core import ggv_finance_nota as _nota

    c = conn or _nota._open_ready()
    try:
        with _fce.entity_scope(eid):
            ensure_schema(c)
            _assert_finance_read(verified_person_id, c, eid)
            row = c.execute(
                f"SELECT * FROM {imp_table} WHERE import_id=? AND entity_id=? {_library_filter_sql()}",
                (import_id.strip(), eid),
            ).fetchone()
            if not row:
                raise FinanceStatementError("Statement not found.", code="not_found", http_status=404)
            imp = dict(row)
            txns = [
                dict(t)
                for t in c.execute(
                    f"SELECT * FROM {txn_table} WHERE import_id=? AND entity_id=? ORDER BY txn_date, created_at",
                    (import_id, eid),
                ).fetchall()
            ]
            for t in txns:
                raw = t.pop("raw_json", None)
                t["raw"] = json.loads(raw) if raw else {}
                if eid != "ENT-BZG":
                    conf = str(t.get("match_confidence") or "").upper()
                    if conf == "PROPOSE MATCH":
                        t["match_label"] = "PROPOSE MATCH"
                    elif str(t.get("recon_status") or "").upper() == "NEEDS_REVIEW":
                        t["match_label"] = "HUMAN REVIEW"
                    else:
                        t["match_label"] = "UNMATCHED"
            audit_tail: list[dict[str, Any]] = []
            try:
                audits = c.execute(
                    """
                    SELECT action, result, created_at, metadata_json
                    FROM core_audit_events
                    WHERE resource_type IN ('bank_statement_import','ggv_bank_statement_import')
                      AND resource_id=?
                    ORDER BY created_at DESC LIMIT 20
                    """,
                    (import_id,),
                ).fetchall()
                audit_tail = [dict(a) for a in audits]
            except sqlite3.OperationalError:
                audit_tail = []
            public = _public_import(imp)
            public["transactions"] = txns
            public["audit_trail"] = audit_tail
            public["original_download_href"] = f"{_fce.entity_config(eid)['api_prefix']}/statements/{import_id}/original"
            public["content_sha256"] = imp.get("content_sha256")
            public["parse_notes"] = imp.get("parse_notes")
            return {"ok": True, "statement": public, "entity_id": eid, **HONESTY}
    finally:
        if own:
            c.close()


def original_bytes(
    *,
    verified_person_id: str,
    import_id: str,
    conn: sqlite3.Connection | None = None,
    entity_id: str | None = None,
) -> tuple[bytes, str, str]:
    eid = entity_id or _eid()
    imp_table, _ = _entity_tables(eid)
    own = conn is None
    from core import ggv_finance_nota as _nota

    c = conn or _nota._open_ready()
    try:
        with _fce.entity_scope(eid):
            ensure_schema(c)
            _assert_finance_read(verified_person_id, c, eid)
            row = c.execute(
                f"SELECT original_path, original_filename, entity_id FROM {imp_table} WHERE import_id=? AND entity_id=?",
                (import_id.strip(), eid),
            ).fetchone()
            if not row:
                raise FinanceStatementError("Statement not found.", code="not_found", http_status=404)
            if row["entity_id"] != eid:
                raise FinanceStatementError("Forbidden.", code="forbidden", http_status=403)
            path = Path(str(row["original_path"] or ""))
            if not path.is_file():
                raise FinanceStatementError("Original file not retrievable.", code="not_found", http_status=404)
            data = path.read_bytes()
            fname = str(row["original_filename"] or path.name)
            ext = path.suffix.lower()
            mime = "application/pdf" if ext == ".pdf" else "text/csv" if ext == ".csv" else "application/octet-stream"
            return data, mime, fname
    finally:
        if own:
            c.close()


def month_completeness(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    entity_id: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    eid = entity_id or _eid()
    imp_table, _ = _entity_tables(eid)
    own = conn is None
    from core import ggv_finance_nota as _nota

    c = conn or _nota._open_ready()
    try:
        with _fce.entity_scope(eid):
            ensure_schema(c)
            _assert_finance_read(verified_person_id, c, eid)
            today = (as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:10]
            current_month = today[:7]
            accounts_out: list[dict[str, Any]] = []
            for acct_cfg in ENTITY_ACCOUNTS.get(eid, ()):
                start = acct_cfg["start_month"]
                months = _iter_months(start, current_month)
                covered: set[str] = set()
                imports = c.execute(
                    f"""
                    SELECT period_start, period_end, parse_status, reconciliation_status
                    FROM {imp_table}
                    WHERE entity_id=? AND COALESCE(is_test_fixture,0)=0
                      AND (account_number=? OR account_label LIKE ? OR bank_label=?)
                    """,
                    (
                        eid,
                        acct_cfg["account_number"],
                        f"%{acct_cfg['account_number']}%",
                        acct_cfg["bank_label"],
                    ),
                ).fetchall()
                for imp in imports:
                    ps = imp["period_start"] or imp["period_end"]
                    pe = imp["period_end"] or imp["period_start"]
                    if ps and pe:
                        for m in _iter_months(ps[:7], pe[:7]):
                            covered.add(m)
                    elif ps:
                        covered.add(ps[:7])
                strip: list[dict[str, str]] = []
                for m in months:
                    label = m[5:8].upper()
                    if m == current_month:
                        strip.append({"month": m, "label": f"{label} CURRENT", "status": "CURRENT"})
                    elif m in covered:
                        strip.append({"month": m, "label": f"{label} ON FILE", "status": "ON_FILE"})
                    else:
                        strip.append({"month": m, "label": f"{label} MISSING STATEMENT", "status": "MISSING"})
                accounts_out.append(
                    {
                        "account": _mask_account(acct_cfg["account_number"]),
                        "bank": acct_cfg["bank_label"],
                        "account_label": acct_cfg["account_label"],
                        "months": strip,
                        "statement_count": len(imports),
                    }
                )
            return {"ok": True, "entity_id": eid, "accounts": accounts_out, **HONESTY}
    finally:
        if own:
            c.close()


def flag_ggv_prove_fixtures(conn: sqlite3.Connection) -> list[str]:
    """Mark 3 Oct prove imports as TEST_FIXTURE (hidden from library)."""
    ensure_schema(conn)
    ids = []
    rows = conn.execute(
        """
        SELECT import_id FROM ggv_bank_statement_imports
        WHERE entity_id='ENT-GGV' AND original_filename='ggv-prove-statement.csv'
        """
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE ggv_bank_statement_imports SET is_test_fixture=1 WHERE import_id=?",
            (r["import_id"],),
        )
        ids.append(r["import_id"])
    return ids


def _is_statement_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name in SKIP_FILENAMES:
        return False
    for pat in SKIP_PATTERNS:
        if pat.search(path.name):
            return False
    ext = path.suffix.lower()
    return ext in {".csv", ".pdf", ".xls", ".xlsx"}


def _collect_historical_files(entity_id: str) -> list[Path]:
    seen_sha: set[str] = set()
    out: list[Path] = []
    def _sort_key(p: Path) -> tuple:
        ext = p.suffix.lower()
        return (0 if ext == ".pdf" else 1, p.name)

    for root in HISTORICAL_SOURCES.get(entity_id, ()):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), key=_sort_key):
            if not _is_statement_file(path):
                continue
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            if digest in seen_sha:
                continue
            seen_sha.add(digest)
            out.append(path)
    return out


def register_historical_statements(
    *,
    conn: sqlite3.Connection,
    entity_id: str,
    actor: str = HISTORICAL_ACTOR,
    commit: bool = True,
) -> dict[str, Any]:
    """Import authorised historical files not already in catalog (by sha256)."""
    registered = 0
    skipped = 0
    errors: list[str] = []
    with _fce.entity_scope(entity_id):
        for path in _collect_historical_files(entity_id):
            try:
                content = path.read_bytes()
                sha = hashlib.sha256(content).hexdigest()
                imp_table, _ = _entity_tables(entity_id)
                exists = conn.execute(
                    f"SELECT import_id FROM {imp_table} WHERE entity_id=? AND content_sha256=?",
                    (entity_id, sha),
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                import_statement(
                    verified_person_id=actor,
                    filename=path.name,
                    content=content,
                    conn=conn,
                    commit=False,
                    entity_id=entity_id,
                )
                registered += 1
            except FinanceStatementError as exc:
                if exc.code in ("already_imported", "possible_duplicate_import"):
                    skipped += 1
                else:
                    errors.append(f"{path.name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name}: {exc}")
    if commit:
        conn.commit()
    return {"registered": registered, "skipped": skipped, "errors": errors}


def list_fixture_files_ignored() -> list[str]:
    """Leaked test fixture originals in live dirs — do not delete, only list."""
    patterns = ("*__fc1-ggv-statement.csv", "*__amg-fc1-statement.csv", "*__amg-idem.csv", "*__fc1-isolation.csv")
    found: list[str] = []
    for sub in ("ggv-bank-statements/originals", "amg-bank-statements/originals"):
        root = BETA_ROOT / "state" / sub
        if not root.is_dir():
            continue
        for pat in patterns:
            for p in root.glob(pat):
                found.append(str(p.relative_to(BETA_ROOT)))
    return sorted(found)


def build_registry(conn: sqlite3.Connection) -> dict[str, Any]:
    """Per-entity account registry from real DB rows."""
    reg: dict[str, Any] = {}
    for eid in ("ENT-GGV", "ENT-AMG", "ENT-BZG"):
        imp_table, _ = _entity_tables(eid)
        accounts: dict[str, Any] = {}
        for acct_cfg in ENTITY_ACCOUNTS.get(eid, ()):
            key = acct_cfg["account_label"]
            rows = conn.execute(
                f"""
                SELECT period_start, period_end, parse_status, txn_count
                FROM {imp_table}
                WHERE entity_id=? AND COALESCE(is_test_fixture,0)=0
                  AND (account_number=? OR account_label LIKE ? OR bank_label=?)
                """,
                (eid, acct_cfg["account_number"], f"%{acct_cfg['account_number']}%", acct_cfg["bank_label"]),
            ).fetchall()
            covered: set[str] = set()
            parse_statuses: list[str] = []
            for r in rows:
                parse_statuses.append(str(r["parse_status"] or ""))
                ps, pe = r["period_start"], r["period_end"]
                if ps and pe:
                    for m in _iter_months(ps[:7], pe[:7]):
                        covered.add(m)
                elif ps:
                    covered.add(ps[:7])
            start = acct_cfg["start_month"]
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")[:7]
            expected = set(_iter_months(start, today))
            missing = sorted(expected - covered)
            accounts[key] = {
                "months_covered": sorted(covered),
                "months_missing": missing,
                "statement_count": len(rows),
                "parse_status": parse_statuses,
            }
        reg[eid] = accounts
    return reg


def backfill_import_metadata(conn: sqlite3.Connection, entity_id: str = "ENT-BZG") -> int:
    """Derive account_number and period from filename for legacy BZG rows."""
    imp_table, _ = _entity_tables(entity_id)
    updated = 0
    rows = conn.execute(
        f"SELECT import_id, original_filename, bank_label, account_label FROM {imp_table} WHERE entity_id=?",
        (entity_id,),
    ).fetchall()
    for row in rows:
        fname = str(row["original_filename"] or "")
        acct = row["account_number"] if "account_number" in row.keys() else None
        ps = row["period_start"] if "period_start" in row.keys() else None
        pe = row["period_end"] if "period_end" in row.keys() else None
        account_number = None
        period_start = period_end = None
        m = re.search(r"Acc_Statement_(\d+)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", fname)
        if m:
            account_number = m.group(1)
            period_start, period_end = m.group(2), m.group(3)
        m2 = re.search(r"(\d{10,16})_(\d{4})-(\d{2})", fname)
        if m2 and not account_number:
            account_number = m2.group(1)
            period_start = f"{m2.group(2)}-{m2.group(3)}-01"
            period_end = f"{m2.group(2)}-{m2.group(3)}-28"
        m3 = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", fname)
        if m3 and not period_start:
            period_start, period_end = m3.group(1), m3.group(2)
        m_ibiz = re.search(r"IBIZ_0*(\d+)_(\d{4})(\d{2})(\d{2})_(\d{4})(\d{2})(\d{2})", fname)
        if m_ibiz and not period_start:
            account_number = account_number or m_ibiz.group(1).lstrip("0") or m_ibiz.group(1)
            period_start = f"{m_ibiz.group(2)}-{m_ibiz.group(3)}-{m_ibiz.group(4)}"
            period_end = f"{m_ibiz.group(5)}-{m_ibiz.group(6)}-{m_ibiz.group(7)}"
        if not account_number and row["account_label"]:
            m4 = re.search(r"(\d{10,16})", str(row["account_label"]))
            if m4:
                account_number = m4.group(1)
        sets: list[str] = []
        args: list[Any] = []
        if account_number:
            sets.append("account_number=?")
            args.append(account_number)
        if period_start:
            sets.append("period_start=?")
            args.append(period_start)
        if period_end:
            sets.append("period_end=?")
            args.append(period_end)
        if sets:
            args.append(row["import_id"])
            conn.execute(
                f"UPDATE {imp_table} SET {', '.join(sets)} WHERE import_id=?",
                tuple(args),
            )
            updated += 1
    return updated


def backup_catalog_before_write() -> dict[str, str]:
    """Back up catalog to catalog/backups with sha256 recorded."""
    from core.canonical_guard import assert_write_allowed

    assert_write_allowed(CATALOG_DB)
    backup_dir = BETA_ROOT / "catalog" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"content_library_pre_statements1_{ts}.sqlite"
    shutil.copy2(CATALOG_DB, dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest = backup_dir / f"content_library_pre_statements1_{ts}.sha256"
    manifest.write_text(f"{digest}  {dest.name}\n", encoding="utf-8")
    return {"backup_path": str(dest), "sha256": digest}
