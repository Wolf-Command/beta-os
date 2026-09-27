#!/usr/bin/env python3
"""Staff Ops Routing — seat → live pack Today + derived next_action.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + armed plan
docs/deliveries/GROK-PLAN-SPRINT-2-TRACK-G-STAFF-OPS-ROUTING-2026-09-22.md
+ Staff Ops × Needs-You connective
docs/deliveries/GROK-PLAN-STAFF-OPS-NEEDS-YOU-CONNECTIVE-2026-09-23.md.

Bound: beta-connective-safe
Connective bound: beta-staff-ready-safe

Routes each authorised seat to their home pack with an honest next_action
derived from that pack's live read. Needs-You / Waiting-Others / Morning
Commissioning seed rows from Owner Progress Needs-You depth project per seat
and, when present, become the preferred next_action. Owner disappearance strip
labels entity handoffs ELIMINATE / AUTOMATE / AUGMENT without inventing staff
seats, hotel-ops people, money, PROVEN, READY, or staff_ready. No second
scoring table. No duplicate Needs-You mutate surface.
"""
from __future__ import annotations

import re
from typing import Any

from core import amg_ops_pack as amg
from core import founder_dep_routing as fdr
from core import ggv_ops_pack as ggv
from core import staff_ready_ux as sru

BOUND = "beta-connective-safe"
CONNECTIVE_BOUND = "beta-staff-ready-safe"
SCHEMA_ID = "wolf.staff-ops-routing.v1"
SLICE = "staff_ops_routing_v1"
CONNECTIVE_SLICE = "staff_ops_needs_you_connective"
CONNECTIVE_SCHEMA_ID = "wolf.staff-ops-needs-you-connective.v1"
CONNECTIVE_RUN_ID = "BF-staff-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-staff-ops-needs-you-connective-20260923"
CONNECTIVE_KINDS: tuple[str, ...] = ("needs_you", "waiting_others", "morning_seed")

OWNER = "PERS-MATT"
AMANDA = "PERS-AMANDA"
HAIKAL = "PERS-HAIKAL"
MISA = "PERS-MISA"
DEVI = "PERS-DEVI"

PACK_HREFS = {
    "bzg": {"href": "/bzg/uma-blu", "api": "/api/bzg/uma-blu/today", "label": "Uma Today"},
    "ggv": {"href": "/ggv-ops-pack", "api": "/api/ggv/ops-pack", "label": "GGV ops"},
    "amg": {"href": "/amg-ops-pack", "api": "/api/amg/ops-pack", "label": "Atrium desk"},
    "empire": {
        "href": "/owner-empire-pack",
        "api": "/api/owner/empire-pack",
        "label": "Owner Empire",
    },
    "intel": {
        "href": "/intel-ops-pack",
        "api": "/api/intel/ops-pack",
        "label": "Intel Ops",
    },
}

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "additive_only": True,
    "proven": False,
    "ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_hotel_ops_person": False,
    "invented_system_pct": False,
    "second_scoring_table": False,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "folio_write": False,
    "zayen_write": False,
    "cloudflare_mutated": False,
    "production_mutate": False,
    "cr_resolved": False,
    "caps_raised": False,
    "wip_quartet_touched": False,
    "staff_ready": False,
    "invented_staff_ready": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "invented_haikal_human": False,
    "invented_devi_done": False,
    "false_resolve_cr": False,
    "duplicate_mutate_surface": False,
    "staff_ops_needs_you_connective": True,
    "connective_bound": CONNECTIVE_BOUND,
    "connective_claim_id": CONNECTIVE_CLAIM_ID,
    "connective_run_id": CONNECTIVE_RUN_ID,
}


class StaffOpsRoutingError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def schema_document() -> dict[str, Any]:
    return {
        "id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "seats": [
            "owner",
            "ggv_close",
            "ggv_read",
            "bzg_uma",
            "hotel_ops",
            "waiting_assignment",
        ],
        "packs": list(PACK_HREFS.keys()),
        "writes": False,
        "money": False,
        "second_scoring_table": False,
        "connective_schema": CONNECTIVE_SCHEMA_ID,
        "connective_kinds": list(CONNECTIVE_KINDS),
        "why": (
            "Seat → home pack → derived next_action from live pack read. "
            "Needs-You / Waiting-Others / Morning seed project per seat and "
            "prefer next_action when in scope. EMPTY / UNWIRED / "
            "WAITING_ASSIGNMENT stay honest. No invent counts."
        ),
    }


