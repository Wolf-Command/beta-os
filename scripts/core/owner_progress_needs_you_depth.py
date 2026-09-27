#!/usr/bin/env python3
"""Owner Progress Needs-You operator depth — usable morning loop (Beta).

Decision served: keep_building_without_matt (owner-autonomous-release-2026-09-19)
+ Owner Commissioning Queue P0 ENGINEERING_PASS + Progress projection P0.
Plan: docs/deliveries/GROK-PLAN-OWNER-PROGRESS-NEEDS-YOU-DEPTH-2026-09-23.md.

Authorised Owner seat sees Needs-You / Waiting-Others / Policy / Morning
Commissioning seed items, opens fixture-honest detail, and records
next-action-touch / acknowledge / park that refresh Needs-You strips.
EMPTY honesty when no rows. No invent staff_ready / PROVEN / READY.
No invent Haikal/Devi human completion. Do not false-resolve Progress/CORE CRs.
No money.

Bound: beta-owner-progress-safe (:8788 only).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import owner_commissioning_queue as ocq
from core import progress_read_model as prm

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OPERATOR_STATE = BETA_ROOT / "state" / "progress" / "needs-you-operator-state.json"
OPERATOR_EVENTS = BETA_ROOT / "state" / "progress" / "needs-you-operator-events.jsonl"
SEED_DOC = (
    BETA_ROOT
    / "docs"
    / "deliveries"
    / "WOLF-MORNING-COMMISSIONING-SEED-2026-09-22.md"
)

BOUND = "beta-owner-progress-safe"
SCHEMA_ID = "wolf.owner-progress-needs-you-depth.v1"
SLICE = "owner_progress_needs_you_depth"
RUN_ID = "BF-owner-progress-needs-you-depth-20260923"
CLAIM_ID = "bf-owner-progress-needs-you-depth-20260923"
DESK_HREF = "/progress"
DESK_ANCHOR = "/progress#needs-you-depth"

OWNER = "PERS-MATT"
OPERATOR_FIXTURES: tuple[str, ...] = (OWNER,)

CAP_IDS: tuple[str, ...] = ("CAP-CORE-11", "CAP-CORE-12")
TARGET_CRS: tuple[str, ...] = (
    "e38d9812128a4535b4a6f59f3a3a0319",  # Progress ACTIVE honesty
    "CR-c4ed4e3fa9f15a40",  # CAP-CORE-11
    "CR-6e3fd7b9d7edca0e",  # CAP-CORE-12
    "CR-7a022a9394592c75",  # CAP-CORE-12 dup
)

KIND_FILTERS: tuple[str, ...] = (
    "needs_you",
    "waiting_others",
    "policy",
    "morning_seed",
)
KIND_ALIASES: dict[str, str] = {
    "needs_you": "needs_you",
    "needs-you": "needs_you",
    "needsyou": "needs_you",
    "matt": "needs_you",
    "waiting_others": "waiting_others",
    "waiting-others": "waiting_others",
    "waiting_on_others": "waiting_others",
    "waiting": "waiting_others",
    "policy": "policy",
    "needs_policy": "policy",
    "morning_seed": "morning_seed",
    "morning-seed": "morning_seed",
    "morning": "morning_seed",
    "commissioning": "morning_seed",
    "seed": "morning_seed",
    "cmq": "morning_seed",
}

ACTION_KINDS = frozenset(
    {"next_action", "next_action_touch", "acknowledge", "park", "note"}
)
_ACTION_ALIASES = {
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "next_action": "next_action",
    "acknowledge": "acknowledge",
    "ack": "acknowledge",
    "park": "park",
    "note": "note",
}

WITA = timezone(timedelta(hours=8))

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema_id": SCHEMA_ID,
    "run_id": RUN_ID,
    "claim_id": CLAIM_ID,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_haikal_human": False,
    "invented_devi_done": False,
    "haikal_human": "not_started",
    "haikal_human_status": "not_started",
    "devi_retest": "parked",
    "devi_retest_status": "parked",
    "human_commissioned_invented": False,
    "cr_resolved": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "money": None,
    "payment_executed": False,
    "folio_executed": False,
    "production": False,
    "production_mutate": False,
    "cf_seat_mint": False,
    "clickup_retired": True,
    "telegram_retired": True,
    "anon_fail_closed": True,
    "empty_needs_you_is_not_live": True,
    "owner_progress_needs_you_depth": True,
    "inside_progress_not_orphan_dashboard": True,
}


class NeedsYouDepthError(ValueError):
    """Fail closed. Does not invent maturity, human done, or money."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.http = http_status


