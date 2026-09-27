"""STRAT Ops × Needs-You connective — STRAT / 12wy / radar projection.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json).

Owner sees derived STRAT / 12-Week Year / Owner Radar Needs-You /
Morning seed / strat-loop rows on the existing Strategy Management Cluster
desk. Does not copy the MSC, Sale, CRM, GGV, BZG, or INTG Ops Needs-You
strips. Does not invent staff_ready, PROVEN, READY, AU adoption done,
Haikal done, or Devi done. Does not compose BZG, mutate Cloudflare Access,
mint a secret, or move money.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import strat_mgmt_cluster as strat

BETA_ROOT = strat.BETA_ROOT
CATALOG_DB = strat.CATALOG_DB
LEDGER_JSON = strat.LEDGER_JSON

CONNECTIVE_SCHEMA_ID = "wolf.strat-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "strat_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-strat-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-strat-ops-needs-you-connective-20260923"
CONNECTIVE_BOUND = "beta-connective-safe"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "strat_loop",
)
CONNECTIVE_DEPTH_KINDS = frozenset({"morning_seed", "waiting_others", "needs_you"})
STRAT_TARGET_CRS: tuple[str, ...] = (
    strat.CR_01,
    strat.CR_02,
    strat.CR_AU_01,
    strat.CR_AU_02,
)
CAP_IDS: tuple[str, ...] = (
    strat.CAP_01,
    strat.CAP_02,
)
AU_IDS: tuple[str, ...] = (
    strat.AU_01,
    strat.AU_02,
)
EXPECTED_MATURITY = {
    strat.CAP_01: "BUILT",
    strat.CAP_02: "BUILT",
}
OWNER = "PERS-MATT"
_STRAT_SURFACES = frozenset(
    {
        "strat_ops",
        "strat_mgmt",
        "12wy",
        "radar",
        "twelve_week",
        "owner_radar",
        "mission_control",
        "strat_12wy",
        "strat_radar",
    }
)
_OTHER_BUSINESS = frozenset(
    {"GGV", "BZG", "AMG", "SALE", "INTEL", "CRM", "FIN", "HR", "INTG", "MSC"}
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
        "sale_ops",
        "sale_evidence",
        "sale_buyer",
        "sale_mgmt",
        "buyer_dataroom",
        "buyer_mode",
        "attack_audit",
        "sale_evidence_pack",
        "progress",
        "lead_spine",
        "crm",
        "habitat_operator",
        "crm_ops",
        "habitat_lead",
        "integration_health",
        "intg_ops",
        "intg_mgmt",
        "connector",
        "connector_contract",
        "connector_cap_tests",
        "gws",
        "gws_integrate",
        "tech_registry",
        "intg_secrets",
        "secrets",
        "msc_ops",
        "msc_mgmt",
        "msc_assets",
        "msc_posture",
        "msc_compliance",
        "msc_cyber",
        "msc_records",
        "asset_register",
        "posture_prove",
        "compliance_pack",
        "cyber_baseline",
        "records_defensibility",
    }
)
_OTHER_CAPS = (
    "CAP-GGV",
    "CAP-BZG",
    "CAP-AMG",
    "CAP-CORE",
    "CAP-SALE",
    "CAP-INTEL",
    "CAP-CRM",
    "CAP-INTG",
    "CAP-MSC",
    "AU-INTG",
    "AU-MSC",
)
_OTHER_LOOP_KINDS = frozenset(
    {
        "sale_loop",
        "lead_loop",
        "bzg_loop",
        "ggv_loop",
        "crm_loop",
        "amg_loop",
        "intg_loop",
        "msc_loop",
    }
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
    """Owner only. Haikal, Misa, Devi, and Amanda are not this STRAT seat.

    Commission is not inserted. AU adoption is not granted.
    """
    pid = (person_id or "").strip()
    if pid == OWNER:
        return {
            "person_id": pid,
            "seat": "owner",
            "sees_full_strat": True,
            "authorised": True,
            "invented_commission": False,
            "au_started": False,
            "au_adoption_done": False,
            "invented_au_adoption": False,
        }
    raise ConnectiveError(
        "STRAT Needs-You is for the Owner seat. "
        "Haikal, Misa, Devi, and Amanda are not this STRAT seat.",
        code="forbidden",
        status=403,
    )


def _is_strat_scoped(item: dict[str, Any]) -> bool:
    """STRAT / 12-Week Year / Owner Radar commissioning or strat-loop.

    Other business strips stay out. A named slot is not AU adoption done.
    """
    kind = str(item.get("kind") or "")
    if kind in _OTHER_LOOP_KINDS:
        return False
    if kind == "strat_loop":
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
            "/sale-evidence",
            "/sale-mgmt",
            "/sale/",
            "/buyer-dataroom",
            "/buyer-mode",
            "/integration-health",
            "/intg-mgmt",
            "/intg/",
            "/connector",
            "/gws-integrate",
            "/tech-registry",
            "/intg-secrets",
            "/msc-",
            "/msc/",
            "/progress",
            "/staff-ops",
        )
    ):
        return False
    if cap.startswith("CAP-STRAT") or cap.startswith("AU-STRAT"):
        return True
    if business == "STRAT" or domain in {"STRAT", "D-STRAT"}:
        return True
    if surface in _STRAT_SURFACES:
        return True
    if any(
        token in blob
        for token in (
            "/12wy",
            "/radar-prove",
            "/strat-mgmt",
            "/api/strat/",
        )
    ):
        return True
    oid = str(item.get("object_id") or "")
    if oid.startswith(("CMQ-STRAT", "AU-STRAT", "CMQ-12WY", "CMQ-RADAR")):
        return True
    return False


def _in_scope_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every STRAT-scoped row. Other seats do not, including Owner-only rows."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    return False


def _honesty_row() -> dict[str, Any]:
    return {
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "au_started": False,
        "au_adoption_done": False,
        "invented_au_adoption": False,
        "invented_mission_scores": False,
        "aus_not_started": True,
        "access_mutated": False,
        "secret_mint": False,
        "money": None,
        "bzg_compose": False,
    }


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_strat_loop": kind == "strat_loop",
        "au_started": False,
        "au_adoption_done": False,
        "invented_au_adoption": False,
        "access_mutated": False,
        "secret_mint": False,
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
                "strat_detail": f"/api/strat/mgmt-cluster/needs-you/items/{oid}",
                "strat_acknowledge": f"/api/strat/mgmt-cluster/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "strat_loop":
        block.update(
            {
                "detail": f"/api/strat/mgmt-cluster/modules/{oid}",
                "desk": item.get("href") or "/strat-mgmt-cluster",
                "read_only_here": True,
            }
        )
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/strat-mgmt-cluster"
    row = {
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
        "handoff": _handoff_block(item),
    }
    row.update(_honesty_row())
    return row


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/strat-mgmt-cluster"
    nxt = {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope STRAT Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "state": "READ",
        "source": "strat_ops_needs_you_connective",
        "preferred_over_pack": True,
    }
    nxt.update(_honesty_row())
    return nxt


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Strategy Management Cluster",
        "href": "/strat-mgmt-cluster",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "au_started": False,
        "au_adoption_done": False,
        "invented_au_adoption": False,
        "invented_mission_scores": False,
        "access_mutated": False,
        "secret_mint": False,
        "money": None,
        "bzg_compose": False,
    }


def _honesty_tail() -> dict[str, Any]:
    tail = _honesty_row()
    tail.update(
        {
            "invented_count": False,
            "invented_haikal_human": False,
            "invented_devi_done": False,
            "invented_staff_ready": False,
            "duplicate_mutate_surface": False,
            "false_resolve_cr": False,
            "msc_strip_duplicated": False,
            "sale_strip_duplicated": False,
            "crm_strip_duplicated": False,
            "ggv_strip_duplicated": False,
            "bzg_strip_duplicated": False,
            "intg_strip_duplicated": False,
        }
    )
    return tail


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
            "strat_loop": 3,
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
        if extra.get("open_href") and not merged.get("open_href"):
            merged["open_href"] = extra["open_href"]
        if not _is_strat_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "STRAT"
        out.append(merged)
    return out


def _strat_loop_rows(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Recorded Strategy module attention only. Untouched frameworks stay off.

    A module card with recorded_count 0 is not invented work and not AU
    adoption done.
    """
    out: list[dict[str, Any]] = []
    for spec in strat.MODULE_SPECS:
        try:
            card = strat._module_card(
                spec,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                adoption_path=adoption_path,
            )
        except Exception:  # noqa: BLE001
            continue
        try:
            recorded = int(card.get("recorded_count") or 0)
        except (TypeError, ValueError):
            recorded = 0
        if recorded <= 0:
            continue
        href = spec.get("href") or "/strat-mgmt-cluster"
        out.append(
            {
                "object_id": spec["id"],
                "kind": "strat_loop",
                "title": spec.get("staff_title") or spec.get("title") or spec["id"],
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "priority": "P1",
                "status": "OPEN",
                "business": "STRAT",
                "domain": "D-STRAT",
                "surface": spec.get("kind") or "strat_ops",
                "capability": spec.get("cap"),
                "href": href,
                "open_href": href,
                "reasons": ["recorded_attention"],
                "recorded_count": recorded,
                "au_started": False,
                "au_adoption_done": False,
                "invented_au_adoption": False,
                "invented_mission_scores": False,
                "access_mutated": False,
                "secret_mint": False,
            }
        )
    return out


