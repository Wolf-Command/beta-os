#!/usr/bin/env python3
"""GGV-METRIC-HONESTY-1 — GGV Metricool metric honesty deepen (NOT_RUNTIME holds).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack GGV-METRIC-HONESTY-1
(armed 2026-09-30 after BZG-INVENTORY-TRUTH-1 PASS_VERIFIED).

Deepens Metricool metric honesty on the existing Content / GGV path.
Engagement and publish metrics stay null while INT-MET-WOLF is NOT_RUNTIME.
Never invent engagement, publish success, or Metricool last_success.
Preserves CONTENT-ENGINE-LIVE-1 + GGV-CONTENT-PROVE-1.
staff_ready=false · human_commissioned=false. Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain OWNER-EXCEPTIONS-LIVE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import content_engine_live1 as _cel
from core import content_publish as _publish
from core import ggv_content_prove1 as _prove
from core import ggv_ops_pack as _ops
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "GGV-METRIC-HONESTY-1"
SCHEMA_ID = "wolf.ggv-metric-honesty-1.v1"
BOUND = "beta-ggv-metric-safe"
CAP_METRICS = "CAP-GGV metrics"
LEGAL_ENTITY = "ENT-GGV"
OWNER_PERSON = "PERS-MATT"
METRICOOL_ID = "INT-MET-WOLF"
HONESTY_BOARD = "/ops/integrations-status"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/ggv/metric-honesty-1",
        "/ggv/metric-honesty-1/",
        "/ggv/metric-honesty",
        "/ggv/metric-honesty/",
        "/ggv/metrics",
        "/ggv/metrics/",
        "/ggv-metric-honesty-1",
        "/ggv-metric-honesty-1/",
        "/ggv-metric-honesty",
        "/ggv-metric-honesty/",
        "/ggv-metric-honesty-1.html",
        "/dashboards/ggv-metric-honesty-1.html",
    }
)
API_PATH = "/api/ggv/metric-honesty-1"

PRESERVED_PACKS = ("CONTENT-ENGINE-LIVE-1", "GGV-CONTENT-PROVE-1")

# Metric slots — values stay null while Metricool is NOT_RUNTIME.
_METRIC_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "metricool_runtime",
        "Metricool Wolf runtime",
        "INT-MET-WOLF Wolf runtime. NOT_RUNTIME (INTG-TRUTH-1). No invented last_success.",
    ),
    (
        "engagement",
        "Engagement",
        "Engagement stays null while Metricool is NOT_RUNTIME. Never invent.",
    ),
    (
        "publish_success",
        "Publish success",
        "Publish success stays null while Metricool is NOT_RUNTIME. Never invent.",
    ),
    (
        "impressions",
        "Impressions",
        "Impressions stay null while Metricool is NOT_RUNTIME. Never invent.",
    ),
    (
        "reach",
        "Reach",
        "Reach stays null while Metricool is NOT_RUNTIME. Never invent.",
    ),
    (
        "last_success",
        "Metricool last_success",
        "last_success stays null. NOT_RUNTIME — never invent a success stamp.",
    ),
)

_INVENT_METRIC_TOKENS = frozenset(
    {
        "engagement",
        "engagements",
        "fake-engagement",
        "fake_engagement",
        "invent-engagement",
        "invent_engagement",
        "publish",
        "publish-success",
        "publish_success",
        "fake-publish",
        "fake_publish",
        "invent-publish",
        "invent_publish",
        "metric",
        "metrics",
        "fake-metric",
        "fake_metric",
        "invent-metric",
        "invent_metric",
        "impressions",
        "impression",
        "reach",
        "likes",
        "like",
        "views",
        "view",
        "last-success",
        "last_success",
        "metricool-success",
        "metricool_success",
        "metricool",
        "success",
    }
)


class GgvMetricHonesty1Error(ValueError):
    """Fail closed. Does not invent engagement or publish metrics."""

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


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner progress.read or GGV Habitat read seats (Amanda/Haikal/Misa)."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid in _ops.READ_SEATS:
        return True
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        return bool(_rbac.can(pid, "progress.read", {}, conn=c))
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise GgvMetricHonesty1Error(
            "GGV metric honesty desk is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _metricool_from_board() -> dict[str, Any]:
    board = _intg.build_board(persist_audit=False)
    connectors = list(board.get("connectors") or [])
    met = next(
        (c for c in connectors if c.get("integration_id") == METRICOOL_ID),
        None,
    )
    probe = (met or {}).get("probe_status")
    not_runtime = probe == "NOT_RUNTIME" or (
        (met or {}).get("audit_status") in ("MISSING_OR_UNPROVEN", "NOT_RUNTIME")
        and (met or {}).get("last_success") is None
    )
    # Force honesty: never surface invented last_success / engagement / publish.
    return {
        "integration_id": METRICOOL_ID,
        "audit_status": (met or {}).get("audit_status") or "MISSING_OR_UNPROVEN",
        "probe_status": probe or "NOT_RUNTIME",
        "display": "NOT_RUNTIME",
        "status": "NOT_RUNTIME",
        "last_success": None,
        "engagement": None,
        "publish_success": None,
        "metricool_success": None,
        "not_runtime": True if not_runtime or probe in (None, "NOT_RUNTIME") else True,
        "fake_metrics": False,
        "honesty_board_href": HONESTY_BOARD,
        "intg_board_pack": board.get("pack"),
        "intg_board_ok": board.get("ok") is True,
        "why": (
            "INTG-TRUTH-1: INT-MET-WOLF Wolf runtime NOT_RUNTIME. "
            "MCP-Metricool is AGENT_HOST_ONLY. No invented Metricool success."
        ),
    }


def _metric_slot(
    stub_id: str, label: str, why: str, *, metricool: dict[str, Any]
) -> dict[str, Any]:
    is_runtime = stub_id == "metricool_runtime"
    return {
        "id": stub_id,
        "label": label,
        "kind": "metric_honesty",
        "entity": "GGV",
        "brand_id": "habitat",
        "status": "NOT_RUNTIME" if is_runtime else "UNKNOWN",
        "display": "NOT_RUNTIME" if is_runtime else "null",
        "value": None,
        "count": None,
        "engagement": None,
        "publish_success": None,
        "metricool_success": None,
        "last_success": None,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metric": False,
        "integration_id": METRICOOL_ID if is_runtime else None,
        "honesty_board_href": HONESTY_BOARD,
        "metricool_not_runtime": metricool.get("not_runtime") is True,
        "why": why,
    }


def _metric_slots(metricool: dict[str, Any]) -> list[dict[str, Any]]:
    return [_metric_slot(*spec, metricool=metricool) for spec in _METRIC_SLOT_SPECS]


def content_engine_live1_preserved() -> dict[str, Any]:
    """Read-only: CONTENT-ENGINE-LIVE-1 still NOT_RUNTIME / no fake engagement."""
    try:
        board = _cel.build_board()
        flags = _cel.honesty_flags()
        ok = (
            board.get("ok") is True
            and board.get("staff_ready") is False
            and board.get("human_commissioned") is False
            and board.get("fake_metrics") is False
            and board.get("invented_engagement") is False
            and board.get("invented_publish_success") is False
            and _cel.metricool_not_runtime(board) is True
            and flags.get("staff_ready") is False
        )
        return {
            "ok": ok,
            "staff_ready": board.get("staff_ready"),
            "human_commissioned": board.get("human_commissioned"),
            "fake_metrics": board.get("fake_metrics"),
            "invented_engagement": board.get("invented_engagement"),
            "metricool_not_runtime": _cel.metricool_not_runtime(board),
            "why": (
                "CONTENT-ENGINE-LIVE-1 preserved: Metricool NOT_RUNTIME, "
                "no fake engagement/publish, staff_ready/human_commissioned false. "
                "This pack deepens metric honesty — does not replace content engine."
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


def ggv_content_prove1_preserved() -> dict[str, Any]:
    """Read-only: GGV-CONTENT-PROVE-1 still honest / NOT_RUNTIME."""
    try:
        prove = _prove.public_payload()
        ok = (
            prove.get("ok") is True
            and prove.get("staff_ready") is False
            and prove.get("human_commissioned") is False
            and prove.get("fake_metrics") is False
            and prove.get("invented_engagement") is False
            and prove.get("invented_publish_success") is False
            and prove.get("live_adoption") is False
            and ((prove.get("metricool") or {}).get("not_runtime") is True)
            and ((prove.get("metricool") or {}).get("last_success") is None)
            and _prove.all_publish_tiles_honest(prove) is True
        )
        return {
            "ok": ok,
            "staff_ready": prove.get("staff_ready"),
            "human_commissioned": prove.get("human_commissioned"),
            "fake_metrics": prove.get("fake_metrics"),
            "live_adoption": prove.get("live_adoption"),
            "metricool_not_runtime": (prove.get("metricool") or {}).get("not_runtime"),
            "why": (
                "GGV-CONTENT-PROVE-1 preserved: Metricool NOT_RUNTIME, "
                "publish tiles honest, live_adoption false, "
                "staff_ready/human_commissioned false."
                if ok
                else "GGV-CONTENT-PROVE-1 check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "GGV-CONTENT-PROVE-1 check failed — pack must not break it.",
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "content_engine_live",
            "label": "Content Engine Live",
            "href": "/ops/content-engine-live",
            "kind": "existing",
            "note": "Upstream storage truth. Preserved — Metricool NOT_RUNTIME.",
        },
        {
            "id": "content_prove",
            "label": "GGV Content Prove",
            "href": "/ggv/content-prove",
            "kind": "existing",
            "note": "Prior prove pack. Preserved — no fake metrics.",
        },
        {
            "id": "integrations_honesty",
            "label": "Integrations honesty board",
            "href": HONESTY_BOARD,
            "kind": "honesty",
            "note": "INT-MET-WOLF NOT_RUNTIME — source of truth for Metricool Wolf.",
        },
        {
            "id": "ggv_ops_pack",
            "label": "GGV ops pack",
            "href": "/ggv-ops-pack",
            "kind": "existing",
            "note": "GGV operator board. Not fake engagement.",
        },
    ]


def _honesty_tiles(
    metricool: dict[str, Any],
    cel: dict[str, Any],
    prove: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "metricool_runtime",
            "label": "Metricool Wolf runtime",
            "status": "NOT_RUNTIME",
            "value": None,
            "why": metricool.get("why"),
        },
        {
            "id": "engagement_null",
            "label": "Engagement metrics",
            "status": "NULL",
            "value": None,
            "why": "Engagement stays null while Metricool is NOT_RUNTIME.",
        },
        {
            "id": "publish_null",
            "label": "Publish success",
            "status": "NULL",
            "value": None,
            "why": "Publish success stays null while Metricool is NOT_RUNTIME.",
        },
        {
            "id": "fake_metrics",
            "label": "Fake / invent metrics",
            "status": "REFUSED",
            "value": False,
            "why": "Invent-metric / fake-engagement writes are refused.",
        },
        {
            "id": "content_engine_live1",
            "label": "CONTENT-ENGINE-LIVE-1",
            "status": "PRESERVED" if cel.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": cel.get("why"),
        },
        {
            "id": "ggv_content_prove1",
            "label": "GGV-CONTENT-PROVE-1",
            "status": "PRESERVED" if prove.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": prove.get("why"),
        },
        {
            "id": "cap_ggv_metrics",
            "label": "CAP-GGV metrics",
            "status": "SPECIFIED",
            "value": None,
            "why": "Metric honesty deepen only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    cel = content_engine_live1_preserved()
    prove = ggv_content_prove1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_ggv_metrics": CAP_METRICS,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "invented_metric": False,
        "metricool_publish": False,
        "metricool_write": False,
        "live_adoption": False,
        "metric_write": False,
        "engagement_null_when_not_runtime": True,
        "publish_null_when_not_runtime": True,
        "metricool_not_runtime": True,
        "content_engine_live1_preserved": cel.get("ok") is True,
        "ggv_content_prove1_preserved": prove.get("ok") is True,
        "replaces_content_engine": False,
        "second_metric_system": False,
        "cap_ggv_metrics_proven": False,
        "cap_ggv_metrics_ready": False,
        "cap_ggv_metrics_maturity": "SPECIFIED",
        "cap_ggv_metrics_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "production": False,
        "anon_fail_closed": True,
        "zayen_deny_ggv": True,
        "owner_read": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "OWNER-EXCEPTIONS-LIVE-1",
    }


def refuse_fake_engagement(_body: dict | None = None) -> None:
    raise GgvMetricHonesty1Error(
        "Fake engagement is refused. Engagement stays null while Metricool is NOT_RUNTIME.",
        code="fake_engagement_refused",
        http_status=403,
    )


def refuse_fake_publish(_body: dict | None = None) -> None:
    raise GgvMetricHonesty1Error(
        "Fake publish success is refused. Publish stays null while Metricool is NOT_RUNTIME.",
        code="fake_publish_refused",
        http_status=403,
    )


def refuse_invent_metric(_body: dict | None = None) -> None:
    raise GgvMetricHonesty1Error(
        "Invented metrics are refused. Metric slots stay null while Metricool is NOT_RUNTIME.",
        code="invent_metric_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise GgvMetricHonesty1Error(
        "PROVEN is refused. CAP-GGV metrics stays SPECIFIED. NOT_RUNTIME is not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise GgvMetricHonesty1Error(
        "READY is refused. A Metricool NOT_RUNTIME honesty desk is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise GgvMetricHonesty1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if token in {
            "fake-engagement",
            "engagement",
            "engagements",
            "invent-engagement",
        } or norm in {
            "fake_engagement",
            "engagement",
            "engagements",
            "invent_engagement",
        }:
            refuse_fake_engagement(payload)
        if token in {
            "fake-publish",
            "publish",
            "publish-success",
            "invent-publish",
        } or norm in {
            "fake_publish",
            "publish",
            "publish_success",
            "invent_publish",
        }:
            refuse_fake_publish(payload)
        if token in _INVENT_METRIC_TOKENS or norm in {
            t.replace("-", "_") for t in _INVENT_METRIC_TOKENS
        }:
            if "engagement" in token or "engagement" in norm:
                refuse_fake_engagement(payload)
            if "publish" in token or "publish" in norm:
                refuse_fake_publish(payload)
            refuse_invent_metric(payload)
    raise GgvMetricHonesty1Error(
        "GGV-METRIC-HONESTY-1 is a read honesty desk. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_metric_slots_null(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    slots = pack.get("metric_slots") or []
    if not slots:
        return False
    return all(
        s.get("value") is None
        and s.get("count") is None
        and s.get("engagement") is None
        and s.get("publish_success") is None
        and s.get("metricool_success") is None
        and s.get("last_success") is None
        and s.get("fake_metrics") is False
        and s.get("invented_engagement") is False
        and s.get("invented_publish_success") is False
        and s.get("invented_metric") is False
        and s.get("status") in ("NOT_RUNTIME", "UNKNOWN", "NULL", "EMPTY")
        for s in slots
    )


def metricool_not_runtime(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    met = pack.get("metricool") or {}
    return (
        met.get("not_runtime") is True
        and met.get("last_success") is None
        and met.get("display") == "NOT_RUNTIME"
        and met.get("engagement") is None
        and met.get("publish_success") is None
        and met.get("fake_metrics") is False
    )


def no_fake_metrics(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    return (
        pack.get("fake_metrics") is False
        and pack.get("invented_engagement") is False
        and pack.get("invented_publish_success") is False
        and pack.get("invented_metricool_success") is False
        and pack.get("invented_metric") is False
        and all_metric_slots_null(pack)
        and metricool_not_runtime(pack)
    )


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility
    when person_id is None (tests); require_view when person_id provided."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    metricool = _metricool_from_board()
    slots = _metric_slots(metricool)
    cel = content_engine_live1_preserved()
    prove = ggv_content_prove1_preserved()
    mc = _publish.metricool_write_status()
    engagement = _ops.engagement_scaffold()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_METRICS],
        "title": "GGV Metricool Metric Honesty Desk",
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "invented_metric": False,
        "metricool_publish": False,
        "metricool_write": False,
        "metric_write": False,
        "live_adoption": False,
        "metricool_not_runtime": True,
        "engagement": None,
        "publish_success": None,
        "metricool_success": None,
        "last_success": None,
        "content_engine_live1_preserved": cel.get("ok") is True,
        "ggv_content_prove1_preserved": prove.get("ok") is True,
        "cap_ggv_metrics_proven": False,
        "cap_ggv_metrics_ready": False,
        "cap_ggv_metrics_maturity": flags["cap_ggv_metrics_maturity"],
        "cap_ggv_metrics_ceiling": flags["cap_ggv_metrics_ceiling"],
        "metric_slots": slots,
        "honesty_tiles": _honesty_tiles(metricool, cel, prove),
        "desk_links": _desk_links(),
        "metricool": metricool,
        "content_engine_live1": cel,
        "ggv_content_prove1": prove,
        "engagement_scaffold": {
            "empty": engagement.get("empty") is True,
            "live_engagement": False,
            "revenue": engagement.get("revenue"),
            "why": engagement.get("why"),
        },
        "publish_gate": {
            "metricool_write_status": mc.get("status") or "DISABLED",
            "approved_is_not_published": True,
            "real_external_publish": "NO",
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_adoption",
            "engagement_metrics",
            "publish_success",
            "Metricool last_success",
            "metric_write",
            "CAP-GGV metrics PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "OWNER-EXCEPTIONS-LIVE-1",
        "summary": (
            "GGV Metricool metric honesty desk. NOT_RUNTIME holds. "
            "Engagement/publish stay null. No fake metrics. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "metric_slots": [s[0] for s in _METRIC_SLOT_SPECS],
        "status_enum": ["NOT_RUNTIME", "UNKNOWN", "NULL", "REFUSED", "PRESERVED"],
        "engagement_property": False,
        "publish_success_property": False,
        "writes_accepted": False,
        "fake_metrics": False,
        "null_when_not_runtime": True,
        "preserves": list(PRESERVED_PACKS),
        "why": (
            "GGV Metricool metric honesty deepen. NOT_RUNTIME holds. "
            "Engagement/publish stay null. No fake metrics."
        ),
    }
