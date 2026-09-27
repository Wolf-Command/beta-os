#!/usr/bin/env python3
"""GGV Content Machine x NAS — Haikal operator prep (engineering only).

Decision served: Owner Connection Commissioning READ/WRITE package APPROVED
2026-09-22 (ClickUp/Telegram RETIRED); RULE-Wolf-Connection-Commissioning-
NAS-GoLive-2026-09-22; extends NAS Library Upload P0 + NAS index continue;
Content machine NAS upload pick 2026-08-22.

Bound: Beta :8788 only. Does NOT invent Haikal human PASS, CAP PROVEN/READY,
or staff_ready=true. Does NOT destroy NAS. Does NOT mutate Production.
"""
from __future__ import annotations

from typing import Any

from core import nas_library as nas
from core import wolf_shell as shell

BOUND = "beta-ggv-content-nas-haikal-prep"
SLICE = "wolf_ggv_content_nas_haikal_prep"
SCHEMA_ID = "wolf.ggv-content-nas-haikal-prep.v1"
RUN_ID = "BF-wolf-ggv-content-nas-haikal-prep-v2-20260922"
CONTENT_HREF = "/content-2.0"
CHECKLIST_DOC = (
    "docs/deliveries/WOLF-HAIKAL-NAS-LIBRARY-RETEST-CHECKLIST-2026-09-22.md"
)

HONESTY: dict[str, Any] = {
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_haikal_human_pass": False,
    "haikal_human_status": "not_started",
    "clickup_retired": True,
    "telegram_retired": True,
    "nas_destructive": False,
    "cap_ggv_01_invented_ready": False,
}

# Morning human loop — engineering artifact labels only (not a sign-off).
RETEST_STEPS: tuple[dict[str, str], ...] = (
    {
        "id": "upload",
        "label": "Upload one authorised file via Smart Upload (habitat / selo / tropik)",
        "href": "/content-2.0#upload",
    },
    {
        "id": "search",
        "label": "Search Library for the upload; confirm NAS badge + relative path",
        "href": "/content-2.0#library",
    },
    {
        "id": "preview",
        "label": "Open preview; confirm provenance shows NAS when verified",
        "href": "/content-2.0#library",
    },
    {
        "id": "select_zip",
        "label": "Select the asset and Download selected (ZIP)",
        "href": "/content-2.0#library",
    },
    {
        "id": "wrong_scope",
        "label": "Wrong brand (e.g. atrium) must deny — 403, not silent empty",
        "href": "/content-2.0",
    },
)


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def refuse_staff_ready(_payload: dict[str, Any] | None = None) -> None:
    raise ValueError(
        "GGV Content NAS Haikal prep refuses inventing staff_ready=true "
        "(engineering only; Haikal human not_started)."
    )


def refuse_haikal_human_pass(_payload: dict[str, Any] | None = None) -> None:
    raise ValueError(
        "GGV Content NAS Haikal prep refuses inventing Haikal human PASS."
    )


def _next_action(*, nas_connected: bool, can_upload: bool) -> dict[str, Any]:
    if not can_upload:
        return {
            "code": "no_upload_permission",
            "label": "This seat cannot upload — ask management for content scope.",
            "empty": True,
            "href": CONTENT_HREF,
        }
    if nas_connected:
        return {
            "code": "upload_via_smart_upload_nas",
            "label": (
                "NAS connected. Next: Smart Upload one file (authorised brand) "
                "→ Library search → preview → ZIP. Wrong brand must 403. "
                "staff_ready stays false until Haikal human submit."
            ),
            "empty": False,
            "href": f"{CONTENT_HREF}#upload",
            "nas_connected": True,
        }
    return {
        "code": "nas_not_connected",
        "label": (
            "NAS not connected — uploads stay on Beta only. "
            "Do not claim nas_received. Fix mount, then retry Smart Upload."
        ),
        "empty": True,
        "href": f"{CONTENT_HREF}#upload",
        "nas_connected": False,
    }


def empty_states(*, nas_connected: bool) -> dict[str, Any]:
    if nas_connected:
        lib_next = (
            "No assets yet. Open Smart Upload — authorised files land under "
            "_Imports/Wolf-Library. nas_received only after verify."
        )
    else:
        lib_next = (
            "No assets yet. NAS not connected — uploads stay on Beta only. "
            "We will not claim NAS received."
        )
    return {
        "library": {
            "empty": True,
            "title": "No assets",
            "next_action": lib_next,
            "href": f"{CONTENT_HREF}#upload",
        },
        "search_miss": {
            "empty": True,
            "title": "Nothing matched",
            "next_action": (
                "Try another name, or upload via Smart Upload if the file is new."
            ),
            "href": f"{CONTENT_HREF}#upload",
        },
    }


def operator_desk(
    *,
    person_id: str | None = None,
    subject: str | None = None,
    permissions: list[str] | set[str] | None = None,
    scopes: list[str] | set[str] | None = None,
    can_upload: bool | None = None,
) -> dict[str, Any]:
    """Haikal / content-crew operator path through NAS Library (honest)."""
    nas_connected = nas.media_library_connected()
    perms = set(permissions or [])
    if can_upload is None:
        can_upload = "can_upload" in perms
    else:
        can_upload = bool(can_upload)
    scope_list = list(scopes or [])
    brands = nas.brands_for_scopes(scope_list)
    next_action = _next_action(nas_connected=nas_connected, can_upload=can_upload)
    return {
        "ok": True,
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "run_id": RUN_ID,
        "surface": "content-2.0",
        "href": CONTENT_HREF,
        "person_id": person_id,
        "subject": subject,
        "nas_connected": nas_connected,
        "can_upload": can_upload,
        "allowed_brands": brands,
        "wrong_scope_example": "atrium",
        "next_action": next_action,
        "empty_states": empty_states(nas_connected=nas_connected),
        "retest_steps": [dict(s) for s in RETEST_STEPS],
        "checklist_doc": CHECKLIST_DOC,
        "wolf_write_prefix_rel": "_Imports/Wolf-Library",
        "clickup": "RETIRED",
        "telegram": "RETIRED",
        "honesty": honesty_flags(),
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "destructive": False,
        "message": next_action["label"],
    }


def ui_markers() -> dict[str, Any]:
    """Markers expected in content-2.0.html for phone + desktop."""
    return {
        "haikal_next_strip": "haikalNasNext",
        "nas_banner": "nasBanner",
        "nas_badge_token": "NAS",
        "lib_empty_next": "libEmptyNext",
        "provenance_token": "provenance",
        "zip_button": "libDownloadSel",
        "smart_upload": "Smart Upload",
    }
