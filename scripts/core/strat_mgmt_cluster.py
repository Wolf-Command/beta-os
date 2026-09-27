#!/usr/bin/env python3
"""STRAT Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-STRAT-CLUSTER-2026-09-22.md
+ Sprint2 continuous pack gen / Owner compressed sprint.

Composes existing Strategy modules (12-Week Year Cadence Prove, Owner Radar /
Mission Control Prove) into one phone-first Owner operating loop with honesty
EMPTY/UNWIRED/WAITING_DATA strips and derived next actions.

Bound beta-owner-safe.

Additive compose-only. Does not invent live mission scores / AU adoption.
Does not invent PROVEN/READY/COMMISSIONED/ADOPTED. Does not resolve CRs.
Does not raise CAP maturity (CAP-STRAT-01/02 stay BUILT). No Production/CF/
Access-mutate/secret-exfil/external-write. No P1/P7/Devi/w12 FIN/parked
GGV/INTG reopen. Does not reopen DONE BZG/AMG/INTEL/CORE/CRM/MSC. Does not
touch WIP quartet. CAP CRs stay OPEN. AUs stay NOT STARTED.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import staff_ready_ux as sru
from core import strat_12wy_prove as wy
from core import strat_radar_prove as radar

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ADOPTION_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"

BOUND = "beta-owner-safe"
SCHEMA_ID = "wolf.strat-mgmt-cluster.v1"
SLICE = "strat_mgmt_cluster_v1"
OWNER = "PERS-MATT"

CAP_01 = wy.CAP_ID  # CAP-STRAT-01
CAP_02 = radar.CAP_ID  # CAP-STRAT-02
CR_01 = wy.CR_ID  # CR-6535f7cb02370850
CR_02 = radar.CR_ID  # CR-7a145ad69d8bf3c5
AU_01 = "AU-STRAT-01-GGV"
AU_02 = "AU-STRAT-02-OWNER"
CR_AU_01 = "CR-d6c1c6769b441944"
CR_AU_02 = "CR-df9f073e3c32ac6d"

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "strat_12wy_prove",
        "cap": CAP_01,
        "cr": CR_01,
        "title": "12-Week Year Cadence Prove",
        "staff_title": "12WY cadence",
        "href": "/12wy-prove",
        "kind": "12wy",
        "empty_message": (
            "12WY prove score is empty or unwired. "
            "Empty is not 0%, not a live mission score, and not CAP-STRAT-01 PROVEN."
        ),
        "waiting_message": (
            "12WY cadence bindings are readable. A wired week percent is not PROVEN, "
            "not READY, and not AU-STRAT-01-GGV started. CR stays OPEN."
        ),
        "unwired_message": (
            "12WY score binding was not read. UNWIRED. No percent invented. "
            "Not 0%. CR stays OPEN."
        ),
        "next_label": "Open 12WY prove desk",
        "next_code": "open_12wy_prove",
    },
    {
        "id": "strat_radar_prove",
        "cap": CAP_02,
        "cr": CR_02,
        "title": "Owner Radar / Mission Control Prove",
        "staff_title": "Owner radar",
        "href": "/radar-prove",
        "kind": "radar",
        "empty_message": (
            "Owner Radar pulse / exceptions are empty or unnamed. "
            "Empty is not zero exceptions and not CAP-STRAT-02 PROVEN."
        ),
        "waiting_message": (
            "Radar surfaces are named. A named pulse is not live mission scores, "
            "not AU-STRAT-02-OWNER started, and not READY. CR stays OPEN."
        ),
        "unwired_message": (
            "Radar binding was not read. UNWIRED. Pulse and exception counts "
            "are not zero and not invented. CR stays OPEN."
        ),
        "next_label": "Open Radar prove desk",
        "next_code": "open_radar_prove",
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
    "invented_mission_scores": False,
    "invented_au_adoption": False,
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
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "strat_caps_unchanged": True,
    "aus_not_started": True,
    "au_started": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent STRAT management facts or maturity."""

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
        "mission_score_property": False,
        "au_adoption_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_secret_exfil(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster refuses secret exfiltration / mint / store.",
        code="secret_exfil_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "STRAT Management Cluster is compose-only. External writes are refused.",
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
        "mission-score": "writes",
        "au-start": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "STRAT Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "STRAT Management Cluster is Owner (PERS-MATT) only.",
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


def _au_state(au_id: str, adoption_path: Path | str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "au_id": au_id,
        "present": False,
        "state": None,
        "started": False,
        "adopted": False,
    }
    path = Path(adoption_path) if adoption_path else ADOPTION_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    rows = data if isinstance(data, list) else None
    if not isinstance(rows, list) and isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                rows = value
                break
    if not isinstance(rows, list):
        return out
    for row in rows:
        if isinstance(row, dict) and row.get("au_id") == au_id:
            state = str(row.get("state") or "").strip() or None
            out["present"] = True
            out["state"] = state
            out["started"] = bool(state) and state.upper() not in {
                "NOT STARTED",
                "NOT_STARTED",
            }
            out["adopted"] = bool(state) and state.upper() in {"ADOPTED", "COMMISSIONED"}
            return out
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
        "STRAT management cluster routing — Owner retain",
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


