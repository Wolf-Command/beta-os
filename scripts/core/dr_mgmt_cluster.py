#!/usr/bin/env python3
"""DR Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-DR-CLUSTER-2026-09-22.md
+ Sprint2 continuous pack gen / Owner compressed sprint.

Composes existing Disaster Recovery modules (Restore Drill Framework, Failure
Domains Prove, Crown Jewel Protection) into one phone-first Owner operating
loop with honesty EMPTY/UNWIRED/WAITING_DATA strips and derived next actions.

Bound beta-core-safe.

Additive compose-only. Does not invent live restore proof / Production backup
facts. Does not invent PROVEN/READY/COMMISSIONED/ADOPTED. Does not resolve CRs.
Does not raise CAP maturity (CAP-DR-01 and CAP-DR-02 stay SPECIFIED). No
Production/CF/Access-mutate/secret-exfil/external-write/B2-mutate. No
P1/P7/Devi/w12 FIN/parked GGV/INTG reopen. Does not reopen DONE
BZG/AMG/INTEL/CORE/CRM/MSC/STRAT. Does not touch WIP quartet. CRs stay OPEN.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import dr_crown_jewel as crown
from core import failure_domains as domains
from core import founder_dep_routing as fdr
from core import restore_drill as restore
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-core-safe"
SCHEMA_ID = "wolf.dr-mgmt-cluster.v1"
SLICE = "dr_mgmt_cluster_v1"
OWNER = "PERS-MATT"

CAP_01 = restore.CAP_ID  # CAP-DR-01
CAP_02 = domains.CAP_ID  # CAP-DR-02 (failure domains + crown jewel)
CR_01 = restore.CR_ID  # CR-667f31959d1bbe82
CR_02 = domains.CR_ID  # CR-01fc21cfe028333b

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "restore_drill",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "Restore Drill Framework",
        "staff_title": "Restore drill",
        "href": "/restore-drill",
        "kind": "restore",
        "empty_message": (
            "Restore drill checklist is empty or unwired. "
            "Empty is not a live restore, not Production backup proof, "
            "and not CAP-DR-01 PROVEN."
        ),
        "waiting_message": (
            "Restore drill checklist is named. NOT_RUN is not a live restore, "
            "not Production backup proof, and not CAP-DR-01 PROVEN or READY. "
            "CR stays OPEN."
        ),
        "unwired_message": (
            "Restore drill framework was not read. UNWIRED. No live restore "
            "invented. Not PROVEN. CR stays OPEN."
        ),
        "next_label": "Open Restore Drill desk",
        "next_code": "open_restore_drill",
    },
    {
        "id": "failure_domains",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Failure Domains Prove",
        "staff_title": "Failure domains",
        "href": "/failure-domains",
        "kind": "domains",
        "empty_message": (
            "Failure domain independence slots are empty or unwired. "
            "Empty is not independence proved and not CAP-DR-02 PROVEN."
        ),
        "waiting_message": (
            "Beta and Production are named as separate domains. Naming is not "
            "independence proved, not a live restore, and not CAP-DR-02 PROVEN "
            "or READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Failure domains framework was not read. UNWIRED. Independence is "
            "not proved and not invented. CR stays OPEN."
        ),
        "next_label": "Open Failure Domains desk",
        "next_code": "open_failure_domains",
    },
    {
        "id": "dr_crown_jewel",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Crown Jewel Protection",
        "staff_title": "Crown jewels",
        "href": "/crown-jewels",
        "kind": "crown",
        "empty_message": (
            "Crown jewel protection slots are empty or unwired. "
            "Empty is not protection proved and not CAP-DR-02 PROVEN."
        ),
        "waiting_message": (
            "Crown jewel systems are named. Naming is not opening contents, "
            "not protection proved, and not CAP-DR-02 PROVEN or READY. "
            "CR stays OPEN."
        ),
        "unwired_message": (
            "Crown jewel register was not read. UNWIRED. Protection is not "
            "proved and not invented. CR stays OPEN."
        ),
        "next_label": "Open Crown Jewels desk",
        "next_code": "open_crown_jewels",
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
    "invented_restore_proof": False,
    "invented_backup_facts": False,
    "invented_independence": False,
    "invented_protection": False,
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
    "live_restore": False,
    "nas_destructive": False,
    "b2_mutated": False,
    "b2_destructive": False,
    "commission_flip": False,
    "secret_exfil": False,
    "external_write": False,
    "p1_reopened": False,
    "p7_reopened": False,
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
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "dr_caps_unchanged": True,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent DR management facts or maturity."""

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
        "live_restore_property": False,
        "b2_mutate_property": False,
        "nas_destructive_property": False,
        "backup_facts_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_secret_exfil(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses secret exfiltration / mint / store.",
        code="secret_exfil_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_b2(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses B2 mutate / delete / overwrite.",
        code="b2_refused",
    )


def refuse_nas(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses NAS destructive mutation.",
        code="nas_refused",
    )


