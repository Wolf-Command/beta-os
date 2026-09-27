#!/usr/bin/env python3
"""CRM Management Cluster desk + Sprint2 P8 CRM Lead Operator Depth — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-CRM-CLUSTER-2026-09-22.md
+ docs/deliveries/GROK-PLAN-SPRINT2-P8-CRM-OPERATOR-DEPTH-2026-09-22.md
(keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete).

Composes existing CRM modules (Lead Spine, Customer Identity & Memory,
Package Intelligence, Habitat Klaviyo read wire) into one phone-first
operator/Owner operating loop with honesty EMPTY/UNWIRED/WAITING_DATA
strips and derived next actions.

P8 adds CRM/lead operator detail/action path (note / next-action /
ownership / handover / dismiss-noise) that refreshes Lead Spine + GGV
desk next-action + Owner/staff attention strips. Reuses lead_spine +
ggv_ops_pack. Never external CRM/Metricool/Klaviyo/Habitat cutover write.
Never invents leads.

Bound beta-ggv-loop-safe.

Additive compose + operator depth. Does not invent guest/client/money facts.
Does not invent PROVEN/READY/COMMISSIONED/ADOPTED. Does not resolve CRs.
Does not raise CAP maturity. No Production/CF/external-write/Klaviyo-send.
No P1/P7/Devi/w12 FIN/parked GGV reopen. Does not touch WIP quartet.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import crm_identity_memory as ident
from core import crm_package_intel as pkg
from core import founder_dep_routing as fdr
from core import habitat_klaviyo_reader as klaviyo
from core import lead_spine as spine
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
KLAVIYO_READER_PATH = BETA_ROOT / "scripts" / "core" / "habitat_klaviyo_reader.py"

BOUND = "beta-ggv-loop-safe"
SCHEMA_ID = "wolf.crm-mgmt-cluster.v1"
SLICE = "crm_mgmt_cluster_v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.crm-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "crm_operator_depth"
OWNER = "PERS-MATT"
AMANDA = "PERS-AMANDA"
HAIKAL = "PERS-HAIKAL"
MISA = "PERS-MISA"
SEAT_STAFF = frozenset({AMANDA, HAIKAL, MISA})
HABITAT = "habitat"
ENTITY_GGV = "ENT-GGV"
PERM_CRM_OPERATOR = "crm.lead.operator"
PERM_CRM_OPERATOR_ID = "PERM-CRM-LEAD-OPERATOR"
SCOPE_CRM_HABITAT_LEAD = "SCOPE-CRM-HABITAT-LEAD"
CRM_OPERATOR_ROLES: tuple[str, ...] = (
    "ROLE-CONTENT-MGMT",
    "ROLE-GGV-EDIT",
    "ROLE-CONTENT-CREW",
)
CRM_OPERATOR_FIXTURES: tuple[str, ...] = (AMANDA, HAIKAL, MISA)
CRM_OPERATOR_ACTION_KINDS = frozenset(
    {
        "note",
        "next_action",
        "ownership_touch",
        "handover_touch",
        "dismiss_noise",
    }
)
# Accept plan wording aliases → canonical kinds.
_ACTION_KIND_ALIASES = {
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "ownership-touch": "ownership_touch",
    "handover-touch": "handover_touch",
    "dismiss-noise": "dismiss_noise",
}

CAP_01 = "CAP-CRM-01"
CAP_02 = "CAP-CRM-02"
CAP_03 = "CAP-CRM-03"
CAP_04 = "CAP-CRM-04"
CR_01 = "CR-ff42f3a7c49caa79"
CR_02 = ident.CR_ID  # CR-820682ce791563fa
CR_03 = pkg.CR_ID  # CR-e5ff219bb1d585f7
CR_04 = "CR-c8719063fb940ed4"

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "lead_spine",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "Lead Spine",
        "staff_title": "Lead operating loop",
        "href": "/lead-spine",
        "kind": "lead_spine",
        "empty_message": (
            "Lead Spine has no fixture leads yet. "
            "Empty is not a live CRM board, not a customer, and not CAP-CRM-01 PROVEN."
        ),
        "waiting_message": (
            "Lead rows are readable on Beta. A lead is not a customer, not a sale, "
            "and not invented money. CR stays OPEN."
        ),
        "next_label": "Open Lead Spine desk",
        "next_code": "open_lead_spine",
    },
    {
        "id": "identity_memory",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Customer Identity & Memory",
        "staff_title": "Identity / memory",
        "href": "/crm-identity",
        "kind": "identity",
        "empty_message": (
            "Customer identity register is empty or unwired. "
            "Empty is not a complete identity graph and not a lead merge."
        ),
        "waiting_message": (
            "Customer rows exist. A customer is not a lead. "
            "A link candidate is not a merge and not graph-complete."
        ),
        "next_label": "Open CRM Identity desk",
        "next_code": "open_identity",
    },
    {
        "id": "package_intel",
        "cap": CAP_03,
        "cr": CR_03,
        "title": "Package Intelligence",
        "staff_title": "Package register",
        "href": "/crm-package-intel",
        "kind": "package",
        "empty_message": (
            "Package product register is empty. "
            "Empty is not a market census and not a price."
        ),
        "waiting_message": (
            "Named package rows exist. A named row is not pricing truth "
            "and not a booking. CR stays OPEN."
        ),
        "next_label": "Open Package Intelligence desk",
        "next_code": "open_package_intel",
    },
    {
        "id": "klaviyo_reader",
        "cap": CAP_04,
        "cr": CR_04,
        "title": "Email / Klaviyo read wire",
        "staff_title": "Klaviyo read-only",
        "href": "/crm-connector-prove",
        "kind": "klaviyo",
        "empty_message": (
            "Habitat Klaviyo reader file is missing. "
            "Absence is not zero subscribers and not a send."
        ),
        "waiting_message": (
            "Habitat Klaviyo reader is present as read-only compose. "
            "This desk does not call Klaviyo, does not send, and does not invent counts."
        ),
        "next_label": "Review CRM connector prove (read-only)",
        "next_code": "open_connector_prove",
    },
)

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "operator_depth_slice": OPERATOR_DEPTH_SLICE,
    "compose_only": True,
    "additive_only": True,
    "phone_first": True,
    "invented_proven": False,
    "invented_ready": False,
    "invented_commissioned": False,
    "invented_adopted": False,
    "invented_leads": False,
    "empty_leads_is_not_invent": True,
    "proven": False,
    "ready": False,
    "caps_raised": False,
    "cr_resolved": False,
    "live_habitat_commission": False,
    "ledger_write": False,
    "model_c_write": False,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "zayen_write": False,
    "finance_controls": False,
    "hr": False,
    "trading": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "commission_flip": False,
    "crm_external_write": False,
    "klaviyo_write": False,
    "klaviyo_send": False,
    "klaviyo_called": False,
    "metricool_write": False,
    "activecampaign_write": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "ggv_reopened": False,
    "bzg_reopened": False,
    "amg_reopened": False,
    "intel_reopened": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "invented_guest": False,
    "invented_client": False,
    "au_crm_01_in_scope": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent CRM management facts or maturity."""

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
        "caps": sorted({m["cap"] for m in MODULE_SPECS}),
        "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "operator_depth_slice": OPERATOR_DEPTH_SLICE,
        "crm_operator_action_kinds": sorted(CRM_OPERATOR_ACTION_KINDS),
        "writes_accepted": False,
        "operator_actions_accepted": True,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "commission_flip_property": False,
        "crm_write_property": False,
        "klaviyo_send_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_crm_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses CRM / Klaviyo send / Metricool / ActiveCampaign writes.",
        code="crm_write_refused",
    )


