#!/usr/bin/env python3
"""Business dashboards — one projection under Owner Command.

Decision served: owner brief 27 Sep 2026, PACK 2. Extends Owner Command
and the Pack 4 truth layer. Not a new task or approval database.

WOLF/GROUP → legal entity → site → business unit/venue → department →
workspace → object. AMG/Atrium, BZG, Uma Blu, and GGV are derived from
one canonical snapshot. The next read shows a changed snapshot. A held
projection that disagrees is STALE and is not shown as current.

Specialist workspaces stay as links. Their numbers are not copied here.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import dashboard_truth as truth
from core import ledger_class
from core import owner_empire_pack as empire
from core import staff_home as home
from core import wolf_shell as shell

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
BOUND = "beta-owner-safe"
SCHEMA_ID = "wolf.business-dashboard.v1"

LEVELS = (
    "WOLF/GROUP",
    "LEGAL ENTITY",
    "SITE",
    "BUSINESS UNIT/VENUE",
    "DEPARTMENT/FUNCTION",
    "WORKSPACE",
    "OBJECT",
)
SECTIONS = (
    "today",
    "performance",
    "people",
    "money",
    "customers",
    "exceptions",
    "priorities",
    "activity",
)
BUSINESSES: tuple[dict[str, Any], ...] = (
    {
        "code": "amg",
        "label": "AMG / Atrium",
        "entity_id": "ENT-AMG",
        "brand_id": "AMG-ATR",
        "grain": "entity",
        "surface": "amg",
    },
    {
        "code": "bzg",
        "label": "BZG",
        "entity_id": "ENT-BZG",
        "brand_id": None,
        "grain": "entity",
        "surface": "bzg",
    },
    {
        "code": "uma-blu",
        "label": "Uma Blu",
        "entity_id": "ENT-BZG",
        "brand_id": "BZG-UMA",
        "grain": "venue",
        "surface": "bzg",
    },
    {
        "code": "ggv",
        "label": "GGV",
        "entity_id": "ENT-GGV",
        "brand_id": None,
        "grain": "entity",
        "surface": "ggv",
    },
)
CODES = frozenset(row["code"] for row in BUSINESSES)
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
        "proven",
        "ready",
        "resolve",
        "production",
        "cloudflare",
    }
)


class DashboardError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    raise DashboardError(
        "Business dashboards are a read. Writes are refused.",
        code="writes_refused",
    )


def write_view(view: str | None) -> bool:
    return (view or "").strip().lower() in _WRITE_VIEWS


def _text(value: Any) -> str:
    return truth.public_text(value)


def _demo(*parts: Any) -> bool:
    return home._demo(*parts)


def _ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _digest(snapshot: dict[str, Any]) -> str:
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _projection(canonical: str, projected: str) -> dict[str, Any]:
    """Matching store projection is CURRENT. Disagreement is STALE, not current."""
    if canonical != projected:
        status = truth.projection_status(canonical, projected)
    else:
        now = datetime.now(timezone.utc).isoformat()
        status = truth.classify(
            {
                "available": True,
                "readable": True,
                "authoritative": True,
                "verification": "VERIFIED",
                "presence": "PRESENT",
                "time_class": "CURRENT",
                "measure": "ACTUAL",
                "build": "BUILT",
                "observed_at": now,
                "external": False,
                "commissioned": False,
            }
        )
    status = dict(status)
    status["canonical"] = canonical
    status["projected"] = projected
    status["commissioned"] = False
    status["human_commissioned"] = False
    status["staff_ready"] = False
    if status.get("display_state") == "STALE":
        status["shown_as_current"] = False
        status["stale_shown_as_current"] = False
    elif status.get("display_state") == "LIVE":
        status["display_state"] = "CURRENT"
        status["shown_as_current"] = True
        status["plain"] = (
            "Current. This is a projection of the store just read. It is not a live feed."
        )
    return status


def _source_rows(surface: str) -> list[dict[str, Any]]:
    try:
        stamp = truth.stamp(surface)
    except Exception:  # noqa: BLE001 — loud empty, no invented source
        return []
    rows = []
    for source in stamp.get("sources") or []:
        display = str(source.get("display_state") or "UNKNOWN")
        if display not in truth.DISPLAY_STATES:
            display = "UNKNOWN"
        rows.append(
            {
                "source_id": str(source.get("source_id") or ""),
                "name": _text(source.get("name") or source.get("source_id") or "Source"),
                "display_state": display,
            }
        )
    rows.sort(key=lambda row: row["source_id"])
    return rows


def _finance_state(sources_by_surface: dict[str, list[dict[str, Any]]]) -> str:
    for source in sources_by_surface.get("empire") or []:
        if source["source_id"] == "finance_ledgers":
            return source["display_state"]
    return "MISSING"


def _person_maps(conn: sqlite3.Connection) -> tuple[dict[str, str], dict[str, str]]:
    names: dict[str, str] = {}
    roles: dict[str, str] = {}
    if "person_id" in _columns(conn, "org_persons"):
        for row in conn.execute("SELECT person_id, display_name FROM org_persons"):
            pid = str(row["person_id"] or "")
            label = str(row["display_name"] or "").strip()
            if pid and label and not _demo(pid, label):
                names[pid] = _text(label)
    if "assignment_id" in _columns(conn, "org_assignments"):
        rows = conn.execute(
            """
            SELECT a.person_id, r.display_name AS role_label
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.status = 'ACTIVE' AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """
        ).fetchall()
        for row in rows:
            pid = str(row["person_id"] or "")
            label = str(row["role_label"] or "").strip()
            if pid and label and pid not in roles and not _demo(pid, label):
                roles[pid] = _text(label)
    return names, roles


def _ledger_counts(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        return ledger_class.summarize(conn)
    except sqlite3.Error:
        return {"read": "UNAVAILABLE"}


def read_snapshot(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """One canonical snapshot. Dashboards do not read past this object."""
    own = conn is None
    db = conn or _ro()
    try:
        tables = _tables(db)
        entities = _rows(
            db,
            tables,
            "org_entities",
            "SELECT entity_id, display_name, legal_name, status FROM org_entities ORDER BY entity_id",
            ("entity_id", "display_name", "legal_name", "status"),
        )
        brands = _rows(
            db,
            tables,
            "org_brands",
            """
            SELECT brand_id, entity_id, display_name, brand_type, status
            FROM org_brands ORDER BY entity_id, brand_id
            """,
            ("brand_id", "entity_id", "display_name", "brand_type", "status"),
        )
        locations = _rows(
            db,
            tables,
            "org_locations",
            """
            SELECT location_id, entity_id, display_name, location_type, status
            FROM org_locations ORDER BY location_id
            """,
            ("location_id", "entity_id", "display_name", "location_type", "status"),
        )
        links = _rows(
            db,
            tables,
            "org_brand_locations",
            """
            SELECT brand_id, location_id, status
            FROM org_brand_locations ORDER BY brand_id, location_id
            """,
            ("brand_id", "location_id", "status"),
        )
        departments = _rows(
            db,
            tables,
            "org_departments",
            """
            SELECT department_id, entity_id, display_name, status, ownership
            FROM org_departments ORDER BY entity_id, department_id
            """,
            ("department_id", "entity_id", "display_name", "status", "ownership"),
        )
        work = _rows(
            db,
            tables,
            "core_work_items",
            """
            SELECT work_item_id, title, status, priority, owning_entity_id, owner_person_id, updated_at
            FROM core_work_items
            ORDER BY owning_entity_id, work_item_id
            """,
            (
                "work_item_id",
                "title",
                "status",
                "priority",
                "owning_entity_id",
                "owner_person_id",
                "updated_at",
            ),
        )
        work = [row for row in work if not _demo(row.get("work_item_id"), row.get("title"))]
        exceptions = _rows(
            db,
            tables,
            "core_governance_exceptions",
            """
            SELECT exception_id, entity_id, status, reason, requested_by_person_id, created_at
            FROM core_governance_exceptions
            ORDER BY entity_id, exception_id
            """,
            (
                "exception_id",
                "entity_id",
                "status",
                "reason",
                "requested_by_person_id",
                "created_at",
            ),
        )
        exceptions = [
            row
            for row in exceptions
            if not _demo(row.get("exception_id"), row.get("reason"), row.get("requested_by_person_id"))
        ]
        approvals = _rows(
            db,
            tables,
            "core_approval_requests",
            """
            SELECT approval_request_id, owning_entity_id, status, title, requested_by_person_id
            FROM core_approval_requests
            ORDER BY owning_entity_id, approval_request_id
            """,
            (
                "approval_request_id",
                "owning_entity_id",
                "status",
                "title",
                "requested_by_person_id",
            ),
        )
        approvals = [
            row
            for row in approvals
            if not _demo(row.get("approval_request_id"), row.get("title"), row.get("requested_by_person_id"))
        ]
        activity = _activity_rows(db, tables)
        names, roles = _person_maps(db)
        surfaces = {
            "empire": _source_rows("empire"),
            "amg": _source_rows("amg"),
            "bzg": _source_rows("bzg"),
            "ggv": _source_rows("ggv"),
        }
        snapshot = {
            "entities": entities,
            "brands": brands,
            "locations": locations,
            "brand_locations": links,
            "departments": departments,
            "work": work,
            "exceptions": exceptions,
            "approvals": approvals,
            "activity": activity,
            "persons": [{"person_id": pid, "display_name": names[pid]} for pid in sorted(names)],
            "roles": [{"person_id": pid, "role_label": roles[pid]} for pid in sorted(roles)],
            "sources": surfaces,
            "finance_state": _finance_state(surfaces),
            "targets": [],
            "present": {
                "work": "core_work_items" in tables,
                "exceptions": "core_governance_exceptions" in tables,
                "approvals": "core_approval_requests" in tables,
                "activity": "core_audit_events" in tables,
            },
            "ledger_classification": _ledger_counts(db),
        }
        return snapshot
    finally:
        if own:
            db.close()


def _rows(
    conn: sqlite3.Connection,
    tables: set[str],
    table: str,
    sql: str,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    if table not in tables:
        return []
    found = conn.execute(sql).fetchall()
    out = []
    for row in found:
        item: dict[str, Any] = {}
        for key in keys:
            value = row[key]
            if key == "priority":
                item[key] = value if isinstance(value, int) and not isinstance(value, bool) else None
            elif value is None:
                item[key] = None
            else:
                item[key] = _text(value) if isinstance(value, str) else value
        out.append(item)
    return out


def _activity_rows(conn: sqlite3.Connection, tables: set[str]) -> list[dict[str, Any]]:
    if "core_audit_events" not in tables:
        return []
    entity_ids = sorted({row["entity_id"] for row in BUSINESSES})
    brand_ids = sorted({row["brand_id"] for row in BUSINESSES if row["brand_id"]})
    marks_e = ",".join("?" for _ in entity_ids)
    marks_b = ",".join("?" for _ in brand_ids) or "?"
    params: list[Any] = list(entity_ids)
    if brand_ids:
        params.extend(brand_ids)
        brand_clause = f"OR brand_id IN ({marks_b})"
    else:
        brand_clause = ""
    found = conn.execute(
        f"""
        SELECT audit_event_id, occurred_at, entity_id, brand_id, action, result, actor_person_id
        FROM core_audit_events
        WHERE entity_id IN ({marks_e}) {brand_clause}
        ORDER BY occurred_at DESC, audit_event_id DESC
        LIMIT 80
        """,
        params,
    ).fetchall()
    rows = []
    for row in found:
        if _demo(row["audit_event_id"], row["action"], row["actor_person_id"]):
            continue
        rows.append(
            {
                "audit_event_id": _text(row["audit_event_id"]),
                "occurred_at": _text(row["occurred_at"]) if row["occurred_at"] else None,
                "entity_id": _text(row["entity_id"]) if row["entity_id"] else None,
                "brand_id": _text(row["brand_id"]) if row["brand_id"] else None,
                "action": _text(row["action"]) if row["action"] else "MISSING",
                "result": _text(row["result"]) if row["result"] else "MISSING",
                "actor_person_id": _text(row["actor_person_id"]) if row["actor_person_id"] else None,
            }
        )
    return rows


def _lookup(rows: list[dict[str, Any]], key: str) -> dict[str, str]:
    return {str(row[key]): str(row.get("display_name") or row.get("role_label") or "") for row in rows if row.get(key)}


def _workspaces(code: str) -> list[dict[str, Any]]:
    grammar = {
        "amg": shell.amg_grammar(),
        "bzg": shell.bzg_grammar(),
        "uma-blu": shell.uma_grammar(),
        "ggv": shell.ggv_grammar(),
    }[code]
    items = []
    for row in grammar:
        href = row.get("href")
        if not href:
            continue
        items.append(
            {
                "id": _text(row.get("key") or "workspace"),
                "name": _text(row.get("label") or "Workspace"),
                "href": str(href),
                "status": "LINKED",
            }
        )
    return items


def _level(name: str, state: str, why: str, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"level": name, "state": state, "why": why, "items": items or []}


def _hierarchy(snapshot: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    entity_id = spec["entity_id"]
    brand_id = spec["brand_id"]
    entities = [row for row in snapshot["entities"] if row["entity_id"] == entity_id]
    entity = entities[0] if entities else None
    brands = [row for row in snapshot["brands"] if row["entity_id"] == entity_id]
    if brand_id:
        brands = [row for row in brands if row["brand_id"] == brand_id]
    brand_ids = {row["brand_id"] for row in brands}
    link_ids = {row["location_id"] for row in snapshot["brand_locations"] if row["brand_id"] in brand_ids}
    sites = [row for row in snapshot["locations"] if row["location_id"] in link_ids]
    if spec["grain"] == "venue":
        departments: list[dict[str, Any]] = []
        dept_state = "MISSING"
        dept_why = (
            "Departments are stored on the legal entity, not on this venue. "
            "No venue department was read."
        )
    else:
        departments = [
            row
            for row in snapshot["departments"]
            if row["entity_id"] == entity_id and row.get("ownership") in {None, "ENTITY"}
        ]
        dept_state = "READ" if departments else "EMPTY"
        dept_why = (
            "Departments on this legal entity."
            if departments
            else "No department is stored for this legal entity."
        )
    workspaces = _workspaces(spec["code"])
    if spec["grain"] == "venue":
        objects: list[dict[str, Any]] = []
        object_state = "MISSING"
        object_why = (
            "Work items are stored on the legal entity, not on this venue. "
            "This venue's objects were not taken from the group total."
        )
    else:
        objects = [
            {
                "id": row["work_item_id"],
                "name": row["title"] or "MISSING",
                "status": row["status"] or "MISSING",
            }
            for row in snapshot["work"]
            if row["owning_entity_id"] == entity_id
        ]
        object_state = "READ" if objects else "EMPTY"
        object_why = (
            "Work items on this legal entity."
            if objects
            else "No work item is stored for this legal entity. Empty is not unknown."
        )
    entity_items = []
    if entity:
        entity_items.append(
            {
                "id": entity["entity_id"],
                "name": entity["display_name"] or "MISSING",
                "legal_name": entity["legal_name"] or "MISSING",
                "status": entity["status"] or "MISSING",
                "href": f"/business/{spec['code']}" if spec["grain"] == "entity" else "/business/bzg",
            }
        )
    return [
        _level("WOLF/GROUP", "READ", "Owner Command is the group desk.", [
            {"id": "WOLF", "name": "Wolf", "status": "GROUP", "href": "/wolf"},
        ]),
        _level(
            "LEGAL ENTITY",
            "READ" if entity else "MISSING",
            entity["legal_name"] if entity and entity.get("legal_name") else "This legal entity was not in the register.",
            entity_items,
        ),
        _level(
            "SITE",
            "READ" if sites else "EMPTY",
            "Sites linked to the brand on this dashboard." if sites else "No site is stored for this business.",
            [
                {
                    "id": row["location_id"],
                    "name": row["display_name"] or "MISSING",
                    "status": row["status"] or "MISSING",
                }
                for row in sites
            ],
        ),
        _level(
            "BUSINESS UNIT/VENUE",
            "READ" if brands else "EMPTY",
            "Brands on this dashboard." if brands else "No brand is stored for this dashboard.",
            [
                {
                    "id": row["brand_id"],
                    "name": row["display_name"] or "MISSING",
                    "status": row["status"] or "MISSING",
                    "kind": row["brand_type"] or "MISSING",
                }
                for row in brands
            ],
        ),
        _level("DEPARTMENT/FUNCTION", dept_state, dept_why, [
            {
                "id": row["department_id"],
                "name": row["display_name"] or "MISSING",
                "status": row["status"] or "MISSING",
            }
            for row in departments
        ]),
        _level(
            "WORKSPACE",
            "READ" if workspaces else "EMPTY",
            "Specialist workspaces stay underneath. Their figures are not copied here.",
            workspaces,
        ),
        _level("OBJECT", object_state, object_why, objects),
    ]


def _section(key: str, title: str, state: str, why: str, *, value: Any = None, items: list | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "state": state,
        "value": value,
        "why": why,
        "items": items or [],
        "green_kpi": False,
    }


def _open_work(snapshot: dict[str, Any], entity_id: str) -> list[dict[str, Any]]:
    return [
        row
        for row in snapshot["work"]
        if row["owning_entity_id"] == entity_id and row.get("status") in {"OPEN", "IN_PROGRESS"}
    ]


def _sections(snapshot: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    entity_id = spec["entity_id"]
    venue = spec["grain"] == "venue"
    names = _lookup(snapshot["persons"], "person_id")
    roles = {row["person_id"]: row["role_label"] for row in snapshot["roles"]}
    if venue:
        today = _section(
            "today",
            "Today",
            "MISSING",
            "Today's work is stored on the legal entity, not on this venue. No venue total was invented.",
        )
        people = _section(
            "people",
            "People",
            "MISSING",
            "No venue work is on record, so no owner of today's work was read.",
        )
        exceptions = _section(
            "exceptions",
            "Exceptions",
            "MISSING",
            "Governance exceptions are stored on the legal entity, not on this venue.",
        )
        priorities = _section(
            "priorities",
            "Priorities",
            "MISSING",
            "No venue priority is stored. The legal-entity list was not copied here.",
        )
    else:
        if not (snapshot.get("present") or {}).get("work", True):
            today = _section(
                "today",
                "Today",
                "UNAVAILABLE",
                "The work record could not be read. No count was invented.",
            )
            open_rows = []
        else:
            work = [row for row in snapshot["work"] if row["owning_entity_id"] == entity_id]
            open_rows = _open_work(snapshot, entity_id)
            blocked = [row for row in work if row.get("status") == "BLOCKED"]
            today = _section(
                "today",
                "Today",
                "READ",
                "Open work is a count of stored rows. Zero is an empty read, not a claim that today is fine.",
                value={"open": len(open_rows), "blocked": len(blocked)},
            )
        owners = []
        for row in open_rows:
            pid = row.get("owner_person_id")
            if not pid or pid not in names:
                owners.append(
                    {
                        "work": row.get("title") or "MISSING",
                        "person": "MISSING",
                        "role": roles.get(pid or "", "MISSING"),
                    }
                )
                continue
            owners.append(
                {
                    "work": row.get("title") or "MISSING",
                    "person": names[pid],
                    "role": roles.get(pid, "MISSING"),
                }
            )
        people = _section(
            "people",
            "People",
            "READ" if owners else "EMPTY",
            "Who owns today's open work, with the role on the assignment."
            if owners
            else "No open work is on record, so no owner of today's work was read.",
            items=owners,
        )
        if not (snapshot.get("present") or {}).get("exceptions", True):
            open_ex = []
            exceptions = _section(
                "exceptions",
                "Exceptions",
                "UNAVAILABLE",
                "The exception record could not be read. No count was invented.",
            )
        else:
            open_ex = [
                row
                for row in snapshot["exceptions"]
                if row["entity_id"] == entity_id and row.get("status") in {"REQUESTED", "AUTHORISED"}
            ]
            ledger = snapshot.get("ledger_classification") or {}
            ex_split = ledger.get("exceptions") or {}
            ev_split = ledger.get("evidence") or {}
            dec_split = ledger.get("approval_decisions") or {}
            exceptions = _section(
                "exceptions",
                "Exceptions",
                "READ",
                (
                    "REQUESTED and AUTHORISED rows on this legal entity. "
                    f"Valid operational exceptions: {ex_split.get('valid_operational', 'UNKNOWN')}. "
                    f"INVALID/TEST exceptions: {ex_split.get('invalid_test', 'UNKNOWN')}. "
                    f"Valid operational evidence: {ev_split.get('valid_operational', 'UNKNOWN')}. "
                    f"INVALID/TEST evidence: {ev_split.get('invalid_test', 'UNKNOWN')}. "
                    f"Valid operational approval decisions: {dec_split.get('valid_operational', 'UNKNOWN')}. "
                    f"INVALID/TEST approval decisions: {dec_split.get('invalid_test', 'UNKNOWN')}. "
                    "Severity has no column, so it stays MISSING."
                ),
                value=len(open_ex),
                items=[
                    {
                        "id": row["exception_id"],
                        "issue": row.get("reason") or "MISSING",
                        "state": row.get("status") or "MISSING",
                        "severity": "MISSING",
                        "owner_role": roles.get(row.get("requested_by_person_id") or "", "MISSING"),
                    }
                    for row in open_ex
                ],
            )
        pri_rows = open_rows[:3]
        priorities = _section(
            "priorities",
            "Priorities",
            "READ" if pri_rows else "EMPTY",
            "Up to three open work items. No fourth was invented."
            if pri_rows
            else "No priorities are on the work record.",
            items=[
                {
                    "title": row.get("title") or "MISSING",
                    "status": row.get("status") or "MISSING",
                    "priority": row.get("priority") if isinstance(row.get("priority"), int) else "MISSING",
                }
                for row in pri_rows
            ],
        )
    targets = [
        row
        for row in snapshot["targets"]
        if row.get("entity_id") in {None, entity_id}
        and (not venue or row.get("brand_id") == spec["brand_id"])
    ]
    performance = _section(
        "performance",
        "Performance",
        "READ" if targets else "MISSING",
        "Targets stored for this business."
        if targets
        else "No performance target is stored. A result against a target was not calculated.",
        items=targets,
    )
    finance = snapshot.get("finance_state") or "UNAVAILABLE"
    if finance not in truth.DISPLAY_STATES and finance not in {"MISSING", "EMPTY", "READ"}:
        finance = "UNKNOWN"
    money = _section(
        "money",
        "Money",
        finance,
        "Genuinely available cash was not read. The books were not opened. This is not zero.",
        value=None,
    )
    sources = (snapshot.get("sources") or {}).get(spec["surface"]) or []
    if spec["code"] == "amg":
        occ = next((row["display_state"] for row in sources if row["source_id"] == "yanolja"), "UNAVAILABLE")
        customers = _section(
            "customers",
            "Customers / guests",
            occ if occ in truth.DISPLAY_STATES else "UNKNOWN",
            "No hotel-engine guest figure was read. Guest issues are UNKNOWN, not zero.",
            value=None,
            items=[{"guest_issues": "UNKNOWN"}],
        )
    elif spec["code"] in {"bzg", "uma-blu"}:
        customers = _section(
            "customers",
            "Customers / guests",
            "UNKNOWN",
            "Guest issues have no source on this dashboard. ESB was not counted as guests.",
            value=None,
            items=[{"guest_issues": "UNKNOWN"}],
        )
    else:
        customers = _section(
            "customers",
            "Customers / guests",
            "UNKNOWN",
            "No customer list was read. The specialist workspace underneath was not copied here.",
            value=None,
            items=[{"guest_issues": "MISSING"}],
        )
    if not (snapshot.get("present") or {}).get("activity", True):
        activity = _section(
            "activity",
            "Recent activity",
            "UNAVAILABLE",
            "The audit record could not be read. No activity was invented.",
        )
    else:
        if venue:
            events = [
                row
                for row in snapshot["activity"]
                if row.get("brand_id") == spec["brand_id"]
            ][:8]
            activity_why = (
                "Audit rows that name this venue."
                if events
                else "No audit row names this venue. Legal-entity history was not copied here."
            )
        else:
            events = [row for row in snapshot["activity"] if row.get("entity_id") == entity_id][:8]
            activity_why = (
                "Latest audit rows on this legal entity."
                if events
                else "No audit row names this legal entity."
            )
        activity_items = []
        for row in events:
            pid = row.get("actor_person_id")
            activity_items.append(
                {
                    "when": row.get("occurred_at") or "MISSING",
                    "action": row.get("action") or "MISSING",
                    "result": row.get("result") or "MISSING",
                    "actor": names.get(pid or "", "MISSING"),
                    "owner_role": roles.get(pid or "", "MISSING"),
                }
            )
        activity = _section(
            "activity",
            "Recent activity",
            "READ" if activity_items else "EMPTY",
            activity_why,
            items=activity_items,
        )
    ordered = {
        "today": today,
        "performance": performance,
        "people": people,
        "money": money,
        "customers": customers,
        "exceptions": exceptions,
        "priorities": priorities,
        "activity": activity,
    }
    return [ordered[key] for key in SECTIONS]


def project_board(
    snapshot: dict[str, Any],
    spec: dict[str, Any],
    *,
    digest: str | None = None,
    held: str | None = None,
) -> dict[str, Any]:
    canonical = digest or _digest(snapshot)
    projected = held if held is not None else canonical
    projection = _projection(canonical, projected)
    current = projection.get("display_state") in {"LIVE", "CURRENT"} and projection.get("shown_as_current") is True
    board: dict[str, Any] = {
        "code": spec["code"],
        "label": spec["label"],
        "href": f"/business/{spec['code']}",
        "entity_id": spec["entity_id"],
        "brand_id": spec["brand_id"],
        "grain": spec["grain"],
        "surface": spec["surface"],
        "projection": projection,
        "sections_shown_as_current": current,
        "green_kpi": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
    }
    if not current:
        board["hierarchy"] = []
        board["sections"] = []
        board["withheld_why"] = (
            "This dashboard does not match the canonical state. Figures are not shown as current."
        )
        return board
    board["hierarchy"] = _hierarchy(snapshot, spec)
    board["sections"] = _sections(snapshot, spec)
    board["withheld_why"] = None
    return board


def project_all(
    snapshot: dict[str, Any],
    *,
    held: str | None = None,
) -> list[dict[str, Any]]:
    digest = _digest(snapshot)
    return [project_board(snapshot, spec, digest=digest, held=held) for spec in BUSINESSES]


def prove_propagation(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two in-memory snapshots. Does not write the catalog."""
    first = project_all(before)
    second = project_all(after)
    old_digest = first[0]["projection"]["canonical"] if first else ""
    held = project_all(after, held=old_digest)
    updated = []
    stale = []
    for fresh, frozen in zip(second, held):
        updated.append(
            {
                "code": fresh["code"],
                "canonical": fresh["projection"]["canonical"],
                "display_state": fresh["projection"]["display_state"],
                "shown_as_current": fresh["projection"]["shown_as_current"],
                "changed": fresh["projection"]["canonical"] != old_digest,
            }
        )
        stale.append(
            {
                "code": frozen["code"],
                "display_state": frozen["projection"]["display_state"],
                "shown_as_current": frozen["projection"]["shown_as_current"],
                "sections_shown_as_current": frozen["sections_shown_as_current"],
                "withheld": bool(frozen.get("withheld_why")),
            }
        )
    return {
        "ok": True,
        "before_digest": old_digest,
        "after_digest": second[0]["projection"]["canonical"] if second else "",
        "updated": updated,
        "stale": stale,
        "ledger_write": False,
    }