def _12wy_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    prove = wy.build_prove(ledger_path=ledger_path, catalog_db=catalog_db)
    score = prove.get("score") or {}
    state = str(score.get("state") or "").upper()
    raw_percent = score.get("percent")
    # Pass-through only when WIRED; never invent. Cluster strip keeps numbers=None
    # for live mission honesty — percent is surface-only on the module desk.
    if state == "WIRED":
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        unwired = False
    elif state == "EMPTY":
        status = "EMPTY"
        tags = ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        unwired = False
    else:
        status = "UNWIRED"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["unwired_message"]
        unwired = True
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
    strip["score_state"] = state or None
    strip["percent"] = None
    strip["empty_is_not_zero"] = True
    strip["invented_percent"] = False
    strip["invented_mission_scores"] = False
    strip["tactics_invented"] = False
    strip["live_mission_score"] = False
    _ = raw_percent  # evidenced percent lives on /12wy-prove; not invented here
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "empty_is_not_zero": True,
            "percent": None,
            "invented_percent": False,
            "invented_mission_scores": False,
            "tactics_invented": False,
            "numbers": None,
            "money": None,
        },
    }


def _radar_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    prove = radar.build_prove(
        ledger_path=ledger_path,
        catalog_db=catalog_db,
        adoption_path=adoption_path,
    )
    surfaces = prove.get("surfaces") or {}
    pulse = surfaces.get("pulse") or {}
    html = surfaces.get("html") or {}
    pulse_status = str(pulse.get("status") or "").upper()
    if pulse_status == "NOT_READ" or html.get("present") is not True:
        status = "UNWIRED"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["unwired_message"]
        unwired = True
    elif pulse_status == "ABSENT":
        status = "EMPTY"
        tags = ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        unwired = False
    elif pulse_status == "NAMED":
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        unwired = False
    else:
        status = "UNWIRED"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["unwired_message"]
        unwired = True
    adoption = prove.get("adoption") or {}
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
    strip["pulse_status"] = pulse_status or None
    strip["pulse_count"] = None
    strip["exception_count"] = None
    strip["invented_pulse"] = False
    strip["invented_exceptions"] = False
    strip["invented_mission_scores"] = False
    strip["invented_au_adoption"] = False
    strip["au_state"] = adoption.get("state")
    strip["au_started"] = False
    strip["progress_used_as_cap"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "pulse_count": None,
            "exception_count": None,
            "invented_pulse": False,
            "invented_exceptions": False,
            "invented_mission_scores": False,
            "invented_au_adoption": False,
            "au_started": False,
            "numbers": None,
            "money": None,
        },
    }


def _module_card(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    kind = spec["kind"]
    if kind == "12wy":
        return _12wy_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "radar":
        return _radar_card(
            spec,
            base=base,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            adoption_path=adoption_path,
        )
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "12wy", "label": "12WY", "href": "/12wy-prove"},
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
            "label": "No further STRAT management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "strat_mgmt",
        "lede": (
            "Strategy management cluster — 12-Week Year cadence and Owner Radar. "
            "Empty stays empty. No invented mission scores or AU adoption."
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
            "why": "Management cluster is compose-only; history lives on each prove desk.",
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
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one Owner-facing STRAT management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            adoption_path=adoption_path,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("STRAT", empty_count)
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

    au_01 = _au_state(AU_01, adoption_path)
    au_02 = _au_state(AU_02, adoption_path)
    aus = {
        AU_01: {
            "state": au_01.get("state"),
            "started": False,
            "adopted": False,
            "cr": CR_AU_01,
            "in_scope": False,
        },
        AU_02: {
            "state": au_02.get("state"),
            "started": False,
            "adopted": False,
            "cr": CR_AU_02,
            "in_scope": False,
        },
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
            "pack": "STRAT",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: STRAT loop attention stays Owner — "
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
        "aus": aus,
        "aus_not_started": True,
        "au_started": False,
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
        "invented_mission_scores": False,
        "invented_au_adoption": False,
        "mission_scores": None,
        "pulse_count": None,
        "exception_count": None,
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import strat_ops_needs_you_connective as strat_nye

    strat_nye._attach_needs_you_connective(
        desk,
        person_id=seat.get("person_id"),
        catalog_db=catalog_db,
        ledger_path=ledger_path,
        adoption_path=adoption_path,
    )
    return desk


def module_strip(
    module_id: str,
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    _ = seat
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                adoption_path=adoption_path,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
