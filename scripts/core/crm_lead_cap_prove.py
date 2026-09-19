#!/usr/bin/env python3
"""CAP-CRM-01 Lead CRM bound prove (Beta, read-only).

Extends the already-BUILT Lead CRM. Not a new system.
Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), plan
docs/deliveries/GROK-PLAN-CRM-LEAD-CAP-BOUND-PROVE-2026-09-19.md.

Red-teams Lead Spine and the Habitat lead page as they exist. Does not
ingest, does not call the Klaviyo reader, does not write Metricool, and
does not invent a lead, an SLA, a sale, or PROVEN. Honesty is bound to
CR-ff42f3a7c49caa79.
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
LEAD_SPINE = BETA_ROOT / "scripts" / "core" / "lead_spine.py"
KLAVIYO_READER = BETA_ROOT / "scripts" / "core" / "habitat_klaviyo_reader.py"
HABITAT_PAGE = BETA_ROOT / "dashboards" / "lead-spine.html"
ADOPTION_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"

CR_ID = "CR-ff42f3a7c49caa79"
CAP_ID = "CAP-CRM-01"
AU_ID = "AU-CRM-01-HABITAT"
HABITAT = "habitat"
ATRIUM = "atrium"
SCHEMA = "wolf.cap-crm-01.lead-bound-prove.v1"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
_MAX_READ = 2_000_000

HONESTY = {
    "cap": CAP_ID,
    "slice": "crm_lead_cap_bound_prove",
    "read_only": True,
    "prove_pack_only": True,
    "invented_leads": False,
    "invented_sla": False,
    "invented_sale": False,
    "closed_is_not_a_sale": True,
    "score_changed": False,
    "klaviyo_write": False,
    "metricool_write": False,
    "klaviyo_called": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "cap_crm_02_not_this_prove": True,
    "anon_fail_closed": True,
}


class ProveError(ValueError):
    """Fail closed. Does not invent a lead, a sale, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_klaviyo_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Lead CAP prove refuses a Klaviyo write. The reader is not called.",
        code="klaviyo_write_refused",
    )


def refuse_metricool_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Lead CAP prove refuses a Metricool write.",
        code="metricool_write_refused",
    )


def refuse_invent_lead(_body: dict | None = None) -> None:
    raise ProveError(
        "Lead CAP prove refuses an invented lead.",
        code="invent_lead_refused",
    )


def refuse_score_write(_body: dict | None = None) -> None:
    raise ProveError(
        "Lead CAP prove refuses a score or maturity write.",
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
        payload.get("invent")
        or payload.get("invent_lead")
        or payload.get("lead")
        or action in {"lead", "invent", "ingest"}
    ):
        refuse_invent_lead(payload)
    if payload.get("proven") or payload.get("score") or action in {"proven", "score", "ready"}:
        refuse_score_write(payload)
    raise ProveError(
        "Lead CAP prove is read-only. Writes are refused.",
        code="writes_refused",
    )


