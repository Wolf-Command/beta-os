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
    ATRIUM_DENIED,
    ATRIUM_FINANCE_HREF,
    ATRIUM_GRANTS,
    ATRIUM_SUBMIT,
    CREATOR_DENIED,
    CREATOR_PERMISSIONS,
    CREATORS,
    FINANCE_EMAIL,
    HAIKAL_CD_ASSIGNMENT,
    HR_MAILBOXES,
    MISA_CD_ASSIGNMENT,
    MISA_CREW_ASSIGNMENT,
    MISA_DAY_ASSIGNMENT,
    MISA_EMAIL,
    MISA_PERSON,
    ROLE_ATRIUM_FINANCE,
    ROLE_CONTENT_CREATOR,
    ROLE_CREATIVE_DIRECTOR,
    SCOPE_AMG_FINANCE,
    ZAYEN_ASSIGNMENT,
    ZAYEN_PERSON,
)
from core.staff_home import StaffHomeError, build_home  # noqa: E402
from core.wolf_shell import build_whoami  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
CONTENT = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
AMG = {"entity_id": "ENT-AMG"}
BZG = {"entity_id": "ENT-BZG"}
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
        check(
            "Zayen email binds Zayen",
            finance is not None
            and finance["person_id"] == ZAYEN_PERSON
            and finance["display_name"] == "Zayen"
            and not finance.get("legal_name"),
        )
        seat = conn.execute(
            """
            SELECT p.role_id, p.position_label, a.is_primary, a.end_at
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.assignment_id=? AND a.status='ACTIVE'
            """,
            (ZAYEN_ASSIGNMENT,),
        ).fetchone()
        check(
            "Zayen seat is Atrium Finance Officer",
            seat is not None
            and seat["role_id"] == ROLE_ATRIUM_FINANCE
            and seat["position_label"] == "Atrium Finance Officer"
            and seat["is_primary"] == 1
            and seat["end_at"] is None,
        )
        named = conn.execute(
            "SELECT COUNT(*) FROM org_roles WHERE role_id LIKE '%ZAYEN%' OR display_name LIKE '%Zayen%'"
        ).fetchone()[0]
        check("role name is not the person", named == 0)
        for assignment_id in (MISA_CREW_ASSIGNMENT, MISA_DAY_ASSIGNMENT):
            ended = conn.execute(
                "SELECT status, end_at, end_reason FROM org_assignments WHERE assignment_id=?",
                (assignment_id,),
            ).fetchone()
            check(
                f"{assignment_id} ended and kept",
                ended is not None
                and ended["status"] == "ENDED"
                and ended["end_at"]
                and str(ended["end_reason"] or "").strip(),
            )
        limits = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        sod = conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
        check("no authority limit added", limits == 0 and sod == 0)
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
            items = today.get("items") or []
            if items:
                check(
                    f"{pid} today is brand-scoped stored plans",
                    all(
                        it.get("origin") == "historical"
                        and it.get("verified_by_wolf") is False
                        and str(it.get("brand_id") or "").lower() == "habitat"
                        and pid not in str(it.get("id"))
                        for it in items
                    ),
                )
            else:
                check(
                    f"{pid} today names the empty seat",
                    today.get("empty") is True and "this role" in str(today.get("empty_message")),
                )
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
        check(
            "Misa crew grant is gone",
            rbac.can(MISA_PERSON, "content.habitat.publish.request", CONTENT, conn=conn) is False
            and rbac.can(MISA_PERSON, "amg.day.operator", {"entity_id": "ENT-AMG", "brand_id": "AMG-ATR"}, conn=conn) is False,
        )
        check("Misa still reads content", rbac.can(MISA_PERSON, "content.plan.read", CONTENT, conn=conn))
        for row in ATRIUM_GRANTS:
            check(
                f"Zayen allows {row[1]}",
                rbac.can(ZAYEN_PERSON, row[1], AMG, conn=conn),
            )
            check(
                f"Zayen denies {row[1]} on GGV",
                rbac.can(ZAYEN_PERSON, row[1], CONTENT, conn=conn) is False,
            )
            check(
                f"Zayen denies {row[1]} on BZG",
                rbac.can(ZAYEN_PERSON, row[1], BZG, conn=conn) is False,
            )
        check(
            "Zayen can submit for approval on Atrium",
            rbac.can(ZAYEN_PERSON, ATRIUM_SUBMIT, AMG, conn=conn),
        )
        check(
            "Zayen cannot submit for approval on GGV",
            rbac.can(ZAYEN_PERSON, ATRIUM_SUBMIT, CONTENT, conn=conn) is False,
        )
        for code in ATRIUM_DENIED:
            check(
                f"Zayen denies {code}",
                rbac.can(ZAYEN_PERSON, code, AMG, conn=conn) is False,
            )
        zwho = build_whoami(person_id=ZAYEN_PERSON)
        check("Zayen lands on Atrium Finance", zwho.get("landing") == ATRIUM_FINANCE_HREF)
        pages = set(zwho.get("pages") or [])
        check("Zayen page set is Atrium Finance and My Work", pages == {ATRIUM_FINANCE_HREF, "/my-work"})
        for hidden in ("/ggv/finance", "/bzg/uma-blu", "/wolf", "/amg-ops-pack", "/content-2.0", "/progress"):
            check(f"Zayen hides {hidden}", hidden not in pages)
        home = build_home(ZAYEN_PERSON, conn=conn)
        check("Zayen my work is atrium finance", home.get("experience") == "atrium_finance")
        check("Zayen cannot move money", home.get("authority", {}).get("move_money") is False)
        check("Zayen staff flags stay false", home.get("staff_ready") is False and home.get("human_commissioned") is False)
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


