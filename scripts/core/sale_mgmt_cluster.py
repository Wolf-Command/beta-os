#!/usr/bin/env python3
"""SALE Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-SALE-CLUSTER-2026-09-22.md
+ Sprint2 continuous pack gen / Owner compressed sprint
+ Sprint2 P10 SALE Operator Depth
(docs/deliveries/GROK-PLAN-SPRINT2-P10-SALE-OPERATOR-DEPTH-2026-09-22.md).

Composes existing Sale modules (Continuous Sale Evidence Pack, Buyer Data
Room, Buyer Mode / Controlled Export, Buyer Attack & Transition Readiness)
into one phone-first Owner operating loop with honesty EMPTY/UNWIRED/
WAITING_DATA strips and derived next actions.

Sprint2 P10 adds operator depth: evidence / buyer-mode / attack-audit detail
+ note / next-action-touch / evidence-touch / handover-touch / dismiss-noise
recording that refreshes SALE desk next-action + Owner Empire / Sale
Readiness strips. Never buyer-grant / live-attack / export.

Bound beta-connective-safe.

Additive compose + operator depth. Does not invent live buyer grant / filled
transition pack / live attack run / PROVEN/READY/COMMISSIONED/ADOPTED. Does
not resolve CRs. Does not raise CAP maturity (CAP-SALE-01…04 stay SPECIFIED).
No Production/CF/Access-mutate/secret-exfil/external-write/money. No
P1/P7/Devi/w12 FIN/parked GGV/INTG/P9 reopen. Does not reopen DONE
BZG/AMG/INTEL/CORE/CRM/MSC/STRAT/DR. Does not touch WIP quartet. CRs stay OPEN.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import sale_attack_audit as attack
from core import sale_buyer_dataroom as dataroom
from core import sale_buyer_mode as buyer_mode
from core import sale_evidence_pack as evidence
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
DEFAULT_OPERATOR_DB = BETA_ROOT / "catalog" / "sale_mgmt_operator.sqlite"
LIVE_OPERATOR_DB = DEFAULT_OPERATOR_DB.resolve()

BOUND = "beta-connective-safe"
SCHEMA_ID = "wolf.sale-mgmt-cluster.v1"
SLICE = "sale_mgmt_cluster_v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.sale-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "sale_operator_depth"
OWNER = "PERS-MATT"

PERM_SALE_OPERATOR = "sale.operator"
PERM_SALE_OPERATOR_ID = "PERM-SALE-OPERATOR"
SCOPE_SALE_OPERATOR = "SCOPE-SALE-OPERATOR"
ROLE_SALE_OPERATORS: tuple[str, ...] = ("ROLE-MATT",)
ASG_SALE_MATT = "ASG-MATT-OWNER-1"
ENTITY_SALE = "ENT-GGV"  # Owner fixture entity (same as POS-OWNER-EXEC-1)

DEPTH_MODULE_IDS: tuple[str, ...] = (
    "sale_evidence_pack",
    "sale_buyer_mode",
    "sale_attack_audit",
)
SALE_OPERATOR_ACTION_KINDS = frozenset(
    {
        "note",
        "next_action",
        "evidence_touch",
        "handover_touch",
        "dismiss_noise",
    }
)
_ACTION_KIND_ALIASES = {
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "evidence-touch": "evidence_touch",
    "evidence_touch": "evidence_touch",
    "handover-touch": "handover_touch",
    "handover_touch": "handover_touch",
    "dismiss": "dismiss_noise",
    "dismiss-noise": "dismiss_noise",
    "dismiss_noise": "dismiss_noise",
    "note": "note",
}
OPERATOR_DISPOSITIONS = frozenset({"open", "dismissed"})

OPERATOR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sale_operator_state (
  object_id TEXT PRIMARY KEY,
  module_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  disposition TEXT NOT NULL DEFAULT 'open',
  note TEXT,
  next_action TEXT,
  last_kind TEXT,
  updated_by TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sale_operator_events (
  event_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  module_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  note TEXT,
  disposition_before TEXT,
  disposition_after TEXT,
  actor_person_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sale_op_events_obj
  ON sale_operator_events(object_id, recorded_at DESC);
"""

