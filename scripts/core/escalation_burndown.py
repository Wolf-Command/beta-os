#!/usr/bin/env python3
"""CAP-CORE-12 escalation / independence burn-down counters (Beta, read-only).

Deepens the already-BUILT delegation module. Not a new system.
Decision served: 2026-09-19 PICK in wolf-output/decisions.md
(lane core-escalation-burndown; plan
docs/deliveries/GROK-PLAN-CORE-ESCALATION-BURNDOWN-2026-09-19.md).

Counts accidental founder dependency (unresolved NEEDS_MATT) against
time-bounded delegations over 7/30/90/365. Does not invent PROVEN.
Does not resolve, harvest, or clear Needs Matt. A resolved row without
resolution evidence is not a burn-down.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

CR_ID = "CR-6e3fd7b9d7edca0e"
CAP_ID = "CAP-CORE-12"
WINDOWS = (7, 30, 90, 365)

WITA = timezone(timedelta(hours=8))
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
OPEN_DELEGATION = frozenset({"SCHEDULED", "ACTIVE"})
UNBOUND_STATUS = frozenset({"SCHEDULED", "ACTIVE", "EXPIRED"})

HONESTY = {
    "cap": CAP_ID,
    "slice": "core_escalation_burndown",
    "read_only": True,
    "score_changed": False,
    "auto_clear_needs_matt": False,
    "operating_test": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
}


class BurndownError(ValueError):
    """Fail closed. Does not clear Needs Matt and does not invent maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    """Every mutation path ends here. Needs Matt stays as it was read."""
    raise BurndownError(
        "Escalation burn-down is read-only. Needs Matt is not auto-cleared.",
        code="writes_refused",
    )


def refuse_needs_matt_clear(_body: dict | None = None) -> None:
    """Explicit clear path. Same refusal. No row is touched."""
    refuse_external_write(_body)


