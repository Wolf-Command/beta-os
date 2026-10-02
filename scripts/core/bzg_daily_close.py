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
from core import venue_close as _vc

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK = "BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1"
PACK_PRIOR = "BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1"
PACK_VISION = "BZG-DAILY-CLOSE-MULTI-EDC-VISION-1"
ENTITY = "ENT-BZG"
OUTLET_UMA = "BZG-UMA"

EVIDENCE_Z = "pos_z_report"
EVIDENCE_EDC = "edc_settlement_slip"
EVIDENCE_ESB_RECEIPT = "esb_closing_receipt"

CLOSE_RECEIPT_DIR = BETA_ROOT / "state" / "bzg-daily-close" / "receipts"
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
    if len(data) > 8_000_000:
        raise BzgDailyCloseError(
            "receipt too large", code="receipt_too_large", http_status=413
        )
    kind_n = (kind or "receipt").strip().lower()
    if kind_n not in ("esb", "edc", "receipt", "z", "till"):
        kind_n = "receipt"
    CLOSE_RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".png") or "png" in ctype:
        ext = ".png"
    elif name.endswith(".webp") or "webp" in ctype:
        ext = ".webp"
    elif name.endswith(".heic") or "heic" in ctype:
        ext = ".heic"
    eid = f"EVD-CLOSE-{kind_n.upper()}-{uuid.uuid4().hex[:12].upper()}"
    dest = CLOSE_RECEIPT_DIR / f"{eid}{ext}"
    dest.write_bytes(data)
    ch = hashlib.sha256(data).hexdigest()
    ref = f"{CLOSE_RECEIPT_SCHEME}{eid}{ext}"
    return {
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
        **HONESTY,
    }


