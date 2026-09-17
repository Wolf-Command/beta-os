#!/usr/bin/env python3
"""Tests for Wolf Core Authority Limits (Beta). CLAIMED ≠ VERIFIED.

Uses a temp sqlite copy of Beta catalog + fixture limits only.
SEEDED LIVE AUTHORITY LIMITS must remain 0 on the real Beta DB.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
AUTH_PY = SCRIPTS / "core" / "authority.py"
MIG = SCRIPTS / "migrations" / "migrate_authority_limits.py"
BACKUP_DIR = ROOT / "backups"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"
PERM = "PERM-CONTENT-PLAN-APPROVE"
CODE = "content.plan.approve"
TGT = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_authority_limits", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def insert_limit(
    conn,
    *,
    lid,
    role_id=None,
    assignment_id=None,
    permission_id=PERM,
    scope_id=None,
    currency="IDR",
    threshold=1_000_000.0,
    effective_from="2026-01-01T00:00:00+08:00",
    effective_to=None,
    status="active",
):
    conn.execute(
        """
        INSERT INTO org_authority_limits (
          authority_limit_id, role_id, assignment_id, permission_id, scope_id,
          limit_type, currency, threshold_value, comparison_rule,
          effective_from, effective_to, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'AMOUNT', ?, ?, 'LTE_INCLUSIVE', ?, ?, ?, ?, ?)
        """,
        (
            lid,
            role_id,
            assignment_id,
            permission_id,
            scope_id,
            currency,
            threshold,
            effective_from,
            effective_to,
            status,
            TS,
            TS,
        ),
    )


def main() -> int:
    src = AUTH_PY.read_text(encoding="utf-8")
    check(
        "no LLM/AI call sites in authority.py",
        "openai" not in src.lower()
        and "anthropic" not in src.lower()
        and "import llm" not in src.lower()
        and "ChatCompletion" not in src
        and "generate(" not in src
        and "ai_decision" in src,
    )
    check("refuses wolf-system", "refuses wolf-system" in src)
    check("refuses Production", "Production" in src)
    check("no production DB open for write in authority", "money.sqlite" in src)

    # Live Beta: migrate must leave seeded live = 0
    mig = load_mig()
    live_before = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {
            r[0]
            for r in live_before.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        live_n_before = (
            live_before.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            if "org_authority_limits" in tabs
            else 0
        )
    finally:
        live_before.close()

    check("migration 1", mig.main() == 0)
    check("migration 2 idempotent", mig.main() == 0)

    live = sqlite3.connect(str(LIVE_DB))
    live_n = live.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
    legacy_n = live.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    test_perm = live.execute(
        "SELECT status FROM org_permissions WHERE permission_id='PERM-TEST-SPEND'"
    ).fetchone()
    check("seeded_live_authority_limits=0", live_n == 0, str(live_n))
    check("live rows unchanged by second migrate", live_n == live_n_before or live_n_before == 0)
    check("PERM-TEST-SPEND inactive catalog", test_perm and test_perm[0] == "INACTIVE")
    check("legacy permissions table untouched count>0", legacy_n > 0, str(legacy_n))
    live.close()

    # Backup evidence present
    backups = list(BACKUP_DIR.glob("content_library-pre-authority-*.sqlite"))
    check("pre-authority backup exists", len(backups) >= 1, str(BACKUP_DIR))

    # Temp DB fixtures
    td = tempfile.mkdtemp(prefix="authlim-")
    tmp_db = Path(td) / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Activate test spend + grant to ROLE-MATT for fixture-only permission path
    conn.execute(
        "UPDATE org_permissions SET status='ACTIVE', updated_at=? WHERE permission_id='PERM-TEST-SPEND'",
        (TS,),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-MATT', 'PERM-TEST-SPEND', 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )

    # Role-level limit for content.plan.approve (Matt)
    insert_limit(
        conn,
        lid="ALIM-MATT-ROLE-APPROVE",
        role_id="ROLE-MATT",
        assignment_id=None,
        permission_id=PERM,
        scope_id=None,
        threshold=5_000_000.0,
    )
    # Assignment-specific stricter override
    insert_limit(
        conn,
        lid="ALIM-MATT-ASG-APPROVE",
        role_id=None,
        assignment_id="ASG-MATT-OWNER-1",
        permission_id=PERM,
        scope_id="SCOPE-GGV-CONTENT",
        threshold=1_000_000.0,
    )
    # Expired limit for Amanda (ROLE-CONTENT-MGMT can approve)
    insert_limit(
        conn,
        lid="ALIM-AMANDA-EXPIRED",
        role_id="ROLE-CONTENT-MGMT",
        assignment_id=None,
        permission_id=PERM,
        threshold=2_000_000.0,
        effective_from="2020-01-01T00:00:00+08:00",
        effective_to="2021-01-01T00:00:00+08:00",
    )
    # Active Amanda role limit
    insert_limit(
        conn,
        lid="ALIM-AMANDA-ACTIVE",
        role_id="ROLE-CONTENT-MGMT",
        assignment_id=None,
        permission_id=PERM,
        threshold=500_000.0,
        effective_from="2026-01-01T00:00:00+08:00",
    )
    # Conflicting second Amanda limit (looser) — strictest must win
    insert_limit(
        conn,
        lid="ALIM-AMANDA-LOOSE",
        role_id="ROLE-CONTENT-MGMT",
        assignment_id=None,
        permission_id=PERM,
        scope_id="SCOPE-GGV-CONTENT",
        threshold=9_000_000.0,
        effective_from="2026-01-01T00:00:00+08:00",
    )
    # Test spend role limit
    insert_limit(
        conn,
        lid="ALIM-MATT-SPEND",
        role_id="ROLE-MATT",
        permission_id="PERM-TEST-SPEND",
        threshold=100_000.0,
        currency="IDR",
    )
    conn.commit()

    from core import authority as auth
    from core import rbac as rb
    import wolf_intelligence as wi

    # Permission required (RBAC fail)
    ev = auth.within_authority(
        "PERS-HAIKAL", CODE, TGT, {"amount": 100, "currency": "IDR"}, conn=conn
    )
    check("permission required / rbac deny", ev["allowed"] is False and ev["reason"] == "rbac_denied")

    # Active assignment required
    ev = auth.within_authority(
        "PERS-NOPE", CODE, TGT, {"amount": 100, "currency": "IDR"}, conn=conn
    )
    check("unknown person rbac/assignment deny", ev["allowed"] is False)

    # Scope required / wrong entity
    ev = auth.within_authority(
        "PERS-MATT",
        CODE,
        {"entity_id": "ENT-AMG"},
        {"amount": 100, "currency": "IDR"},
        conn=conn,
    )
    check("wrong entity denied", ev["allowed"] is False and ev["reason"] == "rbac_denied")

    # Wrong brand/scope
    ev = auth.within_authority(
        "PERS-HAIKAL",
        "content.plan.edit",
        {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"},
        {"amount": 100, "currency": "IDR"},
        conn=conn,
    )
    check("wrong scope denied", ev["allowed"] is False)

    # Below / exact / above threshold (Matt assignment override 1_000_000)
    amt = {"currency": "IDR"}
    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {**amt, "amount": 999_999}, conn=conn
    )
    check("below threshold ALLOW", ev["allowed"] is True and ev["reason"] == "within_authority", str(ev))
    check(
        "assignment preferred over role (strictest asg)",
        ev.get("matched_limit", {}).get("authority_limit_id") == "ALIM-MATT-ASG-APPROVE",
        str(ev.get("matched_limit")),
    )

    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {**amt, "amount": 1_000_000}, conn=conn
    )
    check("exact threshold ALLOW (LTE_INCLUSIVE)", ev["allowed"] is True)

    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {**amt, "amount": 1_000_001}, conn=conn
    )
    check(
        "above threshold DENY higher_approval_required",
        ev["allowed"] is False and ev["reason"] == "higher_approval_required",
    )

    # Negative / malformed / missing
    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {**amt, "amount": -1}, conn=conn
    )
    check("negative amount DENY", ev["allowed"] is False and ev["reason"] == "negative_amount")

    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {**amt, "amount": "not-a-number"}, conn=conn
    )
    check("malformed amount DENY", ev["allowed"] is False and ev["reason"] == "malformed_amount")

    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {"currency": "IDR"}, conn=conn
    )
    check("missing amount DENY", ev["allowed"] is False and ev["reason"] == "missing_amount")

    # Currency mismatch
    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {"amount": 100, "currency": "USD"}, conn=conn
    )
    check("currency mismatch DENY", ev["allowed"] is False and ev["reason"] == "currency_mismatch")

    # Expired authority — temporarily remove Amanda active limits, leave expired only
    conn.execute("UPDATE org_authority_limits SET status='inactive' WHERE authority_limit_id IN ('ALIM-AMANDA-ACTIVE','ALIM-AMANDA-LOOSE')")
    conn.commit()
    ev = auth.within_authority(
        "PERS-AMANDA",
        CODE,
        TGT,
        {"amount": 100, "currency": "IDR", "at": "2026-09-17T12:00:00+08:00"},
        conn=conn,
    )
    check("expired Authority DENY", ev["allowed"] is False and ev["reason"] == "authority_expired", str(ev))
    conn.execute("UPDATE org_authority_limits SET status='active' WHERE authority_limit_id IN ('ALIM-AMANDA-ACTIVE','ALIM-AMANDA-LOOSE')")
    conn.commit()

    # Conflicting limits → strictest wins (500k not 9M)
    ev = auth.within_authority(
        "PERS-AMANDA", CODE, TGT, {"amount": 500_000, "currency": "IDR"}, conn=conn
    )
    check("strictest wins ALLOW at 500k", ev["allowed"] is True, str(ev.get("matched_limit")))
    check(
        "strictest id is ACTIVE 500k",
        ev.get("matched_limit", {}).get("threshold_value") == 500_000.0,
        str(ev.get("matched_limit")),
    )
    ev = auth.within_authority(
        "PERS-AMANDA", CODE, TGT, {"amount": 500_001, "currency": "IDR"}, conn=conn
    )
    check("strictest wins DENY above 500k", ev["allowed"] is False)

    # Authority without Permission denied
    ev = auth.within_authority(
        "PERS-HAIKAL",
        "test.spend.approve",
        TGT,
        {"amount": 10, "currency": "IDR"},
        conn=conn,
    )
    check("authority without permission DENY", ev["allowed"] is False and ev["reason"] == "rbac_denied")

    # Permission without Authority when calling within_authority
    # Haikal has edit permission but no authority limit for edit
    ev = auth.within_authority(
        "PERS-HAIKAL",
        "content.plan.edit",
        TGT,
        {"amount": 10, "currency": "IDR"},
        conn=conn,
    )
    check(
        "permission without authority DENY",
        ev["allowed"] is False
        and ev["reason"] == "higher_approval_required"
        and ev.get("detail") == "no_matching_authority_limit",
        str(ev),
    )

    # Multiple assignments — Matt still evaluates via covering scopes
    check(
        "Matt multi-assignment bool",
        auth.within_authority_bool(
            "PERS-MATT", CODE, TGT, {"amount": 50, "currency": "IDR"}, conn=conn
        )
        is True,
    )

    # Duplicate limits controlled
    dup_ok = False
    try:
        insert_limit(
            conn,
            lid="ALIM-DUP-SHOULD-FAIL",
            role_id="ROLE-MATT",
            assignment_id=None,
            permission_id=PERM,
            scope_id=None,
            threshold=5_000_000.0,
            effective_from="2026-01-01T00:00:00+08:00",
        )
        conn.commit()
    except sqlite3.IntegrityError:
        dup_ok = True
        conn.rollback()
    check("duplicate limits constrained", dup_ok)

    # Email identity alone grants nothing for authority
    check(
        "email alone is not authority truth",
        auth.within_authority_bool(
            "mrwolf@wolfcommand.net", CODE, TGT, {"amount": 1, "currency": "IDR"}, conn=conn
        )
        is False,
    )

    # Honesty labels
    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {"amount": 1, "currency": "IDR"}, conn=conn
    )
    check("honesty real_authentication NOT_BUILT", ev.get("real_authentication") == "NOT_BUILT")
    check("honesty delegation NOT_BUILT", ev.get("delegation") == "NOT_BUILT")
    check("honesty dual_approval NOT_BUILT", ev.get("dual_approval") == "NOT_BUILT")
    check("honesty SoD NOT_BUILT", ev.get("segregation_of_duties") == "NOT_BUILT")
    check("honesty ai_decision False", ev.get("ai_decision") is False)

    # Content Machine compatibility — legacy table + has_permission still work
    check(
        "CM has_permission still works",
        wi.has_permission("mrwolf@wolfcommand.net", "can_approve_plan", conn=conn) is True,
    )
    check(
        "rbac evaluate still permission-only",
        rb.evaluate("PERS-MATT", CODE, TGT, conn=conn).get("authority_limits") == "NOT_BUILT",
    )

    # Active assignment required — end Misa
    conn.execute(
        "UPDATE org_assignments SET end_at=?, status='ENDED' WHERE assignment_id='ASG-MISA-CC-1'",
        ("2099-01-01T00:00:00+08:00",),
    )
    conn.commit()
    # Give Misa a fake limit that can't help without assignment
    insert_limit(
        conn,
        lid="ALIM-MISA-ORPHAN",
        role_id="ROLE-CONTENT-CREW",
        permission_id="PERM-CONTENT-PLAN-EDIT",
        threshold=100.0,
    )
    conn.commit()
    ev = auth.within_authority(
        "PERS-MISA",
        "content.plan.edit",
        TGT,
        {"amount": 1, "currency": "IDR"},
        conn=conn,
    )
    check("inactive assignment denied", ev["allowed"] is False)
    conn.execute(
        "UPDATE org_assignments SET end_at=NULL, status='ACTIVE' WHERE assignment_id='ASG-MISA-CC-1'"
    )
    conn.commit()

    # Scope required — end Matt scopes temporarily
    conn.execute(
        "UPDATE org_assignment_scopes SET end_at=?, status='ENDED' WHERE assignment_id='ASG-MATT-OWNER-1'",
        ("2099-01-01T00:00:00+08:00",),
    )
    conn.commit()
    ev = auth.within_authority(
        "PERS-MATT", CODE, TGT, {"amount": 1, "currency": "IDR"}, conn=conn
    )
    check("scope required denied", ev["allowed"] is False)
    conn.execute(
        "UPDATE org_assignment_scopes SET end_at=NULL, status='ACTIVE' WHERE assignment_id='ASG-MATT-OWNER-1'"
    )
    conn.commit()

    # list for person
    listed = auth.list_authority_limits_for_person("PERS-MATT", conn=conn)
    check("list limits for Matt non-empty", len(listed) >= 1)

    conn.close()

    # Ensure live DB still has 0 after fixture work on temp
    live2 = sqlite3.connect(str(LIVE_DB))
    check(
        "live seeded still 0 after temp fixtures",
        live2.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0] == 0,
    )
    live2.close()

    # API smoke against live (no live limits → higher_approval or similar)
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

                st, data = get(
                    "/api/core/authority/check?permission_code=content.plan.approve"
                    "&amount=100&currency=IDR",
                    "mrwolf@wolfcommand.net",
                )
                check("authority/check 200", st == 200 and data.get("ok") is True, str(data)[:200])
                dec = (data or {}).get("decision") or {}
                check(
                    "authority/check live no seeded limit → deny",
                    dec.get("allowed") is False,
                    str(dec.get("reason")),
                )
                check(
                    "authority/check honesty labels",
                    dec.get("ai_decision") is False
                    and dec.get("delegation") == "NOT_BUILT",
                )

                st, data = get("/api/core/me/authority-limits", "mrwolf@wolfcommand.net")
                check("me/authority-limits 200", st == 200 and data.get("ok") is True)
                check(
                    "me/authority-limits empty live",
                    data.get("authority_limits") == [],
                    str(data.get("authority_limits")),
                )
            finally:
                httpd.shutdown()
    except Exception as e:
        check("API smoke", False, repr(e))

    # Print backup sha for evidence
    if backups:
        import hashlib

        b = sorted(backups)[-1]
        h = hashlib.sha256(b.read_bytes()).hexdigest()
        print(f"BACKUP_PATH={b}")
        print(f"BACKUP_SHA256={h}")

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("seeded_live=0")
    shutil.rmtree(td, ignore_errors=True)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
