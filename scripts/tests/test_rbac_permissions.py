#!/usr/bin/env python3
"""Tests for Wolf Core RBAC / Permissions (Beta). CLAIMED ≠ VERIFIED."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_rbac_permissions.py"
RBAC_PY = SCRIPTS / "core" / "rbac.py"

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


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_rbac_permissions", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    src = RBAC_PY.read_text(encoding="utf-8")
    # Docstring may mention AI must not decide — assert no call sites / imports
    check(
        "no LLM/AI call sites in rbac",
        "openai" not in src.lower()
        and "import llm" not in src.lower()
        and "ChatCompletion" not in src
        and "generate(" not in src,
    )
    check("no has_permission email table in rbac evaluator core", "FROM permissions" not in src)
    check("refuses wolf-system", "refuses wolf-system" in src)

    conn0 = sqlite3.connect(str(DB))
    legacy_before = conn0.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    persons_before = conn0.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
    asg_before = conn0.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0]
    conn0.close()

    mig = load_mig()
    check("migration 1", mig.main() == 0)
    check("migration 2 idempotent", mig.main() == 0)

    from core import rbac as rb
    import wolf_intelligence as wi

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    n_perm = conn.execute("SELECT COUNT(*) FROM org_permissions").fetchone()[0]
    n_grant = conn.execute("SELECT COUNT(*) FROM org_role_permissions").fetchone()[0]
    legacy_after = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    check("seeded permissions >= 11", n_perm >= 11, str(n_perm))
    check("seeded role grants > 0", n_grant > 0, str(n_grant))
    check("legacy rows preserved", legacy_after == legacy_before, f"{legacy_before}->{legacy_after}")

    tgt = rb.default_content_target()
    # deny by default — unknown person
    check("unknown person denied", not rb.can("PERS-NOPE", "content.plan.read", tgt, conn=conn))
    # unknown permission
    ev = rb.evaluate("PERS-MATT", "totally.fake.perm", tgt, conn=conn)
    check("unknown permission denied", ev["allowed"] is False and ev["reason"] == "unknown_permission")

    # explicit role permission works
    check("Matt can content.plan.approve", rb.can("PERS-MATT", "content.plan.approve", tgt, conn=conn))
    check("Matt can organisation.entity.read", rb.can("PERS-MATT", "organisation.entity.read", tgt, conn=conn))

    # Haikal cannot approve (role lacks)
    check("Haikal cannot approve", not rb.can("PERS-HAIKAL", "content.plan.approve", tgt, conn=conn))
    check("Haikal can edit", rb.can("PERS-HAIKAL", "content.plan.edit", tgt, conn=conn))

    # Amanda can create
    check("Amanda can create", rb.can("PERS-AMANDA", "content.plan.create", tgt, conn=conn))

    # wrong entity denied
    amg = {"entity_id": "ENT-AMG"}
    check("Matt GGV scope denied on ENT-AMG entity-only", not rb.can("PERS-MATT", "organisation.entity.read", amg, conn=conn))

    # sibling brand: Uma scope would be needed — GGV content scope must not grant BZG-UMA
    uma = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
    check("GGV assignment denied BZG Uma brand", not rb.can("PERS-HAIKAL", "content.plan.read", uma, conn=conn))

    # permission without matching scope — end all Matt scopes temporarily
    ts = "2099-01-01T00:00:00+08:00"
    conn.execute(
        "UPDATE org_assignment_scopes SET end_at=?, status='ENDED' WHERE assignment_id='ASG-MATT-OWNER-1'",
        (ts,),
    )
    conn.commit()
    check(
        "permission without scope denied",
        not rb.can("PERS-MATT", "content.plan.read", tgt, conn=conn),
    )
    conn.execute(
        "UPDATE org_assignment_scopes SET end_at=NULL, status='ACTIVE' WHERE assignment_id='ASG-MATT-OWNER-1'",
    )
    conn.commit()

    # inactive assignment
    conn.execute(
        "UPDATE org_assignments SET end_at=?, status='ENDED' WHERE assignment_id='ASG-MISA-CC-1'",
        (ts,),
    )
    conn.commit()
    check("inactive assignment denied", not rb.can("PERS-MISA", "content.plan.read", tgt, conn=conn))
    conn.execute(
        "UPDATE org_assignments SET end_at=NULL, status='ACTIVE' WHERE assignment_id='ASG-MISA-CC-1'",
    )
    conn.commit()

    # legacy code maps
    check("legacy can_view_plan maps for Matt", rb.can("PERS-MATT", "can_view_plan", tgt, conn=conn))

    # Content Machine adapter via wi.has_permission
    check(
        "CM adapter Matt can_approve_plan",
        wi.has_permission("mrwolf@wolfcommand.net", "can_approve_plan", conn=conn) is True,
    )
    check(
        "CM adapter Haikal cannot approve",
        wi.has_permission("haikalqilbari123@gmail.com", "can_approve_plan", conn=conn) is False,
    )
    check(
        "CM adapter Haikal can_edit_plan",
        wi.has_permission("haikalqilbari123@gmail.com", "can_edit_plan", conn=conn) is True,
    )
    check(
        "CM unknown email denied (no person, no legacy)",
        wi.has_permission("nobody@example.com", "can_view_plan", conn=conn) is False,
    )

    # email is not permission truth when person exists — revoke role grant temporarily
    conn.execute(
        "DELETE FROM org_role_permissions WHERE role_id='ROLE-GGV-EDIT' AND permission_id='PERM-CONTENT-PLAN-EDIT'"
    )
    conn.commit()
    check(
        "person path ignores leftover email grant when role revoked",
        wi.has_permission("haikalqilbari123@gmail.com", "can_edit_plan", conn=conn) is False,
    )
    # restore grant
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-GGV-EDIT', 'PERM-CONTENT-PLAN-EDIT', 'ALLOW', ?, ?)
        """,
        (ts, ts),
    )
    conn.commit()
    check(
        "restored Haikal edit",
        wi.has_permission("haikalqilbari123@gmail.com", "can_edit_plan", conn=conn) is True,
    )

    # multi-assignment union — Matt has both scopes; still gets grants
    eff = rb.effective_permissions_for_person("PERS-MATT", tgt, conn=conn)
    check("Matt effective includes approve", "content.plan.approve" in eff)
    check("Matt effective includes entity.read", "organisation.entity.read" in eff)

    # Authority Limits live in separate module (010); rbac itself stays permission-only
    check(
        "rbac module does not implement authority",
        "within_authority" not in (ROOT / "scripts" / "core" / "rbac.py").read_text(encoding="utf-8"),
    )
    check("persons unchanged", conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0] == persons_before)
    check("assignments unchanged", conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0] == asg_before)

    # explain structure
    ev2 = rb.evaluate("PERS-AMANDA", "content.plan.create", tgt, conn=conn)
    check("explain has paths", isinstance(ev2.get("paths"), list) and ev2["allowed"] is True)
    check("explain authority NOT_BUILT", ev2.get("authority_limits") == "NOT_BUILT")

    conn.close()

    # API vertical slice
    try:
        import serve_beta as sb
        import inspect
        import os
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        import core.request_auth as ra
        ra._ENV_LOADED = True
        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("API handler found", Handler is not None)
        if Handler:
            if hasattr(sb, "ensure_schema"):
                sb.ensure_schema()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                def get(path, subject=None):
                    headers = {}
                    if subject:
                        headers["X-Wolf-Subject"] = subject
                    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers)
                    try:
                        with urlopen(req, timeout=8) as r:
                            return r.status, json.loads(r.read().decode())
                    except HTTPError as e:
                        body = e.read().decode()
                        try:
                            data = json.loads(body)
                        except Exception:
                            data = {"raw": body}
                        return e.code, data

                st, data = get("/api/core/me/permissions", "mrwolf@wolfcommand.net")
                check("me/permissions 200", st == 200 and data.get("ok") is True)
                check("me/permissions real_auth false", data.get("real_authentication") is False)
                check("me/permissions has codes", "content.plan.approve" in (data.get("permissions") or []))

                st, data = get("/api/core/entities", "mrwolf@wolfcommand.net")
                check("entities authorised", st == 200 and data.get("ok") is True)

                st, data = get("/api/core/entities", "haikalqilbari123@gmail.com")
                check("entities Haikal authorised (entity.read)", st == 200)

                st, data = get("/api/core/persons", "haikalqilbari123@gmail.com")
                check("persons Haikal forbidden (no person.read)", st == 403)

                st, data = get("/api/core/persons", "mrwolf@wolfcommand.net")
                check("persons Matt ok", st == 200)

                st, data = get("/api/core/entities")  # no subject
                check("entities unknown denied", st == 403)

                st, data = get("/api/core/permissions", "mrwolf@wolfcommand.net")
                check("permissions catalog ok", st == 200 and data.get("access_control_live") is False)
            finally:
                httpd.shutdown()
    except Exception as e:
        check("API smoke", False, repr(e))

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print(f"COUNTS permissions={n_perm} grants={n_grant} legacy={legacy_after}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
