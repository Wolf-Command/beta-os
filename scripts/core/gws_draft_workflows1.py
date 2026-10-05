#!/usr/bin/env python3
"""WIRE-GWS-DRAFT-WORKFLOWS-1 (light) — Gmail/Drive/Calendar honesty for Beta.

Policy:
  - Gmail = create_draft ONLY (never send_message)
  - Drive / Calendar = READ via authorised MCP paths
  - No invent of message/event/file counts into Owner claims
  - Documents which Wolf surfaces consume GWS vs still stub

This module is a stamp + refuse surface. It does not call Google APIs from
Beta process (MCP is the authorised path for Peaches/executor).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")
PACK = "WIRE-GWS-DRAFT-WORKFLOWS-1"
WORKFLOW_PACK = "WORKFLOW-GWS-OWNER-CARD-1"
SCHEMA = "wolf.gws-draft-workflows-1.v1"
WORKFLOW_SCHEMA = "wolf.workflow-gws-owner-card-1.v1"


def _now() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


# Surfaces that may consume authorised MCP reads / draft-only.
CONSUMING: list[dict[str, Any]] = [
    {
        "surface": "Peaches executor / MCP user-Gmail",
        "system": "Gmail",
        "mode": "READ+DRAFT",
        "allowed": ["list_labels", "list_drafts", "get_thread", "search_threads", "create_draft", "update_draft"],
        "forbidden": ["send_message", "forward", "trash_message", "trash_thread"],
        "status": "MCP_LIVE",
        "note": "Draft-only YES; send NO. Executor must never call send_message.",
    },
    {
        "surface": "Peaches executor / MCP user-Google-drive",
        "system": "Drive",
        "mode": "READ",
        "allowed": ["list_recent_files", "search_files", "read_file_content", "get_file_metadata"],
        "forbidden": ["create_file", "update_file", "trash_file", "share_file"],
        "status": "MCP_LIVE",
        "note": "READ into Wolf desks; write stays NO default this mission.",
    },
    {
        "surface": "Peaches executor / MCP user-Google-calendar",
        "system": "Calendar",
        "mode": "READ",
        "allowed": ["list_calendars", "list_events", "get_event", "search_events"],
        "forbidden": ["create_event", "update_event", "delete_event"],
        "status": "MCP_LIVE",
        "note": "READ; create/update NO default this mission.",
    },
    {
        "surface": "Owner Home pulse tile gws_workflow",
        "system": "GWS",
        "mode": "POLICY_CARD",
        "allowed": ["load_gws_ro stamp into pulse"],
        "forbidden": ["invent message/event/file counts", "send_message", "drive_write", "calendar_write"],
        "status": "PULSE_CONSUMING",
        "note": "WORKFLOW-GWS-OWNER-CARD-1: visible Owner desk card. No invented GWS counts.",
    },
]

# Beta in-process surfaces that still stub / do not call GWS.
STILL_STUB: list[dict[str, Any]] = [
    {
        "surface": "gws_integrate_prove.py",
        "system": "Gmail/Drive/Calendar",
        "status": "STUB_NAME_ONLY",
        "note": "Names surfaces; does not probe or count messages/events/files.",
    },
    {
        "surface": "/api/owner-pool/email-drafts/*/send",
        "system": "Gmail",
        "status": "SEND_REFUSED",
        "note": "Send path exists in atrium_full_mount wall list — keep refused / Owner-gated.",
    },
    {
        "surface": "sop_factory create_draft",
        "system": "internal",
        "status": "NOT_GWS",
        "note": "SOP draft is internal Wolf draft, not Gmail create_draft.",
    },
]


def refuse_gmail_send(_body: dict | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "refused": True,
        "code": "gmail_send_refused",
        "message": "Gmail send_message is refused. Draft-only. Owner gate required for send.",
        "pack": PACK,
    }


def refuse_drive_write(_body: dict | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "refused": True,
        "code": "drive_write_refused",
        "message": "Drive write refused on Beta GWS light wire. READ only.",
        "pack": PACK,
    }


def refuse_calendar_write(_body: dict | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "refused": True,
        "code": "calendar_write_refused",
        "message": "Calendar create/update refused on Beta GWS light wire. READ only.",
        "pack": PACK,
    }


def load_gws_ro() -> dict[str, Any]:
    """Honesty stamp for Owner / INTG — no live Google counts invented here."""
    return {
        "ok": True,
        "reason": "GWS_DRAFT_WORKFLOWS_LIGHT",
        "staff_ready": False,
        "human_commissioned": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "read_only": True,
        "as_of_wita": _now(),
        "surface": "owner/gws-ro",
        "pack": PACK,
        "schema": SCHEMA,
        "gmail_policy": "DRAFT_ONLY",
        "gmail_send": False,
        "drive_write": False,
        "calendar_write": False,
        "consuming": CONSUMING,
        "still_stub": STILL_STUB,
        "honesty": (
            "GWS MCP paths are LIVE for Peaches executor READ (+ Gmail draft). "
            "Beta in-process gws_integrate_prove remains name-only stub. "
            "Owner pulse shows POLICY_CARD only — no invented message/event/file counts."
        ),
        "mcp_servers": [
            "user-Gmail",
            "user-Google-drive",
            "user-Google-calendar",
        ],
        "owner_workflow_card": {
            "pack": WORKFLOW_PACK,
            "schema": WORKFLOW_SCHEMA,
            "pulse_tile_id": "gws_workflow",
            "visible": True,
            "gmail_policy": "DRAFT_ONLY",
            "gmail_send": False,
            "drive_write": False,
            "calendar_write": False,
            "invented_counts": False,
            "desk_href": "/api/owner/gws-ro",
            "note": "Binds LIVE MCP policy stamp into Owner Home pulse without inventing data.",
        },
        "workflow_pack": WORKFLOW_PACK,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(load_gws_ro(), indent=2))
