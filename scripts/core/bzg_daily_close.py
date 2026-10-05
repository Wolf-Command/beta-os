#!/usr/bin/env python3
"""BZG Daily Close — one reusable engine over venue_close (Till+EDC + Multi-EDC Vision).

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner orders
BZG-DAILY-CLOSE-TILL-EDC-20261002, BZG-DAILY-CLOSE-MULTI-EDC-VISION-20261002,
and BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1 (phone Take/Upload + honest ESB).

Not a second close product. Outlet config from registry. Only Uma Blu
human_close_enabled. EDC terminals unknown → NEEDS CONFIGURATION.
0..N EDC receipts/day with separate EDC card + QRIS (never merge).
Vision draft → human confirm (AI ≠ accounting truth). ESB closing receipt
+ live API dual-source; mismatch visible. Settlement API UNAVAILABLE.
Empty today ESB → ESB DATA UNAVAILABLE (never fake zeros).
No invented variance tolerance / terminal TIDs. No if-Devi.
"""
from __future__ import annotations

import re
import subprocess

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import bzg_close_vision as _vision
from core import bzg_outlet_registry as _outlets
from core import esb_close_snapshot as _esb
from core import evidence as _evidence
from core import uma_ops_console as _petty
from core import venue_close as _vc
from core import wolf_evidence_guard as _weg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK = "BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1"
PACK_PRIOR = "BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1"
PACK_VISION = "BZG-DAILY-CLOSE-MULTI-EDC-VISION-1"
ENTITY = "ENT-BZG"
OUTLET_UMA = "BZG-UMA"
SETTLEMENT_BANK_LABELS = ("MANDIRI", "BNI", "BRI")

EVIDENCE_Z = "pos_z_report"
EVIDENCE_EDC = "edc_settlement_slip"
EVIDENCE_ESB_RECEIPT = "esb_closing_receipt"

LIVE_CLOSE_RECEIPT_DIR = _weg.LIVE_CLOSE_RECEIPT_DIR
CLOSE_RECEIPT_DIR = _weg.resolve_close_receipt_dir()
CLOSE_RECEIPT_SCHEME = "close-receipt://"

HONESTY = {
    **_vc.HONESTY,
    "pack": PACK,
    "prior_pack": PACK_PRIOR,
    "vision_pack": PACK_VISION,
    "staff_ready": False,
    "human_commissioned": False,
    "daily_close_commissioned": False,
    "settlement_api": "UNAVAILABLE",
    "settlement_status": "PENDING_BANK",
    "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
    "esb_payments_are_not_edc_settlement": True,
    "declared_cash_is_not_verified": True,
    "invented_tolerance": False,
    "invented_edc_terminals": False,
    "alchemist_soft_gap_not_policy": True,
    "ai_is_not_accounting_truth": True,
    "qris_never_merged_into_card": True,
    "multi_edc_receipts": True,
    "edc_receipts_required_count": None,  # 0..N — never exactly-one
    "phone_take_upload_photo": True,
    "esb_unavailable_explicit": True,
    "esb_empty_is_not_zero_sales": True,
    "dual_source_api_and_receipt": True,
    "dual_source_never_overwrite": True,
    "bank_split_edc_qris": True,
    "owner_control": True,
    "engine": "venue_close",
}


class BzgDailyCloseError(_vc.VenueCloseError):
    pass


def _require_holder(
    row: dict[str, Any],
    *,
    verified_person_id: str,
    conn: sqlite3.Connection,
    identity: dict[str, Any] | None = None,
) -> None:
    _vc._assert_holder_allows(  # noqa: SLF001 — shared concurrency gate
        row,
        verified_person_id=verified_person_id,
        conn=conn,
        identity=identity,
    )


_STAFF_PHOTO_FAIL = "PHOTO COULD NOT BE SAVED"
_HEIC_FTYP_BRANDS = frozenset(
    {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1", b"heif"}
)


def _image_ext_from_magic(data: bytes) -> str | None:
    if len(data) >= 3 and data[0:3] == b"\xff\xd8\xff":
        return ".jpg"
    if len(data) >= 4 and data[0:4] == b"\x89PNG":
        return ".png"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in _HEIC_FTYP_BRANDS:
            return ".heic"
    return None


def _image_ext_from_name_or_mime(filename: str | None, content_type: str | None) -> str | None:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".png") or "png" in ctype:
        return ".png"
    if name.endswith(".webp") or "webp" in ctype:
        return ".webp"
    if name.endswith((".heic", ".heif")) or "heic" in ctype or "heif" in ctype:
        return ".heic"
    if name.endswith((".jpg", ".jpeg")) or "jpeg" in ctype or "jpg" in ctype:
        return ".jpg"
    return None


