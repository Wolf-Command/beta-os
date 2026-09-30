#!/usr/bin/env python3
"""OWNER-DASH-FRESHNESS-1 — Owner dash freshness deepen (live stamps only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave10 pack
OWNER-DASH-FRESHNESS-1 (armed 2026-09-30 after CONNECTOR-HEALTH-DEEPEN-1
PASS_VERIFIED).

Deepens the owner dashboard freshness board from live derived-view stamps
and truth-register sources only (Owner Command, exceptions, empire,
data-quality, war-room related). Surfaces LIVE|STALE|UNKNOWN with real
as_of. Never invents KPIs or freshness. STALE never shown as current.
Preserves DASH-LIVE-1 + OWNER-EXCEPTIONS-LIVE-1 + OWNER-NEEDS-YOU-1.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain ATRIUM-FC-TRUTH-DEEPEN-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import dash_live1 as _dash
from core import dashboard_truth as _truth
from core import data_quality_exceptions as _dq

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
DQ_REGISTER = _dq.REGISTER_PATH

PACK_ID = "OWNER-DASH-FRESHNESS-1"
SCHEMA_ID = "wolf.owner-dash-freshness-1.v1"
BOUND = "beta-owner-dash-freshness"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WRITE_AUTHORITY = "NONE_EXPANDED"
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
ACTION = "WIRE_LIVE_FRESHNESS_STAMPS"
PRESERVED_PACKS = ("DASH-LIVE-1", "OWNER-EXCEPTIONS-LIVE-1", "OWNER-NEEDS-YOU-1")
NEXT_PACK = "ATRIUM-FC-TRUTH-DEEPEN-1"

PAGE_PATHS = frozenset(
    {
        "/ops/owner-dash-freshness-1",
        "/ops/owner-dash-freshness-1/",
        "/ops/owner-dash-freshness",
        "/ops/owner-dash-freshness/",
        "/ops/owner-freshness-1",
        "/ops/owner-freshness-1/",
        "/owner-dash-freshness-1",
        "/owner-dash-freshness-1/",
        "/owner-dash-freshness-1.html",
        "/dashboards/owner-dash-freshness-1.html",
    }
)
API_PATH = "/api/ops/owner-dash-freshness-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/owner-dash-freshness",
        "/api/ops/owner-freshness-1",
        "/api/owner/dash-freshness-1",
    }
)

# Focal surfaces deepened from live stamps only.
_SURFACE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "owner_command",
        "Owner Command",
        "derived_view",
        _dash.VIEW_OWNER_COMMAND,
    ),
    (
        "exceptions",
        "Owner exceptions",
        "derived_view",
        _dash.VIEW_OWNER_EXCEPTIONS,
    ),
    (
        "empire",
        "Owner empire / data truth",
        "truth_register",
        "empire",
    ),
    (
        "data_quality",
        "Owner data quality",
        "register_mtime",
        "data-quality-exceptions",
    ),
    (
        "war_room",
        "Finish War Room",
        "derived_view",
        _dash.VIEW_WAR_ROOM,
    ),
    (
        "war_room_commissioning",
        "War room commissioning",
        "derived_view",
        _dash.VIEW_WAR_COMMISSIONING,
    ),
)

STATUS_VOCAB = frozenset({"LIVE", "STALE", "UNKNOWN", "CURRENT", "UNAVAILABLE"})

_INVENT_KPI_TOKENS = frozenset(
    {
        "kpi",
        "kpis",
        "invent-kpi",
        "invent_kpi",
        "fake-kpi",
        "fake_kpi",
        "green-kpi",
        "green_kpi",
        "money",
        "revenue",
        "profit",
        "score",
        "scores",
        "invent-score",
        "invent_score",
    }
)

_INVENT_FRESHNESS_TOKENS = frozenset(
    {
        "freshness",
        "invent-freshness",
        "invent_freshness",
        "fake-freshness",
        "fake_freshness",
        "force-live",
        "force_live",
        "mark-live",
        "mark_live",
        "as-of",
        "as_of",
        "as-of-wita",
        "as_of_wita",
        "invent-as-of",
        "invent_as_of",
        "stamp-live",
        "stamp_live",
        "fake-live",
        "fake_live",
        "shown-as-current",
        "shown_as_current",
        "stale-as-current",
        "stale_as_current",
    }
)


class OwnerDashFreshness1Error(ValueError):
    """Fail closed. Does not invent KPIs or freshness timestamps."""

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


def _to_wita(iso_or_none: Any) -> str | None:
    if not iso_or_none:
        return None
    text = str(iso_or_none).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


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
    return trimmed in {p.rstrip("/") for p in API_PATHS} or raw in API_PATHS


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
    """Owner progress.read seat (Matt / owner progress readers)."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
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
        raise OwnerDashFreshness1Error(
            "Owner dash freshness board is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _normalize_surface_status(raw: str | None) -> str:
    """Project to LIVE|STALE|UNKNOWN (CURRENT kept honest, never invent LIVE)."""
    status = str(raw or "UNKNOWN").strip().upper()
    if status in {"LIVE", "STALE", "UNKNOWN"}:
        return status
    if status == "CURRENT":
        return "CURRENT"
    if status in {"UNAVAILABLE", "NEEDS REVIEW", "NEEDS_REVIEW"}:
        return "UNKNOWN"
    return "UNKNOWN"


def _derived_surface(
    *,
    surface_id: str,
    label: str,
    view_id: str,
    refresh: bool,
) -> dict[str, Any]:
    try:
        stamp = (
            _dash.refresh_and_status(view_id)
            if refresh
            else _dash.freshness_for(view_id)
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "id": surface_id,
            "label": label,
            "kind": "derived_view",
            "view_id": view_id,
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "as_of_wita": None,
            "refreshed_at": None,
            "shown_as_current": False,
            "stale_shown_as_current": False,
            "invented": False,
            "invented_kpi": False,
            "invented_freshness": False,
            "ok": False,
            "why": (
                f"{label}: derived-view `{view_id}` read failed "
                f"({type(exc).__name__}). UNKNOWN — not invented LIVE."
            ),
        }
    raw = str(stamp.get("status") or "UNKNOWN").upper()
    # Derived-view stamps are LIVE or STALE only; never invent LIVE.
    status = raw if raw in {"LIVE", "STALE"} else "UNKNOWN"
    as_of = stamp.get("as_of_wita")
    shown = status == "LIVE"
    return {
        "id": surface_id,
        "label": label,
        "kind": "derived_view",
        "view_id": view_id,
        "status": status,
        "display": status,
        "as_of_wita": as_of,
        "refreshed_at": stamp.get("refreshed_at"),
        "shown_as_current": shown,
        "stale_shown_as_current": False,
        "invented": False,
        "invented_kpi": False,
        "invented_freshness": False,
        "ok": True,
        "why": (
            f"Derived-view stamp `{view_id}` is {status}. "
            f"as_of={as_of or 'null'}. "
            "STALE never shown as current. No invent KPI/freshness."
        ),
    }


def _empire_surface() -> dict[str, Any]:
    """Worst honest display_state across empire truth-register sources."""
    try:
        stamp = _truth.stamp("empire")
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "empire",
            "label": "Owner empire / data truth",
            "kind": "truth_register",
            "view_id": "empire",
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "as_of_wita": None,
            "refreshed_at": None,
            "shown_as_current": False,
            "stale_shown_as_current": False,
            "invented": False,
            "invented_kpi": False,
            "invented_freshness": False,
            "source_count": 0,
            "ok": False,
            "why": (
                f"Empire truth stamp failed ({type(exc).__name__}). "
                "UNKNOWN — not invented LIVE."
            ),
        }
    sources = [s for s in (stamp.get("sources") or []) if isinstance(s, dict)]
    if not sources:
        return {
            "id": "empire",
            "label": "Owner empire / data truth",
            "kind": "truth_register",
            "view_id": "empire",
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "as_of_wita": None,
            "refreshed_at": None,
            "shown_as_current": False,
            "stale_shown_as_current": False,
            "invented": False,
            "invented_kpi": False,
            "invented_freshness": False,
            "source_count": 0,
            "ok": True,
            "why": "Empire stamp empty — UNKNOWN. Not invented LIVE.",
        }
    # Worst rank wins (never invent LIVE from a mixed register).
    worst = min(
        sources,
        key=lambda s: _truth._RANK.get(  # noqa: SLF001 — shared honesty rank
            str(s.get("display_state") or "UNKNOWN"), 1
        ),
    )
    raw_state = str(worst.get("display_state") or "UNKNOWN")
    status = _normalize_surface_status(raw_state)
    # Board surface vocab emphasizes LIVE|STALE|UNKNOWN; CURRENT kept honest.
    if status == "CURRENT":
        board_status = "CURRENT"
    elif status in {"LIVE", "STALE", "UNKNOWN"}:
        board_status = status
    else:
        board_status = "UNKNOWN"
    as_ofs = [_to_wita(s.get("observed_at") or s.get("as_of")) for s in sources]
    as_ofs = [a for a in as_ofs if a]
    as_of = min(as_ofs) if as_ofs else None
    shown = board_status == "LIVE"
    # STALE / UNKNOWN / CURRENT never painted as current LIVE invent.
    if board_status == "STALE":
        shown = False
    return {
        "id": "empire",
        "label": "Owner empire / data truth",
        "kind": "truth_register",
        "view_id": "empire",
        "status": board_status,
        "display": board_status,
        "raw_worst_display_state": raw_state,
        "as_of_wita": as_of,
        "refreshed_at": as_of,
        "shown_as_current": shown,
        "stale_shown_as_current": False,
        "invented": False,
        "invented_kpi": False,
        "invented_freshness": False,
        "source_count": len(sources),
        "ok": True,
        "why": (
            f"Empire truth-register worst source display_state={raw_state} → "
            f"{board_status}. as_of={as_of or 'null'}. "
            "Never invent LIVE when any source is worse. No invent KPI."
        ),
    }