def refuse_klaviyo_send(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster refuses Klaviyo send / write. Read-only compose only.",
        code="klaviyo_send_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "CRM Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_code(path: str) -> str | None:
    """Map refuse path tails to refuse codes for serve_beta.

    Operator-depth / operator-action paths are not refused here — they are
    authorised Beta CRM lead-operator writes (no external CRM).
    """
    parts = [p for p in path.rstrip("/").split("/") if p]
    if "operator-depth" in parts or "operator-action" in parts:
        return None
    if parts and parts[-1] == "operator" and "leads" in parts:
        return None
    tail = parts[-1].lower() if parts else ""
    mapping = {
        "proven": "proven",
        "prove": "proven",
        "ready": "ready",
        "payment": "money",
        "money": "money",
        "bank": "money",
        "finance": "money",
        "hr": "money",
        "trading": "money",
        "zayen": "money",
        "folio": "money",
        "transfer": "money",
        "resolve": "resolve",
        "production": "production",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "access": "cloudflare",
        "commission": "commission",
        "commissioned": "commission",
        "adopt": "commission",
        "adopted": "commission",
        "crm": "crm",
        "klaviyo": "klaviyo",
        "klaviyo-send": "klaviyo",
        "send": "klaviyo",
        "metricool": "crm",
        "activecampaign": "crm",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
        "invent-lead": "crm",
        "invent": "crm",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner or GGV seats (Amanda / Haikal / Misa). Fail closed for anon / outsider."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "CRM Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    if pid in SEAT_STAFF:
        return {"person_id": pid, "seat": "ops", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "CRM Management Cluster is Owner or GGV staff seat (Amanda / Haikal / Misa) only.",
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
        "money": None,
        "invented": False,
        "next_action": empty["next_action"],
    }


def _base_card(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    maturity = _ledger_cap(spec["cap"], ledger_path)
    cr = _cr_row(spec["cr"], catalog_db)
    founder = fdr.classify_text(
        f"{spec['cap']} | {spec['title']} | {cr.get('next_action') or spec['next_label']} | "
        "GGV CRM ops continuous next-action routing to Amanda seat",
        has_staff_seat=True,
    )
    return {
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
        "owner_empire_handoff": {
            "founder_dep_class": founder["class"],
            "founder_dep_reason": founder["reason"],
            "safe_implement": founder["safe_implement"],
            "invented_owner_control_away": False,
            "seat_hint": "Amanda" if founder["safe_implement"] else "Owner",
        },
    }


def _count_leads(catalog_db: Path | str | None = None) -> tuple[int, bool]:
    """Read-only lead count. Missing table → (0, False wired). Never invents a lead."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return 0, False
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0, False
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM core_leads"
        ).fetchone()
        return int(row[0] or 0), True
    except sqlite3.Error:
        return 0, False
    finally:
        conn.close()


def _lead_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    count, wired = _count_leads(catalog_db)
    # Touch lead_spine module so compose dependency is real (no invent).
    _ = spine.WOLF_STAGES
    if not wired:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    elif count == 0:
        status = "EMPTY"
        tags = ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=next_label,
        next_href=spec["href"],
        next_code=next_code,
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = not wired
    strip["lead_count_echo"] = None  # never surface as invented operating count
    strip["sale"] = False
    strip["customer"] = False
    strip["revenue"] = None
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": count if wired else 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "lead_is_not_customer": True,
            "lead_is_not_sale": True,
            "external_writes": False,
            "numbers": None,
            "money": None,
        },
    }


def _identity_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    base: dict[str, Any],
    identity_db: Path | str | None = None,
) -> dict[str, Any]:
    # Owner can list. Staff without crm.identity.read must not invent customers —
    # compose falls closed to EMPTY/UNWIRED from file presence only.
    count = 0
    try:
        listed = ident.list_customers(
            person_id, role_allowed=False, db_path=identity_db
        )
        count = int(listed.get("count") or 0)
    except ident.CrmIdentityError:
        count = 0
    default_present = (
        ident.DEFAULT_DB.is_file() if identity_db is None else Path(identity_db).is_file()
    )
    if not default_present:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
        unwired = True
    elif count == 0:
        status = "EMPTY"
        tags = ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        unwired = False
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        unwired = False
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=spec["next_label"],
        next_href=spec["href"],
        next_code=spec["next_code"],
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = unwired
    strip["identity_graph_complete"] = False
    strip["merged"] = False
    strip["marketing_blast"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": count,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "distinct_from_lead": True,
            "identity_graph_complete": False,
            "merged": False,
            "marketing_blast": False,
            "numbers": None,
        },
    }


def _package_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    package_db: Path | str | None = None,
) -> dict[str, Any]:
    register = pkg.build_register(db_path=package_db)
    count = int(register.get("recorded_count") or 0)
    is_empty = bool(register.get("empty")) or count == 0
    default_present = (
        pkg.DEFAULT_DB.is_file() if package_db is None else Path(package_db).is_file()
    )
    if not default_present:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
        unwired = True
    elif is_empty:
        status = "EMPTY"
        tags = ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        unwired = False
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        unwired = False
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=spec["next_label"],
        next_href=spec["href"],
        next_code=spec["next_code"],
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = unwired
    strip["price"] = None
    strip["pricing_is_truth"] = False
    strip["booking"] = False
    strip["market_census"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": count,
        "live": False,
        "operator_depth_href": "/crm-package-intel#package-intel-depth",
        "module_honesty": {
            "empty": empty,
            "empty_is_market_census": False,
            "price": None,
            "pricing_is_truth": False,
            "booking": False,
            "numbers": None,
        },
    }


def _klaviyo_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    reader_path: Path | str | None = None,
) -> dict[str, Any]:
    path = Path(reader_path) if reader_path else KLAVIYO_READER_PATH
    present = path.is_file()
    # Compose constants only — never call run_ingest / network.
    source = getattr(klaviyo, "SOURCE_SYSTEM", None)
    clock = getattr(klaviyo, "CLOCK", None)
    if not present:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
        unwired = True
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA", "READ_ONLY"]
        empty = False
        message = spec["waiting_message"]
        unwired = False
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=spec["next_label"],
        next_href=spec["href"],
        next_code=spec["next_code"],
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = unwired
    strip["klaviyo_called"] = False
    strip["klaviyo_write"] = False
    strip["klaviyo_send"] = False
    strip["sends"] = None
    strip["subscribers"] = None
    strip["source_system"] = source if present else None
    strip["clock"] = clock if present else None
    strip["clock_meaning"] = getattr(klaviyo, "CLOCK_MEANING", None) if present else None
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "read_only": True,
            "klaviyo_called": False,
            "klaviyo_write": False,
            "klaviyo_send": False,
            "sends": None,
            "subscribers": None,
            "numbers": None,
        },
    }


def _module_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    identity_db: Path | str | None = None,
    package_db: Path | str | None = None,
    reader_path: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    kind = spec["kind"]
    if kind == "lead_spine":
        return _lead_card(spec, base=base, catalog_db=catalog_db)
    if kind == "identity":
        return _identity_card(
            spec, person_id=person_id, base=base, identity_db=identity_db
        )
    if kind == "package":
        return _package_card(spec, base=base, package_db=package_db)
    if kind == "klaviyo":
        return _klaviyo_card(spec, base=base, reader_path=reader_path)
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "lead", "label": "Leads", "href": "/lead-spine"},
    ]


def staff_surface(desk: dict[str, Any]) -> dict[str, Any]:
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
            "label": "No further CRM management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "crm_mgmt",
        "lede": (
            "CRM management cluster — Lead Spine, identity, package intel, "
            "Klaviyo read wire. Empty stays empty. No send."
        ),
        "who_line": f"Signed in as {who.get('label') or 'Operator'}",
        "primary_next": primary,
        "nav": phone_nav(),
        "empty_module_count": len(empties),
        "exposed_actions": {
            "show_owner_copy": who.get("seat") == "owner",
            "show_operator_actions": True,
            "payment_on_screen": False,
            "show_seats_panel": False,
            "klaviyo_send": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": "Management cluster is compose-only; history lives on each module desk.",
            "empty_state": sru.empty_with_next(
                "No management history strip here.",
                next_label="Open a module",
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
    identity_db: Path | str | None = None,
    package_db: Path | str | None = None,
    reader_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one Owner/ops-facing CRM management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            person_id=seat["person_id"],
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            identity_db=identity_db,
            package_db=package_db,
            reader_path=reader_path,
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

    bound_crs = (CR_01, CR_02, CR_03, CR_04)
    crs_open = []
    for cr_id in bound_crs:
        row = _cr_row(cr_id, catalog_db)
        if row.get("state") == "OPEN":
            crs_open.append(cr_id)

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
            "pack": "CRM",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: CRM loop attention routes to Amanda "
                "GGV seat when safe — labels only, Owner desk not removed."
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
        "crs_open": crs_open,
        "crs_resolved_here": False,
        "honesty": honesty_flags(),
        "schema": schema_document(),
        "nav": phone_nav(),
        "money": None,
        "proven": False,
        "ready": False,
        "commissioned": False,
        "adopted": False,
        "klaviyo_send": False,
        "klaviyo_called": False,
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
    identity_db: Path | str | None = None,
    package_db: Path | str | None = None,
    reader_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                person_id=seat["person_id"],
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                identity_db=identity_db,
                package_db=package_db,
                reader_path=reader_path,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")


# ---------------------------------------------------------------------------
# Sprint2 P8 — CRM Lead Operator Depth (reuse lead_spine + ggv_ops_pack)
# ---------------------------------------------------------------------------


def _under_test_process() -> bool:
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = Path(path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise MgmtClusterError(
            "test mode refuses writes to live catalog DB; point catalog at a temp copy",
            code="live_write_refused",
        )


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _open_catalog(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ggv():
    from core import ggv_ops_pack as pack

    return pack


def _normalise_action_kind(kind: str | None) -> str:
    raw = (kind or "").strip().lower()
    return _ACTION_KIND_ALIASES.get(raw, raw)


def crm_lead_operator_href(lead_id: str | None) -> str:
    key = (lead_id or "").strip()
    if not key:
        return "/crm-mgmt-cluster#operator-depth"
    return f"/crm-mgmt-cluster#crm-lead-{key}"


def _role_has_perm(conn: sqlite3.Connection, role_id: str, perm_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM org_role_permissions
        WHERE role_id=? AND permission_id=? AND effect='ALLOW'
        """,
        (role_id, perm_id),
    ).fetchone()
    return bool(row)


def ensure_operator_depth_rbac(
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Idempotent grant: crm.lead.operator on GGV/CRM staff roles + Habitat scope.

    Beta catalog only. Does not mint CF Access seats. Does not commission live Habitat.
    """
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ts = _now_utc_iso()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_CRM_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_CRM_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_CRM_HABITAT_LEAD,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='brand' AND target_id=?
                """,
                (SCOPE_CRM_HABITAT_LEAD, HABITAT),
            ).fetchone()
        )
        roles_ok = all(_role_has_perm(c, role_id, op_id) for role_id in CRM_OPERATOR_ROLES)
        fixture_asg: dict[str, str | None] = {}
        for pid in CRM_OPERATOR_FIXTURES:
            asg = c.execute(
                """
                SELECT a.assignment_id
                FROM org_assignments a
                JOIN org_positions po ON po.position_id = a.position_id
                WHERE a.person_id=? AND po.role_id IN (?, ?, ?)
                  AND a.status='ACTIVE' AND a.end_at IS NULL
                LIMIT 1
                """,
                (pid, *CRM_OPERATOR_ROLES),
            ).fetchone()
            fixture_asg[pid] = str(asg["assignment_id"]) if asg else None
        scopes_linked = True
        for asg_id in fixture_asg.values():
            if not asg_id:
                scopes_linked = False
                break
            linked = c.execute(
                """
                SELECT 1 FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=?
                """,
                (asg_id, SCOPE_CRM_HABITAT_LEAD),
            ).fetchone()
            if not linked:
                scopes_linked = False
                break

        already = (
            bool(existing)
            and str(existing["status"] or "") == "ACTIVE"
            and bool(scope_row)
            and str(scope_row["status"] or "") == "ACTIVE"
            and target_ok
            and roles_ok
            and scopes_linked
        )
        if already:
            return {
                "ok": True,
                "grants": [PERM_CRM_OPERATOR],
                "roles": list(CRM_OPERATOR_ROLES),
                "permission_ids": {PERM_CRM_OPERATOR: op_id},
                "scope_id": SCOPE_CRM_HABITAT_LEAD,
                "unchanged": True,
                "live_habitat_commission": False,
                "bound": BOUND,
            }

        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        assert_catalog_writable(db_file)

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'crm.lead', 'operator',
              'CRM lead operator detail + note/next-action/ownership/handover/dismiss (no external CRM write)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_CRM_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_CRM_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'brand', 'CRM Habitat lead operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_CRM_HABITAT_LEAD, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'brand', ?, ?)
            """,
            (SCOPE_CRM_HABITAT_LEAD, HABITAT, ts),
        )
        for role_id in CRM_OPERATOR_ROLES:
            role = c.execute(
                "SELECT role_id, status FROM org_roles WHERE role_id=?",
                (role_id,),
            ).fetchone()
            if not role:
                raise MgmtClusterError(
                    f"{role_id} missing — GGV/CRM staff role required",
                    code="role_missing",
                )
            c.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, op_id, ts, ts),
            )
        for pid, asg_id in fixture_asg.items():
            if not asg_id:
                raise MgmtClusterError(
                    f"fixture assignment missing for {pid}",
                    code="assignment_missing",
                )
            c.execute(
                """
                INSERT OR IGNORE INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (asg_id, SCOPE_CRM_HABITAT_LEAD, ts, ts, ts),
            )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_CRM_OPERATOR],
            "roles": list(CRM_OPERATOR_ROLES),
            "permission_ids": {PERM_CRM_OPERATOR: op_id},
            "scope_id": SCOPE_CRM_HABITAT_LEAD,
            "unchanged": False,
            "live_habitat_commission": False,
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def prove_crm_operator(
    *,
    person_id: str = AMANDA,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove Amanda/Haikal/Misa can run CRM lead-operator actions."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip() or AMANDA
        try:
            seat = require_actor(pid)
        except MgmtClusterError:
            seat = None
        target = {"entity_id": ENTITY_GGV, "brand_id": HABITAT}
        can_operator = bool(_rbac.can(pid, PERM_CRM_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id IN (?, ?, ?)
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, *CRM_OPERATOR_ROLES),
        ).fetchone()
        role_id = str(asg["role_id"]) if asg else None
        allowed = can_operator or pid == OWNER
        pack_seat = seat is not None
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "person_id": pid,
            "seat": seat,
            "role_id": role_id,
            "assignment_active": bool(asg) or pid == OWNER,
            "can_crm_operator": allowed,
            "can_lead_operator": allowed,
            "pack_seat": pack_seat,
            "actions": {
                "crm_operator": allowed and pack_seat,
                "lead_operator": allowed and pack_seat,
                "note": allowed and pack_seat,
                "next_action": allowed and pack_seat,
                "ownership_touch": allowed and pack_seat,
                "handover_touch": allowed and pack_seat,
                "dismiss_noise": allowed and pack_seat,
                "crm_write": False,
                "metricool_write": False,
                "klaviyo_write": False,
                "invent_lead": False,
            },
            "live_habitat_commission": False,
            "human_commissioning": "NOT_DONE",
            "target_crs": [CR_01],
            "proven": False,
            "ready": False,
            "external_crm_write": False,
        }
    finally:
        if own:
            c.close()


