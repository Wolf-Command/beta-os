#!/usr/bin/env python3
"""Staff identity chain. Beta catalog is read-only here. Succession uses a temp copy."""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import identity, rbac  # noqa: E402
from core.staff_access import (  # noqa: E402
    CREATOR_DENIED,
    CREATOR_PERMISSIONS,
    CREATORS,
    FINANCE_EMAIL,
    HAIKAL_CD_ASSIGNMENT,
    HR_MAILBOXES,
    MISA_CD_ASSIGNMENT,
    MISA_EMAIL,
    MISA_PERSON,
    ROLE_CONTENT_CREATOR,
    ROLE_CREATIVE_DIRECTOR,
)
from core.staff_home import StaffHomeError, build_home  # noqa: E402
from core.wolf_shell import build_whoami  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
CONTENT = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def live() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def test_registry() -> None:
    conn = live()
    try:
        haikal = conn.execute(
            "SELECT status, is_primary, end_at FROM org_assignments WHERE assignment_id=?",
            (HAIKAL_CD_ASSIGNMENT,),
        ).fetchone()
        check(
            "Haikal CD assignment preserved",
            haikal is not None and haikal["status"] == "ACTIVE" and haikal["end_at"] is None and haikal["is_primary"] == 1,
        )
        person = identity.resolve_person_from_email("haikalqilbari123@gmail.com", conn=conn)
        check("Haikal email still Haikal", person is not None and person["person_id"] == "PERS-HAIKAL")
        misa_count = conn.execute(
            "SELECT COUNT(*) FROM org_persons WHERE lower(display_name)='misa'"
        ).fetchone()[0]
        check("one Misa person", misa_count == 1)
        misa = identity.resolve_person_from_email(MISA_EMAIL, conn=conn)
        check("Misa email binds existing person", misa is not None and misa["person_id"] == MISA_PERSON)
        primary = conn.execute(
            """
            SELECT a.assignment_id, p.role_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL AND a.is_primary=1
            """,
            (MISA_PERSON,),
        ).fetchone()
        check(
            "Misa primary is Creative Director",
            primary is not None
            and primary["assignment_id"] == MISA_CD_ASSIGNMENT
            and primary["role_id"] == ROLE_CREATIVE_DIRECTOR,
        )
        finance = identity.resolve_person_from_email(FINANCE_EMAIL, conn=conn)
        check("finance email is not bound", finance is None)
        for box in HR_MAILBOXES:
            address = box["address"].lower()
            row = conn.execute(
                "SELECT person_id, auth_identity_id, wolf_login FROM org_function_mailboxes WHERE address=?",
                (address,),
            ).fetchone()
            auth = identity.resolve_person_from_email(address, conn=conn)
            check(
                f"{box['function_key']} mailbox is not a login",
                row is not None
                and row["person_id"] is None
                and row["auth_identity_id"] is None
                and row["wolf_login"] == 0
                and auth is None,
            )
        for row in CREATORS:
            found = identity.resolve_person_from_email(row["email"], conn=conn)
            check(
                f"{row['display_name']} binds",
                found is not None
                and found["person_id"] == row["person_id"]
                and found["display_name"] == row["display_name"]
                and not found.get("legal_name"),
            )
            seat = conn.execute(
                """
                SELECT p.role_id
                FROM org_assignments a
                JOIN org_positions p ON p.position_id = a.position_id
                WHERE a.assignment_id=? AND a.status='ACTIVE' AND a.end_at IS NULL AND a.is_primary=1
                """,
                (row["assignment_id"],),
            ).fetchone()
            check(
                f"{row['display_name']} assignment is Content Creator",
                seat is not None and seat["role_id"] == ROLE_CONTENT_CREATOR,
            )
    finally:
        conn.close()


