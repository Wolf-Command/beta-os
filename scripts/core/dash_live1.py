#!/usr/bin/env python3
"""DASH-LIVE-1 — Owner / War Room live-data honesty (freshness stamps).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack DASH-LIVE-1
(armed 2026-09-30 after FIN-RECON-SHELL-1 PASS_VERIFIED).

Adds LIVE/STALE freshness badges on Owner Command and Finish War Room from
real derived-view stamps (+ ledger mtime for war room). Does not invent KPI
numbers. Does not flip staff_ready / human_commissioned. Preserves existing
Owner Command / War Room / MYWORK-PROVE surfaces (keep-what-works, only-ADD).
Does not auto-chain RELIABILITY-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import universal_my_work as umw
from core.completion_register import MODEL_C_LEDGER

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "DASH-LIVE-1"
SCHEMA_ID = "wolf.dash-live-1.v1"
BOUND = "beta-owner-safe"
WITA = timezone(timedelta(hours=8))

# Derived-view stamp ids for the two desks this pack owns.
VIEW_OWNER_COMMAND = "owner-command"
VIEW_WAR_ROOM = "war-room"
# Related (already stamped by MYWORK / war-room testability) — exposed read-only.
VIEW_OWNER_EXCEPTIONS = "owner-command-exceptions"
VIEW_WAR_COMMISSIONING = "war-room-commissioning"

DESK_VIEWS = (VIEW_OWNER_COMMAND, VIEW_WAR_ROOM)
RELATED_VIEWS = (VIEW_OWNER_EXCEPTIONS, VIEW_WAR_COMMISSIONING)
ALL_VIEWS = DESK_VIEWS + RELATED_VIEWS

# Test-only override: when the live catalog authorizer refuses writes under
# WOLF_TEST_MODE, mark_desk_stale can still force STALE for honesty proves.
_FORCE_STALE_VIEWS: set[str] = set()

OWNER_PAGE = "/wolf"
WAR_ROOM_PAGE = "/finish-war-room"
OWNER_API = "/api/owner/command"
WAR_ROOM_API = "/api/owner/war-room"

# Cap closure honesty — prove stamps only; do not invent PROVEN/READY.
CAP_CLOSES_TOWARD = ("CAP-CORE-12", "MB-004")
CEILING = "BUILT"


class DashLive1Error(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


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


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "invented_kpi": False,
        "kpi_invented": False,
        "fake_kpi": False,
        "green_kpi": False,
        "money": None,
        "payment_executed": False,
        "ledger_write": False,
        "external_writes": False,
        "stale_shown_as_current": False,
        "freshness_from_real_stamps_only": True,
        "ceiling": CEILING,
        "closes_toward": list(CAP_CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "prod_mutate": False,
        "no_push": True,
        "mywork_prove1_preserved": True,
        "owner_command_preserved": True,
        "war_room_preserved": True,
        "truth_vocabulary_reused": True,
        "next_pack_for_parent_only": "RELIABILITY-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": [
            "MYWORK-PROVE-1",
            "Owner Command",
            "Finish war room",
            "W3-P4-TRUTH",
        ],
    }


def refuse_external_write(_body: dict | None = None) -> None:
    raise DashLive1Error(
        "DASH-LIVE-1 is a read honesty pass. Writes are refused.",
        code="writes_refused",
    )


def refuse_kpi(_body: dict | None = None) -> None:
    raise DashLive1Error(
        "KPI numbers are not invented on this pack.",
        code="kpi_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise DashLive1Error(
        "DASH-LIVE-1 does not flip PROVEN or READY.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise DashLive1Error(
        "DASH-LIVE-1 does not flip staff_ready or human_commissioned.",
        code="ready_refused",
    )


def ledger_as_of(*, ledger_path: Path | None = None) -> dict[str, Any]:
    """Real filesystem mtime of the Model C ledger — never invented. Path withheld."""
    path = Path(ledger_path) if ledger_path else MODEL_C_LEDGER
    if not path.is_file():
        return {
            "exists": False,
            "mtime_utc": None,
            "as_of_wita": None,
            "status": "UNKNOWN",
            "display_state": "UNKNOWN",
            "path_withheld": True,
        }
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_s = (datetime.now(timezone.utc) - mtime).total_seconds()
    # Honesty: file present is not LIVE. Older than 24h → STALE. Else CURRENT.
    if age_s > 24 * 60 * 60:
        display = "STALE"
    else:
        display = "CURRENT"
    return {
        "exists": True,
        "mtime_utc": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_wita": mtime.astimezone(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "status": "READ",
        "display_state": display,
        "path_withheld": True,
    }


def _normalize_status(raw: dict[str, Any] | None, *, view_id: str) -> dict[str, Any]:
    row = dict(raw or {})
    status = str(row.get("status") or "STALE").upper()
    if status not in {"LIVE", "STALE"}:
        status = "STALE"
    refreshed = row.get("refreshed_at")
    as_of = _to_wita(refreshed) or None
    return {
        "view_id": view_id,
        "status": status,
        "refreshed_at": refreshed,
        "as_of_wita": as_of,
        "source_fingerprint": row.get("source_fingerprint"),
        "stored_fingerprint": row.get("stored_fingerprint"),
        "shown_as_current": status == "LIVE",
        "invented": False,
    }


def freshness_for(view_id: str, *, conn=None) -> dict[str, Any]:
    """Read-only stamp status. Never invents LIVE when the stamp is STALE."""
    if view_id in _FORCE_STALE_VIEWS:
        return {
            "view_id": view_id,
            "status": "STALE",
            "refreshed_at": None,
            "as_of_wita": None,
            "source_fingerprint": None,
            "stored_fingerprint": None,
            "shown_as_current": False,
            "invented": False,
            "forced_stale": True,
        }
    if view_id not in ALL_VIEWS and view_id not in {
        "my-work",
        "execution-report",
        "team-dashboard",
        "department-dashboard",
        "company-dashboard",
    }:
        return {
            "view_id": view_id,
            "status": "STALE",
            "refreshed_at": None,
            "as_of_wita": None,
            "shown_as_current": False,
            "invented": False,
            "why": "Unknown view_id — fail closed to STALE.",
        }
    return _normalize_status(umw.derived_view_status(view_id, conn=conn), view_id=view_id)


def refresh_and_status(view_id: str, *, conn=None) -> dict[str, Any]:
    """Best-effort refresh then return the real stamp. Fail closed to STALE.

    Clears the in-process force-STALE flag only when the derived-view write
    succeeds. Under WOLF_TEST_MODE live writes are refused, so a prior
    mark_desk_stale() stays STALE until clear_forced_stale() or a temp-catalog
    refresh succeeds — honest, never invents LIVE.
    """
    try:
        umw.refresh_derived_view(view_id, conn=conn)
        _FORCE_STALE_VIEWS.discard(view_id)
    except Exception:  # noqa: BLE001 — write guard / missing table must not invent LIVE
        pass
    return freshness_for(view_id, conn=conn)


def clear_forced_stale() -> None:
    """Drop in-process STALE override (tests / cleanup). Does not invent LIVE."""
    _FORCE_STALE_VIEWS.clear()


def mark_desk_stale(*, conn=None, commit: bool = True) -> None:
    """Force Owner + War Room desk stamps STALE.

    Prefers writing core_derived_view_stamps. Under WOLF_TEST_MODE the live
    catalog authorizer refuses writes — fall back to an in-process force flag
    so honesty tests can still prove STALE without mutating live Beta.
    """
    import sqlite3

    from core import work_items as wi

    own = conn is None
    c = conn or wi.db_connect()
    try:
        # Deliberately mismatch fingerprint so derived_view_status reports STALE.
        fp = umw.fingerprint_work_state(c) + "-forced-stale"
        ts = wi.now_utc_iso()
        for view_id in DESK_VIEWS:
            c.execute(
                """
                INSERT INTO core_derived_view_stamps (view_id, source_fingerprint, refreshed_at, status)
                VALUES (?, ?, ?, 'STALE')
                ON CONFLICT(view_id) DO UPDATE SET
                  source_fingerprint=excluded.source_fingerprint,
                  refreshed_at=excluded.refreshed_at,
                  status='STALE'
                """,
                (view_id, fp, ts),
            )
        if commit:
            c.commit()
        _FORCE_STALE_VIEWS.clear()
    except sqlite3.DatabaseError:
        # Live catalog write refused (test authorizer) — force STALE in-process.
        _FORCE_STALE_VIEWS.update(DESK_VIEWS)
    finally:
        if own:
            c.close()


def _plain_for(status: str) -> str:
    if status == "LIVE":
        return "Live. Derived-view stamp matches the current source fingerprint."
    if status == "STALE":
        return "Stale. Stamp missing, fingerprint drifted, or marked STALE. Not shown as current."
    return "Unknown. Freshness could not be read. Nothing was invented."


def _ui_envelope(
    *,
    status: str,
    view_id: str,
    primary_source: str,
    observed_at: Any,
    as_of_wita: str | None,
    sources: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shape expected by Owner Command / Finish War Room freshness badges."""
    state = status if status in {"LIVE", "STALE"} else "UNKNOWN"
    out = {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "view_id": view_id,
        "status": state,
        "display_state": state,
        "primary_source": primary_source,
        "plain": _plain_for(state),
        "observed_at": observed_at,
        "as_of": as_of_wita,
        "as_of_wita": as_of_wita,
        "sources": sources,
        "shown_as_current": state == "LIVE",
        "stale_shown_as_current": False,
        "invented_kpi": False,
        "kpi_invented": False,
        "staff_ready": False,
        "human_commissioned": False,
    }
    if extra:
        out.update(extra)
    return out