def _quiet() -> dict[str, Any]:
    return {
        "ok": True,
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "levels": list(LEVELS),
        "sections": list(SECTIONS),
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "money": None,
        "payment_executed": False,
        "green_kpi": False,
        "ledger_write": False,
        "external_writes": False,
        "proven": False,
        "ready": False,
    }


def _unavailable(reason: str, code: str | None = None) -> dict[str, Any]:
    body = _quiet()
    body["ok"] = False
    body["read"] = "UNAVAILABLE"
    body["why"] = reason
    if code:
        body["code"] = code
    body["businesses"] = []
    return body


def build_dashboards(
    *,
    verified_person_id: str,
    code: str | None = None,
    held: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    empire.require_owner(verified_person_id)
    if code is not None and code not in CODES:
        raise DashboardError("Unknown business dashboard.", code="not_found")
    try:
        snap = snapshot if snapshot is not None else read_snapshot()
        boards = project_all(snap, held=held)
    except DashboardError:
        raise
    except Exception as exc:  # noqa: BLE001
        return _unavailable(type(exc).__name__, code)
    if code is not None:
        boards = [row for row in boards if row["code"] == code]
    body = _quiet()
    body["read"] = "READ"
    body["code"] = code
    body["businesses"] = boards
    body["canonical"] = boards[0]["projection"]["canonical"] if boards else None
    return body
