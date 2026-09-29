#!/usr/bin/env python3
"""OWNER-NEEDS-YOU-1 — Owner Needs You connective prove (no fake urgency).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack OWNER-NEEDS-YOU-1
(armed 2026-09-30 after FIN-AP-AR-SHELL-1 PASS_VERIFIED).

Owner-facing rollup of existing Needs-You connective boards across arms with
honesty stamps. Counts come only from live connective strips — empty stays
empty; UNKNOWN stays UNKNOWN; no invented urgency. Preserves MYWORK-PROVE-1
and DASH-LIVE-1. staff_ready=false · human_commissioned=false.
Does not auto-chain ESB-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "OWNER-NEEDS-YOU-1"
SCHEMA_ID = "wolf.owner-needs-you-1.v1"
BOUND = "beta-owner-needs-you-safe"
CAP_QUEUE = "CAP-CORE needs-you"
CAP_CORE_12 = "CAP-CORE-12"
OWNER_PERSON = "PERS-MATT"
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/owner/needs-you-1",
        "/owner/needs-you-1/",
        "/owner-needs-you-1",
        "/owner-needs-you-1/",
        "/owner-needs-you-1.html",
        "/dashboards/owner-needs-you-1.html",
    }
)
API_PATH = "/api/owner/needs-you-1"

PRESERVED_PACKS = ("MYWORK-PROVE-1", "DASH-LIVE-1")

# Arm connective specs: id, label, import path, strip callable name,
# API href (existing), desk href, call style ("owner_kw" | "no_person").
_ARM_SPECS: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    (
        "progress",
        "Owner Progress",
        "core.owner_progress_needs_you_depth",
        "needs_you_strip",
        "/api/progress/needs-you/operator-depth",
        "/progress",
        "no_person",
    ),
    (
        "core",
        "CORE Ops",
        "core.core_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/core/mgmt-cluster/needs-you",
        "/core-mgmt-cluster",
        "owner_kw",
    ),
    (
        "crm",
        "CRM / Leads",
        "core.crm_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/leads/needs-you",
        "/habitat-operator",
        "owner_kw",
    ),
    (
        "sale",
        "Sale Ops",
        "core.sale_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/sale/mgmt-cluster/needs-you",
        "/sale-mgmt-cluster",
        "owner_kw",
    ),
    (
        "intg",
        "INTG Ops",
        "core.intg_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/intg/mgmt-cluster/needs-you",
        "/intg-mgmt-cluster",
        "owner_kw",
    ),
    (
        "msc",
        "MSC Ops",
        "core.msc_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/msc/mgmt-cluster/needs-you",
        "/msc-mgmt-cluster",
        "owner_kw",
    ),
    (
        "strat",
        "STRAT Ops",
        "core.strat_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/strat/mgmt-cluster/needs-you",
        "/strat-mgmt-cluster",
        "owner_kw",
    ),
    (
        "dr",
        "DR Ops",
        "core.dr_ops_needs_you_connective",
        "needs_you_connective_strip",
        "/api/dr/mgmt-cluster/needs-you",
        "/dr-mgmt-cluster",
        "owner_kw",
    ),
    (
        "amg",
        "AMG Ops",
        "core.amg_ops_pack",
        "needs_you_connective_strip",
        "/api/amg/ops-pack/needs-you",
        "/amg-ops-pack",
        "owner_kw",
    ),
    (
        "ggv",
        "GGV Ops",
        "core.ggv_ops_pack",
        "needs_you_connective_strip",
        "/api/ggv/ops-pack/needs-you",
        "/ggv-ops-pack",
        "owner_kw",
    ),
    (
        "bzg",
        "BZG / Uma Blu",
        "core.uma_ops_console",
        "needs_you_connective_strip",
        "/api/bzg/uma-blu/needs-you",
        "/bzg/uma-blu",
        "owner_kw",
    ),
    (
        "intel",
        "INTEL Ops",
        "core.intel_ops_pack",
        "needs_you_connective_strip",
        "/api/intel/ops-pack/needs-you",
        "/intel-ops-pack",
        "owner_kw",
    ),
)


class OwnerNeedsYou1Error(ValueError):
    """Fail closed. Does not invent urgency counts or Needs-You items."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == API_PATH


def _load_strip(mod_path: str, fn_name: str) -> Callable[..., dict[str, Any]]:
    mod = importlib.import_module(mod_path)
    fn = getattr(mod, fn_name)
    if not callable(fn):
        raise OwnerNeedsYou1Error(
            f"Strip {mod_path}.{fn_name} is not callable.",
            code="strip_unavailable",
        )
    return fn


