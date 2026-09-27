#!/usr/bin/env python3
"""AMG / Atrium hotel ops pack v1 + Sprint2 P3 day loop + operator depth — Beta :8788 only.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), armed plans
docs/deliveries/GROK-PLAN-SPRINT-TRACK-C-AMG-OPS-PACK-2026-09-21.md,
docs/deliveries/GROK-PLAN-SPRINT2-P3-AMG-DAY-LOOP-2026-09-22.md, and
docs/deliveries/GROK-PLAN-SPRINT2-P3-AMG-OPERATOR-DEPTH-2026-09-22.md.

One vertical desk loop. Reuses the daily-ops, journey, SLA, service-improve,
and PMS skeletons as reads. Desk notes, slot attention, journey tasks,
service handoffs, and day-loop objects (housekeeping, maintenance, incident,
service recovery, handover) are operator words. They are not occupancy,
ADR, RevPAR, a Yanolja write, a live PMS incident number, or a review score.

Yanolja remains PMS truth — empty arrivals/departures/occupancy stay
wait-words. Management exceptions and Owner visibility are fed from recorded
day-loop objects only. Operator depth records status/note/recovery/
handover-touch and refreshes those strips — no folio/payment/bank.

AMG Ops × Needs-You connective (beta-amg-loop-safe) projects AMG-scoped
commissioning / day-ops / SLA rows onto this desk. Owner sees the full
AMG-scoped set. Misa (day operator) sees only in-scope day-operator rows.
EMPTY when none. next_action prefers an in-scope row over the generic pack
href. Detail and acknowledge reuse the Needs-You operator state, or the
existing day-ops / SLA handoff. No second mutate store. No invented
staff_ready, Haikal done, Devi done, or live hotel occupancy.

Does not execute money, a folio, a bank move, or Zayen. Does not invent
PROVEN or READY. Does not resolve CR-bc5785d66c981fd4. CAP-AMG-* stay at
the ledger value. Ops bound beta-amg-ops-safe; day loop / operator depth
bound beta-amg-day-safe.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import amg_daily_ops_state as _ops
from core import amg_journey_workflow as _journey
from core import amg_pms_orchestration as _pms
from core import amg_service_improve as _improve
from core import amg_sla_incident as _sla
from core import intel_connective as _intel_connect
from core import staff_ready_ux as _staff_ready

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "amg_ops_pack.sqlite"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-amg-ops-safe"
DAY_BOUND = "beta-amg-day-safe"
SCHEMA_ID = "wolf.amg-ops-pack.v1"
DAY_SCHEMA_ID = "wolf.amg-day-loop.v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.amg-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "amg_operator_depth"
CONNECTIVE_SCHEMA_ID = "wolf.amg-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "amg_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-amg-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-amg-ops-needs-you-connective-20260923"
CONNECTIVE_BOUND = "beta-amg-loop-safe"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "day_ops",
    "sla",
)
CONNECTIVE_DEPTH_KINDS = frozenset({"morning_seed", "waiting_others", "needs_you"})
AMG_TARGET_CRS: tuple[str, ...] = (
    "CR-d212cdefaef81166",  # CAP-AMG-01
    "CR-ce127471ba41692b",  # CAP-AMG-02
    "CR-f346ff7449a0bd5f",  # CAP-AMG-03
    "CR-bc5785d66c981fd4",  # CAP-AMG-04
    "CR-49f6461020b693fc",  # CAP-AMG-05
    "CR-e9b3d23e63c1c8a7",  # CAP-AMG-06
    "CR-29c6ac36a9ca03f1",  # CAP-AMG-07
)
PRIMARY_CAP = "CAP-AMG-04"
PRIMARY_CR = "CR-bc5785d66c981fd4"
OWNER = "PERS-MATT"
MISA = "PERS-MISA"
BRAND = "AMG-ATR"
ENTITY = "ENT-AMG"
LOCATION = "LOC-ATRIUM-LOMBOK"
WITA = timezone(timedelta(hours=8))

PERM_DAY_OPERATOR = "amg.day.operator"
PERM_DAY_OPERATOR_ID = "PERM-AMG-DAY-OPERATOR"
SCOPE_ATR_DAY = "SCOPE-AMG-ATR-DAY"
ROLE_DAY_OPERATOR = "ROLE-AMG-GM"
DAY_OPERATOR_ROLES: tuple[str, ...] = (ROLE_DAY_OPERATOR,)
DAY_OPERATOR_FIXTURES: tuple[str, ...] = (MISA,)
DAY_OPERATOR_ACTION_KINDS = frozenset({"status", "note", "recovery", "handover_touch"})
POS_DAY_FIXTURE = "POS-AMG-DAY-OPERATOR-FIXTURE"
ASG_DAY_MISA = "ASG-AMG-DAY-MISA"

CAP_IDS = tuple(f"CAP-AMG-0{i}" for i in range(1, 8))
SLOT_IDS = _ops.KIND_IDS
JOURNEY_IDS = _journey.KIND_IDS
HANDOFF_IDS = _improve.KIND_IDS

# Operable Wolf day-loop objects (Sprint2 P3). Not PMS facts.
DAY_OBJECT_KINDS: tuple[str, ...] = (
    "housekeeping",
    "maintenance",
    "incident",
    "service_recovery",
    "handover",
)
DAY_OBJECT_STATUSES = frozenset({"OPEN", "DONE", "ESCALATED"})
DAY_OBJECT_LABELS = {
    "housekeeping": "Housekeeping",
    "maintenance": "Maintenance",
    "incident": "Incident",
    "service_recovery": "Service recovery",
    "handover": "Shift handover",
}
DAY_LOOP_STAGES: tuple[str, ...] = (
    "housekeeping",
    "maintenance",
    "incident",
    "service_recovery",
    "handover",
    "mgmt_exception",
    "owner_visibility",
)

WAIT = {
    "occupancy": "Waiting on the hotel system. This empty slot is not occupancy, ADR, or RevPAR.",
    "arrivals": "Waiting on the hotel system. This empty slot is not an arrival list.",
    "departures": "Waiting on the hotel system. This empty slot is not a departure list.",
    "in-house": "Waiting on the hotel system. This empty slot is not an in-house count.",
    "out-of-order": "Waiting on the hotel system. This empty slot is not a room status.",
    "notes": "No desk note is proof of hotel operations. An empty notes slot is not a live daily state.",
}

FACT_KEYS = frozenset(
    {
        "occupancy",
        "adr",
        "revpar",
        "yanolja",
        "yanolja_write",
        "booking_count",
        "guest_count",
        "room_number",
        "incident_number",
        "sla_timer",
        "review_score",
        "payment",
        "money",
        "amount",
        "folio",
        "bank",
        "settlement",
        "transfer",
        "zayen",
        "books",
        "payroll",
        "tax",
        "proven",
        "ready",
        "resolve",
        "production",
        "cloudflare",
        "guest_blast",
    }
)

HONESTY = {
    "cap": PRIMARY_CAP,
    "bound": BOUND,
    "day_bound": DAY_BOUND,
    "slice": "amg_ops_pack_v1",
    "day_slice": "amg_day_loop_v1",
    "slice_label": "BUILT",
    "empty_is_ops": False,
    "empty_is_hotel_state": False,
    "live_ops": False,
    "hotel_operations": False,
    "occupancy": None,
    "adr": None,
    "revpar": None,
    "yanolja_live": False,
    "yanolja_called": False,
    "yanolja_write": False,
    "yanolja_pms_truth": True,
    "invented_occupancy": False,
    "invented_adr": False,
    "invented_revpar": False,
    "invented_arrivals": False,
    "invented_departures": False,
    "invented_incident": False,
    "invented_sla": False,
    "invented_review": False,
    "invented_proven": False,
    "invented_ready": False,
    "proven": False,
    "ready": False,
    "payment_executed": False,
    "money": None,
    "folio_executed": False,
    "bank_write": False,
    "books_write": False,
    "zayen_write": False,
    "finance_controls": False,
    "production_write": False,
    "production": False,
    "cloudflare_mutated": False,
    "cr_mutated": False,
    "ledger_write": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
    "day_objects_are_ops_words": True,
    "day_object_is_not_pms_fact": True,
    "owner_visibility_from_recorded": True,
    "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "operator_depth_slice": OPERATOR_DEPTH_SLICE,
    "live_hotel_commission": False,
    "empty_day_loop_is_not_live": True,
    "folio_accepted": False,
    "payment_accepted": False,
    "staff_ready": False,
    "invented_staff_ready": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "invented_haikal_human": False,
    "invented_devi_done": False,
    "false_resolve_cr": False,
    "duplicate_mutate_surface": False,
    "amg_ops_needs_you_connective": True,
    "connective_bound": CONNECTIVE_BOUND,
    "connective_schema": CONNECTIVE_SCHEMA_ID,
    "connective_claim_id": CONNECTIVE_CLAIM_ID,
    "connective_run_id": CONNECTIVE_RUN_ID,
    "live_hotel": False,
}


class OpsPackError(ValueError):
    """Fail closed. Does not invent hotel facts, money, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _wrap(exc: Exception) -> None:
    code = getattr(exc, "code", None) or "writes_refused"
    raise OpsPackError(str(exc), code=code) from exc


