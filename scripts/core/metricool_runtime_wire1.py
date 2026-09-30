#!/usr/bin/env python3
"""METRICOOL-RUNTIME-WIRE-1 — Authorised Metricool runtime into Beta.

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
METRICOOL-RUNTIME-WIRE-1 (armed 2026-09-30 after PIPE-RELIABILITY-AUTO-1
PASS_VERIFIED). Challenges overnight blanket NOT_RUNTIME honesty ceiling
(GGV-METRIC-HONESTY-1). Does NOT re-do GGV-METRIC.

Wires Beta board/API to authorised Metricool brand stamps + available
analytics paths (MCP evidence). Per-surface honesty:
RUNTIME_WIRED | NOT_RUNTIME | EXTERNAL_BLOCKER.

Never invents engagement / last_success / publish metric values.
Preserves GGV-METRIC-HONESTY-1 + CONTENT-ENGINE-LIVE-1 where values still
unavailable. staff_ready=false · human_commissioned=false.
Does not auto-chain ESB-SETTLEMENT-PATH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "METRICOOL-RUNTIME-WIRE-1"
SCHEMA_ID = "wolf.metricool-runtime-wire-1.v1"
BOUND = "beta-metricool-runtime-safe"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
CLOSES_TOWARD = ("CAP-GGV metrics", "INT-MET-WOLF")
PRESERVED_PACKS = ("GGV-METRIC-HONESTY-1", "CONTENT-ENGINE-LIVE-1")
METRICOOL_ID = "INT-MET-WOLF"
MCP_ID = "MCP-Metricool"
HONESTY_BOARD = "/ops/integrations-status"

PAGE_PATHS = frozenset(
    {
        "/ops/metricool-runtime-wire-1",
        "/ops/metricool-runtime-wire-1/",
        "/ops/metricool-runtime",
        "/ops/metricool-runtime/",
        "/metricool-runtime-wire-1",
        "/metricool-runtime-wire-1/",
        "/metricool-runtime-wire-1.html",
        "/dashboards/metricool-runtime-wire-1.html",
        "/ggv/metricool-runtime-wire-1",
        "/ggv/metricool-runtime-wire-1/",
    }
)
API_PATH = "/api/ops/metricool-runtime-wire-1"

STATUS_VOCAB = frozenset({"RUNTIME_WIRED", "NOT_RUNTIME", "EXTERNAL_BLOCKER"})

# Authorised MCP getBrandSettings evidence (CLASSIFICATION-LOG-20260930).
# blogIds from prior Metricool READ audit (WOLF-METRICOOL-READ-AUDIT) —
# same 6 live workspaces; labels match MCP stamp.
AUTHORISED_BRANDS: tuple[dict[str, Any], ...] = (
    {
        "label": "Atrium Lombok",
        "blog_id": 6260617,
        "wolf_slug": "atrium",
        "entity": "AMG",
    },
    {
        "label": "Goss Group",
        "blog_id": 6260628,
        "wolf_slug": "goss",
        "entity": "GGV",
    },
    {
        "label": "Uma Blu",
        "blog_id": 6260631,
        "wolf_slug": "uma_blu",
        "entity": "BZG",
        "live_label_note": "MCP/live: Uma Blu Coffee & Brunch",
    },
    {
        "label": "Habitat",
        "blog_id": 6260634,
        "wolf_slug": "habitat",
        "entity": "GGV",
        "live_label_note": "MCP/live: The Habitat",
    },
    {
        "label": "Selo",
        "blog_id": 6260635,
        "wolf_slug": "selo",
        "entity": "GGV",
        "live_label_note": "MCP/live: Selo Properties",
    },
    {
        "label": "Tropik",
        "blog_id": 6260638,
        "wolf_slug": "tropik",
        "entity": "GGV",
        "live_label_note": "MCP/live: Tropik Resort Lombok",
    },
)

# Authorised MCP getAnalyticsAvailableMetrics(instagram, posts):
# 29 fields incl engagement/likes/reach — stamp catalog availability only.
# Do not invent a fabricated 29-name list this session.
ANALYTICS_PATH_EVIDENCE: dict[str, Any] = {
    "network": "instagram",
    "surface": "posts",
    "mcp_tool": "getAnalyticsAvailableMetrics",
    "field_count": 29,
    "proven_includes": ("engagement", "likes", "reach"),
    "evidence": (
        "state/final-completion/CLASSIFICATION-LOG-20260930.json"
        "#metricool_runtime_probe"
    ),
    "values_fetched": False,
}

MCP_EVIDENCE: dict[str, Any] = {
    "server": "user-Metricool",
    "server_status": "ready",
    "getBrandSettings": "6 brands",
    "getAnalyticsAvailableMetrics_instagram_posts": (
        "29 fields incl engagement/likes/reach"
    ),
    "evidence": (
        "state/final-completion/CLASSIFICATION-LOG-20260930.json"
        "#metricool_runtime_probe"
    ),
}


class MetricoolRuntimeWire1Error(ValueError):
    """Fail closed. Does not invent engagement or Metricool success."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
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


