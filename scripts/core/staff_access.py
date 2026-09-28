#!/usr/bin/env python3
"""Staff identity registration on the existing Person → Role → Assignment chain.

Decision served: owner brief 28 Sep 2026 10:09 WITA. Extends Wolf Core.
Not a second people system. Email binds an AuthIdentity. A role mailbox
is not a Wolf login and is not a Person.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from core import nas_library as nas
from core.scope import upsert_assignment_scope

TZ = ZoneInfo("Asia/Makassar")

ROLE_CONTENT_CREATOR = "ROLE-CONTENT-CREATOR"
ROLE_CREATIVE_DIRECTOR = "ROLE-GGV-CREATIVE-DIRECTOR"
ROLE_FINANCE = "ROLE-GGV-EXTERNAL-ACCOUNTANT"

CREATOR_PERMISSIONS: tuple[str, ...] = (
    "content.plan.read",
    "content.asset.upload",
    "evidence.record.submit",
    "approval.request",
    "work.read",
    "work.update",
)
# Floor the Creative Director role still lacked. Does not add publish,
# payment, finance, or owner authority.
CD_FLOOR_PERMISSIONS: tuple[str, ...] = CREATOR_PERMISSIONS + ("work.assign",)

CREATOR_SCOPES: tuple[str, ...] = (
    "SCOPE-GGV-CONTENT",
    "SCOPE-GGV-CONTENT-LIBRARY",
)

CREATOR_DENIED: tuple[str, ...] = (
    "content.plan.approve",
    "content.plan.create",
    "content.habitat.approve",
    "content.habitat.publish.request",
    "approval.decide",
    "finance.nota.read",
    "finance.nota.create",
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "governance.exception.authorise",
    "organisation.role.read",
    "organisation.person.read",
    "progress.read",
    "venue.close.read",
    "amg.day.operator",
    "core.operator",
    "work.assign",
)

FINANCE_EMAIL = "laluzayen@gmail.com"

# Role mailboxes. Not AuthIdentities. Not Persons.
HR_MAILBOXES: tuple[dict[str, str], ...] = (
    {
        "mailbox_id": "MBX-HR-ATRIUM",
        "function_key": "HR",
        "address": "hr@atriumlombok.com",
    },
    {
        "mailbox_id": "MBX-RECRUITMENT-ATRIUM",
        "function_key": "RECRUITMENT",
        "address": "recruitment@atriumlombok.com",
    },
)

# Display names are the short names the owner gave. No surnames.
CREATORS: tuple[dict[str, str], ...] = (
    {
        "person_id": "PERS-YUDI",
        "display_name": "Yudi",
        "email": "widiatmika.11@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-1",
        "assignment_id": "ASG-YUDI-CREATOR-1",
        "auth_identity_id": "AUTH-YUDI-EMAIL",
    },
    {
        "person_id": "PERS-GERY",
        "display_name": "Gery",
        "email": "mr.gerryarfanata@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-2",
        "assignment_id": "ASG-GERY-CREATOR-1",
        "auth_identity_id": "AUTH-GERY-EMAIL",
    },
    {
        "person_id": "PERS-ALAM",
        "display_name": "Alam",
        "email": "alamprojects26@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-3",
        "assignment_id": "ASG-ALAM-CREATOR-1",
        "auth_identity_id": "AUTH-ALAM-EMAIL",
    },
    {
        "person_id": "PERS-TJ",
        "display_name": "TJ",
        "email": "tejasaputra.wahyuhidayat@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-4",
        "assignment_id": "ASG-TJ-CREATOR-1",
        "auth_identity_id": "AUTH-TJ-EMAIL",
    },
    {
        "person_id": "PERS-NATA",
        "display_name": "Nata",
        "email": "omnia.folio@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-5",
        "assignment_id": "ASG-NATA-CREATOR-1",
        "auth_identity_id": "AUTH-NATA-EMAIL",
    },
    {
        "person_id": "PERS-RAPP",
        "display_name": "Rapp",
        "email": "evetrovert@gmail.com",
        "position_id": "POS-CONTENT-CREATOR-6",
        "assignment_id": "ASG-RAPP-CREATOR-1",
        "auth_identity_id": "AUTH-RAPP-EMAIL",
    },
)

MISA_PERSON = "PERS-MISA"
MISA_EMAIL = "mlsary111@gmail.com"
MISA_CD_POSITION = "POS-GGV-CREATIVE-DIRECTOR-2"
MISA_CD_ASSIGNMENT = "ASG-MISA-CD-1"
MISA_CREW_ASSIGNMENT = "ASG-MISA-CC-1"
HAIKAL_CD_ASSIGNMENT = "ASG-HAIKAL-CD-1"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _exec(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> None:
    conn.execute(sql, params)


def ensure_mailbox_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS org_function_mailboxes (
          mailbox_id TEXT PRIMARY KEY,
          function_key TEXT NOT NULL,
          address TEXT NOT NULL,
          purpose TEXT NOT NULL,
          wolf_login INTEGER NOT NULL DEFAULT 0 CHECK (wolf_login IN (0, 1)),
          person_id TEXT,
          auth_identity_id TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )


def finance_search(conn: sqlite3.Connection) -> dict[str, Any]:
    """Find an existing finance person. Does not create one."""
    email = FINANCE_EMAIL.lower()
    by_email = conn.execute(
        """
        SELECT p.person_id, p.display_name
        FROM org_auth_identities a
        JOIN org_persons p ON p.person_id = a.person_id
        WHERE a.provider='email' AND lower(a.identifier)=?
        """,
        (email,),
    ).fetchone()
    by_name = conn.execute(
        """
        SELECT person_id, display_name
        FROM org_persons
        WHERE lower(display_name) LIKE '%zayen%'
           OR lower(ifnull(legal_name, '')) LIKE '%zayen%'
           OR lower(display_name) LIKE '%atrium finance%'
           OR lower(ifnull(legal_name, '')) LIKE '%atrium finance%'
        """
    ).fetchall()
    role = conn.execute(
        "SELECT role_id, display_name FROM org_roles WHERE role_id=?",
        (ROLE_FINANCE,),
    ).fetchone()
    return {
        "email": email,
        "person_by_email": None if by_email is None else by_email[0],
        "name_matches": [row[0] for row in by_name],
        "finance_role_id": None if role is None else role[0],
        "finance_role_label": None if role is None else role[1],
        "bound": False,
        "reason": (
            "No stored person matches this email or a Zayen / Atrium Finance name. "
            "Display name was not invented. AuthIdentity was not created."
        ),
    }


def _grant(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> None:
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
        (code,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"missing permission {code}")
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, row[0], ts, ts),
    )


def _role_scopes(conn: sqlite3.Connection, role_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT s.scope_id
        FROM org_assignment_scopes s
        JOIN org_assignments a ON a.assignment_id = s.assignment_id
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
          AND s.status = 'ACTIVE'
          AND s.end_at IS NULL
        ORDER BY s.scope_id
        """,
        (role_id,),
    ).fetchall()
    found = [str(row[0]) for row in rows if row[0]]
    if found:
        return found
    return [
        "SCOPE-GGV-CONTENT",
        "SCOPE-GGV-CONTENT-LIBRARY",
        nas.CONTENT_ALL_BRANDS_SCOPE,
    ]