def resolve_close_receipt_path(object_ref: str | None) -> Path | None:
    """Map close-receipt://… ref to on-disk path. Refuse path escape."""
    ref = (object_ref or "").strip()
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
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suf, "image/jpeg")
    return data, mime


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
    if not ref and not ch:
        raise BzgDailyCloseError(
            "till declare requires Z-report evidence object_ref or content_hash",
            code="missing_z_report_evidence",
        )

    own = conn is None
    c = conn or db_connect()
    try:
        ensure_schema(c)
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise BzgDailyCloseError("close not found", code="not_found", http_status=404)
        outlet_id = (row.get("outlet_id") or OUTLET_UMA).strip()
        assert_human_close_enabled(outlet_id, c)

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
        # Confirmed/edited count toward recon; drafts excluded from confirmed totals.
        confirmed = [
            r
            for r in receipts
            if r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
        ]
        total_edc = round(sum(float(r.get("edc_card_amount") or 0) for r in confirmed), 2)
        total_qris = round(sum(float(r.get("qris_amount") or 0) for r in confirmed), 2)
        return {
            "close_id": close_id,
            "receipt_count": len(receipts),
            "confirmed_receipt_count": len(confirmed),
            "draft_receipt_count": len(receipts) - len(confirmed),
            "TOTAL_EDC": total_edc,
            "TOTAL_QRIS": total_qris,
            "TOTAL_CARD_QRIS": round(total_edc + total_qris, 2),
            "qris_never_merged_into_card": True,
            "basis": "SUM_CONFIRMED_EDC_RECEIPTS",
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
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Vision draft for Add EDC Receipt. AI is NOT accounting truth."""
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
        )
        extracted = draft.get("extracted") or {}
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
            reason_code="vision_draft_not_truth",
            metadata={
                "vision_event_id": vid,
                "provider": draft.get("provider"),
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
            "image_object_ref": ref,
            "content_hash": ch,
            "ai_is_not_accounting_truth": True,
            "next": "Looks Correct / Edit — human confirm required",
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
    if not ref and not ch:
        raise BzgDailyCloseError(
            "EDC receipt requires image evidence object_ref or content_hash",
            code="missing_edc_evidence",
        )
    batch = (batch_ref or overrides.get("batch_ref") or "").strip() or None
    sdate = (
        settlement_batch_date or overrides.get("settlement_batch_date") or ""
    ).strip() or None
    tlabel = (terminal_label or overrides.get("terminal_label") or "").strip() or None
    tid = (terminal_config_id or overrides.get("terminal_config_id") or "").strip() or None

    own = conn is None
    c = conn or db_connect()
    try:
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
            reason_code="human_confirm_edc_receipt",
            metadata={
                "edc_receipt_id": rid,
                "evidence_id": evid["evidence_id"],
                "edc_card_amount": edc,
                "qris_amount": qris,
                "receipt_total": total,
                "human_confirm_status": status,
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
            "edc_card_amount": edc,
            "qris_amount": qris,
            "receipt_total": total,
            "duplicate_warn": dup["duplicate_warn"],
            "duplicate_warn_detail": dup,
            "edc_receipts": list_edc_receipts(close_id, conn=c),
            "receipt_totals": totals,
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
            "api_mismatch_preview": mismatch,
            "image_object_ref": ref,
            "content_hash": ch,
            "ai_is_not_accounting_truth": True,
            "next": "Looks Correct / Edit — human confirm required; API snapshot kept",
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
    if not ref and not ch:
        raise BzgDailyCloseError(
            "ESB closing receipt requires image evidence",
            code="missing_esb_receipt_evidence",
        )

    own = conn is None
    c = conn or db_connect()
    try:
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
        confirmed_obj = {
            "cash_amount": cash_f,
            "edc_card_amount": edc_f,
            "qris_amount": qris_f,
            "gross_amount": gross_f,
            "action": act,
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
            reason_code="human_confirm_esb_receipt",
            metadata={
                "esb_receipt_id": rid,
                "api_mismatch": mismatch["api_mismatch"],
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
            "api_mismatch": mismatch["api_mismatch"],
            "api_mismatch_detail": mismatch,
            "esb_api_totals_preserved": row.get("esb_totals"),
            "esb_closing_receipts": list_esb_closing_receipts(close_id, conn=c),
            "ai_is_not_accounting_truth": True,
        }
    finally:
        if own:
            c.close()


def _receipt_payments_map(confirmed_esb: list[dict[str, Any]]) -> dict[str, float]:
    """Bank-split map from confirmed closing receipt (confirmed_json.payments or fields)."""
    if not confirmed_esb:
        return {}
    latest = confirmed_esb[-1]
    conf = latest.get("confirmed") or latest.get("extracted") or {}
    pays = conf.get("payments") if isinstance(conf, dict) else None
    out: dict[str, float] = {}
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
    receipt_bills = conf.get("bills") if isinstance(conf, dict) else None
    receipt_cash = None
    if isinstance(conf, dict) and conf.get("cash_amount") is not None:
        receipt_cash = round(float(conf["cash_amount"]), 2)
    elif latest.get("cash_amount") is not None:
        receipt_cash = round(float(latest["cash_amount"]), 2)
    receipt_pax = conf.get("pax") if isinstance(conf, dict) else None

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
            "net_sales": conf.get("net_sales") if isinstance(conf, dict) else None,
            "service_charge": conf.get("service_charge") if isinstance(conf, dict) else None,
            "tax": conf.get("tax") if isinstance(conf, dict) else None,
            "gross_sales": conf.get("gross_sales") if isinstance(conf, dict) else None,
            "payments_by_bank_split": receipt_split,
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


def enrich_close(close: dict[str, Any] | None, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    if not close:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        cid = close.get("close_id") or ""
        oid = (close.get("outlet_id") or OUTLET_UMA).strip()
        rt = receipt_totals(cid, conn=c) if cid else None
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
            "esb_closing_receipts": list_esb_closing_receipts(cid, conn=c) if cid else [],
            "recon_board": recon_board(cid, conn=c) if cid else None,
            "unused_terminals": (
                unused_configured_terminals(cid, oid, conn=c) if cid else None
            ),
            "honesty": {**(close.get("honesty") or {}), **HONESTY},
        }
    finally:
        if own:
            c.close()
