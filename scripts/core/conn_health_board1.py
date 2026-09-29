#!/usr/bin/env python3
"""CONN-HEALTH-BOARD-1 — Connections health board deepen (INTG + BLOCKED honesty).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CONN-HEALTH-BOARD-1
(armed 2026-09-30 after GGV-PIPELINE-TRUTH-1 PASS_VERIFIED).

Surfaces connection stamps from INTG-TRUTH-1 without inventing last_success.
Yanolja stays BLOCKED_EXTERNAL. Never unblocks external connectors.
Preserves INTG-TRUTH-1 + ESB-TRUTH-1.
staff_ready=false · human_commissioned=false.
Does not auto-chain AMG-OCC-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import esb_truth1 as _esb
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "CONN-HEALTH-BOARD-1"
SCHEMA_ID = "wolf.conn-health-board-1.v1"
BOUND = "beta-conn-health"
PROD_PID_HELD = 15975
WRITE_AUTHORITY = "NONE_EXPANDED"
WITA = timezone(timedelta(hours=8))

PAGE_PATHS = frozenset(
    {
        "/ops/conn-health-1",
        "/ops/conn-health-1/",
        "/ops/conn-health",
        "/ops/conn-health/",
        "/conn-health-1",
        "/conn-health-1/",
        "/conn-health",
        "/conn-health/",
        "/conn-health-1.html",
        "/dashboards/conn-health-1.html",
    }
)
API_PATH = "/api/ops/conn-health-1"

PRESERVED_PACKS = ("INTG-TRUTH-1", "ESB-TRUTH-1")

# Focal connectors deepened on this board (stamps, not invent success).
_FOCAL_IDS = (
    "INT-YAN-WOLF",
    "INT-ESB-WOLF",
    "INT-BANK-WOLF",
    "INT-MET-WOLF",
    "INT-GWS-WOLF",
)

_INVENT_SUCCESS_TOKENS = frozenset(
    {
        "last-success",
        "last_success",
        "invent-success",
        "invent_success",
        "invent-last-success",
        "invent_last_success",
        "fake-success",
        "fake_success",
        "fake-last-success",
        "fake_last_success",
        "success",
        "success-at",
        "success_at",
        "mark-success",
        "mark_success",
    }
)

_UNBLOCK_TOKENS = frozenset(
    {
        "unblock",
        "unblock-yanolja",
        "unblock_yanolja",
        "yanolja-unblock",
        "yanolja_unblock",
        "live-yanolja",
        "live_yanolja",
        "enable-yanolja",
        "enable_yanolja",
        "clear-blocked",
        "clear_blocked",
        "blocked-external",
        "blocked_external",
    }
)


class ConnHealthBoard1Error(ValueError):
    """Fail closed. Does not invent last_success or unblock connectors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 403,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _stamp_from_connector(conn: dict[str, Any]) -> dict[str, Any]:
    """Honesty stamp for one connector. Never invent last_success."""
    iid = str(conn.get("integration_id") or "")
    audit = str(conn.get("audit_status") or "UNKNOWN")
    blocked = bool(conn.get("blocked_external") is True)
    # Absolute pin: blank/missing last_success stays null.
    last = conn.get("last_success")
    if not last:
        last = None
    return {
        "id": iid,
        "integration_id": iid,
        "label": iid,
        "source": conn.get("source"),
        "target": conn.get("target"),
        "purpose": conn.get("purpose"),
        "audit_status": audit,
        "probe_status": conn.get("probe_status"),
        "blocked_external": blocked,
        "last_success": last,
        "last_probed_at": conn.get("last_probed_at"),
        "probe_notes": conn.get("probe_notes"),
        "write_authority": WRITE_AUTHORITY,
        "secrets_exposed": False,
        "invented_last_success": False,
        "unblocked": False,
        "status": audit,
        "display": audit,
        "why": (
            conn.get("probe_notes")
            or (
                f"{iid}: {audit}. last_success=null — never invent. "
                + ("BLOCKED stays BLOCKED." if blocked else "No fake live feed.")
            )
        ),
    }


