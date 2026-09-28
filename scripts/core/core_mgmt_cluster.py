#!/usr/bin/env python3
"""Core Management Cluster desk — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + AUTO_ACCEPTED
continuous pack docs/deliveries/GROK-PLAN-AUTO-PACK-CORE-CLUSTER-2026-09-22.md
+ Sprint2 P9-v2 CORE Operator Depth
(docs/deliveries/GROK-PLAN-SPRINT2-P9-CORE-OPERATOR-DEPTH-V2-2026-09-22.md).

Composes existing Core modules (SOP factory, escalation burn-down,
core harden / commissioning honesty, optional permissions strip) into one
phone-first Owner operating loop with honesty EMPTY/UNWIRED/WAITING_DATA
strips and derived next actions.

Sprint2 P9-v2 adds operator depth: SOP / escalation detail + note /
next-action-touch / acknowledge / escalate-touch / handover-touch /
dismiss-noise recording that refreshes CORE desk next-action + Owner
Empire / staff Needs-You strips. Never money / CF / invent PROVEN/READY.

Bound beta-core-safe.

Additive compose + operator depth. Does not invent PROVEN/READY/
COMMISSIONED/ADOPTED. Does not resolve CRs. Does not raise CAP maturity
(CAP-CORE-11 stays SPECIFIED; CAP-CORE-12 stays BUILT). No money/CF/
Production. No P1/P7/Devi/w12 FIN/GGV/parked P9-v1 reopen. Does not break
Track F harden-pack. Does not touch WIP quartet.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import core_harden_pack as harden
from core import escalation_burndown as burndown
from core import founder_dep_routing as fdr
from core import sop_factory as sop
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
DEFAULT_OPERATOR_DB = BETA_ROOT / "catalog" / "core_mgmt_operator.sqlite"
LIVE_OPERATOR_DB = DEFAULT_OPERATOR_DB.resolve()

BOUND = "beta-core-safe"
SCHEMA_ID = "wolf.core-mgmt-cluster.v1"
SLICE = "core_mgmt_cluster_v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.core-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "core_operator_depth"
OWNER = "PERS-MATT"

PERM_CORE_OPERATOR = "core.operator"
PERM_CORE_OPERATOR_ID = "PERM-CORE-OPERATOR"
SCOPE_CORE_OPERATOR = "SCOPE-CORE-OPERATOR"
ROLE_CORE_OPERATORS: tuple[str, ...] = ("ROLE-MATT",)
ASG_CORE_MATT = "ASG-MATT-OWNER-1"
ENTITY_CORE = "ENT-GGV"  # Owner fixture entity (same as POS-OWNER-EXEC-1)

DEPTH_MODULE_IDS: tuple[str, ...] = (
    "sop_factory",
    "escalation_burndown",
)
CORE_OPERATOR_ACTION_KINDS = frozenset(
    {
        "note",
        "next_action",
        "acknowledge",
        "escalate_touch",
        "handover_touch",
        "dismiss_noise",
    }
)
_ACTION_KIND_ALIASES = {
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "ack": "acknowledge",
    "acknowledge": "acknowledge",
    "escalate": "escalate_touch",
    "escalate-touch": "escalate_touch",
    "escalate_touch": "escalate_touch",
    "handover": "handover_touch",
    "handover-touch": "handover_touch",
    "handover_touch": "handover_touch",
    "dismiss": "dismiss_noise",
    "dismiss-noise": "dismiss_noise",
    "dismiss_noise": "dismiss_noise",
    "note": "note",
}
OPERATOR_DISPOSITIONS = frozenset({"open", "dismissed"})

OPERATOR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS core_operator_state (
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

CREATE TABLE IF NOT EXISTS core_operator_events (
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

CREATE INDEX IF NOT EXISTS idx_core_op_events_obj
  ON core_operator_events(object_id, recorded_at DESC);
"""