def _require_crm_operator(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str,
) -> dict[str, Any]:
    from core import rbac as _rbac

    seat = require_actor(verified_person_id)
    pid = seat["person_id"]
    ensure_operator_depth_rbac(conn=conn, commit=False)
    if pid == OWNER:
        return seat
    target = {"entity_id": ENTITY_GGV, "brand_id": HABITAT}
    if not _rbac.can(pid, PERM_CRM_OPERATOR, target, conn=conn):
        raise MgmtClusterError(
            f"permission denied: {PERM_CRM_OPERATOR}",
            code="forbidden",
        )
    return seat


def _lead_has_event(
    conn: sqlite3.Connection,
    lead_id: str,
    event_type: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM core_lead_events
        WHERE lead_id=? AND event_type=?
        LIMIT 1
        """,
        (lead_id, event_type),
    ).fetchone()
    return bool(row)


def _latest_event_kind(
    conn: sqlite3.Connection,
    lead_id: str,
    kinds: tuple[str, ...],
) -> str | None:
    placeholders = ",".join("?" for _ in kinds)
    row = conn.execute(
        f"""
        SELECT event_type FROM core_lead_events
        WHERE lead_id=? AND event_type IN ({placeholders})
        ORDER BY recorded_at DESC, event_id DESC
        LIMIT 1
        """,
        (lead_id, *kinds),
    ).fetchone()
    return str(row[0]) if row else None


def lead_spine_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Lead Spine projection after CRM operator recording. EMPTY honesty."""
    pack = _ggv()
    clock = now or datetime.now(timezone.utc)
    leads = pack._habitat_leads(conn)
    rows = []
    for lead in leads:
        lid = str(lead.get("lead_id") or "")
        dismissed = _lead_has_event(conn, lid, "dismiss_noise_recorded")
        card = pack.operator_card(lead, conn=conn, now=clock)
        rows.append(
            {
                "lead_id": lid,
                "demo_label": card.get("demo_label"),
                "wolf_lifecycle": card.get("wolf_lifecycle"),
                "owner": card.get("owner"),
                "recorded_next_action": card.get("recorded_next_action"),
                "dismissed_noise": dismissed,
                "href": crm_lead_operator_href(lid),
                "invented": False,
            }
        )
    empty = len(rows) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(rows),
        "rows": rows[:40],
        "invented_leads": False,
        "empty_message": (
            "No Habitat leads on Lead Spine — EMPTY (not invent)."
            if empty
            else None
        ),
        "why": (
            "Lead Spine consequence from Habitat fixture leads + CRM operator events. "
            "Empty is not a live CRM board."
        ),
    }


