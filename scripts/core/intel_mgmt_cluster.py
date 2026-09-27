#!/usr/bin/env python3
"""INTEL Learning Policy Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-INTEL-CLUSTER-2026-09-22.md.

Composes existing INTEL primitives (approve-to-rule, intel ops pack,
intel connective / AKR+DM handoffs) into one phone-first learning-policy
management read model with honesty EMPTY / UNWIRED / WAITING_DATA /
WAITING_APPROVAL strips and derived next actions.

Distinct from DONE Sprint2 P4 connective wire and from BLOCKED factory-failure
intel-learning-policy-v1 (inspect_retry_ceiling). Does not relaunch that lane.
Does not invent live learning, adopted rules, or performance proof.

Bound beta-intel-connect-safe.

Additive compose-only. Does not invent PROVEN/READY. Does not resolve CRs.
Does not raise CAP maturity. No auto-promote / auto-execute. No money/CF/Production.
No P1/P7/Devi/w12 FIN/BZG/GGV/AMG reopen.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import founder_dep_routing as fdr
from core import intel_approve_to_rule as rules
from core import intel_connective as connect
from core import intel_ops_pack as ops
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

BOUND = "beta-intel-connect-safe"
SCHEMA_ID = "wolf.intel-mgmt-cluster.v1"
SLICE = "intel_mgmt_cluster_v1"
OWNER = "PERS-MATT"

CAP_01 = "CAP-INTEL-01"
CAP_02 = "CAP-INTEL-02"
CAP_03 = "CAP-INTEL-03"
CAP_04 = "CAP-INTEL-04"
CAP_05 = "CAP-INTEL-05"
CR_05 = "CR-be51980bd1194448"
CR_AU = "CR-dca0ad62e1b0032e"
AU_WOLF = "AU-INTEL-02-WOLF"

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "approve_to_rule",
        "cap": CAP_05,
        "cr": CR_05,
        "title": "Approve-to-rule learning loop",
        "staff_title": "Experiment → approve → stub",
        "href": "/intel-ops-pack",
        "kind": "approve_to_rule",
        "empty_message": (
            "Approve-to-rule queue is empty. "
            "Empty is not live learning, an adopted rule, or performance proof."
        ),
        "waiting_approval_message": (
            "Experiment notes await Owner or role approval. "
            "A note is not an adopted rule. No auto-promote."
        ),
        "stub_message": (
            "Versioned rule stubs exist. A stub is not executed and is not promoted. "
            "Not live learning proof. No auto-promote."
        ),
        "next_label": "Open Intel Ops to record an experiment note",
        "next_code": "open_ops_note",
    },
    {
        "id": "ops_pack",
        "cap": CAP_01,
        "cr": CR_AU,
        "title": "Intel Ops desk",
        "staff_title": "Ask → recall → note handoff",
        "href": "/intel-ops-pack",
        "kind": "ops_pack",
        "empty_message": (
            "Intel Ops today strip has no ask yet. "
            "Empty recall is not invented Decision Memory history."
        ),
        "next_label": "Open Intel Ops desk",
        "next_code": "open_ops_pack",
    },
    {
        "id": "connective",
        "cap": CAP_01,
        "cr": CR_05,
        "title": "Intel connective (P4)",
        "staff_title": "AKR / DM desk wire",
        "href": "/ggv-ops-pack",
        "kind": "connective",
        "empty_message": (
            "P4 connective is wired into BZG/GGV/AMG next actions. "
            "Connective wire is not CAP-INTEL-05 learning proof and not "
            "a relaunch of blocked intel-learning-policy-v1."
        ),
        "next_label": "Review connective on an ops desk",
        "next_code": "open_connective_surface",
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
    "finance_controls": False,
    "hr": False,
    "trading": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "auto_promote": False,
    "auto_execute": False,
    "rule_execution": False,
    "live_rule": False,
    "invented_learning": False,
    "invented_adopted_rule": False,
    "invented_performance": False,
    "p4_reopened": False,
    "learning_policy_v1_relaunched": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "bzg_reopened": False,
    "ggv_reopened": False,
    "amg_reopened": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent learning proof or maturity."""

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
        "auto_promote_property": False,
        "auto_execute_property": False,
        "learning_proof_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_auto_promote(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses auto-promote.",
        code="auto_promote_refused",
    )


