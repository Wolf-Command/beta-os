#!/usr/bin/env python3
"""BZG-WASTE-YIELD-1 — Waste/yield variance honesty desk (facts only).

Decision served: 2026-09-20 PICK CAP-BZG-04 variance/waste + CAP-BZG-06
BOM/yield skeletons, deepened by FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
BZG-WASTE-YIELD-1 (armed 2026-09-30 after CONTENT-ENGINE-LIVE-1 PASS_VERIFIED).

Composes existing bzg_variance_waste + bzg_bom_yield into one Owner/Zayen-
readable honesty desk. Does NOT invent waste, yield, variance, comps, voids,
BOM, theoretical cost, or menu-engineering numbers. Empty slots stay empty /
UNKNOWN. Preserves prior packs — does not replace /bzg-variance-waste or
/bzg-bom-yield. Preserves BZG-OPS-DESK-1 + BZG-VENUEPL-1 honesty.
CAP-BZG-04 / CAP-BZG-06 stay SPECIFIED. Ceiling BUILT only. Not PROVEN/READY.
staff_ready=false · human_commissioned=false.
Does not auto-chain FIN-AP-AR-SHELL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_bom_yield as _bom
from core import bzg_variance_waste as _var

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

PACK_ID = "BZG-WASTE-YIELD-1"
SCHEMA_ID = "wolf.bzg-waste-yield-1.v1"
BOUND = "beta-bzg-waste-yield-safe"
CAP_VARIANCE = "CAP-BZG-04"
CAP_BOM = "CAP-BZG-06"
CR_VARIANCE = "CR-72671b592b8f8631"
CR_BOM = "CR-bbabeb11ff864169"
LEGAL_ENTITY = "ENT-BZG"
OWNER_PERSON = "PERS-MATT"
BOARD_PERM = "atrium.board.read"
PROD_PID_HELD = 15975

PAGE_PATHS = frozenset(
    {
        "/bzg/waste-yield",
        "/bzg/waste-yield/",
        "/bzg/waste-yield-desk",
        "/bzg/waste-yield-desk/",
        "/bzg-waste-yield",
        "/bzg-waste-yield/",
        "/bzg-waste-yield.html",
        "/dashboards/bzg-waste-yield.html",
    }
)
API_PATH = "/api/bzg/waste-yield"

PRESERVED_PACKS = (
    "BZG-OPS-DESK-1",
    "BZG-VENUEPL-1",
    "BZG-VARIANCE-WASTE-V1",
    "BZG-BOM-YIELD-V1",
)

GAPS: tuple[str, ...] = (
    "Waste/yield desk is a read unify over empty variance + BOM/yield skeletons.",
    "Variance / waste / comps / voids / analysis slots stay empty — UNKNOWN, not zero.",
    "BOM / yield / waste / theoretical_cost / menu_engineering slots stay empty.",
    "No invented waste, yield, variance, or cost numbers.",
    "CAP-BZG-04 and CAP-BZG-06 stay SPECIFIED. Ceiling BUILT only.",
    "staff_ready=false · human_commissioned=false always on this pack.",
    "Preserves /bzg-variance-waste, /bzg-bom-yield, BZG-OPS-DESK-1, BZG-VENUEPL-1.",
)

_FAKE_NUMBER_TOKENS = frozenset(
    {
        "waste",
        "fake-waste",
        "yield",
        "fake-yield",
        "variance",
        "fake-variance",
        "comps",
        "voids",
        "analysis",
        "bom",
        "theoretical-cost",
        "theoretical_cost",
        "menu-engineering",
        "menu_engineering",
        "fill",
        "invent",
        "invent-waste",
        "invent-yield",
        "invent-variance",
        "waste-pct",
        "yield-pct",
        "variance-pct",
    }
)


class BzgWasteYield1Error(ValueError):
    """Fail closed. Does not invent waste/yield/variance numbers."""

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
        raise BzgWasteYield1Error(
            "BZG waste/yield desk is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _ledger_cap_state(cap_id: str) -> str:
    if not LEDGER_JSON.is_file():
        return "SPECIFIED"
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "SPECIFIED"
    row = data.get(cap_id)
    if isinstance(row, list) and row:
        return str(row[0] or "SPECIFIED")
    if isinstance(row, str) and row.strip():
        return row.strip()
    return "SPECIFIED"


def honesty_flags() -> dict[str, Any]:
    var_state = _ledger_cap_state(CAP_VARIANCE)
    bom_state = _ledger_cap_state(CAP_BOM)
    ceiling = "BUILT"
    if var_state in {"PROVEN", "READY"} or bom_state in {"PROVEN", "READY"}:
        # Never invent PROVEN/READY from unify — still report ledger truth but
        # desk ceiling stays BUILT unless both are actually proven (they aren't).
        ceiling = "BUILT"
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_variance": CAP_VARIANCE,
        "cap_bom": CAP_BOM,
        "cr_variance": CR_VARIANCE,
        "cr_bom": CR_BOM,
        "legal_entity_id": LEGAL_ENTITY,
        "preserved_packs": list(PRESERVED_PACKS),
        "invented_waste": False,
        "invented_yield": False,
        "invented_variance": False,
        "invented_comps": False,
        "invented_voids": False,
        "invented_bom": False,
        "invented_theoretical_cost": False,
        "invented_menu_engineering": False,
        "zero_as_success": False,
        "unknown_when_facts_missing": True,
        "empty_slots_honest": True,
        "live_variance_waste": False,
        "live_bom_yield_machinery": False,
        "inventory_variance_machinery": False,
        "recipe_cost_standards": False,
        "money_movement": False,
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
        "ledger_maturity_variance": var_state,
        "ledger_maturity_bom": bom_state,
        "maturity": "SPECIFIED",
        "maturity_ceiling": ceiling,
        "proven": False,
        "ready": False,
        "cap_bzg_04_proven": False,
        "cap_bzg_04_ready": False,
        "cap_bzg_06_proven": False,
        "cap_bzg_06_ready": False,
        "replaces_variance_waste_page": False,
        "replaces_bom_yield_page": False,
        "replaces_ops_desk_page": False,
        "replaces_venue_pnl_page": False,
        "extends_variance_waste": True,
        "extends_bom_yield": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "next_pack_for_parent_only": "FIN-AP-AR-SHELL-1",
        "cursor_did_not_auto_start_next": True,
    }


def gaps() -> list[str]:
    return list(GAPS)


def refuse_fake_numbers(_body: dict | None = None) -> None:
    raise BzgWasteYield1Error(
        "Fake waste / yield / variance numbers are refused on BZG-WASTE-YIELD-1.",
        code="fake_numbers_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise BzgWasteYield1Error(
        "Inventing PROVEN is refused. CAP-BZG-04 / CAP-BZG-06 stay at ledger state.",
        code="score_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BzgWasteYield1Error(
        "Inventing READY is refused. An empty waste/yield desk is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise BzgWasteYield1Error(
        "Payment / money movement is refused on BZG-WASTE-YIELD-1.",
        code="payment_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise BzgWasteYield1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in _FAKE_NUMBER_TOKENS or token.replace("-", "_") in {
            t.replace("-", "_") for t in _FAKE_NUMBER_TOKENS
        }:
            refuse_fake_numbers(payload)
        if token in {"proven", "prove", "score"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if token in {"payment", "pay", "transfer", "bank"}:
            refuse_payment(payload)
    raise BzgWasteYield1Error(
        "BZG-WASTE-YIELD-1 is a read unify. Writes (waste/yield/variance/ready/payment) refused.",
        code="write_refused",
        http_status=403,
    )


def _slot_summary(kinds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in kinds:
        kind = str(row.get("kind") or "")
        slot = str(row.get("slot") or "empty")
        evidence = row.get("evidence")
        numeric = None
        for key in (
            "variance",
            "waste",
            "comps",
            "voids",
            "analysis",
            "bom",
            "yield",
            "theoretical_cost",
            "menu_engineering",
        ):
            if row.get(key) is not None:
                numeric = row.get(key)
                break
        status = "EMPTY"
        if evidence is not None or numeric is not None or slot not in {"empty", ""}:
            status = "FACT" if evidence is not None or numeric is not None else "UNKNOWN"
        else:
            status = "UNKNOWN"
        out.append(
            {
                "kind": kind,
                "label": row.get("label") or kind,
                "slot": slot or "empty",
                "status": status,
                "value": numeric if numeric is not None else "UNKNOWN",
                "evidence": evidence,
                "why": row.get("why"),
            }
        )
    return out


def build_desk(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Compose variance/waste + BOM/yield skeletons into one honesty desk."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        require_view(person_id, conn=conn)
    finally:
        conn.close()

    var_fw = _var.build_framework(catalog_db=path)
    bom_fw = _bom.build_framework(catalog_db=path)
    flags = honesty_flags()

    var_kinds = list(var_fw.get("kinds") or [])
    bom_kinds = list(bom_fw.get("kinds") or [])
    var_slots = _slot_summary(var_kinds)
    bom_slots = _slot_summary(bom_kinds)

    var_empty = all(s.get("slot") == "empty" for s in var_slots) if var_slots else True
    bom_empty = all(s.get("slot") == "empty" for s in bom_slots) if bom_slots else True
    var_recorded = int(var_fw.get("recorded_count") or 0)
    bom_recorded = int(bom_fw.get("recorded_count") or 0)

    return {
        "ok": True,
        "title": "BZG Waste / Yield Desk",
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap": CAP_VARIANCE,
        "caps": [CAP_VARIANCE, CAP_BOM],
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "message": (
            "Single Beta BZG waste/yield honesty desk linking CAP-BZG-04 variance/"
            "waste and CAP-BZG-06 BOM/yield skeletons. Facts only — UNKNOWN when "
            "slots are empty. Not PROVEN. Not READY. Not staff_ready."
        ),
        "links": {
            "variance_waste": "/bzg-variance-waste",
            "bom_yield": "/bzg-bom-yield",
            "ops_desk": "/bzg/ops-desk",
            "venue_pnl": "/bzg/venue-pnl",
            "variance_api": "/api/bzg/variance-waste",
            "bom_api": "/api/bzg/bom-yield",
            "waste_yield_api": API_PATH,
        },
        "variance_panel": {
            "pack": "BZG-VARIANCE-WASTE-V1",
            "cap": CAP_VARIANCE,
            "cr_id": CR_VARIANCE,
            "title": "Variance / waste skeleton",
            "href": "/bzg-variance-waste",
            "api": "/api/bzg/variance-waste",
            "framework_skeleton": var_fw.get("framework_skeleton") or "BUILT",
            "recorded_count": var_recorded,
            "on_disk": bool(var_fw.get("on_disk")),
            "empty": var_empty,
            "slots": var_slots,
            "gaps": list(var_fw.get("gaps") or [])[:6],
            "live_variance_waste": False,
            "inventory_variance_machinery": False,
            "message": (
                "Named variance/waste/comps/voids/analysis/notes slots. "
                + (
                    "All empty → values UNKNOWN (not zero). Not a live analysis."
                    if var_empty
                    else "Some slots have facts — still not PROVEN/READY."
                )
            ),
        },
        "bom_yield_panel": {
            "pack": "BZG-BOM-YIELD-V1",
            "cap": CAP_BOM,
            "cr_id": CR_BOM,
            "title": "BOM / yield skeleton",
            "href": "/bzg-bom-yield",
            "api": "/api/bzg/bom-yield",
            "framework_skeleton": bom_fw.get("framework_skeleton") or "BUILT",
            "recorded_count": bom_recorded,
            "on_disk": bool(bom_fw.get("on_disk")),
            "empty": bom_empty,
            "slots": bom_slots,
            "gaps": list(bom_fw.get("gaps") or [])[:6],
            "live_bom_yield_machinery": False,
            "recipe_cost_standards": False,
            "message": (
                "Named bom/yield/waste/theoretical_cost/menu_engineering/notes slots. "
                + (
                    "All empty → values UNKNOWN (not zero). Not live BOM/yield machinery."
                    if bom_empty
                    else "Some slots have facts — still not PROVEN/READY."
                )
            ),
        },
        "status_checks": {
            "variance_empty": var_empty,
            "bom_empty": bom_empty,
            "variance_recorded_count": var_recorded,
            "bom_recorded_count": bom_recorded,
            "all_unknown": var_empty and bom_empty,
            "live_variance_waste": False,
            "live_bom_yield_machinery": False,
        },
        "honesty": flags,
        "gaps": gaps(),
        "staff_ready": False,
        "human_commissioned": False,
        "proven": False,
        "ready": False,
        "live_variance_waste": False,
        "live_bom_yield_machinery": False,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "FIN-AP-AR-SHELL-1",
        "summary": (
            "BZG waste/yield honesty desk. Variance + BOM/yield skeletons on one "
            "Beta surface. UNKNOWN where slots empty. Amanda denied. Unsigned 403. "
            "staff_ready=false · human_commissioned=false."
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
        "caps": [CAP_VARIANCE, CAP_BOM],
        "writes_accepted": False,
        "fake_waste_numbers": False,
        "unknown_when_facts_missing": True,
        "preserves": list(PRESERVED_PACKS),
        "extends": [
            "scripts/core/bzg_variance_waste.py",
            "scripts/core/bzg_bom_yield.py",
        ],
        "why": (
            "Single Beta BZG waste/yield honesty desk linking variance/waste and "
            "BOM/yield skeletons. UNKNOWN when slots empty."
        ),
    }
