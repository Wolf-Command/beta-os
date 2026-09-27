#!/usr/bin/env python3
"""Owner Command Centre — read model for /wolf.

Decision served: owner brief 27 Sep 2026, PACK 1. Extends the Owner Empire
desk and the Pack 4 truth layer. Not a new task or approval database.

Reads Wolf Core and the existing pack handoffs. Does not write, does not
move money, and does not invent a KPI. UNKNOWN stays unknown. MISSING stays
missing. A desk read is not a green business score.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import dashboard_truth as truth
from core import owner_empire_pack as empire
from core import staff_home as home
from core import work_loop as loop

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
BOUND = "beta-owner-safe"
SCHEMA_ID = "wolf.owner-command.v1"
OWNER = empire.OWNER

CLASSES = ("ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN")
TRUTH_STATES = frozenset(truth.DISPLAY_STATES)

COMPANIES: tuple[dict[str, str], ...] = (
    {
        "code": "GGV",
        "entity_id": "ENT-GGV",
        "href": "/business/ggv",
        "surface": "ggv",
        "pack": "GGV",
    },
    {
        "code": "AMG",
        "entity_id": "ENT-AMG",
        "href": "/business/amg",
        "surface": "amg",
        "pack": "AMG",
    },
    {
        "code": "BZG",
        "entity_id": "ENT-BZG",
        "href": "/business/bzg",
        "surface": "bzg",
        "pack": "BZG",
    },
)

_WRITE_VIEWS = frozenset(
    {
        "payment",
        "money",
        "pay",
        "bank",
        "transfer",
        "finance",
        "zayen",
        "payroll",
        "tax",
        "folio",
        "hr",
        "hris",
        "trading",
        "percent",
        "system-pct",
        "proven",
        "ready",
        "resolve",
        "production",
        "cloudflare",
    }
)


class CommandError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    raise CommandError(
        "Owner Command is a read desk. Writes are refused.",
        code="writes_refused",
    )


def write_view(view: str | None) -> bool:
    return (view or "").strip().lower() in _WRITE_VIEWS


def _ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _text(value: Any) -> str:
    return truth.public_text(value)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age(value: Any) -> str:
    parsed = _parse_time(value)
    if parsed is None:
        return "MISSING"
    days = (datetime.now(timezone.utc) - parsed).days
    if days < 0:
        return "MISSING"
    return f"{days}d"


def _demo(*parts: Any) -> bool:
    return home._demo(*parts)


def _mark(state: str) -> str:
    if state in TRUTH_STATES:
        return state
    if state in {"MISSING", "EMPTY", "READ"}:
        return state
    return "UNKNOWN"


def _role(conn: sqlite3.Connection, person_id: str | None, cache: dict[str, str]) -> str:
    pid = (person_id or "").strip()
    if not pid:
        return "MISSING"
    if pid in cache:
        return cache[pid]
    label = "MISSING"
    try:
        row = conn.execute(
            """
            SELECT r.display_name AS role_label
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id = ?
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    if row is not None and str(row["role_label"] or "").strip():
        label = _text(row["role_label"])
    cache[pid] = label or "MISSING"
    return cache[pid]


def _entity_names(conn: sqlite3.Connection) -> dict[str, str]:
    names: dict[str, str] = {}
    if "entity_id" not in _columns(conn, "org_entities"):
        return names
    try:
        rows = conn.execute(
            "SELECT entity_id, display_name, legal_name FROM org_entities"
        ).fetchall()
    except sqlite3.Error:
        return names
    for row in rows:
        eid = str(row["entity_id"] or "")
        label = str(row["display_name"] or "").strip() or str(row["legal_name"] or "").strip()
        if eid and label:
            names[eid] = _text(label)
    return names


def _brands(conn: sqlite3.Connection, entity_id: str) -> tuple[str, list[dict[str, Any]]]:
    if "brand_id" not in _columns(conn, "org_brands"):
        return "UNAVAILABLE", []
    try:
        rows = conn.execute(
            """
            SELECT brand_id, display_name, status
            FROM org_brands
            WHERE entity_id = ?
            ORDER BY display_name, brand_id
            """,
            (entity_id,),
        ).fetchall()
    except sqlite3.Error:
        return "UNAVAILABLE", []
    found: list[dict[str, Any]] = []
    for row in rows:
        bid = str(row["brand_id"] or "")
        name = str(row["display_name"] or "").strip()
        if not bid and not name:
            continue
        blob = f"{bid} {name}".lower()
        href = "/business/uma-blu" if "uma" in blob else None
        found.append(
            {
                "id": bid or "MISSING",
                "name": _text(name) if name else "MISSING",
                "status": _text(row["status"]) if row["status"] else "MISSING",
                "href": href,
                "separate_desk": href is not None,
            }
        )
    if not found:
        return "EMPTY", []
    return "READ", found


