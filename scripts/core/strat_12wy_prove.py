#!/usr/bin/env python3
"""CAP-STRAT-01 12WY deterministic prove (Beta, read-only).

Extends the already-BUILT 12-Week Year cadence. Not a new system.
Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), plan
docs/deliveries/GROK-PLAN-STRAT-12WY-CAP-PROVE-2026-09-19.md.

Reads Radar/Helm bindings as they exist. Does not execute radar_board,
does not call the Wolf desk reader (that path can write tasks), and does not invent
PROVEN, tactics, or a 0% score. Honesty is bound to CR-6535f7cb02370850.
"""
from __future__ import annotations

import json
import re
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

CR_ID = "CR-6535f7cb02370850"
CAP_ID = "CAP-STRAT-01"
SCORE_LOCK_PCT = 85

WITA = timezone(timedelta(hours=8))
P1_START = date(2026, 9, 7)
P1_END = date(2026, 11, 29)
P1_BUFFER_END = date(2026, 12, 6)

RADAR_BOARD = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/radar_board.py"
)
TASKS_JSON = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/wolf-desk/tasks.json"
)
HELM_BETA = BETA_ROOT / "dashboards" / "deliveries" / "12wy-2026-09-18.html"
HELM_PROD = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/deliveries/12wy-2026-09-18.html"
)

KNOWN_READS = frozenset({RADAR_BOARD, TASKS_JSON, HELM_PROD})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
_MAX_READ = 2_000_000

_SCORE_RE = re.compile(r'class="score">\s*([A-Z]+)\s*<')
_WEEK_RE = re.compile(r"week=<b>(\d+)</b>")
_PLANNED_RE = re.compile(r"planned=<b>(\d+)</b>")
_DONE_RE = re.compile(r"done=<b>(\d+)</b>")
_LOCK_RE = re.compile(r"^SCORE_LOCK_PCT\s*=\s*(\d+)\s*$", re.MULTILINE)

HONESTY = {
    "cap": CAP_ID,
    "slice": "strat_12wy_cap_prove",
    "read_only": True,
    "prove_pack_only": True,
    "score_changed": False,
    "tactics_invented": False,
    "auto_now": False,
    "rag_invented": False,
    "wolf_public_called": False,
    "radar_executed": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "cap_strat_02_not_this_prove": True,
    "anon_fail_closed": True,
}


class ProveError(ValueError):
    """Fail closed. Does not invent a score, a tactic, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    raise ProveError(
        "12WY prove pack is read-only. Writes are refused.",
        code="writes_refused",
    )


def _guard_read(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise ProveError("12WY prove refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise ProveError("12WY prove refuses a production money path", code="not_beta")
    resolved = path.resolve()
    if resolved in {item.resolve() for item in KNOWN_READS}:
        return
    try:
        resolved.relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise ProveError(
            "12WY prove refuses a path that is not a known binding or a Beta fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise ProveError(
            "12WY prove refuses a wolf-system fixture path",
            code="not_beta",
        )


def _read_text(path: Path) -> str | None:
    _guard_read(path)
    if not path.is_file():
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _MAX_READ:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-STRAT-01 from the ledger. Does not write it."""
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
    """Read CR-6535f7cb02370850. Does not upsert, resolve, or harvest."""
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
    flags["tactics_invented"] = False
    return flags


