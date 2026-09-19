#!/usr/bin/env python3
"""Intel evaluation + cost ledger v1 (Beta only).

Append-only records of Wolf Intelligence calls: model, tokens, cost estimate,
route, outcome, provenance. Owner-readable summary. Fail closed.

Does not invent prices, call spend APIs, or bill.
Does not raise Model C maturity and does not mark any CAP PROVEN.
Does not edit wolf_intelligence.py. Does not auto-instrument other routes.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "intel_eval_cost_ledger.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
OWNER_PERSON = "PERS-MATT"
TZ_UTC = timezone.utc

SUMMARY_LIMIT_DEFAULT = 20
SUMMARY_LIMIT_MAX = 50

OUTCOME_OK = "OK"
OUTCOME_REFUSED = "REFUSED"
OUTCOME_ERROR = "ERROR"
OUTCOME_NOT_RUN = "NOT_RUN"
OUTCOME_UNKNOWN = "UNKNOWN"
OUTCOMES = frozenset(
    {
        OUTCOME_OK,
        OUTCOME_REFUSED,
        OUTCOME_ERROR,
        OUTCOME_NOT_RUN,
        OUTCOME_UNKNOWN,
    }
)

COST_NOT_SUPPLIED = "NOT_SUPPLIED"
COST_PROVIDED = "PROVIDED"
TOKEN_NOT_SUPPLIED = "NOT_SUPPLIED"
TOKEN_PROVIDED = "PROVIDED"
COST_SOURCE_CALLER = "caller_supplied"

PRICE_KEYS = frozenset(
    {
        "price_lookup",
        "fetch_price",
        "lookup_price",
        "rate_card",
        "compute_cost",
        "invent_price",
        "estimate_tokens",
    }
)
BILLING_KEYS = frozenset(
    {
        "billing",
        "auto_bill",
        "auto_billing",
        "invoice",
        "charge",
    }
)
SPEND_KEYS = frozenset(
    {
        "spend_api",
        "external_spend",
        "usage_api",
    }
)
ALLOW_KEYS = frozenset(
    {
        "model",
        "route",
        "outcome",
        "tokens",
        "cost_estimate",
        "cost_source",
        "currency",
        "provenance",
    }
)
PROVENANCE_KEYS = frozenset({"source", "call_id", "surface"})

_DECIMAL_RE = re.compile(r"^\d{1,12}(\.\d{1,6})?$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,80}$")
_ROUTE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,120}$")
_CALL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)
_BANNED_ROUTE = ("billing", "invoice", "stripe", "spend", "usage", "price", "http")

HONESTY = {
    "ledger": "intel_eval_cost",
    "append_only": True,
    "invent_prices": False,
    "external_spend_api": False,
    "auto_billing": False,
    "auto_instrument": False,
    "currency_defaulted": False,
    "token_total_derived": False,
    "proven": False,
    "cap_proven": False,
    "model_c_maturity_raised": False,
    "model_c_write": False,
    "production": False,
    "alchemist_write": False,
    "owner_only": True,
    "not_a_bill": True,
}


class IntelEvalCostError(ValueError):
    """Fail-closed validation. Does not invent a price or a row."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_record_id() -> str:
    return f"IEL-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_db_writable(db_path: Path) -> None:
    """Refuse accidental live default DB writes from tests."""
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_INTEL_EVAL") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise IntelEvalCostError(
            "test mode refuses writes to the live intel eval ledger; "
            "point db_path at a temp file",
            code="live_guard",
        )


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise IntelEvalCostError(
            "intel eval ledger refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise IntelEvalCostError(
            "intel eval ledger refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise IntelEvalCostError(
            "intel eval ledger refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
    except ValueError as exc:
        raise IntelEvalCostError(
            "intel eval ledger refuses a non-beta path",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_INTEL_EVAL_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    return resolved


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intel_eval_cost_ledger (
  record_id TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  route TEXT NOT NULL,
  outcome TEXT NOT NULL,
  token_input INTEGER NULL,
  token_output INTEGER NULL,
  token_total INTEGER NULL,
  token_status TEXT NOT NULL,
  cost_estimate TEXT NULL,
  cost_currency TEXT NULL,
  cost_status TEXT NOT NULL,
  cost_source TEXT NULL,
  provenance_json TEXT NOT NULL,
  actor TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_iel_recorded ON intel_eval_cost_ledger(recorded_at);
CREATE INDEX IF NOT EXISTS idx_iel_route ON intel_eval_cost_ledger(route);

CREATE TRIGGER IF NOT EXISTS trg_intel_eval_cost_no_update
BEFORE UPDATE ON intel_eval_cost_ledger
BEGIN
  SELECT RAISE(ABORT, 'intel_eval_cost_ledger is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_eval_cost_no_delete
BEFORE DELETE ON intel_eval_cost_ledger
BEGIN
  SELECT RAISE(ABORT, 'intel_eval_cost_ledger is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _require_owner(person_id: str | None) -> str:
    pid = (person_id or "").strip()
    if pid != OWNER_PERSON:
        raise IntelEvalCostError(
            "intel eval ledger is Owner (PERS-MATT) only",
            code="denied",
        )
    return pid


def _refuse_keys(payload: dict[str, Any]) -> None:
    keys = set(payload)
    if keys & SPEND_KEYS:
        raise IntelEvalCostError(
            "external spend APIs are refused",
            code="spend_api_refused",
        )
    if keys & BILLING_KEYS:
        raise IntelEvalCostError(
            "auto-billing is refused",
            code="billing_refused",
        )
    if keys & PRICE_KEYS:
        raise IntelEvalCostError(
            "price lookup and invented prices are refused",
            code="price_refused",
        )
    unknown = keys - ALLOW_KEYS
    if unknown:
        raise IntelEvalCostError(
            "unknown field: " + ", ".join(sorted(unknown)),
            code="bad_payload",
        )


def _clean_label(value: Any, *, code: str, what: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str):
        raise IntelEvalCostError(f"{what} required", code=code)
    text = value.strip()
    if not pattern.fullmatch(text):
        raise IntelEvalCostError(f"{what} is not an allowed label", code=code)
    if _SECRET_RE.search(text):
        raise IntelEvalCostError(f"{what} looks like a secret", code=code)
    low = text.lower()
    if what == "route" and any(bit in low for bit in _BANNED_ROUTE):
        raise IntelEvalCostError(
            "route looks like billing or a remote spend call",
            code="spend_api_refused",
        )
    if what == "model" and any(bit in low for bit in ("billing", "price", "http", "stripe")):
        raise IntelEvalCostError(
            "model looks like a price or billing call",
            code="price_refused",
        )
    return text


def _nn_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise IntelEvalCostError(
            f"{name} must be a non-negative integer",
            code="bad_tokens",
        )
    if value > 100_000_000:
        raise IntelEvalCostError(f"{name} is out of range", code="bad_tokens")
    return value


def _clean_tokens(payload: dict[str, Any]) -> tuple[int | None, int | None, int | None, str]:
    if "tokens" not in payload or payload.get("tokens") is None:
        return None, None, None, TOKEN_NOT_SUPPLIED
    raw = payload["tokens"]
    if not isinstance(raw, dict):
        raise IntelEvalCostError("tokens must be an object", code="bad_tokens")
    unknown = set(raw) - {"input", "output", "total"}
    if unknown:
        raise IntelEvalCostError(
            "unknown token field: " + ", ".join(sorted(unknown)),
            code="bad_tokens",
        )
    if not raw:
        raise IntelEvalCostError("tokens object is empty", code="bad_tokens")
    token_input = _nn_int(raw["input"], "tokens.input") if "input" in raw else None
    token_output = _nn_int(raw["output"], "tokens.output") if "output" in raw else None
    token_total = _nn_int(raw["total"], "tokens.total") if "total" in raw else None
    if (
        token_input is not None
        and token_output is not None
        and token_total is not None
        and token_total != token_input + token_output
    ):
        raise IntelEvalCostError(
            "tokens.total does not match input + output; nothing was corrected",
            code="bad_tokens",
        )
    return token_input, token_output, token_total, TOKEN_PROVIDED


def _clean_cost(payload: dict[str, Any]) -> tuple[str | None, str | None, str, str | None]:
    has_cost = "cost_estimate" in payload and payload.get("cost_estimate") not in (None, "")
    source = payload.get("cost_source")
    currency = payload.get("currency")
    if not has_cost:
        if source not in (None, ""):
            raise IntelEvalCostError(
                "cost_source without a caller-supplied estimate is refused",
                code="price_refused",
            )
        if currency not in (None, ""):
            raise IntelEvalCostError(
                "currency without a caller-supplied estimate is refused",
                code="price_refused",
            )
        return None, None, COST_NOT_SUPPLIED, None
    raw = payload.get("cost_estimate")
    if isinstance(raw, bool) or isinstance(raw, float):
        raise IntelEvalCostError(
            "cost_estimate must be a decimal string; floats are not accepted",
            code="price_refused",
        )
    if isinstance(raw, int):
        raw = str(raw)
    if not isinstance(raw, str) or not _DECIMAL_RE.fullmatch(raw.strip()):
        raise IntelEvalCostError(
            "cost_estimate must be a non-negative decimal string",
            code="price_refused",
        )
    if source != COST_SOURCE_CALLER:
        raise IntelEvalCostError(
            "cost requires cost_source caller_supplied; prices are not looked up",
            code="price_refused",
        )
    currency_out: str | None
    if currency in (None, ""):
        currency_out = None
    elif isinstance(currency, str) and _CURRENCY_RE.fullmatch(currency):
        currency_out = currency
    else:
        raise IntelEvalCostError(
            "currency must be a 3-letter code supplied by the caller",
            code="price_refused",
        )
    return raw.strip(), currency_out, COST_PROVIDED, COST_SOURCE_CALLER


def _clean_provenance(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise IntelEvalCostError("provenance object required", code="bad_provenance")
    unknown = set(value) - PROVENANCE_KEYS
    if unknown:
        raise IntelEvalCostError(
            "unknown provenance field: " + ", ".join(sorted(unknown)),
            code="bad_provenance",
        )
    source = value.get("source")
    if not isinstance(source, str) or not source.strip():
        raise IntelEvalCostError("provenance.source required", code="bad_provenance")
    source = source.strip()
    if len(source) > 120 or _SECRET_RE.search(source):
        raise IntelEvalCostError("provenance.source refused", code="bad_provenance")
    out: dict[str, str] = {"source": source}
    if "call_id" in value and value.get("call_id") not in (None, ""):
        call_id = value.get("call_id")
        if not isinstance(call_id, str) or not _CALL_ID_RE.fullmatch(call_id):
            raise IntelEvalCostError("provenance.call_id refused", code="bad_provenance")
        out["call_id"] = call_id
    if "surface" in value and value.get("surface") not in (None, ""):
        surface = value.get("surface")
        if not isinstance(surface, str) or not _ROUTE_RE.fullmatch(surface.strip()):
            raise IntelEvalCostError("provenance.surface refused", code="bad_provenance")
        out["surface"] = surface.strip()
    encoded = json.dumps(out, separators=(",", ":"))
    if len(encoded) > 500:
        raise IntelEvalCostError("provenance is too large", code="bad_provenance")
    return out


def _clean_outcome(value: Any) -> str:
    if not isinstance(value, str):
        raise IntelEvalCostError("outcome required", code="bad_outcome")
    outcome = value.strip().upper()
    if outcome not in OUTCOMES:
        raise IntelEvalCostError(
            "outcome must be one of " + ", ".join(sorted(OUTCOMES)),
            code="bad_outcome",
        )
    return outcome


def update_record(*_args: Any, **_kwargs: Any) -> None:
    raise NotImplementedError("intel_eval_cost_ledger is append-only")


def delete_record(*_args: Any, **_kwargs: Any) -> None:
    raise NotImplementedError("intel_eval_cost_ledger is append-only")


def _empty_summary() -> dict[str, Any]:
    return {
        "count": 0,
        "cost_supplied_rows": 0,
        "cost_complete": False,
        "not_a_bill": True,
        "cost_sums": [],
        "token_input_supplied_rows": 0,
        "token_input_complete": False,
        "token_input_sum": None,
        "token_output_supplied_rows": 0,
        "token_output_complete": False,
        "token_output_sum": None,
        "token_total_supplied_rows": 0,
        "token_total_complete": False,
        "token_total_sum": None,
        "latest": [],
        "honesty": honesty_flags(),
        "summary": _summary_sentence(0, 0, False, []),
    }


def _summary_sentence(
    count: int,
    cost_supplied: int,
    cost_complete: bool,
    sums: list[dict[str, Any]],
) -> str:
    if count == 0:
        return (
            "No calls on the ledger. No price was invented. This is not a bill."
        )
    parts = [f"{count} calls recorded."]
    if cost_supplied == 0:
        parts.append("No cost estimate was supplied. Missing prices were not filled in.")
    else:
        bits = []
        for row in sums:
            label = row["currency"] or "unspecified currency"
            bits.append(f"{row['sum']} {label} across {row['rows']} supplied rows")
        parts.append("Supplied estimates only: " + "; ".join(bits) + ".")
        if not cost_complete:
            parts.append("Other rows have no cost. Those were not estimated.")
    parts.append("This is not a bill and nothing was charged.")
    return " ".join(parts)


def _connect_write(db_path: Path | str | None) -> tuple[sqlite3.Connection, Path]:
    resolved = _resolve_db(db_path)
    assert_db_writable(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn, resolved


def record_call(
    payload: dict[str, Any] | None,
    *,
    person_id: str | None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Append one call. Refuses price invention, spend APIs, and billing."""
    actor = _require_owner(person_id)
    if not isinstance(payload, dict):
        raise IntelEvalCostError("payload must be an object", code="bad_payload")
    _refuse_keys(payload)
    model = _clean_label(payload.get("model"), code="bad_model", what="model", pattern=_TOKEN_RE)
    route = _clean_label(payload.get("route"), code="bad_route", what="route", pattern=_ROUTE_RE)
    outcome = _clean_outcome(payload.get("outcome"))
    token_input, token_output, token_total, token_status = _clean_tokens(payload)
    cost_estimate, cost_currency, cost_status, cost_source = _clean_cost(payload)
    provenance = _clean_provenance(payload.get("provenance"))
    record_id = mint_record_id()
    recorded_at = now_utc_iso()
    conn, _resolved = _connect_write(db_path)
    try:
        conn.execute(
            """
            INSERT INTO intel_eval_cost_ledger (
              record_id, model, route, outcome,
              token_input, token_output, token_total, token_status,
              cost_estimate, cost_currency, cost_status, cost_source,
              provenance_json, actor, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                model,
                route,
                outcome,
                token_input,
                token_output,
                token_total,
                token_status,
                cost_estimate,
                cost_currency,
                cost_status,
                cost_source,
                json.dumps(provenance, separators=(",", ":")),
                actor,
                recorded_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "record_id": record_id,
        "appended": True,
        "model": model,
        "route": route,
        "outcome": outcome,
        "token_status": token_status,
        "cost_status": cost_status,
        "cost_currency": cost_currency,
        "recorded_at": recorded_at,
        "honesty": honesty_flags(),
    }


def _add(bucket: dict[str, Decimal], counts: dict[str, int], key: str, raw: str) -> None:
    bucket[key] = bucket.get(key, Decimal("0")) + Decimal(raw)
    counts[key] = counts.get(key, 0) + 1


def read_summary(
    person_id: str | None,
    *,
    db_path: Path | str | None = None,
    limit: int = SUMMARY_LIMIT_DEFAULT,
) -> dict[str, Any]:
    """Owner summary. Missing file stays missing. Partial costs are not a bill."""
    _require_owner(person_id)
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise IntelEvalCostError("limit must be an integer", code="bad_limit")
    if limit < 1 or limit > SUMMARY_LIMIT_MAX:
        raise IntelEvalCostError(
            f"limit must be 1..{SUMMARY_LIMIT_MAX}",
            code="bad_limit",
        )
    resolved = _resolve_db(db_path)
    if not resolved.exists():
        return _empty_summary()
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            str(r[0])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "intel_eval_cost_ledger" not in tables:
            raise IntelEvalCostError(
                "ledger schema is missing",
                code="schema_missing",
            )
        rows = conn.execute(
            """
            SELECT record_id, model, route, outcome,
                   token_input, token_output, token_total, token_status,
                   cost_estimate, cost_currency, cost_status, cost_source,
                   provenance_json, recorded_at
            FROM intel_eval_cost_ledger
            ORDER BY recorded_at DESC, rowid DESC
            """
        ).fetchall()
    finally:
        conn.close()

    count = len(rows)
    if count == 0:
        return _empty_summary()

    sums: dict[str, Decimal] = {}
    sum_rows: dict[str, int] = {}
    cost_supplied = 0
    input_sum = 0
    input_n = 0
    output_sum = 0
    output_n = 0
    total_sum = 0
    total_n = 0
    latest: list[dict[str, Any]] = []
    for row in rows:
        if row["cost_status"] == COST_PROVIDED and row["cost_estimate"]:
            cost_supplied += 1
            key = row["cost_currency"] or ""
            _add(sums, sum_rows, key, str(row["cost_estimate"]))
        if row["token_input"] is not None:
            input_n += 1
            input_sum += int(row["token_input"])
        if row["token_output"] is not None:
            output_n += 1
            output_sum += int(row["token_output"])
        if row["token_total"] is not None:
            total_n += 1
            total_sum += int(row["token_total"])
        if len(latest) < limit:
            source = ""
            try:
                parsed = json.loads(row["provenance_json"] or "{}")
                if isinstance(parsed, dict):
                    source = str(parsed.get("source") or "")
            except json.JSONDecodeError:
                source = ""
            latest.append(
                {
                    "record_id": row["record_id"],
                    "model": row["model"],
                    "route": row["route"],
                    "outcome": row["outcome"],
                    "token_status": row["token_status"],
                    "token_input": row["token_input"],
                    "token_output": row["token_output"],
                    "token_total": row["token_total"],
                    "cost_status": row["cost_status"],
                    "cost_estimate": row["cost_estimate"],
                    "cost_currency": row["cost_currency"],
                    "cost_source": row["cost_source"],
                    "provenance_source": source,
                    "recorded_at": row["recorded_at"],
                }
            )
    cost_complete = cost_supplied == count and count > 0
    cost_sums = [
        {
            "currency": key or None,
            "sum": format(sums[key], "f"),
            "rows": sum_rows[key],
        }
        for key in sorted(sums)
    ]
    return {
        "count": count,
        "cost_supplied_rows": cost_supplied,
        "cost_complete": cost_complete,
        "not_a_bill": True,
        "cost_sums": cost_sums,
        "token_input_supplied_rows": input_n,
        "token_input_complete": input_n == count and count > 0,
        "token_input_sum": input_sum if input_n else None,
        "token_output_supplied_rows": output_n,
        "token_output_complete": output_n == count and count > 0,
        "token_output_sum": output_sum if output_n else None,
        "token_total_supplied_rows": total_n,
        "token_total_complete": total_n == count and count > 0,
        "token_total_sum": total_sum if total_n else None,
        "latest": latest,
        "honesty": honesty_flags(),
        "summary": _summary_sentence(count, cost_supplied, cost_complete, cost_sums),
    }
