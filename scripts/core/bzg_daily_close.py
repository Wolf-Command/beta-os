#!/usr/bin/env python3
"""BZG Daily Close Till+EDC — one reusable engine over venue_close.

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner order
BZG-DAILY-CLOSE-TILL-EDC-20261002.

Not a second close product. Outlet config from registry. Only Uma Blu
human_close_enabled. EDC terminals unknown → NEEDS CONFIGURATION.
ESB payment totals ≠ EDC settlement evidence. Settlement API UNAVAILABLE.
No invented variance tolerance. No if-Devi.
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import bzg_outlet_registry as _outlets
from core import evidence as _evidence
from core import venue_close as _vc

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK = "BZG-DAILY-CLOSE-TILL-EDC-1"
ENTITY = "ENT-BZG"
OUTLET_UMA = "BZG-UMA"

EVIDENCE_Z = "pos_z_report"
EVIDENCE_EDC = "edc_settlement_slip"

HONESTY = {
    **_vc.HONESTY,
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "settlement_api": "UNAVAILABLE",
    "settlement_status": "PENDING_BANK",
    "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
    "esb_payments_are_not_edc_settlement": True,
    "declared_cash_is_not_verified": True,
    "invented_tolerance": False,
    "invented_edc_terminals": False,
    "alchemist_soft_gap_not_policy": True,
    "engine": "venue_close",
}


class BzgDailyCloseError(_vc.VenueCloseError):
    pass


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    return _vc.db_connect(db_path)


def ensure_schema(conn: sqlite3.Connection) -> None:
    sql = (
        BETA_ROOT
        / "scripts"
        / "migrations"
        / "031_bzg_daily_close_till_edc.sql"
    ).read_text(encoding="utf-8")
    conn.executescript(sql)


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
                "only Uma Blu human-activated. EDC terminals NEEDS CONFIGURATION until "
                "Owner provides inventory. Settlement API UNAVAILABLE."
            ),
            "person_id": (person_id or "").strip() or None,
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
        return {
            **close,
            **HONESTY,
            "outlet_id": oid,
            "outlet_config": get_outlet_config(oid, conn=c),
            "edc_terminals": list_edc_terminals(oid, conn=c),
            "edc_lines": list_edc_lines(cid, conn=c) if cid else [],
            "card_total": edc_card_total(cid, conn=c) if cid else None,
            "honesty": {**(close.get("honesty") or {}), **HONESTY},
        }
    finally:
        if own:
            c.close()
