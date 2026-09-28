#!/usr/bin/env python3
"""007 Role + Position + Assignment — idempotent Beta-only migration.

Conservative seed from Identity_Roles.csv + known Beta Persons.
Does NOT invent full roster. Does NOT model shareholders as jobs.
Does NOT build Scope/RBAC/Authority. Does NOT touch production.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "007_role_position_assignment.sql"
MIGRATION_ID = "007_role_position_assignment"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def upsert_role(conn, role_id, display_name, department_id, role_type, status, ts):
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name=excluded.display_name,
          department_id=excluded.department_id,
          role_type=excluded.role_type,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (role_id, display_name, department_id, role_type, status, ts, ts),
    )


def upsert_position(
    conn, position_id, role_id, entity_id, location_id, brand_id,
    department_id, position_label, status, fte, ts,
):
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id=excluded.entity_id,
          location_id=excluded.location_id,
          brand_id=excluded.brand_id,
          department_id=excluded.department_id,
          position_label=excluded.position_label,
          status=excluded.status,
          fte=excluded.fte,
          updated_at=excluded.updated_at
        """,
        (
            position_id, role_id, entity_id, location_id, brand_id,
            department_id, position_label, status, fte, ts, ts,
        ),
    )


def upsert_assignment(conn, assignment_id, person_id, position_id, start_at, end_at, status, is_primary, ts):
    # If conflict on unique primary active index, update existing row by assignment_id first
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          person_id=excluded.person_id,
          position_id=excluded.position_id,
          start_at=excluded.start_at,
          end_at=excluded.end_at,
          status=excluded.status,
          is_primary=excluded.is_primary,
          updated_at=excluded.updated_at
        """,
        (assignment_id, person_id, position_id, start_at, end_at, status, is_primary, ts, ts),
    )


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    start = "2026-09-16T00:00:00+08:00"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        # --- Roles from Identity_Roles.csv (IDs preserved) ---
        # ROLE-MATT display is operational title, not the person's name
        upsert_role(conn, "ROLE-MATT", "Owner / Executive", None, "EXECUTIVE", "SPECIFIED", ts)
        upsert_role(conn, "ROLE-AMG-GM", "General Manager", "DEPT-AMG-EXEC", "OPERATING", "SPECIFIED", ts)
        upsert_role(conn, "ROLE-BZG-HFB", "Head of F&B", "DEPT-BZG-FB", "OPERATING", "SPECIFIED", ts)
        upsert_role(conn, "ROLE-GGV-EDIT", "Video Editor", "DEPT-GGV-CONTENT", "OPERATING", "SPECIFIED", ts)
        upsert_role(conn, "ROLE-GGV-CREATIVE-DIRECTOR", "Creative Director", "DEPT-GGV-CONTENT", "OPERATING", "SPECIFIED", ts)
        upsert_role(conn, "ROLE-ENG", "Engineering (shared service)", None, "SHARED_SERVICE", "SPECIFIED", ts)
        # Conservative Beta content seats — titles TBD where canon lacks employment titles
        upsert_role(
            conn, "ROLE-CONTENT-MGMT", "Content Management (TBD title)",
            "DEPT-GGV-CONTENT", "OPERATING", "SPECIFIED", ts,
        )
        upsert_role(
            conn, "ROLE-CONTENT-CREW", "Content Crew (TBD title)",
            "DEPT-GGV-CONTENT", "OPERATING", "SPECIFIED", ts,
        )

        # --- Positions only for known Beta people (no invented empty GM seats) ---
        # Owner seat stewarded under ENT-GGV; group Scope comes later
        upsert_position(
            conn, "POS-OWNER-EXEC-1", "ROLE-MATT", "ENT-GGV",
            None, None, None,
            "Owner / Executive #1", "ACTIVE", 1.0, ts,
        )
        upsert_position(
            conn, "POS-CONTENT-MGMT-1", "ROLE-CONTENT-MGMT", "ENT-GGV",
            None, None, "DEPT-GGV-CONTENT",
            "Content Management #1 (TBD)", "ACTIVE", 1.0, ts,
        )
        upsert_position(
            conn, "POS-VIDEO-EDITOR-1", "ROLE-GGV-EDIT", "ENT-GGV",
            None, None, "DEPT-GGV-CONTENT",
            "Video Editor #1", "ACTIVE", 1.0, ts,
        )
        upsert_position(
            conn, "POS-GGV-CREATIVE-DIRECTOR-1", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV",
            None, None, "DEPT-GGV-CONTENT",
            "Creative Director #1", "ACTIVE", 1.0, ts,
        )
        upsert_position(
            conn, "POS-CONTENT-CREW-1", "ROLE-CONTENT-CREW", "ENT-GGV",
            None, None, "DEPT-GGV-CONTENT",
            "Content Crew #1 (TBD)", "ACTIVE", 1.0, ts,
        )

        # --- Assignments for known Persons ---
        # Owner settled 2026-09-24: Haikal on Creative Director (not Video Editor).
        haikal_ve_end = "2026-09-24T17:34:12+08:00"
        upsert_assignment(conn, "ASG-MATT-OWNER-1", "PERS-MATT", "POS-OWNER-EXEC-1", start, None, "ACTIVE", 1, ts)
        upsert_assignment(conn, "ASG-AMANDA-CM-1", "PERS-AMANDA", "POS-CONTENT-MGMT-1", start, None, "ACTIVE", 1, ts)
        upsert_assignment(conn, "ASG-HAIKAL-VE-1", "PERS-HAIKAL", "POS-VIDEO-EDITOR-1", start, haikal_ve_end, "ENDED", 0, ts)
        upsert_assignment(conn, "ASG-HAIKAL-CD-1", "PERS-HAIKAL", "POS-GGV-CREATIVE-DIRECTOR-1", haikal_ve_end, None, "ACTIVE", 1, ts)
        # 2026-09-28: Creative Director is the primary seat. Crew stays active, not primary.
        upsert_assignment(conn, "ASG-MISA-CC-1", "PERS-MISA", "POS-CONTENT-CREW-1", start, None, "ACTIVE", 0, ts)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, "Role+Position+Assignment; conservative Beta seed"),
        )
        conn.commit()

        for tname in ("org_roles", "org_positions", "org_assignments", "permissions", "org_persons"):
            n = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            print(f"  {tname}={n}")
        print("--- assignments ---")
        for r in conn.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, p.entity_id, r.display_name AS role_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            JOIN org_roles r ON r.role_id=p.role_id
            ORDER BY a.assignment_id
            """
        ):
            print(f"  {r['assignment_id']}: {r['person_id']} → {r['position_id']} ({r['entity_id']}) role={r['role_name']}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
