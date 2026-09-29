#!/usr/bin/env python3
"""AMG-OCC-TRUTH-1 — AMG occupancy truth desk (UNKNOWN when PMS blocked).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OCC-TRUTH-1
(armed 2026-09-30 after CONN-HEALTH-BOARD-1 PASS_VERIFIED) plus 2026-09-20
PICK CAP-AMG-01 (no invent PMS / occupancy numbers). Occupancy honesty over
AMG-OS-SHELL-1. UNKNOWN/BLOCKED when Yanolja PMS blocked. Does NOT unblock
CAP-AMG-01. Never invents occupancy percent/count. staff_ready=false ·
human_commissioned=false. Ceiling BUILT. Does not auto-chain SOP-LESSON-LIVE-1
/ HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core import amg_os_shell as _shell

BETA_ROOT = __import__("pathlib").Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "AMG-OCC-TRUTH-1"
SCHEMA_ID = "wolf.amg-occ-truth-1.v1"
BOUND = "beta-amg-ops-safe"
CAP_AMG_OCC = "CAP-AMG occupancy"
CAP_AMG_01 = "CAP-AMG-01"
YANOLJA_ID = "INT-YAN-WOLF"
HONESTY_BOARD = "/ops/integrations-status"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/amg/occ-truth-1",
        "/amg/occ-truth-1/",
        "/amg/occ-truth",
        "/amg/occ-truth/",
        "/amg-occ-truth-1",
        "/amg-occ-truth-1/",
        "/amg-occ-truth",
        "/amg-occ-truth/",
        "/amg-occ-truth-1.html",
        "/dashboards/amg-occ-truth-1.html",
    }
)
API_PATH = "/api/amg/occ-truth-1"

# Occupancy honesty slots — always UNKNOWN/BLOCKED while PMS is blocked.
_OCC_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "occupancy_pct",
        "Occupancy %",
        "Waiting on Yanolja PMS. Occupancy percent UNKNOWN — never invent a rate.",
    ),
    (
        "rooms_sold",
        "Rooms sold",
        "Waiting on Yanolja PMS. Rooms-sold count UNKNOWN — not zeros-as-success.",
    ),
    (
        "rooms_available",
        "Rooms available",
        "Waiting on Yanolja PMS. Inventory UNKNOWN — not a live room count.",
    ),
    (
        "adr",
        "ADR",
        "Waiting on Yanolja PMS. ADR UNKNOWN — not a yield invent.",
    ),
    (
        "revpar",
        "RevPAR",
        "Waiting on Yanolja PMS. RevPAR UNKNOWN — not a revenue invent.",
    ),
)

PRESERVED_PACKS = ("AMG-OS-SHELL-1",)


class AmgOccTruth1Error(ValueError):
    """Fail closed. Does not invent occupancy, unblock PMS, or claim PROVEN."""

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


def _occ_slot(slot_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": slot_id,
        "label": label,
        "kind": "occupancy_dependent",
        "status": "BLOCKED_EXTERNAL",
        "blocked_external": True,
        "display": "UNKNOWN",
        "value": None,
        "occupancy_pct": None,
        "count": None,
        "amount": None,
        "yanolja_live": False,
        "pms_connected": False,
        "integration_id": YANOLJA_ID,
        "honesty_board_href": HONESTY_BOARD,
        "invented_occupancy": False,
        "why": why,
    }


def _occ_slots() -> list[dict[str, Any]]:
    return [_occ_slot(*spec) for spec in _OCC_SLOT_SPECS]


def amg_os_shell1_preserved() -> dict[str, Any]:
    """Read-only: AMG-OS-SHELL-1 still BLOCKED_EXTERNAL / UNKNOWN PMS tiles."""
    try:
        shell = _shell.build_shell()
        blocked = _shell.all_pms_tiles_blocked(shell)
        return {
            "ok": (
                blocked
                and shell.get("ok") is True
                and shell.get("staff_ready") is False
                and shell.get("human_commissioned") is False
                and shell.get("cap_amg_01_unblocked") is False
                and shell.get("fake_pms_data") is False
                and shell.get("invented_occupancy") is False
                and (shell.get("yanolja") or {}).get("audit_status") == "BLOCKED_EXTERNAL"
                and (shell.get("yanolja") or {}).get("last_success") is None
            ),
            "pms_tiles_blocked": blocked,
            "cap_amg_01_unblocked": shell.get("cap_amg_01_unblocked"),
            "fake_pms_data": shell.get("fake_pms_data"),
            "invented_occupancy": shell.get("invented_occupancy"),
            "yanolja_status": (shell.get("yanolja") or {}).get("audit_status"),
            "last_success": (shell.get("yanolja") or {}).get("last_success"),
            "why": (
                "AMG-OS-SHELL-1 preserved: PMS tiles BLOCKED_EXTERNAL / UNKNOWN, "
                "cap_amg_01_unblocked=false, no fake PMS. This pack deepens "
                "occupancy honesty over that shell — does not replace it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "AMG-OS-SHELL-1 check failed — pack must not break OS shell.",
        }


def yanolja_path_honesty() -> dict[str, Any]:
    """Reuse AMG-OS-SHELL-1 / INTG board Yanolja pin."""
    shell = _shell.build_shell()
    yan = shell.get("yanolja") or {}
    return {
        "integration_id": YANOLJA_ID,
        "audit_status": yan.get("audit_status") or "BLOCKED_EXTERNAL",
        "blocked_external": True,
        "probe_status": yan.get("probe_status"),
        "last_success": None,
        "yanolja_live": False,
        "pms_connected": False,
        "honesty_board_href": HONESTY_BOARD,
        "why": (
            "INT-YAN-WOLF remains BLOCKED_EXTERNAL. CAP-AMG-01 not unblocked. "
            "Occupancy stays UNKNOWN — never invent a percent."
        ),
    }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "amg_os_shell",
            "label": "AMG Operating Shell",
            "href": "/amg/os-shell",
            "kind": "existing",
            "note": "Upstream PMS tiles BLOCKED_EXTERNAL. Preserved.",
        },
        {
            "id": "integrations_status",
            "label": "Integrations honesty (INTG-TRUTH-1)",
            "href": HONESTY_BOARD,
            "kind": "existing",
            "note": "INT-YAN-WOLF BLOCKED_EXTERNAL · last_success null.",
        },
        {
            "id": "amg_today",
            "label": "AMG Today desk",
            "href": "/amg-ops-pack",
            "kind": "existing",
            "note": "Day-loop structure — not live occupancy.",
        },
        {
            "id": "conn_health",
            "label": "Connection health board",
            "href": "/ops/conn-health-1",
            "kind": "existing",
            "note": "Yanolja stamp BLOCKED_EXTERNAL — no invented last_success.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    yan = yanolja_path_honesty()
    shell_pin = amg_os_shell1_preserved()
    return [
        {
            "id": "occupancy",
            "label": "Occupancy",
            "status": "UNKNOWN",
            "value": None,
            "why": "PMS blocked → occupancy UNKNOWN (not zero, not invented).",
        },
        {
            "id": "yanolja",
            "label": "Yanolja / PMS",
            "status": "BLOCKED_EXTERNAL",
            "value": None,
            "why": yan.get("why"),
        },
        {
            "id": "invented_occupancy",
            "label": "Invented occupancy",
            "status": "REFUSED",
            "value": False,
            "why": "Occupancy invent writes are refused. UNKNOWN is honest.",
        },
        {
            "id": "amg_os_shell1",
            "label": "AMG-OS-SHELL-1",
            "status": "PRESERVED" if shell_pin.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": shell_pin.get("why"),
        },
        {
            "id": "cap_amg_01",
            "label": "CAP-AMG-01",
            "status": "BLOCKED_EXTERNAL",
            "value": None,
            "why": "Does not unblock CAP-AMG-01. Needs external Yanolja.",
        },
        {
            "id": "cap_amg_occ",
            "label": "CAP-AMG occupancy",
            "status": "SPECIFIED",
            "value": None,
            "why": "Occupancy honesty desk only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    yan = yanolja_path_honesty()
    shell_pin = amg_os_shell1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_amg_occ": CAP_AMG_OCC,
        "cap_amg_01": CAP_AMG_01,
        "yanolja_id": YANOLJA_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "yanolja_live": False,
        "pms_connected": False,
        "cap_amg_01_unblocked": False,
        "fake_pms_data": False,
        "invented_occupancy": False,
        "invented_occupancy_pct": False,
        "invented_rooms_sold": False,
        "invented_adr": False,
        "invented_revpar": False,
        "invented_proven": False,
        "invented_ready": False,
        "occupancy_unknown": True,
        "occupancy_blocked": True,
        "last_success_null": yan.get("last_success") is None,
        "yanolja_blocked": yan.get("audit_status") == "BLOCKED_EXTERNAL",
        "amg_os_shell1_preserved": shell_pin.get("ok") is True,
        "extends_amg_os_shell1": True,
        "second_amg_system": False,
        "cap_amg_01_proven": False,
        "cap_amg_occ_proven": False,
        "cap_amg_occ_ready": False,
        "cap_amg_occ_maturity": "SPECIFIED",
        "cap_amg_occ_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "production": False,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "SOP-LESSON-LIVE-1",
    }


def refuse_invent_occupancy(_body: dict | None = None) -> None:
    raise AmgOccTruth1Error(
        "Occupancy is UNKNOWN while PMS is blocked. Not invented.",
        code="invent_occupancy_refused",
    )


def refuse_unblock_pms(_body: dict | None = None) -> None:
    raise AmgOccTruth1Error(
        "CAP-AMG-01 / Yanolja unblock is refused. External seating required.",
        code="unblock_pms_refused",
    )


def refuse_fake_pct(_body: dict | None = None) -> None:
    raise AmgOccTruth1Error(
        "Occupancy percent invent is refused. UNKNOWN when PMS blocked.",
        code="invent_pct_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise AmgOccTruth1Error(
        "PROVEN is refused. CAP-AMG occupancy stays SPECIFIED. UNKNOWN is not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise AmgOccTruth1Error(
        "READY is refused. A blocked occupancy desk is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise AmgOccTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "occupancy",
            "occupancy-pct",
            "occupancy_pct",
            "occ",
            "occ-pct",
            "rooms-sold",
            "rooms_sold",
            "rooms-available",
            "rooms_available",
            "adr",
            "revpar",
            "invent-occupancy",
            "invent_occupancy",
            "fake-occupancy",
            "fake_occupancy",
            "fake-occ",
            "fake_occ",
        }:
            refuse_invent_occupancy(payload)
        if token in {
            "pct",
            "percent",
            "percentage",
            "rate",
        }:
            refuse_fake_pct(payload)
        if token in {
            "unblock",
            "unblock-pms",
            "unblock_pms",
            "yanolja-live",
            "yanolja_live",
            "pms-live",
            "pms_live",
            "cap-amg-01",
            "cap_amg_01",
        }:
            refuse_unblock_pms(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise AmgOccTruth1Error(
        "External writes are refused. Occupancy truth desk is read-only honesty.",
        code="write_refused",
    )


def all_occ_slots_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    slots = pack.get("occ_slots") or []
    if not slots:
        return False
    return all(
        s.get("value") is None
        and s.get("occupancy_pct") is None
        and s.get("count") is None
        and s.get("amount") is None
        and s.get("display") == "UNKNOWN"
        and s.get("status") == "BLOCKED_EXTERNAL"
        and s.get("invented_occupancy") is False
        and s.get("yanolja_live") is False
        for s in slots
    )


def yanolja_stays_blocked(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    yan = pack.get("yanolja") or {}
    return (
        yan.get("audit_status") == "BLOCKED_EXTERNAL"
        and yan.get("blocked_external") is True
        and yan.get("last_success") is None
        and yan.get("yanolja_live") is False
        and pack.get("cap_amg_01_unblocked") is False
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    slots = _occ_slots()
    yan = yanolja_path_honesty()
    shell_pin = amg_os_shell1_preserved()
    shell = _shell.build_shell()
    shell_occ = next(
        (t for t in (shell.get("pms_tiles") or []) if t.get("id") == "occupancy"),
        None,
    )
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_AMG_OCC, CAP_AMG_01],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "yanolja_live": False,
        "pms_connected": False,
        "cap_amg_01_unblocked": False,
        "fake_pms_data": False,
        "invented_occupancy": False,
        "invented_occupancy_pct": False,
        "invented_rooms_sold": False,
        "invented_adr": False,
        "invented_revpar": False,
        "occupancy_unknown": True,
        "occupancy_blocked": True,
        "last_success": None,
        "amg_os_shell1_preserved": shell_pin.get("ok") is True,
        "cap_amg_01_proven": False,
        "cap_amg_occ_proven": False,
        "cap_amg_occ_ready": False,
        "cap_amg_occ_maturity": flags["cap_amg_occ_maturity"],
        "cap_amg_occ_ceiling": flags["cap_amg_occ_ceiling"],
        "yanolja": yan,
        "occ_slots": slots,
        "shell_occupancy_tile": shell_occ,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "amg_os_shell1": shell_pin,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_occupancy",
            "occupancy_pct",
            "rooms_sold",
            "adr",
            "revpar",
            "CAP-AMG-01 unblocked",
            "CAP-AMG occupancy PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "does_not_unblock": [CAP_AMG_01, "Yanolja"],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "SOP-LESSON-LIVE-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "occ_slots": [s[0] for s in _OCC_SLOT_SPECS],
        "status_enum": ["UNKNOWN", "BLOCKED_EXTERNAL", "REFUSED", "PRESERVED"],
        "occupancy_property": False,
        "pct_property": False,
        "writes_accepted": False,
        "pms_unblocked": False,
        "extends": [
            "scripts/core/amg_os_shell.py",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_amg_system": False,
        "why": (
            "Occupancy honesty desk over AMG-OS-SHELL-1. "
            "UNKNOWN/BLOCKED when PMS blocked. No invented occupancy."
        ),
    }
