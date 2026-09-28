#!/usr/bin/env python3
"""Role dashboard — one staff projection for /my-work.

Decision served: owner brief 27 Sep 2026, PACK 3. Extends the staff home.
Not a second task or approval database.

Person is the greeting only. The page follows Role, Assignment, Scope,
Permission, and Audience. A replacement with the same role and the same
scopes gets the same page. No performance figure is invented.
"""
from __future__ import annotations

from typing import Any

REPRESENTATIVES: dict[str, str] = {
    "creative_director": "creative_director",
    "content_creator": "content_creator",
    "bzg_fb_ops": "bzg_fb_ops",
    "finance": "external_accountant",
    "atrium_finance": "atrium_finance_officer",
    "closer": "closer",
    "manager": "manager",
    "owner_pulse": "owner",
    "staff": "staff",
}

# The catalog has one finance seat. Both brief names point at it.
_FINANCE_ALIASES = ("finance", "external_accountant")


def audience_for(role_id: str | None, person_id: str | None) -> str:
    """Audience from the role. Known people keep the shell's existing map."""
    from core import wolf_shell as shell

    role = str(role_id or "")
    mapped = shell.ROLE_AUDIENCE.get(role)
    if mapped:
        return mapped
    return shell.audience_for_person(person_id)


def _truth() -> dict[str, Any]:
    try:
        from core import dashboard_truth as truth

        stamp = truth.stamp("my-work")
        core = next(
            (row for row in (stamp.get("sources") or []) if row.get("source_id") == "wolf_core"),
            None,
        )
        if not core:
            raise RuntimeError("wolf core stamp missing")
        state = str(core.get("display_state") or "UNKNOWN")
        shown = bool(core.get("shown_as_current"))
        if state in {"STALE", "UNAVAILABLE", "UNKNOWN"}:
            shown = False
        return {
            "surface": "my-work",
            "display_state": state,
            "shown_as_current": shown,
            "staff_ready": False,
            "human_commissioned": False,
        }
    except Exception:
        return {
            "surface": "my-work",
            "display_state": "UNAVAILABLE",
            "shown_as_current": False,
            "staff_ready": False,
            "human_commissioned": False,
        }


def _by_key(sections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("key") or ""): row for row in sections}


