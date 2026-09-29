#!/usr/bin/env python3
"""BZG-LABOR-COST-1 — BZG labor cost honesty shell (no fake payroll).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-LABOR-COST-1
(armed 2026-09-30 after FIN-CASH-TRUTH-1 PASS_VERIFIED).

Labor cost desk for BZG. UNKNOWN when no facts. Never invent wages, hours,
headcount, overtime, or payroll runs. Preserves BZG-OPS-DESK-1. Preserves
HR deferred (do not flip). staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain GGV-PIPELINE-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_ops_desk1 as _ops
from core import v1_status_register as _v1

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
PHASE2_QUEUE = BETA_ROOT / "state" / "final-completion" / "PHASE2-PACK-QUEUE.json"

PACK_ID = "BZG-LABOR-COST-1"
SCHEMA_ID = "wolf.bzg-labor-cost-1.v1"
BOUND = "beta-bzg-labor-cost-safe"
CAP_LABOR = "CAP-BZG labor"
LEGAL_ENTITY = "ENT-BZG"
OWNER_PERSON = "PERS-MATT"
BOARD_PERM = "atrium.board.read"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/bzg/labor-cost-1",
        "/bzg/labor-cost-1/",
        "/bzg/labor-cost",
        "/bzg/labor-cost/",
        "/bzg-labor-cost-1",
        "/bzg-labor-cost-1/",
        "/bzg-labor-cost",
        "/bzg-labor-cost/",
        "/bzg-labor-cost-1.html",
        "/dashboards/bzg-labor-cost-1.html",
    }
)
API_PATH = "/api/bzg/labor-cost-1"

PRESERVED_PACKS = ("BZG-OPS-DESK-1",)

# Labor cost stubs — structure only. Values stay null/UNKNOWN until real facts.
_LABOR_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "labor_cost_total",
        "Labor cost · total",
        "Aggregate BZG labor cost. No payroll facts. UNKNOWN — never invent.",
    ),
    (
        "wage_cost",
        "Wage cost",
        "Wage / base pay stub. No payroll facts. UNKNOWN — never invent.",
    ),
    (
        "overtime_cost",
        "Overtime cost",
        "Overtime stub. No OT facts. UNKNOWN — never invent.",
    ),
    (
        "headcount",
        "Headcount",
        "BZG headcount stub. No roster facts. UNKNOWN — never invent.",
    ),
    (
        "hours_worked",
        "Hours worked",
        "Hours stub. No timeclock facts. UNKNOWN — never invent.",
    ),
    (
        "payroll_run",
        "Payroll run",
        "Payroll run stub. HR deferred — no fake payroll. UNKNOWN.",
    ),
)

_FAKE_PAYROLL_TOKENS = frozenset(
    {
        "payroll",
        "fake-payroll",
        "fake_payroll",
        "invent-payroll",
        "invent_payroll",
        "payroll-run",
        "payroll_run",
        "wage",
        "wages",
        "wage-cost",
        "wage_cost",
        "labor",
        "labor-cost",
        "labor_cost",
        "overtime",
        "overtime-cost",
        "overtime_cost",
        "headcount",
        "hours",
        "hours-worked",
        "hours_worked",
        "salary",
        "salaries",
        "pay",
        "payslip",
        "payslips",
        "invent",
        "invent-labor",
        "invent_labor",
        "fake-labor",
        "fake_labor",
        "fill",
    }
)


class BzgLaborCost1Error(ValueError):
    """Fail closed. Does not invent labor cost or payroll."""

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
    """Owner progress.read or BZG board (Zayen). Amanda / unsigned fail closed."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        if _rbac.can(pid, "progress.read", {}, conn=c):
            return True
        if _rbac.can(pid, BOARD_PERM, {"entity_id": LEGAL_ENTITY}, conn=c):
            return True
        return False
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise BzgLaborCost1Error(
            "BZG labor cost desk is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _labor_slot(stub_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "kind": "labor_cost_stub",
        "entity": "BZG",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "value": None,
        "amount": None,
        "currency": None,
        "fact_count": 0,
        "last_fact_at": None,
        "last_success": None,
        "fake_payroll": False,
        "invented_labor_cost": False,
        "payroll_executed": False,
        "why": why,
    }


def _labor_slots() -> list[dict[str, Any]]:
    return [_labor_slot(*spec) for spec in _LABOR_SLOT_SPECS]


