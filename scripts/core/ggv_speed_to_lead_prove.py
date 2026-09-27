#!/usr/bin/env python3
"""CAP-GGV-04 speed-to-lead bound prove (Beta, read-only).

Extends the already-BUILT Lead Triage capability. Not a new system.
Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), plan
docs/deliveries/GROK-PLAN-GGV-SPEED-TO-LEAD-CAP-PROVE-2026-09-19.md.

Red-teams Habitat speed-to-lead as it exists. Does not ingest, does not
call the Klaviyo reader, does not write Metricool or ActiveCampaign, and
does not invent a lead, a first-touch receipt, an SLA, or PROVEN.
Honesty is bound to CR-f089b11530ab4673. The change request is not resolved.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEAD_SPINE = BETA_ROOT / "scripts" / "core" / "lead_spine.py"
KLAVIYO_READER = BETA_ROOT / "scripts" / "core" / "habitat_klaviyo_reader.py"
AC_READER = BETA_ROOT / "scripts" / "core" / "activecampaign_reader.py"
HABITAT_PAGE = BETA_ROOT / "dashboards" / "lead-spine.html"
ADOPTION_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"

CR_ID = "CR-f089b11530ab4673"
CAP_ID = "CAP-GGV-04"
AU_ID = "AU-GGV-04-HABITAT"
HABITAT = "habitat"
IVY = "ivy"
SCHEMA = "wolf.cap-ggv-04.speed-to-lead-prove.v1"
GAP_TEXT = "Governed speed-to-lead capability with tests/red-team"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
_MAX_READ = 2_000_000

HONESTY = {
    "cap": CAP_ID,
    "slice": "ggv_speed_to_lead_cap_prove",
    "read_only": True,
    "prove_pack_only": True,
    "habitat_scope_only": True,
    "invented_leads": False,
    "invented_receipts": False,
    "invented_sla": False,
    "invented_proven": False,
    "closed_is_not_a_sale": True,
    "score_changed": False,
    "klaviyo_write": False,
    "klaviyo_called": False,
    "metricool_write": False,
    "activecampaign_write": False,
    "activecampaign_called": False,
    "external_crm_write": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "cap_ggv_05_not_this_prove": True,
    "triage_board_executed": False,
    "anon_fail_closed": True,
}


class ProveError(ValueError):
    """Fail closed. Does not invent a lead, a receipt, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_klaviyo_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses a Klaviyo write. The reader is not called.",
        code="klaviyo_write_refused",
    )


def refuse_metricool_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses a Metricool write.",
        code="metricool_write_refused",
    )


def refuse_activecampaign_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses an ActiveCampaign write. ActiveCampaign is not called.",
        code="activecampaign_write_refused",
    )


def refuse_external_crm_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses an external CRM write.",
        code="external_crm_write_refused",
    )


def refuse_invent_lead(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses an invented lead.",
        code="invent_lead_refused",
    )


def refuse_invent_receipt(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses an invented first-touch receipt.",
        code="invent_receipt_refused",
    )


def refuse_score_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Speed-to-lead prove refuses a score or maturity write.",
        code="score_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("klaviyo") or payload.get("klaviyo_write") or action == "klaviyo":
        refuse_klaviyo_write(payload)
    if payload.get("metricool") or payload.get("metricool_write") or action == "metricool":
        refuse_metricool_write(payload)
    if (
        payload.get("activecampaign")
        or payload.get("activecampaign_write")
        or action in {"activecampaign", "ac", "ac_write"}
    ):
        refuse_activecampaign_write(payload)
    if (
        payload.get("external_crm")
        or payload.get("crm_write")
        or action in {"crm", "external_crm"}
    ):
        refuse_external_crm_write(payload)
    if (
        payload.get("invent_receipt")
        or payload.get("receipt")
        or action in {"receipt", "receipts", "touch"}
    ):
        refuse_invent_receipt(payload)
    if (
        payload.get("invent")
        or payload.get("invent_lead")
        or payload.get("lead")
        or action in {"lead", "leads", "invent", "ingest"}
    ):
        refuse_invent_lead(payload)
    if payload.get("proven") or payload.get("score") or payload.get("ready") or action in {
        "proven",
        "score",
        "ready",
    }:
        refuse_score_write(payload)
    raise ProveError(
        "Speed-to-lead prove is read-only. Writes are refused.",
        code="writes_refused",
    )


