#!/usr/bin/env python3
"""GGV receipt accounting queues — vault reuse, human confirm beside extraction.

Decision served: Finance Control Repair 2026-10-03 Part B (extend) +
existing identity-vault receipts + ggv_bank_statement1 matching surface.

Queue states (human labels): needs_coding, needs_review, unmatched, duplicate.
Original receipt image stays evidence. Human confirm never erases extraction.
Missing evidence stays visible. AMG/BZG rows excluded from GGV. staff_ready false.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import ggv_finance_nota as _nota
from core import ggv_receipt_intake_ro as _rx
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ENTITY_GGV = "ENT-GGV"

QUEUE_LABELS = {
    "needs_coding": "NEEDS CODING",
    "needs_review": "NEEDS REVIEW",
    "unmatched": "UNMATCHED",
    "duplicate": "POSSIBLE DUPLICATE",
    "matched": "MATCHED",
    "completed": "COMPLETED",
}

HONESTY = {
    "staff_ready": False,
    "eng_proved": False,
    "proven": False,
    "second_pipeline": False,
    "entity_id": ENTITY_GGV,
    "amg_bzg_isolated": True,
    "extraction_retained_on_confirm": True,
    "image_permanent": True,
    "money_movement": False,
    "xero_live_create": "CANCELLED_FAIL_CLOSED",
}


class GgvReceiptAccountingError(ValueError):
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


def _date_only(value: Any, fallback_iso: str) -> str:
    """Normalize to YYYY-MM-DD. Upload date uses stored meta filed_at, not vault file scan."""
    raw = str(value or "").strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    fb = str(fallback_iso or "").strip()
    if len(fb) >= 10:
        return fb[:10]
    return fb or _now()[:10]


def _upload_date_at_store(*, meta: dict[str, Any] | None, store_ts: str) -> str:
    filed_at = meta.get("filed_at") if isinstance(meta, dict) else None
    return _date_only(filed_at, store_ts)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _is_ggv_receipt(name_l: str, meta_tenant: str | None) -> bool:
    """Entity isolation — meta tenant wins; exclude AMG/BZG filename infixes."""
    if "_bzg_receipt_" in name_l or "_amg_receipt_" in name_l:
        return False
    if meta_tenant in ("BZG", "AMG"):
        return False
    if meta_tenant == "GGV":
        return True
    if "_ggv_receipt_" in name_l:
        return True
    return False


def _extraction_from_meta(meta: dict[str, Any] | None, vault_row: dict[str, Any]) -> dict[str, Any]:
    meta = meta if isinstance(meta, dict) else {}
    return {
        "source": "vault_meta",
        "note": meta.get("note") or vault_row.get("note"),
        "sender": meta.get("sender_slug") or vault_row.get("sender"),
        "filed_at": meta.get("filed_at"),
        "reimburse": bool(meta.get("reimburse") or vault_row.get("reimburse")),
        "uploaded_via": meta.get("uploaded_via") or vault_row.get("uploaded_via"),
        "amount": meta.get("amount") or meta.get("total") or meta.get("idr"),
        "receipt_date": meta.get("receipt_date") or meta.get("date"),
        "vendor": meta.get("vendor"),
        "category": meta.get("category"),
        "account_code": meta.get("account_code"),
        "tax": meta.get("tax"),
        "currency": meta.get("currency"),
        "raw_meta": meta,
    }


def _confirmed_tax(body: dict[str, Any]) -> str | None:
    """Tax only when explicitly provided; missing stays blank, not zero."""
    if "tax" not in body:
        return None
    raw = body.get("tax")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _confirmed_currency(body: dict[str, Any]) -> str | None:
    """Currency only when explicitly provided; missing stays blank, not a default code."""
    if "currency" not in body:
        return None
    raw = body.get("currency")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _classify_queue(
    *,
    duplicate_of: str | None,
    human: dict[str, Any] | None,
    extraction: dict[str, Any] | None,
    bank_matched: bool,
    missing_evidence: bool,
) -> str:
    if duplicate_of:
        return "duplicate"
    if not human:
        return "needs_review"
    account_code = str((human or {}).get("account_code") or "").strip()
    category = str((human or {}).get("category") or "").strip()
    if not account_code and not category:
        return "needs_coding"
    if missing_evidence or not bank_matched:
        return "unmatched"
    return "unmatched"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ggv_receipt_accounting (
          receipt_key TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          vault_filename TEXT NOT NULL,
          vault_queue TEXT NOT NULL,
          vault_path TEXT NOT NULL,
          content_sha256 TEXT NULL,
          accounting_queue TEXT NOT NULL,
          extraction_json TEXT NULL,
          human_confirmed_json TEXT NULL,
          duplicate_of TEXT NULL,
          missing_evidence INTEGER NOT NULL DEFAULT 0,
          bank_match_proposed TEXT NULL,
          bank_match_confirmed INTEGER NOT NULL DEFAULT 0,
          confirmed_by_person_id TEXT NULL,
          confirmed_at TEXT NULL,
          upload_date TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(entity_id, vault_filename)
        )
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ggv_receipt_accounting)").fetchall()}
    if "upload_date" not in cols:
        conn.execute("ALTER TABLE ggv_receipt_accounting ADD COLUMN upload_date TEXT NULL")
        conn.execute(
            """
            UPDATE ggv_receipt_accounting
            SET upload_date = substr(created_at, 1, 10)
            WHERE upload_date IS NULL OR upload_date = ''
            """
        )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ggv_rx_acct_queue
          ON ggv_receipt_accounting(entity_id, accounting_queue)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ggv_rx_acct_sha
          ON ggv_receipt_accounting(entity_id, content_sha256)
        """
    )


