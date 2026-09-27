#!/usr/bin/env python3
"""INTG Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-INTG-CLUSTER-V2-2026-09-22.md
+ Sprint2 continuous pack gen / Owner compressed sprint.

Composes existing INTG modules (Connector Contract, Connector Cap Tests,
Google Workspace prove, Tech/Capability Registry, Secrets & Env Separation)
into one phone-first Owner operating loop with honesty EMPTY/UNWIRED/
WAITING_DATA strips and derived next actions.

Bound beta-connective-safe.

Additive compose-only. Does not invent connector live facts / PROVEN /
READY / COMMISSIONED / ADOPTED. Does not resolve CRs. Does not raise CAP
maturity (CAP-INTG-01 stays ABSENT; 02–05 stay BUILT; 06–07 stay SPECIFIED).
No Production/CF/Access-mutate/secret-exfil/mint-secret/external-write/
bank-API/money. No P1/P7/Devi/w12 FIN/parked GGV reopen. Does not reopen
DONE BZG/AMG/INTEL/CORE/CRM/MSC/STRAT/DR/SALE. Does not touch WIP quartet.
CRs stay OPEN. ESB/Metricool strips are honesty-only pointers.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import gws_integrate_prove as gws
from core import intg_connector_cap_tests as cap_tests
from core import intg_connector_contract as contract
from core import intg_secrets_env as secrets
from core import staff_ready_ux as sru
from core import tech_capability_registry as tech

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-connective-safe"
SCHEMA_ID = "wolf.intg-mgmt-cluster.v1"
SLICE = "intg_mgmt_cluster_v2"
OWNER = "PERS-MATT"

CAP_01 = contract.CAP_ID  # CAP-INTG-01
CAP_02 = "CAP-INTG-02"
CAP_03 = gws.CAP_ID  # CAP-INTG-03
CAP_04 = cap_tests.CAP_ID  # CAP-INTG-04
CAP_05 = "CAP-INTG-05"
CAP_06 = tech.CAP_ID  # CAP-INTG-06
CAP_07 = secrets.CAP_ID  # CAP-INTG-07

CR_01 = contract.CR_ID  # CR-227e2514ac8dcd02
CR_02 = "CR-00b1a48e6620ec7f"
CR_03 = gws.CR_ID  # CR-260e724b776f2b89
CR_04 = cap_tests.CR_ID  # CR-859e7cad64e7e4ad
CR_05 = "CR-25e89e3efdb0caf9"
CR_06 = tech.CR_ID  # CR-44ffb6a57469ff25
CR_07 = secrets.CR_ID  # CR-273f30371bd52c8a

ALL_CAPS = (CAP_01, CAP_02, CAP_03, CAP_04, CAP_05, CAP_06, CAP_07)
ALL_CRS = (CR_01, CR_02, CR_03, CR_04, CR_05, CR_06, CR_07)

EXPECTED_MATURITY = {
    CAP_01: "ABSENT",
    CAP_02: "BUILT",
    CAP_03: "BUILT",
    CAP_04: "BUILT",
    CAP_05: "BUILT",
    CAP_06: "SPECIFIED",
    CAP_07: "SPECIFIED",
}

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "intg_connector_contract",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "Connector Contract",
        "staff_title": "Connector contract",
        "href": "/connector-contract",
        "kind": "contract",
        "empty_message": (
            "Yanolja connector contract is ABSENT / empty. "
            "Empty is not a live Yanolja connector and not CAP-INTG-01 PROVEN."
        ),
        "waiting_message": (
            "Connector contract slots are named. Naming is not a live Yanolja "
            "connector, not ESB, and not CAP-INTG-01 PROVEN or READY. "
            "CAP-INTG-01 stays ABSENT. CR stays OPEN."
        ),
        "unwired_message": (
            "Connector contract was not read. UNWIRED. No live connector "
            "invented. CAP-INTG-01 stays ABSENT. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Connector Contract desk",
        "next_code": "open_connector_contract",
    },
    {
        "id": "intg_connector_cap_tests",
        "cap": CAP_04,
        "cr": CR_04,
        "title": "Connector Cap Tests",
        "staff_title": "Connector cap tests",
        "href": "/connector-cap-tests",
        "kind": "cap_tests",
        "empty_message": (
            "Connector cap-test slots are empty or unwired. "
            "Empty is not a live bank connector and not CAP-INTG-04 PROVEN."
        ),
        "waiting_message": (
            "Connector cap-test slots are named. Naming is not a live bank API "
            "call, not a bank feed, and not CAP-INTG-04 PROVEN or READY. "
            "CR stays OPEN."
        ),
        "unwired_message": (
            "Connector cap tests were not read. UNWIRED. No bank API call "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Connector Cap Tests desk",
        "next_code": "open_connector_cap_tests",
    },
    {
        "id": "gws_integrate_prove",
        "cap": CAP_03,
        "cr": CR_03,
        "title": "Google Workspace Integrate Prove",
        "staff_title": "GWS prove",
        "href": "/gws-integrate-prove",
        "kind": "gws",
        "empty_message": (
            "GWS integrate prove checklist is empty or unwired. "
            "Empty is not a live Gmail/Calendar/Drive prove and not "
            "CAP-INTG-03 PROVEN."
        ),
        "waiting_message": (
            "GWS prove checklist and surfaces are named. Naming is not a live "
            "probe, not green health, and not CAP-INTG-03 PROVEN or READY. "
            "CR stays OPEN."
        ),
        "unwired_message": (
            "GWS integrate prove was not read. UNWIRED. No live GWS call "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open GWS Integrate Prove desk",
        "next_code": "open_gws_integrate_prove",
    },
    {
        "id": "tech_capability_registry",
        "cap": CAP_06,
        "cr": CR_06,
        "title": "Tech & Capability Registry",
        "staff_title": "Tech registry",
        "href": "/tech-registry",
        "kind": "tech",
        "empty_message": (
            "Tech / capability registry is empty or unwired. "
            "Empty is not an inventory prove and not CAP-INTG-06 PROVEN."
        ),
        "waiting_message": (
            "Tech registry entries are named. Naming is not green health, "
            "not PROVEN, and not CAP-INTG-06 READY. CAP-INTG-06 stays "
            "SPECIFIED. CR stays OPEN."
        ),
        "unwired_message": (
            "Tech capability registry was not read. UNWIRED. No green health "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Tech Registry desk",
        "next_code": "open_tech_registry",
    },
    {
        "id": "intg_secrets_env",
        "cap": CAP_07,
        "cr": CR_07,
        "title": "Secrets & Env Separation",
        "staff_title": "Secrets / env",
        "href": "/intg-secrets",
        "kind": "secrets",
        "empty_message": (
            "Secrets & env separation register is empty or unwired. "
            "Empty is not vault separation prove and not CAP-INTG-07 PROVEN."
        ),
        "waiting_message": (
            "Secrets / env slots and pointers are named. Naming is not a live "
            "vault, not secret contents, not mint, and not CAP-INTG-07 PROVEN "
            "or READY. CAP-INTG-07 stays SPECIFIED. CR stays OPEN."
        ),
        "unwired_message": (
            "Secrets & env register was not read. UNWIRED. No secret mint or "
            "exfil invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Secrets & Env desk",
        "next_code": "open_intg_secrets",
    },
)

POINTER_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "esb_connector_pointer",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "ESB Connector (honesty pointer)",
        "staff_title": "ESB pointer",
        "href": None,
        "kind": "pointer_esb",
        "message": (
            "ESB connector is honesty-only here. CAP-INTG-02 stays BUILT. "
            "No live ESB call. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "No live ESB action from this cluster",
        "next_code": "esb_pointer_only",
    },
    {
        "id": "metricool_connector_pointer",
        "cap": CAP_05,
        "cr": CR_05,
        "title": "Metricool Connector (honesty pointer)",
        "staff_title": "Metricool pointer",
        "href": None,
        "kind": "pointer_metricool",
        "message": (
            "Metricool connector is honesty-only here. CAP-INTG-05 stays BUILT. "
            "No live Metricool write. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "No live Metricool action from this cluster",
        "next_code": "metricool_pointer_only",
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
    "invented_commissioned": False,
    "invented_adopted": False,
    "invented_connector_live": False,
    "invented_yanolja": False,
    "invented_esb": False,
    "invented_bank_api": False,
    "invented_metricool": False,
    "invented_secret_mint": False,
    "proven": False,
    "ready": False,
    "caps_raised": False,
    "cr_resolved": False,
    "ledger_write": False,
    "model_c_write": False,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "bank_api_called": False,
    "zayen_write": False,
    "finance_controls": False,
    "hr": False,
    "trading": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "yanolja_called": False,
    "esb_called": False,
    "metricool_write": False,
    "secret_exfil": False,
    "mint_secret": False,
    "secret_store_write": False,
    "external_write": False,
    "commission_flip": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "ggv_reopened": False,
    "bzg_reopened": False,
    "amg_reopened": False,
    "intel_reopened": False,
    "core_reopened": False,
    "crm_reopened": False,
    "msc_reopened": False,
    "strat_reopened": False,
    "dr_reopened": False,
    "sale_reopened": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "intg_caps_unchanged": True,
    "cap_intg_01_absent": True,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent INTG management facts or maturity."""

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
        "pointers": [p["id"] for p in POINTER_SPECS],
        "caps": sorted(ALL_CAPS),
        "writes_accepted": False,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "commission_flip_property": False,
        "secret_exfil_property": False,
        "mint_secret_property": False,
        "external_write_property": False,
        "cloudflare_mutate_property": False,
        "access_mutate_property": False,
        "bank_api_property": False,
        "yanolja_call_property": False,
        "esb_call_property": False,
        "metricool_write_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_secret_exfil(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses secret exfiltration / mint / store.",
        code="secret_exfil_refused",
    )