def refuse_proven(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing has no money, payment, bank, or folio action.",
        code="money_refused",
    )


def refuse_production(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses Production mutate.",
        code="production_refused",
    )


def refuse_resolve(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses resolving completion-register items.",
        code="resolve_refused",
    )


def refuse_external_write(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing is read-only routing. External writes refused.",
        code="writes_refused",
    )


def refuse_staff_ready(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses inventing staff_ready.",
        code="staff_ready_refused",
    )


def refuse_haikal_done(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses inventing Haikal human done.",
        code="haikal_done_refused",
    )


def refuse_devi_done(_payload: dict[str, Any] | None = None) -> None:
    raise StaffOpsRoutingError(
        "Staff Ops Routing refuses inventing Devi done.",
        code="devi_done_refused",
    )


def refuse_code(path: str) -> str | None:
    refused = {
        "/api/staff/ops-routing/proven": "proven",
        "/api/staff/ops-routing/ready": "ready",
        "/api/staff/ops-routing/staff-ready": "staff_ready",
        "/api/staff/ops-routing/staff_ready": "staff_ready",
        "/api/staff/ops-routing/haikal-done": "haikal_done",
        "/api/staff/ops-routing/haikal_done": "haikal_done",
        "/api/staff/ops-routing/devi-done": "devi_done",
        "/api/staff/ops-routing/devi_done": "devi_done",
        "/api/staff/ops-routing/payment": "money",
        "/api/staff/ops-routing/money": "money",
        "/api/staff/ops-routing/bank": "money",
        "/api/staff/ops-routing/folio": "money",
        "/api/staff/ops-routing/zayen": "money",
        "/api/staff/ops-routing/resolve": "resolve",
        "/api/staff/ops-routing/production": "production",
        "/api/staff/ops-routing/cloudflare": "production",
    }
    return refused.get(path)


_NAME_RE = re.compile(r"[a-z]+")
_SEAT_NAME_TOKENS: dict[str, frozenset[str]] = {
    OWNER: frozenset({"matt"}),
    AMANDA: frozenset({"amanda"}),
    HAIKAL: frozenset({"haikal"}),
    MISA: frozenset({"misa"}),
    DEVI: frozenset({"devi"}),
}
_HOTEL_OPS_TOKENS = frozenset({"coral", "authorised", "authorized"})


def _name_tokens(*parts: Any) -> set[str]:
    blob = " ".join(str(p or "") for p in parts).lower()
    return set(_NAME_RE.findall(blob))


def _needs_you_module():
    from core import owner_progress_needs_you_depth as nye

    return nye


def _connective_candidates(*, state_path=None) -> list[dict[str, Any]]:
    nye = _needs_you_module()
    rows = nye.collect_candidates(state_path=state_path, include_parked=False)
    return [row for row in rows if row.get("kind") in CONNECTIVE_KINDS]


