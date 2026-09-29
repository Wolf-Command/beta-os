#!/usr/bin/env python3
"""ESB-TRUTH-1 — ESB warehouse truth board (PARTIAL_IN_BETA deepen).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack ESB-TRUTH-1
(armed 2026-09-30 after OWNER-NEEDS-YOU-1 PASS_VERIFIED).

Read-only warehouse status on Beta. Deepens INTG-TRUTH-1 PARTIAL_IN_BETA
honesty with table inventory + sales date-range facts. Never invents
settlement, P&L, or warehouse rows. Never writes ESB.
staff_ready=false · human_commissioned=false.
Preserves INTG-TRUTH-1 + BZG-VENUEPL-1.
Does not auto-chain BACKUP-HEALTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_venue_pnl as _bzg_vpl
from core import esb_close_snapshot as _esb
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "ESB-TRUTH-1"
SCHEMA_ID = "wolf.esb-truth-1.v1"
BOUND = "beta-esb-ro"
CAP_INTG = "INT-ESB"
CAP_BZG = "CAP-BZG ESB"
INTEGRATION_ID = "INT-ESB-WOLF"
WRITE_AUTHORITY = "NONE_EXPANDED"
WITA = timezone(timedelta(hours=8))

PAGE_PATHS = frozenset(
    {
        "/ops/esb-truth-1",
        "/ops/esb-truth-1/",
        "/esb-truth-1",
        "/esb-truth-1/",
        "/esb-truth-1.html",
        "/dashboards/esb-truth-1.html",
    }
)
API_PATH = "/api/ops/esb-truth-1"

PRESERVED_PACKS = ("INTG-TRUTH-1", "BZG-VENUEPL-1")

# Warehouse table inventory — counts are RO facts, not P&L.
_WAREHOUSE_TABLES = (
    "sales",
    "sales_menu_summary",
    "gl_journal",
    "goods_receipts",
    "material_usage",
    "members",
    "menu_categories",
    "menu_templates",
    "menus",
    "products",
    "promotions",
)


class EsbTruth1Error(ValueError):
    """Fail closed. Does not invent settlement, P&L, or ESB writes."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == API_PATH


def _venue_close_count() -> int | None:
    if not CATALOG_DB.is_file():
        return None
    try:
        uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            present = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='venue_daily_closes'"
            ).fetchone()
            if not present:
                return None
            n = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
            return int(n)
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None


def _table_inventory(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """RO table presence + row counts. Missing table → present=false, count=null."""
    out: list[dict[str, Any]] = []
    for name in _WAREHOUSE_TABLES:
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone()
            if not row:
                out.append(
                    {
                        "table": name,
                        "present": False,
                        "row_count": None,
                        "status": "ABSENT",
                    }
                )
                continue
            n = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
            out.append(
                {
                    "table": name,
                    "present": True,
                    "row_count": int(n),
                    "status": "PRESENT",
                }
            )
        except sqlite3.Error:
            out.append(
                {
                    "table": name,
                    "present": None,
                    "row_count": None,
                    "status": "UNKNOWN",
                }
            )
    return out


def _sales_date_facts(conn: sqlite3.Connection) -> dict[str, Any]:
    """Warehouse sales date-range facts only — not revenue / P&L / settlement."""
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales'"
        ).fetchone()
        if not row:
            return {
                "table_present": False,
                "row_count": None,
                "min_biz_date": None,
                "max_biz_date": None,
                "status": "ABSENT",
                "pnl": None,
                "settlement": None,
            }
        stats = conn.execute(
            "SELECT COUNT(*), MIN(biz_date), MAX(biz_date) FROM sales"
        ).fetchone()
        return {
            "table_present": True,
            "row_count": int(stats[0]) if stats and stats[0] is not None else 0,
            "min_biz_date": stats[1] if stats else None,
            "max_biz_date": stats[2] if stats else None,
            "status": "READ_OK",
            "pnl": None,
            "settlement": None,
            "note": (
                "Date-range + row_count are warehouse inventory facts. "
                "Not settlement. Not P&L. Not invented."
            ),
        }
    except sqlite3.Error:
        return {
            "table_present": None,
            "row_count": None,
            "min_biz_date": None,
            "max_biz_date": None,
            "status": "UNKNOWN",
            "pnl": None,
            "settlement": None,
        }