def _wolf_http_connector_status() -> dict[str, Any]:
    """status() only — no credential load, no network."""
    try:
        import metricool_read_client as metricool

        st = metricool.metricool_status()
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "wolf_http_connector",
            "label": "Wolf Beta HTTP Metricool connector",
            "status": "EXTERNAL_BLOCKER",
            "enabled": False,
            "write_enabled": False,
            "last_success": None,
            "engagement": None,
            "why": (
                f"metricool_status() failed ({type(exc).__name__}). "
                "No invented success. EXTERNAL_BLOCKER with evidence."
            ),
            "evidence": "metricool_read_client.metricool_status",
        }
    enabled = bool(st.get("enabled"))
    if not enabled:
        return {
            "id": "wolf_http_connector",
            "label": "Wolf Beta HTTP Metricool connector",
            "status": "EXTERNAL_BLOCKER",
            "enabled": False,
            "write_enabled": bool(st.get("write_enabled")),
            "connected": bool(st.get("connected")),
            "raw_status": st.get("status"),
            "last_success": None,
            "engagement": None,
            "why": (
                "BETA_METRICOOL_ENABLED=false — Wolf product HTTP path fail-closed. "
                "MCP brands/analytics catalog are RUNTIME_WIRED separately; "
                "live engagement/last_success values stay unavailable here. "
                "EXTERNAL_BLOCKER evidenced — not invented GREEN."
            ),
            "evidence": "metricool_read_client.metricool_status + .env gate",
        }
    # Enabled but this pack still does not invent live values without a prove pull.
    return {
        "id": "wolf_http_connector",
        "label": "Wolf Beta HTTP Metricool connector",
        "status": "NOT_RUNTIME",
        "enabled": True,
        "write_enabled": bool(st.get("write_enabled")),
        "connected": bool(st.get("connected")),
        "raw_status": st.get("status"),
        "last_success": None,
        "engagement": None,
        "why": (
            "BETA_METRICOOL_ENABLED is on but this pack does not invent "
            "engagement/last_success without an authorised live pull prove. "
            "NOT_RUNTIME for values."
        ),
        "evidence": "metricool_read_client.metricool_status",
    }


def brand_stamps() -> list[dict[str, Any]]:
    """Authorised brand stamps — RUNTIME_WIRED. No engagement invented."""
    out: list[dict[str, Any]] = []
    for b in AUTHORISED_BRANDS:
        out.append(
            {
                **b,
                "status": "RUNTIME_WIRED",
                "source": "MCP getBrandSettings (authorised)",
                "engagement": None,
                "last_success": None,
                "publish_success": None,
                "fake_metrics": False,
            }
        )
    return out


