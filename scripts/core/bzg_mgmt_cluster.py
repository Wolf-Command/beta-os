#!/usr/bin/env python3
"""BZG Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-BZG-CLUSTER-2026-09-22.md.

Composes existing Wave modules (venue P&L, variance, allocation, BOM,
reputation, POS/ESB via Uma) into one phone-first staff read model with
honesty EMPTY/UNWIRED/WAITING_DATA strips and derived next actions.

Bound beta-bzg-loop-safe.

Additive compose-only. Does not invent P&L/variance/allocation/BOM/reputation
numbers. Does not invent PROVEN/READY. Does not resolve CRs. Does not raise
CAP maturity. No money/CF/Production. No P1 Today→PR→close reopen.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_allocation_engine as alloc
from core import bzg_bom_yield as bom
from core import bzg_reputation_observe as rep
from core import bzg_variance_waste as var
from core import bzg_venue_pnl as pnl
from core import founder_dep_routing as fdr
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-bzg-loop-safe"
SCHEMA_ID = "wolf.bzg-mgmt-cluster.v1"
SLICE = "bzg_mgmt_cluster_v1"
OWNER = "PERS-MATT"
SEAT_STAFF = frozenset({"PERS-MATT", "PERS-DEVI"})

# Cluster modules — CAP-BZG-01 POS is partial via Uma (no separate skeleton).
MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "venue_pnl",
        "cap": pnl.CAP_ID,
        "cr": pnl.CR_ID,
        "title": "Venue P&L",
        "staff_title": "Venue P&L",
        "href": "/bzg-venue-pnl",
        "kind": "skeleton",
        "builder": "pnl",
        "empty_message": "Venue P&L slots are empty. Empty is not a live P&L.",
        "next_label": "Wire a venue P&L source",
        "next_code": "wire_source",
    },
    {
        "id": "variance_waste",
        "cap": var.CAP_ID,
        "cr": var.CR_ID,
        "title": "Variance / waste",
        "staff_title": "Variance & waste",
        "href": "/bzg-variance-waste",
        "kind": "skeleton",
        "builder": "var",
        "empty_message": "Variance/waste slots are empty. Empty is not a live analysis.",
        "next_label": "Wire variance/waste source",
        "next_code": "wire_source",
    },
    {
        "id": "allocation_engine",
        "cap": alloc.CAP_ID,
        "cr": alloc.CR_ID,
        "title": "Allocation engine",
        "staff_title": "Cost allocation",
        "href": "/bzg-allocation-engine",
        "kind": "skeleton",
        "builder": "alloc",
        "empty_message": "Allocation slots are empty. Empty is not a live allocation engine.",
        "next_label": "Wire allocation drivers",
        "next_code": "wire_source",
    },
    {
        "id": "bom_yield",
        "cap": bom.CAP_ID,
        "cr": bom.CR_ID,
        "title": "BOM / yield",
        "staff_title": "Recipe cost / yield",
        "href": "/bzg-bom-yield",
        "kind": "skeleton",
        "builder": "bom",
        "empty_message": "BOM/yield slots are empty. Empty is not live recipe cost machinery.",
        "next_label": "Wire BOM / yield source",
        "next_code": "wire_source",
    },
    {
        "id": "pos_observe",
        "cap": "CAP-BZG-01",
        "cr": "CR-cdba39b34b44985e",
        "title": "POS / ESB observe",
        "staff_title": "POS / ESB",
        "href": "/bzg/uma-blu",
        "kind": "pos_partial",
        "builder": None,
        "empty_message": (
            "POS orchestration is partial via Uma / ESB facts. "
            "This desk does not invent sales numbers."
        ),
        "next_label": "Open Uma Today for live ops facts",
        "next_code": "open_uma",
    },
    {
        "id": "reputation",
        "cap": rep.CAP_ID,
        "cr": rep.CR_ID,
        "title": "Reputation observe",
        "staff_title": "Reputation",
        "href": "/bzg-reputation",
        "kind": "reputation",
        "builder": "rep",
        "empty_message": (
            "No review source is connected. No star rating was invented. "
            "Empty is not a reputation summary."
        ),
        "next_label": "Record a provenance observation",
        "next_code": "record_observation",
    },
)

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "compose_only": True,
    "additive_only": True,
    "phone_first": True,
    "invented_proven": False,
    "invented_ready": False,
    "proven": False,
    "ready": False,
    "caps_raised": False,
    "cr_resolved": False,
    "ledger_write": False,
    "model_c_write": False,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "zayen_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "p1_reopened": False,
    "wip_quartet_touched": False,
    "invented_pnl": False,
    "invented_variance": False,
    "invented_allocation": False,
    "invented_bom": False,
    "invented_reputation": False,
    "invented_pos_numbers": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent management numbers or maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "modules": [m["id"] for m in MODULE_SPECS],
        "caps": [m["cap"] for m in MODULE_SPECS],
        "writes_accepted": False,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses money, payment, bank, and Zayen paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "BZG Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_code(path: str) -> str | None:
    """Map refuse path tails to refuse codes for serve_beta."""
    tail = path.rstrip("/").rsplit("/", 1)[-1].lower()
    mapping = {
        "proven": "proven",
        "prove": "proven",
        "ready": "ready",
        "payment": "money",
        "money": "money",
        "bank": "money",
        "zayen": "money",
        "books": "money",
        "transfer": "money",
        "resolve": "resolve",
        "production": "production",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "access": "cloudflare",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner or Uma/BZG ops seat (Devi). Fail closed for anon / outsider."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "BZG Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    if pid in SEAT_STAFF:
        return {"person_id": pid, "seat": "ops", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "BZG Management Cluster is Owner or Uma/BZG ops seat only.",
        code="forbidden",
    )


def _ledger_cap(cap: str, ledger_path: Path | str | None = None) -> str:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(cap) if isinstance(data, dict) else None
    if isinstance(row, list) and row:
        return str(row[0])
    return "UNKNOWN"


def _cr_row(cr_id: str, catalog_db: Path | str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": cr_id,
        "state": None,
        "capability": None,
        "title": None,
        "next_action": None,
        "present": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (cr_id,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["present"] = True
    out["state"] = row[0]
    out["capability"] = row[1]
    out["title"] = row[2]
    out["next_action"] = row[3]
    return out


def _skeleton_framework(builder: str) -> dict[str, Any]:
    if builder == "pnl":
        return pnl.build_framework()
    if builder == "var":
        return var.build_framework()
    if builder == "alloc":
        return alloc.build_framework()
    if builder == "bom":
        return bom.build_framework()
    raise MgmtClusterError(f"Unknown skeleton builder {builder}", code="bad_module")


def _honesty_strip(
    *,
    status: str,
    message: str,
    next_label: str,
    next_href: str,
    next_code: str,
) -> dict[str, Any]:
    """Staff-facing honesty strip. Never invents numbers."""
    empty = sru.empty_with_next(
        message,
        next_label=next_label,
        next_href=next_href,
        next_code=next_code,
    )
    return {
        "status": status,  # EMPTY | UNWIRED | WAITING_DATA
        "empty": True,
        "message": message,
        "numbers": None,
        "invented": False,
        "next_action": empty["next_action"],
    }


def _module_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    reputation_db: Path | str | None = None,
) -> dict[str, Any]:
    maturity = _ledger_cap(spec["cap"], ledger_path)
    cr = _cr_row(spec["cr"], catalog_db)
    founder = fdr.classify_text(
        f"{spec['cap']} | {spec['title']} | {cr.get('next_action') or spec['next_label']} | "
        "Uma ops switchboard staff seat Devi",
        has_staff_seat=True,
    )
    handoff = {
        "founder_dep_class": founder["class"],
        "founder_dep_reason": founder["reason"],
        "safe_implement": founder["safe_implement"],
        "invented_owner_control_away": False,
        "seat_hint": "Devi" if founder["safe_implement"] else "Owner",
    }

    base = {
        "id": spec["id"],
        "cap": spec["cap"],
        "cr": spec["cr"],
        "title": spec["title"],
        "staff_title": spec["staff_title"],
        "href": spec["href"],
        "kind": spec["kind"],
        "ledger_maturity": maturity,
        "cr_state": cr.get("state"),
        "cr_resolved": cr.get("state") == "RESOLVED",
        "invented_proven": False,
        "invented_ready": False,
        "owner_empire_handoff": handoff,
    }

    if spec["kind"] == "skeleton":
        fw = _skeleton_framework(spec["builder"])
        is_empty = bool(fw.get("empty")) or int(fw.get("recorded_count") or 0) == 0
        # Skeleton with no wired source → EMPTY + UNWIRED (surface both honestly).
        status = "EMPTY" if is_empty else "WAITING_DATA"
        strip = _honesty_strip(
            status=status,
            message=spec["empty_message"],
            next_label=spec["next_label"],
            next_href=spec["href"],
            next_code=spec["next_code"],
        )
        if is_empty:
            strip["unwired"] = True
            strip["status_tags"] = ["EMPTY", "UNWIRED"]
        else:
            strip["status_tags"] = [status]
        return {
            **base,
            "honesty_strip": strip,
            "primary_next": strip["next_action"],
            "framework_empty": is_empty,
            "recorded_count": int(fw.get("recorded_count") or 0),
            "live": False,
            "module_honesty": {
                "empty": True,
                "live_pnl": False,
                "live_analysis": False,
                "live_allocation": False,
                "live_bom": False,
                "numbers": None,
            },
        }

    if spec["kind"] == "pos_partial":
        strip = _honesty_strip(
            status="WAITING_DATA",
            message=spec["empty_message"],
            next_label=spec["next_label"],
            next_href=spec["href"],
            next_code=spec["next_code"],
        )
        strip["status_tags"] = ["WAITING_DATA", "PARTIAL"]
        strip["unwired"] = False
        return {
            **base,
            "honesty_strip": strip,
            "primary_next": strip["next_action"],
            "framework_empty": False,
            "recorded_count": None,
            "live": False,
            "module_honesty": {
                "empty": False,
                "partial_via_uma": True,
                "numbers": None,
                "invented_pos_numbers": False,
            },
        }

    # reputation
    try:
        obs = rep.list_observations(
            person_id,
            role_allowed=(person_id != OWNER),
            db_path=reputation_db,
        )
        count = int(obs.get("count") or 0)
        source_connected = bool(obs.get("source_connected"))
    except rep.ReputationObserveError:
        count = 0
        source_connected = False
        obs = {"summary_rating": None, "five_star_invented": False}

    if not source_connected and count == 0:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    elif not source_connected:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA", "UNWIRED"]
        next_label = "Connect a review source (no invent)"
        next_code = "wire_source"
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        next_label = "Review stored observations"
        next_code = "review_obs"

    strip = _honesty_strip(
        status=status,
        message=spec["empty_message"] if count == 0 else (
            f"{count} provenance row(s) stored. No connected source. "
            "No summary rating invented."
        ),
        next_label=next_label,
        next_href=spec["href"],
        next_code=next_code,
    )
    strip["status_tags"] = tags
    strip["unwired"] = not source_connected
    strip["observation_count"] = count
    strip["summary_rating"] = None  # never invent
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": count == 0,
        "recorded_count": count,
        "live": False,
        "module_honesty": {
            "empty": count == 0,
            "source_connected": False,
            "summary_rating": None,
            "five_star_invented": False,
            "numbers": None,
        },
    }


def phone_nav() -> list[dict[str, str]]:
    """Phone-first nav for the management cluster (additive; not P1 ops loop)."""
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "uma", "label": "Uma", "href": "/bzg/uma-blu"},
    ]


def staff_surface(desk: dict[str, Any]) -> dict[str, Any]:
    """Phone-first staff overlay — human words, no CAP-/PROVEN invent."""
    modules = desk.get("modules") or []
    empties = [m for m in modules if (m.get("honesty_strip") or {}).get("empty")]
    primary = None
    for m in modules:
        nxt = m.get("primary_next")
        if nxt and nxt.get("label"):
            primary = nxt
            break
    if primary is None:
        primary = {
            "code": "none",
            "label": "No further management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "bzg_mgmt",
        "lede": (
            "BZG management cluster — P&L, variance, allocation, recipe cost, "
            "POS observe, reputation. Empty stays empty."
        ),
        "who_line": f"Signed in as {who.get('label') or 'Staff'}",
        "primary_next": primary,
        "nav": phone_nav(),
        "empty_module_count": len(empties),
        "exposed_actions": {
            "show_owner_copy": who.get("seat") == "owner",
            "show_operator_actions": True,
            "payment_on_screen": False,
            "show_seats_panel": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": "Management cluster is compose-only; history lives on each module desk.",
            "empty_state": sru.empty_with_next(
                "No management history strip here.",
                next_label="Open a module and wire its source",
                next_href="#modules",
                next_code="open_module",
            ),
        },
    }


def build_desk(
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    reputation_db: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one staff-readable management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            person_id=seat["person_id"],
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            reputation_db=reputation_db,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("BZG", empty_count)
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    desk = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "seat": seat,
        "modules": modules,
        "module_count": len(modules),
        "empty_count": empty_count,
        "primary_next": primary,
        "owner_empire_handoff": {
            **empire,
            "pack": "BZG",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: route empty-module attention "
                "to Devi Uma seat — labels only, Owner desk not removed."
            ),
        },
        "caps": {
            m["cap"]: {
                "maturity": m["ledger_maturity"],
                "cr": m["cr"],
                "cr_state": m["cr_state"],
                "raised": False,
            }
            for m in modules
        },
        "crs_open": [m["cr"] for m in modules if m.get("cr_state") == "OPEN"],
        "crs_resolved_here": False,
        "honesty": honesty_flags(),
        "schema": schema_document(),
        "nav": phone_nav(),
        "money": None,
        "proven": False,
        "ready": False,
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    return desk


def module_strip(
    module_id: str,
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    reputation_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                person_id=seat["person_id"],
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                reputation_db=reputation_db,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