# Bound CRs — stay OPEN; no false-resolve.
CR_SOP = sop.CR_ID  # CR-c4ed4e3fa9f15a40 · CAP-CORE-11
CR_ESC = burndown.CR_ID  # CR-6e3fd7b9d7edca0e · CAP-CORE-12
CR_ESC_DUP = "CR-7a022a9394592c75"  # CAP-CORE-12 duplicate OPEN

MODULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "sop_factory",
        "cap": sop.CAP_ID,
        "cr": CR_SOP,
        "title": "SOP Factory",
        "staff_title": "SOP draft → approve",
        "href": "#sop_factory",
        "kind": "sop_factory",
        "empty_message": (
            "SOP factory has no drafts yet. "
            "Empty is not a live SOP, not training, and not CAP-CORE-11 PROVEN."
        ),
        "waiting_message": (
            "SOP drafts exist. A draft is not live until an approval row exists. "
            "Not training. Not PROVEN."
        ),
        "next_label": "Draft an SOP via the factory API",
        "next_code": "draft_sop",
    },
    {
        "id": "escalation_burndown",
        "cap": burndown.CAP_ID,
        "cr": CR_ESC,
        "title": "Escalation burn-down",
        "staff_title": "Needs Matt independence",
        "href": "/escalation-burndown",
        "kind": "escalation",
        "empty_message": (
            "Escalation burn-down counters are readable. "
            "Clear windows are not an operating test and do not invent PROVEN."
        ),
        "waiting_message": (
            "Unresolved Needs Matt or unbounded delegations remain. "
            "Counters are not auto-clear and not maturity raise."
        ),
        "next_label": "Open escalation burn-down desk",
        "next_code": "open_burndown",
    },
    {
        "id": "core_harden",
        "cap": "CAP-CORE-11",
        "cr": CR_SOP,
        "title": "Commissioning honesty",
        "staff_title": "Devi / Habitat harden",
        "href": "/core-harden-pack",
        "kind": "harden",
        "empty_message": (
            "Commissioning honesty desk is lit. "
            "NOT_DONE stays NOT_DONE — not COMMISSIONED, not ADOPTED."
        ),
        "waiting_message": (
            "Human commissioning gates remain open. "
            "Opening Today does not mark the loop commissioned."
        ),
        "next_label": "Open Core Harden desk",
        "next_code": "open_harden",
    },
    {
        "id": "permissions_strip",
        "cap": "CAP-CORE-11",
        "cr": CR_SOP,
        "title": "Permissions (read-only)",
        "staff_title": "Authority / permissions",
        "href": "#permissions_strip",
        "kind": "permissions",
        "empty_message": (
            "Permissions strip is read-only compose on this desk. "
            "Empty is not a permission grant and not invented authority."
        ),
        "next_label": "Review permissions on Core Harden",
        "next_code": "open_permissions_context",
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
    "esb_write": False,
    "finance_controls": False,
    "hr": False,
    "trading": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "commission_flip": False,
    "auto_approve_sop": False,
    "sop_promoted_to_policy": False,
    "p1_reopened": False,
    "p7_reopened": False,
    "p9_v1_unparked": False,
    "devi_reopened": False,
    "w12_fin_reopened": False,
    "ggv_reopened": False,
    "intg_reopened": False,
    "bzg_reopened": False,
    "amg_reopened": False,
    "intel_reopened": False,
    "crm_reopened": False,
    "sale_reopened": False,
    "track_f_broken": False,
    "wip_quartet_touched": False,
    "anon_fail_closed": True,
    "false_resolve_cr": False,
    "core_caps_unchanged": True,
    "cf_seat_mint": False,
}