def _caught(payload: dict, expect: str) -> tuple[bool, str | None]:
    try:
        refuse_external_write(payload)
    except ProveError as exc:
        return exc.code == expect, exc.code
    return False, None


def red_team_table() -> list[dict[str, Any]]:
    """Exercise the refusals. Anonymous 403 is a gate contract, not a socket."""
    proven_ok, proven_code = _caught({"proven": True}, "score_refused")
    ready_ok, ready_code = _caught({"ready": True}, "score_refused")
    leads_ok, leads_code = _caught({"invent_lead": True}, "invent_lead_refused")
    receipt_ok, receipt_code = _caught({"invent_receipt": True}, "invent_receipt_refused")
    locks = []
    lock_ok = True
    for payload, code in (
        ({"metricool": True}, "metricool_write_refused"),
        ({"klaviyo": True}, "klaviyo_write_refused"),
        ({"activecampaign": True}, "activecampaign_write_refused"),
        ({"external_crm": True}, "external_crm_write_refused"),
    ):
        ok, got = _caught(payload, code)
        locks.append({"expected": code, "got": got, "refused": ok})
        lock_ok = lock_ok and ok
    rows = [
        {
            "id": "invent_proven",
            "result": "REFUSED" if proven_ok and ready_ok else "FAIL",
            "code": proven_code,
            "ready_code": ready_code,
            "why": "A request to raise maturity is refused. The ledger is not written.",
        },
        {
            "id": "invent_leads",
            "result": "REFUSED" if leads_ok else "FAIL",
            "code": leads_code,
            "why": "An empty brand read stays empty. A missing brand is not an invented lead.",
        },
        {
            "id": "invent_receipts",
            "result": "REFUSED" if receipt_ok else "FAIL",
            "code": receipt_code,
            "why": "A missing first touch stays absent. No receipt timestamp is written.",
        },
        {
            "id": "write_locks",
            "result": "REFUSED" if lock_ok else "FAIL",
            "locks": locks,
            "why": "Metricool, Klaviyo, ActiveCampaign, and external CRM writes are refused.",
        },
        {
            "id": "anon_403",
            "result": "FAIL_CLOSED",
            "code": "forbidden",
            "exercised_in_module": False,
            "why": (
                "Anonymous and staff requests are 403 on the Beta gate. "
                "This module does not open a port and does not grant access."
            ),
        },
    ]
    bad = [row["id"] for row in rows if row["result"] not in {"REFUSED", "FAIL_CLOSED"}]
    if bad:
        raise ProveError(
            "red-team table failed: " + ", ".join(bad),
            code="red_team_failed",
        )
    return rows