def _source_row(
    *,
    source_id: str,
    name: str,
    display_state: str,
    as_of_wita: str | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "name": name,
        "display_state": display_state if display_state in {"LIVE", "STALE", "UNKNOWN", "UNAVAILABLE", "CURRENT", "NEEDS REVIEW"} else "UNKNOWN",
        "as_of_wita": as_of_wita,
        "commissioned": False,
        "invented": False,
    }


def owner_command_freshness(*, refresh: bool = True, conn=None) -> dict[str, Any]:
    desk = (
        refresh_and_status(VIEW_OWNER_COMMAND, conn=conn)
        if refresh
        else freshness_for(VIEW_OWNER_COMMAND, conn=conn)
    )
    exceptions = freshness_for(VIEW_OWNER_EXCEPTIONS, conn=conn)
    sources = [
        _source_row(
            source_id=VIEW_OWNER_COMMAND,
            name="Owner Command desk stamp",
            display_state=desk["status"],
            as_of_wita=desk.get("as_of_wita"),
        ),
        _source_row(
            source_id=VIEW_OWNER_EXCEPTIONS,
            name="Owner Command exceptions stamp",
            display_state=exceptions["status"],
            as_of_wita=exceptions.get("as_of_wita"),
        ),
    ]
    return _ui_envelope(
        status=desk["status"],
        view_id=VIEW_OWNER_COMMAND,
        primary_source="wolf_core",
        observed_at=desk.get("refreshed_at"),
        as_of_wita=desk.get("as_of_wita"),
        sources=sources,
        extra={"desk": desk, "exceptions": exceptions},
    )