def _call_strip(fn: Callable[..., dict[str, Any]], style: str) -> dict[str, Any]:
    if style == "no_person":
        return fn()
    return fn(verified_person_id=OWNER_PERSON)


def _project_arm(
    arm_id: str,
    label: str,
    mod_path: str,
    fn_name: str,
    api_href: str,
    desk_href: str,
    style: str,
) -> dict[str, Any]:
    """Project one arm's connective strip into an honesty stamp board."""
    base: dict[str, Any] = {
        "id": arm_id,
        "label": label,
        "kind": "needs_you_arm_board",
        "api_href": api_href,
        "desk_href": desk_href,
        "module": mod_path,
        "invented": False,
        "invented_urgency": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
    }
    try:
        strip = _call_strip(_load_strip(mod_path, fn_name), style)
    except Exception as exc:  # noqa: BLE001
        base.update(
            {
                "ok": False,
                "status": "UNKNOWN",
                "display": "UNKNOWN",
                "empty": None,
                "count": None,
                "count_matches_items": False,
                "bound": None,
                "why": (
                    f"{label} Needs-You connective read failed "
                    f"({type(exc).__name__}). Status UNKNOWN — not invented empty."
                ),
            }
        )
        return base

    if not isinstance(strip, dict) or strip.get("ok") is not True:
        base.update(
            {
                "ok": False,
                "status": "UNKNOWN",
                "display": "UNKNOWN",
                "empty": None,
                "count": None,
                "count_matches_items": False,
                "bound": (strip or {}).get("bound") if isinstance(strip, dict) else None,
                "why": (
                    f"{label} strip did not return ok=true. "
                    "UNKNOWN honesty — count not invented."
                ),
            }
        )
        return base

    items = strip.get("items")
    if not isinstance(items, list):
        items = []
    try:
        count = int(strip.get("count") if strip.get("count") is not None else len(items))
    except (TypeError, ValueError):
        count = len(items)
    empty_flag = strip.get("empty")
    if empty_flag is None:
        empty_flag = count == 0
    empty = bool(empty_flag)
    # Honesty: count matches projected items, or strip paginates (count >= len, cap 20).
    if "items" not in strip:
        count_matches = True
    elif count == len(items):
        count_matches = True
    elif count > len(items) and len(items) <= 20:
        count_matches = True  # progress-style item cap
    else:
        count_matches = empty and count == 0 and len(items) == 0

    invented = bool(
        strip.get("invented")
        or strip.get("invented_count")
        or strip.get("invented_urgency")
    )
    status = "EMPTY" if empty and count == 0 else "CONNECTIVE"
    if invented:
        # Never surface invented urgency as connective — fail closed to UNKNOWN.
        status = "UNKNOWN"
        count = None
        empty = None

    base.update(
        {
            "ok": True,
            "status": status,
            "display": status,
            "empty": empty if status != "UNKNOWN" else None,
            "count": count if status != "UNKNOWN" else None,
            "count_matches_items": bool(count_matches) and status != "UNKNOWN",
            "bound": strip.get("bound"),
            "by_kind": strip.get("by_kind"),
            "schema": strip.get("schema") or strip.get("schema_id"),
            "why": (
                f"{label}: EMPTY honesty — no Needs-You rows in seat scope."
                if status == "EMPTY"
                else (
                    f"{label}: connective count={count} from live strip "
                    f"(invented=false). Not padded."
                    if status == "CONNECTIVE"
                    else f"{label}: UNKNOWN — invented strip refused."
                )
            ),
        }
    )
    return base


def arm_boards() -> list[dict[str, Any]]:
    return [_project_arm(*spec) for spec in _ARM_SPECS]


def mywork_prove1_preserved() -> dict[str, Any]:
    html = BETA_ROOT / "dashboards" / "my-work.html"
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "MYWORK-PROVE-1-RESULT.md"
    suite = BETA_ROOT / "scripts" / "tests" / "test_mywork_prove1_20260930.py"
    ok = html.is_file() and result.is_file() and suite.is_file()
    if ok:
        text = html.read_text(encoding="utf-8")
        ok = "staff_ready" in text and "human_commissioned" in text
    return {
        "ok": ok,
        "pack": "MYWORK-PROVE-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "why": (
            "My Work prove surfaces present; commissioning honesty banners intact."
            if ok
            else "MYWORK-PROVE-1 surface missing or honesty banner stripped."
        ),
    }


