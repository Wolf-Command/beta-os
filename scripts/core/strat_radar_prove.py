#!/usr/bin/env python3
"""CAP-STRAT-02 Owner Radar prove (Beta, read-only).

Extends the already-BUILT Owner Radar. Not a new system.
Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), plan
docs/deliveries/GROK-PLAN-STRAT-RADAR-CAP-PROVE-2026-09-19.md.

Reads Owner Radar bindings as text. Does not execute radar_board, does not
write a Wolf NOW, and does not treat the Progress dashboard as this CAP.
Does not invent PROVEN. Honesty is bound to CR-7a145ad69d8bf3c5.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ADOPTION_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"
PROGRESS_HTML = BETA_ROOT / "dashboards" / "progress.html"

RADAR_HTML = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/radar.html"
)
RADAR_BOARD = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/radar_board.py"
)

CR_ID = "CR-7a145ad69d8bf3c5"
CAP_ID = "CAP-STRAT-02"
AU_ID = "AU-STRAT-02-OWNER"
SCHEMA = "wolf.cap-strat-02.owner-radar-prove.v1"

KNOWN_READS = frozenset({RADAR_HTML, RADAR_BOARD})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
STUBS = frozenset({"AMG", "BZG"})
_MAX_READ = 2_000_000

REQUIRED_TILES = (
    "tile-12wy",
    "tile-mars",
    "tile-pace",
    "tile-proof",
    "tile-atlas",
    "tile-cadence",
    "tile-bank",
    "tile-roadmap",
    "tile-retainers",
    "tile-queue",
    "tile-actions",
    "tile-assign",
    "tile-heal",
    "tile-sop",
)

# Named product bindings. A Python "except Exception" is not this capability.
PULSE_NEEDLES = ('id="tile-pulse"', 'data-actual="pulse"', "Pulse + Exceptions")
EXCEPTION_NEEDLES = (
    'id="tile-exceptions"',
    'data-actual="exceptions"',
    "Pulse + Exceptions",
)
QUIET_NEEDLE = "progressive quiet"

HONESTY = {
    "cap": CAP_ID,
    "slice": "strat_radar_cap_prove",
    "read_only": True,
    "prove_pack_only": True,
    "score_changed": False,
    "invented_pulse": False,
    "invented_exceptions": False,
    "progress_used_as_cap": False,
    "progress_dashboard_is_not_this_cap": True,
    "cap_strat_01_not_this_prove": True,
    "radar_executed": False,
    "create_task_called": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
}


class ProveError(ValueError):
    """Fail closed. Does not invent a pulse, a score, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_create_task(_body: dict | None = None) -> None:
    raise ProveError(
        "Owner Radar prove refuses a Wolf NOW write.",
        code="create_task_refused",
    )


def refuse_progress_inflate(_body: dict | None = None) -> None:
    raise ProveError(
        "Progress dashboard is not this CAP alone.",
        code="progress_not_this_cap",
    )


def refuse_score_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Owner Radar prove refuses a score or maturity write.",
        code="score_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("create_task") or payload.get("task") or action in {"task", "create_task"}:
        refuse_create_task(payload)
    if (
        payload.get("progress")
        or "system_pct" in payload
        or action == "progress"
    ):
        refuse_progress_inflate(payload)
    if payload.get("proven") or payload.get("score") or action in {"proven", "score", "ready"}:
        refuse_score_write(payload)
    raise ProveError(
        "Owner Radar prove is read-only. Writes are refused.",
        code="writes_refused",
    )


def reject_progress_as_cap(system_pct: Any) -> None:
    """A Progress system percent is not Owner Radar maturity."""
    if system_pct is None:
        return
    refuse_progress_inflate({"system_pct": system_pct})


