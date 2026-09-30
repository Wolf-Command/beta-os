#!/usr/bin/env python3
"""CONTENT-PUBLISH-PATH-1 — Publish path honesty (Metricool write NOT_RUNTIME).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
CONTENT-PUBLISH-PATH-1 (armed 2026-09-30 after CRM-PIPELINE-TRUTH-1
PASS_VERIFIED).

Documents the content publish path. Metricool write stays DISABLED /
NOT_RUNTIME until human-authorised. Never invents publish success.
Preserves METRICOOL-RUNTIME-WIRE-1 engagement-null / publish_success
NOT_RUNTIME honesty, CONTENT-ENGINE-LIVE-1, and GGV-METRIC-HONESTY-1.

staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain OCCUPANCY-EXTERNAL-HOLD-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import content_publish as _publish
from core import ggv_ops_pack as _ops

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
COMMISSION_STAMP = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "CONTENT-PUBLISH-PATH-1-COMMISSION.json"
)

PACK_ID = "CONTENT-PUBLISH-PATH-1"
SCHEMA_ID = "wolf.content-publish-path-1.v1"
BOUND = "beta-content-publish-path-safe"
CAP_PUBLISH = "CAP-GGV publish"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Pack-level (ARM/queue): human must commission write OR external stays blocked.
PACK_CLASSIFICATION = "HUMAN_COMMISSIONING_OR_EXTERNAL"
# Board stamp until Metricool write is authorised.
CLASSIFICATION = "HUMAN_COMMISSIONING"
ACTION = "DOCUMENT_PUBLISH_PATH"
CLOSES_TOWARD = (CAP_PUBLISH, "Metricool write", "CONTENT publish")
PRESERVED_PACKS = (
    "METRICOOL-RUNTIME-WIRE-1",
    "CONTENT-ENGINE-LIVE-1",
    "GGV-METRIC-HONESTY-1",
)

PAGE_PATHS = frozenset(
    {
        "/ops/content-publish-path-1",
        "/ops/content-publish-path-1/",
        "/ops/content-publish-path",
        "/ops/content-publish-path/",
        "/content/publish-path-1",
        "/content/publish-path-1/",
        "/content/publish-path",
        "/content/publish-path/",
        "/content-publish-path-1",
        "/content-publish-path-1/",
        "/content-publish-path-1.html",
        "/dashboards/content-publish-path-1.html",
        "/ggv/content-publish-path-1",
        "/ggv/content-publish-path-1/",
    }
)
API_PATH = "/api/ops/content-publish-path-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ggv/content-publish-path-1",
        "/api/content/publish-path-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "HUMAN_COMMISSIONING",
        "NOT_RUNTIME",
        "DISABLED",
        "PRESERVED",
        "DOCUMENTED",
        "REFUSED",
        "UNKNOWN",
        "EXTERNAL_BLOCKER",
    }
)

PUBLISH_PATH_STEPS: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "title": "Content library / planner slot",
        "detail": (
            "Authorised catalog content_planner slots only. "
            "approved ≠ published. Empty queue is UNKNOWN — never invent."
        ),
    },
    {
        "step": "2",
        "title": "Habitat publish gate (read)",
        "detail": (
            "content_publish.assert_habitat_publish_allowed is a readiness gate "
            "only — it does not call Metricool write or invent publish_success."
        ),
    },
    {
        "step": "3",
        "title": "Metricool write authority",
        "detail": (
            "BETA_METRICOOL_WRITE_ENABLED must be true AND Owner must commission "
            "write. Absent both → write DISABLED / NOT_RUNTIME. This pack never "
            "flips write on."
        ),
    },
    {
        "step": "4",
        "title": "Until authorised: hold honesty",
        "detail": (
            "publish_success=null · engagement=null · last_success=null. "
            "METRICOOL-RUNTIME-WIRE-1 publish_success surface stays NOT_RUNTIME. "
            "Never invent publish success."
        ),
    },
)

_FAKE_PUBLISH_TOKENS = frozenset(
    {
        "publish",
        "publish-success",
        "publish_success",
        "published",
        "auto-publish",
        "auto_publish",
        "fake-publish",
        "fake_publish",
        "invent-publish",
        "invent_publish",
        "invented-publish",
        "invented_publish",
        "force-published",
        "force_published",
        "paint-published",
        "paint_published",
        "metricool-publish",
        "metricool_publish",
        "metricool-write",
        "metricool_write",
        "write-enabled",
        "write_enabled",
        "engagement",
        "fake-engagement",
        "fake_engagement",
        "invent-engagement",
        "invent_engagement",
        "last-success",
        "last_success",
    }
)


class ContentPublishPath1Error(ValueError):
    """Fail closed. Does not invent publish success or enable Metricool write."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 403,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _catalog_ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


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
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


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
        raise ContentPublishPath1Error(
            "Content publish path board is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def commission_stamp_present(*, stamp_path: Path | None = None) -> bool:
    path = Path(stamp_path) if stamp_path is not None else COMMISSION_STAMP
    return path.is_file()


def metricool_write_surface() -> dict[str, Any]:
    """Pack-level hold: always DISABLED / NOT_RUNTIME on this board.

    Observes content_publish.metricool_write_status for evidence only —
    never paints write live or invents publish_success.
    """
    mc = _publish.metricool_write_status()
    env_enabled = bool(mc.get("write_enabled"))
    return {
        "id": "metricool_write",
        "label": "Metricool write",
        "status": "NOT_RUNTIME",
        "write_status": "DISABLED",
        "write_enabled": False,
        "env_write_enabled_observed": env_enabled,
        "real_external_publish": "NO",
        "publish_success": None,
        "engagement": None,
        "last_success": None,
        "commission_stamp_present": commission_stamp_present(),
        "why": (
            "Metricool write stays DISABLED / NOT_RUNTIME until Owner authorises. "
            "CONTENT-PUBLISH-PATH-1 documents the path only — never invents publish."
        ),
        "evidence": "content_publish.metricool_write_status + pack forbids",
    }


def publish_success_surface() -> dict[str, Any]:
    return {
        "id": "publish_success",
        "label": "Publish success",
        "status": "NOT_RUNTIME",
        "value": None,
        "publish_success": None,
        "engagement": None,
        "last_success": None,
        "fact_count": 0,
        "why": (
            "Publish success stays null. Metricool write stays disabled. "
            "Preserves METRICOOL-RUNTIME-WIRE-1 publish_success NOT_RUNTIME."
        ),
        "evidence": "METRICOOL-RUNTIME-WIRE-1 + pack forbids fake publish success",
    }


def engagement_surface() -> dict[str, Any]:
    return {
        "id": "engagement_values",
        "label": "Engagement values",
        "status": "NOT_RUNTIME",
        "value": None,
        "engagement": None,
        "why": (
            "Engagement stays null when not fetched. "
            "Preserves METRICOOL-RUNTIME-WIRE-1 engagement-null honesty."
        ),
        "evidence": "METRICOOL-RUNTIME-WIRE-1 + GGV-METRIC-HONESTY-1",
    }


def path_step_surfaces() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in PUBLISH_PATH_STEPS:
        out.append(
            {
                "id": f"path_step_{step['step']}",
                "step": step["step"],
                "label": step["title"],
                "status": "DOCUMENTED",
                "publish_success": None,
                "why": step["detail"],
            }
        )
    return out


def metricool_runtime_wire1_preserved() -> dict[str, Any]:
    """Read-only: METRICOOL-RUNTIME-WIRE-1 engagement/publish stay NOT_RUNTIME null."""
    try:
        from core import metricool_runtime_wire1 as _mw

        board = _mw.build_board()
        surfaces = {s.get("id"): s for s in (board.get("surfaces") or []) if isinstance(s, dict)}
        pub = surfaces.get("publish_success") or {}
        eng = surfaces.get("engagement_values") or {}
        ok = (
            board.get("ok") is True
            and board.get("staff_ready") is False
            and board.get("human_commissioned") is False
            and board.get("invented_engagement") is False
            and board.get("invented_publish_success") is False
            and board.get("engagement") is None
            and board.get("publish_success") is None
            and board.get("last_success") is None
            and pub.get("status") == "NOT_RUNTIME"
            and eng.get("status") == "NOT_RUNTIME"
            and _mw.surfaces_are_honest(board) is True
        )
        return {
            "ok": ok,
            "pack": "METRICOOL-RUNTIME-WIRE-1",
            "engagement": None,
            "publish_success": None,
            "last_success": None,
            "publish_success_status": pub.get("status"),
            "engagement_status": eng.get("status"),
            "why": (
                "METRICOOL-RUNTIME-WIRE-1 preserved: engagement/publish_success/"
                "last_success null NOT_RUNTIME; no invented metrics."
                if ok
                else "METRICOOL-RUNTIME-WIRE-1 check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "METRICOOL-RUNTIME-WIRE-1 check failed — pack must not break it.",
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
            and board.get("invented_publish_success") is False
            and _cel.metricool_not_runtime(board) is True
            and _cel.storage_surfaces_honest(board) is True
        )
        return {
            "ok": ok,
            "pack": "CONTENT-ENGINE-LIVE-1",
            "fake_metrics": board.get("fake_metrics"),
            "invented_publish_success": board.get("invented_publish_success"),
            "metricool_not_runtime": _cel.metricool_not_runtime(board),
            "why": (
                "CONTENT-ENGINE-LIVE-1 preserved: Metricool values still NOT_RUNTIME; "
                "no invented engagement/publish."
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


def ggv_metric_honesty1_preserved() -> dict[str, Any]:
    """Read-only: GGV-METRIC-HONESTY-1 still refuses fake engagement/publish."""
    try:
        from core import ggv_metric_honesty1 as _ggv

        flags = _ggv.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("fake_metrics") is False
            and flags.get("invented_engagement") is False
            and flags.get("metricool_not_runtime") is True
        )
        return {
            "ok": ok,
            "pack": "GGV-METRIC-HONESTY-1",
            "engagement": None,
            "publish_success": None,
            "last_success": None,
            "fake_metrics": flags.get("fake_metrics"),
            "metricool_not_runtime": flags.get("metricool_not_runtime"),
            "why": (
                "GGV-METRIC-HONESTY-1 preserved: engagement/publish/last_success null; "
                "fake_metrics false."
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


def _desk_links() -> list[dict[str, str]]:
    return [
        {
            "id": "metricool_runtime_wire_1",
            "label": "Metricool Runtime Wire-1",
            "href": "/ops/metricool-runtime-wire-1",
            "note": "Authorised brand/analytics stamps; publish_success NOT_RUNTIME.",
        },
        {
            "id": "content_engine_live_1",
            "label": "Content Engine Live-1",
            "href": "/ops/content-engine-live",
            "note": "Library/NAS/queue honesty; Metricool NOT_RUNTIME.",
        },
        {
            "id": "ggv_metric_honesty_1",
            "label": "GGV Metric Honesty-1",
            "href": "/ggv/metric-honesty-1",
            "note": "Engagement/publish null; fake_metrics false.",
        },
        {
            "id": "integrations_status",
            "label": "Integrations status",
            "href": "/ops/integrations-status",
            "note": "INT-MET per-surface honesty board.",
        },
    ]


def _honesty_tiles(
    write_surf: dict[str, Any],
    pub_surf: dict[str, Any],
    eng_surf: dict[str, Any],
    mw: dict[str, Any],
    cel: dict[str, Any],
    ggv: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "classification",
            "label": "Classification",
            "status": CLASSIFICATION,
            "value": PACK_CLASSIFICATION,
            "why": (
                "HUMAN_COMMISSIONING_OR_EXTERNAL: Owner must commission Metricool "
                "write or external write stays blocked. Path documented only."
            ),
        },
        {
            "id": "metricool_write",
            "label": "Metricool write",
            "status": write_surf.get("status") or "NOT_RUNTIME",
            "value": write_surf.get("write_status") or "DISABLED",
            "why": write_surf.get("why"),
        },
        {
            "id": "publish_success",
            "label": "Publish success",
            "status": "NOT_RUNTIME",
            "value": None,
            "why": pub_surf.get("why"),
        },
        {
            "id": "engagement_values",
            "label": "Engagement values",
            "status": "NOT_RUNTIME",
            "value": None,
            "why": eng_surf.get("why"),
        },
        {
            "id": "invent_publish",
            "label": "Invent publish success",
            "status": "REFUSED",
            "value": False,
            "why": "Fake publish success / engagement invent are refused.",
        },
        {
            "id": "metricool_runtime_wire_1",
            "label": "METRICOOL-RUNTIME-WIRE-1",
            "status": "PRESERVED" if mw.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": mw.get("why"),
        },
        {
            "id": "content_engine_live_1",
            "label": "CONTENT-ENGINE-LIVE-1",
            "status": "PRESERVED" if cel.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": cel.get("why"),
        },
        {
            "id": "ggv_metric_honesty_1",
            "label": "GGV-METRIC-HONESTY-1",
            "status": "PRESERVED" if ggv.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": ggv.get("why"),
        },
        {
            "id": "cap_ggv_publish",
            "label": CAP_PUBLISH,
            "status": "SPECIFIED",
            "value": None,
            "why": "Publish path documented. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    mw = metricool_runtime_wire1_preserved()
    cel = content_engine_live1_preserved()
    ggv = ggv_metric_honesty1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_ggv_publish": CAP_PUBLISH,
        "classification": CLASSIFICATION,
        "pack_classification": PACK_CLASSIFICATION,
        "action": ACTION,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "invented_last_success": False,
        "metricool_publish": False,
        "metricool_write": False,
        "metricool_write_disabled": True,
        "auto_publish_claimed": False,
        "real_external_publish": "NO",
        "approved_is_not_published": True,
        "engagement": None,
        "publish_success": None,
        "last_success": None,
        "live_publish": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "ceiling": CEILING,
        "cap_ggv_publish_proven": False,
        "cap_ggv_publish_ready": False,
        "cap_ggv_publish_maturity": "SPECIFIED",
        "cap_ggv_publish_ceiling": CEILING,
        "metricool_runtime_wire1_preserved": mw.get("ok") is True,
        "content_engine_live1_preserved": cel.get("ok") is True,
        "ggv_metric_honesty1_preserved": ggv.get("ok") is True,
        "replaces_metricool_runtime_page": False,
        "replaces_content_engine_page": False,
        "preserved_packs": list(PRESERVED_PACKS),
        "anon_fail_closed": True,
        "owner_read": True,
        "ggv_habitat_seats": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "OCCUPANCY-EXTERNAL-HOLD-1",
    }


def refuse_fake_publish(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "Fake publish success refused. publish_success stays null / NOT_RUNTIME.",
        code="fake_publish_refused",
        http_status=403,
    )


def refuse_invent_publish(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "Invented publish success refused. Never invent publish / engagement.",
        code="invent_publish_refused",
        http_status=403,
    )


def refuse_metricool_write(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "Metricool write refused. Write stays DISABLED until Owner authorises.",
        code="metricool_write_refused",
        http_status=403,
    )


def refuse_fake_engagement(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "Fake engagement refused. Engagement stays null when not fetched.",
        code="engagement_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "PROVEN is refused. CAP-GGV publish stays SPECIFIED. Path docs are not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ContentPublishPath1Error(
        "READY is refused. A publish-path honesty board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ContentPublishPath1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {
            "ready",
            "staff-ready",
            "staff_ready",
            "human-commissioned",
            "human_commissioned",
            "live-adoption",
            "live_adoption",
        }:
            refuse_ready(payload)
        if token in {"prod", "prod-mutate", "prod-write", "8787", "15975"}:
            raise ContentPublishPath1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
                http_status=403,
            )
        if token in {
            "engagement",
            "fake-engagement",
            "invent-engagement",
        } or norm in {"engagement", "fake_engagement", "invent_engagement"}:
            refuse_fake_engagement(payload)
        if token in {
            "metricool-write",
            "metricool_write",
            "write-enabled",
            "write_enabled",
            "metricool-publish",
            "metricool_publish",
        } or norm in {
            "metricool_write",
            "write_enabled",
            "metricool_publish",
        }:
            refuse_metricool_write(payload)
        if token in _FAKE_PUBLISH_TOKENS or norm in {
            t.replace("-", "_") for t in _FAKE_PUBLISH_TOKENS
        }:
            if "engagement" in token or "engagement" in norm:
                refuse_fake_engagement(payload)
            if "write" in token or "write" in norm:
                refuse_metricool_write(payload)
            if "fake" in token or "fake" in norm:
                refuse_fake_publish(payload)
            refuse_invent_publish(payload)
    raise ContentPublishPath1Error(
        "CONTENT-PUBLISH-PATH-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def no_invented_publish_success(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    if pack.get("invented_publish_success") is not False:
        return False
    if pack.get("publish_success") is not None:
        return False
    if pack.get("engagement") is not None:
        return False
    if pack.get("last_success") is not None:
        return False
    if pack.get("metricool_write") is not False:
        return False
    if pack.get("real_external_publish") not in (None, "NO", False):
        return False
    surfaces = {s.get("id"): s for s in (pack.get("surfaces") or []) if isinstance(s, dict)}
    pub = surfaces.get("publish_success") or {}
    eng = surfaces.get("engagement_values") or {}
    write = surfaces.get("metricool_write") or {}
    if pub.get("status") != "NOT_RUNTIME" or pub.get("value") is not None:
        return False
    if pub.get("publish_success") is not None:
        return False
    if eng.get("status") != "NOT_RUNTIME" or eng.get("engagement") is not None:
        return False
    if write.get("write_enabled") is True:
        return False
    if write.get("real_external_publish") not in (None, "NO"):
        return False
    if write.get("publish_success") is not None:
        return False
    if write.get("status") != "NOT_RUNTIME":
        return False
    return True


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    if not no_invented_publish_success(pack):
        return False
    if pack.get("classification") != CLASSIFICATION:
        return False
    if pack.get("staff_ready") is not False or pack.get("human_commissioned") is not False:
        return False
    steps = pack.get("path_steps") or []
    if len(steps) < 4:
        return False
    for step in steps:
        if step.get("status") != "DOCUMENTED":
            return False
        if step.get("publish_success") is not None:
            return False
    return True


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    write_surf = metricool_write_surface()
    pub_surf = publish_success_surface()
    eng_surf = engagement_surface()
    path_steps = path_step_surfaces()
    mw = metricool_runtime_wire1_preserved()
    cel = content_engine_live1_preserved()
    ggv = ggv_metric_honesty1_preserved()
    surfaces = [write_surf, pub_surf, eng_surf]
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": list(CLOSES_TOWARD),
        "title": "Content Publish Path Board",
        "person_id": (person_id or "").strip() or None,
        "classification": CLASSIFICATION,
        "pack_classification": PACK_CLASSIFICATION,
        "action": ACTION,
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
        "metricool_publish": False,
        "metricool_write": False,
        "metricool_write_disabled": True,
        "auto_publish_claimed": False,
        "write_authority_expanded": False,
        "real_external_publish": "NO",
        "approved_is_not_published": True,
        "live_publish": False,
        "engagement": None,
        "publish_success": None,
        "last_success": None,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "cap_ggv_publish_proven": False,
        "cap_ggv_publish_ready": False,
        "cap_ggv_publish_maturity": "SPECIFIED",
        "cap_ggv_publish_ceiling": CEILING,
        "surfaces": surfaces,
        "path_steps": path_steps,
        "publish_path": list(PUBLISH_PATH_STEPS),
        "metricool_write_surface": write_surf,
        "publish_success_surface": pub_surf,
        "engagement_surface": eng_surf,
        "honesty_tiles": _honesty_tiles(write_surf, pub_surf, eng_surf, mw, cel, ggv),
        "desk_links": _desk_links(),
        "metricool_runtime_wire1": mw,
        "content_engine_live1": cel,
        "ggv_metric_honesty1": ggv,
        "metricool_runtime_wire1_preserved": mw.get("ok") is True,
        "content_engine_live1_preserved": cel.get("ok") is True,
        "ggv_metric_honesty1_preserved": ggv.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "publish_success",
            "engagement",
            "last_success",
            "metricool_write_enabled",
            "real_external_publish",
            "auto_publish",
            "CAP-GGV publish PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "OCCUPANCY-EXTERNAL-HOLD-1",
        "summary": (
            "Content publish path documented. Metricool write DISABLED / NOT_RUNTIME "
            "until Owner authorises. publish_success=null · engagement=null. "
            "METRICOOL-RUNTIME-WIRE-1 + CONTENT-ENGINE-LIVE-1 + GGV-METRIC-HONESTY-1 "
            "preserved. staff_ready=false · human_commissioned=false."
        ),
    }


def build_board(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "writes_accepted": False,
        "invented_publish_success": False,
        "publish_success": None,
        "engagement": None,
        "metricool_write": False,
        "classification": CLASSIFICATION,
        "pack_classification": PACK_CLASSIFICATION,
        "status_enum": sorted(STATUS_VOCAB),
        "path_steps": [s["step"] for s in PUBLISH_PATH_STEPS],
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": "OCCUPANCY-EXTERNAL-HOLD-1",
    }
