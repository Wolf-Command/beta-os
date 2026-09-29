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
ROLE_ATRIUM_FINANCE = "ROLE-AMG-FINANCE-OFFICER"
ROLE_ATRIUM_FINANCIAL_CONTROLLER = "ROLE-AMG-FINANCIAL-CONTROLLER"
ZAYEN_FC_ASSIGNMENT = "ASG-ZAYEN-FC-1"
ZAYEN_FC_POSITION = "POS-AMG-FINANCIAL-CONTROLLER-1"
ROLE_GGV_FINANCE_OPERATOR = "ROLE-GGV-FINANCE-OPERATOR"
GGV_FINANCE_HREF = "/ggv/finance"
AMANDA_PERSON = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"
AMANDA_FINANCE_POSITION = "POS-GGV-FINANCE-OPERATOR-1"
AMANDA_FINANCE_ASSIGNMENT = "ASG-AMANDA-GGV-FIN-1"
ATRIUM_FINANCE_HREF = "/amg/finance"
SCOPE_AMG_FINANCE = "SCOPE-AMG-FINANCE"
ENTITY_AMG = "ENT-AMG"

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

# Team scopes + all active content brands (HUMFIX-1). Brand ACL is role-based.
CREATOR_SCOPES: tuple[str, ...] = (
    "SCOPE-GGV-CONTENT",
    "SCOPE-GGV-CONTENT-LIBRARY",
    nas.CONTENT_ALL_BRANDS_SCOPE,
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
ZAYEN_PERSON = "PERS-ZAYEN"
ZAYEN_POSITION = "POS-AMG-FINANCE-OFFICER-1"
ZAYEN_ASSIGNMENT = "ASG-ZAYEN-FIN-1"
ZAYEN_AUTH = "AUTH-ZAYEN-EMAIL"

# Route map is atrium-finance server/routeAccess.ts plus the General Accountant
# pillar flags. Only the actions named for this seat are granted.
# Source-document upload has no /api route, so no upload grant is created.
ATRIUM_GRANTS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "PERM-ATRIUM-BOARD-READ",
        "atrium.board.read",
        "atrium.board",
        "read",
        "GET /api/dashboard. Command centre view only.",
    ),
    (
        "PERM-ATRIUM-LEDGER-READ",
        "atrium.ledger.read",
        "atrium.ledger",
        "read",
        "GET /api/journals, /api/journals/:id, /api/ledger, /api/trial-balance.",
    ),
    (
        "PERM-ATRIUM-JOURNAL-DRAFT",
        "atrium.journal.draft",
        "atrium.journal",
        "draft",
        "POST /api/journals and POST /api/journals/:id/validate. Not approve, post, or reverse.",
    ),
    (
        "PERM-ATRIUM-REPORT-READ",
        "atrium.report.read",
        "atrium.report",
        "read",
        "GET /api/reports/financial-statements, /api/reports/usali, /api/reports/drilldown.",
    ),
    (
        "PERM-ATRIUM-COA-READ",
        "atrium.coa.read",
        "atrium.coa",
        "read",
        "GET /api/accounts. Chart read only.",
    ),
)
ATRIUM_HELD_BACK: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "PERM-ATRIUM-JOURNAL-POST",
        "atrium.journal.post",
        "atrium.journal",
        "post",
        "POST /api/journals/:id/post. Held — open Matt policy (HUMFIX-1).",
    ),
)
# Approve is granted to Financial Controller (HUMFIX-1) with SoD. Kept here for docs only.
ATRIUM_APPROVE_PERM: tuple[str, str, str, str, str] = (
    "PERM-ATRIUM-JOURNAL-APPROVE",
    "atrium.journal.approve",
    "atrium.journal",
    "approve",
    "POST /api/journals/:id/approve. FC only; SoD preparer≠approver.",
)
ATRIUM_SUBMIT = "approval.request"
# HUMFIX-1: approve removed from denied — granted to Financial Controller with SoD.
# Post stays denied (open policy for Matt).
ATRIUM_DENIED: tuple[str, ...] = (
    "atrium.journal.post",
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "finance.policy.admin",
    "finance.nota.read",
    "finance.nota.create",
    "organisation.role.read",
    "organisation.person.read",
    "progress.read",
    "amg.day.operator",
    "core.operator",
    "approval.decide",
    "content.plan.read",
    "governance.exception.authorise",
)

