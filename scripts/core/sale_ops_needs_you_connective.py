"""Sale Ops × Needs-You connective — Sale/Evidence/Buyer projection on the Sale desk.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json).

Owner sees derived Sale/Evidence/Buyer Needs-You / Morning seed / sale-loop
rows on the existing Sale Management Cluster and Sale Evidence desk. Does not
copy the CRM, GGV, or BZG Ops Needs-You strips. Does not invent staff_ready,
PROVEN, READY, Haikal done, Devi done, buyer-live, or a controlled export.
Does not compose BZG or move money.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import sale_mgmt_cluster as sale

BETA_ROOT = sale.BETA_ROOT
CATALOG_DB = sale.CATALOG_DB

CONNECTIVE_SCHEMA_ID = "wolf.sale-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "sale_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-sale-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-sale-ops-needs-you-connective-20260923"
CONNECTIVE_BOUND = "beta-connective-safe"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "sale_loop",
)
CONNECTIVE_DEPTH_KINDS = frozenset({"morning_seed", "waiting_others", "needs_you"})
SALE_TARGET_CRS: tuple[str, ...] = (
    sale.CR_01,
    sale.CR_02,
    sale.CR_03,
    sale.CR_04,
)
CAP_IDS: tuple[str, ...] = ("CAP-SALE-01", "CAP-SALE-02", "CAP-SALE-03", "CAP-SALE-04")
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OWNER = "PERS-MATT"
_SALE_SURFACES = frozenset(
    {
        "sale_ops",
        "sale_evidence",
        "sale_buyer",
        "sale_mgmt",
        "buyer_dataroom",
        "buyer_mode",
        "attack_audit",
        "sale_evidence_pack",
    }
)
_OTHER_BUSINESS = frozenset(
    {"GGV", "BZG", "AMG", "SYSTEM", "INTEL", "CRM", "FIN", "HR"}
)
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
        "lead_spine",
        "crm",
        "habitat_operator",
        "crm_ops",
        "habitat_lead",
    }
)
_OTHER_CAPS = (
    "CAP-GGV",
    "CAP-BZG",
    "CAP-AMG",
    "CAP-CORE",
    "CAP-INTG",
    "CAP-INTEL",
    "CAP-CRM",
)


class ConnectiveError(Exception):
    """Seat and handoff failures. status_code is for the Beta route only."""

    def __init__(self, message: str, *, code: str, status: int):
        super().__init__(message)
        self.code = code
        self.status_code = status

    @property
    def http_status(self) -> int:
        return self.status_code


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


def require_connective_seat(person_id: str | None) -> dict[str, Any]:
    """Owner only. Haikal, Misa, Devi, and Amanda are not this Sale seat.

    Commission is not inserted. Buyer access is not granted.
    """
    pid = (person_id or "").strip()
    if pid == OWNER:
        return {
            "person_id": pid,
            "seat": "owner",
            "sees_full_sale": True,
            "authorised": True,
            "invented_commission": False,
            "buyer_live": False,
            "buyer_dataroom_live": False,
        }
    raise ConnectiveError(
        "Sale Needs-You is for the Owner seat. "
        "Haikal, Misa, Devi, and Amanda are not this Sale seat.",
        code="forbidden",
        status=403,
    )


def _is_sale_scoped(item: dict[str, Any]) -> bool:
    """Sale / Evidence / Buyer commissioning or recorded sale-loop. Other strips stay out."""
    kind = str(item.get("kind") or "")
    if kind == "sale_loop":
        return True
    cap = str(item.get("capability") or "")
    business = str(item.get("business") or "").upper()
    domain = str(item.get("domain") or "").upper()
    surface = str(item.get("surface") or "").lower()
    if cap.startswith(_OTHER_CAPS):
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
            "/bzg/",
            "/amg",
            "/lead-spine",
            "/habitat",
            "/crm",
            "metricool",
            "klaviyo",
        )
    ):
        return False
    if cap.startswith("CAP-SALE") or cap.startswith("AU-SALE"):
        return True
    if business == "SALE" or domain in {"SALE", "D-SALE"}:
        return True
    if surface in _SALE_SURFACES:
        return True
    if any(
        token in blob
        for token in (
            "/sale-evidence",
            "/sale-mgmt",
            "/sale/",
            "/buyer-dataroom",
            "/buyer-mode",
            "/attack-audit",
        )
    ):
        return True
    oid = str(item.get("object_id") or "")
    if oid.startswith(("CMQ-SALE", "AU-SALE")):
        return True
    return False


def _in_scope_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every Sale-scoped row. Other seats do not, including Owner-only rows."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    return False


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_sale_loop": kind == "sale_loop",
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "controlled_export_send": False,
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
                "sale_detail": f"/api/sale/mgmt-cluster/needs-you/items/{oid}",
                "sale_acknowledge": f"/api/sale/mgmt-cluster/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "sale_loop":
        block.update(
            {
                "detail": f"/api/sale/mgmt-cluster/objects/{oid}/operator",
                "action": f"/api/sale/mgmt-cluster/objects/{oid}/operator-action",
                "desk": item.get("href") or "/sale-mgmt-cluster",
                "read_only_here": True,
            }
        )
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/sale-mgmt-cluster"
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
        "reasons": list(item.get("reasons") or []),
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "controlled_export_send": False,
        "money": None,
        "bzg_compose": False,
        "handoff": _handoff_block(item),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/sale-mgmt-cluster"
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope Sale Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "sale_ops_needs_you_connective",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "money": None,
        "bzg_compose": False,
    }


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Sale Management Cluster",
        "href": "/sale-mgmt-cluster",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "buyer_live": False,
        "controlled_export": False,
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
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "controlled_export_send": False,
        "money": None,
        "bzg_compose": False,
        "duplicate_mutate_surface": False,
        "false_resolve_cr": False,
        "crm_strip_duplicated": False,
        "ggv_strip_duplicated": False,
        "bzg_strip_duplicated": False,
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
            "sale_loop": 3,
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
        if not _is_sale_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "SALE"
        out.append(merged)
    return out


def _sale_loop_rows(
    *,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Recorded Sale operator attention only. An empty loop is not invented work.

    Uses the existing Owner Empire consequence (handover / missing next /
    evidence-touch). Dismissed objects and untouched frameworks stay off.
    This does not invent a live buyer data room or a controlled export.
    """
    try:
        empire = sale.owner_empire_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
    except Exception:  # noqa: BLE001
        return []
    specs = {spec["id"]: spec for spec in sale.MODULE_SPECS}
    out: list[dict[str, Any]] = []
    for row in empire.get("items") or []:
        oid = str(row.get("object_id") or "").strip()
        if not oid:
            continue
        spec = specs.get(oid) or {}
        href = spec.get("href") or row.get("href") or "/sale-mgmt-cluster"
        out.append(
            {
                "object_id": oid,
                "kind": "sale_loop",
                "title": row.get("staff_title") or spec.get("staff_title") or oid,
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "priority": "P1",
                "status": "OPEN",
                "business": "SALE",
                "domain": "D-SALE",
                "surface": "sale_ops",
                "capability": spec.get("cap"),
                "href": href,
                "open_href": href,
                "reasons": list(row.get("reasons") or []),
                "invented": False,
                "buyer_live": False,
                "buyer_dataroom_live": False,
                "controlled_export": False,
            }
        )
    return out