def dash_live1_preserved() -> dict[str, Any]:
    try:
        from core import dash_live1 as dl

        flags = dl.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("invented_kpi") is False
            and flags.get("stale_shown_as_current") is False
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "DASH-LIVE-1",
            "status": "CHECK_FAILED",
            "why": f"DASH-LIVE-1 honesty read failed ({type(exc).__name__}).",
        }
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "DASH-LIVE-1-RESULT.md"
    ok = ok and result.is_file()
    return {
        "ok": ok,
        "pack": "DASH-LIVE-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "why": (
            "Owner/War-Room freshness honesty intact; invented KPI false."
            if ok
            else "DASH-LIVE-1 RESULT missing or honesty pins drifted."
        ),
    }


def _honesty_tiles(boards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    empty_n = sum(1 for b in boards if b.get("status") == "EMPTY")
    conn_n = sum(1 for b in boards if b.get("status") == "CONNECTIVE")
    unk_n = sum(1 for b in boards if b.get("status") == "UNKNOWN")
    mywork = mywork_prove1_preserved()
    dash = dash_live1_preserved()
    return [
        {
            "id": "arm_boards",
            "label": "Arm Needs-You boards",
            "status": "HONEST",
            "value": len(boards),
            "why": (
                f"{len(boards)} arms projected. EMPTY={empty_n} · "
                f"CONNECTIVE={conn_n} · UNKNOWN={unk_n}. Counts from live strips only."
            ),
        },
        {
            "id": "fake_urgency",
            "label": "Fake urgency",
            "status": "REFUSED",
            "value": 0,
            "why": "No invented Needs-You items or padded urgency counts.",
        },
        {
            "id": "empty_honest",
            "label": "Empty stays empty",
            "status": "HONEST",
            "value": empty_n,
            "why": "EMPTY arms keep count=0. Not rewritten as urgency.",
        },
        {
            "id": "unknown_honest",
            "label": "UNKNOWN stays UNKNOWN",
            "status": "HONEST" if unk_n == 0 else "PRESENT",
            "value": unk_n,
            "why": "Failed strips stay UNKNOWN — never coerced to empty or invent.",
        },
        {
            "id": "mywork_prove1",
            "label": "MYWORK-PROVE-1",
            "status": mywork.get("status"),
            "value": None,
            "why": mywork.get("why"),
        },
        {
            "id": "dash_live1",
            "label": "DASH-LIVE-1",
            "status": dash.get("status"),
            "value": None,
            "why": dash.get("why"),
        },
        {
            "id": "cap_core_needs_you",
            "label": CAP_QUEUE,
            "status": "BUILT",
            "value": None,
            "why": (
                "Connective prove across arms. Ceiling BUILT. "
                "Not PROVEN/READY. CAP-CORE-12 stays eng prove only."
            ),
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "progress",
            "label": "Owner Progress Needs-You",
            "href": "/progress",
            "kind": "existing",
            "note": "Operator depth + morning seed. Empty stays empty.",
        },
        {
            "id": "staff_ops",
            "label": "Staff Ops Routing (Needs You nav)",
            "href": "/staff-ops-routing",
            "kind": "existing",
            "note": "Shell Needs You href. Not a second invent surface.",
        },
        {
            "id": "my_work",
            "label": "Universal My Work",
            "href": "/my-work",
            "kind": "existing",
            "note": "MYWORK-PROVE-1 preserved. Eng prove only.",
        },
        {
            "id": "owner_command",
            "label": "Owner Command",
            "href": "/wolf",
            "kind": "existing",
            "note": "DASH-LIVE-1 freshness stamps preserved.",
        },
        {
            "id": "war_room",
            "label": "Finish War Room",
            "href": "/finish-war-room",
            "kind": "existing",
            "note": "DASH-LIVE-1 war-room freshness preserved.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    mywork = mywork_prove1_preserved()
    dash = dash_live1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_queue_label": CAP_QUEUE,
        "cap_core_12": CAP_CORE_12,
        "staff_ready": False,
        "human_commissioned": False,
        "invented_urgency": False,
        "invented_count": False,
        "invented_needs_you": False,
        "fake_urgency": False,
        "padded_empty": False,
        "unknown_coerced_to_empty": False,
        "invented_proven": False,
        "invented_ready": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "unknown_honest": True,
        "connective_not_invented": True,
        "mywork_prove1_preserved": mywork.get("ok") is True,
        "dash_live1_preserved": dash.get("ok") is True,
        "second_needs_you_system": False,
        "extends_existing_connective": True,
        "cap_core_needs_you_proven": False,
        "cap_core_needs_you_ready": False,
        "cap_core_needs_you_maturity": "BUILT",
        "cap_core_needs_you_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "ESB-TRUTH-1",
    }


def refuse_urgency(_body: dict | None = None) -> None:
    raise OwnerNeedsYou1Error(
        "Fake urgency counts are refused. Empty stays empty; counts come from live strips only.",
        code="urgency_refused",
    )


def refuse_invent_item(_body: dict | None = None) -> None:
    raise OwnerNeedsYou1Error(
        "Invented Needs-You items are refused. Connective prove does not mint work.",
        code="invent_refused",
    )


def refuse_staff_ready(_body: dict | None = None) -> None:
    raise OwnerNeedsYou1Error(
        "staff_ready stays false. Not flipped by this pack.",
        code="staff_ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise OwnerNeedsYou1Error(
        "PROVEN is refused. CAP-CORE needs-you stays connective prove only (ceiling BUILT).",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise OwnerNeedsYou1Error(
        "READY is refused. An Owner Needs-You prove board is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise OwnerNeedsYou1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "urgency",
            "fake-urgency",
            "urgency-count",
            "padded-count",
            "invent-count",
            "force-count",
            "count",
            "counts",
        }:
            refuse_urgency(payload)
        if token in {
            "invent",
            "invent-item",
            "invent-needs-you",
            "fake-item",
            "mint-item",
            "needs-you-item",
            "item",
            "items",
        }:
            refuse_invent_item(payload)
        if token in {"staff-ready", "staff_ready", "commission", "human-commissioned"}:
            refuse_staff_ready(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise OwnerNeedsYou1Error(
        "External writes are refused. Owner Needs-You-1 is a read-only connective prove.",
        code="write_refused",
    )


def no_invented_urgency(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    if pack.get("invented_urgency") is not False:
        return False
    if pack.get("invented_count") is not False:
        return False
    if pack.get("fake_urgency") is not False:
        return False
    boards = pack.get("arm_boards") or []
    for board in boards:
        if board.get("invented") or board.get("invented_urgency") or board.get("invented_count"):
            return False
        if board.get("status") == "EMPTY" and board.get("count") not in (0, None):
            return False
        if board.get("status") == "UNKNOWN" and board.get("count") is not None:
            return False
    return True


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    boards = arm_boards()
    mywork = mywork_prove1_preserved()
    dash = dash_live1_preserved()
    empty_n = sum(1 for b in boards if b.get("status") == "EMPTY")
    conn_n = sum(1 for b in boards if b.get("status") == "CONNECTIVE")
    unk_n = sum(1 for b in boards if b.get("status") == "UNKNOWN")
    # Total is sum of live connective counts only — never invent.
    total = 0
    for b in boards:
        if b.get("status") == "CONNECTIVE" and isinstance(b.get("count"), int):
            total += int(b["count"])
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_QUEUE, CAP_CORE_12],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "invented_urgency": False,
        "invented_count": False,
        "invented_needs_you": False,
        "fake_urgency": False,
        "padded_empty": False,
        "unknown_coerced_to_empty": False,
        "arm_count": len(boards),
        "empty_arm_count": empty_n,
        "connective_arm_count": conn_n,
        "unknown_arm_count": unk_n,
        "total_connective_count": total,
        "arm_boards": boards,
        "honesty_tiles": _honesty_tiles(boards),
        "desk_links": _desk_links(),
        "mywork_prove1": mywork,
        "dash_live1": dash,
        "mywork_prove1_preserved": mywork.get("ok") is True,
        "dash_live1_preserved": dash.get("ok") is True,
        "cap_core_needs_you_proven": False,
        "cap_core_needs_you_ready": False,
        "cap_core_needs_you_maturity": flags["cap_core_needs_you_maturity"],
        "cap_core_needs_you_ceiling": flags["cap_core_needs_you_ceiling"],
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "fake_urgency_counts",
            "invented_needs_you_items",
            "staff_ready",
            "human_commissioned",
            "CAP-CORE needs-you PROVEN",
            "CAP-CORE-12 READY",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "ESB-TRUTH-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "arms": [s[0] for s in _ARM_SPECS],
        "status_enum": ["EMPTY", "CONNECTIVE", "UNKNOWN", "HONEST", "PRESERVED", "REFUSED"],
        "urgency_property": False,
        "invent_property": False,
        "writes_accepted": False,
        "extends": [
            "scripts/core/owner_progress_needs_you_depth.py",
            "scripts/core/core_ops_needs_you_connective.py",
            "arm Needs-You connective strips",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_needs_you_system": False,
        "why": (
            "Owner Needs-You connective prove across arms. "
            "Honesty stamps only. No fake urgency."
        ),
    }