def _item_in_scope(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees the full connective projection. Staff see named in-scope rows only."""
    if seat.get("seat") == "owner" or seat.get("can_read_all"):
        return True
    tokens = _name_tokens(item.get("who"), item.get("audience"))
    allowed = set(_SEAT_NAME_TOKENS.get(seat.get("person_id") or "", frozenset()))
    if seat.get("seat") == "hotel_ops":
        allowed |= set(_HOTEL_OPS_TOKENS)
    if not allowed:
        return False
    return bool(tokens & allowed)


def _scoped_connective_items(
    seat: dict[str, Any], *, state_path=None
) -> list[dict[str, Any]]:
    items = [row for row in _connective_candidates(state_path=state_path) if _item_in_scope(row, seat)]

    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        kind_rank = {"morning_seed": 0, "waiting_others": 1, "needs_you": 2}.get(
            str(it.get("kind") or ""), 9
        )
        pri = {"P0": 0, "P1": 1, "P2": 2}.get(str(it.get("priority") or ""), 5)
        return (kind_rank, pri, str(it.get("object_id") or ""))

    items.sort(key=sort_key)
    return items


def _handoff_block(object_id: str) -> dict[str, Any]:
    oid = object_id
    return {
        "detail": f"/api/progress/needs-you/items/{oid}",
        "acknowledge": f"/api/progress/needs-you/items/{oid}/acknowledge",
        "staff_detail": f"/api/staff/ops-routing/needs-you/items/{oid}",
        "staff_acknowledge": f"/api/staff/ops-routing/needs-you/items/{oid}/acknowledge",
        "reuse_needs_you_depth": True,
        "duplicate_mutate_surface": False,
    }


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    href = item.get("open_href") or item.get("href")
    return {
        "object_id": oid,
        "kind": item.get("kind"),
        "title": item.get("title"),
        "who": item.get("who"),
        "audience": item.get("audience"),
        "priority": item.get("priority"),
        "status": item.get("operator_status") or item.get("status"),
        "href": href,
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "handoff": _handoff_block(oid),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href")
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "owner_progress_needs_you_depth",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
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
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db=None,
) -> dict[str, Any]:
    """Per-seat projection of Needs-You / Waiting-Others / Morning seed.

    Owner sees the full projection. Other seats see only rows that name them.
    EMPTY honesty when none. Counts are len(in-scope rows), never invented.
    """
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    try:
        items = _scoped_connective_items(seat, state_path=state_path)
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "Needs-You connective read failed "
                f"({exc}). Count stays EMPTY. No work invented."
            )
        )
        empty["seat"] = {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
            "label": seat.get("label"),
        }
        return empty
    projected = [_project_row(it) for it in items]
    by_kind = {k: 0 for k in CONNECTIVE_KINDS}
    for it in items:
        kind = str(it.get("kind") or "")
        if kind in by_kind:
            by_kind[kind] += 1
    empty = len(items) == 0
    nye = _needs_you_module()
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
            "label": seat.get("label"),
            "sees_full": bool(seat.get("can_read_all")),
        },
        "empty": empty,
        "count": len(items),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(items[0]),
        "empty_message": (
            "No Needs-You / Waiting-Others / Morning seed items in this seat's scope — "
            "EMPTY honesty."
            if empty
            else None
        ),
        "invented": False,
        "invented_count": False,
        "source": "owner_progress_needs_you_depth",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": nye.cap_honesty(catalog_db=catalog_db),
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
        "why": (
            "Derived from Owner Progress Needs-You depth. Owner sees the full "
            "Needs-You / Waiting-Others / Morning seed projection. Staff seats "
            "see only rows that name them. Counts are the in-scope length."
        ),
    }


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    catalog_db=None,
) -> dict[str, Any]:
    """Thin detail. Out of scope is 403. Reuses Needs-You depth item identity."""
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    oid = (object_id or "").strip()
    nye = _needs_you_module()
    found = None
    for row in nye.collect_candidates(state_path=state_path, include_parked=True):
        if row.get("kind") not in CONNECTIVE_KINDS:
            continue
        if row.get("object_id") == oid:
            found = row
            break
    if found is None:
        raise StaffOpsRoutingError(
            f"Needs-You item '{oid}' not found.",
            code="not_found",
        )
    if not _item_in_scope(found, seat):
        raise StaffOpsRoutingError(
            "Needs-You item is outside this seat's scope.",
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
        "handoff": _handoff_block(oid),
        "reuse_needs_you_depth": True,
        "duplicate_mutate_surface": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "caps": nye.cap_honesty(catalog_db=catalog_db),
    }


def acknowledge_handoff(
    object_id: str,
    *,
    verified_person_id: str,
    note: str | None = None,
    state_path=None,
    events_path=None,
    catalog_db=None,
) -> dict[str, Any]:
    """Acknowledge via the Needs-You operator state. No second mutate surface.

    Wrong-scope seats are refused. Touch does not invent staff_ready, PROVEN,
    READY, Haikal done, Devi done, or a resolved CR.
    """
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    oid = (object_id or "").strip()
    nye = _needs_you_module()
    found = None
    for row in nye.collect_candidates(state_path=state_path, include_parked=True):
        if row.get("kind") not in CONNECTIVE_KINDS:
            continue
        if row.get("object_id") == oid:
            found = row
            break
    if found is None:
        raise StaffOpsRoutingError(
            f"Needs-You item '{oid}' not found.",
            code="not_found",
        )
    if not _item_in_scope(found, seat):
        raise StaffOpsRoutingError(
            "Needs-You item is outside this seat's scope.",
            code="forbidden",
        )
    recorded = nye.record_operator_action(
        oid,
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
    )
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "recorded": True,
        "action": "acknowledge",
        "object_id": oid,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        },
        "handoff": _handoff_block(oid),
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
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "and Devi done stay uninvented."
        ),
    }


def _empty_next(label: str, *, code: str = "empty", href: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "label": label,
        "href": href,
        "invented": False,
        "state": "EMPTY",
    }


def _waiting_assignment_next() -> dict[str, Any]:
    return {
        "code": "waiting_assignment",
        "label": "Waiting for hotel-ops assignment — no person invented",
        "href": None,
        "invented": False,
        "state": "WAITING_ASSIGNMENT",
    }


def resolve_seat(person_id: str | None, *, catalog_db=None) -> dict[str, Any]:
    """Map verified person → routing seat. Fail closed when unknown."""
    pid = (person_id or "").strip()
    if not pid:
        raise StaffOpsRoutingError(
            "Staff Ops Routing requires a verified person.",
            code="forbidden",
        )
    if pid == OWNER:
        return {
            "person_id": pid,
            "seat": "owner",
            "label": "Owner",
            "home_packs": ["bzg", "ggv", "amg"],
            "extra_links": ["empire", "intel"],
            "can_read_all": True,
            "can_mutate_foreign": False,
        }
    ggv_seat = ggv.seat_for(pid)
    if ggv_seat is not None:
        kind = "ggv_close" if ggv_seat.get("can_close") else "ggv_read"
        return {
            "person_id": pid,
            "seat": kind,
            "label": sru.human_person(pid),
            "home_packs": ["ggv"],
            "extra_links": [],
            "can_read_all": False,
            "can_mutate_foreign": False,
            "ggv_seat": ggv_seat,
        }
    if pid == DEVI:
        return {
            "person_id": pid,
            "seat": "bzg_uma",
            "label": "Devi",
            "home_packs": ["bzg"],
            "extra_links": [],
            "can_read_all": False,
            "can_mutate_foreign": False,
            "assignment": "bzg_uma_when_scoped",
        }
    hotel = amg.hotel_ops_ids(catalog_db)
    if pid in hotel:
        return {
            "person_id": pid,
            "seat": "hotel_ops",
            "label": sru.human_person(pid),
            "home_packs": ["amg"],
            "extra_links": [],
            "can_read_all": False,
            "can_mutate_foreign": False,
            "assigned": True,
        }
    # No invented hotel-ops person. Unknown seat stays forbidden.
    raise StaffOpsRoutingError(
        "Staff Ops Routing has no seat for this person. "
        "Hotel-ops stays WAITING_ASSIGNMENT until catalog assignment exists.",
        code="forbidden",
    )


def require_seat(person_id: str | None, *, catalog_db=None) -> dict[str, Any]:
    return resolve_seat(person_id, catalog_db=catalog_db)


def _attention_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _pack_card_shell(pack: str, *, state: str = "EMPTY") -> dict[str, Any]:
    meta = PACK_HREFS[pack]
    return {
        "pack": pack,
        "label": meta["label"],
        "href": meta["href"],
        "api": meta["api"],
        "state": state,
        "attention_count": None,
        "next_action": None,
        "loud": state in {"EMPTY", "UNWIRED", "WAITING_ASSIGNMENT"},
        "money": None,
        "occupancy": None,
        "adr": None,
        "revpar": None,
        "invented": False,
    }


def derive_bzg_card(person_id: str) -> dict[str, Any]:
    card = _pack_card_shell("bzg")
    try:
        from core import uma_ops_console as uma
    except Exception:  # noqa: BLE001
        card["why"] = "Uma Today module was not importable. Attention is EMPTY."
        card["next_action"] = _empty_next(
            "Open Uma Today when the module is available",
            code="unwired",
            href=card["href"],
        )
        card["state"] = "UNWIRED"
        return card
    try:
        today = uma.today_cards(person_id=person_id)
    except Exception as exc:  # noqa: BLE001
        card["why"] = f"Uma Today read failed ({exc}). Attention is EMPTY. No money shown."
        card["next_action"] = _empty_next(
            "Retry Uma Today — count stays EMPTY until a live read succeeds",
            code="empty",
            href=card["href"],
        )
        return card
    nxt = sru.primary_next_bzg(today)
    # Attention: open purchase requests if present on today strip; else EMPTY.
    count = None
    for key in ("attention_count", "open_count", "needs_you_count"):
        if isinstance(today.get(key), int):
            count = today[key]
            break
    now = today.get("now") or {}
    if count is None and isinstance(now.get("count"), int):
        count = now["count"]
    # Prefer Empire-compatible open-PR count via owner handoff helper when Owner.
    if count is None and person_id == OWNER:
        try:
            from core import owner_empire_pack as empire

            hand = empire._bzg_handoff()  # noqa: SLF001 — shared projection
            if isinstance(hand.get("attention_count"), int):
                count = hand["attention_count"]
        except Exception:  # noqa: BLE001
            pass
    card["state"] = "READ" if count is not None else "EMPTY"
    card["loud"] = count is None
    card["attention_count"] = count
    card["next_action"] = {
        "code": nxt.get("code") or "today",
        "label": nxt.get("label") or "Open Uma Today",
        "href": nxt.get("href") or card["href"],
        "invented": False,
        "state": "READ" if nxt.get("label") else "EMPTY",
    }
    card["why"] = (
        "Derived from Uma Today live read. EMPTY attention is not zero work invented. "
        "Bills, payment, and petty amounts stay off this card."
    )
    return card


def derive_ggv_card(person_id: str) -> dict[str, Any]:
    card = _pack_card_shell("ggv")
    seat = ggv.seat_for(person_id)
    if seat is None and person_id != OWNER:
        raise StaffOpsRoutingError(
            "GGV pack is foreign to this seat.",
            code="forbidden",
        )
    actor = person_id if seat is not None else OWNER
    try:
        board = ggv.build_board(verified_person_id=actor)
    except Exception as exc:  # noqa: BLE001
        card["why"] = f"GGV ops read failed ({exc}). Attention is EMPTY. No lead invented."
        card["next_action"] = _empty_next(
            "Retry GGV ops — empty is not an invented lead",
            code="empty",
            href=card["href"],
        )
        return card
    nxt = sru.primary_next_ggv(board)
    exceptions = board.get("exceptions") or {}
    count = _attention_int(exceptions.get("count"))
    card["state"] = "READ" if count is not None else "EMPTY"
    card["loud"] = count is None
    card["attention_count"] = count
    card["next_action"] = {
        "code": nxt.get("code") or "ggv",
        "label": nxt.get("label") or "Open GGV ops",
        "href": nxt.get("href") or card["href"],
        "invented": False,
        "state": "READ" if nxt.get("label") else "EMPTY",
    }
    card["why"] = (
        "Derived from GGV ops live board. Empty exceptions list is not an SLA breach. "
        "No lead or money invented."
    )
    return card


def derive_amg_card(person_id: str, *, catalog_db=None) -> dict[str, Any]:
    card = _pack_card_shell("amg")
    hotel = amg.hotel_ops_ids(catalog_db)
    seat = amg.seat_for(person_id, catalog_db)
    if seat is None and person_id != OWNER:
        # Not Owner and not assigned hotel-ops → waiting, not invented person.
        if not hotel:
            card["state"] = "WAITING_ASSIGNMENT"
            card["loud"] = True
            card["next_action"] = _waiting_assignment_next()
            card["why"] = (
                "No active Atrium hotel-ops assignment in the catalog. "
                "This desk does not invent Lyly, Clara, or any hotel-ops person."
            )
            return card
        raise StaffOpsRoutingError(
            "AMG pack is foreign to this seat.",
            code="forbidden",
        )
    actor = person_id if seat is not None else OWNER
    try:
        board = amg.build_board(verified_person_id=actor, catalog_db=catalog_db)
    except Exception as exc:  # noqa: BLE001
        card["why"] = (
            f"Atrium desk read failed ({exc}). Attention is EMPTY. "
            "This is not occupancy."
        )
        card["next_action"] = _empty_next(
            "Retry Atrium desk — empty is not hotel occupancy",
            code="empty",
            href=card["href"],
        )
        return card
    nxt = sru.primary_next_amg(board)
    slots = ((board.get("today") or {}).get("slots")) or []
    flagged = [s for s in slots if isinstance(s, dict) and s.get("attention")]
    card["state"] = "READ"
    card["loud"] = False
    card["attention_count"] = len(flagged)
    card["hotel_ops_assigned"] = bool(hotel)
    if not hotel:
        # Owner may still open the desk; staff seat honesty stays waiting.
        card["staff_seat_state"] = "WAITING_ASSIGNMENT"
        card["staff_seat_why"] = (
            "Owner can open Atrium. Hotel-ops staff seat stays WAITING_ASSIGNMENT — "
            "no person invented."
        )
    card["next_action"] = {
        "code": nxt.get("code") or "amg",
        "label": nxt.get("label") or "Open Atrium desk",
        "href": nxt.get("href") or card["href"],
        "invented": False,
        "state": "WAITING_ASSIGNMENT"
        if nxt.get("code") == "waiting_assignment"
        else "READ",
    }
    card["why"] = (
        "Derived from Atrium desk live read. Empty slots are not occupancy, ADR, or RevPAR. "
        "No folio or payment shown."
    )
    return card


def _link_card(pack: str) -> dict[str, Any]:
    meta = PACK_HREFS[pack]
    return {
        "pack": pack,
        "label": meta["label"],
        "href": meta["href"],
        "api": meta["api"],
        "kind": "link",
        "invented": False,
    }


def disappearance_strip(*, catalog_db=None) -> dict[str, Any]:
    """Owner disappearance labels for entity handoffs.

    Honesty: if no staff seat exists for a card, label stays AUGMENT — never
    fake ELIMINATE. Reusable by Empire Today as a thin strip.
    """
    hotel = amg.hotel_ops_ids(catalog_db)
    cards: list[dict[str, Any]] = []
    # BZG — Devi seat exists as named BZG Uma seat.
    bzg_labels = fdr.label_for_pack_handoff("BZG", None)
    cards.append(
        {
            "pack": "BZG",
            "label": "Uma ops",
            "href": PACK_HREFS["bzg"]["href"],
            "staff_seat": DEVI,
            "staff_seat_present": True,
            **bzg_labels,
            "why_routing": (
                "ELIMINATE when Uma attention can route to Devi — Owner is not the daily switchboard."
                if bzg_labels.get("founder_dep_class") == "ELIMINATE"
                else bzg_labels.get("founder_dep_reason")
            ),
        }
    )
    # GGV — Amanda seat exists.
    ggv_labels = fdr.label_for_pack_handoff("GGV", None)
    cards.append(
        {
            "pack": "GGV",
            "label": "GGV ops",
            "href": PACK_HREFS["ggv"]["href"],
            "staff_seat": AMANDA,
            "staff_seat_present": True,
            **ggv_labels,
            "why_routing": ggv_labels.get("founder_dep_reason"),
        }
    )
    # AMG — only ELIMINATE if hotel-ops assignment present; else AUGMENT.
    amg_labels = fdr.label_for_pack_handoff(
        "AMG",
        1 if hotel else None,
    )
    # Force honesty when no hotel-ops seat: never fake ELIMINATE.
    if not hotel and amg_labels.get("founder_dep_class") == "ELIMINATE":
        amg_labels = {
            "founder_dep_class": "AUGMENT",
            "founder_dep_reason": (
                "Would be ELIMINATE but no hotel-ops seat — honesty keeps AUGMENT."
            ),
            "safe_implement": True,
            "invented_owner_control_away": False,
        }
    elif not hotel:
        # label_for_pack_handoff already keeps AUGMENT when has_staff_seat=False
        pass
    cards.append(
        {
            "pack": "AMG",
            "label": "Atrium desk",
            "href": PACK_HREFS["amg"]["href"],
            "staff_seat": None if not hotel else hotel[0],
            "staff_seat_present": bool(hotel),
            "staff_seat_state": "ASSIGNED" if hotel else "WAITING_ASSIGNMENT",
            **amg_labels,
            "why_routing": (
                amg_labels.get("founder_dep_reason")
                if hotel
                else "No hotel-ops assignment — Owner stays AUGMENT; person not invented."
            ),
        }
    )
    return {
        "ok": True,
        "bound": BOUND,
        "title": "Owner disappearance",
        "cards": cards,
        "invented_hotel_ops_person": False,
        "invented_owner_control_away": False,
        "why": (
            "ELIMINATE = auto-routable to a staff seat. "
            "AUTOMATE = system can do without a human. "
            "AUGMENT = Owner still needed. Never fake ELIMINATE without a seat."
        ),
    }


def home_for_seat(seat: dict[str, Any]) -> dict[str, Any]:
    packs = list(seat.get("home_packs") or [])
    if not packs:
        return {
            "pack": None,
            "href": None,
            "state": "EMPTY",
            "why": "No home pack for this seat.",
        }
    primary = packs[0]
    meta = PACK_HREFS[primary]
    return {
        "pack": primary,
        "href": meta["href"],
        "api": meta["api"],
        "label": meta["label"],
        "all_home_packs": packs,
    }


def build_desk(
    *,
    verified_person_id: str,
    catalog_db=None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    pid = seat["person_id"]
    cards: list[dict[str, Any]] = []
    for pack in seat.get("home_packs") or []:
        if pack == "bzg":
            cards.append(derive_bzg_card(pid if pid == DEVI or pid == OWNER else OWNER))
        elif pack == "ggv":
            cards.append(derive_ggv_card(pid))
        elif pack == "amg":
            cards.append(derive_amg_card(pid, catalog_db=catalog_db))
    # Owner gets entity trio even when already listed; ensure all three.
    if seat["seat"] == "owner":
        by_pack = {c["pack"]: c for c in cards}
        for pack, builder in (
            ("bzg", lambda: derive_bzg_card(OWNER)),
            ("ggv", lambda: derive_ggv_card(OWNER)),
            ("amg", lambda: derive_amg_card(OWNER, catalog_db=catalog_db)),
        ):
            if pack not in by_pack:
                by_pack[pack] = builder()
        cards = [by_pack["bzg"], by_pack["ggv"], by_pack["amg"]]

    extras = [_link_card(p) for p in seat.get("extra_links") or []]
    home = home_for_seat(seat)
    connective = needs_you_connective_strip(
        verified_person_id=pid, catalog_db=catalog_db
    )
    # Pack next_action is the fallback. In-scope Needs-You rows prefer it.
    primary_next = None
    if cards:
        primary_next = cards[0].get("next_action")
    if primary_next is None:
        primary_next = _empty_next("No routed next action yet", code="empty")
    preferred = connective.get("next_action") if connective.get("count") else None
    if isinstance(preferred, dict) and preferred.get("label"):
        primary_next = preferred

    strip = None
    if seat["seat"] == "owner":
        strip = disappearance_strip(catalog_db=catalog_db)

    # Attention projection — dashboard derivative read model (no second scoring).
    attention = {
        "ok": True,
        "projection_of": "pack_live_reads",
        "second_scoring_table": False,
        "system_pct_invented": False,
        "cards": [
            {
                "pack": c.get("pack"),
                "attention_count": c.get("attention_count"),
                "state": c.get("state"),
                "next_action": c.get("next_action"),
                "href": c.get("href"),
            }
            for c in cards
        ],
        "why": (
            "Attention + next_action are projections of pack state. "
            "No second scoring table. SYSTEM% is not invented here."
        ),
    }

    return {
        "ok": True,
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "slice": SLICE,
        "seat": seat,
        "home": home,
        "cards": cards,
        "extra_links": extras,
        "next_action": primary_next,
        "needs_you_connective": connective,
        "disappearance": strip,
        "attention": attention,
        "honesty": honesty_flags(),
        "money": None,
        "payment_executed": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "why": (
            "Staff Ops Routing lands each seat on their live pack Today. "
            "When Needs-You depth has in-scope rows, next_action prefers them. "
            "EMPTY / WAITING_ASSIGNMENT stay honest."
        ),
    }


def attention_projection(
    *,
    verified_person_id: str,
    catalog_db=None,
) -> dict[str, Any]:
    desk = build_desk(verified_person_id=verified_person_id, catalog_db=catalog_db)
    return desk["attention"]