def now_iso() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    flags["caps"] = cap_honesty(catalog_db=catalog_db)
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "kind_filters": list(KIND_FILTERS),
        "kind_aliases": dict(KIND_ALIASES),
        "action_kinds": sorted(ACTION_KINDS),
        "caps": list(CAP_IDS),
        "target_crs": list(TARGET_CRS),
        "surface": DESK_HREF,
        "desk_anchor": DESK_ANCHOR,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "additionalProperties": False,
    }


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/")
    # Allowed operator routes skip refuse by tail alone when not a banned verb.
    if any(
        x in p
        for x in (
            "/operator-depth",
            "/items/",
            "/kinds",
            "/rbac",
            "/next-action",
            "/acknowledge",
            "/park",
        )
    ):
        pass
    tail = p.rsplit("/", 1)[-1].lower()
    # Operator action verbs are not refuses.
    if tail in {
        "acknowledge",
        "park",
        "next-action-touch",
        "next_action_touch",
        "kinds",
        "rbac",
        "operator-depth",
    }:
        return None
    mapping = {
        "proven": "proven_refused",
        "ready": "ready_refused",
        "staff-ready": "staff_ready_refused",
        "staff_ready": "staff_ready_refused",
        "human-commissioned": "human_commissioned_invent_refused",
        "human_commissioned": "human_commissioned_invent_refused",
        "haikal-done": "haikal_done_refused",
        "haikal_done": "haikal_done_refused",
        "devi-done": "devi_done_refused",
        "devi_done": "devi_done_refused",
        "money": "payment_refused",
        "payment": "payment_refused",
        "folio": "folio_refused",
        "bank": "bank_refused",
        "resolve": "resolve_refused",
        "production": "production_refused",
        "cloudflare": "cloudflare_refused",
        "cf": "cloudflare_refused",
    }
    return mapping.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"Owner Progress Needs-You depth refuses: {code}",
        **honesty_flags(),
    }


def _ledger_cap(cap_id: str) -> str:
    if not LEDGER_JSON.is_file():
        return "UNKNOWN"
    try:
        ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = ledger.get(cap_id)
    if isinstance(row, list) and row:
        return str(row[0])
    if isinstance(row, str):
        return row
    return "UNKNOWN"