def _image_long_edge(path: Path) -> int:
    try:
        out = subprocess.run(
            ["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        w = h = 0
        for line in (out.stdout or "").splitlines():
            if "pixelWidth:" in line:
                w = int(line.split(":")[-1].strip() or 0)
            elif "pixelHeight:" in line:
                h = int(line.split(":")[-1].strip() or 0)
        return max(w, h)
    except Exception:
        return 0


def _create_read_jpeg_derivative(src: Path, eid: str) -> str | None:
    """Create <eid>.read.jpg beside original for vision reading. Failure is non-fatal."""
    dest = src.parent / f"{eid}.read.jpg"
    try:
        subprocess.run(
            [
                "/usr/bin/sips",
                "-s",
                "format",
                "jpeg",
                "-Z",
                "3000",
                str(src),
                "--out",
                str(dest),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        if dest.is_file() and dest.stat().st_size > 0:
            return f"{CLOSE_RECEIPT_SCHEME}{eid}.read.jpg"
    except Exception:
        pass
    if src.suffix.lower() not in (".heic", ".heif"):
        try:
            from PIL import Image  # type: ignore[import-untyped]

            with Image.open(src) as im:
                im = im.convert("RGB")
                long_edge = max(im.size)
                if long_edge > 3000:
                    ratio = 3000 / float(long_edge)
                    im = im.resize(
                        (max(1, int(im.size[0] * ratio)), max(1, int(im.size[1] * ratio))),
                        Image.Resampling.LANCZOS,
                    )
                im.save(dest, format="JPEG", quality=85)
            if dest.is_file() and dest.stat().st_size > 0:
                return f"{CLOSE_RECEIPT_SCHEME}{eid}.read.jpg"
        except Exception:
            pass
    return None


def save_close_receipt_bytes(
    *,
    data: bytes,
    kind: str = "receipt",
    close_id: str | None = None,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Persist phone receipt photo under Beta state. Returns object_ref + hash."""
    if not data:
        raise BzgDailyCloseError("receipt photo required", code="missing_receipt")
    if len(data) > 40_000_000:
        raise BzgDailyCloseError(
            "receipt too large",
            code="receipt_too_large",
            http_status=413,
            details={"staff_message": _STAFF_PHOTO_FAIL},
        )
    magic_ext = _image_ext_from_magic(data)
    if magic_ext is None:
        raise BzgDailyCloseError(
            "not an image",
            code="invalid_image",
            http_status=415,
            details={"staff_message": _STAFF_PHOTO_FAIL},
        )
    kind_n = (kind or "receipt").strip().lower()
    if kind_n not in ("esb", "edc", "receipt", "z", "till"):
        kind_n = "receipt"
    _weg.assert_live_evidence_writable(CLOSE_RECEIPT_DIR, label="close receipt")
    CLOSE_RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    ext = magic_ext or _image_ext_from_name_or_mime(filename, content_type) or ".jpg"
    eid = f"EVD-CLOSE-{kind_n.upper()}-{uuid.uuid4().hex[:12].upper()}"
    dest = CLOSE_RECEIPT_DIR / f"{eid}{ext}"
    dest.write_bytes(data)
    ch = hashlib.sha256(data).hexdigest()
    ref = f"{CLOSE_RECEIPT_SCHEME}{eid}{ext}"
    derivative_ref: str | None = None
    if ext in (".heic", ".heif") or _image_long_edge(dest) > 3000:
        derivative_ref = _create_read_jpeg_derivative(dest, eid)
    out = {
        "ok": True,
        "evidence_id": eid,
        "object_ref": ref,
        "image_object_ref": ref,
        "content_hash": ch,
        "bytes": len(data),
        "mime_type": content_type or f"image/{ext.lstrip('.')}",
        "filename": filename or dest.name,
        "kind": kind_n,
        "close_id": (close_id or "").strip() or None,
        "path": str(dest),
        "kept_original": True,
        "derivative_object_ref": derivative_ref,
        **HONESTY,
    }
    try:
        idx = CLOSE_RECEIPT_DIR / "photo-index.jsonl"
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "close_id": out["close_id"],
                        "object_ref": ref,
                        "content_hash": ch,
                        "kind": kind_n,
                        "mime_type": out["mime_type"],
                        "filename": out["filename"],
                        "bytes": out["bytes"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    except OSError:
        pass
    return out


def resolve_close_receipt_path(object_ref: str | None) -> Path | None:
    """Map close-receipt://… ref to on-disk path. Refuse path escape."""
    ref = (object_ref or "").strip()
    if _weg.is_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR):
        return None
    if not ref.startswith(CLOSE_RECEIPT_SCHEME):
        return None
    token = ref[len(CLOSE_RECEIPT_SCHEME) :].strip()
    if not token or "/" in token or "\\" in token or ".." in token:
        return None
    path = (CLOSE_RECEIPT_DIR / token).resolve()
    try:
        path.relative_to(CLOSE_RECEIPT_DIR.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _close_receipt_derivative_path(object_ref: str | None) -> Path | None:
    path = resolve_close_receipt_path(object_ref)
    if path is None:
        return None
    stem = path.name
    eid = stem.rsplit(".", 1)[0] if "." in stem else stem
    deriv = path.parent / f"{eid}.read.jpg"
    return deriv if deriv.is_file() else None


def load_close_receipt_bytes(
    object_ref: str | None,
) -> tuple[bytes | None, str]:
    """Load stored receipt bytes + mime. Returns (None, mime) if missing."""
    path = resolve_close_receipt_path(object_ref)
    if path is None:
        return None, "image/jpeg"
    data = path.read_bytes()
    suf = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suf, "image/jpeg")
    return data, mime


def load_close_receipt_vision_bytes(
    object_ref: str | None,
) -> tuple[bytes | None, str]:
    """Load receipt bytes for vision reading; prefers JPEG derivative when present."""
    deriv = _close_receipt_derivative_path(object_ref)
    if deriv is not None:
        return deriv.read_bytes(), "image/jpeg"
    return load_close_receipt_bytes(object_ref)


def _evidence_preservation_snapshot(
    conn: sqlite3.Connection,
    evidence_id: str,
) -> dict[str, Any]:
    """Capture immutable evidence spine + bytes before supersede."""
    row = _evidence.get_evidence(evidence_id, conn=conn)
    if not row:
        raise BzgDailyCloseError(
            f"prior evidence missing: {evidence_id}",
            code="evidence_preservation_broken",
            http_status=500,
        )
    data, _mime = load_close_receipt_bytes(row.get("object_ref"))
    return {
        "evidence_id": row["evidence_id"],
        "status": row["status"],
        "object_ref": row.get("object_ref"),
        "content_hash": row.get("content_hash"),
        "bytes": data,
    }


def _assert_evidence_preservation_intact(
    conn: sqlite3.Connection,
    snapshot: dict[str, Any],
) -> None:
    """Fail closed if supersede deleted or overwrote original evidence."""
    eid = str(snapshot.get("evidence_id") or "")
    row = _evidence.get_evidence(eid, conn=conn)
    if not row:
        raise BzgDailyCloseError(
            f"original evidence row deleted: {eid}",
            code="evidence_preservation_broken",
            http_status=500,
        )
    for key in ("status", "object_ref", "content_hash"):
        if row.get(key) != snapshot.get(key):
            raise BzgDailyCloseError(
                f"original evidence row overwritten on {key}",
                code="evidence_preservation_broken",
                http_status=500,
            )
    if snapshot.get("bytes") is not None:
        data, _mime = load_close_receipt_bytes(row.get("object_ref"))
        if data != snapshot["bytes"]:
            raise BzgDailyCloseError(
                "original evidence bytes overwritten",
                code="evidence_preservation_broken",
                http_status=500,
            )


def read_preserved_close_evidence(
    evidence_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read venue-close evidence row + stored bytes (readable after supersede)."""
    eid = (evidence_id or "").strip()
    if not eid:
        raise BzgDailyCloseError("evidence_id required", code="missing_evidence_id")
    own = conn is None
    c = conn or db_connect()
    try:
        row = _evidence.get_evidence(eid, conn=c)
        if not row:
            raise BzgDailyCloseError("evidence not found", code="not_found", http_status=404)
        data, mime = load_close_receipt_bytes(row.get("object_ref"))
        ch = (row.get("content_hash") or "").strip() or None
        hash_match = None
        if data is not None and ch:
            hash_match = hashlib.sha256(data).hexdigest() == ch
        return {
            **HONESTY,
            "ok": True,
            "evidence_id": eid,
            "evidence": row,
            "bytes": data,
            "bytes_len": len(data) if data is not None else 0,
            "mime_type": mime,
            "readable": data is not None,
            "content_hash_match": hash_match,
            "original_preserved": row["status"] == "ACTIVE",
        }
    finally:
        if own:
            c.close()


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    return _vc.db_connect(db_path)


def ensure_schema(conn: sqlite3.Connection) -> None:
    sql_031 = (
        BETA_ROOT
        / "scripts"
        / "migrations"
        / "031_bzg_daily_close_till_edc.sql"
    ).read_text(encoding="utf-8")
    sql_032 = (
        BETA_ROOT
        / "scripts"
        / "migrations"
        / "032_bzg_daily_close_multi_edc_vision.sql"
    ).read_text(encoding="utf-8")
    conn.executescript(sql_031)
    conn.executescript(sql_032)
    # 033: bank cards + evidence_role (ADD COLUMN may already be applied)
    _ensure_edc_bank_card_schema(conn)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_edc_bank_card_schema(conn: sqlite3.Connection) -> None:
    if _has_table(conn, "venue_close_edc_receipts"):
        cols = _table_columns(conn, "venue_close_edc_receipts")
        for name, decl in (
            ("evidence_role", "TEXT NOT NULL DEFAULT 'CURRENT'"),
            ("superseded_by", "TEXT NULL"),
            ("superseded_at", "TEXT NULL"),
            ("supersede_reason", "TEXT NULL"),
            ("counted_in_totals", "INTEGER NOT NULL DEFAULT 1"),
        ):
            if name not in cols:
                conn.execute(
                    f"ALTER TABLE venue_close_edc_receipts ADD COLUMN {name} {decl}"
                )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS venue_close_outlet_banks (
          bank_config_id TEXT PRIMARY KEY,
          outlet_id TEXT NOT NULL,
          bank_label TEXT NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 100,
          status TEXT NOT NULL DEFAULT 'ACTIVE',
          note TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE (outlet_id, bank_label)
        );
        CREATE INDEX IF NOT EXISTS idx_venue_close_outlet_banks_outlet
          ON venue_close_outlet_banks(outlet_id);
        CREATE TABLE IF NOT EXISTS venue_close_workflow_acks (
          close_id TEXT NOT NULL,
          ack_kind TEXT NOT NULL,
          ack_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY (close_id, ack_kind)
        );
        """
    )
    # Bank-level terminal options when empty (TID unknown OK)
    tn = conn.execute(
        "SELECT COUNT(*) FROM venue_close_edc_terminals WHERE outlet_id=?",
        (OUTLET_UMA,),
    ).fetchone()[0]
    if int(tn) == 0:
        ts = _vc.now_utc_iso()
        for bank in ("MANDIRI", "BNI", "BRI"):
            conn.execute(
                """
                INSERT OR IGNORE INTO venue_close_edc_terminals
                  (terminal_config_id, outlet_id, terminal_label, acquirer_label, status, note, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """,
                (
                    f"TERM-{OUTLET_UMA}-{bank}",
                    OUTLET_UMA,
                    f"{bank} terminal",
                    bank,
                    "Bank-level config (TID unknown — label only)",
                    ts,
                    ts,
                ),
            )


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def list_outlet_configs(
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Registry-driven outlet close config. Unknown map → NEEDS CONFIGURATION."""
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_outlet_config"):
            return []
        rows = c.execute(
            """
            SELECT * FROM venue_close_outlet_config
            ORDER BY
              CASE WHEN human_close_enabled=1 THEN 0 ELSE 1 END,
              outlet_id
            """
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            term_n = c.execute(
                "SELECT COUNT(*) FROM venue_close_edc_terminals WHERE outlet_id=?",
                (d["outlet_id"],),
            ).fetchone()[0]
            # Live honesty: empty terminal registry always NEEDS CONFIGURATION.
            if int(term_n) == 0:
                d["edc_terminal_config_status"] = "NEEDS CONFIGURATION"
            d["edc_terminal_count"] = int(term_n)
            d["human_close_enabled"] = bool(d.get("human_close_enabled"))
            d["till_float_excluded_from_takings"] = d.get("till_float_idr") is not None
            out.append(d)
        return out
    finally:
        if own:
            c.close()


def get_outlet_config(
    outlet_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    oid = (outlet_id or "").strip()
    if not oid:
        return None
    for row in list_outlet_configs(conn):
        if row["outlet_id"] == oid:
            return row
    return None


def assert_human_close_enabled(
    outlet_id: str,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    cfg = get_outlet_config(outlet_id, conn=conn)
    if not cfg:
        raise BzgDailyCloseError(
            f"outlet close config missing for {outlet_id}",
            code="outlet_config_missing",
            http_status=409,
        )
    if not cfg.get("human_close_enabled"):
        raise BzgDailyCloseError(
            f"human close not activated for {outlet_id} (config present only)",
            code="human_close_disabled",
            http_status=403,
        )
    return cfg



def _norm_bank(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().upper())


def _has_confirmed_shift_receipt(close_id: str, conn: sqlite3.Connection) -> bool:
    if not _has_table(conn, "venue_close_esb_closing_receipts"):
        return False
    n = conn.execute(
        """
        SELECT COUNT(*) FROM venue_close_esb_closing_receipts
        WHERE close_id=? AND human_confirm_status IN ('CONFIRMED','EDITED')
        """,
        (close_id.strip(),),
    ).fetchone()[0]
    return int(n) > 0


def _current_edc_receipt_ids_for_bank(
    conn: sqlite3.Connection,
    close_id: str,
    bank_label: str,
) -> list[str]:
    """CURRENT evidence rows for one bank — matched via normalized acquirer label."""
    bank_n = _norm_bank(bank_label)
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT edc_receipt_id, acquirer_label FROM venue_close_edc_receipts
            WHERE close_id=? AND COALESCE(evidence_role,'CURRENT')='CURRENT'
              AND human_confirm_status IN ('CONFIRMED','EDITED','DRAFT')
            """,
            (close_id.strip(),),
        ).fetchall()
    ]
    return [
        r["edc_receipt_id"]
        for r in rows
        if _norm_bank(r.get("acquirer_label") or "") == bank_n
    ]


def _bank_explicit_zero(slot: dict[str, Any] | None) -> bool:
    if not slot:
        return False
    return bool(
        slot.get("edc_explicit")
        and slot.get("qris_explicit")
        and float(slot.get("edc_expected") or 0) == 0
        and float(slot.get("qris_expected") or 0) == 0
    )


def _snapshot_bank_expected(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-bank EDC/QRIS from captured ESB snapshot — only when split keys exist."""
    out: dict[str, dict[str, Any]] = {}
    if not row.get("esb_fingerprint_sha256"):
        return out
    totals = row.get("esb_totals") or {}
    split = totals.get("payments_by_bank_split") or {}
    if not isinstance(split, dict):
        return out
    banks: set[str] = set()
    for key in split:
        ku = str(key).upper()
        if ku.startswith("EDC_"):
            banks.add(_norm_bank(key[4:]))
        elif ku.startswith("QRIS_"):
            banks.add(_norm_bank(key[5:]))
    for bank in banks:
        edc_amt: float | None = None
        qris_amt: float | None = None
        edc_explicit = False
        qris_explicit = False
        for key, val in split.items():
            ku = str(key).upper()
            if ku.startswith("EDC_") and _norm_bank(key[4:]) == bank:
                edc_amt = round(float(val), 2)
                edc_explicit = True
            elif ku.startswith("QRIS_") and _norm_bank(key[5:]) == bank:
                qris_amt = round(float(val), 2)
                qris_explicit = True
        out[bank] = {
            "edc_expected": edc_amt,
            "qris_expected": qris_amt,
            "edc_explicit": edc_explicit,
            "qris_explicit": qris_explicit,
        }
    return out


def list_outlet_banks(
    outlet_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    oid = (outlet_id or "").strip() or OUTLET_UMA
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        if not _has_table(c, "venue_close_outlet_banks"):
            return {
                "ok": True,
                "outlet_id": oid,
                "banks": [],
                "bank_config_status": "NEEDS CONFIGURATION",
            }
        rows = [
            dict(r)
            for r in c.execute(
                """
                SELECT * FROM venue_close_outlet_banks
                WHERE outlet_id=? AND status='ACTIVE'
                ORDER BY sort_order, bank_label
                """,
                (oid,),
            ).fetchall()
        ]
        return {
            "ok": True,
            "outlet_id": oid,
            "banks": rows,
            "bank_labels": [r.get("bank_label") for r in rows],
            "bank_config_status": "CONFIGURED" if rows else "NEEDS CONFIGURATION",
            "bank_count": len(rows),
        }
    finally:
        if own:
            c.close()


def configure_outlet_settlement_banks(
    outlet_id: str,
    *,
    note: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Store MANDIRI, BNI, and BRI as separate ACTIVE rows for one outlet (idempotent)."""
    oid = (outlet_id or "").strip()
    if not oid:
        raise BzgDailyCloseError("outlet_id required", code="missing_outlet")
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        ts = _vc.now_utc_iso()
        note_txt = (note or "Owner-configured settlement banks").strip()
        for i, bank in enumerate(SETTLEMENT_BANK_LABELS, start=1):
            c.execute(
                """
                INSERT OR IGNORE INTO venue_close_outlet_banks
                  (bank_config_id, outlet_id, bank_label, sort_order, status, note, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """,
                (
                    f"BANK-{oid}-{bank}",
                    oid,
                    bank,
                    i * 10,
                    note_txt,
                    ts,
                    ts,
                ),
            )
        if commit:
            c.commit()
        return list_outlet_banks(oid, conn=c)
    finally:
        if own:
            c.close()


def _shift_receipt_has_document(rec: dict[str, Any]) -> bool:
    conf = rec.get("confirmed") or {}
    doc = conf.get("document")
    if isinstance(doc, dict) and doc.get("sections"):
        return True
    ext = rec.get("extracted") or {}
    doc = ext.get("document") if isinstance(ext.get("document"), dict) else ext
    return isinstance(doc, dict) and bool(doc.get("sections"))


def _pick_authoritative_shift_receipt(
    recs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Latest human correction > confirmed raw read > latest confirmed row."""
    confirmed = [
        r
        for r in recs
        if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
    ]
    if not confirmed:
        return {}
    for rec in reversed(confirmed):
        if rec.get("human_confirm_status") == "EDITED" and _shift_receipt_has_document(rec):
            return rec
    for rec in reversed(confirmed):
        if _shift_receipt_has_document(rec):
            return rec
    return confirmed[-1]


def _document_from_shift_receipt(rec: dict[str, Any]) -> dict[str, Any] | None:
    if not rec:
        return None
    conf = rec.get("confirmed") or {}
    doc = conf.get("document")
    if isinstance(doc, dict) and doc.get("sections"):
        return doc
    ext = rec.get("extracted") or {}
    doc = ext.get("document") if isinstance(ext.get("document"), dict) else ext
    if isinstance(doc, dict) and doc.get("sections"):
        return doc
    return None


def _authoritative_shift_document(
    close_id: str,
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    recs = list_esb_closing_receipts(close_id, conn=conn)
    return _document_from_shift_receipt(_pick_authoritative_shift_receipt(recs))


def _flat_shift_to_owner_figures(flat: dict[str, Any]) -> dict[str, Any]:
    gross = flat.get("gross_sales_rp") or flat.get("gross_amount")
    return {
        "gross_sales_total": gross,
        "bills": flat.get("bills"),
        "pax": flat.get("pax"),
        "cash": flat.get("cash_rp") or flat.get("cash_amount"),
        "edc_bni": flat.get("edc_bni_rp"),
        "qris_bni": flat.get("qris_bni_rp"),
        "edc_bri": flat.get("edc_bri_rp"),
        "qris_bri": flat.get("qris_bri_rp"),
        "edc_mandiri": flat.get("edc_mandiri_rp"),
        "qris_mandiri": flat.get("qris_mandiri_rp"),
        "scott_etik": flat.get("scott_etik_rp"),
        "non_sales_executive_chef": flat.get("non_sales_executive_chef_rp"),
        "payment_total": gross,
    }


def _payments_by_bank_split_from_fields(fig: dict[str, Any]) -> dict[str, Any]:
    split: dict[str, Any] = {}
    pairs = (
        ("EDC_BNI", "edc_bni"),
        ("QRIS_BNI", "qris_bni"),
        ("EDC_BRI", "edc_bri"),
        ("QRIS_BRI", "qris_bri"),
        ("EDC_MANDIRI", "edc_mandiri"),
        ("QRIS_MANDIRI", "qris_mandiri"),
    )
    for key, fig_k in pairs:
        val = fig.get(fig_k)
        if val is not None:
            split[key] = round(float(val), 2)
    return split


def _esb_expected_by_bank(close_id: str, conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """From confirmed ESB closing document payment lines — expected EDC/QRIS per bank."""
    out: dict[str, dict[str, Any]] = {}
    doc = _authoritative_shift_document(close_id, conn)
    if not isinstance(doc, dict):
        return out
    for sec in doc.get("sections") or []:
        if sec.get("normalized_type") != "PAYMENT_METHODS":
            continue
        for ln in sec.get("lines") or []:
            nt = ln.get("normalized_type")
            bank = _norm_bank(ln.get("bank_acquirer") or "")
            if nt not in ("EDC", "QRIS") or not bank:
                continue
            amt = ln.get("human_confirmed_value")
            if amt is None:
                amt = ln.get("amount")
            if amt is None:
                continue
            slot = out.setdefault(
                bank,
                {
                    "edc_expected": 0.0,
                    "qris_expected": 0.0,
                    "edc_explicit": False,
                    "qris_explicit": False,
                },
            )
            if nt == "EDC":
                slot["edc_expected"] = round(float(amt), 2)
                slot["edc_explicit"] = True
            else:
                slot["qris_expected"] = round(float(amt), 2)
                slot["qris_explicit"] = True
    return out


def _resolve_shift_report_evidence(
    close_id: str,
    conn: sqlite3.Connection,
) -> tuple[str | None, str | None]:
    """Latest confirmed shift-report image ref/hash — for resume after reload."""
    cid = close_id.strip()
    recs = list_esb_closing_receipts(cid, conn=conn)
    confirmed = [
        r
        for r in recs
        if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
    ]
    drafts_with_image = [
        r
        for r in recs
        if r.get("human_confirm_status") == "DRAFT"
        and (r.get("image_object_ref") or r.get("content_hash"))
    ]
    for rec in reversed(confirmed + drafts_with_image):
        ref = (rec.get("image_object_ref") or rec.get("object_ref") or "").strip() or None
        ch = (rec.get("content_hash") or "").strip() or None
        if ref or ch:
            if not _weg.is_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR):
                return ref, ch
            continue
        evid_id = (rec.get("evidence_id") or "").strip()
        if evid_id and _has_table(conn, "core_evidence_records"):
            row = conn.execute(
                """
                SELECT object_ref, content_hash FROM core_evidence_records
                WHERE evidence_id=? LIMIT 1
                """,
                (evid_id,),
            ).fetchone()
            if row:
                ref = (row["object_ref"] or "").strip() or None
                ch = (row["content_hash"] or "").strip() or None
                if ref or ch:
                    if not _weg.is_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR):
                        return ref, ch
    if confirmed:
        last = confirmed[-1]
        conf = last.get("confirmed") or {}
        if conf.get("entry_source") == "OWNER_TYPED" or conf.get(
            "image_status"
        ) == "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER":
            rid = (last.get("esb_receipt_id") or cid).strip()
            ref = f"{CLOSE_RECEIPT_SCHEME}PRINTED-SHIFT-{rid}"
            ch = hashlib.sha256(ref.encode("utf-8")).hexdigest()
            return ref, ch
    return None, None


def _bank_slot_on_shift(slot: dict[str, Any] | None) -> bool:
    """True when this bank has real expected EDC/QRIS (not a silent empty default)."""
    if not slot:
        return False
    return bool(
        slot.get("edc_explicit")
        or slot.get("qris_explicit")
        or (
            slot.get("edc_expected") is not None
            and float(slot.get("edc_expected") or 0) > 0
        )
        or (
            slot.get("qris_expected") is not None
            and float(slot.get("qris_expected") or 0) > 0
        )
    )


def _shift_bank_figures_incomplete(
    close_id: str,
    conn: sqlite3.Connection,
) -> bool:
    """Confirmed shift exists but no usable per-bank EDC/QRIS amounts."""
    if not _has_confirmed_shift_receipt(close_id, conn):
        return False
    expected = _shift_expected_by_bank(close_id, conn)
    if any(_bank_slot_on_shift(s) for s in expected.values()):
        return False
    # Document lists EDC/QRIS rows with null amounts = vision/manual incomplete.
    doc = _authoritative_shift_document(close_id, conn)
    if isinstance(doc, dict):
        for sec in doc.get("sections") or []:
            if sec.get("normalized_type") != "PAYMENT_METHODS":
                continue
            for ln in sec.get("lines") or []:
                if ln.get("normalized_type") in ("EDC", "QRIS"):
                    amt = ln.get("human_confirmed_value")
                    if amt is None:
                        amt = ln.get("amount")
                    if amt is None:
                        return True
    # No bank amounts anywhere (incl. warehouse fallback already tried).
    return True


def _shift_expected_by_bank(
    close_id: str,
    conn: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    """EDC/QRIS per bank — confirmed figures, printed fallback, then warehouse split.

    Never invent empty BNI/BRI/MANDIRI slots: those become a false wall of
    "not used" after a failed vision/manual confirm. Only banks with real
    amounts (or explicit zeros) appear.
    """
    expected = _esb_expected_by_bank(close_id, conn)
    printed = printed_shift_source(close_id, conn=conn)
    split = printed.get("payments_by_bank_split") or {}
    bank_keys = {
        "BNI": ("edc_bni_rp", "qris_bni_rp"),
        "BRI": ("edc_bri_rp", "qris_bri_rp"),
        "MANDIRI": ("edc_mandiri_rp", "qris_mandiri_rp"),
    }
    for bank, (edc_k, qris_k) in bank_keys.items():
        amt_edc = split.get(f"EDC_{bank}") or printed.get(edc_k)
        amt_qris = split.get(f"QRIS_{bank}") or printed.get(qris_k)
        if bank not in expected and amt_edc is None and amt_qris is None:
            continue
        slot = expected.setdefault(
            bank,
            {
                "edc_expected": 0.0,
                "qris_expected": 0.0,
                "edc_explicit": False,
                "qris_explicit": False,
            },
        )
        if not slot.get("edc_explicit") and amt_edc is not None:
            slot["edc_expected"] = round(float(amt_edc), 2)
            slot["edc_explicit"] = True
        if not slot.get("qris_explicit") and amt_qris is not None:
            slot["qris_expected"] = round(float(amt_qris), 2)
            slot["qris_explicit"] = True
    # Warehouse ESB payment-line split — only when confirmed/printed lack banks.
    if not any(_bank_slot_on_shift(s) for s in expected.values()):
        row = _vc.get_close(close_id, conn=conn)
        if row and row.get("esb_fingerprint_sha256"):
            snap = _snapshot_bank_expected(row)
            for bank, slot in snap.items():
                if _bank_slot_on_shift(slot):
                    expected[bank] = dict(slot)
                    expected[bank]["expected_source"] = "warehouse_payment_lines"
    return expected


def list_edc_terminals(
    outlet_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    oid = (outlet_id or "").strip() or OUTLET_UMA
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_edc_terminals"):
            return {
                **HONESTY,
                "ok": True,
                "outlet_id": oid,
                "terminals": [],
                "edc_terminal_config_status": "NEEDS CONFIGURATION",
                "edc_terminal_count": 0,
                "message": "EDC terminal inventory unknown — NEEDS CONFIGURATION",
            }
        rows = [
            dict(r)
            for r in c.execute(
                """
                SELECT * FROM venue_close_edc_terminals
                WHERE outlet_id=? ORDER BY terminal_label
                """,
                (oid,),
            ).fetchall()
        ]
        status = "CONFIGURED" if rows else "NEEDS CONFIGURATION"
        return {
            **HONESTY,
            "ok": True,
            "outlet_id": oid,
            "terminals": rows,
            "edc_terminal_config_status": status,
            "edc_terminal_count": len(rows),
            "message": (
                "EDC terminals configured"
                if rows
                else "EDC terminal inventory unknown — NEEDS CONFIGURATION (no invented IDs)"
            ),
        }
    finally:
        if own:
            c.close()


def edc_card_total(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Card Total = Σ EDC batch totals when present. Never ESB card payments."""
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_edc_lines"):
            return {
                "close_id": close_id,
                "card_total_from_edc": None,
                "edc_line_count": 0,
                "basis": "NO_EDC_LINES",
                "esb_payments_are_not_edc_settlement": True,
            }
        rows = c.execute(
            """
            SELECT batch_total FROM venue_close_edc_lines WHERE close_id=?
            """,
            (close_id.strip(),),
        ).fetchall()
        if not rows:
            return {
                "close_id": close_id,
                "card_total_from_edc": None,
                "edc_line_count": 0,
                "basis": "NO_EDC_LINES",
                "esb_payments_are_not_edc_settlement": True,
            }
        total = round(sum(float(r[0]) for r in rows), 2)
        return {
            "close_id": close_id,
            "card_total_from_edc": total,
            "edc_line_count": len(rows),
            "basis": "SUM_EDC_BATCH_TOTALS",
            "esb_payments_are_not_edc_settlement": True,
        }
    finally:
        if own:
            c.close()


def list_edc_lines(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_edc_lines"):
            return []
        return [
            dict(r)
            for r in c.execute(
                "SELECT * FROM venue_close_edc_lines WHERE close_id=? ORDER BY created_at",
                (close_id.strip(),),
            ).fetchall()
        ]
    finally:
        if own:
            c.close()


def attach_edc_line(
    close_id: str,
    *,
    acquirer_label: str,
    batch_total: float,
    verified_person_id: str,
    object_ref: str | None = None,
    content_hash: str | None = None,
    txn_count: int | None = None,
    terminal_config_id: str | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Bind one EDC settlement slip to a close. Orphan amounts refused."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    bank = (acquirer_label or "").strip()
    if not bank:
        raise BzgDailyCloseError(
            "acquirer_label required", code="missing_acquirer_label"
        )
    try:
        amount = float(batch_total)
    except (TypeError, ValueError) as exc:
        raise BzgDailyCloseError(
            "batch_total must be numeric", code="invalid_amount"
        ) from exc
    if amount < 0:
        raise BzgDailyCloseError("batch_total cannot be negative", code="invalid_amount")
    ref = (object_ref or "").strip() or None
    ch = (content_hash or "").strip() or None
    if not ref and not ch:
        raise BzgDailyCloseError(
            "EDC line requires evidence object_ref or content_hash — no orphan amounts",
            code="missing_edc_evidence",
        )

    own = conn is None
    c = conn or db_connect()
    try:
        _vc.assert_catalog_writable(Path(_vc.CATALOG_DB))
        _vc._assert_perm(  # noqa: SLF001 — shared engine RBAC
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        _require_holder(row, verified_person_id=verified, conn=c, identity=identity)
        if row["state"] in _vc.TERMINAL:
            raise BzgDailyCloseError(
                f"close is terminal ({row['state']})", code="terminal_state"
            )
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        # Terminal inventory may be empty — allow evidence lines with honesty flag.
        term_cfg = list_edc_terminals(outlet_id, conn=c)
        tid = (terminal_config_id or "").strip() or None
        if tid:
            known = {t["terminal_config_id"] for t in term_cfg["terminals"]}
            if tid not in known:
                raise BzgDailyCloseError(
                    "terminal_config_id not in registry (do not invent)",
                    code="unknown_terminal",
                    http_status=409,
                )

        evid = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_EDC,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=ref,
            content_hash=ch,
            brand_id=row.get("venue_brand_id") or _vc.BRAND_UMA,
            metadata={
                "kind": "edc_settlement_slip",
                "acquirer_label": bank,
                "batch_total": amount,
                "txn_count": txn_count,
                "terminal_config_id": tid,
                "esb_payments_are_not_edc_settlement": True,
                "edc_terminal_config_status": term_cfg["edc_terminal_config_status"],
            },
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )
        line_id = f"EDC-{uuid.uuid4()}"
        ts = _vc.now_utc_iso()
        c.execute(
            """
            INSERT INTO venue_close_edc_lines (
              edc_line_id, close_id, outlet_id, terminal_config_id,
              acquirer_label, batch_total, txn_count, evidence_id,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                line_id,
                close_id,
                outlet_id,
                tid,
                bank,
                amount,
                txn_count,
                evid["evidence_id"],
                verified,
                ts,
                ts,
            ),
        )
        _audit.safe_record(
            action="venue_close.edc_line",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="edc_settlement_evidence",
            metadata={
                "edc_line_id": line_id,
                "evidence_id": evid["evidence_id"],
                "batch_total": amount,
                "acquirer_label": bank,
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        card = edc_card_total(close_id, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "edc_line_id": line_id,
            "evidence": evid,
            "close_id": close_id,
            "edc_lines": list_edc_lines(close_id, conn=c),
            "card_total": card,
            "edc_terminal_config_status": term_cfg["edc_terminal_config_status"],
        }
    finally:
        if own:
            c.close()


def attach_till_with_z_report(
    close_id: str,
    *,
    declared_cash_amount: float,
    verified_person_id: str,
    object_ref: str | None = None,
    content_hash: str | None = None,
    declared_card_amount: float | None = None,
    declared_qris_amount: float | None = None,
    declared_gross_amount: float | None = None,
    notes: str | None = None,
    source: str | None = None,
    copy_from_esb: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Till declare + POS/Z-report evidence. Refuses ESB-copy. Declared ≠ verified."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    # Explicit ESB-copy refuse (also enforced in venue_close.attach_declared_cash).
    src = (source or "").strip().lower()
    if copy_from_esb or src in (
        "esb",
        "esb_cash",
        "esb_cash_from_payments",
        "copy_esb",
        "esb_copy",
    ):
        raise BzgDailyCloseError(
            "refuses copying ESB cash into declared till",
            code="esb_copy_refused",
            http_status=400,
        )
    ref = (object_ref or "").strip() or None
    ch = (content_hash or "").strip() or None

    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        assert_human_close_enabled(outlet_id, c)

        amt = round(float(declared_cash_amount), 2)
        existing = row.get("declared_cash_amount")
        if existing is not None and round(float(existing), 2) == amt:
            till_dup = False
            if _has_table(c, "venue_close_till_evidence"):
                till_dup = bool(
                    c.execute(
                        """
                        SELECT 1 FROM venue_close_till_evidence
                        WHERE close_id=? AND declared_cash_amount=?
                        LIMIT 1
                        """,
                        (close_id, amt),
                    ).fetchone()
                )
            if till_dup or (not ref and not ch):
                out = _vc.get_close(close_id, conn=c)
                assert out
                return {
                    **out,
                    **HONESTY,
                    "idempotent": True,
                    "declared_cash_is_not_verified": True,
                }

        if not ref and not ch:
            ref, ch = _resolve_shift_report_evidence(close_id, c)
        if not ref and not ch:
            raise BzgDailyCloseError(
                "till declare requires Z-report evidence object_ref or content_hash",
                code="missing_z_report_evidence",
                details={
                    "staff_message": (
                        "Confirm the shift report before counting cash. "
                        "Upload and read the photo, or tap Continue if it is already on file."
                    ),
                },
            )

        # Declared cash path — never copies ESB.
        close_out = _vc.attach_declared_cash(
            close_id,
            declared_cash_amount=declared_cash_amount,
            verified_person_id=verified,
            object_ref=ref,
            content_hash=ch,
            notes=notes,
            source=source,
            copy_from_esb=False,
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )

        evid_z = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_Z,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=ref,
            content_hash=ch,
            brand_id=row.get("venue_brand_id") or _vc.BRAND_UMA,
            metadata={
                "kind": "pos_z_report",
                "declared_cash_amount": float(declared_cash_amount),
                "declared_card_amount": declared_card_amount,
                "declared_qris_amount": declared_qris_amount,
                "declared_gross_amount": declared_gross_amount,
                "declared_is_not_verified": True,
                "notes": (notes or "").strip() or None,
            },
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )
        till_id = f"TILL-{uuid.uuid4()}"
        ts = _vc.now_utc_iso()
        c.execute(
            """
            INSERT INTO venue_close_till_evidence (
              till_row_id, close_id, outlet_id, evidence_id,
              declared_cash_amount, declared_card_amount, declared_qris_amount,
              declared_gross_amount, z_report_object_ref,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                till_id,
                close_id,
                outlet_id,
                evid_z["evidence_id"],
                float(declared_cash_amount),
                declared_card_amount,
                declared_qris_amount,
                declared_gross_amount,
                ref,
                verified,
                ts,
                ts,
            ),
        )
        _audit.safe_record(
            action="venue_close.till_z_report",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="till_z_report_bound",
            metadata={
                "till_row_id": till_id,
                "evidence_id": evid_z["evidence_id"],
                "declared_is_not_verified": True,
            },
            conn=c,
        )
        if commit:
            c.commit()
        return {
            **close_out,
            **HONESTY,
            "till_row_id": till_id,
            "z_report_evidence": evid_z,
            "declared_cash_is_not_verified": True,
        }
    finally:
        if own:
            c.close()


def open_human_close(
    business_date: str,
    *,
    verified_person_id: str,
    outlet_id: str = OUTLET_UMA,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Open close only when outlet human_close_enabled. Defaults Uma Blu."""
    oid = (outlet_id or OUTLET_UMA).strip()
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        cfg = assert_human_close_enabled(oid, c)
        # Roster/oversight gate before open — authorisation ≠ attribution.
        authz = _vc.person_authorised_for_venue_close(
            verified_person_id,
            venue_brand_id=str(cfg.get("venue_brand_id") or _vc.BRAND_UMA),
            entity_id=str(cfg.get("entity_id") or _vc.ENTITY_BZG),
            conn=c,
        )
        if not authz.get("allowed"):
            raise BzgDailyCloseError(
                authz.get("message") or "This close is not on your assignment.",
                code="forbidden",
                http_status=403,
            )
        out = _vc.open_or_get(
            business_date,
            verified_person_id=verified_person_id,
            entity_id=cfg["entity_id"],
            venue_brand_id=cfg["venue_brand_id"],
            identity=identity,
            conn=c,
            commit=False,
        )
        # Best-effort outlet_id stamp when column present (BZG-XOUTLET-1).
        cols = {r[1] for r in c.execute("PRAGMA table_info(venue_daily_closes)")}
        if "outlet_id" in cols and out.get("close_id"):
            c.execute(
                "UPDATE venue_daily_closes SET outlet_id=?, updated_at=? WHERE close_id=?",
                (oid, _vc.now_utc_iso(), out["close_id"]),
            )
            refreshed = _vc.get_close(out["close_id"], conn=c)
            if refreshed:
                out = {**out, **refreshed, "created": out.get("created")}
        # Multi-closer take attribution. Concurrent take → 409 + audit.
        taken = _vc.take_open_venue_close(
            str(out["close_id"]),
            verified_person_id=verified_person_id,
            identity=identity,
            conn=c,
            commit=False,
        )
        out = {**out, **taken, "created": out.get("created"), "authz": authz}
        if commit:
            c.commit()
        return {
            **out,
            **HONESTY,
            "outlet_id": oid,
            "outlet_config": cfg,
            "edc_terminals": list_edc_terminals(oid, conn=c),
        }
    finally:
        if own:
            c.close()


def overview(
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Config surface for UI — outlets, activation, terminal honesty."""
    own = conn is None
    c = conn or db_connect()
    try:
        configs = list_outlet_configs(c)
        enabled = [x for x in configs if x.get("human_close_enabled")]
        active_pol = 0
        if _has_table(c, "venue_close_variance_policies"):
            active_pol = int(
                c.execute(
                    "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
                ).fetchone()[0]
            )
        registry_n = len(_outlets.list_outlets(c))
        uma_terms = list_edc_terminals(OUTLET_UMA, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "title": "BZG Daily Close",
            "outlets": configs,
            "outlet_count": len(configs),
            "human_close_enabled_outlet_ids": [x["outlet_id"] for x in enabled],
            "human_close_enabled_count": len(enabled),
            "registry_outlet_count": registry_n,
            "active_variance_policies": active_pol,
            "uma_edc_terminals": uma_terms,
            "mobile_close_path": "/uma-blu-close",
            "bzg_close_path": "/bzg/daily-close",
            "message": (
                "One BZG Daily Close engine (venue_close). Config for Owner outlets; "
                "only Uma Blu human-activated. Multi EDC receipts (0..N) with separate "
                "EDC card + QRIS; vision draft ≠ truth. EDC terminals NEEDS CONFIGURATION "
                "until Owner names inventory (free-text bank still works). "
                "Settlement API UNAVAILABLE."
            ),
            "person_id": (person_id or "").strip() or None,
        }
    finally:
        if own:
            c.close()


def _dumps(obj: Any) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _loads(s: Any) -> Any:
    if s is None or s == "":
        return None
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(str(s))
    except (TypeError, json.JSONDecodeError):
        return None


def _amt(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return float(default)
    try:
        n = float(v)
    except (TypeError, ValueError) as exc:
        raise BzgDailyCloseError("amount must be numeric", code="invalid_amount") from exc
    if n < 0:
        raise BzgDailyCloseError("amount cannot be negative", code="invalid_amount")
    return round(n, 2)


def _entry_source_from_vision(
    conn: sqlite3.Connection,
    *,
    vision_event_id: str | None,
    manual_entry: bool,
) -> str:
    """MANUAL when staff typed figures; VISION_CONFIRMED only after successful extract."""
    if manual_entry:
        return "MANUAL"
    vid = (vision_event_id or "").strip()
    if not vid:
        return "MANUAL"
    row = conn.execute(
        "SELECT extracted_json FROM venue_close_vision_events WHERE vision_event_id=?",
        (vid,),
    ).fetchone()
    if not row:
        return "MANUAL"
    ext = _loads(row["extracted_json"]) or {}
    if ext.get("extraction_unavailable") or ext.get("extraction_status") == "UNAVAILABLE":
        return "MANUAL"
    return "VISION_CONFIRMED"


def _record_vision_event(
    conn: sqlite3.Connection,
    *,
    close_id: str,
    target_kind: str,
    target_id: str | None,
    provider: str,
    model: str | None,
    confidence: float | None,
    confidence_band: str | None,
    extracted: dict[str, Any],
    image_object_ref: str | None,
    content_hash: str | None,
    actor_person_id: str | None,
) -> str:
    eid = f"VIS-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO venue_close_vision_events (
          vision_event_id, close_id, target_kind, target_id, provider, model,
          confidence, confidence_band, extracted_json, image_object_ref,
          content_hash, actor_person_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eid,
            close_id,
            target_kind,
            target_id,
            provider,
            model,
            confidence,
            confidence_band,
            _dumps(extracted) or "{}",
            image_object_ref,
            content_hash,
            actor_person_id,
            _vc.now_utc_iso(),
        ),
    )
    return eid


def list_edc_receipts(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_edc_receipts"):
            return []
        rows = [
            dict(r)
            for r in c.execute(
                """
                SELECT * FROM venue_close_edc_receipts
                WHERE close_id=? ORDER BY created_at
                """,
                (close_id.strip(),),
            ).fetchall()
        ]
        out: list[dict[str, Any]] = []
        for r in rows:
            r["extracted"] = _loads(r.pop("extracted_json", None))
            r["confirmed"] = _loads(r.pop("confirmed_json", None))
            r["duplicate_warn_detail"] = _loads(r.pop("duplicate_warn_json", None))
            r["duplicate_warn"] = bool(r.get("duplicate_warn"))
            out.append(r)
        return out
    finally:
        if own:
            c.close()


def receipt_totals(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Aggregate confirmed (or all non-draft) receipt amounts. QRIS never in EDC."""
    own = conn is None
    c = conn or db_connect()
    try:
        receipts = list_edc_receipts(close_id, conn=c)
        # Only CURRENT confirmed/edited evidence counts — SUPERSEDED kept for audit only.
        current = [
            r
            for r in receipts
            if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
            and str(r.get("evidence_role") or "CURRENT").upper() == "CURRENT"
            and int(r.get("counted_in_totals") if r.get("counted_in_totals") is not None else 1) == 1
        ]
        superseded = [
            r for r in receipts if str(r.get("evidence_role") or "").upper() == "SUPERSEDED"
        ]
        total_edc = round(sum(float(r.get("edc_card_amount") or 0) for r in current), 2)
        total_qris = round(sum(float(r.get("qris_amount") or 0) for r in current), 2)
        return {
            "close_id": close_id,
            "receipt_count": len(receipts),
            "confirmed_receipt_count": len(current),
            "current_receipt_count": len(current),
            "superseded_receipt_count": len(superseded),
            "draft_receipt_count": len(
                [r for r in receipts if r.get("human_confirm_status") == "DRAFT"]
            ),
            "TOTAL_EDC": total_edc,
            "TOTAL_QRIS": total_qris,
            "TOTAL_CARD_QRIS": round(total_edc + total_qris, 2),
            "qris_never_merged_into_card": True,
            "basis": "SUM_CURRENT_CONFIRMED_EDC_RECEIPTS",
            "superseded_excluded_from_totals": True,
            "esb_payments_are_not_edc_settlement": True,
        }
    finally:
        if own:
            c.close()


def unused_configured_terminals(
    close_id: str,
    outlet_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Configured terminals with no receipt today — available options, not placeholders."""
    own = conn is None
    c = conn or db_connect()
    try:
        terms = list_edc_terminals(outlet_id, conn=c)
        receipts = list_edc_receipts(close_id, conn=c)
        used_ids = {
            (r.get("terminal_config_id") or "").strip()
            for r in receipts
            if (r.get("terminal_config_id") or "").strip()
        }
        unused = [
            t
            for t in terms["terminals"]
            if t["terminal_config_id"] not in used_ids
        ]
        return {
            "outlet_id": outlet_id,
            "close_id": close_id,
            "configured_count": terms["edc_terminal_count"],
            "used_terminal_ids": sorted(used_ids),
            "unused_terminals": unused,
            "unused_count": len(unused),
            "edc_terminal_config_status": terms["edc_terminal_config_status"],
            "no_fake_placeholders": True,
            "message": (
                "Unused configured terminals are available options only — "
                "no placeholder receipt rows created"
            ),
        }
    finally:
        if own:
            c.close()


def _duplicate_warn(
    conn: sqlite3.Connection,
    *,
    close_id: str,
    content_hash: str | None,
    batch_ref: str | None,
    edc_card_amount: float,
    qris_amount: float,
    settlement_batch_date: str | None,
    exclude_receipt_id: str | None = None,
) -> dict[str, Any]:
    receipts = list_edc_receipts(close_id, conn=conn)
    hits: list[dict[str, Any]] = []
    ch = (content_hash or "").strip()
    ref = (batch_ref or "").strip()
    date = (settlement_batch_date or "").strip()
    total = round(edc_card_amount + qris_amount, 2)
    for r in receipts:
        if exclude_receipt_id and r.get("edc_receipt_id") == exclude_receipt_id:
            continue
        if str(r.get("evidence_role") or "CURRENT").upper() == "SUPERSEDED":
            continue
        if int(r.get("counted_in_totals") if r.get("counted_in_totals") is not None else 1) == 0:
            continue
        reasons: list[str] = []
        if ch and (r.get("content_hash") or "").strip() == ch:
            reasons.append("content_hash")
        if ref and (r.get("batch_ref") or "").strip() == ref:
            reasons.append("batch_ref")
        r_total = round(float(r.get("edc_card_amount") or 0) + float(r.get("qris_amount") or 0), 2)
        r_date = (r.get("settlement_batch_date") or "").strip()
        if total > 0 and r_total == total and date and r_date == date:
            reasons.append("amount_and_date")
        if reasons:
            hits.append(
                {
                    "edc_receipt_id": r.get("edc_receipt_id"),
                    "reasons": reasons,
                    "acquirer_label": r.get("acquirer_label"),
                }
            )
    return {
        "duplicate_warn": bool(hits),
        "matches": hits,
        "silent_delete": False,
        "message": (
            "Possible duplicate receipt — not deleted; human must decide"
            if hits
            else None
        ),
    }


def extract_edc_receipt_draft(
    close_id: str,
    *,
    verified_person_id: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    image_object_ref: str | None = None,
    content_hash: str | None = None,
    fixture_fields: dict[str, Any] | None = None,
    bank_hint: str | None = None,
    esb_edc_expected: float | None = None,
    esb_qris_expected: float | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Vision draft for a bank card photo. AI is NOT accounting truth."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        # Load stored phone upload when client sent object_ref only.
        if not image_bytes and image_object_ref:
            image_bytes, mime_type = load_close_receipt_bytes(image_object_ref)
        # Explicit fixture_fields keep test/dev path; phone UX omits fixture when photo present.
        draft = _vision.extract_edc_receipt(
            image_bytes=image_bytes,
            mime_type=mime_type,
            fixture_fields=fixture_fields,
            bank_hint=bank_hint,
            esb_edc_expected=esb_edc_expected,
            esb_qris_expected=esb_qris_expected,
        )
        extracted = draft.get("extracted") or {}
        unavailable = bool(draft.get("extraction_unavailable"))
        staff_msg = None
        if unavailable:
            staff_msg = draft.get("staff_message") or _vision.STAFF_VISION_UNAVAILABLE
            extracted = {
                **extracted,
                "extraction_unavailable": True,
                "extraction_status": "UNAVAILABLE",
            }
        ref = (image_object_ref or "").strip() or None
        ch = (content_hash or "").strip() or None
        if image_bytes and not ch:
            ch = hashlib.sha256(image_bytes).hexdigest()
        if not ref and ch:
            ref = f"vision://edc/{ch[:16]}"
        vid = _record_vision_event(
            c,
            close_id=close_id,
            target_kind="EDC_RECEIPT",
            target_id=None,
            provider=str(draft.get("provider") or "unknown"),
            model=draft.get("model"),
            confidence=extracted.get("ocr_confidence"),
            confidence_band=extracted.get("ocr_confidence_band"),
            extracted=extracted,
            image_object_ref=ref,
            content_hash=ch,
            actor_person_id=verified,
        )
        _audit.safe_record(
            action="venue_close.edc_receipt_extract",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code=(
                "vision_extract_unavailable"
                if unavailable
                else "vision_draft_not_truth"
            ),
            metadata={
                "vision_event_id": vid,
                "provider": draft.get("provider"),
                "extraction_unavailable": unavailable,
                "ai_is_not_accounting_truth": True,
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "vision_event_id": vid,
            "draft": draft,
            "extracted": extracted,
            "extraction_unavailable": unavailable,
            "staff_message": staff_msg,
            "message": staff_msg if unavailable else draft.get("message"),
            "manual_entry_ok": True if unavailable else False,
            "image_object_ref": ref,
            "content_hash": ch,
            "ai_is_not_accounting_truth": True,
            "bank_hint": _norm_bank(bank_hint) if bank_hint else None,
            "esb_edc_expected": esb_edc_expected,
            "esb_qris_expected": esb_qris_expected,
            "next": (
                "Receipt reading unavailable — Retry Reading or Enter Manually. Photo kept."
                if unavailable
                else "Confirm or Edit — replaces any prior receipt for this bank"
            ),
        }
    finally:
        if own:
            c.close()


def confirm_edc_receipt(
    close_id: str,
    *,
    verified_person_id: str,
    acquirer_label: str,
    edc_card_amount: float | None = None,
    qris_amount: float | None = None,
    action: str = "confirm",
    object_ref: str | None = None,
    content_hash: str | None = None,
    terminal_config_id: str | None = None,
    terminal_label: str | None = None,
    settlement_batch_date: str | None = None,
    batch_ref: str | None = None,
    ocr_confidence: float | None = None,
    extracted: dict[str, Any] | None = None,
    confirmed_overrides: dict[str, Any] | None = None,
    vision_event_id: str | None = None,
    manual_entry: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Human Looks Correct / Edit — persist confirmed EDC+QRIS separately."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    bank = (acquirer_label or "").strip()
    if not bank:
        raise BzgDailyCloseError(
            "acquirer_label required (free-text bank OK)",
            code="missing_acquirer_label",
        )
    act = (action or "confirm").strip().lower()
    if act not in ("confirm", "edit", "looks_correct"):
        raise BzgDailyCloseError("action must be confirm|edit|looks_correct", code="invalid_action")
    status = "EDITED" if act == "edit" else "CONFIRMED"

    overrides = confirmed_overrides or {}
    edc = _amt(
        overrides.get("edc_card_amount", edc_card_amount)
        if "edc_card_amount" in overrides or edc_card_amount is not None
        else 0.0
    )
    qris = _amt(
        overrides.get("qris_amount", qris_amount)
        if "qris_amount" in overrides or qris_amount is not None
        else 0.0
    )
    if edc == 0.0 and qris == 0.0:
        raise BzgDailyCloseError(
            "receipt needs edc_card_amount and/or qris_amount > 0",
            code="missing_amounts",
        )
    total = round(edc + qris, 2)
    ref = (object_ref or overrides.get("object_ref") or "").strip() or None
    ch = (content_hash or overrides.get("content_hash") or "").strip() or None

    batch = (batch_ref or overrides.get("batch_ref") or "").strip() or None
    sdate = (
        settlement_batch_date or overrides.get("settlement_batch_date") or ""
    ).strip() or None
    tlabel = (terminal_label or overrides.get("terminal_label") or "").strip() or None
    tid = (terminal_config_id or overrides.get("terminal_config_id") or "").strip() or None

    own = conn is None
    c = conn or db_connect()
    try:
        if not ref and not ch:
            ref, ch = _resolve_shift_report_evidence(close_id, c)
        if not ref and not ch:
            raise BzgDailyCloseError(
                "EDC receipt requires image evidence object_ref or content_hash",
                code="missing_edc_evidence",
                details={
                    "staff_message": (
                        "Add a bank receipt photo, or confirm the shift report first "
                        "so amounts can be saved."
                    ),
                },
            )
        _vc.assert_catalog_writable(Path(_vc.CATALOG_DB))
        _vc._assert_perm(  # noqa: SLF001
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        _require_holder(row, verified_person_id=verified, conn=c, identity=identity)
        if row["state"] in _vc.TERMINAL:
            raise BzgDailyCloseError(
                f"close is terminal ({row['state']})", code="terminal_state"
            )
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        term_cfg = list_edc_terminals(outlet_id, conn=c)
        if tid:
            known = {t["terminal_config_id"] for t in term_cfg["terminals"]}
            if tid not in known:
                raise BzgDailyCloseError(
                    "terminal_config_id not in registry (do not invent)",
                    code="unknown_terminal",
                    http_status=409,
                )

        dup = _duplicate_warn(
            c,
            close_id=close_id,
            content_hash=ch,
            batch_ref=batch,
            edc_card_amount=edc,
            qris_amount=qris,
            settlement_batch_date=sdate,
        )

        # One CURRENT evidence state per bank: prior CURRENT for this bank → SUPERSEDED
        ts_super = _vc.now_utc_iso()
        prior_ids = _current_edc_receipt_ids_for_bank(c, close_id, bank)
        preservation: list[dict[str, Any]] = []
        for pid in prior_ids:
            prow = c.execute(
                "SELECT evidence_id FROM venue_close_edc_receipts WHERE edc_receipt_id=?",
                (pid,),
            ).fetchone()
            if prow and prow["evidence_id"]:
                preservation.append(
                    _evidence_preservation_snapshot(c, str(prow["evidence_id"]))
                )
        prior = [{"edc_receipt_id": pid} for pid in prior_ids]
        # Will set superseded_by after new rid known — mark temporarily
        for pr in prior:
            c.execute(
                """
                UPDATE venue_close_edc_receipts
                SET evidence_role='SUPERSEDED', counted_in_totals=0,
                    superseded_at=?, supersede_reason=?, updated_at=?
                WHERE edc_receipt_id=?
                """,
                (
                    ts_super,
                    "Replaced by corrected bank receipt — previous attempt kept in audit, not counted",
                    ts_super,
                    pr["edc_receipt_id"],
                ),
            )

        evid = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_EDC,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=ref,
            content_hash=ch,
            brand_id=row.get("venue_brand_id") or _vc.BRAND_UMA,
            metadata={
                "kind": "edc_receipt",
                "acquirer_label": bank,
                "edc_card_amount": edc,
                "qris_amount": qris,
                "receipt_total": total,
                "batch_ref": batch,
                "settlement_batch_date": sdate,
                "terminal_config_id": tid,
                "human_confirm_status": status,
                "qris_never_merged_into_card": True,
                "ai_is_not_accounting_truth": True,
                "duplicate_warn": dup["duplicate_warn"],
            },
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )

        rid = f"EDCR-{uuid.uuid4()}"
        ts = _vc.now_utc_iso()
        extracted_obj = extracted or {}
        entry_source = _entry_source_from_vision(
            c, vision_event_id=vision_event_id, manual_entry=manual_entry
        )
        confirmed_obj = {
            "acquirer_label": bank,
            "edc_card_amount": edc,
            "qris_amount": qris,
            "receipt_total": total,
            "batch_ref": batch,
            "settlement_batch_date": sdate,
            "terminal_config_id": tid,
            "terminal_label": tlabel,
            "action": act,
            "entry_source": entry_source,
            "vision_extract_succeeded": entry_source == "VISION_CONFIRMED",
            "confirmed_by_person_id": verified,
            "confirmed_at": ts,
        }
        conf_val = ocr_confidence
        if conf_val is None and isinstance(extracted_obj, dict):
            conf_val = extracted_obj.get("ocr_confidence")
        band = None
        if isinstance(extracted_obj, dict):
            band = extracted_obj.get("ocr_confidence_band")
        if band is None and conf_val is not None:
            band = _vision._confidence_band(float(conf_val))  # noqa: SLF001

        c.execute(
            """
            INSERT INTO venue_close_edc_receipts (
              edc_receipt_id, close_id, outlet_id, acquirer_label,
              terminal_config_id, terminal_label, settlement_batch_date,
              edc_card_amount, qris_amount, receipt_total, batch_ref,
              image_object_ref, content_hash, evidence_id,
              ocr_confidence, ocr_confidence_band,
              extracted_json, confirmed_json, human_confirm_status,
              confirmed_by_person_id, confirmed_at,
              duplicate_warn, duplicate_warn_json,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                close_id,
                outlet_id,
                bank,
                tid,
                tlabel,
                sdate,
                edc,
                qris,
                total,
                batch,
                ref,
                ch,
                evid["evidence_id"],
                conf_val,
                band,
                _dumps(extracted_obj),
                _dumps(confirmed_obj),
                status,
                verified,
                ts,
                1 if dup["duplicate_warn"] else 0,
                _dumps(dup),
                verified,
                ts,
                ts,
            ),
        )
        # New row is the only CURRENT counted evidence for this bank
        c.execute(
            """
            UPDATE venue_close_edc_receipts
            SET evidence_role='CURRENT', counted_in_totals=1, updated_at=?
            WHERE edc_receipt_id=?
            """,
            (ts, rid),
        )
        for pr in prior:
            c.execute(
                """
                UPDATE venue_close_edc_receipts
                SET superseded_by=?, updated_at=?
                WHERE edc_receipt_id=?
                """,
                (rid, ts, pr["edc_receipt_id"]),
            )
        for snap in preservation:
            _assert_evidence_preservation_intact(c, snap)
        if vision_event_id:
            c.execute(
                """
                UPDATE venue_close_vision_events
                SET target_id=? WHERE vision_event_id=? AND close_id=?
                """,
                (rid, vision_event_id, close_id),
            )
        _audit.safe_record(
            action="venue_close.edc_receipt_confirm",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code=(
                "manual_entry_edc_receipt"
                if entry_source == "MANUAL"
                else "human_confirm_edc_receipt"
            ),
            metadata={
                "edc_receipt_id": rid,
                "evidence_id": evid["evidence_id"],
                "edc_card_amount": edc,
                "qris_amount": qris,
                "receipt_total": total,
                "human_confirm_status": status,
                "entry_source": entry_source,
                "duplicate_warn": dup["duplicate_warn"],
                "ai_is_not_accounting_truth": True,
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        totals = receipt_totals(close_id, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "edc_receipt_id": rid,
            "evidence": evid,
            "close_id": close_id,
            "human_confirm_status": status,
            "entry_source": entry_source,
            "edc_card_amount": edc,
            "qris_amount": qris,
            "receipt_total": total,
            "duplicate_warn": dup["duplicate_warn"],
            "duplicate_warn_detail": dup,
            "edc_receipts": list_edc_receipts(close_id, conn=c),
            "receipt_totals": totals,
            "bank_cards": bank_cards(close_id, conn=c),
            "unused_terminals": unused_configured_terminals(close_id, outlet_id, conn=c),
            "edc_terminal_config_status": term_cfg["edc_terminal_config_status"],
            "ai_is_not_accounting_truth": True,
        }
    finally:
        if own:
            c.close()


def list_esb_closing_receipts(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        if not _has_table(c, "venue_close_esb_closing_receipts"):
            return []
        rows = [
            dict(r)
            for r in c.execute(
                """
                SELECT * FROM venue_close_esb_closing_receipts
                WHERE close_id=? ORDER BY created_at
                """,
                (close_id.strip(),),
            ).fetchall()
        ]
        out: list[dict[str, Any]] = []
        for r in rows:
            r["extracted"] = _loads(r.pop("extracted_json", None))
            r["confirmed"] = _loads(r.pop("confirmed_json", None))
            r["api_mismatch_detail"] = _loads(r.pop("api_mismatch_json", None))
            r["api_mismatch"] = bool(r.get("api_mismatch"))
            out.append(r)
        return out
    finally:
        if own:
            c.close()


def _api_vs_receipt_mismatch(
    close_row: dict[str, Any],
    *,
    cash_amount: float | None,
    edc_card_amount: float | None,
    qris_amount: float | None,
) -> dict[str, Any]:
    totals = close_row.get("esb_totals") or {}
    diffs: list[dict[str, Any]] = []
    pairs = (
        ("cash", cash_amount, totals.get("cash_from_payments")),
        ("edc_card", edc_card_amount, totals.get("card_from_payments")),
        ("qris", qris_amount, totals.get("qris_from_payments")),
    )
    for name, receipt_v, api_v in pairs:
        if receipt_v is None or api_v is None:
            continue
        rv = round(float(receipt_v), 2)
        av = round(float(api_v), 2)
        if rv != av:
            diffs.append(
                {
                    "field": name,
                    "receipt_amount": rv,
                    "api_amount": av,
                    "variance": round(rv - av, 2),
                }
            )
    return {
        "api_mismatch": bool(diffs),
        "diffs": diffs,
        "silent_overwrite": False,
        "message": (
            "ESB closing receipt ≠ live ESB API — visible exception; API not overwritten"
            if diffs
            else None
        ),
        "dual_source_kept": True,
    }


def extract_esb_closing_receipt_draft(
    close_id: str,
    *,
    verified_person_id: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    image_object_ref: str | None = None,
    content_hash: str | None = None,
    fixture_fields: dict[str, Any] | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        if not image_bytes and image_object_ref:
            image_bytes, mime_type = load_close_receipt_bytes(image_object_ref)
        # Explicit fixture_fields keep test/dev path; phone UX omits fixture when photo present.
        draft = _vision.extract_esb_closing_receipt(
            image_bytes=image_bytes,
            mime_type=mime_type,
            fixture_fields=fixture_fields,
        )
        extracted = draft.get("extracted") or {}
        unavailable = bool(draft.get("extraction_unavailable"))
        staff_msg = None
        if unavailable:
            staff_msg = draft.get("staff_message") or _vision.STAFF_VISION_UNAVAILABLE
            extracted = {
                **extracted,
                "extraction_unavailable": True,
                "extraction_status": "UNAVAILABLE",
            }
        ref = (image_object_ref or "").strip() or None
        ch = (content_hash or "").strip() or None
        if image_bytes and not ch:
            ch = hashlib.sha256(image_bytes).hexdigest()
        if not ref and ch:
            ref = f"vision://esb/{ch[:16]}"
        mismatch = _api_vs_receipt_mismatch(
            row,
            cash_amount=extracted.get("cash_amount"),
            edc_card_amount=extracted.get("edc_card_amount"),
            qris_amount=extracted.get("qris_amount"),
        )
        vid = _record_vision_event(
            c,
            close_id=close_id,
            target_kind="ESB_CLOSING_RECEIPT",
            target_id=None,
            provider=str(draft.get("provider") or "unknown"),
            model=draft.get("model"),
            confidence=extracted.get("ocr_confidence"),
            confidence_band=extracted.get("ocr_confidence_band"),
            extracted={**extracted, "api_mismatch_preview": mismatch},
            image_object_ref=ref,
            content_hash=ch,
            actor_person_id=verified,
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "vision_event_id": vid,
            "draft": draft,
            "extracted": extracted,
            "document": extracted if isinstance(extracted, dict) else None,
            "extraction_unavailable": unavailable,
            "staff_message": staff_msg,
            "message": staff_msg if unavailable else draft.get("message"),
            "manual_entry_ok": True if unavailable else False,
            "api_mismatch_preview": mismatch,
            "image_object_ref": ref,
            "content_hash": ch,
            "ai_is_not_accounting_truth": True,
            "next": (
                "Receipt reading unavailable — Retry Reading or Enter Manually. Photo kept."
                if unavailable
                else "Looks Correct / Edit — human confirm required; API snapshot kept"
            ),
        }
    finally:
        if own:
            c.close()


def confirm_esb_closing_receipt(
    close_id: str,
    *,
    verified_person_id: str,
    action: str = "confirm",
    object_ref: str | None = None,
    content_hash: str | None = None,
    cash_amount: float | None = None,
    edc_card_amount: float | None = None,
    qris_amount: float | None = None,
    gross_amount: float | None = None,
    ocr_confidence: float | None = None,
    extracted: dict[str, Any] | None = None,
    confirmed_overrides: dict[str, Any] | None = None,
    vision_event_id: str | None = None,
    manual_entry: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    act = (action or "confirm").strip().lower()
    if act not in ("confirm", "edit", "looks_correct"):
        raise BzgDailyCloseError("action must be confirm|edit|looks_correct", code="invalid_action")
    status = "EDITED" if act == "edit" else "CONFIRMED"
    overrides = confirmed_overrides or {}
    cash = overrides.get("cash_amount", cash_amount)
    edc = overrides.get("edc_card_amount", edc_card_amount)
    qris = overrides.get("qris_amount", qris_amount)
    gross = overrides.get("gross_amount", gross_amount)
    cash_f = None if cash is None else _amt(cash)
    edc_f = None if edc is None else _amt(edc)
    qris_f = None if qris is None else _amt(qris)
    gross_f = None if gross is None else _amt(gross)
    ref = (object_ref or overrides.get("object_ref") or "").strip() or None
    ch = (content_hash or overrides.get("content_hash") or "").strip() or None
    if ref:
        try:
            _weg.refuse_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR, label="ESB receipt")
        except ValueError as exc:
            raise BzgDailyCloseError(str(exc), code="quarantined_evidence") from exc

    own = conn is None
    c = conn or db_connect()
    try:
        if not ref and not ch:
            ref, ch = _resolve_shift_report_evidence(close_id, c)
        if not ref and not ch:
            raise BzgDailyCloseError(
                "ESB closing receipt requires image evidence",
                code="missing_esb_receipt_evidence",
                details={
                    "staff_message": (
                        "Shift report photo is missing. Upload a photo first, "
                        "then tap Read shift report."
                    ),
                },
            )
        _vc.assert_catalog_writable(Path(_vc.CATALOG_DB))
        _vc._assert_perm(  # noqa: SLF001
            verified_person_id=verified,
            permission_code="venue.close.submit",
            conn=c,
        )
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        _require_holder(row, verified_person_id=verified, conn=c, identity=identity)
        if not row.get("esb_fingerprint_sha256"):
            raise BzgDailyCloseError(
                "live ESB API snapshot required before ESB receipt confirm",
                code="missing_esb_api_snapshot",
                http_status=409,
            )
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        mismatch = _api_vs_receipt_mismatch(
            row, cash_amount=cash_f, edc_card_amount=edc_f, qris_amount=qris_f
        )
        # Dual source: never overwrite API totals on the close row.
        evid = _evidence.submit_evidence(
            entity_id=row["entity_id"],
            evidence_type=EVIDENCE_ESB_RECEIPT,
            governed_object_type="venue_daily_close",
            governed_object_id=close_id,
            verified_person_id=verified,
            source_type="HUMAN",
            object_ref=ref,
            content_hash=ch,
            brand_id=row.get("venue_brand_id") or _vc.BRAND_UMA,
            metadata={
                "kind": "esb_closing_receipt",
                "cash_amount": cash_f,
                "edc_card_amount": edc_f,
                "qris_amount": qris_f,
                "gross_amount": gross_f,
                "api_mismatch": mismatch["api_mismatch"],
                "dual_source_kept": True,
                "silent_overwrite": False,
                "ai_is_not_accounting_truth": True,
            },
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )
        rid = f"ESBR-{uuid.uuid4()}"
        ts = _vc.now_utc_iso()
        extracted_obj = extracted or {}
        entry_source = _entry_source_from_vision(
            c, vision_event_id=vision_event_id, manual_entry=manual_entry
        )
        # Full document is authoritative; flat cash/edc/qris are derived mirrors only.
        confirmed_doc = None
        if isinstance(overrides.get("document"), dict):
            confirmed_doc = overrides.get("document")
        elif isinstance(extracted_obj, dict) and extracted_obj.get("sections"):
            confirmed_doc = extracted_obj
        if isinstance(confirmed_doc, dict) and confirmed_doc.get("sections"):
            # Re-derive from human-edited section lines (document is authority)
            try:
                from core import bzg_close_vision as _vis

                confirmed_doc = _vis.normalize_esb_document(
                    {
                        "business_date": confirmed_doc.get("business_date"),
                        "ocr_confidence": confirmed_doc.get("ocr_confidence"),
                        "sections": [
                            {
                                "raw_title": s.get("raw_title"),
                                "lines": [
                                    {
                                        "raw_label": ln.get("raw_label"),
                                        "quantity": ln.get("quantity"),
                                        "amount": ln.get("human_confirmed_value")
                                        if ln.get("human_confirmed_value") is not None
                                        else ln.get("amount"),
                                        "raw_value": ln.get("raw_value"),
                                        "confidence": ln.get("confidence"),
                                    }
                                    for ln in (s.get("lines") or [])
                                ],
                            }
                            for s in (confirmed_doc.get("sections") or [])
                        ],
                    }
                )
                # Preserve human_confirmed_value on re-normalized lines by amount match
            except Exception:
                pass
            # Apply flat overrides into derived mirrors if human edited headline fields
            der = dict(confirmed_doc.get("derived") or {})
            if cash_f is not None:
                der["cash_amount"] = cash_f
                der["total_cash"] = cash_f
            if edc_f is not None:
                der["edc_card_amount"] = edc_f
                der["total_edc"] = edc_f
            if qris_f is not None:
                der["qris_amount"] = qris_f
                der["total_qris"] = qris_f
            if gross_f is not None:
                der["gross_amount"] = gross_f
            confirmed_doc = {**confirmed_doc, "derived": der}
            # Prefer document-derived flats when caller omitted headline amounts
            if cash_f is None:
                cash_f = der.get("cash_amount")
            if edc_f is None:
                edc_f = der.get("edc_card_amount")
            if qris_f is None:
                qris_f = der.get("qris_amount")
            if gross_f is None:
                gross_f = der.get("gross_amount")
        confirmed_obj = {
            "cash_amount": cash_f,
            "edc_card_amount": edc_f,
            "qris_amount": qris_f,
            "gross_amount": gross_f,
            "document": confirmed_doc,
            "schema_version": (confirmed_doc or {}).get("schema_version") if isinstance(confirmed_doc, dict) else None,
            "action": act,
            "entry_source": entry_source,
            "vision_extract_succeeded": entry_source == "VISION_CONFIRMED",
            "confirmed_by_person_id": verified,
            "confirmed_at": ts,
        }
        conf_val = ocr_confidence
        if conf_val is None and isinstance(extracted_obj, dict):
            conf_val = extracted_obj.get("ocr_confidence")
        band = None
        if isinstance(extracted_obj, dict):
            band = extracted_obj.get("ocr_confidence_band")
        c.execute(
            """
            INSERT INTO venue_close_esb_closing_receipts (
              esb_receipt_id, close_id, outlet_id, image_object_ref, content_hash,
              evidence_id, extracted_json, confirmed_json,
              cash_amount, edc_card_amount, qris_amount, gross_amount,
              ocr_confidence, ocr_confidence_band, human_confirm_status,
              confirmed_by_person_id, confirmed_at,
              api_mismatch, api_mismatch_json,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                close_id,
                outlet_id,
                ref,
                ch,
                evid["evidence_id"],
                _dumps(extracted_obj),
                _dumps(confirmed_obj),
                cash_f,
                edc_f,
                qris_f,
                gross_f,
                conf_val,
                band,
                status,
                verified,
                ts,
                1 if mismatch["api_mismatch"] else 0,
                _dumps(mismatch),
                verified,
                ts,
                ts,
            ),
        )
        if vision_event_id:
            c.execute(
                """
                UPDATE venue_close_vision_events
                SET target_id=? WHERE vision_event_id=? AND close_id=?
                """,
                (rid, vision_event_id, close_id),
            )
        _audit.safe_record(
            action="venue_close.esb_receipt_confirm",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            identity_assurance=(identity or {}).get("identity_assurance"),
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code=(
                "manual_entry_esb_receipt"
                if entry_source == "MANUAL"
                else "human_confirm_esb_receipt"
            ),
            metadata={
                "esb_receipt_id": rid,
                "api_mismatch": mismatch["api_mismatch"],
                "entry_source": entry_source,
                "dual_source_kept": True,
                **HONESTY,
            },
            conn=c,
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "esb_receipt_id": rid,
            "evidence": evid,
            "close_id": close_id,
            "human_confirm_status": status,
            "entry_source": entry_source,
            "api_mismatch": mismatch["api_mismatch"],
            "api_mismatch_detail": mismatch,
            "esb_api_totals_preserved": row.get("esb_totals"),
            "esb_closing_receipts": list_esb_closing_receipts(close_id, conn=c),
            "bank_cards": bank_cards(close_id, conn=c),
            "ai_is_not_accounting_truth": True,
        }
    finally:
        if own:
            c.close()


def _document_from_esb_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Prefer confirmed document, else extracted document."""
    for blob in (row.get("confirmed"), row.get("extracted")):
        if not isinstance(blob, dict):
            continue
        doc = blob.get("document") if isinstance(blob.get("document"), dict) else None
        if doc and doc.get("sections"):
            return doc
        if blob.get("sections"):
            return blob
    return None


def _receipt_payments_map(confirmed_esb: list[dict[str, Any]]) -> dict[str, float]:
    """Bank-split map from confirmed closing receipt document lines (fallback to flats)."""
    if not confirmed_esb:
        return {}
    latest = confirmed_esb[-1]
    conf = latest.get("confirmed") or latest.get("extracted") or {}
    out: dict[str, float] = {}

    doc = _document_from_esb_row(latest)
    if doc:
        for sec in doc.get("sections") or []:
            if sec.get("normalized_type") != "PAYMENT_METHODS":
                continue
            for ln in sec.get("lines") or []:
                nt = ln.get("normalized_type")
                if nt in (None, "PAYMENT_METHOD_TOTAL", "UNKNOWN"):
                    continue
                amt = ln.get("human_confirmed_value")
                if amt is None:
                    amt = ln.get("amount")
                if amt is None:
                    continue
                bank = (ln.get("bank_acquirer") or "").upper()
                if nt == "CASH":
                    key = "Cash"
                elif nt in ("EDC", "QRIS") and bank:
                    key = f"{nt}_{bank}"
                elif nt in ("EDC", "QRIS"):
                    key = f"{nt}_TOTAL"
                else:
                    # Preserve raw house/account labels — do not invent meaning
                    key = str(ln.get("raw_label") or nt)
                try:
                    out[key] = round(float(amt), 2)
                except (TypeError, ValueError):
                    continue
        if out:
            return out

    pays = conf.get("payments") if isinstance(conf, dict) else None
    if isinstance(pays, dict):
        for k, v in pays.items():
            if v is None:
                continue
            try:
                out[str(k)] = round(float(v), 2)
            except (TypeError, ValueError):
                continue
        return out
    # Flatten confirmed cash/edc/qris when vision did not emit bank keys
    if isinstance(conf, dict):
        if conf.get("cash_amount") is not None:
            out["Cash"] = round(float(conf["cash_amount"]), 2)
        if conf.get("edc_card_amount") is not None:
            out["EDC_TOTAL"] = round(float(conf["edc_card_amount"]), 2)
        if conf.get("qris_amount") is not None:
            out["QRIS_TOTAL"] = round(float(conf["qris_amount"]), 2)
    elif latest.get("cash_amount") is not None:
        out["Cash"] = round(float(latest["cash_amount"]), 2)
        if latest.get("edc_card_amount") is not None:
            out["EDC_TOTAL"] = round(float(latest["edc_card_amount"]), 2)
        if latest.get("qris_amount") is not None:
            out["QRIS_TOTAL"] = round(float(latest["qris_amount"]), 2)
    return out


def _receipt_document_recon(confirmed_esb: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Section-aware receipt view for recon — nonsales/exceptions stay separate."""
    if not confirmed_esb:
        return None
    doc = _document_from_esb_row(confirmed_esb[-1])
    if not doc:
        return None
    der = doc.get("derived") or {}
    shift = der.get("shift") or {}
    pay_lines = []
    nonsales = []
    exceptions = []
    unclassified = []
    for sec in doc.get("sections") or []:
        st = sec.get("normalized_type")
        for ln in sec.get("lines") or []:
            row = {
                "raw_label": ln.get("raw_label"),
                "quantity": ln.get("quantity"),
                "amount": ln.get("human_confirmed_value")
                if ln.get("human_confirmed_value") is not None
                else ln.get("amount"),
                "normalized_type": ln.get("normalized_type"),
                "bank_acquirer": ln.get("bank_acquirer"),
                "classification": ln.get("classification"),
                "section": st,
            }
            if ln.get("classification") == "NEEDS_CLASSIFICATION":
                unclassified.append(row)
            if st == "PAYMENT_METHODS" and ln.get("normalized_type") != "PAYMENT_METHOD_TOTAL":
                pay_lines.append(row)
            elif st == "NON_SALES":
                nonsales.append(row)
            elif st in ("CANCELLED_MENU", "VOID_PAYMENT", "PROMOTION", "DISCOUNT", "UNKNOWN"):
                exceptions.append(row)
    gross = shift.get("GROSS_SALES")
    pay_sum = der.get("payment_methods_sum")
    gross_vs_payments = None
    if gross is not None and pay_sum is not None:
        gross_vs_payments = {
            "gross_sales": gross,
            "payment_methods_sum": pay_sum,
            "delta": round(float(pay_sum) - float(gross), 2),
            "status": "MATCH"
            if round(float(pay_sum) - float(gross), 2) == 0
            else "MISMATCH",
        }
    return {
        "schema_version": doc.get("schema_version"),
        "business_date": doc.get("business_date"),
        "shift": shift,
        "payment_lines": pay_lines,
        "nonsales_lines": nonsales,
        "exception_lines": exceptions,
        "unclassified_lines": unclassified,
        "derived_totals": {
            "cash": der.get("total_cash"),
            "edc": der.get("total_edc"),
            "qris": der.get("total_qris"),
            "payment_methods_sum": pay_sum,
        },
        "gross_vs_payment_methods": gross_vs_payments,
        "raw_labels_preserved": True,
        "nonsales_excluded_from_sales_recon": True,
    }


def _diff_payment_maps(
    live: dict[str, float],
    receipt: dict[str, float],
) -> list[dict[str, Any]]:
    keys = sorted(set(live) | set(receipt))
    rows: list[dict[str, Any]] = []
    for k in keys:
        lv = round(float(live.get(k) or 0), 2)
        rv = round(float(receipt.get(k) or 0), 2)
        if lv == rv:
            status = "MATCH"
        elif k not in receipt:
            status = "LIVE_ONLY"
        elif k not in live:
            status = "RECEIPT_ONLY"
        else:
            status = "MISMATCH"
        rows.append(
            {
                "key": k,
                "live": lv,
                "closing_receipt": rv,
                "delta_live_minus_receipt": round(lv - rv, 2),
                "status": status,
            }
        )
    return rows


def dual_source_difference_board(
    *,
    live_totals: dict[str, Any],
    stored_totals: dict[str, Any],
    confirmed_esb: list[dict[str, Any]],
    business_date: str | None,
) -> dict[str, Any]:
    """LIVE ESB operational vs END OF DAY closing receipt — never overwrite either."""
    live_split = dict(live_totals.get("payments_by_bank_split") or {})
    if not live_split:
        # Fallback: stored snapshot may predate bank-split; use method names if present
        live_split = dict(
            live_totals.get("payment_by_method_name")
            or stored_totals.get("payment_by_method_name")
            or {}
        )
    receipt_split = _receipt_payments_map(confirmed_esb)
    latest = confirmed_esb[-1] if confirmed_esb else {}
    conf = (latest.get("confirmed") or latest.get("extracted") or {}) if latest else {}
    doc = _document_from_esb_row(latest) if latest else None
    der = (doc or {}).get("derived") or {}
    shift = der.get("shift") or {}
    receipt_bills = shift.get("BILLS")
    if receipt_bills is None and isinstance(conf, dict):
        receipt_bills = conf.get("bills")
    receipt_cash = der.get("total_cash") or der.get("cash_amount")
    if receipt_cash is None and isinstance(conf, dict) and conf.get("cash_amount") is not None:
        receipt_cash = round(float(conf["cash_amount"]), 2)
    elif receipt_cash is None and latest.get("cash_amount") is not None:
        receipt_cash = round(float(latest["cash_amount"]), 2)
    elif receipt_cash is not None:
        receipt_cash = round(float(receipt_cash), 2)
    receipt_pax = shift.get("PAX")
    if receipt_pax is None and isinstance(conf, dict):
        receipt_pax = conf.get("pax")
    receipt_gross = shift.get("GROSS_SALES") or der.get("gross_amount")
    receipt_net = shift.get("NET_SALES") or der.get("net_sales")
    receipt_service = shift.get("SERVICE_CHARGE") or der.get("service_charge")
    receipt_tax = shift.get("TAX") or der.get("tax")

    live_bills = live_totals.get("finished_count")
    live_cash_tendered = live_totals.get("cash_from_payments")
    live_cash_sales = live_totals.get("cash_sales_grand")
    live_sales_bills = live_totals.get("sales_bill_count_excl_other_cost")
    live_pax_sales = live_totals.get("sales_pax_excl_other_cost")

    explanations: list[dict[str, Any]] = []
    flags: list[str] = []

    if (
        live_bills is not None
        and live_sales_bills is not None
        and int(live_bills) != int(live_sales_bills)
    ):
        explanations.append(
            {
                "code": "OTHER_COST_BILLS_IN_LIVE",
                "message": (
                    f"Live Finished includes {int(live_bills) - int(live_sales_bills)} "
                    "OTHER COST bill(s) (comp/chef) that closing receipts typically omit."
                ),
                "live_finished": live_bills,
                "live_sales_excl_other": live_sales_bills,
            }
        )
    if (
        live_cash_tendered is not None
        and live_cash_sales is not None
        and round(float(live_cash_tendered) - float(live_cash_sales), 2) != 0
    ):
        explanations.append(
            {
                "code": "CASH_TENDERED_VS_SALES",
                "message": (
                    "Live cash is payment-line tendered (includes change overpay). "
                    "Closing receipt cash usually equals sales grand on cash bills."
                ),
                "cash_tendered": live_cash_tendered,
                "cash_sales_grand": live_cash_sales,
                "change_overpay": live_totals.get("cash_change_overpay"),
            }
        )
    if receipt_bills is not None and live_sales_bills is not None:
        if int(receipt_bills) == int(live_sales_bills):
            explanations.append(
                {
                    "code": "BILLS_MATCH_EXCL_OTHER",
                    "message": "Receipt bill count matches live Finished excluding OTHER COST.",
                    "bills": int(receipt_bills),
                }
            )
        else:
            flags.append("BILLS_STILL_MISMATCH_AFTER_OTHER_EXCL")
            explanations.append(
                {
                    "code": "BILLS_MISMATCH",
                    "message": "Receipt bills ≠ live sales bills even after excluding OTHER COST.",
                    "receipt_bills": receipt_bills,
                    "live_sales_bills": live_sales_bills,
                    "live_finished": live_bills,
                }
            )
    elif receipt_bills is not None and live_bills is not None:
        if int(receipt_bills) != int(live_bills):
            flags.append("BILLS_MISMATCH")
    if receipt_cash is not None and live_cash_sales is not None:
        if round(float(receipt_cash), 2) == round(float(live_cash_sales), 2):
            explanations.append(
                {
                    "code": "CASH_MATCHES_SALES_GRAND",
                    "message": "Receipt cash matches live cash-bill grandTotal (not tendered).",
                    "cash": receipt_cash,
                }
            )
        elif live_cash_tendered is not None and round(
            float(receipt_cash), 2
        ) != round(float(live_cash_tendered), 2):
            flags.append("CASH_MISMATCH")
    if receipt_pax is not None and live_pax_sales is not None:
        if round(float(receipt_pax), 2) == round(float(live_pax_sales), 2):
            explanations.append(
                {
                    "code": "PAX_MATCH_EXCL_OTHER",
                    "message": "Receipt pax matches live pax excluding OTHER COST bills.",
                    "pax": receipt_pax,
                }
            )

    pay_rows = _diff_payment_maps(live_split, receipt_split)
    any_mismatch = any(r["status"] != "MATCH" for r in pay_rows) or bool(flags)

    return {
        "policy": "Do not overwrite live with receipt or vice versa; dual-source reconcile + explain/flag",
        "business_date": business_date,
        "live_esb_operational": {
            "source": "warehouse_payment_lines",
            "finished_bills": live_bills,
            "sales_bills_excl_other_cost": live_sales_bills,
            "other_cost_bills": live_totals.get("other_cost_bill_count"),
            "cash_tendered": live_cash_tendered,
            "cash_sales_grand": live_cash_sales,
            "cash_change_overpay": live_totals.get("cash_change_overpay"),
            "pax_total": live_totals.get("pax_total"),
            "sales_pax_excl_other_cost": live_pax_sales,
            "grand_total": live_totals.get("grand_total"),
            "sales_grand_excl_other_cost": live_totals.get("sales_grand_excl_other_cost"),
            "card_from_payments": live_totals.get("card_from_payments"),
            "qris_from_payments": live_totals.get("qris_from_payments"),
            "other_from_payments": live_totals.get("other_from_payments"),
            "payments_by_bank_split": live_split,
        },
        "esb_end_of_day_closing_receipt": {
            "source": "photo_vision_confirm",
            "confirmed": bool(confirmed_esb),
            "bills": receipt_bills,
            "cash": receipt_cash,
            "pax": receipt_pax,
            "net_sales": receipt_net if receipt_net is not None else (conf.get("net_sales") if isinstance(conf, dict) else None),
            "service_charge": receipt_service if receipt_service is not None else (conf.get("service_charge") if isinstance(conf, dict) else None),
            "tax": receipt_tax if receipt_tax is not None else (conf.get("tax") if isinstance(conf, dict) else None),
            "gross_sales": receipt_gross if receipt_gross is not None else (conf.get("gross_sales") if isinstance(conf, dict) else None),
            "payments_by_bank_split": receipt_split,
            "document_present": bool(doc),
            "image_preserved": bool(
                latest.get("object_ref") or latest.get("content_hash")
            ),
        },
        "difference_board": {
            "bills": {
                "live_finished": live_bills,
                "live_sales_excl_other": live_sales_bills,
                "closing_receipt": receipt_bills,
                "delta_finished_minus_receipt": (
                    None
                    if live_bills is None or receipt_bills is None
                    else int(live_bills) - int(receipt_bills)
                ),
            },
            "cash": {
                "live_tendered": live_cash_tendered,
                "live_sales_grand": live_cash_sales,
                "closing_receipt": receipt_cash,
                "delta_tendered_minus_receipt": (
                    None
                    if live_cash_tendered is None or receipt_cash is None
                    else round(float(live_cash_tendered) - float(receipt_cash), 2)
                ),
            },
            "payments": pay_rows,
        },
        "explanations": explanations,
        "flags": flags,
        "has_unexplained_delta": any_mismatch and not explanations,
        "silent_overwrite": False,
        "sources_kept": True,
    }



def bank_cards(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Staff bank checklist: ESB expected vs CURRENT bank receipt actual."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        oid = (row.get("outlet_id") or OUTLET_UMA).strip()
        banks = list_outlet_banks(oid, conn=c)
        has_shift = _has_confirmed_shift_receipt(close_id, c)
        shift_expected = _esb_expected_by_bank(close_id, c) if has_shift else {}
        snapshot_expected = _snapshot_bank_expected(row)
        has_snapshot = bool(row.get("esb_fingerprint_sha256"))
        receipts = list_edc_receipts(close_id, conn=c)
        current_by_bank: dict[str, dict[str, Any]] = {}
        history_by_bank: dict[str, list[dict[str, Any]]] = {}
        for r in receipts:
            bank = _norm_bank(r.get("acquirer_label") or "")
            if not bank:
                continue
            history_by_bank.setdefault(bank, []).append(r)
            role = str(r.get("evidence_role") or "CURRENT").upper()
            if (
                role == "CURRENT"
                and r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
                and int(r.get("counted_in_totals") if r.get("counted_in_totals") is not None else 1) == 1
            ):
                current_by_bank[bank] = r

        cards = []
        for b in banks.get("banks") or []:
            label = _norm_bank(b.get("bank_label") or "")
            shift_slot = shift_expected.get(label)
            snap_slot = snapshot_expected.get(label) or {}
            if shift_slot:
                edc_exp = (
                    float(shift_slot["edc_expected"])
                    if shift_slot.get("edc_explicit")
                    else None
                )
                qris_exp = (
                    float(shift_slot["qris_expected"])
                    if shift_slot.get("qris_explicit")
                    else None
                )
                expected_basis = "shift_receipt"
            else:
                edc_exp = None
                qris_exp = None
                expected_basis = None

            explicit_zero = _bank_explicit_zero(shift_slot) or (
                not has_shift and _bank_explicit_zero(snap_slot)
            )
            esb_used = has_shift and (
                (edc_exp is not None and edc_exp > 0)
                or (qris_exp is not None and qris_exp > 0)
            )
            cur = current_by_bank.get(label)
            edc_act = float(cur.get("edc_card_amount") or 0) if cur else None
            qris_act = float(cur.get("qris_amount") or 0) if cur else None
            edc_exp_cmp = float(edc_exp or 0) if edc_exp is not None else 0.0
            qris_exp_cmp = float(qris_exp or 0) if qris_exp is not None else 0.0

            live_edc = (
                float(snap_slot["edc_expected"])
                if snap_slot.get("edc_explicit") and snap_slot.get("edc_expected") is not None
                else None
            )
            live_qris = (
                float(snap_slot["qris_expected"])
                if snap_slot.get("qris_explicit") and snap_slot.get("qris_expected") is not None
                else None
            )
            shift_edc = edc_exp
            shift_qris = qris_exp
            terminal_edc = edc_act
            terminal_qris = qris_act

            if not has_shift and not (explicit_zero and not cur):
                status = "SHIFT_RECEIPT_NEEDED"
                staff_status = "CHECK THIS AMOUNT"
                edc_receipt_status = "Waiting for shift report"
                qris_receipt_status = "Waiting for shift report"
                need_receipt = False
            elif explicit_zero and not cur:
                status = "NOT_USED_TODAY"
                staff_status = "NOT USED TODAY"
                edc_receipt_status = "Not required"
                qris_receipt_status = "Not required"
                need_receipt = False
            elif esb_used and not cur:
                status = "RECEIPT_REQUIRED"
                staff_status = "RECEIPT MISSING"
                edc_receipt_status = (
                    "Not added" if edc_exp is not None and edc_exp > 0 else "Not required"
                )
                qris_receipt_status = (
                    "Not added" if qris_exp is not None and qris_exp > 0 else "Not required"
                )
                need_receipt = True
            elif cur:
                need_receipt = False
                edc_receipt_status = "Confirmed"
                qris_receipt_status = "Confirmed"
                edc_diff = round((edc_act or 0) - edc_exp_cmp, 2)
                qris_diff = round((qris_act or 0) - qris_exp_cmp, 2)
                if edc_diff == 0 and qris_diff == 0:
                    status = "MATCH"
                    staff_status = "MATCH"
                else:
                    status = "MISMATCH"
                    staff_status = "DIFFERENCE FOUND"
            elif has_shift and not cur and not esb_used:
                # Confirmed shift report with no positive EDC/QRIS for this bank
                # (omitted or explicit zero already handled) — not used, no photo.
                status = "NOT_USED_TODAY"
                staff_status = "NOT USED TODAY"
                edc_receipt_status = "Not required"
                qris_receipt_status = "Not required"
                need_receipt = False
            else:
                status = "SHIFT_RECEIPT_NEEDED"
                staff_status = "CHECK THIS AMOUNT"
                edc_receipt_status = "Waiting for shift report"
                qris_receipt_status = "Waiting for shift report"
                need_receipt = False

            edc_diff = (
                None
                if edc_act is None or edc_exp is None
                else round(float(edc_act) - edc_exp_cmp, 2)
            )
            qris_diff = (
                None
                if qris_act is None or qris_exp is None
                else round(float(qris_act) - qris_exp_cmp, 2)
            )
            cards.append(
                {
                    "bank": label,
                    "bank_config_id": b.get("bank_config_id"),
                    "expected_basis": expected_basis,
                    "esb_used": esb_used,
                    "esb_edc_expected": edc_exp,
                    "esb_qris_expected": qris_exp,
                    "live_esb_edc": live_edc,
                    "live_esb_qris": live_qris,
                    "shift_report_edc": shift_edc,
                    "shift_report_qris": shift_qris,
                    "terminal_edc": terminal_edc,
                    "terminal_qris": terminal_qris,
                    "edc_receipt_status": edc_receipt_status,
                    "qris_receipt_status": qris_receipt_status,
                    "receipt_required": need_receipt,
                    "status": status,
                    "staff_status": staff_status,
                    "actual_edc": edc_act,
                    "actual_qris": qris_act,
                    "difference_edc": edc_diff,
                    "difference_qris": qris_diff,
                    "current_receipt_id": cur.get("edc_receipt_id") if cur else None,
                    "history_count": len(history_by_bank.get(label) or []),
                    "superseded_count": len(
                        [
                            h
                            for h in (history_by_bank.get(label) or [])
                            if str(h.get("evidence_role") or "").upper() == "SUPERSEDED"
                        ]
                    ),
                }
            )
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "outlet_id": oid,
            "bank_config_status": banks.get("bank_config_status"),
            "esb_confirmed": has_shift,
            "shift_receipt_confirmed": has_shift,
            "cards": cards,
            "staff_questions": [
                "What does ESB expect?",
                "What does the bank receipt say?",
                "Do they match?",
            ],
            "esb_expected_is_not_settlement_proof": True,
        }
    finally:
        if own:
            c.close()


def mark_bank_unused(
    close_id: str,
    *,
    verified_person_id: str,
    bank_label: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Owner/staff override: mark bank unused — supersede CURRENT evidence if any."""
    verified = (verified_person_id or "").strip()
    bank = _norm_bank(bank_label)
    why = (reason or "").strip()
    if not verified or not bank or not why:
        raise BzgDailyCloseError(
            "verified_person_id, bank_label, and reason required",
            code="missing_fields",
        )
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        _require_holder(row, verified_person_id=verified, conn=c, identity=identity)
        ts = _vc.now_utc_iso()
        cur_ids = _current_edc_receipt_ids_for_bank(c, close_id, bank)
        cur_rows = [{"edc_receipt_id": rid} for rid in cur_ids]
        for r in cur_rows:
            c.execute(
                """
                UPDATE venue_close_edc_receipts
                SET evidence_role='SUPERSEDED', counted_in_totals=0,
                    superseded_at=?, supersede_reason=?, updated_at=?
                WHERE edc_receipt_id=?
                """,
                (
                    ts,
                    f"Marked unused: {why}",
                    ts,
                    r["edc_receipt_id"],
                ),
            )
        _audit.safe_record(
            action="venue_close.bank_mark_unused",
            result="ALLOWED",
            source="bzg_daily_close",
            actor_type="PERSON",
            verified_person_id=verified,
            actor_person_id=verified,
            resource_type="venue_daily_close",
            resource_id=close_id,
            reason_code="bank_marked_unused",
            metadata={"bank": bank, "reason": why, "superseded": len(cur_rows)},
            conn=c,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "close_id": close_id,
            "bank": bank,
            "superseded_count": len(cur_rows),
            "bank_cards": bank_cards(close_id, conn=c),
            "receipt_totals": receipt_totals(close_id, conn=c),
            "edc_receipts": list_edc_receipts(close_id, conn=c),
        }
    finally:
        if own:
            c.close()


def cash_reconciliation_with_petty(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Till cash reconciliation including same-day petty OUT from Wolf (no re-entry).

    expected = opening_float + cash_sales - petty_out + other_authorised_movements
    difference = counted_cash - expected (when both known)
    """
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        biz = (row.get("business_date") or "").strip()
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        totals = row.get("esb_totals") or {}
        cash_sales = totals.get("cash_from_payments")
        if cash_sales is not None:
            cash_sales = round(float(cash_sales), 2)

        opening_float: float | None = None
        cfg = get_outlet_config(outlet_id, conn=c)
        if cfg and cfg.get("till_float_idr") is not None:
            opening_float = round(float(cfg["till_float_idr"]), 2)

        petty_out = 0.0
        petty_in = 0.0
        petty_movements: list[dict[str, Any]] = []
        petty_in_movements: list[dict[str, Any]] = []
        if biz:
            try:
                _petty.ensure_schema(c)
                petty_out = _petty.sum_petty_out_for_date(biz, conn=c)
                petty_in = _petty.sum_petty_in_for_date(biz, conn=c)
                petty_movements = _petty.list_petty_out_for_date(biz, conn=c)
                petty_in_movements = _petty.list_petty_in_for_date(biz, conn=c)
            except (sqlite3.Error, RuntimeError, OSError):
                petty_out = 0.0
                petty_in = 0.0
                petty_movements = []
                petty_in_movements = []

        other_movements: list[dict[str, Any]] = []
        expected: float | None = None
        if opening_float is not None and cash_sales is not None:
            other_sum = sum(float(m.get("amount") or 0) for m in other_movements)
            expected = round(opening_float + cash_sales - petty_out + petty_in + other_sum, 2)

        counted = row.get("declared_cash_amount")
        if counted is not None:
            counted = round(float(counted), 2)

        difference: float | None = None
        if expected is not None and counted is not None:
            difference = round(counted - expected, 2)

        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": biz,
            "opening_float": opening_float,
            "opening_float_status": "PROVIDED" if opening_float is not None else "NOT_FOUND",
            "cash_sales": cash_sales,
            "petty_out_total": petty_out,
            "petty_in_total": petty_in,
            "petty_out_movements": petty_movements,
            "petty_in_movements": petty_in_movements,
            "petty_out_source": "bzg_ops_petty_movements",
            "petty_in_source": "bzg_ops_petty_movements",
            "other_authorised_movements": other_movements,
            "expected_closing_cash": expected,
            "counted_cash": counted,
            "difference": difference,
            "double_count_avoided": True,
            "staff_retype_required": False,
        }
    finally:
        if own:
            c.close()


def recon_board(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Cash / EDC / QRIS + bank-split dual-source board. Never overwrites sources."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        totals = row.get("esb_totals") or {}
        rt = receipt_totals(close_id, conn=c)
        esb_recs = list_esb_closing_receipts(close_id, conn=c)
        confirmed_esb = [
            r for r in esb_recs if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
        ]
        declared_cash = row.get("declared_cash_amount")

        # Live operational re-read (RO warehouse) — does not mutate stored close.
        live_totals = dict(totals)
        live_meta: dict[str, Any] = {"source": "stored_close_snapshot"}
        biz = (row.get("business_date") or "").strip()
        if biz:
            try:
                snap = _esb.snapshot_day(biz)
                live_totals = dict(snap.get("totals") or {})
                live_meta = {
                    "source": "warehouse_payment_lines_live",
                    "esb_pulled_at": snap.get("esb_pulled_at"),
                    "fingerprint_sha256": snap.get("fingerprint_sha256"),
                    "stored_fingerprint_sha256": row.get("esb_fingerprint_sha256"),
                    "fingerprint_matches_stored": snap.get("fingerprint_sha256")
                    == row.get("esb_fingerprint_sha256"),
                }
            except _esb.EsbSnapshotError as exc:
                live_meta = {
                    "source": "stored_close_snapshot",
                    "live_read_error": str(exc),
                    "live_read_code": getattr(exc, "code", None),
                }

        # Captured snapshot remains the close's expected basis (fingerprint-locked).
        # Live warehouse re-read feeds dual_source only — never overwrites captured.
        esb_cash = totals.get("cash_from_payments")
        esb_edc = totals.get("card_from_payments")
        esb_qris = totals.get("qris_from_payments")
        conf_edc = rt["TOTAL_EDC"]
        conf_qris = rt["TOTAL_QRIS"]
        bank_split = (
            live_totals.get("payments_by_bank_split")
            or totals.get("payments_by_bank_split")
            or {}
        )

        def _var(expected: Any, confirmed: Any) -> float | None:
            if expected is None or confirmed is None:
                return None
            return round(float(confirmed) - float(expected), 2)

        mismatches = [r for r in confirmed_esb if r.get("api_mismatch")]
        evidence = {
            "esb_api_snapshot": bool(row.get("esb_fingerprint_sha256")),
            "esb_closing_receipt_confirmed": bool(confirmed_esb),
            "declared_cash": declared_cash is not None,
            "edc_receipts_confirmed": rt["confirmed_receipt_count"] > 0,
            "z_report_or_till": bool(
                row.get("declared_cash_evidence_id")
                or (
                    _has_table(c, "venue_close_till_evidence")
                    and c.execute(
                        "SELECT 1 FROM venue_close_till_evidence WHERE close_id=? LIMIT 1",
                        (close_id,),
                    ).fetchone()
                )
            ),
        }
        complete = all(
            [
                evidence["esb_api_snapshot"],
                evidence["esb_closing_receipt_confirmed"],
                evidence["declared_cash"],
            ]
        )
        dual = dual_source_difference_board(
            live_totals=live_totals,
            stored_totals=totals,
            confirmed_esb=confirmed_esb,
            business_date=biz,
        )
        petty_recon = cash_reconciliation_with_petty(close_id, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "state": row.get("state"),
            "cash": {
                "esb_expected": esb_cash,
                "esb_cash_tendered": esb_cash,
                "esb_cash_sales_grand": live_totals.get("cash_sales_grand"),
                "declared_confirmed": declared_cash,
                "variance": _var(esb_cash, declared_cash),
            },
            "cash_reconciliation": petty_recon,
            "edc": {
                "esb_expected": esb_edc,
                "receipts_confirmed": conf_edc,
                "variance": _var(esb_edc, conf_edc),
            },
            "qris": {
                "esb_expected": esb_qris,
                "receipts_confirmed": conf_qris,
                "variance": _var(esb_qris, conf_qris),
            },
            "other_methods": {
                "esb_expected": live_totals.get(
                    "other_from_payments", totals.get("other_from_payments")
                ),
            },
            "payments_by_bank_split": bank_split,
            "bank_split_edc": {
                k: v for k, v in bank_split.items() if str(k).startswith("EDC_")
            },
            "bank_split_qris": {
                k: v for k, v in bank_split.items() if str(k).startswith("QRIS_")
            },
            "live_esb_meta": live_meta,
            "dual_source": dual,
            "document_recon": _receipt_document_recon(confirmed_esb),
            "receipt_totals": rt,
            "esb_api_vs_receipt_mismatch": bool(mismatches)
            or bool(dual.get("flags"))
            or any(
                r.get("status") == "MISMATCH"
                for r in (dual.get("difference_board") or {}).get("payments") or []
            ),
            "esb_mismatch_rows": len(mismatches),
            "evidence_completeness": evidence,
            "evidence_complete": complete,
            "qris_never_merged_into_card": True,
            "unused_terminals": unused_configured_terminals(
                close_id, (row.get("outlet_id") or OUTLET_UMA), conn=c
            ),
        }
    finally:
        if own:
            c.close()



def _sidecar_row_db_anchored(
    close_id: str,
    object_ref: str,
    content_hash: str | None,
    conn: sqlite3.Connection,
) -> bool:
    """Sidecar row is recoverable only when a DB receipt/evidence row anchors it."""
    cid = close_id.strip()
    ref = object_ref.strip()
    ch = (content_hash or "").strip()
    for rec in list_esb_closing_receipts(cid, conn=conn):
        rref = (rec.get("image_object_ref") or rec.get("object_ref") or "").strip()
        rch = (rec.get("content_hash") or "").strip()
        if rref == ref or (ch and rch == ch):
            return True
        evid_id = (rec.get("evidence_id") or "").strip()
        if evid_id and _has_table(conn, "core_evidence_records"):
            row = conn.execute(
                """
                SELECT object_ref, content_hash FROM core_evidence_records
                WHERE evidence_id=? LIMIT 1
                """,
                (evid_id,),
            ).fetchone()
            if row:
                er = (row["object_ref"] or "").strip()
                ech = (row["content_hash"] or "").strip()
                if er == ref or (ch and ech == ch):
                    return True
    return False


def find_pending_esb_receipt_photo(
    close_id: str | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Recover stored ESB closing photo only when DB-anchored sidecar exists.

    Never uses bare sidecar rows or newest-on-disk fallback. Never deletes.
    """
    cid = (close_id or "").strip()
    if not cid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        idx = CLOSE_RECEIPT_DIR / "photo-index.jsonl"
        if not idx.is_file():
            return None
        try:
            lines = idx.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("close_id") or "") != cid:
                continue
            if str(row.get("kind") or "").lower() not in ("esb", "receipt"):
                continue
            ref = (row.get("object_ref") or "").strip()
            if not ref or _weg.is_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR):
                continue
            if not resolve_close_receipt_path(ref):
                continue
            if not _sidecar_row_db_anchored(cid, ref, row.get("content_hash"), c):
                continue
            return {
                "object_ref": ref,
                "content_hash": row.get("content_hash"),
                "mime_type": row.get("mime_type") or "image/jpeg",
                "source": "photo_index_db_anchored",
                "extraction_status": "PHOTO_STORED_EXTRACT_PENDING",
            }
        return None
    finally:
        if own:
            c.close()


def history_detail(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    include_live_side_read: bool = False,
) -> dict[str, Any]:
    """Closing History card: saved snapshot + API vs receipt + bank/QRIS/cash/nonsales.

    Primary figures come from the dated closing snapshot and confirmed receipts.
    Live warehouse re-read is optional and never mutates the close.
    SUPERSEDED EDC attempts appear under audit/history only — excluded from totals.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        cid = str(row.get("close_id") or "")
        stored = row.get("esb_totals") if isinstance(row.get("esb_totals"), dict) else {}
        esb_recs = list_esb_closing_receipts(cid, conn=c)
        confirmed_esb = [
            r
            for r in esb_recs
            if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
        ]
        rt = receipt_totals(cid, conn=c)
        cards = bank_cards(cid, conn=c)
        edc_all = list_edc_receipts(cid, conn=c)
        superseded = [
            r
            for r in edc_all
            if str(r.get("evidence_role") or "").upper() == "SUPERSEDED"
        ]
        # History dual-source: stored dated snapshot vs printed receipt (not today's live).
        dual = dual_source_difference_board(
            live_totals=stored,
            stored_totals=stored,
            confirmed_esb=confirmed_esb,
            business_date=row.get("business_date"),
        )
        # Relabel: for history the left column is the frozen snapshot API, not live ops.
        if isinstance(dual.get("live_esb_operational"), dict):
            dual["dated_closing_snapshot_api"] = {
                **dual["live_esb_operational"],
                "source": "dated_closing_snapshot",
                "object": "DATED_CLOSING_SNAPSHOT",
            }
            dual["live_esb_operational"] = {
                "object": "LIVE_ESB_OPERATIONAL",
                "included": False,
                "note": "History card uses saved snapshot; live side-read optional and non-mutating.",
            }
        live_totals = None
        live_meta: dict[str, Any] = {"included": False}
        if include_live_side_read:
            live_totals, live_meta = _vc._side_read_live_esb(  # noqa: SLF001
                str(row.get("business_date") or ""),
                stored_fingerprint=row.get("esb_fingerprint_sha256"),
            )
            live_meta = {**live_meta, "included": True, "mutates_close": False}
            dual["live_esb_operational"] = {
                "object": "LIVE_ESB_OPERATIONAL",
                "included": True,
                "totals": live_totals,
                "meta": live_meta,
                "mutates_close": False,
            }
        doc_recon = _receipt_document_recon(confirmed_esb)
        nonsales = (doc_recon or {}).get("nonsales_lines") or []
        api_vs_receipt = {
            "api_cash": stored.get("cash_from_payments"),
            "receipt_cash": (
                confirmed_esb[-1].get("cash_amount") if confirmed_esb else None
            ),
            "api_bills_finished": stored.get("finished_count"),
            "api_sales_bills_excl_other": stored.get("sales_bill_count_excl_other_cost"),
            "receipt_bills": (
                (dual.get("esb_end_of_day_closing_receipt") or {}).get("bills")
            ),
            "api_edc": stored.get("card_from_payments"),
            "receipt_edc": (
                confirmed_esb[-1].get("edc_card_amount") if confirmed_esb else None
            ),
            "api_qris": stored.get("qris_from_payments"),
            "receipt_qris": (
                confirmed_esb[-1].get("qris_amount") if confirmed_esb else None
            ),
            "difference_visible": bool(dual.get("flags"))
            or any(
                r.get("api_mismatch") for r in confirmed_esb
            ),
            "cause_invented": False,
            "silent_overwrite": False,
            "sources_kept": True,
        }
        objects = _vc.three_close_objects(
            row, live_totals=live_totals, live_meta=live_meta
        )
        return {
            **HONESTY,
            "ok": True,
            "close_id": cid,
            "business_date": row.get("business_date"),
            "outlet_id": row.get("outlet_id") or OUTLET_UMA,
            "state": row.get("state"),
            "holder_person_id": row.get("taken_by_person_id"),
            "source": "venue_daily_closes_saved",
            "live_esb_used": False,
            "snapshot_frozen": bool(row.get("esb_fingerprint_sha256")),
            "three_objects": objects,
            "source_snapshot": {
                "object": "DATED_CLOSING_SNAPSHOT",
                "esb_fingerprint_sha256": row.get("esb_fingerprint_sha256"),
                "esb_pulled_at": row.get("esb_pulled_at"),
                "fingerprint_stale_flag": bool(row.get("fingerprint_stale")),
                "totals": stored or None,
            },
            "api_vs_receipt": api_vs_receipt,
            "dual_source": dual,
            "bank_cards": cards,
            "cash": {
                "api_tendered": stored.get("cash_from_payments"),
                "api_sales_grand": stored.get("cash_sales_grand"),
                "receipt": api_vs_receipt.get("receipt_cash"),
                "declared": row.get("declared_cash_amount"),
                "variance_declared_minus_api": (
                    None
                    if row.get("declared_cash_amount") is None
                    or stored.get("cash_from_payments") is None
                    else round(
                        float(row["declared_cash_amount"])
                        - float(stored["cash_from_payments"]),
                        2,
                    )
                ),
            },
            "qris": {
                "api": stored.get("qris_from_payments"),
                "receipts_current": rt.get("TOTAL_QRIS"),
                "superseded_excluded": True,
            },
            "edc": {
                "api": stored.get("card_from_payments"),
                "receipts_current": rt.get("TOTAL_EDC"),
                "superseded_excluded": True,
                "superseded_attempts": len(superseded),
            },
            "non_sales": nonsales,
            "document_recon": doc_recon,
            "receipt_totals_current_only": rt,
            "esb_closing_receipts": esb_recs,
            "edc_receipts_current": [
                r
                for r in edc_all
                if str(r.get("evidence_role") or "CURRENT").upper() == "CURRENT"
            ],
            "edc_receipts_superseded_audit": superseded,
            "evidence": {
                "esb_api_snapshot": bool(row.get("esb_fingerprint_sha256")),
                "esb_closing_receipt_count": len(esb_recs),
                "edc_current_count": rt.get("confirmed_receipt_count"),
                "edc_superseded_count": len(superseded),
                "declared_cash": row.get("declared_cash_amount") is not None,
                "declared_cash_evidence_id": row.get("declared_cash_evidence_id"),
            },
            "corrections_note": (
                "SUPERSEDED evidence retained for audit; CURRENT only in totals. "
                "Cancel unfinished abandons draft only — does not rewrite history."
            ),
            "cancel_unfinished_rewrites_history": False,
        }
    finally:
        if own:
            c.close()


def staff_cash_summary(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Staff-language cash lines — frozen snapshot basis; petty counted once."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        totals = row.get("esb_totals") or {}
        recon = cash_reconciliation_with_petty(close_id, conn=c)
        esb_cash = totals.get("cash_from_payments")
        if esb_cash is not None:
            esb_cash = round(float(esb_cash), 2)
        petty_out = recon.get("petty_out_total")
        opening = recon.get("opening_float")
        expected = recon.get("expected_closing_cash")
        counted = recon.get("counted_cash")
        difference = recon.get("difference")
        finished = totals.get("finished_count")

        formula_bits: list[str] = []
        if opening is not None:
            formula_bits.append(f"opening {int(opening)}")
        if esb_cash is not None:
            formula_bits.append(f"ESB cash {int(esb_cash)}")
        if petty_out is not None and float(petty_out) > 0:
            formula_bits.append(f"petty OUT −{int(float(petty_out))}")
        formula = ""
        if formula_bits:
            if len(formula_bits) == 3:
                formula = (
                    f"{formula_bits[0]} + {formula_bits[1]} − "
                    f"{int(float(petty_out or 0))}"
                )
            else:
                formula = " + ".join(formula_bits)
            if expected is not None:
                formula += f" = {int(expected)}"

        if counted is None or expected is None:
            diff_label = "Cannot calculate yet"
        elif difference is not None and abs(float(difference)) < 0.01:
            diff_label = "MATCHES"
        elif difference is not None:
            diff_label = f"DIFFERENCE Rp {int(abs(float(difference)))}"
        else:
            diff_label = "Cannot calculate yet"

        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "esb_cash": esb_cash,
            "esb_cash_field": "cash_from_payments",
            "petty_cash_paid_today": petty_out,
            "expected_cash": expected,
            "cash_counted": counted,
            "difference": difference,
            "difference_label": diff_label,
            "finished_bills": finished,
            "expected_cash_formula": formula or None,
            "snapshot_frozen": bool(row.get("esb_fingerprint_sha256")),
            "declared_cash_amount": row.get("declared_cash_amount"),
            "declared_stayed_null": row.get("declared_cash_amount") is None,
        }
    finally:
        if own:
            c.close()


def cash_three_sources(
    close_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Live ESB, printed shift receipt, and physical till — kept separate."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        biz = (row.get("business_date") or "").strip()
        stored_totals = row.get("esb_totals") or {}
        live_cash = stored_totals.get("cash_from_payments")
        live_source = "frozen_close_snapshot"
        if live_cash is not None:
            live_cash = round(float(live_cash), 2)
        elif biz:
            try:
                snap = _esb.snapshot_day(biz)
                totals = snap.get("totals") or {}
                live_cash = totals.get("cash_from_payments")
                live_source = "warehouse_payment_lines_live"
                if live_cash is not None:
                    live_cash = round(float(live_cash), 2)
            except _esb.EsbSnapshotError:
                pass
        receipt_cash: float | None = None
        for rec in list_esb_closing_receipts(close_id, conn=c):
            if rec.get("human_confirm_status") not in ("CONFIRMED", "EDITED"):
                continue
            if rec.get("cash_amount") is not None:
                receipt_cash = round(float(rec["cash_amount"]), 2)
                break
        till_cash = row.get("declared_cash_amount")
        if till_cash is not None:
            till_cash = round(float(till_cash), 2)

        def _delta(a: float | None, b: float | None) -> float | None:
            if a is None or b is None:
                return None
            return round(float(a) - float(b), 2)

        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": biz,
            "live_esb": {
                "label": "Live ESB",
                "amount": live_cash,
                "source": live_source,
            },
            "printed_shift_receipt": {
                "label": "Printed shift receipt",
                "amount": receipt_cash,
            },
            "physical_till": {
                "label": "Physical till",
                "amount": till_cash,
            },
            "differences": {
                "till_minus_live_esb": _delta(till_cash, live_cash),
                "receipt_minus_live_esb": _delta(receipt_cash, live_cash),
                "till_minus_receipt": _delta(till_cash, receipt_cash),
            },
            "sources_kept_separate": True,
        }
    finally:
        if own:
            c.close()


def _format_rp(amount: float | int | None) -> str:
    if amount is None:
        return "—"
    n = int(round(abs(float(amount))))
    return "Rp" + f"{n:,}".replace(",", ".")


def format_variance_label(diff: float | int | None) -> str:
    """Plain words for staff UI — Short / Over / Matches."""
    if diff is None:
        return "—"
    d = float(diff)
    if abs(d) < 0.01:
        return "Matches"
    amt = _format_rp(d)
    return f"Short {amt}" if d < 0 else f"Over {amt}"


def _shift_figures_readable(
    extracted: dict[str, Any] | None,
    printed: dict[str, Any] | None = None,
) -> bool:
    """YES is blocked when vision returned nothing meaningful."""
    pr = printed or {}
    if isinstance(extracted, dict) and extracted:
        gross = extracted.get("gross_sales_rp") or extracted.get("gross_amount")
        cash = extracted.get("cash_rp") or extracted.get("cash_amount")
        doc = extracted.get("document") if isinstance(extracted.get("document"), dict) else {}
        der = doc.get("derived") or {}
        shift = der.get("shift") or {}
        if gross is None:
            gross = der.get("gross_amount") or shift.get("GROSS_SALES")
        if cash is None:
            cash = der.get("cash_amount") or der.get("total_cash")
        try:
            if gross is None or float(gross) <= 0:
                return False
            if cash is None:
                return False
            return True
        except (TypeError, ValueError):
            return False
    if isinstance(extracted, dict) and not extracted:
        return False
    gross = pr.get("gross_sales_rp")
    cash = pr.get("cash_rp")
    try:
        if gross is None or float(gross) <= 0:
            return False
        if cash is None:
            return False
        return True
    except (TypeError, ValueError):
        return False


def _staff_submit_message(
    *,
    state: str,
    cash_sources: dict[str, Any],
    variance: float | None,
    close_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str:
    expected: float | None = None
    counted: float | None = None
    cash_diff: float | None = variance
    if close_id and conn is not None:
        try:
            cash_wiz = wizard_cash_summary(close_id, conn=conn)
            expected = cash_wiz.get("expected_cash_in_till")
            counted = cash_wiz.get("cash_counted")
            if cash_diff is None and expected is not None and counted is not None:
                cash_diff = round(float(counted) - float(expected), 2)
        except BzgDailyCloseError:
            pass
    if expected is None:
        till = cash_sources.get("physical_till") or {}
        counted = till.get("amount")
    parts: list[str] = []
    if cash_diff is not None and abs(cash_diff) >= 0.01:
        label = "Cash short" if cash_diff < 0 else "Cash over"
        parts.append(f"{label} {_format_rp(cash_diff)}")
    esb_exc: dict[str, Any] | None = None
    if close_id and conn is not None:
        esb_exc = get_workflow_ack(close_id, "esb_data_difference", conn=conn)
    if esb_exc:
        diff = esb_exc.get("difference") or {}
        cash_d = diff.get("cash_rp")
        bills_d = diff.get("bills")
        if cash_d is not None:
            bill_txt = f" / {abs(int(bills_d))} bill" if bills_d else ""
            if bills_d and abs(int(bills_d)) != 1:
                bill_txt = f" / {abs(int(bills_d))} bills"
            parts.append(
                f"ESB data difference {_format_rp(cash_d)}{bill_txt} kept as exceptions"
            )
    if not parts:
        till = cash_sources.get("physical_till") or {}
        cnt = till.get("amount")
        if cnt is not None:
            parts.append(f"Cash counted {_format_rp(cnt)}")
        else:
            parts.append("Close saved")
    msg = " · ".join(parts)
    if state in ("EXCEPTION", "VARIANCE_REQUIRES_POLICY") and "exception" not in msg.lower():
        msg += " · kept as exceptions"
    return msg


def staff_submit_close(
    close_id: str,
    *,
    declared_cash_amount: float,
    verified_person_id: str,
    business_date: str | None = None,
    object_ref: str | None = None,
    content_hash: str | None = None,
    notes: str | None = None,
    confirm_recount: bool = False,
    submit_with_exception: bool = False,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Staff submit: idempotent declare, auto-compare, optional exception route."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise BzgDailyCloseError(
            "verified_person_id required", code="missing_verified_person"
        )
    try:
        amount = round(float(declared_cash_amount), 2)
    except (TypeError, ValueError) as exc:
        raise BzgDailyCloseError("declared_cash_amount must be numeric", code="invalid_amount") from exc
    if amount < 0:
        raise BzgDailyCloseError("declared_cash_amount cannot be negative", code="invalid_amount")

    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        _vc._assert_close_business_date(row, business_date, action="submit close")  # noqa: SLF001
        _require_holder(
            row, verified_person_id=verified, conn=c, identity=identity
        )
        st = str(row.get("state") or "")
        existing_amt = row.get("declared_cash_amount")
        if st in ("EXCEPTION", "VARIANCE_REQUIRES_POLICY") and existing_amt is not None:
            if round(float(existing_amt), 2) == amount:
                cash_src = cash_three_sources(close_id, conn=c)
                staff_result = (
                    "CLOSE SAVED WITH EXCEPTION"
                    if st == "EXCEPTION"
                    else "NEEDS MANAGER REVIEW"
                )
                msg = _staff_submit_message(
                    state=st,
                    cash_sources=cash_src,
                    variance=row.get("variance_cash_amount"),
                    close_id=close_id,
                    conn=c,
                )
                return {
                    **HONESTY,
                    "ok": True,
                    "staff_result": staff_result,
                    "staff_message": msg,
                    "cash_sources": cash_src,
                    "close": enrich_close(row, conn=c),
                    "idempotent": True,
                }
        try:
            from core import uma_hist_close_queue1 as _hist_q

            prot = _hist_q.submit_block_reason(
                close_id, row, verified_person_id=verified, conn=c
            )
            if prot:
                cash_src = cash_three_sources(close_id, conn=c)
                return {
                    **HONESTY,
                    "ok": False,
                    "staff_result": "CANNOT SUBMIT",
                    "staff_message": prot,
                    "cannot_reason": "protected_close",
                    "cash_sources": cash_src,
                    "close": enrich_close(row, conn=c),
                }
        except ImportError:
            pass
        if st == "VERIFIED_CLOSED":
            cash_src = cash_three_sources(close_id, conn=c)
            if existing_amt is not None and round(float(existing_amt), 2) == amount:
                msg = _staff_submit_message(
                    state=st,
                    cash_sources=cash_src,
                    variance=row.get("variance_cash_amount"),
                    close_id=close_id,
                    conn=c,
                )
                return {
                    **HONESTY,
                    "ok": True,
                    "staff_result": "CLOSE SAVED",
                    "staff_message": msg,
                    "cash_sources": cash_src,
                    "close": enrich_close(row, conn=c),
                    "idempotent": True,
                }
            return {
                **HONESTY,
                "ok": False,
                "staff_result": "CANNOT SUBMIT",
                "staff_message": (
                    "Close is already verified with a different declared amount; "
                    "refresh cannot change the submission."
                ),
                "cannot_reason": "amount_mismatch",
                "cash_sources": cash_src,
                "close": enrich_close(row, conn=c),
                "idempotent": False,
            }
        if st not in ("DATA_CAPTURED", "EVIDENCE_SUBMITTED", "VARIANCE_REQUIRES_POLICY"):
            cash_src = cash_three_sources(close_id, conn=c)
            return {
                **HONESTY,
                "ok": False,
                "staff_result": "CANNOT SUBMIT",
                "staff_message": f"Close is already {st.lower().replace('_', ' ')}.",
                "cash_sources": cash_src,
                "close": enrich_close(row, conn=c),
            }

        ref = (object_ref or "").strip() or None
        ch = (content_hash or "").strip() or None
        if ref or ch:
            declared = attach_till_with_z_report(
                close_id,
                declared_cash_amount=amount,
                verified_person_id=verified,
                object_ref=ref,
                content_hash=ch,
                notes=notes,
                identity=identity,
                allow_test_write=allow_test_write,
                conn=c,
                commit=False,
            )
        else:
            declared = _vc.attach_declared_cash(
                close_id,
                declared_cash_amount=amount,
                verified_person_id=verified,
                object_ref=ref,
                content_hash=ch,
                notes=notes,
                identity=identity,
                allow_test_write=allow_test_write,
                conn=c,
                commit=False,
            )

        cash_wiz = wizard_cash_summary(close_id, conn=c)
        expected_cash = cash_wiz.get("expected_cash_in_till")
        totals = (row.get("esb_totals") or {})
        esb_cash = totals.get("cash_from_payments")
        basis_cash = expected_cash if expected_cash is not None else esb_cash
        variance = None
        if basis_cash is not None and amount is not None:
            variance = round(amount - float(basis_cash), 2)
        if expected_cash is not None:
            record_workflow_ack(
                close_id,
                "cash_expected_basis",
                {
                    "expected_cash_in_till": expected_cash,
                    "counted": amount,
                    "recorded_at": _vc.now_utc_iso(),
                },
                conn=c,
                commit=False,
            )

        if (
            variance is not None
            and abs(variance) >= 1e-9
            and not confirm_recount
            and not submit_with_exception
        ):
            cash_src = cash_three_sources(close_id, conn=c)
            if commit:
                c.commit()
            return {
                **HONESTY,
                "ok": True,
                "staff_result": "PLEASE RECOUNT CASH",
                "staff_message": _staff_submit_message(
                    state="RECOUNT_REQUIRED",
                    cash_sources=cash_src,
                    variance=variance,
                    close_id=close_id,
                    conn=c,
                ),
                "variance_cash_amount": variance,
                "cash_sources": cash_src,
                "close": enrich_close(declared, conn=c),
                "needs_recount": True,
            }

        reconciled = _vc.reconcile(
            close_id,
            verified_person_id=verified,
            identity=identity,
            conn=c,
            commit=False,
        )
        final = reconciled
        staff_result = "CLOSE SAVED"
        if reconciled.get("state") == "VARIANCE_REQUIRES_POLICY":
            if submit_with_exception:
                try:
                    final = _vc.open_exception(
                        close_id,
                        verified_person_id=verified,
                        identity=identity,
                        conn=c,
                        commit=False,
                    )
                    staff_result = "CLOSE SAVED WITH EXCEPTION"
                except _vc.VenueCloseError as exc:
                    if exc.code != "invalid_transition":
                        raise
                    staff_result = "NEEDS MANAGER REVIEW"
            else:
                staff_result = "NEEDS MANAGER REVIEW"
        elif reconciled.get("state") == "EXCEPTION":
            staff_result = "CLOSE SAVED WITH EXCEPTION"
        elif reconciled.get("state") != "VERIFIED_CLOSED":
            staff_result = "CANNOT SUBMIT"
        cash_src = cash_three_sources(close_id, conn=c)
        if commit:
            c.commit()
        msg = _staff_submit_message(
            state=str(final.get("state") or ""),
            cash_sources=cash_src,
            variance=final.get("variance_cash_amount"),
            close_id=close_id,
            conn=c,
        )
        cannot_reason = None
        if staff_result == "CANNOT SUBMIT":
            cannot_reason = f"Close state is {final.get('state')}. Check missing steps."
            msg = cannot_reason
        return {
            **HONESTY,
            "ok": staff_result != "CANNOT SUBMIT",
            "staff_result": staff_result,
            "staff_message": msg,
            "cannot_reason": cannot_reason,
            "cash_sources": cash_src,
            "close": enrich_close(final, conn=c),
            "idempotent": bool(declared.get("idempotent")),
        }
    finally:
        if own:
            c.close()


SOURCE_WIZARD_PACK = "UMA-CLOSE-SOURCE-WIZARD-1"
SIX_STEP_PACK = "UMA-CLOSE-6STEP-REBUILD-2"
UNLINKED_EVIDENCE_SCHEME = "unlinked-evidence://"

# Owner-typed printed shift summaries — second source beside warehouse; never overwrites ESB snapshot.
OWNER_TYPED_PRINTED_SOURCES: dict[str, dict[str, Any]] = {
    "2026-09-29": {
        "close_id": "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad",
        "provenance": (
            "provided by Owner, 5 Oct 2026, during historical Daily Close human test"
        ),
        "figures": {
            "sales_total": 11103306,
            "net_sales_total": 11103306,
            "service_charge": 1221364,
            "tax": 1110331,
            "gross_sales_total": 13435000,
            "pax": 79,
            "bills": 50,
            "cancel": 0,
            "void": 0,
            "cash": 3790000,
            "edc_bni": 2545000,
            "edc_bri": 4465000,
            "qris_bni": 145000,
            "qris_bri": 1065000,
            "scott_etik": 1425000,
            "payment_total": 13435000,
            "non_sales_executive_chef": 78512,
            "total_non_sales": 78512,
        },
    },
}


def _owner_typed_config_for_close(
    close_id: str,
    business_date: str,
) -> dict[str, Any] | None:
    biz = (business_date or "").strip()
    cid = (close_id or "").strip()
    cfg = OWNER_TYPED_PRINTED_SOURCES.get(biz)
    if cfg and (cfg.get("close_id") or "").strip() == cid:
        return cfg
    for row in OWNER_TYPED_PRINTED_SOURCES.values():
        if (row.get("close_id") or "").strip() == cid:
            return row
    return None


def _build_owner_typed_document(
    figures: dict[str, Any],
    *,
    business_date: str,
    provenance: str,
) -> dict[str, Any]:
    """Normalize owner-typed FINAL Shift Summary into receipt document shape."""
    pm_lines = [
        {"raw_label": "Cash", "amount": figures.get("cash")},
        {"raw_label": "EDC BNI", "amount": figures.get("edc_bni")},
        {"raw_label": "EDC BRI", "amount": figures.get("edc_bri")},
        {"raw_label": "QRIS BNI", "amount": figures.get("qris_bni")},
        {"raw_label": "QRIS BRI", "amount": figures.get("qris_bri")},
        {"raw_label": "SCOTT & ETIK", "amount": figures.get("scott_etik")},
    ]
    shift_lines = [
        {"raw_label": "Sales Total", "amount": figures.get("sales_total")},
        {"raw_label": "Net Sales Total", "amount": figures.get("net_sales_total")},
        {"raw_label": "Service Charge", "amount": figures.get("service_charge")},
        {"raw_label": "Tax", "amount": figures.get("tax")},
        {"raw_label": "Gross Sales Total", "amount": figures.get("gross_sales_total")},
        {"raw_label": "Number of Pax", "amount": figures.get("pax")},
        {"raw_label": "Number of Bills", "amount": figures.get("bills")},
        {"raw_label": "Payment Total", "amount": figures.get("payment_total")},
    ]
    nonsales_lines = [
        {
            "raw_label": "Executive Chef",
            "amount": figures.get("non_sales_executive_chef"),
        },
        {
            "raw_label": "Total Non Sales",
            "amount": figures.get("total_non_sales"),
        },
    ]
    raw_doc = {
        "business_date": business_date,
        "ocr_confidence": None,
        "sections": [
            {"raw_title": "Shift Summary", "lines": shift_lines},
            {"raw_title": "Payment Method Summary", "lines": pm_lines},
            {"raw_title": "Non Sales", "lines": nonsales_lines},
        ],
        "provenance": provenance,
        "entry_source": "OWNER_TYPED",
        "image_status": "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER",
    }
    return _vision.normalize_esb_document(raw_doc)


def _has_owner_typed_receipt(close_id: str, conn: sqlite3.Connection) -> bool:
    if not _has_table(conn, "venue_close_esb_closing_receipts"):
        return False
    rows = conn.execute(
        """
        SELECT confirmed_json FROM venue_close_esb_closing_receipts
        WHERE close_id=? AND human_confirm_status IN ('CONFIRMED','EDITED')
        """,
        (close_id.strip(),),
    ).fetchall()
    for row in rows:
        conf = _loads(row["confirmed_json"]) or {}
        if conf.get("entry_source") == "OWNER_TYPED":
            return True
        if conf.get("image_status") == "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER":
            return True
    return False


def ensure_owner_typed_printed_source(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any] | None:
    """Attach configured owner-typed printed source beside frozen warehouse snapshot.

    Idempotent. Never mutates esb_totals_json or warehouse fingerprint on the close row.
    """
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            return None
        biz = (row.get("business_date") or "").strip()
        cfg = _owner_typed_config_for_close(close_id, biz)
        if not cfg:
            return None
        if _has_confirmed_shift_receipt(close_id, c):
            recs = list_esb_closing_receipts(close_id, conn=c)
            confirmed = [
                r for r in recs if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
            ]
            latest = confirmed[-1] if confirmed else {}
            conf = (latest.get("confirmed") or {}) if latest else {}
            return {
                "ok": True,
                "already_present": True,
                "close_id": close_id,
                "image_attached": bool(
                    latest.get("image_object_ref") or latest.get("content_hash")
                ),
                "image_status": conf.get("image_status")
                or (
                    "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER"
                    if conf.get("entry_source") == "OWNER_TYPED"
                    else "MISSING_FILE"
                ),
            }
        figures = dict(cfg.get("figures") or {})
        provenance = str(cfg.get("provenance") or "")
        doc = _build_owner_typed_document(figures, business_date=biz, provenance=provenance)
        der = doc.get("derived") or {}
        cash_f = round(float(figures.get("cash") or 0), 2)
        edc_f = round(
            float(figures.get("edc_bni") or 0) + float(figures.get("edc_bri") or 0), 2
        )
        qris_f = round(
            float(figures.get("qris_bni") or 0) + float(figures.get("qris_bri") or 0), 2
        )
        gross_f = round(float(figures.get("gross_sales_total") or 0), 2)
        mismatch = _api_vs_receipt_mismatch(
            row, cash_amount=cash_f, edc_card_amount=edc_f, qris_amount=qris_f
        )
        rid = f"ESBR-OWNER-TYPED-{uuid.uuid4().hex[:12].upper()}"
        ts = _vc.now_utc_iso()
        confirmed_obj = {
            "cash_amount": cash_f,
            "edc_card_amount": edc_f,
            "qris_amount": qris_f,
            "gross_amount": gross_f,
            "document": doc,
            "entry_source": "OWNER_TYPED",
            "image_status": "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER",
            "provenance": provenance,
            "action": "owner_typed",
            "confirmed_at": ts,
        }
        c.execute(
            """
            INSERT INTO venue_close_esb_closing_receipts (
              esb_receipt_id, close_id, outlet_id, image_object_ref, content_hash,
              evidence_id, extracted_json, confirmed_json,
              cash_amount, edc_card_amount, qris_amount, gross_amount,
              ocr_confidence, ocr_confidence_band, human_confirm_status,
              confirmed_by_person_id, confirmed_at,
              api_mismatch, api_mismatch_json,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                close_id,
                row.get("outlet_id") or OUTLET_UMA,
                None,
                None,
                None,
                _dumps({"document": doc, "entry_source": "OWNER_TYPED"}),
                _dumps(confirmed_obj),
                cash_f,
                edc_f,
                qris_f,
                gross_f,
                None,
                None,
                "CONFIRMED",
                "OWNER-HUMAN-TEST",
                ts,
                1 if mismatch["api_mismatch"] else 0,
                _dumps(mismatch),
                "OWNER-HUMAN-TEST",
                ts,
                ts,
            ),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "attached": True,
            "esb_receipt_id": rid,
            "close_id": close_id,
            "image_attached": False,
            "image_status": "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER",
            "provenance": provenance,
            "dual_source_kept": True,
        }
    finally:
        if own:
            c.close()


def warehouse_source_board(row: dict[str, Any]) -> dict[str, Any]:
    """Frozen warehouse (ESB payment-line) snapshot — never replaced by printed report."""
    totals = row.get("esb_totals") or {}
    split = totals.get("payments_by_bank_split") or {}
    return {
        "source": "warehouse_payment_lines",
        "object": "WAREHOUSE_SNAPSHOT",
        "business_date": row.get("business_date"),
        "fingerprint_sha256": row.get("esb_fingerprint_sha256"),
        "cash_rp": totals.get("cash_from_payments"),
        "finished_bills": totals.get("finished_count"),
        "gross_sales_rp": totals.get("grand_total"),
        "payments_by_bank_split": split,
        "snapshot_frozen": bool(row.get("esb_fingerprint_sha256")),
    }


def printed_shift_source(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Printed FINAL shift report — photo or owner-typed; independent of warehouse."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        biz = (row.get("business_date") or "").strip()
        ensure_owner_typed_printed_source(close_id, conn=c, commit=False)
        recs = list_esb_closing_receipts(close_id, conn=c)
        confirmed = [
            r for r in recs if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
        ]
        latest = _pick_authoritative_shift_receipt(recs)
        conf = (latest.get("confirmed") or {}) if latest else {}
        doc = _document_from_shift_receipt(latest) or {}
        der = doc.get("derived") or {}
        shift = der.get("shift") or {}
        split = der.get("payments_by_bank_split") or {}
        image_ref = latest.get("image_object_ref") or latest.get("object_ref")
        image_hash = latest.get("content_hash")
        has_image = bool(image_ref or image_hash)
        entry_source = conf.get("entry_source") or (
            "OWNER_TYPED"
            if conf.get("image_status") == "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER"
            else ("VISION_CONFIRMED" if has_image else None)
        )
        cfg = _owner_typed_config_for_close(close_id, biz)
        fig = (cfg or {}).get("figures") or {}
        if not split and fig:
            split = _payments_by_bank_split_from_fields(fig)
        cash = latest.get("cash_amount") if latest else None
        if cash is None:
            cash = conf.get("cash_amount")
        if cash is None:
            cash = der.get("cash_amount") or der.get("total_cash")
        if cash is None and fig:
            cash = fig.get("cash")
        bills = shift.get("BILLS")
        if bills is None and fig:
            bills = fig.get("bills")
        gross = shift.get("GROSS_SALES") or (latest.get("gross_amount") if latest else None)
        if gross is None:
            gross = conf.get("gross_amount") or der.get("gross_amount")
        if gross is None and fig:
            gross = fig.get("gross_sales_total")
        pax = shift.get("PAX") if shift else None
        if pax is None and fig:
            pax = fig.get("pax")
        doc_exp = _esb_expected_by_bank(close_id, c) if confirmed else {}
        bni_slot = doc_exp.get("BNI") or {}
        bri_slot = doc_exp.get("BRI") or {}
        man_slot = doc_exp.get("MANDIRI") or {}
        return {
            "source": "printed_shift_report",
            "object": "PRINTED_SHIFT_REPORT",
            "confirmed": bool(confirmed),
            "entry_source": entry_source,
            "provenance": conf.get("provenance"),
            "image_attached": has_image,
            "image_status": (
                conf.get("image_status")
                or ("ATTACHED" if has_image else "MISSING_FILE")
            ),
            "image_object_ref": image_ref,
            "content_hash": image_hash,
            "cash_rp": cash,
            "bills": bills,
            "pax": pax,
            "gross_sales_rp": gross,
            "edc_bni_rp": (
                split.get("EDC_BNI")
                or fig.get("edc_bni")
                or (bni_slot.get("edc_expected") if bni_slot.get("edc_explicit") else None)
            ),
            "edc_bri_rp": (
                split.get("EDC_BRI")
                or fig.get("edc_bri")
                or (bri_slot.get("edc_expected") if bri_slot.get("edc_explicit") else None)
            ),
            "qris_bni_rp": (
                split.get("QRIS_BNI")
                or fig.get("qris_bni")
                or (bni_slot.get("qris_expected") if bni_slot.get("qris_explicit") else None)
            ),
            "qris_bri_rp": (
                split.get("QRIS_BRI")
                or fig.get("qris_bri")
                or (bri_slot.get("qris_expected") if bri_slot.get("qris_explicit") else None)
            ),
            "edc_mandiri_rp": (
                split.get("EDC_MANDIRI")
                or fig.get("edc_mandiri")
                or (man_slot.get("edc_expected") if man_slot.get("edc_explicit") else None)
            ),
            "qris_mandiri_rp": (
                split.get("QRIS_MANDIRI")
                or fig.get("qris_mandiri")
                or (man_slot.get("qris_expected") if man_slot.get("qris_explicit") else None)
            ),
            "scott_etik_rp": split.get("SCOTT_ETIK") or fig.get("scott_etik"),
            "payment_total_rp": shift.get("PAYMENT_TOTAL") or fig.get("payment_total"),
            "non_sales_executive_chef_rp": fig.get("non_sales_executive_chef"),
            "payments_by_bank_split": split,
        }
    finally:
        if own:
            c.close()


def source_discrepancy_between(
    warehouse: dict[str, Any],
    printed: dict[str, Any],
) -> dict[str, Any]:
    """Visible warehouse vs printed differences — never auto-resolved."""
    w_cash = warehouse.get("cash_rp")
    p_cash = printed.get("cash_rp")
    w_bills = warehouse.get("finished_bills")
    p_bills = printed.get("bills")
    cash_delta: float | None = None
    bills_delta: int | None = None
    flags: list[str] = []
    if w_cash is not None and p_cash is not None:
        cash_delta = round(float(w_cash) - float(p_cash), 2)
        if abs(cash_delta) >= 0.01:
            flags.append("CASH_MISMATCH")
    if w_bills is not None and p_bills is not None:
        bills_delta = int(w_bills) - int(p_bills)
        if bills_delta != 0:
            flags.append("BILLS_MISMATCH")
    return {
        "has_discrepancy": bool(flags),
        "warehouse": {
            "cash_rp": w_cash,
            "finished_bills": w_bills,
            "staff_label": "Historical ESB data",
        },
        "printed": {
            "cash_rp": p_cash,
            "bills": p_bills,
            "staff_label": "Final report",
        },
        "difference": {
            "cash_rp": cash_delta,
            "bills": bills_delta,
        },
        "auto_resolve": False,
        "staff_heading": "ESB DATA DIFFERENCE FOUND" if flags else None,
        "flags": flags,
    }


def wizard_petty_summary(
    business_date: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Petty movements for one business date only — not live balance."""
    own = conn is None
    c = conn or db_connect()
    try:
        biz = (business_date or "").strip()
        out_movements: list[dict[str, Any]] = []
        in_movements: list[dict[str, Any]] = []
        petty_out = 0.0
        petty_in = 0.0
        needs_review = False
        review_reason: str | None = None
        if biz:
            try:
                _petty.ensure_schema(c)
                petty_out = _petty.sum_petty_out_for_date(biz, conn=c)
                petty_in = _petty.sum_petty_in_for_date(biz, conn=c)
                out_movements = _petty.list_petty_out_for_date(biz, conn=c)
                in_movements = _petty.list_petty_in_for_date(biz, conn=c)
            except (sqlite3.Error, RuntimeError, OSError):
                needs_review = True
                review_reason = "ledger_unreadable"
        forbidden_ids = ("PETTY-UMA-6D853EEAE0",)
        for mv in out_movements + in_movements:
            pid = str(mv.get("movement_id") or mv.get("petty_movement_id") or "")
            if any(x in pid for x in forbidden_ids):
                needs_review = True
                review_reason = "forbidden_movement_on_date"
        if biz == "2026-09-29" and not out_movements and not in_movements:
            needs_review = True
            review_reason = "no_proved_movements_for_date"
        return {
            **HONESTY,
            "ok": True,
            "business_date": biz,
            "petty_out_total": petty_out,
            "petty_in_total": petty_in,
            "out_movements": out_movements,
            "in_movements": in_movements,
            "needs_review": needs_review,
            "review_heading": (
                "PETTY CASH FOR THIS DATE NEEDS REVIEW" if needs_review else None
            ),
            "review_reason": review_reason,
            "live_balance_excluded": True,
        }
    finally:
        if own:
            c.close()


def wizard_bank_cards(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Staff bank evidence — UNKNOWN≠ZERO, UNREAD≠NOT USED.

    Rules:
    - Banks with known expected Card/QRIS → ADD RECEIPT (RECEIPT_REQUIRED)
    - Payment lines present but unread/null and no warehouse amount → UNCERTAIN
      ("WE COULDN'T READ THIS PAYMENT") with CHECK — never silent NOT USED
    - Banks unused per ESB/confirmed figures → omitted (hidden), never a NOT USED wall
    """
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        oid = (row.get("outlet_id") or OUTLET_UMA).strip()
        banks = list_outlet_banks(oid, conn=c)
        has_shift = _has_confirmed_shift_receipt(close_id, c)
        shift_expected = _shift_expected_by_bank(close_id, c) if has_shift else {}
        # Banks named on the confirmed document with null amounts = unread.
        unread_banks: set[str] = set()
        doc = _authoritative_shift_document(close_id, c) if has_shift else None
        if isinstance(doc, dict):
            for sec in doc.get("sections") or []:
                if sec.get("normalized_type") != "PAYMENT_METHODS":
                    continue
                for ln in sec.get("lines") or []:
                    if ln.get("normalized_type") not in ("EDC", "QRIS"):
                        continue
                    bank = _norm_bank(ln.get("bank_acquirer") or "")
                    if not bank:
                        continue
                    amt = ln.get("human_confirmed_value")
                    if amt is None:
                        amt = ln.get("amount")
                    if amt is None and not _bank_slot_on_shift(shift_expected.get(bank)):
                        unread_banks.add(bank)
        receipts = list_edc_receipts(close_id, conn=c)
        current_by_bank: dict[str, dict[str, Any]] = {}
        for r in receipts:
            bank = _norm_bank(r.get("acquirer_label") or "")
            if (
                bank
                and str(r.get("evidence_role") or "CURRENT").upper() == "CURRENT"
                and r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
            ):
                current_by_bank[bank] = r
        cards: list[dict[str, Any]] = []
        outlet_labels = [
            _norm_bank(b.get("bank_label") or "")
            for b in (banks.get("banks") or [])
        ]
        # Union of outlet banks + expected + unread (so Mandiri from warehouse appears).
        labels: list[str] = []
        for lab in outlet_labels + list(shift_expected.keys()) + sorted(unread_banks):
            if lab and lab not in labels:
                labels.append(lab)
        for label in labels:
            slot = shift_expected.get(label) or {}
            on_shift = _bank_slot_on_shift(slot)
            if not has_shift:
                continue
            if not on_shift and label in unread_banks:
                cards.append(
                    {
                        "bank": label,
                        "staff_label": "WE COULDN'T READ THIS PAYMENT",
                        "status": "UNCERTAIN",
                        "expected_edc": None,
                        "expected_qris": None,
                        "actual_edc": None,
                        "actual_qris": None,
                        "difference_edc": None,
                        "difference_qris": None,
                        "receipt_added": False,
                        "needs_check": True,
                    }
                )
                continue
            if not on_shift:
                # Truly unused from ESB/confirmed — hide (do not emit NOT_USED).
                continue
            edc_exp = (
                float(slot["edc_expected"])
                if slot.get("edc_explicit")
                else None
            )
            qris_exp = (
                float(slot["qris_expected"])
                if slot.get("qris_explicit")
                else None
            )
            cur = current_by_bank.get(label)
            edc_act = float(cur.get("edc_card_amount") or 0) if cur else None
            qris_act = float(cur.get("qris_amount") or 0) if cur else None
            edc_diff = (
                None
                if edc_act is None or edc_exp is None
                else round(edc_act - edc_exp, 2)
            )
            qris_diff = (
                None
                if qris_act is None or qris_exp is None
                else round(qris_act - qris_exp, 2)
            )
            if cur:
                staff_label = (
                    "MATCH"
                    if (edc_diff == 0 or edc_diff is None)
                    and (qris_diff == 0 or qris_diff is None)
                    else "DIFFERENCE FOUND"
                )
                status = "MATCH" if staff_label == "MATCH" else "MISMATCH"
            else:
                staff_label = "ADD BANK RECEIPT"
                status = "RECEIPT_REQUIRED"
            cards.append(
                {
                    "bank": label,
                    "staff_label": staff_label,
                    "status": status,
                    "expected_edc": edc_exp,
                    "expected_qris": qris_exp,
                    "actual_edc": edc_act,
                    "actual_qris": qris_act,
                    "difference_edc": edc_diff if cur else None,
                    "difference_qris": qris_diff if cur else None,
                    "receipt_added": bool(cur),
                    "expected_source": slot.get("expected_source") or "confirmed_shift",
                    "needs_check": False,
                }
            )
        need_edit = bool(
            has_shift
            and not cards
            and unread_banks
        )
        # If shift confirmed but zero bank cards and no unread lines either,
        # still surface CHECK when vision failed entirely (no bank amounts anywhere).
        if has_shift and not cards and _shift_bank_figures_incomplete(close_id, c):
            need_edit = True
            cards.append(
                {
                    "bank": "",
                    "staff_label": "WE COULDN'T READ THIS PAYMENT",
                    "status": "UNCERTAIN",
                    "expected_edc": None,
                    "expected_qris": None,
                    "actual_edc": None,
                    "actual_qris": None,
                    "difference_edc": None,
                    "difference_qris": None,
                    "receipt_added": False,
                    "needs_check": True,
                }
            )
        staff_message = None
        if need_edit or any(x.get("status") == "UNCERTAIN" for x in cards):
            staff_message = (
                "We couldn't read every payment — tap CHECK and type the amounts."
            )
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "shift_receipt_confirmed": has_shift,
            "bank_figures_need_edit": need_edit,
            "staff_message": staff_message,
            "cards": cards,
            "staff_wizard": True,
            "unused_banks_hidden": True,
            "unknown_is_not_zero": True,
            "unread_is_not_unused": True,
        }
    finally:
        if own:
            c.close()



def wizard_cash_summary(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Cash step — shift report cash basis; one next-step message."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        printed = printed_shift_source(close_id, conn=c)
        petty = wizard_petty_summary(str(row.get("business_date") or ""), conn=c)
        has_shift = bool(printed.get("confirmed"))
        shift_cash = printed.get("cash_rp")
        petty_out = petty.get("petty_out_total") or 0.0
        petty_in = petty.get("petty_in_total") or 0.0
        opening: float | None = None
        cfg = get_outlet_config((row.get("outlet_id") or OUTLET_UMA).strip(), conn=c)
        if cfg and cfg.get("till_float_idr") is not None:
            opening = round(float(cfg["till_float_idr"]), 2)
        expected: float | None = None
        next_step: str | None = None
        formula_note: str | None = None
        if not has_shift:
            next_step = "Confirm the shift report first"
        elif shift_cash is not None and opening is not None:
            expected = round(
                opening + float(shift_cash) - float(petty_out) + float(petty_in), 2
            )
            formula_note = (
                "Opening till float plus shift report cash, minus petty paid out, "
                "plus petty paid in, for this business date only."
            )
        counted = row.get("declared_cash_amount")
        if counted is not None:
            counted = round(float(counted), 2)
        difference: float | None = None
        if expected is not None and counted is not None:
            difference = round(counted - expected, 2)
        diff_label: str | None = None
        if difference is not None:
            diff_label = format_variance_label(difference)
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "shift_report_cash": shift_cash,
            "opening_till_float": opening,
            "petty_cash_paid_today": petty_out,
            "petty_cash_in_today": petty_in,
            "expected_cash_in_till": expected,
            "cash_formula_note": formula_note,
            "cash_counted": counted,
            "difference": difference,
            "difference_label": diff_label,
            "next_step": next_step,
            "shift_report_confirmed": has_shift,
        }
    finally:
        if own:
            c.close()


def wizard_submit_readiness(
    close_id: str,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Single next action + submit gate for staff wizard."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        warehouse = warehouse_source_board(row)
        printed = printed_shift_source(close_id, conn=c)
        discrepancy = source_discrepancy_between(warehouse, printed)
        banks = wizard_bank_cards(close_id, conn=c)
        cash = wizard_cash_summary(close_id, conn=c)
        petty = wizard_petty_summary(str(row.get("business_date") or ""), conn=c)
        missing: list[str] = []
        next_action = "Add the printed shift report"
        esb_ack = get_workflow_ack(close_id, "esb_data_difference_ack", conn=c)
        figures_yes = get_workflow_ack(close_id, "shift_figures_yes", conn=c)
        if not printed.get("confirmed"):
            missing.append("shift_report")
        elif not figures_yes:
            missing.append("shift_figures_yes")
            next_action = "Confirm shift report figures — tap YES when they match"
        elif discrepancy.get("has_discrepancy") and not esb_ack:
            missing.append("source_discrepancy_ack")
            next_action = "Review ESB data difference — tap CONTINUE when ready"
        else:
            next_action = "Add bank receipts for terminals on the shift report"
        if printed.get("confirmed"):
            for card in banks.get("cards") or []:
                if card.get("status") == "RECEIPT_REQUIRED":
                    missing.append(f"bank_receipt_{card.get('bank')}")
                    next_action = f"Add bank receipt for {card.get('bank')}"
                    break
            if not any(m.startswith("bank_receipt_") for m in missing):
                if cash.get("cash_counted") is None:
                    missing.append("cash_counted")
                    next_action = cash.get("next_step") or "Enter cash counted in till"
                elif cash.get("difference_label") not in (None, "MATCHES"):
                    missing.append("cash_difference_ack")
                    next_action = "Review cash difference before submit"
        soft_missing = {"source_discrepancy_ack", "cash_difference_ack"}
        hard_missing = [m for m in missing if m not in soft_missing]
        submit_enabled = not missing and row.get("state") not in (
            "VERIFIED_CLOSED",
            "CANCELLED",
        )
        block = None
        try:
            from core import uma_hist_close_queue1 as _hist_q

            block = _hist_q.submit_block_reason(
                close_id, row, verified_person_id=verified_person_id, conn=c
            )
            if block:
                submit_enabled = False
                missing.append("protected_close")
                hard_missing = [m for m in missing if m not in soft_missing]
                next_action = block
        except ImportError:
            pass
        has_exception = bool(discrepancy.get("has_discrepancy")) or petty.get(
            "needs_review"
        )
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "submit_enabled": submit_enabled,
            "submit_with_exception_available": has_exception and not hard_missing,
            "missing_steps": missing,
            "next_action": next_action if not submit_enabled else "Submit close",
            "has_exception": has_exception,
            "protected_submit_block": block,
        }
    finally:
        if own:
            c.close()


def _loads_ack(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def get_workflow_ack(
    close_id: str,
    ack_kind: str,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    if not _has_table(conn, "venue_close_workflow_acks"):
        return None
    row = conn.execute(
        """
        SELECT ack_json FROM venue_close_workflow_acks
        WHERE close_id=? AND ack_kind=?
        """,
        (close_id.strip(), ack_kind.strip()),
    ).fetchone()
    if not row:
        return None
    return _loads_ack(row["ack_json"])


def record_workflow_ack(
    close_id: str,
    ack_kind: str,
    payload: dict[str, Any],
    *,
    conn: sqlite3.Connection,
    commit: bool = False,
) -> dict[str, Any]:
    ensure_schema(conn)
    ts = _vc.now_utc_iso()
    conn.execute(
        """
        INSERT INTO venue_close_workflow_acks (close_id, ack_kind, ack_json, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(close_id, ack_kind) DO UPDATE SET
          ack_json=excluded.ack_json,
          created_at=excluded.created_at
        """,
        (close_id.strip(), ack_kind.strip(), json.dumps(payload, sort_keys=True), ts),
    )
    if commit:
        conn.commit()
    return payload


def discover_unlinked_evidence_for_date(
    business_date: str,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Read-only discovery of nightly unlinked evidence for one business date."""
    biz = (business_date or "").strip()
    shift_reports: list[dict[str, Any]] = []
    edc_receipts: list[dict[str, Any]] = []
    if not biz or not _has_table(conn, "bzg_ops_evidence_unlinked"):
        return {
            "ok": True,
            "business_date": biz,
            "shift_reports": shift_reports,
            "edc_receipts": edc_receipts,
        }
    rows = conn.execute(
        """
        SELECT queue_id, file_path, file_kind, file_mtime, migration_status
        FROM bzg_ops_evidence_unlinked
        WHERE migration_status='EVIDENCE UNLINKED' AND file_kind='nightly'
          AND substr(file_mtime, 1, 10)=?
        ORDER BY file_mtime
        """,
        (biz,),
    ).fetchall()
    for row in rows:
        fp = str(row["file_path"] or "")
        name = Path(fp).name.lower()
        item = {
            "queue_id": row["queue_id"],
            "file_path": fp,
            "file_mtime": row["file_mtime"],
            "object_ref": f"{UNLINKED_EVIDENCE_SCHEME}{row['queue_id']}",
            "thumbnail_url": (
                f"/api/venue-close/receipt-image?ref="
                f"{UNLINKED_EVIDENCE_SCHEME}{row['queue_id']}"
            ),
        }
        if name.startswith("pos_"):
            shift_reports.append(item)
        elif name.startswith("edc_"):
            edc_receipts.append(item)
    return {
        **HONESTY,
        "ok": True,
        "business_date": biz,
        "shift_reports": shift_reports,
        "edc_receipts": edc_receipts,
    }


def resolve_unlinked_evidence_path(object_ref: str | None) -> Path | None:
    ref = (object_ref or "").strip()
    if not ref.startswith(UNLINKED_EVIDENCE_SCHEME):
        return None
    queue_id = ref[len(UNLINKED_EVIDENCE_SCHEME) :].strip()
    if not queue_id:
        return None
    c = db_connect()
    try:
        if not _has_table(c, "bzg_ops_evidence_unlinked"):
            return None
        row = c.execute(
            "SELECT file_path FROM bzg_ops_evidence_unlinked WHERE queue_id=?",
            (queue_id,),
        ).fetchone()
        if not row:
            return None
        path = Path(str(row["file_path"]))
        return path if path.is_file() else None
    finally:
        c.close()


def register_shift_report_photo(
    close_id: str,
    *,
    object_ref: str,
    content_hash: str,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Append DRAFT shift-report evidence with image — preserved for resume."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        ref = (object_ref or "").strip()
        ch = (content_hash or "").strip()
        if not ref or not ch:
            raise BzgDailyCloseError(
                "shift report photo requires object_ref and content_hash",
                code="missing_evidence",
            )
        try:
            _weg.refuse_quarantined_ref(ref, receipt_dir=CLOSE_RECEIPT_DIR, label="shift report")
        except ValueError as exc:
            raise BzgDailyCloseError(str(exc), code="quarantined_evidence") from exc
        for rec in list_esb_closing_receipts(close_id, conn=c):
            if (
                rec.get("image_object_ref") == ref
                and rec.get("content_hash") == ch
            ):
                return {
                    **HONESTY,
                    "ok": True,
                    "idempotent": True,
                    "esb_receipt_id": rec.get("esb_receipt_id"),
                    "object_ref": ref,
                    "content_hash": ch,
                }
        rid = f"ESBR-PHOTO-{uuid.uuid4().hex[:12].upper()}"
        ts = _vc.now_utc_iso()
        c.execute(
            """
            INSERT INTO venue_close_esb_closing_receipts (
              esb_receipt_id, close_id, outlet_id, image_object_ref, content_hash,
              extracted_json, confirmed_json, human_confirm_status,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?)
            """,
            (
                rid,
                close_id,
                row.get("outlet_id") or OUTLET_UMA,
                ref,
                ch,
                _dumps({"entry_source": "PHONE_UPLOAD", "uploaded_at": ts}),
                _dumps({"image_object_ref": ref, "content_hash": ch}),
                verified_person_id,
                ts,
                ts,
            ),
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "esb_receipt_id": rid,
            "object_ref": ref,
            "content_hash": ch,
            "human_confirm_status": "DRAFT",
        }
    finally:
        if own:
            c.close()


def save_shift_human_corrections(
    close_id: str,
    *,
    verified_person_id: str,
    figures: dict[str, Any],
    object_ref: str | None = None,
    content_hash: str | None = None,
    extracted: dict[str, Any] | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Staff EDIT on shift report — append-only human correction; does not advance YES."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        biz = str(row.get("business_date") or "")
        fig = figures or {}
        owner_figs = {
            "gross_sales_total": fig.get("gross_sales_rp"),
            "bills": fig.get("bills"),
            "pax": fig.get("pax"),
            "cash": fig.get("cash_rp"),
            "edc_bni": fig.get("edc_bni_rp"),
            "qris_bni": fig.get("qris_bni_rp"),
            "edc_bri": fig.get("edc_bri_rp"),
            "qris_bri": fig.get("qris_bri_rp"),
            "edc_mandiri": fig.get("edc_mandiri_rp"),
            "qris_mandiri": fig.get("qris_mandiri_rp"),
            "scott_etik": fig.get("scott_etik_rp"),
            "non_sales_executive_chef": fig.get("non_sales_executive_chef_rp"),
            "payment_total": fig.get("gross_sales_rp"),
        }
        doc = _build_owner_typed_document(
            owner_figs,
            business_date=biz,
            provenance="Human correction during close workflow — original kept",
        )
        overrides: dict[str, Any] = {
            "document": doc,
            "cash_amount": fig.get("cash_rp"),
            "gross_amount": fig.get("gross_sales_rp"),
        }
        return confirm_esb_closing_receipt(
            close_id,
            verified_person_id=verified_person_id,
            action="edit",
            object_ref=object_ref,
            content_hash=content_hash,
            extracted=extracted,
            confirmed_overrides=overrides,
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=commit,
        )
    finally:
        if own:
            c.close()


def confirm_shift_figures_yes(
    close_id: str,
    *,
    verified_person_id: str,
    object_ref: str | None = None,
    content_hash: str | None = None,
    extracted: dict[str, Any] | None = None,
    confirmed_overrides: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Staff tapped YES — persist human confirmation and advance workflow."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        printed_before = printed_shift_source(close_id, conn=c)
        if not _shift_figures_readable(extracted, printed_before):
            raise BzgDailyCloseError(
                "Nothing read — tap EDIT and type the figures from the report.",
                code="shift_figures_empty",
                http_status=409,
                details={
                    "staff_message": (
                        "Nothing read — tap EDIT and type the figures from the report."
                    ),
                },
            )
        overrides = dict(confirmed_overrides or {})
        if not isinstance(overrides.get("document"), dict):
            biz = str(row.get("business_date") or "")
            prior_doc = _authoritative_shift_document(close_id, conn=c)
            flat_src = extracted if isinstance(extracted, dict) else {}
            if not flat_src and printed_before:
                flat_src = {
                    "gross_sales_rp": printed_before.get("gross_sales_rp"),
                    "cash_rp": printed_before.get("cash_rp"),
                    "bills": printed_before.get("bills"),
                    "pax": printed_before.get("pax"),
                    "edc_bni_rp": printed_before.get("edc_bni_rp"),
                    "qris_bni_rp": printed_before.get("qris_bni_rp"),
                    "edc_bri_rp": printed_before.get("edc_bri_rp"),
                    "qris_bri_rp": printed_before.get("qris_bri_rp"),
                    "edc_mandiri_rp": printed_before.get("edc_mandiri_rp"),
                    "qris_mandiri_rp": printed_before.get("qris_mandiri_rp"),
                    "scott_etik_rp": printed_before.get("scott_etik_rp"),
                    "non_sales_executive_chef_rp": printed_before.get(
                        "non_sales_executive_chef_rp"
                    ),
                }
            if isinstance(prior_doc, dict) and prior_doc.get("sections"):
                overrides["document"] = prior_doc
            elif flat_src:
                owner_figs = _flat_shift_to_owner_figures(flat_src)
                overrides["document"] = _build_owner_typed_document(
                    owner_figs,
                    business_date=biz,
                    provenance=(
                        "Confirmed shift figures — human correction preserved"
                    ),
                )
            if overrides.get("document"):
                overrides.setdefault(
                    "cash_amount",
                    flat_src.get("cash_rp") or flat_src.get("cash_amount"),
                )
                overrides.setdefault(
                    "gross_amount",
                    flat_src.get("gross_sales_rp") or flat_src.get("gross_amount"),
                )
        out = confirm_esb_closing_receipt(
            close_id,
            verified_person_id=verified_person_id,
            action="looks_correct",
            object_ref=object_ref,
            content_hash=content_hash,
            extracted=extracted,
            confirmed_overrides=overrides,
            conn=c,
            commit=False,
        )
        printed_after = printed_shift_source(close_id, conn=c)
        record_workflow_ack(
            close_id,
            "shift_figures_yes",
            {
                "confirmed_at": _vc.now_utc_iso(),
                "by": verified_person_id,
                "printed_before": printed_before,
                "printed_after": printed_after,
                "raw_extraction": extracted,
                "corrections": confirmed_overrides,
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "shift_figures_yes": True,
            "confirm": out,
        }
    finally:
        if own:
            c.close()


def link_unlinked_shift_report(
    close_id: str,
    *,
    queue_id: str,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Link discovered nightly shift photo to close — append-only, provenance kept."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        if not _has_table(c, "bzg_ops_evidence_unlinked"):
            raise BzgDailyCloseError("evidence queue missing", code="missing_table")
        row = c.execute(
            "SELECT * FROM bzg_ops_evidence_unlinked WHERE queue_id=?",
            (queue_id.strip(),),
        ).fetchone()
        if not row:
            raise BzgDailyCloseError("evidence not found", code="not_found", http_status=404)
        fp = Path(str(row["file_path"]))
        if not fp.is_file():
            raise BzgDailyCloseError("evidence file missing", code="missing_file")
        data = fp.read_bytes()
        ch = hashlib.sha256(data).hexdigest()
        stored = save_close_receipt_bytes(
            data=data,
            kind="esb",
            close_id=close_id,
            filename=fp.name,
            content_type="image/jpeg",
        )
        reg = register_shift_report_photo(
            close_id,
            object_ref=stored["object_ref"],
            content_hash=stored["content_hash"],
            verified_person_id=verified_person_id,
            conn=c,
            commit=False,
        )
        ts = _vc.now_utc_iso()
        c.execute(
            """
            UPDATE bzg_ops_evidence_unlinked
            SET migration_status='EVIDENCE LINKED',
                linked_record_type='venue_close_esb_closing_receipt',
                linked_record_id=?,
                match_rule='staff_use_this_report'
            WHERE queue_id=?
            """,
            (reg.get("esb_receipt_id"), queue_id.strip()),
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "linked": True,
            "queue_id": queue_id,
            "object_ref": stored["object_ref"],
            "content_hash": stored["content_hash"],
            "provenance": {"source_path": str(fp), "linked_at": ts},
            **reg,
        }
    finally:
        if own:
            c.close()


def link_unlinked_edc_receipt(
    close_id: str,
    *,
    queue_id: str,
    bank_label: str,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Link discovered nightly EDC slip — staff USE THIS RECEIPT."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        if not _has_table(c, "bzg_ops_evidence_unlinked"):
            raise BzgDailyCloseError("evidence queue missing", code="missing_table")
        row = c.execute(
            "SELECT * FROM bzg_ops_evidence_unlinked WHERE queue_id=?",
            (queue_id.strip(),),
        ).fetchone()
        if not row:
            raise BzgDailyCloseError("evidence not found", code="not_found", http_status=404)
        fp = Path(str(row["file_path"]))
        if not fp.is_file():
            raise BzgDailyCloseError("evidence file missing", code="missing_file")
        data = fp.read_bytes()
        ch = hashlib.sha256(data).hexdigest()
        stored = save_close_receipt_bytes(
            data=data,
            kind="edc",
            close_id=close_id,
            filename=fp.name,
        )
        ts = _vc.now_utc_iso()
        rid = f"EDCR-UNLINKED-{uuid.uuid4().hex[:12].upper()}"
        c.execute(
            """
            INSERT INTO venue_close_edc_receipts (
              edc_receipt_id, close_id, outlet_id, acquirer_label,
              human_confirm_status, image_object_ref, content_hash, evidence_role,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'DRAFT', ?, ?, 'CURRENT', ?, ?, ?)
            """,
            (
                rid,
                close_id,
                OUTLET_UMA,
                _norm_bank(bank_label),
                stored["object_ref"],
                stored["content_hash"],
                verified_person_id,
                ts,
                ts,
            ),
        )
        c.execute(
            """
            UPDATE bzg_ops_evidence_unlinked
            SET migration_status='EVIDENCE LINKED',
                linked_record_type='venue_close_edc_receipt',
                linked_record_id=?,
                match_rule='staff_use_this_receipt'
            WHERE queue_id=?
            """,
            (rid, queue_id.strip()),
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "linked": True,
            "edc_receipt_id": rid,
            "bank": _norm_bank(bank_label),
            "object_ref": stored["object_ref"],
            "content_hash": stored["content_hash"],
            "provenance": {"source_path": str(fp), "linked_at": ts},
        }
    finally:
        if own:
            c.close()


def declare_cash_with_note(
    close_id: str,
    *,
    declared_cash_amount: float,
    cash_why_note: str | None = None,
    verified_person_id: str,
    object_ref: str | None = None,
    content_hash: str | None = None,
    identity: dict[str, Any] | None = None,
    allow_test_write: bool = False,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """One confirmed cash count — debounced basis for submit variance."""
    own = conn is None
    c = conn or db_connect()
    try:
        cash_wiz = wizard_cash_summary(close_id, conn=c)
        expected = cash_wiz.get("expected_cash_in_till")
        amt = round(float(declared_cash_amount), 2)
        existing = get_workflow_ack(close_id, "cash_count_confirmed", conn=c)
        if existing:
            if (
                round(float(existing.get("counted") or 0), 2) == amt
                and (existing.get("why_note") or "") == (cash_why_note or "")
            ):
                out = _vc.get_close(close_id, conn=c)
                return {**(out or {}), **HONESTY, "idempotent": True}
        out = attach_till_with_z_report(
            close_id,
            declared_cash_amount=amt,
            verified_person_id=verified_person_id,
            object_ref=object_ref,
            content_hash=content_hash,
            notes=cash_why_note,
            identity=identity,
            allow_test_write=allow_test_write,
            conn=c,
            commit=False,
        )
        record_workflow_ack(
            close_id,
            "cash_count_confirmed",
            {
                "counted": amt,
                "expected_cash_in_till": expected,
                "why_note": (cash_why_note or "").strip() or None,
                "confirmed_at": _vc.now_utc_iso(),
                "by": verified_person_id,
            },
            conn=c,
            commit=False,
        )
        if expected is not None:
            record_workflow_ack(
                close_id,
                "cash_expected_basis",
                {
                    "expected_cash_in_till": expected,
                    "counted": amt,
                    "recorded_at": _vc.now_utc_iso(),
                },
                conn=c,
                commit=False,
            )
        if commit:
            c.commit()
        return {**out, **HONESTY, "cash_why_note": (cash_why_note or "").strip() or None}
    finally:
        if own:
            c.close()


def peek_business_date(
    business_date: str,
    *,
    verified_person_id: str | None = None,
    outlet_id: str = OUTLET_UMA,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read-only date open — never creates or mutates a close row."""
    own = conn is None
    c = conn or db_connect()
    try:
        from core import uma_hist_close_queue1 as _hist_q

        biz = (business_date or "").strip()
        if not biz:
            raise BzgDailyCloseError("business_date required", code="missing_date")
        row = _vc.get_close(business_date=biz, conn=c)
        closes = _hist_q._closes_for_date(biz, conn=c)  # noqa: SLF001
        close_id = row.get("close_id") if row else None
        ev = _hist_q._evidence_counts(close_id, conn=c)  # noqa: SLF001
        ui_status = _hist_q.canonical_ui_status(
            business_date=biz, closes=closes, evidence=ev
        )
        discovered = discover_unlinked_evidence_for_date(biz, conn=c)
        action = "START"
        ui_label = "OPEN"
        if row:
            st = str(row.get("state") or "")
            if st in ("VERIFIED_CLOSED",):
                action = "VIEW_CLOSE"
                ui_label = "VIEW CLOSE"
            elif st in ("EXCEPTION", "VARIANCE_REQUIRES_POLICY"):
                action = "REVIEW_EXCEPTION"
                ui_label = "REVIEW EXCEPTION"
            elif st in ("CANCELLED",):
                action = "START"
                ui_label = "OPEN"
            else:
                action = "CONTINUE"
                ui_label = "CONTINUE"
        elif discovered.get("shift_reports") or discovered.get("edc_receipts"):
            action = "CONTINUE"
            ui_label = "CONTINUE"
        owner_typed = OWNER_TYPED_PRINTED_SOURCES.get(biz)
        return {
            **HONESTY,
            "ok": True,
            "pack": SIX_STEP_PACK,
            "read_only_peek": True,
            "business_date": biz,
            "has_close": bool(row),
            "close_id": close_id,
            "state": row.get("state") if row else None,
            "ui_status": ui_status,
            "action": action,
            "action_label": ui_label,
            "outlet_id": outlet_id,
            "discovered_evidence": discovered,
            "owner_typed_available": bool(owner_typed),
        }
    finally:
        if own:
            c.close()


def ensure_close_on_evidence(
    business_date: str,
    *,
    verified_person_id: str,
    outlet_id: str = OUTLET_UMA,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create or resume a close only when staff takes an evidence action."""
    biz = (business_date or "").strip()
    if not biz:
        raise BzgDailyCloseError("business_date required", code="missing_date")
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(business_date=biz, conn=c)
        created = False
        if not row or str(row.get("state") or "") == "CANCELLED":
            out = open_human_close(
                biz,
                verified_person_id=verified_person_id,
                outlet_id=outlet_id,
                identity=identity,
                conn=c,
                commit=False,
            )
            row = _vc.get_close(out["close_id"], conn=c) or out
            created = bool(out.get("created"))
        close_id = str(row.get("close_id") or "")
        if close_id and not row.get("esb_fingerprint_sha256"):
            try:
                _vc.capture_esb_snapshot(
                    close_id,
                    verified_person_id=verified_person_id,
                    business_date=biz,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
                row = _vc.get_close(close_id, conn=c) or row
            except _vc.VenueCloseError:
                pass
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "created": created,
            "close": enrich_close(row, conn=c),
            "close_id": close_id,
            "business_date": biz,
        }
    finally:
        if own:
            c.close()


def list_shift_report_evidence(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """All shift-report photos preserved — selected final marked."""
    own = conn is None
    c = conn or db_connect()
    try:
        recs = list_esb_closing_receipts(close_id, conn=c)
        selected_ref, selected_hash = _resolve_shift_report_evidence(close_id, c)
        items: list[dict[str, Any]] = []
        for rec in recs:
            ref = rec.get("image_object_ref") or rec.get("object_ref")
            ch = rec.get("content_hash")
            status = rec.get("human_confirm_status")
            items.append(
                {
                    "esb_receipt_id": rec.get("esb_receipt_id"),
                    "image_object_ref": ref,
                    "content_hash": ch,
                    "human_confirm_status": status,
                    "is_selected_final": bool(
                        ref and ref == selected_ref and ch == selected_hash
                    ),
                    "confirmed": status in ("CONFIRMED", "EDITED"),
                    "has_image": bool(ref or ch),
                    "entry_source": (rec.get("confirmed") or {}).get("entry_source"),
                }
            )
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "reports": items,
            "selected_object_ref": selected_ref,
            "selected_content_hash": selected_hash,
        }
    finally:
        if own:
            c.close()


def ensure_esb_difference_exception(
    close_id: str,
    discrepancy: dict[str, Any],
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection,
    commit: bool = False,
) -> dict[str, Any]:
    """Idempotent workflow exception for ESB vs printed difference."""
    if not discrepancy.get("has_discrepancy"):
        return {"ok": True, "created": False, "reason": "no_discrepancy"}
    existing = get_workflow_ack(close_id, "esb_data_difference", conn=conn)
    if existing:
        return {**existing, "ok": True, "created": False, "idempotent": True}
    payload = {
        "kind": "esb_data_difference",
        "heading": "ESB DATA DIFFERENCE FOUND",
        "final_report": discrepancy.get("printed") or {},
        "historical_esb": discrepancy.get("warehouse") or {},
        "difference": discrepancy.get("difference") or {},
        "created_by": verified_person_id,
        "created_at": _vc.now_utc_iso(),
    }
    record_workflow_ack(close_id, "esb_data_difference", payload, conn=conn, commit=commit)
    return {**payload, "ok": True, "created": True}


def ack_esb_data_difference(
    close_id: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Staff tapped CONTINUE on ESB difference panel."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        warehouse = warehouse_source_board(row)
        printed = printed_shift_source(close_id, conn=c)
        discrepancy = source_discrepancy_between(warehouse, printed)
        exc = ensure_esb_difference_exception(
            close_id,
            discrepancy,
            verified_person_id=verified_person_id,
            conn=c,
            commit=False,
        )
        record_workflow_ack(
            close_id,
            "esb_data_difference_ack",
            {"acked_at": _vc.now_utc_iso(), "by": verified_person_id},
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "exception": exc,
            "source_discrepancy": discrepancy,
        }
    finally:
        if own:
            c.close()


def _workflow_needs_bank_receipts(
    close_id: str,
    business_date: str,
    *,
    conn: sqlite3.Connection,
) -> bool:
    """Banks with expected amounts stay open until receipt confirmed; offer found slips."""
    banks = wizard_bank_cards(close_id, conn=conn)
    cards = banks.get("cards") or []
    if banks.get("bank_figures_need_edit"):
        return True
    if any(
        c.get("status") in ("RECEIPT_REQUIRED", "FIGURES_NEED_EDIT", "UNCERTAIN")
        for c in cards
    ):
        return True
    active = [c for c in cards if c.get("status") != "NOT_USED"]
    if not active:
        return False
    if any(not c.get("receipt_added") for c in active):
        disc = discover_unlinked_evidence_for_date(business_date, conn=conn)
        if disc.get("edc_receipts"):
            return True
    return False


def workflow_resume_step(
    close_id: str,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Return the next 6-step screen (1–6) for resume."""
    row = _vc.get_close(close_id, conn=conn)
    if not row:
        return {"step": 1, "screen": "choose_date"}
    printed = printed_shift_source(close_id, conn=conn)
    readiness = wizard_submit_readiness(close_id, conn=conn)
    missing = readiness.get("missing_steps") or []
    ack = get_workflow_ack(close_id, "esb_data_difference_ack", conn=conn)
    figures_yes = get_workflow_ack(close_id, "shift_figures_yes", conn=conn)
    shift_ev = list_shift_report_evidence(close_id, conn=conn)
    has_draft_photo = any(
        r.get("human_confirm_status") == "DRAFT" and r.get("image_object_ref")
        for r in (shift_ev.get("reports") or [])
    )
    if has_draft_photo and not printed.get("confirmed"):
        return {"step": 2, "screen": "shift_report"}
    if not printed.get("confirmed"):
        return {"step": 2, "screen": "shift_report"}
    if not figures_yes:
        return {"step": 2, "screen": "shift_report_figures"}
    discrepancy = source_discrepancy_between(
        warehouse_source_board(row), printed
    )
    if discrepancy.get("has_discrepancy") and not ack:
        return {"step": 2, "screen": "shift_report_esb_diff"}
    biz = str(row.get("business_date") or "")
    if _workflow_needs_bank_receipts(close_id, biz, conn=conn):
        return {"step": 3, "screen": "bank_receipts"}
    if any(m.startswith("bank_receipt_") for m in missing):
        return {"step": 3, "screen": "bank_receipts"}
    if "cash_counted" in missing or "cash_difference_ack" in missing:
        return {"step": 4, "screen": "count_cash"}
    if readiness.get("submit_enabled"):
        return {"step": 6, "screen": "submit"}
    if not missing or set(missing).issubset(
        {"source_discrepancy_ack", "cash_difference_ack", "protected_close"}
    ):
        return {"step": 5, "screen": "review"}
    return {"step": 5, "screen": "review"}


def wizard_review_board(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Step 5 review — one clean summary for staff."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        printed = printed_shift_source(close_id, conn=c)
        cash = wizard_cash_summary(close_id, conn=c)
        petty = wizard_petty_summary(str(row.get("business_date") or ""), conn=c)
        banks = wizard_bank_cards(close_id, conn=c)
        discrepancy = source_discrepancy_between(
            warehouse_source_board(row), printed
        )
        exc_ack = get_workflow_ack(close_id, "esb_data_difference", conn=c)
        cash_ack = get_workflow_ack(close_id, "cash_count_confirmed", conn=c)
        shift_ev = list_shift_report_evidence(close_id, conn=c)
        has_shift_photo = any(
            r.get("image_object_ref") for r in (shift_ev.get("reports") or [])
        )
        bank_checks: list[dict[str, Any]] = []
        for card in banks.get("cards") or []:
            if card.get("status") == "NOT_USED":
                continue
            bank_checks.append(
                {
                    "bank": card.get("bank"),
                    "status": "ok" if card.get("receipt_added") else "missing",
                    "expected_edc": card.get("expected_edc"),
                    "expected_qris": card.get("expected_qris"),
                    "actual_edc": card.get("actual_edc"),
                    "actual_qris": card.get("actual_qris"),
                    "difference_edc": card.get("difference_edc"),
                    "difference_qris": card.get("difference_qris"),
                }
            )
        exceptions: list[dict[str, Any]] = []
        if exc_ack:
            diff = exc_ack.get("difference") or {}
            exceptions.append(
                {
                    "kind": "esb_discrepancy",
                    "heading": "Historical ESB discrepancy",
                    "cash_rp": diff.get("cash_rp"),
                    "bills": diff.get("bills"),
                }
            )
        cash_diff = cash.get("difference")
        if cash_diff is not None and abs(float(cash_diff)) >= 0.01:
            exceptions.append(
                {
                    "kind": "cash_difference",
                    "heading": "Cash difference",
                    "cash_rp": cash_diff,
                    "why_note": (cash_ack or {}).get("why_note"),
                }
            )
        cash_diff_label = cash.get("difference_label")
        return {
            **HONESTY,
            "ok": True,
            "business_date": row.get("business_date"),
            "sales_rp": printed.get("gross_sales_rp"),
            "bills": printed.get("bills"),
            "pax": printed.get("pax"),
            "cash_expected": cash.get("expected_cash_in_till"),
            "cash_counted": cash.get("cash_counted"),
            "cash_difference": cash_diff_label,
            "opening_till_float": cash.get("opening_till_float"),
            "banks": bank_checks,
            "other_payment_scott_etik_rp": printed.get("scott_etik_rp"),
            "non_sales_exec_chef_rp": printed.get("non_sales_executive_chef_rp"),
            "petty_out": petty.get("petty_out_total"),
            "petty_in": petty.get("petty_in_total"),
            "evidence_checklist": {
                "shift_report": "ok" if printed.get("confirmed") else "missing",
                "shift_report_photo": "ok" if has_shift_photo else (
                    "owner_typed" if printed.get("image_status")
                    == "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER"
                    else "missing"
                ),
                "bni": next(
                    (
                        ("ok" if b.get("status") == "ok" else "missing")
                        for b in bank_checks
                        if b.get("bank") == "BNI"
                    ),
                    "n/a",
                ),
                "bri": next(
                    (
                        ("ok" if b.get("status") == "ok" else "missing")
                        for b in bank_checks
                        if b.get("bank") == "BRI"
                    ),
                    "n/a",
                ),
                "cash_photo": "optional",
            },
            "exceptions": exceptions,
        }
    finally:
        if own:
            c.close()



def phone_close_summary(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Captain-facing one-page totals — no recon jargon, no IDs."""
    own = conn is None
    c = conn or db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        printed = printed_shift_source(close_id, conn=c)
        warehouse = warehouse_source_board(row)
        banks = wizard_bank_cards(close_id, conn=c)
        cash = wizard_cash_summary(close_id, conn=c)
        petty = wizard_petty_summary(str(row.get("business_date") or ""), conn=c)
        # Sales / bills / pax / cash from confirmed printed; card/qris from banks or warehouse.
        sales = printed.get("gross_sales_rp")
        bills = printed.get("bills")
        pax = printed.get("pax")
        cash_amt = printed.get("cash_rp")
        live_tot = row.get("esb_totals") or {}
        # Prefer ESB snapshot Card/QRIS/Other for the shift strip; banks stay per-acquirer below.
        card = live_tot.get("card_from_payments")
        qris = live_tot.get("qris_from_payments")
        card_known = card is not None
        qris_known = qris is not None
        if not card_known or not qris_known:
            card_sum = 0.0
            qris_sum = 0.0
            saw_edc = False
            saw_qris = False
            for card_row in banks.get("cards") or []:
                if card_row.get("status") in ("UNCERTAIN", "FIGURES_NEED_EDIT"):
                    continue
                if card_row.get("expected_edc") is not None:
                    card_sum += float(card_row["expected_edc"])
                    saw_edc = True
                if card_row.get("expected_qris") is not None:
                    qris_sum += float(card_row["expected_qris"])
                    saw_qris = True
            if not card_known and saw_edc:
                card = card_sum
                card_known = True
            if not qris_known and saw_qris:
                qris = qris_sum
                qris_known = True
        other = None
        if live_tot.get("other_from_payments") is not None:
            other = float(live_tot["other_from_payments"])
        shift_ok = bool(printed.get("confirmed"))
        return {
            "ok": True,
            "business_date": row.get("business_date"),
            "state": row.get("state"),
            "shift_read": shift_ok,
            "sales": sales,
            "bills": bills,
            "pax": pax,
            "cash": cash_amt,
            "card": round(card, 2) if card_known else None,
            "qris": round(qris, 2) if qris_known else None,
            "other": other,
            "banks": banks,
            "cash_summary": cash,
            "petty": {
                "out": petty.get("petty_out_total"),
                "in": petty.get("petty_in_total"),
            },
            "image_attached": bool(printed.get("image_attached")),
        }
    finally:
        if own:
            c.close()


def source_wizard_state(
    close_id: str,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Phone-first wizard payload — warehouse and printed kept separate."""
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        ensure_owner_typed_printed_source(close_id, conn=c, commit=False)
        warehouse = warehouse_source_board(row)
        printed = printed_shift_source(close_id, conn=c)
        discrepancy = source_discrepancy_between(warehouse, printed)
        readiness = wizard_submit_readiness(
            close_id, verified_person_id=verified_person_id, conn=c
        )
        if own:
            c.commit()
        exc = ensure_esb_difference_exception(
            close_id,
            discrepancy,
            verified_person_id=verified_person_id,
            conn=c,
            commit=False,
        )
        resume = workflow_resume_step(close_id, conn=c)
        esb_ack = get_workflow_ack(close_id, "esb_data_difference_ack", conn=c)
        figures_yes = get_workflow_ack(close_id, "shift_figures_yes", conn=c)
        cash_ack = get_workflow_ack(close_id, "cash_count_confirmed", conn=c)
        biz = str(row.get("business_date") or "")
        discovered = discover_unlinked_evidence_for_date(biz, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "pack": SIX_STEP_PACK,
            "staff_ready": False,
            "human_commissioned": False,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "state": row.get("state"),
            "warehouse_source": warehouse,
            "printed_source": printed,
            "source_discrepancy": discrepancy,
            "esb_difference_exception": exc,
            "esb_difference_acked": bool(esb_ack),
            "shift_figures_yes": bool(figures_yes),
            "cash_why_note": (cash_ack or {}).get("why_note"),
            "discovered_evidence": discovered,
            "shift_report_evidence": list_shift_report_evidence(close_id, conn=c),
            "wizard_bank_cards": wizard_bank_cards(close_id, conn=c),
            "phone_close": phone_close_summary(close_id, conn=c),
            "wizard_cash": wizard_cash_summary(close_id, conn=c),
            "wizard_petty": wizard_petty_summary(
                str(row.get("business_date") or ""), conn=c
            ),
            "wizard_review": wizard_review_board(close_id, conn=c),
            "workflow_resume": resume,
            "submit_readiness": readiness,
            "dual_source_never_overwrite": True,
        }
    finally:
        if own:
            c.close()


def close_date_register(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    outlet_id: str | None = None,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Historical close calendar — no 7-day cap. Owner/Finance date search."""
    own = conn is None
    c = conn or db_connect()
    try:
        from datetime import date, timedelta

        oid = (outlet_id or OUTLET_UMA).strip()
        today = date.today().isoformat()
        df = (date_from or "").strip() or "2026-04-01"
        dt = (date_to or "").strip() or today
        search_s = (search or "").strip()
        if search_s:
            df = search_s
            dt = search_s
        from core import uma_hist_close_queue1 as _hist_q

        closes = _vc.list_closes(
            outlet_id=oid,
            date_from=df,
            date_to=dt,
            limit=500,
            conn=c,
        )
        by_date: dict[str, dict[str, Any]] = {}
        for cl in closes:
            bd = str(cl.get("business_date") or "")
            if not bd:
                continue
            entry = by_date.setdefault(
                bd,
                {"business_date": bd, "closes": []},
            )
            entry["closes"].append(cl)
        esb_dates: set[str] = set()
        try:
            esb_path = _esb.resolve_esb_path()
            esb_conn = sqlite3.connect(f"file:{esb_path}?mode=ro", uri=True)
            rows = esb_conn.execute(
                """
                SELECT DISTINCT biz_date FROM sales
                WHERE biz_date>=? AND biz_date<=?
                ORDER BY biz_date
                """,
                (df, dt),
            ).fetchall()
            esb_dates = {str(r[0]) for r in rows}
            esb_conn.close()
        except (_esb.EsbSnapshotError, sqlite3.Error, OSError):
            esb_dates = set()
        all_dates = sorted(set(by_date.keys()) | esb_dates)
        days: list[dict[str, Any]] = []
        for bd in all_dates:
            if bd < df or bd > dt:
                continue
            rec = by_date.get(bd)
            date_closes = (rec or {}).get("closes") or []
            if not date_closes:
                date_closes = _hist_q._closes_for_date(bd, conn=c)  # noqa: SLF001
            current = [
                x
                for x in date_closes
                if str(x.get("state") or "").upper() != "CANCELLED"
            ]
            primary = _hist_q._primary_close(date_closes)  # noqa: SLF001
            close_id = primary.get("close_id") if primary else None
            ev = _hist_q._evidence_counts(close_id, conn=c)  # noqa: SLF001
            status = _hist_q.canonical_ui_status(
                business_date=bd, closes=date_closes, evidence=ev
            )
            primary = _hist_q._primary_close(date_closes)  # noqa: SLF001
            prefix = _hist_q._close_prefix(  # noqa: SLF001
                primary.get("close_id") if primary else None
            )
            protected = prefix in _hist_q.PROTECTED_CLOSE_PREFIXES
            owner_can_complete = (
                protected
                and status in ("OPEN", "INCOMPLETE")
                and _hist_q.can_complete_protected_close(
                    verified_person_id, conn=c
                )
                and prefix in _hist_q.COMPLETABLE_PROTECTED_PREFIXES
            )
            variance = primary.get("variance_cash_amount") if primary else None
            days.append(
                {
                    "business_date": bd,
                    "status": status,
                    "close_id": close_id,
                    "selectable": True,
                    "action_label": _hist_q.row_action_label(
                        status,
                        protected=protected,
                        owner_can_complete=owner_can_complete,
                    ),
                    "summary_line": _hist_q.row_summary_line(
                        status,
                        protected=protected,
                        variance_cash_amount=variance,
                    ),
                }
            )
        return {
            **HONESTY,
            "ok": True,
            "date_from": df,
            "date_to": dt,
            "search": search_s or None,
            "days": days,
            "seven_day_limit_removed": True,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        if own:
            c.close()


_STAFF_AUDIT_PLAIN: dict[str, str] = {
    "venue_close.open": "Close opened for this date",
    "venue_close.esb_captured": "ESB sales saved for this date",
    "venue_close.declared_cash": "Cash in the till recorded",
    "venue_close.reconcile": "Close submitted",
    "venue_close.exception_opened": "Difference sent for manager review",
    "venue_close.exception_resolved": "Difference resolved",
    "venue_close.verify": "Close finished",
    "venue_close.edc_receipt_extract": "Bank receipt photo read (draft only)",
    "venue_close.edc_receipt_confirm": "Bank terminal totals confirmed",
    "venue_close.esb_receipt_extract": "Shift report photo read (draft only)",
    "venue_close.esb_receipt_confirm": "Shift report figures confirmed",
    "venue_close.cancel_unfinished": "Unfinished close set aside",
    "venue_close.takeover": "Close taken over by another closer",
    "venue_close.reassign": "Close reassigned",
}


def staff_plain_audit_trail(
    close_id: str,
    *,
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Plain-language close history for staff — no raw event names or person ids."""
    out: list[dict[str, Any]] = []
    try:
        trail = _vc.audit_trail(close_id, conn=conn)
    except sqlite3.Error:
        return []
    for row in trail:
        action = str(row.get("action") or "")
        if action.startswith("venue_close.owner_"):
            text = "Owner change recorded"
        elif action == "venue_close.owner_reopen":
            text = "Close reopened — original still stands"
        else:
            text = _STAFF_AUDIT_PLAIN.get(action) or ""
        if not text:
            continue
        when = str(row.get("occurred_at") or "")
        day = when[:10] if len(when) >= 10 else ""
        sentence = f"{day} · {text}" if day else text
        out.append({"when": when or None, "sentence": sentence})
    return out


def staff_reopen_notice(
    close_id: str,
    *,
    conn: sqlite3.Connection,
) -> str | None:
    """Plain reopen summary for staff — not stage or table names."""
    try:
        chain = _vc.reopen_chain(close_id, conn=conn)
    except Exception:  # noqa: BLE001
        return None
    if not chain.get("reopen_event"):
        return None
    changes = chain.get("changes") or []
    approval = chain.get("new_approval")
    bits = [
        "This close was reopened. The original completed close still stands on record."
    ]
    if changes:
        bits.append(f"{len(changes)} change(s) were made after reopen.")
    if not approval:
        bits.append("A new approval is required before this close can finish again.")
    return " ".join(bits)


def staff_close_surface(
    close_id: str,
    *,
    outlet_id: str | None = None,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Staff-visible context wired from existing close behaviour (surface only)."""
    oid = (outlet_id or OUTLET_UMA).strip()
    banks = list_outlet_banks(oid, conn=conn)
    cfg = str(banks.get("bank_config_status") or "NEEDS CONFIGURATION")
    bank_setup = "needs setup" if cfg == "NEEDS CONFIGURATION" else "ready"
    cid = (close_id or "").strip()
    return {
        "audit_history": staff_plain_audit_trail(cid, conn=conn) if cid else [],
        "reopen_notice": staff_reopen_notice(cid, conn=conn) if cid else None,
        "bank_setup": bank_setup,
        "blank_bank_is_not_zero": True,
        "three_sources_distinct": True,
    }


def enrich_close(close: dict[str, Any] | None, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    if not close:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        cid = close.get("close_id") or ""
        oid = (close.get("outlet_id") or OUTLET_UMA).strip()
        rt = receipt_totals(cid, conn=c) if cid else None
        esb_recs = list_esb_closing_receipts(cid, conn=c) if cid else []
        pending_esb = None
        if cid and not esb_recs:
            pending_esb = find_pending_esb_receipt_photo(cid, conn=c)
        three = _vc.three_close_objects(close, conn=c)
        return {
            **close,
            **HONESTY,
            "outlet_id": oid,
            "outlet_config": get_outlet_config(oid, conn=c),
            "edc_terminals": list_edc_terminals(oid, conn=c),
            "edc_lines": list_edc_lines(cid, conn=c) if cid else [],
            "card_total": edc_card_total(cid, conn=c) if cid else None,
            "edc_receipts": list_edc_receipts(cid, conn=c) if cid else [],
            "receipt_totals": rt,
            "bank_cards": bank_cards(cid, conn=c) if cid else None,
            "esb_closing_receipts": esb_recs,
            "pending_esb_photo": pending_esb,
            "recon_board": recon_board(cid, conn=c) if cid else None,
            "unused_terminals": (
                unused_configured_terminals(cid, oid, conn=c) if cid else None
            ),
            "three_objects": three,
            "cash_sources": cash_three_sources(cid, conn=c) if cid else None,
            "staff_cash": staff_cash_summary(cid, conn=c) if cid else None,
            "snapshot_frozen": bool(close.get("esb_fingerprint_sha256")),
            "honesty": {**(close.get("honesty") or {}), **HONESTY},
            "staff_surface": staff_close_surface(
                cid, outlet_id=oid, conn=c
            ),
            "governance": _vc.close_governance_info(close, conn=c),
        }
    finally:
        if own:
            c.close()
