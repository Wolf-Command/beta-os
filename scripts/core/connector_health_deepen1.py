#!/usr/bin/env python3
"""CONNECTOR-HEALTH-DEEPEN-1 — Connector health deepen (per-connector honesty).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack
CONNECTOR-HEALTH-DEEPEN-1 (armed 2026-09-30 after WEEKLY-CASH-FORECAST-SHELL-1
PASS_VERIFIED).

Deepens CONN-HEALTH with Wave7/8 classifications per connector.
Never invents last_success. Never paints fake connector UP.
Preserve CONN-HEALTH (CONN-HEALTH-BOARD-1) + INTG-TRUTH-1.
staff_ready=false · human_commissioned=false.
Does not auto-chain WAVE10-SYNTH-CONTINUE / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import conn_health_board1 as _conn
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "CONNECTOR-HEALTH-DEEPEN-1"
SCHEMA_ID = "wolf.connector-health-deepen-1.v1"
BOUND = "beta-connector-health-deepen"
PROD_PID_HELD = 15975
WRITE_AUTHORITY = "NONE_EXPANDED"
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
ACTION = "DEEPEN_CONN_HEALTH_WAVE78_CLASS"
PRESERVED_PACKS = ("CONN-HEALTH", "CONN-HEALTH-BOARD-1", "INTG-TRUTH-1")
NEXT_PACK = "WAVE10-SYNTH-CONTINUE"

PAGE_PATHS = frozenset(
    {
        "/ops/connector-health-deepen-1",
        "/ops/connector-health-deepen-1/",
        "/ops/connector-health-deepen",
        "/ops/connector-health-deepen/",
        "/ops/conn-health-deepen-1",
        "/ops/conn-health-deepen-1/",
        "/ops/conn-health-deepen",
        "/ops/conn-health-deepen/",
        "/connector-health-deepen-1",
        "/connector-health-deepen-1/",
        "/connector-health-deepen-1.html",
        "/dashboards/connector-health-deepen-1.html",
    }
)
API_PATH = "/api/ops/connector-health-deepen-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/conn-health-deepen-1",
        "/api/ops/connector-health-deepen",
        "/api/ops/conn-health-deepen",
    }
)

# Focal connectors deepened with Wave7/8 classification stamps.
_FOCAL_IDS = (
    "INT-YAN-WOLF",
    "INT-ESB-WOLF",
    "INT-BANK-WOLF",
    "INT-MET-WOLF",
    "INT-GWS-WOLF",
)

# Wave7/8 per-connector honesty map — never UP / never invent last_success.
_WAVE78: dict[str, dict[str, Any]] = {
    "INT-YAN-WOLF": {
        "classification": "EXTERNAL_BLOCKER",
        "health_display": "BLOCKED_EXTERNAL",
        "wave_pack": "OCCUPANCY-EXTERNAL-HOLD-1",
        "wave": "8",
        "evidence": (
            "Yanolja BLOCKED_EXTERNAL; CAP-AMG-01 not unblocked; "
            "OCCUPANCY-EXTERNAL-HOLD-1 stamped EXTERNAL_BLOCKER"
        ),
        "fake_up_refused": True,
        "last_success": None,
    },
    "INT-ESB-WOLF": {
        "classification": "EXTERNAL_BLOCKER",
        "health_display": "PARTIAL_IN_BETA",
        "wave_pack": "ESB-SETTLEMENT-PATH-1",
        "wave": "7",
        "evidence": (
            "Warehouse PARTIAL_IN_BETA RO; settlement_api UNAVAILABLE "
            "(Felix 2026-07-19); ESB-SETTLEMENT-PATH-1 EXTERNAL_BLOCKER"
        ),
        "sub_pins": {
            "warehouse": "PARTIAL_IN_BETA",
            "settlement": "EXTERNAL_BLOCKER",
        },
        "fake_up_refused": True,
        "last_success": None,
    },
    "INT-BANK-WOLF": {
        "classification": "HUMAN_COMMISSIONING",
        "health_display": "FILE_IMPORT_ONLY",
        "wave_pack": "FIN-BANK-CREDS-ROUTE-1",
        "wave": "7",
        "evidence": (
            "FIN-BANK-CREDS-ROUTE-1 HUMAN_COMMISSIONING; FILE_IMPORT_ONLY held; "
            "live scrape refused until Owner creds"
        ),
        "fake_up_refused": True,
        "last_success": None,
    },
    "INT-MET-WOLF": {
        "classification": "INTERNALLY_SOLVABLE",
        "health_display": "PER_SURFACE_RUNTIME_WIRED_PARTIAL",
        "wave_pack": "METRICOOL-RUNTIME-WIRE-1",
        "wave": "7",
        "evidence": (
            "METRICOOL-RUNTIME-WIRE-1 lifted blanket NOT_RUNTIME; "
            "engagement still NOT_RUNTIME null; write DISABLED/NOT_RUNTIME "
            "(CONTENT-PUBLISH-PATH-1); never invent UP"
        ),
        "sub_pins": {
            "runtime_wire": "PER_SURFACE",
            "engagement": "NOT_RUNTIME",
            "write": "DISABLED",
        },
        "fake_up_refused": True,
        "last_success": None,
    },
    "INT-GWS-WOLF": {
        "classification": "HUMAN_COMMISSIONING_OR_INTERNAL",
        "health_display": "MISSING_OR_UNPROVEN",
        "wave_pack": None,
        "wave": "7/8",
        "evidence": (
            "INTG registry MISSING_OR_UNPROVEN; no Wave7/8 pack wired GWS live; "
            "never invent last_success or UP"
        ),
        "fake_up_refused": True,
        "last_success": None,
    },
    "CAP-INTG-01": {
        "classification": "EXTERNAL_BLOCKER",
        "health_display": "BLOCKED_EXTERNAL",
        "wave_pack": "OCCUPANCY-EXTERNAL-HOLD-1",
        "wave": "8",
        "evidence": "CAP-INTG-01 / Yanolja capability stays BLOCKED_EXTERNAL",
        "fake_up_refused": True,
        "last_success": None,
    },
    "CAP-INTG-02": {
        "classification": "EXTERNAL_BLOCKER",
        "health_display": "PARTIAL_IN_BETA",
        "wave_pack": "ESB-SETTLEMENT-PATH-1",
        "wave": "7",
        "evidence": "ESB capability: warehouse PARTIAL; settlement EXTERNAL_BLOCKER",
        "fake_up_refused": True,
        "last_success": None,
    },
    "CAP-INTG-04": {
        "classification": "HUMAN_COMMISSIONING",
        "health_display": "FILE_IMPORT_ONLY",
        "wave_pack": "FIN-BANK-CREDS-ROUTE-1",
        "wave": "7",
        "evidence": "Bank capability FILE_IMPORT_ONLY until Owner commission",
        "fake_up_refused": True,
        "last_success": None,
    },
    "CAP-INTG-05": {
        "classification": "INTERNALLY_SOLVABLE",
        "health_display": "PER_SURFACE_RUNTIME_WIRED_PARTIAL",
        "wave_pack": "METRICOOL-RUNTIME-WIRE-1",
        "wave": "7",
        "evidence": "Metricool capability per-surface; engagement NOT_RUNTIME",
        "fake_up_refused": True,
        "last_success": None,
    },
    "CAP-INTG-07": {
        "classification": "EXTERNAL_BLOCKER",
        "health_display": "BLOCKED_EXTERNAL",
        "wave_pack": "OCCUPANCY-EXTERNAL-HOLD-1",
        "wave": "8",
        "evidence": "CAP-INTG-07 remains blocked_external_not_auto_solved",
        "fake_up_refused": True,
        "last_success": None,
    },
}

STATUS_VOCAB = frozenset(
    {
        "INTERNALLY_SOLVABLE",
        "HUMAN_COMMISSIONING",
        "HUMAN_COMMISSIONING_OR_INTERNAL",
        "HUMAN_COMMISSIONING_OR_EXTERNAL",
        "EXTERNAL_BLOCKER",
        "MATT_ACTION",
        "BLOCKED_EXTERNAL",
        "PARTIAL_IN_BETA",
        "FILE_IMPORT_ONLY",
        "PER_SURFACE_RUNTIME_WIRED_PARTIAL",
        "MISSING_OR_UNPROVEN",
        "AGENT_HOST_ONLY",
        "NOT_RUNTIME",
        "DISABLED",
        "PRESERVED",
        "REFUSED",
        "UNKNOWN",
        "ABSENT",
    }
)

_FAKE_UP_TOKENS = frozenset(
    {
        "up",
        "mark-up",
        "mark_up",
        "fake-up",
        "fake_up",
        "connector-up",
        "connector_up",
        "force-up",
        "force_up",
        "set-up",
        "set_up",
        "health-up",
        "health_up",
        "status-up",
        "status_up",
        "live-up",
        "live_up",
        "online",
        "healthy",
        "green",
    }
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
    }
)


class ConnectorHealthDeepen1Error(ValueError):
    """Fail closed. Does not invent last_success or fake connector UP."""

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
    return raw.rstrip("/") in {p.rstrip("/") for p in API_PATHS}


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _wave78_for(iid: str, audit: str | None) -> dict[str, Any]:
    pinned = _WAVE78.get(iid)
    if pinned:
        return dict(pinned)
    # MCP hosts: agent-only — not connector UP.
    if iid.startswith("MCP-"):
        return {
            "classification": "INTERNALLY_SOLVABLE",
            "health_display": "AGENT_HOST_ONLY",
            "wave_pack": None,
            "wave": "7",
            "evidence": f"{iid} AGENT_HOST_ONLY — never invent connector UP",
            "fake_up_refused": True,
            "last_success": None,
        }
    # Default: stamp from audit without inventing UP.
    display = audit or "UNKNOWN"
    if display in ("BLOCKED_EXTERNAL",):
        cls = "EXTERNAL_BLOCKER"
    elif display in ("PARTIAL_IN_BETA", "BUILT_NOT_PROVEN"):
        cls = "INTERNALLY_SOLVABLE"
    elif display in ("MISSING", "MISSING_OR_UNPROVEN", "UNKNOWN"):
        cls = "HUMAN_COMMISSIONING_OR_INTERNAL"
    elif display == "AGENT_HOST_ONLY":
        cls = "INTERNALLY_SOLVABLE"
    else:
        cls = "HUMAN_COMMISSIONING_OR_INTERNAL"
    return {
        "classification": cls,
        "health_display": display,
        "wave_pack": None,
        "wave": "7/8",
        "evidence": f"{iid} audit={display}; Wave7/8 deepen without invent UP",
        "fake_up_refused": True,
        "last_success": None,
    }


def _stamp_row(conn: dict[str, Any]) -> dict[str, Any]:
    iid = str(conn.get("integration_id") or "")
    audit = str(conn.get("audit_status") or "UNKNOWN")
    blocked = bool(conn.get("blocked_external") is True)
    last = conn.get("last_success")
    if not last:
        last = None
    wave = _wave78_for(iid, audit)
    health = str(wave.get("health_display") or audit)
    # Absolute pin: never paint UP / online / healthy.
    if health.upper() in {"UP", "ONLINE", "HEALTHY", "GREEN", "OK"}:
        health = audit if audit not in {"UP", "ONLINE", "HEALTHY"} else "UNKNOWN"
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
        "classification": wave.get("classification"),
        "wave78_classification": wave.get("classification"),
        "health_display": health,
        "wave_pack": wave.get("wave_pack"),
        "wave": wave.get("wave"),
        "evidence": wave.get("evidence"),
        "sub_pins": wave.get("sub_pins") or {},
        "fake_up": False,
        "fake_up_refused": True,
        "connector_up": False,
        "write_authority": WRITE_AUTHORITY,
        "secrets_exposed": False,
        "invented_last_success": False,
        "unblocked": False,
        "status": wave.get("classification") or audit,
        "display": health,
        "why": (
            f"{iid}: {wave.get('classification')} · health={health} · "
            f"last_success=null — never invent. "
            + ("BLOCKED stays BLOCKED. " if blocked else "")
            + "No fake UP."
        ),
    }


def _connection_stamps(board: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = board if board is not None else _intg.build_board(persist_audit=False)
    stamps = [
        _stamp_row(c)
        for c in (payload.get("connectors") or [])
        if isinstance(c, dict) and c.get("integration_id")
    ]

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
        wave = _wave78_for(iid, "UNKNOWN")
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
                "probe_notes": f"{iid} absent — UNKNOWN, not invent.",
                "classification": wave.get("classification"),
                "wave78_classification": wave.get("classification"),
                "health_display": wave.get("health_display") or "UNKNOWN",
                "wave_pack": wave.get("wave_pack"),
                "wave": wave.get("wave"),
                "evidence": wave.get("evidence"),
                "sub_pins": {},
                "fake_up": False,
                "fake_up_refused": True,
                "connector_up": False,
                "write_authority": WRITE_AUTHORITY,
                "secrets_exposed": False,
                "invented_last_success": False,
                "unblocked": False,
                "status": wave.get("classification") or "UNKNOWN",
                "display": wave.get("health_display") or "UNKNOWN",
                "why": f"{iid} absent — UNKNOWN. last_success=null. No fake UP.",
            }
        )
    return out


def conn_health_preserved() -> dict[str, Any]:
    """CONN-HEALTH-BOARD-1 still honest: stamps, Yanolja BLOCKED, no invent."""
    try:
        slice_ = _conn.build_slice()
        flags = _conn.honesty_flags()
        ok = (
            slice_.get("ok") is True
            and slice_.get("staff_ready") is False
            and slice_.get("human_commissioned") is False
            and slice_.get("invented_last_success") is False
            and slice_.get("fake_last_success") is False
            and slice_.get("yanolja_blocked") is True
            and slice_.get("yanolja_unblocked") is False
            and slice_.get("last_success") is None
            and _conn.all_last_success_null(slice_)
            and _conn.yanolja_stays_blocked(slice_)
            and flags.get("invented_last_success") is False
            and flags.get("yanolja_blocked") is True
        )
        return {
            "ok": ok,
            "pack": "CONN-HEALTH",
            "board_pack": "CONN-HEALTH-BOARD-1",
            "yanolja_blocked": slice_.get("yanolja_blocked"),
            "last_success": slice_.get("last_success"),
            "invented_last_success": slice_.get("invented_last_success"),
            "href": "/ops/conn-health-1",
            "why": (
                "CONN-HEALTH preserved: stamps · Yanolja BLOCKED_EXTERNAL · "
                "last_success=null · invented_last_success=false."
                if ok
                else "CONN-HEALTH honesty check failed."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "CONN-HEALTH",
            "error": type(exc).__name__,
            "why": "CONN-HEALTH honesty check failed.",
        }


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
            "INT-ESB-WOLF PARTIAL_IN_BETA pnl_invented=false."
            if ok
            else "INTG-TRUTH-1 honesty check failed."
        ),
    }


def _class_counts(stamps: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in stamps:
        cls = str(s.get("wave78_classification") or s.get("classification") or "UNKNOWN")
        counts[cls] = counts.get(cls, 0) + 1
    return counts


def _honesty_tiles(
    focal: list[dict[str, Any]],
    conn_p: dict[str, Any],
    intg_p: dict[str, Any],
    class_counts: dict[str, int],
) -> list[dict[str, Any]]:
    yan = next((s for s in focal if s.get("integration_id") == "INT-YAN-WOLF"), {})
    esb = next((s for s in focal if s.get("integration_id") == "INT-ESB-WOLF"), {})
    bank = next((s for s in focal if s.get("integration_id") == "INT-BANK-WOLF"), {})
    met = next((s for s in focal if s.get("integration_id") == "INT-MET-WOLF"), {})
    return [
        {
            "id": "pack_class",
            "label": "Pack classification",
            "status": CLASSIFICATION,
            "value": CLASSIFICATION,
            "why": "Deepen CONN-HEALTH with Wave7/8 stamps is INTERNALLY_SOLVABLE.",
        },
        {
            "id": "yanolja",
            "label": "Yanolja (INT-YAN-WOLF)",
            "status": "EXTERNAL_BLOCKER",
            "value": "BLOCKED_EXTERNAL",
            "why": yan.get("evidence")
            or "EXTERNAL_BLOCKER · BLOCKED_EXTERNAL · last_success=null · no fake UP.",
        },
        {
            "id": "esb",
            "label": "ESB (INT-ESB-WOLF)",
            "status": "EXTERNAL_BLOCKER",
            "value": esb.get("health_display") or "PARTIAL_IN_BETA",
            "why": esb.get("evidence")
            or "Settlement EXTERNAL_BLOCKER; warehouse PARTIAL_IN_BETA.",
        },
        {
            "id": "bank",
            "label": "Bank (INT-BANK-WOLF)",
            "status": "HUMAN_COMMISSIONING",
            "value": "FILE_IMPORT_ONLY",
            "why": bank.get("evidence") or "HUMAN_COMMISSIONING · FILE_IMPORT_ONLY.",
        },
        {
            "id": "metricool",
            "label": "Metricool (INT-MET-WOLF)",
            "status": "INTERNALLY_SOLVABLE",
            "value": "PER_SURFACE_RUNTIME_WIRED_PARTIAL",
            "why": met.get("evidence")
            or "Per-surface wired; engagement NOT_RUNTIME; never invent UP.",
        },
        {
            "id": "last_success_policy",
            "label": "last_success policy",
            "status": "NULL",
            "value": None,
            "why": "null_if_unknown_never_invent. Deepen does not invent success.",
        },
        {
            "id": "fake_up_policy",
            "label": "Fake UP policy",
            "status": "REFUSED",
            "value": False,
            "why": "connector_up=false always. Wave7/8 class stamps ≠ UP.",
        },
        {
            "id": "class_mix",
            "label": "Wave7/8 class mix",
            "status": "FACT",
            "value": class_counts,
            "why": f"by_classification={class_counts}",
        },
        {
            "id": "conn_health",
            "label": "CONN-HEALTH",
            "status": "PRESERVED" if conn_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": conn_p.get("why"),
        },
        {
            "id": "intg_truth1",
            "label": "INTG-TRUTH-1",
            "status": "PRESERVED" if intg_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": intg_p.get("why"),
        },
        {
            "id": "write_authority",
            "label": "Write authority",
            "status": WRITE_AUTHORITY,
            "value": WRITE_AUTHORITY,
            "why": "Invent-success / fake-UP / unblock writes refused.",
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "conn_health",
            "label": "Connections health board",
            "href": "/ops/conn-health-1",
            "kind": "existing",
            "note": "CONN-HEALTH-BOARD-1 — stamps without invent last_success.",
        },
        {
            "id": "intg_truth",
            "label": "Integrations honesty board",
            "href": "/ops/integrations-status",
            "kind": "existing",
            "note": "INTG-TRUTH-1 — connector registry + safe probes.",
        },
        {
            "id": "esb_settlement",
            "label": "ESB settlement path",
            "href": "/ops/esb-settlement-path-1",
            "kind": "existing",
            "note": "Wave7 EXTERNAL_BLOCKER pin for settlement.",
        },
        {
            "id": "metricool",
            "label": "Metricool runtime wire",
            "href": "/ops/metricool-runtime-wire-1",
            "kind": "existing",
            "note": "Wave7 per-surface; engagement NOT_RUNTIME.",
        },
        {
            "id": "occupancy_hold",
            "label": "Occupancy external hold",
            "href": "/amg/occupancy-external-hold-1",
            "kind": "existing",
            "note": "Wave8 Yanolja EXTERNAL_BLOCKER.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    conn_p = conn_health_preserved()
    intg_p = intg_truth1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "ceiling": CEILING,
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
        "fake_up": False,
        "fake_connector_up": False,
        "connector_up": False,
        "fake_live_feeds": False,
        "yanolja_unblocked": False,
        "yanolja_blocked": True,
        "external_connectors_unblocked": False,
        "last_success_policy": "null_if_unknown_never_invent",
        "blocked_stays_blocked": True,
        "anon_fail_closed": True,
        "owner_read": True,
        "conn_health_preserved": conn_p.get("ok") is True,
        "intg_truth1_preserved": intg_p.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "pins": {
            "pack": CLASSIFICATION,
            "yanolja": "EXTERNAL_BLOCKER",
            "esb_settlement": "EXTERNAL_BLOCKER",
            "bank": "HUMAN_COMMISSIONING",
            "metricool": "INTERNALLY_SOLVABLE",
            "gws": "HUMAN_COMMISSIONING_OR_INTERNAL",
            "fake_up": "REFUSED",
            "invent_last_success": "REFUSED",
            "exit_report_headchef": "MATT_ACTION",
            "prod_mutate": "EXTERNAL_BLOCKER",
        },
    }


def refuse_invent_success(_body: dict | None = None) -> None:
    raise ConnectorHealthDeepen1Error(
        "Invented last_success is refused. Stamps stay null when unknown.",
        code="invent_success_refused",
        http_status=403,
    )


def refuse_fake_up(_body: dict | None = None) -> None:
    raise ConnectorHealthDeepen1Error(
        "Fake connector UP is refused. Wave7/8 classifications are not UP.",
        code="fake_up_refused",
        http_status=403,
    )


def refuse_unblock(_body: dict | None = None) -> None:
    raise ConnectorHealthDeepen1Error(
        "Unblock refused. Yanolja and other external connectors stay BLOCKED.",
        code="unblock_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ConnectorHealthDeepen1Error(
        "PROVEN is refused. Connector deepen stamps are honesty, not a full prove.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ConnectorHealthDeepen1Error(
        "READY is refused. A connector health deepen board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ConnectorHealthDeepen1Error("Write payload refused.", code="write_refused")
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
            token in _FAKE_UP_TOKENS
            or norm in {t.replace("-", "_") for t in _FAKE_UP_TOKENS}
            or token.endswith("-up")
            or norm.endswith("_up")
        ):
            refuse_fake_up(payload)
        if (
            token in _UNBLOCK_TOKENS
            or norm in {t.replace("-", "_") for t in _UNBLOCK_TOKENS}
            or "unblock" in token
            or "unblock" in norm
            or "yanolja" in token
        ):
            refuse_unblock(payload)
    raise ConnectorHealthDeepen1Error(
        "CONNECTOR-HEALTH-DEEPEN-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_last_success_null(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
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


def no_fake_up(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("fake_up") is not False or pack.get("connector_up") is not False:
        return False
    for s in list(pack.get("connection_stamps") or []) + list(
        pack.get("focal_stamps") or []
    ):
        if s.get("fake_up") is not False or s.get("connector_up") is not False:
            return False
        disp = str(s.get("health_display") or "").upper()
        if disp in {"UP", "ONLINE", "HEALTHY", "GREEN", "OK"}:
            return False
    return True


def yanolja_stays_blocked(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    yan = pack.get("yanolja") or {}
    return (
        yan.get("audit_status") == "BLOCKED_EXTERNAL"
        and yan.get("classification") == "EXTERNAL_BLOCKER"
        and yan.get("blocked_external") is True
        and yan.get("last_success") is None
        and yan.get("unblocked") is False
        and pack.get("yanolja_unblocked") is False
        and pack.get("yanolja_blocked") is True
    )


def focal_wave78_pinned(payload: dict[str, Any] | None = None) -> bool:
    """Each focal INT-* has the expected Wave7/8 classification."""
    pack = payload if payload is not None else build_board()
    expected = {
        "INT-YAN-WOLF": "EXTERNAL_BLOCKER",
        "INT-ESB-WOLF": "EXTERNAL_BLOCKER",
        "INT-BANK-WOLF": "HUMAN_COMMISSIONING",
        "INT-MET-WOLF": "INTERNALLY_SOLVABLE",
        "INT-GWS-WOLF": "HUMAN_COMMISSIONING_OR_INTERNAL",
    }
    by_id = {
        s.get("integration_id"): s for s in (pack.get("focal_stamps") or [])
    }
    for iid, cls in expected.items():
        row = by_id.get(iid) or {}
        if row.get("wave78_classification") != cls and row.get("classification") != cls:
            return False
        if row.get("last_success") is not None:
            return False
        if row.get("connector_up") is not False:
            return False
    return True


def build_board() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    board = _intg.build_board(persist_audit=False)
    stamps = _connection_stamps(board)
    focal = _focal_stamps(stamps)
    conn_p = conn_health_preserved()
    intg_p = intg_truth1_preserved()
    yan = next((s for s in focal if s.get("integration_id") == "INT-YAN-WOLF"), {})
    class_counts = _class_counts(stamps)
    by_audit = dict((board.get("counts") or {}).get("by_audit_status") or {})
    blocked = int((board.get("counts") or {}).get("blocked_external") or 0)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": ["connections"],
        "title": "Connector health deepen — Wave7/8 per-connector honesty",
        "classification": CLASSIFICATION,
        "action": ACTION,
        "ceiling": CEILING,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "write_authority": WRITE_AUTHORITY,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "invented_last_success": False,
        "fake_last_success": False,
        "fake_up": False,
        "fake_connector_up": False,
        "connector_up": False,
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
        "by_wave78_classification": class_counts,
        "connection_stamps": stamps,
        "focal_stamps": focal,
        "yanolja": yan,
        "conn_health_preserved": conn_p.get("ok") is True,
        "intg_truth1_preserved": intg_p.get("ok") is True,
        "conn_health": conn_p,
        "intg_truth1": intg_p,
        "honesty_tiles": _honesty_tiles(focal, conn_p, intg_p, class_counts),
        "desk_links": _desk_links(),
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "connector_up",
            "live_connector_success",
            "last_success",
            "yanolja_unblocked",
            "external_connectors_live",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "pins": flags.get("pins"),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "summary": (
            "Connector health deepen. Wave7/8 classifications per connector. "
            "No invent last_success. No fake UP. "
            "CONN-HEALTH + INTG-TRUTH-1 preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def build_slice() -> dict[str, Any]:
    return build_board()


def public_payload() -> dict[str, Any]:
    return build_board()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "last_success_property": False,
        "invented_last_success": False,
        "fake_up": False,
        "connector_up": False,
        "yanolja_unblocked": False,
        "writes_accepted": False,
        "unblock_accepted": False,
        "classification": CLASSIFICATION,
        "preserves": list(PRESERVED_PACKS),
        "focal_ids": list(_FOCAL_IDS),
        "wave78_focal": {
            iid: _WAVE78[iid]["classification"] for iid in _FOCAL_IDS if iid in _WAVE78
        },
        "why": (
            "Connector health deepen with Wave7/8 classifications. "
            "Stamps without inventing last_success. No fake UP. BLOCKED stays BLOCKED."
        ),
    }
