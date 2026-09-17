#!/usr/bin/env python3
"""Tests for Wolf Core Assignment Scope (Beta). CLAIMED ≠ VERIFIED."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_assignment_scope.py"
SCOPE_PY = SCRIPTS / "core" / "scope.py"
STAFF_PY = SCRIPTS / "core" / "staffing.py"
TZ8 = timezone(timedelta(hours=8))

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
    spec = importlib.util.spec_from_file_location("migrate_assignment_scope", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    # Guards in source
    scope_src = SCOPE_PY.read_text(encoding="utf-8")
    check("scope refuses wolf-system in source", "refuses wolf-system" in scope_src)
    check("no has_permission in scope.py", "has_permission" not in scope_src)
    check("no KNOWN_PERMISSIONS in scope.py", "KNOWN_PERMISSIONS" not in scope_src)
    check("no Person-direct scope table", "org_person_scopes" not in scope_src)
    check("staffing has no permission engine", "has_permission" not in STAFF_PY.read_text(encoding="utf-8"))

    # Baseline counts
    conn0 = sqlite3.connect(str(DB))
    perm_before = conn0.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    persons_before = conn0.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
    brands_before = conn0.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    asg_before = conn0.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0]
    conn0.close()

    mig = load_mig()
    rc1 = mig.main()
    check("migration 1 exit 0", rc1 == 0)
    rc2 = mig.main()
    check("migration 2 idempotent exit 0", rc2 == 0)

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Tables
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    check("org_scopes exists", "org_scopes" in tables)
    check("org_scope_targets exists", "org_scope_targets" in tables)
    check("org_assignment_scopes exists", "org_assignment_scopes" in tables)
    check("no org_scopes rbac sibling tables", "org_rbac" not in tables)
    check("authority limits are separate slice", "org_authority_limits" in tables)
    check("no org_person_scopes table", "org_person_scopes" not in tables)

    n_scopes = conn.execute("SELECT COUNT(*) FROM org_scopes").fetchone()[0]
    n_targets = conn.execute("SELECT COUNT(*) FROM org_scope_targets").fetchone()[0]
    n_links = conn.execute("SELECT COUNT(*) FROM org_assignment_scopes").fetchone()[0]
    check("seeded scopes >= 2", n_scopes >= 2, str(n_scopes))
    check("seeded targets >= 2", n_targets >= 2, str(n_targets))
    check("seeded assignment-scope links >= 5", n_links >= 5, str(n_links))

    # Stable IDs
    for sid in ("SCOPE-GGV-ALL", "SCOPE-GGV-CONTENT"):
        check(f"stable scope id {sid}", conn.execute(
            "SELECT 1 FROM org_scopes WHERE scope_id=?", (sid,)
        ).fetchone() is not None)

    # Assignment can have scope + multi-scope for Matt
    from core import scope as sc

    matt_scopes = sc.list_scopes_for_assignment("ASG-MATT-OWNER-1")
    check("Matt assignment has scopes", len(matt_scopes) >= 2, str(len(matt_scopes)))
    matt_ids = {s["scope_id"] for s in matt_scopes}
    check("Matt multi-scope GGV-ALL+CONTENT", matt_ids >= {"SCOPE-GGV-ALL", "SCOPE-GGV-CONTENT"}, str(matt_ids))

    amanda = sc.list_scopes_for_assignment("ASG-AMANDA-CM-1")
    check("Amanda has content scope", any(s["scope_id"] == "SCOPE-GGV-CONTENT" for s in amanda))

    # Entity structural cover — GGV only children
    ctx = sc.resolve_effective_scope_context("SCOPE-GGV-ALL", conn=conn)
    check("entity scope found", ctx.get("found") is True)
    check("entity covers ENT-GGV", "ENT-GGV" in ctx["structurally_covered"]["entities"])
    check("entity does not cover ENT-AMG", "ENT-AMG" not in ctx["structurally_covered"]["entities"])
    check("entity does not cover ENT-BZG", "ENT-BZG" not in ctx["structurally_covered"]["entities"])
    check("permission_decision NOT_BUILT", ctx.get("permission_decision") == "NOT_BUILT")
    check("inheritance_not_permission", ctx.get("inheritance_not_permission") is True)
    # GGV departments should include DEPT-GGV-CONTENT; AMG depts must not
    deps = set(ctx["structurally_covered"]["departments"])
    check("GGV entity lists DEPT-GGV-CONTENT", "DEPT-GGV-CONTENT" in deps)
    check("GGV entity excludes DEPT-AMG-EXEC", "DEPT-AMG-EXEC" not in deps)
    check("GGV entity excludes DEPT-BZG-FB", "DEPT-BZG-FB" not in deps)

    # Brand sibling test — insert temp scopes, resolve, cleanup
    ts = datetime.now(TZ8).isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("TEST-SCOPE-UMA", "brand", "TEST Uma Blu", "ACTIVE", ts, ts),
    )
    conn.execute(
        "INSERT OR REPLACE INTO org_scope_targets (scope_id, target_type, target_id, created_at) VALUES (?,?,?,?)",
        ("TEST-SCOPE-UMA", "brand", "BZG-UMA", ts),
    )
    conn.execute(
        "INSERT OR REPLACE INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("TEST-SCOPE-RAIN", "brand", "TEST Rainforest", "ACTIVE", ts, ts),
    )
    conn.execute(
        "INSERT OR REPLACE INTO org_scope_targets (scope_id, target_type, target_id, created_at) VALUES (?,?,?,?)",
        ("TEST-SCOPE-RAIN", "brand", "BZG-RAIN", ts),
    )
    conn.commit()
    uma_ctx = sc.resolve_effective_scope_context("TEST-SCOPE-UMA", conn=conn)
    brands = set(uma_ctx["structurally_covered"]["brands"])
    check("brand scope covers Uma only", brands == {"BZG-UMA"}, str(brands))
    check("brand scope excludes sibling Rain", "BZG-RAIN" not in brands)

    # Location unrelated
    conn.execute(
        "INSERT OR REPLACE INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("TEST-SCOPE-LOC-ATR", "location", "TEST Atrium loc", "ACTIVE", ts, ts),
    )
    conn.execute(
        "INSERT OR REPLACE INTO org_scope_targets (scope_id, target_type, target_id, created_at) VALUES (?,?,?,?)",
        ("TEST-SCOPE-LOC-ATR", "location", "LOC-ATRIUM-LOMBOK", ts),
    )
    conn.commit()
    loc_ctx = sc.resolve_effective_scope_context("TEST-SCOPE-LOC-ATR", conn=conn)
    locs = set(loc_ctx["structurally_covered"]["locations"])
    check("location scope covers atrium only", locs == {"LOC-ATRIUM-LOMBOK"}, str(locs))

    # BZG entity must not include AMG
    conn.execute(
        "INSERT OR REPLACE INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("TEST-SCOPE-BZG", "entity", "TEST BZG all", "ACTIVE", ts, ts),
    )
    conn.execute(
        "INSERT OR REPLACE INTO org_scope_targets (scope_id, target_type, target_id, created_at) VALUES (?,?,?,?)",
        ("TEST-SCOPE-BZG", "entity", "ENT-BZG", ts),
    )
    conn.commit()
    bzg_ctx = sc.resolve_effective_scope_context("TEST-SCOPE-BZG", conn=conn)
    check("BZG entity covers ENT-BZG", "ENT-BZG" in bzg_ctx["structurally_covered"]["entities"])
    check("BZG entity excludes ENT-AMG", "ENT-AMG" not in bzg_ctx["structurally_covered"]["entities"])
    check("BZG brands exclude AMG-ATR", "AMG-ATR" not in bzg_ctx["structurally_covered"]["brands"])

    # Ending assignment does not delete scope history
    conn.execute(
        "UPDATE org_assignments SET end_at=?, status='ENDED', updated_at=? WHERE assignment_id=?",
        (ts, ts, "ASG-MISA-CC-1"),
    )
    conn.commit()
    hist = sc.list_scopes_for_assignment("ASG-MISA-CC-1", include_ended=True, conn=conn)
    check("ended asg keeps scope link rows", len(hist) >= 1, str(len(hist)))
    scope_still = conn.execute(
        "SELECT 1 FROM org_scopes WHERE scope_id='SCOPE-GGV-CONTENT'"
    ).fetchone()
    check("ending asg does not delete Scope def", scope_still is not None)
    person_still = conn.execute(
        "SELECT 1 FROM org_persons WHERE person_id='PERS-MISA'"
    ).fetchone()
    check("ending asg does not delete person", person_still is not None)
    # restore Misa assignment
    conn.execute(
        "UPDATE org_assignments SET end_at=NULL, status='ACTIVE', updated_at=? WHERE assignment_id=?",
        (ts, "ASG-MISA-CC-1"),
    )
    # cleanup TEST scopes
    for sid in ("TEST-SCOPE-UMA", "TEST-SCOPE-RAIN", "TEST-SCOPE-LOC-ATR", "TEST-SCOPE-BZG"):
        conn.execute("DELETE FROM org_scope_targets WHERE scope_id=?", (sid,))
        conn.execute("DELETE FROM org_scopes WHERE scope_id=?", (sid,))
    conn.commit()

    # Content Machine compat
    perm_after = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    persons_after = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
    brands_after = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    asg_after = conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0]
    check("permissions unchanged", perm_after == perm_before, f"{perm_before}->{perm_after}")
    check("persons unchanged", persons_after == persons_before)
    check("brands unchanged", brands_after == brands_before)
    check("assignments count unchanged", asg_after == asg_before)
    email_subj = conn.execute(
        "SELECT COUNT(*) FROM permissions WHERE subject LIKE '%@%'"
    ).fetchone()[0]
    check("content permission still email", email_subj == perm_after)

    # Person scopes via assignment path
    via = sc.list_active_scopes_for_person("PERS-MATT", conn=conn)
    check("person scopes via assignment", len(via) >= 2)

    # Guard path refusal
    try:
        sc.db_connect(Path("/tmp/wolf-system/fake.sqlite"))
        check("refuses wolf-system path", False)
    except RuntimeError as e:
        check("refuses wolf-system path", "wolf-system" in str(e))

    conn.close()

    # API smoke — start serve_beta briefly if importable
    try:
        import serve_beta as sb

        # ensure schema includes 008
        if hasattr(sb, "ensure_schema"):
            sb.ensure_schema()

        class H(sb.Handler if hasattr(sb, "Handler") else sb.BetaHandler):
            pass

        # Find handler class
        Handler = None
        for name in ("BetaHandler", "Handler", "RequestHandler"):
            if hasattr(sb, name):
                Handler = getattr(sb, name)
                break
        if Handler is None:
            # search for BaseHTTPRequestHandler subclass
            import inspect
            from http.server import BaseHTTPRequestHandler
            for _, obj in inspect.getmembers(sb, inspect.isclass):
                if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                    Handler = obj
                    break
        if Handler is None:
            check("API handler class found", False)
        else:
            import os
            os.environ["BETA_AUTH_MODE"] = "development_assertion"
            import core.request_auth as ra
            ra._ENV_LOADED = True
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/core/scopes", timeout=5) as r:
                    data = json.loads(r.read().decode())
                check("API scopes ok", data.get("ok") is True and len(data.get("scopes", [])) >= 2)

                with urlopen(f"http://127.0.0.1:{port}/api/core/scopes/SCOPE-GGV-ALL", timeout=5) as r:
                    data = json.loads(r.read().decode())
                check("API scope detail ok", data.get("ok") is True)
                check(
                    "API effective_context NOT_BUILT perm",
                    data.get("effective_context", {}).get("permission_decision") == "NOT_BUILT",
                )

                with urlopen(
                    f"http://127.0.0.1:{port}/api/core/assignments/ASG-MATT-OWNER-1/scopes",
                    timeout=5,
                ) as r:
                    data = json.loads(r.read().decode())
                check("API assignment scopes ok", data.get("ok") is True and len(data.get("scopes", [])) >= 2)

                req = Request(
                    f"http://127.0.0.1:{port}/api/core/me/scopes",
                    headers={"X-Wolf-Subject": "mrwolf@wolfcommand.net"},
                )
                with urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode())
                check("API me/scopes ok", data.get("ok") is True)
                check("API me/scopes real_auth false", data.get("real_authentication") is False)
                ia = (data.get("identity_assurance") or "").lower()
                check(
                    "API me/scopes development assertion",
                    "development" in ia or "assertion" in ia or data.get("real_authentication") is False,
                    str(data.get("identity_assurance")),
                )
                check("API me/scopes has scopes list", isinstance(data.get("scopes"), list))
            finally:
                httpd.shutdown()
    except Exception as e:
        check("API smoke", False, repr(e))

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print(f"COUNTS scopes={n_scopes} targets={n_targets} links={n_links}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
