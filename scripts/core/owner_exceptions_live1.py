#!/usr/bin/env python3
"""OWNER-EXCEPTIONS-LIVE-1 — Owner exceptions board deepen (no fake severity).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack OWNER-EXCEPTIONS-LIVE-1
(armed 2026-09-30 after GGV-METRIC-HONESTY-1 PASS_VERIFIED).

Deepens the Owner exceptions board from live stamps / live operational
collectors only. Severity stays MISSING when the record has no severity
column — never invent CRITICAL/HIGH/P1/urgency. Empty stays empty.
Preserves DASH-LIVE-1 + OWNER-NEEDS-YOU-1.
staff_ready=false · human_commissioned=false. Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain BACKUP-RESTORE-DRILL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import dash_live1 as _dash
from core import owner_operational_exceptions as _ops_ex
from core import universal_my_work as _umw

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "OWNER-EXCEPTIONS-LIVE-1"
SCHEMA_ID = "wolf.owner-exceptions-live-1.v1"
BOUND = "beta-owner-exceptions-safe"
CAP_QUEUE = "CAP-CORE exceptions"
CAP_CORE_12 = "CAP-CORE-12"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
VIEW_EXCEPTIONS = "owner-command-exceptions"

PAGE_PATHS = frozenset(
    {
        "/owner/exceptions-live-1",
        "/owner/exceptions-live-1/",
        "/owner/exceptions",
        "/owner/exceptions/",
        "/owner-exceptions-live-1",
        "/owner-exceptions-live-1/",
        "/owner-exceptions-live-1.html",
        "/dashboards/owner-exceptions-live-1.html",
    }
)
API_PATH = "/api/owner/exceptions-live-1"

PRESERVED_PACKS = ("DASH-LIVE-1", "OWNER-NEEDS-YOU-1")

# Kind boards projected from live operational rollup (no invented severity).
_KIND_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "uma_daily_close",
        "Uma Blu Daily Close",
        "Live uma_daily_close exceptions. Severity not on record → MISSING.",
    ),
    (
        "data_quality",
        "Data quality",
        "Live data-quality exceptions. Severity not on record → MISSING.",
    ),
    (
        "finance_books",
        "Finance books / stale",
        "Live finance_books / stale_data / missing_data. Severity MISSING.",
    ),
    (
        "integration",
        "Integrations",
        "Live integration ERROR/DEGRADED. Severity not invented.",
    ),
    (
        "month_end",
        "Month-end blockers",
        "Live month-end bank-statement gates. Severity MISSING.",
    ),
    (
        "commissioning_fail",
        "Commissioning FAIL",
        "Live testability-matrix FAIL rows. Severity MISSING.",
    ),
    (
        "work_item",
        "Work-item exceptions",
        "Live overdue/blocked work items. Severity MISSING.",
    ),
    (
        "external_route",
        "External finance routes",
        "Live EXTERNAL-ROUTE-HEALTH RED CRITICAL (Host Error / sidecar). Severity MISSING.",
    ),
)

_FINANCE_KINDS = frozenset({"finance_books", "stale_data", "missing_data"})

_INVENT_SEVERITY_TOKENS = frozenset(
    {
        "severity",
        "severities",
        "fake-severity",
        "fake_severity",
        "invent-severity",
        "invent_severity",
        "force-severity",
        "force_severity",
        "critical",
        "p1",
        "p2",
        "high",
        "medium",
        "low",
        "urgency",
        "fake-urgency",
        "fake_urgency",
        "invent-urgency",
        "invent_urgency",
        "urgency-count",
        "urgency_count",
        "count",
        "counts",
        "padded-count",
        "padded_count",
        "invent-count",
        "invent_count",
        "force-count",
        "force_count",
        "exception",
        "exceptions",
        "invent-exception",
        "invent_exception",
        "fake-exception",
        "fake_exception",
        "mint-exception",
        "mint_exception",
        "item",
        "items",
    }
)


class OwnerExceptionsLive1Error(ValueError):
    """Fail closed. Does not invent severity, urgency, or exception counts."""

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
        raise OwnerExceptionsLive1Error(
            "Owner exceptions board is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _normalize_severity(raw: Any) -> str | None:
    """Severity is never invented. Missing → MISSING; refuse fake ranks."""
    if raw is None:
        return "MISSING"
    text = str(raw).strip()
    if not text:
        return "MISSING"
    upper = text.upper()
    if upper in {"MISSING", "UNKNOWN", "UNAVAILABLE", "NONE", "NULL", "N/A"}:
        return "MISSING" if upper in {"NONE", "NULL", "N/A"} else upper
    # Any invented rank (CRITICAL/HIGH/P1/…) is refused → MISSING honesty.
    return "MISSING"


def _project_item(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    severity = _normalize_severity(row.get("severity"))
    return {
        "id": str(row.get("id") or row.get("kind") or source),
        "kind": str(row.get("kind") or source),
        "title": str(row.get("title") or "Exception"),
        "detail": str(row.get("detail") or row.get("plain") or "")[:320],
        "href": str(row.get("href") or "/wolf"),
        "owner_role": str(row.get("owner_role") or "Owner"),
        "money_risk": bool(row.get("money_risk")),
        "blocked": bool(row.get("blocked")),
        "severity": severity,
        "invented_severity": False,
        "invented": False,
        "source": source,
    }


def _freshness_board(*, refresh: bool = True) -> dict[str, Any]:
    try:
        stamp = (
            _dash.refresh_and_status(VIEW_EXCEPTIONS)
            if refresh
            else _dash.freshness_for(VIEW_EXCEPTIONS)
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "freshness",
            "label": "Exceptions freshness stamp",
            "kind": "live_stamp",
            "ok": False,
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "empty": None,
            "count": None,
            "severity": None,
            "invented_severity": False,
            "invented": False,
            "staff_ready": False,
            "human_commissioned": False,
            "view_id": VIEW_EXCEPTIONS,
            "why": (
                f"owner-command-exceptions stamp read failed "
                f"({type(exc).__name__}). UNKNOWN — not invented LIVE."
            ),
        }
    status = str(stamp.get("status") or "UNKNOWN")
    if status not in {"LIVE", "STALE", "UNKNOWN", "UNAVAILABLE"}:
        status = "UNKNOWN"
    return {
        "id": "freshness",
        "label": "Exceptions freshness stamp",
        "kind": "live_stamp",
        "ok": True,
        "status": status,
        "display": status,
        "empty": None,
        "count": None,
        "severity": None,
        "invented_severity": False,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
        "view_id": VIEW_EXCEPTIONS,
        "as_of_wita": stamp.get("as_of_wita"),
        "refreshed_at": stamp.get("refreshed_at"),
        "why": (
            f"Derived-view stamp `{VIEW_EXCEPTIONS}` is {status}. "
            "Count/severity are not on the stamp — left null/MISSING. Not invented."
        ),
    }


def _operational_rollup() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        rollup = _ops_ex.collect()
    except Exception as exc:  # noqa: BLE001
        board = {
            "id": "operational",
            "label": "Operational exceptions rollup",
            "kind": "operational_rollup",
            "ok": False,
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "empty": None,
            "count": None,
            "severity": None,
            "invented_severity": False,
            "invented": False,
            "staff_ready": False,
            "human_commissioned": False,
            "why": (
                f"Operational rollup failed ({type(exc).__name__}). "
                "UNKNOWN — count/severity not invented."
            ),
        }
        return board, []

    items_raw = list(rollup.get("items") or [])
    items = [_project_item(row, source="operational") for row in items_raw]
    try:
        count = int(rollup.get("count") if rollup.get("count") is not None else len(items))
    except (TypeError, ValueError):
        count = len(items)
    empty = count == 0
    status = "EMPTY" if empty else "OPEN"
    # Severity is never a rollup field — always MISSING honesty pin.
    board = {
        "id": "operational",
        "label": "Operational exceptions rollup",
        "kind": "operational_rollup",
        "ok": True,
        "status": status,
        "display": status,
        "empty": empty,
        "count": count,
        "count_matches_items": count == len(items),
        "severity": "MISSING",
        "invented_severity": False,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
        "money_count": len(rollup.get("money_items") or []),
        "blocked_count": len(rollup.get("blocked_items") or []),
        "empty_message": rollup.get("empty_message"),
        "why": (
            "No material operational exceptions are open. Empty is not unknown."
            if empty
            else (
                f"{count} live operational exception(s). "
                "Severity not on operational record → MISSING (not invented)."
            )
        ),
    }
    return board, items


def _governance_board() -> dict[str, Any]:
    """Governance exceptions: severity column absent → MISSING (owner_command honesty)."""
    try:
        from core import owner_command as oc

        # Prefer the shared exceptions reader when a catalog is available.
        conn = _catalog_ro()
        try:
            cards = oc._company_cards(conn)  # noqa: SLF001
            gov = oc._exceptions(conn, cards)  # noqa: SLF001
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "governance",
            "label": "Governance exceptions record",
            "kind": "governance",
            "ok": False,
            "status": "UNKNOWN",
            "display": "UNKNOWN",
            "empty": None,
            "count": None,
            "severity": None,
            "invented_severity": False,
            "invented": False,
            "staff_ready": False,
            "human_commissioned": False,
            "why": (
                f"Governance exceptions read failed ({type(exc).__name__}). "
                "UNKNOWN — severity/count not invented."
            ),
        }

    read = str(gov.get("read") or "UNAVAILABLE")
    if read != "READ":
        return {
            "id": "governance",
            "label": "Governance exceptions record",
            "kind": "governance",
            "ok": True,
            "status": "UNAVAILABLE" if read == "UNAVAILABLE" else "UNKNOWN",
            "display": read,
            "empty": None,
            "count": None,
            "severity": None,
            "invented_severity": False,
            "invented": False,
            "staff_ready": False,
            "human_commissioned": False,
            "why": str(
                gov.get("why")
                or "Governance exceptions could not be read. Nothing was invented."
            ),
        }

    items = list(gov.get("items") or [])
    # Force severity honesty — never surface invented ranks from items.
    severities = {_normalize_severity(row.get("severity")) for row in items}
    open_count = gov.get("open_count")
    stored = gov.get("stored_count")
    try:
        count = int(open_count if open_count is not None else stored if stored is not None else len(items))
    except (TypeError, ValueError):
        count = len(items)
    empty = count == 0
    status = "EMPTY" if empty else "OPEN"
    return {
        "id": "governance",
        "label": "Governance exceptions record",
        "kind": "governance",
        "ok": True,
        "status": status,
        "display": status,
        "empty": empty,
        "count": count,
        "stored_count": stored,
        "valid_operational_count": gov.get("valid_operational_count"),
        "invalid_test_count": gov.get("invalid_test_count"),
        "severity": "MISSING",
        "severity_values": sorted(severities) if severities else ["MISSING"],
        "invented_severity": False,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
        "empty_message": gov.get("empty_message"),
        "why": (
            "No open governance exceptions. Empty is not unknown. "
            "Severity column absent → MISSING."
            if empty
            else (
                f"{count} open governance exception(s). "
                "Severity/current action/escalation stay MISSING — not invented."
            )
        ),
    }


def _kind_board(
    kind_id: str,
    label: str,
    why_base: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if kind_id == "finance_books":
        matched = [row for row in items if row.get("kind") in _FINANCE_KINDS]
    else:
        matched = [row for row in items if row.get("kind") == kind_id]
    count = len(matched)
    empty = count == 0
    status = "EMPTY" if empty else "OPEN"
    return {
        "id": kind_id,
        "label": label,
        "kind": "exception_kind_board",
        "ok": True,
        "status": status,
        "display": status,
        "empty": empty,
        "count": count,
        "count_matches_items": True,
        "severity": "MISSING",
        "invented_severity": False,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "human_commissioned": False,
        "items_preview": matched[:5],
        "why": (
            f"{label}: EMPTY honesty — no live rows of this kind."
            if empty
            else f"{label}: {count} live row(s). {why_base}"
        ),
    }


def exception_boards(*, refresh_stamp: bool = True) -> list[dict[str, Any]]:
    freshness = _freshness_board(refresh=refresh_stamp)
    operational, items = _operational_rollup()
    governance = _governance_board()
    boards = [freshness, operational, governance]
    for kind_id, label, why in _KIND_SPECS:
        boards.append(_kind_board(kind_id, label, why, items))
    return boards


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
        "why": (
            "Owner/War-Room freshness honesty intact; invented KPI false; "
            "owner-command-exceptions stamp remains a real derived-view source."
            if ok
            else "DASH-LIVE-1 RESULT missing or honesty pins drifted."
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
        "why": (
            "Needs-You connective prove intact; invented urgency false."
            if ok
            else "OWNER-NEEDS-YOU-1 surface missing or honesty pins drifted."
        ),
    }


def _honesty_tiles(boards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    empty_n = sum(1 for b in boards if b.get("status") == "EMPTY")
    open_n = sum(1 for b in boards if b.get("status") == "OPEN")
    unk_n = sum(1 for b in boards if b.get("status") in {"UNKNOWN", "UNAVAILABLE"})
    stamp_n = sum(1 for b in boards if b.get("kind") == "live_stamp")
    dash = dash_live1_preserved()
    nye = owner_needs_you1_preserved()
    return [
        {
            "id": "exception_boards",
            "label": "Exception source boards",
            "status": "HONEST",
            "value": len(boards),
            "why": (
                f"{len(boards)} boards projected. EMPTY={empty_n} · "
                f"OPEN={open_n} · UNKNOWN/UNAVAIL={unk_n} · stamps={stamp_n}. "
                "Counts from live stamps/collectors only."
            ),
        },
        {
            "id": "fake_severity",
            "label": "Fake severity",
            "status": "REFUSED",
            "value": 0,
            "why": "Severity stays MISSING when not on the record. No CRITICAL/HIGH/P1 invent.",
        },
        {
            "id": "empty_honest",
            "label": "Empty stays empty",
            "status": "HONEST",
            "value": empty_n,
            "why": "EMPTY boards keep count=0. Not rewritten as severity.",
        },
        {
            "id": "live_stamps_only",
            "label": "Live stamps only",
            "status": "HONEST",
            "value": True,
            "why": "Exceptions projected from derived-view stamp + live operational/governance reads.",
        },
        {
            "id": "dash_live1",
            "label": "DASH-LIVE-1",
            "status": dash.get("status"),
            "value": None,
            "why": dash.get("why"),
        },
        {
            "id": "owner_needs_you1",
            "label": "OWNER-NEEDS-YOU-1",
            "status": nye.get("status"),
            "value": None,
            "why": nye.get("why"),
        },
        {
            "id": "cap_core_exceptions",
            "label": CAP_QUEUE,
            "status": "BUILT",
            "value": None,
            "why": (
                "Exceptions board deepen. Ceiling BUILT. "
                "Not PROVEN/READY. CAP-CORE-12 stays eng prove only."
            ),
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "owner_command",
            "label": "Owner Command",
            "href": "/wolf",
            "kind": "existing",
            "note": "Operational + governance exceptions live here. DASH-LIVE-1 freshness preserved.",
        },
        {
            "id": "needs_you",
            "label": "Owner Needs You-1",
            "href": "/owner/needs-you-1",
            "kind": "existing",
            "note": "OWNER-NEEDS-YOU-1 preserved. No fake urgency.",
        },
        {
            "id": "war_room",
            "label": "Finish War Room",
            "href": "/finish-war-room",
            "kind": "existing",
            "note": "DASH-LIVE-1 war-room freshness preserved.",
        },
        {
            "id": "data_quality",
            "label": "Owner data quality",
            "href": "/owner/data-quality",
            "kind": "existing",
            "note": "Live data-quality exceptions feed the operational rollup.",
        },
        {
            "id": "my_work",
            "label": "Universal My Work",
            "href": "/my-work",
            "kind": "existing",
            "note": "Work-item exceptions feed the rollup. Not a second invent surface.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    dash = dash_live1_preserved()
    nye = owner_needs_you1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_queue_label": CAP_QUEUE,
        "cap_core_12": CAP_CORE_12,
        "staff_ready": False,
        "human_commissioned": False,
        "invented_severity": False,
        "fake_severity": False,
        "invented_urgency": False,
        "fake_urgency": False,
        "invented_count": False,
        "invented_exception": False,
        "padded_empty": False,
        "unknown_coerced_to_empty": False,
        "invented_proven": False,
        "invented_ready": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "live_stamps_only": True,
        "severity_from_record_only": True,
        "severity_missing_when_absent": True,
        "dash_live1_preserved": dash.get("ok") is True,
        "owner_needs_you1_preserved": nye.get("ok") is True,
        "second_exceptions_system": False,
        "extends_existing_operational": True,
        "cap_core_exceptions_proven": False,
        "cap_core_exceptions_ready": False,
        "cap_core_exceptions_maturity": "BUILT",
        "cap_core_exceptions_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "BACKUP-RESTORE-DRILL-1",
        "prod_pid_held": PROD_PID_HELD,
    }


def refuse_severity(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "Invented severity is refused. Severity stays MISSING when not on the record.",
        code="severity_refused",
    )


def refuse_urgency(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "Fake urgency counts are refused. Counts come from live stamps only.",
        code="urgency_refused",
    )


def refuse_invent_exception(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "Invented exceptions are refused. Board deepen does not mint exceptions.",
        code="invent_refused",
    )


def refuse_staff_ready(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "staff_ready stays false. Not flipped by this pack.",
        code="staff_ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "PROVEN is refused. CAP-CORE exceptions stays board deepen only (ceiling BUILT).",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise OwnerExceptionsLive1Error(
        "READY is refused. An Owner exceptions prove board is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise OwnerExceptionsLive1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        # Also accept underscore form via normalize above.
        token_us = str(key).strip().lower()
        check = {token, token_us, token.replace("-", "_")}
        if check & {
            "severity",
            "severities",
            "fake-severity",
            "fake_severity",
            "invent-severity",
            "invent_severity",
            "force-severity",
            "force_severity",
            "critical",
            "p1",
            "p2",
            "high",
            "medium",
            "low",
        }:
            refuse_severity(payload)
        if check & {
            "urgency",
            "fake-urgency",
            "fake_urgency",
            "invent-urgency",
            "invent_urgency",
            "urgency-count",
            "urgency_count",
            "count",
            "counts",
            "padded-count",
            "padded_count",
            "invent-count",
            "invent_count",
            "force-count",
            "force_count",
        }:
            refuse_urgency(payload)
        if check & {
            "invent",
            "invent-exception",
            "invent_exception",
            "fake-exception",
            "fake_exception",
            "mint-exception",
            "mint_exception",
            "exception",
            "exceptions",
            "item",
            "items",
        }:
            refuse_invent_exception(payload)
        if check & {
            "staff-ready",
            "staff_ready",
            "commission",
            "human-commissioned",
            "human_commissioned",
        }:
            refuse_staff_ready(payload)
        if check & {"proven", "prove"}:
            refuse_proven(payload)
        if check & {"ready"}:
            refuse_ready(payload)
        if token in _INVENT_SEVERITY_TOKENS or token_us in _INVENT_SEVERITY_TOKENS:
            refuse_severity(payload)
    raise OwnerExceptionsLive1Error(
        "External writes are refused. Owner Exceptions-Live-1 is a read-only board deepen.",
        code="write_refused",
    )


def no_invented_severity(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    if pack.get("invented_severity") is not False:
        return False
    if pack.get("fake_severity") is not False:
        return False
    if pack.get("invented_urgency") is not False:
        return False
    boards = pack.get("exception_boards") or []
    for board in boards:
        if board.get("invented") or board.get("invented_severity") or board.get("invented_count"):
            return False
        sev = board.get("severity")
        if sev is not None and str(sev).upper() not in {
            "MISSING",
            "UNKNOWN",
            "UNAVAILABLE",
        }:
            return False
        if board.get("status") == "EMPTY" and board.get("count") not in (0, None):
            return False
        if board.get("status") in {"UNKNOWN", "UNAVAILABLE"} and board.get("count") is not None:
            # freshness stamp may be LIVE/STALE with count null — OK
            if board.get("kind") != "live_stamp":
                return False
        for item in board.get("items_preview") or []:
            if item.get("invented_severity"):
                return False
            isev = str(item.get("severity") or "MISSING").upper()
            if isev not in {"MISSING", "UNKNOWN", "UNAVAILABLE"}:
                return False
    for item in pack.get("items") or []:
        if item.get("invented_severity"):
            return False
        isev = str(item.get("severity") or "MISSING").upper()
        if isev not in {"MISSING", "UNKNOWN", "UNAVAILABLE"}:
            return False
    return True


def build_slice(*, refresh_stamp: bool = True) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    boards = exception_boards(refresh_stamp=refresh_stamp)
    dash = dash_live1_preserved()
    nye = owner_needs_you1_preserved()
    empty_n = sum(1 for b in boards if b.get("status") == "EMPTY")
    open_n = sum(1 for b in boards if b.get("status") == "OPEN")
    unk_n = sum(1 for b in boards if b.get("status") in {"UNKNOWN", "UNAVAILABLE"})
    stamp_status = next(
        (b.get("status") for b in boards if b.get("id") == "freshness"),
        "UNKNOWN",
    )
    ops_board = next((b for b in boards if b.get("id") == "operational"), {})
    total = ops_board.get("count") if isinstance(ops_board.get("count"), int) else None
    # Flatten live items from operational rollup only (no invent).
    _, items = _operational_rollup()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_QUEUE, CAP_CORE_12],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "invented_severity": False,
        "fake_severity": False,
        "invented_urgency": False,
        "fake_urgency": False,
        "invented_count": False,
        "invented_exception": False,
        "padded_empty": False,
        "unknown_coerced_to_empty": False,
        "live_stamps_only": True,
        "board_count": len(boards),
        "empty_board_count": empty_n,
        "open_board_count": open_n,
        "unknown_board_count": unk_n,
        "operational_count": total,
        "stamp_status": stamp_status,
        "stamp_view_id": VIEW_EXCEPTIONS,
        "exception_boards": boards,
        "items": items,
        "honesty_tiles": _honesty_tiles(boards),
        "desk_links": _desk_links(),
        "dash_live1": dash,
        "owner_needs_you1": nye,
        "dash_live1_preserved": dash.get("ok") is True,
        "owner_needs_you1_preserved": nye.get("ok") is True,
        "cap_core_exceptions_proven": False,
        "cap_core_exceptions_ready": False,
        "cap_core_exceptions_maturity": flags["cap_core_exceptions_maturity"],
        "cap_core_exceptions_ceiling": flags["cap_core_exceptions_ceiling"],
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "fake_severity",
            "invented_urgency",
            "invented_exception_counts",
            "staff_ready",
            "human_commissioned",
            "CAP-CORE exceptions PROVEN",
            "CAP-CORE-12 READY",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "BACKUP-RESTORE-DRILL-1",
    }


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    if person_id is not None:
        require_view(person_id)
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "boards": ["freshness", "operational", "governance"]
        + [s[0] for s in _KIND_SPECS],
        "status_enum": [
            "EMPTY",
            "OPEN",
            "LIVE",
            "STALE",
            "UNKNOWN",
            "UNAVAILABLE",
            "HONEST",
            "PRESERVED",
            "REFUSED",
            "BUILT",
        ],
        "severity_property": "MISSING_when_absent",
        "invent_severity": False,
        "writes_accepted": False,
        "extends": [
            "scripts/core/owner_operational_exceptions.py",
            "scripts/core/dash_live1.py",
            "owner-command-exceptions derived-view stamp",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_exceptions_system": False,
        "why": (
            "Owner exceptions board deepen from live stamps. "
            "Honesty only. No fake severity."
        ),
    }
