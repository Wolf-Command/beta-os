#!/usr/bin/env python3
"""CAP-HR-01 stored-person read. Counts people already stored. Writes nothing."""
from __future__ import annotations

import inspect
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import staffing as staff  # noqa: E402
from core.canonical_guard import CanonicalGuardError, assert_write_allowed  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
CR_ID = "CR-6e8a5493b94e788a"
GAP = "Canonical People Master per legal entity with CAP-bound tests"
FORBIDDEN_KEYS = {
    "person_id",
    "display_name",
    "legal_name",
    "identifier",
    "email",
    "assignment_id",
    "position_id",
    "role_id",
    "position_label",
    "org_role_name",
    "auth_identity_id",
    "name",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _demo(alias: str) -> str:
    return (
        f"upper({alias}.person_id) LIKE '%DEMO%'"
        f" OR upper({alias}.person_id) LIKE '%SEED%'"
        f" OR upper({alias}.person_id) LIKE '%FIXTURE%'"
        f" OR upper({alias}.person_id) LIKE '%TEST%'"
    )


def _fixture(pos: str = "pos", role: str = "r") -> str:
    return (
        f"upper({pos}.position_id) LIKE '%FIXTURE%'"
        f" OR upper({pos}.position_id) LIKE '%DEMO%'"
        f" OR upper({pos}.position_id) LIKE '%SEED%'"
        f" OR upper({pos}.position_id) LIKE '%TEST%'"
        f" OR lower(COALESCE({role}.role_type, '')) = 'fixture'"
    )


def _ledger_counts() -> tuple[int, int, int, str | None, int, int, int, int]:
    conn = _ro(CATALOG)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0])
        approvals = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        status = conn.execute(
            "SELECT status FROM core_evidence_records WHERE evidence_id=?",
            (EVIDENCE_ID,),
        ).fetchone()
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        roles = int(conn.execute("SELECT COUNT(*) FROM org_roles").fetchone()[0])
        positions = int(conn.execute("SELECT COUNT(*) FROM org_positions").fetchone()[0])
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        persons,
        roles,
        positions,
        assignments,
    )


