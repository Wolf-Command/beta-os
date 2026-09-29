#!/usr/bin/env python3
"""BZG-INVENTORY-TRUTH-1 — BZG inventory count honesty (no fake stock).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-INVENTORY-TRUTH-1
(armed 2026-09-30 after FIN-TAX-SHELL-1 PASS_VERIFIED).

Inventory count desk for BZG. UNKNOWN when empty/no facts. Never invent
stock levels, counts, SKU on-hand, or par fills. Preserves BZG-OPS-DESK-1.
staff_ready=false · human_commissioned=false. Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain GGV-METRIC-HONESTY-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_ops_desk1 as _ops

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "BZG-INVENTORY-TRUTH-1"
SCHEMA_ID = "wolf.bzg-inventory-truth-1.v1"
BOUND = "beta-bzg-inventory-safe"
CAP_INVENTORY = "CAP-BZG inventory"
LEGAL_ENTITY = "ENT-BZG"
OWNER_PERSON = "PERS-MATT"
BOARD_PERM = "atrium.board.read"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/bzg/inventory-truth-1",
        "/bzg/inventory-truth-1/",
        "/bzg/inventory-truth",
        "/bzg/inventory-truth/",
        "/bzg/inventory",
        "/bzg/inventory/",
        "/bzg-inventory-truth-1",
        "/bzg-inventory-truth-1/",
        "/bzg-inventory-truth",
        "/bzg-inventory-truth/",
        "/bzg-inventory",
        "/bzg-inventory/",
        "/bzg-inventory-truth-1.html",
        "/dashboards/bzg-inventory-truth-1.html",
    }
)
API_PATH = "/api/bzg/inventory-truth-1"

PRESERVED_PACKS = ("BZG-OPS-DESK-1",)

# Inventory count stubs — structure only. Values stay null/UNKNOWN until facts.
_INVENTORY_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "on_hand_total",
        "On-hand · total",
        "Aggregate BZG on-hand. No count facts. UNKNOWN — never invent stock.",
    ),
    (
        "sku_on_hand",
        "SKU on-hand",
        "Per-SKU on-hand stub. No count facts. UNKNOWN — never invent.",
    ),
    (
        "last_count",
        "Last count",
        "Last physical count stub. No count stamp. UNKNOWN — never invent.",
    ),
    (
        "count_qty",
        "Count quantity",
        "Counted quantity stub. No count sheet facts. UNKNOWN — never invent.",
    ),
    (
        "par_level",
        "Par level",
        "Par / reorder stub. No par facts. UNKNOWN — never invent fills.",
    ),
    (
        "count_variance",
        "Count variance",
        "Count vs book variance stub. No facts. UNKNOWN — never invent.",
    ),
)

_INVENT_STOCK_TOKENS = frozenset(
    {
        "stock",
        "stocks",
        "invent-stock",
        "invent_stock",
        "fake-stock",
        "fake_stock",
        "on-hand",
        "on_hand",
        "onhand",
        "sku-on-hand",
        "sku_on_hand",
        "count",
        "counts",
        "count-qty",
        "count_qty",
        "counted",
        "inventory",
        "invent",
        "invent-count",
        "invent_count",
        "fake-count",
        "fake_count",
        "par",
        "par-level",
        "par_level",
        "fill",
        "qty",
        "quantity",
        "level",
        "levels",
        "variance",
        "count-variance",
        "count_variance",
    }
)


class BzgInventoryTruth1Error(ValueError):
    """Fail closed. Does not invent stock or counts."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 403,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner progress.read or BZG board (Zayen). Amanda / unsigned fail closed."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        if _rbac.can(pid, "progress.read", {}, conn=c):
            return True
        if _rbac.can(pid, BOARD_PERM, {"entity_id": LEGAL_ENTITY}, conn=c):
            return True
        return False
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise BzgInventoryTruth1Error(
            "BZG inventory truth desk is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _inventory_slot(stub_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "kind": "inventory_count_stub",
        "entity": "BZG",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "value": None,
        "qty": None,
        "unit": None,
        "fact_count": 0,
        "last_fact_at": None,
        "last_count_at": None,
        "fake_stock": False,
        "invented_count": False,
        "invented_stock": False,
        "why": why,
    }


def _inventory_slots() -> list[dict[str, Any]]:
    return [_inventory_slot(*spec) for spec in _INVENTORY_SLOT_SPECS]