def _data_quality_surface() -> dict[str, Any]:
    """RO freshness of data-quality register file. Never invent LIVE."""
    path = Path(DQ_REGISTER)
    if not path.is_file():
        return {
            "id": "data_quality",
            "label": "Owner data quality",
            "kind": "register_mtime",
            "view_id": "data-quality-exceptions",
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "as_of_wita": None,
            "refreshed_at": None,
            "shown_as_current": False,
            "stale_shown_as_current": False,
            "invented": False,
            "invented_kpi": False,
            "invented_freshness": False,
            "open_count": None,
            "ok": True,
            "why": (
                "Data-quality register absent. UNKNOWN — not invented LIVE. "
                "Counts left null."
            ),
        }
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_s = (datetime.now(timezone.utc) - mtime).total_seconds()
    # File present is not LIVE. >24h → STALE. Else CURRENT (not invent LIVE).
    if age_s > 24 * 60 * 60:
        status = "STALE"
    else:
        status = "CURRENT"
    as_of = mtime.astimezone(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    generated = None
    open_count = None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        generated = _to_wita(raw.get("generated"))
        if raw.get("open_count") is not None:
            open_count = int(raw.get("open_count"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {
        "id": "data_quality",
        "label": "Owner data quality",
        "kind": "register_mtime",
        "view_id": "data-quality-exceptions",
        "status": status,
        "display": status,
        "as_of_wita": generated or as_of,
        "refreshed_at": as_of,
        "shown_as_current": False,  # register mtime is never LIVE invent
        "stale_shown_as_current": False,
        "invented": False,
        "invented_kpi": False,
        "invented_freshness": False,
        "open_count": open_count,
        "ok": True,
        "why": (
            f"Data-quality register mtime → {status}. "
            f"as_of={generated or as_of}. "
            "File presence is not LIVE. STALE never shown as current. "
            "No invent KPI/freshness."
        ),
    }


def surface_stamps(*, refresh_derived: bool = True) -> list[dict[str, Any]]:
    """Per-surface LIVE|STALE|UNKNOWN(+CURRENT) from live stamps only."""
    out: list[dict[str, Any]] = []
    for surface_id, label, kind, key in _SURFACE_SPECS:
        if kind == "derived_view":
            # Owner Command refresh once; related views read-only.
            do_refresh = refresh_derived and surface_id == "owner_command"
            out.append(
                _derived_surface(
                    surface_id=surface_id,
                    label=label,
                    view_id=key,
                    refresh=do_refresh,
                )
            )
        elif kind == "truth_register":
            out.append(_empire_surface())
        elif kind == "register_mtime":
            out.append(_data_quality_surface())
        else:
            out.append(
                {
                    "id": surface_id,
                    "label": label,
                    "kind": kind,
                    "status": "UNKNOWN",
                    "display": "UNKNOWN",
                    "as_of_wita": None,
                    "shown_as_current": False,
                    "stale_shown_as_current": False,
                    "invented": False,
                    "invented_kpi": False,
                    "invented_freshness": False,
                    "ok": False,
                    "why": f"Unknown kind {kind} — UNKNOWN, not invented.",
                }
            )
    return out


def dash_live1_preserved() -> dict[str, Any]:
    try:
        flags = _dash.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("invented_kpi") is False
            and flags.get("stale_shown_as_current") is False
            and flags.get("freshness_from_real_stamps_only") is True
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "DASH-LIVE-1",
            "status": "CHECK_FAILED",
            "why": f"DASH-LIVE-1 honesty read failed ({type(exc).__name__}).",
        }
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "DASH-LIVE-1-RESULT.md"
    ok = ok and result.is_file()
    return {
        "ok": ok,
        "pack": "DASH-LIVE-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "href": "/wolf",
        "why": (
            "Owner/War-Room freshness honesty intact; invented KPI false; "
            "freshness_from_real_stamps_only."
            if ok
            else "DASH-LIVE-1 RESULT missing or honesty pins drifted."
        ),
    }


def owner_exceptions_live1_preserved() -> dict[str, Any]:
    try:
        from core import owner_exceptions_live1 as oel

        flags = oel.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("invented_severity") is False
            and flags.get("fake_severity") is False
            and flags.get("dash_live1_preserved") is True
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "OWNER-EXCEPTIONS-LIVE-1",
            "status": "CHECK_FAILED",
            "why": (
                f"OWNER-EXCEPTIONS-LIVE-1 honesty read failed "
                f"({type(exc).__name__})."
            ),
        }
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "OWNER-EXCEPTIONS-LIVE-1-RESULT.md"
    html = BETA_ROOT / "dashboards" / "owner-exceptions-live-1.html"
    ok = ok and result.is_file() and html.is_file()
    return {
        "ok": ok,
        "pack": "OWNER-EXCEPTIONS-LIVE-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "href": "/owner/exceptions-live-1",
        "why": (
            "Exceptions deepen intact; invented severity false; DASH-LIVE-1 held."
            if ok
            else "OWNER-EXCEPTIONS-LIVE-1 surface missing or honesty pins drifted."
        ),
    }


def owner_needs_you1_preserved() -> dict[str, Any]:
    try:
        from core import owner_needs_you1 as nye

        flags = nye.honesty_flags()
        ok = (
            flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("invented_urgency") is False
            and flags.get("fake_urgency") is False
            and flags.get("dash_live1_preserved") is True
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "OWNER-NEEDS-YOU-1",
            "status": "CHECK_FAILED",
            "why": f"OWNER-NEEDS-YOU-1 honesty read failed ({type(exc).__name__}).",
        }
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "OWNER-NEEDS-YOU-1-RESULT.md"
    html = BETA_ROOT / "dashboards" / "owner-needs-you-1.html"
    ok = ok and result.is_file() and html.is_file()
    return {
        "ok": ok,
        "pack": "OWNER-NEEDS-YOU-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "href": "/owner/needs-you-1",
        "why": (
            "Needs-You connective prove intact; invented urgency false."
            if ok
            else "OWNER-NEEDS-YOU-1 surface missing or honesty pins drifted."
        ),
    }


def _status_counts(stamps: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in stamps:
        st = str(s.get("status") or "UNKNOWN")
        counts[st] = counts.get(st, 0) + 1
    return counts


def _honesty_tiles(
    stamps: list[dict[str, Any]],
    dash_p: dict[str, Any],
    oel_p: dict[str, Any],
    nye_p: dict[str, Any],
    counts: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "pack_class",
            "label": "Pack classification",
            "status": CLASSIFICATION,
            "value": CLASSIFICATION,
            "why": "Wire live freshness stamps is INTERNALLY_SOLVABLE.",
        },
        {
            "id": "surface_mix",
            "label": "Surface freshness mix",
            "status": "FACT",
            "value": counts,
            "why": f"by_status={counts}. LIVE|STALE|UNKNOWN(+CURRENT) from real stamps.",
        },
        {
            "id": "invent_kpi",
            "label": "Invent KPI",
            "status": "REFUSED",
            "value": False,
            "why": "No KPI / money / green scores invented on this deepen board.",
        },
        {
            "id": "invent_freshness",
            "label": "Invent freshness",
            "status": "REFUSED",
            "value": False,
            "why": "as_of comes from derived-view / truth / register mtime only.",
        },
        {
            "id": "stale_as_current",
            "label": "STALE shown as current",
            "status": "REFUSED",
            "value": False,
            "why": "stale_shown_as_current=false always.",
        },
        {
            "id": "dash_live1",
            "label": "DASH-LIVE-1",
            "status": "PRESERVED" if dash_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": dash_p.get("why"),
        },
        {
            "id": "owner_exceptions_live1",
            "label": "OWNER-EXCEPTIONS-LIVE-1",
            "status": "PRESERVED" if oel_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": oel_p.get("why"),
        },
        {
            "id": "owner_needs_you1",
            "label": "OWNER-NEEDS-YOU-1",
            "status": "PRESERVED" if nye_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": nye_p.get("why"),
        },
        {
            "id": "write_authority",
            "label": "Write authority",
            "status": WRITE_AUTHORITY,
            "value": WRITE_AUTHORITY,
            "why": "Invent-KPI / invent-freshness / force-LIVE writes refused.",
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "owner_command",
            "label": "Owner Command",
            "href": "/wolf",
            "kind": "existing",
            "note": "DASH-LIVE-1 freshness badges preserved.",
        },
        {
            "id": "exceptions",
            "label": "Owner exceptions live",
            "href": "/owner/exceptions-live-1",
            "kind": "existing",
            "note": "OWNER-EXCEPTIONS-LIVE-1 preserved. No fake severity.",
        },
        {
            "id": "needs_you",
            "label": "Owner Needs You",
            "href": "/owner/needs-you-1",
            "kind": "existing",
            "note": "OWNER-NEEDS-YOU-1 preserved. No fake urgency.",
        },
        {
            "id": "empire",
            "label": "Owner empire pack",
            "href": "/owner-empire-pack",
            "kind": "existing",
            "note": "Empire desk; truth-register freshness read here.",
        },
        {
            "id": "data_quality",
            "label": "Owner data quality",
            "href": "/owner/data-quality",
            "kind": "existing",
            "note": "Register mtime freshness — never invent LIVE.",
        },
        {
            "id": "war_room",
            "label": "Finish War Room",
            "href": "/finish-war-room",
            "kind": "existing",
            "note": "DASH-LIVE-1 war-room freshness preserved.",
        },
        {
            "id": "data_truth",
            "label": "Data truth register",
            "href": "/owner/data-truth",
            "kind": "existing",
            "note": "dashboard_truth source register (empire surface).",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    dash_p = dash_live1_preserved()
    oel_p = owner_exceptions_live1_preserved()
    nye_p = owner_needs_you1_preserved()
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
        "invented_kpi": False,
        "kpi_invented": False,
        "fake_kpi": False,
        "green_kpi": False,
        "money": None,
        "invented_freshness": False,
        "fake_freshness": False,
        "stale_shown_as_current": False,
        "freshness_from_real_stamps_only": True,
        "anon_fail_closed": True,
        "owner_read": True,
        "dash_live1_preserved": dash_p.get("ok") is True,
        "owner_exceptions_live1_preserved": oel_p.get("ok") is True,
        "owner_needs_you1_preserved": nye_p.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "pins": {
            "pack": CLASSIFICATION,
            "invent_kpi": "REFUSED",
            "invent_freshness": "REFUSED",
            "stale_as_current": "REFUSED",
            "exit_report_headchef": "MATT_ACTION",
            "prod_mutate": "EXTERNAL_BLOCKER",
        },
    }


def refuse_invent_kpi(_body: dict | None = None) -> None:
    raise OwnerDashFreshness1Error(
        "Invented KPIs are refused. Freshness deepen does not invent scores.",
        code="invent_kpi_refused",
        http_status=403,
    )


def refuse_invent_freshness(_body: dict | None = None) -> None:
    raise OwnerDashFreshness1Error(
        "Invented freshness / force-LIVE is refused. Stamps stay real.",
        code="invent_freshness_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise OwnerDashFreshness1Error(
        "PROVEN is refused. Owner dash freshness deepen is honesty, not prove.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise OwnerDashFreshness1Error(
        "READY is refused. A freshness deepen board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise OwnerDashFreshness1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if (
            token in _INVENT_KPI_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_KPI_TOKENS}
        ):
            refuse_invent_kpi(payload)
        if (
            token in _INVENT_FRESHNESS_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_FRESHNESS_TOKENS}
            or "freshness" in token
            or "as-of" in token
            or "as_of" in norm
        ):
            refuse_invent_freshness(payload)
    raise OwnerDashFreshness1Error(
        "OWNER-DASH-FRESHNESS-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def no_invented_kpi(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("invented_kpi") is not False or pack.get("fake_kpi") is not False:
        return False
    if pack.get("money") is not None or pack.get("green_kpi") is not False:
        return False
    for s in pack.get("surface_stamps") or []:
        if s.get("invented_kpi") is not False or s.get("invented") is not False:
            return False
    return True


def no_stale_as_current(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("stale_shown_as_current") is not False:
        return False
    for s in pack.get("surface_stamps") or []:
        if s.get("stale_shown_as_current") is not False:
            return False
        if s.get("status") == "STALE" and s.get("shown_as_current") is True:
            return False
    return True


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    stamps = pack.get("surface_stamps") or []
    if len(stamps) < 5:
        return False
    ids = {s.get("id") for s in stamps}
    required = {
        "owner_command",
        "exceptions",
        "empire",
        "data_quality",
        "war_room",
    }
    if not required.issubset(ids):
        return False
    for s in stamps:
        status = str(s.get("status") or "")
        if status not in STATUS_VOCAB:
            return False
        if s.get("invented_freshness") is not False:
            return False
        if status == "STALE" and s.get("shown_as_current") is True:
            return False
    return True


def build_board(*, refresh_derived: bool = True) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    stamps = surface_stamps(refresh_derived=refresh_derived)
    dash_p = dash_live1_preserved()
    oel_p = owner_exceptions_live1_preserved()
    nye_p = owner_needs_you1_preserved()
    counts = _status_counts(stamps)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": ["owner dash"],
        "title": "Owner dash freshness — live stamps only",
        "classification": CLASSIFICATION,
        "action": ACTION,
        "ceiling": CEILING,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "write_authority": WRITE_AUTHORITY,
        "write_authority_expanded": False,
        "invented_kpi": False,
        "kpi_invented": False,
        "fake_kpi": False,
        "green_kpi": False,
        "money": None,
        "invented_freshness": False,
        "fake_freshness": False,
        "stale_shown_as_current": False,
        "freshness_from_real_stamps_only": True,
        "surface_count": len(stamps),
        "by_status": counts,
        "surface_stamps": stamps,
        "dash_live1_preserved": dash_p.get("ok") is True,
        "owner_exceptions_live1_preserved": oel_p.get("ok") is True,
        "owner_needs_you1_preserved": nye_p.get("ok") is True,
        "dash_live1": dash_p,
        "owner_exceptions_live1": oel_p,
        "owner_needs_you1": nye_p,
        "honesty_tiles": _honesty_tiles(stamps, dash_p, oel_p, nye_p, counts),
        "desk_links": _desk_links(),
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "invented_kpi",
            "green_kpi",
            "money",
            "invented_freshness",
            "stale_shown_as_current",
            "staff_ready",
            "human_commissioned",
            "proven",
            "ready",
        ],
        "honesty": flags,
        "pins": flags.get("pins"),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "summary": (
            "Owner dash freshness deepen. LIVE|STALE|UNKNOWN from real stamps. "
            "No invent KPI / freshness. STALE never current. "
            "DASH-LIVE-1 + OWNER-EXCEPTIONS-LIVE-1 + OWNER-NEEDS-YOU-1 preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def build_slice() -> dict[str, Any]:
    return build_board()


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    if person_id is not None:
        require_view(person_id)
    return build_board()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "invented_kpi": False,
        "invented_freshness": False,
        "stale_shown_as_current": False,
        "writes_accepted": False,
        "classification": CLASSIFICATION,
        "preserves": list(PRESERVED_PACKS),
        "surfaces": [s[0] for s in _SURFACE_SPECS],
        "status_vocab": sorted(STATUS_VOCAB),
        "why": (
            "Owner dash freshness from live derived-view / truth / register stamps. "
            "LIVE|STALE|UNKNOWN with real as_of. No invent KPI. STALE ≠ current."
        ),
    }