def _strat_candidates(
    *,
    state_path=None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(
        _strat_loop_rows(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            adoption_path=adoption_path,
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
    strat_crs = {cr: _cr_state(catalog_db, cr) for cr in STRAT_TARGET_CRS}
    aus = {}
    for au in AU_IDS:
        row = strat._au_state(au)
        state = row.get("state")
        aus[au] = {
            "state": state,
            "started": False,
            "adopted": False,
            "not_started": str(state or "").upper() in {"NOT STARTED", "NOT_STARTED"},
        }
    body = {
        "caps": caps,
        "expected": {cap: EXPECTED_MATURITY[cap] for cap in CAP_IDS},
        "strat_crs": strat_crs,
        "progress_core_crs": progress,
        "aus": aus,
        "false_resolve_cr": False,
        "cap_strat_01": caps.get("CAP-STRAT-01"),
        "cap_strat_02": caps.get("CAP-STRAT-02"),
        "au_strat_01": (aus.get(strat.AU_01) or {}).get("state"),
        "au_strat_02": (aus.get(strat.AU_02) or {}).get("state"),
    }
    body.update(_honesty_tail())
    return body


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    """STRAT / 12wy / radar Needs-You projection.

    Owner sees the full STRAT-scoped set. EMPTY honesty when none.
    Counts are the in-scope length.
    """
    seat = require_connective_seat(verified_person_id)
    try:
        rows = _strat_candidates(
            state_path=state_path,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            adoption_path=adoption_path,
        )
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "STRAT Needs-You connective read failed "
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
            "sees_full_strat": seat.get("person_id") == OWNER,
            "invented_commission": False,
            "au_started": False,
            "au_adoption_done": False,
            "invented_au_adoption": False,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "pack_next_action": _pack_href_next(),
        "empty_message": (
            "No STRAT/12-Week Year/Owner Radar-scoped Needs-You / "
            "Morning seed / strat-loop rows in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "source": "strat_scoped_needs_you_morning_strat_loop",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=catalog_db),
        "reuse_needs_you_depth": True,
        "why": (
            "Derived STRAT / 12-Week Year / Owner Radar commissioning and "
            "recorded strat-loop rows on the Strategy desk. Owner sees the full "
            "STRAT-scoped projection. Counts are the in-scope length. Empty is "
            "not invented work. The MSC, Sale, CRM, GGV, BZG, and INTG Ops strips "
            "are not copied here. AU-STRAT stays NOT_STARTED. No Cloudflare "
            "Access mutate. No secret mint."
        ),
    }
    body.update(_honesty_tail())
    return body


def _find_strat_item(
    object_id: str,
    *,
    state_path=None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _strat_candidates(
        state_path=state_path,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
        adoption_path=adoption_path,
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
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of STRAT seat scope is 403. Reuses existing handoffs."""
    seat = require_connective_seat(verified_person_id)
    found = _find_strat_item(
        object_id,
        state_path=state_path,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
        adoption_path=adoption_path,
    )
    if found is None:
        raise ConnectiveError(
            f"STRAT Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "STRAT Needs-You item is outside this seat's scope.",
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
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Strat-loop rows stay on the existing Strategy module desks. This route
    does not open a second mutate store, does not mutate Access, and does
    not mint a secret.
    """
    seat = require_connective_seat(verified_person_id)
    found = _find_strat_item(
        object_id,
        state_path=state_path,
        ledger_path=ledger_path,
        catalog_db=catalog_db,
        adoption_path=adoption_path,
    )
    if found is None:
        raise ConnectiveError(
            f"STRAT Needs-You item '{object_id}' not found.",
            code="not_found",
            status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise ConnectiveError(
            "STRAT Needs-You item is outside this seat's scope.",
            code="forbidden",
            status=403,
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise ConnectiveError(
            "Strat-loop rows use the existing Strategy module desks. "
            "This route does not open a second mutate surface, does not invent "
            "AU adoption, and does not mint a secret.",
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
        ledger_path=ledger_path,
        adoption_path=adoption_path,
    )
    body = {
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
        "commissioned": False,
        "cr_resolved": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, AU adoption, "
            "Haikal done, and Devi done stay uninvented."
        ),
    }
    body.update(_honesty_tail())
    return body


def _attach_needs_you_connective(
    payload: dict[str, Any],
    *,
    person_id: str | None,
    state_path=None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    adoption_path: Path | str | None = None,
) -> None:
    """Prefer an in-scope Needs-You row over the generic Strategy pack href."""
    pid = (person_id or "").strip()
    if not pid:
        return
    try:
        strip = needs_you_connective_strip(
            verified_person_id=pid,
            state_path=state_path,
            catalog_db=catalog_db,
            ledger_path=ledger_path,
            adoption_path=adoption_path,
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
        "STRAT desk refuses inventing PROVEN.",
        code="proven_refused",
        status=405,
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses inventing READY.",
        code="ready_refused",
        status=405,
    )


def refuse_staff_ready(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses inventing staff_ready.",
        code="staff_ready_refused",
        status=405,
    )


def refuse_haikal_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses inventing Haikal human done.",
        code="haikal_done_refused",
        status=405,
    )


def refuse_devi_done(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses inventing Devi done. Devi retest stays parked.",
        code="devi_done_refused",
        status=405,
    )


def refuse_au_adoption(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses inventing AU adoption done. AU-STRAT-01/02 stay NOT_STARTED.",
        code="au_adoption_refused",
        status=405,
    )


def refuse_money(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses money movement.",
        code="money_refused",
        status=405,
    )


def refuse_access_include(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses Cloudflare Access Include mutate.",
        code="access_include_refused",
        status=405,
    )


def refuse_secret_mint(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses secret mint.",
        code="secret_mint_refused",
        status=405,
    )


def refuse_bzg_compose(_body: dict[str, Any] | None = None) -> None:
    raise ConnectiveError(
        "STRAT desk refuses BZG compose.",
        code="bzg_compose_refused",
        status=405,
    )


def connective_refuse_code(path: str) -> str | None:
    refused = {
        "/api/strat/mgmt-cluster/haikal-done": "haikal_done",
        "/api/strat/mgmt-cluster/haikal_done": "haikal_done",
        "/api/strat/mgmt-cluster/devi-done": "devi_done",
        "/api/strat/mgmt-cluster/devi_done": "devi_done",
        "/api/strat/mgmt-cluster/au-adoption": "au_adoption",
        "/api/strat/mgmt-cluster/au_adoption": "au_adoption",
        "/api/strat/mgmt-cluster/secret-mint": "secret_mint",
        "/api/strat/mgmt-cluster/bzg-compose": "bzg_compose",
        "/api/strat/mgmt-cluster/access-include": "access_include",
        "/api/strat/mgmt-cluster/needs-you/staff-ready": "staff_ready",
        "/api/strat/mgmt-cluster/needs-you/haikal-done": "haikal_done",
        "/api/strat/mgmt-cluster/needs-you/devi-done": "devi_done",
        "/api/strat/mgmt-cluster/needs-you/au-adoption": "au_adoption",
        "/api/strat/mgmt-cluster/needs-you/secret-mint": "secret_mint",
        "/api/strat/mgmt-cluster/needs-you/access-include": "access_include",
        "/api/strat/mgmt-cluster/needs-you/proven": "proven",
        "/api/strat/mgmt-cluster/needs-you/ready": "ready",
        "/api/strat/mgmt-cluster/needs-you/money": "money",
        "/api/strat/mgmt-cluster/needs-you/bzg-compose": "bzg_compose",
    }
    return refused.get(path)


def _apply_connective_refuse(code: str) -> None:
    mapping = {
        "staff_ready": refuse_staff_ready,
        "haikal_done": refuse_haikal_done,
        "devi_done": refuse_devi_done,
        "au_adoption": refuse_au_adoption,
        "access_include": refuse_access_include,
        "secret_mint": refuse_secret_mint,
        "proven": refuse_proven,
        "ready": refuse_ready,
        "money": refuse_money,
        "bzg_compose": refuse_bzg_compose,
    }
    fn = mapping.get(code)
    if fn is None:
        raise ConnectiveError(f"refused: {code}", code="refused", status=405)
    fn()
