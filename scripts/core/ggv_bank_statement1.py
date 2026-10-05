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
from datetime import datetime, timezone
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
    try:
        return float(str(s or "").strip().replace(",", "") or 0)
    except (TypeError, ValueError):
        return 0.0


def ensure_schema(conn: sqlite3.Connection) -> None:
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


def _parse_generic_csv(text: str) -> list[dict[str, Any]]:
    """Fallback: date, description, debit, credit [, balance] header row."""
    sample = text.lstrip()[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []
    fields = {((f or "").strip().lower()): f for f in reader.fieldnames}

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
        return []
    out: list[dict[str, Any]] = []
    for row in reader:
        raw_date = str(row.get(dcol) or "").strip()
        # Accept YYYY-MM-DD or DD/MM/YYYY
        txn_date = None
        if re.match(r"\d{4}-\d{2}-\d{2}", raw_date):
            txn_date = raw_date[:10]
        else:
            m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw_date)
            if m:
                txn_date = f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        out.append(
            {
                "txn_date": txn_date,
                "value_date": txn_date,
                "description": (str(row.get(desc) or "").strip() if desc else None) or None,
                "reference": (str(row.get(ref) or "").strip() if ref else None) or None,
                "debit": _num(row.get(debit)) if debit else 0.0,
                "credit": _num(row.get(credit)) if credit else 0.0,
                "running_balance": _num(row.get(bal)) if bal else None,
                "bank_account": "UNKNOWN",
                "raw": dict(row),
            }
        )
    return out


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


def propose_matches(
    import_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Propose high-confidence amount+date matches to vault receipts. Never auto-reconcile."""
    from core import ggv_receipt_intake_ro as _rx

    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        vault = _rx.list_ggv_receipts(limit=300)
        receipts = vault.get("receipts") or []
        # Extract amount/date hints from meta when present
        rx_hints: list[dict[str, Any]] = []
        for r in receipts:
            meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
            amt = meta.get("amount") or meta.get("total") or meta.get("idr")
            try:
                amount = float(amt) if amt is not None else None
            except (TypeError, ValueError):
                amount = None
            rx_hints.append(
                {
                    "ref": r.get("filename"),
                    "amount": amount,
                    "date": meta.get("receipt_date") or meta.get("date") or (r.get("mtime") or "")[:10],
                    "queue": r.get("queue"),
                }
            )

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
            amount = float(t["credit"] or 0) or float(t["debit"] or 0)
            if amount <= 0:
                continue
            tdate = (t["txn_date"] or "")[:10]
            hit = None
            for h in rx_hints:
                if h["amount"] is None:
                    continue
                if abs(float(h["amount"]) - amount) > 1.0:
                    continue
                hdate = (h.get("date") or "")[:10]
                if tdate and hdate and tdate != hdate:
                    continue
                hit = h
                break
            if hit:
                c.execute(
                    """
                    UPDATE ggv_bank_transactions
                    SET recon_status='NEEDS_REVIEW', matched_receipt_ref=?,
                        match_confidence='PROPOSE MATCH', match_proposed=1
                    WHERE txn_id=?
                    """,
                    (hit["ref"], t["txn_id"]),
                )
                proposed += 1
            else:
                c.execute(
                    """
                    UPDATE ggv_bank_transactions
                    SET recon_status='UNIDENTIFIED', match_confidence='UNMATCHED', match_proposed=0
                    WHERE txn_id=? AND recon_status='UNIDENTIFIED'
                    """,
                    (t["txn_id"],),
                )
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


def list_transactions(
    *,
    verified_person_id: str,
    import_id: str | None = None,
    recon_status: str | None = None,
    limit: int = 200,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        _assert_ggv_finance(verified_person_id, c)
        lim = max(1, min(int(limit or 200), 500))
        sql = [
            "SELECT * FROM ggv_bank_transactions WHERE entity_id=?",
        ]
        args: list[Any] = [_eid()]
        if import_id:
            sql.append("AND import_id=?")
            args.append(import_id.strip())
        if recon_status:
            sql.append("AND recon_status=?")
            args.append(recon_status.strip().upper())
        sql.append("ORDER BY txn_date DESC, created_at DESC LIMIT ?")
        args.append(lim)
        rows = [dict(r) for r in c.execute(" ".join(sql), tuple(args)).fetchall()]
        for r in rows:
            r.pop("raw_json", None)  # keep payload lean; original file is evidence
            r["proposed_not_confirmed"] = bool(r.get("match_proposed")) and not bool(
                r.get("human_confirmed")
            )
            conf = str(r.get("match_confidence") or "").upper()
            status = str(r.get("recon_status") or "").upper()
            if conf == "PROPOSE MATCH" or (r.get("match_proposed") and not r.get("human_confirmed")):
                r["match_label"] = "PROPOSE MATCH"
            elif status == "NEEDS_REVIEW":
                r["match_label"] = "HUMAN REVIEW"
            else:
                r["match_label"] = "UNMATCHED"
        return {
            "ok": True,
            "entity_id": _eid(),
            "transactions": rows,
            "count": len(rows),
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
