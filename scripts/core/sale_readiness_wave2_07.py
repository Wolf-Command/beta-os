#!/usr/bin/env python3
"""Wave 2.07 — Sale readiness honesty. Not a buyer data room.

CAP-SALE-01 is a system checklist. CAP-SALE-02 names empty folders.
Neither writes a document, a buyer, or a share. This desk does not
fill those slots.
"""
from __future__ import annotations

import re
from typing import Any

from core import sale_buyer_dataroom as room
from core import sale_evidence_pack as evidence

PAGE = evidence.BETA_ROOT / "dashboards" / "sale-evidence-pack.html"


def _domains(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "control_count": row.get("control_count"),
                "empty_controls": row.get("empty_controls"),
                "filled_controls": row.get("filled_controls"),
                "slot": row.get("slot"),
                "evidence": None,
            }
        )
    return out


def _page() -> dict[str, Any]:
    if not PAGE.is_file():
        return {"present": False, "page_type": None, "why": "sale-evidence-pack.html is missing."}
    text = PAGE.read_text(encoding="utf-8", errors="replace")
    kind = re.search(r'data-wolf-page-type="([^"]+)"', text)
    title = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    return {
        "present": True,
        "file": "dashboards/sale-evidence-pack.html",
        "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else None,
        "page_type": kind.group(1) if kind else None,
        "nav_says_sale_readiness": "Sale Readiness" in text,
        "buyer_data_room": False,
        "why": "The route is a system page. The nav label is not a buyer data room.",
    }


def load_readiness() -> dict[str, Any]:
    pack = evidence.build_pack()
    built = room.build_room()
    honesty = pack.get("honesty") or {}
    room_honesty = built.get("honesty") or {}
    unmapped = pack.get("unmapped") or {}
    gaps = _domains(pack.get("domains") or [])
    gaps.append(
        {
            "id": unmapped.get("domain"),
            "name": "Unmapped",
            "control_count": unmapped.get("control_count"),
            "empty_controls": unmapped.get("empty_controls"),
            "filled_controls": unmapped.get("filled_controls"),
            "slot": unmapped.get("slot"),
            "evidence": None,
        }
    )
    return {
        "ok": True,
        "pack": "WAVE2-07",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "sale_ready": False,
        "buyer_data_room": False,
        "state": "SHELL",
        "system_page": _page(),
        "evidence_pack": {
            "cap": pack.get("cap"),
            "controls_read": pack.get("controls_read"),
            "controls_expected": pack.get("controls_expected"),
            "control_list_matches_canon": pack.get("control_list_matches_canon"),
            "empty_slots": pack.get("empty_slots"),
            "filled_slots": pack.get("filled_slots"),
            "framework_skeleton": pack.get("framework_skeleton"),
            "maturity": honesty.get("maturity"),
            "maturity_ceiling": honesty.get("maturity_ceiling"),
            "proven": honesty.get("proven"),
            "ready": honesty.get("ready"),
            "cr_id": honesty.get("cr_id"),
            "cr_state": honesty.get("cr_state"),
            "buyer_export": False,
            "vdr_export": False,
            "evidence_invented": False,
        },
        "data_room": {
            "cap": built.get("cap"),
            "on_disk": built.get("on_disk"),
            "document_count": built.get("document_count"),
            "buyer_count": built.get("buyer_count"),
            "buyer_access": built.get("buyer_access"),
            "live_share": built.get("live_share"),
            "empty_slots": built.get("empty_slots"),
            "filled_slots": built.get("filled_slots"),
            "maturity": room_honesty.get("maturity"),
            "proven": room_honesty.get("proven"),
            "ready": room_honesty.get("ready"),
            "documents_invented": False,
        },
        "gaps": gaps,
        "why": "A system checklist with empty slots is not a buyer data room.",
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "sale_ready": False,
        "buyer_data_room": False,
        "message": "Sale readiness does not write a document, a buyer, or a data room.",
    }