CREW_END_REASON = (
    "Content Crew is a 16 Sep 2026 TBD seed. Creative Director is the live seat. "
    "The crew grants are not on that role. Ended so the old seat does not keep access."
)
DAY_END_REASON = (
    "Atrium day-operator seat is a Beta fixture from 22 Sep 2026, not a live hotel assignment. "
    "Ended so hotel day access does not stay on this person."
)
MISA_DAY_ASSIGNMENT = "ASG-AMG-DAY-MISA"

ATRIUM_PAGE_PATHS = frozenset(
    {
        "/amg/finance",
        "/amg/finance/ledger",
        "/amg/finance/accounts",
        "/amg/finance/journals",
        "/amg/finance/reports",
        "/amg/finance/approvals",
        "/amg-finance",
        "/amg-finance.html",
        "/dashboards/amg-finance.html",
        "/api/amg/finance",
        "/api/amg/finance/ledger",
        "/api/amg/finance/accounts",
        "/api/amg/finance/journals",
        "/api/amg/finance/reports",
        "/api/amg/finance/approvals",
    }
)
ATRIUM_CHROME_PATHS = frozenset(
    {
        "/api/health",
        "/api/wolf/shell-whoami",
        "/api/staff/home",
        "/my-work",
        "/my-work.html",
        "/signout",
        "/wolf-tokens.css",
        "/assets/wolf-shell.css",
        "/assets/sidenav.js",
        "/assets/wolf-truth.css",
        "/assets/wolf-truth.js",
        "/api/dashboard-truth/stamp",
    }
)

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
HAIKAL_PERSON = "PERS-HAIKAL"

# Same role as Haikal and Misa. Not a person-named role.
CREATIVE_DIRECTORS: tuple[dict[str, Any], ...] = (
    {
        "person_id": "PERS-ZARAH",
        "display_name": "Zarah",
        "email": "zarah.lestrange@gmail.com",
        "name_tokens": ("zarah", "lestrange"),
        "position_id": "POS-GGV-CREATIVE-DIRECTOR-3",
        "position_label": "Creative Director #3",
        "assignment_id": "ASG-ZARAH-CD-1",
        "auth_identity_id": "AUTH-ZARAH-EMAIL",
    },
    {
        "person_id": "PERS-FRAIL",
        "display_name": "Frail",
        "email": "frail.bongat@icloud.com",
        "name_tokens": ("frail", "bongat"),
        "position_id": "POS-GGV-CREATIVE-DIRECTOR-4",
        "position_label": "Creative Director #4",
        "assignment_id": "ASG-FRAIL-CD-1",
        "auth_identity_id": "AUTH-FRAIL-EMAIL",
    },
)


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
        (ROLE_ATRIUM_FINANCE,),
    ).fetchone()
    bound = by_email is not None
    return {
        "email": email,
        "person_by_email": None if by_email is None else by_email[0],
        "name_matches": [row[0] for row in by_name],
        "finance_role_id": None if role is None else role[0],
        "finance_role_label": None if role is None else role[1],
        "bound": bound,
        "reason": (
            "AuthIdentity is stored. Access follows the active Atrium Finance Officer assignment."
            if bound
            else (
                "No stored person matches this email or a Zayen / Atrium Finance name. "
                "Display name was not invented. AuthIdentity was not created."
            )
        ),
    }


def _ensure_end_reason(conn: sqlite3.Connection) -> None:
    cols = {str(row[1]) for row in conn.execute("PRAGMA table_info(org_assignments)")}
    if "end_reason" not in cols:
        conn.execute("ALTER TABLE org_assignments ADD COLUMN end_reason TEXT")


