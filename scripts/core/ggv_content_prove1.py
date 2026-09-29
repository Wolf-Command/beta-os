#!/usr/bin/env python3
"""GGV-CONTENT-PROVE-1 — GGV Content Machine prove/harden (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack GGV-CONTENT-PROVE-1
(armed 2026-09-30) — prove/harden CAP-GGV-01 / IL-R6 content / MB-006 structure
on the existing Content Machine path. Does NOT invent a second content system.
Does NOT claim LIVE adoption, staff_ready, human_commissioned, or Metricool
publish/engagement success. INT-MET-WOLF stays NOT_RUNTIME (INTG-TRUTH-1).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import content_publish as _publish
from core import ggv_content_ops_depth as _ops_depth
from core import ggv_ops_pack as _ops
from core import ggv_social_derive as _social
from core import ggv_strategy_machine as _strategy
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK = "GGV-CONTENT-PROVE-1"
SCHEMA_ID = "wolf.ggv-content-prove1.v1"
BOUND = "beta-ggv-loop-safe"
HONESTY_BOARD = "/ops/integrations-status"
METRICOOL_ID = "INT-MET-WOLF"
CONTENT_HREF = "/content-2.0"
OPS_DEPTH_ANCHOR = "/content-2.0#content-ops-depth"

PAGE_PATHS = frozenset(
    {
        "/ggv/content-prove",
        "/ggv/content-prove/",
        "/ggv-content-prove",
        "/ggv-content-prove/",
        "/ggv-content-prove.html",
        "/dashboards/ggv-content-prove.html",
    }
)

WITA = timezone(timedelta(hours=8))

# Publish / Metricool dependent slots — honesty stamps, never fake success.
_PUBLISH_TILE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "metricool_runtime",
        "Metricool Wolf runtime",
        "NOT_RUNTIME",
        "INT-MET-WOLF is NOT_RUNTIME (INTG-TRUTH-1). MCP-Metricool is AGENT_HOST_ONLY. "
        "Not a live publish connector. No invented last_success.",
    ),
    (
        "publish_success",
        "Publish / engagement success",
        "UNKNOWN",
        "No invented publish, engagement, or Metricool success metrics. "
        "approved ≠ published. Metricool write DISABLED on Beta.",
    ),
    (
        "live_adoption",
        "LIVE Content Machine adoption",
        "NOT_LIVE",
        "Not LIVE adoption. CAP-GGV-01 ceiling stays BUILT (not PROVEN/READY). "
        "staff_ready=false · human_commissioned=false.",
    ),
)


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
    return raw.rstrip("/") == "/api/ggv/content-prove"


def _publish_tile(tile_id: str, label: str, display: str, why: str) -> dict[str, Any]:
    return {
        "id": tile_id,
        "label": label,
        "kind": "publish_honesty",
        "status": display,
        "display": display,
        "value": None,
        "count": None,
        "engagement": None,
        "publish_success": None,
        "metricool_success": None,
        "fake_metrics": False,
        "integration_id": METRICOOL_ID if tile_id == "metricool_runtime" else None,
        "honesty_board_href": HONESTY_BOARD,
        "why": why,
    }


def _desk_links() -> list[dict[str, Any]]:
    """Existing Content Machine surfaces — not a second system."""
    return [
        {
            "id": "content_desk",
            "label": "Content desk",
            "href": CONTENT_HREF,
            "kind": "existing",
            "note": "Staff Content Machine desk (content-2.0). Not LIVE adoption.",
        },
        {
            "id": "content_ops_depth",
            "label": "Content ops depth",
            "href": OPS_DEPTH_ANCHOR,
            "kind": "existing",
            "note": "Library operator depth — note/tag/handoff only. No Metricool publish.",
        },
        {
            "id": "strategy_machine",
            "label": "Strategy machine",
            "href": "/ggv-strategy-machine",
            "kind": "existing",
            "note": "CAP-GGV-01 skeleton. Empty slots ≠ live strategy machine.",
        },
        {
            "id": "ops_pack",
            "label": "GGV ops pack",
            "href": "/ggv-ops-pack",
            "kind": "existing",
            "note": "GGV operator board + publish gate read. Not fake engagement.",
        },
        {
            "id": "social_derive",
            "label": "Social DERIVE",
            "href": "/ggv-social",
            "kind": "existing",
            "note": "Stored Metricool reads only. metricool_called=false. No write.",
        },
        {
            "id": "integrations_honesty",
            "label": "Integrations honesty board",
            "href": HONESTY_BOARD,
            "kind": "honesty",
            "note": "INT-MET-WOLF NOT_RUNTIME — source of truth for Metricool Wolf runtime.",
        },
    ]


def _metricool_from_board() -> dict[str, Any]:
    board = _intg.build_board(persist_audit=False)
    connectors = list(board.get("connectors") or [])
    met = next(
        (c for c in connectors if c.get("integration_id") == METRICOOL_ID),
        None,
    )
    probe = (met or {}).get("probe_status")
    # INTG-TRUTH-1: Wolf runtime Metricool is NOT_RUNTIME when NOT_CONFIGURED.
    not_runtime = probe == "NOT_RUNTIME" or (
        (met or {}).get("audit_status") in ("MISSING_OR_UNPROVEN", "NOT_RUNTIME")
        and (met or {}).get("last_success") is None
    )
    return {
        "integration_id": METRICOOL_ID,
        "audit_status": (met or {}).get("audit_status") or "MISSING_OR_UNPROVEN",
        "probe_status": probe or "NOT_RUNTIME",
        "last_success": None,
        "not_runtime": True if not_runtime or probe in (None, "NOT_RUNTIME") else False,
        "honesty_board_href": HONESTY_BOARD,
        "intg_board_pack": board.get("pack"),
        "intg_board_ok": board.get("ok") is True,
        "why": (
            "INTG-TRUTH-1: INT-MET-WOLF Wolf runtime NOT_RUNTIME. "
            "MCP-Metricool is AGENT_HOST_ONLY. No invented Metricool success."
        ),
    }


def _prior_honesty_bundle() -> dict[str, Any]:
    """Reuse honesty from existing Content Machine modules."""
    ops_depth = _ops_depth.honesty_flags()
    strategy = _strategy.honesty_flags()
    social = _social.honesty_flags()
    ops = _ops.honesty_flags()
    mc = _publish.metricool_write_status()
    return {
        "content_ops_depth": {
            "staff_ready": ops_depth.get("staff_ready") is False,
            "metricool_publish": ops_depth.get("metricool_publish") is False,
            "invented_metricool_metrics": ops_depth.get("invented_metricool_metrics") is False,
            "proven": ops_depth.get("proven") is False,
            "bound": ops_depth.get("bound"),
        },
        "strategy_machine": {
            "live_strategy_machine": strategy.get("live_strategy_machine") is False,
            "ledger_maturity": strategy.get("ledger_maturity"),
            "maturity_ceiling": strategy.get("maturity_ceiling") or "BUILT",
            "proven": strategy.get("proven") is False,
            "staff_ready": False,
        },
        "social_derive": {
            "metricool_called": social.get("metricool_called") is False,
            "metricool_write": social.get("metricool_write") is False,
        },
        "ops_pack": {
            "staff_ready": ops.get("staff_ready") is False,
            "metricool_publish": ops.get("metricool_publish") is False,
            "metricool_write": ops.get("metricool_write") is False,
        },
        "publish_gate": {
            "metricool_write_status": mc.get("status") or "DISABLED",
            "approved_is_not_published": True,
            "real_external_publish": "NO",
        },
    }


def build_prove(*, refresh_board: bool = False) -> dict[str, Any]:
    """Public prove/harden payload. Auth gating is caller's responsibility."""
    del refresh_board  # symmetry with AMG shell; never persists audit here
    metricool = _metricool_from_board()
    prior = _prior_honesty_bundle()
    publish_tiles = [_publish_tile(*spec) for spec in _PUBLISH_TILE_SPECS]
    engagement = _ops.engagement_scaffold()
    payload = {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "live_adoption": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "metricool_publish": False,
        "metricool_write": False,
        "cap_ggv_01_proven": False,
        "cap_ggv_01_ceiling": "BUILT",
        "closes_toward": ["CAP-GGV-01", "IL-R6 content", "MB-006"],
        "does_not_claim": [
            "LIVE_ADOPTION",
            "staff_ready",
            "human_commissioned",
            "Metricool publish success",
            "engagement success metrics",
        ],
        "publish_honesty_tiles": publish_tiles,
        "desk_links": _desk_links(),
        "metricool": metricool,
        "prior_path_honesty": prior,
        "engagement_scaffold": {
            "empty": engagement.get("empty") is True,
            "live_engagement": False,
            "revenue": engagement.get("revenue"),
            "why": engagement.get("why"),
        },
        "honesty": {
            "metricool_wolf": "NOT_RUNTIME",
            "metricool_mcp": "AGENT_HOST_ONLY",
            "publish_metrics": "UNKNOWN_never_invent",
            "live_adoption": "NOT_LIVE",
            "cap_ggv_01": "BUILT_NOT_PROVEN",
            "staff_ready": False,
            "human_commissioned": False,
            "honesty_board_href": HONESTY_BOARD,
            "extends_existing_path": True,
            "second_content_system": False,
        },
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "CRM-IDENTITY-1",
    }
    return payload


def public_payload() -> dict[str, Any]:
    return build_prove()


def all_publish_tiles_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_prove()
    tiles = pack.get("publish_honesty_tiles") or []
    if not tiles:
        return False
    return all(
        t.get("value") is None
        and t.get("count") is None
        and t.get("engagement") is None
        and t.get("publish_success") is None
        and t.get("metricool_success") is None
        and t.get("fake_metrics") is False
        and t.get("display") in ("NOT_RUNTIME", "UNKNOWN", "NOT_LIVE")
        for t in tiles
    )


def metricool_not_runtime(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_prove()
    met = pack.get("metricool") or {}
    return (
        met.get("not_runtime") is True
        and met.get("last_success") is None
        and met.get("probe_status") == "NOT_RUNTIME"
    )