def probe_warehouse(*, esb_path: Path | str | None = None) -> dict[str, Any]:
    """Read-only warehouse probe. Never invents P&L or settlement."""
    from core import integration_health as ih

    health = ih._read_esb(esb_path)
    warehouse_status = health.get("status")
    evidence = health.get("evidence")
    closes = _venue_close_count()

    path_resolved: Path | None = None
    path_present = False
    path_error: str | None = None
    tables: list[dict[str, Any]] = []
    sales_facts: dict[str, Any] = {
        "table_present": None,
        "row_count": None,
        "min_biz_date": None,
        "max_biz_date": None,
        "status": "UNKNOWN",
        "pnl": None,
        "settlement": None,
    }

    try:
        path_resolved = _esb.resolve_esb_path(esb_path)
        path_present = path_resolved.is_file()
    except Exception as exc:  # noqa: BLE001
        path_error = type(exc).__name__

    if path_present and path_resolved is not None:
        try:
            conn = _esb._connect_ro(path_resolved)
            try:
                tables = _table_inventory(conn)
                sales_facts = _sales_date_facts(conn)
            finally:
                conn.close()
        except _esb.EsbSnapshotError as exc:
            path_error = exc.code
        except (OSError, sqlite3.Error) as exc:
            path_error = type(exc).__name__

    present_tables = [t for t in tables if t.get("present") is True]
    absent_tables = [t for t in tables if t.get("present") is False]

    return {
        "warehouse_status": warehouse_status,
        "evidence": evidence,
        "path_present": path_present,
        "path_basename": path_resolved.name if path_resolved else None,
        "path_error": path_error,
        "venue_daily_closes_count": closes,
        "tables": tables,
        "tables_present_count": len(present_tables),
        "tables_absent_count": len(absent_tables),
        "sales_facts": sales_facts,
        "settlement_api": "UNAVAILABLE",
        "settlement": None,
        "pnl": None,
        "pnl_invented": False,
        "settlement_invented": False,
        "last_success": None,
        "write": False,
        "esb_mutated": False,
        "branch_close_note": (
            "Uma Blu daily-close path uses branch BLZ only. "
            "This board does not invent multi-outlet settlement."
        ),
        "audit_status": "PARTIAL_IN_BETA",
        "probe_status": (
            "WAREHOUSE_READ_OK_PARTIAL"
            if warehouse_status == "READ_OK"
            else (
                "WAREHOUSE_ABSENT"
                if warehouse_status in ("NOT_CONFIGURED", "UNKNOWN")
                else f"WAREHOUSE_{warehouse_status}"
            )
        ),
    }


def intg_truth1_preserved() -> dict[str, Any]:
    """INTG-TRUTH-1 ESB row stays PARTIAL_IN_BETA; pnl_invented false."""
    board = _intg.build_board(persist_audit=False)
    esb = next(
        (
            c
            for c in (board.get("connectors") or [])
            if c.get("integration_id") == INTEGRATION_ID
        ),
        None,
    )
    ok = (
        board.get("ok") is True
        and board.get("staff_ready") is False
        and board.get("human_commissioned") is False
        and esb is not None
        and esb.get("audit_status") == "PARTIAL_IN_BETA"
        and (esb.get("probe_facts") or {}).get("pnl_invented") is False
        and esb.get("last_success") is None
    )
    return {
        "ok": ok,
        "pack": "INTG-TRUTH-1",
        "integration_id": INTEGRATION_ID,
        "audit_status": (esb or {}).get("audit_status"),
        "probe_status": (esb or {}).get("probe_status"),
        "pnl_invented": (esb or {}).get("probe_facts", {}).get("pnl_invented"),
        "last_success": (esb or {}).get("last_success"),
        "href": "/ops/integrations-status",
        "why": (
            "INTG-TRUTH-1 preserved: INT-ESB-WOLF PARTIAL_IN_BETA; "
            "pnl_invented=false; last_success null."
            if ok
            else "INTG-TRUTH-1 ESB honesty check failed."
        ),
    }


