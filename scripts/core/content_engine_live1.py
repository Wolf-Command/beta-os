#!/usr/bin/env python3
"""CONTENT-ENGINE-LIVE-1 — Content Engine live-data path (storage truth).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CONTENT-ENGINE-LIVE-1
(armed 2026-09-30 after RELIABILITY-1 PASS_VERIFIED). Closes toward CAP-GGV-01 /
MB content.

Surfaces real content-library / NAS / publish-queue paths with empty/UNKNOWN when
missing. Metricool stays NOT_RUNTIME (INTG-TRUTH-1) — never invents engagement,
publish success, or Metricool last_success. Preserves GGV-CONTENT-PROVE-1 honesty.
staff_ready / human_commissioned stay false.
Does not auto-chain BZG-WASTE-YIELD-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import content_publish as _publish
from core import intg_truth_board as _intg
from core import nas_library as _nas

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
CONTENT_THUMBS = BETA_ROOT / "state" / "content-thumbs"
NAS_INDEX_DIR = BETA_ROOT / "state" / "nas-index"
NAS_COVERAGE = BETA_ROOT / "state" / "content-engine" / "nas-index-coverage.json"
LIBRARY_V2 = BETA_ROOT / "library_v2"
INCOMING_DROP = BETA_ROOT / "incoming_drop"

PACK_ID = "CONTENT-ENGINE-LIVE-1"
SCHEMA_ID = "wolf.content-engine-live1.v1"
BOUND = "beta-content-engine-live-safe"
HONESTY_BOARD = "/ops/integrations-status"
METRICOOL_ID = "INT-MET-WOLF"
CONTENT_HREF = "/content-2.0"
PROD_PID_HELD = 15975

PAGE_PATHS = frozenset(
    {
        "/ops/content-engine-live",
        "/ops/content-engine-live/",
        "/content/engine-live",
        "/content/engine-live/",
        "/content-engine-live",
        "/content-engine-live/",
        "/content-engine-live.html",
        "/dashboards/content-engine-live.html",
    }
)
API_PATH = "/api/ops/content-engine-live"

CLOSES_TOWARD = ("CAP-GGV-01", "MB content")
CEILING = "BUILT"
PRESERVED_PACKS = ("GGV-CONTENT-PROVE-1", "INTG-TRUTH-1", "RELIABILITY-1")

WITA = timezone(timedelta(hours=8))

# Statuses that must never be invented as published / engagement success.
_FAKE_PUBLISH_TOKENS = frozenset(
    {
        "engagement",
        "engagement-count",
        "engagement-success",
        "fake-engagement",
        "invent-engagement",
        "publish-success",
        "published",
        "auto-publish",
        "metricool-success",
        "metricool-last-success",
        "last-success",
        "fake-publish",
        "fake-metrics",
        "invent-metrics",
        "force-published",
        "paint-published",
    }
)


class ContentEngineLive1Error(ValueError):
    """Fail closed. Does not invent Metricool / publish / engagement success."""

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


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "metricool_publish": False,
        "metricool_write": False,
        "auto_publish_claimed": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "ggv_content_prove1_preserved": True,
        "intg_truth1_preserved": True,
        "next_pack_for_parent_only": "BZG-WASTE-YIELD-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
    }


def refuse_fake_publish(body: dict | None = None) -> None:
    raise ContentEngineLive1Error(
        "Fake publish / engagement / Metricool success invent refused.",
        code="fake_publish_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ContentEngineLive1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in _FAKE_PUBLISH_TOKENS:
            raise ContentEngineLive1Error(
                "Fake publish / engagement / Metricool success invent refused.",
                code="fake_publish_refused",
            )
        if token in {"staff-ready", "human-commissioned", "proven", "ready", "live-adoption"}:
            raise ContentEngineLive1Error(
                "Commissioning flags / PROVEN / READY / LIVE adoption are refused.",
                code="ready_refused",
            )
        if token in {"prod", "prod-mutate", "prod-write", "8787", "15975"}:
            raise ContentEngineLive1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
    raise ContentEngineLive1Error(
        "CONTENT-ENGINE-LIVE-1 is a read-only storage-truth board. Writes refused.",
        code="write_refused",
    )


def _path_surface(label: str, path: Path, *, role: str) -> dict[str, Any]:
    exists = False
    try:
        exists = path.exists()
    except OSError:
        exists = False
    is_dir = False
    is_file = False
    size: int | None = None
    if exists:
        try:
            is_dir = path.is_dir()
            is_file = path.is_file()
            if is_file:
                size = int(path.stat().st_size)
        except OSError:
            exists = False
    status = "PRESENT" if exists else "UNKNOWN"
    if exists and not (is_dir or is_file):
        status = "UNKNOWN"
    return {
        "id": role,
        "label": label,
        "role": role,
        "path": str(path),
        "exists": exists,
        "is_dir": is_dir,
        "is_file": is_file,
        "size_bytes": size,
        "status": status,
        "empty": (not exists) or (is_dir and _dir_empty(path)),
        "invented": False,
    }


def _dir_empty(path: Path) -> bool:
    try:
        if not path.is_dir():
            return True
        next(path.iterdir())
        return False
    except (OSError, StopIteration):
        return True


def _library_surfaces() -> dict[str, Any]:
    surfaces = [
        _path_surface("Catalog DB", CATALOG_DB, role="catalog_db"),
        _path_surface("Library v2", LIBRARY_V2, role="library_v2"),
        _path_surface("Incoming drop", INCOMING_DROP, role="incoming_drop"),
        _path_surface("Content thumbs", CONTENT_THUMBS, role="content_thumbs"),
        _path_surface("NAS index state", NAS_INDEX_DIR, role="nas_index_state"),
        _path_surface("NAS coverage stamp", NAS_COVERAGE, role="nas_coverage"),
    ]
    counts = _catalog_counts()
    return {
        "id": "content_library",
        "label": "Content library storage",
        "kind": "storage_truth",
        "paths": surfaces,
        "counts": counts,
        "content_desk_href": CONTENT_HREF,
        "why": (
            "Real Beta paths only. Missing paths stay UNKNOWN/empty — "
            "never invent library inventory or publish success."
        ),
    }


def _catalog_counts() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {
            "catalog_present": False,
            "assets": None,
            "nas_index_rows": None,
            "content_planner_slots": None,
            "content_cards": None,
            "staged_assets": None,
            "status": "UNKNOWN",
            "why": "catalog/content_library.sqlite missing — counts UNKNOWN.",
        }
    try:
        con = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
        try:
            cur = con.cursor()

            def _count(table: str) -> int | None:
                try:
                    return int(cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                except sqlite3.Error:
                    return None

            return {
                "catalog_present": True,
                "assets": _count("assets"),
                "nas_index_rows": _count("nas_index"),
                "content_planner_slots": _count("content_planner"),
                "content_cards": _count("content_cards"),
                "staged_assets": _count("staged_assets"),
                "status": "PRESENT",
                "why": "Counts from live Beta catalog (read-only).",
            }
        finally:
            con.close()
    except sqlite3.Error as exc:
        return {
            "catalog_present": True,
            "assets": None,
            "nas_index_rows": None,
            "content_planner_slots": None,
            "content_cards": None,
            "staged_assets": None,
            "status": "UNKNOWN",
            "why": f"Catalog unreadable ({type(exc).__name__}) — counts UNKNOWN.",
        }


def _nas_surfaces() -> dict[str, Any]:
    reg = _nas.registry()
    roots = list(reg.get("roots") or [])
    canonical = bool(reg.get("canonical_connected"))
    indexing = _nas.indexing_state_from_disk()
    return {
        "id": "nas",
        "label": "NAS mounts",
        "kind": "storage_truth",
        "canonical_root": reg.get("canonical_root") or str(_nas.MEDIA_LIBRARY),
        "canonical_connected": canonical,
        "wolf_write_prefix": reg.get("wolf_write_prefix"),
        "roots": [
            {
                "id": r.get("id"),
                "path": r.get("path"),
                "role": r.get("role"),
                "connected": bool(r.get("connected")),
                "evidence": r.get("evidence") or ("mounted" if r.get("connected") else "UNKNOWN"),
                "wolf_library_target": r.get("wolf_library_target"),
                "status": "MOUNTED" if r.get("connected") else "UNKNOWN",
                "invented": False,
            }
            for r in roots
        ],
        "indexing": {
            "sample_manifests": indexing.get("sample_manifests"),
            "full_tree_indexed": False,
            "continue_folders_indexed": list(indexing.get("continue_folders_indexed") or []),
            "note": indexing.get("note")
            or "Partial capped samples only — full tree UNKNOWN / not claimed",
            "staff_ready": False,
        },
        "status": "MOUNTED" if canonical else "UNKNOWN",
        "why": (
            "NAS truth from volume mounts. Unmounted = UNKNOWN — never invent files "
            "or paint Metricool publish success from NAS presence."
        ),
    }


def _publish_queue_surfaces() -> dict[str, Any]:
    """Honest content_planner read — approved ≠ published; no engagement invent."""
    mc = _publish.metricool_write_status()
    if not CATALOG_DB.is_file():
        return {
            "id": "publish_queue",
            "label": "Publish queue",
            "kind": "publish_honesty",
            "status": "UNKNOWN",
            "slots": [],
            "slot_count": None,
            "by_status": {},
            "published_count": None,
            "engagement": None,
            "publish_success": None,
            "metricool_write_status": mc.get("status") or "DISABLED",
            "approved_is_not_published": True,
            "real_external_publish": "NO",
            "fake_metrics": False,
            "why": "Catalog missing — publish queue UNKNOWN. No invented publish success.",
        }
    slots: list[dict[str, Any]] = []
    by_status: dict[str, int] = {}
    try:
        con = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                """
                SELECT id, brand, platform, status, title_slug, scheduled_date,
                       core_approval_request_id, approved_version_hash
                FROM content_planner
                ORDER BY id ASC
                LIMIT 50
                """
            ).fetchall()
            for row in rows:
                status = str(row["status"] or "UNKNOWN")
                by_status[status] = by_status.get(status, 0) + 1
                # Never paint planner status as published / engagement success.
                published = False
                slots.append(
                    {
                        "id": row["id"],
                        "brand": row["brand"],
                        "platform": row["platform"],
                        "status": status,
                        "title_slug": row["title_slug"],
                        "scheduled_date": row["scheduled_date"],
                        "core_approval_request_id": row["core_approval_request_id"],
                        "approved_version_hash": row["approved_version_hash"],
                        "published": published,
                        "engagement": None,
                        "publish_success": None,
                        "metricool_success": None,
                        "approved_is_not_published": True,
                    }
                )
        finally:
            con.close()
    except sqlite3.Error as exc:
        return {
            "id": "publish_queue",
            "label": "Publish queue",
            "kind": "publish_honesty",
            "status": "UNKNOWN",
            "slots": [],
            "slot_count": None,
            "by_status": {},
            "published_count": None,
            "engagement": None,
            "publish_success": None,
            "metricool_write_status": mc.get("status") or "DISABLED",
            "approved_is_not_published": True,
            "real_external_publish": "NO",
            "fake_metrics": False,
            "why": f"Planner unread ({type(exc).__name__}) — UNKNOWN. No invent.",
        }
    return {
        "id": "publish_queue",
        "label": "Publish queue",
        "kind": "publish_honesty",
        "status": "PRESENT" if slots else "EMPTY",
        "slots": slots,
        "slot_count": len(slots),
        "by_status": by_status,
        "published_count": None,  # never invent a published total
        "engagement": None,
        "publish_success": None,
        "metricool_write_status": mc.get("status") or "DISABLED",
        "approved_is_not_published": True,
        "real_external_publish": mc.get("real_external_publish") or "NO",
        "fake_metrics": False,
        "why": (
            "Planner slots from catalog only. approved ≠ published. "
            "No engagement / Metricool success invent. Metricool write DISABLED on Beta."
        ),
    }


def _metricool_stamp() -> dict[str, Any]:
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
    # Force honesty: never surface invented last_success on this pack.
    return {
        "id": "metricool_runtime",
        "label": "Metricool Wolf runtime",
        "kind": "publish_honesty",
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


def build_board() -> dict[str, Any]:
    """Public storage-truth board. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    library = _library_surfaces()
    nas = _nas_surfaces()
    queue = _publish_queue_surfaces()
    metricool = _metricool_stamp()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "live_adoption": False,
        "operating_adoption": False,
        "fake_metrics": False,
        "invented_engagement": False,
        "invented_publish_success": False,
        "invented_metricool_success": False,
        "metricool_publish": False,
        "metricool_write": False,
        "auto_publish_claimed": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "does_not_claim": [
            "LIVE_ADOPTION",
            "staff_ready",
            "human_commissioned",
            "Metricool publish success",
            "engagement success metrics",
            "auto-publish",
        ],
        "surfaces": {
            "content_library": library,
            "nas": nas,
            "publish_queue": queue,
            "metricool": metricool,
        },
        "honesty": {
            "metricool_wolf": "NOT_RUNTIME",
            "metricool_mcp": "AGENT_HOST_ONLY",
            "publish_metrics": "UNKNOWN_never_invent",
            "storage_policy": "real_paths_empty_or_UNKNOWN",
            "live_adoption": "NOT_LIVE",
            "cap_ggv_01": "BUILT_NOT_PROVEN",
            "staff_ready": False,
            "human_commissioned": False,
            "honesty_board_href": HONESTY_BOARD,
            "ggv_content_prove1_preserved": True,
            "intg_truth1_preserved": True,
        },
        "desk_links": [
            {
                "id": "content_desk",
                "label": "Content desk",
                "href": CONTENT_HREF,
                "note": "Existing Content Machine desk. Not LIVE adoption.",
            },
            {
                "id": "content_prove",
                "label": "GGV Content Prove",
                "href": "/ggv/content-prove",
                "note": "Prior prove pack — Metricool NOT_RUNTIME preserved.",
            },
            {
                "id": "integrations_honesty",
                "label": "Integrations honesty board",
                "href": HONESTY_BOARD,
                "note": "INT-MET-WOLF NOT_RUNTIME source of truth.",
            },
        ],
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": "BZG-WASTE-YIELD-1",
        "cursor_did_not_auto_start_next": True,
        **{
            k: flags[k]
            for k in (
                "proven_claimed",
                "ready_claimed",
                "ggv_content_prove1_preserved",
                "intg_truth1_preserved",
                "no_push",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def metricool_not_runtime(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    met = (pack.get("surfaces") or {}).get("metricool") or pack.get("metricool") or {}
    return (
        met.get("not_runtime") is True
        and met.get("last_success") is None
        and met.get("display") == "NOT_RUNTIME"
        and met.get("engagement") is None
        and met.get("publish_success") is None
        and met.get("fake_metrics") is False
    )


def storage_surfaces_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when library/NAS/queue never invent publish/engagement success."""
    pack = payload if payload is not None else build_board()
    surfaces = pack.get("surfaces") or {}
    queue = surfaces.get("publish_queue") or {}
    if queue.get("engagement") is not None:
        return False
    if queue.get("publish_success") is not None:
        return False
    if queue.get("published_count") is not None:
        return False
    if queue.get("fake_metrics") is True:
        return False
    for slot in queue.get("slots") or []:
        if slot.get("engagement") is not None:
            return False
        if slot.get("publish_success") is not None:
            return False
        if slot.get("metricool_success") is not None:
            return False
        if slot.get("published") is True:
            return False
    for path in (surfaces.get("content_library") or {}).get("paths") or []:
        if path.get("invented") is True:
            return False
        if not path.get("exists") and path.get("status") not in ("UNKNOWN", "MISSING"):
            return False
    for root in (surfaces.get("nas") or {}).get("roots") or []:
        if root.get("invented") is True:
            return False
        if not root.get("connected") and root.get("status") not in ("UNKNOWN", "UNMOUNTED"):
            return False
    return metricool_not_runtime(pack)