def ggv_desk_next_action_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """GGV desk Needs-You / next-action strip refresh. EMPTY honesty."""
    pack = _ggv()
    clock = now or datetime.now(timezone.utc)
    mgmt = pack.management_exceptions(conn, now=clock)
    speed = pack.speed_exceptions(conn, now=clock)
    primary = None
    leads = pack._habitat_leads(conn)
    for lead in leads:
        lid = str(lead.get("lead_id") or "")
        if _lead_has_event(conn, lid, "dismiss_noise_recorded"):
            continue
        wolf = str(lead.get("wolf_stage") or "").upper()
        if wolf in ("PARKED", "CLOSED"):
            continue
        card = pack.operator_card(lead, conn=conn, now=clock)
        nxt = card.get("loop_next_action") or card.get("recorded_next_action")
        if isinstance(nxt, dict):
            primary = {
                "code": nxt.get("code") or "crm_lead_next",
                "label": nxt.get("label") or "Open CRM lead operator",
                "href": crm_lead_operator_href(lid),
                "lead_id": lid,
                "invented": False,
            }
            break
        if nxt:
            primary = {
                "code": "recorded_next_action",
                "label": str(nxt),
                "href": crm_lead_operator_href(lid),
                "lead_id": lid,
                "invented": False,
            }
            break
    needs = list(mgmt.get("exceptions") or []) + list(speed.get("exceptions") or [])
    empty = primary is None and len(needs) == 0 and len(leads) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "primary_next": primary,
        "management_exceptions": {
            "count": mgmt.get("count") or 0,
            "empty": mgmt.get("empty") is True,
            "exceptions": (mgmt.get("exceptions") or [])[:20],
            "invented": False,
        },
        "needs_you": {
            "count": speed.get("count") or 0,
            "empty": speed.get("empty") is True,
            "exceptions": (speed.get("exceptions") or [])[:20],
            "invented_sla": False,
        },
        "invented_leads": False,
        "empty_message": (
            "No GGV desk next-action / Needs-You from Habitat leads — EMPTY (not invent)."
            if empty
            else None
        ),
        "why": (
            "GGV desk next-action is a projection of Habitat lead loop facts + "
            "management/Needs-You exceptions. Dismiss-noise leads fall off staff strip."
        ),
    }