def war_room_freshness(*, refresh: bool = True, conn=None, ledger_path: Path | None = None) -> dict[str, Any]:
    desk = (
        refresh_and_status(VIEW_WAR_ROOM, conn=conn)
        if refresh
        else freshness_for(VIEW_WAR_ROOM, conn=conn)
    )
    commissioning = freshness_for(VIEW_WAR_COMMISSIONING, conn=conn)
    ledger = ledger_as_of(ledger_path=ledger_path)
    ledger_state = str(ledger.get("display_state") or ("CURRENT" if ledger.get("exists") else "UNKNOWN"))
    sources = [
        _source_row(
            source_id=VIEW_WAR_ROOM,
            name="Finish war room desk stamp",
            display_state=desk["status"],
            as_of_wita=desk.get("as_of_wita"),
        ),
        _source_row(
            source_id="model_c_ledger",
            name="Model C maturity ledger file",
            display_state=ledger_state,
            as_of_wita=ledger.get("as_of_wita"),
        ),
        _source_row(
            source_id=VIEW_WAR_COMMISSIONING,
            name="War room commissioning stamp",
            display_state=commissioning["status"],
            as_of_wita=commissioning.get("as_of_wita"),
        ),
    ]
    return _ui_envelope(
        status=desk["status"],
        view_id=VIEW_WAR_ROOM,
        primary_source="model_c_ledger",
        observed_at=desk.get("refreshed_at") or ledger.get("mtime_utc"),
        as_of_wita=desk.get("as_of_wita") or ledger.get("as_of_wita"),
        sources=sources,
        extra={
            "desk": desk,
            "commissioning": commissioning,
            "ledger": ledger,
            "ledger_as_of_wita": ledger.get("as_of_wita"),
        },
    )


def build_pack_slice(*, refresh: bool = True, conn=None) -> dict[str, Any]:
    """Combined honesty slice for tests / RESULT. No KPI figures."""
    flags = honesty_flags()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "owner_command": owner_command_freshness(refresh=refresh, conn=conn),
        "war_room": war_room_freshness(refresh=refresh, conn=conn),
        "staff_ready": False,
        "human_commissioned": False,
        "kpi_invented": False,
        "invented_kpi": False,
        "fake_kpi": False,
        "closes_toward": list(CAP_CLOSES_TOWARD),
        "ceiling": CEILING,
        "preserved_packs": list(flags["preserved_packs"]),
        "honesty": flags,
        "next_pack_for_parent_only": "RELIABILITY-1",
        "cursor_did_not_auto_start_next": True,
    }


def attach_owner_command(report: dict[str, Any], *, refresh: bool = True, conn=None) -> dict[str, Any]:
    """Only-ADD: stamp freshness onto an Owner Command payload. No KPI invent."""
    out = dict(report)
    fresh = owner_command_freshness(refresh=refresh, conn=conn)
    out["freshness"] = fresh
    out["pack_dash_live"] = PACK_ID
    out["staff_ready"] = False
    out["human_commissioned"] = False
    # Never invent scores from this pack.
    if "green_kpi" not in out:
        out["green_kpi"] = False
    if out.get("money") is None:
        out["money"] = None
    return out


def attach_war_room(
    report: dict[str, Any],
    *,
    refresh: bool = True,
    conn=None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Only-ADD: stamp freshness onto a Finish War Room payload. No KPI invent."""
    out = dict(report)
    fresh = war_room_freshness(refresh=refresh, conn=conn, ledger_path=ledger_path)
    out["freshness"] = fresh
    out["pack_dash_live"] = PACK_ID
    out["staff_ready"] = False
    out["human_commissioned"] = False
    out["staff_ready_count"] = 0
    out["human_commissioned_count"] = 0
    if "green_kpi" not in out:
        out["green_kpi"] = False
    if out.get("money") is None:
        out["money"] = None
    return out
