"""CRM Ops × Needs-You connective — CRM/Lead/Habitat projection on Lead Spine.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json).

Owner, and Amanda when ASG-AMANDA-CM-1 is already active, see derived
CRM/Lead/Habitat Needs-You / Morning seed / lead-loop rows on the existing
Lead Spine desk. Does not copy the GGV Ops Needs-You strip. Does not invent
Habitat commission, staff_ready, PROVEN, READY, Haikal done, or Devi done.
Does not cut over CRM or write Klaviyo / Metricool / money.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from core import lead_spine as spine

BETA_ROOT = spine.BETA_ROOT
CATALOG_DB = spine.CATALOG_DB

CONNECTIVE_SCHEMA_ID = "wolf.crm-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "crm_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-crm-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-crm-ops-needs-you-connective-20260923"
CONNECTIVE_BOUND = "beta-crm-loop-safe"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "lead_loop",
)
CONNECTIVE_DEPTH_KINDS = frozenset({"morning_seed", "waiting_others", "needs_you"})
CRM_TARGET_CRS: tuple[str, ...] = (
    "CR-ff42f3a7c49caa79",
    "CR-820682ce791563fa",
    "CR-e5ff219bb1d585f7",
    "CR-c8719063fb940ed4",
)
CAP_IDS: tuple[str, ...] = ("CAP-CRM-01", "CAP-CRM-02", "CAP-CRM-03", "CAP-CRM-04")
AU_CRM_HABITAT = "AU-CRM-01-HABITAT"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
AU_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"
OWNER = "PERS-MATT"
AMANDA = "PERS-AMANDA"
HABITAT_BRAND = "habitat"
ROLE_CONTENT_MGMT = "ROLE-CONTENT-MGMT"
AMANDA_ASSIGNMENT = "ASG-AMANDA-CM-1"
SCOPE_CRM_HABITAT_LEAD = "SCOPE-CRM-HABITAT-LEAD"
_NAME_RE = re.compile(r"[a-z]+")
_SEAT_NAME_TOKENS: dict[str, frozenset[str]] = {
    OWNER: frozenset({"matt", "owner"}),
    AMANDA: frozenset({"amanda"}),
}
_CRM_SURFACES = frozenset(
    {"lead_spine", "crm", "habitat_operator", "crm_ops", "habitat_lead"}
)
_OTHER_BUSINESS = frozenset({"GGV", "BZG", "AMG", "SYSTEM", "INTEL", "SALE", "FIN"})
_OTHER_SURFACES = frozenset(
    {
        "ggv_ops",
        "nas_library",
        "smart_upload",
        "uma_ops",
        "bzg_ops",
        "uma_blu",
        "amg_ops",
        "progress",
        "integration_health",
    }
)


class ConnectiveError(spine.LeadSpineError):
    """Seat and handoff failures. status_code is for the Beta route only."""

    def __init__(self, message: str, *, code: str, status: int):
        super().__init__(message, code=code)
        self.status_code = status

    @property
    def http_status(self) -> int:
        return self.status_code


def _name_tokens(*parts: Any) -> set[str]:
    blob = " ".join(str(p or "") for p in parts).lower()
    return set(_NAME_RE.findall(blob))


def _needs_you_module():
    from core import owner_progress_needs_you_depth as nye

    return nye


def _morning_meta() -> dict[str, dict[str, Any]]:
    from core import owner_commissioning_queue as ocq

    return {str(t.get("id")): t for t in ocq.seed_templates() if t.get("id")}


def _cr_state(catalog_db: Path | str | None, cr_id: str) -> str:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return "OPEN"
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except (OSError, sqlite3.Error):
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


def au_crm_habitat_state() -> str:
    """Read AU-CRM-01-HABITAT. Does not write the discovery file."""
    try:
        data = json.loads(AU_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "NOT STARTED"
    rows = data if isinstance(data, list) else []
    for row in rows:
        if isinstance(row, dict) and str(row.get("au_id") or "") == AU_CRM_HABITAT:
            state = str(row.get("state") or "").strip()
            return state or "NOT STARTED"
    return "NOT STARTED"


def _amanda_already_authorised(catalog_db: Path | str | None = None) -> bool:
    """True only when Amanda's existing content-mgmt CRM Habitat assignment is active.

    Does not insert a role, scope, or Habitat commission.
    """
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return False
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except (OSError, sqlite3.Error):
        return False
    try:
        row = conn.execute(
            """
            SELECT 1
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_assignment_scopes s ON s.assignment_id = a.assignment_id
            WHERE a.person_id = ?
              AND a.assignment_id = ?
              AND a.status = 'ACTIVE' AND a.end_at IS NULL
              AND p.role_id = ?
              AND s.status = 'ACTIVE' AND (s.end_at IS NULL OR s.end_at = '')
              AND s.scope_id = ?
            LIMIT 1
            """,
            (AMANDA, AMANDA_ASSIGNMENT, ROLE_CONTENT_MGMT, SCOPE_CRM_HABITAT_LEAD),
        ).fetchone()
    except sqlite3.Error:
        return False
    finally:
        conn.close()
    return bool(row)


def require_connective_seat(
    person_id: str | None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner, or Amanda only when her CRM Habitat assignment is already authorised.

    Haikal, Misa, and Devi stay outside this strip even if a shared CRM operator
    scope exists on their other roles. Commission is not inserted.
    """
    pid = (person_id or "").strip()
    if pid == OWNER:
        return {
            "person_id": pid,
            "seat": "owner",
            "sees_full_crm": True,
            "authorised": True,
            "invented_commission": False,
            "live_habitat_commission": False,
        }
    if pid == AMANDA and _amanda_already_authorised(catalog_db):
        return {
            "person_id": pid,
            "seat": "crm_lead",
            "sees_full_crm": False,
            "authorised": True,
            "invented_commission": False,
            "live_habitat_commission": False,
        }
    if pid == AMANDA:
        raise ConnectiveError(
            "Amanda CRM seat is not authorised on this catalog. Commission is not invented.",
            code="forbidden",
            status=403,
        )
    raise ConnectiveError(
        "CRM Needs-You is for the Owner and the existing Amanda CRM lead seat.",
        code="forbidden",
        status=403,
    )


