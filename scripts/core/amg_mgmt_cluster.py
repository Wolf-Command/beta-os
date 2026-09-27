#!/usr/bin/env python3
"""AMG Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-AMG-CLUSTER-2026-09-22.md.

Composes existing AMG capability modules (service improve, revenue yield,
daily ops state, journey workflow, PMS orchestration, SLA/incident) into one
phone-first hotel management read model with honesty EMPTY/UNWIRED/WAITING_DATA
strips and derived next actions.

Distinct from Sprint2 P3 day-loop (amg_ops_pack). Does not duplicate day-loop
or claim live PMS/occupancy/ADR/RevPAR/revenue/guest/service proof.

Bound beta-amg-day-safe.

Additive compose-only. Does not invent hotel facts. Does not invent PROVEN/READY.
Does not resolve CRs. Does not raise CAP maturity. No Yanolja/external write.
No money/CF/Production. No P3 reopen. No GGV/BZG touch.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import amg_daily_ops_state as daily
from core import amg_journey_workflow as journey
from core import amg_ops_pack as ops
from core import amg_pms_orchestration as pms
from core import amg_revenue_yield as yield_
from core import amg_service_improve as improve
from core import amg_sla_incident as sla
from core import founder_dep_routing as fdr
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-amg-day-safe"
SCHEMA_ID = "wolf.amg-mgmt-cluster.v1"
SLICE = "amg_mgmt_cluster_v1"
OWNER = "PERS-MATT"

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "service_improve",
        "cap": improve.CAP_ID,
        "cr": improve.CR_ID,
        "title": "Service improvement",
        "staff_title": "Review-to-improve",
        "href": "/amg-service-improve",
        "kind": "skeleton",
        "builder": "improve",
        "empty_message": (
            "Review / finding / action slots are empty. "
            "Empty is not a live review-to-improve loop."
        ),
        "next_label": "Wire service improvement source",
        "next_code": "wire_source",
    },
    {
        "id": "revenue_yield",
        "cap": yield_.CAP_ID,
        "cr": yield_.CR_ID,
        "title": "Revenue / yield",
        "staff_title": "Yield machinery",
        "href": "/amg-revenue-yield",
        "kind": "skeleton",
        "builder": "yield",
        "empty_message": (
            "Revenue / yield slots are empty. "
            "Empty is not ADR, RevPAR, occupancy, or live yield machinery."
        ),
        "next_label": "Wire revenue / yield source",
        "next_code": "wire_source",
    },
    {
        "id": "daily_ops_state",
        "cap": daily.CAP_ID,
        "cr": daily.CR_ID,
        "title": "Daily hotel operating state",
        "staff_title": "Daily ops state",
        "href": "/amg-daily-ops-state",
        "kind": "daily_ops",
        "builder": "daily",
        "empty_message": (
            "Daily hotel operating-state slots are empty. "
            "Day-loop objects on the AMG ops pack are operable but are not "
            "occupancy, ADR, RevPAR, revenue, guest, or live PMS evidence."
        ),
        "next_label": "Open daily ops state framework",
        "next_code": "wire_source",
    },
    {
        "id": "journey_workflow",
        "cap": journey.CAP_ID,
        "cr": journey.CR_ID,
        "title": "Guest journey workflow",
        "staff_title": "Journey workflow",
        "href": "/amg-journey-workflow",
        "kind": "skeleton",
        "builder": "journey",
        "empty_message": (
            "Journey workflow slots are empty. "
            "Empty is not a live guest journey and not guest/service proof."
        ),
        "next_label": "Wire journey workflow source",
        "next_code": "wire_source",
    },
    {
        "id": "pms_orchestration",
        "cap": pms.CAP_ID,
        "cr": pms.CR_ID,
        "title": "PMS orchestration",
        "staff_title": "PMS / Yanolja",
        "href": "/amg-pms-orchestration",
        "kind": "pms_skeleton",
        "builder": "pms",
        "empty_message": (
            "PMS orchestration slots are empty. No Yanolja connector. "
            "Empty is not live PMS proof, occupancy, or folio evidence."
        ),
        "next_label": "Review PMS orchestration framework",
        "next_code": "wire_source",
    },
    {
        "id": "sla_incident",
        "cap": sla.CAP_ID,
        "cr": sla.CR_ID,
        "title": "SLA / incident trail",
        "staff_title": "SLA / incidents",
        "href": "/amg-sla-incident",
        "kind": "skeleton",
        "builder": "sla",
        "empty_message": (
            "SLA / incident slots are empty. "
            "Empty is not a live incident trail or service SLA proof."
        ),
        "next_label": "Wire SLA / incident source",
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
    "folio_write": False,
    "zayen_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "p3_reopened": False,
    "day_loop_rewritten": False,
    "ggv_touched": False,
    "bzg_touched": False,
    "wip_quartet_touched": False,
    "invented_occupancy": False,
    "invented_adr": False,
    "invented_revpar": False,
    "invented_revenue": False,
    "invented_guest": False,
    "invented_pms": False,
    "invented_service": False,
    "invented_hotel_facts": False,
    "yanolja_write": False,
    "yanolja_called": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent hotel management facts or maturity."""

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
        "yanolja_write_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses money, payment, bank, folio, and Zayen paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_yanolja(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster refuses Yanolja / PMS external write.",
        code="yanolja_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "AMG Management Cluster is compose-only. External writes are refused.",
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
        "folio": "money",
        "zayen": "money",
        "books": "money",
        "transfer": "money",
        "resolve": "resolve",
        "production": "production",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "access": "cloudflare",
        "yanolja": "yanolja",
        "pms": "yanolja",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
    }
    return mapping.get(tail)