def surface_stamps(*, wolf_http: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Per-surface honesty stamps. Values stay null where not fetched."""
    http = wolf_http if wolf_http is not None else _wolf_http_connector_status()
    brands = brand_stamps()
    return [
        {
            "id": "mcp_server",
            "label": "Metricool MCP server",
            "status": "RUNTIME_WIRED",
            "value": MCP_EVIDENCE["server_status"],
            "last_success": None,
            "engagement": None,
            "why": (
                f"{MCP_EVIDENCE['server']} serverStatus={MCP_EVIDENCE['server_status']} "
                "(authorised evidence). Agent-host MCP stamped into Beta board."
            ),
            "evidence": MCP_EVIDENCE["evidence"],
        },
        {
            "id": "brand_stamps",
            "label": "Brand stamps (getBrandSettings)",
            "status": "RUNTIME_WIRED",
            "value": len(brands),
            "brand_count": len(brands),
            "brands": [b["label"] for b in brands],
            "last_success": None,
            "engagement": None,
            "why": (
                "6 authorised brands stamped: Atrium Lombok, Goss Group, Uma Blu, "
                "Habitat, Selo, Tropik. No invented engagement per brand."
            ),
            "evidence": MCP_EVIDENCE["evidence"],
        },
        {
            "id": "analytics_paths_instagram_posts",
            "label": "Analytics paths (IG posts)",
            "status": "RUNTIME_WIRED",
            "value": ANALYTICS_PATH_EVIDENCE["field_count"],
            "field_count": ANALYTICS_PATH_EVIDENCE["field_count"],
            "proven_includes": list(ANALYTICS_PATH_EVIDENCE["proven_includes"]),
            "network": ANALYTICS_PATH_EVIDENCE["network"],
            "surface": ANALYTICS_PATH_EVIDENCE["surface"],
            "values_fetched": False,
            "last_success": None,
            "engagement": None,
            "why": (
                "getAnalyticsAvailableMetrics(instagram, posts) → 29 fields "
                "incl engagement/likes/reach. Catalog path RUNTIME_WIRED; "
                "numeric values not fetched — stay null (GGV honesty)."
            ),
            "evidence": ANALYTICS_PATH_EVIDENCE["evidence"],
        },
        {
            "id": "engagement_values",
            "label": "Engagement values",
            "status": "NOT_RUNTIME",
            "value": None,
            "engagement": None,
            "last_success": None,
            "why": (
                "Engagement numbers stay null. Catalog path is RUNTIME_WIRED; "
                "live values not pulled into Beta this pack. "
                "Preserves GGV-METRIC-HONESTY-1 — never invent."
            ),
            "evidence": "GGV-METRIC-HONESTY-1 + pack forbids fake engagement",
        },
        {
            "id": "last_success",
            "label": "Metricool last_success",
            "status": "NOT_RUNTIME",
            "value": None,
            "last_success": None,
            "engagement": None,
            "why": (
                "last_success stays null. Brand/catalog RUNTIME_WIRED is not a "
                "publish/sync success stamp. Never invent."
            ),
            "evidence": "INTG / GGV honesty — null_if_unknown_never_invent",
        },
        {
            "id": "publish_success",
            "label": "Publish success",
            "status": "NOT_RUNTIME",
            "value": None,
            "publish_success": None,
            "last_success": None,
            "engagement": None,
            "why": (
                "Publish success stays null. Metricool write stays disabled. "
                "Never invent publish metrics."
            ),
            "evidence": "BETA_METRICOOL_WRITE_ENABLED fail-closed + pack forbids",
        },
        {
            "id": http["id"],
            "label": http["label"],
            "status": http["status"],
            "value": http.get("raw_status") or http.get("enabled"),
            "enabled": http.get("enabled"),
            "write_enabled": http.get("write_enabled"),
            "last_success": None,
            "engagement": None,
            "why": http.get("why"),
            "evidence": http.get("evidence"),
        },
    ]


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "invented_last_success": False,
        "metricool_publish": False,
        "metricool_write": False,
        "live_adoption": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "ggv_metric_honesty1_preserved": True,
        "content_engine_live1_preserved": True,
        "blanket_not_runtime_replaced": True,
        "per_surface_honesty": True,
        "status_vocab": "RUNTIME_WIRED|NOT_RUNTIME|EXTERNAL_BLOCKER",
        "next_pack_for_parent_only": "ESB-SETTLEMENT-PATH-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
    }


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise MetricoolRuntimeWire1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "engagement",
            "engagements",
            "fake-engagement",
            "invent-engagement",
            "likes",
            "reach",
            "impressions",
            "views",
        } or norm in {
            "fake_engagement",
            "invent_engagement",
            "engagement",
            "likes",
            "reach",
        }:
            raise MetricoolRuntimeWire1Error(
                "Engagement / invent-metric refused. Values stay null when not fetched.",
                code="engagement_refused",
            )
        if token in {
            "last-success",
            "metricool-success",
            "publish",
            "publish-success",
            "fake-publish",
            "invent-publish",
            "fake-metric",
            "invent-metric",
            "metrics",
        } or norm in {
            "last_success",
            "metricool_success",
            "publish_success",
            "fake_publish",
            "invent_publish",
            "fake_metric",
            "invent_metric",
        }:
            raise MetricoolRuntimeWire1Error(
                "Invented last_success / publish / metrics refused.",
                code="invent_metric_refused",
            )
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        }:
            raise MetricoolRuntimeWire1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
        }:
            raise MetricoolRuntimeWire1Error(
                "Commissioning flags / PROVEN / READY are refused.",
                code="ready_refused",
            )
    raise MetricoolRuntimeWire1Error(
        "METRICOOL-RUNTIME-WIRE-1 is a read-only runtime stamp board. Writes refused.",
        code="write_refused",
    )


def refuse_fake_engagement(_body: dict | None = None) -> None:
    raise MetricoolRuntimeWire1Error(
        "Fake engagement refused. Engagement stays null when not fetched.",
        code="engagement_refused",
    )


def refuse_invent_metric(_body: dict | None = None) -> None:
    raise MetricoolRuntimeWire1Error(
        "Invented metrics refused. Never invent last_success / publish / engagement.",
        code="invent_metric_refused",
    )


def ggv_metric_honesty1_preserved() -> dict[str, Any]:
    """Read-only: GGV-METRIC-HONESTY-1 still refuses fake engagement.

    Uses honesty_flags() only — avoids build_slice → intg.build_board recursion
    when this pack is called from INTG overlay paths.
    """
    try:
        from core import ggv_metric_honesty1 as _ggv

        flags = _ggv.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("fake_metrics") is False
            and flags.get("invented_engagement") is False
            and flags.get("metricool_not_runtime") is True
            and flags.get("content_engine_live1_preserved") is True
        )
        return {
            "ok": ok,
            "pack": "GGV-METRIC-HONESTY-1",
            "engagement": None,
            "last_success": None,
            "fake_metrics": flags.get("fake_metrics"),
            "metricool_not_runtime": flags.get("metricool_not_runtime"),
            "why": (
                "GGV-METRIC-HONESTY-1 preserved: engagement/publish/last_success null; "
                "fake_metrics false. This pack adds per-surface RUNTIME_WIRED for "
                "brands/analytics catalog — does not invent GGV metric values."
                if ok
                else "GGV-METRIC-HONESTY-1 check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "GGV-METRIC-HONESTY-1 check failed — pack must not break it.",
        }


def content_engine_live1_preserved() -> dict[str, Any]:
    """Read-only: CONTENT-ENGINE-LIVE-1 still honest / no fake Metricool success."""
    try:
        from core import content_engine_live1 as _cel

        board = _cel.build_board()
        ok = (
            board.get("ok") is True
            and board.get("staff_ready") is False
            and board.get("human_commissioned") is False
            and board.get("fake_metrics") is False
            and _cel.metricool_not_runtime(board) is True
            and _cel.storage_surfaces_honest(board) is True
        )
        return {
            "ok": ok,
            "pack": "CONTENT-ENGINE-LIVE-1",
            "fake_metrics": board.get("fake_metrics"),
            "metricool_not_runtime": _cel.metricool_not_runtime(board),
            "why": (
                "CONTENT-ENGINE-LIVE-1 preserved: Metricool values still NOT_RUNTIME "
                "on content board; no invented engagement/publish."
                if ok
                else "CONTENT-ENGINE-LIVE-1 check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "CONTENT-ENGINE-LIVE-1 check failed — pack must not break it.",
        }


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when every surface uses allowed vocab and value metrics stay null."""
    pack = payload if payload is not None else build_board()
    if pack.get("fake_metrics") is True or pack.get("invented_engagement") is True:
        return False
    if pack.get("invented_last_success") is True:
        return False
    if pack.get("engagement") is not None or pack.get("last_success") is not None:
        return False
    if pack.get("publish_success") is not None:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 6:
        return False
    wired = 0
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        st = s.get("status")
        if st not in STATUS_VOCAB:
            return False
        if s.get("id") in ("engagement_values", "last_success", "publish_success"):
            if st != "NOT_RUNTIME":
                return False
            if s.get("engagement") is not None or s.get("value") is not None:
                return False
            if s.get("last_success") is not None:
                return False
        if s.get("id") == "brand_stamps" and st == "RUNTIME_WIRED":
            if int(s.get("brand_count") or 0) != 6:
                return False
            wired += 1
        if s.get("id") == "analytics_paths_instagram_posts" and st == "RUNTIME_WIRED":
            if int(s.get("field_count") or 0) != 29:
                return False
            wired += 1
        if s.get("id") == "mcp_server" and st == "RUNTIME_WIRED":
            wired += 1
        if s.get("id") == "wolf_http_connector":
            if st not in ("EXTERNAL_BLOCKER", "NOT_RUNTIME"):
                return False
    brands = pack.get("brands") or []
    if len(brands) != 6:
        return False
    for b in brands:
        if b.get("status") != "RUNTIME_WIRED":
            return False
        if b.get("engagement") is not None or b.get("last_success") is not None:
            return False
    return wired >= 3


def build_board() -> dict[str, Any]:
    """Public Metricool runtime wire board. Auth gating is caller's job."""
    probed_at = _now_wita()
    wolf_http = _wolf_http_connector_status()
    surfaces = surface_stamps(wolf_http=wolf_http)
    brands = brand_stamps()
    ggv = ggv_metric_honesty1_preserved()
    cel = content_engine_live1_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": probed_at,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "invented_last_success": False,
        "engagement": None,
        "publish_success": None,
        "last_success": None,
        "metricool_write": False,
        "metricool_publish": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "integration_id": METRICOOL_ID,
        "mcp_id": MCP_ID,
        "mcp": dict(MCP_EVIDENCE),
        "analytics_path": dict(ANALYTICS_PATH_EVIDENCE),
        "brands": brands,
        "brand_count": len(brands),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "wolf_http_connector": wolf_http,
        "honesty": {
            "policy": "per_surface_RUNTIME_WIRED_NOT_RUNTIME_EXTERNAL_BLOCKER",
            "blanket_not_runtime_replaced": True,
            "engagement_policy": "null_when_not_fetched_never_invent",
            "last_success_policy": "null_never_invent",
            "brand_stamps": "RUNTIME_WIRED",
            "analytics_catalog": "RUNTIME_WIRED",
            "engagement_values": "NOT_RUNTIME",
            "wolf_http": wolf_http.get("status"),
        },
        "preserved": {
            "GGV-METRIC-HONESTY-1": ggv,
            "CONTENT-ENGINE-LIVE-1": cel,
        },
        "ggv_metric_honesty1_preserved": ggv.get("ok") is True,
        "content_engine_live1_preserved": cel.get("ok") is True,
        "honesty_board_href": HONESTY_BOARD,
        "next_pack_for_parent_only": "ESB-SETTLEMENT-PATH-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "no_push",
                "per_surface_honesty",
                "status_vocab",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def intg_probe_overlay() -> dict[str, Any]:
    """Compact overlay for INTG-TRUTH-1 INT-MET-WOLF row.

    Light path — does not call build_board() / GGV preserved (avoids INTG↔GGV cycle).
    """
    wolf_http = _wolf_http_connector_status()
    surfaces_list = surface_stamps(wolf_http=wolf_http)
    brands = brand_stamps()
    surfaces = {s["id"]: s.get("status") for s in surfaces_list}
    return {
        "probe_status": "RUNTIME_WIRED_PARTIAL",
        "audit_status": "PARTIAL_IN_BETA",
        "last_success": None,
        "engagement": None,
        "publish_success": None,
        "wolf_runtime": True,  # Beta board wired — not live value sync
        "brand_count": len(brands),
        "analytics_field_count": ANALYTICS_PATH_EVIDENCE["field_count"],
        "surfaces": surfaces,
        "probe_notes": (
            "METRICOOL-RUNTIME-WIRE-1: brands + IG posts analytics catalog "
            "RUNTIME_WIRED from authorised MCP. Engagement/last_success/publish "
            "values NOT_RUNTIME (null). Wolf HTTP connector "
            f"{wolf_http.get('status')}. "
            "No invented metrics."
        ),
        "probe_facts": {
            "pack": PACK_ID,
            "brand_count": len(brands),
            "analytics_field_count": ANALYTICS_PATH_EVIDENCE["field_count"],
            "engagement": None,
            "last_success": None,
            "fake_metrics": False,
            "surfaces": surfaces,
            "wolf_http": wolf_http.get("status"),
        },
        "honesty_summary": "PER_SURFACE",
    }