def _is_crm_scoped(item: dict[str, Any]) -> bool:
    """CRM / Lead / Habitat commissioning or Habitat lead-loop. GGV strip stays out."""
    kind = str(item.get("kind") or "")
    if kind == "lead_loop":
        return str(item.get("brand_id") or "") == HABITAT_BRAND
    cap = str(item.get("capability") or "")
    business = str(item.get("business") or "").upper()
    domain = str(item.get("domain") or "").upper()
    surface = str(item.get("surface") or "").lower()
    if cap.startswith(("CAP-GGV", "CAP-BZG", "CAP-AMG", "CAP-CORE", "CAP-INTG", "CAP-INTEL")):
        return False
    if business in _OTHER_BUSINESS:
        return False
    if surface in _OTHER_SURFACES:
        return False
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "source", "open_href", "route", "object_id", "href")
    ).lower()
    if any(
        token in blob
        for token in (
            "/ggv",
            "habitat content",
            "habitat-publish",
            "/bzg/",
            "/amg",
            "metricool",
            "klaviyo",
        )
    ):
        return False
    if cap.startswith("CAP-CRM") or cap.startswith("AU-CRM"):
        return True
    if business == "CRM" or domain in {"CRM", "D-CRM"}:
        return True
    if surface in _CRM_SURFACES:
        return True
    if any(token in blob for token in ("/lead-spine", "/habitat-operator", "/crm")):
        return True
    oid = str(item.get("object_id") or "")
    if oid.startswith(("CMQ-CRM", "AU-CRM")):
        return True
    return False