def refuse_live_restore(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "DR Management Cluster refuses inventing live restore proof.",
        code="restore_refused",
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
        "b2": "b2",
        "b2-mutate": "b2",
        "backblaze": "b2",
        "nas": "nas",
        "restore": "restore",
        "live-restore": "restore",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
        "backup-facts": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "DR Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "DR Management Cluster is Owner (PERS-MATT) only.",
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
        "DR management cluster routing — Owner retain",
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


def _framework_status(
    spec: dict[str, Any],
    pack: dict[str, Any] | None,
) -> tuple[str, list[str], bool, str, bool]:
    """Map DR framework packs to EMPTY / UNWIRED / WAITING_DATA honesty."""
    if not isinstance(pack, dict) or pack.get("ok") is not True:
        return (
            "UNWIRED",
            ["EMPTY", "UNWIRED"],
            True,
            spec["unwired_message"],
            True,
        )
    status = str(pack.get("status") or "").upper()
    checklist_count = int(pack.get("checklist_count") or 0)
    executed = int(pack.get("checklist_executed") or 0)
    if checklist_count <= 0:
        return (
            "EMPTY",
            ["EMPTY"],
            True,
            spec["empty_message"],
            False,
        )
    if status == "NOT_RUN" and executed == 0:
        # Named checklist / domains — waiting for real evidence, not PROVEN.
        return (
            "WAITING_DATA",
            ["WAITING_DATA"],
            False,
            spec["waiting_message"],
            False,
        )
    # Anything else fails closed as unwired — never invent SUCCESS/PROVEN.
    return (
        "UNWIRED",
        ["EMPTY", "UNWIRED"],
        True,
        spec["unwired_message"],
        True,
    )


def _restore_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = restore.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    status, tags, empty, message, unwired = _framework_status(spec, pack)
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
    strip["live_restore"] = False
    strip["drill_status"] = (pack or {}).get("status")
    strip["checklist_executed"] = 0
    strip["invented_restore_proof"] = False
    strip["invented_backup_facts"] = False
    strip["b2_destructive"] = False
    strip["nas_destructive"] = False
    strip["production_mutated"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "live_restore": False,
            "invented_restore_proof": False,
            "invented_backup_facts": False,
            "checklist_executed": 0,
            "numbers": None,
            "money": None,
        },
    }


def _domains_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = domains.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    status, tags, empty, message, unwired = _framework_status(spec, pack)
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
    strip["independence_proved"] = False
    strip["invented_independence"] = False
    strip["slots_filled"] = False
    strip["live_restore"] = False
    strip["b2_destructive"] = False
    strip["nas_destructive"] = False
    strip["production_mutated"] = False
    strip["domain_count"] = None
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "independence_proved": False,
            "invented_independence": False,
            "slots_filled": False,
            "numbers": None,
            "money": None,
        },
    }


def _crown_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    try:
        pack = crown.build_framework(ledger_path=ledger_path, catalog_db=catalog_db)
    except Exception:
        pack = None
    status, tags, empty, message, unwired = _framework_status(spec, pack)
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
    strip["protection_proved"] = False
    strip["invented_protection"] = False
    strip["crown_jewels_opened"] = False
    strip["contents_read"] = False
    strip["protected_count"] = None
    strip["live_restore"] = False
    strip["b2_destructive"] = False
    strip["nas_destructive"] = False
    strip["production_mutated"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "protection_proved": False,
            "invented_protection": False,
            "protected_count": None,
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
    if kind == "restore":
        return _restore_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "domains":
        return _domains_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "crown":
        return _crown_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "needs", "label": "Needs", "href": "#needs-you-connective"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "drill", "label": "Drill", "href": "/restore-drill"},
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
            "label": "No further DR management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "dr_mgmt",
        "lede": (
            "Disaster recovery management cluster — restore drill, failure "
            "domains, crown jewels. Empty stays empty. No invented live restore "
            "or Production backup facts."
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
            "b2_mutate": False,
            "live_restore": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": "Management cluster is compose-only; history lives on each DR desk.",
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
    """Compose one Owner-facing DR management cluster desk."""
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
    empire = fdr.label_for_pack_handoff("DR", empty_count)
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    bound_crs = (CR_01, CR_02)
    crs_open = []
    for cr_id in bound_crs:
        row = _cr_row(cr_id, catalog_db)
        if row.get("state") == "OPEN":
            crs_open.append(cr_id)

    # Distinct CAP rows (CAP-DR-02 appears twice via domains + crown).
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
            "pack": "DR",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: DR loop attention stays Owner — "
                "labels only, Owner desk not removed. No secret exfil. No B2 mutate."
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
        "live_restore": False,
        "b2_mutated": False,
        "b2_destructive": False,
        "nas_destructive": False,
        "invented_restore_proof": False,
        "invented_backup_facts": False,
        "invented_independence": False,
        "invented_protection": False,
        "protected_count": None,
        "backup_facts": None,
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import dr_ops_needs_you_connective as dr_nye

    dr_nye._attach_needs_you_connective(
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
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
