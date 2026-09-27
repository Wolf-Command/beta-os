#!/usr/bin/env python3
"""MSC Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-MSC-CLUSTER-2026-09-22.md.

Composes existing MSC modules (Asset Register, Posture Prove, Compliance Pack,
Cyber Baseline, Records Defensibility) into one phone-first Owner operating
loop with honesty EMPTY/UNWIRED/WAITING_DATA strips and derived next actions.

Bound beta-core-safe.

Additive compose-only. Does not invent live MFA/compliance/legal-hold facts.
Does not invent PROVEN/READY/COMMISSIONED/ADOPTED. Does not resolve CRs.
Does not raise CAP maturity. No Production/CF/Access-mutate/secret-exfil/
external-write. No P1/P7/Devi/w12 FIN/parked GGV/INTG reopen. Does not touch
WIP quartet. CAP-MSC-01 stays SPECIFIED; CAP-MSC-02 stays BUILT;
CAP-MSC-03..05 stay SPECIFIED; CRs stay OPEN.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import msc_asset_register as assets
from core import msc_compliance_pack as compliance
from core import msc_cyber_baseline as cyber
from core import msc_posture_prove as posture
from core import msc_records_defensibility as records
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-core-safe"
SCHEMA_ID = "wolf.msc-mgmt-cluster.v1"
SLICE = "msc_mgmt_cluster_v1"
OWNER = "PERS-MATT"

CAP_01 = assets.CAP_ID  # CAP-MSC-01
CAP_02 = posture.CAP_ID  # CAP-MSC-02
CAP_03 = compliance.CAP_ID  # CAP-MSC-03
CAP_04 = cyber.CAP_ID  # CAP-MSC-04
CAP_05 = records.CAP_ID  # CAP-MSC-05
CR_01 = assets.CR_ID  # CR-7ea69933a9d39ba9
CR_02 = posture.CR_ID  # CR-80296d7bc9c35452
CR_03 = compliance.CR_ID  # CR-1f93c785c88e9564
CR_04 = cyber.CR_ID  # CR-7dae8b389cce6f9a
CR_05 = records.CR_ID  # CR-2d299c339747f432

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "asset_register",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "Asset & Maintenance Register",
        "staff_title": "Asset register",
        "href": "/msc-assets",
        "kind": "assets",
        "empty_message": (
            "Asset register is empty or unwired. "
            "Empty is not an inventory count, not a payment, and not CAP-MSC-01 PROVEN."
        ),
        "waiting_message": (
            "Named asset rows exist. A row is not inventory census, not service proved, "
            "and not invented money. CR stays OPEN."
        ),
        "next_label": "Open MSC Asset Register desk",
        "next_code": "open_msc_assets",
    },
    {
        "id": "posture_prove",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Automated Posture Prove",
        "staff_title": "Posture prove",
        "href": "/msc-posture",
        "kind": "posture",
        "empty_message": (
            "Posture prove framework slots are empty. "
            "Empty is not a live posture score and not a prove."
        ),
        "waiting_message": (
            "Posture / control / evidence slots are named. "
            "A named slot is not a live score, not Cloudflare mutate, and not READY."
        ),
        "next_label": "Open MSC Posture Prove desk",
        "next_code": "open_msc_posture",
    },
    {
        "id": "compliance_pack",
        "cap": CAP_03,
        "cr": CR_03,
        "title": "Compliance Pack",
        "staff_title": "Compliance pack",
        "href": "/msc-compliance",
        "kind": "compliance",
        "empty_message": (
            "Compliance pack slots are empty. "
            "Empty is not licence status and not proof of compliance."
        ),
        "waiting_message": (
            "Compliance kinds are named. A named kind is not a current licence "
            "and not invented statutory proof. CR stays OPEN."
        ),
        "next_label": "Open MSC Compliance desk",
        "next_code": "open_msc_compliance",
    },
    {
        "id": "cyber_baseline",
        "cap": CAP_04,
        "cr": CR_04,
        "title": "Cybersecurity Baseline",
        "staff_title": "Cyber baseline",
        "href": "/msc-cyber",
        "kind": "cyber",
        "empty_message": (
            "Cyber baseline slots are empty. "
            "Empty is not live MFA status and not device posture truth."
        ),
        "waiting_message": (
            "Cyber kinds are named. A named kind is not live MFA, not audited access, "
            "and not Access mutate. CR stays OPEN."
        ),
        "next_label": "Open MSC Cyber Baseline desk",
        "next_code": "open_msc_cyber",
    },
    {
        "id": "records_defensibility",
        "cap": CAP_05,
        "cr": CR_05,
        "title": "Documents / Records / Legal Defensibility",
        "staff_title": "Records defensibility",
        "href": "/msc-records",
        "kind": "records",
        "empty_message": (
            "Records defensibility slots are empty. "
            "Empty is not a legal hold and not retention truth."
        ),
        "waiting_message": (
            "Records kinds are named. A named kind is not a live legal hold, "
            "not retention proof, and not invented defensibility. CR stays OPEN."
        ),
        "next_label": "Open MSC Records desk",
        "next_code": "open_msc_records",
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
    "commission_flip": False,
    "secret_exfil": False,
    "external_write": False,
    "invented_mfa": False,
    "invented_licence_status": False,
    "invented_legal_hold": False,
    "invented_posture_score": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "ggv_reopened": False,
    "intg_reopened": False,
    "bzg_reopened": False,
    "amg_reopened": False,
    "intel_reopened": False,
    "crm_reopened": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "msc_caps_unchanged": True,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent MSC management facts or maturity."""

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
        "writes_accepted": False,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "commission_flip_property": False,
        "secret_exfil_property": False,
        "external_write_property": False,
        "cloudflare_mutate_property": False,
        "access_mutate_property": False,
        "mfa_property": False,
        "legal_hold_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_secret_exfil(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster refuses secret exfiltration / mint / store.",
        code="secret_exfil_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "MSC Management Cluster is compose-only. External writes are refused.",
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
        "fill": "writes",
        "note": "writes",
        "current": "writes",
        "mfa": "writes",
        "legal-hold": "writes",
        "licence": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "MSC Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "MSC Management Cluster is Owner (PERS-MATT) only.",
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
        "MSC management cluster routing — Owner retain",
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


