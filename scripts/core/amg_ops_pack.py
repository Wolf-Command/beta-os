#!/usr/bin/env python3
"""AMG / Atrium hotel ops pack v1 — Beta :8788 only.

Decision served: 2026-09-21 compressed sprint Track C
(docs/deliveries/GROK-PLAN-SPRINT-TRACK-C-AMG-OPS-PACK-2026-09-21.md),
under the 2026-09-19 owner release keep_building_without_matt.

One vertical desk loop. Reuses the daily-ops, journey, SLA, service-improve,
and PMS skeletons as reads. Desk notes, slot attention, journey tasks, and
service handoffs are operator words. They are not occupancy, ADR, RevPAR,
a Yanolja write, a live incident, or a review score.

Does not execute money, a folio, a bank move, or Zayen. Does not invent
PROVEN or READY. Does not resolve CR-bc5785d66c981fd4. CAP-AMG-* stay at
the ledger value. Bound beta-amg-ops-safe.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import amg_daily_ops_state as _ops
from core import amg_journey_workflow as _journey
from core import amg_pms_orchestration as _pms
from core import amg_service_improve as _improve
from core import amg_sla_incident as _sla

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "amg_ops_pack.sqlite"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-amg-ops-safe"
SCHEMA_ID = "wolf.amg-ops-pack.v1"
PRIMARY_CAP = "CAP-AMG-04"
PRIMARY_CR = "CR-bc5785d66c981fd4"
OWNER = "PERS-MATT"
BRAND = "AMG-ATR"
ENTITY = "ENT-AMG"
LOCATION = "LOC-ATRIUM-LOMBOK"
WITA = timezone(timedelta(hours=8))

CAP_IDS = tuple(f"CAP-AMG-0{i}" for i in range(1, 8))
SLOT_IDS = _ops.KIND_IDS
JOURNEY_IDS = _journey.KIND_IDS
HANDOFF_IDS = _improve.KIND_IDS

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
    "slice": "amg_ops_pack_v1",
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
    "invented_occupancy": False,
    "invented_adr": False,
    "invented_revpar": False,
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
}


class OpsPackError(ValueError):
    """Fail closed. Does not invent hotel facts, money, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


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
        "writes_accepted": ["notes", "attention", "journey", "handoff"],
        "money_accepted": False,
        "folio_accepted": False,
        "yanolja_accepted": False,
        "proven_accepted": False,
        "ready_accepted": False,
        "resolve_accepted": False,
        "slots": list(SLOT_IDS),
        "journey_kinds": list(JOURNEY_IDS),
        "handoff_kinds": list(HANDOFF_IDS),
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
        "cr_resolved": False,
        "ledger_write": False,
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
    finally:
        if conn is not None:
            conn.close()
    daily = _ops.build_framework(ledger_path, catalog_db)
    journey = _journey.build_framework(ledger_path, catalog_db)
    pms = _pms.build_framework(ledger_path, catalog_db)
    sla = sla_list()
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "bound": BOUND,
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
