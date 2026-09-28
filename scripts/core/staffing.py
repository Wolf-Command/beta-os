#!/usr/bin/env python3
"""Organisation Role / Position / Assignment repository (Beta).

Uses org_roles / org_positions / org_assignments — not LLM routing "role".
Permission engines are out of scope for this module. Scope lives in core.scope.

CAP-HR-01 reads the same tables. A person is not a role. The read adds no person.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"staffing refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"staffing refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_roles(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT role_id, display_name, department_id, role_type, status,
                   created_at, updated_at
            FROM org_roles ORDER BY role_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_role(role_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    rid = (role_id or "").strip()
    if not rid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT role_id, display_name, department_id, role_type, status,
                       created_at, updated_at
                FROM org_roles WHERE role_id=?
                """,
                (rid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_positions(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions ORDER BY position_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_positions_by_entity(
    entity_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    eid = (entity_id or "").strip()
    if not eid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions WHERE entity_id=? ORDER BY position_id
            """,
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_positions_by_role(
    role_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    rid = (role_id or "").strip()
    if not rid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                   position_label, status, fte, created_at, updated_at
            FROM org_positions WHERE role_id=? ORDER BY position_id
            """,
            (rid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_position(position_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    pid = (position_id or "").strip()
    if not pid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT position_id, role_id, entity_id, location_id, brand_id, department_id,
                       position_label, status, fte, created_at, updated_at
                FROM org_positions WHERE position_id=?
                """,
                (pid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_active_assignments_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   p.position_label, p.entity_id, p.role_id, r.display_name AS org_role_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def list_assignments_for_person(
    person_id: str, *, include_ended: bool = True, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        sql = """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   p.position_label, p.entity_id, p.role_id, r.display_name AS org_role_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id=?
        """
        if not include_ended:
            sql += " AND a.status='ACTIVE' AND a.end_at IS NULL"
        sql += " ORDER BY a.start_at DESC, a.assignment_id"
        return [dict(r) for r in c.execute(sql, (pid,)).fetchall()]
    finally:
        if own:
            c.close()


def list_assignments_for_position(
    position_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (position_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.start_at, a.end_at,
                   a.status, a.is_primary, a.created_at, a.updated_at,
                   per.display_name AS person_display_name
            FROM org_assignments a
            JOIN org_persons per ON per.person_id = a.person_id
            WHERE a.position_id=?
            ORDER BY a.start_at DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_current_occupants(
    position_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (position_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.is_primary, a.start_at,
                   per.display_name AS person_display_name
            FROM org_assignments a
            JOIN org_persons per ON per.person_id = a.person_id
            WHERE a.position_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def resolve_org_context_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Active Assignment → Position → org Role + Assignment Scopes (not LLM role)."""
    active = list_active_assignments_for_person(person_id, conn=conn)
    # Import locally to avoid circular import at module load
    from core import scope as _scope  # type: ignore
    scopes = _scope.list_active_scopes_for_person(person_id, conn=conn)
    return {
        "person_id": person_id,
        "active_assignments": active,
        "scopes": scopes,
        "scope": scopes,  # transitional alias; was "NOT_BUILT"
        "rbac": "NOT_BUILT",
    }


CAP_HR01 = "CAP-HR-01"
CR_HR01 = "CR-6e8a5493b94e788a"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
HR01_GAP = "Canonical People Master per legal entity with CAP-bound tests"
_PERSON_DEMO = (
    "upper({alias}.person_id) LIKE '%DEMO%'"
    " OR upper({alias}.person_id) LIKE '%SEED%'"
    " OR upper({alias}.person_id) LIKE '%FIXTURE%'"
    " OR upper({alias}.person_id) LIKE '%TEST%'"
)
_POSITION_FIXTURE = (
    "upper({pos}.position_id) LIKE '%FIXTURE%'"
    " OR upper({pos}.position_id) LIKE '%DEMO%'"
    " OR upper({pos}.position_id) LIKE '%SEED%'"
    " OR upper({pos}.position_id) LIKE '%TEST%'"
    " OR lower(COALESCE({role}.role_type, '')) = 'fixture'"
)


class StaffingError(ValueError):
    """Fail closed. Does not create a person or raise the ledger."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_person_create(body: dict | None = None) -> None:
    """People-master mutation ends here. Nothing is written."""
    payload = body or {}
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("person") or payload.get("create_person") or action in {"person", "create"}:
        raise StaffingError("A person is not created from this read.", code="person_create_refused")
    if payload.get("proven") or payload.get("score") or action in {"proven", "score", "ready"}:
        raise StaffingError("The people-master ledger row is not raised.", code="score_refused")
    raise StaffingError("The people-master read is read-only. Writes are refused.", code="writes_refused")


def _guard_read(path: Path) -> None:
    low = str(path).lower()
    if "alchemist" in low:
        raise StaffingError("People-master read refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low or "wolf-system" in low:
        raise StaffingError("People-master read refuses a production path", code="not_beta")
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
        raise StaffingError(
            "People-master read refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _ro(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
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


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"}:
        return token
    return "UNKNOWN"


def _ledger_cap_state(ledger_path: Path | str | None = None) -> tuple[str, int | None]:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_read(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN", None
    if not isinstance(data, dict):
        return "UNKNOWN", None
    row = data.get(CAP_HR01)
    state = "UNKNOWN"
    if isinstance(row, list) and row:
        state = _maturity(str(row[0]))
    return state, len(data)


def _load_hr_cr(conn: sqlite3.Connection) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cr_id": CR_HR01,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_HR01,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    if not _table_exists(conn, "wolf_completion_items"):
        return out
    row = conn.execute(
        """
        SELECT state, blocker_class, capability, next_action
        FROM wolf_completion_items WHERE id=?
        """,
        (CR_HR01,),
    ).fetchone()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_HR01
    out["cr_next_action"] = row[3]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def _unread_people(why: str, ledger_path: Path | str | None) -> dict[str, Any]:
    state, rows = _ledger_cap_state(ledger_path)
    return {
        "ok": False,
        "cap": CAP_HR01,
        "read": "stored_people",
        "data_lane": "UNKNOWN",
        "lane_column": False,
        "persons_stored": "UNKNOWN",
        "demo_persons": "UNKNOWN",
        "operational_persons": "UNKNOWN",
        "fixture_only_persons": "UNKNOWN",
        "unseated_persons": "UNKNOWN",
        "ended_only_persons": "UNKNOWN",
        "roles_stored": "UNKNOWN",
        "positions_stored": "UNKNOWN",
        "assignments_stored": "UNKNOWN",
        "legal_entities": "UNKNOWN",
        "entities": [],
        "people_are_not_roles": "UNKNOWN",
        "person_role_id_overlap": "UNKNOWN",
        "name_based_authorization": False,
        "authorization": "NOT PERFORMED",
        "persons_created": 0,
        "roles_created": 0,
        "positions_created": 0,
        "assignments_created": 0,
        "person_id_listed": False,
        "role_id_listed": False,
        "position_id_listed": False,
        "assignment_id_listed": False,
        "identity_fields_selected": False,
        "operating_board": False,
        "proved": False,
        "current": False,
        "pay_figure": None,
        "payroll_source": "UNAVAILABLE",
        "payroll_cap": "CAP-HR-04",
        "payroll_tested_here": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "catalog_write": False,
        "ledger_write": False,
        "payment_executed": False,
        "esb_write": False,
        "cr_resolved": False,
        "honesty": {
            "maturity": state,
            "proven": False,
            "ledger_rows": rows,
            "ledger_write": False,
            "model_c_maturity_raised": False,
        },
        "why": why,
    }


def read_stored_people(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read persons already stored, per legal entity. Creates nobody.

    A demo person is a person id containing DEMO, SEED, FIXTURE, or TEST.
    A fixture seat is a position id containing those tokens, or a fixture role.
    Operational occupancy is an active assignment of a non-demo person on a
    seat that is not a fixture. Empty occupancy is not an absent entity.
    """
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    _guard_read(path)
    conn = _ro(path)
    if conn is None:
        return _unread_people(
            "The catalog was not read. Absence is not zero people and not an invented person.",
            ledger_path,
        )
    needed = ("org_persons", "org_roles", "org_positions", "org_assignments", "org_entities")
    try:
        if any(not _table_exists(conn, name) for name in needed):
            return _unread_people(
                "A people-master table is missing. Absence is not zero people.",
                ledger_path,
            )
        person_cols = _columns(conn, "org_persons")
        demo = _PERSON_DEMO.format(alias="per")
        fixture = _POSITION_FIXTURE.format(pos="pos", role="r")
        state, ledger_rows = _ledger_cap_state(ledger_path)
        cr = _load_hr_cr(conn)
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        roles = int(conn.execute("SELECT COUNT(*) FROM org_roles").fetchone()[0])
        positions = int(conn.execute("SELECT COUNT(*) FROM org_positions").fetchone()[0])
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
        demo_persons = int(
            conn.execute(
                f"SELECT COUNT(*) FROM org_persons AS per WHERE {demo}"
            ).fetchone()[0]
        )
        operational_persons = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM org_persons AS per
                WHERE NOT ({demo})
                  AND EXISTS (
                    SELECT 1
                    FROM org_assignments AS a
                    JOIN org_positions AS pos ON pos.position_id = a.position_id
                    JOIN org_roles AS r ON r.role_id = pos.role_id
                    WHERE a.person_id = per.person_id
                      AND a.status = 'ACTIVE'
                      AND NOT ({fixture})
                  )
                """
            ).fetchone()[0]
        )
        fixture_only_persons = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM org_persons AS per
                WHERE NOT ({demo})
                  AND EXISTS (
                    SELECT 1 FROM org_assignments AS a
                    WHERE a.person_id = per.person_id AND a.status = 'ACTIVE'
                  )
                  AND NOT EXISTS (
                    SELECT 1
                    FROM org_assignments AS a
                    JOIN org_positions AS pos ON pos.position_id = a.position_id
                    JOIN org_roles AS r ON r.role_id = pos.role_id
                    WHERE a.person_id = per.person_id
                      AND a.status = 'ACTIVE'
                      AND NOT ({fixture})
                  )
                """
            ).fetchone()[0]
        )
        unseated_persons = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM org_persons AS per
                WHERE NOT ({demo})
                  AND NOT EXISTS (
                    SELECT 1 FROM org_assignments AS a WHERE a.person_id = per.person_id
                  )
                """
            ).fetchone()[0]
        )
        ended_only_persons = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM org_persons AS per
                WHERE NOT ({demo})
                  AND EXISTS (
                    SELECT 1 FROM org_assignments AS a WHERE a.person_id = per.person_id
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM org_assignments AS a
                    WHERE a.person_id = per.person_id AND a.status = 'ACTIVE'
                  )
                """
            ).fetchone()[0]
        )
        overlap = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_persons AS per
                JOIN org_roles AS r ON r.role_id = per.person_id
                """
            ).fetchone()[0]
        )
        person_is_role = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_assignments AS a
                JOIN org_roles AS r ON r.role_id = a.person_id
                """
            ).fetchone()[0]
        )
        person_is_position = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_assignments AS a
                JOIN org_positions AS pos ON pos.position_id = a.person_id
                """
            ).fetchone()[0]
        )
        missing_person = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_assignments AS a
                WHERE NOT EXISTS (
                  SELECT 1 FROM org_persons AS per WHERE per.person_id = a.person_id
                )
                """
            ).fetchone()[0]
        )
        missing_position = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_assignments AS a
                WHERE NOT EXISTS (
                  SELECT 1 FROM org_positions AS pos WHERE pos.position_id = a.position_id
                )
                """
            ).fetchone()[0]
        )
        missing_role = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_positions AS pos
                WHERE NOT EXISTS (
                  SELECT 1 FROM org_roles AS r WHERE r.role_id = pos.role_id
                )
                """
            ).fetchone()[0]
        )
        missing_entity = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_positions
                WHERE entity_id IS NULL OR length(trim(entity_id)) = 0
                """
            ).fetchone()[0]
        )
        unknown_entity = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_positions AS pos
                WHERE entity_id IS NOT NULL AND length(trim(entity_id)) > 0
                  AND NOT EXISTS (
                    SELECT 1 FROM org_entities AS e WHERE e.entity_id = pos.entity_id
                  )
                """
            ).fetchone()[0]
        )
        active_assignments = int(
            conn.execute(
                "SELECT COUNT(*) FROM org_assignments WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        ended_assignments = int(
            conn.execute(
                "SELECT COUNT(*) FROM org_assignments WHERE status='ENDED'"
            ).fetchone()[0]
        )
        other_assignments = assignments - active_assignments - ended_assignments
        operational_active = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM org_assignments AS a
                JOIN org_persons AS per ON per.person_id = a.person_id
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE a.status = 'ACTIVE' AND NOT ({demo}) AND NOT ({fixture})
                """
            ).fetchone()[0]
        )
        fixture_active = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM org_assignments AS a
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE a.status = 'ACTIVE' AND ({fixture})
                """
            ).fetchone()[0]
        )
        demo_on_plain = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM org_assignments AS a
                JOIN org_persons AS per ON per.person_id = a.person_id
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE a.status = 'ACTIVE' AND ({demo}) AND NOT ({fixture})
                """
            ).fetchone()[0]
        )
        legal_present = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM org_persons AS per
                WHERE NOT ({demo})
                  AND legal_name IS NOT NULL AND length(trim(legal_name)) > 0
                  AND EXISTS (
                    SELECT 1
                    FROM org_assignments AS a
                    JOIN org_positions AS pos ON pos.position_id = a.position_id
                    JOIN org_roles AS r ON r.role_id = pos.role_id
                    WHERE a.person_id = per.person_id
                      AND a.status = 'ACTIVE'
                      AND NOT ({fixture})
                  )
                """
            ).fetchone()[0]
        )
        roles_without_position = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_roles AS r
                WHERE NOT EXISTS (
                  SELECT 1 FROM org_positions AS pos WHERE pos.role_id = r.role_id
                )
                """
            ).fetchone()[0]
        )
        role_status = [
            {"status": row[0] or "", "rows": int(row[1])}
            for row in conn.execute(
                """
                SELECT status, COUNT(*) FROM org_roles
                GROUP BY status ORDER BY status
                """
            ).fetchall()
        ]
        role_types = [
            {"role_type": row[0] or "", "rows": int(row[1])}
            for row in conn.execute(
                """
                SELECT role_type, COUNT(*) FROM org_roles
                GROUP BY role_type ORDER BY role_type
                """
            ).fetchall()
        ]
        entities_raw = conn.execute(
            """
            SELECT entity_id, entity_type, status,
                   CASE
                     WHEN legal_name IS NOT NULL AND length(trim(legal_name)) > 0
                     THEN 1 ELSE 0
                   END
            FROM org_entities
            ORDER BY entity_id
            """
        ).fetchall()
        position_counts = {
            row[0]: (int(row[1]), int(row[2]))
            for row in conn.execute(
                f"""
                SELECT pos.entity_id,
                       COUNT(*),
                       SUM(CASE WHEN {fixture} THEN 1 ELSE 0 END)
                FROM org_positions AS pos
                JOIN org_roles AS r ON r.role_id = pos.role_id
                GROUP BY pos.entity_id
                """
            ).fetchall()
        }
        empty_seats = {
            row[0]: int(row[1])
            for row in conn.execute(
                f"""
                SELECT pos.entity_id, COUNT(*)
                FROM org_positions AS pos
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE NOT ({fixture})
                  AND NOT EXISTS (
                    SELECT 1 FROM org_assignments AS a
                    WHERE a.position_id = pos.position_id AND a.status = 'ACTIVE'
                  )
                GROUP BY pos.entity_id
                """
            ).fetchall()
        }
        operational_by_entity = {
            row[0]: (int(row[1]), int(row[2]))
            for row in conn.execute(
                f"""
                SELECT pos.entity_id, COUNT(DISTINCT a.person_id), COUNT(*)
                FROM org_assignments AS a
                JOIN org_persons AS per ON per.person_id = a.person_id
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE a.status = 'ACTIVE' AND NOT ({demo}) AND NOT ({fixture})
                GROUP BY pos.entity_id
                """
            ).fetchall()
        }
        fixture_by_entity = {
            row[0]: int(row[1])
            for row in conn.execute(
                f"""
                SELECT pos.entity_id, COUNT(*)
                FROM org_assignments AS a
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE a.status = 'ACTIVE' AND ({fixture})
                GROUP BY pos.entity_id
                """
            ).fetchall()
        }
        not_legal = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_entities
                WHERE entity_type IS NULL OR entity_type != 'LEGAL_ENTITY'
                """
            ).fetchone()[0]
        )
        auth_stored: int | str = "UNKNOWN"
        auth_missing_person: int | str = "UNKNOWN"
        persons_without_auth: int | str = "UNKNOWN"
        operational_without_auth: int | str = "UNKNOWN"
        auth_providers: list[dict[str, Any]] = []
        if _table_exists(conn, "org_auth_identities"):
            auth_stored = int(
                conn.execute("SELECT COUNT(*) FROM org_auth_identities").fetchone()[0]
            )
            auth_missing_person = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM org_auth_identities AS a
                    WHERE NOT EXISTS (
                      SELECT 1 FROM org_persons AS per WHERE per.person_id = a.person_id
                    )
                    """
                ).fetchone()[0]
            )
            persons_without_auth = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM org_persons AS per
                    WHERE NOT EXISTS (
                      SELECT 1 FROM org_auth_identities AS a
                      WHERE a.person_id = per.person_id AND a.status = 'ACTIVE'
                    )
                    """
                ).fetchone()[0]
            )
            operational_without_auth = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*) FROM org_persons AS per
                    WHERE NOT ({demo})
                      AND EXISTS (
                        SELECT 1
                        FROM org_assignments AS a
                        JOIN org_positions AS pos ON pos.position_id = a.position_id
                        JOIN org_roles AS r ON r.role_id = pos.role_id
                        WHERE a.person_id = per.person_id
                          AND a.status = 'ACTIVE'
                          AND NOT ({fixture})
                      )
                      AND NOT EXISTS (
                        SELECT 1 FROM org_auth_identities AS auth
                        WHERE auth.person_id = per.person_id AND auth.status = 'ACTIVE'
                      )
                    """
                ).fetchone()[0]
            )
            auth_providers = [
                {"provider": row[0] or "", "status": row[1] or "", "rows": int(row[2])}
                for row in conn.execute(
                    """
                    SELECT provider, status, COUNT(*)
                    FROM org_auth_identities
                    GROUP BY provider, status
                    ORDER BY provider, status
                    """
                ).fetchall()
            ]
        payroll_tables = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND lower(name) LIKE '%payroll%'
                """
            ).fetchone()[0]
        )
        wage_column = any(
            token in name.lower()
            for name in person_cols
            for token in ("pay", "wage", "salary")
        )
    except sqlite3.Error:
        return _unread_people(
            "The people-master read failed closed. Absence is not zero people.",
            ledger_path,
        )
    finally:
        conn.close()

    entities: list[dict[str, Any]] = []
    for row in entities_raw:
        entity_id = row[0] or ""
        pos_count, fixture_positions = position_counts.get(entity_id, (0, 0))
        op_persons, op_assignments = operational_by_entity.get(entity_id, (0, 0))
        entities.append(
            {
                "entity_id": entity_id,
                "entity_type": row[1] or "",
                "entity_status": row[2] or "",
                "legal_name_present": bool(row[3]),
                "entity_absent": False,
                "positions": pos_count,
                "fixture_positions": fixture_positions,
                "operational_positions": pos_count - fixture_positions,
                "operational_persons": op_persons,
                "operational_assignments": op_assignments,
                "empty_operational_seats": empty_seats.get(entity_id, 0),
                "fixture_active_assignments": fixture_by_entity.get(entity_id, 0),
                "operational_occupancy": "PRESENT" if op_persons else "EMPTY",
            }
        )
    held = (
        missing_person == 0
        and missing_position == 0
        and missing_role == 0
        and missing_entity == 0
        and unknown_entity == 0
    )
    if persons == 0:
        why = "No stored persons. Empty is not an invented person."
    else:
        why = (
            "Stored persons were read. A demo person id is not operational. "
            "A fixture seat is not operational occupancy. "
            "An empty entity occupancy is not an absent legal entity. "
            "A count is not commissioning."
        )
    return {
        "ok": True,
        "cap": CAP_HR01,
        "read": "stored_people",
        "data_lane": "UNKNOWN" if "data_lane" not in person_cols else "PRESENT",
        "lane_column": "data_lane" in person_cols,
        "email_column": any("email" in name.lower() for name in person_cols),
        "persons_stored": persons,
        "demo_persons": demo_persons,
        "operational_persons": operational_persons,
        "fixture_only_persons": fixture_only_persons,
        "unseated_persons": unseated_persons,
        "ended_only_persons": ended_only_persons,
        "demo_counted_as_operational": False,
        "roles_stored": roles,
        "positions_stored": positions,
        "assignments_stored": assignments,
        "active_assignments": active_assignments,
        "ended_assignments": ended_assignments,
        "other_status_assignments": other_assignments,
        "operational_active_assignments": operational_active,
        "fixture_active_assignments": fixture_active,
        "demo_on_plain_seat_assignments": demo_on_plain,
        "legal_entities": len(entities),
        "entities_not_legal": not_legal,
        "entities": entities,
        "legal_name_present_operational": legal_present,
        "legal_name_absent_operational": operational_persons - legal_present,
        "roles_without_position": roles_without_position,
        "role_status": role_status,
        "role_types": role_types,
        "people_are_not_roles": overlap == 0 and person_is_role == 0 and person_is_position == 0,
        "person_role_id_overlap": overlap,
        "assignment_person_is_role": person_is_role,
        "assignment_person_is_position": person_is_position,
        "assignment_missing_person": missing_person,
        "assignment_missing_position": missing_position,
        "position_missing_role": missing_role,
        "position_missing_entity": missing_entity,
        "position_entity_unknown": unknown_entity,
        "boundary": "HELD" if held else "BREACHED",
        "name_based_authorization": False,
        "authorization": "NOT PERFORMED",
        "persons_created": 0,
        "roles_created": 0,
        "positions_created": 0,
        "assignments_created": 0,
        "person_id_listed": False,
        "role_id_listed": False,
        "position_id_listed": False,
        "assignment_id_listed": False,
        "identity_fields_selected": False,
        "auth_identities_stored": auth_stored,
        "auth_missing_person": auth_missing_person,
        "persons_without_active_auth": persons_without_auth,
        "operational_persons_without_active_auth": operational_without_auth,
        "auth_providers": auth_providers,
        "operating_board": False,
        "proved": False,
        "current": False,
        "pay_figure": None,
        "wage_column": wage_column,
        "payroll_tables": payroll_tables,
        "payroll_source": "UNAVAILABLE" if payroll_tables == 0 and not wage_column else "UNKNOWN",
        "payroll_cap": "CAP-HR-04",
        "payroll_tested_here": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "catalog_write": False,
        "ledger_write": False,
        "payment_executed": False,
        "esb_write": False,
        "cr_resolved": False,
        "honesty": {
            "maturity": state,
            "proven": state == "PROVEN",
            "ready": state == "READY",
            "ledger_rows": ledger_rows,
            "ledger_write": False,
            "model_c_maturity_raised": False,
            "invented_proven": False,
            "cr_id": cr["cr_id"],
            "cr_present": cr["cr_present"],
            "cr_state": cr["cr_state"],
            "cr_blocker": cr["cr_blocker"],
            "cr_next_action": cr["cr_next_action"],
            "cr_resolved": cr["cr_resolved"],
        },
        "why": why,
    }