class MgmtClusterError(ValueError):
    """Fail closed. Does not invent Core management facts or maturity."""

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
        "core_operator_action_kinds": sorted(CORE_OPERATOR_ACTION_KINDS),
        "writes_accepted": False,
        "operator_actions_accepted": True,
        "money_property": False,
        "proven_property": False,
        "ready_property": False,
        "commission_flip_property": False,
        "auto_approve_sop_property": False,
        "esb_write_property": False,
        "cloudflare_mutate_property": False,
        "access_mutate_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses money, payment, bank, Finance, HR, and Trading paths.",
        code="money_refused",
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses Production mutation.",
        code="production_refused",
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses resolving completion rows.",
        code="resolve_refused",
    )


def refuse_cloudflare(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses Cloudflare / Access mutation.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster refuses commission flip / invent COMMISSIONED / ADOPTED.",
        code="commission_refused",
    )


def refuse_external_write(_body: dict[str, Any] | None = None) -> None:
    raise MgmtClusterError(
        "Core Management Cluster is compose-only. External writes are refused.",
        code="writes_refused",
    )


def refuse_code(path: str) -> str | None:
    """Map refuse path tails to refuse codes for serve_beta.

    Operator-depth / operator-action paths are not refused here — they are
    authorised Beta CORE operator writes (no money / CF / invent PROVEN).
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
        "esb": "money",
        "resolve": "resolve",
        "production": "production",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "access": "cloudflare",
        "commission": "commission",
        "commissioned": "commission",
        "adopt": "commission",
        "adopted": "commission",
        "approve": "writes",
        "auto-approve": "writes",
        "fill": "writes",
        "note": "writes",
        "current": "writes",
    }
    return mapping.get(tail)


def require_actor(person_id: str | None) -> dict[str, Any]:
    """Owner only. Staff / anon / outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise MgmtClusterError(
            "Core Management Cluster refuses anonymous callers.",
            code="forbidden",
        )
    if pid == OWNER:
        return {"person_id": pid, "seat": "owner", "label": sru.human_person(pid)}
    raise MgmtClusterError(
        "Core Management Cluster is Owner (PERS-MATT) only.",
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
        "Core management cluster routing — Owner retain",
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


def _sop_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    base: dict[str, Any],
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    listed = sop.list_sops(person_id, role_allowed=False, db_path=sop_db_path)
    count = int(listed.get("count") or 0)
    db_exists = bool(listed.get("db_exists"))
    if count == 0:
        status = "EMPTY"
        tags = ["EMPTY", "UNWIRED"] if not db_exists else ["EMPTY"]
        empty = True
        message = spec["empty_message"]
        next_label = spec["next_label"]
        next_code = spec["next_code"]
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
        next_label = "Review SOP drafts (approve gate required for live)"
        next_code = "review_sop"
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=next_label,
        next_href=spec["href"],
        next_code=next_code,
    )
    strip["empty"] = empty
    strip["status_tags"] = tags
    strip["unwired"] = not db_exists
    strip["sop_count"] = count
    strip["live"] = False
    strip["train_staff"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": count,
        "live": False,
        "module_honesty": {
            "empty": empty,
            "live_sop": False,
            "train_staff": False,
            "full_loop": sop.honesty_flags().get("full_loop") is True,
            "numbers": None,
        },
    }


def _escalation_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    report = burndown.build_report(catalog_db=catalog_db, ledger_path=ledger_path)
    needs = int(report.get("needs_matt_open") or 0)
    unbounded = int(report.get("unbounded_delegations") or 0)
    windows = report.get("windows") or []
    still_open = sum(int(w.get("still_open") or 0) for w in windows if isinstance(w, dict))
    attention = needs + unbounded + still_open
    if attention == 0:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["empty_message"]
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = spec["waiting_message"]
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=spec["next_label"],
        next_href=spec["href"],
        next_code=spec["next_code"],
    )
    # Burn-down is wired (BUILT) — not EMPTY; counters readable is not invent.
    strip["empty"] = False
    strip["status_tags"] = tags
    strip["unwired"] = False
    strip["needs_matt_open"] = needs
    strip["unbounded_delegations"] = unbounded
    strip["operating_test"] = False
    strip["proven"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": needs,
        "live": False,
        "module_honesty": {
            "empty": False,
            "operating_test": False,
            "auto_clear": False,
            "needs_matt_open": needs,
            "unbounded_delegations": unbounded,
            "numbers": None,
            "proven": False,
        },
    }


