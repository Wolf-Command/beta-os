#!/usr/bin/env python3
"""Owner Empire / Command pack v1 — Beta :8788 only.

Decision served: 2026-09-21 compressed sprint Track E
(docs/deliveries/GROK-PLAN-SPRINT-TRACK-E-OWNER-EMPIRE-PACK-2026-09-21.md),
under the 2026-09-19 owner release keep_building_without_matt.

One Owner desk. It reads the Progress ledger projection, the CAP-STRAT-02
Radar prove, and the CAP-STRAT-01 12WY prove. It does not keep a second
score, invent a SYSTEM% or a 12WY%, or raise those caps. Pack handoffs are
read-only cards. Track D stays parked.

Bound beta-owner-safe. Owner only. No money, bank, payment, Zayen, HR,
payroll, tax, or trading.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import progress_read_model as _progress
from core import strat_12wy_prove as _wy
from core import strat_radar_prove as _radar

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

BOUND = "beta-owner-safe"
SCHEMA_ID = "wolf.owner-empire-pack.v1"
OWNER = "PERS-MATT"
SLICE = "owner_empire_pack_v1"

HIDDEN = (
    "finance",
    "zayen",
    "hr",
    "trading",
    "bank",
    "payment",
    "payroll",
    "tax",
)

MONEY_KEYS = frozenset(
    {
        "money",
        "amount",
        "payment",
        "bank",
        "folio",
        "zayen",
        "payroll",
        "tax",
        "trading",
        "finance",
        "expected_value",
        "currency",
        "settlement",
        "transfer",
    }
)

INVENT_KEYS = frozenset(
    {
        "system_pct",
        "percent",
        "execution_pct",
        "proven",
        "ready",
        "resolve",
        "production",
        "cloudflare",
    }
)


class EmpirePackError(ValueError):
    """Fail closed. Does not invent a percent, a maturity, or a money move."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_payment(_body: dict | None = None) -> None:
    raise EmpirePackError("Owner Empire does not move money.", code="payment_refused")


def refuse_bank(_body: dict | None = None) -> None:
    raise EmpirePackError("Owner Empire does not touch a bank.", code="bank_refused")


def refuse_finance(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Finance, Zayen, payroll, and tax stay off this desk.",
        code="finance_refused",
    )


def refuse_hr(_body: dict | None = None) -> None:
    raise EmpirePackError("HR stays off this desk.", code="hr_refused")


def refuse_trading(_body: dict | None = None) -> None:
    raise EmpirePackError("Trading stays off this desk.", code="trading_refused")