def _guard_read(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise ProveError("Speed-to-lead prove refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise ProveError("Speed-to-lead prove refuses a production money path", code="not_beta")
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
        raise ProveError(
            "Speed-to-lead prove refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise ProveError("Speed-to-lead prove refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-GGV-04 from the ledger. Does not write it."""
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


def ledger_row_count(ledger_path: Path | str | None = None) -> int | None:
    """Count ledger rows. Does not add or remove one."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_read(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return len(data)


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
    """Read CR-f089b11530ab4673. Does not upsert, resolve, or harvest."""
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
    flags["ledger_rows"] = ledger_row_count(ledger_path)
    flags["ledger_gap"] = ledger_gap_text(ledger_path)
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["score_changed"] = False
    return flags


def _blank() -> dict[str, Any]:
    return {
        "status": "NOT_READ",
        "brand_id": HABITAT,
        "rows": None,
        "waiting": None,
        "measured": None,
        "unavailable": None,
        "receipt_present": None,
        "receipt_absent": None,
        "receipt_unreadable": None,
        "receipts_invented": 0,
        "leads_invented": False,
        "sla_target_seconds": None,
        "sla_breached": None,
        "sales": None,
        "closed": None,
        "demo": None,
        "not_demo": None,
        "empty": None,
        "operating_board": False,
        "boundary": "NOT_READ",
        "why": "Habitat leads were not read. Absence is not zero and not an invented lead or receipt.",
    }


def _is_demo(row: dict[str, Any]) -> bool:
    if row.get("demo") is True:
        return True
    raw = row.get("provenance_json")
    if isinstance(raw, str):
        compact = raw.replace(" ", "")
        return '"demo":true' in compact
    return False


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def _parse_ts(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _bucket(row: dict[str, Any], clock: datetime) -> tuple[str, str]:
    """Speed status and receipt status from timestamps already on the row.

    A missing touch is ABSENT. This function does not fill one in.
    """
    observed = _parse_ts(str(row.get("source_observed_at") or ""))
    touch_raw = str(row.get("first_human_touch_at") or "").strip()
    touch = _parse_ts(touch_raw) if touch_raw else None
    if touch_raw and touch is None:
        receipt = "UNREADABLE"
    elif touch is None:
        receipt = "ABSENT"
    else:
        receipt = "PRESENT"
    if observed is None:
        return "UNAVAILABLE", receipt
    if receipt != "PRESENT":
        if receipt == "ABSENT":
            if (clock - observed).total_seconds() < 0:
                return "UNAVAILABLE", receipt
            return "WAITING", receipt
        return "UNAVAILABLE", receipt
    if touch is None or (touch - observed).total_seconds() < 0:
        return "UNAVAILABLE", receipt
    return "MEASURED", receipt


def classify_speed(
    rows: list[dict[str, Any]] | None,
    *,
    brand_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pure red-team. None means unread. Habitat only.

    Does not mutate rows. Does not invent a lead, a receipt, or an SLA.
    Closed is counted and is not a sale.
    """
    bid = (brand_id or "").strip().lower()
    if bid != HABITAT:
        raise ProveError(
            "Speed-to-lead prove is Habitat scope only.",
            code="not_habitat",
        )
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ProveError("now must be timezone-aware", code="invalid")
    if rows is None:
        return _blank()
    waiting = measured = unavailable = 0
    present = absent = unreadable = 0
    closed = demo = not_demo = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ProveError("lead row must be an object", code="invalid")
        if row.get("invented_receipt") or row.get("receipt_invented"):
            raise ProveError(
                "A row marked as an invented receipt is refused.",
                code="invent_receipt_refused",
            )
        if row.get("sla_target_seconds") not in (None, ""):
            raise ProveError(
                "An SLA target on a lead row is refused. No SLA is invented.",
                code="invent_sla_refused",
            )
        row_brand = str(row.get("brand_id") or "").strip().lower()
        if row_brand != HABITAT:
            raise ProveError(
                "client-data boundary breached: row brand is not Habitat",
                code="boundary_breach",
            )
        if not _present(row.get("entity_id")):
            raise ProveError(
                "client-data boundary breached: entity_id required",
                code="boundary_breach",
            )
        speed, receipt = _bucket(row, clock)
        if speed == "WAITING":
            waiting += 1
        elif speed == "MEASURED":
            measured += 1
        else:
            unavailable += 1
        if receipt == "PRESENT":
            present += 1
        elif receipt == "UNREADABLE":
            unreadable += 1
        else:
            absent += 1
        if str(row.get("wolf_stage") or "").strip().upper() == "CLOSED":
            closed += 1
        if _is_demo(row):
            demo += 1
        else:
            not_demo += 1
    count = len(rows)
    demo_only = count > 0 and demo == count
    if count == 0:
        why = "No Habitat rows. Empty is not an invented lead and not an invented receipt."
    elif demo_only:
        why = "Every Habitat row read is a demo fixture. That is not a live operating board."
    else:
        why = "Habitat rows were read. A non-demo row is not commissioning and is not a higher maturity."
    return {
        "status": "READ",
        "brand_id": HABITAT,
        "rows": count,
        "waiting": waiting,
        "measured": measured,
        "unavailable": unavailable,
        "receipt_present": present,
        "receipt_absent": absent,
        "receipt_unreadable": unreadable,
        "receipts_invented": 0,
        "leads_invented": False,
        "sla_target_seconds": None,
        "sla_breached": None,
        "sales": None,
        "closed": closed,
        "demo": demo,
        "not_demo": not_demo,
        "empty": count == 0,
        "operating_board": False,
        "boundary": "HELD",
        "why": why,
    }


def _ro(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    _guard_read(path)
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def read_habitat_rows(catalog_db: Path | str | None) -> list[dict[str, Any]] | None:
    """Habitat-filtered read. No email, no source id, no provenance blob.

    None means the table was not read. An empty list means the table was
    read and Habitat had no rows. Timestamps stay on the row for classification
    and are not copied into the Owner pack.
    """
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    conn = _ro(path)
    if conn is None:
        return None
    try:
        if not _table_exists(conn, "core_leads"):
            return None
        fetched = conn.execute(
            """
            SELECT entity_id, brand_id,
                   source_observed_at, first_human_touch_at,
                   wolf_stage,
                   CASE
                     WHEN provenance_json LIKE '%"demo": true%'
                       OR provenance_json LIKE '%"demo":true%'
                     THEN 1 ELSE 0
                   END AS demo_flag
            FROM core_leads
            WHERE lower(brand_id)=?
            """,
            (HABITAT,),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    rows: list[dict[str, Any]] = []
    for item in fetched:
        rows.append(
            {
                "entity_id": item[0],
                "brand_id": item[1],
                "source_observed_at": item[2],
                "first_human_touch_at": item[3],
                "wolf_stage": item[4],
                "demo": bool(item[5]),
            }
        )
    return rows


def brand_count(catalog_db: Path | str | None, brand_id: str) -> int | None:
    """None if unread. A zero count is not shown as a board."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    conn = _ro(path)
    if conn is None:
        return None
    try:
        if not _table_exists(conn, "core_leads"):
            return None
        row = conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE lower(brand_id)=?",
            (brand_id.strip().lower(),),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None:
        return None
    return int(row[0])


def ivy_surface(count: int | None) -> dict[str, Any]:
    """Ledger names Ivy. No rows is ABSENT, not zero, not a Habitat lead."""
    if count is None:
        return {
            "brand_id": IVY,
            "status": "NOT_READ",
            "rows": None,
            "operating_board": False,
            "why": "Ivy leads were not read. Absence is not zero.",
        }
    if count == 0:
        return {
            "brand_id": IVY,
            "status": "ABSENT",
            "rows": None,
            "operating_board": False,
            "why": (
                "Ledger evidence names Ivy stale leads. Beta core_leads has no ivy rows. "
                "ABSENT is not zero and not an invented lead."
            ),
        }
    return {
        "brand_id": IVY,
        "status": "PRESENT",
        "rows": count,
        "operating_board": False,
        "why": "Ivy rows exist. This prove is Habitat scope and does not score them.",
    }


def _read_text(path: Path) -> str | None:
    _guard_read(path)
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > _MAX_READ:
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def inspect_surfaces(
    spine_path: Path | str | None = None,
    reader_path: Path | str | None = None,
    ac_path: Path | str | None = None,
    page_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read source text. Does not import readers and does not run triage."""
    spine = _read_text(Path(spine_path) if spine_path else LEAD_SPINE)
    reader = _read_text(Path(reader_path) if reader_path else KLAVIYO_READER)
    page = _read_text(Path(page_path) if page_path else HABITAT_PAGE)
    ac_file = Path(ac_path) if ac_path else AC_READER
    _guard_read(ac_file)
    return {
        "lead_spine": {
            "present": spine is not None,
            "executed": False,
            "never_invent_lead_stated": bool(spine and "never invent a lead" in spine),
            "never_inserts_lead_stated": bool(spine and "Never inserts a lead" in spine),
            "sla_not_invented_stated": bool(spine and "Never invents an SLA target" in spine),
            "receipt_clock_stated": bool(
                spine and "not the speed-to-lead receipt clock" in spine
            ),
            "maturity_built_stated": bool(spine and '"maturity": "BUILT"' in spine),
            "proven_false_stated": bool(spine and '"proven": False' in spine),
        },
        "klaviyo_reader": {
            "present": reader is not None,
            "write_path_present": bool(reader and "def run_ingest" in reader),
            "called_by_prove": False,
            "network_called": False,
        },
        "activecampaign_reader": {
            "present": ac_file.is_file(),
            "called_by_prove": False,
            "network_called": False,
        },
        "habitat_page": {
            "present": page is not None,
            "demo_stated": bool(page and "Demo data" in page),
            "closed_not_sale_stated": bool(page and "not a sale" in page),
            "sla_not_invented_stated": bool(page and "No SLA number is invented" in page),
        },
        "metricool_write": False,
        "triage_board_executed": False,
    }


def read_adoption(path: Path | str | None = None) -> dict[str, Any]:
    """Read AU-GGV-04-HABITAT. Does not write the discovery file."""
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
    out["why"] = "Adoption file was read and AU-GGV-04-HABITAT was not in it. Absence is not ADOPTED."
    return out


def _gap(gap_id: str, status: str, why: str) -> dict[str, Any]:
    return {
        "id": gap_id,
        "status": status,
        "blocks_proven": True,
        "why": why,
    }


def document_gaps(
    habitat: dict[str, Any],
    ivy: dict[str, Any],
    surfaces: dict[str, Any],
    adoption: dict[str, Any],
    ledger_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Honest gaps. Each one still blocks a higher maturity. None is cleared here."""
    if habitat.get("status") != "READ":
        board = "NOT_READ"
    elif habitat.get("demo") and habitat.get("demo") == habitat.get("rows"):
        board = "DEMO"
    else:
        board = "NOT_COMMISSIONED"
    ac = (surfaces.get("activecampaign_reader") or {}).get("present")
    return [
        _gap(
            "ivy_surface",
            str(ivy.get("status") or "NOT_READ"),
            str(ivy.get("why") or ""),
        ),
        _gap(
            "habitat_operating_board",
            board,
            "Demo fixtures and an uncommissioned board are not a live Habitat speed-to-lead board.",
        ),
        _gap(
            "first_touch_receipts",
            "NOT_INVENTED",
            "A missing first touch stays absent. This pack writes no receipt.",
        ),
        _gap(
            "klaviyo_write",
            "NOT_CALLED",
            "The Klaviyo reader has a write path. This prove does not call it and does not open the network.",
        ),
        _gap(
            "activecampaign_write",
            "ABSENT" if not ac else "NOT_CALLED",
            "ActiveCampaign is not Klaviyo. The reader is not called. A write is refused.",
        ),
        _gap(
            "metricool_write",
            "REFUSED",
            "Metricool write is refused. Brand social performance is not this CAP.",
        ),
        _gap(
            "external_crm_write",
            "REFUSED",
            "External CRM write is refused.",
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
            "change_request",
            "OPEN_UNLESS_ALREADY_RESOLVED",
            "This slice does not resolve "
            + CR_ID
            + ". Next action stays the ledger gap unless a real product exit already closed it.",
        ),
    ]


def build_prove(
    *,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
    spine_path: Path | str | None = None,
    reader_path: Path | str | None = None,
    ac_path: Path | str | None = None,
    page_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Owner read. No write, no ingest, no invented lead, no invented receipt."""
    flags = honesty_flags(ledger_path, catalog_db)
    habitat_rows = read_habitat_rows(catalog_db)
    habitat = classify_speed(habitat_rows, brand_id=HABITAT, now=now)
    ivy = ivy_surface(brand_count(catalog_db, IVY))
    surfaces = inspect_surfaces(spine_path, reader_path, ac_path, page_path)
    adoption = read_adoption(adoption_path)
    gaps = document_gaps(habitat, ivy, surfaces, adoption, ledger_path)
    table = red_team_table()
    return {
        "ok": True,
        "schema": SCHEMA,
        "cap": CAP_ID,
        "honesty": flags,
        "habitat": habitat,
        "ivy": ivy,
        "surfaces": surfaces,
        "adoption": adoption,
        "red_team": table,
        "gaps": gaps,
        "writes": {
            "klaviyo": False,
            "metricool": False,
            "activecampaign": False,
            "external_crm": False,
            "invented_leads": False,
            "invented_receipts": False,
            "ledger": False,
            "cr": False,
        },
    }


def _speed_counts(rows: list[dict[str, Any]], clock: datetime) -> dict[str, Any]:
    """Bucket timestamps already on the rows. Does not fill a missing touch."""
    waiting = measured = unavailable = 0
    present = absent = unreadable = 0
    for row in rows:
        speed, receipt = _bucket(row, clock)
        if speed == "WAITING":
            waiting += 1
        elif speed == "MEASURED":
            measured += 1
        else:
            unavailable += 1
        if receipt == "PRESENT":
            present += 1
        elif receipt == "UNREADABLE":
            unreadable += 1
        else:
            absent += 1
    return {
        "status": "READ",
        "rows": len(rows),
        "waiting": waiting,
        "measured": measured,
        "unavailable": unavailable,
        "receipt_present": present,
        "receipt_absent": absent,
        "receipt_unreadable": unreadable,
        "empty": len(rows) == 0,
    }


def _group_counts(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        token = str(row.get(key) or "")
        counts[token] = counts.get(token, 0) + 1
    return [{key: token, "rows": counts[token]} for token in sorted(counts)]


def read_stored_leads(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read leads already in core_leads. Writes nothing and creates no person.

    Demo rows stay out of the operational counts. A demo row is not an
    operating board. No SLA, sale, or lead is invented. CAP-CRM-01 is a
    different row. The ledger stays unread for writes.
    """
    flags = honesty_flags(ledger_path, catalog_db)
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ProveError("now must be timezone-aware", code="invalid")
    base: dict[str, Any] = {
        "ok": False,
        "cap": CAP_ID,
        "read": "stored_leads",
        "data_lane": "UNKNOWN",
        "lane_column": False,
        "stored_rows": "UNKNOWN",
        "demo_rows": "UNKNOWN",
        "operational_rows": "UNKNOWN",
        "demo_counted_as_operational": False,
        "leads_created": 0,
        "persons_created": 0,
        "persons_stored": "UNKNOWN",
        "person_id_listed": False,
        "operating_board": False,
        "proved": False,
        "current": False,
        "sla_target_seconds": None,
        "sla_breached": None,
        "sales": None,
        "closed_is_not_a_sale": True,
        "closed_rows": "UNKNOWN",
        "receipts_invented": 0,
        "leads_invented": False,
        "owner_set_rows": "UNKNOWN",
        "owner_matches_stored_person": "UNKNOWN",
        "work_item_set_rows": "UNKNOWN",
        "event_rows": "UNKNOWN",
        "crm_cap": "CAP-CRM-01",
        "crm_tested_here": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "catalog_write": False,
        "ledger_write": False,
        "klaviyo_called": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "activecampaign_called": False,
        "activecampaign_write": False,
        "external_crm_write": False,
        "payment_executed": False,
        "esb_write": False,
        "cr_resolved": False,
        "honesty": flags,
        "why": "Stored leads were not read. Absence is not zero and not an invented lead.",
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    _guard_read(path)
    conn = _ro(path)
    if conn is None:
        return base
    try:
        if not _table_exists(conn, "core_leads"):
            return base
        fetched = conn.execute(
            """
            SELECT entity_id, brand_id, source_system,
                   source_observed_at, first_human_touch_at,
                   wolf_stage, source_stage, conversion_status,
                   CASE
                     WHEN owner_person_id IS NOT NULL AND length(trim(owner_person_id)) > 0
                     THEN 1 ELSE 0
                   END,
                   CASE
                     WHEN current_work_item_id IS NOT NULL
                      AND length(trim(current_work_item_id)) > 0
                     THEN 1 ELSE 0
                   END,
                   CASE
                     WHEN provenance_json LIKE '%"demo": true%'
                       OR provenance_json LIKE '%"demo":true%'
                     THEN 1 ELSE 0
                   END
            FROM core_leads
            """
        ).fetchall()
        event_rows: list[tuple] = []
        event_lead_count = None
        if _table_exists(conn, "core_lead_events"):
            event_rows = conn.execute(
                """
                SELECT event_type, COUNT(*)
                FROM core_lead_events
                GROUP BY event_type
                ORDER BY event_type
                """
            ).fetchall()
            event_lead_count = conn.execute(
                "SELECT COUNT(DISTINCT lead_id) FROM core_lead_events"
            ).fetchone()
        persons_stored: int | str = "UNKNOWN"
        owner_matches: int | str = "UNKNOWN"
        if _table_exists(conn, "org_persons"):
            persons_stored = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
            owner_matches = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM core_leads AS lead
                    WHERE lead.owner_person_id IS NOT NULL
                      AND length(trim(lead.owner_person_id)) > 0
                      AND EXISTS (
                        SELECT 1 FROM org_persons AS person
                        WHERE person.person_id = lead.owner_person_id
                      )
                    """
                ).fetchone()[0]
            )
    except sqlite3.Error:
        return base
    finally:
        conn.close()

    stored: list[dict[str, Any]] = []
    for item in fetched:
        stored.append(
            {
                "entity_id": item[0],
                "brand_id": item[1],
                "source_system": item[2] or "",
                "source_observed_at": item[3],
                "first_human_touch_at": item[4],
                "wolf_stage": item[5] or "",
                "source_stage": item[6] or "",
                "conversion_status": item[7] or "",
                "owner_set": bool(item[8]),
                "work_item_set": bool(item[9]),
                "demo": bool(item[10]),
            }
        )
    demo_rows = [row for row in stored if row["demo"]]
    operational_rows = [row for row in stored if not row["demo"]]
    stored_speed = _speed_counts(stored, clock)
    operational_speed = _speed_counts(operational_rows, clock)
    brand_counts: dict[str, dict[str, int]] = {}
    for row in stored:
        brand = str(row["brand_id"] or "")
        slot = brand_counts.setdefault(brand, {"rows": 0, "demo": 0, "operational": 0})
        slot["rows"] += 1
        if row["demo"]:
            slot["demo"] += 1
        else:
            slot["operational"] += 1
    brands = [
        {"brand_id": brand, **brand_counts[brand]}
        for brand in sorted(brand_counts)
    ]
    if not stored:
        why = "No stored leads. Empty is not an invented lead and not an operating board."
    elif len(demo_rows) == len(stored):
        why = (
            "Every stored lead is a demo fixture. Operational speed-to-lead is empty. "
            "Empty is not an invented lead and not an operating board."
        )
    else:
        why = (
            "Stored leads were read. A non-demo row is not commissioning and is not a higher maturity."
        )
    report = dict(base)
    report.update(
        {
            "ok": True,
            "stored_rows": len(stored),
            "demo_rows": len(demo_rows),
            "operational_rows": len(operational_rows),
            "persons_stored": persons_stored,
            "closed_rows": sum(1 for row in stored if str(row["wolf_stage"]).upper() == "CLOSED"),
            "stored_speed": stored_speed,
            "operational_speed": operational_speed,
            "brands": brands,
            "other_brand_rows": sum(1 for row in stored if str(row["brand_id"] or "").strip().lower() != HABITAT),
            "source_systems": _group_counts(stored, "source_system"),
            "wolf_stages": _group_counts(stored, "wolf_stage"),
            "source_stages": _group_counts(stored, "source_stage"),
            "conversion_statuses": _group_counts(stored, "conversion_status"),
            "owner_set_rows": sum(1 for row in stored if row["owner_set"]),
            "owner_matches_stored_person": owner_matches,
            "work_item_set_rows": sum(1 for row in stored if row["work_item_set"]),
            "events": [
                {"event_type": row[0] or "", "rows": int(row[1])}
                for row in event_rows
            ],
            "event_rows": sum(int(row[1]) for row in event_rows),
            "event_leads": None if event_lead_count is None else int(event_lead_count[0]),
            "ivy": ivy_surface(brand_count(catalog_db, IVY)),
            "why": why,
        }
    )
    return report