def _in_scope_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every CRM-scoped row. Amanda sees in-scope rows only."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    audience = str(item.get("audience") or "").upper()
    if audience == "NEEDS_MATT":
        return False
    kind = str(item.get("kind") or "")
    if kind == "lead_loop" and seat.get("seat") == "crm_lead":
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
    return bool(tokens & allowed)


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_lead_loop": kind == "lead_loop",
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "money": None,
        "bzg_compose": False,
    }
    if kind in CONNECTIVE_DEPTH_KINDS:
        block.update(
            {
                "detail": f"/api/progress/needs-you/items/{oid}",
                "acknowledge": f"/api/progress/needs-you/items/{oid}/acknowledge",
                "staff_detail": f"/api/staff/ops-routing/needs-you/items/{oid}",
                "staff_acknowledge": f"/api/staff/ops-routing/needs-you/items/{oid}/acknowledge",
                "crm_detail": f"/api/leads/needs-you/items/{oid}",
                "crm_acknowledge": f"/api/leads/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "lead_loop":
        block.update(
            {
                "detail": f"/api/leads/{oid}",
                "action": f"/api/leads/{oid}/touch",
                "desk": "/lead-spine",
                "read_only_here": True,
            }
        )
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/lead-spine"
    return {
        "object_id": str(item.get("object_id") or ""),
        "kind": item.get("kind"),
        "title": item.get("title"),
        "who": item.get("who"),
        "audience": item.get("audience"),
        "priority": item.get("priority"),
        "status": item.get("operator_status") or item.get("status"),
        "href": href,
        "owner_person_id": item.get("owner_person_id"),
        "demo": bool(item.get("demo")),
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "live_habitat_commission": False,
        "habitat_commissioned": False,
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "money": None,
        "bzg_compose": False,
        "handoff": _handoff_block(item),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/lead-spine"
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope CRM Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "crm_ops_needs_you_connective",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "live_habitat_commission": False,
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "money": None,
        "bzg_compose": False,
    }


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Lead Spine",
        "href": "/lead-spine",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "money": None,
        "bzg_compose": False,
    }


def _honesty_tail() -> dict[str, Any]:
    return {
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "invented_staff_ready": False,
        "live_habitat_commission": False,
        "habitat_commissioned": False,
        "au_crm_01_habitat": au_crm_habitat_state(),
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "external_crm_write": False,
        "money": None,
        "bzg_compose": False,
        "duplicate_mutate_surface": False,
        "false_resolve_cr": False,
        "ggv_strip_duplicated": False,
    }


def _empty_connective(*, why: str) -> dict[str, Any]:
    body = {
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
        "pack_next_action": _pack_href_next(),
        "empty_message": why,
        "reuse_needs_you_depth": True,
    }
    body.update(_honesty_tail())
    return body


def _sort_connective(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        kind_rank = {
            "morning_seed": 0,
            "waiting_others": 1,
            "needs_you": 2,
            "lead_loop": 3,
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
            "domain",
        ):
            if extra.get(key) and not merged.get(key):
                merged[key] = extra[key]
        if not merged.get("who") and extra.get("person_to_test"):
            merged["who"] = extra.get("person_to_test")
        if not _is_crm_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "CRM"
        out.append(merged)
    return out


def _lead_loop_rows(
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Habitat leads that already need triage. An empty queue is not invented work."""
    own = conn is None
    try:
        c = conn or spine._open(db_path)
    except Exception:  # noqa: BLE001
        return []
    try:
        present = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_leads'"
        ).fetchone()
        if not present:
            return []
        rows = c.execute(
            "SELECT * FROM core_leads WHERE brand_id=? ORDER BY lead_id ASC",
            (HABITAT_BRAND,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if own:
            c.close()
    out: list[dict[str, Any]] = []
    for raw in rows:
        lead = dict(raw)
        if not spine.needs_triage(lead):
            continue
        oid = str(lead.get("lead_id") or "").strip()
        if not oid:
            continue
        touch = (lead.get("first_human_touch_at") or "").strip()
        owner_pid = (lead.get("owner_person_id") or "").strip() or None
        audience = "NEEDS_MATT" if owner_pid == OWNER else "NEEDS_STAFF"
        out.append(
            {
                "object_id": oid,
                "kind": "lead_loop",
                "title": spine._demo_label(lead.get("provenance_json")) or oid,
                "who": owner_pid,
                "owner_person_id": owner_pid,
                "audience": audience,
                "priority": "P1" if touch else "P0",
                "status": lead.get("wolf_stage") or "OPEN",
                "business": "CRM",
                "domain": "D-CRM",
                "brand_id": HABITAT_BRAND,
                "surface": "lead_spine",
                "href": "/lead-spine",
                "open_href": "/lead-spine",
                "demo": spine._row_is_demo(lead),
                "invented": False,
                "live_habitat_commission": False,
            }
        )
    return out


def _crm_candidates(
    *,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(_lead_loop_rows(conn=conn, db_path=db_path))
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
    crm = {cr: _cr_state(catalog_db, cr) for cr in CRM_TARGET_CRS}
    return {
        "caps": caps,
        "crm_crs": crm,
        "progress_core_crs": progress,
        "au_crm_01_habitat": au_crm_habitat_state(),
        "false_resolve_cr": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "live_habitat_commission": False,
        "crm_cutover": False,
        "bzg_compose": False,
        "money": None,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """CRM/Lead/Habitat Needs-You / Morning seed / lead-loop projection.

    Owner sees the full CRM-scoped set. Amanda sees in-scope rows only when
    her existing assignment is already active. EMPTY honesty when none.
    Counts are the in-scope length.
    """
    seat = require_connective_seat(verified_person_id, catalog_db)
    try:
        rows = _crm_candidates(state_path=state_path, conn=conn, db_path=db_path)
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "CRM Needs-You connective read failed "
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
    body = {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
            "sees_full_crm": seat.get("person_id") == OWNER,
            "invented_commission": False,
            "live_habitat_commission": False,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "pack_next_action": _pack_href_next(),
        "empty_message": (
            "No CRM/Lead/Habitat-scoped Needs-You / Morning seed / lead-loop rows "
            "in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "source": "crm_scoped_needs_you_morning_lead_loop",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=catalog_db),
        "reuse_needs_you_depth": True,
        "why": (
            "Derived CRM/Lead/Habitat commissioning and recorded Habitat lead-loop "
            "rows on Lead Spine. Owner sees the full CRM-scoped projection. The "
            "existing Amanda CRM seat sees only in-scope rows. Counts are the "
            "in-scope length. Empty is not invented work. The GGV Ops strip is "
            "not copied here. Habitat commission stays uninvented."
        ),
    }
    body.update(_honesty_tail())
    return body


def _find_crm_item(
    object_id: str,
    *,
    state_path=None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _crm_candidates(state_path=state_path, conn=conn, db_path=db_path):
        if str(row.get("object_id") or "") == oid:
            return row
    return None


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of CRM seat scope is 403. Reuses existing handoffs."""
    seat = require_connective_seat(verified_person_id, catalog_db)
    found = _find_crm_item(object_id, state_path=state_path, conn=conn, db_path=db_path)
    if found is None:
        raise ConnectiveError(
            f"CRM Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "CRM Needs-You item is outside this seat's scope.",
            code="forbidden",
            status=403,
        )
    body = {
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
        "human_done": False,
        "caps": connective_cap_honesty(catalog_db=catalog_db),
    }
    body.update(_honesty_tail())
    return body


def acknowledge_handoff(
    object_id: str,
    *,
    verified_person_id: str,
    note: str | None = None,
    state_path=None,
    events_path=None,
    catalog_db: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Lead-loop rows keep the existing Lead Spine actions. This route does not
    open a second mutate store and does not write Klaviyo, Metricool, or CRM.
    """
    seat = require_connective_seat(verified_person_id, catalog_db)
    found = _find_crm_item(object_id, state_path=state_path, conn=conn, db_path=db_path)
    if found is None:
        raise ConnectiveError(
            f"CRM Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "CRM Needs-You item is outside this seat's scope.",
            code="forbidden",
            status=403,
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise ConnectiveError(
            "Habitat lead-loop rows use the existing Lead Spine actions. "
            "This route does not open a second mutate surface, does not cut over CRM, "
            "and does not write Klaviyo or Metricool.",
            code="handoff_only",
            status=405,
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
        catalog_db=catalog_db,
        conn=conn,
        db_path=db_path,
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
        "human_done": False,
        "commissioned": False,
        "cr_resolved": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "live_habitat_commission": False,
        "habitat_commissioned": False,
        "crm_cutover": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "money": None,
        "bzg_compose": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "Devi done, and Habitat commissioned stay uninvented. No CRM cutover."
        ),
    }


def _attach_needs_you_connective(
    payload: dict[str, Any],
    *,
    person_id: str | None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Prefer an in-scope Needs-You row over the generic Lead Spine href."""
    pid = (person_id or "").strip()
    if not pid:
        return
    try:
        strip = needs_you_connective_strip(
            verified_person_id=pid, conn=conn, db_path=db_path
        )
    except spine.LeadSpineError:
        return
    pack_next = payload.get("next_action")
    if not isinstance(pack_next, dict) or pack_next.get("code") == "needs_you_connective":
        pack_next = _pack_href_next()
    payload["needs_you_connective"] = strip
    payload["pack_next_action"] = pack_next
    preferred = strip.get("next_action") if strip.get("count") else None
    payload["next_action"] = preferred if isinstance(preferred, dict) else pack_next


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing PROVEN.",
        code="proven_refused",
        status=405,
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing READY.",
        code="ready_refused",
        status=405,
    )


def refuse_staff_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing staff_ready.",
        code="staff_ready_refused",
        status=405,
    )


def refuse_haikal_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing Haikal human done.",
        code="haikal_done_refused",
        status=405,
    )


def refuse_devi_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing Devi done. Devi retest stays parked.",
        code="devi_done_refused",
        status=405,
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses money movement.",
        code="money_refused",
        status=405,
    )