def _seat(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    display_name: str,
    email: str,
    auth_identity_id: str,
    position_id: str,
    position_label: str,
    role_id: str,
    assignment_id: str,
    scopes: list[str],
    ts: str,
    primary: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO NOTHING
        """,
        (person_id, display_name, ts, ts),
    )
    existing = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (email.lower(),),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (auth_identity_id, person_id, email.lower(), ts, ts),
        )
    elif str(existing[0]) != person_id:
        raise RuntimeError(f"{email.lower()} is already bound to {existing[0]}")
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, department_id, position_label,
          status, fte, created_at, updated_at
        ) VALUES (?, ?, 'ENT-GGV', 'DEPT-GGV-CONTENT', ?, 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (position_id, role_id, position_label, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', ?, ?, ?)
        ON CONFLICT(assignment_id) DO NOTHING
        """,
        (assignment_id, person_id, position_id, ts, 1 if primary else 0, ts, ts),
    )
    for scope_id in scopes:
        upsert_assignment_scope(conn, assignment_id, scope_id, ts, ts)


def apply(conn: sqlite3.Connection) -> dict[str, Any]:
    """Idempotent registry write. Does not invent a finance person."""
    ts = now_iso()
    finance = finance_search(conn)
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Content Creator', 'DEPT-GGV-CONTENT', 'OPERATING', 'SPECIFIED', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name='Content Creator',
          updated_at=excluded.updated_at
        """,
        (ROLE_CONTENT_CREATOR, ts, ts),
    )
    for code in CREATOR_PERMISSIONS:
        _grant(conn, ROLE_CONTENT_CREATOR, code, ts)
    for code in CD_FLOOR_PERMISSIONS:
        _grant(conn, ROLE_CREATIVE_DIRECTOR, code, ts)

    for row in CREATORS:
        _seat(
            conn,
            person_id=row["person_id"],
            display_name=row["display_name"],
            email=row["email"],
            auth_identity_id=row["auth_identity_id"],
            position_id=row["position_id"],
            position_label=f"Content Creator {row['position_id'][-1]}",
            role_id=ROLE_CONTENT_CREATOR,
            assignment_id=row["assignment_id"],
            scopes=list(CREATOR_SCOPES),
            ts=ts,
            primary=True,
        )

    misa = conn.execute(
        "SELECT person_id, display_name FROM org_persons WHERE person_id=?",
        (MISA_PERSON,),
    ).fetchone()
    if misa is None:
        raise RuntimeError("PERS-MISA is not in the registry")
    cd_scopes = _role_scopes(conn, ROLE_CREATIVE_DIRECTOR)
    _seat(
        conn,
        person_id=MISA_PERSON,
        display_name=str(misa[1] or "Misa"),
        email=MISA_EMAIL,
        auth_identity_id="AUTH-MISA-EMAIL",
        position_id=MISA_CD_POSITION,
        position_label="Creative Director #2",
        role_id=ROLE_CREATIVE_DIRECTOR,
        assignment_id=MISA_CD_ASSIGNMENT,
        scopes=cd_scopes,
        ts=ts,
        primary=True,
    )
    conn.execute(
        """
        UPDATE org_assignments
        SET is_primary=0, updated_at=?
        WHERE person_id=? AND assignment_id!=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ts, MISA_PERSON, MISA_CD_ASSIGNMENT),
    )
    conn.execute(
        """
        UPDATE org_assignments
        SET is_primary=1, updated_at=?
        WHERE assignment_id=? AND status='ACTIVE'
        """,
        (ts, MISA_CD_ASSIGNMENT),
    )

    ensure_mailbox_table(conn)
    for box in HR_MAILBOXES:
        address = box["address"].lower()
        stolen = conn.execute(
            """
            SELECT auth_identity_id FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (address,),
        ).fetchone()
        if stolen is not None:
            raise RuntimeError(f"role mailbox {address} is already an AuthIdentity")
        conn.execute(
            """
            INSERT INTO org_function_mailboxes (
              mailbox_id, function_key, address, purpose, wolf_login,
              person_id, auth_identity_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, NULL, NULL, 'ACTIVE', ?, ?)
            ON CONFLICT(mailbox_id) DO UPDATE SET
              function_key=excluded.function_key,
              address=excluded.address,
              wolf_login=0,
              person_id=NULL,
              auth_identity_id=NULL,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (
                box["mailbox_id"],
                box["function_key"],
                address,
                "Role mailbox. Not a Wolf login. Access follows an authorised human's active HR assignment.",
                ts,
                ts,
            ),
        )

    haikal = conn.execute(
        "SELECT status, is_primary, end_at FROM org_assignments WHERE assignment_id=?",
        (HAIKAL_CD_ASSIGNMENT,),
    ).fetchone()
    conn.commit()
    return {
        "finance": finance,
        "haikal_cd": None
        if haikal is None
        else {"status": haikal[0], "is_primary": haikal[1], "end_at": haikal[2]},
        "creators": [row["person_id"] for row in CREATORS],
        "misa_assignment": MISA_CD_ASSIGNMENT,
        "hr_mailboxes": [box["address"].lower() for box in HR_MAILBOXES],
        "staff_ready": False,
        "human_commissioned": False,
    }