def refuse_percent(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Owner Empire refuses an invented SYSTEM% or 12WY%.",
        code="percent_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Owner Empire does not mark PROVEN.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Owner Empire does not mark READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Owner Empire does not resolve a completion row.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise EmpirePackError(
        "Owner Empire refuses a production write.",
        code="production_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    keys = {str(key).strip().lower() for key in payload.keys()}
    if keys & MONEY_KEYS or payload.get("pay") or payload.get("settle"):
        if keys & {"bank", "transfer"}:
            refuse_bank(payload)
        if keys & {"hr"}:
            refuse_hr(payload)
        if keys & {"trading"}:
            refuse_trading(payload)
        if keys & {"zayen", "payroll", "tax", "finance", "folio"}:
            refuse_finance(payload)
        refuse_payment(payload)
    if keys & {"system_pct", "percent", "execution_pct"} or payload.get("invent_percent"):
        refuse_percent(payload)
    if payload.get("proven") or "proven" in keys:
        refuse_proven(payload)
    if payload.get("ready") or "ready" in keys:
        refuse_ready(payload)
    if payload.get("resolve") or payload.get("cr_resolve"):
        refuse_resolve(payload)
    if payload.get("production") or payload.get("cloudflare"):
        refuse_production(payload)
    raise EmpirePackError(
        "Owner Empire is a read desk. Writes are refused.",
        code="writes_refused",
    )


def seat_for(person_id: str | None) -> dict[str, Any] | None:
    if (person_id or "").strip() != OWNER:
        return None
    return {
        "person_id": OWNER,
        "seat": "owner",
        "can_read": True,
        "money": False,
        "finance": False,
        "hr": False,
        "trading": False,
    }


def require_owner(person_id: str | None) -> dict[str, Any]:
    seat = seat_for(person_id)
    if seat is None:
        raise EmpirePackError(
            "Owner Empire is Owner (PERS-MATT) only.",
            code="forbidden",
        )
    return seat


def _ledger_state(cap_id: str, ledger_path: Path | str | None = None) -> str:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(cap_id) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return str(row[0]).strip().upper() or "UNKNOWN"


def honesty_flags(ledger_path: Path | str | None = None) -> dict[str, Any]:
    strat_01 = _ledger_state("CAP-STRAT-01", ledger_path)
    strat_02 = _ledger_state("CAP-STRAT-02", ledger_path)
    return {
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "owner_only": True,
        "person_gate": OWNER,
        "system_is_ledger_projection": True,
        "second_scoring_table": False,
        "invented_system_pct": False,
        "invented_12wy_percent": False,
        "invented_proven": False,
        "invented_ready": False,
        "progress_used_as_radar_cap": False,
        "caps_raised": False,
        "cap_strat_01": strat_01,
        "cap_strat_02": strat_02,
        "proven": strat_01 == "PROVEN" or strat_02 == "PROVEN",
        "ready": strat_01 == "READY" or strat_02 == "READY",
        "cr_mutated": False,
        "ledger_write": False,
        "model_c_write": False,
        "model_c_maturity_raised": False,
        "money": None,
        "payment_executed": False,
        "bank_write": False,
        "zayen_write": False,
        "finance_controls": False,
        "hr_broadened": False,
        "trading": False,
        "payroll": False,
        "tax": False,
        "production_write": False,
        "production": False,
        "cloudflare_mutated": False,
        "track_d_built": False,
        "anon_fail_closed": True,
        "hidden": list(HIDDEN),
    }


def today_strip(ledger_path: Path | str | None = None) -> dict[str, Any]:
    """SYSTEM% from the Progress ledger helper. Stale or unreadable is loud UNWIRED."""
    href = "/progress.html"
    formula = _progress.SYSTEM_FORMULA
    try:
        system = _progress.compute_system_from_ledger(
            Path(ledger_path) if ledger_path else None
        )
    except Exception as exc:  # noqa: BLE001 — loud empty, never a frozen percent
        return {
            "ok": False,
            "status": "UNWIRED",
            "loud": True,
            "system_pct": None,
            "invented_system_pct": False,
            "formula": formula,
            "href": href,
            "why": (
                "Progress SYSTEM% was not computed (%s). UNWIRED. "
                "This desk does not freeze a percent."
            )
            % exc,
        }
    status = system.get("status")
    pct = system.get("system_pct")
    if status != "OK" or pct is None:
        return {
            "ok": True,
            "status": "UNWIRED",
            "loud": True,
            "system_pct": None,
            "invented_system_pct": False,
            "ledger_status": status,
            "n": system.get("n"),
            "expected_n": system.get("expected_n"),
            "formula": system.get("formula") or formula,
            "href": href,
            "why": (
                "SYSTEM% is withheld. The ledger projection is %s. "
                "UNWIRED. No frozen percent."
            )
            % (status or "EMPTY"),
        }
    return {
        "ok": True,
        "status": "LEDGER",
        "loud": False,
        "system_pct": pct,
        "invented_system_pct": False,
        "ledger_status": status,
        "n": system.get("n"),
        "expected_n": system.get("expected_n"),
        "counts": system.get("counts"),
        "formula": system.get("formula") or formula,
        "href": href,
        "why": (
            "SYSTEM% is the Progress ledger projection. "
            "This desk does not keep a second score."
        ),
    }


def radar_strip() -> dict[str, Any]:
    """CAP-STRAT-02 summary. Does not copy SYSTEM% and does not raise the cap."""
    prove = _radar.build_prove()
    flags = prove.get("honesty") or {}
    surfaces = prove.get("surfaces") or {}
    pulse = surfaces.get("pulse") or {}
    html = surfaces.get("html") or {}
    pulse_status = pulse.get("status")
    if pulse_status == "NOT_READ" or html.get("present") is not True:
        display = "UNWIRED"
        why = pulse.get("why") or (
            "Radar binding was not read. UNWIRED. Pulse and exception counts are not zero."
        )
    elif pulse_status == "ABSENT":
        display = "EMPTY"
        why = pulse.get("why") or (
            "Pulse and Exceptions are not named. EMPTY. Counts are not zero."
        )
    elif pulse_status == "NAMED":
        display = "NAMED"
        why = pulse.get("why") or "Pulse and Exceptions are named. Counts are not invented."
    else:
        display = "UNWIRED"
        why = "Radar prove returned no known pulse status. UNWIRED. Counts are not zero."
    if display in {"UNWIRED", "EMPTY"} and "zero" not in why.lower():
        why = why.rstrip() + " Counts are not zero."
    return {
        "ok": True,
        "cap": "CAP-STRAT-02",
        "display": display,
        "loud": display in {"UNWIRED", "EMPTY"},
        "maturity": flags.get("maturity"),
        "proven": flags.get("proven"),
        "ready": flags.get("ready"),
        "invented_proven": False,
        "invented_ready": False,
        "system_pct": None,
        "progress_used_as_cap": False,
        "pulse_count": None,
        "exception_count": None,
        "href": "/radar-prove",
        "why": why,
        "cr_id": flags.get("cr_id"),
        "cr_state": flags.get("cr_state"),
        "cr_resolved": flags.get("cr_resolved"),
        "cr_mutated": False,
    }


def wy_strip() -> dict[str, Any]:
    """CAP-STRAT-01 summary. EMPTY is not 0%. A percent only passes through when WIRED."""
    prove = _wy.build_prove()
    score = prove.get("score") or {}
    flags = prove.get("honesty") or {}
    state = score.get("state")
    raw_percent = score.get("percent")
    if state == "WIRED" and isinstance(raw_percent, int) and not isinstance(raw_percent, bool):
        display = "WIRED"
        percent: int | None = raw_percent
        why = str(score.get("why") or "Evidenced week score from the 12WY prove.")
    elif state == "EMPTY":
        display = "EMPTY"
        percent = None
        why = str(
            score.get("why")
            or "No evidenced planned tactics. EMPTY, not 0%."
        )
    else:
        display = "UNWIRED"
        percent = None
        why = str(
            score.get("why")
            or "12WY score was not read. UNWIRED. No percent is invented."
        )
    return {
        "ok": True,
        "cap": "CAP-STRAT-01",
        "display": display,
        "loud": display in {"EMPTY", "UNWIRED"},
        "score_state": state,
        "percent": percent,
        "invented_percent": False,
        "empty_is_not_zero": True,
        "tactics_invented": False,
        "maturity": flags.get("maturity"),
        "proven": flags.get("proven"),
        "ready": flags.get("ready"),
        "invented_proven": False,
        "invented_ready": False,
        "href": "/12wy-prove",
        "why": why,
        "cr_id": flags.get("cr_id"),
        "cr_state": flags.get("cr_state"),
        "cr_resolved": flags.get("cr_resolved"),
        "cr_mutated": False,
    }


def _empty_handoff(pack_id: str, label: str, href: str, api: str, why: str) -> dict[str, Any]:
    return {
        "pack": pack_id,
        "label": label,
        "state": "EMPTY",
        "loud": True,
        "attention_count": None,
        "api_present": False,
        "href": href,
        "api": api,
        "money": None,
        "payment": None,
        "why": why,
    }


def _bzg_handoff() -> dict[str, Any]:
    card = _empty_handoff(
        "BZG",
        "Uma ops",
        "/bzg/uma-blu",
        "/api/bzg/uma-blu/today",
        "Uma Today was not read. Attention is EMPTY. No money is shown.",
    )
    try:
        from core import uma_ops_console as uma
    except Exception:  # noqa: BLE001
        return card
    card["api_present"] = callable(getattr(uma, "today_cards", None))
    path = getattr(uma, "CATALOG_DB", None)
    if not isinstance(path, Path) or not path.is_file():
        card["why"] = (
            "Uma Today exists. The catalog was not read. Attention is EMPTY. No money is shown."
        )
        return card
    uri = path.resolve().as_uri() + "?mode=ro"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_purchase_requests'"
        ).fetchone()
        if present is None:
            card["why"] = (
                "Uma Today exists. The purchase-request table was not on this read. "
                "Attention is EMPTY. Bills, payment, and petty stay off this card."
            )
            return card
        count = conn.execute(
            """
            SELECT COUNT(*) FROM bzg_ops_purchase_requests
            WHERE COALESCE(example, 0) = 0
              AND state IN ('DRAFT', 'REQUESTED', 'ORDERED', 'PARTIALLY_RECEIVED', 'POLICY_REQUIRED')
            """
        ).fetchone()[0]
    except sqlite3.Error:
        card["why"] = (
            "Uma Today exists. This attention read failed. Count stays EMPTY. No money is shown."
        )
        return card
    finally:
        if conn is not None:
            conn.close()
    card["state"] = "READ"
    card["loud"] = False
    card["attention_count"] = int(count)
    card["why"] = (
        "Read-only count of Uma requests still with a person, excluding bills, "
        "payment, and petty. Amounts are not on this card. Open Uma Today for the full list."
    )
    return card