def test_zayen_succession() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="staff-zayen-"))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    conn = sqlite3.connect(copy)
    conn.row_factory = sqlite3.Row
    try:
        check("Zayen can read the board before end", rbac.can(ZAYEN_PERSON, "atrium.board.read", AMG, conn=conn))
        conn.execute(
            """
            UPDATE org_assignments
            SET status='ENDED', end_at='2026-09-28T12:00:00+08:00', is_primary=0,
                end_reason='succession test'
            WHERE assignment_id=?
            """,
            (ZAYEN_ASSIGNMENT,),
        )
        conn.commit()
        check(
            "ended Zayen assignment removes access",
            rbac.can(ZAYEN_PERSON, "atrium.board.read", AMG, conn=conn) is False,
        )
        kept = conn.execute(
            "SELECT person_id, status, end_reason FROM org_assignments WHERE assignment_id=?",
            (ZAYEN_ASSIGNMENT,),
        ).fetchone()
        check(
            "Zayen history stays with Zayen",
            kept is not None and kept["person_id"] == ZAYEN_PERSON and kept["status"] == "ENDED",
        )
        ts = "2026-09-28T12:01:00+08:00"
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES ('PERS-FIN-REPLACEMENT', 'Replacement', NULL, 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, position_label, status, fte, created_at, updated_at
            ) VALUES ('POS-AMG-FINANCE-OFFICER-REPL', ?, 'ENT-AMG',
                      'Atrium Finance Officer', 'ACTIVE', 1.0, ?, ?)
            """,
            (ROLE_ATRIUM_FINANCE, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES ('ASG-FIN-REPLACEMENT', 'PERS-FIN-REPLACEMENT', 'POS-AMG-FINANCE-OFFICER-REPL',
                      ?, NULL, 'ACTIVE', 1, ?, ?)
            """,
            (ts, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES ('ASG-FIN-REPLACEMENT', ?, ?, NULL, 'ACTIVE', ?, ?)
            """,
            (SCOPE_AMG_FINANCE, ts, ts, ts),
        )
        conn.commit()
        check(
            "replacement with the same role can read the board",
            rbac.can("PERS-FIN-REPLACEMENT", "atrium.board.read", AMG, conn=conn),
        )
        check(
            "replacement is denied payment",
            rbac.can("PERS-FIN-REPLACEMENT", "payment.approve", AMG, conn=conn) is False,
        )
        check(
            "replacement is denied GGV",
            rbac.can("PERS-FIN-REPLACEMENT", "atrium.board.read", CONTENT, conn=conn) is False,
        )
        home = build_home("PERS-FIN-REPLACEMENT", conn=conn)
        check("replacement reaches atrium finance", home.get("experience") == "atrium_finance")
        try:
            build_home(ZAYEN_PERSON, conn=conn)
            check("Zayen no longer has an active seat", False)
        except StaffHomeError:
            check("Zayen no longer has an active seat", True)
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)


def test_direct_urls() -> None:
    import os
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    import serve_beta as sb

    handler = None
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            handler = obj
            break
    check("beta handler found", handler is not None)
    if handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(path: str, subject: str | None = None, method: str = "GET") -> int:
        headers = {"Accept": "*/*"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.status
        except HTTPError as exc:
            return exc.code

    email = FINANCE_EMAIL
    check("Zayen direct Atrium Finance", call(ATRIUM_FINANCE_HREF, email) == 200)
    check("unsigned Atrium Finance denied", call(ATRIUM_FINANCE_HREF) == 403)
    for path in (
        "/ggv/finance",
        "/bzg/uma-blu",
        "/wolf",
        "/amg-ops-pack",
        "/content-2.0",
        "/api/ggv/finance/pay",
    ):
        check(f"Zayen direct deny {path}", call(path, email) == 403)
    check("Zayen cannot post on Atrium Finance", call("/api/amg/finance", email, "POST") == 405)
    spoof = Request(
        f"http://127.0.0.1:{port}/ggv/finance",
        headers={"Cf-Access-Authenticated-User-Email": email},
        method="GET",
    )
    try:
        with urlopen(spoof, timeout=30) as resp:
            spoof_code = resp.status
    except HTTPError as exc:
        spoof_code = exc.code
    check("spoofed access email does not open GGV", spoof_code == 403)
    httpd.shutdown()


def main() -> None:
    test_registry()
    test_permissions()
    test_succession()
    test_zayen_succession()
    test_direct_urls()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