def refuse_mint_secret(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses minting secrets.",
        code="mint_secret_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_bank_api(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses live bank API calls.",
        code="bank_api_refused",
    )


def refuse_yanolja(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses live Yanolja calls. CAP-INTG-01 stays ABSENT.",
        code="yanolja_refused",
    )


def refuse_esb(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses live ESB calls. Honesty pointer only.",
        code="esb_refused",
    )


def refuse_metricool(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTG Management Cluster refuses live Metricool writes. Honesty pointer only.",
        code="metricool_refused",
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
        "bank": "bank_api",
        "bank-api": "bank_api",
        "live-bank": "bank_api",
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
        "mint": "mint_secret",
        "mint-secret": "mint_secret",
        "secret-store": "mint_secret",
        "yanolja": "yanolja",
        "live-yanolja": "yanolja",
        "esb": "esb",
        "live-esb": "esb",
        "metricool": "metricool",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
        "upload": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "INTG Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "INTG Management Cluster is Owner (PERS-MATT) only.",
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
    next_href: str | None,
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
        "INTG management cluster routing — Owner retain",
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


def _intg_framework_status(
    spec: dict[str, Any],
    pack: dict[str, Any] | None,
    *,
    named_count: int,
    empty_flag: bool,
    ledger_maturity: str | None = None,
) -> tuple[str, list[str], bool, str, bool]:
    """Map INTG framework packs to EMPTY / UNWIRED / WAITING_DATA honesty."""
    if not isinstance(pack, dict) or pack.get("ok") is not True:
        return (
            "UNWIRED",
            ["EMPTY", "UNWIRED"],
            True,
            spec["unwired_message"],
            True,
        )
    # CAP-INTG-01 ABSENT stays honest EMPTY — do not invent WAITING as progress.
    if ledger_maturity == "ABSENT" or (spec.get("cap") == CAP_01 and ledger_maturity != "BUILT"):
        return (
            "EMPTY",
            ["EMPTY", "ABSENT"],
            True,
            spec["empty_message"],
            False,
        )
    if named_count <= 0 and empty_flag:
        return (
            "EMPTY",
            ["EMPTY"],
            True,
            spec["empty_message"],
            False,
        )
    if empty_flag or named_count > 0:
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


def _contract_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = contract.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = len((pack or {}).get("kinds") or [])
    empty_flag = bool((pack or {}).get("empty", True))
    status, tags, empty, message, unwired = _intg_framework_status(
        spec,
        pack,
        named_count=named,
        empty_flag=empty_flag,
        ledger_maturity=base.get("ledger_maturity"),
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
    strip["yanolja_called"] = False
    strip["esb_called"] = False
    strip["live_connector"] = False
    strip["connector_invented"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "yanolja_called": False,
            "esb_called": False,
            "live_connector": False,
            "numbers": None,
            "money": None,
        },
    }


def _cap_tests_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = cap_tests.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = len((pack or {}).get("kinds") or [])
    empty_flag = bool((pack or {}).get("empty", True))
    status, tags, empty, message, unwired = _intg_framework_status(
        spec,
        pack,
        named_count=named,
        empty_flag=empty_flag,
        ledger_maturity=base.get("ledger_maturity"),
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
    strip["bank_api_called"] = False
    strip["bank_feed_called"] = False
    strip["live_bank_connector"] = False
    strip["payment_executed"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "bank_api_called": False,
            "live_bank_connector": False,
            "numbers": None,
            "money": None,
        },
    }


def _gws_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = gws.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = int(
        (pack or {}).get("checklist_count")
        or (pack or {}).get("surface_count")
        or 0
    )
    empty_flag = int((pack or {}).get("empty_slot_count") or 0) > 0 or named > 0
    # GWS skeleton is named but NOT_RUN — treat as waiting, not live prove.
    if isinstance(pack, dict) and pack.get("ok") is True:
        empty_flag = True
    status, tags, empty, message, unwired = _intg_framework_status(
        spec,
        pack,
        named_count=named,
        empty_flag=empty_flag,
        ledger_maturity=base.get("ledger_maturity"),
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
    strip["gmail_called"] = False
    strip["calendar_called"] = False
    strip["drive_called"] = False
    strip["probed"] = False
    strip["green_claimed"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "gmail_called": False,
            "probed": False,
            "green_claimed": False,
            "numbers": None,
            "money": None,
        },
    }


def _tech_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = tech.build_registry(
            ledger_path=ledger_path,
            catalog_path=None,
            attach_health=False,
        )
    except Exception:
        pack = None
    named = len((pack or {}).get("entries") or [])
    empty_flag = named >= 0  # named registry is not PROVEN
    if isinstance(pack, dict) and pack.get("ok") is True and named > 0:
        empty_flag = True
    status, tags, empty, message, unwired = _intg_framework_status(
        spec,
        pack,
        named_count=named,
        empty_flag=empty_flag,
        ledger_maturity=base.get("ledger_maturity"),
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
    strip["green_invented"] = False
    strip["network_probes"] = False
    strip["external_writes"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "green_invented": False,
            "network_probes": False,
            "numbers": None,
            "money": None,
        },
    }


def _secrets_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = secrets.build_register(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    named = len((pack or {}).get("kinds") or []) + len((pack or {}).get("pointers") or [])
    empty_flag = bool((pack or {}).get("empty", True))
    status, tags, empty, message, unwired = _intg_framework_status(
        spec,
        pack,
        named_count=named,
        empty_flag=empty_flag,
        ledger_maturity=base.get("ledger_maturity"),
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
    strip["secret_exfil"] = False
    strip["mint_secret"] = False
    strip["contents_read"] = False
    strip["live_vault"] = False
    strip["secret_store_write"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "secret_exfil": False,
            "mint_secret": False,
            "contents_read": False,
            "numbers": None,
            "money": None,
        },
    }


def _pointer_card(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    strip = _honesty_strip(
        status="EMPTY",
        message=spec["message"],
        next_label=spec["next_label"],
        next_href=spec.get("href"),
        next_code=spec["next_code"],
    )
    strip["empty"] = True
    strip["status_tags"] = ["EMPTY", "POINTER"]
    strip["unwired"] = False
    strip["pointer_only"] = True
    strip["live_call"] = False
    strip["invented"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": True,
        "recorded_count": 0,
        "live": False,
        "pointer_only": True,
        "module_honesty": {
            "empty": True,
            "pointer_only": True,
            "live_call": False,
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
    if kind == "contract":
        return _contract_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "cap_tests":
        return _cap_tests_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "gws":
        return _gws_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "tech":
        return _tech_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "secrets":
        return _secrets_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "needs-you", "label": "Needs-You", "href": "#needs-you-connective"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "contract", "label": "Contract", "href": "/connector-contract"},
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
            "label": "No further INTG management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "intg_mgmt",
        "lede": (
            "Integration management cluster — connector contract, cap tests, "
            "GWS prove, tech registry, secrets/env. Empty stays empty. No "
            "invented live connector, bank API, or secret mint."
        ),
        "who_line": f"Signed in as {who.get('label') or 'Owner'}",
        "primary_next": primary,
        "nav": phone_nav(),
        "empty_module_count": len(empties),
        "exposed_actions": {
            "show_owner_copy": who.get("seat") == "owner",
            "show_operator_actions": False,
            "payment_on_screen": False,
            "show_seats_panel": False,
            "cloudflare_mutate": False,
            "secret_exfil": False,
            "mint_secret": False,
            "bank_api": False,
            "yanolja_call": False,
            "esb_call": False,
            "metricool_write": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": "Management cluster is compose-only; history lives on each INTG desk.",
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
    """Compose one Owner-facing INTG management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
        for spec in MODULE_SPECS
    ]
    pointers = [
        _pointer_card(
            spec,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
        for spec in POINTER_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("INTG", empty_count)
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    crs_open = []
    for cr_id in ALL_CRS:
        row = _cr_row(cr_id, catalog_db)
        if row.get("state") == "OPEN":
            crs_open.append(cr_id)

    cap_rows: dict[str, dict[str, Any]] = {}
    for cap in ALL_CAPS:
        maturity = _ledger_cap(cap, ledger_path)
        cr_id = {
            CAP_01: CR_01,
            CAP_02: CR_02,
            CAP_03: CR_03,
            CAP_04: CR_04,
            CAP_05: CR_05,
            CAP_06: CR_06,
            CAP_07: CR_07,
        }[cap]
        cr = _cr_row(cr_id, catalog_db)
        cap_rows[cap] = {
            "maturity": maturity,
            "expected": EXPECTED_MATURITY[cap],
            "cr": cr_id,
            "cr_state": cr.get("state"),
            "raised": False,
            "unchanged": maturity == EXPECTED_MATURITY[cap],
        }

    desk = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "seat": seat,
        "modules": modules,
        "module_count": len(modules),
        "honesty_pointers": pointers,
        "pointer_count": len(pointers),
        "empty_count": empty_count,
        "primary_next": primary,
        "owner_empire_handoff": {
            **empire,
            "pack": "INTG",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: INTG loop attention stays Owner — "
                "labels only, Owner desk not removed. No secret exfil. "
                "No mint secret. No bank API. No live Yanolja."
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
        "mint_secret": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "bank_api_called": False,
        "yanolja_called": False,
        "esb_called": False,
        "metricool_write": False,
        "external_write": False,
        "invented_connector_live": False,
        "invented_secret_mint": False,
        "cap_intg_01_absent": cap_rows[CAP_01]["maturity"] == "ABSENT",
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import intg_ops_needs_you_connective as intg_nye

    intg_nye._attach_needs_you_connective(
        desk,
        person_id=seat.get("person_id"),
        catalog_db=catalog_db,
        ledger_path=ledger_path,
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
    for spec in POINTER_SPECS:
        if spec["id"] == module_id:
            card = _pointer_card(
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