def _oracle() -> dict:
    demo = _demo("per")
    fixture = _fixture()
    conn = _ro(CATALOG)
    try:
        person_cols = [str(row[1]) for row in conn.execute("PRAGMA table_info(org_persons)").fetchall()]
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        roles = int(conn.execute("SELECT COUNT(*) FROM org_roles").fetchone()[0])
        positions = int(conn.execute("SELECT COUNT(*) FROM org_positions").fetchone()[0])
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
        demo_persons = int(
            conn.execute(f"SELECT COUNT(*) FROM org_persons AS per WHERE {demo}").fetchone()[0]
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
        fixture_only = int(
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
        unseated = int(
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
        ended_only = int(
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
                "SELECT COUNT(*) FROM org_persons AS per JOIN org_roles AS r ON r.role_id = per.person_id"
            ).fetchone()[0]
        )
        person_is_role = int(
            conn.execute(
                "SELECT COUNT(*) FROM org_assignments AS a JOIN org_roles AS r ON r.role_id = a.person_id"
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
                WHERE NOT EXISTS (SELECT 1 FROM org_roles AS r WHERE r.role_id = pos.role_id)
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
        active = int(conn.execute("SELECT COUNT(*) FROM org_assignments WHERE status='ACTIVE'").fetchone()[0])
        ended = int(conn.execute("SELECT COUNT(*) FROM org_assignments WHERE status='ENDED'").fetchone()[0])
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
                "SELECT status, COUNT(*) FROM org_roles GROUP BY status ORDER BY status"
            ).fetchall()
        ]
        role_types = [
            {"role_type": row[0] or "", "rows": int(row[1])}
            for row in conn.execute(
                "SELECT role_type, COUNT(*) FROM org_roles GROUP BY role_type ORDER BY role_type"
            ).fetchall()
        ]
        entities = []
        for row in conn.execute(
            """
            SELECT entity_id, entity_type, status,
                   CASE
                     WHEN legal_name IS NOT NULL AND length(trim(legal_name)) > 0
                     THEN 1 ELSE 0
                   END
            FROM org_entities
            ORDER BY entity_id
            """
        ).fetchall():
            entity_id = row[0] or ""
            pos_count, fixture_positions = conn.execute(
                f"""
                SELECT COUNT(*),
                       SUM(CASE WHEN {fixture} THEN 1 ELSE 0 END)
                FROM org_positions AS pos
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE pos.entity_id = ?
                """,
                (entity_id,),
            ).fetchone()
            pos_count = int(pos_count or 0)
            fixture_positions = int(fixture_positions or 0)
            op_persons, op_assignments = conn.execute(
                f"""
                SELECT COUNT(DISTINCT a.person_id), COUNT(*)
                FROM org_assignments AS a
                JOIN org_persons AS per ON per.person_id = a.person_id
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE pos.entity_id = ?
                  AND a.status = 'ACTIVE' AND NOT ({demo}) AND NOT ({fixture})
                """,
                (entity_id,),
            ).fetchone()
            empty = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM org_positions AS pos
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE pos.entity_id = ?
                  AND NOT ({fixture})
                  AND NOT EXISTS (
                    SELECT 1 FROM org_assignments AS a
                    WHERE a.position_id = pos.position_id AND a.status = 'ACTIVE'
                  )
                """,
                (entity_id,),
            ).fetchone()[0]
            fixture_asg = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM org_assignments AS a
                JOIN org_positions AS pos ON pos.position_id = a.position_id
                JOIN org_roles AS r ON r.role_id = pos.role_id
                WHERE pos.entity_id = ? AND a.status = 'ACTIVE' AND ({fixture})
                """,
                (entity_id,),
            ).fetchone()[0]
            op_persons = int(op_persons or 0)
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
                    "operational_assignments": int(op_assignments or 0),
                    "empty_operational_seats": int(empty or 0),
                    "fixture_active_assignments": int(fixture_asg or 0),
                    "operational_occupancy": "PRESENT" if op_persons else "EMPTY",
                }
            )
        not_legal = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_entities
                WHERE entity_type IS NULL OR entity_type != 'LEGAL_ENTITY'
                """
            ).fetchone()[0]
        )
        auth_stored = int(conn.execute("SELECT COUNT(*) FROM org_auth_identities").fetchone()[0])
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
            token in name.lower() for name in person_cols for token in ("pay", "wage", "salary")
        )
        cr = conn.execute(
            "SELECT state, blocker_class, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "persons": persons,
        "roles": roles,
        "positions": positions,
        "assignments": assignments,
        "demo_persons": demo_persons,
        "operational_persons": operational_persons,
        "fixture_only_persons": fixture_only,
        "unseated_persons": unseated,
        "ended_only_persons": ended_only,
        "overlap": overlap,
        "person_is_role": person_is_role,
        "person_is_position": person_is_position,
        "missing_person": missing_person,
        "missing_position": missing_position,
        "missing_role": missing_role,
        "missing_entity": missing_entity,
        "unknown_entity": unknown_entity,
        "active": active,
        "ended": ended,
        "operational_active": operational_active,
        "fixture_active": fixture_active,
        "demo_on_plain": demo_on_plain,
        "legal_present": legal_present,
        "roles_without_position": roles_without_position,
        "role_status": role_status,
        "role_types": role_types,
        "entities": entities,
        "not_legal": not_legal,
        "auth_stored": auth_stored,
        "auth_missing_person": auth_missing_person,
        "persons_without_auth": persons_without_auth,
        "operational_without_auth": operational_without_auth,
        "auth_providers": auth_providers,
        "payroll_tables": payroll_tables,
        "wage_column": wage_column,
        "lane_column": "data_lane" in person_cols,
        "email_column": any("email" in name.lower() for name in person_cols),
        "cr": None if cr is None else (cr[0], cr[1], cr[2]),
    }


def _forbidden(obj: object, trail: str = "") -> str:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                return trail + "." + str(key)
            found = _forbidden(value, trail + "." + str(key))
            if found:
                return found
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found = _forbidden(value, f"{trail}[{index}]")
            if found:
                return found
    return ""


def main() -> int:
    before = _ledger_counts()
    ledger_before = LEDGER.read_bytes()
    ledger = json.loads(ledger_before)
    oracle = _oracle()
    report = staff.read_stored_people()
    again = staff.read_stored_people()
    check("two reads match", report == again)
    check("read ok", report.get("ok") is True and report.get("cap") == "CAP-HR-01")
    check("read is stored people", report.get("read") == "stored_people")
    check(
        "lane column absent or named",
        report.get("lane_column") is oracle["lane_column"]
        and (
            (oracle["lane_column"] is False and report.get("data_lane") == "UNKNOWN")
            or oracle["lane_column"] is True
        ),
    )
    check("email column flag", report.get("email_column") is oracle["email_column"])
    check(
        "stored persons match",
        report.get("persons_stored") == oracle["persons"] == before[4] and oracle["persons"] > 0,
        str(report.get("persons_stored")),
    )
    check(
        "person partition matches",
        report.get("demo_persons") == oracle["demo_persons"]
        and report.get("operational_persons") == oracle["operational_persons"]
        and report.get("fixture_only_persons") == oracle["fixture_only_persons"]
        and report.get("unseated_persons") == oracle["unseated_persons"]
        and report.get("ended_only_persons") == oracle["ended_only_persons"]
        and report.get("demo_counted_as_operational") is False
        and (
            oracle["demo_persons"]
            + oracle["operational_persons"]
            + oracle["fixture_only_persons"]
            + oracle["unseated_persons"]
            + oracle["ended_only_persons"]
            == oracle["persons"]
        ),
        str(report.get("operational_persons")),
    )
    check(
        "roles positions assignments match",
        report.get("roles_stored") == oracle["roles"] == before[5]
        and report.get("positions_stored") == oracle["positions"] == before[6]
        and report.get("assignments_stored") == oracle["assignments"] == before[7],
    )
    check(
        "people are not roles",
        report.get("people_are_not_roles") is True
        and report.get("person_role_id_overlap") == oracle["overlap"] == 0
        and report.get("assignment_person_is_role") == oracle["person_is_role"] == 0
        and report.get("assignment_person_is_position") == oracle["person_is_position"] == 0
        and report.get("name_based_authorization") is False
        and report.get("authorization") == "NOT PERFORMED",
    )
    held = (
        oracle["missing_person"] == 0
        and oracle["missing_position"] == 0
        and oracle["missing_role"] == 0
        and oracle["missing_entity"] == 0
        and oracle["unknown_entity"] == 0
    )
    check(
        "seat boundary",
        report.get("boundary") == ("HELD" if held else "BREACHED")
        and report.get("assignment_missing_person") == oracle["missing_person"]
        and report.get("assignment_missing_position") == oracle["missing_position"]
        and report.get("position_missing_role") == oracle["missing_role"]
        and report.get("position_missing_entity") == oracle["missing_entity"]
        and report.get("position_entity_unknown") == oracle["unknown_entity"],
        str(report.get("boundary")),
    )
    check(
        "assignment partition matches",
        report.get("active_assignments") == oracle["active"]
        and report.get("ended_assignments") == oracle["ended"]
        and report.get("other_status_assignments")
        == oracle["assignments"] - oracle["active"] - oracle["ended"]
        and report.get("operational_active_assignments") == oracle["operational_active"]
        and report.get("fixture_active_assignments") == oracle["fixture_active"]
        and report.get("demo_on_plain_seat_assignments") == oracle["demo_on_plain"]
        and oracle["operational_active"] + oracle["fixture_active"] + oracle["demo_on_plain"]
        == oracle["active"],
    )
    check("entities match", report.get("entities") == oracle["entities"])
    check(
        "legal entities stay present when occupancy is empty",
        report.get("legal_entities") == len(oracle["entities"])
        and report.get("entities_not_legal") == oracle["not_legal"]
        and all(row.get("entity_absent") is False for row in report.get("entities") or [])
        and any(
            row.get("operational_occupancy") == "EMPTY" and row.get("operational_persons") == 0
            for row in oracle["entities"]
        ),
    )
    check(
        "legal name is a count",
        report.get("legal_name_present_operational") == oracle["legal_present"]
        and report.get("legal_name_absent_operational")
        == oracle["operational_persons"] - oracle["legal_present"],
    )
    check(
        "role aggregates match",
        report.get("role_status") == oracle["role_status"]
        and report.get("role_types") == oracle["role_types"]
        and report.get("roles_without_position") == oracle["roles_without_position"],
    )
    check(
        "auth counts omit identifiers",
        report.get("auth_identities_stored") == oracle["auth_stored"]
        and report.get("auth_missing_person") == oracle["auth_missing_person"]
        and report.get("persons_without_active_auth") == oracle["persons_without_auth"]
        and report.get("operational_persons_without_active_auth") == oracle["operational_without_auth"]
        and report.get("auth_providers") == oracle["auth_providers"]
        and report.get("identity_fields_selected") is False,
    )
    check(
        "no pay figure",
        report.get("pay_figure") is None
        and report.get("wage_column") is oracle["wage_column"]
        and report.get("payroll_tables") == oracle["payroll_tables"]
        and report.get("payroll_source") == "UNAVAILABLE"
        and report.get("payroll_cap") == "CAP-HR-04"
        and report.get("payroll_tested_here") is False,
    )
    check(
        "nothing created",
        report.get("persons_created") == 0
        and report.get("roles_created") == 0
        and report.get("positions_created") == 0
        and report.get("assignments_created") == 0
        and report.get("operating_board") is False
        and report.get("proved") is False
        and report.get("current") is False
        and report.get("catalog_write") is False
        and report.get("ledger_write") is False
        and report.get("payment_executed") is False
        and report.get("esb_write") is False
        and report.get("cr_resolved") is False,
    )
    check(
        "people gates stay unset",
        report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("operating_adoption") == "NOT MEASURED",
    )
    flags = report.get("honesty") or {}
    check(
        "ledger stays built",
        flags.get("maturity") == "BUILT"
        and ledger.get("CAP-HR-01", [None])[0] == "BUILT"
        and flags.get("proven") is False
        and flags.get("ready") is False
        and flags.get("ledger_rows") == 77
        and flags.get("model_c_maturity_raised") is False,
    )
    check(
        "cr stays open",
        flags.get("cr_id") == CR_ID
        and flags.get("cr_state") == "OPEN"
        and flags.get("cr_resolved") is False
        and flags.get("cr_next_action") == GAP
        and oracle["cr"] == ("OPEN", "NEEDS_ENGINEERING", GAP),
    )
    check("ids stay out of the report", _forbidden(report) == "", _forbidden(report))
    check("no email text", "@" not in json.dumps(report))
    reader = inspect.getsource(staff.read_stored_people)
    check("reader has no store statement", "INSERT INTO" not in reader and "UPDATE " not in reader)
    check("reader opens read-only", "mode=ro" in inspect.getsource(staff._ro))
    check("reader does not select a display name", "display_name" not in reader)
    check("reader does not select an auth identifier", "identifier" not in reader)
    refused = False
    try:
        staff.read_stored_people("/tmp/wolf-system/not-a-catalog.sqlite")
    except staff.StaffingError as exc:
        refused = exc.code == "not_beta"
    check("outside path refused", refused)
    try:
        staff.refuse_person_create({"create_person": True})
        check("person create refused", False, "no raise")
    except staff.StaffingError as exc:
        check("person create refused", exc.code == "person_create_refused", exc.code)
    try:
        assert_write_allowed(CATALOG)
        check("guard refuses canonical write", False, "no raise")
    except CanonicalGuardError as exc:
        text = str(exc)
        print(text)
        check(
            "guard refuses canonical write",
            "test process refuses canonical Beta write" in text,
            text,
        )
    insert_refused = False
    conn = sqlite3.connect(str(CATALOG))
    try:
        conn.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES ('PERS-PACK-F6-HR01', 'pack', NULL, 'ACTIVE', 'x', 'x')
            """
        )
        conn.commit()
    except sqlite3.Error:
        insert_refused = True
    finally:
        conn.close()
    check("guard denies person insert", insert_refused)

    after = _ledger_counts()
    check("evidence count unchanged", after[0] == before[0] == 4, str(after[0]))
    check("exception count unchanged", after[1] == before[1] == 3, str(after[1]))
    check("approval count unchanged", after[2] == before[2] == 9, str(after[2]))
    check(
        "preserved evidence stays invalidated",
        before[3] == "INVALIDATED" and after[3] == "INVALIDATED",
        str(after[3]),
    )
    check("persons unchanged", after[4] == before[4] == oracle["persons"], str(after[4]))
    check("roles unchanged", after[5] == before[5] == oracle["roles"], str(after[5]))
    check("positions unchanged", after[6] == before[6] == oracle["positions"], str(after[6]))
    check("assignments unchanged", after[7] == before[7] == oracle["assignments"], str(after[7]))
    check("ledger file unchanged", LEDGER.read_bytes() == ledger_before)
    print(
        "COUNTS stored={stored} demo={demo} operational={operational} "
        "fixture_only={fixture_only} roles={roles} positions={positions} "
        "assignments={assignments} active_operational={active_op} "
        "entities={entities} boundary={boundary}".format(
            stored=report.get("persons_stored"),
            demo=report.get("demo_persons"),
            operational=report.get("operational_persons"),
            fixture_only=report.get("fixture_only_persons"),
            roles=report.get("roles_stored"),
            positions=report.get("positions_stored"),
            assignments=report.get("assignments_stored"),
            active_op=report.get("operational_active_assignments"),
            entities=report.get("legal_entities"),
            boundary=report.get("boundary"),
        )
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