def _end_assignment(conn: sqlite3.Connection, assignment_id: str, reason: str, ts: str) -> None:
    row = conn.execute(
        "SELECT status, end_at, end_reason FROM org_assignments WHERE assignment_id=?",
        (assignment_id,),
    ).fetchone()
    if row is None:
        return
    if str(row[0] or "") == "ENDED" or row[1]:
        if not str(row[2] or "").strip():
            conn.execute(
                "UPDATE org_assignments SET end_reason=?, updated_at=? WHERE assignment_id=?",
                (reason, ts, assignment_id),
            )
        return
    conn.execute(
        """
        UPDATE org_assignments
        SET status='ENDED', end_at=?, is_primary=0, end_reason=?, updated_at=?
        WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ts, reason, ts, assignment_id),
    )
    conn.execute(
        """
        UPDATE org_assignment_scopes
        SET status='ENDED', end_at=?, updated_at=?
        WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ts, ts, assignment_id),
    )


def _ensure_permission(
    conn: sqlite3.Connection,
    permission_id: str,
    code: str,
    resource: str,
    action: str,
    description: str,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code,
          description=excluded.description,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (permission_id, code, resource, action, description, ts, ts),
    )


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
    _attach_scopes_once(conn, assignment_id, scopes, ts)


def officer_must_deny(person_id: str | None, path: str, conn: sqlite3.Connection) -> bool:
    """Atrium Finance Officer, and only that role, cannot leave Atrium Finance."""
    pid = (person_id or "").strip()
    if not pid:
        return False
    rows = conn.execute(
        """
        SELECT DISTINCT pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
        """,
        (pid,),
    ).fetchall()
    roles = {str(row[0]) for row in rows if row[0]}
    if roles not in ({ROLE_ATRIUM_FINANCE}, {ROLE_ATRIUM_FINANCIAL_CONTROLLER}):
        return False
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    base = raw.rstrip("/") or "/"
    if base in ATRIUM_PAGE_PATHS or raw in ATRIUM_PAGE_PATHS:
        return False
    if ".." not in base and (
        base.startswith("/amg/finance/") or base.startswith("/api/amg/finance/")
    ):
        return False
    if base in ATRIUM_CHROME_PATHS or raw in ATRIUM_CHROME_PATHS:
        return False
    if base.startswith("/assets/"):
        return False
    return True


# Human page for the active primary assignment. Scope stays on the assignment.
# This does not add a grant. Owner stays on /wolf.
HUMAN_PAGE_BY_ROLE: dict[str, str] = {
    "ROLE-GGV-CREATIVE-DIRECTOR": "/content-2.0",
    "ROLE-CONTENT": "/content-2.0",
    "ROLE-CONTENT-MGMT": "/content-2.0",
    "ROLE-CONTENT-CREW": "/content-2.0",
    "ROLE-CONTENT-CREATOR": "/content-2.0",
    "ROLE-BZG-FB-OPS-LEAD": "/bzg/uma-blu",
    "ROLE-GGV-LEAD": "/ggv-ops-pack",
    "ROLE-AMG-OPS": "/amg-ops-pack",
    "ROLE-AMG-GM": "/amg-ops-pack",
    "ROLE-MATT": "/wolf",
    "ROLE-OWNER": "/wolf",
    "ROLE-AMG-FINANCE-OFFICER": ATRIUM_FINANCE_HREF,
    "ROLE-AMG-FINANCIAL-CONTROLLER": ATRIUM_FINANCE_HREF,
    "ROLE-GGV-FINANCE-OPERATOR": GGV_FINANCE_HREF,
    "ROLE-GGV-EXTERNAL-ACCOUNTANT": GGV_FINANCE_HREF,
}

