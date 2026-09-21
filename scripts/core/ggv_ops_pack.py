#!/usr/bin/env python3
"""GGV operator loop v1 — Beta :8788 only.

Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), armed plan
docs/deliveries/GROK-PLAN-SPRINT-TRACK-B-GGV-OPS-PACK-2026-09-21.md.

One vertical pack. Reuses Lead Spine lifecycle, the speed-to-lead read
model, and the Habitat publish gate as a read. Bound beta-ggv-ops-safe.

Does not write Metricool, Klaviyo, or an external CRM. Does not invent a
lead, an SLA breach, PROVEN, or READY. Does not resolve a completion row.
CAP-GGV-04 stays at the ledger value. An empty client/project framework
is not live profitability.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import content_publish as _content_publish
from core import lead_spine as _lead_spine

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-ggv-ops-safe"
CAP_ID = "CAP-GGV-04"
CR_ID = "CR-f089b11530ab4673"
CLIENT_CR_ID = "CR-ccb3287dabe91d4b"
SCHEMA_ID = "wolf.ggv-ops-pack.v1"
HABITAT = "habitat"

OWNER = "PERS-MATT"
AMANDA = "PERS-AMANDA"
HAIKAL = "PERS-HAIKAL"
MISA = "PERS-MISA"

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
    "slice": "ggv_ops_pack_v1",
    "slice_label": "BUILT",
    "habitat_only": True,
    "invented_leads": False,
    "invented_sla": False,
    "invented_proven": False,
    "invented_ready": False,
    "closed_is_not_a_sale": True,
    "empty_is_profitability": False,
    "live_profitability": False,
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
}


class OpsPackError(ValueError):
    """Fail closed. Does not invent a lead, an SLA, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


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
        "additionalProperties": False,
        "writes_accepted": False,
        "metricool_property": False,
        "klaviyo_property": False,
        "crm_property": False,
        "proven_property": False,
        "ready_property": False,
        "lifecycle_requires_next_action": True,
        "stages": list(STAGES),
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
    speed = _lead_spine.speed_to_lead_signal(lead, now=now)
    card["recorded_next_action"] = recorded
    card["suggested_next_action"] = suggested
    card["next_action_required_on_lifecycle"] = True
    card["speed"] = speed
    card["aging"] = aging_exception(lead, now=now)
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
        return {
            "ok": True,
            "brand_id": HABITAT,
            "seat": seat,
            "permissions": permission_matrix(),
            "stages": list(STAGES),
            "board": by_stage,
            "unstaged": unstaged,
            "leads": cards,
            "count": len(cards),
            "empty": len(cards) == 0,
            "exceptions": speed_exceptions(c, now=clock),
            "isolation": brand_isolation(c),
            "framework": client_project_framework(),
            "publish_gate": publish_gate_strip(c, verified_person_id=verified_person_id),
            "schema": schema_document(),
            "honesty": flags,
            **_quiet(),
        }
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