def _cr_state(item_id: str, *, catalog: Path | str | None = None) -> str:
    path = Path(catalog) if catalog else CATALOG_DB
    try:
        conn = sqlite3.connect(str(path))
        try:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?",
                (item_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return "OPEN"
    return str(row[0]) if row and row[0] else "OPEN"


def cap_honesty(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    """CAP / CR honesty — CORE maturity stays; Progress/CORE CRs stay OPEN."""
    caps = {cid: _ledger_cap(cid) for cid in CAP_IDS}
    crs = {cr: _cr_state(cr, catalog=catalog_db) for cr in TARGET_CRS}
    return {
        **caps,
        "crs": crs,
        "cap_core_11_specified": caps.get("CAP-CORE-11") == "SPECIFIED",
        "cap_core_12_built": caps.get("CAP-CORE-12") == "BUILT",
        "all_crs_open": all(v == "OPEN" for v in crs.values()),
        "false_resolve_refused": True,
        "denominator": 77,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def normalize_kind_filter(raw: str | None) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    key = str(raw).strip().lower().replace(" ", "_")
    if key in ("all", "*", "any"):
        return None
    if key in KIND_ALIASES:
        return KIND_ALIASES[key]
    raise NeedsYouDepthError(
        f"Unknown Needs-You kind filter '{raw}'. Use: {', '.join(KIND_FILTERS)}",
        code="invalid_kind",
        http_status=400,
    )


def require_owner_operator(person_id: str | None) -> dict[str, Any]:
    """RBAC: Owner (PERS-MATT) only. Staff / outsider → 403."""
    pid = (person_id or "").strip()
    if not pid:
        raise NeedsYouDepthError(
            "verified_person_id required",
            code="missing_verified_person",
            http_status=403,
        )
    if pid != OWNER:
        raise NeedsYouDepthError(
            "Owner Progress Needs-You depth is Owner (PERS-MATT) only.",
            code="forbidden",
            http_status=403,
        )
    return {
        "person_id": OWNER,
        "seat": "owner",
        "label": "Owner",
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def _load_operator_state(path: Path | None = None) -> dict[str, Any]:
    p = path or OPERATOR_STATE
    if not p.is_file():
        return {"items": {}, "as_of": None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": {}, "as_of": None}
    if not isinstance(data, dict):
        return {"items": {}, "as_of": None}
    data.setdefault("items", {})
    return data


def _save_operator_state(state: dict[str, Any], path: Path | None = None) -> None:
    p = path or OPERATOR_STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["as_of"] = now_iso()
    p.write_text(json.dumps(state, indent=2, default=str) + "\n", encoding="utf-8")


def _append_event(event: dict[str, Any], path: Path | None = None) -> None:
    p = path or OPERATOR_EVENTS
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _mission_rows() -> dict[str, list[dict[str, Any]]]:
    overlay = prm.load_overlay() if hasattr(prm, "load_overlay") else None
    if overlay is None:
        try:
            overlay = json.loads(
                (BETA_ROOT / "state" / "progress" / "v1_overlay.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            overlay = {}
    issues = []
    if hasattr(prm, "_safe_operating_issues"):
        try:
            issues = prm._safe_operating_issues()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            issues = []
    missions = prm._build_commissioning_missions(overlay, issues)  # noqa: SLF001
    policies = prm._build_policy_decisions(  # noqa: SLF001
        overlay, overlay.get("verticals") or {}
    )
    return {
        "needs_you": list(missions.get("needs_you") or []),
        "waiting_others": list(missions.get("waiting_on_others") or []),
        "policy": list(policies or []),
        "needs_staff": list(missions.get("needs_staff") or []),
        "needs_external": list(missions.get("needs_external_access") or []),
    }


def _morning_seed_items() -> list[dict[str, Any]]:
    queue = ocq.build_queue()
    cards = [
        c
        for c in (queue.get("active_cards") or queue.get("cards") or [])
        if str(c.get("status") or "").upper() != "COMMISSIONED"
        and not c.get("commissioned")
    ]
    return cards


def _item_operator_overlay(
    item_id: str, *, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    st = state if state is not None else _load_operator_state()
    row = (st.get("items") or {}).get(item_id) or {}
    return dict(row) if isinstance(row, dict) else {}


def _normalize_source_item(
    raw: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    item_id = str(
        raw.get("id")
        or raw.get("object_id")
        or raw.get("task_id")
        or ""
    ).strip()
    title = str(
        raw.get("title")
        or raw.get("task")
        or raw.get("text")
        or item_id
        or "Untitled"
    )
    status = str(raw.get("status") or "OPEN").upper()
    return {
        "object_id": item_id,
        "id": item_id,
        "kind": kind,
        "filter": kind,
        "title": title,
        "task": title,
        "status": status,
        "who": raw.get("who") or raw.get("person_to_test") or raw.get("owner"),
        "note": raw.get("note") or raw.get("check") or raw.get("why") or "",
        "audience": raw.get("audience") or raw.get("classification") or raw.get("bucket"),
        "priority": raw.get("priority"),
        "open_href": raw.get("open_href") or raw.get("route") or DESK_HREF,
        "source": raw.get("source"),
        "capability": raw.get("capability"),
        "criterion": raw.get("criterion"),
        "do_this": list(raw.get("do_this") or []),
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_done": False,
        "fixture_honest": True,
    }


def collect_candidates(
    *,
    kind: str | None = None,
    state_path: Path | None = None,
    include_parked: bool = False,
) -> list[dict[str, Any]]:
    """Build operator candidates from Progress missions + morning seed."""
    filt = normalize_kind_filter(kind)
    op_state = _load_operator_state(state_path)
    rows = _mission_rows()
    buckets: list[tuple[str, list[dict[str, Any]]]] = [
        ("needs_you", rows["needs_you"]),
        ("waiting_others", rows["waiting_others"]),
        ("policy", rows["policy"]),
        ("morning_seed", _morning_seed_items()),
    ]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket, items in buckets:
        if filt and bucket != filt:
            continue
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = _normalize_source_item(raw, kind=bucket)
            oid = item["object_id"]
            if not oid or oid in seen:
                continue
            seen.add(oid)
            overlay = _item_operator_overlay(oid, state=op_state)
            op_status = str(overlay.get("operator_status") or "").upper()
            if op_status == "PARKED" and not include_parked:
                continue
            item["operator_status"] = op_status or None
            item["last_action"] = overlay.get("last_action")
            item["last_note"] = overlay.get("last_note")
            item["last_at"] = overlay.get("last_at")
            item["acknowledged"] = op_status == "ACKNOWLEDGED"
            item["parked"] = op_status == "PARKED"
            item["href"] = f"{DESK_ANCHOR}&item={oid}"
            out.append(item)
    # Stable order: morning_seed P0 first when all; else bucket order already applied
    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        pri = {"P0": 0, "P1": 1, "P2": 2}.get(str(it.get("priority") or ""), 5)
        kind_rank = {k: i for i, k in enumerate(KIND_FILTERS)}.get(it["kind"], 9)
        return (kind_rank, pri, str(it.get("object_id") or ""))

    out.sort(key=sort_key)
    return out


def needs_you_strip(
    *,
    state_path: Path | None = None,
) -> dict[str, Any]:
    """Needs-You strip — Owner-facing open items. EMPTY honesty."""
    candidates = collect_candidates(kind="needs_you", state_path=state_path)
    # Morning seed Needs Matt also count toward Needs-You attention
    seed_matt = [
        c
        for c in collect_candidates(kind="morning_seed", state_path=state_path)
        if str(c.get("audience") or "").upper() == "NEEDS_MATT"
    ]
    items = candidates + [
        s for s in seed_matt if s["object_id"] not in {c["object_id"] for c in candidates}
    ]
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(items),
        "items": [
            {
                "object_id": i["object_id"],
                "kind": i["kind"],
                "title": i["title"],
                "status": i.get("operator_status") or i.get("status"),
                "audience": i.get("audience"),
                "href": i.get("href"),
                "code": "owner_progress_needs_you",
            }
            for i in items[:20]
        ],
        "empty_message": (
            "Nothing Needs-You on Owner Progress — EMPTY honesty."
            if empty
            else None
        ),
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def waiting_others_strip(*, state_path: Path | None = None) -> dict[str, Any]:
    candidates = collect_candidates(kind="waiting_others", state_path=state_path)
    empty = len(candidates) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(candidates),
        "items": candidates[:20],
        "empty_message": (
            "No Waiting-Others rows — EMPTY honesty." if empty else None
        ),
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def morning_seed_strip(*, state_path: Path | None = None) -> dict[str, Any]:
    candidates = collect_candidates(kind="morning_seed", state_path=state_path)
    empty = len(candidates) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(candidates),
        "items": candidates[:20],
        "seed_doc": str(SEED_DOC.relative_to(BETA_ROOT)) if SEED_DOC.is_file() else None,
        "empty_message": (
            "Morning Commissioning seed empty — EMPTY honesty." if empty else None
        ),
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
    }


def readiness_strip(*, state_path: Path | None = None) -> dict[str, Any]:
    by_kind = {f: 0 for f in KIND_FILTERS}
    all_items = collect_candidates(state_path=state_path)
    for it in all_items:
        k = it.get("kind")
        if k in by_kind:
            by_kind[k] += 1
    empty = len(all_items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "open_count": len(all_items),
        "by_kind": by_kind,
        "empty": empty,
        "staff_ready": False,
        "ready": False,
        "proven": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "empty_message": (
            "No open Needs-You / Waiting-Others / Policy / Morning seed items — "
            "EMPTY honesty."
            if empty
            else None
        ),
        "why": (
            "Owner Progress readiness from curated missions + morning commissioning "
            "seed only. Not staff_ready=true invent. Not Haikal/Devi done invent."
        ),
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    kind: str | None = None,
    limit: int = 40,
    state_path: Path | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Needs-You / Waiting-Others / Policy / Morning seed desk + EMPTY honesty."""
    seat = require_owner_operator(verified_person_id)
    filt = normalize_kind_filter(kind)
    candidates = collect_candidates(kind=filt, state_path=state_path)
    capped = candidates[: max(1, min(int(limit or 40), 100))]
    empty = len(candidates) == 0
    readiness = readiness_strip(state_path=state_path)
    needs = needs_you_strip(state_path=state_path)
    waiting = waiting_others_strip(state_path=state_path)
    morning = morning_seed_strip(state_path=state_path)
    caps = cap_honesty(catalog_db=catalog_db)
    kind_buckets = [
        {
            "filter": f,
            "kind": f,
            "label": {
                "needs_you": "Needs You",
                "waiting_others": "Waiting Others",
                "policy": "Policy",
                "morning_seed": "Morning Commissioning seed",
            }[f],
            "open_count": readiness["by_kind"].get(f, 0),
        }
        for f in KIND_FILTERS
    ]
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "desk_anchor": DESK_ANCHOR,
        "desk_href": DESK_HREF,
        "kind_filter": filt,
        "kind_buckets": kind_buckets,
        "seat": seat,
        "rbac": {
            "person_id": seat["person_id"],
            "can_owner_progress_operator": True,
            "owner_only": True,
        },
        "candidates": capped,
        "candidate_count": len(candidates),
        "empty": empty,
        "empty_message": (
            (
                f"No open {filt or 'Needs-You depth'} items — EMPTY honesty "
                "(not invent live commissioning done)."
            )
            if empty
            else None
        ),
        "progress_readiness": readiness,
        "needs_you_strip": needs,
        "waiting_others_strip": waiting,
        "morning_seed_strip": morning,
        "caps": caps,
        "target_crs": list(TARGET_CRS),
        "why": (
            "Owner Progress Needs-You depth: Needs-You / Waiting-Others / Policy / "
            "Morning Commissioning seed; open detail; next-action / acknowledge / park "
            "refresh strips. No invent staff_ready / PROVEN / READY / Haikal done / "
            "Devi done. Progress/CORE CRs stay OPEN."
        ),
        **honesty_flags(catalog_db=catalog_db),
    }


def _find_item(
    object_id: str,
    *,
    state_path: Path | None = None,
    include_parked: bool = True,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    if not oid:
        return None
    for it in collect_candidates(
        state_path=state_path, include_parked=include_parked
    ):
        if it.get("object_id") == oid:
            return it
    return None


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    state_path: Path | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Item detail — fixture/CR honesty; no invent human test done."""
    seat = require_owner_operator(verified_person_id)
    item = _find_item(object_id, state_path=state_path, include_parked=True)
    if item is None:
        raise NeedsYouDepthError(
            f"Needs-You item '{object_id}' not found",
            code="not_found",
            http_status=404,
        )
    readiness = readiness_strip(state_path=state_path)
    needs = needs_you_strip(state_path=state_path)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "seat": seat,
        "object": {
            **item,
            "haikal_human": "not_started",
            "devi_retest": "parked",
            "staff_ready": False,
            "proven": False,
            "ready": False,
            "human_done": False,
            "invented_human_done": False,
        },
        "actions": {
            "next_action_touch": True,
            "acknowledge": True,
            "park": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "human_commissioned": False,
            "haikal_done": False,
            "devi_done": False,
            "money": False,
        },
        "next_actions": [
            {
                "code": "next_action_touch",
                "label": "Touch next action (refresh Needs-You strips)",
            },
            {"code": "acknowledge", "label": "Acknowledge (Owner saw it)"},
            {"code": "park", "label": "Park (remove from Needs-You strip)"},
        ],
        "progress_readiness": readiness,
        "needs_you_strip": needs,
        "waiting_others_strip": waiting_others_strip(state_path=state_path),
        "morning_seed_strip": morning_seed_strip(state_path=state_path),
        "caps": cap_honesty(catalog_db=catalog_db),
        "href": item.get("href"),
        **honesty_flags(catalog_db=catalog_db),
    }


def record_operator_action(
    object_id: str,
    *,
    verified_person_id: str | None,
    kind: str | None = None,
    note: str | None = None,
    state_path: Path | None = None,
    events_path: Path | None = None,
    catalog_db: Path | str | None = None,
    connective_actor: str | None = None,
) -> dict[str, Any]:
    """Record next-action / acknowledge / park; refresh Needs-You strips.

    Does not invent COMMISSIONED / Haikal done / Devi done / PROVEN / READY.
    Does not resolve Progress/CORE CRs.

    connective_actor writes the same operator state after Staff Ops has already
    scope-checked the seat. Owner HTTP routes leave it unset and stay Owner-only.
    """
    actor = (connective_actor or "").strip()
    if actor:
        seat = {
            "person_id": actor,
            "seat": "connective",
            "label": actor,
            "haikal_human": "not_started",
            "devi_retest": "parked",
        }
    else:
        seat = require_owner_operator(verified_person_id)
    raw_kind = (kind or "next_action").strip().lower()
    action = _ACTION_ALIASES.get(raw_kind) or _ACTION_ALIASES.get(
        raw_kind.replace("-", "_")
    )
    if action is None:
        raise NeedsYouDepthError(
            "kind must be one of next-action-touch / acknowledge / park / note",
            code="invalid_kind",
            http_status=400,
        )
    item = _find_item(object_id, state_path=state_path, include_parked=True)
    if item is None:
        raise NeedsYouDepthError(
            f"Needs-You item '{object_id}' not found",
            code="not_found",
            http_status=404,
        )

    op_status_map = {
        "next_action": "TOUCHED",
        "acknowledge": "ACKNOWLEDGED",
        "park": "PARKED",
        "note": "NOTED",
    }
    op_status = op_status_map[action]
    text = (note or "").strip()[:500] or None
    event = {
        "event_id": f"nye-{uuid.uuid4().hex[:12]}",
        "at": now_iso(),
        "kind": action,
        "object_id": object_id,
        "person_id": seat["person_id"],
        "note": text,
        "source_kind": item.get("kind"),
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
        "cr_resolved": False,
        "money": None,
    }
    _append_event(event, path=events_path)

    st = _load_operator_state(state_path)
    items = dict(st.get("items") or {})
    items[object_id] = {
        "operator_status": op_status,
        "last_action": action,
        "last_note": text,
        "last_at": event["at"],
        "last_event_id": event["event_id"],
        "person_id": seat["person_id"],
        # Honesty locks — touches never invent maturity / human done
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "commissioned": False,
    }
    st["items"] = items
    _save_operator_state(st, path=state_path)

    readiness = readiness_strip(state_path=state_path)
    needs = needs_you_strip(state_path=state_path)
    refreshed = _find_item(object_id, state_path=state_path, include_parked=True)
    return {
        "ok": True,
        "recorded": True,
        "action": "owner_progress_needs_you",
        "kind": action,
        "seat": seat,
        "object": refreshed or {**item, "operator_status": op_status},
        "event": event,
        "progress_readiness": readiness,
        "needs_you_strip": needs,
        "waiting_others_strip": waiting_others_strip(state_path=state_path),
        "morning_seed_strip": morning_seed_strip(state_path=state_path),
        "message": (
            f"{action} recorded. Needs-You / Waiting-Others / Morning seed strips "
            "refreshed. No invent staff_ready / PROVEN / READY / Haikal done / Devi done."
        ),
        "caps": cap_honesty(catalog_db=catalog_db),
        **honesty_flags(catalog_db=catalog_db),
    }


def next_action_touch(
    object_id: str,
    *,
    verified_person_id: str | None,
    note: str | None = None,
    kind: str | None = None,
    state_path: Path | None = None,
    events_path: Path | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    return record_operator_action(
        object_id,
        verified_person_id=verified_person_id,
        kind=kind or "next_action",
        note=note,
        state_path=state_path,
        events_path=events_path,
        catalog_db=catalog_db,
    )


def acknowledge(
    object_id: str,
    *,
    verified_person_id: str | None,
    note: str | None = None,
    state_path: Path | None = None,
    events_path: Path | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    return record_operator_action(
        object_id,
        verified_person_id=verified_person_id,
        kind="acknowledge",
        note=note,
        state_path=state_path,
        events_path=events_path,
        catalog_db=catalog_db,
    )


def park(
    object_id: str,
    *,
    verified_person_id: str | None,
    note: str | None = None,
    state_path: Path | None = None,
    events_path: Path | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    return record_operator_action(
        object_id,
        verified_person_id=verified_person_id,
        kind="park",
        note=note,
        state_path=state_path,
        events_path=events_path,
        catalog_db=catalog_db,
    )


def prove_rbac(*, person_id: str | None = None) -> dict[str, Any]:
    pid = (person_id or "").strip() or OWNER
    try:
        seat = require_owner_operator(pid)
        can = True
    except NeedsYouDepthError:
        seat = {"person_id": pid, "seat": None}
        can = False
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "person_id": pid,
        "can_owner_progress_operator": can,
        "rbac": seat,
        "fixtures": list(OPERATOR_FIXTURES),
        "owner_only": True,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "caps": cap_honesty(),
        **honesty_flags(),
    }


def kind_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "kind_filters": list(KIND_FILTERS),
        "kind_aliases": dict(KIND_ALIASES),
        "labels": {
            "needs_you": "Needs You",
            "waiting_others": "Waiting Others",
            "policy": "Policy",
            "morning_seed": "Morning Commissioning seed",
        },
        "action_kinds": sorted(ACTION_KINDS),
        **honesty_flags(),
    }