HUMAN_PAGE_LABEL: dict[str, str] = {
    "/amg/finance": "Atrium Finance",
    "/content-2.0": "Content",
    "/bzg/uma-blu": "Uma Blu",
    "/ggv/finance": "GGV Finance",
    "/ggv-ops-pack": "GGV",
    "/wolf": "Owner",
    "/amg-ops-pack": "Atrium",
    "/my-work": "My Work",
}

ENTRY_PATHS = frozenset({"/", "/index.html"})


def normalise_human_page(path: str | None) -> str:
    raw = (path or "").split("?")[0].split("#")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw.startswith("/dashboards/"):
        raw = raw[len("/dashboards"):] or "/"
    if raw.endswith(".html"):
        raw = raw[: -len(".html")] or "/"
    return raw.rstrip("/") or "/"


def active_assignment_pages(person_id: str | None, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Active assignments, primary first. One human page per role. No new grant."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    rows = conn.execute(
        """
        SELECT a.assignment_id, a.is_primary, pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
        ORDER BY a.is_primary DESC, a.assignment_id
        """,
        (pid,),
    ).fetchall()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        role = str(row[2] or "")
        href = HUMAN_PAGE_BY_ROLE.get(role)
        if not href or href in seen:
            continue
        seen.add(href)
        out.append(
            {
                "assignment_id": str(row[0]),
                "role_id": role,
                "href": href,
                "label": HUMAN_PAGE_LABEL.get(href, "your workspace"),
                "primary": "1" if int(row[1] or 0) == 1 else "0",
            }
        )
    return out


def primary_human_landing(person_id: str | None, conn: sqlite3.Connection) -> str | None:
    """AuthIdentity is already resolved to person_id. Primary assignment picks the page."""
    pages = active_assignment_pages(person_id, conn)
    if not pages:
        return None
    primary = next((page for page in pages if page["primary"] == "1"), pages[0])
    return primary["href"]


def assignment_allows_page(person_id: str | None, path: str, conn: sqlite3.Connection) -> bool:
    want = normalise_human_page(path)
    return any(normalise_human_page(page["href"]) == want for page in active_assignment_pages(person_id, conn))


def _seat_zayen(conn: sqlite3.Connection, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Atrium Finance Officer', NULL, 'OPERATING', 'SPECIFIED', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name='Atrium Finance Officer',
          role_type='OPERATING',
          updated_at=excluded.updated_at
        """,
        (ROLE_ATRIUM_FINANCE, ts, ts),
    )
    for row in ATRIUM_GRANTS + ATRIUM_HELD_BACK:
        _ensure_permission(conn, row[0], row[1], row[2], row[3], row[4], ts)
    for row in ATRIUM_GRANTS:
        _grant(conn, ROLE_ATRIUM_FINANCE, row[1], ts)
    _grant(conn, ROLE_ATRIUM_FINANCE, ATRIUM_SUBMIT, ts)
    held_ids = [row[0] for row in ATRIUM_HELD_BACK]
    conn.execute(
        f"""
        DELETE FROM org_role_permissions
        WHERE role_id=? AND permission_id IN ({",".join("?" for _ in held_ids)})
        """,
        (ROLE_ATRIUM_FINANCE, *held_ids),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'structural', 'Atrium Finance only', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          display_name='Atrium Finance only', status='ACTIVE', updated_at=excluded.updated_at
        """,
        (SCOPE_AMG_FINANCE, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_AMG_FINANCE, ENTITY_AMG, ts),
    )
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, 'Zayen', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO NOTHING
        """,
        (ZAYEN_PERSON, ts, ts),
    )
    existing = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (FINANCE_EMAIL,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (ZAYEN_AUTH, ZAYEN_PERSON, FINANCE_EMAIL, ts, ts),
        )
    elif str(existing[0]) != ZAYEN_PERSON:
        raise RuntimeError(f"{FINANCE_EMAIL} is already bound to {existing[0]}")
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, 'Atrium Finance Officer', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id=excluded.entity_id,
          brand_id=NULL,
          location_id=NULL,
          position_label='Atrium Finance Officer',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (ZAYEN_POSITION, ROLE_ATRIUM_FINANCE, ENTITY_AMG, ts, ts),
    )
    # MYWORK-1: Financial Controller is the live seat. Do not revive the ended Officer row.
    fc = conn.execute(
        """
        SELECT status, end_at FROM org_assignments WHERE assignment_id=?
        """,
        (ZAYEN_FC_ASSIGNMENT,),
    ).fetchone()
    if fc and str(fc[0] or "") == "ACTIVE" and not fc[1]:
        _attach_scopes_once(conn, ZAYEN_FC_ASSIGNMENT, [SCOPE_AMG_FINANCE], ts)
        return
    ended = conn.execute(
        """
        SELECT status, end_at FROM org_assignments WHERE assignment_id=?
        """,
        (ZAYEN_ASSIGNMENT,),
    ).fetchone()
    if ended and (str(ended[0] or "") == "ENDED" or ended[1]):
        # History preserved — leave ended Officer assignment alone.
        return
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE',
          end_at=NULL,
          is_primary=1,
          updated_at=excluded.updated_at
        """,
        (ZAYEN_ASSIGNMENT, ZAYEN_PERSON, ZAYEN_POSITION, ts, ts, ts),
    )
    _attach_scopes_once(conn, ZAYEN_ASSIGNMENT, [SCOPE_AMG_FINANCE], ts)