def owner_attention_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Owner attention from handover / missing next / Needs-You. EMPTY honesty."""
    pack = _ggv()
    clock = now or datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for lead in pack._habitat_leads(conn):
        lid = str(lead.get("lead_id") or "")
        if _lead_has_event(conn, lid, "dismiss_noise_recorded"):
            continue
        wolf = str(lead.get("wolf_stage") or "").upper()
        if wolf in ("PARKED", "CLOSED"):
            continue
        card = pack.operator_card(lead, conn=conn, now=clock)
        aging = pack.aging_exception(lead, now=clock)
        last = _latest_event_kind(
            conn,
            lid,
            (
                "handover_touch_recorded",
                "ownership_touch_recorded",
                "next_action_linked",
                "note_recorded",
                "dismiss_noise_recorded",
            ),
        )
        reasons: list[str] = []
        if last == "handover_touch_recorded":
            reasons.append("handover_touch")
        if aging.get("needs_you"):
            reasons.append("needs_you")
        if wolf in ("OPEN", "ACTIVE") and not card.get("recorded_next_action"):
            reasons.append("missing_next_action")
        if wolf in ("OPEN", "ACTIVE") and not (lead.get("owner_person_id") or "").strip():
            reasons.append("missing_owner")
        if not reasons:
            continue
        items.append(
            {
                "lead_id": lid,
                "demo_label": card.get("demo_label"),
                "reasons": reasons,
                "last_kind": last,
                "href": crm_lead_operator_href(lid),
                "invented": False,
            }
        )
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(items) if not empty else 0,
        "attention_count": len(items) if not empty else None,
        "items": items,
        "empty_message": (
            "No CRM leads need Owner attention — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "why": (
            "Owner attention is a projection of handover-touched / Needs-You / "
            "missing next-action or owner Habitat leads. Dismiss-noise drops off."
        ),
    }


def staff_attention_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Staff attention projection (same connective honesty as Owner strip)."""
    owner = owner_attention_consequence(conn, now=now)
    return {
        "ok": True,
        "bound": BOUND,
        "empty": owner.get("empty") is True,
        "count": owner.get("count") or 0,
        "attention_count": owner.get("attention_count"),
        "items": owner.get("items") or [],
        "empty_message": (
            "No CRM leads need staff attention — EMPTY (not invent)."
            if owner.get("empty")
            else None
        ),
        "invented": False,
        "why": (
            "Staff attention mirrors Owner CRM attention projection. "
            "No separate invented score."
        ),
    }