def refuse_crm_cutover(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses CRM cutover and external CRM write.",
        code="crm_cutover_refused",
        status=405,
    )


def refuse_klaviyo(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses a Klaviyo write.",
        code="klaviyo_write_refused",
        status=405,
    )


def refuse_metricool(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses a Metricool write.",
        code="metricool_write_refused",
        status=405,
    )


def refuse_habitat_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses inventing Habitat commissioned. "
        "AU-CRM-01-HABITAT stays NOT STARTED.",
        code="habitat_done_refused",
        status=405,
    )


def refuse_bzg_compose(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "CRM Lead Spine refuses BZG compose.",
        code="bzg_compose_refused",
        status=405,
    )


def connective_refuse_code(path: str) -> str | None:
    refused = {
        "/api/leads/haikal-done": "haikal_done",
        "/api/leads/haikal_done": "haikal_done",
        "/api/leads/devi-done": "devi_done",
        "/api/leads/devi_done": "devi_done",
        "/api/leads/habitat-done": "habitat_done",
        "/api/leads/habitat_done": "habitat_done",
        "/api/leads/needs-you/staff-ready": "staff_ready",
        "/api/leads/needs-you/haikal-done": "haikal_done",
        "/api/leads/needs-you/devi-done": "devi_done",
        "/api/leads/needs-you/habitat-done": "habitat_done",
        "/api/leads/needs-you/proven": "proven",
        "/api/leads/needs-you/ready": "ready",
        "/api/leads/needs-you/money": "money",
        "/api/leads/needs-you/crm-cutover": "crm_cutover",
        "/api/leads/needs-you/klaviyo": "klaviyo",
        "/api/leads/needs-you/metricool": "metricool",
        "/api/leads/needs-you/bzg-compose": "bzg_compose",
    }
    return refused.get(path)


def _apply_connective_refuse(code: str) -> None:
    mapping = {
        "staff_ready": refuse_staff_ready,
        "haikal_done": refuse_haikal_done,
        "devi_done": refuse_devi_done,
        "habitat_done": refuse_habitat_done,
        "proven": refuse_proven,
        "ready": refuse_ready,
        "money": refuse_money,
        "crm_cutover": refuse_crm_cutover,
        "klaviyo": refuse_klaviyo,
        "metricool": refuse_metricool,
        "bzg_compose": refuse_bzg_compose,
    }
    fn = mapping.get(code)
    if fn is None:
        raise ConnectiveError(f"refused: {code}", code="refused", status=405)
    fn()