def _harden_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    base: dict[str, Any],
) -> dict[str, Any]:
    desk = harden.build_desk(verified_person_id=person_id)
    devi = desk.get("devi") or {}
    commissioned = bool(devi.get("commissioned"))
    human = str(devi.get("human_commissioning") or "NOT_READ")
    nxt = (desk.get("actions") or {}).get("next") or {}
    if commissioned:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA"]
        empty = False
        message = (
            "Commissioning gate reports commissioned in claim files. "
            "This cluster does not invent ADOPTED or raise maturity."
        )
        next_label = "Review Core Harden honesty"
        next_code = "open_harden"
        next_href = spec["href"]
    else:
        status = "WAITING_DATA"
        tags = ["WAITING_DATA", "NOT_DONE"]
        empty = False
        message = spec["waiting_message"]
        next_label = str(nxt.get("label") or spec["next_label"])
        next_code = str(nxt.get("id") or spec["next_code"])
        next_href = str(nxt.get("href") or spec["href"])
    strip = _honesty_strip(
        status=status,
        message=message,
        next_label=next_label,
        next_href=next_href,
        next_code=next_code,
    )
    strip["empty"] = False
    strip["status_tags"] = tags
    strip["unwired"] = False
    strip["human_commissioning"] = human
    strip["commissioned"] = False  # never invent; desk may say False
    strip["invented_commissioned"] = False
    strip["invented_adopted"] = False
    strip["cloudflare_mutated"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": empty,
        "recorded_count": 0 if not commissioned else 1,
        "live": False,
        "module_honesty": {
            "empty": False,
            "commissioned": False,
            "adopted": False,
            "human_commissioning": human,
            "cloudflare_write": False,
            "numbers": None,
        },
    }


def _permissions_card(
    spec: dict[str, Any],
    *,
    base: dict[str, Any],
) -> dict[str, Any]:
    strip = _honesty_strip(
        status="EMPTY",
        message=spec["empty_message"],
        next_label=spec["next_label"],
        next_href="/core-harden-pack",
        next_code=spec["next_code"],
    )
    strip["empty"] = True
    strip["status_tags"] = ["EMPTY", "UNWIRED"]
    strip["unwired"] = True
    strip["permission_grant"] = False
    strip["invented_grant"] = False
    return {
        **base,
        "honesty_strip": strip,
        "primary_next": strip["next_action"],
        "framework_empty": True,
        "recorded_count": 0,
        "live": False,
        "module_honesty": {
            "empty": True,
            "read_only": True,
            "permission_grant": False,
            "numbers": None,
        },
    }