def list_crm_operator_actions(
    lead_id: str,
    *,
    conn: sqlite3.Connection,
    limit: int = 40,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT event_id, event_type, payload_json, actor_person_id, recorded_at
        FROM core_lead_events
        WHERE lead_id=? AND event_type IN (
          'next_action_linked', 'note_recorded', 'human_touch_recorded',
          'ownership_touch_recorded', 'handover_touch_recorded',
          'dismiss_noise_recorded'
        )
        ORDER BY recorded_at DESC, event_id DESC
        LIMIT ?
        """,
        (lead_id, int(limit)),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        payload: dict[str, Any] = {}
        raw = r["payload_json"]
        try:
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                payload = parsed
        except (TypeError, json.JSONDecodeError):
            payload = {}
        et = str(r["event_type"])
        if et == "next_action_linked":
            kind = "next_action"
            note = payload.get("next_action")
        elif et == "note_recorded":
            kind = "note"
            note = payload.get("note")
        elif et in ("human_touch_recorded", "ownership_touch_recorded"):
            kind = "ownership_touch"
            note = payload.get("note") or payload.get("touched_at")
        elif et == "handover_touch_recorded":
            kind = "handover_touch"
            note = payload.get("note")
        elif et == "dismiss_noise_recorded":
            kind = "dismiss_noise"
            note = payload.get("note")
        else:
            kind = et
            note = None
        out.append(
            {
                "event_id": r["event_id"],
                "kind": kind,
                "note": note,
                "payload": payload,
                "created_by": r["actor_person_id"],
                "created_at": r["recorded_at"],
                "external_crm_write": False,
                "invented": False,
            }
        )
    return out


def operator_lead_detail(
    lead_id: str,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """CRM lead operator detail/action path. No external CRM write. No invent leads."""
    pack = _ggv()
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        lead = pack._habitat_lead_or_raise(c, lead_id)
        pid = (verified_person_id or "").strip() or None
        actions = {
            "crm_operator": False,
            "lead_operator": False,
            "next_action": False,
            "note": False,
            "ownership_touch": False,
            "handover_touch": False,
            "dismiss_noise": False,
            "crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invent_lead": False,
        }
        if pid:
            try:
                require_actor(pid)
                prove = prove_crm_operator(person_id=pid, conn=c)
                actions.update(prove.get("actions") or {})
            except MgmtClusterError:
                pass
        card = pack.operator_card(lead, conn=c, now=now)
        prior = list_crm_operator_actions(str(lead.get("lead_id") or ""), conn=c)
        events = spine.list_lead_events(str(lead.get("lead_id") or ""), conn=c)
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "lead": card,
            "raw": {
                "lead_id": lead.get("lead_id"),
                "source_system": lead.get("source_system"),
                "source_id": lead.get("source_id"),
                "source_stage": lead.get("source_stage"),
                "wolf_stage": lead.get("wolf_stage"),
                "owner_person_id": lead.get("owner_person_id"),
                "first_human_touch_at": lead.get("first_human_touch_at"),
            },
            "actions": actions,
            "operator_actions": prior,
            "events": events[:40],
            "href": crm_lead_operator_href(str(lead.get("lead_id") or "")),
            "lead_spine": lead_spine_consequence(c, now=now),
            "ggv_desk_next_action": ggv_desk_next_action_consequence(c, now=now),
            "owner_attention": owner_attention_consequence(c, now=now),
            "staff_attention": staff_attention_consequence(c, now=now),
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invented_leads": False,
            "live_habitat_commission": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    except pack.OpsPackError as exc:
        raise MgmtClusterError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def record_crm_lead_operator_action(
    *,
    verified_person_id: str,
    lead_id: str,
    kind: str,
    note: str | None = None,
    touched_at: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record note / next-action / ownership / handover / dismiss. Refresh consequences.

    No external CRM / Metricool / Klaviyo write. Does not invent leads.
    """
    pack = _ggv()
    k = _normalise_action_kind(kind)
    if k not in CRM_OPERATOR_ACTION_KINDS:
        raise MgmtClusterError(
            f"kind must be one of {sorted(CRM_OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise MgmtClusterError("verified_person_id required", code="missing_verified_person")
    key = (lead_id or "").strip()
    if not key:
        raise MgmtClusterError("lead_id required", code="missing_lead")
    if k == "next_action" and not text:
        raise MgmtClusterError("next_action note required", code="missing_note")
    if k == "note" and not text:
        raise MgmtClusterError("note required", code="missing_note")
    if k == "handover_touch" and not text:
        raise MgmtClusterError("handover note required", code="missing_note")

    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or db_path or CATALOG_DB)
        assert_catalog_writable(db_file)
        seat = _require_crm_operator(c, verified_person_id=pid)
        lead = pack._habitat_lead_or_raise(c, key)
        before_source = lead.get("source_stage")
        event: dict[str, Any] | None = None

        if k == "next_action":
            spine._refuse_inference({"next_action": text})
            event = spine.append_event(
                key,
                "next_action_linked",
                payload={
                    "next_action": text,
                    "wolf_stage": lead.get("wolf_stage"),
                    "external_crm_write": False,
                    "operator_depth": True,
                    "crm_operator_depth": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "note":
            event = spine.append_event(
                key,
                "note_recorded",
                payload={
                    "note": text,
                    "external_crm_write": False,
                    "operator_depth": True,
                    "crm_operator_depth": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "ownership_touch":
            touch_ts = (touched_at or "").strip() or _now_utc_iso()
            observed = (lead.get("source_observed_at") or "").strip()
            if observed and lead.get("first_human_touch_at") is None:
                try:
                    touch_dt = spine._parse_ts(touch_ts)
                    observed_dt = spine._parse_ts(observed)
                except (TypeError, ValueError) as exc:
                    raise MgmtClusterError(
                        "unparseable touch chronology",
                        code="invalid_chronology",
                    ) from exc
                if touch_dt < observed_dt:
                    raise MgmtClusterError(
                        "touched_at before source_observed_at",
                        code="invalid_chronology",
                    )
                c.execute(
                    "UPDATE core_leads SET first_human_touch_at=? WHERE lead_id=?",
                    (touch_ts, key),
                )
                spine.append_event(
                    key,
                    "human_touch_recorded",
                    payload={"touched_at": touch_ts, "person_id": pid},
                    actor_type="PERSON",
                    actor_person_id=pid,
                    verified_person_id=pid,
                    occurred_at=touch_ts,
                    require_perm=False,
                    conn=c,
                )
            event = spine.append_event(
                key,
                "ownership_touch_recorded",
                payload={
                    "note": text or None,
                    "touched_at": touch_ts,
                    "person_id": pid,
                    "external_crm_write": False,
                    "operator_depth": True,
                    "crm_operator_depth": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "handover_touch":
            event = spine.append_event(
                key,
                "handover_touch_recorded",
                payload={
                    "note": text,
                    "person_id": pid,
                    "external_crm_write": False,
                    "operator_depth": True,
                    "crm_operator_depth": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "dismiss_noise":
            if not text:
                text = "Dismissed as noise — Beta CRM operator path only."
            event = spine.append_event(
                key,
                "dismiss_noise_recorded",
                payload={
                    "note": text,
                    "person_id": pid,
                    "external_crm_write": False,
                    "operator_depth": True,
                    "crm_operator_depth": True,
                    "stage_unchanged": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )

        after = spine.get_lead(key, conn=c) or lead
        if after.get("source_stage") != before_source:
            raise MgmtClusterError("source_stage mutated", code="append_only_violation")
        card = pack.operator_card(after, conn=c)
        spine_c = lead_spine_consequence(c)
        desk = ggv_desk_next_action_consequence(c)
        owner = owner_attention_consequence(c)
        staff = staff_attention_consequence(c)
        if commit:
            c.commit()
        return {
            "ok": True,
            "action": "crm_lead_operator",
            "kind": k,
            "seat": seat,
            "lead": card,
            "event": event,
            "lead_spine": spine_c,
            "ggv_desk_next_action": desk,
            "owner_attention": owner,
            "staff_attention": staff,
            "loop": card.get("loop"),
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invented_leads": False,
            "live_habitat_commission": False,
            "closed_is_not_a_sale": True,
            "cr_resolved": False,
            "proven": False,
            "ready": False,
            "honesty": honesty_flags(),
        }
    except spine.LeadSpineError as exc:
        raise MgmtClusterError(str(exc), code=exc.code) from exc
    except pack.OpsPackError as exc:
        raise MgmtClusterError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def operator_depth_desk(
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """CRM operator depth desk: RBAC prove + lead candidates + consequence honesty."""
    pack = _ggv()
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (verified_person_id or "").strip() or AMANDA
        prove = prove_crm_operator(person_id=pid, conn=c)
        clock = now or datetime.now(timezone.utc)
        leads = pack._habitat_leads(c)
        candidates = []
        for lead in leads:
            lid = str(lead.get("lead_id") or "")
            if _lead_has_event(c, lid, "dismiss_noise_recorded"):
                continue
            card = pack.operator_card(lead, conn=c, now=clock)
            wolf = str(card.get("wolf_lifecycle") or "").upper()
            if wolf in ("PARKED", "CLOSED"):
                continue
            candidates.append(
                {
                    "lead_id": card.get("lead_id"),
                    "demo_label": card.get("demo_label"),
                    "wolf_lifecycle": wolf,
                    "owner": card.get("owner"),
                    "recorded_next_action": card.get("recorded_next_action"),
                    "loop_next_action": card.get("loop_next_action"),
                    "speed": card.get("speed"),
                    "href": crm_lead_operator_href(lid),
                }
            )
        spine_c = lead_spine_consequence(c, now=clock)
        desk = ggv_desk_next_action_consequence(c, now=clock)
        owner = owner_attention_consequence(c, now=clock)
        staff = staff_attention_consequence(c, now=clock)
        empty = len(candidates) == 0 and spine_c.get("empty") is True
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "rbac": prove,
            "lead_candidates": candidates[:20],
            "lead_candidate_count": len(candidates),
            "lead_spine": spine_c,
            "ggv_desk_next_action": desk,
            "owner_attention": owner,
            "staff_attention": staff,
            "target_crs": [CR_01],
            "invented_leads": False,
            "empty": empty,
            "empty_message": (
                "No Habitat leads for CRM operator depth — EMPTY (not invent)."
                if empty
                else None
            ),
            "live_habitat_commission": False,
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "why": (
                "CRM lead operator depth: Habitat lead detail/action path + note/"
                "next-action/ownership/handover/dismiss-noise recording that refreshes "
                "Lead Spine, GGV desk next-action, and Owner/staff attention strips. "
                "No invent leads. No external CRM/Metricool/Klaviyo write. "
                "No live Habitat seat commissioning on this path."
            ),
            "honesty": honesty_flags(),
        }
    finally:
        if own:
            c.close()
