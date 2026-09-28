#!/usr/bin/env python3
"""Zarah and Frail on the existing Creative Director role. Beta catalog.

Does not grant a new permission. Does not mark staff_ready or commissioned.
Succession uses a temp copy. HTTP uses a temp copy.
"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import wolf_intelligence as wi  # noqa: E402
from core import audit, content_publish, identity, nas_library, rbac, wolf_shell, work_items  # noqa: E402
from core.staff_access import (  # noqa: E402
    CREATIVE_DIRECTORS,
    HAIKAL_CD_ASSIGNMENT,
    HAIKAL_PERSON,
    ROLE_CREATIVE_DIRECTOR,
    apply,
)
from core.staff_home import StaffHomeError, build_home  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
CONTENT = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
CD_GRANTS = (
    "approval.decide",
    "approval.request",
    "content.asset.upload",
    "content.habitat.approve",
    "content.plan.edit",
    "content.plan.read",
    "content.production.update",
    "evidence.record.submit",
    "work.assign",
    "work.read",
    "work.update",
)
HELD_BACK = (
    "content.habitat.publish.request",
    "content.plan.approve",
    "finance.nota.read",
    "finance.nota.create",
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "organisation.role.read",
    "organisation.person.read",
    "progress.read",
    "amg.day.operator",
    "venue.close.read",
    "core.operator",
    "governance.exception.authorise",
)
FORBIDDEN_PAGES = (
    "/ggv/finance",
    "/amg/finance",
    "/wolf",
    "/hr-payroll-inputs",
    "/hr-hiring-onboarding",
)
FORBIDDEN_APIS = (
    "/api/ggv/finance",
    "/api/amg/finance",
    "/api/hr/payroll-inputs",
    "/api/core/roles",
    "/api/core/persons",
)
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


def _scopes(conn: sqlite3.Connection, person_id: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT s.scope_id
        FROM org_assignment_scopes s
        JOIN org_assignments a ON a.assignment_id = s.assignment_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND s.status='ACTIVE' AND s.end_at IS NULL
        """,
        (person_id,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def test_registry() -> None:
    conn = live()
    try:
        named_roles = conn.execute(
            """
            SELECT COUNT(*) FROM org_roles
            WHERE role_id LIKE '%ZARAH%' OR role_id LIKE '%FRAIL%'
               OR display_name LIKE '%Zarah%' OR display_name LIKE '%Frail%'
            """
        ).fetchone()[0]
        check("no person-named role", named_roles == 0)
        haikal = conn.execute(
            "SELECT status, is_primary, end_at FROM org_assignments WHERE assignment_id=?",
            (HAIKAL_CD_ASSIGNMENT,),
        ).fetchone()
        check(
            "Haikal CD assignment still primary",
            haikal is not None
            and haikal["status"] == "ACTIVE"
            and haikal["end_at"] is None
            and haikal["is_primary"] == 1,
        )
        grants = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT perm.code
                FROM org_role_permissions rp
                JOIN org_permissions perm ON perm.permission_id = rp.permission_id
                WHERE rp.role_id=? AND rp.effect='ALLOW'
                """,
                (ROLE_CREATIVE_DIRECTOR,),
            ).fetchall()
        }
        check("Creative Director grants unchanged", grants == set(CD_GRANTS), str(sorted(grants)))
        haikal_scopes = _scopes(conn, HAIKAL_PERSON)
        for seat in CREATIVE_DIRECTORS:
            email = seat["email"]
            mixed = "".join(ch.upper() if i % 2 == 0 else ch.lower() for i, ch in enumerate(email))
            for variant in (email, mixed, email.upper()):
                person = identity.resolve_person_from_email(variant, conn=conn)
                check(
                    f"{seat['display_name']} resolves {variant}",
                    person is not None and person["person_id"] == seat["person_id"],
                    str(None if person is None else person["person_id"]),
                )
            count = conn.execute(
                "SELECT COUNT(*) FROM org_persons WHERE lower(display_name)=?",
                (seat["display_name"].lower(),),
            ).fetchone()[0]
            check(f"one {seat['display_name']} person", count == 1)
            auth_count = conn.execute(
                """
                SELECT COUNT(*) FROM org_auth_identities
                WHERE provider='email' AND lower(identifier)=?
                """,
                (email,),
            ).fetchone()[0]
            check(f"one AuthIdentity for {seat['display_name']}", auth_count == 1)
            row = conn.execute(
                """
                SELECT a.assignment_id, a.is_primary, a.end_at, p.role_id, p.position_id, r.display_name
                FROM org_assignments a
                JOIN org_positions p ON p.position_id = a.position_id
                JOIN org_roles r ON r.role_id = p.role_id
                WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL AND a.is_primary=1
                """,
                (seat["person_id"],),
            ).fetchone()
            check(
                f"{seat['display_name']} primary is Creative Director",
                row is not None
                and row["assignment_id"] == seat["assignment_id"]
                and row["role_id"] == ROLE_CREATIVE_DIRECTOR
                and row["position_id"] == seat["position_id"]
                and row["display_name"] == "Creative Director"
                and row["is_primary"] == 1
                and row["end_at"] is None,
            )
            check(
                f"{seat['display_name']} scopes match Haikal",
                _scopes(conn, seat["person_id"]) == haikal_scopes,
                str(sorted(_scopes(conn, seat["person_id"]))),
            )
            check(
                f"{seat['display_name']} audience matches Haikal",
                wolf_shell.audience_for_person(seat["person_id"])
                == wolf_shell.audience_for_person(HAIKAL_PERSON)
                == "SPECIALIST_CONTENT",
            )
            from core.staff_access import primary_human_landing

            check(
                f"{seat['display_name']} lands on content",
                primary_human_landing(seat["person_id"], conn) == "/content-2.0",
            )
    finally:
        conn.close()


def test_permissions() -> None:
    conn = live()
    try:
        haikal_rights = set(
            rbac.effective_permissions_for_person(HAIKAL_PERSON, CONTENT, conn=conn)
        )
        haikal_scopes = _scopes(conn, HAIKAL_PERSON)
        brands = set(nas_library.brands_for_scopes(haikal_scopes))
        check("Haikal brand set is non-empty", len(brands) > 0, str(sorted(brands)))
        check(
            "unknown brand is not authorised",
            nas_library.scopes_allow_brand(haikal_scopes, "not-a-brand") is False,
        )
        for seat in CREATIVE_DIRECTORS:
            pid = seat["person_id"]
            rights = set(rbac.effective_permissions_for_person(pid, CONTENT, conn=conn))
            check(
                f"{pid} rights match Haikal",
                rights == haikal_rights,
                str(sorted(rights ^ haikal_rights)),
            )
            for code in ("work.assign", "content.plan.edit", "content.habitat.approve", "approval.decide", "content.asset.upload"):
                check(f"{pid} allows {code}", rbac.can(pid, code, CONTENT, conn=conn))
            for code in HELD_BACK:
                check(f"{pid} denies {code}", rbac.can(pid, code, CONTENT, conn=conn) is False)
            seat_brands = set(nas_library.brands_for_scopes(_scopes(conn, pid)))
            check(f"{pid} brands match Haikal", seat_brands == brands, str(sorted(seat_brands)))
            for brand in brands:
                check(
                    f"{pid} brand {brand}",
                    nas_library.scopes_allow_brand(_scopes(conn, pid), brand) is True,
                )
            home = build_home(pid, conn=conn)
            check(f"{pid} my work is creative director", home.get("experience") == "creative_director")
            check(
                f"{pid} my work names Creative Director",
                (home.get("role") or {}).get("label") == "Creative Director",
            )
            check(
                f"{pid} greeting uses the name",
                home.get("greeting") == f"Hello, {seat['display_name']}",
            )
            check(
                f"{pid} flags stay false",
                home.get("staff_ready") is False and home.get("human_commissioned") is False,
            )
            check(f"{pid} cannot move money", home.get("authority", {}).get("move_money") is False)
    finally:
        conn.close()


def test_idempotent() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="zarah-frail-idem-", dir=str(ROOT / "state")))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    conn = sqlite3.connect(copy)
    conn.row_factory = sqlite3.Row
    try:
        before_people = conn.execute(
            "SELECT COUNT(*) FROM org_persons WHERE person_id IN ('PERS-ZARAH','PERS-FRAIL')"
        ).fetchone()[0]
        before_scopes = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignment_scopes
            WHERE assignment_id IN ('ASG-ZARAH-CD-1','ASG-FRAIL-CD-1')
              AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchone()[0]
        apply(conn)
        after_people = conn.execute(
            "SELECT COUNT(*) FROM org_persons WHERE person_id IN ('PERS-ZARAH','PERS-FRAIL')"
        ).fetchone()[0]
        after_scopes = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignment_scopes
            WHERE assignment_id IN ('ASG-ZARAH-CD-1','ASG-FRAIL-CD-1')
              AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchone()[0]
        check("second apply does not add a person", before_people == 2 and after_people == 2)
        check(
            "second apply does not duplicate scopes",
            before_scopes == after_scopes and after_scopes > 0,
            f"{before_scopes} -> {after_scopes}",
        )
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)


def test_succession() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="zarah-frail-succ-", dir=str(ROOT / "state")))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    conn = sqlite3.connect(copy)
    conn.row_factory = sqlite3.Row
    try:
        original = "PERS-ZARAH"
        before = set(rbac.effective_permissions_for_person(original, CONTENT, conn=conn))
        scopes = sorted(_scopes(conn, original))
        check("Zarah can read before end", "content.plan.read" in before and rbac.can(original, "content.plan.read", CONTENT, conn=conn))
        conn.execute(
            """
            UPDATE org_assignments
            SET status='ENDED', end_at='2026-09-28T14:00:00+08:00', is_primary=0,
                end_reason='succession test'
            WHERE person_id=? AND status='ACTIVE'
            """,
            (original,),
        )
        conn.commit()
        check(
            "ended assignment removes Zarah access",
            rbac.can(original, "content.plan.read", CONTENT, conn=conn) is False
            and rbac.can(original, "work.assign", CONTENT, conn=conn) is False,
        )
        kept = conn.execute(
            "SELECT person_id, status FROM org_assignments WHERE assignment_id='ASG-ZARAH-CD-1'"
        ).fetchone()
        check(
            "ended row stays on Zarah",
            kept is not None and kept["person_id"] == original and kept["status"] == "ENDED",
        )
        check(
            "Frail still has the role after Zarah ends",
            rbac.can("PERS-FRAIL", "content.plan.read", CONTENT, conn=conn),
        )
        ts = "2026-09-28T14:01:00+08:00"
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES ('PERS-CD-REPLACEMENT', 'Replacement', NULL, 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, department_id, position_label,
              status, fte, created_at, updated_at
            ) VALUES ('POS-GGV-CREATIVE-DIRECTOR-REPL', ?, 'ENT-GGV', 'DEPT-GGV-CONTENT',
                      'Creative Director replacement', 'ACTIVE', 1.0, ?, ?)
            """,
            (ROLE_CREATIVE_DIRECTOR, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES ('ASG-CD-REPLACEMENT', 'PERS-CD-REPLACEMENT', 'POS-GGV-CREATIVE-DIRECTOR-REPL',
                      ?, NULL, 'ACTIVE', 1, ?, ?)
            """,
            (ts, ts, ts),
        )
        for scope_id in scopes:
            conn.execute(
                """
                INSERT INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES ('ASG-CD-REPLACEMENT', ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (scope_id, ts, ts, ts),
            )
        conn.commit()
        replacement = set(
            rbac.effective_permissions_for_person("PERS-CD-REPLACEMENT", CONTENT, conn=conn)
        )
        check(
            "replacement on the same role matches Zarah",
            replacement == before,
            str(sorted(replacement ^ before)),
        )
        check(
            "replacement is denied finance",
            rbac.can("PERS-CD-REPLACEMENT", "finance.nota.read", CONTENT, conn=conn) is False
            and rbac.can("PERS-CD-REPLACEMENT", "payment.execute", CONTENT, conn=conn) is False,
        )
        home = build_home("PERS-CD-REPLACEMENT", conn=conn)
        check("replacement my work is creative director", home.get("experience") == "creative_director")
        try:
            build_home(original, conn=conn)
            check("Zarah no longer has an active seat", False)
        except StaffHomeError:
            check("Zarah no longer has an active seat", True)
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)


def http_call(
    port: int,
    path: str,
    email: str | None,
    accept: str,
    method: str = "GET",
    body: str | None = None,
) -> tuple[int, str, str, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    data = None
    if body is not None:
        data = body.encode("utf-8")
        headers["Content-Type"] = "application/json"
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=90)
    try:
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, resp.getheader("Location") or "", resp.getheader("Content-Type") or "", raw
    finally:
        conn.close()


def test_http() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="zarah-frail-http-", dir=str(ROOT / "state")))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    import serve_beta as sb
    from core import ggv_finance_nota as fin

    saved = {
        "sb": sb.CATALOG_DB,
        "shell": wolf_shell._CATALOG_DB,
        "wi": wi.CATALOG_DB,
        "identity": identity.CATALOG_DB,
        "rbac": rbac.CATALOG_DB,
        "fin": fin.CATALOG_DB,
        "publish": content_publish.CATALOG_DB,
        "work": work_items.CATALOG_DB,
        "audit": audit.CATALOG_DB,
    }
    sb.CATALOG_DB = copy
    wolf_shell._CATALOG_DB = copy
    wi.CATALOG_DB = copy
    identity.CATALOG_DB = copy
    rbac.CATALOG_DB = copy
    fin.CATALOG_DB = copy
    content_publish.CATALOG_DB = copy
    work_items.CATALOG_DB = copy
    audit.CATALOG_DB = copy

    handler = None
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            handler = obj
            break
    check("beta handler found", handler is not None)
    if handler is None:
        shutil.rmtree(tmp, ignore_errors=True)
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, _loc, _ctype, body = http_call(port, "/", None, "text/html")
        check("unsigned / is 403", status == 403, f"status={status} body={body[:60]!r}")
        status, _loc, _ctype, body = http_call(port, "/api/health", None, "*/*")
        check("health 200", status == 200 and b"beta-os" in body, f"status={status}")

        haikal_email = "haikalqilbari123@gmail.com"
        h_status, _h_loc, h_ctype, h_body = http_call(
            port, "/api/planner/publish-gate?id=1", haikal_email, "application/json"
        )
        h_gate = json.loads(h_body.decode() or "{}") if h_status == 200 else {}
        b_status, _b_loc, _b_ctype, b_body = http_call(
            port, "/bzg/uma-blu", haikal_email, "text/html"
        )

        for seat in CREATIVE_DIRECTORS:
            email = seat["email"]
            name = seat["display_name"]
            status, loc, _ctype, raw = http_call(port, "/", email, "text/html")
            check(
                f"{name} / redirects to content",
                status == 302 and loc == "/content-2.0" and not raw.startswith(b"{"),
                f"status={status} loc={loc} body={raw[:60]!r}",
            )
            status, _loc, ctype, raw = http_call(port, "/content-2.0", email, "text/html")
            text = raw.decode("utf-8", "replace")
            check(
                f"{name} content page renders",
                status == 200 and "text/html" in ctype and "Content Engine" in text and "Access denied" not in text,
                f"status={status} head={text[:80]!r}",
            )
            status, _loc, ctype, raw = http_call(port, "/my-work", email, "text/html")
            text = raw.decode("utf-8", "replace")
            check(
                f"{name} my work page renders",
                status == 200 and "text/html" in ctype and "My Work" in text and "Access denied" not in text,
                f"status={status} head={text[:80]!r}",
            )
            status, _loc, ctype, raw = http_call(port, "/api/staff/home", email, "application/json")
            payload = json.loads(raw.decode() or "{}")
            check(
                f"{name} my work API is Creative Director",
                status == 200
                and "json" in ctype
                and payload.get("experience") == "creative_director"
                and (payload.get("role") or {}).get("label") == "Creative Director"
                and payload.get("staff_ready") is False
                and payload.get("human_commissioned") is False,
                str(payload.get("role")),
            )
            status, _loc, ctype, raw = http_call(port, "/api/content/brand-registry", email, "application/json")
            brands = json.loads(raw.decode() or "{}")
            check(
                f"{name} library brand registry",
                status == 200 and brands.get("ok") is True and len(brands.get("brands") or []) > 0,
                f"status={status} count={len(brands.get('brands') or [])}",
            )
            status, _loc, ctype, raw = http_call(port, "/api/assets?brand=habitat&nas_limit=1", email, "application/json")
            library = json.loads(raw.decode() or "{}")
            check(
                f"{name} library allows habitat",
                status == 200 and library.get("ok") is True and "json" in ctype,
                f"status={status} body={raw[:80]!r}",
            )
            status, _loc, ctype, raw = http_call(port, "/api/assets?brand=not-a-brand", email, "application/json")
            check(
                f"{name} library denies an unknown brand",
                status == 403 and "json" in ctype and raw.lstrip().startswith(b"{"),
                f"status={status} body={raw[:80]!r}",
            )
            status, _loc, ctype, raw = http_call(
                port, "/api/upload/preview-names", email, "application/json", "POST", "{}"
            )
            check(
                f"{name} upload gate allows the seat",
                status == 400 and "json" in ctype and b"brand required" in raw,
                f"status={status} body={raw[:120]!r}",
            )
            status, _loc, ctype, raw = http_call(
                port, "/api/assets/2147483647/download", email, "application/json"
            )
            check(
                f"{name} download gate allows the seat",
                status == 404 and "json" in ctype and b"asset not found" in raw.lower(),
                f"status={status} body={raw[:80]!r}",
            )
            status, _loc, ctype, raw = http_call(
                port, "/api/planner/publish-gate?id=1", email, "application/json"
            )
            gate = json.loads(raw.decode() or "{}") if status == 200 else {}
            check(
                f"{name} publish gate matches Haikal",
                status == h_status
                and gate.get("allowed") == h_gate.get("allowed")
                and gate.get("stage") == h_gate.get("stage")
                and gate.get("reason") == h_gate.get("reason"),
                f"status={status} reason={gate.get('reason')} haikal={h_gate.get('reason')}",
            )
            z_status, _z_loc, _z_ctype, _z_raw = http_call(port, "/bzg/uma-blu", email, "text/html")
            check(
                f"{name} uma page matches Haikal",
                z_status == b_status,
                f"{name}={z_status} haikal={b_status}",
            )
            for path in FORBIDDEN_PAGES:
                status, _loc, ctype, raw = http_call(port, path, email, "text/html")
                text = raw.decode("utf-8", "replace")
                check(
                    f"{name} denied page {path} is HTML",
                    status == 403
                    and "text/html" in ctype
                    and text.lstrip().startswith("<!DOCTYPE html>")
                    and "Access denied" in text
                    and email in text
                    and 'href="/content-2.0"' in text
                    and not text.lstrip().startswith("{"),
                    f"status={status} type={ctype} head={text[:140]!r}",
                )
            for path in FORBIDDEN_APIS:
                status, _loc, ctype, raw = http_call(port, path, email, "text/html")
                check(
                    f"{name} denied API {path} stays JSON",
                    status == 403 and "json" in ctype and raw.lstrip().startswith(b"{"),
                    f"status={status} type={ctype} body={raw[:100]!r}",
                )
            status, loc, _ctype, _raw = http_call(port, "/signout", email, "text/html")
            check(
                f"{name} signout is logout",
                status == 302 and "cdn-cgi/access/logout" in loc,
                f"status={status} loc={loc}",
            )
        zayen = "laluzayen@gmail.com"
        status, _loc, ctype, raw = http_call(
            port, "/api/upload/preview-names", zayen, "application/json", "POST", "{}"
        )
        check(
            "finance officer upload stays denied",
            status == 403 and raw.lstrip().startswith(b"{"),
            f"status={status} body={raw[:80]!r}",
        )
        status, _loc, ctype, raw = http_call(
            port, "/api/assets/2147483647/download", zayen, "application/json"
        )
        check(
            "finance officer download stays denied",
            status == 403 and "json" in ctype,
            f"status={status} body={raw[:80]!r}",
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        sb.CATALOG_DB = saved["sb"]
        wolf_shell._CATALOG_DB = saved["shell"]
        wi.CATALOG_DB = saved["wi"]
        identity.CATALOG_DB = saved["identity"]
        rbac.CATALOG_DB = saved["rbac"]
        fin.CATALOG_DB = saved["fin"]
        content_publish.CATALOG_DB = saved["publish"]
        work_items.CATALOG_DB = saved["work"]
        audit.CATALOG_DB = saved["audit"]
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    test_registry()
    test_permissions()
    test_idempotent()
    test_succession()
    test_http()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