def _assets_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    assets_db: Path | str | None = None,
) -> dict[str, Any]:
    db_path = Path(assets_db) if assets_db else assets.DEFAULT_DB
    present = db_path.is_file()
    register = assets.build_register(
        db_path if present else db_path,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
    )
    count = int(register.get("recorded_count") or 0)
    if not present:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
        unwired = True
    elif count == 0 or register.get("empty"):
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
    strip["inventory_count"] = None
    strip["empty_is_inventory"] = False
    strip["service_proved"] = False
    strip["payment"] = None
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": count if present else 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "empty_is_inventory": False,
            "inventory_count": None,
            "service_proved": False,
            "payment": None,
            "numbers": None,
            "money": None,
        },
    }


def _skeleton_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    pack: dict[str, Any],
    invent_flags: dict[str, Any],
) -> dict[str, Any]:
    """Compose empty MSC skeleton packs — EMPTY honesty, never invent live facts."""
    is_empty = bool(pack.get("empty", True))
    on_disk = bool(pack.get("on_disk"))
    kinds = pack.get("kinds") or []
    named = len(kinds) > 0
    if is_empty and not named:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"] if not on_disk else ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        unwired = not on_disk
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
    strip.update(invent_flags)
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": int(pack.get("recorded_count") or 0),
        "live": False,
        "module_honesty": {
            "empty": empty,
            "numbers": None,
            "money": None,
            **invent_flags,
        },
    }


def _posture_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    pack = posture.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    return _skeleton_card(
        spec,
        base=base,
        pack=pack,
        invent_flags={
            "proved": False,
            "posture_score": None,
            "current": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "empty_is_prove": False,
        },
    )


def _compliance_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    pack = compliance.build_pack(ledger_path=ledger_path, catalog_db=catalog_db)
    card = _skeleton_card(
        spec,
        base=base,
        pack=pack,
        invent_flags={
            "compliance_proved": False,
            "licence_status": None,
            "current": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "empty_is_compliance": False,
        },
    )
    card["operator_depth_href"] = "/msc-compliance#compliance-depth"
    return card


def _cyber_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    pack = cyber.build_baseline(ledger_path=ledger_path, catalog_db=catalog_db)
    return _skeleton_card(
        spec,
        base=base,
        pack=pack,
        invent_flags={
            "security_proved": False,
            "mfa_status": None,
            "device_posture": None,
            "audited_access": None,
            "current": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "empty_is_security": False,
            "invented_mfa": False,
        },
    )


def _module_card(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    assets_db: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    kind = spec["kind"]
    if kind == "assets":
        return _assets_card(
            spec,
            base=base,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            assets_db=assets_db,
        )
    if kind == "posture":
        return _posture_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "compliance":
        return _compliance_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "cyber":
        return _cyber_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "records":
        pack = records.build_register(ledger_path=ledger_path, catalog_db=catalog_db)
        return _skeleton_card(
            spec,
            base=base,
            pack=pack,
            invent_flags={
                "defensibility_proved": False,
                "records_status": None,
                "retention": None,
                "legal_hold": None,
                "current": False,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "empty_is_defensibility": False,
                "invented_legal_hold": False,
            },
        )
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "assets", "label": "Assets", "href": "/msc-assets"},
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
            "label": "No further MSC management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "msc_mgmt",
        "lede": (
            "MSC management cluster — assets, posture, compliance, cyber, "
            "records. Empty stays empty. No invented MFA or legal hold."
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
    assets_db: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one Owner-facing MSC management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            assets_db=assets_db,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("MSC", empty_count)
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    bound_crs = (CR_01, CR_02, CR_03, CR_04, CR_05)
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
            "pack": "MSC",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: MSC loop attention stays Owner — "
                "labels only, Owner desk not removed. No secret exfil."
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
        "secret_exfil": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "mfa_status": None,
        "legal_hold": None,
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import msc_ops_needs_you_connective as msc_nye

    msc_nye._attach_needs_you_connective(
        desk,
        person_id=seat.get("person_id"),
        catalog_db=catalog_db,
        ledger_path=ledger_path,
        assets_db=assets_db,
    )
    return desk


def module_strip(
    module_id: str,
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    assets_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    _ = seat
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                assets_db=assets_db,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