def _ggv_handoff() -> dict[str, Any]:
    card = _empty_handoff(
        "GGV",
        "GGV ops",
        "/ggv-ops-pack",
        "/api/ggv/ops-pack",
        "GGV ops pack was not read. Attention is EMPTY. No lead was invented.",
    )
    try:
        from core import ggv_ops_pack as ggv
    except Exception:  # noqa: BLE001
        return card
    card["api_present"] = callable(getattr(ggv, "build_board", None))
    try:
        board = ggv.build_board(verified_person_id=OWNER)
    except Exception:  # noqa: BLE001
        card["why"] = (
            "GGV ops pack is present. This read failed. Attention is EMPTY. No lead was invented."
        )
        return card
    exceptions = board.get("exceptions") or {}
    count = exceptions.get("count")
    if not isinstance(count, int):
        card["why"] = (
            "GGV ops pack is present. No attention count came back. EMPTY. No lead was invented."
        )
        return card
    card["state"] = "READ"
    card["loud"] = False
    card["attention_count"] = count
    card["money"] = None
    card["why"] = (
        "Habitat leads waiting on a recorded source time, from the GGV ops pack. "
        "An empty list is not an SLA breach. No money is shown."
    )
    return card


def _amg_handoff() -> dict[str, Any]:
    card = _empty_handoff(
        "AMG",
        "Atrium desk",
        "/amg-ops-pack",
        "/api/amg/ops-pack",
        "Atrium desk was not read. Attention is EMPTY. This is not occupancy.",
    )
    try:
        from core import amg_ops_pack as amg
    except Exception:  # noqa: BLE001
        return card
    card["api_present"] = callable(getattr(amg, "build_board", None))
    try:
        board = amg.build_board(verified_person_id=OWNER)
    except Exception:  # noqa: BLE001
        card["why"] = (
            "Atrium desk is present. This read failed. Attention is EMPTY. This is not occupancy."
        )
        return card
    slots = ((board.get("today") or {}).get("slots")) or []
    flagged = [slot for slot in slots if isinstance(slot, dict) and slot.get("attention")]
    card["state"] = "READ"
    card["loud"] = False
    card["attention_count"] = len(flagged)
    card["occupancy"] = None
    card["adr"] = None
    card["revpar"] = None
    card["why"] = (
        "Desk slots marked for a look. An empty slot is not occupancy, ADR, or RevPAR. "
        "No folio or payment is shown."
    )
    return card