def _seat_ggv_finance_operator(conn: sqlite3.Connection, ts: str) -> str:
    """Bind the existing Amanda person to the generic GGV Finance Operator role.

    The role is not named for her. Her content seat stays primary.
    """
    from core import ggv_finance_invoice as invoices

    invoices.seed_operator_role(conn)
    bound = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (AMANDA_EMAIL,),
    ).fetchone()
    if bound is None:
        raise RuntimeError(f"{AMANDA_EMAIL} has no AuthIdentity. Not creating a person.")
    if str(bound[0]) != AMANDA_PERSON:
        raise RuntimeError(f"{AMANDA_EMAIL} is already bound to {bound[0]}")
    person = conn.execute(
        "SELECT person_id FROM org_persons WHERE person_id=?",
        (AMANDA_PERSON,),
    ).fetchone()
    if person is None:
        raise RuntimeError(f"{AMANDA_PERSON} is missing. Not creating a second person.")
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, 'ENT-GGV', NULL, NULL, NULL, 'GGV Finance Operator', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id='ENT-GGV',
          position_label='GGV Finance Operator',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (AMANDA_FINANCE_POSITION, ROLE_GGV_FINANCE_OPERATOR, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 0, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE',
          end_at=NULL,
          is_primary=0,
          updated_at=excluded.updated_at
        """,
        (AMANDA_FINANCE_ASSIGNMENT, AMANDA_PERSON, AMANDA_FINANCE_POSITION, ts, ts, ts),
    )
    _attach_scopes_once(conn, AMANDA_FINANCE_ASSIGNMENT, ["SCOPE-GGV-FINANCE"], ts)
    return AMANDA_FINANCE_ASSIGNMENT


def _search_person(conn: sqlite3.Connection, email: str, name_tokens: tuple[str, ...]) -> dict[str, Any]:
    """Existing Person by email or name. Does not insert."""
    email_l = email.lower()
    by_email = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (email_l,),
    ).fetchone()
    clauses: list[str] = []
    params: list[str] = []
    for token in name_tokens:
        tok = token.lower()
        clauses.append("lower(display_name)=?")
        params.append(tok)
        clauses.append("lower(ifnull(legal_name, ''))=?")
        params.append(tok)
        clauses.append("lower(display_name) LIKE ?")
        params.append(f"%{tok}%")
        clauses.append("lower(ifnull(legal_name, '')) LIKE ?")
        params.append(f"%{tok}%")
    rows = conn.execute(
        f"SELECT person_id FROM org_persons WHERE {' OR '.join(clauses)}",
        tuple(params),
    ).fetchall()
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        pid = str(row[0])
        if pid not in seen:
            seen.add(pid)
            names.append(pid)
    return {
        "email": email_l,
        "person_by_email": None if by_email is None else str(by_email[0]),
        "name_matches": names,
    }


def _attach_scopes_once(
    conn: sqlite3.Connection, assignment_id: str, scopes: list[str], ts: str
) -> None:
    """Attach missing scopes. A second apply does not add a second row."""
    start = conn.execute(
        "SELECT start_at FROM org_assignments WHERE assignment_id=?",
        (assignment_id,),
    ).fetchone()
    start_at = str(start[0]) if start and start[0] else ts
    for scope_id in scopes:
        existing = conn.execute(
            """
            SELECT 1 FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (assignment_id, scope_id),
        ).fetchone()
        if existing is not None:
            continue
        upsert_assignment_scope(conn, assignment_id, scope_id, start_at, ts)


