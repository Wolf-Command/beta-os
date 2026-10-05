#!/usr/bin/env python3
"""Operational exception rollup for Owner Command.

Merges material unresolved exceptions from real Beta state so Owner Command
never says nothing is going wrong while any of these are open.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import data_quality_exceptions as dq
from core import integration_health as health
from core import uma_real_projection as uma

BETA_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = BETA_ROOT / "state" / "ops" / "testability-matrix.json"
WITA = timezone(timedelta(hours=8))


def _item(
    *,
    kind: str,
    title: str,
    detail: str,
    href: str,
    owner_role: str,
    money_risk: bool = False,
    blocked: bool = False,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "detail": detail,
        "href": href,
        "owner_role": owner_role,
        "money_risk": money_risk,
        "blocked": blocked,
        "plain": f"{title}: {detail}",
    }


def _uma_close() -> list[dict[str, Any]]:
    close = uma._close_branch()  # noqa: SLF001 — shared read of the live close gate
    # Owner P0 5 Oct 2026: surface as Action required, not a save-blocker. Null policy → exception path.
    if not close.get("action_required") and not close.get("branch_blocked"):
        return []
    return [
        _item(
            kind="uma_daily_close",
            title="DAILY CLOSE · Action required",
            detail=str(close.get("reason") or "Variance policy needs approval · [REVIEW]"),
            href=str(close.get("href") or "/uma-blu-close"),
            owner_role="Owner",
            blocked=False,
            money_risk=True,
        )
    ]


def _data_quality() -> list[dict[str, Any]]:
    items = []
    for row in dq.open_items():
        items.append(
            _item(
                kind="data_quality",
                title=str(row.get("title") or "Data-quality exception"),
                detail=str(row.get("plain_english") or row.get("do_not_act") or ""),
                href=str(row.get("href") or "/owner/data-quality"),
                owner_role=str(row.get("owner_role") or "Owner"),
                money_risk="cash" in str(row.get("id") or "")
                or "alchemist" in str(row.get("id") or "")
                or "payable" in str(row.get("title") or "").lower(),
            )
        )
    return items


def _stale_authoritative(cards: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        day = uma.operating_day()
    except Exception:  # noqa: BLE001
        # Test guard may refuse prod recipes.sqlite — other exception sources still count.
        day = {}
    sales = day.get("sales") or {}
    latest = sales.get("latest") or {}
    if sales.get("stale"):
        out.append(
            _item(
                kind="stale_data",
                title="Uma Blu ESB sales day is stale",
                detail=str(sales.get("stale_banner") or "The last warehouse day is older than yesterday."),
                href="/bzg/uma-blu",
                owner_role="BZG F&B Operations",
                money_risk=True,
            )
        )
    elif day and not latest.get("biz_date"):
        out.append(
            _item(
                kind="missing_data",
                title="Uma Blu ESB warehouse has no sales day",
                detail="No finished BLZ sales day is in the local warehouse.",
                href="/bzg/uma-blu",
                owner_role="BZG F&B Operations",
                money_risk=True,
            )
        )
    finance = "UNAVAILABLE"
    if cards:
        finance = str((cards[0].get("financial_position") or {}).get("state") or "UNAVAILABLE")
    else:
        try:
            from core import owner_command as oc

            finance = oc._finance_state()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            finance = "UNAVAILABLE"
    if finance in {"UNAVAILABLE", "MISSING", "UNKNOWN"}:
        out.append(
            _item(
                kind="finance_books",
                title=f"Finance books are {finance}",
                detail="Group finance ledgers were not opened. Unavailable is not a zero balance.",
                href="/wolf",
                owner_role="Owner / Finance",
                money_risk=True,
            )
        )
    return out


def _failed_integrations() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        report = health.build_report()
    except Exception as exc:  # noqa: BLE001
        return [
            _item(
                kind="integration",
                title="Integration health could not be read",
                detail=type(exc).__name__,
                href="/owner/integration-health" if False else "/wolf",
                owner_role="Owner",
            )
        ]
    for row in report.get("connectors") or []:
        status = str(row.get("status") or "")
        if status not in {"ERROR", "DEGRADED"}:
            continue
        name = str(row.get("name") or row.get("cap_id") or "Connector")
        out.append(
            _item(
                kind="integration",
                title=f"{name} is {status}",
                detail=str(row.get("evidence") or "Integration health reported a problem."),
                href="/wolf",
                owner_role="Owner",
                money_risk="bank" in name.lower() or "esb" in name.lower(),
            )
        )
    return out


def _month_end_blockers() -> list[dict[str, Any]]:
    """Surface month-end bank-statement gate from the permanent rule."""
    # No commissioned statement register yet → the close is blocked for the prior month.
    today = datetime.now(WITA).date()
    prior = (today.replace(day=1) - timedelta(days=1))
    period = prior.strftime("%Y-%m")
    register = BETA_ROOT / "state" / "finance" / "bank-statement-register.json"
    if register.is_file():
        try:
            payload = json.loads(register.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        missing = [
            row
            for row in payload.get("accounts") or []
            if str(row.get("period") or "") == period
            and str(row.get("status") or "").upper() in {"MISSING", "", "WAITING"}
        ]
        if missing:
            return [
                _item(
                    kind="month_end",
                    title=f"MONTH END BLOCKED — BANK STATEMENT MISSING ({period})",
                    detail="; ".join(
                        f"{row.get('company') or '?'} {row.get('bank') or ''} {row.get('account') or ''}".strip()
                        for row in missing[:6]
                    ),
                    href="/docs/wolf/finance/MONTH-END-CLOSE-RULE.md",
                    owner_role="Finance",
                    money_risk=True,
                    blocked=True,
                )
            ]
        return []
    return [
        _item(
            kind="month_end",
            title=f"MONTH END BLOCKED — BANK STATEMENT MISSING ({period})",
            detail=(
                "No bank-statement register is on Beta yet. Per the month-end close rule, "
                "missing statements block close for GGV, AMG, and BZG."
            ),
            href="/finish-war-room",
            owner_role="Finance",
            money_risk=True,
            blocked=True,
        )
    ]


def _commissioning_fails() -> list[dict[str, Any]]:
    if not MATRIX_PATH.is_file():
        return []
    try:
        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict[str, Any]] = []
    for surface in matrix.get("surfaces") or []:
        if not isinstance(surface, dict):
            continue
        blob = " ".join(
            [
                str(surface.get("last_human_result") or ""),
                " ".join(str(row.get("result") or "") for row in surface.get("human_results") or []),
            ]
        )
        if "FAIL" not in blob.upper():
            continue
        out.append(
            _item(
                kind="commissioning_fail",
                title=f"Human commissioning FAIL — {surface.get('surface')}",
                detail=str(surface.get("last_human_result") or "A FAIL remains on the testability matrix."),
                href=str(surface.get("route") or "/finish-war-room"),
                owner_role=str(surface.get("human_tester") or "Owner"),
                blocked=True,
            )
        )
    return out



def _external_route_exceptions() -> list[dict[str, Any]]:
    """P0 Host Error / sidecar availability — RED only, deduped by probe tick."""
    try:
        from core import external_route_health as erh

        rows = erh.owner_exception_items()
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            _item(
                kind=str(row.get("kind") or "external_route"),
                title=str(row.get("title") or "External finance route failure"),
                detail=str(row.get("detail") or row.get("plain") or ""),
                href=str(row.get("href") or "/ops/reliability"),
                owner_role=str(row.get("owner_role") or "Owner / Ops"),
                money_risk=bool(row.get("money_risk", True)),
                blocked=bool(row.get("blocked", True)),
            )
        )
    return out


def _work_item_exceptions() -> list[dict[str, Any]]:
    """Overdue / blocked / failed commissioning work from the canonical work model."""
    try:
        from core import universal_my_work as umw

        rows = umw.owner_work_exceptions()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows[:12]:
        out.append(
            _item(
                kind="work_item",
                title=str(row.get("title") or "Work item"),
                detail=(
                    f"{row.get('status_label') or row.get('status')}: "
                    f"{row.get('what_happens_next') or row.get('current_owner') or ''}"
                )[:240],
                href=str(row.get("href") or "/my-work"),
                owner_role=str(row.get("company_site_department") or "Owner"),
                blocked=str(row.get("status") or "") in {"BLOCKED", "RETURNED"}
                or row.get("commissioning_result") == "FAIL",
            )
        )
    return out


def collect(*, cards: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build the material unresolved exception list for Owner Command."""
    # Ensure the data-quality register exists before rollup.
    dq.load_register(refresh=False)
    items: list[dict[str, Any]] = []
    items.extend(_uma_close())
    items.extend(_data_quality())
    items.extend(_stale_authoritative(cards))
    items.extend(_failed_integrations())
    items.extend(_month_end_blockers())
    items.extend(_commissioning_fails())
    items.extend(_work_item_exceptions())
    items.extend(_external_route_exceptions())
    return {
        "ok": True,
        "read": "READ",
        "count": len(items),
        "items": items,
        "money_items": [row for row in items if row.get("money_risk")],
        "blocked_items": [row for row in items if row.get("blocked")],
        "empty_message": None if items else "No material operational exceptions are open.",
    }