def refuse_auto_execute(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster refuses auto-execute / rule execution.",
        code="auto_execute_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "INTEL Management Cluster is compose-only. External writes are refused.",
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
        "promote": "auto_promote",
        "auto-promote": "auto_promote",
        "auto_promote": "auto_promote",
        "execute": "auto_execute",
        "auto-execute": "auto_execute",
        "auto_execute": "auto_execute",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner or existing intel.rule / decision.memory holder. Fail closed."""
    try:
        seat = ops.require_actor(person_id)
    except ops.IntelOpsPackError as exc:
        raise MgmtClusterError(str(exc), code=exc.code) from exc
    label = sru.human_person(seat.get("person_id"))
    return {
        **seat,
        "label": label,
    }


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
        "empty": status in {"EMPTY", "UNWIRED"},
        "message": message,
        "numbers": None,
        "learning_proof": None,
        "adopted_rule": None,
        "performance": None,
        "invented": False,
        "auto_promote": False,
        "auto_execute": False,
        "next_action": empty["next_action"],
    }


def _module_handoff(spec: dict[str, Any], cr: dict[str, Any]) -> dict[str, Any]:
    founder = fdr.classify_text(
        f"{spec['cap']} | {spec['title']} | {cr.get('next_action') or spec['next_label']} | "
        "Owner approval policy intentional authority learning-policy cluster routing",
        has_staff_seat=False,
    )
    return {
        "founder_dep_class": founder["class"],
        "founder_dep_reason": founder["reason"],
        "safe_implement": founder["safe_implement"],
        "invented_owner_control_away": False,
        "seat_hint": "Owner",
    }


def _approve_to_rule_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    base: dict[str, Any],
    rule_db_path: Path | str | None = None,
) -> dict[str, Any]:
    role_allowed = False
    try:
        seat = ops.seat_for(person_id) or {}
        role_allowed = seat.get("gate") == "role"
    except Exception:  # noqa: BLE001 — fail closed to empty
        role_allowed = False
    try:
        listed = rules.list_experiments(
            person_id,
            role_allowed=role_allowed or person_id == OWNER,
            db_path=rule_db_path,
        )
    except rules.IntelRuleError:
        listed = rules._empty_summary()  # noqa: SLF001 — honest empty on read miss

    note_count = int(listed.get("note_count") or 0)
    approval_count = int(listed.get("approval_count") or 0)
    stub_count = int(listed.get("stub_count") or 0)
    experiments = listed.get("experiments") or []

    if note_count == 0:
        status = "EMPTY"
        message = spec["empty_message"]
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    elif approval_count == 0:
        status = "WAITING_APPROVAL"
        message = spec["waiting_approval_message"]
        tags = ["WAITING_APPROVAL"]
        empty = False
        next_label = "Review experiment notes for approval"
        next_code = "review_approvals"
    elif stub_count == 0:
        status = "WAITING_DATA"
        message = (
            "Approvals exist without a versioned stub. "
            "Approval is not an adopted live rule."
        )
        tags = ["WAITING_DATA", "WAITING_APPROVAL"]
        empty = False
        next_label = "Record a versioned rule stub after approval"
        next_code = "stub_after_approval"
    else:
        status = "WAITING_DATA"
        message = spec["stub_message"]
        tags = ["WAITING_DATA"]
        empty = False
        next_label = "Review stubs on Intel Ops (not live rules)"
        next_code = "review_stubs"

    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=next_label,
        next_href=spec["href"],
        next_code=next_code,
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = note_count == 0
    strip["note_count"] = note_count
    strip["approval_count"] = approval_count
    strip["stub_count"] = stub_count
    strip["promoted_count"] = int(listed.get("promoted_count") or 0)
    strip["executed_count"] = int(listed.get("executed_count") or 0)
    strip["live"] = False
    strip["live_rule"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": note_count,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "live_learning": False,
            "adopted_rule": False,
            "performance_proof": False,
            "auto_promote": False,
            "stub_not_live": True,
            "experiment_count": len(experiments),
            "numbers": None,
        },
    }


def _ops_pack_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    base: dict[str, Any],
    pack_db_path: Path | str | None = None,
    rule_db_path: Path | str | None = None,
) -> dict[str, Any]:
    today = ops.today_strip(pack_db_path)
    last = today.get("last_ask") if isinstance(today, dict) else None
    has_ask = isinstance(last, dict) and bool(last.get("ask_id") or last.get("question"))
    try:
        queue = ops.queue_summary(
            verified_person_id=person_id,
            rule_db_path=rule_db_path,
        )
    except ops.IntelOpsPackError:
        queue = {"count": 0, "note_count": 0, "live": False}

    if not has_ask and int(queue.get("note_count") or 0) == 0:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"]
        empty = True
        message = spec["empty_message"]
    elif not has_ask:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = (
            "Approve-to-rule notes exist without a recent Intel Ops ask. "
            "Queue objects are not live learning proof."
        )
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = (
            "Intel Ops has an ask strip. Ask / recall / note handoff is not "
            "CAP-INTEL-05 PROVEN and not performance policy evidence."
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
    strip["unwired"] = empty
    strip["has_ask"] = has_ask
    strip["queue_count"] = int(queue.get("count") or 0)
    strip["live"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": int(queue.get("note_count") or 0),
        "live": False,
        "module_honesty": {
            "empty": empty,
            "ops_pack_bound": ops.BOUND,
            "cluster_bound": BOUND,
            "distinct_from_p4": True,
            "au_wolf_started": False,
            "live_learning": False,
            "numbers": None,
        },
    }


def _connective_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
) -> dict[str, Any]:
    """P4 connective is DONE wire — honest, not learning proof."""
    flags = connect.honesty_flags()
    surfaces = list(connect.SURFACES)
    status = "WAITING_DATA"
    tags = ["WAITING_DATA"]
    message = spec["empty_message"]
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=spec["next_label"],
        next_href=spec["href"],
        next_code=spec["next_code"],
    )
    strip["empty"] = False
    strip["status_tags"] = tags
    strip["unwired"] = False
    strip["p4_done"] = True
    strip["surfaces"] = surfaces
    strip["changes_work"] = bool(flags.get("changes_work"))
    strip["orphan_dashboard"] = False
    strip["learning_policy_v1_relaunched"] = False
    strip["live_learning"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": False,
        "recorded_count": len(surfaces),
        "live": False,
        "module_honesty": {
            "empty": False,
            "p4_connective_done": True,
            "p4_reopened": False,
            "learning_policy_v1_blocked": True,
            "learning_policy_v1_relaunched": False,
            "live_learning": False,
            "adopted_rule": False,
            "auto_promote": False,
            "auto_execute": False,
            "numbers": None,
        },
    }


def _module_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    rule_db_path: Path | str | None = None,
    pack_db_path: Path | str | None = None,
) -> dict[str, Any]:
    maturity = _ledger_cap(spec["cap"], ledger_path)
    cr = _cr_row(spec["cr"], catalog_db)
    handoff = _module_handoff(spec, cr)
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
    if spec["kind"] == "approve_to_rule":
        return _approve_to_rule_card(
            spec, person_id=person_id, base=base, rule_db_path=rule_db_path
        )
    if spec["kind"] == "ops_pack":
        return _ops_pack_card(
            spec,
            person_id=person_id,
            base=base,
            pack_db_path=pack_db_path,
            rule_db_path=rule_db_path,
        )
    if spec["kind"] == "connective":
        return _connective_card(spec, base=base)
    raise MgmtClusterError(f"Unknown module kind {spec['kind']}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "ops", "label": "Ops desk", "href": "/intel-ops-pack"},
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
            "label": "No further learning-policy action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "intel_mgmt",
        "lede": (
            "INTEL learning-policy cluster — experiment notes, Intel Ops handoff, "
            "and P4 connective. Empty stays empty. Stub is not a live rule."
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
            "auto_promote": False,
            "auto_execute": False,
        },
        "history_evidence_handover": {
            "ok": True,
            "invented": False,
            "items": [],
            "empty": True,
            "why": (
                "Management cluster is compose-only; experiment history lives on "
                "approve-to-rule / Intel Ops."
            ),
            "empty_state": sru.empty_with_next(
                "No management history strip here.",
                next_label="Open Intel Ops",
                next_href="/intel-ops-pack",
                next_code="open_ops_pack",
            ),
        },
    }


def build_desk(
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    rule_db_path: Path | str | None = None,
    pack_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one staff-readable INTEL learning-policy management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            person_id=seat["person_id"],
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            rule_db_path=rule_db_path,
            pack_db_path=pack_db_path,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.classify_text(
        "INTEL learning-policy management cluster — Owner approval intentional "
        "authority; route attention labels only; do not invent Owner controls away",
        has_staff_seat=False,
    )
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    cap05 = _ledger_cap(CAP_05, ledger_path)
    cap01 = _ledger_cap(CAP_01, ledger_path)
    cr05 = _cr_row(CR_05, catalog_db)
    cr_au = _cr_row(CR_AU, catalog_db)

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
            "founder_dep_class": empire["class"],
            "founder_dep_reason": empire["reason"],
            "safe_implement": empire["safe_implement"],
            "invented_owner_control_away": False,
            "pack": "INTEL",
            "attention_count": empty_count,
            "label": (
                f"{empire['class']}: route learning-policy attention to Owner "
                "intel desk — labels only, Owner controls not removed."
            ),
        },
        "caps": {
            CAP_01: {"maturity": cap01, "raised": False},
            CAP_02: {"maturity": _ledger_cap(CAP_02, ledger_path), "raised": False},
            CAP_03: {"maturity": _ledger_cap(CAP_03, ledger_path), "raised": False},
            CAP_04: {"maturity": _ledger_cap(CAP_04, ledger_path), "raised": False},
            CAP_05: {
                "maturity": cap05,
                "cr": CR_05,
                "cr_state": cr05.get("state"),
                "raised": False,
            },
        },
        "crs": {
            CR_05: {
                "state": cr05.get("state"),
                "resolved": cr05.get("state") == "RESOLVED",
            },
            CR_AU: {
                "state": cr_au.get("state"),
                "resolved": cr_au.get("state") == "RESOLVED",
                "au": AU_WOLF,
                "started": False,
            },
        },
        "crs_open": [
            cid
            for cid, row in (
                (CR_05, cr05),
                (CR_AU, cr_au),
            )
            if row.get("state") == "OPEN"
        ],
        "crs_resolved_here": False,
        "distinction": {
            "p4_connective": "DONE — AKR/DM wired into BZG/GGV/AMG; not this pack",
            "learning_policy_v1": (
                "BLOCKED factory-failure inspect_retry_ceiling — not relaunched"
            ),
            "this_pack": (
                "Auto-INTEL Learning Policy Management Cluster composition for "
                f"{CR_05} / {CAP_05}"
            ),
        },
        "honesty": honesty_flags(),
        "schema": schema_document(),
        "nav": phone_nav(),
        "money": None,
        "proven": False,
        "ready": False,
        "auto_promote": False,
        "auto_execute": False,
        "learning_proof": None,
        "adopted_rule": None,
        "performance": None,
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
    rule_db_path: Path | str | None = None,
    pack_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                person_id=seat["person_id"],
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                rule_db_path=rule_db_path,
                pack_db_path=pack_db_path,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")
