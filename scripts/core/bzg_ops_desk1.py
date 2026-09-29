#!/usr/bin/env python3
"""BZG-OPS-DESK-1 — Single Beta BZG ops desk (outlets + venue-pnl + foundations).

Decision served: 2026-09-20 PICK CAP-BZG-02 venue P&L & management rollup
framework skeleton on Beta only, deepened by FINAL_WOLF_COMPLETION_MISSION
Phase 2 pack BZG-OPS-DESK-1 (armed 2026-09-30 after INTEL-LEARN-1 PASS_VERIFIED).

Composes existing BZG-OUTLET-1 registry, BZG-VENUEPL-1 rollup, and
BZG-XOUTLET-1 foundations into one Owner/Zayen-readable ops desk.
Does NOT invent sales, P&L, closes, or go-live numbers. UNKNOWN when
facts missing (venue_daily_closes may be 0). Preserves prior packs —
does not replace /bzg/outlets or /bzg/venue-pnl.
CAP-BZG-02 stays SPECIFIED. Ceiling BUILT only. Not PROVEN/READY.
staff_ready=false · human_commissioned=false.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_outlet_registry as _outlets
from core import bzg_venue_pnl as _vpnl
from core import bzg_xoutlet_foundations as _xout

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

PACK_ID = "BZG-OPS-DESK-1"
SCHEMA_ID = "wolf.bzg-ops-desk-1.v1"
BOUND = "beta-bzg-ops-desk-safe"
CAP_ID = "CAP-BZG-02"
CR_ID = "CR-1f136175afbcf7d4"
LEGAL_ENTITY = "ENT-BZG"
OWNER_PERSON = "PERS-MATT"
BOARD_PERM = "atrium.board.read"

PAGE_PATHS = frozenset(
    {
        "/bzg/ops-desk",
        "/bzg/ops-desk/",
        "/bzg/ops",
        "/bzg/ops/",
        "/bzg-ops-desk",
        "/bzg-ops-desk/",
        "/bzg-ops-desk.html",
        "/dashboards/bzg-ops-desk.html",
    }
)
API_PATH = "/api/bzg/ops-desk"

PRESERVED_PACKS = (
    "BZG-OUTLET-1",
    "BZG-XOUTLET-1",
    "BZG-VENUEPL-1",
    "FC-SHELL-2",
)

GAPS: tuple[str, ...] = (
    "Ops desk is a read unify over outlets + venue-pnl + foundations.",
    "venue_daily_closes may be 0 — revenue/cost/contribution stay UNKNOWN.",
    "No invented sales, P&L, budgets, allocations, or go-live numbers.",
    "CAP-BZG-02 stays SPECIFIED. CR-1f136175afbcf7d4 stays OPEN.",
    "staff_ready=false · human_commissioned=false always on this pack.",
    "Preserves /bzg/outlets and /bzg/venue-pnl — does not replace them.",
)


class BzgOpsDesk1Error(ValueError):
    """Fail closed. Does not invent sales or flip readiness."""

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
        raise BzgOpsDesk1Error(
            "BZG ops desk is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def ledger_cap_state() -> str:
    if not LEDGER_JSON.is_file():
        return "SPECIFIED"
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "SPECIFIED"
    row = data.get(CAP_ID)
    if isinstance(row, list) and row:
        return str(row[0] or "SPECIFIED")
    if isinstance(row, str) and row.strip():
        return row.strip()
    return "SPECIFIED"


def honesty_flags() -> dict[str, Any]:
    state = ledger_cap_state()
    ceiling = state if state in {"PROVEN", "READY"} else "BUILT"
    return {
        "cap": CAP_ID,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cr_id": CR_ID,
        "legal_entity_id": LEGAL_ENTITY,
        "preserved_packs": list(PRESERVED_PACKS),
        "invented_sales": False,
        "invented_pnl": False,
        "invented_costs": False,
        "invented_covers": False,
        "invented_go_live_numbers": False,
        "invented_allocations": False,
        "invented_multi_outlet_totals": False,
        "zero_as_success": False,
        "unknown_when_facts_missing": True,
        "money_movement": False,
        "live_pnl": False,
        "rollup_machinery": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "score_changed": False,
        "production": False,
        "alchemist_write": False,
        "anon_fail_closed": True,
        "amanda_deny_bzg": True,
        "cr_mutated": False,
        "model_c_write": False,
        "model_c_maturity_raised": False,
        "ledger_maturity": state,
        "maturity": state,
        "maturity_ceiling": ceiling,
        "proven": False,
        "ready": False,
        "cap_bzg_02_proven": False,
        "cap_bzg_02_ready": False,
        "replaces_outlets_page": False,
        "replaces_venue_pnl_page": False,
        "extends_outlet_registry": True,
        "extends_venue_pnl": True,
        "extends_xoutlet_foundations": True,
    }


def gaps() -> list[str]:
    return list(GAPS)


def refuse_fake_sales(_body: dict | None = None) -> None:
    raise BzgOpsDesk1Error(
        "Fake sales / invented P&L numbers are refused on BZG-OPS-DESK-1.",
        code="fake_sales_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise BzgOpsDesk1Error(
        "Inventing PROVEN is refused. CAP-BZG-02 stays at the ledger state.",
        code="score_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BzgOpsDesk1Error(
        "Inventing READY is refused. An ops desk unify is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise BzgOpsDesk1Error(
        "Payment / money movement is refused on BZG-OPS-DESK-1.",
        code="payment_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise BzgOpsDesk1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "sales",
            "fake-sales",
            "revenue",
            "pnl",
            "contribution",
            "fill",
            "invent",
        }:
            refuse_fake_sales(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token == "ready":
            refuse_ready(payload)
        if token in {"payment", "pay", "transfer", "bank"}:
            refuse_payment(payload)
    raise BzgOpsDesk1Error(
        "BZG-OPS-DESK-1 is a read unify. Writes (sales/P&L/ready/payment) refused.",
        code="write_refused",
        http_status=403,
    )


def _close_count(conn: sqlite3.Connection) -> int:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='venue_daily_closes'"
    ).fetchone()
    if not exists:
        return 0
    row = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()
    return int(row[0] or 0) if row else 0


def build_desk(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Compose outlets registry + venue-pnl rollup + xoutlet foundations."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        require_view(person_id, conn=conn)
        outlets = _outlets.list_outlets(conn)
        foundations = _xout.foundations_panel(conn)
        close_n = _close_count(conn)
    finally:
        conn.close()

    rollup = _vpnl.build_outlet_rollup(catalog_db=path)
    panel = _vpnl.rollup_panel_for_outlets()
    flags = honesty_flags()

    uma = next((o for o in outlets if o["outlet_id"] == "BZG-UMA"), None)
    rain = next((o for o in outlets if o["outlet_id"] == "BZG-RAIN"), None)
    pool = next((o for o in outlets if o["outlet_id"] == "OU-BZG-RAIN-POOL"), None)

    master = rollup.get("master") or {}
    master_status = master.get("status") or "insufficient_facts"

    return {
        "ok": True,
        "title": "BZG Ops Desk",
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap": CAP_ID,
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "message": (
            "Single Beta BZG ops desk linking outlet registry, venue P&L rollup, "
            "and cross-outlet foundations. Facts only — UNKNOWN when closes/journals "
            "are absent. Not PROVEN. Not READY. Not staff_ready."
        ),
        "links": {
            "outlets": "/bzg/outlets",
            "venue_pnl": "/bzg/venue-pnl",
            "outlets_api": "/api/bzg/outlets/overview",
            "venue_pnl_api": "/api/bzg/venue-pnl/rollup",
            "foundations_api": "/api/bzg/outlets/foundations",
            "ops_desk_api": API_PATH,
        },
        "outlets_panel": {
            "pack": "BZG-OUTLET-1",
            "title": "Outlet registry",
            "href": "/bzg/outlets",
            "outlet_count": len(outlets),
            "outlets": outlets,
            "open_count": sum(1 for o in outlets if o.get("status") == "OPEN"),
            "uma_open": bool(uma and uma.get("status") == "OPEN"),
            "rainforest_pre_opening": bool(
                rain and rain.get("status") == "PRE-OPENING"
            ),
            "pool_bar_pre_opening": bool(
                pool and pool.get("status") == "PRE-OPENING"
            ),
            "empty_ops_metrics": True,
            "message": (
                "Canonical ENT-BZG outlets. Statuses only — no invented sales."
            ),
        },
        "venue_pnl_panel": {
            **panel,
            "pack": "BZG-VENUEPL-1",
            "master_status": master_status,
            "master_message": master.get("message"),
            "master_revenue": master.get("revenue"),
            "outlets_with_numeric_facts": rollup.get("outlets_with_numeric_facts", 0),
            "venue_daily_closes": close_n,
            "closes_unknown": close_n == 0,
            "live_pnl": False,
            "message": (
                "Read-only venue mini-business rollup. "
                f"venue_daily_closes={close_n} → "
                + (
                    "revenue/cost/contribution UNKNOWN (not zero)."
                    if close_n == 0
                    else "facts present for some outlets only."
                )
            ),
        },
        "foundations_panel": {
            **{k: foundations[k] for k in foundations if k not in {"ok"}},
            "pack": "BZG-XOUTLET-1",
            "href": "/bzg/outlets",
            "api": "/api/bzg/outlets/foundations",
        },
        "status_checks": {
            "uma_open": bool(uma and uma.get("status") == "OPEN"),
            "rainforest_pre_opening": bool(
                rain and rain.get("status") == "PRE-OPENING"
            ),
            "pool_bar_pre_opening": bool(
                pool and pool.get("status") == "PRE-OPENING"
            ),
            "master_insufficient_facts": master_status == "insufficient_facts",
            "venue_daily_closes": close_n,
        },
        "honesty": flags,
        "gaps": gaps(),
        "staff_ready": False,
        "human_commissioned": False,
        "proven": False,
        "ready": False,
        "live_pnl": False,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "FIN-RECON-SHELL-1",
        "summary": (
            "BZG ops desk unify. Outlets + venue-pnl + foundations on one Beta "
            "surface. Honesty UNKNOWN where facts missing. Amanda denied. "
            "Unsigned 403. staff_ready=false · human_commissioned=false."
        ),
    }


def public_payload(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    return build_desk(person_id, catalog_db=catalog_db)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "cap": CAP_ID,
        "writes_accepted": False,
        "fake_sales": False,
        "unknown_when_facts_missing": True,
        "preserves": list(PRESERVED_PACKS),
        "extends": [
            "scripts/core/bzg_outlet_registry.py",
            "scripts/core/bzg_venue_pnl.py",
            "scripts/core/bzg_xoutlet_foundations.py",
        ],
        "why": (
            "Single Beta BZG ops desk linking outlets, venue-pnl, and foundations "
            "with honesty. UNKNOWN when closes/journals absent."
        ),
    }