def handoffs() -> dict[str, Any]:
    cards = [_bzg_handoff(), _ggv_handoff(), _amg_handoff()]
    return {
        "ok": True,
        "cards": cards,
        "money": None,
        "why": "Read-only pack attention. EMPTY means this desk did not invent a count.",
    }


def intel_strip() -> dict[str, Any]:
    return {
        "ok": True,
        "track": "D",
        "state": "PARKED",
        "loud": True,
        "ops_pack_built": False,
        "href": None,
        "status_only": True,
        "existing_status_href": "/api/intel/orchestrate",
        "why": "Track D is parked. This desk does not build an intel ops pack.",
    }


def _action(action_id: str, label: str, href: str, why: str) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "href": href,
        "kind": "board",
        "why": why,
    }


def next_actions(
    today: dict[str, Any],
    radar: dict[str, Any],
    wy: dict[str, Any],
    packs: dict[str, Any],
) -> dict[str, Any]:
    """Links into boards that already exist. Does not invent pace or money."""
    catalog = [
        _action(
            "progress",
            "Open Progress",
            "/progress.html",
            "The ledger projection lives on the Progress board.",
        ),
        _action(
            "radar",
            "Open Radar prove",
            "/radar-prove",
            "CAP-STRAT-02 honesty lives on the Radar prove.",
        ),
        _action(
            "12wy",
            "Open 12-Week Year prove",
            "/12wy-prove",
            "CAP-STRAT-01 honesty lives on the 12WY prove.",
        ),
        _action(
            "bzg",
            "Open Uma ops",
            "/bzg/uma-blu",
            "Uma Today is the BZG board. Amounts stay on that board, not here.",
        ),
        _action(
            "ggv",
            "Open GGV ops",
            "/ggv-ops-pack",
            "Habitat operator loop is the GGV board.",
        ),
        _action(
            "amg",
            "Open Atrium desk",
            "/amg-ops-pack",
            "The Atrium desk is the AMG board. Empty slots are not hotel numbers.",
        ),
    ]
    by_id = {row["id"]: row for row in catalog}
    if today.get("status") != "LEDGER":
        chosen = by_id["progress"]
    elif radar.get("display") in {"UNWIRED", "EMPTY"}:
        chosen = by_id["radar"]
    elif wy.get("display") in {"UNWIRED", "EMPTY"}:
        chosen = by_id["12wy"]
    else:
        chosen = by_id["progress"]
        for card in packs.get("cards") or []:
            count = card.get("attention_count")
            if isinstance(count, int) and count > 0:
                chosen = by_id[str(card.get("pack") or "").lower()]
                break
    return {
        "ok": True,
        "next": chosen,
        "actions": catalog,
        "pace_invented": False,
        "money": None,
    }