def bzg_venuepl1_preserved() -> dict[str, Any]:
    """BZG-VENUEPL-1 skeleton + honesty pins preserved (no invent P&L)."""
    flags = _bzg_vpl.honesty_flags()
    page_ok = "/bzg/venue-pnl" in getattr(_bzg_vpl, "PAGE_PATHS", ())
    html = BETA_ROOT / "dashboards" / "bzg-venue-pnl.html"
    ok = (
        page_ok
        and html.is_file()
        and flags.get("invented_revenue") is False
        and flags.get("invented_cost") is False
        and flags.get("invented_contribution") is False
        and flags.get("invented_rollup") is False
        and flags.get("live_pnl") is False
        and flags.get("payment_executed") is False
        and flags.get("books_write") is False
        and _bzg_vpl.PACK == "BZG-VENUEPL-1"
    )
    return {
        "ok": ok,
        "pack": "BZG-VENUEPL-1",
        "cap_id": _bzg_vpl.CAP_ID,
        "live_pnl": flags.get("live_pnl"),
        "invented_revenue": flags.get("invented_revenue"),
        "invented_cost": flags.get("invented_cost"),
        "href": "/bzg/venue-pnl",
        "why": (
            "BZG-VENUEPL-1 preserved: no invented revenue/cost/contribution; "
            "live_pnl=false; books_write=false."
            if ok
            else "BZG-VENUEPL-1 honesty check failed."
        ),
    }