def _seat_creative_directors(
    conn: sqlite3.Connection, scopes: list[str], ts: str
) -> list[dict[str, Any]]:
    """Seat Zarah and Frail on the existing Creative Director role.

    Search email and name first. Reuse a person. Do not add a role or a grant.
    """
    reports: list[dict[str, Any]] = []
    for seat in CREATIVE_DIRECTORS:
        found = _search_person(conn, seat["email"], tuple(seat["name_tokens"]))
        email_pid = found["person_by_email"]
        names = list(found["name_matches"])
        if email_pid and any(pid != email_pid for pid in names):
            raise RuntimeError(
                f"{found['email']} is bound to {email_pid} but the name also matches {names}"
            )
        if email_pid:
            person_id = email_pid
            reused = True
        elif len(names) > 1:
            raise RuntimeError(f"{seat['display_name']} matches more than one person: {names}")
        elif len(names) == 1:
            person_id = names[0]
            reused = True
        else:
            person_id = str(seat["person_id"])
            reused = False
            clash = conn.execute(
                "SELECT person_id FROM org_persons WHERE person_id=?",
                (person_id,),
            ).fetchone()
            if clash is not None:
                raise RuntimeError(f"{person_id} already exists without this email or name")
            conn.execute(
                """
                INSERT INTO org_persons (
                  person_id, display_name, legal_name, status, created_at, updated_at
                ) VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (person_id, seat["display_name"], ts, ts),
            )
        bound = conn.execute(
            """
            SELECT person_id, auth_identity_id FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (found["email"],),
        ).fetchone()
        if bound is None:
            taken = conn.execute(
                "SELECT identifier FROM org_auth_identities WHERE auth_identity_id=?",
                (seat["auth_identity_id"],),
            ).fetchone()
            if taken is not None:
                raise RuntimeError(f"{seat['auth_identity_id']} is already an AuthIdentity")
            conn.execute(
                """
                INSERT INTO org_auth_identities (
                  auth_identity_id, person_id, provider, identifier, status,
                  is_primary, created_at, updated_at
                ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
                """,
                (seat["auth_identity_id"], person_id, found["email"], ts, ts),
            )
            auth_identity_id = str(seat["auth_identity_id"])
        else:
            if str(bound[0]) != person_id:
                raise RuntimeError(f"{found['email']} is already bound to {bound[0]}")
            auth_identity_id = str(bound[1])
        active = conn.execute(
            """
            SELECT a.assignment_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.person_id=? AND p.role_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
            """,
            (person_id, ROLE_CREATIVE_DIRECTOR),
        ).fetchone()
        ended = False
        if active is not None:
            assignment_id = str(active[0])
        else:
            assignment_id = str(seat["assignment_id"])
            owner = conn.execute(
                "SELECT person_id, status FROM org_assignments WHERE assignment_id=?",
                (assignment_id,),
            ).fetchone()
            if owner is not None and str(owner[0]) != person_id:
                raise RuntimeError(f"{assignment_id} belongs to {owner[0]}")
            if owner is not None and str(owner[1] or "") == "ENDED":
                ended = True
            else:
                pos_owner = conn.execute(
                    "SELECT role_id FROM org_positions WHERE position_id=?",
                    (seat["position_id"],),
                ).fetchone()
                if pos_owner is not None and str(pos_owner[0]) != ROLE_CREATIVE_DIRECTOR:
                    raise RuntimeError(f"{seat['position_id']} is not the Creative Director role")
                conn.execute(
                    """
                    INSERT INTO org_positions (
                      position_id, role_id, entity_id, department_id, position_label,
                      status, fte, created_at, updated_at
                    ) VALUES (?, ?, 'ENT-GGV', 'DEPT-GGV-CONTENT', ?, 'ACTIVE', 1.0, ?, ?)
                    ON CONFLICT(position_id) DO NOTHING
                    """,
                    (seat["position_id"], ROLE_CREATIVE_DIRECTOR, seat["position_label"], ts, ts),
                )
                conn.execute(
                    """
                    INSERT INTO org_assignments (
                      assignment_id, person_id, position_id, start_at, end_at, status,
                      is_primary, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
                    ON CONFLICT(assignment_id) DO NOTHING
                    """,
                    (assignment_id, person_id, seat["position_id"], ts, ts, ts),
                )
        if not ended:
            conn.execute(
                """
                UPDATE org_assignments
                SET is_primary=0, updated_at=?
                WHERE person_id=? AND assignment_id!=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (ts, person_id, assignment_id),
            )
            conn.execute(
                """
                UPDATE org_assignments
                SET is_primary=1, updated_at=?
                WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (ts, assignment_id),
            )
            _attach_scopes_once(conn, assignment_id, scopes, ts)
        reports.append(
            {
                "display_name": seat["display_name"],
                "email": found["email"],
                "existed": found,
                "reused": reused,
                "person_id": person_id,
                "auth_identity_id": auth_identity_id,
                "assignment_id": assignment_id,
                "position_id": seat["position_id"],
                "role_id": ROLE_CREATIVE_DIRECTOR,
                "scopes": list(scopes),
                "ended": ended,
            }
        )
    return reports


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
    creative_directors = _seat_creative_directors(conn, cd_scopes, ts)

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

    _ensure_end_reason(conn)
    _end_assignment(conn, MISA_CREW_ASSIGNMENT, CREW_END_REASON, ts)
    _end_assignment(conn, MISA_DAY_ASSIGNMENT, DAY_END_REASON, ts)
    _seat_zayen(conn, ts)
    ggv_finance_assignment = _seat_ggv_finance_operator(conn, ts)
    finance = finance_search(conn)

    haikal = conn.execute(
        "SELECT status, is_primary, end_at FROM org_assignments WHERE assignment_id=?",
        (HAIKAL_CD_ASSIGNMENT,),
    ).fetchone()
    limits = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
    sod = conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
    conn.commit()
    return {
        "finance": finance,
        "haikal_cd": None
        if haikal is None
        else {"status": haikal[0], "is_primary": haikal[1], "end_at": haikal[2]},
        "creators": [row["person_id"] for row in CREATORS],
        "misa_assignment": MISA_CD_ASSIGNMENT,
        "creative_directors": creative_directors,
        "misa_crew_ended": MISA_CREW_ASSIGNMENT,
        "misa_day_ended": MISA_DAY_ASSIGNMENT,
        "zayen_assignment": ZAYEN_ASSIGNMENT,
        "zayen_role": ROLE_ATRIUM_FINANCE,
        "ggv_finance_assignment": ggv_finance_assignment,
        "ggv_finance_role": ROLE_GGV_FINANCE_OPERATOR,
        "authority_limits": limits,
        "sod_constraints": sod,
        "hr_mailboxes": [box["address"].lower() for box in HR_MAILBOXES],
        "staff_ready": False,
        "human_commissioned": False,
    }