def _assert_ggv_finance(person_id: str, conn: sqlite3.Connection) -> None:
    _nota.require(person_id, "finance.nota.read", conn)
    decision = _rbac.evaluate(
        person_id,
        "finance.nota.read",
        {"entity_id": ENTITY_GGV},
        conn=conn,
    )
    if not decision.get("allowed"):
        raise GgvReceiptAccountingError(
            "GGV finance denied for this person (entity scope).",
            code="forbidden",
            http_status=403,
            details={"reason": decision.get("reason"), "entity_id": ENTITY_GGV},
        )


def _bank_match_for_receipt(
    conn: sqlite3.Connection, filename: str
) -> tuple[str | None, bool]:
    row = conn.execute(
        """
        SELECT matched_receipt_ref, human_confirmed, recon_status
        FROM ggv_bank_transactions
        WHERE entity_id=? AND matched_receipt_ref=?
        ORDER BY created_at DESC LIMIT 1
        """,
        (ENTITY_GGV, filename),
    ).fetchone()
    if not row:
        return None, False
    confirmed = bool(row["human_confirmed"])
    return str(row["matched_receipt_ref"]), confirmed


def sync_vault_receipts(
    *,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Upsert GGV vault receipts into accounting rows (persisted, not fixtures)."""
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        vault = _rx.list_ggv_receipts(limit=500)
        receipts = vault.get("receipts") or []
        sha_first: dict[str, str] = {}
        sha_rows: list[tuple[str, str]] = []
        for r in receipts:
            path = Path(str(r.get("path") or ""))
            sha = _sha256_file(path) if path.is_file() else None
            key = str(r.get("filename") or path.name)
            if sha:
                sha_rows.append((sha, key))
        for sha, key in sha_rows:
            if sha not in sha_first:
                sha_first[sha] = key

        synced = 0
        ts = _now()
        for r in receipts:
            filename = str(r.get("filename") or "")
            if not filename:
                continue
            name_l = filename.lower()
            meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
            meta_tenant = str(meta.get("tenant") or r.get("tenant") or "").upper() or None
            if not _is_ggv_receipt(name_l, meta_tenant):
                continue
            path = Path(str(r.get("path") or ""))
            sha = _sha256_file(path) if path.is_file() else None
            duplicate_of = None
            if sha and sha_first.get(sha) and sha_first[sha] != filename:
                duplicate_of = sha_first[sha]
            extraction = _extraction_from_meta(meta, r)
            existing = c.execute(
                "SELECT * FROM ggv_receipt_accounting WHERE receipt_key=?",
                (filename,),
            ).fetchone()
            human = None
            if existing and existing["human_confirmed_json"]:
                try:
                    human = json.loads(existing["human_confirmed_json"])
                except json.JSONDecodeError:
                    human = None
            if existing and existing["extraction_json"] and not extraction.get("amount"):
                try:
                    stored_ext = json.loads(existing["extraction_json"])
                    if isinstance(stored_ext, dict):
                        extraction = stored_ext
                except json.JSONDecodeError:
                    pass
            bank_ref, bank_confirmed = _bank_match_for_receipt(c, filename)
            missing_evidence = not bool(r.get("image_retrievable"))
            queue = _classify_queue(
                duplicate_of=duplicate_of,
                human=human,
                extraction=extraction,
                bank_matched=bool(bank_ref and bank_confirmed),
                missing_evidence=missing_evidence,
            )
            if existing:
                c.execute(
                    """
                    UPDATE ggv_receipt_accounting SET
                      vault_queue=?, vault_path=?, content_sha256=?, accounting_queue=?,
                      extraction_json=?, duplicate_of=?, missing_evidence=?,
                      bank_match_proposed=?, bank_match_confirmed=?, updated_at=?
                    WHERE receipt_key=?
                    """,
                    (
                        r.get("queue") or "processed",
                        str(path),
                        sha,
                        queue,
                        json.dumps(extraction, ensure_ascii=False),
                        duplicate_of,
                        1 if missing_evidence else 0,
                        bank_ref,
                        1 if bank_confirmed else 0,
                        ts,
                        filename,
                    ),
                )
            else:
                upload_date = _upload_date_at_store(meta=meta, store_ts=ts)
                c.execute(
                    """
                    INSERT INTO ggv_receipt_accounting (
                      receipt_key, entity_id, vault_filename, vault_queue, vault_path,
                      content_sha256, accounting_queue, extraction_json,
                      human_confirmed_json, duplicate_of, missing_evidence,
                      bank_match_proposed, bank_match_confirmed,
                      confirmed_by_person_id, confirmed_at, upload_date,
                      created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        filename,
                        ENTITY_GGV,
                        filename,
                        r.get("queue") or "processed",
                        str(path),
                        sha,
                        queue,
                        json.dumps(extraction, ensure_ascii=False),
                        None,
                        duplicate_of,
                        1 if missing_evidence else 0,
                        bank_ref,
                        1 if bank_confirmed else 0,
                        None,
                        None,
                        upload_date,
                        ts,
                        ts,
                    ),
                )
            synced += 1
        if commit:
            c.commit()
        return {"ok": True, "synced": synced, "vault_count": len(receipts), **HONESTY}
    finally:
        if own:
            c.close()


