#!/usr/bin/env python3
"""CAP-GGV-06 intercompany client-mode skeleton v1 (Beta only).

Decision served: 2026-09-20 PICK — CAP-GGV-06 intercompany client-mode
framework skeleton on Beta only
(docs/deliveries/GROK-PLAN-GGV-INTERCOMPANY-CLIENT-V1-2026-09-20.md).
Owner order KEEP BUILDING WITHOUT MATT. Lane ggv-intercompany-client-v1 on
mission owner-autonomous-20260920-w9 after amg-revenue-yield-v1 DONE
(ce6fe39 / 1fd4931). CR-6a19c9221cab0178 stays OPEN.
Bound beta-ggv-ops-safe.

Names the service_record, invoice, allocation, arms_length, ar_ap, and
notes slots and leaves every slot empty. An empty framework is not live
intercompany billing and not proof of GGV, AMG, and BZG client machinery.
This module does not invent invoices, allocations, AR/AP balances, or a
tax treatment. It does not write Production, Alchemist, Zayen books, a
bank, a payment, Cloudflare, Access, the Model C ledger, or the completion
row. CAP-GGV-06 stays SPECIFIED. The ceiling label is BUILT. PROVEN and
READY are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "ggv_intercompany_client.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-6a19c9221cab0178"
CAP_ID = "CAP-GGV-06"
SCHEMA_ID = "wolf.cap-ggv-06.intercompany-client.v1"
BOUND = "beta-ggv-ops-safe"

_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "service_record",
        "Service record",
        "Named service record slot. Empty is not a service record and not live intercompany billing.",
    ),
    (
        "invoice",
        "Invoice",
        "Named invoice slot. Empty is not an invoice and not live intercompany billing.",
    ),
    (
        "allocation",
        "Allocation",
        "Named allocation slot. Empty is not an allocation and not live intercompany billing.",
    ),
    (
        "arms_length",
        "Arms length",
        "Named arms-length slot. Empty is not arms-length evidence and not proof of GGV, AMG, and BZG client machinery.",
    ),
    (
        "ar_ap",
        "AR/AP",
        "Named AR/AP slot. Empty is not an AR or AP balance and not live intercompany billing.",
    ),
    (
        "notes",
        "Notes",
        "Named notes slot. Empty is not a billing note and not live intercompany billing.",
    ),
)


def _empty_slot(kind: str, label: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "slot": "empty",
        "evidence": None,
        "service_record": None,
        "invoice": None,
        "allocation": None,
        "arms_length": None,
        "ar_ap": None,
        "tax_treatment": None,
        "tax_claimed": False,
        "current": False,
        "live_billing": False,
        "client_machinery": False,
        "payment": None,
        "payment_executed": False,
        "why": why,
    }


EVIDENCE_KINDS: tuple[dict[str, Any], ...] = tuple(
    _empty_slot(*row) for row in _SLOT_SPECS
)
KIND_IDS = tuple(row["kind"] for row in EVIDENCE_KINDS)
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not live intercompany billing.",
    "An empty framework is not proof of GGV, AMG, and BZG client machinery.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "Invoices, allocations, and AR/AP balances are not invented.",
    "Tax treatment is not claimed.",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-GGV-06 stays SPECIFIED.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "ggv_intercompany_client_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_billing": False,
    "empty_is_client_machinery": False,
    "empty_is_ready": False,
    "proved": False,
    "live_billing": False,
    "client_machinery": False,
    "current": False,
    "service_record": None,
    "invoice": None,
    "allocation": None,
    "arms_length": None,
    "ar_ap": None,
    "tax_treatment": None,
    "tax_claimed": False,
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
    "invented_invoice": False,
    "invented_allocation": False,
    "invented_ar_ap": False,
    "invented_tax": False,
    "ledger_write": False,
}


class IntercompanyClientError(ValueError):
    """Fail closed. Does not invent invoices, allocations, AR/AP, tax, or PROVEN."""

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
        raise IntercompanyClientError(
            "intercompany framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise IntercompanyClientError(
            "intercompany framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise IntercompanyClientError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "tax" in name:
        raise IntercompanyClientError(
            "Tax treatment is not claimed from this framework.",
            code="tax_refused",
        )
    if (
        "invoice" in name
        or "allocation" in name
        or "ar_ap" in name
        or "arap" in name
        or "arms_length" in name
        or "service_record" in name
    ):
        raise IntercompanyClientError(
            "Invoices, allocations, and AR/AP are not invented. Empty is not live intercompany billing.",
            code="current_refused",
        )
    if "bank" in name:
        raise IntercompanyClientError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise IntercompanyClientError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise IntercompanyClientError(
            "intercompany framework refuses a production path",
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
        raise IntercompanyClientError(
            "intercompany framework refuses a path outside Beta or a test fixture",
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
    """Read CAP-GGV-06. Does not write the ledger."""
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
    """Read CR-6a19c9221cab0178. Does not upsert, resolve, or harvest."""
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
    flags["specified"] = state == "SPECIFIED"
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["invented_invoice"] = False
    flags["invented_allocation"] = False
    flags["invented_ar_ap"] = False
    flags["invented_tax"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_billing"] = False
    flags["empty_is_client_machinery"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_billing"] = False
    flags["client_machinery"] = False
    flags["current"] = False
    flags["service_record"] = None
    flags["invoice"] = None
    flags["allocation"] = None
    flags["arms_length"] = None
    flags["ar_ap"] = None
    flags["tax_treatment"] = None
    flags["tax_claimed"] = False
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
                "description": "Not accepted. A note would not be live intercompany billing.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "service_record_property": False,
        "invoice_property": False,
        "allocation_property": False,
        "arms_length_property": False,
        "ar_ap_property": False,
        "tax_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not live intercompany billing."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_billing": False,
        "empty_is_client_machinery": False,
        "empty_is_ready": False,
        "proved": False,
        "live_billing": False,
        "client_machinery": False,
        "current": False,
        "service_record": None,
        "invoice": None,
        "allocation": None,
        "arms_length": None,
        "ar_ap": None,
        "tax_treatment": None,
        "tax_claimed": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "invented_invoice": False,
        "invented_allocation": False,
        "invented_ar_ap": False,
        "invented_tax": False,
    }


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower().replace("-", "_")
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                **_quiet_read(),
                "honesty": honesty_flags(),
            }
    raise IntercompanyClientError("Unknown intercompany slot.", code="not_found")


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
    raise IntercompanyClientError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_tax(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Tax treatment is not claimed from this framework.",
        code="tax_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Invoices, allocations, and AR/AP are not invented. Empty is not live intercompany billing.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Resolving the completion row is refused. CR-6a19c9221cab0178 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "The framework stays empty. A filled slot would not be live intercompany billing.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise IntercompanyClientError(
        "An Alchemist write is refused.",
        code="alchemist_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "transfer", "payout", "withdraw"}:
                refuse_bank(payload)
            if token in {"zayen", "books", "journal"}:
                refuse_books(payload)
            if token in {"tax", "tax-treatment", "gst", "vat"}:
                refuse_tax(payload)
            if token in {
                "invoice",
                "invoices",
                "allocation",
                "allocations",
                "ar-ap",
                "arms-length",
                "service-record",
                "current",
                "live-billing",
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
                "notes",
            }:
                refuse_fill(payload)
    raise IntercompanyClientError(
        "This framework does not store live intercompany billing, invoices, allocations, AR/AP, or a tax treatment.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise IntercompanyClientError(
            "intercompany framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise IntercompanyClientError(
            "intercompany framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_GGV_INTERCOMPANY") or "").strip() != "1":
            raise IntercompanyClientError(
                "test mode refuses the live intercompany framework path",
                code="live_guard",
            )
    raise IntercompanyClientError(
        "The framework stays empty. Empty is not live intercompany billing.",
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


def invent_invoice(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_allocation(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_ar_ap(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_tax(*_args: Any, **_kwargs: Any) -> None:
    refuse_tax({})


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
    invoice: str | None = None,
    allocation: str | None = None,
    ar_ap: str | None = None,
    arms_length: str | None = None,
    service_record: str | None = None,
    tax: str | None = None,
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
    if _present(tax):
        refuse_tax({})
    if (
        _present(invoice)
        or _present(allocation)
        or _present(ar_ap)
        or _present(arms_length)
        or _present(service_record)
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