def _module_card(
    spec: dict[str, Any],
    *,
    person_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    base = _base_card(spec, ledger_path=ledger_path, catalog_db=catalog_db)
    kind = spec["kind"]
    if kind == "sop_factory":
        return _sop_card(
            spec, person_id=person_id, base=base, sop_db_path=sop_db_path
        )
    if kind == "escalation":
        return _escalation_card(
            spec, base=base, ledger_path=ledger_path, catalog_db=catalog_db
        )
    if kind == "harden":
        return _harden_card(spec, person_id=person_id, base=base)
    if kind == "permissions":
        return _permissions_card(spec, base=base)
    raise MgmtClusterError(f"Unknown module kind {kind}", code="bad_module")


def phone_nav() -> list[dict[str, str]]:
    return [
        {"id": "now", "label": "Now", "href": "#now"},
        {"id": "needs", "label": "Needs", "href": "#needs-you-connective"},
        {"id": "operator-depth", "label": "Depth", "href": "#operator-depth"},
        {"id": "modules", "label": "Modules", "href": "#modules"},
        {"id": "handoff", "label": "Handoff", "href": "#handoff"},
        {"id": "harden", "label": "Harden", "href": "/core-harden-pack"},
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
            "label": "No further Core management action",
            "href": None,
            "invented": False,
        }
    who = desk.get("seat") or {}
    return {
        "pack": "core_mgmt",
        "lede": (
            "Core management cluster — SOP factory, escalation burn-down, "
            "commissioning honesty. Empty stays empty."
        ),
        "who_line": f"Signed in as {who.get('label') or 'Owner'}",
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
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose one Owner-facing Core management cluster desk."""
    seat = require_actor(verified_person_id)
    modules = [
        _module_card(
            spec,
            person_id=seat["person_id"],
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            sop_db_path=sop_db_path,
        )
        for spec in MODULE_SPECS
    ]
    empty_count = sum(1 for m in modules if (m.get("honesty_strip") or {}).get("empty"))
    empire = fdr.label_for_pack_handoff("CORE", empty_count)
    primary = None
    for m in modules:
        if m.get("primary_next"):
            primary = m["primary_next"]
            break

    bound_crs = (CR_SOP, CR_ESC, CR_ESC_DUP)
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
            "pack": "CORE",
            "attention_count": empty_count,
            "label": (
                f"{empire['founder_dep_class']}: Core loop attention stays with Owner — "
                "labels only, Owner desk not removed."
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
    }
    desk["staff_ready"] = staff_surface(desk)
    desk["staff_ready_bound"] = sru.BOUND
    from core import core_ops_needs_you_connective as core_nye

    core_nye._attach_needs_you_connective(
        desk,
        person_id=seat.get("person_id"),
        catalog_db=catalog_db,
        ledger_path=ledger_path,
        sop_db_path=sop_db_path,
    )
    return desk


def module_strip(
    module_id: str,
    *,
    verified_person_id: str | None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    for spec in MODULE_SPECS:
        if spec["id"] == module_id:
            card = _module_card(
                spec,
                person_id=seat["person_id"],
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                sop_db_path=sop_db_path,
            )
            return {
                "ok": True,
                "bound": BOUND,
                "module": card,
                "honesty": honesty_flags(),
            }
    raise MgmtClusterError(f"Unknown module {module_id}", code="not_found")


# ---------------------------------------------------------------------------
# Sprint2 P9-v2 — CORE operator depth (SOP / escalation)
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _under_test_process() -> bool:
    return (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1"


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


def assert_operator_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    resolved = Path(path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_OPERATOR_DB and _under_test_process():
        raise MgmtClusterError(
            "test mode refuses writes to live CORE operator DB; point operator_db at a temp copy",
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
            "CORE operator depth refuses a path outside Beta or a test fixture.",
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
        f"Unknown CORE depth object {object_id!r} "
        f"(allowed: {', '.join(DEPTH_MODULE_IDS)})",
        code="not_found",
    )


def core_object_operator_href(object_id: str | None) -> str:
    key = (object_id or "").strip()
    if not key:
        return "/core-mgmt-cluster#operator-depth"
    return f"/core-mgmt-cluster#core-obj-{key}"


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
    """Idempotent grant: core.operator on ROLE-MATT + Owner fixture scope.

    Beta catalog only. Does not mint CF Access seats. Owner fixture only.
    """
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ts = _now_utc_iso()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_CORE_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_CORE_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_CORE_OPERATOR,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='entity' AND target_id=?
                """,
                (SCOPE_CORE_OPERATOR, ENTITY_CORE),
            ).fetchone()
        )
        roles_ok = all(_role_has_perm(c, role_id, op_id) for role_id in ROLE_CORE_OPERATORS)
        asg = c.execute(
            """
            SELECT a.assignment_id, a.status, a.end_at
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.assignment_id=? AND a.person_id=? AND po.role_id=?
            """,
            (ASG_CORE_MATT, OWNER, ROLE_CORE_OPERATORS[0]),
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
                (ASG_CORE_MATT, SCOPE_CORE_OPERATOR),
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
                "grants": [PERM_CORE_OPERATOR],
                "roles": list(ROLE_CORE_OPERATORS),
                "permission_ids": {PERM_CORE_OPERATOR: op_id},
                "scope_id": SCOPE_CORE_OPERATOR,
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
            ) VALUES (?, ?, 'core', 'operator',
              'CORE SOP/escalation operator detail + note/next/ack/escalate/handover/dismiss (no invent PROVEN/auto-approve)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_CORE_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_CORE_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'entity', 'CORE Owner operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_CORE_OPERATOR, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'entity', ?, ?)
            """,
            (SCOPE_CORE_OPERATOR, ENTITY_CORE, ts),
        )
        for role_id in ROLE_CORE_OPERATORS:
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
            (ASG_CORE_MATT, SCOPE_CORE_OPERATOR, ts, ts, ts),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_CORE_OPERATOR],
            "roles": list(ROLE_CORE_OPERATORS),
            "permission_ids": {PERM_CORE_OPERATOR: op_id},
            "scope_id": SCOPE_CORE_OPERATOR,
            "unchanged": False,
            "cf_seat_mint": False,
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def prove_core_operator(
    *,
    person_id: str = OWNER,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove PERS-MATT can run CORE operator actions."""
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
        target = {"entity_id": ENTITY_CORE}
        can_operator = bool(_rbac.can(pid, PERM_CORE_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id=?
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, ROLE_CORE_OPERATORS[0]),
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
            "can_core_operator": allowed,
            "pack_seat": pack_seat,
            "actions": {
                "core_operator": allowed and pack_seat,
                "note": allowed and pack_seat,
                "next_action": allowed and pack_seat,
                "acknowledge": allowed and pack_seat,
                "escalate_touch": allowed and pack_seat,
                "handover_touch": allowed and pack_seat,
                "dismiss_noise": allowed and pack_seat,
                "auto_approve": False,
                "invent_proven": False,
                "money": False,
            },
            "cf_seat_mint": False,
            "target_crs": [CR_SOP, CR_ESC, CR_ESC_DUP],
            "proven": False,
            "ready": False,
            "auto_approve": False,
            "money": False,
        }
    finally:
        if own:
            c.close()