def _items(section: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not section:
        return []
    return [dict(item) for item in (section.get("items") or [])]


def _block(
    key: str,
    title: str,
    *,
    prompt: str | None,
    items: list[dict[str, Any]],
    empty_message: str,
    parts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "key": key,
        "title": title,
        "prompt": prompt,
        "show": True,
        "empty": not items,
        "empty_message": None if items else empty_message,
        "items": items,
    }
    if parts:
        row["parts"] = parts
        row["empty"] = not any(part.get("items") for part in parts) and not items
    return row


def _part(prompt: str, section: dict[str, Any] | None, empty_message: str) -> dict[str, Any]:
    items = _items(section)
    return {
        "prompt": prompt,
        "empty": not items,
        "empty_message": None if items else (section or {}).get("empty_message") or empty_message,
        "items": items,
    }


def _desk_items(desk: list[dict[str, str]]) -> list[dict[str, str]]:
    items = []
    for link in desk:
        href = str(link.get("href") or "").strip()
        label = str(link.get("label") or "").strip()
        if not href or not label:
            continue
        items.append({"id": href, "title": label, "href": href})
    return items


def _responsibilities(
    *,
    experience: str,
    role_label: str,
    covers: list[str],
    boundary: str | None,
    authority: dict[str, Any] | None,
    money: dict[str, Any] | None,
) -> dict[str, Any]:
    if experience == "owner_pulse":
        lines = [
            "The daily picture stays with the Owner.",
            "Payment, bank changes, and exception decisions stay with the Owner.",
        ]
    else:
        lines = []
        if role_label:
            lines.append(f"You are the {role_label}.")
        if covers:
            lines.append("This covers " + ", ".join(covers) + ".")
        if boundary:
            lines.append(boundary)
        elif authority and not (
            authority.get("move_money") or authority.get("change_bank") or authority.get("authorise_governance")
        ):
            lines.append("You cannot pay, change a bank account, or change a governance rule.")
    items = [{"id": f"duty-{index}", "title": line} for index, line in enumerate(lines, start=1)]
    parts = [
        {
            "prompt": "My responsibilities",
            "empty": not items,
            "empty_message": None if items else "No responsibilities are on this assignment.",
            "items": items,
        }
    ]
    if money is not None:
        parts.append(_part("Money or control at risk", money, "Nothing on record is flagged as money or control at risk."))
        items = items + _items(money)
    return {
        "key": "responsibilities",
        "title": "My responsibilities",
        "prompt": None,
        "show": True,
        "empty": not items,
        "empty_message": None if items else "No responsibilities are on this assignment.",
        "items": items,
        "parts": parts,
        "performance": {
            "state": "MISSING",
            "message": "No performance figure is on record.",
            "shown_as_score": False,
        },
    }


def project(
    *,
    experience: str,
    role_id: str | None,
    role_label: str,
    covers: list[str],
    desk: list[dict[str, str]],
    boundary: str | None,
    sections: list[dict[str, Any]],
    audience: str,
    authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Framework sections. Does not read or write the catalog itself."""
    by = _by_key(sections)
    representative = REPRESENTATIVES.get(experience, "staff")
    if experience == "owner_pulse":
        wrong = _part("What's wrong", by.get("wrong"), "Nothing is marked wrong.")
        blocked = _part("What's blocked", by.get("blocked"), "Nothing is blocked.")
        attention_items = list(wrong["items"]) + list(blocked["items"])
        blocks = [
            _block(
                "today",
                "Today",
                prompt="What's happening",
                items=_items(by.get("happening")),
                empty_message=(by.get("happening") or {}).get("empty_message") or "Nothing open is on record.",
            ),
            _block(
                "do_this",
                "Do this",
                prompt="What needs your decision",
                items=_items(by.get("authority")),
                empty_message=(by.get("authority") or {}).get("empty_message") or "Nothing is waiting for your decision.",
            ),
            _block(
                "attention",
                "Needs attention",
                prompt=None,
                items=attention_items,
                empty_message="Nothing is marked wrong.",
                parts=[wrong, blocked],
            ),
            _block(
                "waiting",
                "Waiting",
                prompt="What am I waiting for?",
                items=[],
                empty_message="You are not waiting on anyone.",
            ),
            _block(
                "completed",
                "Recently completed",
                prompt="What improved",
                items=_items(by.get("improving")),
                empty_message=(by.get("improving") or {}).get("empty_message") or "Nothing new has been completed.",
            ),
            _responsibilities(
                experience=experience,
                role_label=role_label,
                covers=covers,
                boundary=boundary,
                authority=authority,
                money=by.get("money"),
            ),
        ]
    else:
        today = by.get("today") or {}
        attention = by.get("attention") or {}
        waiting = by.get("waiting") or {}
        completed = by.get("completed") or {}
        desk_items = _desk_items(desk)
        blocks = [
            _block(
                "today",
                "Today",
                prompt=str(today.get("title") or "What do I need to do today?"),
                items=_items(today),
                empty_message=str(today.get("empty_message") or "Nothing is assigned to you for today."),
            ),
            _block(
                "do_this",
                "Do this",
                prompt=None,
                items=desk_items,
                empty_message="Nothing else to open from here.",
            ),
            _block(
                "attention",
                "Needs attention",
                prompt=str(attention.get("title") or "What needs my attention?"),
                items=_items(attention),
                empty_message=str(attention.get("empty_message") or "Nothing needs your attention."),
            ),
            _block(
                "waiting",
                "Waiting",
                prompt=str(waiting.get("title") or "What am I waiting for?"),
                items=_items(waiting),
                empty_message=str(waiting.get("empty_message") or "You are not waiting on anyone."),
            ),
            _block(
                "completed",
                "Recently completed",
                prompt=str(completed.get("title") or "What did I recently complete?"),
                items=_items(completed),
                empty_message=str(completed.get("empty_message") or "Nothing completed recently."),
            ),
            _responsibilities(
                experience=experience,
                role_label=role_label,
                covers=covers,
                boundary=boundary,
                authority=authority,
                money=None,
            ),
        ]
    aliases = list(_FINANCE_ALIASES) if representative == "external_accountant" else []
    return {
        "ok": True,
        "representative": representative,
        "also_represents": aliases,
        "role_id": role_id,
        "role_label": role_label,
        "audience": audience,
        "sections": blocks,
        "truth": _truth(),
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
    }
