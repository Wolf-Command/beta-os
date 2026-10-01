#!/usr/bin/env python3
"""Atrium sales desk — READ-ONLY over the V1 atrium_sales.sqlite.

Fourteen views from wolf-system/scripts/dash_data.py (same ladder, tax
ceiling, and construction-plan rule). The sqlite is opened mode=ro.
No new sale is posted. Occupancy is vacant-versus-rooms; in-house stays
UNKNOWN. Kuta tonight is the same RO loader as the rates leaf. LEARN only.
staff_ready stays false.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

WS = Path.home() / ".openclaw/workspace/wolf-system"
DEFAULT_DB = WS / "atrium" / "atrium_sales.sqlite"
DASH_DATA = WS / "scripts" / "dash_data.py"
MASTER_STATUS = WS / "dashboards" / "data" / "master.status.json"
DB_PATH = Path(os.environ.get("ATRIUM_SALES_DB", str(DEFAULT_DB)))

VIEWS: list[tuple[str, str, str]] = [
    ("overview", "Money", "Overview"),
    ("milestones", "Money", "Milestones"),
    ("payments", "Money", "Payments"),
    ("newsale", "Sales", "New sale"),
    ("inventory", "Sales", "Inventory"),
    ("deals", "Sales", "Deal types"),
    ("leads", "Sales", "Leads"),
    ("comms", "Sales", "Commissions"),
    ("cv", "Cash", "CV Cash"),
    ("payables", "Cash", "CV Payables"),
    ("tax", "Cash", "Tax Ceiling"),
    ("vendors", "Cash", "Vendors"),
    ("commonarea", "Ref", "Common Area"),
    ("exceptions", "Ref", "Exceptions"),
]
VIEW_IDS = {v[0] for v in VIEWS}

_CACHE: dict[str, Any] = {"key": None, "data": None}
_DASH_MOD: Any = None


def _now_key(path: Path) -> tuple[str, int, int]:
    st = path.stat()
    return (str(path), st.st_mtime_ns, st.st_size)


def _load_dash():
    global _DASH_MOD
    if _DASH_MOD is None:
        spec = importlib.util.spec_from_file_location("v1_dash_data_ro", DASH_DATA)
        if spec is None or spec.loader is None:
            raise FileNotFoundError(f"dash_data missing: {DASH_DATA}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _DASH_MOD = mod
    return _DASH_MOD


def _ro_connect(orig):
    def connect(db, *args, **kwargs):
        if kwargs.get("uri") or (isinstance(db, str) and str(db).startswith("file:")):
            conn = orig(db, *args, **kwargs)
        else:
            conn = orig(f"file:{db}?mode=ro", uri=True, timeout=8)
        conn.execute("PRAGMA query_only = ON")
        return conn

    return connect


def _table_counts(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    try:
        conn.execute("PRAGMA query_only = ON")
        out: dict[str, int] = {}
        for table in (
            "units", "leads", "payments", "commissions", "exceptions", "common_area",
            "vendors", "cv_transactions", "cv_invoices",
        ):
            out[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        out["exceptions_unresolved"] = int(
            conn.execute("SELECT COUNT(*) FROM exceptions WHERE resolved=0").fetchone()[0]
        )
        return out
    finally:
        conn.close()


def _built(path: Path) -> dict[str, Any]:
    key = _now_key(path)
    if _CACHE["key"] == key and isinstance(_CACHE["data"], dict):
        return _CACHE["data"]
    mod = _load_dash()
    orig = mod.sqlite3.connect
    mod.sqlite3.connect = _ro_connect(orig)
    try:
        data = mod.build(str(path))
    finally:
        mod.sqlite3.connect = orig
    _CACHE["key"] = key
    _CACHE["data"] = data
    return data


def _page(rows: list[dict[str, Any]], limit: int, offset: int) -> tuple[list[dict[str, Any]], int, int]:
    limit = max(1, min(int(limit or 40), 80))
    offset = max(0, int(offset or 0))
    return rows[offset:offset + limit], limit, offset


def _slim_unit(u: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": u.get("unit_id"),
        "floor": u.get("floor"),
        "type": u.get("type"),
        "sqm": u.get("sqm"),
        "status": u.get("status"),
        "owner": u.get("owner"),
        "contract_price_idr": u.get("contract_price_idr"),
        "deal_structure": u.get("deal_structure"),
        "deal_label": u.get("deal_label"),
        "stage": u.get("stage"),
        "stage_code": u.get("stage_code"),
        "paid_idr": u.get("paid_idr"),
        "balance_idr": u.get("balance_idr"),
        "pct_paid": u.get("pct_paid"),
        "n_payments": u.get("n_payments"),
        "sold_date": u.get("sold_date"),
        "cv_applicable": u.get("cv_applicable"),
    }


def _lead_row(lead: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lead.get("id"),
        "date": lead.get("date"),
        "name": lead.get("name"),
        "source": lead.get("source"),
        "stage": lead.get("stage"),
        "status": lead.get("status"),
        "unit_interest": lead.get("unit_interest"),
        "assigned_agent": lead.get("assigned_agent"),
        "country": lead.get("country"),
        "budget_idr": lead.get("budget_idr"),
        "qualification": lead.get("qualification"),
    }


def _payments(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit in data.get("units") or []:
        for pay in unit.get("payments") or []:
            rows.append({
                "id": pay.get("id"),
                "unit_id": unit.get("unit_id"),
                "paid_date": pay.get("d"),
                "amount_idr": pay.get("a"),
                "milestone": pay.get("m"),
                "payee": pay.get("payee"),
                "cv": pay.get("cv"),
            })
    rows.sort(key=lambda r: (r.get("paid_date") or "", r.get("id") or 0), reverse=True)
    return rows


def _find(rows: list[dict[str, Any]], detail_id: str | None, *keys: str) -> dict[str, Any] | None:
    if not detail_id:
        return None
    want = str(detail_id)
    for row in rows:
        for key in keys:
            if str(row.get(key)) == want:
                return row
    return None


def _v1_master_atrium() -> dict[str, Any]:
    if not MASTER_STATUS.is_file():
        return {"status": "MISSING", "path": str(MASTER_STATUS), "val": None}
    try:
        payload = json.loads(MASTER_STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "READ_ERROR", "path": str(MASTER_STATUS), "error": str(exc), "val": None}
    tiles = payload.get("tiles") if isinstance(payload, dict) else None
    if not isinstance(tiles, list):
        tiles = payload.get("cards") if isinstance(payload, dict) else None
    found = None
    if isinstance(tiles, list):
        for tile in tiles:
            if isinstance(tile, dict) and tile.get("key") == "atrium":
                found = tile
                break
    if found is None and isinstance(payload, dict):
        # master.status.json uses a list under one of several keys; scan values.
        for value in payload.values():
            if not isinstance(value, list):
                continue
            for tile in value:
                if isinstance(tile, dict) and tile.get("key") == "atrium":
                    found = tile
                    break
    if not isinstance(found, dict):
        return {
            "status": "ABSENT",
            "path": str(MASTER_STATUS),
            "val": None,
            "question": "different_from_yanolja_vacant_vs_rooms",
        }
    return {
        "status": "PRESENT",
        "path": str(MASTER_STATUS),
        "key": "atrium",
        "val": found.get("val"),
        "lab": found.get("lab"),
        "href": found.get("href"),
        "question": "different_from_yanolja_vacant_vs_rooms",
        "not_merged": True,
    }


def _occupancy() -> dict[str, Any]:
    tile: dict[str, Any] = {}
    err = None
    try:
        from core.owner_pulse_ro import _occ_tile

        loaded = _occ_tile()
        if isinstance(loaded, dict):
            tile = loaded
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
    return {
        "question": "vacant_versus_rooms",
        "in_house": "UNKNOWN",
        "arrivals": "UNKNOWN",
        "guests": None,
        "adr": None,
        "revpar": None,
        "merged_pct": None,
        "yanolja": {
            "state": tile.get("state"),
            "value": tile.get("value"),
            "occupancy_pct": tile.get("occupancy_pct"),
            "rooms_total": tile.get("rooms_total"),
            "rooms_vacant": tile.get("rooms_vacant"),
            "guests": None,
            "freshness": tile.get("freshness"),
            "source": tile.get("source"),
            "why": tile.get("why"),
        },
        "v1_master_tile": _v1_master_atrium(),
        "loader_error": err,
        "href": "/amg/sales-desk#occ",
        "honesty": (
            "Yanolja vacant-versus-rooms and the V1 master tile are different "
            "questions. They are not averaged. In-house and arrivals stay UNKNOWN."
        ),
    }


def _kuta_panel() -> dict[str, Any]:
    try:
        from core.ops_kuta_rates_ro import load_kuta_rates_ro

        payload = load_kuta_rates_ro()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "learn_only": True,
            "booking": False,
            "error": f"{type(exc).__name__}: {exc}",
            "href": "/amg/sales-desk#kuta",
            "href_leaf": "/kuta-rates",
        }
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    official = [row for row in (status.get("official") or []) if isinstance(row, dict)]
    return {
        "ok": bool(payload.get("ok")),
        "learn_only": True,
        "booking": False,
        "spend": False,
        "adr_invented": False,
        "revpar_invented": False,
        "night": status.get("night"),
        "headline": status.get("headline"),
        "generated_at": status.get("generated_at"),
        "counts": status.get("counts"),
        "official_total": len(official),
        "official_shown": official[:12],
        "reason": payload.get("reason"),
        "source": "ops_kuta_rates_ro",
        "href": "/amg/sales-desk#kuta",
        "href_leaf": "/kuta-rates",
        "honesty": "LEARN only. Nobody books. No ADR or RevPAR is invented.",
    }


def _rows_for(view: str, data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    units = list(data.get("units") or [])
    extra: dict[str, Any] = {}
    if view == "overview":
        kpi = data.get("kpi") or {}
        keys = (
            "contract_lines", "sold_lines", "available", "physical_units",
            "list_value", "booked", "collected", "outstanding", "owed_cash",
            "owed_other", "pct_collected", "exceptions", "exceptions_action",
            "cv_net", "cv_payable", "vendor_outstanding",
        )
        rows = [{"k": key, "v": kpi.get(key)} for key in keys]
        extra["generated"] = data.get("generated")
        extra["tax_ceiling"] = data.get("tax_ceiling")
        return rows, extra
    if view == "milestones":
        rows = []
        for row in data.get("ladder_totals") or []:
            rows.append({
                "code": row.get("code"),
                "label": row.get("label"),
                "payee": row.get("payee"),
                "pct": row.get("pct"),
                "due": row.get("due"),
                "applied": row.get("applied"),
                "outstanding": row.get("outstanding"),
                "units_open": row.get("units_open"),
            })
        extra["source"] = "dash_data.LADDER"
        return rows, extra
    if view == "payments":
        return _payments(data), {"source": "payments table via dash_data.build"}
    if view == "newsale":
        available = [_slim_unit(u) for u in units if (u.get("status") or "") == "Available"]
        sold = [_slim_unit(u) for u in units if (u.get("status") or "").lower() == "sold"]
        sold.sort(key=lambda u: (u.get("sold_date") or "", u.get("unit_id") or ""), reverse=True)
        extra = {
            "writes_enabled": False,
            "post": "refused",
            "available_total": len(available),
            "latest_sold": sold[:8],
            "fields_a_sale_records": [
                "unit", "type", "floor", "size", "deal type", "introducer",
                "contract price", "buyer",
            ],
            "honesty": "Read desk. Recording a sale stays off. No row is invented.",
        }
        return available, extra
    if view == "inventory":
        return [_slim_unit(u) for u in units], {"source": "units"}
    if view == "deals":
        return list(data.get("deal_rollup") or []), {"source": "dash_data.DEAL_LABELS"}
    if view == "leads":
        rows = [_lead_row(lead) for lead in (data.get("leads") or [])]
        extra = {
            "pipeline": data.get("pipeline") or [],
            "summary": {
                "total": (data.get("lead_summary") or {}).get("total"),
                "won": (data.get("lead_summary") or {}).get("won"),
                "open": (data.get("lead_summary") or {}).get("open"),
            },
            "contact_fields": "email, phone, and notes stay in the sqlite and are not on this wire",
        }
        return rows, extra
    if view == "comms":
        rows = []
        for row in data.get("commissions") or []:
            rows.append({
                "id": row.get("id"),
                "unit_id": row.get("unit_id"),
                "client": row.get("client"),
                "introducer": row.get("introducer"),
                "price_idr": row.get("price_idr"),
                "total_rec": row.get("total_rec"),
                "unpaid": row.get("unpaid"),
            })
        return rows, {"by_party": data.get("comm_by_party") or []}
    if view == "cv":
        rows = []
        for row in data.get("cvs") or []:
            gov = row.get("governing") or {}
            rows.append({
                "cv": row.get("cv"),
                "n": row.get("n"),
                "credit": row.get("credit"),
                "debit": row.get("debit"),
                "net": row.get("net"),
                "payable": row.get("payable"),
                "revenue": gov.get("revenue"),
                "pct": gov.get("pct"),
                "headroom": gov.get("headroom"),
                "tier": gov.get("tier"),
                "basis": gov.get("basis"),
            })
        extra = {"txn_count": len(data.get("txns") or []), "recon": data.get("cv_recon")}
        return rows, extra
    if view == "payables":
        rows = []
        for row in data.get("payables") or []:
            rows.append({
                "id": row.get("id"),
                "cv": row.get("cv"),
                "vendor": row.get("vendor"),
                "invoice_ref": row.get("invoice_ref"),
                "due_date": row.get("due_date"),
                "amount_idr": row.get("amount_idr"),
                "paid_idr": row.get("paid_idr"),
                "status": row.get("status"),
            })
        return rows, {}
    if view == "tax":
        extra = {
            "tax_ceiling": data.get("tax_ceiling"),
            "ceiling_source": "wolf-system/scripts/dash_data.py TAX_CEILING",
            "basis": (data.get("tax_window") or {}).get("basis"),
        }
        return list(data.get("tax_rows") or []), extra
    if view == "vendors":
        rows = []
        for row in data.get("vendors") or []:
            rows.append({
                "id": row.get("id"),
                "vendor": row.get("vendor"),
                "n_invoices": row.get("n_invoices"),
                "n_payments": row.get("n_payments"),
                "invoiced_idr": row.get("invoiced_idr"),
                "paid_idr": row.get("paid_idr"),
                "balance_idr": row.get("balance_idr"),
                "preferred_cv": row.get("preferred_cv"),
            })
        extra = {"bank_account": "not on this wire"}
        return rows, extra
    if view == "commonarea":
        rows = []
        for row in data.get("common_area") or []:
            rows.append({
                "unit_id": row.get("unit_id"),
                "category": row.get("category"),
                "floor": row.get("floor"),
                "sqm": row.get("sqm"),
                "fee_idr": row.get("fee_idr"),
                "fee_usd": row.get("fee_usd"),
            })
        return rows, {}
    if view == "exceptions":
        rows = []
        for row in data.get("exceptions") or []:
            detail = row.get("detail") or ""
            if isinstance(detail, str) and len(detail) > 240:
                detail = detail[:240] + "…"
            rows.append({
                "id": row.get("id"),
                "severity": row.get("severity"),
                "entity": row.get("entity"),
                "entity_id": row.get("entity_id"),
                "code": row.get("code"),
                "detail": detail,
                "resolved": row.get("resolved"),
            })
        extra = {
            "filter": "resolved=0",
            "honesty": "Total is unresolved exceptions. The table also holds resolved rows; those are not this view.",
        }
        return rows, extra
    return [], {}


def _stamp(**extra: Any) -> dict[str, Any]:
    out = {
        "ok": True,
        "staff_ready": False,
        "human_commissioned": False,
        "writes": False,
        "read_only": True,
        "housekeeping": False,
        "guest_stay": False,
        "surface": "amg_sales_desk",
        "next": "PACK-04 content tick to draft. Not started. Metricool WRITE stays off.",
    }
    out.update(extra)
    return out


def load_sales_desk(
    view: str | None = None,
    limit: int = 40,
    offset: int = 0,
    detail_id: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    path = Path(db_path) if db_path else DB_PATH
    if not path.is_file():
        return _stamp(ok=False, error="sales_db_missing", path=str(path))
    if view and view not in VIEW_IDS:
        return _stamp(ok=False, error="unknown_view", view=view, views=sorted(VIEW_IDS))
    try:
        data = _built(path)
        counts = _table_counts(path)
    except Exception as exc:  # noqa: BLE001
        return _stamp(ok=False, error="sales_ro_fail", detail=f"{type(exc).__name__}: {exc}")
    totals: dict[str, int] = {}
    for vid, _group, _title in VIEWS:
        rows, _extra = _rows_for(vid, data)
        totals[vid] = len(rows)
    base = _stamp(
        source={
            "db": str(path),
            "open_mode": "ro",
            "formula": "wolf-system/scripts/dash_data.py",
            "tax_ceiling": data.get("tax_ceiling"),
            "ceiling_source": "dash_data.TAX_CEILING",
        },
        counts={
            "units": counts["units"],
            "leads": counts["leads"],
            "payments": counts["payments"],
            "exceptions_unresolved": counts["exceptions_unresolved"],
            "exceptions_table": counts["exceptions"],
            "common_area": counts["common_area"],
            "vendors": counts["vendors"],
            "cv_transactions": counts["cv_transactions"],
            "cv_invoices": counts["cv_invoices"],
            "commissions": counts["commissions"],
        },
        view_totals=totals,
        occupancy=_occupancy(),
        kuta=_kuta_panel(),
    )
    if counts["units"] != len(data.get("units") or []):
        base["ok"] = False
        base["error"] = "unit_count_mismatch"
    if counts["leads"] != len(data.get("leads") or []):
        base["ok"] = False
        base["error"] = "lead_count_mismatch"
    if counts["payments"] != totals["payments"]:
        base["ok"] = False
        base["error"] = "payment_count_mismatch"
    if not view:
        base["views"] = [
            {"id": vid, "group": group, "title": title, "total": totals[vid]}
            for vid, group, title in VIEWS
        ]
        return base
    rows, extra = _rows_for(view, data)
    shown, limit, offset = _page(rows, limit, offset)
    title = next(title for vid, _g, title in VIEWS if vid == view)
    group = next(group for vid, group, _t in VIEWS if vid == view)
    detail = _find(rows, detail_id, "id", "unit_id", "cv", "code", "k")
    base.update({
        "view": view,
        "title": title,
        "group": group,
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "rows": shown,
        "detail": detail,
        "detail_found": bool(detail_id) and detail is not None,
    })
    base.update(extra)
    return base


def refuse_write() -> dict[str, Any]:
    return _stamp(ok=False, error="writes_off", post="refused")