def _require_core_operator(
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
    target = {"entity_id": ENTITY_CORE}
    if not _rbac.can(pid, PERM_CORE_OPERATOR, target, conn=conn):
        raise MgmtClusterError(
            f"permission denied: {PERM_CORE_OPERATOR}",
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
            FROM core_operator_state
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


def list_core_operator_actions(
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
            FROM core_operator_events
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
                "auto_approve": False,
                "invented": False,
                "money": False,
            }
        )
    return out


def operator_object_card(
    object_id: str,
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
    person_id: str = OWNER,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    spec = _depth_spec(object_id)
    base = _module_card(
        spec,
        person_id=person_id,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
        sop_db_path=sop_db_path,
    )
    state = _load_operator_state(object_id, operator_db=operator_db)
    prior = events if events is not None else list_core_operator_actions(
        object_id, operator_db=operator_db
    )
    dismissed = state.get("disposition") == "dismissed"
    recorded_next = state.get("next_action")
    primary = base.get("primary_next") or {}
    if recorded_next and not dismissed:
        primary = {
            "code": "operator_next_action",
            "label": recorded_next,
            "href": core_object_operator_href(object_id),
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
        "href": core_object_operator_href(object_id),
        "auto_approve": False,
        "invented": False,
        "proven": False,
        "ready": False,
        "money": False,
    }


def core_desk_next_action_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
    person_id: str = OWNER,
) -> dict[str, Any]:
    """Refreshed CORE desk next-action after operator recording. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=person_id,
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
                "code": nxt.get("code") or "core_operator_next",
                "label": nxt.get("label"),
                "href": nxt.get("href") or card.get("href"),
                "invented": False,
                "object_id": mid,
            }
    empty = primary is None
    if empty:
        primary = {
            "code": "none",
            "label": "No CORE operator next action — EMPTY (not invent).",
            "href": "/core-mgmt-cluster#operator-depth",
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
            "No CORE SOP/escalation next action — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "proven": False,
        "ready": False,
        "money": False,
        "why": (
            "CORE desk next-action is a projection of open SOP/escalation operator "
            "depth objects (dismiss-noise drops off). Recording refreshes this strip."
        ),
    }


def owner_empire_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
    person_id: str = OWNER,
) -> dict[str, Any]:
    """Owner Empire attention strip from CORE operator work. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=person_id,
        )
        if card.get("dismissed"):
            continue
        last = card.get("last_kind")
        if not last:
            continue
        reasons: list[str] = []
        if last == "handover_touch":
            reasons.append("handover_touch")
        if last == "escalate_touch":
            reasons.append("escalate_touch")
        if last in ("note", "acknowledge") and not card.get("recorded_next_action"):
            reasons.append("missing_next_action")
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
        "pack": "CORE",
        "empty": empty,
        "count": 0 if empty else len(items),
        "attention_count": None if empty else len(items),
        "items": items,
        "empty_message": (
            "No CORE objects need Owner Empire attention — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "proven": False,
        "ready": False,
        "money": False,
        "why": (
            "Owner Empire CORE strip projects handover / escalate / missing next "
            "from SOP/escalation operator depth. Dismiss-noise drops off. "
            "Not a CAP maturity invent."
        ),
    }