def build_desk(
    *,
    verified_person_id: str,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_owner(verified_person_id)
    today = today_strip(ledger_path)
    radar = radar_strip()
    wy = wy_strip()
    packs = handoffs()
    actions = next_actions(today, radar, wy, packs)
    flags = honesty_flags(ledger_path)
    flags["cr_12wy_id"] = wy.get("cr_id")
    flags["cr_12wy_state"] = wy.get("cr_state")
    flags["cr_12wy_resolved"] = wy.get("cr_resolved")
    flags["cr_radar_id"] = radar.get("cr_id")
    flags["cr_radar_state"] = radar.get("cr_state")
    flags["cr_radar_resolved"] = radar.get("cr_resolved")
    flags["cr_mutated"] = False
    return {
        "ok": True,
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "seat": seat,
        "today": today,
        "radar": radar,
        "twelve_wy": wy,
        "handoffs": packs,
        "actions": actions,
        "intel": intel_strip(),
        "honesty": flags,
        "hidden": list(HIDDEN),
        "money": None,
        "payment_executed": False,
        "finance_controls": False,
        "hr_broadened": False,
        "trading": False,
    }


def schema_document() -> dict[str, Any]:
    return {
        "id": SCHEMA_ID,
        "bound": BOUND,
        "owner": OWNER,
        "writes": False,
        "hidden": list(HIDDEN),
    }
