#!/usr/bin/env python3
"""CAP-INTG-04 CAP-bound connector tests framework skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-INTG-CONNECTOR-CAP-TESTS-V1-2026-09-20.md.
CR-859e7cad64e7e4ad stays OPEN. Owner lane intg-connector-cap-tests-v1.
Mission owner-autonomous-20260920-w8 after intg-connector-contract-v1 DONE
(141d30b / 6c6ef51). intel-learning-policy-v1 stays parked.

Names the cap, fixture, and refuse slots and leaves every slot empty.
An empty framework is not a live bank-connector prove and not a live bank
feed. This module does not call a bank API, does not execute a payment,
and does not write Production, Alchemist, Cloudflare, Access, the Model C
ledger, CAP-INTG-01, or the completion row. CAP-INTG-04 stays BUILT.
The ceiling label is BUILT. PROVEN and READY are not invented.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "intg_connector_cap_tests.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CONTRACT_DB = BETA_ROOT / "catalog" / "intg_connector_contract.sqlite"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-859e7cad64e7e4ad"
CAP_ID = "CAP-INTG-04"
# 2026-07-30 decision: no bank feed. Statements are files the owner already filed.
OWNER_ARCHIVE = Path.home() / ".openclaw" / "state" / "bank"
STATEMENT_SUFFIXES = frozenset({".pdf", ".csv", ".xls", ".xlsx", ".ofx", ".qfx", ".mt940"})
SPREADSHEET_SUFFIXES = frozenset({".xls", ".xlsx"})
MAX_STATEMENT_BYTES = 20_000_000
OTHER_CAP_ID = "CAP-INTG-01"
SCHEMA_ID = "wolf.cap-intg-04.connector-cap-tests.v1"

KIND_IDS = ("cap", "fixture", "refuse")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "cap",
        "label": "Cap",
        "slot": "empty",
        "evidence": None,
        "fixture": None,
        "bank_feed": None,
        "bank_connector": None,
        "current": False,
        "proved": False,
        "payment": None,
        "payment_executed": False,
        "bank_api_called": False,
        "bank_feed_called": False,
        "why": "Named cap slot. Empty is not a live bank-connector prove and not a live bank feed.",
    },
    {
        "kind": "fixture",
        "label": "Fixture",
        "slot": "empty",
        "evidence": None,
        "fixture": None,
        "bank_feed": None,
        "bank_connector": None,
        "current": False,
        "proved": False,
        "payment": None,
        "payment_executed": False,
        "bank_api_called": False,
        "bank_feed_called": False,
        "why": "Named fixture slot. Empty is not a test fixture and not a live bank feed.",
    },
    {
        "kind": "refuse",
        "label": "Refuse",
        "slot": "empty",
        "evidence": None,
        "fixture": None,
        "bank_feed": None,
        "bank_connector": None,
        "current": False,
        "proved": False,
        "payment": None,
        "payment_executed": False,
        "bank_api_called": False,
        "bank_feed_called": False,
        "why": "Named refuse slot. Empty is not a live refuse of a bank API.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live bank-connector prove.",
    "An empty framework is not a live bank feed.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "No live bank API call.",
    "No payment is executed.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-INTG-04 stays BUILT.",
    "CAP-INTG-01 stays ABSENT.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "intg_connector_cap_tests_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_prove": False,
    "empty_is_ready": False,
    "empty_is_bank_feed": False,
    "proved": False,
    "live_bank_connector": False,
    "current": False,
    "fixture": None,
    "bank_feed": None,
    "bank_connector": None,
    "bank_api_called": False,
    "bank_feed_called": False,
    "payment": None,
    "money": None,
    "payment_executed": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "external_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "cap_intg_01_rewritten": False,
    "ledger_write": False,
}


class ConnectorCapTestsError(ValueError):
    """Fail closed. Does not invent a bank connector, a bank feed, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _bank_name(name: str) -> bool:
    token = name.lower().replace("_", "-")
    needles = (
        "plaid",
        "openbanking",
        "open-banking",
        "bank-api",
        "bank-feed",
        "bankfeed",
    )
    return any(needle in token for needle in needles)


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise ConnectorCapTestsError(
            "connector tests refuse an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise ConnectorCapTestsError(
            "connector tests refuse a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise ConnectorCapTestsError(
            "connector tests refuse a production path",
            code="not_beta",
        )
    if _bank_name(resolved.name):
        raise ConnectorCapTestsError(
            "A live bank API call is refused. An empty framework is not a live bank feed.",
            code="bank_refused",
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
        raise ConnectorCapTestsError(
            "connector tests refuse a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _row_state(data: Any, cap_id: str) -> str:
    row = data.get(cap_id) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ledger_cap_state(
    ledger_path: Path | str | None = None,
    cap_id: str = CAP_ID,
) -> str:
    """Read a ledger row. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    return _row_state(data, cap_id)


def ceiling_for(_state: str) -> str:
    """BUILT label only. At most BUILT. Does not write the ledger."""
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-859e7cad64e7e4ad. Does not upsert, resolve, or harvest."""
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
    state = ledger_cap_state(ledger_path, CAP_ID)
    other = ledger_cap_state(ledger_path, OTHER_CAP_ID)
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling_for(state)
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["absent"] = state == "ABSENT"
    flags["cap_intg_01"] = other
    flags["cap_intg_01_rewritten"] = False
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_prove"] = False
    flags["empty_is_ready"] = False
    flags["empty_is_bank_feed"] = False
    flags["proved"] = False
    flags["live_bank_connector"] = False
    flags["current"] = False
    flags["fixture"] = None
    flags["bank_feed"] = None
    flags["bank_connector"] = None
    flags["bank_api_called"] = False
    flags["bank_feed_called"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["payment_executed"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["external_write"] = False
    flags["on_disk"] = False
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
                "description": "Not accepted. A note would not be a live bank-connector prove.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_api_property": False,
        "bank_feed_property": False,
        "current_property": False,
        "fixture_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live bank-connector prove."""
    return [dict(row) for row in EVIDENCE_KINDS]


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                "empty": True,
                "empty_is_prove": False,
                "empty_is_ready": False,
                "empty_is_bank_feed": False,
                "proved": False,
                "live_bank_connector": False,
                "current": False,
                "fixture": None,
                "bank_feed": None,
                "bank_connector": None,
                "bank_api_called": False,
                "bank_feed_called": False,
                "payment": None,
                "payment_executed": False,
                "ledger_write": False,
                "cr_resolved": False,
                "cap_intg_01_rewritten": False,
                "honesty": honesty_flags(),
            }
    raise ConnectorCapTestsError("Unknown connector slot.", code="not_found")


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a framework file."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_prove": False,
        "empty_is_ready": False,
        "empty_is_bank_feed": False,
        "recorded_count": 0,
        "proved": False,
        "live_bank_connector": False,
        "current": False,
        "fixture": None,
        "bank_feed": None,
        "bank_connector": None,
        "bank_api_called": False,
        "bank_feed_called": False,
        "payment": None,
        "money": None,
        "payment_executed": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "score_changed": False,
        "external_write": False,
        "on_disk": False,
        "kinds": slots,
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        "ledger_write": False,
        "cap_intg_01_rewritten": False,
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "A live bank API call is refused. An empty framework is not a live bank-connector prove.",
        code="bank_refused",
    )


def refuse_feed(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "A live bank feed is refused. An empty framework is not a live bank feed.",
        code="feed_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "A live bank connector is not current. Empty is not a current connector.",
        code="current_refused",
    )


def refuse_connector(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "An external connector write is refused.",
        code="connector_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays BUILT.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "Resolving the completion row is refused. CR-859e7cad64e7e4ad stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "The framework stays empty. A filled slot would not be a live bank-connector prove.",
        code="slots_refused",
    )


def refuse_rewrite(_body: dict | None = None) -> None:
    raise ConnectorCapTestsError(
        "CAP-INTG-01 stays ABSENT. This framework does not rewrite that work.",
        code="rewrite_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "bank-api", "live-bank", "plaid", "open-banking"}:
                refuse_bank(payload)
            if token in {"feed", "bank-feed", "live-feed"}:
                refuse_feed(payload)
            if token in {"current", "live-connector"}:
                refuse_current(payload)
            if token in {"connector", "external", "external-write"}:
                refuse_connector(payload)
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
            if token in {"cap-intg-01", "rewrite", "intg-01"}:
                refuse_rewrite(payload)
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "cap",
                "fixture",
                "refuse",
            }:
                refuse_fill(payload)
    raise ConnectorCapTestsError(
        "This framework does not store a cap slot, a fixture, a payment, or a live bank feed.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise ConnectorCapTestsError(
            "connector tests do not write the content catalog",
            code="catalog_refused",
        )
    if resolved == CONTRACT_DB.resolve() or resolved.name == "intg_connector_contract.sqlite":
        refuse_rewrite({})
    if resolved.name == "model-c-baseline-assessments.json":
        raise ConnectorCapTestsError(
            "connector tests do not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_INTG_CAP_TESTS") or "").strip() != "1":
            raise ConnectorCapTestsError(
                "test mode refuses the live connector tests path",
                code="live_guard",
            )
    raise ConnectorCapTestsError(
        "The framework stays empty. Empty is not a live bank-connector prove.",
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


def call_bank_api(*_args: Any, **_kwargs: Any) -> None:
    refuse_bank({})


def call_bank_feed(*_args: Any, **_kwargs: Any) -> None:
    refuse_feed({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def _redact_name(name: str) -> str:
    """Drop digit runs. A file name is not an account number to repeat."""
    return re.sub(r"\d{4,}", "#", name)


def _root_kind(root: Path) -> str:
    """Owner archive, or a temp shape check. Anything else is refused."""
    resolved = root.resolve()
    archive = OWNER_ARCHIVE.resolve()
    try:
        resolved.relative_to(archive)
        return "archive"
    except ValueError:
        pass
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(temp_root)
        return "temp"
    except ValueError as exc:
        raise ConnectorCapTestsError(
            "Statement read refuses a path that is not the owner archive.",
            code="archive_refused",
        ) from exc


def _empty_read(*, authorised: bool, archive_present: bool) -> dict[str, Any]:
    configured = bool(authorised and archive_present)
    return {
        "ok": True,
        "cap": CAP_ID,
        "archive_present": archive_present,
        "authorised": authorised,
        "configured": configured,
        "connected": False,
        "tested": True,
        "commissioned": False,
        "states_collapsed": False,
        "state_notes": {
            "configured": (
                "The owner statement archive is on disk."
                if configured
                else "The owner statement archive is not on disk."
            ),
            "connected": "No bank API is called. A file on disk is not a bank connection.",
            "tested": "This read attempt finished.",
            "commissioned": "No human acceptance was recorded.",
        },
        "file_read": False,
        "opened": 0,
        "pdf": 0,
        "csv": 0,
        "spreadsheet": 0,
        "skipped_other": 0,
        "unreadable": 0,
        "oversize": 0,
        "bytes": 0,
        "manifest_sha256": hashlib.sha256(b"").hexdigest(),
        "payment_executed": False,
        "bank_api_called": False,
        "bank_feed_called": False,
        "money_moved": False,
        "amounts_parsed": False,
        "persisted": False,
        "books_written": False,
        "reconciled": False,
        "management_report": False,
        "ledger_write": False,
        "external_write": False,
        "rows": [],
    }


def read_authorised_files(
    root: Path | str | None = None,
    *,
    payment: str | None = None,
) -> dict[str, Any]:
    """Read statement files the owner already filed.

    Serves the 2026-07-30 decision: there is no bank feed. This does not
    call a bank, parse an amount, write books, or move money. A temp
    directory is a shape check and is not the authorised archive.
    CONFIGURED, CONNECTED, TESTED, and COMMISSIONED stay separate.
    """
    if _present(payment):
        refuse_payment({})
    if root is None:
        base = OWNER_ARCHIVE
        kind = "archive"
    else:
        base = Path(root)
        kind = _root_kind(base)
    authorised = kind == "archive"
    if not base.is_dir():
        report = _empty_read(authorised=authorised, archive_present=False)
        report["authorised"] = authorised
        return report

    opened = 0
    pdf = 0
    csv = 0
    spreadsheet = 0
    skipped_other = 0
    unreadable = 0
    oversize = 0
    total = 0
    rows: list[dict[str, Any]] = []
    manifest = hashlib.sha256()
    root_resolved = base.resolve()
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        for name in sorted(filenames):
            if name.startswith("."):
                skipped_other += 1
                continue
            path = Path(dirpath) / name
            try:
                resolved = path.resolve()
                resolved.relative_to(root_resolved)
            except (OSError, ValueError):
                skipped_other += 1
                continue
            suffix = resolved.suffix.lower()
            if suffix not in STATEMENT_SUFFIXES:
                skipped_other += 1
                continue
            try:
                size = resolved.stat().st_size
            except OSError:
                unreadable += 1
                continue
            if size > MAX_STATEMENT_BYTES:
                oversize += 1
                continue
            try:
                blob = resolved.read_bytes()
            except OSError:
                unreadable += 1
                continue
            digest = hashlib.sha256(blob).hexdigest()
            rel = _redact_name(str(resolved.relative_to(root_resolved)))
            if re.search(r"\d{4,}", rel):
                rel = re.sub(r"\d", "#", rel)
            opened += 1
            total += len(blob)
            if suffix == ".pdf":
                pdf += 1
            elif suffix == ".csv":
                csv += 1
            elif suffix in SPREADSHEET_SUFFIXES:
                spreadsheet += 1
            manifest.update(suffix.encode("ascii"))
            manifest.update(b"\0")
            manifest.update(digest.encode("ascii"))
            manifest.update(b"\0")
            manifest.update(str(len(blob)).encode("ascii"))
            manifest.update(b"\n")
            rows.append(
                {
                    "name": rel,
                    "suffix": suffix,
                    "bytes": len(blob),
                    "sha256": digest,
                }
            )
    report = _empty_read(authorised=authorised, archive_present=True)
    report["authorised"] = authorised
    report["configured"] = authorised
    report["file_read"] = bool(authorised and opened)
    report["opened"] = opened
    report["pdf"] = pdf
    report["csv"] = csv
    report["spreadsheet"] = spreadsheet
    report["skipped_other"] = skipped_other
    report["unreadable"] = unreadable
    report["oversize"] = oversize
    report["bytes"] = total
    report["manifest_sha256"] = manifest.hexdigest()
    report["rows"] = rows
    return report


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    feed: str | None = None,
    current: str | None = None,
    connector: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    write: str | None = None,
    score: str | None = None,
    rewrite: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(bank):
        refuse_bank({})
    if _present(feed):
        refuse_feed({})
    if _present(current):
        refuse_current({})
    if _present(connector):
        refuse_connector({})
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
    if _present(rewrite):
        refuse_rewrite({})
    if _present(fill):
        refuse_fill({})
    if _present(write):
        refuse_external_write({})