def _handoff_map() -> dict[str, dict[str, Any]]:
    try:
        cards = (empire.handoffs().get("cards") or [])
    except Exception:  # noqa: BLE001 — loud empty, no invented count
        return {}
    out: dict[str, dict[str, Any]] = {}
    for card in cards:
        if isinstance(card, dict) and card.get("pack"):
            out[str(card["pack"])] = card
    return out


def _surface_states() -> dict[str, list[dict[str, str]]]:
    states: dict[str, list[dict[str, str]]] = {}
    for company in COMPANIES:
        surface = company["surface"]
        try:
            stamp = truth.stamp(surface)
        except Exception:  # noqa: BLE001
            states[surface] = []
            continue
        rows = []
        for source in stamp.get("sources") or []:
            display = str(source.get("display_state") or "UNKNOWN")
            if display not in TRUTH_STATES:
                display = "UNKNOWN"
            rows.append(
                {
                    "source_id": str(source.get("source_id") or ""),
                    "name": _text(source.get("name") or source.get("source_id") or "Source"),
                    "display_state": display,
                    "commissioned": False,
                }
            )
        states[surface] = rows
    return states


def _finance_state() -> str:
    try:
        stamp = truth.stamp("empire")
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE"
    for source in stamp.get("sources") or []:
        if source.get("source_id") == "finance_ledgers":
            display = str(source.get("display_state") or "UNKNOWN")
            return display if display in TRUTH_STATES else "UNKNOWN"
    return "MISSING"