def _honesty_tiles(wh: dict[str, Any], intg: dict[str, Any], vpl: dict[str, Any]) -> list[dict[str, Any]]:
    closes = wh.get("venue_daily_closes_count")
    closes_label = "UNKNOWN" if closes is None else str(closes)
    sales = wh.get("sales_facts") or {}
    return [
        {
            "id": "audit_status",
            "label": "Audit status",
            "status": "PARTIAL_IN_BETA",
            "value": "PARTIAL_IN_BETA",
            "why": "Warehouse RO facts only. Not a full ESB connector prove.",
        },
        {
            "id": "warehouse",
            "label": "Warehouse RO",
            "status": str(wh.get("warehouse_status") or "UNKNOWN"),
            "value": wh.get("warehouse_status"),
            "why": wh.get("evidence") or "Warehouse probe evidence missing.",
        },
        {
            "id": "settlement_api",
            "label": "Settlement API",
            "status": "UNAVAILABLE",
            "value": None,
            "why": "settlement_api UNAVAILABLE. Settlement not invented.",
        },
        {
            "id": "pnl",
            "label": "P&L / contribution",
            "status": "UNKNOWN",
            "value": None,
            "why": "P&L not invented from warehouse. UNKNOWN ≠ zero success.",
        },
        {
            "id": "venue_closes",
            "label": "venue_daily_closes",
            "status": "EMPTY" if closes == 0 else ("UNKNOWN" if closes is None else "FACT"),
            "value": closes,
            "why": f"venue_daily_closes={closes_label}. Not invented.",
        },
        {
            "id": "sales_range",
            "label": "Sales date range",
            "status": str(sales.get("status") or "UNKNOWN"),
            "value": (
                f"{sales.get('min_biz_date')} → {sales.get('max_biz_date')}"
                if sales.get("min_biz_date") and sales.get("max_biz_date")
                else None
            ),
            "why": (
                f"sales rows={sales.get('row_count')}. Inventory fact only — not settlement."
            ),
        },
        {
            "id": "last_success",
            "label": "last_success",
            "status": "NULL",
            "value": None,
            "why": "Warehouse ≠ connector success. last_success stays null.",
        },
        {
            "id": "intg_truth1",
            "label": "INTG-TRUTH-1",
            "status": "PRESERVED" if intg.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": intg.get("why"),
        },
        {
            "id": "bzg_venuepl1",
            "label": "BZG-VENUEPL-1",
            "status": "PRESERVED" if vpl.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": vpl.get("why"),
        },
        {
            "id": "write_authority",
            "label": "Write authority",
            "status": WRITE_AUTHORITY,
            "value": WRITE_AUTHORITY,
            "why": "ESB writes refused. Write authority not expanded.",
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "intg_truth",
            "label": "Integrations honesty board",
            "href": "/ops/integrations-status",
            "kind": "existing",
            "note": "INTG-TRUTH-1 — INT-ESB-WOLF PARTIAL_IN_BETA.",
        },
        {
            "id": "bzg_venue_pnl",
            "label": "BZG venue P&L",
            "href": "/bzg/venue-pnl",
            "kind": "existing",
            "note": "BZG-VENUEPL-1 — no invented revenue/cost.",
        },
        {
            "id": "bzg_ops_desk",
            "label": "BZG ops desk",
            "href": "/bzg/ops-desk",
            "kind": "existing",
            "note": "Ops desk; venue_daily_closes may be 0.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    intg = intg_truth1_preserved()
    vpl = bzg_venuepl1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "integration_id": INTEGRATION_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "esb_write": False,
        "esb_mutated": False,
        "write_authority_expanded": False,
        "write_authority": WRITE_AUTHORITY,
        "secrets_exposed": False,
        "pnl_invented": False,
        "settlement_invented": False,
        "fake_settlement": False,
        "invented_warehouse_rows": False,
        "invented_last_success": False,
        "settlement_api": "UNAVAILABLE",
        "audit_status": "PARTIAL_IN_BETA",
        "partial_in_beta": True,
        "anon_fail_closed": True,
        "owner_read": True,
        "intg_truth1_preserved": intg.get("ok") is True,
        "bzg_venuepl1_preserved": vpl.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "BACKUP-HEALTH-1",
    }


def refuse_esb_write(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "ESB writes are refused. Warehouse board is read-only.",
        code="esb_write_refused",
    )


def refuse_settlement(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "Fake settlement is refused. settlement_api UNAVAILABLE.",
        code="settlement_refused",
    )


def refuse_pnl(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "P&L is UNKNOWN. Not invented from warehouse facts.",
        code="pnl_refused",
    )


def refuse_last_success(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "last_success is not invented. Warehouse ≠ connector success.",
        code="last_success_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "PROVEN is refused. PARTIAL_IN_BETA warehouse facts are not a full prove.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise EsbTruth1Error(
        "READY is refused. A PARTIAL_IN_BETA warehouse board is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise EsbTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "esb",
            "esb-write",
            "esb-mutate",
            "warehouse-write",
            "write",
            "mutate",
            "insert",
            "update",
            "delete",
        }:
            refuse_esb_write(payload)
        if token in {
            "settlement",
            "settle",
            "settlement-api",
            "fake-settlement",
            "clearing",
        }:
            refuse_settlement(payload)
        if token in {"pnl", "p-and-l", "profit", "contribution", "revenue", "cost"}:
            refuse_pnl(payload)
        if token in {"last-success", "last_success", "success"}:
            refuse_last_success(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise EsbTruth1Error(
        "External writes are refused. ESB truth board is read-only.",
        code="write_refused",
    )


def build_slice(*, esb_path: Path | str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    wh = probe_warehouse(esb_path=esb_path)
    intg = intg_truth1_preserved()
    vpl = bzg_venuepl1_preserved()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_INTG, CAP_BZG],
        "integration_id": INTEGRATION_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "esb_write": False,
        "esb_mutated": False,
        "write_authority": WRITE_AUTHORITY,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "audit_status": "PARTIAL_IN_BETA",
        "probe_status": wh.get("probe_status"),
        "warehouse_status": wh.get("warehouse_status"),
        "warehouse": wh,
        "settlement_api": "UNAVAILABLE",
        "settlement": None,
        "pnl": None,
        "pnl_invented": False,
        "settlement_invented": False,
        "fake_settlement": False,
        "invented_warehouse_rows": False,
        "last_success": None,
        "venue_daily_closes_count": wh.get("venue_daily_closes_count"),
        "intg_truth1_preserved": intg.get("ok") is True,
        "bzg_venuepl1_preserved": vpl.get("ok") is True,
        "intg_truth1": intg,
        "bzg_venuepl1": vpl,
        "honesty_tiles": _honesty_tiles(wh, intg, vpl),
        "desk_links": _desk_links(),
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "full_esb_connector_prove",
            "settlement_api",
            "pnl",
            "last_success",
            "esb_write",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "BACKUP-HEALTH-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "audit_status": "PARTIAL_IN_BETA",
        "settlement_api": "UNAVAILABLE",
        "pnl_property": False,
        "settlement_property": False,
        "last_success_property": False,
        "writes_accepted": False,
        "esb_write": False,
        "extends": [
            "scripts/core/intg_truth_board.py",
            "scripts/core/esb_close_snapshot.py",
            "scripts/core/bzg_venue_pnl.py",
        ],
        "preserved": list(PRESERVED_PACKS),
        "why": (
            "ESB warehouse truth board. PARTIAL_IN_BETA deepen. "
            "Warehouse RO facts only. No fake settlement. No ESB write."
        ),
    }
