#!/usr/bin/env python3
"""Sprint2 P6 Staff-Ready UX — phone-first overlays for BZG / GGV / AMG packs.

Decision served: 2026-09-19 owner release keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), armed plan
docs/deliveries/GROK-PLAN-SPRINT2-P6-STAFF-READY-UX-2026-09-22.md /
docs/deliveries/GROK-GAP-ATTACK-SPRINT-2-2026-09-22.md §Staff-ready.

Bound: beta-staff-ready-safe

Additive presentation helpers only. Does not invent leads, hotel facts,
money, PROVEN, or READY. Does not execute payment. Does not mutate
Production or Cloudflare. Empty stays empty with a next action.
"""
from __future__ import annotations

from typing import Any

BOUND = "beta-staff-ready-safe"
SCHEMA_ID = "wolf.staff-ready-ux.v1"

# Staff-facing person labels — never show PERS-* in operator copy.
PERSON_LABELS: dict[str, str] = {
    "PERS-MATT": "Owner",
    "PERS-AMANDA": "Amanda",
    "PERS-HAIKAL": "Haikal",
    "PERS-MISA": "Misa",
    "PERS-DEVI": "Devi",
}

# GGV loop stage keys → operator words.
STAGE_LABELS: dict[str, str] = {
    "lead": "Lead",
    "identity_contact": "Contact noted",
    "qualification": "Qualified",
    "next_action": "Next step",
    "ownership": "Owner set",
    "pipeline": "In pipeline",
    "client_project": "Client / project",
    "proposal_engagement": "Proposal / engagement",
    "content_work": "Content work",
    "approval": "Approval",
    "publish_read": "Publish read",
    "performance": "Performance",
    "client_visibility": "Client visibility",
    "mgmt_exception": "Needs management",
    "empty": "Not started",
    "done": "Done",
    "read": "Read",
    "raised": "Raised",
    "due": "Due",
}

LIFECYCLE_LABELS: dict[str, str] = {
    "OPEN": "Open",
    "ACTIVE": "Active",
    "PARKED": "Parked",
    "CLOSED": "Closed",
}

SEAT_LABELS: dict[str, str] = {
    "owner": "Owner",
    "content_management": "Content management",
    "editor": "Editor",
    "crew": "Crew",
    "hotel_ops": "Hotel ops",
}

# Developer tokens that must not appear in staff-facing copy surfaces.
DEV_TOKENS: tuple[str, ...] = (
    "PERS-",
    "CAP-",
    "CR-",
    "DERIVE",
    "SPECIFIED",
    "BUILT",
    "PROVEN",
    "READY",
    "wolf_lifecycle",
    "loop_next_action",
    "day_next_action",
    "metricool_write=",
    "live_client_report=",
    "invented_metrics=",
)

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "schema_id": SCHEMA_ID,
    "proven": False,
    "ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "money_actions": False,
    "cloudflare_mutate": False,
    "production_mutate": False,
    "additive_only": True,
    "phone_first": True,
}