def require_actor(
    person_id: str | None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner or active Atrium hotel-ops seat. Fail closed for anon / outsider."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "AMG Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    if pid in set(ops.hotel_ops_ids(catalog_db)):
        return {
            "person_id": pid,
            "seat": "hotel_ops",
            "label": sru.human_person(pid),
        }
    raise MgmtClusterError(
        "AMG Management Cluster is Owner or an active Atrium hotel-ops seat only.",
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


def _skeleton_framework(builder: str, ledger_path: Path | str | None, catalog_db: Path | str | None) -> dict[str, Any]:
    if builder == "improve":
        return improve.build_framework(ledger_path, catalog_db)
    if builder == "yield":
        return yield_.build_framework(ledger_path, catalog_db)
    if builder == "daily":
        return daily.build_framework(ledger_path, catalog_db)
    if builder == "journey":
        return journey.build_framework(ledger_path, catalog_db)
    if builder == "pms":
        return pms.build_framework(ledger_path, catalog_db)
    if builder == "sla":
        return sla.build_framework(ledger_path, catalog_db)
    raise MgmtClusterError(f"Unknown skeleton builder {builder}", code="bad_module")


def _honesty_strip(
    *,
    status: str,
    message: str,
    next_label: str,
    next_href: str,
    next_code: str,
) -> dict[str, Any]:
    empty = sru.empty_with_next(
        message,
        next_label=next_label,
        next_href=next_href,
        next_code=next_code,
    )
    return {
        "status": status,
        "empty": True,
        "message": message,
        "numbers": None,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "revenue": None,
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
        "Atrium hotel-ops management cluster routing",
        has_staff_seat=bool(ops.hotel_ops_ids(catalog_db)),
    )
    handoff = {
        "founder_dep_class": founder["class"],
        "founder_dep_reason": founder["reason"],
        "safe_implement": founder["safe_implement"],
        "invented_owner_control_away": False,
        "seat_hint": "Hotel ops" if founder["safe_implement"] else "Owner",
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

    if spec["kind"] == "daily_ops":
        fw = _skeleton_framework(spec["builder"], ledger_path, catalog_db)
        is_empty = int(fw.get("recorded_count") or 0) == 0
        status = "EMPTY" if is_empty else "WAITING_DATA"
        strip = _honesty_strip(
            status=status,
            message=spec["empty_message"],
            next_label=spec["next_label"],
            next_href=spec["href"],
            next_code=spec["next_code"],
        )
        strip["status_tags"] = ["EMPTY", "UNWIRED"] if is_empty else ["WAITING_DATA"]
        strip["unwired"] = is_empty
        strip["day_loop_not_occupancy"] = True
        return {
            **base,
            "honesty_strip": strip,
            "primary_next": strip["next_action"],
            "framework_empty": is_empty,
            "recorded_count": int(fw.get("recorded_count") or 0),
            "live": False,
            "module_honesty": {
                "empty": is_empty,
                "day_loop_separate": True,
                "day_loop_href": "/amg-ops-pack",
                "occupancy": None,
                "adr": None,
                "revpar": None,
                "hotel_operations": False,
                "numbers": None,
            },
        }

    if spec["kind"] == "pms_skeleton":
        fw = _skeleton_framework(spec["builder"], ledger_path, catalog_db)
        is_empty = int(fw.get("recorded_count") or 0) == 0
        status = "EMPTY" if is_empty else "WAITING_DATA"
        strip = _honesty_strip(
            status=status,
            message=spec["empty_message"],
            next_label=spec["next_label"],
            next_href=spec["href"],
            next_code=spec["next_code"],
        )
        strip["status_tags"] = ["EMPTY", "UNWIRED"] if is_empty else ["WAITING_DATA"]
        strip["unwired"] = is_empty
        strip["yanolja_connected"] = False
        strip["yanolja_write"] = False
        return {
            **base,
            "honesty_strip": strip,
            "primary_next": strip["next_action"],
            "framework_empty": is_empty,
            "recorded_count": int(fw.get("recorded_count") or 0),
            "live": False,
            "module_honesty": {
                "empty": is_empty,
                "yanolja_connected": False,
                "yanolja_write": False,
                "pms_live": False,
                "occupancy": None,
                "numbers": None,
            },
        }

    if spec["kind"] == "skeleton":
        fw = _skeleton_framework(spec["builder"], ledger_path, catalog_db)
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
                "empty": is_empty,
                "live_yield": False,
                "live_journey": False,
                "live_service": False,
                "numbers": None,
            },
        }

    raise MgmtClusterError(f"Unknown module kind {spec['kind']}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    """Phone-first nav for the management cluster (additive; not P3 day-loop)."""
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "ops", "label": "Day loop", "href": "/amg-ops-pack"},
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
        "pack": "amg_mgmt",
        "lede": (
            "AMG management cluster — service improve, yield, daily ops state, "
            "journey, PMS orchestration, SLA/incident. Empty stays empty."
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
    """Compose one staff-readable AMG management cluster desk."""
    seat = require_actor(verified_person_id, catalog_db)
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
    empire = fdr.label_for_pack_handoff("AMG", empty_count)
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
            "pack": "AMG",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: route empty-module attention "
                "to Atrium hotel-ops seat — labels only, Owner desk not removed."
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
        "occupancy": None,
        "adr": None,
        "revpar": None,
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
    seat = require_actor(verified_person_id, catalog_db)
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
