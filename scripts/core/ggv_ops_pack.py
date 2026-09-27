#!/usr/bin/env python3
"""GGV operator loop v1 + Sprint2 P2 loop closure + lead operator depth — Beta :8788 only.

Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), armed plans
docs/deliveries/GROK-PLAN-SPRINT-TRACK-B-GGV-OPS-PACK-2026-09-21.md,
docs/deliveries/GROK-PLAN-SPRINT2-P2-GGV-LOOP-CLOSURE-2026-09-22.md, and
docs/deliveries/GROK-PLAN-SPRINT2-P2-GGV-OPERATOR-DEPTH-2026-09-22.md.

One vertical pack. Reuses Lead Spine lifecycle, the speed-to-lead read
model, and the Habitat publish gate as a read. Ops bound beta-ggv-ops-safe;
loop closure / operator depth bound beta-ggv-loop-safe.

Does not write Metricool, Klaviyo, or an external CRM. Does not invent a
lead, an SLA breach, PROVEN, or READY. Does not resolve a completion row.
CAP-GGV-04 stays at the ledger value. An empty client/project framework
is not live profitability.

GGV Ops × Needs-You connective (beta-ggv-loop-safe) projects GGV-scoped
commissioning / content / lead rows onto this desk. Owner sees the full
GGV-scoped set. Other Habitat seats see only rows that name them. EMPTY
when none. next_action prefers an in-scope row over the generic pack href.
Detail and acknowledge reuse the Needs-You operator state (or the existing
content / lead operator handoff). No second mutate store. No invented
staff_ready, Haikal done, or Devi done.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import content_publish as _content_publish
from core import ggv_social_derive as _social
from core import intel_connective as _intel_connect
from core import lead_spine as _lead_spine
from core import staff_ready_ux as _staff_ready

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-ggv-ops-safe"
LOOP_BOUND = "beta-ggv-loop-safe"
CAP_ID = "CAP-GGV-04"
CR_ID = "CR-f089b11530ab4673"
CLIENT_CR_ID = "CR-ccb3287dabe91d4b"
SCHEMA_ID = "wolf.ggv-ops-pack.v1"
LOOP_SCHEMA_ID = "wolf.ggv-loop-closure.v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.ggv-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "ggv_operator_depth"
CONNECTIVE_SCHEMA_ID = "wolf.ggv-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "ggv_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-ggv-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-ggv-ops-needs-you-connective-20260923"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "content",
    "lead",
)
CONNECTIVE_DEPTH_KINDS = frozenset({"morning_seed", "waiting_others", "needs_you"})
GGV_CAP_IDS: tuple[str, ...] = (
    "CAP-GGV-01",
    "CAP-GGV-03",
    "CAP-GGV-04",
    "CAP-GGV-05",
    "CAP-GGV-06",
)
GGV_TARGET_CRS: tuple[str, ...] = (
    "CR-8c1fa12404180c02",  # CAP-GGV-01
    "CR-e20099e21930b9a6",  # CAP-GGV-05
    "CR-f089b11530ab4673",  # CAP-GGV-04
    "CR-ccb3287dabe91d4b",  # CAP-GGV-03 client
    "CR-6a19c9221cab0178",  # CAP-GGV-06
)
HABITAT = "habitat"
ENTITY_GGV = "ENT-GGV"
PERM_LEAD_OPERATOR = "ggv.lead.operator"
PERM_LEAD_OPERATOR_ID = "PERM-GGV-LEAD-OPERATOR"
SCOPE_HABITAT_LEAD = "SCOPE-GGV-HABITAT-LEAD"
LEAD_OPERATOR_ROLES: tuple[str, ...] = (
    "ROLE-CONTENT-MGMT",
    "ROLE-GGV-EDIT",
    "ROLE-CONTENT-CREW",
)
LEAD_OPERATOR_ACTION_KINDS = frozenset({"next_action", "note", "ownership_touch"})
LIVE_CATALOG_DB = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()

# Full GGV operator loop (Sprint2 P2). Empty stages stay empty — never invent.
LOOP_STAGES: tuple[str, ...] = (
    "lead",
    "identity_contact",
    "qualification",
    "next_action",
    "ownership",
    "pipeline",
    "client_project",
    "proposal_engagement",
    "content_work",
    "approval",
    "publish_read",
    "performance",
    "client_visibility",
    "mgmt_exception",
)

OWNER = "PERS-MATT"
AMANDA = "PERS-AMANDA"
HAIKAL = "PERS-HAIKAL"
MISA = "PERS-MISA"
LEAD_OPERATOR_FIXTURES: tuple[str, ...] = (AMANDA, HAIKAL, MISA)

STAGES = ("OPEN", "ACTIVE", "PARKED", "CLOSED")
CLOSE_SEATS = frozenset({OWNER, AMANDA})
READ_SEATS = frozenset({OWNER, AMANDA, HAIKAL, MISA})
OPERATOR_STAGES = {
    OWNER: frozenset(STAGES),
    AMANDA: frozenset(STAGES),
    HAIKAL: frozenset({"OPEN", "ACTIVE", "PARKED"}),
    MISA: frozenset({"OPEN", "ACTIVE", "PARKED"}),
}
SEAT_LABEL = {
    OWNER: "owner",
    AMANDA: "content_management",
    HAIKAL: "editor",
    MISA: "crew",
}

KIND_IDS = ("client", "project")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

FRAMEWORK_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "client",
        "label": "Client",
        "slot": "empty",
        "evidence": None,
        "revenue": None,
        "cost": None,
        "margin": None,
        "live_profitability": False,
        "why": "Named client slot. Empty is not a live P&L and not proof of profitability.",
    },
    {
        "kind": "project",
        "label": "Project",
        "slot": "empty",
        "evidence": None,
        "revenue": None,
        "cost": None,
        "margin": None,
        "live_profitability": False,
        "why": "Named project slot. Empty is not a live project result and not proof of profitability.",
    },
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "loop_bound": LOOP_BOUND,
    "slice": "ggv_ops_pack_v1",
    "loop_slice": "ggv_loop_closure_v1",
    "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "operator_depth_slice": OPERATOR_DEPTH_SLICE,
    "slice_label": "BUILT",
    "habitat_only": True,
    "invented_leads": False,
    "invented_sla": False,
    "invented_proven": False,
    "invented_ready": False,
    "closed_is_not_a_sale": True,
    "empty_is_profitability": False,
    "live_profitability": False,
    "empty_client_visibility_is_not_live": True,
    "empty_pipeline_is_not_live": True,
    "performance_is_derive_read": True,
    "live_habitat_commission": False,
    "metricool_write": False,
    "klaviyo_write": False,
    "klaviyo_called": False,
    "external_crm_write": False,
    "production_write": False,
    "production": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "ledger_write": False,
    "anon_fail_closed": True,
    "staff_ready": False,
    "invented_staff_ready": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "invented_haikal_human": False,
    "invented_devi_done": False,
    "false_resolve_cr": False,
    "duplicate_mutate_surface": False,
    "metricool_publish": False,
    "ggv_ops_needs_you_connective": True,
    "connective_bound": LOOP_BOUND,
    "connective_schema": CONNECTIVE_SCHEMA_ID,
    "connective_claim_id": CONNECTIVE_CLAIM_ID,
    "connective_run_id": CONNECTIVE_RUN_ID,
}


class OpsPackError(ValueError):
    """Fail closed. Does not invent a lead, an SLA, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _assert_beta_db(db_path: Path | str | None) -> Path | None:
    if db_path is None:
        return None
    raw = str(db_path)
    if "wolf-system" in raw or "8787" in raw:
        raise OpsPackError("GGV ops pack refuses a non-beta path.", code="not_beta")
    path = Path(db_path)
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    low = str(resolved).lower()
    if "wolf-system" in low or "beta-os" not in low:
        raise OpsPackError("GGV ops pack refuses a non-beta database.", code="not_beta")
    return path


def _open(db_path: Path | str | None) -> sqlite3.Connection:
    _assert_beta_db(db_path)
    return _lead_spine.db_connect(db_path)