def _sale_candidates(
    *,
    state_path=None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(
        _sale_loop_rows(
            operator_db=operator_db,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
    )
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
    sale_crs = {cr: _cr_state(catalog_db, cr) for cr in SALE_TARGET_CRS}
    return {
        "caps": caps,
        "sale_crs": sale_crs,
        "progress_core_crs": progress,
        "false_resolve_cr": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "bzg_compose": False,
        "money": None,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Sale/Evidence/Buyer Needs-You / Morning seed / sale-loop projection.

    Owner sees the full Sale-scoped set. EMPTY honesty when none.
    Counts are the in-scope length.
    """
    seat = require_connective_seat(verified_person_id)
    try:
        rows = _sale_candidates(
            state_path=state_path,
            operator_db=operator_db,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
        )
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "Sale Needs-You connective read failed "
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
            "sees_full_sale": seat.get("person_id") == OWNER,
            "invented_commission": False,
            "buyer_live": False,
            "buyer_dataroom_live": False,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "pack_next_action": _pack_href_next(),
        "empty_message": (
            "No Sale/Evidence/Buyer-scoped Needs-You / Morning seed / sale-loop "
            "rows in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "source": "sale_scoped_needs_you_morning_sale_loop",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=catalog_db),
        "reuse_needs_you_depth": True,
        "why": (
            "Derived Sale/Evidence/Buyer commissioning and recorded sale-loop "
            "rows on the Sale desk. Owner sees the full Sale-scoped projection. "
            "Counts are the in-scope length. Empty is not invented work. The "
            "CRM, GGV, and BZG Ops strips are not copied here. Buyer data room "
            "stays uninvented. Controlled export is not sent."
        ),
    }
    body.update(_honesty_tail())
    return body


def _find_sale_item(
    object_id: str,
    *,
    state_path=None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _sale_candidates(
        state_path=state_path,
        operator_db=operator_db,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
    ):
        if str(row.get("object_id") or "") == oid:
            return row
    return None


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of Sale seat scope is 403. Reuses existing handoffs."""
    seat = require_connective_seat(verified_person_id)
    found = _find_sale_item(
        object_id,
        state_path=state_path,
        operator_db=operator_db,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
    )
    if found is None:
        raise ConnectiveError(
            f"Sale Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "Sale Needs-You item is outside this seat's scope.",
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
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Sale-loop rows keep the existing Sale operator actions. This route does
    not open a second mutate store, does not send a controlled export, and
    does not grant buyer access.
    """
    seat = require_connective_seat(verified_person_id)
    found = _find_sale_item(
        object_id,
        state_path=state_path,
        operator_db=operator_db,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
    )
    if found is None:
        raise ConnectiveError(
            f"Sale Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "Sale Needs-You item is outside this seat's scope.",
            code="forbidden",
            status=403,
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise ConnectiveError(
            "Sale-loop rows use the existing Sale operator actions. "
            "This route does not open a second mutate surface, does not grant "
            "buyer access, and does not send a controlled export.",
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
        operator_db=operator_db,
        ledger_path=ledger_path,
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
        "buyer_live": False,
        "buyer_dataroom_live": False,
        "controlled_export": False,
        "controlled_export_send": False,
        "money": None,
        "bzg_compose": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "Devi done, buyer-live, and controlled export stay uninvented."
        ),
    }


def _attach_needs_you_connective(
    payload: dict[str, Any],
    *,
    person_id: str | None,
    state_path=None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> None:
    """Prefer an in-scope Needs-You row over the generic Sale pack href."""
    pid = (person_id or "").strip()
    if not pid:
        return
    try:
        strip = needs_you_connective_strip(
            verified_person_id=pid,
            state_path=state_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            ledger_path=ledger_path,
        )
    except ConnectiveError:
        return
    pack_next = payload.get("primary_next")
    if not isinstance(pack_next, dict) or pack_next.get("code") == "needs_you_connective":
        pack_next = payload.get("next_action")
    if not isinstance(pack_next, dict) or pack_next.get("code") == "needs_you_connective":
        pack_next = _pack_href_next()
    payload["needs_you_connective"] = strip
    payload["pack_next_action"] = pack_next
    preferred = strip.get("next_action") if strip.get("count") else None
    if isinstance(preferred, dict):
        payload["next_action"] = preferred
        payload["primary_next"] = preferred
    else:
        payload["next_action"] = pack_next


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing PROVEN.",
        code="proven_refused",
        status=405,
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing READY.",
        code="ready_refused",
        status=405,
    )


def refuse_staff_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing staff_ready.",
        code="staff_ready_refused",
        status=405,
    )


def refuse_haikal_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing Haikal human done.",
        code="haikal_done_refused",
        status=405,
    )


def refuse_devi_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing Devi done. Devi retest stays parked.",
        code="devi_done_refused",
        status=405,
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses money movement.",
        code="money_refused",
        status=405,
    )


def refuse_buyer_live(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses inventing a live buyer data room or buyer grant.",
        code="buyer_live_refused",
        status=405,
    )


def refuse_controlled_export(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses a controlled export send.",
        code="controlled_export_refused",
        status=405,
    )


def refuse_bzg_compose(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "Sale desk refuses BZG compose.",
        code="bzg_compose_refused",
        status=405,
    )


def connective_refuse_code(path: str) -> str | None:
    refused = {
        "/api/sale/mgmt-cluster/haikal-done": "haikal_done",
        "/api/sale/mgmt-cluster/haikal_done": "haikal_done",
        "/api/sale/mgmt-cluster/devi-done": "devi_done",
        "/api/sale/mgmt-cluster/devi_done": "devi_done",
        "/api/sale/mgmt-cluster/buyer-live": "buyer_live",
        "/api/sale/mgmt-cluster/buyer_live": "buyer_live",
        "/api/sale/mgmt-cluster/controlled-export": "controlled_export",
        "/api/sale/mgmt-cluster/controlled_export": "controlled_export",
        "/api/sale/mgmt-cluster/bzg-compose": "bzg_compose",
        "/api/sale/mgmt-cluster/needs-you/staff-ready": "staff_ready",
        "/api/sale/mgmt-cluster/needs-you/haikal-done": "haikal_done",
        "/api/sale/mgmt-cluster/needs-you/devi-done": "devi_done",
        "/api/sale/mgmt-cluster/needs-you/buyer-live": "buyer_live",
        "/api/sale/mgmt-cluster/needs-you/controlled-export": "controlled_export",
        "/api/sale/mgmt-cluster/needs-you/proven": "proven",
        "/api/sale/mgmt-cluster/needs-you/ready": "ready",
        "/api/sale/mgmt-cluster/needs-you/money": "money",
        "/api/sale/mgmt-cluster/needs-you/bzg-compose": "bzg_compose",
    }
    return refused.get(path)


def _apply_connective_refuse(code: str) -> None:
    mapping = {
        "staff_ready": refuse_staff_ready,
        "haikal_done": refuse_haikal_done,
        "devi_done": refuse_devi_done,
        "buyer_live": refuse_buyer_live,
        "controlled_export": refuse_controlled_export,
        "proven": refuse_proven,
        "ready": refuse_ready,
        "money": refuse_money,
        "bzg_compose": refuse_bzg_compose,
    }
    fn = mapping.get(code)
    if fn is None:
        raise ConnectiveError(f"refused: {code}", code="refused", status=405)
    fn()
