#!/usr/bin/env python3
"""NAS Index Operator Depth — browse/filter/search facets + object detail (Beta).

Decision served: Owner Connection Commissioning READ/WRITE package APPROVED
2026-09-22 (RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22);
extends NAS Library Upload P0 + NAS index continue v2 + GGV Content ops depth
ENGINEERING_PASS. Plan: GROK-PLAN-NAS-INDEX-OPERATOR-DEPTH-2026-09-23.md.

Authorised content/library seats browse/filter/search Beta nas_index with
operator facets (folder / brand-token / type / recent) and open indexed object
detail (rel-only + scope gate). Optional READ-only capped `_needs_sorting`
sample. Keep full_tree_indexed=false. No Haikal human fake. No NAS destroy.
No invent PROVEN/READY/staff_ready. No Metricool publish. Do not false-resolve CRs.

Bound: beta-nas-library-safe (:8788 only).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core import ggv_content_ops_depth as content_ops
from core import nas_library as nas
from core import wolf_shell as shell

TZ = ZoneInfo("Asia/Makassar")
BETA_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
OPERATOR_EVENTS = BETA_ROOT / "state" / "nas-index" / "operator-events.jsonl"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-nas-library-safe"
SCHEMA_ID = "wolf.nas-index-operator-depth.v1"
SLICE = "nas_index_operator_depth"
RUN_ID = "BF-nas-index-operator-depth-20260923"
CLAIM_ID = "bf-nas-index-operator-depth-20260923"
CONTENT_HREF = "/content-2.0"
DESK_ANCHOR = "/content-2.0#nas-index-ops"

# Related OPEN CRs — never false-resolve
CR_CAP_GGV_01 = "CR-8c1fa12404180c02"
CR_CONNECTION = "wolf-connection-commissioning-nas-20260922"

HAIKAL = content_ops.HAIKAL
AMANDA = content_ops.AMANDA
MISA = content_ops.MISA
OWNER = content_ops.OWNER
OPERATOR_FIXTURES: tuple[str, ...] = (AMANDA, HAIKAL, MISA, OWNER)

HONESTY = {
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "full_tree_indexed": False,
    "haikal_human_status": "not_started",
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_haikal_human_pass": False,
    "nas_destructive": False,
    "metricool_publish": False,
    "cr_resolved": False,
}


class NasIndexOpsError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "nas_index_ops_error",
        http: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http = http
        self.http_status = http


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def honesty_flags() -> dict[str, Any]:
    flags = dict(HONESTY)
    flags["slice"] = SLICE
    flags["schema_id"] = SCHEMA_ID
    flags["run_id"] = RUN_ID
    flags["bound"] = BOUND
    flags["nas_index_operator_depth"] = True
    flags["nas_index_continue"] = True
    return flags


def _open_catalog(path: Path | str | None = None) -> sqlite3.Connection:
    db = Path(path) if path else CATALOG_DB
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def _cr_state(item_id: str, *, catalog: Path | None = None) -> str | None:
    conn = _open_catalog(catalog)
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()
    return None if row is None else str(row[0])


def cap_honesty() -> dict[str, Any]:
    """CAP / CR honesty — never invent PROVEN/READY; never false-resolve."""
    ledger: dict[str, Any] = {}
    if LEDGER_JSON.is_file():
        try:
            ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ledger = {}

    def cap_state(cap_id: str) -> str:
        row = ledger.get(cap_id)
        if isinstance(row, list) and row:
            return str(row[0])
        if isinstance(row, str):
            return row
        return "UNKNOWN"

    cr01 = _cr_state(CR_CAP_GGV_01) or "OPEN"
    return {
        "CAP-GGV-01": cap_state("CAP-GGV-01"),
        "CAP-GGV-05": cap_state("CAP-GGV-05"),
        "CAP-GGV-03": cap_state("CAP-GGV-03"),
        "CAP-GGV-06": cap_state("CAP-GGV-06"),
        "cr_8c1fa12404180c02": cr01,
        "cr_connection_commissioning": "OPEN",
        "false_resolve_refused": True,
        "denominator": len(ledger) if ledger else None,
    }


def require_operator_person(person_id: str | None) -> dict[str, Any]:
    """Reuse GGV content operator seat fixtures (Haikal/Misa/Amanda/Owner)."""
    try:
        return content_ops.require_actor(person_id)
    except content_ops.ContentOpsError as exc:
        raise NasIndexOpsError(
            str(exc),
            code=getattr(exc, "code", "forbidden"),
            http=int(getattr(exc, "http_status", 403) or 403),
        ) from exc


def refuse_code(path: str) -> str | None:
    """Map refuse path tails. Operator browse/detail/touch routes are not refused."""
    p = (path or "").rstrip("/")
    if any(
        x in p
        for x in (
            "/operator-depth",
            "/browse",
            "/facets",
            "/objects/",
            "/needs-sorting",
            "/search",
        )
    ):
        # Still refuse if the tail itself is a forbidden action name
        pass
    tail = p.rsplit("/", 1)[-1].lower()
    mapping = {
        "proven": "proven_refused",
        "ready": "ready_refused",
        "staff-ready": "staff_ready_refused",
        "staff_ready": "staff_ready_refused",
        "haikal-human": "haikal_human_refused",
        "haikal_human": "haikal_human_refused",
        "metricool": "metricool_refused",
        "metricool-publish": "metricool_refused",
        "klaviyo": "klaviyo_refused",
        "klaviyo-publish": "klaviyo_refused",
        "nas-destroy": "nas_destroy_refused",
        "destroy": "nas_destroy_refused",
        "full-tree": "full_tree_refused",
        "full_tree": "full_tree_refused",
        "full_tree_indexed": "full_tree_refused",
        "production": "production_refused",
        "resolve": "resolve_refused",
    }
    return mapping.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"refused: {code}",
        **honesty_flags(),
    }


def _append_event(event: dict[str, Any]) -> None:
    OPERATOR_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with OPERATOR_EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _strip_volumes(blob: Any) -> Any:
    """Defence in depth — never leak /Volumes/ absolute paths."""
    if isinstance(blob, dict):
        return {k: _strip_volumes(v) for k, v in blob.items() if k != "original_path"}
    if isinstance(blob, list):
        return [_strip_volumes(x) for x in blob]
    if isinstance(blob, str) and "/Volumes/" in blob:
        try:
            rel = str(Path(blob).resolve().relative_to(nas.MEDIA_LIBRARY.resolve()))
            return rel
        except (ValueError, OSError):
            return "[redacted-absolute]"
    return blob


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    scopes: list[str] | set[str] | None = None,
    catalog: Path | str | None = None,
    q: str = "",
    folder: str | None = None,
    brand_token: str | None = None,
    media_type: str | None = None,
    extension: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    """Operator desk: facets + browse sample + honesty + NAS readiness strip."""
    seat = require_operator_person(verified_person_id)
    pid = seat.get("person_id") or verified_person_id
    who_scopes = list(scopes or [])
    if not who_scopes:
        who_scopes = list(
            shell.scopes_from_assignments(shell.assignments_for_person(str(pid))) or []
        )
    conn = _open_catalog(catalog)
    try:
        nas.migrate_schema(conn)
        try:
            content_ops.ensure_operator_depth_rbac(conn=conn, commit=True)
        except Exception:  # noqa: BLE001
            pass
        facets = nas.nas_index_facets(conn, scopes=who_scopes)
        browse = nas.browse_nas_index(
            conn,
            q=q,
            folder=folder,
            brand_token=brand_token,
            media_type=media_type,
            extension=extension,
            limit=limit,
            recent=True,
            scopes=who_scopes,
        )
        caps = cap_honesty()
        nas_strip = content_ops.nas_readiness_strip()
        needs = content_ops.content_desk_needs_you_consequence(
            catalog_db=catalog or CATALOG_DB,
        )
        out = {
            "ok": True,
            "bound": BOUND,
            "schema_id": SCHEMA_ID,
            "slice": SLICE,
            "run_id": RUN_ID,
            "desk_anchor": DESK_ANCHOR,
            "content_href": CONTENT_HREF,
            "seat": {
                "person_id": pid,
                "label": seat.get("label"),
            },
            "facets": {
                "folders": facets.get("folders"),
                "brand_tokens": facets.get("brand_tokens"),
                "media_types": facets.get("media_types"),
                "extensions": facets.get("extensions"),
                "browse_tops": facets.get("browse_tops"),
                "refused_tops": facets.get("refused_tops"),
            },
            "browse": browse,
            "nas_readiness": nas_strip,
            "content_desk_needs_you": needs,
            "caps": caps,
            "why": (
                "Browse/filter/search Beta nas_index samples with folder / brand-token / "
                "media-type / recent facets; open indexed object detail (rel-only). "
                "Optional READ-only _needs_sorting sample. full_tree_indexed=false."
            ),
            "empty_message": browse.get("empty_message"),
            **honesty_flags(),
        }
        return _strip_volumes(out)
    finally:
        conn.close()


def object_detail(
    object_id: int | str,
    *,
    verified_person_id: str | None,
    scopes: list[str] | set[str] | None = None,
    catalog: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_operator_person(verified_person_id)
    pid = seat.get("person_id") or verified_person_id
    who_scopes = list(scopes or [])
    if not who_scopes:
        who_scopes = list(
            shell.scopes_from_assignments(shell.assignments_for_person(str(pid))) or []
        )
    conn = _open_catalog(catalog)
    try:
        try:
            detail = nas.get_nas_index_object(conn, object_id, scopes=who_scopes)
        except nas.NasLibraryError as exc:
            raise NasIndexOpsError(str(exc), code=exc.code, http=exc.http) from exc
        detail["seat"] = {"person_id": pid}
        detail["nas_readiness"] = content_ops.nas_readiness_strip()
        detail["next_actions"] = [
            {
                "code": "next_action_touch",
                "label": "Touch next action (refresh Needs-You / NAS strip)",
            },
            {
                "code": "open_library",
                "label": "Open Content Library",
                "href": f"{CONTENT_HREF}#library",
            },
        ]
        detail.update(honesty_flags())
        return _strip_volumes(detail)
    finally:
        conn.close()


def next_action_touch(
    object_id: int | str,
    *,
    verified_person_id: str | None,
    note: str | None = None,
    scopes: list[str] | set[str] | None = None,
    catalog: Path | str | None = None,
) -> dict[str, Any]:
    """Optional next-action-touch — refreshes Content Needs-You / NAS readiness.

    Does not invent content assets, Metricool publish, or Haikal human PASS.
    """
    seat = require_operator_person(verified_person_id)
    pid = seat.get("person_id") or verified_person_id
    detail = object_detail(
        object_id,
        verified_person_id=verified_person_id,
        scopes=scopes,
        catalog=catalog,
    )
    obj = detail.get("object") or {}
    event = {
        "at": now_iso(),
        "kind": "next_action_touch",
        "nas_index_id": obj.get("id"),
        "rel": obj.get("rel"),
        "person_id": pid,
        "note": (note or "").strip()[:500] or None,
        "metricool_publish": False,
        "nas_destructive": False,
    }
    _append_event(event)
    needs = content_ops.content_desk_needs_you_consequence(
        catalog_db=catalog or CATALOG_DB,
    )
    return _strip_volumes(
        {
            "ok": True,
            "recorded": True,
            "kind": "next_action_touch",
            "object": obj,
            "event": event,
            "nas_readiness": content_ops.nas_readiness_strip(),
            "content_desk_needs_you": needs,
            "message": (
                "Next-action touch recorded for indexed object. "
                "NAS readiness + Content Needs-You strips refreshed. "
                "No Metricool publish · no NAS destroy · staff_ready=false."
            ),
            **honesty_flags(),
        }
    )


def needs_sorting_sample(
    *,
    verified_person_id: str | None,
    cap: int = 25,
    ingest: bool = False,
    catalog: Path | str | None = None,
) -> dict[str, Any]:
    """READ-only capped `_needs_sorting` sample. Refuse recycle/archive."""
    require_operator_person(verified_person_id)
    if ingest:
        conn = _open_catalog(catalog)
        try:
            result = nas.persist_and_ingest_needs_sorting(conn, cap=cap)
        finally:
            conn.close()
    else:
        result = nas.inventory_needs_sorting_sample(cap=cap)
        result.pop("_raw_for_ingest", None)
    result.update(honesty_flags())
    result["seat_person_id"] = verified_person_id
    return _strip_volumes(result)


def browse(
    *,
    verified_person_id: str | None,
    scopes: list[str] | set[str] | None = None,
    catalog: Path | str | None = None,
    q: str = "",
    folder: str | None = None,
    brand_token: str | None = None,
    media_type: str | None = None,
    extension: str | None = None,
    limit: int = 50,
    recent: bool = True,
) -> dict[str, Any]:
    seat = require_operator_person(verified_person_id)
    pid = seat.get("person_id") or verified_person_id
    who_scopes = list(scopes or [])
    if not who_scopes:
        who_scopes = list(
            shell.scopes_from_assignments(shell.assignments_for_person(str(pid))) or []
        )
    conn = _open_catalog(catalog)
    try:
        try:
            out = nas.browse_nas_index(
                conn,
                q=q,
                folder=folder,
                brand_token=brand_token,
                media_type=media_type,
                extension=extension,
                limit=limit,
                recent=recent,
                scopes=who_scopes,
            )
        except nas.NasLibraryError as exc:
            raise NasIndexOpsError(str(exc), code=exc.code, http=exc.http) from exc
        out["seat"] = {"person_id": pid}
        out.update(honesty_flags())
        return _strip_volumes(out)
    finally:
        conn.close()