def _connection_stamps(board: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = board if board is not None else _intg.build_board(persist_audit=False)
    stamps = [
        _stamp_from_connector(c)
        for c in (payload.get("connectors") or [])
        if isinstance(c, dict) and c.get("integration_id")
    ]
    # Stable: INT-* first, then CAP-*, MCP-*, other
    def sort_key(s: dict[str, Any]) -> tuple[int, str]:
        iid = str(s.get("integration_id") or "")
        if iid.startswith("INT-"):
            return (0, iid)
        if iid.startswith("CAP-INTG-"):
            return (1, iid)
        if iid.startswith("MCP-"):
            return (2, iid)
        return (3, iid)

    stamps.sort(key=sort_key)
    return stamps


def _focal_stamps(stamps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {s["integration_id"]: s for s in stamps}
    out: list[dict[str, Any]] = []
    for iid in _FOCAL_IDS:
        row = by_id.get(iid)
        if row:
            out.append(row)
            continue
        # Missing focal still stamped UNKNOWN — never invent success.
        out.append(
            {
                "id": iid,
                "integration_id": iid,
                "label": iid,
                "source": None,
                "target": None,
                "purpose": None,
                "audit_status": "UNKNOWN",
                "probe_status": "ABSENT_FROM_REGISTRY",
                "blocked_external": iid == "INT-YAN-WOLF",
                "last_success": None,
                "last_probed_at": None,
                "probe_notes": f"{iid} absent from INTG registry — UNKNOWN, not invent.",
                "write_authority": WRITE_AUTHORITY,
                "secrets_exposed": False,
                "invented_last_success": False,
                "unblocked": False,
                "status": "UNKNOWN",
                "display": "UNKNOWN",
                "why": f"{iid} absent — UNKNOWN. last_success=null.",
            }
        )
    return out


def intg_truth1_preserved() -> dict[str, Any]:
    """INTG-TRUTH-1 board still honest: Yanolja BLOCKED, ESB PARTIAL, no invent."""
    board = _intg.build_board(persist_audit=False)
    yan = next(
        (
            c
            for c in (board.get("connectors") or [])
            if c.get("integration_id") == "INT-YAN-WOLF"
        ),
        None,
    )
    esb = next(
        (
            c
            for c in (board.get("connectors") or [])
            if c.get("integration_id") == "INT-ESB-WOLF"
        ),
        None,
    )
    ok = (
        board.get("ok") is True
        and board.get("staff_ready") is False
        and board.get("human_commissioned") is False
        and board.get("invented_last_success") is False
        and yan is not None
        and yan.get("audit_status") == "BLOCKED_EXTERNAL"
        and yan.get("blocked_external") is True
        and yan.get("last_success") is None
        and esb is not None
        and esb.get("audit_status") == "PARTIAL_IN_BETA"
        and esb.get("last_success") is None
        and (esb.get("probe_facts") or {}).get("pnl_invented") is False
        and _intg.yanolja_blocked(board.get("connectors"))
    )
    return {
        "ok": ok,
        "pack": "INTG-TRUTH-1",
        "yanolja_audit": (yan or {}).get("audit_status"),
        "yanolja_blocked": bool((yan or {}).get("blocked_external")),
        "yanolja_last_success": (yan or {}).get("last_success"),
        "esb_audit": (esb or {}).get("audit_status"),
        "esb_last_success": (esb or {}).get("last_success"),
        "pnl_invented": (esb or {}).get("probe_facts", {}).get("pnl_invented"),
        "href": "/ops/integrations-status",
        "why": (
            "INTG-TRUTH-1 preserved: INT-YAN-WOLF BLOCKED_EXTERNAL last_success=null; "
            "INT-ESB-WOLF PARTIAL_IN_BETA pnl_invented=false; staff_ready/human_commissioned false."
            if ok
            else "INTG-TRUTH-1 honesty check failed."
        ),
    }


def esb_truth1_preserved() -> dict[str, Any]:
    """ESB-TRUTH-1 warehouse board still PARTIAL_IN_BETA; no fake settlement."""
    try:
        flags = _esb.honesty_flags()
        slice_ = _esb.build_slice()
        ok = (
            slice_.get("ok") is True
            and slice_.get("staff_ready") is False
            and slice_.get("human_commissioned") is False
            and slice_.get("audit_status") == "PARTIAL_IN_BETA"
            and slice_.get("settlement_api") == "UNAVAILABLE"
            and slice_.get("pnl") is None
            and slice_.get("pnl_invented") is False
            and slice_.get("fake_settlement") is False
            and slice_.get("esb_write") is False
            and slice_.get("last_success") is None
            and flags.get("pnl_invented") is False
            and flags.get("fake_settlement") is False
            and flags.get("esb_write") is False
            and flags.get("invented_last_success") is False
        )
        return {
            "ok": ok,
            "pack": "ESB-TRUTH-1",
            "audit_status": slice_.get("audit_status"),
            "settlement_api": slice_.get("settlement_api"),
            "pnl_invented": slice_.get("pnl_invented"),
            "esb_write": slice_.get("esb_write"),
            "last_success": slice_.get("last_success"),
            "href": "/ops/esb-truth-1",
            "why": (
                "ESB-TRUTH-1 preserved: PARTIAL_IN_BETA · settlement_api UNAVAILABLE · "
                "pnl_invented=false · esb_write=false · last_success=null."
                if ok
                else "ESB-TRUTH-1 honesty check failed."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "ESB-TRUTH-1",
            "error": type(exc).__name__,
            "why": "ESB-TRUTH-1 honesty check failed.",
        }


def _honesty_tiles(
    focal: list[dict[str, Any]],
    intg: dict[str, Any],
    esb: dict[str, Any],
    counts: dict[str, Any],
) -> list[dict[str, Any]]:
    yan = next((s for s in focal if s.get("integration_id") == "INT-YAN-WOLF"), {})
    esb_row = next((s for s in focal if s.get("integration_id") == "INT-ESB-WOLF"), {})
    return [
        {
            "id": "yanolja",
            "label": "Yanolja (INT-YAN-WOLF)",
            "status": "BLOCKED_EXTERNAL",
            "value": "BLOCKED_EXTERNAL",
            "why": (
                "Yanolja stays BLOCKED_EXTERNAL. last_success=null. "
                "No unblock. No fake live feed."
            ),
        },
        {
            "id": "esb",
            "label": "ESB (INT-ESB-WOLF)",
            "status": str(esb_row.get("audit_status") or "PARTIAL_IN_BETA"),
            "value": esb_row.get("audit_status"),
            "why": "PARTIAL_IN_BETA warehouse facts. Warehouse ≠ connector success.",
        },
        {
            "id": "last_success_policy",
            "label": "last_success policy",
            "status": "NULL",
            "value": None,
            "why": "null_if_unknown_never_invent. Stamps do not invent success timestamps.",
        },
        {
            "id": "blocked_count",
            "label": "BLOCKED_EXTERNAL count",
            "status": "FACT",
            "value": counts.get("blocked_external"),
            "why": f"blocked_external={counts.get('blocked_external')}. Count from INTG registry.",
        },
        {
            "id": "intg_truth1",
            "label": "INTG-TRUTH-1",
            "status": "PRESERVED" if intg.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": intg.get("why"),
        },
        {
            "id": "esb_truth1",
            "label": "ESB-TRUTH-1",
            "status": "PRESERVED" if esb.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": esb.get("why"),
        },
        {
            "id": "write_authority",
            "label": "Write authority",
            "status": WRITE_AUTHORITY,
            "value": WRITE_AUTHORITY,
            "why": "Invent-success / unblock writes refused. Write authority not expanded.",
        },
        {
            "id": "yanolja_last_success",
            "label": "Yanolja last_success",
            "status": "NULL",
            "value": yan.get("last_success"),
            "why": "Yanolja last_success stays null. BLOCKED stays BLOCKED.",
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "intg_truth",
            "label": "Integrations honesty board",
            "href": "/ops/integrations-status",
            "kind": "existing",
            "note": "INTG-TRUTH-1 — connector registry + safe probes.",
        },
        {
            "id": "esb_truth",
            "label": "ESB warehouse truth",
            "href": "/ops/esb-truth-1",
            "kind": "existing",
            "note": "ESB-TRUTH-1 — PARTIAL_IN_BETA warehouse RO.",
        },
        {
            "id": "reliability",
            "label": "Reliability board",
            "href": "/ops/reliability",
            "kind": "existing",
            "note": "Listener/sidecar health — separate from connectors.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    intg = intg_truth1_preserved()
    esb = esb_truth1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "write_authority_expanded": False,
        "write_authority": WRITE_AUTHORITY,
        "secrets_exposed": False,
        "invented_last_success": False,
        "fake_last_success": False,
        "fake_live_feeds": False,
        "yanolja_unblocked": False,
        "yanolja_blocked": True,
        "external_connectors_unblocked": False,
        "last_success_policy": "null_if_unknown_never_invent",
        "blocked_stays_blocked": True,
        "anon_fail_closed": True,
        "owner_read": True,
        "intg_truth1_preserved": intg.get("ok") is True,
        "esb_truth1_preserved": esb.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "AMG-OCC-TRUTH-1",
    }


def refuse_invent_success(_body: dict | None = None) -> None:
    raise ConnHealthBoard1Error(
        "Invented last_success is refused. Stamps stay null when unknown.",
        code="invent_success_refused",
        http_status=403,
    )


def refuse_unblock(_body: dict | None = None) -> None:
    raise ConnHealthBoard1Error(
        "Unblock refused. Yanolja and other external connectors stay BLOCKED.",
        code="unblock_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ConnHealthBoard1Error(
        "PROVEN is refused. Connections health stamps are honesty, not a full prove.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ConnHealthBoard1Error(
        "READY is refused. A connections health board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ConnHealthBoard1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if (
            token in _INVENT_SUCCESS_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_SUCCESS_TOKENS}
        ):
            refuse_invent_success(payload)
        if (
            token in _UNBLOCK_TOKENS
            or norm in {t.replace("-", "_") for t in _UNBLOCK_TOKENS}
            or "unblock" in token
            or "unblock" in norm
            or "yanolja" in token
        ):
            refuse_unblock(payload)
    raise ConnHealthBoard1Error(
        "CONN-HEALTH-BOARD-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_last_success_null(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stamps = pack.get("connection_stamps") or []
    focal = pack.get("focal_stamps") or []
    if not stamps:
        return False
    for s in list(stamps) + list(focal):
        if s.get("last_success") is not None:
            return False
        if s.get("invented_last_success") is not False:
            return False
    return pack.get("last_success") is None and pack.get("invented_last_success") is False


def yanolja_stays_blocked(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    yan = pack.get("yanolja") or {}
    return (
        yan.get("audit_status") == "BLOCKED_EXTERNAL"
        and yan.get("blocked_external") is True
        and yan.get("last_success") is None
        and yan.get("unblocked") is False
        and pack.get("yanolja_unblocked") is False
        and pack.get("yanolja_blocked") is True
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    board = _intg.build_board(persist_audit=False)
    stamps = _connection_stamps(board)
    focal = _focal_stamps(stamps)
    intg = intg_truth1_preserved()
    esb = esb_truth1_preserved()
    yan = next((s for s in focal if s.get("integration_id") == "INT-YAN-WOLF"), {})
    counts = dict(board.get("counts") or {})
    by_audit = dict(counts.get("by_audit_status") or {})
    blocked = int(counts.get("blocked_external") or 0)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": ["connections"],
        "title": "Connections health board",
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "write_authority": WRITE_AUTHORITY,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "invented_last_success": False,
        "fake_last_success": False,
        "fake_live_feeds": False,
        "yanolja_unblocked": False,
        "yanolja_blocked": True,
        "external_connectors_unblocked": False,
        "blocked_stays_blocked": True,
        "last_success": None,
        "last_success_policy": "null_if_unknown_never_invent",
        "connection_count": len(stamps),
        "focal_count": len(focal),
        "blocked_external_count": blocked,
        "by_audit_status": by_audit,
        "connection_stamps": stamps,
        "focal_stamps": focal,
        "yanolja": yan,
        "intg_truth1_preserved": intg.get("ok") is True,
        "esb_truth1_preserved": esb.get("ok") is True,
        "intg_truth1": intg,
        "esb_truth1": esb,
        "honesty_tiles": _honesty_tiles(focal, intg, esb, counts),
        "desk_links": _desk_links(),
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_connector_success",
            "last_success",
            "yanolja_unblocked",
            "external_connectors_live",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "AMG-OCC-TRUTH-1",
        "summary": (
            "Connections health board. Stamps from INTG-TRUTH-1 without inventing "
            "last_success. Yanolja BLOCKED_EXTERNAL. "
            "INTG-TRUTH-1 + ESB-TRUTH-1 preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "last_success_property": False,
        "invented_last_success": False,
        "yanolja_unblocked": False,
        "writes_accepted": False,
        "unblock_accepted": False,
        "preserves": list(PRESERVED_PACKS),
        "focal_ids": list(_FOCAL_IDS),
        "why": (
            "Connections health board deepen. Stamps without inventing last_success. "
            "BLOCKED stays BLOCKED. No fake live feeds."
        ),
    }