def staff_needs_you_consequence(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    sop_db_path: Path | str | None = None,
    person_id: str = OWNER,
) -> dict[str, Any]:
    """Staff Needs-You strip from CORE operator work. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    for mid in DEPTH_MODULE_IDS:
        card = operator_object_card(
            mid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=person_id,
        )
        if card.get("dismissed"):
            continue
        last = card.get("last_kind")
        if last not in (
            "acknowledge",
            "escalate_touch",
            "handover_touch",
            "next_action",
            "note",
        ):
            continue
        if last is None:
            continue
        items.append(
            {
                "object_id": mid,
                "cap": card.get("cap"),
                "staff_title": card.get("staff_title"),
                "last_kind": last,
                "recorded_next_action": card.get("recorded_next_action"),
                "ledger_maturity": card.get("ledger_maturity"),
                "cr_state": card.get("cr_state"),
                "href": card.get("href"),
                "source_kind": "core_operator_depth",
                "invented": False,
                "raised_cap": False,
            }
        )
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "strip": "Needs-You",
        "empty": empty,
        "count": 0 if empty else len(items),
        "items": items,
        "empty_message": (
            "No CORE staff Needs-You signals — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "caps_raised": False,
        "proven": False,
        "ready": False,
        "money": False,
        "why": (
            "Staff Needs-You is a projection of CORE operator acknowledge / escalate / "
            "handover / next / note touches. Does not invent PROVEN/READY or raise CAP."
        ),
    }


def operator_object_detail(
    object_id: str,
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """CORE object operator detail/action path. No invent PROVEN / auto-approve."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        _depth_spec(object_id)
        pid = (verified_person_id or "").strip() or None
        actions = {
            "core_operator": False,
            "note": False,
            "next_action": False,
            "acknowledge": False,
            "escalate_touch": False,
            "handover_touch": False,
            "dismiss_noise": False,
            "auto_approve": False,
            "invent_proven": False,
            "money": False,
        }
        if pid:
            try:
                require_actor(pid)
                prove = prove_core_operator(person_id=pid, conn=catalog)
                actions.update(prove.get("actions") or {})
            except MgmtClusterError:
                pass
        prior = list_core_operator_actions(object_id, operator_db=operator_db)
        card = operator_object_card(
            object_id,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=pid or OWNER,
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
            "core_desk_next_action": core_desk_next_action_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
                sop_db_path=sop_db_path,
                person_id=pid or OWNER,
            ),
            "owner_empire": owner_empire_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
                sop_db_path=sop_db_path,
                person_id=pid or OWNER,
            ),
            "staff_needs_you": staff_needs_you_consequence(
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
                sop_db_path=sop_db_path,
                person_id=pid or OWNER,
            ),
            "auto_approve": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "money": False,
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()


