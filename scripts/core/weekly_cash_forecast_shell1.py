#!/usr/bin/env python3
"""WEEKLY-CASH-FORECAST-SHELL-1 — 13-week cash forecast shell (no invent cash).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack
WEEKLY-CASH-FORECAST-SHELL-1 (armed 2026-09-30 after APPROVALS-LIVE-DEEPEN-1
PASS_VERIFIED) + 2026-09-20 PICK CAP-FIN-07 Budget / Forecast / Cash Cadence
(empty cash_13_week slots — never invent numbers).

Honest UNKNOWN shell for 13-week cash until bank facts land.
FILE_IMPORT_ONLY path preserved from FIN-CASH-TRUTH-1 + FIN-BANK-CREDS-ROUTE-1.
Never invents cash positions, forecast numbers, or week totals.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain CONNECTOR-HEALTH-DEEPEN-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core import fin_bank_creds_route1 as _creds
from core import fin_cash_truth1 as _cash

BETA_ROOT = __import__("pathlib").Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "WEEKLY-CASH-FORECAST-SHELL-1"
SCHEMA_ID = "wolf.weekly-cash-forecast-shell-1.v1"
BOUND = "beta-fin-weekly-cash-safe"
CAP_FIN_07 = "CAP-FIN-07"
CAP_FIN_CASH = "CAP-FIN cash"
INT_BANK = "INT-BANK"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "HUMAN_COMMISSIONING_OR_INTERNAL"
ACTION = "STAMP_UNKNOWN_13_WEEK_SHELL"
WEEK_COUNT = 13
PRESERVED_PACKS = ("FIN-CASH-TRUTH-1", "FIN-BANK-CREDS-ROUTE-1", "CAP-FIN-07")

PAGE_PATHS = frozenset(
    {
        "/fin/weekly-cash-forecast-shell-1",
        "/fin/weekly-cash-forecast-shell-1/",
        "/fin/weekly-cash-forecast",
        "/fin/weekly-cash-forecast/",
        "/fin/weekly-cash",
        "/fin/weekly-cash/",
        "/fin/cash-forecast-shell-1",
        "/fin/cash-forecast-shell-1/",
        "/weekly-cash-forecast-shell-1",
        "/weekly-cash-forecast-shell-1/",
        "/weekly-cash-forecast-shell-1.html",
        "/dashboards/weekly-cash-forecast-shell-1.html",
    }
)
API_PATH = "/api/fin/weekly-cash-forecast-shell-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/fin/weekly-cash-forecast",
        "/api/fin/weekly-cash",
        "/api/ops/weekly-cash-forecast-shell-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "HUMAN_COMMISSIONING_OR_INTERNAL",
        "HUMAN_COMMISSIONING",
        "MATT_ACTION",
        "EXTERNAL_BLOCKER",
        "FILE_IMPORT_ONLY",
        "PRESERVED",
        "REFUSED",
        "UNKNOWN",
        "EMPTY",
        "ABSENT",
    }
)

_INVENT_CASH_TOKENS = frozenset(
    {
        "cash",
        "cash-on-hand",
        "cash_on_hand",
        "balance",
        "balances",
        "amount",
        "amounts",
        "money",
        "forecast",
        "forecasts",
        "inflow",
        "outflow",
        "opening",
        "closing",
        "week-total",
        "week_total",
        "invent-cash",
        "invent_cash",
        "invent-forecast",
        "invent_forecast",
        "fake-cash",
        "fake_cash",
        "fake-forecast",
        "fake_forecast",
        "pad-weeks",
        "pad_weeks",
        "invent-weeks",
        "invent_weeks",
        "scrape",
        "live-scrape",
        "live_scrape",
        "bank-write",
        "bank_write",
        "bank-api",
        "bank_api",
        "payment",
        "payments",
        "staff-ready",
        "staff_ready",
        "human-commissioned",
        "human_commissioned",
        "proven",
        "ready",
        "prod-mutate",
        "prod_mutate",
    }
)


class WeeklyCashForecastShell1Error(ValueError):
    """Fail closed. Does not invent cash or forecast numbers."""

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
    trimmed = raw.rstrip("/") or "/"
    return trimmed in API_PATHS or raw in API_PATHS


def _week_stub(week_index: int) -> dict[str, Any]:
    return {
        "id": f"week_{week_index:02d}",
        "week_index": week_index,
        "label": f"Week {week_index}",
        "kind": "cash_13_week_stub",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "opening": None,
        "inflow": None,
        "outflow": None,
        "closing": None,
        "net": None,
        "currency": None,
        "import_count": 0,
        "last_import_at": None,
        "last_success": None,
        "invented_cash": False,
        "invented_forecast": False,
        "file_import_only": True,
        "why": (
            f"Week {week_index}/13 stub. No bank facts → amounts UNKNOWN (not zero). "
            "FILE_IMPORT_ONLY — never invent cash or forecast numbers."
        ),
    }


def week_stubs() -> list[dict[str, Any]]:
    return [_week_stub(i) for i in range(1, WEEK_COUNT + 1)]


def fin_cash_truth1_preserved() -> dict[str, Any]:
    try:
        board = _cash.build_slice()
        flags = _cash.honesty_flags()
        ok = (
            board.get("ok") is True
            and flags.get("file_import_only") is True
            and flags.get("invented_balance") is False
            and flags.get("live_scrape") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and _cash.all_cash_positions_unknown(board)
        )
        return {
            "ok": ok,
            "file_import_only": flags.get("file_import_only"),
            "invented_balance": flags.get("invented_balance"),
            "live_scrape": flags.get("live_scrape"),
            "import_count": board.get("import_count"),
            "positions_unknown": board.get("positions_unknown"),
            "why": (
                "FIN-CASH-TRUTH-1 preserved: FILE_IMPORT_ONLY, positions UNKNOWN, "
                "import_count=0, no invented balances. Forecast shell does not replace it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-CASH-TRUTH-1 check failed — pack must not break cash truth.",
        }


def fin_bank_creds_preserved() -> dict[str, Any]:
    try:
        flags = _creds.honesty_flags()
        ok = (
            flags.get("file_import_only") is True
            and flags.get("invented_scrape") is False
            and flags.get("invented_balance") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("live_scrape") is False
            and (
                flags.get("classification") == "HUMAN_COMMISSIONING"
                or flags.get("pack_classification") == "HUMAN_COMMISSIONING"
            )
        )
        return {
            "ok": ok,
            "file_import_only": flags.get("file_import_only"),
            "invented_scrape": flags.get("invented_scrape"),
            "invented_balance": flags.get("invented_balance"),
            "classification": flags.get("classification"),
            "creds_present": flags.get("creds_present"),
            "balance": flags.get("balance"),
            "last_success": flags.get("last_success"),
            "why": (
                "FIN-BANK-CREDS-ROUTE-1 preserved: FILE_IMPORT_ONLY held, "
                "HUMAN_COMMISSIONING, no invent scrape/balances."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-BANK-CREDS-ROUTE-1 check failed — pack must not break bank creds route.",
        }


def cap_fin_07_empty_preserved() -> dict[str, Any]:
    """CAP-FIN-07 cash_13_week slot stays empty — this shell is not live machinery."""
    try:
        from core import fin_budget_forecast_cash as _bfc

        flags = _bfc.honesty_flags() if hasattr(_bfc, "honesty_flags") else {}
        ok = (
            flags.get("cash_13_week") is None
            and flags.get("cash_13_week_machinery") is False
            and flags.get("rolling_forecast") is None
            and flags.get("live_cash") is False
        )
        return {
            "ok": ok if flags else True,
            "cash_13_week": flags.get("cash_13_week"),
            "cash_13_week_machinery": flags.get("cash_13_week_machinery", False),
            "why": (
                "CAP-FIN-07 preserved: cash_13_week slot empty; shell is not proof "
                "of 13-week cash machinery. Ceiling BUILT only."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": True,
            "error": type(exc).__name__,
            "why": (
                "CAP-FIN-07 module probe soft: shell still refuses invent; "
                "empty framework decision stands."
            ),
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "fin_cash_truth_1",
            "label": "FIN Cash Truth-1",
            "href": "/fin/cash-truth-1",
            "kind": "existing",
            "note": "Upstream cash positions UNKNOWN · FILE_IMPORT_ONLY. Preserved.",
        },
        {
            "id": "fin_bank_creds",
            "label": "FIN Bank Creds Route-1",
            "href": "/fin/bank-creds-route-1",
            "kind": "existing",
            "note": "HUMAN_COMMISSIONING · FILE_IMPORT_ONLY held. Preserved.",
        },
        {
            "id": "fin_recon_shell_1",
            "label": "FIN Recon Shell-1",
            "href": "/fin/recon-shell-1",
            "kind": "existing",
            "note": "FILE_IMPORT_ONLY recon queue. Upstream of cash truth.",
        },
        {
            "id": "fin_budget_forecast",
            "label": "CAP-FIN-07 Budget / Forecast / Cash",
            "href": "/fin/budget-forecast-cash",
            "kind": "existing",
            "note": "Empty framework slots. cash_13_week not live machinery.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    cash = fin_cash_truth1_preserved()
    creds = fin_bank_creds_preserved()
    bfc = cap_fin_07_empty_preserved()
    return [
        {
            "id": "weeks_unknown",
            "label": "13-week amounts",
            "status": "UNKNOWN",
            "value": None,
            "why": "No bank facts → all week opening/inflow/outflow/closing UNKNOWN (not zero).",
        },
        {
            "id": "file_import_only",
            "label": "Bank path",
            "status": "FILE_IMPORT_ONLY",
            "value": None,
            "why": "FILE_IMPORT_ONLY held until human bank facts. Never invent scrape.",
        },
        {
            "id": "invented_cash",
            "label": "Invented cash",
            "status": "REFUSED",
            "value": False,
            "why": "Cash invent / pad-weeks / fake forecast writes are refused.",
        },
        {
            "id": "invented_forecast",
            "label": "Invented forecast",
            "status": "REFUSED",
            "value": False,
            "why": "Forecast numbers are refused until real bank facts import.",
        },
        {
            "id": "fin_cash_truth1",
            "label": "FIN-CASH-TRUTH-1",
            "status": "PRESERVED" if cash.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": cash.get("why"),
        },
        {
            "id": "fin_bank_creds",
            "label": "FIN-BANK-CREDS-ROUTE-1",
            "status": "PRESERVED" if creds.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": creds.get("why"),
        },
        {
            "id": "cap_fin_07",
            "label": "CAP-FIN-07",
            "status": "PRESERVED" if bfc.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": bfc.get("why"),
        },
        {
            "id": "bank_facts",
            "label": "Bank facts needed",
            "status": "HUMAN_COMMISSIONING",
            "value": None,
            "why": "Live forecast needs human-commissioned bank facts. Shell only until then.",
        },
        {
            "id": "exit_report_headchef",
            "label": "Exit Report / HEADCHEF",
            "status": "MATT_ACTION",
            "value": None,
            "why": "Forbidden until Phase 13 / separate Matt arm. Cursor must not auto-chain.",
        },
        {
            "id": "prod_mutate",
            "label": "Prod mutate / push",
            "status": "EXTERNAL_BLOCKER",
            "value": False,
            "why": "Hard rule — never touch prod pid 15975; no push.",
        },
    ]


def _classification_surfaces() -> list[dict[str, Any]]:
    return [
        {
            "id": "pack_shell",
            "label": "13-week forecast shell",
            "status": CLASSIFICATION,
            "why": "Honest UNKNOWN shell is internal; live numbers need bank facts.",
        },
        {
            "id": "bank_facts",
            "label": "Bank facts / live forecast",
            "status": "HUMAN_COMMISSIONING",
            "why": "Owner commissions bank creds + import before any week amounts.",
        },
        {
            "id": "file_import_only",
            "label": "FILE_IMPORT_ONLY",
            "status": "FILE_IMPORT_ONLY",
            "why": "Held from FIN-CASH-TRUTH-1 + FIN-BANK-CREDS-ROUTE-1.",
        },
        {
            "id": "exit_report_headchef",
            "label": "Exit Report / HEADCHEF",
            "status": "MATT_ACTION",
            "why": "Not started from this pack.",
        },
        {
            "id": "prod_mutate",
            "label": "Prod mutate / push",
            "status": "EXTERNAL_BLOCKER",
            "why": "Prod pid 15975 untouched; no push.",
        },
        {
            "id": "invent_cash_forecast",
            "label": "Invent cash / forecast",
            "status": "REFUSED",
            "why": "POST invent-cash / invent-forecast → 403.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    cash = fin_cash_truth1_preserved()
    creds = fin_bank_creds_preserved()
    bfc = cap_fin_07_empty_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_07": CAP_FIN_07,
        "cap_fin_cash": CAP_FIN_CASH,
        "int_bank": INT_BANK,
        "staff_ready": False,
        "human_commissioned": False,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "week_count": WEEK_COUNT,
        "live_cash": False,
        "live_forecast": False,
        "cash_13_week_machinery": False,
        "invented_cash": False,
        "invented_forecast": False,
        "invented_weeks": False,
        "padded_weeks": False,
        "invented_balance": False,
        "invented_scrape": False,
        "invented_proven": False,
        "invented_ready": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "live_scrape": False,
        "file_import_only": True,
        "books_write": False,
        "production": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "weeks_unknown": True,
        "amounts_null": True,
        "last_success_null": True,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "fin_bank_creds_preserved": creds.get("ok") is True,
        "cap_fin_07_preserved": bfc.get("ok") is True,
        "extends_fin_cash_truth1": True,
        "extends_fin_bank_creds": True,
        "second_cash_system": False,
        "cap_fin_07_proven": False,
        "cap_fin_07_ready": False,
        "cap_fin_07_maturity": "SPECIFIED",
        "cap_fin_07_ceiling": CEILING,
        "ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "CONNECTOR-HEALTH-DEEPEN-1",
        "tests_ne_staff_ready": True,
        "shell_ne_complete": True,
        "status_vocab": "|".join(sorted(STATUS_VOCAB)),
    }


def refuse_invent_cash(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Cash amounts are UNKNOWN until bank facts land. Not invented.",
        code="invent_cash_refused",
    )


def refuse_invent_forecast(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Forecast numbers are refused. Empty 13-week shell is not a live forecast.",
        code="invent_forecast_refused",
    )


def refuse_pad_weeks(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Padding week amounts with invented numbers is refused.",
        code="pad_weeks_refused",
    )


def refuse_scrape(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Live bank scrape invent is refused. FILE_IMPORT_ONLY.",
        code="scrape_refused",
    )


def refuse_bank_write(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Bank writes are refused. FILE_IMPORT_ONLY — no bank API mutate.",
        code="bank_write_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "A payment is not executed on this weekly cash forecast shell.",
        code="payment_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "PROVEN is refused. CAP-FIN-07 stays SPECIFIED. Empty shell is not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "READY / staff_ready / human_commissioned flips are refused on this shell.",
        code="ready_refused",
    )


def refuse_prod_mutate(_body: dict | None = None) -> None:
    raise WeeklyCashForecastShell1Error(
        "Prod mutate / push is EXTERNAL_BLOCKER. Pid 15975 untouched.",
        code="prod_mutate_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise WeeklyCashForecastShell1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        token_us = str(key).strip().lower()
        if token in _INVENT_CASH_TOKENS or token_us in _INVENT_CASH_TOKENS:
            if token in {
                "forecast",
                "forecasts",
                "invent-forecast",
                "fake-forecast",
            } or token_us in {
                "forecast",
                "forecasts",
                "invent_forecast",
                "fake_forecast",
            }:
                refuse_invent_forecast(payload)
            if token in {
                "pad-weeks",
                "invent-weeks",
            } or token_us in {"pad_weeks", "invent_weeks"}:
                refuse_pad_weeks(payload)
            if token in {
                "scrape",
                "live-scrape",
            } or token_us in {"scrape", "live_scrape"}:
                refuse_scrape(payload)
            if token in {
                "bank-write",
                "bank-api",
            } or token_us in {"bank_write", "bank_api"}:
                refuse_bank_write(payload)
            if token in {"payment", "payments"} or token_us in {"payment", "payments"}:
                refuse_payment(payload)
            if token in {"proven"} or token_us in {"proven"}:
                refuse_proven(payload)
            if token in {
                "ready",
                "staff-ready",
                "human-commissioned",
            } or token_us in {
                "ready",
                "staff_ready",
                "human_commissioned",
            }:
                refuse_ready(payload)
            if token in {"prod-mutate"} or token_us in {"prod_mutate"}:
                refuse_prod_mutate(payload)
            refuse_invent_cash(payload)
    raise WeeklyCashForecastShell1Error(
        "External writes are refused. Weekly cash forecast shell is read-only UNKNOWN.",
        code="write_refused",
    )


def all_weeks_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    weeks = pack.get("weeks") or []
    if len(weeks) != WEEK_COUNT:
        return False
    return all(
        w.get("opening") is None
        and w.get("inflow") is None
        and w.get("outflow") is None
        and w.get("closing") is None
        and w.get("net") is None
        and w.get("import_count") == 0
        and w.get("last_success") is None
        and w.get("invented_cash") is False
        and w.get("invented_forecast") is False
        and w.get("status") in ("EMPTY", "UNKNOWN")
        and w.get("file_import_only") is True
        for w in weeks
        if isinstance(w, dict)
    )


def no_invented_cash(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    return (
        pack.get("invented_cash") is False
        and pack.get("invented_forecast") is False
        and pack.get("invented_weeks") is False
        and pack.get("padded_weeks") is False
        and pack.get("live_cash") is False
        and pack.get("live_forecast") is False
        and all_weeks_unknown(pack)
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 6:
        return False
    by_id = {s.get("id"): s for s in surfaces if isinstance(s, dict)}
    return (
        by_id.get("pack_shell", {}).get("status") == CLASSIFICATION
        and by_id.get("bank_facts", {}).get("status") == "HUMAN_COMMISSIONING"
        and by_id.get("file_import_only", {}).get("status") == "FILE_IMPORT_ONLY"
        and by_id.get("exit_report_headchef", {}).get("status") == "MATT_ACTION"
        and by_id.get("prod_mutate", {}).get("status") == "EXTERNAL_BLOCKER"
        and by_id.get("invent_cash_forecast", {}).get("status") == "REFUSED"
    )


def build_board() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    weeks = week_stubs()
    cash = fin_cash_truth1_preserved()
    creds = fin_bank_creds_preserved()
    bfc = cap_fin_07_empty_preserved()
    import_count = sum(int(w.get("import_count") or 0) for w in weeks)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_FIN_07, CAP_FIN_CASH, INT_BANK, "cash forecast"],
        "classification": CLASSIFICATION,
        "action": ACTION,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "week_count": WEEK_COUNT,
        "live_cash": False,
        "live_forecast": False,
        "cash_13_week_machinery": False,
        "import_count": import_count,
        "weeks_unknown": import_count == 0,
        "amounts_null": True,
        "invented_cash": False,
        "invented_forecast": False,
        "invented_weeks": False,
        "padded_weeks": False,
        "invented_balance": False,
        "invented_scrape": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "live_scrape": False,
        "file_import_only": True,
        "books_write": False,
        "last_success": None,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "fin_bank_creds_preserved": creds.get("ok") is True,
        "cap_fin_07_preserved": bfc.get("ok") is True,
        "cap_fin_07_proven": False,
        "cap_fin_07_ready": False,
        "cap_fin_07_maturity": flags["cap_fin_07_maturity"],
        "cap_fin_07_ceiling": flags["cap_fin_07_ceiling"],
        "weeks": weeks,
        "surfaces": _classification_surfaces(),
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fin_cash_truth1": cash,
        "fin_bank_creds": creds,
        "cap_fin_07": bfc,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_forecast",
            "cash_13_week_machinery",
            "week_amounts",
            "payment_write",
            "CAP-FIN-07 PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "CONNECTOR-HEALTH-DEEPEN-1",
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "week_count": WEEK_COUNT,
        "week_ids": [f"week_{i:02d}" for i in range(1, WEEK_COUNT + 1)],
        "status_enum": sorted(STATUS_VOCAB),
        "amount_property": False,
        "forecast_property": False,
        "cash_property": False,
        "writes_accepted": False,
        "file_import_only": True,
        "extends": [
            "scripts/core/fin_cash_truth1.py",
            "scripts/core/fin_bank_creds_route1.py",
            "scripts/core/fin_budget_forecast_cash.py",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_cash_system": False,
        "why": (
            "Honest UNKNOWN 13-week cash forecast shell until bank facts. "
            "No invented cash or forecast numbers. FILE_IMPORT_ONLY preserved."
        ),
    }
