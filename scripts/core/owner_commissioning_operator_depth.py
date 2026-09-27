#!/usr/bin/env python3
"""Owner Commissioning Queue operator depth — Beta :8788 only.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) +
RULE-Wolf-Overnight-Owner-Commissioning-2026-09-22.md.
Plan: docs/deliveries/GROK-PLAN-OWNER-COMMISSIONING-OPERATOR-DEPTH-2026-09-23.md.

Authorised Owner opens a commissioning card, or the EMPTY placeholder when
the open queue is clear, and records note / next-action-touch /
handoff-touch / dismiss-noise / review-decision. Recording refreshes the
Progress Needs-You strips and the commissioning counters. It does not write
PASS evidence, invent HUMAN COMMISSIONED / PROVEN / READY / staff_ready, or
mark Haikal or Devi done.

PASS submit on the existing commissioning queue remains the only commission
evidence. Progress, CORE, and Global Nav completion rows stay as they are.
No BZG compose. No Cloudflare Access Include mutate. No secret mint.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import owner_commissioning_queue as ocq
from core import owner_progress_needs_you_depth as nye

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
QUEUE_STUB = (
    BETA_ROOT
    / "state"
    / "completion-register"
    / "wolf-owner-commissioning-queue-20260922.json"
)
DEFAULT_EVENTS = BETA_ROOT / "state" / "progress" / "commissioning-operator-events.jsonl"

BOUND = "beta-owner-progress-safe"
SCHEMA_ID = "wolf.owner-commissioning-operator-depth.v1"
SLICE = "owner_commissioning_operator_depth"
RUN_ID = "BF-owner-commissioning-operator-depth-20260923"
CLAIM_ID = "bf-owner-commissioning-operator-depth-20260923"
DESK_HREF = "/progress"
DESK_ANCHOR = "/progress#my-commissioning"
EMPTY_ID = "EMPTY-OWNER-COMMISSIONING"
OWNER = ocq.PERS_MATT

PROGRESS_CRS: tuple[str, ...] = nye.TARGET_CRS
NAV_AS_IS: dict[str, str] = {
    "531f29b41f5dfb381503889cacdcfb39": "IN_PROGRESS",
    "e4bee2462ff81803287fa3562776d8ec": "OPEN",
    "CR-5a5e660e41f782a4": "RESOLVED",
    "CR-26989486969627cd": "RESOLVED",
}

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_open", "not_commissioned", "keep_as_note"})
_ACTION_ALIASES = {
    "note": "note",
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "next_action": "next_action",
    "handoff": "handoff_touch",
    "handoff-touch": "handoff_touch",
    "handoff_touch": "handoff_touch",
    "dismiss": "dismiss_noise",
    "dismiss-noise": "dismiss_noise",
    "dismiss_noise": "dismiss_noise",
    "review": "review_decision",
    "review-decision": "review_decision",
    "review_decision": "review_decision",
}
_BANNED_KINDS = {
    "proven": "proven_refused",
    "ready": "ready_refused",
    "staff_ready": "staff_ready_refused",
    "staff-ready": "staff_ready_refused",
    "human_commissioned": "human_commissioned_invent_refused",
    "human-commissioned": "human_commissioned_invent_refused",
    "commissioned": "human_commissioned_invent_refused",
    "pass": "pass_submit_only",
    "submit": "pass_submit_only",
    "haikal_done": "haikal_done_refused",
    "haikal-done": "haikal_done_refused",
    "devi_done": "devi_done_refused",
    "devi-done": "devi_done_refused",
    "money": "money_refused",
    "secret": "secret_refused",
    "secret-mint": "secret_refused",
    "access": "access_refused",
    "access-include": "access_refused",
    "compose": "bzg_compose_refused",
    "bzg-compose": "bzg_compose_refused",
    "production": "production_refused",
    "resolve": "resolve_refused",
}
_BANNED_BODY = frozenset(
    {
        "proven",
        "ready",
        "staff_ready",
        "human_commissioned",
        "commissioned",
        "pass",
        "submit",
        "haikal_done",
        "devi_done",
        "maturity",
        "money",
        "secret",
        "token",
        "access",
        "access_include",
        "compose",
        "bzg_compose",
        "production",
        "resolve",
        "cr_resolved",
    }
)
_ALLOWED_BODY = frozenset({"kind", "note", "body", "decision", "provenance"})
_CARD_RE = re.compile(r"^CMQ-[A-Za-z0-9][A-Za-z0-9-]{0,96}$")
_NOTE_BANNED = re.compile(
    r"human[_\s-]?commissioned|staff[_\s-]?ready|\bproven\b|\bready\b|"
    r"haikal[_\s-]?done|devi[_\s-]?done",
    re.IGNORECASE,
)
_MONEY_NOTE = re.compile(
    r"\b(payment|idr|usd|invoice|transfer)\b|\$\s*\d",
    re.IGNORECASE,
)
_REFUSE_TAILS = dict(_BANNED_KINDS)

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
    "invented_human_commissioned": False,
    "human_commissioned_requires_submit_evidence": True,
    "pass_submit_is_only_commission_evidence": True,
    "pass_submit_bypassed": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "bzg_compose": False,
    "money": None,
    "secret_mint": False,
    "cf_access_include_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "cr_mutated": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "queue_mutated": False,
    "evidence_mutated": False,
    "duplicate_mutate_surface": False,
    "anon_fail_closed": True,
    "invented_permission_grant": False,
    "intg_reopened": False,
    "w12_fin_reopened": False,
    "clickup_retired": True,
    "telegram_retired": True,
    "owner_commissioning_operator_depth": True,
    "inside_progress_not_orphan_dashboard": True,
    "empty_queue_is_not_human_commissioned": True,
}


class CommissionDepthError(ValueError):
    """Fail closed. Does not invent commission, maturity, or a PASS bypass."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.http = http_status


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _assert_events_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low or "wolf-system" in low or "/production" in low:
        raise CommissionDepthError(
            "Owner commissioning operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if resolved.name == "money.sqlite":
        raise CommissionDepthError(
            "Owner commissioning operator depth refuses money",
            code="money_refused",
            http_status=403,
        )
    if resolved.name in {ocq.EVIDENCE_NAME, ocq.QUEUE_STATE_NAME}:
        raise CommissionDepthError(
            "PASS submit remains the only commission evidence. "
            "Operator depth does not write the commissioning evidence or queue state.",
            code="pass_submit_only",
            http_status=403,
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise CommissionDepthError(
            "Owner commissioning operator depth refuses a path outside Beta",
            code="production_refused",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env = (os.environ.get("WOLF_OWNER_CMQ_OPS_EVENTS") or "").strip()
        path = Path(env) if env else DEFAULT_EVENTS
    _assert_events_path(path)
    return path


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
        return "UNKNOWN"
    return str(row[0]) if row and row[0] else "UNKNOWN"


def _stub_status() -> str:
    try:
        data = json.loads(QUEUE_STUB.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    if isinstance(data, dict):
        return str(data.get("status") or "UNKNOWN")
    return "UNKNOWN"


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    caps = nye.cap_honesty(catalog_db=catalog_db)
    flags["caps"] = caps
    flags["cap_core_11"] = _ledger_cap("CAP-CORE-11")
    flags["cap_core_12"] = _ledger_cap("CAP-CORE-12")
    flags["progress_core_crs"] = {cr: _cr_state(cr, catalog=catalog_db) for cr in PROGRESS_CRS}
    flags["global_nav_crs"] = {cr: _cr_state(cr, catalog=catalog_db) for cr in NAV_AS_IS}
    flags["commissioning_queue_stub_status"] = _stub_status()
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["cr_resolved"] = False
    flags["false_resolve_cr"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "surface": DESK_HREF,
        "desk_anchor": DESK_ANCHOR,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "empty_object_id": EMPTY_ID,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "human_commissioned_accepted": False,
        "pass_submit_bypass_accepted": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "additionalProperties": False,
    }


def _object_tail(tail: str) -> bool:
    token = (tail or "").strip()
    if token.upper() == EMPTY_ID:
        return True
    return bool(_CARD_RE.fullmatch(token))


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    marker = "/api/progress/commissioning/operator-depth"
    if marker not in p:
        return None
    tail = p.rsplit("/", 1)[-1]
    if tail in {
        "operator-depth",
        "desk",
        "rbac",
        "operator-action",
        "note",
        "next-action-touch",
        "handoff-touch",
        "dismiss-noise",
        "review-decision",
    }:
        return None
    if _object_tail(tail):
        return None
    return _REFUSE_TAILS.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"Owner commissioning operator depth refuses: {code}",
        "human_commissioned": False,
        "pass_submit_bypassed": False,
        "bzg_compose": False,
        "queue_mutated": False,
        "evidence_mutated": False,
        **honesty_flags(),
    }


def require_seat(person_id: str | None) -> dict[str, Any]:
    """Owner only. Haikal, Devi, Amanda, Misa, and outsiders stay refused.

    This slice does not insert a permission, a Cloudflare Access Include,
    or a secret.
    """
    pid = (person_id or "").strip()
    if not pid:
        raise CommissionDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    if pid != OWNER:
        raise CommissionDepthError(
            "Owner commissioning operator depth is Owner only. "
            "Haikal, Devi, Amanda, Misa, and other seats are not granted.",
            code="outsider",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": "owner",
        "authorised": True,
        "invented_permission_grant": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def prove_rbac(*, person_id: str) -> dict[str, Any]:
    seat = require_seat(person_id)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "can_commissioning_operator": True,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "human_commissioned": False,
            "pass_submit": False,
            "haikal_done": False,
            "devi_done": False,
            "bzg_compose": False,
            "access_include": False,
            "secret_mint": False,
            "money": False,
        },
        "invented_permission_grant": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(),
    }


def _normalise_kind(kind: str) -> str:
    raw = (kind or "").strip().lower()
    if raw in _BANNED_KINDS:
        code = _BANNED_KINDS[raw]
        raise CommissionDepthError(
            f"Owner commissioning operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise CommissionDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise CommissionDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key) or _BANNED_KINDS.get(key.replace("_", "-"), "refused_field")
        raise CommissionDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise CommissionDepthError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _append_event(path: Path, event: dict[str, Any]) -> None:
    _assert_events_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _events_for(events: list[dict[str, Any]], object_id: str) -> list[dict[str, Any]]:
    return [e for e in events if str(e.get("object_id") or "") == object_id]


def _latest(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    found = [e for e in events if e.get("kind") == kind]
    return found[-1] if found else None


def _action_view(object_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    related = _events_for(events, object_id)
    review = _latest(related, "review_decision")
    return {
        "operator_event_count": len(related),
        "review_recorded": review is not None,
        "review_decision": (review or {}).get("decision"),
        "dismissed_noise": _latest(related, "dismiss_noise") is not None,
        "latest_note": (_latest(related, "note") or {}).get("note"),
        "latest_next_action": (_latest(related, "next_action") or {}).get("note"),
        "human_commissioned": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def _person_flags(card: dict[str, Any] | None) -> dict[str, Any]:
    person = str((card or {}).get("person_to_test") or "")
    return {
        "person_to_test": person or None,
        "haikal_card": person.lower() == "haikal",
        "devi_card": person.lower() == "devi",
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "operator_does_not_complete_haikal": True,
        "operator_does_not_complete_devi": True,
    }


def _project_card(card: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    oid = str(card.get("id") or "")
    return {
        "object_id": oid,
        "object_kind": "commissioning_card",
        "task": card.get("task"),
        "priority": card.get("priority"),
        "business": card.get("business"),
        "status": card.get("status"),
        "audience": card.get("audience"),
        "open_href": card.get("open_href"),
        "check": card.get("check"),
        "capability": card.get("capability"),
        "criterion": card.get("criterion"),
        "href": f"{DESK_ANCHOR}-{oid}",
        "commissioned": False,
        "empty": False,
        "pass_submit_is_only_commission_evidence": True,
        **_person_flags(card),
        **_action_view(oid, events),
    }


def _empty_placeholder(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_id": EMPTY_ID,
        "object_kind": "empty_placeholder",
        "task": None,
        "status": None,
        "href": f"{DESK_ANCHOR}-{EMPTY_ID}",
        "commissioned": False,
        "empty": True,
        "empty_message": (
            "Commissioning queue has no open cards. Empty is not a new "
            "HUMAN COMMISSIONED invent. PASS submit remains the only commission evidence."
        ),
        "pass_submit_is_only_commission_evidence": True,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        **_action_view(EMPTY_ID, events),
    }


def _queue(state_override: Path | None) -> dict[str, Any]:
    return ocq.build_queue(state_override=state_override, include_commissioned=True)


def _commissioning_projection(queue: dict[str, Any]) -> dict[str, Any]:
    counters = dict(queue.get("counters") or {})
    return {
        "ok": True,
        "bound": queue.get("bound"),
        "schema_id": queue.get("schema_id"),
        "counters": counters,
        "active_count": len(queue.get("active_cards") or []),
        "evidence_count": queue.get("evidence_count"),
        "first_task": (queue.get("first_task") or {}).get("id"),
        "pass_submit_is_only_commission_evidence": True,
        "human_commissioned_invented": False,
        "queue_mutated": False,
        "evidence_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "href": DESK_ANCHOR,
    }


def _needs_you_projection() -> dict[str, Any]:
    needs = nye.needs_you_strip()
    waiting = nye.waiting_others_strip()
    morning = nye.morning_seed_strip()
    return {
        "ok": True,
        "needs_you_strip": needs,
        "waiting_others_strip": waiting,
        "morning_seed_strip": morning,
        "count": needs.get("count"),
        "waiting_count": waiting.get("count"),
        "morning_count": morning.get("count"),
        "duplicate_mutate_surface": False,
        "queue_mutated": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    state_override: Path | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    queue = _queue(state_override)
    events = _load_events(events_path(events_file))
    active = [c for c in (queue.get("active_cards") or []) if isinstance(c, dict)]
    empty = len(active) == 0
    cards = [_project_card(card, events) for card in active]
    placeholder = [_empty_placeholder(events)] if empty else []
    objects = placeholder + cards
    open_objects = [obj for obj in objects if not obj.get("dismissed_noise")]
    if empty:
        empty_message = (
            "No open commissioning cards. Empty is not HUMAN COMMISSIONED, "
            "not PROVEN, and not staff_ready. PASS submit remains the only commission evidence."
        )
    else:
        empty_message = None
    commissioning = _commissioning_projection(queue)
    needs = _needs_you_projection()
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "seat": seat,
        "href": DESK_ANCHOR,
        "cards": cards,
        "card_count": len(cards),
        "empty_placeholder": placeholder[0] if placeholder else None,
        "objects": objects,
        "open_count": len(open_objects),
        "empty": empty,
        "empty_message": empty_message,
        "commissioning": commissioning,
        "counters": commissioning.get("counters"),
        "needs_you": needs,
        "queue_mutated": False,
        "evidence_mutated": False,
        "pass_submit_bypassed": False,
        "human_commissioned": False,
        "bzg_compose": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _find_object(
    object_id: str,
    *,
    state_override: Path | None,
) -> dict[str, Any]:
    token = (object_id or "").strip()
    queue = _queue(state_override)
    active = [c for c in (queue.get("active_cards") or []) if isinstance(c, dict)]
    all_cards = [c for c in (queue.get("cards") or []) if isinstance(c, dict)]
    by_active = {str(c.get("id")): c for c in active}
    by_all = {str(c.get("id")): c for c in all_cards}
    if token == EMPTY_ID:
        if active:
            raise CommissionDepthError(
                "The queue still has open cards. The empty placeholder is not a second commission.",
                code="not_found",
                http_status=404,
            )
        return {"object_kind": "empty_placeholder", "object_id": EMPTY_ID, "card": None}
    if token in by_active:
        return {
            "object_kind": "commissioning_card",
            "object_id": token,
            "card": by_active[token],
        }
    if token in by_all:
        raise CommissionDepthError(
            "This card is not an open commissioning object. "
            "Operator depth does not invent HUMAN COMMISSIONED and does not bypass PASS submit.",
            code="not_open",
            http_status=404,
        )
    if _CARD_RE.fullmatch(token):
        raise CommissionDepthError(
            "Commissioning card was not found. It was not invented.",
            code="not_found",
            http_status=404,
        )
    raise CommissionDepthError(
        "Unknown commissioning object. It was not invented.",
        code="not_found",
        http_status=404,
    )


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    state_override: Path | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    events = _load_events(events_path(events_file))
    found = _find_object(object_id, state_override=state_override)
    oid = found["object_id"]
    card = found["card"]
    queue = _queue(state_override)
    detail = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "seat": seat,
        "object_id": oid,
        "object_kind": found["object_kind"],
        "card": _project_card(card, events) if card else None,
        "actions": _action_view(oid, events),
        "events": _events_for(events, oid),
        "empty": found["object_kind"] == "empty_placeholder",
        "commissioning": _commissioning_projection(queue),
        "counters": (queue.get("counters") or {}),
        "needs_you": _needs_you_projection(),
        "human_commissioned": False,
        "pass_submit_bypassed": False,
        "queue_mutated": False,
        "evidence_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
        **_person_flags(card),
    }
    if found["object_kind"] == "empty_placeholder":
        detail["empty_message"] = (
            "No open commissioning cards. Empty is not HUMAN COMMISSIONED."
        )
    return detail


def _clean_note(text: str) -> str:
    note = (text or "").strip()
    if len(note) < 2 or len(note) > 4000:
        raise CommissionDepthError(
            "An operator note is required. A blank note is not a commission.",
            code="missing_note",
            http_status=400,
        )
    if _MONEY_NOTE.search(note):
        raise CommissionDepthError(
            "An operator note is not a payment.",
            code="money_refused",
            http_status=403,
        )
    if _NOTE_BANNED.search(note):
        raise CommissionDepthError(
            "An operator note cannot invent HUMAN COMMISSIONED, maturity, Haikal done, or Devi done.",
            code="refused_field",
            http_status=403,
        )
    return note


def _fingerprint(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def record_operator_action(
    object_id: str,
    *,
    verified_person_id: str | None,
    kind: str,
    note: str | None = None,
    decision: str | None = None,
    body: dict | None = None,
    state_override: Path | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Record an allowed operator action. Does not write PASS evidence."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id)
    canon = _normalise_kind(kind)
    evidence_before = _fingerprint(ocq.evidence_path(state_override))
    queue_before = _fingerprint(ocq.queue_state_path(state_override))
    nye_state_before = _fingerprint(nye.OPERATOR_STATE)
    nye_events_before = _fingerprint(nye.OPERATOR_EVENTS)
    stub_before = _fingerprint(QUEUE_STUB)
    counters_before = (_queue(state_override).get("counters") or {})
    found = _find_object(object_id, state_override=state_override)
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise CommissionDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        decision_token = (decision or "").strip().lower().replace("-", "_")
        banned_decision = _BANNED_KINDS.get(decision_token) or _BANNED_KINDS.get(
            decision_token.replace("_", "-")
        )
        if banned_decision:
            raise CommissionDepthError(
                "A review decision does not commission a card and does not invent maturity.",
                code=banned_decision,
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise CommissionDepthError(
                "decision must be still_open, not_commissioned, or keep_as_note",
                code="invalid_decision",
                http_status=400,
            )
    path = events_path(events_file)
    event = {
        "event_id": f"EVT-{uuid.uuid4()}",
        "object_id": found["object_id"],
        "object_kind": found["object_kind"],
        "task_id": (found["card"] or {}).get("id") if found["card"] else None,
        "kind": canon,
        "note": text or None,
        "decision": decision_token,
        "person_id": seat["person_id"],
        "recorded_at": now_utc_iso(),
        "human_commissioned": False,
        "pass_submit_bypassed": False,
        "queue_mutated": False,
        "evidence_mutated": False,
        "bzg_compose": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
    }
    _append_event(path, event)
    evidence_after = _fingerprint(ocq.evidence_path(state_override))
    queue_after = _fingerprint(ocq.queue_state_path(state_override))
    if evidence_before != evidence_after or queue_before != queue_after:
        raise CommissionDepthError(
            "Operator depth must not write commissioning evidence or queue state.",
            code="pass_submit_only",
            http_status=403,
        )
    if _fingerprint(nye.OPERATOR_STATE) != nye_state_before or _fingerprint(nye.OPERATOR_EVENTS) != nye_events_before:
        raise CommissionDepthError(
            "Operator depth refreshes Needs-You by reading it. It does not write a second mutate surface.",
            code="duplicate_mutate_surface",
            http_status=403,
        )
    if _fingerprint(QUEUE_STUB) != stub_before:
        raise CommissionDepthError(
            "Operator depth does not rewrite the commissioning completion stub.",
            code="resolve_refused",
            http_status=403,
        )
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        state_override=state_override,
        events_file=path,
        catalog_db=catalog_db,
    )
    counters_after = desk.get("counters") or {}
    return {
        "ok": True,
        "action": "owner_commissioning_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": found["object_id"],
        "evidence_unchanged": True,
        "queue_unchanged": True,
        "counters_unchanged": counters_before == counters_after,
        "queue_mutated": False,
        "evidence_mutated": False,
        "pass_submit_bypassed": False,
        "human_commissioned": False,
        "commissioning": desk.get("commissioning"),
        "counters": counters_after,
        "needs_you": desk.get("needs_you"),
        "card_desk": {
            "card_count": desk.get("card_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "open_count": desk.get("open_count"),
            "href": DESK_ANCHOR,
        },
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
        "money": None,
        "secret_mint": False,
        "cf_access_include_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