def _guard_read(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise ProveError("Owner Radar prove refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise ProveError("Owner Radar prove refuses a production money path", code="not_beta")
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
            "Owner Radar prove refuses a path that is not a known binding or a Beta fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise ProveError(
            "Owner Radar prove refuses a wolf-system fixture path",
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
    """Read CAP-STRAT-02 from the ledger. Does not write it."""
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


def ledger_gap_text(ledger_path: Path | str | None = None) -> str | None:
    """Read the missing-for-next cell. Does not clear it."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_read(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or len(row) < 3:
        return None
    text = str(row[2] or "").strip()
    return text or None


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-7a145ad69d8bf3c5. Does not upsert, resolve, or harvest."""
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
    flags["progress_used_as_cap"] = False
    flags["invented_pulse"] = False
    flags["invented_exceptions"] = False
    return flags


def entity_surface(entity: str, numbers: Any = None) -> dict[str, Any]:
    """GGV is the live entity. AMG and BZG are stubs and have no numbers."""
    token = (entity or "").strip().upper()
    if not token:
        raise ProveError("entity is required", code="invalid")
    if token not in {"GGV", "AMG", "BZG"}:
        raise ProveError("unknown entity", code="invalid")
    if numbers not in (None, {}, []):
        if token in STUBS:
            raise ProveError(
                "%s is a stub. No numbers. No switch." % token,
                code="boundary_breach",
            )
        raise ProveError(
            "GGV numbers are not invented by this prove.",
            code="invent_refused",
        )
    if token in STUBS:
        return {
            "entity": token,
            "state": "stub",
            "numbers": None,
            "operating_board": False,
            "why": "%s is a stub. This prove does not invent numbers." % token,
        }
    return {
        "entity": "GGV",
        "state": "live",
        "numbers": None,
        "operating_board": False,
        "why": "GGV is the live Owner Radar entity. This prove does not invent a score.",
    }


def pulse_binding(html: str | None, board: str | None) -> dict[str, Any]:
    """Catalog intent is Pulse + Exceptions. Names absent are not a zero count."""
    if html is None and board is None:
        return {
            "status": "NOT_READ",
            "pulse_named": None,
            "exceptions_named": None,
            "progressive_quiet_named": None,
            "pulse_count": None,
            "exception_count": None,
            "quiet": None,
            "why": "Radar text was not read. Pulse and exceptions are not zero.",
        }
    blob = "\n".join(part for part in (html or "", board or "") if part)
    pulse_named = any(needle in blob for needle in PULSE_NEEDLES)
    exceptions_named = any(needle in blob for needle in EXCEPTION_NEEDLES)
    quiet_named = QUIET_NEEDLE in blob.lower()
    if pulse_named and exceptions_named:
        status = "NAMED"
        why = (
            "Pulse and Exceptions are named in the binding text. "
            "Counts are not invented. A name is not progressive quiet."
        )
    else:
        status = "ABSENT"
        why = (
            "Catalog intent is Pulse + Exceptions. Those names are not on the Owner Radar text. "
            "Counts are not invented. A Python exception handler is not this binding."
        )
    return {
        "status": status,
        "pulse_named": pulse_named,
        "exceptions_named": exceptions_named,
        "progressive_quiet_named": quiet_named,
        "pulse_count": None,
        "exception_count": None,
        "quiet": False,
        "why": why,
    }


def birdseye(html: str | None, pulse: dict[str, Any]) -> dict[str, Any]:
    """Tiles are the bird's-eye board. Satisfied is not claimed from Progress."""
    if html is None:
        return {
            "status": "NOT_READ",
            "tiles": None,
            "tile_count": None,
            "missing": None,
            "satisfied": None,
            "quiet": None,
            "until_satisfied": None,
            "why": "Radar page was not read. Missing tiles are not zero.",
        }
    found = [tile for tile in REQUIRED_TILES if 'id="%s"' % tile in html]
    missing = [tile for tile in REQUIRED_TILES if tile not in found]
    named = pulse.get("status") == "NAMED" and pulse.get("progressive_quiet_named") is True
    satisfied = not missing and named
    return {
        "status": "READ",
        "tiles": found,
        "tile_count": len(found),
        "missing": missing,
        "satisfied": satisfied,
        "quiet": False,
        "until_satisfied": not satisfied,
        "why": (
            "Bird's-eye tiles are the Owner board. Satisfied stays false until Pulse, "
            "Exceptions, and progressive quiet are named. Progress does not satisfy this."
        ),
    }


def mission_control_binding(html: str | None, board: str | None) -> dict[str, Any]:
    """A comment alias is not a second Mission Control board."""
    if html is None and board is None:
        return {
            "status": "NOT_READ",
            "separate_board": False,
            "title_present": None,
            "mentioned": None,
            "why": "Radar text was not read. Mission Control was not invented.",
        }
    title_present = bool(html and ("<h1>Mission Control" in html or "<title>Mission Control" in html))
    mentioned = bool(board and "Mission Control" in board)
    if title_present:
        status = "PRESENT"
        why = "A Mission Control title is on the page. This prove still does not raise maturity."
    elif mentioned:
        status = "ALIAS"
        why = (
            "Mission Control is named in Radar comments. It is not a separate board. "
            "The live surface is Wolf Radar."
        )
    else:
        status = "ABSENT"
        why = "Mission Control is not a titled surface. This prove does not invent one."
    return {
        "status": status,
        "separate_board": title_present,
        "title_present": title_present,
        "mentioned": mentioned,
        "why": why,
    }


def inspect_radar(
    radar_html: Path | str | None = None,
    radar_board: Path | str | None = None,
) -> dict[str, Any]:
    """Read radar.html and radar_board.py as text. Does not import or execute them."""
    html_path = Path(radar_html) if radar_html else RADAR_HTML
    board_path = Path(radar_board) if radar_board else RADAR_BOARD
    html = _read_text(html_path)
    board = _read_text(board_path)
    pulse = pulse_binding(html, board)
    return {
        "html": {
            "present": html is not None,
            "executed": False,
            "owner_plan_board": bool(html and "Owner plan board" in html),
            "never_invent_stated": bool(html and "Never invent. Never paint RAG green." in html),
            "ggv_live": bool(html and 'data-entity="GGV"' in html),
            "amg_stub": bool(html and 'class="stub" data-entity="AMG"' in html),
            "bzg_stub": bool(html and 'class="stub" data-entity="BZG"' in html),
            "progress_strip_present": bool(html and "plan-progress-strip" in html),
            "progress_strip_is_this_cap": False,
            "now_write_path_present": bool(html and "/api/radar/task" in html),
            "now_write_called_by_prove": False,
        },
        "board": {
            "present": board is not None,
            "executed": False,
            "has_public": bool(board and "def public(" in board),
            "read_only_stated": bool(board and "Must never write tasks.json." in board),
            "has_create_task": bool(board and "def create_task(" in board),
            "create_task_called_by_prove": False,
            "learn_mode": bool(board and 'MODE = "LEARN"' in board),
            "vesper_amber": bool(board and 'VESPER = "AMBER"' in board),
            "never_invent_stated": bool(
                board and "Never invent metrics, never paint RAG green" in board
            ),
            "auto_now_false_stated": bool(board and '"auto_now": False' in board),
            "post_radar_405_stated": bool(board and "POST /api/radar stays 405" in board),
            "posts": False,
        },
        "pulse": pulse,
        "birdseye": birdseye(html, pulse),
        "mission_control": mission_control_binding(html, board),
    }


def inspect_progress(progress_path: Path | str | None = None) -> dict[str, Any]:
    """The Progress page is adjacent. Its percent is not copied and is not this CAP."""
    path = Path(progress_path) if progress_path else PROGRESS_HTML
    text = _read_text(path)
    return {
        "name": "progress_dashboard",
        "present": text is not None,
        "titled": bool(text and "Wolf · Progress" in text),
        "this_cap": False,
        "used_as_maturity": False,
        "system_pct": None,
        "why": (
            "Progress dashboard is adjacent. It is not CAP-STRAT-02 alone. "
            "No system percent is copied here."
        ),
    }


def read_adoption(path: Path | str | None = None) -> dict[str, Any]:
    """Read AU-STRAT-02-OWNER. Does not write the discovery file."""
    out: dict[str, Any] = {
        "au_id": AU_ID,
        "present": False,
        "state": None,
        "status": "NOT_READ",
        "why": "Adoption unit was not read. That is not NOT STARTED and not ADOPTED.",
    }
    target = Path(path) if path else ADOPTION_JSON
    text = _read_text(target)
    if text is None:
        return out
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return out
    rows = data if isinstance(data, list) else None
    if not isinstance(rows, list) and isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                rows = value
                break
    if not isinstance(rows, list):
        return out
    for row in rows:
        if isinstance(row, dict) and row.get("au_id") == AU_ID:
            state = str(row.get("state") or "").strip() or None
            out["present"] = True
            out["state"] = state
            out["status"] = "READ"
            out["why"] = (
                "Model E unit was read. This prove does not commission it and does not mark it ADOPTED."
            )
            return out
    out["status"] = "ABSENT"
    out["why"] = "Adoption file was read and AU-STRAT-02-OWNER was not in it."
    return out


def _gap(gap_id: str, status: str, why: str) -> dict[str, Any]:
    return {
        "id": gap_id,
        "status": status,
        "blocks_proven": True,
        "why": why,
    }


def document_gaps(
    surfaces: dict[str, Any],
    progress: dict[str, Any],
    adoption: dict[str, Any],
    ledger_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Honest gaps. Each one still blocks a higher maturity. None is cleared here."""
    pulse = surfaces.get("pulse") or {}
    bird = surfaces.get("birdseye") or {}
    mission = surfaces.get("mission_control") or {}
    board = surfaces.get("board") or {}
    return [
        _gap(
            "pulse_exceptions",
            str(pulse.get("status") or "NOT_READ"),
            str(pulse.get("why") or ""),
        ),
        _gap(
            "progressive_quiet",
            "NAMED" if pulse.get("progressive_quiet_named") else (
                "NOT_READ" if pulse.get("status") == "NOT_READ" else "NOT_NAMED"
            ),
            "Progressive quiet is not evidenced. A Progress page is not quiet.",
        ),
        _gap(
            "birdseye",
            "UNTIL_SATISFIED" if bird.get("until_satisfied") else (
                "NOT_READ" if bird.get("status") == "NOT_READ" else "READ"
            ),
            str(bird.get("why") or ""),
        ),
        _gap(
            "mission_control",
            str(mission.get("status") or "NOT_READ"),
            str(mission.get("why") or ""),
        ),
        _gap(
            "progress_dashboard",
            "NOT_THIS_CAP",
            str(progress.get("why") or ""),
        ),
        _gap(
            "create_task",
            "NOT_CALLED" if board.get("has_create_task") else "ABSENT",
            "The Wolf NOW write path is not called. This prove does not create a task.",
        ),
        _gap(
            "stub_entities",
            "STUB",
            "AMG and BZG stay stubs. This prove does not invent numbers for them.",
        ),
        _gap(
            "model_e_au",
            str(adoption.get("state") or adoption.get("status") or "NOT_READ"),
            str(adoption.get("why") or ""),
        ),
        _gap(
            "ledger_gap_text",
            "UNCLEARED",
            "The ledger missing-for-next cell is left as read: "
            + (ledger_gap_text(ledger_path) or "unread")
            + ". This pack does not edit it.",
        ),
        _gap(
            "cap_strat_01",
            "NOT_THIS_PROVE",
            "12-Week Year cadence is CAP-STRAT-01. It is not proved here.",
        ),
    ]


def build_prove(
    *,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
    radar_html: Path | str | None = None,
    radar_board: Path | str | None = None,
    progress_path: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read. No write, no executed Radar, no Progress percent, no invented pulse."""
    flags = honesty_flags(ledger_path, catalog_db)
    surfaces = inspect_radar(radar_html, radar_board)
    progress = inspect_progress(progress_path)
    adoption = read_adoption(adoption_path)
    gaps = document_gaps(surfaces, progress, adoption, ledger_path)
    ggv = entity_surface("GGV")
    return {
        "ok": True,
        "schema": SCHEMA,
        "cap": CAP_ID,
        "honesty": flags,
        "entities": {
            "ggv": ggv,
            "amg": entity_surface("AMG"),
            "bzg": entity_surface("BZG"),
        },
        "surfaces": surfaces,
        "progress": progress,
        "adoption": adoption,
        "gaps": gaps,
        "writes": {
            "create_task": False,
            "progress": False,
            "ledger": False,
            "cr": False,
            "external": False,
        },
    }