CAP_01 = evidence.CAP_ID  # CAP-SALE-01
CAP_02 = dataroom.CAP_ID  # CAP-SALE-02
CAP_03 = buyer_mode.CAP_ID  # CAP-SALE-03
CAP_04 = attack.CAP_ID  # CAP-SALE-04
CR_01 = evidence.CR_ID  # CR-b7ce6d6668848b6e
CR_02 = dataroom.CR_ID  # CR-766f242208e401ad
CR_03 = buyer_mode.CR_ID  # CR-b428ac5cbc8986b5
CR_04 = attack.CR_ID  # CR-c6e1a48e4a3e8a91

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "sale_evidence_pack",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "Continuous Sale Evidence Pack",
        "staff_title": "Evidence pack",
        "href": "/sale-evidence-pack",
        "kind": "evidence",
        "empty_message": (
            "Sale evidence pack controls are empty or unwired. "
            "Empty is not filled evidence and not CAP-SALE-01 PROVEN."
        ),
        "waiting_message": (
            "Sale evidence domains and controls are named. Naming is not "
            "filled evidence, not a buyer VDR export, and not CAP-SALE-01 "
            "PROVEN or READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Sale evidence pack was not read. UNWIRED. No filled evidence "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Sale Evidence Pack desk",
        "next_code": "open_sale_evidence_pack",
    },
    {
        "id": "sale_buyer_dataroom",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Buyer Data Room",
        "staff_title": "Buyer data room",
        "href": "/buyer-dataroom",
        "kind": "dataroom",
        "empty_message": (
            "Buyer data room folders are empty or unwired. "
            "Empty is not a live VDR share and not CAP-SALE-02 PROVEN."
        ),
        "waiting_message": (
            "Buyer data room folders and checklist are named. Naming is not "
            "buyer access, not a live share, and not CAP-SALE-02 PROVEN or "
            "READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Buyer data room was not read. UNWIRED. No buyer grant invented. "
            "Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Buyer Data Room desk",
        "next_code": "open_buyer_dataroom",
    },
    {
        "id": "sale_buyer_mode",
        "cap": CAP_03,
        "cr": CR_03,
        "title": "Buyer Mode / Controlled Export",
        "staff_title": "Buyer mode",
        "href": "/buyer-mode",
        "kind": "buyer_mode",
        "empty_message": (
            "Buyer mode surfaces are empty or unwired. "
            "Empty is not a controlled export and not CAP-SALE-03 PROVEN."
        ),
        "waiting_message": (
            "Buyer mode diligence surfaces are named. Naming is not a buyer "
            "grant, not a controlled export of real data, and not CAP-SALE-03 "
            "PROVEN or READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Buyer mode was not read. UNWIRED. No buyer grant or export "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Buyer Mode desk",
        "next_code": "open_buyer_mode",
    },
    {
        "id": "sale_attack_audit",
        "cap": CAP_04,
        "cr": CR_04,
        "title": "Buyer Attack & Transition Readiness",
        "staff_title": "Attack audit",
        "href": "/attack-audit",
        "kind": "attack",
        "empty_message": (
            "Attack audit sections are empty or unwired. "
            "Empty is not a live attack and not CAP-SALE-04 PROVEN."
        ),
        "waiting_message": (
            "Attack audit sections and transition-pack slots are named. "
            "Naming is not a live attack run, not a filled transition pack, "
            "and not CAP-SALE-04 PROVEN or READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Attack audit was not read. UNWIRED. No live attack or filled "
            "transition pack invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Attack Audit desk",
        "next_code": "open_attack_audit",
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
    "operator_depth": True,
    "empty_operator_is_not_invent": True,
    "invented_proven": False,
    "invented_ready": False,
    "invented_commissioned": False,
    "invented_adopted": False,
    "invented_buyer_grant": False,
    "invented_live_attack": False,
    "invented_transition_pack": False,
    "invented_controlled_export": False,
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
    "finance_controls": False,
    "hr": False,
    "trading": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "buyer_grant": False,
    "live_attack": False,
    "attack_run": False,
    "transition_pack_filled": False,
    "controlled_export": False,
    "export_written": False,
    "commission_flip": False,
    "secret_exfil": False,
    "external_write": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "p9_reopened": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "ggv_reopened": False,
    "intg_reopened": False,
    "bzg_reopened": False,
    "amg_reopened": False,
    "intel_reopened": False,
    "core_reopened": False,
    "crm_reopened": False,
    "msc_reopened": False,
    "strat_reopened": False,
    "dr_reopened": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "sale_caps_unchanged": True,
    "cf_seat_mint": False,
    "live_habitat_commission": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent SALE management facts or maturity."""

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
        "depth_modules": list(DEPTH_MODULE_IDS),
        "sale_operator_action_kinds": sorted(SALE_OPERATOR_ACTION_KINDS),
        "writes_accepted": False,
        "operator_actions_accepted": True,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "commission_flip_property": False,
        "secret_exfil_property": False,
        "external_write_property": False,
        "cloudflare_mutate_property": False,
        "access_mutate_property": False,
        "buyer_grant_property": False,
        "live_attack_property": False,
        "export_mutate_property": False,
        "transition_pack_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_secret_exfil(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses secret exfiltration / mint / store.",
        code="secret_exfil_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_buyer_grant(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses inventing live buyer grant / access.",
        code="buyer_grant_refused",
    )


def refuse_live_attack(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses inventing live attack run.",
        code="live_attack_refused",
    )


def refuse_export(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "SALE Management Cluster refuses export mutate / controlled export of real data.",
        code="export_refused",
    )


def refuse_code(path: str) -> str | None:
    """Map refuse path tails to refuse codes for serve_beta.

    Operator-depth / operator-action paths are not refused here — they are
    authorised Beta SALE operator writes (no buyer-grant / live-attack / export).
    """
    parts = [p for p in path.rstrip("/").split("/") if p]
    if "operator-depth" in parts or "operator-action" in parts:
        return None
    if parts and parts[-1] == "operator" and "objects" in parts:
        return None
    if parts and parts[-1] == "rbac" and "operator-depth" in parts:
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
        "secret": "secret",
        "secrets": "secret",
        "exfil": "secret",
        "secret-exfil": "secret",
        "grant": "buyer_grant",
        "buyer-grant": "buyer_grant",
        "buyer": "buyer_grant",
        "attack": "live_attack",
        "live-attack": "live_attack",
        "run": "live_attack",
        "redteam": "live_attack",
        "export": "export",
        "export-mutate": "export",
        "download": "export",
        "vdr": "export",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
        "upload": "writes",
        "transition": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "SALE Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "SALE Management Cluster is Owner (PERS-MATT) only.",
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
        "SALE management cluster routing — Owner retain",
        has_staff_seat=False,
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
            "seat_hint": "Owner",
        },
    }


def _sale_framework_status(
    spec: dict[str, Any],
    pack: dict[str, Any] | None,
    *,
    named_count: int,
    empty_slots: int,
) -> tuple[str, list[str], bool, str, bool]:
    """Map SALE framework packs to EMPTY / UNWIRED / WAITING_DATA honesty."""
    if not isinstance(pack, dict) or pack.get("ok") is not True:
        return (
            "UNWIRED",
            ["EMPTY", "UNWIRED"],
            True,
            spec["unwired_message"],
            True,
        )
    if named_count <= 0:
        return (
            "EMPTY",
            ["EMPTY"],
            True,
            spec["empty_message"],
            False,
        )
    # Named skeleton with empty slots — waiting for real evidence, not PROVEN.
    if empty_slots >= 0:
        return (
            "WAITING_DATA",
            ["WAITING_DATA"],
            False,
            spec["waiting_message"],
            False,
        )
    return (
        "UNWIRED",
        ["EMPTY", "UNWIRED"],
        True,
        spec["unwired_message"],
        True,
    )


def _evidence_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = evidence.build_pack(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = int((pack or {}).get("controls_read") or (pack or {}).get("control_count") or 0)
    empty_slots = int((pack or {}).get("empty_slots") or 0)
    status, tags, empty, message, unwired = _sale_framework_status(
        spec, pack, named_count=named, empty_slots=empty_slots
    )
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
    strip["buyer_grant"] = False
    strip["live_attack"] = False
    strip["controlled_export"] = False
    strip["vdr_export"] = False
    strip["evidence_invented"] = False
    strip["filled_slots"] = 0
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "buyer_grant": False,
            "controlled_export": False,
            "evidence_invented": False,
            "numbers": None,
            "money": None,
        },
    }


def _dataroom_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = dataroom.build_room(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = int((pack or {}).get("slots_read") or (pack or {}).get("slot_count") or 0)
    empty_slots = int((pack or {}).get("empty_slots") or 0)
    status, tags, empty, message, unwired = _sale_framework_status(
        spec, pack, named_count=named, empty_slots=empty_slots
    )
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
    strip["buyer_grant"] = False
    strip["buyer_access"] = False
    strip["live_share"] = False
    strip["vdr_share"] = False
    strip["document_count"] = None
    strip["documents_invented"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "buyer_grant": False,
            "buyer_access": False,
            "live_share": False,
            "document_count": None,
            "numbers": None,
            "money": None,
        },
    }


def _buyer_mode_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = buyer_mode.build_mode(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = int((pack or {}).get("controls_read") or (pack or {}).get("approved_count") or 0)
    empty_slots = int((pack or {}).get("empty_exports") or 0)
    status, tags, empty, message, unwired = _sale_framework_status(
        spec, pack, named_count=named, empty_slots=empty_slots
    )
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
    strip["buyer_grant"] = False
    strip["controlled_export"] = False
    strip["export_written"] = False
    strip["crown_jewels_opened"] = False
    strip["filled_exports"] = 0
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "buyer_grant": False,
            "controlled_export": False,
            "export_written": False,
            "numbers": None,
            "money": None,
        },
    }


def _attack_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = attack.build_audit(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = int((pack or {}).get("controls_read") or (pack or {}).get("section_count") or 0)
    empty_slots = int((pack or {}).get("empty_packs") or 0)
    status, tags, empty, message, unwired = _sale_framework_status(
        spec, pack, named_count=named, empty_slots=empty_slots
    )
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
    strip["buyer_grant"] = False
    strip["live_attack"] = False
    strip["attack_run"] = False
    strip["transition_pack_filled"] = False
    strip["transition_pack_written"] = False
    strip["licence_granted"] = False
    strip["filled_packs"] = 0
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "buyer_grant": False,
            "live_attack": False,
            "transition_pack_filled": False,
            "numbers": None,
            "money": None,
        },
    }


def _module_card(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    kind = spec["kind"]
    if kind == "evidence":
        return _evidence_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "dataroom":
        return _dataroom_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "buyer_mode":
        return _buyer_mode_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "attack":
        return _attack_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "needs-you", "label": "Needs-You", "href": "#needs-you-connective"},
        {"id": "operator-depth", "label": "Depth", "href": "#operator-depth"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "evidence", "label": "Evidence", "href": "/sale-evidence-pack"},
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
            "label": "No further SALE management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "sale_mgmt",
        "lede": (
            "Sale management cluster — evidence pack, buyer data room, "
            "buyer mode, attack audit. Empty stays empty. No invented buyer "
            "grant, live attack, or controlled export."
        ),
        "who_line": f"Signed in as {who.get('label') or 'Owner'}",
        "primary_next": primary,
        "nav": phone_nav(),
        "empty_module_count": len(empties),
        "exposed_actions": {
            "show_owner_copy": who.get("seat") == "owner",
            "show_operator_actions": who.get("seat") == "owner",
            "payment_on_screen": False,
            "show_seats_panel": False,
            "cloudflare_mutate": False,
            "secret_exfil": False,
            "buyer_grant": False,
            "live_attack": False,
            "export_mutate": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": "Management cluster is compose-only; history lives on each SALE desk.",
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
) -> dict[str, Any]:
    """Compose one Owner-facing SALE management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("SALE", empty_count)
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

    cap_rows: dict[str, dict[str, Any]] = {}
    for m in modules:
        cap = m["cap"]
        if cap not in cap_rows:
            cap_rows[cap] = {
                "maturity": m["ledger_maturity"],
                "cr": m["cr"],
                "cr_state": m["cr_state"],
                "raised": False,
            }

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
            "pack": "SALE",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: SALE loop attention stays Owner — "
                "labels only, Owner desk not removed. No secret exfil. "
                "No buyer grant. No live attack."
            ),
        },
        "caps": cap_rows,
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
        "secret_exfil": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "buyer_grant": False,
        "live_attack": False,
        "attack_run": False,
        "transition_pack_filled": False,
        "controlled_export": False,
        "export_written": False,
        "invented_buyer_grant": False,
        "invented_live_attack": False,
        "invented_transition_pack": False,
        "invented_controlled_export": False,
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import sale_ops_needs_you_connective as sale_nye

    sale_nye._attach_needs_you_connective(
        desk, person_id=seat.get("person_id"), catalog_db=catalog_db, ledger_path=ledger_path
    )
    return desk


def module_strip(
    module_id: str,
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    _ = seat
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
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


# ---------------------------------------------------------------------------
# Sprint2 P10 — SALE operator depth (evidence / buyer-mode / attack-audit)
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _under_test_process() -> bool:
    return (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1"


def assert_catalog_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = Path(path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise MgmtClusterError(
            "test mode refuses writes to live catalog DB; point catalog at a temp copy",
            code="live_write_refused",
        )


def assert_operator_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    resolved = Path(path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_OPERATOR_DB and _under_test_process():
        raise MgmtClusterError(
            "test mode refuses writes to live SALE operator DB; point operator_db at a temp copy",
            code="live_write_refused",
        )


def _assert_beta_path(path: Path) -> Path:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    try:
        resolved.relative_to(BETA_ROOT)
        return resolved
    except ValueError:
        pass
    tmp = Path(os.environ.get("TMPDIR") or "/tmp").resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise MgmtClusterError(
            "SALE operator depth refuses a path outside Beta or a test fixture.",
            code="not_beta",
        ) from exc
    return resolved


def operator_db_path(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return _assert_beta_path(resolved)


def ensure_operator_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(OPERATOR_SCHEMA_SQL)
    conn.commit()


def _open_catalog(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _open_operator(
    db_path: Path | str | None = None, *, write: bool = True
) -> tuple[sqlite3.Connection, Path]:
    path = operator_db_path(db_path)
    if write:
        assert_operator_writable(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    if not path.is_file():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn, path


def _normalise_action_kind(kind: str | None) -> str:
    raw = (kind or "").strip().lower()
    return _ACTION_KIND_ALIASES.get(raw, raw)


def _depth_spec(object_id: str) -> dict[str, Any]:
    key = (object_id or "").strip()
    for spec in MODULE_SPECS:
        if spec["id"] == key and key in DEPTH_MODULE_IDS:
            return spec
    raise MgmtClusterError(
        f"Unknown SALE depth object {object_id!r} "
        f"(allowed: {', '.join(DEPTH_MODULE_IDS)})",
        code="not_found",
    )


def sale_object_operator_href(object_id: str | None) -> str:
    key = (object_id or "").strip()
    if not key:
        return "/sale-mgmt-cluster#operator-depth"
    return f"/sale-mgmt-cluster#sale-obj-{key}"


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
    """Idempotent grant: sale.operator on ROLE-MATT + Owner fixture scope.

    Beta catalog only. Does not mint CF Access seats. Owner fixture only.
    """
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ts = _now_utc_iso()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_SALE_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_SALE_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_SALE_OPERATOR,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='entity' AND target_id=?
                """,
                (SCOPE_SALE_OPERATOR, ENTITY_SALE),
            ).fetchone()
        )
        roles_ok = all(_role_has_perm(c, role_id, op_id) for role_id in ROLE_SALE_OPERATORS)
        asg = c.execute(
            """
            SELECT a.assignment_id, a.status, a.end_at
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.assignment_id=? AND a.person_id=? AND po.role_id=?
            """,
            (ASG_SALE_MATT, OWNER, ROLE_SALE_OPERATORS[0]),
        ).fetchone()
        asg_active = bool(
            asg and str(asg["status"] or "") == "ACTIVE" and asg["end_at"] is None
        )
        scope_linked = bool(
            asg_active
            and c.execute(
                """
                SELECT 1 FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=?
                """,
                (ASG_SALE_MATT, SCOPE_SALE_OPERATOR),
            ).fetchone()
        )

        already = (
            bool(existing)
            and str(existing["status"] or "") == "ACTIVE"
            and bool(scope_row)
            and str(scope_row["status"] or "") == "ACTIVE"
            and target_ok
            and roles_ok
            and scope_linked
        )
        if already:
            return {
                "ok": True,
                "grants": [PERM_SALE_OPERATOR],
                "roles": list(ROLE_SALE_OPERATORS),
                "permission_ids": {PERM_SALE_OPERATOR: op_id},
                "scope_id": SCOPE_SALE_OPERATOR,
                "unchanged": True,
                "cf_seat_mint": False,
                "bound": BOUND,
            }

        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        assert_catalog_writable(db_file)

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'sale', 'operator',
              'SALE evidence/buyer-mode/attack-audit operator detail + note/next/evidence/handover/dismiss (no buyer-grant/live-attack/export)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_SALE_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_SALE_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'entity', 'SALE Owner operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_SALE_OPERATOR, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'entity', ?, ?)
            """,
            (SCOPE_SALE_OPERATOR, ENTITY_SALE, ts),
        )
        for role_id in ROLE_SALE_OPERATORS:
            role = c.execute(
                "SELECT role_id, status FROM org_roles WHERE role_id=?",
                (role_id,),
            ).fetchone()
            if not role:
                raise MgmtClusterError(
                    f"{role_id} missing — Owner role required",
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
        if not asg_active:
            raise MgmtClusterError(
                f"fixture assignment missing for {OWNER}",
                code="assignment_missing",
            )
        c.execute(
            """
            INSERT OR IGNORE INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
            """,
            (ASG_SALE_MATT, SCOPE_SALE_OPERATOR, ts, ts, ts),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_SALE_OPERATOR],
            "roles": list(ROLE_SALE_OPERATORS),
            "permission_ids": {PERM_SALE_OPERATOR: op_id},
            "scope_id": SCOPE_SALE_OPERATOR,
            "unchanged": False,
            "cf_seat_mint": False,
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def prove_sale_operator(
    *,
    person_id: str = OWNER,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove PERS-MATT can run SALE operator actions."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip() or OWNER
        try:
            seat = require_actor(pid)
        except MgmtClusterError:
            seat = None
        target = {"entity_id": ENTITY_SALE}
        can_operator = bool(_rbac.can(pid, PERM_SALE_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id=?
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, ROLE_SALE_OPERATORS[0]),
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
            "can_sale_operator": allowed,
            "pack_seat": pack_seat,
            "actions": {
                "sale_operator": allowed and pack_seat,
                "note": allowed and pack_seat,
                "next_action": allowed and pack_seat,
                "evidence_touch": allowed and pack_seat,
                "handover_touch": allowed and pack_seat,
                "dismiss_noise": allowed and pack_seat,
                "buyer_grant": False,
                "live_attack": False,
                "export": False,
                "export_to_buyer": False,
            },
            "cf_seat_mint": False,
            "live_habitat_commission": False,
            "target_crs": [CR_01, CR_02, CR_03, CR_04],
            "proven": False,
            "ready": False,
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
        }
    finally:
        if own:
            c.close()


def _require_sale_operator(
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
    target = {"entity_id": ENTITY_SALE}
    if not _rbac.can(pid, PERM_SALE_OPERATOR, target, conn=conn):
        raise MgmtClusterError(
            f"permission denied: {PERM_SALE_OPERATOR}",
            code="forbidden",
        )
    return seat


def _load_operator_state(
    object_id: str,
    *,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        row = conn.execute(
            """
            SELECT object_id, module_id, kind, disposition, note, next_action,
                   last_kind, updated_by, updated_at, created_at
            FROM sale_operator_state
            WHERE object_id=?
            """,
            (object_id,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()
    if row is None:
        return {
            "object_id": object_id,
            "disposition": "open",
            "note": None,
            "next_action": None,
            "last_kind": None,
            "updated_by": None,
            "updated_at": None,
            "empty": True,
        }
    return {
        "object_id": row["object_id"],
        "module_id": row["module_id"],
        "kind": row["kind"],
        "disposition": str(row["disposition"] or "open"),
        "note": row["note"],
        "next_action": row["next_action"],
        "last_kind": row["last_kind"],
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
        "empty": False,
    }


def list_sale_operator_actions(
    object_id: str,
    *,
    operator_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        rows = conn.execute(
            """
            SELECT event_id, object_id, module_id, kind, note,
                   disposition_before, disposition_after, actor_person_id,
                   recorded_at, payload_json
            FROM sale_operator_events
            WHERE object_id=?
            ORDER BY recorded_at DESC
            LIMIT 40
            """,
            (object_id,),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        out.append(
            {
                "event_id": r["event_id"],
                "kind": r["kind"],
                "note": r["note"],
                "disposition_before": r["disposition_before"],
                "disposition_after": r["disposition_after"],
                "created_by": r["actor_person_id"],
                "created_at": r["recorded_at"],
                "payload": payload,
                "buyer_grant": False,
                "live_attack": False,
                "export": False,
                "invented": False,
            }
        )
    return out


def operator_object_card(
    object_id: str,
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    spec = _depth_spec(object_id)
    base = _module_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    state = _load_operator_state(object_id, operator_db=operator_db)
    prior = events if events is not None else list_sale_operator_actions(
        object_id, operator_db=operator_db
    )
    dismissed = state.get("disposition") == "dismissed"
    recorded_next = state.get("next_action")
    primary = base.get("primary_next") or {}
    if recorded_next and not dismissed:
        primary = {
            "code": "operator_next_action",
            "label": recorded_next,
            "href": sale_object_operator_href(object_id),
            "invented": False,
            "operator_recorded": True,
        }
    return {
        "object_id": object_id,
        "module_id": spec["id"],
        "kind": spec["kind"],
        "title": spec["title"],
        "staff_title": spec["staff_title"],
        "cap": spec["cap"],
        "cr": spec["cr"],
        "ledger_maturity": base.get("ledger_maturity"),
        "cr_state": base.get("cr_state"),
        "honesty_strip": base.get("honesty_strip"),
        "disposition": state.get("disposition") or "open",
        "note": state.get("note"),
        "recorded_next_action": recorded_next,
        "last_kind": state.get("last_kind"),
        "primary_next": primary,
        "operator_action_count": len(prior or []),
        "dismissed": dismissed,
        "href": sale_object_operator_href(object_id),
        "buyer_grant": False,
        "live_attack": False,
        "export": False,
        "invented": False,
        "proven": False,
        "ready": False,
    }


def sale_desk_next_action_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Refreshed SALE desk next-action after operator recording. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        if card.get("dismissed"):
            continue
        nxt = card.get("primary_next") or {}
        row = {
            "object_id": mid,
            "label": nxt.get("label") or card.get("staff_title"),
            "href": card.get("href"),
            "last_kind": card.get("last_kind"),
            "recorded_next_action": card.get("recorded_next_action"),
            "invented": False,
        }
        items.append(row)
        if primary is None and nxt.get("label"):
            primary = {
                "code": nxt.get("code") or "sale_operator_next",
                "label": nxt.get("label"),
                "href": nxt.get("href") or card.get("href"),
                "invented": False,
                "object_id": mid,
            }
    empty = primary is None
    if empty:
        primary = {
            "code": "none",
            "label": "No SALE operator next action — EMPTY (not invent).",
            "href": "/sale-mgmt-cluster#operator-depth",
            "invented": False,
        }
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": 0 if empty else len(items),
        "items": items,
        "next_action": primary,
        "empty_message": (
            "No SALE evidence/buyer-mode/attack-audit next action — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "buyer_grant": False,
        "live_attack": False,
        "export": False,
        "why": (
            "SALE desk next-action is a projection of open operator depth objects "
            "(dismiss-noise drops off). Recording refreshes this strip."
        ),
    }


def owner_empire_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner Empire attention strip from SALE operator work. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        if card.get("dismissed"):
            continue
        last = card.get("last_kind")
        if not last:
            # No operator engagement yet — EMPTY honesty, not invent attention.
            continue
        reasons: list[str] = []
        if last == "handover_touch":
            reasons.append("handover_touch")
        if last in ("note", "evidence_touch") and not card.get("recorded_next_action"):
            reasons.append("missing_next_action")
        if card.get("kind") == "evidence" and last != "evidence_touch":
            reasons.append("evidence_needs_touch")
        if not reasons:
            continue
        items.append(
            {
                "object_id": mid,
                "staff_title": card.get("staff_title"),
                "reasons": reasons,
                "last_kind": last,
                "href": card.get("href"),
                "invented": False,
            }
        )
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "pack": "SALE",
        "empty": empty,
        "count": 0 if empty else len(items),
        "attention_count": None if empty else len(items),
        "items": items,
        "empty_message": (
            "No SALE objects need Owner Empire attention — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "buyer_grant": False,
        "live_attack": False,
        "export": False,
        "why": (
            "Owner Empire SALE strip projects handover / missing next / evidence-touch "
            "needs from operator depth. Dismiss-noise drops off. Not a CAP maturity invent."
        ),
    }


def sale_readiness_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Sale Readiness projection strip from operator evidence/readiness work.

    EMPTY honesty. Does not invent CSV rows or raise CAP maturity.
    """
    items: list[dict[str, Any]] = []
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        if card.get("dismissed"):
            continue
        last = card.get("last_kind")
        if last not in ("evidence_touch", "next_action", "note", "handover_touch"):
            continue
        if last is None:
            continue
        items.append(
            {
                "object_id": mid,
                "cap": card.get("cap"),
                "staff_title": card.get("staff_title"),
                "last_kind": last,
                "ledger_maturity": card.get("ledger_maturity"),
                "cr_state": card.get("cr_state"),
                "href": card.get("href"),
                "source_kind": "sale_operator_depth",
                "lifecycle": "SPECIFIED",
                "invented": False,
                "raised_cap": False,
            }
        )
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "domain": "Sale Readiness",
        "empty": empty,
        "count": 0 if empty else len(items),
        "items": items,
        "empty_message": (
            "No Sale Readiness operator signals — EMPTY (not invent CSV or CAP raise)."
            if empty
            else None
        ),
        "invented": False,
        "caps_raised": False,
        "csv_mutated": False,
        "buyer_grant": False,
        "live_attack": False,
        "export": False,
        "why": (
            "Sale Readiness strip is a projection of SALE operator evidence/next/note/"
            "handover touches. Does not invent Sale_Readiness.csv rows or PROVEN/READY."
        ),
    }


def operator_object_detail(
    object_id: str,
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """SALE object operator detail/action path. No buyer-grant / live-attack / export."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        _depth_spec(object_id)
        pid = (verified_person_id or "").strip() or None
        actions = {
            "sale_operator": False,
            "note": False,
            "next_action": False,
            "evidence_touch": False,
            "handover_touch": False,
            "dismiss_noise": False,
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
        }
        if pid:
            try:
                require_actor(pid)
                prove = prove_sale_operator(person_id=pid, conn=catalog)
                actions.update(prove.get("actions") or {})
            except MgmtClusterError:
                pass
        prior = list_sale_operator_actions(object_id, operator_db=operator_db)
        card = operator_object_card(
            object_id,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            events=prior,
        )
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "object": card,
            "actions": actions,
            "operator_actions": prior,
            "href": card["href"],
            "sale_desk_next_action": sale_desk_next_action_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
            ),
            "owner_empire": owner_empire_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
            ),
            "sale_readiness": sale_readiness_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
            ),
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()


def record_sale_operator_action(
    *,
    verified_person_id: str,
    object_id: str,
    kind: str,
    note: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record note / next-action / evidence / handover / dismiss. Refresh strips.

    Never buyer-grant / live-attack / export-to-buyer. Never invent PROVEN/READY.
    """
    k = _normalise_action_kind(kind)
    if k not in SALE_OPERATOR_ACTION_KINDS:
        raise MgmtClusterError(
            f"kind must be one of {sorted(SALE_OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "verified_person_id required", code="missing_verified_person"
        )
    key = (object_id or "").strip()
    if not key:
        raise MgmtClusterError("object_id required", code="missing_object")
    if k in ("note", "next_action", "evidence_touch", "handover_touch") and not text:
        raise MgmtClusterError(f"{k} note required", code="missing_note")
    if text and len(text) > 2000:
        raise MgmtClusterError("note too long", code="invalid")

    spec = _depth_spec(key)
    catalog = _open_catalog(catalog_db)
    op_conn, op_path = _open_operator(operator_db, write=True)
    try:
        assert_catalog_writable(
            Path(catalog.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        )
        seat = _require_sale_operator(catalog, verified_person_id=pid)
        before = _load_operator_state(key, operator_db=op_path)
        before_disp = str(before.get("disposition") or "open")
        stamp = _now_utc_iso()
        new_disp = before_disp
        new_note = str(before.get("note") or "")
        new_next = before.get("next_action")
        event_note: str | None = text or None

        if k == "note":
            new_note = text
        elif k == "next_action":
            new_next = text
            new_note = text if not new_note else new_note
        elif k == "evidence_touch":
            new_note = text
        elif k == "handover_touch":
            new_note = text
        elif k == "dismiss_noise":
            new_disp = "dismissed"
            if text:
                new_note = text
            elif not event_note:
                event_note = "Dismissed noise by operator."

        created_at = before.get("created_at") or stamp
        op_conn.execute(
            """
            INSERT INTO sale_operator_state (
              object_id, module_id, kind, disposition, note, next_action,
              last_kind, updated_by, updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              disposition=excluded.disposition,
              note=excluded.note,
              next_action=excluded.next_action,
              last_kind=excluded.last_kind,
              updated_by=excluded.updated_by,
              updated_at=excluded.updated_at
            """,
            (
                key,
                spec["id"],
                spec["kind"],
                new_disp,
                new_note or None,
                new_next,
                k,
                seat["person_id"],
                stamp,
                created_at,
            ),
        )
        event_id = "SEV-" + uuid.uuid4().hex[:12]
        payload = {
            "operator_depth": True,
            "sale_operator_depth": True,
            "kind": k,
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
            "invented": False,
        }
        op_conn.execute(
            """
            INSERT INTO sale_operator_events (
              event_id, object_id, module_id, kind, note,
              disposition_before, disposition_after, actor_person_id,
              recorded_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                key,
                spec["id"],
                k,
                event_note,
                before_disp,
                new_disp,
                seat["person_id"],
                stamp,
                json.dumps(payload, separators=(",", ":")),
            ),
        )
        if commit:
            op_conn.commit()
            catalog.commit()

        desk = sale_desk_next_action_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
        )
        empire = owner_empire_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
        )
        readiness = sale_readiness_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
        )
        prior = list_sale_operator_actions(key, operator_db=op_path)
        card = operator_object_card(
            key,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
            events=prior,
        )
        return {
            "ok": True,
            "action": "sale_operator",
            "kind": k,
            "seat": seat,
            "object": card,
            "event": {
                "event_id": event_id,
                "kind": k,
                "note": event_note,
                "disposition_before": before_disp,
                "disposition_after": new_disp,
                "actor_person_id": seat["person_id"],
                "recorded_at": stamp,
            },
            "sale_desk_next_action": desk,
            "owner_empire": empire,
            "sale_readiness": readiness,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    finally:
        op_conn.close()
        catalog.close()


def operator_depth_desk(
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """SALE operator depth desk: RBAC prove + depth candidates + consequence honesty."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        pid = (verified_person_id or "").strip() or OWNER
        seat = require_actor(pid)
        prove = prove_sale_operator(person_id=pid, conn=catalog)
        candidates: list[dict[str, Any]] = []
        for mid in DEPTH_MODULE_IDS:
            card = operator_object_card(
                mid,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
            )
            if card.get("dismissed"):
                continue
            candidates.append(card)
        desk = sale_desk_next_action_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        empire = owner_empire_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        readiness = sale_readiness_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        empty = len(candidates) == 0
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "seat": seat,
            "rbac": prove,
            "object_candidates": candidates,
            "sale_desk_next_action": desk,
            "owner_empire": empire,
            "sale_readiness": readiness,
            "empty": empty,
            "empty_message": (
                "No SALE evidence/buyer-mode/attack-audit objects for operator depth — "
                "EMPTY (not invent)."
                if empty
                else None
            ),
            "why": (
                "SALE operator depth: evidence / buyer-mode / attack-audit detail + "
                "note/next-action/evidence/handover/dismiss recording that refreshes "
                "SALE desk next-action and Owner Empire / Sale Readiness strips. "
                "No buyer-grant. No live-attack. No export."
            ),
            "buyer_grant": False,
            "live_attack": False,
            "export": False,
            "cf_seat_mint": False,
            "live_habitat_commission": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "target_crs": [CR_01, CR_03, CR_04],
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()