def _guard_read(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise BurndownError("burn-down refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise BurndownError("burn-down refuses a production money path", code="not_beta")
    resolved = path.resolve()
    try:
        resolved.relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise BurndownError(
            "burn-down refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise BurndownError("burn-down refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-CORE-12 from the ledger. Does not write it."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_read(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return _maturity(str(row[0]))


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-6e3fd7b9d7edca0e. Does not upsert, resolve, or harvest."""
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
    _guard_read(path)
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
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["score_changed"] = False
    flags["auto_clear_needs_matt"] = False
    flags["operating_test"] = False
    return flags


def _as_wita(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(WITA)
    if now.tzinfo is None:
        return now.replace(tzinfo=WITA)
    return now.astimezone(WITA)


def _parse_ts(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=WITA)
    return parsed.astimezone(WITA)


def _evidence(value: Any) -> bool:
    return bool(str(value or "").strip())


def _blank_window(days: int, *, independence: str, why: str) -> dict[str, Any]:
    return {
        "days": days,
        "opened": None,
        "still_open": None,
        "older_open": None,
        "burned_down": None,
        "refused_silent_clear": None,
        "intentional_time_bounded": None,
        "independence": independence,
        "proven": False,
        "operating_test": False,
        "why": why,
    }


def counters_for(
    completion: list[dict[str, Any]] | None,
    delegations: list[dict[str, Any]] | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pure counters. None source means unread (not zero). Does not mutate inputs."""
    moment = _as_wita(now)
    base: dict[str, Any] = {
        "as_of": moment.isoformat(timespec="seconds"),
        "windows": [],
        "needs_matt_open": None,
        "undated_or_future": None,
        "unbounded_delegations": None,
        "refused_silent_clear": None,
        "completion_rows": None,
        "delegation_rows": None,
        "completion_status": "NOT_READ" if completion is None else "READ",
        "delegation_status": "NOT_READ" if delegations is None else "READ",
        "auto_clear_needs_matt": False,
        "operating_test": False,
        "proven": False,
    }
    if completion is None or delegations is None:
        why = "A source was not read. Counts stay blank. Empty is not assumed."
        base["windows"] = [
            _blank_window(days, independence="NOT_READ", why=why) for days in WINDOWS
        ]
        return base

    needs = [row for row in completion if str(row.get("blocker_class") or "").upper() == "NEEDS_MATT"]
    undated = 0
    dated_open: list[datetime] = []
    opened_at: list[tuple[datetime, bool]] = []
    burned: list[datetime] = []
    silent: list[datetime | None] = []
    for row in needs:
        state = str(row.get("state") or "").strip().upper()
        seen = _parse_ts(row.get("first_seen"))
        resolved_at = _parse_ts(row.get("resolved_at"))
        evidenced = _evidence(row.get("resolution_evidence"))
        if seen is None or seen > moment:
            undated += 1
            if state == "RESOLVED":
                silent.append(resolved_at)
            continue
        if state == "RESOLVED":
            if evidenced and resolved_at is not None and resolved_at <= moment:
                burned.append(resolved_at)
                opened_at.append((seen, False))
            else:
                silent.append(resolved_at)
                opened_at.append((seen, False))
            continue
        dated_open.append(seen)
        opened_at.append((seen, True))

    unbounded = 0
    bounded: list[tuple[datetime, datetime]] = []
    for row in delegations:
        status = str(row.get("status") or "").strip().upper()
        start = _parse_ts(row.get("effective_from"))
        end = _parse_ts(row.get("effective_to"))
        if status in UNBOUND_STATUS and (start is None or end is None or end <= start):
            unbounded += 1
            continue
        if status in OPEN_DELEGATION and start is not None and end is not None and end > start:
            bounded.append((start, end))

    silent_blocks = len(silent) > 0
    base["needs_matt_open"] = len(dated_open) + undated
    base["undated_or_future"] = undated
    base["unbounded_delegations"] = unbounded
    base["refused_silent_clear"] = len(silent)
    base["completion_rows"] = len(completion)
    base["delegation_rows"] = len(delegations)

    windows: list[dict[str, Any]] = []
    for days in WINDOWS:
        start = moment - timedelta(days=days)
        opened = sum(1 for seen, _ in opened_at if start <= seen <= moment)
        still_open = sum(1 for seen in dated_open if start <= seen <= moment)
        older_open = sum(1 for seen in dated_open if seen < start)
        burned_down = sum(1 for when in burned if start <= when <= moment)
        refused = sum(
            1 for when in silent if when is not None and start <= when <= moment
        )
        intentional = sum(1 for begin, end in bounded if begin <= moment and end >= start)
        if undated or silent_blocks or unbounded:
            independence = "BLOCKED"
            why = (
                "Undated Needs Matt, a clear without evidence, or a delegation "
                "without both ends. Not treated as burned down."
            )
        elif len(completion) == 0:
            independence = "EMPTY"
            why = "Register is empty. Empty is not independence and not a burn-down."
        elif still_open or older_open:
            independence = "OPEN"
            why = "Unresolved Needs Matt remains. It was not cleared."
        else:
            independence = "CLEAR"
            why = (
                "No unresolved Needs Matt in the register for this window. "
                "That is not an operating test and does not promote the capability."
            )
        windows.append(
            {
                "days": days,
                "opened": opened,
                "still_open": still_open,
                "older_open": older_open,
                "burned_down": burned_down,
                "refused_silent_clear": refused,
                "intentional_time_bounded": intentional,
                "independence": independence,
                "proven": False,
                "operating_test": False,
                "why": why,
            }
        )
    base["windows"] = windows
    return base


def _read_table(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]] | None:
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except sqlite3.Error:
        return None


def build_report(
    catalog_db: Path | str | None = None,
    now: datetime | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Owner report. Opens the catalog read-only. Does not clear Needs Matt."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    completion: list[dict[str, Any]] | None = None
    delegations: list[dict[str, Any]] | None = None
    if path.is_file():
        _guard_read(path)
        uri = path.resolve().as_uri() + "?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
        except sqlite3.Error:
            conn = None
        if conn is not None:
            try:
                completion = _read_table(
                    conn,
                    """
                    SELECT id, state, blocker_class, first_seen, resolved_at, resolution_evidence
                    FROM wolf_completion_items
                    """,
                )
                delegations = _read_table(
                    conn,
                    """
                    SELECT delegation_id, status, effective_from, effective_to
                    FROM core_delegations
                    """,
                )
            finally:
                conn.close()
    counted = counters_for(completion, delegations, now)
    flags = honesty_flags(ledger_path, path if path.is_file() else None)
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "core_escalation_burndown",
        "read_only": True,
        "as_of": counted["as_of"],
        "windows": counted["windows"],
        "needs_matt_open": counted["needs_matt_open"],
        "undated_or_future": counted["undated_or_future"],
        "unbounded_delegations": counted["unbounded_delegations"],
        "refused_silent_clear": counted["refused_silent_clear"],
        "completion_rows": counted["completion_rows"],
        "delegation_rows": counted["delegation_rows"],
        "completion_status": counted["completion_status"],
        "delegation_status": counted["delegation_status"],
        "honesty": flags,
        "ledger_write": False,
        "alchemist_write": False,
        "production_write": False,
        "external_writes": False,
        "needs_matt_auto_cleared": False,
        "operating_test": False,
    }