def bzg_ops_desk1_preserved() -> dict[str, Any]:
    """Read-only: BZG-OPS-DESK-1 still honest empty / no invented sales."""
    try:
        desk = _ops.build_desk(OWNER_PERSON)
        flags = _ops.honesty_flags()
        sc = desk.get("status_checks") or {}
        ok = (
            desk.get("ok") is True
            and desk.get("staff_ready") is False
            and desk.get("human_commissioned") is False
            and flags.get("invented_sales") is False
            and flags.get("unknown_when_facts_missing") is True
            and bool(sc.get("master_insufficient_facts"))
        )
        return {
            "ok": ok,
            "staff_ready": desk.get("staff_ready"),
            "human_commissioned": desk.get("human_commissioned"),
            "invented_sales": flags.get("invented_sales"),
            "master_insufficient_facts": bool(sc.get("master_insufficient_facts")),
            "why": (
                "BZG-OPS-DESK-1 preserved: master insufficient_facts, "
                "invented_sales=false, staff_ready/human_commissioned false. "
                "This pack adds inventory honesty — does not replace ops desk."
                if ok
                else "BZG-OPS-DESK-1 check failed — pack must not break ops desk."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "BZG-OPS-DESK-1 check failed — pack must not break ops desk.",
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "bzg_ops_desk",
            "label": "BZG Ops Desk",
            "href": "/bzg/ops-desk",
            "kind": "existing",
            "note": "Upstream ops unify. Preserved — not replaced.",
        },
        {
            "id": "bzg_waste_yield",
            "label": "BZG Waste / Yield",
            "href": "/bzg/waste-yield",
            "kind": "existing",
            "note": "Variance/BOM honesty. Separate from inventory counts.",
        },
        {
            "id": "bzg_labor_cost",
            "label": "BZG Labor Cost",
            "href": "/bzg/labor-cost-1",
            "kind": "existing",
            "note": "Labor honesty shell. Separate from inventory.",
        },
        {
            "id": "bzg_finance",
            "label": "BZG finance desk",
            "href": "/bzg/finance",
            "kind": "existing",
            "note": "BZG COA template shell. No invent stock from finance.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    ops = bzg_ops_desk1_preserved()
    return [
        {
            "id": "inventory_slots",
            "label": "Inventory count slots",
            "status": "UNKNOWN",
            "value": None,
            "why": "No count facts → stock/qty UNKNOWN (not zero). Empty is honest.",
        },
        {
            "id": "fake_stock",
            "label": "Fake stock",
            "status": "REFUSED",
            "value": False,
            "why": "Fake stock / invent-count writes are refused.",
        },
        {
            "id": "invented_count",
            "label": "Invented counts",
            "status": "REFUSED",
            "value": False,
            "why": "Count qty stays null until a real count fact lands.",
        },
        {
            "id": "bzg_ops_desk1",
            "label": "BZG-OPS-DESK-1",
            "status": "PRESERVED" if ops.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": ops.get("why"),
        },
        {
            "id": "cap_bzg_inventory",
            "label": "CAP-BZG inventory",
            "status": "SPECIFIED",
            "value": None,
            "why": "Inventory count honesty desk only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    ops = bzg_ops_desk1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_bzg_inventory": CAP_INVENTORY,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_stock": False,
        "invented_stock": False,
        "invented_count": False,
        "invented_qty": False,
        "invented_par": False,
        "invented_on_hand": False,
        "live_inventory": False,
        "inventory_write": False,
        "count_write": False,
        "zero_as_success": False,
        "unknown_when_facts_missing": True,
        "empty_slots_honest": True,
        "inventory_unknown": True,
        "counts_unknown": True,
        "bzg_ops_desk1_preserved": ops.get("ok") is True,
        "replaces_ops_desk_page": False,
        "second_inventory_system": False,
        "cap_bzg_inventory_proven": False,
        "cap_bzg_inventory_ready": False,
        "cap_bzg_inventory_maturity": "SPECIFIED",
        "cap_bzg_inventory_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "production": False,
        "anon_fail_closed": True,
        "amanda_deny_bzg": True,
        "owner_read": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "GGV-METRIC-HONESTY-1",
    }


def refuse_fake_stock(_body: dict | None = None) -> None:
    raise BzgInventoryTruth1Error(
        "Fake stock is refused. Inventory stays UNKNOWN until real count facts.",
        code="fake_stock_refused",
        http_status=403,
    )


def refuse_invent_stock(_body: dict | None = None) -> None:
    raise BzgInventoryTruth1Error(
        "Invented stock / on-hand / qty / par are refused.",
        code="invent_stock_refused",
        http_status=403,
    )


def refuse_invent_count(_body: dict | None = None) -> None:
    raise BzgInventoryTruth1Error(
        "Invented counts are refused. Count qty stays null until facts.",
        code="invent_count_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise BzgInventoryTruth1Error(
        "PROVEN is refused. CAP-BZG inventory stays SPECIFIED. Empty is not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BzgInventoryTruth1Error(
        "READY is refused. An empty inventory honesty desk is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise BzgInventoryTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if token in {
            "fake-stock",
            "fake_stock",
            "stock",
            "stocks",
            "on-hand",
            "onhand",
        } or norm in {"fake_stock", "stock", "stocks", "on_hand", "onhand"}:
            refuse_fake_stock(payload)
        if token in {
            "count",
            "counts",
            "count-qty",
            "counted",
            "fake-count",
            "invent-count",
        } or norm in {
            "count",
            "counts",
            "count_qty",
            "counted",
            "fake_count",
            "invent_count",
        }:
            refuse_invent_count(payload)
        if token in _INVENT_STOCK_TOKENS or norm in {
            t.replace("-", "_") for t in _INVENT_STOCK_TOKENS
        }:
            if "count" in token or "count" in norm:
                refuse_invent_count(payload)
            if "stock" in token or "stock" in norm or "fake" in token:
                refuse_fake_stock(payload)
            refuse_invent_stock(payload)
    raise BzgInventoryTruth1Error(
        "BZG-INVENTORY-TRUTH-1 is a read honesty desk. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_inventory_slots_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    slots = pack.get("inventory_slots") or []
    if not slots:
        return False
    return all(
        s.get("value") is None
        and s.get("qty") is None
        and s.get("fact_count") == 0
        and s.get("last_count_at") is None
        and s.get("fake_stock") is False
        and s.get("invented_count") is False
        and s.get("invented_stock") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        for s in slots
    )


def no_fake_stock(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    return (
        pack.get("fake_stock") is False
        and pack.get("invented_stock") is False
        and pack.get("invented_count") is False
        and all_inventory_slots_unknown(pack)
    )


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility
    when person_id is None (tests); require_view when person_id provided."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    slots = _inventory_slots()
    ops = bzg_ops_desk1_preserved()
    fact_count = sum(int(s.get("fact_count") or 0) for s in slots)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_INVENTORY],
        "title": "BZG Inventory Count Honesty Desk",
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "fake_stock": False,
        "invented_stock": False,
        "invented_count": False,
        "invented_qty": False,
        "invented_par": False,
        "invented_on_hand": False,
        "live_inventory": False,
        "inventory_write": False,
        "count_write": False,
        "fact_count": fact_count,
        "inventory_unknown": fact_count == 0,
        "counts_unknown": fact_count == 0,
        "last_count_at": None,
        "bzg_ops_desk1_preserved": ops.get("ok") is True,
        "cap_bzg_inventory_proven": False,
        "cap_bzg_inventory_ready": False,
        "cap_bzg_inventory_maturity": flags["cap_bzg_inventory_maturity"],
        "cap_bzg_inventory_ceiling": flags["cap_bzg_inventory_ceiling"],
        "inventory_slots": slots,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "bzg_ops_desk1": ops,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_inventory",
            "stock_levels",
            "count_qty",
            "on_hand",
            "par_level",
            "inventory_write",
            "CAP-BZG inventory PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "GGV-METRIC-HONESTY-1",
        "summary": (
            "BZG inventory count honesty desk. UNKNOWN when empty. "
            "No fake stock. No invented counts. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "inventory_slots": [s[0] for s in _INVENTORY_SLOT_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "REFUSED", "PRESERVED"],
        "stock_value_property": False,
        "count_property": False,
        "writes_accepted": False,
        "fake_stock": False,
        "unknown_when_facts_missing": True,
        "preserves": list(PRESERVED_PACKS),
        "why": (
            "BZG inventory count honesty desk. UNKNOWN when empty. "
            "No fake stock. No invented counts."
        ),
    }