def test_permissions() -> None:
    conn = live()
    try:
        for row in CREATORS:
            pid = row["person_id"]
            for code in CREATOR_PERMISSIONS:
                check(f"{pid} allows {code}", rbac.can(pid, code, CONTENT, conn=conn))
            for code in CREATOR_DENIED:
                check(f"{pid} denies {code}", rbac.can(pid, code, CONTENT, conn=conn) is False)
            who = build_whoami(person_id=pid)
            check(f"{pid} lands on content", who.get("landing") == "/content-2.0")
            check(f"{pid} hides owner", "/wolf" not in (who.get("pages") or []))
            check(f"{pid} hides finance page", "/ggv/finance" not in (who.get("pages") or []))
            home = build_home(pid, conn=conn)
            check(f"{pid} my work is content creator", home.get("experience") == "content_creator")
            today = home["sections"][0]
            check(f"{pid} today names the empty seat", today.get("empty") is True and "this role" in str(today.get("empty_message")))
        misa_home = build_home(MISA_PERSON, conn=conn)
        check("Misa my work is creative director", misa_home.get("experience") == "creative_director")
        check(
            "Misa denies payment",
            rbac.can(MISA_PERSON, "payment.approve", CONTENT, conn=conn) is False
            and rbac.can(MISA_PERSON, "payment.execute", CONTENT, conn=conn) is False
            and rbac.can(MISA_PERSON, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=conn) is False,
        )
        who = build_whoami(person_id=MISA_PERSON)
        check("Misa lands on content", who.get("landing") == "/content-2.0")
    finally:
        conn.close()


def test_succession() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="staff-access-"))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    conn = sqlite3.connect(copy)
    conn.row_factory = sqlite3.Row
    try:
        original = CREATORS[0]["person_id"]
        check("original can read before end", rbac.can(original, "content.plan.read", CONTENT, conn=conn))
        conn.execute(
            """
            UPDATE org_assignments
            SET status='ENDED', end_at='2026-09-28T12:00:00+08:00', is_primary=0
            WHERE person_id=? AND status='ACTIVE'
            """,
            (original,),
        )
        conn.commit()
        check("ended assignment removes access", rbac.can(original, "content.plan.read", CONTENT, conn=conn) is False)
        kept = conn.execute(
            "SELECT status FROM org_assignments WHERE assignment_id=?",
            (CREATORS[0]["assignment_id"],),
        ).fetchone()
        check("ended row kept", kept is not None and kept["status"] == "ENDED")
        ts = "2026-09-28T12:01:00+08:00"
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES ('PERS-REPLACEMENT', 'Replacement', NULL, 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, department_id, position_label,
              status, fte, created_at, updated_at
            ) VALUES ('POS-CONTENT-CREATOR-REPL', ?, 'ENT-GGV', 'DEPT-GGV-CONTENT',
                      'Content Creator replacement', 'ACTIVE', 1.0, ?, ?)
            """,
            (ROLE_CONTENT_CREATOR, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES ('ASG-REPLACEMENT-CREATOR', 'PERS-REPLACEMENT', 'POS-CONTENT-CREATOR-REPL',
                      ?, NULL, 'ACTIVE', 1, ?, ?)
            """,
            (ts, ts, ts),
        )
        for scope_id in ("SCOPE-GGV-CONTENT", "SCOPE-GGV-CONTENT-LIBRARY"):
            conn.execute(
                """
                INSERT INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES ('ASG-REPLACEMENT-CREATOR', ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (scope_id, ts, ts, ts),
            )
        conn.commit()
        check(
            "replacement with the same role can read",
            rbac.can("PERS-REPLACEMENT", "content.plan.read", CONTENT, conn=conn),
        )
        check(
            "replacement is denied finance",
            rbac.can("PERS-REPLACEMENT", "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=conn) is False,
        )
        home = build_home("PERS-REPLACEMENT", conn=conn)
        check("replacement reaches my work", home.get("experience") == "content_creator")
        try:
            build_home(original, conn=conn)
            check("original no longer has an active seat", False)
        except StaffHomeError:
            check("original no longer has an active seat", True)
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    test_registry()
    test_permissions()
    test_succession()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