def _count_work(conn: sqlite3.Connection, entity_id: str, statuses: tuple[str, ...]) -> tuple[str, int | None]:
    if "core_work_items" not in {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")} :
        return "UNAVAILABLE", None
    marks = ",".join("?" for _ in statuses)
    try:
        rows = conn.execute(
            f"""
            SELECT work_item_id, title
            FROM core_work_items
            WHERE owning_entity_id = ?
              AND status IN ({marks})
            """,
            (entity_id, *statuses),
        ).fetchall()
    except sqlite3.Error:
        return "UNAVAILABLE", None
    count = 0
    for row in rows:
        if _demo(row["work_item_id"], row["title"]):
            continue
        count += 1
    return "READ", count


def _priorities(conn: sqlite3.Connection, entity_id: str) -> tuple[str, list[dict[str, Any]]]:
    cols = _columns(conn, "core_work_items")
    if "title" not in cols:
        return "UNAVAILABLE", []
    try:
        rows = conn.execute(
            """
            SELECT work_item_id, title, priority, status
            FROM core_work_items
            WHERE owning_entity_id = ?
              AND status IN ('OPEN', 'IN_PROGRESS')
            ORDER BY priority IS NULL, priority ASC, due_at IS NULL, due_at ASC
            LIMIT 12
            """,
            (entity_id,),
        ).fetchall()
    except sqlite3.Error:
        return "UNAVAILABLE", []
    items: list[dict[str, Any]] = []
    for row in rows:
        if _demo(row["work_item_id"], row["title"]):
            continue
        priority = row["priority"]
        items.append(
            {
                "title": _text(row["title"]) or "MISSING",
                "status": _text(row["status"]) if row["status"] else "MISSING",
                "priority": priority if isinstance(priority, int) and not isinstance(priority, bool) else "MISSING",
            }
        )
        if len(items) == 3:
            break
    if not items:
        return "EMPTY", []
    return "READ", items


def _permission_codes(conn: sqlite3.Connection, person_id: str) -> set[str]:
    try:
        rows = conn.execute(
            """
            SELECT perm.code
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_role_permissions rp
              ON rp.role_id = p.role_id AND rp.effect = 'ALLOW'
            JOIN org_permissions perm ON perm.permission_id = rp.permission_id
            WHERE a.person_id = ?
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
            """,
            (person_id,),
        ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(row["code"]) for row in rows if row["code"]}


def _company_cards(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    names = _entity_names(conn)
    handoffs = _handoff_map()
    surfaces = _surface_states()
    finance = _finance_state()
    cards: list[dict[str, Any]] = []
    for company in COMPANIES:
        eid = company["entity_id"]
        pack = handoffs.get(company["pack"]) or {}
        attention = pack.get("attention_count")
        if pack.get("state") == "READ" and isinstance(attention, int) and not isinstance(attention, bool):
            attention_state = "READ"
            attention_value: int | None = attention
        elif pack:
            attention_state = "MISSING"
            attention_value = None
        else:
            attention_state = "UNAVAILABLE"
            attention_value = None
        brand_state, brands = _brands(conn, eid)
        open_state, open_count = _count_work(conn, eid, ("OPEN", "IN_PROGRESS"))
        blocked_state, blocked_count = _count_work(conn, eid, ("BLOCKED",))
        priority_state, priorities = _priorities(conn, eid)
        occupancy_state = "UNAVAILABLE" if company["code"] == "AMG" else "MISSING"
        for source in surfaces.get(company["surface"]) or []:
            if source["source_id"] == "yanolja":
                occupancy_state = source["display_state"]
        name = names.get(eid) or "MISSING"
        cards.append(
            {
                "code": company["code"],
                "name": name,
                "entity_id": eid,
                "href": company["href"],
                "desk_state": pack.get("state") or "UNAVAILABLE",
                "desk_why": _text(pack.get("why") or "This desk was not read. No count was invented."),
                "attention": {"state": attention_state, "value": attention_value},
                "sources": surfaces.get(company["surface"]) or [],
                "financial_position": {
                    "state": finance,
                    "value": None,
                    "why": "Group finance books were not opened. This is not a company figure and not zero.",
                },
                "occupancy": {
                    "state": occupancy_state,
                    "value": None,
                    "why": (
                        "No hotel-engine figure was read."
                        if company["code"] == "AMG"
                        else "No occupancy source is on this company."
                    ),
                },
                "guest_issues": {
                    "state": "UNKNOWN",
                    "value": None,
                    "why": "No guest-issue source was read. Unknown is not zero.",
                },
                "open_work": {"state": open_state, "value": open_count},
                "blocked_work": {"state": blocked_state, "value": blocked_count},
                "approvals": {"state": "MISSING", "value": None},
                "exceptions": {"state": "MISSING", "value": None},
                "priorities": {"state": priority_state, "items": priorities},
                "operating_businesses": {"state": brand_state, "items": brands},
                "green_kpi": False,
            }
        )
    return cards


def _fill_exception_approval_counts(
    conn: sqlite3.Connection, cards: list[dict[str, Any]]
) -> None:
    by_entity = {card["entity_id"]: card for card in cards}
    entities = list(by_entity)
    if not entities:
        return
    marks = ",".join("?" for _ in entities)
    if "exception_id" in _columns(conn, "core_governance_exceptions"):
        try:
            rows = conn.execute(
                f"""
                SELECT exception_id, entity_id, reason, requested_by_person_id
                FROM core_governance_exceptions
                WHERE entity_id IN ({marks})
                  AND status IN ('REQUESTED', 'AUTHORISED')
                """,
                entities,
            ).fetchall()
            counts = {eid: 0 for eid in entities}
            for row in rows:
                if _demo(row["exception_id"], row["reason"], row["requested_by_person_id"]):
                    continue
                counts[str(row["entity_id"])] = counts.get(str(row["entity_id"]), 0) + 1
            for eid, card in by_entity.items():
                card["exceptions"] = {"state": "READ", "value": counts.get(eid, 0)}
        except sqlite3.Error:
            for card in cards:
                card["exceptions"] = {"state": "UNAVAILABLE", "value": None}
    else:
        for card in cards:
            card["exceptions"] = {"state": "UNAVAILABLE", "value": None}
    if "approval_request_id" in _columns(conn, "core_approval_requests"):
        try:
            rows = conn.execute(
                f"""
                SELECT approval_request_id, owning_entity_id, title, requested_by_person_id
                FROM core_approval_requests
                WHERE owning_entity_id IN ({marks})
                  AND status = 'PENDING'
                """,
                entities,
            ).fetchall()
            counts = {eid: 0 for eid in entities}
            for row in rows:
                if _demo(row["approval_request_id"], row["title"], row["requested_by_person_id"]):
                    continue
                eid = str(row["owning_entity_id"])
                counts[eid] = counts.get(eid, 0) + 1
            for eid, card in by_entity.items():
                card["approvals"] = {"state": "READ", "value": counts.get(eid, 0)}
        except sqlite3.Error:
            for card in cards:
                card["approvals"] = {"state": "UNAVAILABLE", "value": None}
    else:
        for card in cards:
            card["approvals"] = {"state": "UNAVAILABLE", "value": None}


def _needs_you(conn: sqlite3.Connection, cards: list[dict[str, Any]]) -> dict[str, Any]:
    names = {card["entity_id"]: card["code"] for card in cards}
    roles: dict[str, str] = {}
    codes = _permission_codes(conn, OWNER)
    items: list[dict[str, Any]] = []
    approvals_read = "UNAVAILABLE"
    exceptions_read = "UNAVAILABLE"
    entities = list(names)
    marks = ",".join("?" for _ in entities) if entities else ""
    if entities and "approval_request_id" in _columns(conn, "core_approval_requests"):
        try:
            rows = conn.execute(
                f"""
                SELECT approval_request_id, title, status, request_type, material_amount,
                       currency, requested_by_person_id, owning_entity_id,
                       required_permission_code, linked_work_item_id, requested_at
                FROM core_approval_requests
                WHERE owning_entity_id IN ({marks})
                  AND status = 'PENDING'
                ORDER BY requested_at DESC
                LIMIT 40
                """,
                entities,
            ).fetchall()
            approvals_read = "READ"
        except sqlite3.Error:
            rows = []
        for row in rows:
            if _demo(row["approval_request_id"], row["title"], row["requested_by_person_id"]):
                continue
            requester = str(row["requested_by_person_id"] or "")
            if requester == OWNER:
                continue
            needed = str(row["required_permission_code"] or "")
            if "approval.decide" not in codes or (needed and needed not in codes):
                continue
            spend = str(row["request_type"] or "").upper() == "SPEND" or str(row["material_amount"] or "").strip()
            amount = str(row["material_amount"] or "").strip()
            linked = str(row["linked_work_item_id"] or "")
            items.append(
                {
                    "id": str(row["approval_request_id"]),
                    "kind": "financial" if spend else "approval",
                    "company": names.get(str(row["owning_entity_id"]), "MISSING"),
                    "issue": _text(row["title"]) or "MISSING",
                    "owner_role": _role(conn, requester, roles),
                    "age": _age(row["requested_at"]),
                    "state": "PENDING",
                    "amount_state": "READ" if amount else "MISSING",
                    "amount": _text(f"{amount} {row['currency'] or ''}".strip()) if amount else None,
                    "href": f"/my-work/item/{linked}" if linked else None,
                    "why": "This request is waiting for owner authority.",
                }
            )
    if entities and "exception_id" in _columns(conn, "core_governance_exceptions"):
        try:
            rows = conn.execute(
                f"""
                SELECT exception_id, entity_id, reason, status, control_type,
                       requested_by_person_id, created_at
                FROM core_governance_exceptions
                WHERE entity_id IN ({marks})
                  AND status = 'REQUESTED'
                ORDER BY created_at DESC
                LIMIT 40
                """,
                entities,
            ).fetchall()
            exceptions_read = "READ"
        except sqlite3.Error:
            rows = []
        for row in rows:
            if _demo(row["exception_id"], row["reason"], row["requested_by_person_id"]):
                continue
            control = str(row["control_type"] or "").lower()
            financial = any(word in control for word in ("pay", "bank", "finance", "money"))
            items.append(
                {
                    "id": str(row["exception_id"]),
                    "kind": "financial" if financial else "exception",
                    "company": names.get(str(row["entity_id"]), "MISSING"),
                    "issue": _text(row["reason"]) or "MISSING",
                    "owner_role": _role(conn, row["requested_by_person_id"], roles),
                    "age": _age(row["created_at"]),
                    "state": "REQUESTED",
                    "amount_state": "MISSING",
                    "amount": None,
                    "href": None,
                    "why": "A governance exception is waiting for owner authority.",
                }
            )
    commissioning_read = "UNAVAILABLE"
    try:
        stamp = truth.stamp("empire")
        commissioning_read = "READ"
        for source in stamp.get("sources") or []:
            if source.get("commissioned") is True:
                continue
            display = str(source.get("display_state") or "UNKNOWN")
            if display not in TRUTH_STATES:
                display = "UNKNOWN"
            name = _text(source.get("name") or source.get("source_id") or "Source")
            items.append(
                {
                    "id": f"commission:{source.get('source_id')}",
                    "kind": "commissioning",
                    "company": "GROUP",
                    "issue": f"{name} is {display}. Declaring it commissioned is still an owner decision.",
                    "owner_role": "Owner",
                    "age": "MISSING",
                    "state": display,
                    "amount_state": "MISSING",
                    "amount": None,
                    "href": "/dashboard-truth",
                    "why": "Commissioning is an owner decision. This is not an infrastructure repair.",
                }
            )
    except Exception:  # noqa: BLE001
        commissioning_read = "UNAVAILABLE"
    order = {"financial": 0, "exception": 1, "approval": 2, "commissioning": 3}
    items.sort(key=lambda row: order.get(str(row.get("kind")), 9))
    empty = None
    if not items and approvals_read == "READ" and exceptions_read == "READ":
        empty = "Nothing in Wolf Core is waiting for your authority."
    return {
        "ok": True,
        "items": items,
        "approvals_read": approvals_read,
        "exceptions_read": exceptions_read,
        "commissioning_read": commissioning_read,
        "empty_message": empty,
        "excludes_routine_staff_work": True,
        "excludes_infrastructure_repair": True,
    }


def _exceptions(conn: sqlite3.Connection, cards: list[dict[str, Any]]) -> dict[str, Any]:
    names = {card["entity_id"]: card["code"] for card in cards}
    entities = list(names)
    cols = _columns(conn, "core_governance_exceptions")
    if "exception_id" not in cols or not entities:
        return {
            "ok": True,
            "read": "UNAVAILABLE",
            "items": [],
            "empty_message": None,
            "why": "The exception record could not be read. Nothing was invented.",
        }
    marks = ",".join("?" for _ in entities)
    try:
        rows = conn.execute(
            f"""
            SELECT exception_id, entity_id, reason, status, control_type,
                   requested_by_person_id, evidence_id, created_at
            FROM core_governance_exceptions
            WHERE entity_id IN ({marks})
              AND status IN ('REQUESTED', 'AUTHORISED')
            ORDER BY created_at DESC
            LIMIT 20
            """,
            entities,
        ).fetchall()
    except sqlite3.Error:
        return {
            "ok": True,
            "read": "UNAVAILABLE",
            "items": [],
            "empty_message": None,
            "why": "The exception record could not be read. Nothing was invented.",
        }
    roles: dict[str, str] = {}
    items = []
    for row in rows:
        if _demo(row["exception_id"], row["reason"], row["requested_by_person_id"]):
            continue
        evidence = str(row["evidence_id"] or "").strip()
        items.append(
            {
                "id": str(row["exception_id"]),
                "severity": "MISSING",
                "company": names.get(str(row["entity_id"]), "MISSING"),
                "issue": _text(row["reason"]) or "MISSING",
                "owner_role": _role(conn, row["requested_by_person_id"], roles),
                "age": _age(row["created_at"]),
                "current_action": "MISSING",
                "state": _text(row["status"]) or "MISSING",
                "escalation_state": "MISSING",
                "evidence": _text(evidence) if evidence else None,
                "evidence_state": "READ" if evidence else "EMPTY",
            }
        )
    return {
        "ok": True,
        "read": "READ",
        "items": items,
        "empty_message": (
            "No governance exceptions are on record. Empty is not unknown."
            if not items
            else None
        ),
        "why": "Severity, current action, and escalation are not columns on this record, so they stay MISSING.",
    }


def _changed(conn: sqlite3.Connection, cards: list[dict[str, Any]]) -> dict[str, Any]:
    names = {card["entity_id"]: card["code"] for card in cards}
    entities = list(names)
    cols = _columns(conn, "core_audit_events")
    if "action" not in cols or not entities:
        return {
            "ok": True,
            "read": "UNAVAILABLE",
            "items": [],
            "why": "The audit record could not be read. Nothing was invented.",
        }
    wanted = [name for name in ("occurred_at", "action", "result", "entity_id", "source") if name in cols]
    order = "occurred_at DESC" if "occurred_at" in cols else "rowid DESC"
    marks = ",".join("?" for _ in entities)
    try:
        rows = conn.execute(
            f"""
            SELECT {", ".join(wanted)}
            FROM core_audit_events
            WHERE entity_id IN ({marks})
            ORDER BY {order}
            LIMIT 8
            """,
            entities,
        ).fetchall()
    except sqlite3.Error:
        return {
            "ok": True,
            "read": "UNAVAILABLE",
            "items": [],
            "why": "The audit record could not be read. Nothing was invented.",
        }
    items = []
    for row in rows:
        data = {key: row[key] for key in row.keys()}
        items.append(
            {
                "company": names.get(str(data.get("entity_id") or ""), "MISSING"),
                "action": _text(data.get("action")) or "MISSING",
                "result": _text(data.get("result")) if data.get("result") else "MISSING",
                "when": _text(data.get("occurred_at")) if data.get("occurred_at") else "MISSING",
                "source": _text(data.get("source")) if data.get("source") else "MISSING",
            }
        )
    return {
        "ok": True,
        "read": "READ",
        "items": items,
        "empty_message": (
            "No audit events are on record for these companies. Empty is not 'nothing happened in the world'."
            if not items
            else None
        ),
    }


def _blocked(conn: sqlite3.Connection, cards: list[dict[str, Any]]) -> dict[str, Any]:
    names = {card["entity_id"]: card["code"] for card in cards}
    entities = list(names)
    if "title" not in _columns(conn, "core_work_items") or not entities:
        return {"ok": True, "read": "UNAVAILABLE", "items": [], "why": "Blocked work could not be read."}
    marks = ",".join("?" for _ in entities)
    try:
        rows = conn.execute(
            f"""
            SELECT work_item_id, title, owning_entity_id, owner_person_id, updated_at
            FROM core_work_items
            WHERE owning_entity_id IN ({marks})
              AND status = 'BLOCKED'
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            entities,
        ).fetchall()
    except sqlite3.Error:
        return {"ok": True, "read": "UNAVAILABLE", "items": [], "why": "Blocked work could not be read."}
    roles: dict[str, str] = {}
    items = []
    for row in rows:
        if _demo(row["work_item_id"], row["title"], row["owner_person_id"]):
            continue
        items.append(
            {
                "id": str(row["work_item_id"]),
                "company": names.get(str(row["owning_entity_id"]), "MISSING"),
                "what": _text(row["title"]) or "MISSING",
                "owner_role": _role(conn, row["owner_person_id"], roles),
                "age": _age(row["updated_at"]),
                "href": f"/my-work/item/{row['work_item_id']}",
            }
        )
    return {
        "ok": True,
        "read": "READ",
        "items": items,
        "empty_message": "No blocked work is on record." if not items else None,
    }


def _founder() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    try:
        from core import staff_ops_routing as routing

        strip = routing.disappearance_strip()
        for card in strip.get("cards") or []:
            label = str(card.get("founder_dep_class") or "AUGMENT")
            if label not in CLASSES:
                label = "AUGMENT"
            items.append(
                {
                    "name": _text(card.get("label") or card.get("pack") or "Desk"),
                    "class": label,
                    "reason": _text(card.get("why_routing") or card.get("founder_dep_reason") or ""),
                    "href": card.get("href"),
                    "source": "desk_routing",
                    "staff_seat_present": bool(card.get("staff_seat_present")),
                }
            )
    except Exception:  # noqa: BLE001
        items.append(
            {
                "name": "Desk routing",
                "class": "AUGMENT",
                "reason": "Desk routing could not be read. ELIMINATE was not invented.",
                "href": None,
                "source": "desk_routing",
                "staff_seat_present": False,
            }
        )
    for name, label in loop.founder_dependency().items():
        klass = label if label in CLASSES else "RETAIN"
        items.append(
            {
                "name": name,
                "class": klass,
                "reason": "Work-loop classification. Not a measured reduction in owner load.",
                "href": None,
                "source": "work_loop",
                "staff_seat_present": False,
            }
        )
    for name, label in home._founder("owner_pulse").items():
        klass = label if label in CLASSES else "RETAIN"
        items.append(
            {
                "name": name,
                "class": klass,
                "reason": "Owner pulse still holds this. Not a measured reduction.",
                "href": "/wolf",
                "source": "owner_pulse",
                "staff_seat_present": False,
            }
        )
    counts = {label: 0 for label in CLASSES}
    for item in items:
        counts[item["class"]] = counts.get(item["class"], 0) + 1
    routed = [
        item["name"]
        for item in items
        if item["class"] == "ELIMINATE" and item["source"] == "desk_routing"
    ]
    retained = [item["name"] for item in items if item["class"] == "RETAIN"]
    if routed:
        verdict = (
            "Some desks are classed ELIMINATE because a staff seat can take the daily queue: "
            + ", ".join(routed)
            + ". "
        )
    else:
        verdict = "No desk is classed ELIMINATE on this read. "
    if retained:
        verdict += "These stay with you: " + ", ".join(retained[:8]) + ". "
    verdict += "Wolf has not measured a reduction in your load. This screen is not commissioned."
    return {
        "ok": True,
        "classes": list(CLASSES),
        "counts": counts,
        "items": items,
        "less_dependent": "NOT MEASURED",
        "measured_reduction": False,
        "verdict": verdict,
        "invented_owner_control_away": False,
    }


def _answers(
    cards: list[dict[str, Any]],
    changed: dict[str, Any],
    needs: dict[str, Any],
    exceptions: dict[str, Any],
    blocked: dict[str, Any],
    founder: dict[str, Any],
    finance_state: str,
) -> list[dict[str, str]]:
    unread = [card["code"] for card in cards if card.get("desk_state") != "READ"]
    if unread:
        okay = (
            "At least one desk did not read ("
            + ", ".join(unread)
            + "). That is not a health score."
        )
    else:
        okay = (
            "GGV, AMG, and BZG desks were read. Attention counts are on the cards. "
            "This is not a green KPI."
        )
    if changed.get("read") != "READ":
        changed_answer = "What changed could not be read. Nothing was invented."
    elif changed.get("items"):
        newest = changed["items"][0]
        changed_answer = (
            f"{len(changed['items'])} recent audit events are on record for these companies. "
            f"The newest is {newest.get('action')} ({newest.get('company')})."
        )
    else:
        changed_answer = changed.get("empty_message") or "No audit events are on record."
    if exceptions.get("read") != "READ":
        wrong = "What is going wrong could not be read from the exception record."
    elif exceptions.get("items"):
        wrong = f"{len(exceptions['items'])} governance exceptions are on record. Severity is MISSING on each row."
    else:
        wrong = "No governance exceptions are on record. Empty is not unknown."
    waiting = [item for item in needs.get("items") or [] if item.get("kind") != "commissioning"]
    commissioning = [item for item in needs.get("items") or [] if item.get("kind") == "commissioning"]
    if needs.get("approvals_read") != "READ" or needs.get("exceptions_read") != "READ":
        decision = "Approvals or exceptions could not be read. Commissioning may still be listed. Nothing was invented."
    elif waiting:
        decision = f"{len(waiting)} Wolf Core items are waiting for your authority."
    elif commissioning:
        decision = (
            f"No approval or exception is waiting. {len(commissioning)} sources still need a commissioning decision."
        )
    else:
        decision = needs.get("empty_message") or "Nothing is waiting for your authority."
    money_items = [item for item in needs.get("items") or [] if item.get("kind") == "financial"]
    if money_items:
        money = (
            f"{len(money_items)} items on record are flagged as money or control. "
            f"Finance books are {finance_state}. That is not a cash position."
        )
    else:
        money = (
            f"Nothing on record is flagged as money or control. Finance books are {finance_state}. "
            "Unavailable is not a zero balance."
        )
    if blocked.get("read") != "READ":
        blocked_answer = "Blocked work could not be read."
    elif blocked.get("items"):
        blocked_answer = f"{len(blocked['items'])} work items are blocked. The owner role is on each row."
    else:
        blocked_answer = "No blocked work is on record."
    return [
        {"id": "okay", "question": "Are my businesses okay?", "answer": okay},
        {"id": "changed", "question": "What changed?", "answer": changed_answer},
        {"id": "wrong", "question": "What is going wrong?", "answer": wrong},
        {"id": "decision", "question": "What needs my decision?", "answer": decision},
        {"id": "money", "question": "Where is money at risk?", "answer": money},
        {"id": "blocked", "question": "Who or what is blocked?", "answer": blocked_answer},
        {"id": "dependency", "question": "Are we less dependent on me?", "answer": founder.get("verdict") or "NOT MEASURED"},
    ]


def _unavailable(reason: str) -> dict[str, Any]:
    cards = []
    for company in COMPANIES:
        cards.append(
            {
                "code": company["code"],
                "name": "MISSING",
                "entity_id": company["entity_id"],
                "href": company["href"],
                "desk_state": "UNAVAILABLE",
                "desk_why": "The command read failed. No figure was invented.",
                "attention": {"state": "UNAVAILABLE", "value": None},
                "sources": [],
                "financial_position": {"state": "UNAVAILABLE", "value": None, "why": reason},
                "occupancy": {"state": "UNKNOWN", "value": None, "why": "Not read."},
                "guest_issues": {"state": "UNKNOWN", "value": None, "why": "Not read."},
                "open_work": {"state": "UNAVAILABLE", "value": None},
                "blocked_work": {"state": "UNAVAILABLE", "value": None},
                "approvals": {"state": "UNAVAILABLE", "value": None},
                "exceptions": {"state": "UNAVAILABLE", "value": None},
                "priorities": {"state": "UNAVAILABLE", "items": []},
                "operating_businesses": {"state": "UNAVAILABLE", "items": []},
                "green_kpi": False,
            }
        )
    founder = {
        "ok": True,
        "classes": list(CLASSES),
        "counts": {label: 0 for label in CLASSES},
        "items": [],
        "less_dependent": "NOT MEASURED",
        "measured_reduction": False,
        "verdict": "The dependency read did not finish. NOT MEASURED.",
        "invented_owner_control_away": False,
    }
    empty = {"ok": True, "read": "UNAVAILABLE", "items": [], "why": reason}
    needs = {
        "ok": True,
        "items": [],
        "approvals_read": "UNAVAILABLE",
        "exceptions_read": "UNAVAILABLE",
        "commissioning_read": "UNAVAILABLE",
        "empty_message": None,
        "excludes_routine_staff_work": True,
        "excludes_infrastructure_repair": True,
    }
    return _envelope(
        cards,
        _answers(cards, empty, needs, empty, empty, founder, "UNAVAILABLE"),
        needs,
        empty,
        empty,
        empty,
        founder,
        read="UNAVAILABLE",
    )


def _envelope(
    cards: list[dict[str, Any]],
    answers: list[dict[str, str]],
    needs: dict[str, Any],
    exceptions: dict[str, Any],
    changed: dict[str, Any],
    blocked: dict[str, Any],
    founder: dict[str, Any],
    *,
    read: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "read": read,
        "answers": answers,
        "companies": cards,
        "needs_you": needs,
        "exceptions": exceptions,
        "changed": changed,
        "blocked": blocked,
        "founder_dependency": founder,
        "system_health": {
            "secondary": True,
            "href": "/dashboard-truth",
            "why": "Source freshness sits under the businesses. Open Data truth for the register.",
        },
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "money": None,
        "payment_executed": False,
        "occupancy": None,
        "green_kpi": False,
        "ledger_write": False,
        "external_writes": False,
    }


def build_command(*, verified_person_id: str) -> dict[str, Any]:
    empire.require_owner(verified_person_id)
    conn: sqlite3.Connection | None = None
    try:
        conn = _ro()
        cards = _company_cards(conn)
        _fill_exception_approval_counts(conn, cards)
        needs = _needs_you(conn, cards)
        exceptions = _exceptions(conn, cards)
        changed = _changed(conn, cards)
        blocked = _blocked(conn, cards)
        founder = _founder()
        finance = cards[0]["financial_position"]["state"] if cards else "UNAVAILABLE"
        answers = _answers(cards, changed, needs, exceptions, blocked, founder, finance)
        return _envelope(cards, answers, needs, exceptions, changed, blocked, founder, read="READ")
    except empire.EmpirePackError:
        raise
    except Exception as exc:  # noqa: BLE001
        return _unavailable(type(exc).__name__)
    finally:
        if conn is not None:
            conn.close()
