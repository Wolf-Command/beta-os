#!/usr/bin/env python3
"""GGV Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-GGV-CLUSTER-2026-09-22.md.

Composes existing Wave modules (strategy machine, client P&L, speed-to-lead,
social derive, intercompany) into one phone-first staff read model with
honesty EMPTY/UNWIRED/WAITING_DATA strips and derived next actions for
Amanda / Haikal / Misa seats.

Bound beta-ggv-loop-safe.

Additive compose-only. Does not invent strategy scores, client P&L,
speed-to-lead SLAs, social metrics, or intercompany numbers. Does not invent
PROVEN/READY. Does not resolve CRs. Does not raise CAP maturity. No money /
CRM external write / CF / Production. No WIP quartet. No P2 loop reopen.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import ggv_client_profitability as pnl
from core import ggv_intercompany_client as ic
from core import ggv_social_derive as social
from core import ggv_speed_to_lead_prove as stl
from core import ggv_strategy_machine as strat
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-ggv-loop-safe"
SCHEMA_ID = "wolf.ggv-mgmt-cluster.v1"
SLICE = "ggv_mgmt_cluster_v1"
OWNER = "PERS-MATT"
SEAT_STAFF = frozenset({"PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA"})

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "strategy_machine",
        "cap": strat.CAP_ID,
        "cr": strat.CR_ID,
        "title": "Strategy machine",
        "staff_title": "Strategy / plan / asset",
        "href": "/ggv-strategy-machine",
        "kind": "skeleton",
        "builder": "strat",
        "empty_message": (
            "Strategy / plan / asset / workflow / learn slots are empty. "
            "Empty is not a live strategy machine."
        ),
        "next_label": "Wire strategy source",
        "next_code": "wire_source",
    },
    {
        "id": "client_profitability",
        "cap": pnl.CAP_ID,
        "cr": pnl.CR_ID,
        "title": "Client / contract P&L",
        "staff_title": "Client P&L",
        "href": "/ggv-client-profitability",
        "kind": "skeleton",
        "builder": "pnl",
        "empty_message": (
            "Client / contract / allocation slots are empty. "
            "Empty is not a live client P&L."
        ),
        "next_label": "Wire client P&L source",
        "next_code": "wire_source",
    },
    {
        "id": "speed_to_lead",
        "cap": stl.CAP_ID,
        "cr": stl.CR_ID,
        "title": "Speed-to-lead prove",
        "staff_title": "Speed to lead",
        "href": "/speed-to-lead-prove",
        "kind": "speed_prove",
        "builder": None,
        "empty_message": (
            "Speed-to-lead prove is read-only Habitat red-team. "
            "No SLA target invented. CAP ledger stays BUILT; CR stays OPEN."
        ),
        "next_label": "Review Habitat speed-to-lead prove",
        "next_code": "review_prove",
    },
    {
        "id": "social_derive",
        "cap": social.CAP_ID,
        "cr": social.CR_ID,
        "title": "Social DERIVE views",
        "staff_title": "Social metrics",
        "href": "/ggv-social",
        "kind": "social",
        "builder": None,
        "empty_message": (
            "No authorised Metricool-read rows on this desk. "
            "Missing numbers stay missing. No Metricool write."
        ),
        "next_label": "Open social DERIVE with a brand key",
        "next_code": "wire_source",
    },
    {
        "id": "intercompany_client",
        "cap": ic.CAP_ID,
        "cr": ic.CR_ID,
        "title": "Intercompany client",
        "staff_title": "Intercompany",
        "href": "/ggv-intercompany-client",
        "kind": "skeleton",
        "builder": "ic",
        "empty_message": (
            "Intercompany slots are empty. Empty is not live "
            "GGV/AMG/BZG client billing."
        ),
        "next_label": "Wire intercompany source",
        "next_code": "wire_source",
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
    "p2_reopened": False,
    "wip_quartet_touched": False,
    "invented_strategy_score": False,
    "invented_client_pnl": False,
    "invented_sla": False,
    "invented_social_metrics": False,
    "invented_intercompany": False,
    "crm_external_write": False,
    "klaviyo_write": False,
    "metricool_write": False,
    "activecampaign_write": False,
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
        "crm_write_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses money, payment, bank, and Zayen paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_crm_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster refuses CRM / Klaviyo / Metricool / ActiveCampaign writes.",
        code="crm_write_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "GGV Management Cluster is compose-only. External writes are refused.",
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
        "crm": "crm",
        "klaviyo": "crm",
        "metricool": "crm",
        "activecampaign": "crm",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner or GGV seats (Amanda / Haikal / Misa). Fail closed for anon / outsider."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "GGV Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    if pid in SEAT_STAFF:
        return {"person_id": pid, "seat": "ops", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "GGV Management Cluster is Owner or GGV staff seat (Amanda / Haikal / Misa) only.",
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
    if builder == "strat":
        return strat.build_framework()
    if builder == "pnl":
        return pnl.build_register()
    if builder == "ic":
        return ic.build_framework()
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
) -> dict[str, Any]:
    maturity = _ledger_cap(spec["cap"], ledger_path)
    cr = _cr_row(spec["cr"], catalog_db)
    founder = fdr.classify_text(
        f"{spec['cap']} | {spec['title']} | {cr.get('next_action') or spec['next_label']} | "
        "GGV ops continuous next-action routing to Amanda seat",
        has_staff_seat=True,
    )
    handoff = {
        "founder_dep_class": founder["class"],
        "founder_dep_reason": founder["reason"],
        "safe_implement": founder["safe_implement"],
        "invented_owner_control_away": False,
        "seat_hint": "Amanda" if founder["safe_implement"] else "Owner",
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
                "live_strategy": False,
                "live_pnl": False,
                "live_billing": False,
                "numbers": None,
            },
        }

    if spec["kind"] == "speed_prove":
        prove = stl.build_prove(catalog_db=catalog_db, ledger_path=ledger_path)
        habitat = prove.get("habitat") or {}
        habitat_empty = bool(habitat.get("empty"))
        sla = habitat.get("sla_target_seconds")
        if habitat_empty:
            status = "WAITING_DATA"
            tags = ["WAITING_DATA", "BUILT"]
            message = spec["empty_message"]
            next_label = spec["next_label"]
            next_code = spec["next_code"]
        else:
            status = "WAITING_DATA"
            tags = ["WAITING_DATA"]
            message = (
                "Habitat rows classified for speed-to-lead prove. "
                "No SLA invented. CR stays OPEN."
            )
            next_label = "Review speed-to-lead prove gaps"
            next_code = "review_prove"
        strip = _honesty_strip(
            status=status,
            message=message,
            next_label=next_label,
            next_href=spec["href"],
            next_code=next_code,
        )
        # Prove pack is BUILT ledger — not an empty skeleton invent.
        strip["empty"] = habitat_empty
        strip["status_tags"] = tags
        strip["unwired"] = False
        strip["sla_target_seconds"] = None  # never invent
        strip["invented_sla"] = False
        if sla is not None:
            # Module must never surface an invented SLA; refuse to echo one.
            strip["sla_target_seconds"] = None
        return {
            **base,
            "honesty_strip": strip,
            "primary_next": strip["next_action"],
            "framework_empty": habitat_empty,
            "recorded_count": int(habitat.get("count") or 0) if isinstance(habitat.get("count"), int) else None,
            "live": False,
            "module_honesty": {
                "empty": habitat_empty,
                "prove_pack_only": True,
                "sla_target_seconds": None,
                "invented_sla": False,
                "numbers": None,
                "cap_stays_built": True,
                "cr_stays_open": True,
            },
        }

    # social derive — brand-less compose strip (WAITING / EMPTY, no invent)
    try:
        view = social.derive_view(
            None,
            person_id=person_id,
            role_allowed=(person_id != OWNER),
            catalog_db=catalog_db,
        )
        available = bool(view.get("available"))
        note = str(view.get("note") or spec["empty_message"])
    except social.SocialDeriveError:
        available = False
        note = spec["empty_message"]
        view = {"blended_score": None, "invented_metrics": False}

    if not available:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        next_label = "Review social DERIVE surfaces"
        next_code = "review_derive"

    strip = _honesty_strip(
        status=status,
        message=note if not available else (
            "Authorised Metricool-read rows present. Surfaces not blended. "
            "Missing stays missing."
        ),
        next_label=next_label,
        next_href=spec["href"],
        next_code=next_code,
    )
    strip["empty"] = not available
    strip["status_tags"] = tags
    strip["unwired"] = not available
    strip["blended_score"] = None
    strip["invented_metrics"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": not available,
        "recorded_count": None,
        "live": False,
        "module_honesty": {
            "empty": not available,
            "available": available,
            "blended_score": None,
            "invented_metrics": False,
            "metricool_write": False,
            "numbers": None,
        },
    }


def phone_nav() -> list[dict[str, str]]:
    """Phone-first nav for the management cluster (additive; not P2 ops loop)."""
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "ops", "label": "Ops", "href": "/ggv-ops-pack"},
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
        "pack": "ggv_mgmt",
        "lede": (
            "GGV management cluster — strategy, client P&L, speed-to-lead, "
            "social derive, intercompany. Empty stays empty."
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
) -> dict[str, Any]:
    """Compose one staff-readable GGV management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            person_id=seat["person_id"],
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("GGV", empty_count)
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
            "pack": "GGV",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: route empty-module attention "
                "to Amanda GGV seat — labels only, Owner desk not removed."
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
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                person_id=seat["person_id"],
                ledger_path=ledger_path,
                catalog_db=catalog_db,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