class StaffReadyError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_proven(_payload: dict[str, Any] | None = None) -> None:
    raise StaffReadyError(
        "Staff-ready UX refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_payload: dict[str, Any] | None = None) -> None:
    raise StaffReadyError(
        "Staff-ready UX refuses inventing READY.",
        code="ready_refused",
    )


def refuse_money(_payload: dict[str, Any] | None = None) -> None:
    raise StaffReadyError(
        "Staff-ready UX has no money, payment, bank, or folio action.",
        code="money_refused",
    )


def refuse_production(_payload: dict[str, Any] | None = None) -> None:
    raise StaffReadyError(
        "Staff-ready UX refuses Production mutate.",
        code="production_refused",
    )


def human_person(person_id: str | None) -> str:
    pid = (person_id or "").strip()
    if not pid:
        return "Unassigned"
    return PERSON_LABELS.get(pid, pid if not pid.startswith("PERS-") else pid.replace("PERS-", "").title())


def human_stage(key: str | None) -> str:
    k = (key or "").strip()
    if not k:
        return "Not started"
    return STAGE_LABELS.get(k, k.replace("_", " ").strip().title())


def human_lifecycle(stage: str | None) -> str:
    s = (stage or "").strip().upper()
    return LIFECYCLE_LABELS.get(s, s.title() if s else "Unknown")


def human_seat(seat: str | None) -> str:
    s = (seat or "").strip()
    return SEAT_LABELS.get(s, s.replace("_", " ").title() if s else "Seat")


def empty_with_next(
    message: str,
    *,
    next_label: str,
    next_href: str | None = None,
    next_code: str = "act",
) -> dict[str, Any]:
    """Blank empty that always carries a next action — never a dead end."""
    return {
        "empty": True,
        "message": message,
        "next_action": {
            "code": next_code,
            "label": next_label,
            "href": next_href,
            "invented": False,
        },
    }


def phone_nav(pack: str) -> list[dict[str, str]]:
    """Single phone nav per pack — no duplicate strips."""
    p = (pack or "").strip().lower()
    if p == "ggv":
        return [
            {"id": "now", "label": "Now", "href": "#now"},
            {"id": "loop", "label": "Leads", "href": "#loop"},
            {"id": "content", "label": "Content", "href": "#content"},
            {"id": "history", "label": "History", "href": "#history"},
        ]
    if p == "amg":
        return [
            {"id": "now", "label": "Now", "href": "#now"},
            {"id": "day", "label": "Day", "href": "#day"},
            {"id": "today", "label": "Slots", "href": "#today"},
            {"id": "handover", "label": "Handover", "href": "#handover"},
            {"id": "history", "label": "History", "href": "#history"},
        ]
    if p == "bzg":
        return [
            {"id": "today", "label": "Today", "href": "/bzg/uma-blu"},
            {"id": "bills", "label": "Bills", "href": "/bzg/uma-blu/bills"},
            {"id": "petty", "label": "Petty", "href": "/bzg/uma-blu/petty"},
            {"id": "close", "label": "Close", "href": "/uma-blu-close"},
            {"id": "issues", "label": "Issues", "href": "/bzg/uma-blu/issues"},
            {"id": "history", "label": "History", "href": "/bzg/uma-blu#history"},
        ]
    raise StaffReadyError(f"Unknown pack for phone nav: {pack}", code="unknown_pack")


def exposed_actions_ggv(seat: dict[str, Any] | None) -> dict[str, Any]:
    """Which operator actions to expose vs hide for this GGV seat."""
    s = seat or {}
    can_close = bool(s.get("can_close"))
    can_read = bool(s.get("can_read", True))
    lifecycle = list(s.get("lifecycle") or [])
    return {
        "update_lifecycle": can_read and bool(lifecycle),
        "close_lead": can_close,
        "note_contact": can_read,
        "qualify": can_read,
        "assign_owner": can_read,
        "record_engagement": can_read,
        "raise_exception": can_read,
        "lead_operator": can_read,
        "record_next_action": can_read,
        "record_note": can_read,
        "ownership_touch": can_read,
        "show_owner_matrix": (s.get("seat") == "owner" or s.get("person_id") == "PERS-MATT"),
        "show_seats_panel": False,  # developer matrix — never staff-facing
        "lifecycle_options": [human_lifecycle(x) for x in lifecycle],
        "lifecycle_values": lifecycle,
    }


def exposed_actions_amg(seat: dict[str, Any] | None) -> dict[str, Any]:
    s = seat or {}
    assigned = s.get("assigned") is not False
    is_owner = s.get("person_id") == "PERS-MATT" or s.get("seat") == "owner"
    return {
        "open_day_object": assigned,
        "mark_day_done": assigned,
        "raise_exception": assigned,
        "save_note": assigned,
        "mark_look": assigned,
        "open_journey": assigned,
        "save_handoff": assigned,
        "show_owner_visibility": is_owner,
        "show_seats_panel": False,
        "waiting_assignment": not assigned,
    }


def exposed_actions_bzg(permissions: dict[str, Any] | None) -> dict[str, Any]:
    perm = permissions or {}
    view = str(perm.get("view") or "")
    return {
        "show_owner_copy": view == "owner",
        "show_operator_actions": view in {"owner", "operator", ""},
        "hide_unusable_buttons": True,
        "payment_on_screen": False,
    }


def _history_rows_from_events(events: list[dict[str, Any]], *, limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in events[:limit]:
        rows.append(
            {
                "when": ev.get("when") or ev.get("at") or ev.get("updated_at") or "",
                "sentence": ev.get("sentence")
                or ev.get("label")
                or ev.get("title")
                or ev.get("note")
                or ev.get("body")
                or "Recorded",
                "kind": ev.get("kind") or ev.get("event_type") or "event",
                "evidence": bool(ev.get("evidence") or ev.get("legacy") or ev.get("object_id")),
            }
        )
    return rows


def history_evidence_handover_ggv(board: dict[str, Any]) -> dict[str, Any]:
    """Compose history / evidence / handover from live board — no invent."""
    leads = list(board.get("leads") or [])
    mgmt = (board.get("management_exceptions") or {}).get("exceptions") or []
    history: list[dict[str, Any]] = []
    for lead in leads:
        nxt = lead.get("recorded_next_action")
        if nxt:
            history.append(
                {
                    "when": "",
                    "sentence": f"{lead.get('demo_label') or lead.get('lead_id')}: {nxt}",
                    "kind": "next_action",
                    "evidence": True,
                }
            )
        loop = lead.get("loop") or {}
        stages = loop.get("stages") or {}
        for key, st in stages.items():
            status = (st or {}).get("status") if isinstance(st, dict) else st
            if status in {"done", "read", "raised", "due"}:
                history.append(
                    {
                        "when": "",
                        "sentence": f"{human_stage(key)} — {human_stage(str(status))}",
                        "kind": "loop_stage",
                        "evidence": True,
                    }
                )
    for row in mgmt:
        history.append(
            {
                "when": "",
                "sentence": f"Needs management: {row.get('demo_label') or row.get('lead_id')}",
                "kind": "mgmt",
                "evidence": True,
            }
        )
    history = history[:20]
    empty = empty_with_next(
        "No Habitat history on this board yet.",
        next_label="Open a lead and record the next step",
        next_href="#loop",
        next_code="record_next",
    )
    handover = {
        "ok": True,
        "items": [
            {
                "kind": "shift",
                "note": (
                    (board.get("leads") or [{}])[0].get("recorded_next_action")
                    if leads
                    else None
                ),
                "label": "What the next person should do",
            }
        ]
        if leads and (leads[0].get("recorded_next_action"))
        else [],
        "empty": not (leads and leads[0].get("recorded_next_action")),
        "why": "Handover is the recorded next step on the top lead. Empty is not a sale.",
    }
    if handover["empty"]:
        handover["empty_state"] = empty_with_next(
            "No handover note yet.",
            next_label="Record a next step on a lead",
            next_href="#loop",
            next_code="handover_next",
        )
    return {
        "ok": True,
        "history": history,
        "history_empty": len(history) == 0,
        "history_empty_state": empty if not history else None,
        "evidence_count": sum(1 for h in history if h.get("evidence")),
        "handover": handover,
        "invented": False,
    }


def history_evidence_handover_amg(board: dict[str, Any]) -> dict[str, Any]:
    day = board.get("day_loop") or {}
    items = list(day.get("items") or [])
    hands = list((board.get("handoff") or {}).get("items") or [])
    notes = list((board.get("today") or {}).get("notes") or [])
    history: list[dict[str, Any]] = []
    for item in items:
        history.append(
            {
                "when": item.get("updated_at") or item.get("opened_at") or "",
                "sentence": f"{item.get('label') or item.get('kind')}: {item.get('title')}",
                "kind": item.get("kind") or "day",
                "evidence": True,
            }
        )
    for note in notes:
        history.append(
            {
                "when": note.get("updated_at") or "",
                "sentence": note.get("body") or "Desk note",
                "kind": "note",
                "evidence": True,
            }
        )
    for hand in hands:
        history.append(
            {
                "when": hand.get("updated_at") or "",
                "sentence": hand.get("note") or "Shift handoff",
                "kind": "handover",
                "evidence": True,
            }
        )
    history = history[:20]
    empty = empty_with_next(
        "No Atrium desk history yet.",
        next_label="Open a day object or save a handoff",
        next_href="#day",
        next_code="open_day",
    )
    handover = {
        "ok": True,
        "items": hands,
        "empty": len(hands) == 0,
        "why": "A handoff is a note to the next shift. It is not a review score.",
    }
    if handover["empty"]:
        handover["empty_state"] = empty_with_next(
            "No shift handoff yet.",
            next_label="Write what the next shift should carry",
            next_href="#handover",
            next_code="save_handoff",
        )
    return {
        "ok": True,
        "history": history,
        "history_empty": len(history) == 0,
        "history_empty_state": empty if not history else None,
        "evidence_count": sum(1 for h in history if h.get("evidence")),
        "handover": handover,
        "invented": False,
        "hotel_facts_invented": False,
    }


def history_evidence_handover_bzg(today: dict[str, Any]) -> dict[str, Any]:
    closes = (today.get("previous_closes") or {}).get("closes") or []
    history: list[dict[str, Any]] = []
    for cl in closes[:12]:
        history.append(
            {
                "when": cl.get("business_date") or "",
                "sentence": f"Close — {cl.get('state') or 'recorded'}",
                "kind": "close",
                "evidence": True,
            }
        )
    empty = empty_with_next(
        "No earlier closes recorded in Wolf yet.",
        next_label="Open Daily Close",
        next_href="/uma-blu-close",
        next_code="open_close",
    )
    now = today.get("now") or {}
    handover_note = now.get("why") or now.get("waiting_copy") or (now.get("next_action") or {}).get("label")
    handover = {
        "ok": True,
        "items": (
            [{"kind": "today", "note": handover_note, "label": "What needs you now"}]
            if handover_note
            else []
        ),
        "empty": not bool(handover_note),
        "why": "Handover is what needs you now on Uma Blu Today.",
    }
    if handover["empty"]:
        handover["empty_state"] = empty_with_next(
            "Nothing to hand over right now.",
            next_label="Check Bills or Petty",
            next_href="/bzg/uma-blu/bills",
            next_code="check_bills",
        )
    return {
        "ok": True,
        "history": history,
        "history_empty": len(history) == 0,
        "history_empty_state": empty if not history else None,
        "evidence_count": sum(1 for h in history if h.get("evidence")),
        "handover": handover,
        "invented": False,
    }


def primary_next_ggv(board: dict[str, Any]) -> dict[str, Any]:
    leads = list(board.get("leads") or [])
    mgmt = (board.get("management_exceptions") or {}).get("exceptions") or []
    if mgmt:
        row = mgmt[0]
        return {
            "code": "mgmt",
            "label": f"Handle management exception: {row.get('demo_label') or row.get('lead_id')}",
            "href": "#now",
            "invented": False,
        }
    for lead in leads:
        loop_next = lead.get("loop_next_action") or {}
        if isinstance(loop_next, dict) and loop_next.get("label"):
            return {
                "code": loop_next.get("code") or "loop",
                "label": str(loop_next["label"]),
                "href": "#loop",
                "invented": False,
            }
        if lead.get("recorded_next_action"):
            return {
                "code": "recorded",
                "label": str(lead["recorded_next_action"]),
                "href": "#loop",
                "invented": False,
            }
    return {
        "code": "empty_board",
        "label": "No Habitat lead needs you — check Content or wait for a new lead",
        "href": "#content",
        "invented": False,
    }


def primary_next_amg(board: dict[str, Any]) -> dict[str, Any]:
    day = board.get("day_loop") or {}
    nxt = day.get("day_next_action") or {}
    if isinstance(nxt, dict) and nxt.get("label"):
        return {
            "code": nxt.get("code") or "day",
            "label": str(nxt["label"]),
            "href": "#day",
            "invented": False,
        }
    seat = board.get("seat") or {}
    if seat.get("assigned") is False:
        return {
            "code": "waiting_assignment",
            "label": "Waiting for hotel-ops assignment — Owner must assign a seat",
            "href": "#now",
            "invented": False,
        }
    return {
        "code": "open_day",
        "label": "Open a day object (housekeeping, maintenance, incident, recovery, or handover)",
        "href": "#day",
        "invented": False,
    }


def primary_next_bzg(today: dict[str, Any]) -> dict[str, Any]:
    nxt = today.get("next_action") or {}
    if isinstance(nxt, dict) and nxt.get("label"):
        return {
            "code": nxt.get("code") or "today",
            "label": str(nxt["label"]),
            "href": (today.get("now") or {}).get("href") or "/bzg/uma-blu",
            "invented": False,
        }
    now = today.get("now") or {}
    if now.get("title"):
        return {
            "code": str(now.get("kind") or "now"),
            "label": str(now["title"]),
            "href": now.get("href") or "/bzg/uma-blu",
            "invented": False,
        }
    return {
        "code": "idle",
        "label": "Nothing live needs you — check History or earlier closes",
        "href": "#history",
        "invented": False,
    }


def staff_surface_ggv(board: dict[str, Any]) -> dict[str, Any]:
    seat = board.get("seat") or {}
    heh = history_evidence_handover_ggv(board)
    nxt = primary_next_ggv(board)
    leads_empty = not list(board.get("leads") or [])
    return {
        "ok": True,
        "pack": "ggv",
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "phone_nav": phone_nav("ggv"),
        "nav_duplicate": False,
        "lede": "Habitat desk. Record the next step. Closed is not a sale.",
        "who_line": f"{human_seat(seat.get('seat'))} · {human_person(seat.get('person_id'))} · Habitat",
        "primary_next": nxt,
        "exposed_actions": exposed_actions_ggv(seat),
        "terminology": {
            "person_labels": PERSON_LABELS,
            "stage_labels": STAGE_LABELS,
            "lifecycle_labels": LIFECYCLE_LABELS,
        },
        "empty_states": {
            "leads": empty_with_next(
                "No Habitat leads on this board.",
                next_label="Check Content gate or wait — Wolf does not invent leads",
                next_href="#content",
                next_code="wait_leads",
            )
            if leads_empty
            else None,
            "mgmt": empty_with_next(
                (board.get("management_exceptions") or {}).get("empty_message")
                or "No management exception.",
                next_label=nxt["label"],
                next_href=nxt.get("href"),
                next_code="mgmt_idle",
            )
            if (board.get("management_exceptions") or {}).get("empty")
            else None,
            "client_visibility": empty_with_next(
                "Client visibility is empty. Empty is not live profitability.",
                next_label="Stay on the lead loop — do not invent a client report",
                next_href="#loop",
                next_code="client_empty",
            ),
            "performance": empty_with_next(
                (board.get("performance") or {}).get("why")
                or "Performance read is empty. Empty is not zero.",
                next_label="Open Content to see publish-gate status",
                next_href="#content",
                next_code="perf_empty",
            )
            if not (board.get("performance") or {}).get("available")
            else None,
        },
        "history_evidence_handover": heh,
        "dead_buttons": [],  # UI must not render actions outside exposed_actions
        "honesty": dict(HONESTY),
        "pack_honesty_ref": (board.get("honesty") or {}).get("ledger_maturity"),
        "dev_tokens_forbidden_in_staff_copy": list(DEV_TOKENS),
    }


def staff_surface_amg(board: dict[str, Any]) -> dict[str, Any]:
    seat = board.get("seat") or {}
    heh = history_evidence_handover_amg(board)
    nxt = primary_next_amg(board)
    day = board.get("day_loop") or {}
    day_empty = not list(day.get("items") or [])
    return {
        "ok": True,
        "pack": "amg",
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "phone_nav": phone_nav("amg"),
        "nav_duplicate": False,
        "lede": "Atrium desk. Day objects and shift handoff. Not hotel occupancy.",
        "who_line": (
            f"{human_seat(seat.get('seat'))} · {human_person(seat.get('person_id'))} · Atrium"
            if seat.get("assigned") is not False
            else "Waiting for hotel-ops assignment"
        ),
        "primary_next": nxt,
        "exposed_actions": exposed_actions_amg(seat),
        "terminology": {
            "person_labels": PERSON_LABELS,
            "day_kinds": {
                "housekeeping": "Housekeeping",
                "maintenance": "Maintenance",
                "incident": "Incident",
                "service_recovery": "Service recovery",
                "handover": "Shift handover",
            },
        },
        "empty_states": {
            "day": empty_with_next(
                day.get("why") or "No day-loop object yet.",
                next_label=nxt["label"],
                next_href="#day",
                next_code="day_empty",
            )
            if day_empty
            else None,
            "notes": empty_with_next(
                "No desk note yet.",
                next_label="Write what the next person should know",
                next_href="#today",
                next_code="note_empty",
            ),
            "journey": empty_with_next(
                (board.get("journey") or {}).get("why") or "No journey item for today.",
                next_label="Open a journey task if needed — it is not a booking",
                next_href="#today",
                next_code="journey_empty",
            )
            if not list((board.get("journey") or {}).get("items") or [])
            else None,
            "sla": empty_with_next(
                "Open incident list is empty. Empty is not an SLA timer.",
                next_label="Open an incident day object if something needs tracking",
                next_href="#day",
                next_code="sla_empty",
            ),
        },
        "history_evidence_handover": heh,
        "dead_buttons": [],
        "honesty": dict(HONESTY),
        "pack_honesty_ref": (board.get("honesty") or {}).get("ledger_maturity"),
        "dev_tokens_forbidden_in_staff_copy": list(DEV_TOKENS),
    }


def staff_surface_bzg(today: dict[str, Any]) -> dict[str, Any]:
    heh = history_evidence_handover_bzg(today)
    nxt = primary_next_bzg(today)
    perm = today.get("permissions") or {}
    return {
        "ok": True,
        "pack": "bzg",
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "phone_nav": phone_nav("bzg"),
        "nav_duplicate": False,
        "lede": "Uma Blu Today. What needs you — payment is not on this screen.",
        "who_line": None,
        "primary_next": nxt,
        "exposed_actions": exposed_actions_bzg(perm),
        "terminology": {"person_labels": PERSON_LABELS},
        "empty_states": {
            "now": empty_with_next(
                "Nothing live needs you right now.",
                next_label="Check History or earlier closes",
                next_href="#history",
                next_code="now_idle",
            )
            if not today.get("now")
            else None,
            "history": heh.get("history_empty_state"),
        },
        "history_evidence_handover": heh,
        "dead_buttons": [],
        "honesty": dict(HONESTY),
        "dev_tokens_forbidden_in_staff_copy": list(DEV_TOKENS),
    }


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "packs": ["bzg", "ggv", "amg"],
        "phone_first": True,
        "additionalProperties": False,
        "proven_property": False,
        "ready_property": False,
        "money_property": False,
    }


def staff_ready_board(
    *,
    pack: str,
    board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Top-level staff-ready read for one pack board payload."""
    p = (pack or "").strip().lower()
    data = board or {}
    if p == "ggv":
        surface = staff_surface_ggv(data)
    elif p == "amg":
        surface = staff_surface_amg(data)
    elif p == "bzg":
        surface = staff_surface_bzg(data)
    else:
        raise StaffReadyError(f"Unknown pack: {pack}", code="unknown_pack")
    return {
        "ok": True,
        "bound": BOUND,
        "schema": schema_document(),
        "staff_ready": surface,
        "honesty": honesty_flags(),
    }