def hr_deferred_stamp() -> dict[str, Any]:
    """Read-only: HR stays deferred. Do not flip."""
    deferred = True
    source = "default"
    try:
        reg = _v1.load_register()
        deferred = reg.get("hr_deferred") is True
        source = "v1_status_register"
    except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError):
        deferred = True
        source = "default_fail_closed"
    queue_flag = True
    try:
        if PHASE2_QUEUE.is_file():
            q = json.loads(PHASE2_QUEUE.read_text(encoding="utf-8"))
            if isinstance(q, dict) and "hr_deferred_not_in_queue" in q:
                queue_flag = q.get("hr_deferred_not_in_queue") is True
    except (OSError, json.JSONDecodeError):
        queue_flag = True
    ok = deferred is True and queue_flag is True
    return {
        "ok": ok,
        "hr_deferred": deferred is True,
        "hr_deferred_not_flipped": True,
        "hr_deferred_not_in_queue": queue_flag is True,
        "status": "DEFERRED" if deferred else "CHECK_FAILED",
        "source": source,
        "why": (
            "HR deferred preserved. Labor cost honesty shell does not flip "
            "HR commissioning or invent payroll. CAP-HR stays out of Phase 2 queue."
            if ok
            else "HR deferred stamp check failed — must not flip HR."
        ),
    }