def _as_wita(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(WITA)
    if now.tzinfo is None:
        return now.replace(tzinfo=WITA)
    return now.astimezone(WITA)


def period_clock(now: datetime | None = None) -> dict[str, Any]:
    """Period 1 week number in WITA. Same dates as radar_board.period_clock. No write."""
    day = _as_wita(now).date()
    if day < P1_START:
        return {
            "period": 1,
            "week": None,
            "phase": "before",
            "label": "Period 1 starts Mon 7 Sep 2026",
            "week_start": None,
            "week_end": None,
            "display": "P1 · starts Mon 7 Sep",
            "p1_start": P1_START.isoformat(),
            "p1_end": P1_END.isoformat(),
        }
    week_n = (day - P1_START).days // 7 + 1
    week_start = P1_START + timedelta(days=(week_n - 1) * 7)
    week_end = week_start + timedelta(days=6)
    if week_n <= 12:
        return {
            "period": 1,
            "week": week_n,
            "phase": "p1",
            "label": "Week %d of 12" % week_n,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "display": "P1 · Week %d of 12" % week_n,
            "p1_start": P1_START.isoformat(),
            "p1_end": P1_END.isoformat(),
        }
    if day <= P1_BUFFER_END:
        return {
            "period": 1,
            "week": 13,
            "phase": "buffer",
            "label": "W13 buffer to 6 Dec 2026",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "display": "P1 · W13 buffer",
            "p1_start": P1_START.isoformat(),
            "p1_end": P1_END.isoformat(),
        }
    return {
        "period": 1,
        "week": None,
        "phase": "after",
        "label": "Period 1 ended 29 Nov 2026 (W13 buffer ended 6 Dec)",
        "week_start": None,
        "week_end": None,
        "display": "P1 · ended",
        "p1_start": P1_START.isoformat(),
        "p1_end": P1_END.isoformat(),
    }


def task_is_evidenced_tactic(task: dict, week: int | None) -> bool:
    """A tactic counts only with an explicit 12WY flag and a matching week."""
    if not isinstance(task, dict) or week is None:
        return False
    kind = str(task.get("kind") or "").strip().lower()
    flagged = (
        task.get("tactic") is True
        or task.get("twelve_week") is True
        or kind in ("tactic", "12wy", "twelve_week")
    )
    if not flagged:
        return False
    raw_week = task.get("week")
    if raw_week is None:
        raw_week = task.get("period_week")
    try:
        return int(raw_week) == int(week)
    except (TypeError, ValueError):
        return False


def tactic_done_evidenced(task: dict) -> bool:
    """Done only when the Wolf status is evidenced done."""
    if not isinstance(task, dict):
        return False
    return str(task.get("status") or "").strip().lower() == "done"


def score_contract(planned: Any, done: Any) -> dict[str, Any]:
    """LOCK C. planned=0 is EMPTY, not 0%. On-track only at ≥85% evidenced."""
    if isinstance(planned, bool) or isinstance(done, bool):
        planned_n = 0
        done_n = 0
    else:
        try:
            planned_n = int(planned)
            done_n = int(done)
        except (TypeError, ValueError):
            planned_n = 0
            done_n = 0
    if planned_n < 0:
        planned_n = 0
    if done_n < 0:
        done_n = 0
    if planned_n == 0:
        return {
            "name": "weekly_score",
            "state": "EMPTY",
            "rag": None,
            "value": None,
            "percent": None,
            "planned": 0,
            "done": 0,
            "threshold": SCORE_LOCK_PCT,
            "threshold_met": None,
            "on_track": False,
            "auto_now": False,
            "tactics_invented": False,
            "why": "No evidenced planned tactics this week. EMPTY, not 0%. Score does not create NOW.",
        }
    if done_n > planned_n:
        done_n = planned_n
    percent = int(round(100.0 * done_n / planned_n))
    met = percent >= SCORE_LOCK_PCT
    return {
        "name": "weekly_score",
        "state": "WIRED",
        "rag": None,
        "value": percent,
        "percent": percent,
        "planned": planned_n,
        "done": done_n,
        "threshold": SCORE_LOCK_PCT,
        "threshold_met": met,
        "on_track": met,
        "auto_now": False,
        "tactics_invented": False,
        "why": (
            "%s/%s evidenced tactics (done/planned). ≥%s%% is the week lock. "
            "No green RAG. Score does not create NOW. Not PROVEN."
            % (done_n, planned_n, SCORE_LOCK_PCT)
        ),
    }


def score_week(tasks: list, week: int | None) -> dict[str, Any]:
    """Score only evidenced rows for this week. Does not invent rows."""
    rows = [row for row in tasks if task_is_evidenced_tactic(row, week)]
    done = sum(1 for row in rows if tactic_done_evidenced(row))
    scored = score_contract(len(rows), done)
    scored["week"] = week
    scored["tactic_ids"] = [str(row.get("id") or "") for row in rows if isinstance(row, dict)]
    return scored


def not_read_score(week: int | None, why: str) -> dict[str, Any]:
    return {
        "name": "weekly_score",
        "state": "NOT_READ",
        "rag": None,
        "value": None,
        "percent": None,
        "planned": None,
        "done": None,
        "week": week,
        "threshold": SCORE_LOCK_PCT,
        "threshold_met": None,
        "on_track": False,
        "auto_now": False,
        "tactics_invented": False,
        "tactic_ids": [],
        "why": why,
    }


def inspect_radar(radar_path: Path | str | None = None) -> dict[str, Any]:
    """Read radar_board.py as text. Does not import or execute it."""
    path = Path(radar_path) if radar_path else RADAR_BOARD
    out: dict[str, Any] = {
        "name": "radar",
        "binding": "radar_board.weekly_scorecard",
        "present": False,
        "readable": False,
        "executed": False,
        "has_weekly_scorecard": False,
        "has_score_tactics": False,
        "score_lock_pct": None,
        "lock_matches_contract": False,
        "empty_not_zero_stated": False,
        "auto_now_false_stated": False,
        "create_task_called_by_prove": False,
    }
    text = _read_text(path)
    if text is None:
        return out
    out["present"] = True
    out["readable"] = True
    out["has_weekly_scorecard"] = "def weekly_scorecard" in text
    out["has_score_tactics"] = "def score_tactics" in text
    lock = _LOCK_RE.search(text)
    if lock:
        out["score_lock_pct"] = int(lock.group(1))
    out["lock_matches_contract"] = out["score_lock_pct"] == SCORE_LOCK_PCT
    out["empty_not_zero_stated"] = "EMPTY, not 0%" in text
    out["auto_now_false_stated"] = '"auto_now": False' in text
    return out


def inspect_helm(helm_path: Path | str | None) -> dict[str, Any]:
    """Read a dated Helm coach pack. Does not treat its words as today's score."""
    path = Path(helm_path) if helm_path else HELM_BETA
    out: dict[str, Any] = {
        "name": "helm",
        "binding": "12wy coach pack",
        "present": False,
        "readable": False,
        "dated_pack": True,
        "stated_state": None,
        "stated_week": None,
        "stated_planned": None,
        "stated_done": None,
        "invented": False,
    }
    text = _read_text(path)
    if text is None:
        return out
    out["present"] = True
    out["readable"] = True
    score = _SCORE_RE.search(text)
    week = _WEEK_RE.search(text)
    planned = _PLANNED_RE.search(text)
    done = _DONE_RE.search(text)
    if score:
        out["stated_state"] = score.group(1)
    if week:
        out["stated_week"] = int(week.group(1))
    if planned:
        out["stated_planned"] = int(planned.group(1))
    if done:
        out["stated_done"] = int(done.group(1))
    return out


def _load_tasks(path: Path) -> tuple[str, list]:
    text = _read_text(path)
    if text is None:
        if path.is_file():
            return "invalid", []
        return "missing", []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return "invalid", []
    if isinstance(data, dict):
        rows = data.get("tasks")
    elif isinstance(data, list):
        rows = data
    else:
        return "invalid", []
    if not isinstance(rows, list):
        return "invalid", []
    return "readable", [row for row in rows if isinstance(row, dict)]


def build_prove(
    *,
    now: datetime | None = None,
    tasks_path: Path | str | None = None,
    radar_path: Path | str | None = None,
    helm_path: Path | str | None = None,
    helm_prod_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    read_tasks: bool = True,
) -> dict[str, Any]:
    """Owner prove pack. Writes nothing. Does not invent PROVEN or tactics."""
    clock = period_clock(now)
    week = clock.get("week")
    preview = False
    if week is None and clock.get("phase") == "before":
        week = 1
        preview = True
    radar = inspect_radar(radar_path)
    helm = inspect_helm(helm_path if helm_path is not None else HELM_BETA)
    helm_prod = inspect_helm(helm_prod_path if helm_prod_path is not None else HELM_PROD)
    task_status = "skipped"
    rows: list = []
    if read_tasks:
        path = Path(tasks_path) if tasks_path else TASKS_JSON
        task_status, rows = _load_tasks(path)
    if not read_tasks:
        score = not_read_score(week, "Live Wolf tasks were not read. Not EMPTY. Not 0%.")
    elif task_status != "readable":
        score = not_read_score(
            week,
            "Wolf tasks file was not a readable list. Not EMPTY. Not 0%. No tactics invented.",
        )
    elif radar["present"] and not radar["lock_matches_contract"]:
        score = not_read_score(
            week,
            "Radar score lock does not match 85. No percent emitted.",
        )
        score["state"] = "LOCK_MISMATCH"
    else:
        score = score_week(rows, week)
    score["preview"] = preview
    score["clock"] = clock
    if preview and score.get("state") == "WIRED":
        score["why"] = "PREVIEW W1 · " + str(score.get("why") or "")
    flags = honesty_flags(ledger_path, catalog_db)
    flags["radar_executed"] = False
    flags["wolf_public_called"] = False
    return {
        "ok": True,
        "bound": "beta-strat-12wy-cap-prove",
        "cap": CAP_ID,
        "clock": clock,
        "score": score,
        "radar": radar,
        "helm": helm,
        "helm_production_copy": helm_prod,
        "tasks": {
            "status": task_status,
            "read": task_status == "readable",
            "wolf_public_called": False,
        },
        "external_writes": False,
        "ledger_write": False,
        "production_write": False,
        "alchemist_write": False,
        "tactics_invented": False,
        "honesty": flags,
    }