def refuse_metricool(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses a Metricool write.", code="metricool_refused")


def refuse_klaviyo(_body: dict | None = None) -> None:
    raise OpsPackError(
        "GGV ops pack refuses a Klaviyo write. The reader is not called.",
        code="klaviyo_refused",
    )


def refuse_external_crm(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses an external CRM write.", code="crm_refused")


def refuse_invent_lead(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses an invented lead.", code="invent_lead_refused")


def refuse_proven(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses an invented PROVEN mark.", code="proven_refused")


def refuse_ready(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses an invented READY mark.", code="ready_refused")


def refuse_resolve(_body: dict | None = None) -> None:
    raise OpsPackError(
        "GGV ops pack does not resolve the completion row.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise OpsPackError("GGV ops pack refuses a Production write.", code="production_refused")


def refuse_staff_ready(_body: dict | None = None) -> None:
    raise OpsPackError(
        "GGV ops pack refuses inventing staff_ready.",
        code="staff_ready_refused",
    )


def refuse_haikal_done(_body: dict | None = None) -> None:
    raise OpsPackError(
        "GGV ops pack refuses inventing Haikal human done.",
        code="haikal_done_refused",
    )


def refuse_devi_done(_body: dict | None = None) -> None:
    raise OpsPackError(
        "GGV ops pack refuses inventing Devi done.",
        code="devi_done_refused",
    )


def connective_refuse_code(path: str) -> str | None:
    """Refuse invent paths. GET /staff-ready stays the existing read surface."""
    refused = {
        "/api/ggv/ops-pack/haikal-done": "haikal_done",
        "/api/ggv/ops-pack/haikal_done": "haikal_done",
        "/api/ggv/ops-pack/devi-done": "devi_done",
        "/api/ggv/ops-pack/devi_done": "devi_done",
        "/api/ggv/ops-pack/staff_ready": "staff_ready",
        "/api/ggv/ops-pack/needs-you/staff-ready": "staff_ready",
        "/api/ggv/ops-pack/needs-you/haikal-done": "haikal_done",
        "/api/ggv/ops-pack/needs-you/devi-done": "devi_done",
        "/api/ggv/ops-pack/needs-you/proven": "proven",
        "/api/ggv/ops-pack/needs-you/ready": "ready",
        "/api/ggv/ops-pack/needs-you/metricool": "metricool",
    }
    return refused.get(path)


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("metricool") or payload.get("metricool_write") or action == "metricool":
        refuse_metricool(payload)
    if payload.get("klaviyo") or payload.get("klaviyo_write") or action == "klaviyo":
        refuse_klaviyo(payload)
    if (
        payload.get("external_crm")
        or payload.get("crm_write")
        or action in {"crm", "external_crm"}
    ):
        refuse_external_crm(payload)
    if payload.get("invent_lead") or payload.get("invent") or action in {"lead", "ingest", "invent"}:
        refuse_invent_lead(payload)
    if payload.get("proven") or action == "proven":
        refuse_proven(payload)
    if payload.get("ready") or action == "ready":
        refuse_ready(payload)
    if payload.get("resolve") or action == "resolve":
        refuse_resolve(payload)
    if payload.get("production") or action == "production":
        refuse_production(payload)
    raise OpsPackError("GGV ops pack refuses this write.", code="writes_refused")


def seat_for(person_id: str | None) -> dict[str, Any] | None:
    pid = (person_id or "").strip()
    if pid not in READ_SEATS:
        return None
    stages = sorted(OPERATOR_STAGES[pid])
    return {
        "person_id": pid,
        "seat": SEAT_LABEL[pid],
        "brand_id": HABITAT,
        "can_read": True,
        "can_close": pid in CLOSE_SEATS,
        "lifecycle": stages,
    }


def permission_matrix() -> list[dict[str, Any]]:
    return [seat_for(pid) for pid in (OWNER, AMANDA, HAIKAL, MISA)]


def require_seat(person_id: str | None, *, stage: str | None = None) -> dict[str, Any]:
    seat = seat_for(person_id)
    if seat is None:
        raise OpsPackError(
            "GGV ops pack is for Owner, Amanda, Haikal, and Misa on Habitat.",
            code="forbidden",
        )
    if stage is not None:
        ws = stage.strip().upper()
        if ws not in seat["lifecycle"]:
            who = seat["seat"]
            raise OpsPackError(
                f"{who} cannot set Wolf lifecycle to {ws}. Close is Owner or Amanda.",
                code="forbidden",
            )
    return seat


def _ledger_state(ledger_path: Path | str | None = None) -> str:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "BUILT"
    row = data.get(CAP_ID)
    if isinstance(row, list) and row and str(row[0]) in MATURITY:
        return str(row[0])
    return "BUILT"


def _ceiling(state: str) -> str:
    if state in HIGHER_THAN_BUILT:
        return state
    return "BUILT"


def _cr_state(catalog_db: Path | str | None, cr_id: str) -> str:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    _assert_beta_db(path)
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (cr_id,),
        ).fetchone()
    except sqlite3.Error:
        return "OPEN"
    finally:
        conn.close()
    if not row or not row[0]:
        return "OPEN"
    return str(row[0])


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = _ledger_state(ledger_path)
    flags = dict(HONESTY)
    flags["cr_id"] = CR_ID
    flags["cr_state"] = _cr_state(catalog_db, CR_ID)
    flags["client_cr_id"] = CLIENT_CR_ID
    flags["client_cr_state"] = _cr_state(catalog_db, CLIENT_CR_ID)
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = _ceiling(state)
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["cr_resolved"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "loop_schema_id": LOOP_SCHEMA_ID,
        "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "additionalProperties": False,
        "writes_accepted": False,
        "metricool_property": False,
        "klaviyo_property": False,
        "crm_property": False,
        "proven_property": False,
        "ready_property": False,
        "lifecycle_requires_next_action": True,
        "lead_operator_action_kinds": sorted(LEAD_OPERATOR_ACTION_KINDS),
        "stages": list(STAGES),
        "loop_stages": list(LOOP_STAGES),
        "loop_bound": LOOP_BOUND,
    }


def _quiet() -> dict[str, Any]:
    return {
        "invented_leads": False,
        "invented_sla": False,
        "sla_breached": None,
        "sla_target_seconds": None,
        "empty_is_profitability": False,
        "live_profitability": False,
        "revenue": None,
        "cost": None,
        "margin": None,
        "metricool_write": False,
        "klaviyo_write": False,
        "klaviyo_called": False,
        "external_crm_write": False,
        "production_write": False,
        "cr_resolved": False,
        "invented_proven": False,
        "invented_ready": False,
        "proven": False,
        "ready": False,
        "closed_is_not_a_sale": True,
        "bound": BOUND,
    }


def client_project_framework() -> dict[str, Any]:
    """Named client and project slots. Every slot stays empty."""
    return {
        "ok": True,
        "empty": True,
        "recorded_count": 0,
        "rows": [],
        "kinds": [dict(row) for row in FRAMEWORK_KINDS],
        "empty_is_profitability": False,
        "live_profitability": False,
        "revenue": None,
        "cost": None,
        "margin": None,
        "on_disk": False,
        "cap_ggv_03_not_rewritten": True,
        "why": "An empty client/project framework is not live profitability.",
    }


def _recorded_next_action(conn: sqlite3.Connection, lead_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT payload_json FROM core_lead_events
        WHERE lead_id=? AND event_type='next_action_linked'
        ORDER BY recorded_at DESC, event_id DESC
        LIMIT 1
        """,
        (lead_id,),
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        payload = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    text = payload.get("next_action")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _habitat_leads(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM core_leads
        WHERE brand_id=?
        ORDER BY wolf_ingested_at DESC, lead_id ASC
        """,
        (HABITAT,),
    ).fetchall()
    return [dict(r) for r in rows]


def operator_card(
    lead: dict[str, Any],
    *,
    conn: sqlite3.Connection,
    now: datetime | None = None,
) -> dict[str, Any]:
    card = _lead_spine.lead_operator_card(lead, conn=conn)
    recorded = _recorded_next_action(conn, str(lead.get("lead_id") or ""))
    suggested = _lead_spine.next_action_for_lead(lead)
    loop_next = _lead_spine.loop_next_action_for_lead(lead, conn=conn)
    lead_id = str(lead.get("lead_id") or "")
    # Sprint2 P4: AKR + Decision Memory + provider fail-safe change the next action.
    intel_next = _intel_connect.attach_to_next_action(
        "ggv",
        loop_next,
        context={"lead_id": lead_id},
    )
    speed = _lead_spine.speed_to_lead_signal(lead, now=now)
    card["recorded_next_action"] = recorded
    card["suggested_next_action"] = suggested
    card["loop_next_action_base"] = loop_next
    card["loop_next_action"] = intel_next
    card["intel_recommendation"] = intel_next.get("intel_recommendation")
    card["next_action_required_on_lifecycle"] = True
    card["speed"] = speed
    card["aging"] = aging_exception(lead, now=now)
    card["loop"] = loop_progress(lead, conn=conn, now=now)
    card["closed_is_not_a_sale"] = True
    return card


def aging_exception(
    lead: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Needs-you only when a source clock and a wait are both already on the lead.

    A missing clock is unavailable. It is not an SLA breach.
    """
    clock = now or datetime.now(timezone.utc)
    speed = _lead_spine.speed_to_lead_signal(lead, now=clock)
    wolf = (lead.get("wolf_stage") or "").strip().upper()
    observed = (lead.get("source_observed_at") or "").strip()
    base = {
        "needs_you": False,
        "kind": "not_an_exception",
        "sla_breached": None,
        "sla_target_seconds": None,
        "words": speed.get("words") or "unavailable",
        "waiting_seconds": speed.get("waiting_seconds"),
        "reason": "No SLA target is stored.",
    }
    if not observed or speed.get("status") == "UNAVAILABLE":
        base["reason"] = "No authorised source clock. This is not an SLA breach."
        base["waiting_seconds"] = None
        return base
    if wolf in ("PARKED", "CLOSED"):
        base["reason"] = "Parked and closed leads are not a Needs You exception."
        return base
    if speed.get("status") == "WAITING" and speed.get("waiting_seconds") is not None:
        base["needs_you"] = True
        base["kind"] = "needs_you"
        base["reason"] = "Waiting on a recorded source time. No SLA target is stored."
        return base
    return base


def speed_exceptions(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    exceptions: list[dict[str, Any]] = []
    unavailable = 0
    for lead in _habitat_leads(conn):
        aging = aging_exception(lead, now=clock)
        if aging["needs_you"]:
            card = operator_card(lead, conn=conn, now=clock)
            exceptions.append(
                {
                    "lead_id": card.get("lead_id"),
                    "demo_label": card.get("demo_label"),
                    "wolf_lifecycle": card.get("wolf_lifecycle"),
                    "owner": card.get("owner"),
                    "aging": aging,
                    "recorded_next_action": card.get("recorded_next_action"),
                }
            )
        elif aging["reason"].startswith("No authorised source clock"):
            unavailable += 1
    exceptions.sort(
        key=lambda row: (
            -float((row.get("aging") or {}).get("waiting_seconds") or 0),
            str(row.get("lead_id") or ""),
        )
    )
    return {
        "ok": True,
        "brand_id": HABITAT,
        "exceptions": exceptions,
        "count": len(exceptions),
        "empty": len(exceptions) == 0,
        "unavailable_clocks": unavailable,
        "empty_message": (
            "No Habitat lead is waiting on a recorded source time."
            if len(exceptions) == 0
            else None
        ),
        "sla_breached": None,
        "sla_target_seconds": None,
        "invented_sla": False,
        "unavailable_is_not_a_breach": True,
    }


def brand_isolation(conn: sqlite3.Connection) -> dict[str, Any]:
    """Board cards are Habitat only. Other brands are counts, never cards."""
    rows = conn.execute(
        "SELECT brand_id, COUNT(*) AS n FROM core_leads GROUP BY brand_id"
    ).fetchall()
    counts = {str(r[0]): int(r[1]) for r in rows}
    habitat_n = int(counts.get(HABITAT, 0))
    others = {brand: n for brand, n in counts.items() if brand != HABITAT}
    return {
        "ok": True,
        "board_brand": HABITAT,
        "habitat_lead_count": habitat_n,
        "other_brand_lead_rows": others,
        "other_brand_cards": [],
        "isolated": True,
        "external_crm_not_read": True,
        "catalog_count_is_not_external_crm": True,
    }


def publish_gate_strip(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str,
    limit: int = 8,
) -> dict[str, Any]:
    """Read Habitat planner gate status. Does not enable Metricool."""
    mc = _content_publish.metricool_write_status()
    lim = max(1, min(int(limit), 20))
    try:
        slots = conn.execute(
            """
            SELECT id, brand, platform, title_slug, status
            FROM content_planner
            WHERE lower(COALESCE(brand, ''))=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (HABITAT, lim),
        ).fetchall()
    except sqlite3.Error as exc:
        raise OpsPackError(f"publish gate read failed: {exc}", code="publish_read_failed") from exc
    items: list[dict[str, Any]] = []
    for row in slots:
        slot_id = int(row[0])
        try:
            gate = _content_publish.assert_habitat_publish_allowed(
                slot_id,
                verified_person_id=verified_person_id,
                conn=conn,
            )
        except _content_publish.ContentPublishError as exc:
            gate = {"ok": False, "stage": "DENIED", "reason": exc.code}
        items.append(
            {
                "slot_id": slot_id,
                "brand": row[1],
                "platform": row[2],
                "title_slug": row[3],
                "legacy_status": row[4],
                "gate_stage": gate.get("stage"),
                "gate_ok": gate.get("ok") is True,
                "reason": gate.get("reason"),
                "metricool": "DISABLED",
                "write_performed": False,
            }
        )
    return {
        "ok": True,
        "brand_id": HABITAT,
        "items": items,
        "count": len(items),
        "empty": len(items) == 0,
        "metricool_write": False,
        "metricool_status_read": mc.get("status"),
        "real_external_publish": "NO",
        "approved_is_not_published": True,
    }


def build_board(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise OpsPackError("now must be timezone-aware", code="invalid")
    own = conn is None
    c = conn or _open(db_path)
    try:
        leads = _habitat_leads(c)
        cards = [operator_card(lead, conn=c, now=clock) for lead in leads]
        by_stage = {stage: [] for stage in STAGES}
        unstaged = []
        for card in cards:
            stage = str(card.get("wolf_lifecycle") or "none").upper()
            if stage in by_stage:
                by_stage[stage].append(card)
            else:
                unstaged.append(card)
        flags = honesty_flags(catalog_db=db_path)
        primary_next = None
        if cards:
            primary_next = cards[0].get("loop_next_action_base") or cards[0].get(
                "loop_next_action"
            )
        intel_strip = _intel_connect.desk_intel_strip(
            "ggv",
            base_next=primary_next if isinstance(primary_next, dict) else None,
        )
        board_payload = {
            "ok": True,
            "brand_id": HABITAT,
            "seat": seat,
            "permissions": permission_matrix(),
            "stages": list(STAGES),
            "loop_stages": list(LOOP_STAGES),
            "board": by_stage,
            "unstaged": unstaged,
            "leads": cards,
            "count": len(cards),
            "empty": len(cards) == 0,
            "exceptions": speed_exceptions(c, now=clock),
            "management_exceptions": management_exceptions(c, now=clock),
            "isolation": brand_isolation(c),
            "framework": client_project_framework(),
            "client_visibility": client_visibility_strip(),
            "publish_gate": publish_gate_strip(c, verified_person_id=verified_person_id),
            "content_work": content_work_strip(c, verified_person_id=verified_person_id),
            "performance": performance_strip(verified_person_id=verified_person_id),
            "engagement_scaffold": engagement_scaffold(),
            "loop": loop_desk(c, verified_person_id=verified_person_id, now=clock),
            "intel_connective": intel_strip,
            "schema": schema_document(),
            "honesty": flags,
            "loop_bound": LOOP_BOUND,
            "intel_bound": _intel_connect.BOUND,
            **_quiet(),
        }
        # Sprint2 P6: phone-first staff surface (terminology / empty+next / history).
        board_payload["staff_ready"] = _staff_ready.staff_surface_ggv(board_payload)
        board_payload["staff_ready_bound"] = _staff_ready.BOUND
        connective = needs_you_connective_strip(
            verified_person_id=verified_person_id,
            conn=c,
            db_path=db_path,
        )
        pack_next = _pack_href_next()
        preferred = connective.get("next_action") if connective.get("count") else None
        board_payload["needs_you_connective"] = connective
        board_payload["pack_next_action"] = pack_next
        board_payload["next_action"] = (
            preferred if isinstance(preferred, dict) else pack_next
        )
        return board_payload
    finally:
        if own:
            c.close()


def move_lifecycle(
    lead_id: str,
    wolf_stage: str,
    next_action: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Move OPEN/ACTIVE/PARKED/CLOSED only when a next action is recorded."""
    ws = (wolf_stage or "").strip().upper()
    if ws not in _lead_spine.WOLF_STAGES:
        raise OpsPackError(
            "wolf_stage must be OPEN, ACTIVE, PARKED, or CLOSED.",
            code="invalid_stage",
        )
    text = (next_action or "").strip()
    if not text:
        raise OpsPackError(
            "A next action is required before the Wolf lifecycle changes.",
            code="next_action_required",
        )
    _lead_spine._refuse_inference({"next_action": text})
    seat = require_seat(verified_person_id, stage=ws)
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = _lead_spine.get_lead(lead_id, conn=c)
        if not lead:
            raise OpsPackError("lead not found", code="not_found")
        if (lead.get("brand_id") or "") != HABITAT:
            raise OpsPackError(
                "This pack moves Habitat leads only.",
                code="brand_isolated",
            )
        before_source = lead.get("source_stage")
        result = _lead_spine.set_wolf_stage(
            lead_id,
            ws,
            verified_person_id=verified_person_id,
            actor_type="PERSON",
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        event = _lead_spine.append_event(
            lead_id,
            "next_action_linked",
            payload={"next_action": text, "wolf_stage": ws},
            actor_type="PERSON",
            actor_person_id=verified_person_id,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        after = result.get("lead") or _lead_spine.get_lead(lead_id, conn=c)
        if after and after.get("source_stage") != before_source:
            raise OpsPackError("source_stage mutated", code="append_only_violation")
        card = operator_card(after or lead, conn=c)
        return {
            "ok": True,
            "action": "lifecycle",
            "seat": seat,
            "lead": card,
            "recorded_next_action": text,
            "event": event,
            "closed_is_not_a_sale": ws == "CLOSED",
            **_quiet(),
            "honesty": honesty_flags(catalog_db=db_path),
        }
    finally:
        if own:
            c.close()


def guard_brand(brand_id: str | None) -> None:
    bid = (brand_id or "").strip()
    if bid and bid != HABITAT:
        raise OpsPackError(
            "This pack reads Habitat only. Other brands stay off the board.",
            code="brand_isolated",
        )


def _habitat_lead_or_raise(conn: sqlite3.Connection, lead_id: str) -> dict[str, Any]:
    lead = _lead_spine.get_lead(lead_id, conn=conn)
    if not lead:
        raise OpsPackError("lead not found", code="not_found")
    if (lead.get("brand_id") or "") != HABITAT:
        raise OpsPackError(
            "This pack moves Habitat leads only.",
            code="brand_isolated",
        )
    return lead


def _stage_status(done: bool, *, empty_ok: bool = False) -> str:
    if done:
        return "done"
    return "empty" if empty_ok else "ready"


def loop_progress(
    lead: dict[str, Any],
    *,
    conn: sqlite3.Connection,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Per-lead loop stage board from recorded facts only."""
    clock = now or datetime.now(timezone.utc)
    lead_id = str(lead.get("lead_id") or "")
    touch = bool((lead.get("first_human_touch_at") or "").strip())
    owner = bool((lead.get("owner_person_id") or "").strip())
    wolf = (lead.get("wolf_stage") or "").strip().upper()
    has_identity = _lead_spine.has_event(
        lead_id, "identity_contact_noted", conn=conn
    ) or _lead_spine.has_event(lead_id, "match_candidate_recorded", conn=conn)
    has_qual = _lead_spine.has_event(lead_id, "qualification_recorded", conn=conn)
    has_next = bool(_recorded_next_action(conn, lead_id))
    has_engage = _lead_spine.has_event(lead_id, "engagement_recorded", conn=conn)
    has_due = _lead_spine.has_event(lead_id, "due_recorded", conn=conn)
    has_mgmt = _lead_spine.has_event(lead_id, "mgmt_exception_raised", conn=conn)
    aging = aging_exception(lead, now=clock)
    qual_payload = _lead_spine.latest_event_payload(
        lead_id, "qualification_recorded", conn=conn
    )
    engage_payload = _lead_spine.latest_event_payload(
        lead_id, "engagement_recorded", conn=conn
    )
    due_payload = _lead_spine.latest_event_payload(lead_id, "due_recorded", conn=conn)
    stages = {
        "lead": {
            "status": "done",
            "words": "Lead exists on Habitat board.",
        },
        "identity_contact": {
            "status": _stage_status(has_identity),
            "words": (
                "Identity/contact noted."
                if has_identity
                else "No identity/contact note yet. External CRM not written."
            ),
        },
        "qualification": {
            "status": _stage_status(has_qual),
            "decision": (qual_payload or {}).get("decision"),
            "words": (
                f"Qualification recorded: {(qual_payload or {}).get('decision')}."
                if has_qual
                else "Qualification not recorded."
            ),
        },
        "next_action": {
            "status": _stage_status(has_next),
            "recorded": _recorded_next_action(conn, lead_id),
            "words": (
                "Next action recorded."
                if has_next
                else "Next action required before lifecycle moves."
            ),
        },
        "ownership": {
            "status": _stage_status(owner),
            "owner_person_id": lead.get("owner_person_id"),
            "words": "Owner assigned." if owner else "Owner unassigned.",
        },
        "pipeline": {
            "status": "done" if wolf in STAGES else "ready",
            "wolf_lifecycle": wolf or "none",
            "words": f"Pipeline lifecycle: {wolf or 'none'}.",
        },
        "client_project": {
            "status": "empty",
            "words": "Client/project framework stays empty. Not live profitability.",
            "live_profitability": False,
        },
        "proposal_engagement": {
            "status": _stage_status(has_engage, empty_ok=True),
            "kind": (engage_payload or {}).get("kind"),
            "words": (
                f"Engagement noted: {(engage_payload or {}).get('kind')}."
                if has_engage
                else "Proposal/engagement scaffold empty. Not a contract."
            ),
            "revenue": None,
            "contract": False,
        },
        "content_work": {
            "status": "read",
            "words": "Content work is the Habitat planner read. Metricool write stays off.",
        },
        "approval": {
            "status": "read",
            "words": "Approval is the publish-gate stage read. Approved is not published.",
        },
        "publish_read": {
            "status": "read",
            "words": "Publish/read boundary is a read. Real external publish is NO.",
            "metricool_write": False,
        },
        "performance": {
            "status": "read",
            "words": "Performance is a DERIVE read of stored Metricool rows. NULL is not zero.",
            "invented_metrics": False,
        },
        "client_visibility": {
            "status": "empty",
            "words": "Client visibility strip is empty. Empty is not a live client report.",
            "live_client_report": False,
        },
        "mgmt_exception": {
            "status": (
                "raised"
                if has_mgmt or aging.get("needs_you")
                else ("due" if has_due else "quiet")
            ),
            "needs_you": bool(aging.get("needs_you")),
            "due_at": (due_payload or {}).get("due_at"),
            "raised": has_mgmt,
            "sla_breached": None,
            "words": (
                "Management exception surface active."
                if has_mgmt or aging.get("needs_you")
                else "No management exception on this lead."
            ),
        },
    }
    return {
        "lead_id": lead_id,
        "stages": stages,
        "order": list(LOOP_STAGES),
        "loop_next_action": _lead_spine.loop_next_action_for_lead(lead, conn=conn),
        "touched": touch,
        "bound": LOOP_BOUND,
        "invented": False,
    }


def loop_desk(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """One desk: lead → … → management exception for Habitat leads."""
    clock = now or datetime.now(timezone.utc)
    cards = [
        loop_progress(lead, conn=conn, now=clock) for lead in _habitat_leads(conn)
    ]
    return {
        "ok": True,
        "brand_id": HABITAT,
        "bound": LOOP_BOUND,
        "stages": list(LOOP_STAGES),
        "leads": cards,
        "count": len(cards),
        "empty": len(cards) == 0,
        "person_id": verified_person_id,
        "why": (
            "Operator loop from recorded Habitat facts. Empty stages stay empty. "
            "No external CRM, Metricool, or Klaviyo write."
        ),
        "invented_leads": False,
        "metricool_write": False,
        "klaviyo_write": False,
        "external_crm_write": False,
    }


def engagement_scaffold() -> dict[str, Any]:
    return {
        "ok": True,
        "empty": True,
        "kinds": [
            {
                "kind": "proposal",
                "slot": "empty",
                "why": "Proposal note slot. A note is not a signed contract or revenue.",
            },
            {
                "kind": "engagement",
                "slot": "empty",
                "why": "Engagement note slot. Empty is not a live engagement.",
            },
            {
                "kind": "scope",
                "slot": "empty",
                "why": "Scope note slot. Empty is not a billed scope.",
            },
        ],
        "revenue": None,
        "contract": False,
        "live_engagement": False,
        "why": "Proposal/engagement scaffold. Operator notes only. Not a sale.",
    }


def client_visibility_strip() -> dict[str, Any]:
    return {
        "ok": True,
        "empty": True,
        "rows": [],
        "recorded_count": 0,
        "live_client_report": False,
        "client_dashboard": False,
        "revenue": None,
        "why": (
            "Client visibility strip is empty on purpose. "
            "Empty is not a live client report and not profitability."
        ),
    }


def content_work_strip(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str,
) -> dict[str, Any]:
    """Content → approval → publish/read as one continuous strip (read only)."""
    gate = publish_gate_strip(conn, verified_person_id=verified_person_id)
    return {
        "ok": True,
        "brand_id": HABITAT,
        "items": gate.get("items") or [],
        "count": gate.get("count") or 0,
        "empty": gate.get("empty") is True,
        "approval_is_gate_stage": True,
        "publish_read_boundary": True,
        "approved_is_not_published": True,
        "metricool_write": False,
        "real_external_publish": "NO",
        "why": (
            "Content/marketing work reads the Habitat planner gate. "
            "Approval is the gate stage. Publish stays a read boundary."
        ),
    }


def performance_strip(*, verified_person_id: str) -> dict[str, Any]:
    """DERIVE read of stored Habitat performance. Does not call Metricool."""
    try:
        view = _social.derive_view(
            HABITAT,
            person_id=verified_person_id,
            role_allowed=True,
        )
    except _social.SocialDeriveError as exc:
        return {
            "ok": True,
            "brand_id": HABITAT,
            "available": False,
            "empty": True,
            "metricool_called": False,
            "metricool_write": False,
            "invented_metrics": False,
            "paid_ads_spend": None,
            "error": exc.code,
            "message": str(exc),
            "why": "Performance derive refused. Absence is not zero.",
        }
    surfaces = view.get("by_surface") or view.get("by_network") or {}
    return {
        "ok": True,
        "brand_id": HABITAT,
        "available": bool(view.get("available")),
        "empty": not bool(view.get("available")),
        "authorised": view.get("authorised"),
        "metricool_called": False,
        "metricool_write": False,
        "invented_metrics": False,
        "paid_ads_spend": None,
        "blended_score": None,
        "missing_information": view.get("missing_information") or [],
        "note": view.get("note"),
        "surfaces_present": sorted(surfaces.keys()) if isinstance(surfaces, dict) else [],
        "why": (
            "Performance is a DERIVE read of stored Metricool rows. "
            "NULL is not zero. This strip does not write Metricool."
        ),
    }


def management_exceptions(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Management exception strip: Needs You, missing ownership/next action, operator due, raised."""
    clock = now or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for lead in _habitat_leads(conn):
        lead_id = str(lead.get("lead_id") or "")
        wolf = (lead.get("wolf_stage") or "").strip().upper()
        if wolf in ("PARKED", "CLOSED"):
            continue
        card = operator_card(lead, conn=conn, now=clock)
        aging = card.get("aging") or {}
        owner = (lead.get("owner_person_id") or "").strip()
        touch = (lead.get("first_human_touch_at") or "").strip()
        next_action = card.get("recorded_next_action")
        due_payload = _lead_spine.latest_event_payload(
            lead_id, "due_recorded", conn=conn
        )
        raised = _lead_spine.latest_event_payload(
            lead_id, "mgmt_exception_raised", conn=conn
        )
        reasons: list[str] = []
        if aging.get("needs_you"):
            reasons.append("needs_you_waiting")
        if touch and not owner:
            reasons.append("touched_without_owner")
        if wolf in ("OPEN", "ACTIVE") and not next_action:
            reasons.append("missing_next_action")
        overdue = False
        due_at = (due_payload or {}).get("due_at") if due_payload else None
        if due_at:
            try:
                due_dt = _lead_spine._parse_ts(str(due_at))
                if due_dt <= clock:
                    overdue = True
                    reasons.append("operator_due_passed")
            except (TypeError, ValueError):
                pass
        if raised:
            reasons.append("operator_raised")
        if not reasons:
            continue
        rows.append(
            {
                "lead_id": lead_id,
                "demo_label": card.get("demo_label"),
                "wolf_lifecycle": card.get("wolf_lifecycle"),
                "owner": card.get("owner"),
                "reasons": reasons,
                "aging": aging,
                "due_at": due_at,
                "overdue": overdue,
                "raised_reason": (raised or {}).get("reason"),
                "owner_person_id": lead.get("owner_person_id"),
                "recorded_next_action": next_action,
                "loop_next_action": card.get("loop_next_action"),
                "sla_breached": None,
                "sla_target_seconds": None,
                "invented_sla": False,
            }
        )
    rows.sort(key=lambda r: (0 if r.get("overdue") else 1, str(r.get("lead_id") or "")))
    return {
        "ok": True,
        "brand_id": HABITAT,
        "bound": LOOP_BOUND,
        "exceptions": rows,
        "count": len(rows),
        "empty": len(rows) == 0,
        "empty_message": (
            "No Habitat management exceptions."
            if len(rows) == 0
            else None
        ),
        "sla_breached": None,
        "sla_target_seconds": None,
        "invented_sla": False,
        "owner_visibility": True,
        "why": (
            "Management exceptions from recorded waiting, missing ownership/next action, "
            "operator due, or an explicit raise. No invented SLA breach."
        ),
    }


def _loop_action_result(
    *,
    action: str,
    seat: dict[str, Any],
    lead: dict[str, Any],
    event: dict[str, Any] | None,
    conn: sqlite3.Connection,
    db_path: Path | str | None,
) -> dict[str, Any]:
    card = operator_card(lead, conn=conn)
    return {
        "ok": True,
        "action": action,
        "seat": seat,
        "lead": card,
        "event": event,
        "loop": card.get("loop"),
        "loop_bound": LOOP_BOUND,
        "closed_is_not_a_sale": True,
        **_quiet(),
        "honesty": honesty_flags(catalog_db=db_path),
    }


def note_identity_contact(
    lead_id: str,
    note: str,
    *,
    contact_kind: str = "contact",
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.record_identity_contact(
            lead_id,
            note,
            contact_kind=contact_kind,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="identity_contact",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def qualify_lead(
    lead_id: str,
    decision: str,
    note: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.record_qualification(
            lead_id,
            decision,
            note,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="qualification",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def record_proposal_engagement(
    lead_id: str,
    kind: str,
    note: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.record_engagement(
            lead_id,
            kind,
            note,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="engagement",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def set_due(
    lead_id: str,
    due_at: str,
    note: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.record_due(
            lead_id,
            due_at,
            note,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="due",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def raise_management_exception(
    lead_id: str,
    reason: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.record_mgmt_exception(
            lead_id,
            reason,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="mgmt_exception",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


def assign_loop_owner(
    lead_id: str,
    owner_person_id: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    oid = (owner_person_id or "").strip()
    if not oid:
        raise OpsPackError("owner_person_id required", code="invalid")
    if oid not in READ_SEATS and not oid.startswith("PERS-"):
        raise OpsPackError("owner_person_id invalid", code="invalid")
    own = conn is None
    c = conn or _open(db_path)
    try:
        _habitat_lead_or_raise(c, lead_id)
        result = _lead_spine.assign_owner(
            lead_id,
            oid,
            verified_person_id=verified_person_id,
            operator_auth=_lead_spine.PACK_OPERATOR_AUTH,
            conn=c,
        )
        return _loop_action_result(
            action="assign",
            seat=seat,
            lead=result["lead"],
            event=result.get("event"),
            conn=c,
            db_path=db_path,
        )
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
    finally:
        if own:
            c.close()


# ---------------------------------------------------------------------------
# Sprint2 P2 GGV Lead Operator Depth — detail/action + consequence refresh
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
        raise OpsPackError(
            "test mode refuses writes to live catalog DB; point CATALOG_DB at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def lead_operator_href(lead_id: str | None) -> str:
    key = (lead_id or "").strip()
    if not key:
        return "/ggv-ops-pack#loop"
    return f"/ggv-ops-pack#lead-{key}"


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
    """Idempotent grant: ggv.lead.operator on Content/Sales GGV staff roles + Habitat brand scope.

    Beta catalog only. Does not mint CF Access seats. Does not commission live Habitat.
    """
    own = conn is None
    c = conn or _open(db_path)
    try:
        ts = _now_utc_iso()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_LEAD_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_LEAD_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_HABITAT_LEAD,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='brand' AND target_id=?
                """,
                (SCOPE_HABITAT_LEAD, HABITAT),
            ).fetchone()
        )
        roles_ok = all(_role_has_perm(c, role_id, op_id) for role_id in LEAD_OPERATOR_ROLES)
        fixture_asg: dict[str, str | None] = {}
        for pid in LEAD_OPERATOR_FIXTURES:
            asg = c.execute(
                """
                SELECT a.assignment_id
                FROM org_assignments a
                JOIN org_positions po ON po.position_id = a.position_id
                WHERE a.person_id=? AND po.role_id IN (?, ?, ?)
                  AND a.status='ACTIVE' AND a.end_at IS NULL
                LIMIT 1
                """,
                (pid, *LEAD_OPERATOR_ROLES),
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
                (asg_id, SCOPE_HABITAT_LEAD),
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
                "grants": [PERM_LEAD_OPERATOR],
                "roles": list(LEAD_OPERATOR_ROLES),
                "permission_ids": {PERM_LEAD_OPERATOR: op_id},
                "scope_id": SCOPE_HABITAT_LEAD,
                "unchanged": True,
                "live_habitat_commission": False,
                "bound": LOOP_BOUND,
            }

        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        assert_catalog_writable(db_file)

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'ggv.lead', 'operator',
              'Lead operator detail, next-action, notes, ownership-touch on Habitat (no CRM write)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_LEAD_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_LEAD_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'brand', 'GGV Habitat lead operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_HABITAT_LEAD, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'brand', ?, ?)
            """,
            (SCOPE_HABITAT_LEAD, HABITAT, ts),
        )
        for role_id in LEAD_OPERATOR_ROLES:
            role = c.execute(
                "SELECT role_id, status FROM org_roles WHERE role_id=?",
                (role_id,),
            ).fetchone()
            if not role:
                raise OpsPackError(
                    f"{role_id} missing — GGV staff role required",
                    code="role_missing",
                    http_status=500,
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
                raise OpsPackError(
                    f"fixture assignment missing for {pid}",
                    code="assignment_missing",
                    http_status=500,
                )
            c.execute(
                """
                INSERT OR IGNORE INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (asg_id, SCOPE_HABITAT_LEAD, ts, ts, ts),
            )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_LEAD_OPERATOR],
            "roles": list(LEAD_OPERATOR_ROLES),
            "permission_ids": {PERM_LEAD_OPERATOR: op_id},
            "scope_id": SCOPE_HABITAT_LEAD,
            "unchanged": False,
            "live_habitat_commission": False,
            "bound": LOOP_BOUND,
        }
    finally:
        if own:
            c.close()


def prove_lead_operator(
    *,
    person_id: str = AMANDA,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove Amanda/Haikal/Misa can run lead-operator actions. No live Habitat commission."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _open(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip() or AMANDA
        seat = seat_for(pid)
        target = {"entity_id": ENTITY_GGV, "brand_id": HABITAT}
        can_operator = bool(_rbac.can(pid, PERM_LEAD_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id IN (?, ?, ?)
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, *LEAD_OPERATOR_ROLES),
        ).fetchone()
        role_id = str(asg["role_id"]) if asg else None
        allowed = can_operator or pid == OWNER
        return {
            "ok": True,
            "bound": LOOP_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "person_id": pid,
            "seat": seat,
            "role_id": role_id,
            "assignment_active": bool(asg) or pid == OWNER,
            "can_lead_operator": allowed,
            "pack_seat": seat is not None,
            "actions": {
                "lead_operator": allowed and seat is not None,
                "next_action": allowed and seat is not None,
                "note": allowed and seat is not None,
                "ownership_touch": allowed and seat is not None,
                "crm_write": False,
                "metricool_write": False,
                "klaviyo_write": False,
                "invent_lead": False,
            },
            "live_habitat_commission": False,
            "human_commissioning": "NOT_DONE",
            "target_crs": [CR_ID],
            "proven": False,
            "ready": False,
            "external_crm_write": False,
        }
    finally:
        if own:
            c.close()


def _require_lead_operator(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str,
) -> dict[str, Any]:
    from core import rbac as _rbac

    seat = require_seat(verified_person_id)
    pid = seat["person_id"]
    ensure_operator_depth_rbac(conn=conn, commit=False)
    if pid == OWNER:
        return seat
    target = {"entity_id": ENTITY_GGV, "brand_id": HABITAT}
    if not _rbac.can(pid, PERM_LEAD_OPERATOR, target, conn=conn):
        raise OpsPackError(
            f"permission denied: {PERM_LEAD_OPERATOR}",
            code="forbidden",
            http_status=403,
        )
    return seat


def speed_to_lead_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Speed-to-lead projection from Habitat leads only. Empty ≠ invent."""
    clock = now or datetime.now(timezone.utc)
    leads = _habitat_leads(conn)
    rows = []
    for lead in leads:
        speed = _lead_spine.speed_to_lead_signal(lead, now=clock)
        rows.append(
            {
                "lead_id": lead.get("lead_id"),
                "demo_label": _lead_spine._demo_label(lead.get("provenance_json")),
                "wolf_lifecycle": lead.get("wolf_stage"),
                "speed": speed,
                "waiting": speed.get("status") == "WAITING",
                "measured": speed.get("status") == "MEASURED",
                "invented_sla": False,
            }
        )
    waiting = [r for r in rows if r["waiting"]]
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "empty": len(rows) == 0,
        "count": len(rows),
        "waiting_count": len(waiting),
        "rows": rows[:40],
        "sla_breached": None,
        "sla_target_seconds": None,
        "invented_sla": False,
        "invented_leads": False,
        "empty_message": (
            "No Habitat leads — speed-to-lead consequence is empty (not invent)."
            if len(rows) == 0
            else None
        ),
        "why": "Speed-to-lead from recorded Habitat clocks only. Missing clock is unavailable, not an SLA breach.",
    }


def pipeline_consequence(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pipeline consequence projection: ownership / next-action / stage facts. Empty honesty."""
    clock = now or datetime.now(timezone.utc)
    leads = _habitat_leads(conn)
    by_stage = {stage: 0 for stage in STAGES}
    missing_next = 0
    missing_owner = 0
    rows = []
    for lead in leads:
        stage = str(lead.get("wolf_stage") or "").upper()
        if stage in by_stage:
            by_stage[stage] += 1
        lead_id = str(lead.get("lead_id") or "")
        recorded = _recorded_next_action(conn, lead_id)
        owner = (lead.get("owner_person_id") or "").strip() or None
        if not recorded and stage in ("OPEN", "ACTIVE"):
            missing_next += 1
        if not owner and stage in ("OPEN", "ACTIVE"):
            missing_owner += 1
        rows.append(
            {
                "lead_id": lead_id,
                "demo_label": _lead_spine._demo_label(lead.get("provenance_json")),
                "wolf_lifecycle": stage or None,
                "owner_person_id": owner,
                "recorded_next_action": recorded,
                "loop_next_action": _lead_spine.loop_next_action_for_lead(lead, conn=conn),
                "speed": _lead_spine.speed_to_lead_signal(lead, now=clock),
            }
        )
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "empty": len(rows) == 0,
        "count": len(rows),
        "by_stage": by_stage,
        "missing_next_action": missing_next,
        "missing_owner": missing_owner,
        "rows": rows[:40],
        "invented_leads": False,
        "empty_pipeline_is_not_live": True,
        "live_pipeline": False,
        "empty_message": (
            "No Habitat leads — pipeline consequence is empty (not invent)."
            if len(rows) == 0
            else None
        ),
        "why": (
            "Pipeline consequence from Habitat lead facts + recorded next actions. "
            "Empty is not a live CRM pipeline."
        ),
    }


def list_lead_operator_actions(
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
          'ownership_touch_recorded'
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
    """Lead operator detail/action path. No CRM write. No invent leads."""
    own = conn is None
    c = conn or _open(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        lead = _habitat_lead_or_raise(c, lead_id)
        pid = (verified_person_id or "").strip() or None
        seat = seat_for(pid) if pid else None
        actions = {
            "lead_operator": False,
            "next_action": False,
            "note": False,
            "ownership_touch": False,
            "crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invent_lead": False,
        }
        if pid and seat is not None:
            prove = prove_lead_operator(person_id=pid, conn=c)
            actions.update(prove.get("actions") or {})
        card = operator_card(lead, conn=c, now=now)
        prior = list_lead_operator_actions(str(lead.get("lead_id") or ""), conn=c)
        events = _lead_spine.list_lead_events(str(lead.get("lead_id") or ""), conn=c)
        return {
            "ok": True,
            "bound": LOOP_BOUND,
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
            "href": lead_operator_href(str(lead.get("lead_id") or "")),
            "speed_consequence": speed_to_lead_consequence(c, now=now),
            "pipeline_consequence": pipeline_consequence(c, now=now),
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invented_leads": False,
            "live_habitat_commission": False,
            "proven": False,
            "ready": False,
            "honesty": honesty_flags(catalog_db=db_path),
        }
    finally:
        if own:
            c.close()


def record_lead_operator_action(
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
    """Record allowed next-action / note / ownership-touch. Refreshes consequence projections.

    No CRM / Metricool / Klaviyo write. Does not invent leads.
    """
    k = (kind or "").strip().lower()
    if k not in LEAD_OPERATOR_ACTION_KINDS:
        raise OpsPackError(
            f"kind must be one of {sorted(LEAD_OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise OpsPackError("verified_person_id required", code="missing_verified_person")
    key = (lead_id or "").strip()
    if not key:
        raise OpsPackError("lead_id required", code="missing_lead")

    own = conn is None
    c = conn or _open(db_path)
    try:
        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or db_path or CATALOG_DB)
        assert_catalog_writable(db_file)
        seat = _require_lead_operator(c, verified_person_id=pid)
        lead = _habitat_lead_or_raise(c, key)
        before_source = lead.get("source_stage")
        event: dict[str, Any] | None = None

        if k == "next_action":
            if not text:
                raise OpsPackError("next_action note required", code="missing_note")
            _lead_spine._refuse_inference({"next_action": text})
            event = _lead_spine.append_event(
                key,
                "next_action_linked",
                payload={
                    "next_action": text,
                    "wolf_stage": lead.get("wolf_stage"),
                    "external_crm_write": False,
                    "operator_depth": True,
                },
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "note":
            if not text:
                raise OpsPackError("note required", code="missing_note")
            # Inline note append — avoid nested commit from record_note when we own conn.
            event = _lead_spine.append_event(
                key,
                "note_recorded",
                payload={"note": text, "external_crm_write": False, "operator_depth": True},
                actor_type="PERSON",
                actor_person_id=pid,
                verified_person_id=pid,
                require_perm=False,
                conn=c,
            )
        elif k == "ownership_touch":
            touch_ts = (touched_at or "").strip() or _now_utc_iso()
            observed = (lead.get("source_observed_at") or "").strip()
            if observed:
                # First human touch when missing; always append ownership_touch event.
                if lead.get("first_human_touch_at") is None:
                    try:
                        touch_dt = _lead_spine._parse_ts(touch_ts)
                        observed_dt = _lead_spine._parse_ts(observed)
                    except (TypeError, ValueError) as exc:
                        raise OpsPackError(
                            "unparseable touch chronology",
                            code="invalid_chronology",
                        ) from exc
                    if touch_dt < observed_dt:
                        raise OpsPackError(
                            "touched_at before source_observed_at",
                            code="invalid_chronology",
                        )
                    c.execute(
                        "UPDATE core_leads SET first_human_touch_at=? WHERE lead_id=?",
                        (touch_ts, key),
                    )
                    event = _lead_spine.append_event(
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
                event = _lead_spine.append_event(
                    key,
                    "ownership_touch_recorded",
                    payload={
                        "note": text or None,
                        "touched_at": touch_ts,
                        "person_id": pid,
                        "external_crm_write": False,
                        "operator_depth": True,
                    },
                    actor_type="PERSON",
                    actor_person_id=pid,
                    verified_person_id=pid,
                    require_perm=False,
                    conn=c,
                )
            else:
                if not text:
                    text = "Ownership touch recorded without source_observed_at clock."
                event = _lead_spine.append_event(
                    key,
                    "ownership_touch_recorded",
                    payload={
                        "note": text,
                        "touched_at": touch_ts,
                        "person_id": pid,
                        "external_crm_write": False,
                        "source_clock": "unavailable",
                        "operator_depth": True,
                    },
                    actor_type="PERSON",
                    actor_person_id=pid,
                    verified_person_id=pid,
                    require_perm=False,
                    conn=c,
                )

        after = _lead_spine.get_lead(key, conn=c) or lead
        if after.get("source_stage") != before_source:
            raise OpsPackError("source_stage mutated", code="append_only_violation")
        card = operator_card(after, conn=c)
        speed = speed_to_lead_consequence(c)
        pipeline = pipeline_consequence(c)
        if commit:
            c.commit()
        return {
            "ok": True,
            "action": "lead_operator",
            "kind": k,
            "seat": seat,
            "lead": card,
            "event": event,
            "speed_consequence": speed,
            "pipeline_consequence": pipeline,
            "loop": card.get("loop"),
            "loop_bound": LOOP_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "invented_leads": False,
            "live_habitat_commission": False,
            "closed_is_not_a_sale": True,
            **_quiet(),
            "honesty": honesty_flags(catalog_db=db_path),
        }
    except _lead_spine.LeadSpineError as exc:
        raise OpsPackError(str(exc), code=exc.code) from exc
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
    """Operator depth desk: RBAC prove + lead candidates + consequence honesty."""
    own = conn is None
    c = conn or _open(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (verified_person_id or "").strip() or AMANDA
        prove = prove_lead_operator(person_id=pid, conn=c)
        clock = now or datetime.now(timezone.utc)
        leads = _habitat_leads(c)
        candidates = []
        for lead in leads:
            card = operator_card(lead, conn=c, now=clock)
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
                    "href": lead_operator_href(str(card.get("lead_id") or "")),
                }
            )
        speed = speed_to_lead_consequence(c, now=clock)
        pipeline = pipeline_consequence(c, now=clock)
        return {
            "ok": True,
            "bound": LOOP_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "rbac": prove,
            "lead_candidates": candidates[:20],
            "lead_candidate_count": len(candidates),
            "speed_consequence": speed,
            "pipeline_consequence": pipeline,
            "target_crs": [CR_ID],
            "invented_leads": False,
            "empty_pipeline_is_not_live": True,
            "live_habitat_commission": False,
            "external_crm_write": False,
            "metricool_write": False,
            "klaviyo_write": False,
            "proven": False,
            "ready": False,
            "why": (
                "GGV lead operator depth: Habitat lead detail/action path + next-action/"
                "note/ownership-touch recording that refreshes speed-to-lead and pipeline "
                "consequence projections. No invent leads. No CRM/Metricool/Klaviyo write. "
                "No live Habitat seat commissioning on this path."
            ),
            "honesty": honesty_flags(catalog_db=db_path),
        }
    finally:
        if own:
            c.close()


_NAME_RE = re.compile(r"[a-z]+")
_SEAT_NAME_TOKENS: dict[str, frozenset[str]] = {
    OWNER: frozenset({"matt", "owner"}),
    AMANDA: frozenset({"amanda"}),
    HAIKAL: frozenset({"haikal"}),
    MISA: frozenset({"misa"}),
}


def _name_tokens(*parts: Any) -> set[str]:
    blob = " ".join(str(p or "") for p in parts).lower()
    return set(_NAME_RE.findall(blob))


def _needs_you_module():
    from core import owner_progress_needs_you_depth as nye

    return nye


def _morning_meta() -> dict[str, dict[str, Any]]:
    from core import owner_commissioning_queue as ocq

    return {str(t.get("id")): t for t in ocq.seed_templates() if t.get("id")}


def _is_ggv_scoped(item: dict[str, Any]) -> bool:
    """GGV commissioning, Habitat content, or Habitat lead. Other businesses stay out."""
    cap = str(item.get("capability") or "")
    if cap.startswith("CAP-GGV"):
        return True
    if str(item.get("business") or "").upper() == "GGV":
        return True
    if str(item.get("domain") or "").upper() == "GGV":
        return True
    if str(item.get("brand_id") or "") == HABITAT and item.get("kind") in {"content", "lead"}:
        return True
    surface = str(item.get("surface") or "").lower()
    if surface in {"ggv_ops", "nas_library", "smart_upload"}:
        return True
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "source", "open_href", "route", "object_id")
    ).lower()
    if "habitat content" in blob or "habitat-operator" in blob or "habitat-publish" in blob:
        return True
    if "/ggv-ops" in blob or "/ggv/" in blob:
        return True
    return False


def _named_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every GGV-scoped row. Other seats see rows that name them."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    owner_pid = str(item.get("owner_person_id") or "").strip()
    if owner_pid and owner_pid == seat.get("person_id"):
        return True
    allowed = set(_SEAT_NAME_TOKENS.get(seat.get("person_id") or "", frozenset()))
    if not allowed:
        return False
    tokens = _name_tokens(
        item.get("who"),
        item.get("audience"),
        item.get("person_to_test"),
    )
    return bool(tokens & allowed)


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_content_ops": kind == "content",
        "reuse_lead_operator": kind == "lead",
    }
    if kind in CONNECTIVE_DEPTH_KINDS:
        block.update(
            {
                "detail": f"/api/progress/needs-you/items/{oid}",
                "acknowledge": f"/api/progress/needs-you/items/{oid}/acknowledge",
                "staff_detail": f"/api/staff/ops-routing/needs-you/items/{oid}",
                "staff_acknowledge": f"/api/staff/ops-routing/needs-you/items/{oid}/acknowledge",
                "ggv_detail": f"/api/ggv/ops-pack/needs-you/items/{oid}",
                "ggv_acknowledge": f"/api/ggv/ops-pack/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "content":
        block.update(
            {
                "detail": f"/api/content/ops-depth/objects/{oid}/operator",
                "action": f"/api/content/ops-depth/objects/{oid}/operator-action",
            }
        )
    elif kind == "lead":
        block.update(
            {
                "detail": f"/api/ggv/ops-pack/leads/{oid}/operator",
                "action": f"/api/ggv/ops-pack/leads/{oid}/operator-action",
            }
        )
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    href = item.get("open_href") or item.get("href") or "/ggv-ops-pack"
    return {
        "object_id": oid,
        "kind": item.get("kind"),
        "title": item.get("title"),
        "who": item.get("who"),
        "audience": item.get("audience"),
        "priority": item.get("priority"),
        "status": item.get("operator_status") or item.get("status"),
        "href": href,
        "owner_person_id": item.get("owner_person_id"),
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "metricool_publish": False,
        "handoff": _handoff_block(item),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/ggv-ops-pack"
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope GGV Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "ggv_ops_needs_you_connective",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "metricool_publish": False,
    }


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Habitat desk",
        "href": "/ggv-ops-pack",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
    }


def _empty_connective(*, why: str) -> dict[str, Any]:
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "empty": True,
        "count": 0,
        "by_kind": {k: 0 for k in CONNECTIVE_KINDS},
        "items": [],
        "next_action": None,
        "empty_message": why,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "metricool_publish": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
    }


def _sort_connective(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        kind_rank = {
            "morning_seed": 0,
            "waiting_others": 1,
            "needs_you": 2,
            "content": 3,
            "lead": 4,
        }.get(str(it.get("kind") or ""), 9)
        pri = {"P0": 0, "P1": 1, "P2": 2}.get(str(it.get("priority") or ""), 5)
        return (kind_rank, pri, str(it.get("object_id") or ""))

    items.sort(key=sort_key)
    return items


def _commissioning_rows(*, state_path=None) -> list[dict[str, Any]]:
    nye = _needs_you_module()
    meta = _morning_meta()
    rows = nye.collect_candidates(state_path=state_path, include_parked=False)
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("kind") not in CONNECTIVE_DEPTH_KINDS:
            continue
        merged = dict(row)
        extra = meta.get(str(row.get("object_id") or "")) or {}
        for key in ("business", "surface", "capability", "person_to_test", "route"):
            if extra.get(key) and not merged.get(key):
                merged[key] = extra[key]
        if not merged.get("who") and extra.get("person_to_test"):
            merged["who"] = extra.get("person_to_test")
        if not _is_ggv_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "GGV"
        out.append(merged)
    return out


def _content_rows(*, catalog_db=None) -> list[dict[str, Any]]:
    if catalog_db is not None:
        try:
            if Path(catalog_db).resolve() != CATALOG_DB.resolve():
                return []
        except OSError:
            return []
    try:
        from core import ggv_content_ops_depth as content

        payload = content.content_desk_needs_you_consequence(catalog_db=None)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for row in payload.get("items") or []:
        if not isinstance(row, dict):
            continue
        oid = str(row.get("object_id") or "")
        if not oid:
            continue
        out.append(
            {
                "object_id": oid,
                "kind": "content",
                "title": row.get("staff_title") or oid,
                "who": None,
                "audience": None,
                "priority": "P1",
                "status": "OPEN",
                "business": "GGV",
                "brand_id": HABITAT,
                "href": row.get("href") or "/content-2.0",
                "open_href": row.get("href") or "/content-2.0",
                "invented": False,
                "reasons": list(row.get("reasons") or []),
            }
        )
    return out


def _lead_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    try:
        payload = management_exceptions(conn)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for row in payload.get("exceptions") or []:
        if not isinstance(row, dict):
            continue
        oid = str(row.get("lead_id") or "")
        if not oid:
            continue
        reasons = list(row.get("reasons") or [])
        if not reasons:
            continue
        priority = "P0" if "needs_you_waiting" in reasons else "P1"
        out.append(
            {
                "object_id": oid,
                "kind": "lead",
                "title": row.get("demo_label") or oid,
                "who": row.get("owner"),
                "owner_person_id": row.get("owner_person_id"),
                "audience": None,
                "priority": priority,
                "status": row.get("wolf_lifecycle") or "OPEN",
                "business": "GGV",
                "brand_id": HABITAT,
                "href": "/ggv-ops-pack#loop",
                "open_href": "/ggv-ops-pack",
                "invented": False,
                "reasons": reasons,
            }
        )
    return out


def _ggv_candidates(
    *,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(_content_rows(catalog_db=db_path))
    own = conn is None
    c = conn or _open(db_path)
    try:
        items.extend(_lead_rows(c))
    finally:
        if own:
            c.close()
    return _sort_connective(items)


def connective_cap_honesty(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    caps = {}
    for cap in GGV_CAP_IDS:
        row = data.get(cap)
        caps[cap] = str(row[0]) if isinstance(row, list) and row else "UNKNOWN"
    nye = _needs_you_module()
    progress = {cr: _cr_state(catalog_db, cr) for cr in nye.TARGET_CRS}
    ggv = {cr: _cr_state(catalog_db, cr) for cr in GGV_TARGET_CRS}
    return {
        "caps": caps,
        "ggv_crs": ggv,
        "progress_core_crs": progress,
        "false_resolve_cr": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """GGV-scoped Needs-You / Morning seed / content / lead projection.

    Owner sees the full GGV-scoped set. Amanda and other Habitat seats see
    only rows that name them. EMPTY honesty when none. Counts are the
    in-scope length.
    """
    seat = require_seat(verified_person_id)
    try:
        rows = _ggv_candidates(state_path=state_path, conn=conn, db_path=db_path)
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "GGV Needs-You connective read failed "
                f"({exc}). Count stays EMPTY. No work invented."
            )
        )
        empty["seat"] = {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        }
        return empty
    visible = [row for row in rows if _named_for_seat(row, seat)]
    projected = [_project_row(it) for it in visible]
    by_kind = {k: 0 for k in CONNECTIVE_KINDS}
    for it in visible:
        kind = str(it.get("kind") or "")
        if kind in by_kind:
            by_kind[kind] += 1
    empty = len(visible) == 0
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
            "sees_full_ggv": seat.get("person_id") == OWNER,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "empty_message": (
            "No GGV-scoped Needs-You / Morning seed / content / lead rows "
            "in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "invented": False,
        "invented_count": False,
        "source": "ggv_scoped_needs_you_morning_content_lead",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=db_path),
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "metricool_publish": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
        "why": (
            "Derived GGV-scoped commissioning, content, and lead rows. "
            "Owner sees the full GGV-scoped projection. Other seats see only "
            "rows that name them. Counts are the in-scope length."
        ),
    }


def _find_ggv_item(
    object_id: str,
    *,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _ggv_candidates(state_path=state_path, conn=conn, db_path=db_path):
        if str(row.get("object_id") or "") == oid:
            return row
    return None


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of GGV seat scope is 403. Reuses existing handoffs."""
    seat = require_seat(verified_person_id)
    found = _find_ggv_item(
        object_id, state_path=state_path, conn=conn, db_path=db_path
    )
    if found is None:
        raise OpsPackError(
            f"GGV Needs-You item '{object_id}' not found.",
            code="not_found",
        )
    if not _named_for_seat(found, seat):
        raise OpsPackError(
            "GGV Needs-You item is outside this seat's scope.",
            code="forbidden",
        )
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        },
        "object": _project_row(found),
        "handoff": _handoff_block(found),
        "reuse_needs_you_depth": str(found.get("kind") or "") in CONNECTIVE_DEPTH_KINDS,
        "duplicate_mutate_surface": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "metricool_publish": False,
        "caps": connective_cap_honesty(catalog_db=db_path),
    }


def acknowledge_handoff(
    object_id: str,
    *,
    verified_person_id: str,
    note: str | None = None,
    state_path=None,
    events_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Content and lead rows keep their existing operator actions. This route
    does not open a second mutate store. Wrong-scope seats are refused.
    """
    seat = require_seat(verified_person_id)
    found = _find_ggv_item(
        object_id, state_path=state_path, conn=conn, db_path=db_path
    )
    if found is None:
        raise OpsPackError(
            f"GGV Needs-You item '{object_id}' not found.",
            code="not_found",
        )
    if not _named_for_seat(found, seat):
        raise OpsPackError(
            "GGV Needs-You item is outside this seat's scope.",
            code="forbidden",
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise OpsPackError(
            "Content and lead rows use their existing operator action. "
            "This route does not open a second mutate surface.",
            code="handoff_only",
            http_status=405,
        )
    nye = _needs_you_module()
    recorded = nye.record_operator_action(
        str(found.get("object_id") or ""),
        verified_person_id=None,
        kind="acknowledge",
        note=note,
        state_path=state_path,
        events_path=events_path,
        catalog_db=db_path,
        connective_actor=seat["person_id"],
    )
    strip = needs_you_connective_strip(
        verified_person_id=seat["person_id"],
        state_path=state_path,
        conn=conn,
        db_path=db_path,
    )
    return {
        "ok": True,
        "bound": LOOP_BOUND,
        "recorded": True,
        "action": "acknowledge",
        "object_id": found.get("object_id"),
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        },
        "handoff": _handoff_block(found),
        "reuse_needs_you_depth": True,
        "duplicate_mutate_surface": False,
        "event": recorded.get("event"),
        "needs_you_connective": strip,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "commissioned": False,
        "cr_resolved": False,
        "metricool_publish": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "and Devi done stay uninvented."
        ),
    }