def refuse_payment(_body: dict | None = None) -> None:
    try:
        _ops.refuse_payment({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_bank(_body: dict | None = None) -> None:
    try:
        _ops.refuse_bank({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_books(_body: dict | None = None) -> None:
    try:
        _ops.refuse_books({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_folio(_body: dict | None = None) -> None:
    raise OpsPackError(
        "A folio or settlement is not executed. No money moves.",
        code="folio_refused",
    )


def refuse_yanolja(_body: dict | None = None) -> None:
    try:
        _ops.refuse_yanolja({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_occupancy(_body: dict | None = None) -> None:
    try:
        _ops.invent_occupancy({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_adr(_body: dict | None = None) -> None:
    try:
        _ops.invent_adr({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_revpar(_body: dict | None = None) -> None:
    try:
        _ops.invent_revpar({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_proven(_body: dict | None = None) -> None:
    try:
        _ops.refuse_proven({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_ready(_body: dict | None = None) -> None:
    try:
        _ops.refuse_ready({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_resolve(_body: dict | None = None) -> None:
    try:
        _ops.refuse_resolve({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_production(_body: dict | None = None) -> None:
    try:
        _ops.refuse_production({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_cloudflare(_body: dict | None = None) -> None:
    try:
        _ops.refuse_cloudflare({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_guest_blast(_body: dict | None = None) -> None:
    try:
        _sla.refuse_guest_blast({})
    except _sla.SlaIncidentError as exc:
        _wrap(exc)


def refuse_staff_ready(_body: dict | None = None) -> None:
    raise OpsPackError(
        "AMG ops pack refuses inventing staff_ready.",
        code="staff_ready_refused",
    )


def refuse_haikal_done(_body: dict | None = None) -> None:
    raise OpsPackError(
        "AMG ops pack refuses inventing Haikal human done.",
        code="haikal_done_refused",
    )


def refuse_devi_done(_body: dict | None = None) -> None:
    raise OpsPackError(
        "AMG ops pack refuses inventing Devi done.",
        code="devi_done_refused",
    )


def connective_refuse_code(path: str) -> str | None:
    """Refuse invent paths. GET /staff-ready stays the existing read surface."""
    refused = {
        "/api/amg/ops-pack/haikal-done": "haikal_done",
        "/api/amg/ops-pack/haikal_done": "haikal_done",
        "/api/amg/ops-pack/devi-done": "devi_done",
        "/api/amg/ops-pack/devi_done": "devi_done",
        "/api/amg/ops-pack/staff_ready": "staff_ready",
        "/api/amg/ops-pack/needs-you/staff-ready": "staff_ready",
        "/api/amg/ops-pack/needs-you/haikal-done": "haikal_done",
        "/api/amg/ops-pack/needs-you/devi-done": "devi_done",
        "/api/amg/ops-pack/needs-you/proven": "proven",
        "/api/amg/ops-pack/needs-you/ready": "ready",
        "/api/amg/ops-pack/needs-you/occupancy": "occupancy",
        "/api/amg/ops-pack/needs-you/hotel": "occupancy",
    }
    return refused.get(path)


def refuse_fill(_body: dict | None = None) -> None:
    try:
        _ops.refuse_fill({})
    except _ops.DailyOpsStateError as exc:
        _wrap(exc)


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    _reject_facts(payload)
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if action in {"payment", "money"}:
        refuse_payment(payload)
    if action in {"bank", "transfer"}:
        refuse_bank(payload)
    if action in {"folio", "settlement"}:
        refuse_folio(payload)
    if action in {"zayen", "books"}:
        refuse_books(payload)
    if action in {"yanolja", "yanolja-write"}:
        refuse_yanolja(payload)
    if action == "occupancy":
        refuse_occupancy(payload)
    if action == "adr":
        refuse_adr(payload)
    if action == "revpar":
        refuse_revpar(payload)
    if action == "proven":
        refuse_proven(payload)
    if action == "ready":
        refuse_ready(payload)
    if action == "resolve":
        refuse_resolve(payload)
    if action == "production":
        refuse_production(payload)
    if action in {"cloudflare", "cf"}:
        refuse_cloudflare(payload)
    if action in {"guest-blast", "guest_blast"}:
        refuse_guest_blast(payload)
    if action == "fill":
        refuse_fill(payload)
    raise OpsPackError("AMG ops pack refuses this write.", code="writes_refused")


def _reject_facts(body: dict | None) -> None:
    payload = body or {}
    for key in FACT_KEYS:
        if key in payload and payload.get(key) not in (None, "", False):
            if key in {"payment", "money", "amount", "folio", "bank", "settlement", "transfer"}:
                refuse_payment(payload)
            if key in {"zayen", "books", "payroll", "tax"}:
                refuse_books(payload)
            if key in {"yanolja", "yanolja_write"}:
                refuse_yanolja(payload)
            if key == "occupancy":
                refuse_occupancy(payload)
            if key == "adr":
                refuse_adr(payload)
            if key == "revpar":
                refuse_revpar(payload)
            if key == "proven":
                refuse_proven(payload)
            if key == "ready":
                refuse_ready(payload)
            if key == "resolve":
                refuse_resolve(payload)
            if key == "production":
                refuse_production(payload)
            if key == "cloudflare":
                refuse_cloudflare(payload)
            if key == "guest_blast":
                refuse_guest_blast(payload)
            if key in {"booking_count", "guest_count", "room_number", "incident_number", "sla_timer", "review_score"}:
                raise OpsPackError(
                    "AMG ops pack does not invent a hotel, guest, incident, or review fact.",
                    code="fact_refused",
                )
            refuse_payment(payload)


def _assert_beta_path(path: Path) -> Path:
    low = str(path).lower()
    name = path.name.lower()
    if "wolf-system" in low or "8787" in low:
        raise OpsPackError("AMG ops pack refuses a non-beta path.", code="not_beta")
    if "alchemist" in low or "zayen" in low or "/production" in low or "yanolja" in low:
        raise OpsPackError("AMG ops pack refuses that path.", code="not_beta")
    if "bank" in name or "payment" in name or "folio" in name or name == "books.sqlite":
        raise OpsPackError("AMG ops pack refuses a money path.", code="not_beta")
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    try:
        resolved.relative_to(BETA_ROOT)
        return resolved
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise OpsPackError("AMG ops pack refuses a path outside Beta or a test fixture.", code="not_beta") from exc
    return resolved


def pack_db(db_path: Path | str | None = None) -> Path:
    if db_path is not None:
        return _assert_beta_path(Path(db_path))
    raw = (os.environ.get("AMG_OPS_PACK_DB") or "").strip()
    return _assert_beta_path(Path(raw) if raw else DEFAULT_DB)


def _now() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def service_day(value: str | None = None) -> str:
    text = (value or "").strip()
    if not text:
        return datetime.now(WITA).date().isoformat()
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise OpsPackError("Service day must be YYYY-MM-DD.", code="invalid")
    return text


def _connect(db_path: Path | str | None) -> sqlite3.Connection:
    path = pack_db(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure(conn)
    return conn


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS desk_notes (
          note_id TEXT PRIMARY KEY,
          body TEXT NOT NULL,
          slot_kind TEXT,
          created_by TEXT NOT NULL,
          updated_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS slot_attention (
          slot_kind TEXT PRIMARY KEY,
          attention INTEGER NOT NULL,
          reason TEXT NOT NULL,
          updated_by TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS journey_items (
          item_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          title TEXT NOT NULL,
          status TEXT NOT NULL,
          service_day TEXT NOT NULL,
          opened_by TEXT NOT NULL,
          opened_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS handoffs (
          handoff_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          note TEXT NOT NULL,
          status TEXT NOT NULL,
          opened_by TEXT NOT NULL,
          opened_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS day_objects (
          object_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          title TEXT NOT NULL,
          note TEXT NOT NULL,
          status TEXT NOT NULL,
          service_day TEXT NOT NULL,
          needs_mgmt INTEGER NOT NULL DEFAULT 0,
          mgmt_reason TEXT,
          opened_by TEXT NOT NULL,
          updated_by TEXT NOT NULL,
          opened_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_day_objects_day_kind
          ON day_objects(service_day, kind, status);
        CREATE TABLE IF NOT EXISTS day_object_events (
          event_id TEXT PRIMARY KEY,
          object_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          note TEXT,
          status_before TEXT,
          status_after TEXT,
          actor_person_id TEXT NOT NULL,
          recorded_at TEXT NOT NULL,
          payload_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_day_object_events_object
          ON day_object_events(object_id, recorded_at DESC);
        """
    )


def hotel_ops_ids(catalog_db: Path | str | None = None) -> list[str]:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return []
    _assert_beta_path(path)
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT a.person_id
            FROM org_assignments a
            JOIN org_positions pos ON pos.position_id = a.position_id
            JOIN org_persons p ON p.person_id = a.person_id
            WHERE a.status = 'ACTIVE'
              AND a.end_at IS NULL
              AND p.status = 'ACTIVE'
              AND (
                pos.entity_id = ?
                OR pos.brand_id = ?
                OR pos.location_id = ?
              )
            ORDER BY a.person_id
            """,
            (ENTITY, BRAND, LOCATION),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [str(row[0]) for row in rows]


def seat_for(person_id: str | None, catalog_db: Path | str | None = None) -> dict[str, Any] | None:
    pid = (person_id or "").strip()
    if pid == OWNER:
        return {
            "person_id": pid,
            "seat": "owner",
            "brand_id": BRAND,
            "can_read": True,
            "can_ops": True,
            "money": False,
            "assigned": True,
        }
    if pid and pid in hotel_ops_ids(catalog_db):
        return {
            "person_id": pid,
            "seat": "hotel_ops",
            "brand_id": BRAND,
            "can_read": True,
            "can_ops": True,
            "money": False,
            "assigned": True,
        }
    return None


def permission_matrix(catalog_db: Path | str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [seat_for(OWNER, catalog_db)]  # type: ignore[list-item]
    ops = hotel_ops_ids(catalog_db)
    if not ops:
        rows.append(
            {
                "person_id": None,
                "seat": "hotel_ops",
                "brand_id": BRAND,
                "can_read": False,
                "can_ops": False,
                "money": False,
                "assigned": False,
                "why": "No active Atrium hotel-ops assignment. The desk does not invent a person.",
            }
        )
    else:
        for pid in ops:
            seat = seat_for(pid, catalog_db)
            if seat:
                rows.append(seat)
    return rows


def require_seat(person_id: str | None, catalog_db: Path | str | None = None) -> dict[str, Any]:
    seat = seat_for(person_id, catalog_db)
    if seat is None or not seat.get("can_ops"):
        raise OpsPackError(
            "AMG ops pack is for the Owner and an active Atrium hotel-ops assignment.",
            code="forbidden",
        )
    return seat


def _ledger(ledger_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        return {}
    return data


def cap_states(ledger_path: Path | str | None = None) -> list[dict[str, Any]]:
    data = _ledger(ledger_path)
    rows = []
    for cap in CAP_IDS:
        raw = data.get(cap)
        state = str(raw[0]).strip().upper() if isinstance(raw, list) and raw else "UNKNOWN"
        rows.append(
            {
                "cap": cap,
                "state": state,
                "raised": False,
                "proven": False,
                "ready": False,
            }
        )
    return rows


def _cr_state(catalog_db: Path | str | None, cr_id: str) -> str:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return "OPEN"
    try:
        _assert_beta_path(path)
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except (OSError, sqlite3.Error, OpsPackError):
        return "OPEN"
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
    flags = dict(HONESTY)
    caps = cap_states(ledger_path)
    primary = next((row for row in caps if row["cap"] == PRIMARY_CAP), {"state": "UNKNOWN"})
    flags["caps"] = caps
    flags["ledger_maturity"] = primary["state"]
    flags["maturity"] = primary["state"]
    flags["specified"] = primary["state"] == "SPECIFIED"
    flags["cr_id"] = PRIMARY_CR
    flags["cr_state"] = _cr_state(catalog_db, PRIMARY_CR)
    flags["cr_resolved"] = False
    flags["journey_cr_id"] = _journey.CR_ID
    flags["journey_cr_state"] = _cr_state(catalog_db, _journey.CR_ID)
    flags["sla_cr_id"] = _sla.CR_ID
    flags["sla_cr_state"] = _cr_state(catalog_db, _sla.CR_ID)
    flags["improve_cr_id"] = _improve.CR_ID
    flags["improve_cr_state"] = _cr_state(catalog_db, _improve.CR_ID)
    flags["pms_cr_id"] = _pms.CR_ID
    flags["pms_cr_state"] = _cr_state(catalog_db, _pms.CR_ID)
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "day_bound": DAY_BOUND,
        "day_schema_id": DAY_SCHEMA_ID,
        "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "operator_depth_slice": OPERATOR_DEPTH_SLICE,
        "writes_accepted": [
            "notes",
            "attention",
            "journey",
            "handoff",
            "day-object",
            "day-object-status",
            "mgmt-exception",
            "operator-action",
        ],
        "money_accepted": False,
        "folio_accepted": False,
        "yanolja_accepted": False,
        "proven_accepted": False,
        "ready_accepted": False,
        "resolve_accepted": False,
        "slots": list(SLOT_IDS),
        "journey_kinds": list(JOURNEY_IDS),
        "handoff_kinds": list(HANDOFF_IDS),
        "day_object_kinds": list(DAY_OBJECT_KINDS),
        "day_loop_stages": list(DAY_LOOP_STAGES),
        "day_object_statuses": sorted(DAY_OBJECT_STATUSES),
        "day_operator_action_kinds": sorted(DAY_OPERATOR_ACTION_KINDS),
        "live_hotel_commission": False,
        "connective_schema_id": CONNECTIVE_SCHEMA_ID,
        "connective_bound": CONNECTIVE_BOUND,
    }


def _quiet() -> dict[str, Any]:
    return {
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "yanolja_live": False,
        "yanolja_called": False,
        "yanolja_write": False,
        "live_ops": False,
        "hotel_operations": False,
        "empty_is_hotel_state": False,
        "payment_executed": False,
        "money": None,
        "folio_executed": False,
        "finance_controls": False,
        "invented_proven": False,
        "invented_ready": False,
        "invented_incident": False,
        "invented_sla": False,
        "invented_arrivals": False,
        "invented_departures": False,
        "cr_resolved": False,
        "ledger_write": False,
        "day_bound": DAY_BOUND,
        "bound": BOUND,
    }


def _attention_map(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {str(row["slot_kind"]): row for row in conn.execute("SELECT * FROM slot_attention")}


def today_slots(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    attention = _attention_map(conn) if conn is not None else {}
    slots = []
    for raw in _ops.kind_slots():
        kind = str(raw["kind"])
        mark = attention.get(kind)
        flagged = bool(mark and int(mark["attention"]))
        reason = WAIT.get(kind) or str(raw.get("why") or "")
        if flagged:
            reason = f"{reason} Desk asked for a look: {mark['reason']}"
        slots.append(
            {
                "kind": kind,
                "label": raw["label"],
                "slot": "empty",
                "evidence": None,
                "occupancy": None,
                "adr": None,
                "revpar": None,
                "yanolja_live": False,
                "live_ops": False,
                "hotel_operations": False,
                "attention": flagged,
                "attention_reason": str(mark["reason"]) if flagged else None,
                "why": reason,
            }
        )
    return slots


def _notes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM desk_notes ORDER BY updated_at DESC, note_id DESC"
    ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "body": row["body"],
            "slot_kind": row["slot_kind"],
            "created_by": row["created_by"],
            "updated_by": row["updated_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "hotel_fact": False,
            "occupancy": None,
        }
        for row in rows
    ]


def _journey_items(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM journey_items
        WHERE service_day = ?
        ORDER BY opened_at DESC, item_id DESC
        """,
        (day,),
    ).fetchall()
    return [
        {
            "item_id": row["item_id"],
            "kind": row["kind"],
            "title": row["title"],
            "status": row["status"],
            "service_day": row["service_day"],
            "opened_by": row["opened_by"],
            "opened_at": row["opened_at"],
            "booking_count": None,
            "occupancy": None,
            "live_journey": False,
        }
        for row in rows
    ]


def _handoffs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM handoffs ORDER BY opened_at DESC, handoff_id DESC"
    ).fetchall()
    return [
        {
            "handoff_id": row["handoff_id"],
            "kind": row["kind"],
            "note": row["note"],
            "status": row["status"],
            "opened_by": row["opened_by"],
            "opened_at": row["opened_at"],
            "review_score": None,
            "live_improve": False,
            "desk_handoff": True,
        }
        for row in rows
    ]


def sla_list() -> dict[str, Any]:
    framework = _sla.build_framework()
    return {
        "ok": True,
        "empty": True,
        "open": [],
        "recorded_count": 0,
        "live_incident": False,
        "live_sla": False,
        "invented_incident": False,
        "invented_sla": False,
        "kinds": framework.get("kinds") or [],
        "why": "No open incident is recorded. An empty SLA slot is not a live incident and not an SLA timer.",
        **_quiet(),
    }


def save_note(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    text = str(payload.get("body") or payload.get("text") or "").strip()
    if not text:
        raise OpsPackError("A desk note needs words.", code="invalid")
    if len(text) > 2000:
        raise OpsPackError("Desk note is too long.", code="invalid")
    slot = str(payload.get("slot") or payload.get("slot_kind") or "").strip().lower() or None
    if slot and slot not in SLOT_IDS:
        raise OpsPackError("Unknown Today slot.", code="invalid")
    note_id = str(payload.get("note_id") or "").strip()
    conn = _connect(db_path)
    try:
        stamp = _now()
        if note_id:
            found = conn.execute(
                "SELECT note_id FROM desk_notes WHERE note_id=?",
                (note_id,),
            ).fetchone()
            if found is None:
                raise OpsPackError("Desk note was not found.", code="not_found")
            conn.execute(
                """
                UPDATE desk_notes
                SET body=?, slot_kind=?, updated_by=?, updated_at=?
                WHERE note_id=?
                """,
                (text, slot, seat["person_id"], stamp, note_id),
            )
        else:
            note_id = "NOTE-" + uuid.uuid4().hex[:12]
            conn.execute(
                """
                INSERT INTO desk_notes
                  (note_id, body, slot_kind, created_by, updated_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, text, slot, seat["person_id"], seat["person_id"], stamp, stamp),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM desk_notes WHERE note_id=?", (note_id,)).fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "note": {
            "note_id": row["note_id"],
            "body": row["body"],
            "slot_kind": row["slot_kind"],
            "updated_by": row["updated_by"],
            "updated_at": row["updated_at"],
            "hotel_fact": False,
            "occupancy": None,
        },
        "seat": seat,
        **_quiet(),
    }


def mark_attention(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    slot = str(payload.get("slot") or payload.get("kind") or "").strip().lower()
    if slot not in SLOT_IDS:
        raise OpsPackError("Unknown Today slot.", code="invalid")
    if "attention" not in payload:
        raise OpsPackError("Say whether the slot needs a look.", code="invalid")
    flag = _as_bool(payload.get("attention"))
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise OpsPackError("A look needs a reason in plain words.", code="invalid")
    if len(reason) > 500:
        raise OpsPackError("The reason is too long.", code="invalid")
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO slot_attention (slot_kind, attention, reason, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(slot_kind) DO UPDATE SET
              attention=excluded.attention,
              reason=excluded.reason,
              updated_by=excluded.updated_by,
              updated_at=excluded.updated_at
            """,
            (slot, 1 if flag else 0, reason, seat["person_id"], _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "slot": slot,
        "attention": flag,
        "reason": reason,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "live_ops": False,
        "seat": seat,
        **_quiet(),
    }


def open_journey(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    kind = str(payload.get("kind") or "").strip().lower()
    if kind not in JOURNEY_IDS:
        raise OpsPackError("Unknown journey kind.", code="invalid")
    title = str(payload.get("title") or "").strip()
    if not title:
        raise OpsPackError("A journey item needs a title.", code="invalid")
    if len(title) > 200:
        raise OpsPackError("Journey title is too long.", code="invalid")
    day = service_day(str(payload.get("service_day") or ""))
    item_id = "JRN-" + uuid.uuid4().hex[:12]
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO journey_items
              (item_id, kind, title, status, service_day, opened_by, opened_at)
            VALUES (?, ?, ?, 'OPEN', ?, ?, ?)
            """,
            (item_id, kind, title, day, seat["person_id"], _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "item": {
            "item_id": item_id,
            "kind": kind,
            "title": title,
            "status": "OPEN",
            "service_day": day,
            "booking_count": None,
            "occupancy": None,
            "live_journey": False,
        },
        "seat": seat,
        **_quiet(),
    }


def open_handoff(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    kind = str(payload.get("kind") or "").strip().lower()
    if kind not in HANDOFF_IDS:
        raise OpsPackError("Unknown service-improve kind.", code="invalid")
    note = str(payload.get("note") or payload.get("body") or "").strip()
    if not note:
        raise OpsPackError("A service handoff needs words.", code="invalid")
    if len(note) > 2000:
        raise OpsPackError("Service handoff is too long.", code="invalid")
    handoff_id = "HO-" + uuid.uuid4().hex[:12]
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO handoffs (handoff_id, kind, note, status, opened_by, opened_at)
            VALUES (?, ?, ?, 'OPEN', ?, ?)
            """,
            (handoff_id, kind, note, seat["person_id"], _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "handoff": {
            "handoff_id": handoff_id,
            "kind": kind,
            "note": note,
            "status": "OPEN",
            "review_score": None,
            "live_improve": False,
            "desk_handoff": True,
        },
        "seat": seat,
        **_quiet(),
    }


def _day_object_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "object_id": row["object_id"],
        "kind": row["kind"],
        "label": DAY_OBJECT_LABELS.get(str(row["kind"]), str(row["kind"])),
        "title": row["title"],
        "note": row["note"],
        "status": row["status"],
        "service_day": row["service_day"],
        "needs_mgmt": bool(int(row["needs_mgmt"] or 0)),
        "mgmt_reason": row["mgmt_reason"],
        "opened_by": row["opened_by"],
        "updated_by": row["updated_by"],
        "opened_at": row["opened_at"],
        "updated_at": row["updated_at"],
        "hotel_fact": False,
        "pms_fact": False,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "room_number": None,
        "incident_number": None,
        "sla_timer": None,
        "booking_count": None,
        "guest_count": None,
        "live_incident": False,
        "live_sla": False,
        "yanolja_called": False,
        "yanolja_write": False,
        "day_object": True,
    }


def _day_objects(
    conn: sqlite3.Connection,
    day: str,
    *,
    kind: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM day_objects WHERE service_day = ?"
    args: list[Any] = [day]
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    if status:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY updated_at DESC, object_id DESC"
    return [_day_object_row(row) for row in conn.execute(sql, args).fetchall()]


def day_object_kinds() -> list[dict[str, Any]]:
    return [
        {
            "kind": kind,
            "label": DAY_OBJECT_LABELS[kind],
            "slot": "operator",
            "hotel_fact": False,
            "why": (
                f"{DAY_OBJECT_LABELS[kind]} is an operable Wolf desk object. "
                "It is not occupancy, an arrival list, a departure list, or a Yanolja write."
            ),
        }
        for kind in DAY_OBJECT_KINDS
    ]


def open_day_object(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    kind = str(payload.get("kind") or "").strip().lower()
    if kind not in DAY_OBJECT_KINDS:
        raise OpsPackError("Unknown day-loop object kind.", code="invalid")
    title = str(payload.get("title") or "").strip()
    if not title:
        raise OpsPackError("A day-loop object needs a title.", code="invalid")
    if len(title) > 200:
        raise OpsPackError("Day-loop title is too long.", code="invalid")
    note = str(payload.get("note") or payload.get("body") or "").strip()
    if not note:
        raise OpsPackError("A day-loop object needs words.", code="invalid")
    if len(note) > 2000:
        raise OpsPackError("Day-loop note is too long.", code="invalid")
    day = service_day(str(payload.get("service_day") or ""))
    object_id = "DAY-" + uuid.uuid4().hex[:12]
    stamp = _now()
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO day_objects (
              object_id, kind, title, note, status, service_day,
              needs_mgmt, mgmt_reason, opened_by, updated_by, opened_at, updated_at
            ) VALUES (?, ?, ?, ?, 'OPEN', ?, 0, NULL, ?, ?, ?, ?)
            """,
            (object_id, kind, title, note, day, seat["person_id"], seat["person_id"], stamp, stamp),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM day_objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "action": "open_day_object",
        "object": _day_object_row(row),
        "seat": seat,
        **_quiet(),
    }


def set_day_object_status(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    object_id = str(payload.get("object_id") or "").strip()
    if not object_id:
        raise OpsPackError("A day-loop object id is required.", code="invalid")
    status = str(payload.get("status") or "").strip().upper()
    if status not in DAY_OBJECT_STATUSES:
        raise OpsPackError("Unknown day-loop status.", code="invalid")
    note = str(payload.get("note") or "").strip()
    if note and len(note) > 2000:
        raise OpsPackError("Day-loop note is too long.", code="invalid")
    conn = _connect(db_path)
    try:
        found = conn.execute(
            "SELECT * FROM day_objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
        if found is None:
            raise OpsPackError("Day-loop object was not found.", code="not_found")
        stamp = _now()
        if note:
            conn.execute(
                """
                UPDATE day_objects
                SET status=?, note=?, updated_by=?, updated_at=?
                WHERE object_id=?
                """,
                (status, note, seat["person_id"], stamp, object_id),
            )
        else:
            conn.execute(
                """
                UPDATE day_objects
                SET status=?, updated_by=?, updated_at=?
                WHERE object_id=?
                """,
                (status, seat["person_id"], stamp, object_id),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM day_objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "action": "set_day_object_status",
        "object": _day_object_row(row),
        "seat": seat,
        **_quiet(),
    }


def raise_day_mgmt_exception(
    body: dict | None,
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    payload = body or {}
    _reject_facts(payload)
    object_id = str(payload.get("object_id") or "").strip()
    if not object_id:
        raise OpsPackError("A day-loop object id is required.", code="invalid")
    reason = str(payload.get("reason") or payload.get("mgmt_reason") or "").strip()
    if not reason:
        raise OpsPackError("A management exception needs a reason.", code="invalid")
    if len(reason) > 500:
        raise OpsPackError("The management exception reason is too long.", code="invalid")
    conn = _connect(db_path)
    try:
        found = conn.execute(
            "SELECT * FROM day_objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
        if found is None:
            raise OpsPackError("Day-loop object was not found.", code="not_found")
        stamp = _now()
        conn.execute(
            """
            UPDATE day_objects
            SET needs_mgmt=1, mgmt_reason=?, status=CASE
              WHEN status='DONE' THEN 'ESCALATED'
              ELSE 'ESCALATED'
            END, updated_by=?, updated_at=?
            WHERE object_id=?
            """,
            (reason, seat["person_id"], stamp, object_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM day_objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "action": "mgmt_exception",
        "object": _day_object_row(row),
        "seat": seat,
        "invented_sla": False,
        "sla_breached": None,
        **_quiet(),
    }


def management_exceptions(
    conn: sqlite3.Connection | None,
    *,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Management exception strip from recorded day-loop objects only."""
    day = service_day(service_day_value)
    rows: list[dict[str, Any]] = []
    if conn is not None:
        for item in _day_objects(conn, day):
            reasons: list[str] = []
            if item.get("needs_mgmt"):
                reasons.append("operator_raised")
            if item.get("status") == "ESCALATED":
                reasons.append("escalated")
            if item.get("status") == "OPEN" and item.get("kind") in {
                "incident",
                "service_recovery",
                "maintenance",
            }:
                reasons.append("open_ops_attention")
            if not reasons:
                continue
            rows.append(
                {
                    "object_id": item["object_id"],
                    "kind": item["kind"],
                    "label": item["label"],
                    "title": item["title"],
                    "status": item["status"],
                    "reasons": reasons,
                    "mgmt_reason": item.get("mgmt_reason"),
                    "service_day": item["service_day"],
                    "sla_breached": None,
                    "sla_timer": None,
                    "invented_sla": False,
                    "hotel_fact": False,
                    "occupancy": None,
                    "yanolja_called": False,
                }
            )
    rows.sort(
        key=lambda r: (
            0 if "operator_raised" in (r.get("reasons") or []) else 1,
            0 if r.get("status") == "ESCALATED" else 1,
            str(r.get("kind") or ""),
            str(r.get("object_id") or ""),
        )
    )
    return {
        "ok": True,
        "bound": DAY_BOUND,
        "brand_id": BRAND,
        "service_day": day,
        "exceptions": rows,
        "count": len(rows),
        "empty": len(rows) == 0,
        "empty_message": (
            "No Atrium management exceptions from day-loop objects."
            if len(rows) == 0
            else None
        ),
        "sla_breached": None,
        "invented_sla": False,
        "owner_visibility": True,
        "yanolja_called": False,
        "why": (
            "Management exceptions from recorded housekeeping, maintenance, incident, "
            "service recovery, or handover objects. No invented SLA breach. "
            "Yanolja stays PMS truth for arrivals/departures/occupancy."
        ),
        **_quiet(),
        "bound": DAY_BOUND,
    }


def owner_visibility(
    conn: sqlite3.Connection | None,
    *,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Owner strip fed from recorded day-loop exceptions — not hotel invent."""
    mgmt = management_exceptions(conn, service_day_value=service_day_value)
    day = mgmt["service_day"]
    open_counts = {kind: 0 for kind in DAY_OBJECT_KINDS}
    if conn is not None:
        for item in _day_objects(conn, day, status="OPEN"):
            open_counts[str(item["kind"])] = open_counts.get(str(item["kind"]), 0) + 1
        for item in _day_objects(conn, day, status="ESCALATED"):
            open_counts[str(item["kind"])] = open_counts.get(str(item["kind"]), 0) + 1
    return {
        "ok": True,
        "bound": DAY_BOUND,
        "brand_id": BRAND,
        "service_day": day,
        "exceptions": mgmt["exceptions"],
        "count": mgmt["count"],
        "empty": mgmt["empty"],
        "open_by_kind": open_counts,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "arrivals": None,
        "departures": None,
        "yanolja_called": False,
        "yanolja_live": False,
        "hotel_facts_invented": False,
        "finance_controls": False,
        "why": (
            "Owner visibility is fed from recorded day-loop objects and management "
            "exceptions. Empty arrivals/departures/occupancy stay wait-words. "
            "Wolf did not call Yanolja and did not invent hotel numbers."
        ),
        **_quiet(),
        "bound": DAY_BOUND,
    }


def day_loop_desk(
    conn: sqlite3.Connection | None,
    *,
    verified_person_id: str,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """One desk: HK → maint → incident → recovery → handover → mgmt → Owner."""
    day = service_day(service_day_value)
    by_kind: dict[str, list[dict[str, Any]]] = {kind: [] for kind in DAY_OBJECT_KINDS}
    items: list[dict[str, Any]] = []
    if conn is not None:
        items = _day_objects(conn, day)
        for item in items:
            by_kind.setdefault(str(item["kind"]), []).append(item)
    stages = []
    for kind in DAY_OBJECT_KINDS:
        rows = by_kind.get(kind) or []
        open_n = sum(1 for row in rows if row.get("status") == "OPEN")
        esc_n = sum(1 for row in rows if row.get("status") == "ESCALATED")
        stages.append(
            {
                "kind": kind,
                "label": DAY_OBJECT_LABELS[kind],
                "count": len(rows),
                "open": open_n,
                "escalated": esc_n,
                "empty": len(rows) == 0,
                "hotel_fact": False,
                "why": (
                    f"{DAY_OBJECT_LABELS[kind]} objects are desk words. "
                    "Empty is not a live hotel state and not a Yanolja list."
                ),
            }
        )
    mgmt = management_exceptions(conn, service_day_value=day)
    owner = owner_visibility(conn, service_day_value=day)
    # Derive desk next action from open/escalated day objects (never invent hotel facts).
    base_next: dict[str, Any]
    escalated = [row for row in items if row.get("status") == "ESCALATED"]
    opened = [row for row in items if row.get("status") == "OPEN"]
    if escalated:
        top = escalated[0]
        base_next = {
            "code": "day-escalated",
            "label": f"Work escalated {DAY_OBJECT_LABELS.get(str(top.get('kind')), top.get('kind'))}: {top.get('title')}",
            "hook": "day-object",
            "invented": False,
        }
    elif opened:
        top = opened[0]
        base_next = {
            "code": "day-open",
            "label": f"Continue {DAY_OBJECT_LABELS.get(str(top.get('kind')), top.get('kind'))}: {top.get('title')}",
            "hook": "day-object",
            "invented": False,
        }
    else:
        base_next = {
            "code": "day-open-new",
            "label": "Open a day-loop object (housekeeping / maintenance / incident / recovery / handover)",
            "hook": "day-object",
            "invented": False,
        }
    intel_next = _intel_connect.attach_to_next_action("amg", base_next)
    intel_strip = _intel_connect.desk_intel_strip("amg", base_next=base_next)
    return {
        "ok": True,
        "bound": DAY_BOUND,
        "brand_id": BRAND,
        "service_day": day,
        "person_id": verified_person_id,
        "stages": stages,
        "order": list(DAY_LOOP_STAGES),
        "items": items,
        "count": len(items),
        "empty": len(items) == 0,
        "kinds": day_object_kinds(),
        "management_exceptions": mgmt,
        "owner_visibility": owner,
        "day_next_action_base": base_next,
        "day_next_action": intel_next,
        "intel_recommendation": intel_next.get("intel_recommendation"),
        "intel_connective": intel_strip,
        "intel_bound": _intel_connect.BOUND,
        "yanolja_pms_truth": True,
        "yanolja_called": False,
        "arrivals_wait": WAIT["arrivals"],
        "departures_wait": WAIT["departures"],
        "occupancy_wait": WAIT["occupancy"],
        "why": (
            "AMG day loop around Yanolja slots. Operable Wolf objects only. "
            "Empty arrivals/departures/occupancy stay wait-words. No invent hotel data. "
            "Intel connective may change the next action; it does not auto-execute."
        ),
        **_quiet(),
        "bound": DAY_BOUND,
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "TRUE", "yes", "on"):
        return True
    if value in (0, "0", "false", "FALSE", "no", "off"):
        return False
    raise OpsPackError("Attention must be yes or no.", code="invalid")


def build_board(
    *,
    verified_person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db)
    day = service_day(service_day_value)
    path = pack_db(db_path)
    if path.is_file():
        conn = _connect(path)
    else:
        conn = None
    try:
        notes = _notes(conn) if conn is not None else []
        items = _journey_items(conn, day) if conn is not None else []
        hands = _handoffs(conn) if conn is not None else []
        slots = today_slots(conn)
        day_loop = day_loop_desk(
            conn,
            verified_person_id=verified_person_id,
            service_day_value=day,
        )
        mgmt = management_exceptions(conn, service_day_value=day)
        owner = owner_visibility(conn, service_day_value=day)
    finally:
        if conn is not None:
            conn.close()
    daily = _ops.build_framework(ledger_path, catalog_db)
    journey = _journey.build_framework(ledger_path, catalog_db)
    pms = _pms.build_framework(ledger_path, catalog_db)
    sla = sla_list()
    flags = honesty_flags(ledger_path, catalog_db)
    board = {
        "ok": True,
        "bound": BOUND,
        "day_bound": DAY_BOUND,
        "brand_id": BRAND,
        "service_day": day,
        "seat": seat,
        "permissions": permission_matrix(catalog_db),
        "schema": schema_document(),
        "today": {
            "ok": True,
            "service_day": day,
            "slots": slots,
            "notes": notes,
            "empty_hotel_facts": True,
            "why": "Empty Wolf slots are not live occupancy. Yanolja stays the source of truth when it is connected. Wolf did not call it.",
            **_quiet(),
        },
        "framework": {
            "ok": True,
            "empty": True,
            "recorded_count": daily.get("recorded_count"),
            "on_disk": daily.get("on_disk"),
            "kinds": slots,
            "why": daily.get("kinds", [{}]) and slots[0]["why"],
            **_quiet(),
        },
        "journey": {
            "ok": True,
            "service_day": day,
            "items": items,
            "framework_empty": True,
            "framework_recorded_count": journey.get("recorded_count"),
            "kinds": journey.get("kinds") or [],
            "booking_count": None,
            "live_journey": False,
            "why": "A desk journey item is a task. It is not a booking and not occupancy.",
        },
        "sla": sla,
        "handoff": {
            "ok": True,
            "items": hands,
            "framework_empty": True,
            "review_score": None,
            "live_improve": False,
            "kinds": (_improve.build_framework(ledger_path, catalog_db).get("kinds") or []),
            "why": "A desk handoff is a note to the next shift. It is not a review score.",
        },
        "day_loop": day_loop,
        "management_exceptions": mgmt,
        "owner_visibility": owner,
        "pms": {
            "ok": True,
            "empty": True,
            "recorded_count": pms.get("recorded_count"),
            "yanolja_called": False,
            "yanolja_live": False,
            "kinds": pms.get("kinds") or [],
            "why": "Yanolja stays the source of truth when it is connected. Wolf did not call it and did not invent rooms, reservations, or guests.",
        },
        "honesty": flags,
        "finance_controls": False,
        **_quiet(),
    }
    # Sprint2 P6: phone-first staff surface (terminology / empty+next / history).
    board["staff_ready"] = _staff_ready.staff_surface_amg(board)
    board["staff_ready_bound"] = _staff_ready.BOUND
    connective = needs_you_connective_strip(
        verified_person_id=verified_person_id,
        db_path=path if path.is_file() else db_path,
        catalog_db=catalog_db,
        service_day_value=day,
    )
    pack_next = _pack_href_next()
    preferred = connective.get("next_action") if connective.get("count") else None
    board["needs_you_connective"] = connective
    board["pack_next_action"] = pack_next
    board["next_action"] = preferred if isinstance(preferred, dict) else pack_next
    return board


# ---------------------------------------------------------------------------
# Sprint2 P3 AMG Day-Loop Operator Depth
# ---------------------------------------------------------------------------


def _under_test_process() -> bool:
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = Path(path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_AUDIT") or "").strip() == "1":
        return
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise OpsPackError(
            "test mode refuses writes to live catalog DB; point catalog at a temp copy",
            code="live_write_refused",
            http_status=500,
        )


def _catalog_connect(catalog_db: Path | str | None = None) -> sqlite3.Connection:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    _assert_beta_path(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _role_has_perm(conn: sqlite3.Connection, role_id: str, perm_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM org_role_permissions
        WHERE role_id=? AND permission_id=? AND effect='ALLOW'
        """,
        (role_id, perm_id),
    ).fetchone()
    return bool(row)


def day_object_href(object_id: str | None) -> str:
    key = (object_id or "").strip()
    if not key:
        return "/amg-ops-pack#day"
    return f"/amg-ops-pack#day-{key}"


def ensure_operator_depth_rbac(
    *,
    conn: sqlite3.Connection | None = None,
    catalog_db: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Idempotent grant: amg.day.operator on ROLE-AMG-GM + Atrium brand scope.

    Wires PERS-MISA Beta fixture seat on ROLE-AMG-GM (ENT-AMG / AMG-ATR).
    Does not mint CF Access seats. Does not commission live hotel staff.
    """
    own = conn is None
    c = conn or _catalog_connect(catalog_db)
    try:
        ts = _now()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_DAY_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_DAY_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_ATR_DAY,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='brand' AND target_id=?
                """,
                (SCOPE_ATR_DAY, BRAND),
            ).fetchone()
        )
        roles_ok = all(_role_has_perm(c, role_id, op_id) for role_id in DAY_OPERATOR_ROLES)

        pos = c.execute(
            "SELECT position_id, status FROM org_positions WHERE position_id=?",
            (POS_DAY_FIXTURE,),
        ).fetchone()
        asg = c.execute(
            """
            SELECT assignment_id, status, end_at FROM org_assignments
            WHERE assignment_id=?
            """,
            (ASG_DAY_MISA,),
        ).fetchone()
        asg_active = bool(
            asg
            and str(asg["status"] or "") == "ACTIVE"
            and asg["end_at"] is None
        )
        scope_linked = bool(
            asg_active
            and c.execute(
                """
                SELECT 1 FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=? AND status='ACTIVE'
                """,
                (ASG_DAY_MISA, SCOPE_ATR_DAY),
            ).fetchone()
        )

        already = (
            bool(existing)
            and str(existing["status"] or "") == "ACTIVE"
            and bool(scope_row)
            and str(scope_row["status"] or "") == "ACTIVE"
            and target_ok
            and roles_ok
            and bool(pos)
            and str(pos["status"] or "") == "ACTIVE"
            and asg_active
            and scope_linked
        )
        if already:
            return {
                "ok": True,
                "grants": [PERM_DAY_OPERATOR],
                "roles": list(DAY_OPERATOR_ROLES),
                "permission_ids": {PERM_DAY_OPERATOR: op_id},
                "scope_id": SCOPE_ATR_DAY,
                "fixture_person_id": MISA,
                "unchanged": True,
                "live_hotel_commission": False,
                "bound": DAY_BOUND,
            }

        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or catalog_db or CATALOG_DB)
        assert_catalog_writable(db_file)

        role = c.execute(
            "SELECT role_id, status FROM org_roles WHERE role_id=?",
            (ROLE_DAY_OPERATOR,),
        ).fetchone()
        if not role:
            raise OpsPackError(
                f"{ROLE_DAY_OPERATOR} missing — AMG/Atrium staff role required",
                code="role_missing",
                http_status=500,
            )

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'amg.day', 'operator',
              'Day-object operator detail + status/note/recovery/handover-touch (no folio/payment)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_DAY_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_DAY_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'brand', 'AMG Atrium day operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_ATR_DAY, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'brand', ?, ?)
            """,
            (SCOPE_ATR_DAY, BRAND, ts),
        )
        for role_id in DAY_OPERATOR_ROLES:
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

        # Beta fixture seat — ROLE-AMG-GM on Atrium. Not live hotel commissioning.
        c.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (
              ?, ?, ?, ?, ?, NULL,
              'Atrium day-operator Beta fixture', 'ACTIVE', 1.0, ?, ?
            )
            ON CONFLICT(position_id) DO UPDATE SET
              status='ACTIVE',
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              brand_id=excluded.brand_id,
              location_id=excluded.location_id,
              updated_at=excluded.updated_at
            """,
            (POS_DAY_FIXTURE, ROLE_DAY_OPERATOR, ENTITY, LOCATION, BRAND, ts, ts),
        )
        c.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at,
              status, is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 0, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
              person_id=excluded.person_id,
              position_id=excluded.position_id,
              status='ACTIVE',
              end_at=NULL,
              updated_at=excluded.updated_at
            """,
            (ASG_DAY_MISA, MISA, POS_DAY_FIXTURE, ts, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
            """,
            (ASG_DAY_MISA, SCOPE_ATR_DAY, ts, ts, ts),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_DAY_OPERATOR],
            "roles": list(DAY_OPERATOR_ROLES),
            "permission_ids": {PERM_DAY_OPERATOR: op_id},
            "scope_id": SCOPE_ATR_DAY,
            "fixture_person_id": MISA,
            "unchanged": False,
            "live_hotel_commission": False,
            "bound": DAY_BOUND,
        }
    finally:
        if own:
            c.close()


def prove_day_operator(
    *,
    person_id: str = MISA,
    conn: sqlite3.Connection | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove Misa (ROLE-AMG-GM) can run day-operator actions. No live hotel commission."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _catalog_connect(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip() or MISA
        seat = seat_for(pid, catalog_db or Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB))
        target = {"entity_id": ENTITY, "brand_id": BRAND}
        can_operator = bool(_rbac.can(pid, PERM_DAY_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id=?
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, ROLE_DAY_OPERATOR),
        ).fetchone()
        role_id = str(asg["role_id"]) if asg else (ROLE_DAY_OPERATOR if pid == OWNER else None)
        allowed = can_operator or pid == OWNER
        pack_seat = seat is not None
        return {
            "ok": True,
            "bound": DAY_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "person_id": pid,
            "seat": seat,
            "role_id": role_id,
            "assignment_active": bool(asg) or pid == OWNER,
            "can_day_operator": allowed,
            "pack_seat": pack_seat,
            "actions": {
                "day_operator": allowed and pack_seat,
                "status": allowed and pack_seat,
                "note": allowed and pack_seat,
                "recovery": allowed and pack_seat,
                "handover_touch": allowed and pack_seat,
                "folio": False,
                "payment": False,
                "bank": False,
                "yanolja_write": False,
                "occupancy_invent": False,
            },
            "live_hotel_commission": False,
            "human_commissioning": "NOT_DONE",
            "target_crs": [PRIMARY_CR],
            "proven": False,
            "ready": False,
            "folio_executed": False,
            "payment_executed": False,
        }
    finally:
        if own:
            c.close()


def _require_day_operator(
    catalog_conn: sqlite3.Connection,
    *,
    verified_person_id: str,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    from core import rbac as _rbac

    seat = require_seat(verified_person_id, catalog_db)
    pid = seat["person_id"]
    ensure_operator_depth_rbac(conn=catalog_conn, commit=False)
    if pid == OWNER:
        return seat
    target = {"entity_id": ENTITY, "brand_id": BRAND}
    if not _rbac.can(pid, PERM_DAY_OPERATOR, target, conn=catalog_conn):
        raise OpsPackError(
            f"permission denied: {PERM_DAY_OPERATOR}",
            code="forbidden",
            http_status=403,
        )
    return seat


def mgmt_consequence(
    conn: sqlite3.Connection | None,
    *,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Management-exception consequence strip from recorded day objects. EMPTY honesty."""
    mgmt = management_exceptions(conn, service_day_value=service_day_value)
    return {
        "ok": True,
        "bound": DAY_BOUND,
        "empty": mgmt.get("empty") is True,
        "count": mgmt.get("count") or 0,
        "exceptions": mgmt.get("exceptions") or [],
        "invented_sla": False,
        "sla_breached": None,
        "occupancy": None,
        "yanolja_called": False,
        "empty_message": mgmt.get("empty_message"),
        "empty_day_loop_is_not_live": True,
        "why": mgmt.get("why"),
    }


def owner_consequence(
    conn: sqlite3.Connection | None,
    *,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Owner-visibility consequence strip. EMPTY honesty when no day objects."""
    owner = owner_visibility(conn, service_day_value=service_day_value)
    return {
        "ok": True,
        "bound": DAY_BOUND,
        "empty": owner.get("empty") is True,
        "count": owner.get("count") or 0,
        "exceptions": owner.get("exceptions") or [],
        "open_by_kind": owner.get("open_by_kind") or {},
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "arrivals": None,
        "departures": None,
        "yanolja_called": False,
        "hotel_facts_invented": False,
        "empty_message": (
            "No recorded day-loop objects — Owner visibility is empty (not invent)."
            if owner.get("empty")
            else None
        ),
        "empty_day_loop_is_not_live": True,
        "why": owner.get("why"),
    }


def list_day_operator_actions(
    object_id: str,
    *,
    conn: sqlite3.Connection,
    limit: int = 40,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT event_id, kind, note, status_before, status_after,
               actor_person_id, recorded_at, payload_json
        FROM day_object_events
        WHERE object_id=?
        ORDER BY recorded_at DESC, event_id DESC
        LIMIT ?
        """,
        (object_id, int(limit)),
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
        out.append(
            {
                "event_id": r["event_id"],
                "kind": r["kind"],
                "note": r["note"],
                "status_before": r["status_before"],
                "status_after": r["status_after"],
                "payload": payload,
                "created_by": r["actor_person_id"],
                "created_at": r["recorded_at"],
                "folio_executed": False,
                "payment_executed": False,
                "yanolja_write": False,
                "invented": False,
            }
        )
    return out


def _day_object_or_raise(conn: sqlite3.Connection, object_id: str) -> dict[str, Any]:
    key = (object_id or "").strip()
    if not key:
        raise OpsPackError("A day-loop object id is required.", code="invalid")
    row = conn.execute(
        "SELECT * FROM day_objects WHERE object_id=?",
        (key,),
    ).fetchone()
    if row is None:
        raise OpsPackError("Day-loop object was not found.", code="not_found", http_status=404)
    return _day_object_row(row)


def operator_day_card(obj: dict[str, Any], *, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "object_id": obj.get("object_id"),
        "kind": obj.get("kind"),
        "label": obj.get("label"),
        "title": obj.get("title"),
        "note": obj.get("note"),
        "status": obj.get("status"),
        "service_day": obj.get("service_day"),
        "needs_mgmt": obj.get("needs_mgmt"),
        "mgmt_reason": obj.get("mgmt_reason"),
        "opened_by": obj.get("opened_by"),
        "updated_by": obj.get("updated_by"),
        "opened_at": obj.get("opened_at"),
        "updated_at": obj.get("updated_at"),
        "operator_action_count": len(events or []),
        "href": day_object_href(str(obj.get("object_id") or "")),
        "hotel_fact": False,
        "pms_fact": False,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "yanolja_called": False,
        "yanolja_write": False,
        "folio_executed": False,
        "payment_executed": False,
        "day_object": True,
    }


def operator_day_detail(
    object_id: str,
    *,
    verified_person_id: str | None = None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Day-object operator detail/action path. No PMS invent. No folio/payment."""
    catalog = _catalog_connect(catalog_db)
    pack = _connect(db_path)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        obj = _day_object_or_raise(pack, object_id)
        pid = (verified_person_id or "").strip() or None
        cat_path = Path(catalog.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        seat = seat_for(pid, cat_path) if pid else None
        actions = {
            "day_operator": False,
            "status": False,
            "note": False,
            "recovery": False,
            "handover_touch": False,
            "folio": False,
            "payment": False,
            "bank": False,
            "yanolja_write": False,
            "occupancy_invent": False,
        }
        if pid and seat is not None:
            prove = prove_day_operator(person_id=pid, conn=catalog, catalog_db=cat_path)
            actions.update(prove.get("actions") or {})
        prior = list_day_operator_actions(str(obj.get("object_id") or ""), conn=pack)
        card = operator_day_card(obj, events=prior)
        day = str(obj.get("service_day") or "")
        return {
            "ok": True,
            "bound": DAY_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "object": card,
            "raw": {
                "object_id": obj.get("object_id"),
                "kind": obj.get("kind"),
                "status": obj.get("status"),
                "service_day": obj.get("service_day"),
                "needs_mgmt": obj.get("needs_mgmt"),
            },
            "actions": actions,
            "operator_actions": prior,
            "href": card["href"],
            "mgmt_consequence": mgmt_consequence(pack, service_day_value=day),
            "owner_consequence": owner_consequence(pack, service_day_value=day),
            "folio_executed": False,
            "payment_executed": False,
            "yanolja_write": False,
            "yanolja_called": False,
            "invented_occupancy": False,
            "live_hotel_commission": False,
            "proven": False,
            "ready": False,
            "honesty": honesty_flags(catalog_db=cat_path),
        }
    finally:
        pack.close()
        catalog.close()


def record_day_operator_action(
    *,
    verified_person_id: str,
    object_id: str,
    kind: str,
    note: str | None = None,
    status: str | None = None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record allowed status/note/recovery/handover-touch. Refreshes mgmt + Owner strips.

    No folio/payment/bank. No PMS occupancy/ADR invent. No Yanolja write.
    """
    k = (kind or "").strip().lower()
    if k not in DAY_OPERATOR_ACTION_KINDS:
        raise OpsPackError(
            f"kind must be one of {sorted(DAY_OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise OpsPackError("verified_person_id required", code="missing_verified_person")
    key = (object_id or "").strip()
    if not key:
        raise OpsPackError("object_id required", code="missing_object")

    catalog = _catalog_connect(catalog_db)
    pack = _connect(db_path)
    try:
        cat_path = Path(catalog.execute("PRAGMA database_list").fetchone()[2] or catalog_db or CATALOG_DB)
        seat = _require_day_operator(catalog, verified_person_id=pid, catalog_db=cat_path)
        obj = _day_object_or_raise(pack, key)
        before_status = str(obj.get("status") or "")
        stamp = _now()
        new_note = str(obj.get("note") or "")
        new_status = before_status
        event_note: str | None = text or None

        if k == "status":
            new_status = str(status or "").strip().upper()
            if new_status not in DAY_OBJECT_STATUSES:
                raise OpsPackError("Unknown day-loop status.", code="invalid")
            if text:
                new_note = text
                if len(new_note) > 2000:
                    raise OpsPackError("Day-loop note is too long.", code="invalid")
            pack.execute(
                """
                UPDATE day_objects
                SET status=?, note=?, updated_by=?, updated_at=?
                WHERE object_id=?
                """,
                (new_status, new_note, seat["person_id"], stamp, key),
            )
        elif k == "note":
            if not text:
                raise OpsPackError("note required", code="missing_note")
            if len(text) > 2000:
                raise OpsPackError("Day-loop note is too long.", code="invalid")
            new_note = text
            pack.execute(
                """
                UPDATE day_objects
                SET note=?, updated_by=?, updated_at=?
                WHERE object_id=?
                """,
                (new_note, seat["person_id"], stamp, key),
            )
        elif k == "recovery":
            if not text:
                raise OpsPackError("recovery note required", code="missing_note")
            if len(text) > 2000:
                raise OpsPackError("Day-loop note is too long.", code="invalid")
            # Recovery touch — operator words only; not a review score or payment.
            new_note = text
            pack.execute(
                """
                UPDATE day_objects
                SET note=?, updated_by=?, updated_at=?
                WHERE object_id=?
                """,
                (new_note, seat["person_id"], stamp, key),
            )
        elif k == "handover_touch":
            if text and len(text) > 2000:
                raise OpsPackError("Day-loop note is too long.", code="invalid")
            if text:
                new_note = text
                pack.execute(
                    """
                    UPDATE day_objects
                    SET note=?, updated_by=?, updated_at=?
                    WHERE object_id=?
                    """,
                    (new_note, seat["person_id"], stamp, key),
                )
            else:
                event_note = "Handover touch recorded."
                pack.execute(
                    """
                    UPDATE day_objects
                    SET updated_by=?, updated_at=?
                    WHERE object_id=?
                    """,
                    (seat["person_id"], stamp, key),
                )

        event_id = "DEV-" + uuid.uuid4().hex[:12]
        payload = {
            "operator_depth": True,
            "kind": k,
            "folio_executed": False,
            "payment_executed": False,
            "yanolja_write": False,
            "occupancy": None,
        }
        pack.execute(
            """
            INSERT INTO day_object_events (
              event_id, object_id, kind, note, status_before, status_after,
              actor_person_id, recorded_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                key,
                k,
                event_note,
                before_status,
                new_status,
                seat["person_id"],
                stamp,
                json.dumps(payload, separators=(",", ":")),
            ),
        )
        after = _day_object_or_raise(pack, key)
        day = str(after.get("service_day") or "")
        mgmt = mgmt_consequence(pack, service_day_value=day)
        owner = owner_consequence(pack, service_day_value=day)
        card = operator_day_card(after, events=list_day_operator_actions(key, conn=pack))
        if commit:
            pack.commit()
            catalog.commit()
        return {
            "ok": True,
            "action": "day_operator",
            "kind": k,
            "seat": seat,
            "object": card,
            "event": {
                "event_id": event_id,
                "kind": k,
                "note": event_note,
                "status_before": before_status,
                "status_after": new_status,
                "actor_person_id": seat["person_id"],
                "recorded_at": stamp,
            },
            "mgmt_consequence": mgmt,
            "owner_consequence": owner,
            "management_exceptions": management_exceptions(pack, service_day_value=day),
            "owner_visibility": owner_visibility(pack, service_day_value=day),
            "day_bound": DAY_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "folio_executed": False,
            "payment_executed": False,
            "yanolja_write": False,
            "yanolja_called": False,
            "invented_occupancy": False,
            "live_hotel_commission": False,
            "proven": False,
            "ready": False,
            **_quiet(),
            "honesty": honesty_flags(catalog_db=cat_path),
        }
    finally:
        pack.close()
        catalog.close()


def operator_depth_desk(
    *,
    verified_person_id: str | None = None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Operator depth desk: RBAC prove + day-object candidates + consequence honesty."""
    catalog = _catalog_connect(catalog_db)
    pack = _connect(db_path)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        cat_path = Path(catalog.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        pid = (verified_person_id or "").strip() or MISA
        prove = prove_day_operator(person_id=pid, conn=catalog, catalog_db=cat_path)
        day = service_day(service_day_value)
        candidates: list[dict[str, Any]] = []
        for item in _day_objects(pack, day):
            if item.get("status") == "DONE":
                continue
            candidates.append(
                {
                    "object_id": item.get("object_id"),
                    "kind": item.get("kind"),
                    "label": item.get("label"),
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "needs_mgmt": item.get("needs_mgmt"),
                    "href": day_object_href(str(item.get("object_id") or "")),
                }
            )
        mgmt = mgmt_consequence(pack, service_day_value=day)
        owner = owner_consequence(pack, service_day_value=day)
        return {
            "ok": True,
            "bound": DAY_BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "service_day": day,
            "rbac": prove,
            "day_candidates": candidates[:20],
            "day_candidate_count": len(candidates),
            "mgmt_consequence": mgmt,
            "owner_consequence": owner,
            "target_crs": [PRIMARY_CR],
            "invented_occupancy": False,
            "empty_day_loop_is_not_live": True,
            "live_hotel_commission": False,
            "folio_executed": False,
            "payment_executed": False,
            "yanolja_write": False,
            "yanolja_called": False,
            "proven": False,
            "ready": False,
            "why": (
                "AMG day-loop operator depth: day-object detail/action path + "
                "status/note/recovery/handover-touch recording that refreshes "
                "management-exception and Owner-visibility consequence strips. "
                "No invent occupancy/ADR. No folio/payment/bank. No live hotel "
                "seat commissioning on this path."
            ),
            "honesty": honesty_flags(catalog_db=cat_path),
        }
    finally:
        pack.close()
        catalog.close()


_NAME_RE = re.compile(r"[a-z]+")
_SEAT_NAME_TOKENS: dict[str, frozenset[str]] = {
    OWNER: frozenset({"matt", "owner"}),
    MISA: frozenset({"misa", "coral"}),
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


def _is_amg_scoped(item: dict[str, Any]) -> bool:
    """AMG commissioning, recorded day-ops, or recorded SLA. Other businesses stay out."""
    kind = str(item.get("kind") or "")
    if kind in {"day_ops", "sla"}:
        return True
    cap = str(item.get("capability") or "")
    if cap.startswith("CAP-AMG"):
        return True
    if str(item.get("business") or "").upper() == "AMG":
        return True
    if str(item.get("domain") or "").upper() == "AMG":
        return True
    if str(item.get("brand_id") or "") == BRAND:
        return True
    surface = str(item.get("surface") or "").lower()
    if surface in {"amg_ops", "amg_day"}:
        return True
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "source", "open_href", "route", "object_id")
    ).lower()
    if "/amg-ops" in blob or "/amg/" in blob:
        return True
    return False


def _in_scope_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every AMG-scoped row. Day operator sees named or desk rows only."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    kind = str(item.get("kind") or "")
    if kind in {"day_ops", "sla"} and seat.get("seat") == "hotel_ops":
        return True
    owner_pid = str(item.get("owner_person_id") or item.get("opened_by") or "").strip()
    if owner_pid and owner_pid == seat.get("person_id"):
        return True
    allowed = set(_SEAT_NAME_TOKENS.get(seat.get("person_id") or "", frozenset()))
    if not allowed:
        return False
    tokens = _name_tokens(
        item.get("who"),
        item.get("audience"),
        item.get("person_to_test"),
        item.get("title"),
    )
    if tokens & allowed:
        return True
    audience = str(item.get("audience") or "").upper()
    if audience == "NEEDS_MATT":
        return False
    return False


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_day_ops": kind == "day_ops",
        "reuse_sla_read": kind == "sla",
    }
    if kind in CONNECTIVE_DEPTH_KINDS:
        block.update(
            {
                "detail": f"/api/progress/needs-you/items/{oid}",
                "acknowledge": f"/api/progress/needs-you/items/{oid}/acknowledge",
                "staff_detail": f"/api/staff/ops-routing/needs-you/items/{oid}",
                "staff_acknowledge": f"/api/staff/ops-routing/needs-you/items/{oid}/acknowledge",
                "amg_detail": f"/api/amg/ops-pack/needs-you/items/{oid}",
                "amg_acknowledge": f"/api/amg/ops-pack/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "day_ops":
        block.update(
            {
                "detail": f"/api/amg/day-ops/objects/{oid}",
                "action": f"/api/amg/day-ops/objects/{oid}/next-action-touch",
                "operator": f"/api/amg/ops-pack/day-objects/{oid}/operator",
            }
        )
    elif kind == "sla":
        block.update({"detail": "/api/amg/ops-pack/sla", "read_only": True})
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    href = item.get("open_href") or item.get("href") or "/amg-ops-pack"
    return {
        "object_id": oid,
        "kind": item.get("kind"),
        "day_kind": item.get("day_kind"),
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
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "live_hotel": False,
        "live_sla": False,
        "invented_sla": False,
        "invented_occupancy": False,
        "handoff": _handoff_block(item),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/amg-ops-pack"
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope AMG Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "amg_ops_needs_you_connective",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "occupancy": None,
        "live_hotel": False,
        "invented_occupancy": False,
    }


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Atrium desk",
        "href": "/amg-ops-pack",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "occupancy": None,
        "live_hotel": False,
    }


def _empty_connective(*, why: str) -> dict[str, Any]:
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
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
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "live_hotel": False,
        "live_sla": False,
        "invented_sla": False,
        "invented_occupancy": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
    }


def _sort_connective(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        kind_rank = {
            "morning_seed": 0,
            "waiting_others": 1,
            "needs_you": 2,
            "day_ops": 3,
            "sla": 4,
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
        for key in (
            "business",
            "surface",
            "capability",
            "person_to_test",
            "route",
            "audience",
        ):
            if extra.get(key) and not merged.get(key):
                merged[key] = extra[key]
        if not merged.get("who") and extra.get("person_to_test"):
            merged["who"] = extra.get("person_to_test")
        if not _is_amg_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "AMG"
        out.append(merged)
    return out


def _day_ops_rows(
    *,
    db_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> list[dict[str, Any]]:
    """Recorded open day-ops objects only. Empty day is not a live hotel."""
    try:
        from core import amg_day_ops_operator_depth as depth

        payload = depth.day_ops_needs_you_consequence(
            db_path=db_path,
            service_day_value=service_day_value,
        )
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
                "kind": "day_ops",
                "day_kind": row.get("kind"),
                "title": row.get("title") or oid,
                "who": None,
                "audience": "NEEDS_STAFF",
                "priority": "P0" if row.get("status") == "ESCALATED" else "P1",
                "status": row.get("status") or "OPEN",
                "business": "AMG",
                "brand_id": BRAND,
                "href": row.get("href") or day_object_href(oid),
                "open_href": row.get("href") or "/amg-ops-pack#day",
                "invented": False,
                "reasons": list(row.get("reasons") or []),
                "occupancy": None,
                "live_hotel": False,
            }
        )
    return out


def _sla_rows() -> list[dict[str, Any]]:
    """Recorded open SLA rows only. An empty framework is not an incident list."""
    try:
        payload = sla_list()
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for row in payload.get("open") or []:
        if not isinstance(row, dict):
            continue
        oid = str(row.get("object_id") or row.get("incident_id") or "")
        if not oid:
            continue
        out.append(
            {
                "object_id": oid,
                "kind": "sla",
                "title": row.get("title") or oid,
                "who": row.get("who"),
                "audience": row.get("audience"),
                "priority": row.get("priority") or "P1",
                "status": row.get("status") or "OPEN",
                "business": "AMG",
                "brand_id": BRAND,
                "href": "/amg-ops-pack",
                "open_href": "/amg-ops-pack",
                "invented": False,
                "live_sla": False,
                "invented_sla": False,
            }
        )
    return out


def _amg_candidates(
    *,
    state_path=None,
    db_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(_day_ops_rows(db_path=db_path, service_day_value=service_day_value))
    items.extend(_sla_rows())
    return _sort_connective(items)


def connective_cap_honesty(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    caps = {}
    for cap in CAP_IDS:
        row = data.get(cap)
        caps[cap] = str(row[0]) if isinstance(row, list) and row else "UNKNOWN"
    nye = _needs_you_module()
    progress = {cr: _cr_state(catalog_db, cr) for cr in nye.TARGET_CRS}
    amg = {cr: _cr_state(catalog_db, cr) for cr in AMG_TARGET_CRS}
    return {
        "caps": caps,
        "amg_crs": amg,
        "progress_core_crs": progress,
        "false_resolve_cr": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "live_hotel": False,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """AMG-scoped Needs-You / Morning seed / day-ops / SLA projection.

    Owner sees the full AMG-scoped set. Misa sees day-operator rows only.
    EMPTY honesty when none. Counts are the in-scope length.
    """
    seat = require_seat(verified_person_id, catalog_db)
    try:
        rows = _amg_candidates(
            state_path=state_path,
            db_path=db_path,
            service_day_value=service_day_value,
        )
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "AMG Needs-You connective read failed "
                f"({exc}). Count stays EMPTY. No work invented."
            )
        )
        empty["seat"] = {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        }
        return empty
    visible = [row for row in rows if _in_scope_for_seat(row, seat)]
    projected = [_project_row(it) for it in visible]
    by_kind = {k: 0 for k in CONNECTIVE_KINDS}
    for it in visible:
        kind = str(it.get("kind") or "")
        if kind in by_kind:
            by_kind[kind] += 1
    empty = len(visible) == 0
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
            "sees_full_amg": seat.get("person_id") == OWNER,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "empty_message": (
            "No AMG-scoped Needs-You / Morning seed / day-ops / SLA rows "
            "in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "invented": False,
        "invented_count": False,
        "source": "amg_scoped_needs_you_morning_day_ops_sla",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=catalog_db),
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "live_hotel": False,
        "live_sla": False,
        "invented_sla": False,
        "invented_occupancy": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
        "why": (
            "Derived AMG-scoped commissioning, day-ops, and recorded SLA rows. "
            "Owner sees the full AMG-scoped projection. The day operator sees "
            "only in-scope rows. Counts are the in-scope length. Empty SLA "
            "is not a live incident."
        ),
    }


def _find_amg_item(
    object_id: str,
    *,
    state_path=None,
    db_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _amg_candidates(
        state_path=state_path,
        db_path=db_path,
        service_day_value=service_day_value,
    ):
        if str(row.get("object_id") or "") == oid:
            return row
    return None


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of AMG seat scope is 403. Reuses existing handoffs."""
    seat = require_seat(verified_person_id, catalog_db)
    found = _find_amg_item(
        object_id,
        state_path=state_path,
        db_path=db_path,
        service_day_value=service_day_value,
    )
    if found is None:
        raise OpsPackError(
            f"AMG Needs-You item '{object_id}' not found.",
            code="not_found",
        )
    if not _in_scope_for_seat(found, seat):
        raise OpsPackError(
            "AMG Needs-You item is outside this seat's scope.",
            code="forbidden",
        )
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
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
        "occupancy": None,
        "live_hotel": False,
        "invented_occupancy": False,
        "invented_sla": False,
        "caps": connective_cap_honesty(catalog_db=catalog_db),
    }


def acknowledge_handoff(
    object_id: str,
    *,
    verified_person_id: str,
    note: str | None = None,
    state_path=None,
    events_path=None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Day-ops and SLA rows keep their existing operator actions. This route
    does not open a second mutate store. Wrong-scope seats are refused.
    """
    seat = require_seat(verified_person_id, catalog_db)
    found = _find_amg_item(
        object_id,
        state_path=state_path,
        db_path=db_path,
        service_day_value=service_day_value,
    )
    if found is None:
        raise OpsPackError(
            f"AMG Needs-You item '{object_id}' not found.",
            code="not_found",
        )
    if not _in_scope_for_seat(found, seat):
        raise OpsPackError(
            "AMG Needs-You item is outside this seat's scope.",
            code="forbidden",
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise OpsPackError(
            "Day-ops and SLA rows use their existing operator action. "
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
        catalog_db=catalog_db,
        connective_actor=seat["person_id"],
    )
    strip = needs_you_connective_strip(
        verified_person_id=seat["person_id"],
        state_path=state_path,
        db_path=db_path,
        catalog_db=catalog_db,
        service_day_value=service_day_value,
    )
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
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
        "occupancy": None,
        "live_hotel": False,
        "invented_occupancy": False,
        "invented_sla": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "Devi done, and live hotel occupancy stay uninvented."
        ),
    }