def _guard_read(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise ProveError("Lead CAP prove refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise ProveError("Lead CAP prove refuses a production money path", code="not_beta")
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
            "Lead CAP prove refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise ProveError("Lead CAP prove refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-CRM-01 from the ledger. Does not write it."""
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
    """Read CR-ff42f3a7c49caa79. Does not upsert, resolve, or harvest."""
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
    flags["klaviyo_write"] = False
    flags["metricool_write"] = False
    flags["klaviyo_called"] = False
    flags["invented_leads"] = False
    flags["invented_sla"] = False
    flags["invented_sale"] = False
    return flags


def _blank(brand_id: str) -> dict[str, Any]:
    return {
        "status": "NOT_READ",
        "brand_id": brand_id,
        "rows": None,
        "owned": None,
        "unowned": None,
        "aged": None,
        "not_aged": None,
        "followed": None,
        "not_followed": None,
        "demo": None,
        "not_demo": None,
        "closed": None,
        "claimed_conversion": None,
        "verified_conversion": None,
        "sales": None,
        "empty": None,
        "operating_board": False,
        "boundary": "NOT_READ",
        "why": "Lead rows were not read. Absence is not zero and not an invented lead.",
    }


def _is_demo(row: dict[str, Any]) -> bool:
    if row.get("demo") is True:
        return True
    prov = row.get("provenance")
    if isinstance(prov, dict) and prov.get("demo") is True:
        return True
    raw = row.get("provenance_json")
    if isinstance(raw, str):
        compact = raw.replace(" ", "")
        return '"demo":true' in compact
    return False


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def classify_bound(
    rows: list[dict[str, Any]] | None,
    *,
    brand_id: str,
) -> dict[str, Any]:
    """Pure red-team. None means unread. A foreign brand fails closed.

    Does not mutate rows. Does not invent an owner, an age, a follow-up,
    or a sale. Closed is counted and is not a sale.
    """
    bid = (brand_id or "").strip()
    if not bid:
        raise ProveError("brand required", code="invalid")
    if rows is None:
        return _blank(bid)
    owned = unowned = aged = not_aged = 0
    followed = not_followed = demo = not_demo = 0
    closed = claimed = verified = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ProveError("lead row must be an object", code="invalid")
        row_brand = str(row.get("brand_id") or "").strip()
        if row_brand != bid:
            raise ProveError(
                "client-data boundary breached: row brand does not match the requested brand",
                code="boundary_breach",
            )
        if not _present(row.get("entity_id")):
            raise ProveError(
                "client-data boundary breached: entity_id required",
                code="boundary_breach",
            )
        if _present(row.get("owner_person_id")):
            owned += 1
        else:
            unowned += 1
        if _present(row.get("source_observed_at")):
            aged += 1
        else:
            not_aged += 1
        if _present(row.get("first_human_touch_at")):
            followed += 1
        else:
            not_followed += 1
        if _is_demo(row):
            demo += 1
        else:
            not_demo += 1
        if str(row.get("wolf_stage") or "").strip().upper() == "CLOSED":
            closed += 1
        conversion = str(row.get("conversion_status") or "").strip().upper()
        if conversion == "CLAIMED":
            claimed += 1
        elif conversion == "VERIFIED":
            verified += 1
    count = len(rows)
    demo_only = count > 0 and demo == count
    if count == 0:
        why = "No rows for this brand. Empty is not an invented lead."
    elif demo_only:
        why = "Every row read is a demo fixture. That is not a live operating board."
    else:
        why = "Rows were read. A non-demo row is not commissioning and is not PROVEN."
    return {
        "status": "READ",
        "brand_id": bid,
        "rows": count,
        "owned": owned,
        "unowned": unowned,
        "aged": aged,
        "not_aged": not_aged,
        "followed": followed,
        "not_followed": not_followed,
        "demo": demo,
        "not_demo": not_demo,
        "closed": closed,
        "claimed_conversion": claimed,
        "verified_conversion": verified,
        "sales": None,
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


def read_brand_rows(
    catalog_db: Path | str | None,
    brand_id: str,
) -> list[dict[str, Any]] | None:
    """Brand-filtered read. No email, no source id, no provenance blob.

    None means the table was not read. An empty list means the table was
    read and this brand had no rows.
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
            SELECT entity_id, brand_id, source_system,
                   owner_person_id, source_observed_at, first_human_touch_at,
                   wolf_stage, conversion_status,
                   CASE
                     WHEN provenance_json LIKE '%"demo": true%'
                       OR provenance_json LIKE '%"demo":true%'
                     THEN 1 ELSE 0
                   END AS demo_flag
            FROM core_leads
            WHERE brand_id=?
            """,
            (brand_id,),
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
                "source_system": item[2],
                "owner_person_id": item[3],
                "source_observed_at": item[4],
                "first_human_touch_at": item[5],
                "wolf_stage": item[6],
                "conversion_status": item[7],
                "demo": bool(item[8]),
            }
        )
    return rows


def brand_count(catalog_db: Path | str | None, brand_id: str) -> int | None:
    """None if unread. Zero is a real count and must not be shown as a board."""
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    conn = _ro(path)
    if conn is None:
        return None
    try:
        if not _table_exists(conn, "core_leads"):
            return None
        row = conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE brand_id=?",
            (brand_id,),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None:
        return None
    return int(row[0])


def atrium_surface(count: int | None) -> dict[str, Any]:
    """Ledger names Atrium. No rows is ABSENT, not zero, not a board."""
    if count is None:
        return {
            "brand_id": ATRIUM,
            "status": "NOT_READ",
            "rows": None,
            "operating_board": False,
            "why": "Atrium leads were not read. Absence is not zero.",
        }
    if count == 0:
        return {
            "brand_id": ATRIUM,
            "status": "ABSENT",
            "rows": None,
            "operating_board": False,
            "why": (
                "Ledger names Atrium leads. Beta core_leads has no atrium rows. "
                "ABSENT is not zero and not an operating board."
            ),
        }
    return {
        "brand_id": ATRIUM,
        "status": "PRESENT",
        "rows": count,
        "operating_board": False,
        "why": "Atrium rows exist. This prove does not treat them as a commissioned board.",
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
    page_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read source text. Does not import the Klaviyo reader and does not ingest."""
    spine = _read_text(Path(spine_path) if spine_path else LEAD_SPINE)
    reader = _read_text(Path(reader_path) if reader_path else KLAVIYO_READER)
    page = _read_text(Path(page_path) if page_path else HABITAT_PAGE)
    return {
        "lead_spine": {
            "present": spine is not None,
            "executed": False,
            "never_invent_stated": bool(spine and "never invent a lead" in spine),
            "entity_wide_insufficient": bool(spine and "entity-wide insufficient" in spine),
            "external_writes_false_stated": bool(spine and '"external_writes": False' in spine),
        },
        "klaviyo_reader": {
            "present": reader is not None,
            "write_path_present": bool(reader and "def run_ingest" in reader),
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
    }


def read_adoption(path: Path | str | None = None) -> dict[str, Any]:
    """Read AU-CRM-01-HABITAT. Does not write the discovery file."""
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
    rows = data if isinstance(data, list) else data.get("units") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        # discovery file is a dict with a list somewhere; scan one level
        if isinstance(data, dict):
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
    out["why"] = "Adoption file was read and AU-CRM-01-HABITAT was not in it."
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
    atrium: dict[str, Any],
    surfaces: dict[str, Any],
    adoption: dict[str, Any],
    ledger_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Honest gaps. Each one still blocks a higher maturity. None is cleared here."""
    gaps = [
        _gap(
            "atrium_board",
            str(atrium.get("status") or "NOT_READ"),
            str(atrium.get("why") or ""),
        ),
        _gap(
            "habitat_operating_board",
            "DEMO" if habitat.get("status") == "READ" and habitat.get("demo") and habitat.get("demo") == habitat.get("rows") else (
                "NOT_READ" if habitat.get("status") != "READ" else "NOT_COMMISSIONED"
            ),
            "Demo fixtures and an uncommissioned board are not a live Habitat operating board.",
        ),
        _gap(
            "klaviyo_write",
            "NOT_CALLED",
            "The Klaviyo reader has a write path. This prove does not call it and does not open the network.",
        ),
        _gap(
            "metricool_write",
            "REFUSED",
            "Metricool write is refused. A social connector is not this CAP.",
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
            "cap_crm_02",
            "NOT_THIS_PROVE",
            "Customer identity and memory is CAP-CRM-02. It is not proved here.",
        ),
    ]
    spine = surfaces.get("lead_spine") or {}
    if not spine.get("entity_wide_insufficient"):
        gaps.append(
            _gap(
                "brand_boundary_contract",
                "MISSING",
                "Lead Spine text does not state that entity-wide scope is insufficient.",
            )
        )
    return gaps


def build_prove(
    *,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    adoption_path: Path | str | None = None,
    spine_path: Path | str | None = None,
    reader_path: Path | str | None = None,
    page_path: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read. No write, no ingest, no invented lead."""
    flags = honesty_flags(ledger_path, catalog_db)
    habitat_rows = read_brand_rows(catalog_db, HABITAT)
    habitat = classify_bound(habitat_rows, brand_id=HABITAT)
    atrium = atrium_surface(brand_count(catalog_db, ATRIUM))
    surfaces = inspect_surfaces(spine_path, reader_path, page_path)
    adoption = read_adoption(adoption_path)
    gaps = document_gaps(habitat, atrium, surfaces, adoption, ledger_path)
    return {
        "ok": True,
        "schema": SCHEMA,
        "cap": CAP_ID,
        "honesty": flags,
        "habitat": habitat,
        "atrium": atrium,
        "surfaces": surfaces,
        "adoption": adoption,
        "gaps": gaps,
        "writes": {
            "klaviyo": False,
            "metricool": False,
            "invented_leads": False,
            "ledger": False,
            "cr": False,
        },
    }