def _row_public(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    extraction = None
    human = None
    try:
        extraction = json.loads(d.pop("extraction_json") or "null")
    except json.JSONDecodeError:
        extraction = None
    try:
        human = json.loads(d.pop("human_confirmed_json") or "null")
    except json.JSONDecodeError:
        human = None
    path = Path(str(d.get("vault_path") or ""))
    d["extraction"] = extraction
    d["human_confirmed"] = human
    d["queue_label"] = QUEUE_LABELS.get(d.get("accounting_queue") or "", d.get("accounting_queue"))
    d["image_retrievable"] = path.is_file()
    d["image_url"] = f"/api/ggv/finance/accounting/receipts/{d.get('receipt_key')}/image"
    d["extraction_retained"] = extraction is not None
    d["human_beside_extraction"] = human is not None and extraction is not None
    d["missing_evidence_visible"] = bool(d.get("missing_evidence"))
    return d


def list_accounting_queues(
    *,
    verified_person_id: str,
    queue: str | None = None,
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        _assert_ggv_finance(verified_person_id, c)
        sync_vault_receipts(conn=c, commit=True)
        lim = max(1, min(int(limit or 100), 500))
        qfilter = (queue or "").strip().lower() or None
        if qfilter and qfilter not in QUEUE_LABELS:
            raise GgvReceiptAccountingError(
                f"queue must be one of: {', '.join(QUEUE_LABELS)}",
                code="invalid_queue",
            )
        sql = [
            "SELECT * FROM ggv_receipt_accounting WHERE entity_id=?",
        ]
        args: list[Any] = [ENTITY_GGV]
        if qfilter:
            sql.append("AND accounting_queue=?")
            args.append(qfilter)
        sql.append("ORDER BY updated_at DESC LIMIT ?")
        args.append(lim)
        rows = [_row_public(r) for r in c.execute(" ".join(sql), tuple(args)).fetchall()]
        counts = {
            k: int(
                c.execute(
                    "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND accounting_queue=?",
                    (ENTITY_GGV, k),
                ).fetchone()[0]
            )
            for k in QUEUE_LABELS
        }
        missing_n = int(
            c.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND missing_evidence=1",
                (ENTITY_GGV,),
            ).fetchone()[0]
        )
        bank_missing = int(
            c.execute(
                """
                SELECT COUNT(*) FROM ggv_bank_transactions
                WHERE entity_id=? AND recon_status IN ('NEEDS_RECEIPT','UNIDENTIFIED','NEEDS_REVIEW')
                  AND human_confirmed=0
                """,
                (ENTITY_GGV,),
            ).fetchone()[0]
        )
        amg_bzg_leak = int(
            c.execute(
                """
                SELECT COUNT(*) FROM ggv_receipt_accounting
                WHERE entity_id=? AND (
                  vault_filename LIKE '%_bzg_receipt_%' OR vault_filename LIKE '%_amg_receipt_%'
                )
                """,
                (ENTITY_GGV,),
            ).fetchone()[0]
        )
        return {
            "ok": True,
            "entity_id": ENTITY_GGV,
            "queue_labels": QUEUE_LABELS,
            "queue_counts": counts,
            "items": rows,
            "count": len(rows),
            "missing_evidence_receipts": missing_n,
            "bank_unmatched_txns": bank_missing,
            "amg_bzg_leak_count": amg_bzg_leak,
            "amg_bzg_isolated": amg_bzg_leak == 0,
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def get_receipt(
    *,
    verified_person_id: str,
    receipt_key: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        _assert_ggv_finance(verified_person_id, c)
        sync_vault_receipts(conn=c, commit=True)
        row = c.execute(
            "SELECT * FROM ggv_receipt_accounting WHERE entity_id=? AND receipt_key=?",
            (ENTITY_GGV, receipt_key.strip()),
        ).fetchone()
        if not row:
            raise GgvReceiptAccountingError("Receipt not found.", code="not_found", http_status=404)
        return {"ok": True, "receipt": _row_public(row), **HONESTY}
    finally:
        if own:
            c.close()


def confirm_receipt(
    *,
    verified_person_id: str,
    receipt_key: str,
    body: dict[str, Any],
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        if not (
            _nota.person_can(verified_person_id, "finance.nota.review", c)
            or _nota.person_can(verified_person_id, "finance.nota.edit", c)
        ):
            raise GgvReceiptAccountingError(
                "You do not have access to confirm GGV receipts.",
                code="forbidden",
                http_status=403,
            )
        _assert_ggv_finance(verified_person_id, c)
        sync_vault_receipts(conn=c, commit=False)
        row = c.execute(
            "SELECT * FROM ggv_receipt_accounting WHERE entity_id=? AND receipt_key=?",
            (ENTITY_GGV, receipt_key.strip()),
        ).fetchone()
        if not row:
            raise GgvReceiptAccountingError("Receipt not found.", code="not_found", http_status=404)
        extraction = None
        try:
            extraction = json.loads(row["extraction_json"] or "null")
        except json.JSONDecodeError:
            extraction = None
        human = {
            "vendor": body.get("vendor"),
            "amount": body.get("amount"),
            "tax": _confirmed_tax(body),
            "currency": _confirmed_currency(body),
            "date": body.get("date") or body.get("receipt_date"),
            "category": body.get("category"),
            "account_code": body.get("account_code"),
            "notes": body.get("notes"),
            "confirmed_fields": {
                k: body[k]
                for k in ("vendor", "amount", "tax", "currency", "date", "category", "account_code", "notes")
                if k in body
            },
        }
        bank_ref, bank_confirmed = _bank_match_for_receipt(c, receipt_key)
        missing_evidence = bool(row["missing_evidence"])
        queue = _classify_queue(
            duplicate_of=row["duplicate_of"],
            human=human,
            extraction=extraction if isinstance(extraction, dict) else None,
            bank_matched=bool(bank_ref and bank_confirmed),
            missing_evidence=missing_evidence,
        )
        ts = _now()
        c.execute(
            """
            UPDATE ggv_receipt_accounting SET
              human_confirmed_json=?, accounting_queue=?, confirmed_by_person_id=?,
              confirmed_at=?, updated_at=?
            WHERE receipt_key=?
            """,
            (
                json.dumps(human, ensure_ascii=False),
                queue,
                verified_person_id,
                ts,
                ts,
                receipt_key.strip(),
            ),
        )
        _audit.safe_record(
            action="ggv_receipt_accounting.confirm",
            result="ALLOWED",
            source="ggv_receipt_accounting1",
            actor_type="PERSON",
            verified_person_id=verified_person_id,
            actor_person_id=verified_person_id,
            entity_id=ENTITY_GGV,
            resource_type="ggv_receipt_accounting",
            resource_id=receipt_key.strip(),
            reason_code="human_confirm",
            metadata={
                "accounting_queue": queue,
                "extraction_retained": extraction is not None,
                "before": {"human_confirmed": None},
                "after": {"human_confirmed": human, "extraction": extraction},
            },
            conn=c,
        )
        c.commit()
        updated = c.execute(
            "SELECT * FROM ggv_receipt_accounting WHERE receipt_key=?",
            (receipt_key.strip(),),
        ).fetchone()
        pub = _row_public(updated)
        assert pub.get("extraction") is not None or extraction is None
        assert pub.get("extraction_retained") is True or extraction is None
        stored_human = pub.get("human_confirmed") or {}
        assert stored_human.get("tax") == human.get("tax")
        assert stored_human.get("currency") == human.get("currency")
        return {
            "ok": True,
            "receipt": pub,
            "extraction_retained": pub.get("extraction") is not None,
            "human_beside_extraction": bool(pub.get("human_confirmed") and pub.get("extraction")),
            **HONESTY,
        }
    finally:
        if own:
            c.close()


def receipt_image_bytes(
    *,
    verified_person_id: str,
    receipt_key: str,
    conn: sqlite3.Connection | None = None,
) -> tuple[bytes, str, str]:
    own = conn is None
    c = conn or _nota._open_ready()
    try:
        ensure_schema(c)
        _assert_ggv_finance(verified_person_id, c)
        row = c.execute(
            "SELECT vault_path, vault_filename FROM ggv_receipt_accounting WHERE entity_id=? AND receipt_key=?",
            (ENTITY_GGV, receipt_key.strip()),
        ).fetchone()
        if not row:
            raise GgvReceiptAccountingError("Receipt not found.", code="not_found", http_status=404)
        path = Path(str(row["vault_path"] or ""))
        if not path.is_file():
            raise GgvReceiptAccountingError(
                "Original receipt image missing on disk.",
                code="missing_evidence",
                http_status=404,
            )
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return path.read_bytes(), mime, path.name
    finally:
        if own:
            c.close()