def record_core_operator_action(
    *,
    verified_person_id: str,
    object_id: str,
    kind: str,
    note: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    sop_db_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record note / next / ack / escalate / handover / dismiss. Refresh strips.

    Never invent PROVEN/READY. Never auto-approve SOP. Never money/ESB/CF.
    """
    k = _normalise_action_kind(kind)
    if k not in CORE_OPERATOR_ACTION_KINDS:
        raise MgmtClusterError(
            f"kind must be one of {sorted(CORE_OPERATOR_ACTION_KINDS)}",
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
    if k in ("note", "next_action", "acknowledge", "escalate_touch", "handover_touch") and not text:
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
        seat = _require_core_operator(catalog, verified_person_id=pid)
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
        elif k == "acknowledge":
            new_note = text
        elif k == "escalate_touch":
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
            INSERT INTO core_operator_state (
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
        event_id = "CEV-" + uuid.uuid4().hex[:12]
        payload = {
            "operator_depth": True,
            "core_operator_depth": True,
            "kind": k,
            "auto_approve": False,
            "invented": False,
            "money": False,
            "esb_write": False,
        }
        op_conn.execute(
            """
            INSERT INTO core_operator_events (
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

        desk = core_desk_next_action_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
            sop_db_path=sop_db_path,
            person_id=seat["person_id"],
        )
        empire = owner_empire_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
            sop_db_path=sop_db_path,
            person_id=seat["person_id"],
        )
        needs = staff_needs_you_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
            sop_db_path=sop_db_path,
            person_id=seat["person_id"],
        )
        prior = list_core_operator_actions(key, operator_db=op_path)
        card = operator_object_card(
            key,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=op_path,
            sop_db_path=sop_db_path,
            person_id=seat["person_id"],
            events=prior,
        )
        return {
            "ok": True,
            "action": "core_operator",
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
            "core_desk_next_action": desk,
            "owner_empire": empire,
            "staff_needs_you": needs,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "auto_approve": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "money": False,
            "esb_write": False,
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
    sop_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """CORE operator depth desk: RBAC prove + depth candidates + consequence honesty."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        pid = (verified_person_id or "").strip() or OWNER
        seat = require_actor(pid)
        prove = prove_core_operator(person_id=pid, conn=catalog)
        candidates: list[dict[str, Any]] = []
        for mid in DEPTH_MODULE_IDS:
            card = operator_object_card(
                mid,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
                sop_db_path=sop_db_path,
                person_id=pid,
            )
            if card.get("dismissed"):
                continue
            candidates.append(card)
        desk = core_desk_next_action_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=pid,
        )
        empire = owner_empire_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=pid,
        )
        needs = staff_needs_you_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            sop_db_path=sop_db_path,
            person_id=pid,
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
            "core_desk_next_action": desk,
            "owner_empire": empire,
            "staff_needs_you": needs,
            "empty": empty,
            "empty_message": (
                "No CORE SOP/escalation objects for operator depth — "
                "EMPTY (not invent)."
                if empty
                else None
            ),
            "why": (
                "CORE operator depth: SOP / escalation detail + note/next-action/"
                "acknowledge/escalate/handover/dismiss recording that refreshes "
                "CORE desk next-action and Owner Empire / staff Needs-You strips. "
                "No invent PROVEN/READY. No auto-approve. No money."
            ),
            "auto_approve": False,
            "cf_seat_mint": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "money": False,
            "target_crs": [CR_SOP, CR_ESC, CR_ESC_DUP],
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()
