#!/usr/bin/env python3
"""CAP-GGV-01 strategy / plan / asset / workflow / learn skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-GGV-STRATEGY-MACHINE-V1-2026-09-20.md.
Owner order KEEP BUILDING WITHOUT MATT. Lane ggv-strategy-machine-v1 on
mission owner-autonomous-20260920-w8 after intg-connector-cap-tests-v1 DONE
(b6b7b2e / 6c60a3a). CR-8c1fa12404180c02 stays OPEN.
intel-learning-policy-v1 stays parked. Bound beta-ggv-ops-safe.

Names the strategy, plan, asset, workflow, and learn slots and leaves every
slot empty. An empty framework is not a live strategy machine and not proof
of governed learning. This module does not invent a strategy score, revenue,
or a learn outcome. It does not write Production, Alchemist, Metricool,
Zayen books, a bank, a payment, Cloudflare, Access, the Model C ledger, or
the completion row. CAP-GGV-01 stays BUILT. The ceiling label is BUILT.
PROVEN and READY are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "ggv_strategy_machine.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-8c1fa12404180c02"
CAP_ID = "CAP-GGV-01"
SCHEMA_ID = "wolf.cap-ggv-01.strategy-machine.v1"
BOUND = "beta-ggv-ops-safe"

KIND_IDS = ("strategy", "plan", "asset", "workflow", "learn")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "strategy",
        "label": "Strategy",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named strategy slot. Empty is not a live strategy machine and not proof of governed learning.",
    },
    {
        "kind": "plan",
        "label": "Plan",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named plan slot. Empty is not a live strategy machine and not a current plan.",
    },
    {
        "kind": "asset",
        "label": "Asset",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named asset slot. Empty is not a content asset and not a Metricool write.",
    },
    {
        "kind": "workflow",
        "label": "Workflow",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named workflow slot. Empty is not a live workflow and not a money move.",
    },
    {
        "kind": "learn",
        "label": "Learn",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named learn slot. Empty is not proof of governed learning and not a learn outcome.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live strategy machine.",
    "An empty framework is not proof of governed learning.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "Strategy scores, revenue, and learn outcomes are not invented.",
    "No Metricool write.",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-GGV-01 stays BUILT.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "ggv_strategy_machine_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_machine": False,
    "empty_is_learning": False,
    "empty_is_ready": False,
    "proved": False,
    "live_strategy_machine": False,
    "governed_learning": False,
    "current": False,
    "strategy_score": None,
    "revenue": None,
    "learn_outcome": None,
    "metricool_write": False,
    "metricool_called": False,
    "payment": None,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "books_write": False,
    "zayen_write": False,
    "alchemist_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "wolf_system_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class StrategyMachineError(ValueError):
    """Fail closed. Does not invent a strategy machine, a learn outcome, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "alchemist" in low:
        raise StrategyMachineError(
            "strategy framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise StrategyMachineError(
            "strategy framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise StrategyMachineError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "metricool" in name or "metricool" in low:
        raise StrategyMachineError(
            "A Metricool write is refused. This framework does not post content.",
            code="metricool_refused",
        )
    if "bank" in name:
        raise StrategyMachineError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise StrategyMachineError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise StrategyMachineError(
            "strategy framework refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise StrategyMachineError(
            "strategy framework refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _row_state(data: Any) -> str:
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-GGV-01. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    return _row_state(data)


def ceiling_for(_state: str) -> str:
    """BUILT label only. At most BUILT. Does not write the ledger."""
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-8c1fa12404180c02. Does not upsert, resolve, or harvest."""
    out: dict[str, Any] = {
        "cr_id": CR_ID,
        "cr_bound": True,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_ID,
        "cr_title": None,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    _assert_beta_path(path.resolve())
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_ID
    out["cr_title"] = row[3]
    out["cr_next_action"] = row[4]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling_for(state)
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_machine"] = False
    flags["empty_is_learning"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_strategy_machine"] = False
    flags["governed_learning"] = False
    flags["current"] = False
    flags["strategy_score"] = None
    flags["revenue"] = None
    flags["learn_outcome"] = None
    flags["metricool_write"] = False
    flags["metricool_called"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["payment_executed"] = False
    flags["bank_write"] = False
    flags["books_write"] = False
    flags["zayen_write"] = False
    flags["alchemist_write"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["on_disk"] = False
    flags["bound"] = BOUND
    flags["ledger_write"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["kind", "subject", "status", "evidence_note"],
        "properties": {
            "kind": {"type": "string", "enum": list(KIND_IDS)},
            "subject": {"type": "string"},
            "status": {"type": "string", "enum": ["NOTED"]},
            "evidence_note": {
                "type": "string",
                "description": "Not accepted. A note would not be a live strategy machine.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "metricool_property": False,
        "strategy_score_property": False,
        "revenue_property": False,
        "learn_outcome_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live strategy machine."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_machine": False,
        "empty_is_learning": False,
        "empty_is_ready": False,
        "proved": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "current": False,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "metricool_write": False,
        "metricool_called": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
    }


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                **_quiet_read(),
                "honesty": honesty_flags(),
            }
    raise StrategyMachineError("Unknown strategy slot.", code="not_found")


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a framework file."""
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "recorded_count": 0,
        "money": None,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "score_changed": False,
        "on_disk": False,
        "kinds": kind_slots(),
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        **_quiet_read(),
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_metricool(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A Metricool write is refused. This framework does not post content.",
        code="metricool_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Strategy scores, revenue, and learn outcomes are not invented. Empty is not a live strategy machine.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays BUILT.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Resolving the completion row is refused. CR-8c1fa12404180c02 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "The framework stays empty. A filled slot would not be a live strategy machine.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "An Alchemist write is refused.",
        code="alchemist_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "transfer", "payout", "withdraw"}:
                refuse_bank(payload)
            if token in {"zayen", "books", "journal"}:
                refuse_books(payload)
            if token in {"metricool", "metricool-write"}:
                refuse_metricool(payload)
            if token in {
                "strategy-score",
                "revenue",
                "learn-outcome",
                "outcome",
                "current",
            }:
                refuse_current(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf-access", "zero-trust"}:
                refuse_access(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr-resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production-mutate"}:
                refuse_production(payload)
            if token in {"score", "credits", "green"}:
                refuse_score(payload)
            if token in {"alchemist"}:
                refuse_alchemist(payload)
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "strategy",
                "plan",
                "asset",
                "workflow",
                "learn",
            }:
                refuse_fill(payload)
    raise StrategyMachineError(
        "This framework does not store a strategy, a plan, a payment, or a learn outcome.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise StrategyMachineError(
            "strategy framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise StrategyMachineError(
            "strategy framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_GGV_STRATEGY") or "").strip() != "1":
            raise StrategyMachineError(
                "test mode refuses the live strategy framework path",
                code="live_guard",
            )
    raise StrategyMachineError(
        "The framework stays empty. Empty is not a live strategy machine.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_ready(*_args: Any, **_kwargs: Any) -> None:
    refuse_ready({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def write_metricool(*_args: Any, **_kwargs: Any) -> None:
    refuse_metricool({})


def move_money(*_args: Any, **_kwargs: Any) -> None:
    refuse_payment({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    zayen: str | None = None,
    books: str | None = None,
    metricool: str | None = None,
    strategy_score: str | None = None,
    revenue: str | None = None,
    learn_outcome: str | None = None,
    current: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    score: str | None = None,
    alchemist: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(bank):
        refuse_bank({})
    if _present(zayen) or _present(books):
        refuse_books({})
    if _present(metricool):
        refuse_metricool({})
    if (
        _present(strategy_score)
        or _present(revenue)
        or _present(learn_outcome)
        or _present(current)
    ):
        refuse_current({})
    if _present(cloudflare):
        refuse_cloudflare({})
    if _present(access):
        refuse_access({})
    if _present(proven) or _present(prove):
        refuse_proven({})
    if _present(ready):
        refuse_ready({})
    if _present(resolve):
        refuse_resolve({})
    if _present(production):
        refuse_production({})
    if _present(score):
        refuse_score({})
    if _present(alchemist):
        refuse_alchemist({})
    if _present(fill):
        refuse_fill({})
    if _present(write):
        refuse_external_write({})