def bzg_ops_desk1_preserved() -> dict[str, Any]:
    """Read-only: BZG-OPS-DESK-1 still honest empty / no invented sales."""
    try:
        desk = _ops.build_desk(OWNER_PERSON)
        flags = _ops.honesty_flags()
        sc = desk.get("status_checks") or {}
        ok = (
            desk.get("ok") is True
            and desk.get("staff_ready") is False
            and desk.get("human_commissioned") is False
            and flags.get("invented_sales") is False
            and flags.get("unknown_when_facts_missing") is True
            and bool(sc.get("master_insufficient_facts"))
        )
        return {
            "ok": ok,
            "staff_ready": desk.get("staff_ready"),
            "human_commissioned": desk.get("human_commissioned"),
            "invented_sales": flags.get("invented_sales"),
            "master_insufficient_facts": bool(sc.get("master_insufficient_facts")),
            "why": (
                "BZG-OPS-DESK-1 preserved: master insufficient_facts, "
                "invented_sales=false, staff_ready/human_commissioned false. "
                "This pack adds labor honesty — does not replace ops desk."
                if ok
                else "BZG-OPS-DESK-1 check failed — pack must not break ops desk."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "BZG-OPS-DESK-1 check failed — pack must not break ops desk.",
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "bzg_ops_desk",
            "label": "BZG Ops Desk",
            "href": "/bzg/ops-desk",
            "kind": "existing",
            "note": "Upstream ops unify. Preserved — not replaced.",
        },
        {
            "id": "bzg_waste_yield",
            "label": "BZG Waste / Yield",
            "href": "/bzg/waste-yield",
            "kind": "existing",
            "note": "Variance/BOM honesty. Separate from labor.",
        },
        {
            "id": "bzg_finance",
            "label": "BZG finance desk",
            "href": "/bzg/finance",
            "kind": "existing",
            "note": "BZG COA template shell. No labor invent from finance.",
        },
        {
            "id": "v1_status",
            "label": "V1 status (HR deferred)",
            "href": "/ops/v1-status",
            "kind": "existing",
            "note": "HR deferred stamp lives here. Do not flip.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    ops = bzg_ops_desk1_preserved()
    hr = hr_deferred_stamp()
    return [
        {
            "id": "labor_slots",
            "label": "Labor cost slots",
            "status": "UNKNOWN",
            "value": None,
            "why": "No payroll/roster facts → labor values UNKNOWN (not zero).",
        },
        {
            "id": "fake_payroll",
            "label": "Fake payroll",
            "status": "REFUSED",
            "value": False,
            "why": "Fake payroll / invent labor cost writes are refused.",
        },
        {
            "id": "hr_deferred",
            "label": "HR deferred",
            "status": hr.get("status") or "DEFERRED",
            "value": hr.get("hr_deferred"),
            "why": hr.get("why"),
        },
        {
            "id": "bzg_ops_desk1",
            "label": "BZG-OPS-DESK-1",
            "status": "PRESERVED" if ops.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": ops.get("why"),
        },
        {
            "id": "cap_bzg_labor",
            "label": "CAP-BZG labor",
            "status": "SPECIFIED",
            "value": None,
            "why": "Labor cost honesty shell only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    ops = bzg_ops_desk1_preserved()
    hr = hr_deferred_stamp()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_bzg_labor": CAP_LABOR,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_payroll": False,
        "invented_labor_cost": False,
        "invented_wages": False,
        "invented_overtime": False,
        "invented_headcount": False,
        "invented_hours": False,
        "invented_payroll_run": False,
        "payroll_executed": False,
        "payroll_write": False,
        "live_payroll": False,
        "zero_as_success": False,
        "unknown_when_facts_missing": True,
        "empty_slots_honest": True,
        "labor_unknown": True,
        "hr_deferred": hr.get("hr_deferred") is True,
        "hr_deferred_not_flipped": True,
        "hr_deferred_preserved": hr.get("ok") is True,
        "bzg_ops_desk1_preserved": ops.get("ok") is True,
        "replaces_ops_desk_page": False,
        "second_labor_system": False,
        "cap_bzg_labor_proven": False,
        "cap_bzg_labor_ready": False,
        "cap_bzg_labor_maturity": "SPECIFIED",
        "cap_bzg_labor_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "production": False,
        "anon_fail_closed": True,
        "amanda_deny_bzg": True,
        "owner_read": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "GGV-PIPELINE-TRUTH-1",
    }


def refuse_fake_payroll(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "Fake payroll is refused. Labor cost stays UNKNOWN until real facts.",
        code="fake_payroll_refused",
        http_status=403,
    )


def refuse_invent_labor(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "Invented labor cost / wages / hours / headcount are refused.",
        code="invent_labor_refused",
        http_status=403,
    )


def refuse_payroll_write(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "Payroll writes are refused. HR deferred — no payroll execute.",
        code="payroll_write_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "PROVEN is refused. CAP-BZG labor stays SPECIFIED. Empty labor is not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "READY is refused. An empty labor cost desk is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_hr_flip(_body: dict | None = None) -> None:
    raise BzgLaborCost1Error(
        "Flipping HR deferred is refused. HR stays deferred.",
        code="hr_flip_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise BzgLaborCost1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"hr", "hr-deferred", "hr_deferred", "undefer-hr", "commission-hr"}:
            refuse_hr_flip(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if token in {
            "payroll",
            "fake-payroll",
            "payroll-run",
            "payroll-execute",
            "payslip",
            "payslips",
        } or norm in {
            "payroll",
            "fake_payroll",
            "payroll_run",
            "payroll_execute",
            "payslip",
            "payslips",
        }:
            refuse_fake_payroll(payload)
        if token in _FAKE_PAYROLL_TOKENS or norm in {
            t.replace("-", "_") for t in _FAKE_PAYROLL_TOKENS
        }:
            if "payroll" in token or "payroll" in norm:
                refuse_fake_payroll(payload)
            refuse_invent_labor(payload)
        if token in {"pay", "payment", "transfer", "bank"}:
            refuse_payroll_write(payload)
    raise BzgLaborCost1Error(
        "BZG-LABOR-COST-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_labor_slots_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    slots = pack.get("labor_slots") or []
    if not slots:
        return False
    return all(
        s.get("value") is None
        and s.get("amount") is None
        and s.get("fact_count") == 0
        and s.get("last_success") is None
        and s.get("fake_payroll") is False
        and s.get("invented_labor_cost") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        for s in slots
    )


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility
    when person_id is None (tests); require_view when person_id provided."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    slots = _labor_slots()
    ops = bzg_ops_desk1_preserved()
    hr = hr_deferred_stamp()
    fact_count = sum(int(s.get("fact_count") or 0) for s in slots)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_LABOR],
        "title": "BZG Labor Cost Honesty Shell",
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "fake_payroll": False,
        "invented_labor_cost": False,
        "invented_wages": False,
        "invented_overtime": False,
        "invented_headcount": False,
        "invented_hours": False,
        "invented_payroll_run": False,
        "payroll_executed": False,
        "payroll_write": False,
        "live_payroll": False,
        "fact_count": fact_count,
        "labor_unknown": fact_count == 0,
        "last_success": None,
        "hr_deferred": hr.get("hr_deferred") is True,
        "hr_deferred_not_flipped": True,
        "hr_deferred_preserved": hr.get("ok") is True,
        "bzg_ops_desk1_preserved": ops.get("ok") is True,
        "cap_bzg_labor_proven": False,
        "cap_bzg_labor_ready": False,
        "cap_bzg_labor_maturity": flags["cap_bzg_labor_maturity"],
        "cap_bzg_labor_ceiling": flags["cap_bzg_labor_ceiling"],
        "labor_slots": slots,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "hr_deferred_stamp": hr,
        "bzg_ops_desk1": ops,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_payroll",
            "labor_cost_amounts",
            "wage_cost",
            "headcount",
            "hours_worked",
            "payroll_write",
            "CAP-BZG labor PROVEN",
            "HR commissioned",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "GGV-PIPELINE-TRUTH-1",
        "summary": (
            "BZG labor cost honesty shell. UNKNOWN when no facts. "
            "No fake payroll. HR deferred preserved. "
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
        "labor_slots": [s[0] for s in _LABOR_SLOT_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "DEFERRED", "REFUSED", "PRESERVED"],
        "labor_value_property": False,
        "payroll_property": False,
        "writes_accepted": False,
        "fake_payroll": False,
        "unknown_when_facts_missing": True,
        "hr_deferred": True,
        "preserves": list(PRESERVED_PACKS),
        "why": (
            "BZG labor cost honesty shell. UNKNOWN when no facts. "
            "No fake payroll. HR deferred preserved."
        ),
    }
