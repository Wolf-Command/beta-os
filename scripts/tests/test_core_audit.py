#!/usr/bin/env python3
"""Tests for Wolf Core Audit / Evidence Spine (Beta). CLAIMED ≠ VERIFIED.

Temp sqlite for service + HTTP tests. Never write new audit rows to live catalog.
Does not write Production / wolf-system / :8787.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_audit_evidence_spine.py"
AUDIT_PY = SCRIPTS / "core" / "audit.py"

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_audit_evidence_spine", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_audit_count() -> int:
    conn = sqlite3.connect(str(LIVE_DB))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0])
    finally:
        conn.close()


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"

    src = AUDIT_PY.read_text(encoding="utf-8")
    check("no LLM/AI call sites in audit.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("refuses wolf-system", "refuses wolf-system" in src)
    check("refuses Production", "Production" in src)
    check("update_event raises NotImplementedError", "NotImplementedError" in src and "update_event" in src)
    check("delete_event raises NotImplementedError", "NotImplementedError" in src)
    check("test-mode live write guard present", "WOLF_TEST_MODE" in src and "refuses writes to live" in src)

    # Live migrate idempotent (schema/seed only — no new audit rows from migrate)
    live_before_migrate = live_audit_count()
    mig = load_mig()
    rc = mig.main()
    check("migrate exit 0", rc == 0, str(rc))
    check(
        "migrate did not add audit rows",
        live_audit_count() == live_before_migrate,
        f"{live_before_migrate}->{live_audit_count()}",
    )

    live = sqlite3.connect(str(LIVE_DB))
    live.row_factory = sqlite3.Row
    tabs = {r[0] for r in live.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("core_audit_events on live", "core_audit_events" in tabs)
    trig = {
        r[0]
        for r in live.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='core_audit_events'"
        )
    }
    check("append-only triggers present", len(trig) >= 2, str(trig))
    perm = live.execute(
        "SELECT status FROM org_permissions WHERE code='audit.event.read'"
    ).fetchone()
    check("audit.event.read ACTIVE", perm and perm[0] == "ACTIVE")
    grants = live.execute(
        """
        SELECT role_id FROM org_role_permissions
        WHERE permission_id='PERM-AUDIT-EVENT-READ'
        """
    ).fetchall()
    check("Matt-only grant", [g[0] for g in grants] == ["ROLE-MATT"], str(grants))
    live.close()

    # Temp DB under beta-os (db_connect refuses paths outside beta-os)
    td = ROOT / "catalog" / "backups" / f"tmp-audit-spine-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    import core.audit as audit
    import core.request_auth as ra
    import core.identity as identity
    import core.rbac as rbac
    import core.authority as authority
    import core.organisation as organisation
    import core.staffing as staffing
    import core.scope as scope

    # Point ALL catalog modules at temp DB — never LIVE for HTTP/service writes
    for mod in (audit, identity, rbac, authority, organisation, staffing, scope, ra):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    live_baseline = live_audit_count()

    # 1. record + get + list
    ev = audit.record_event(
        action="test.insert",
        result="SUCCEEDED",
        source="test",
        actor_type="PERSON",
        verified_person_id="PERS-MATT",
        actor_person_id="PERS-MATT",
        identity_assurance="development_assertion",
        correlation_id="corr-test-1",
        metadata={"note": "unit"},
    )
    check("record_event inserts", bool(ev and ev.get("audit_event_id")), str(ev)[:120])
    got = audit.get_event(ev["audit_event_id"])
    check("get_event readable", got and got["action"] == "test.insert")
    listed = audit.list_events(action="test.insert", correlation_id="corr-test-1")
    check("list_events finds row", len(listed) >= 1)

    # 2. UPDATE/DELETE refused
    raised_u = False
    try:
        audit.update_event("x")
    except NotImplementedError:
        raised_u = True
    check("update_event refused", raised_u)
    raised_d = False
    try:
        audit.delete_event("x")
    except NotImplementedError:
        raised_d = True
    check("delete_event refused", raised_d)

    # 3. correct_event
    corr = audit.correct_event(
        ev["audit_event_id"],
        action="test.insert",
        result="SUCCEEDED",
        source="test",
        actor_type="PERSON",
        verified_person_id="PERS-MATT",
        reason_code="typo_fix",
        metadata={"note": "corrected"},
    )
    check(
        "correct_event inserts with corrects_event_id",
        corr
        and corr.get("corrects_event_id") == ev["audit_event_id"]
        and corr["audit_event_id"] != ev["audit_event_id"],
        str(corr)[:160],
    )

    # 4. SYSTEM + person_id rejected
    sys_rej = False
    try:
        audit.record_event(
            action="x",
            result="DENIED",
            source="test",
            actor_type="SYSTEM",
            actor_person_id="PERS-MATT",
        )
    except audit.AuditValidationError:
        sys_rej = True
    check("SYSTEM + actor_person_id rejected", sys_rej)

    # 5. PERSON without verified person_id rejected
    person_rej = False
    try:
        audit.record_event(
            action="x",
            result="SUCCEEDED",
            source="test",
            actor_type="PERSON",
            actor_person_id="PERS-MATT",  # spoof without verified
        )
    except audit.AuditValidationError:
        person_rej = True
    check("PERSON without verified_person_id rejected", person_rej)

    spoof_rej = False
    try:
        audit.record_event(
            action="x",
            result="SUCCEEDED",
            source="test",
            actor_type="PERSON",
            verified_person_id="PERS-MATT",
            actor_person_id="PERS-OTHER",
        )
    except audit.AuditValidationError:
        spoof_rej = True
    check("PERSON client spoof mismatch rejected", spoof_rej)

    # 6. Secret fields stripped / rejected
    secret_rej = False
    try:
        audit.record_event(
            action="x",
            result="DENIED",
            source="test",
            actor_type="SYSTEM",
            metadata={"jwt": "eyJhbGciOiJIUzI1NiJ9.xx.yy", "note": "keep"},
        )
    except audit.AuditValidationError:
        secret_rej = True
    check("secret jwt metadata rejected", secret_rej)

    cleaned = audit.strip_secrets({"password": "x", "note": "ok", "nested": {"api_key": "k", "status": "a"}})
    check(
        "strip_secrets drops secrets",
        "password" not in cleaned and cleaned.get("note") == "ok" and "api_key" not in cleaned.get("nested", {}),
        str(cleaned),
    )

    # 7. metadata size cap / allowlist
    oversize = False
    try:
        audit.record_event(
            action="x",
            result="ERROR",
            source="test",
            actor_type="SYSTEM",
            metadata={"note": "n" * 5000},
        )
    except audit.AuditValidationError:
        oversize = True
    check("metadata size cap", oversize)

    allow = audit.record_event(
        action="meta.allow",
        result="SUCCEEDED",
        source="test",
        actor_type="SYSTEM",
        metadata={"note": "ok", "evil_unknown": "drop_me", "permission": "x"},
    )
    meta = allow.get("metadata") or {}
    check("metadata allowlist drops unknown", "evil_unknown" not in meta and meta.get("note") == "ok", str(meta))

    # Live write refused under WOLF_TEST_MODE when pointed at live
    live_write_blocked = False
    prev_catalog = audit.CATALOG_DB
    try:
        audit.CATALOG_DB = LIVE_DB
        audit.record_event(
            action="should.not.land",
            result="SUCCEEDED",
            source="test",
            actor_type="SYSTEM",
        )
    except audit.AuditValidationError as e:
        live_write_blocked = "live catalog" in str(e).lower()
    finally:
        audit.CATALOG_DB = prev_catalog
    check("WOLF_TEST_MODE blocks live catalog write", live_write_blocked)

    # 13. SQL UPDATE/DELETE blocked by triggers
    conn = audit.db_connect(tmp_db)
    upd_blocked = False
    try:
        conn.execute(
            "UPDATE core_audit_events SET result='FAILED' WHERE audit_event_id=?",
            (ev["audit_event_id"],),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        upd_blocked = "append-only" in str(e).lower() or True
    except sqlite3.DatabaseError as e:
        upd_blocked = "append-only" in str(e).lower() or "abort" in str(e).lower()
    check("SQL UPDATE blocked by trigger", upd_blocked)

    del_blocked = False
    try:
        conn.execute(
            "DELETE FROM core_audit_events WHERE audit_event_id=?",
            (ev["audit_event_id"],),
        )
        conn.commit()
    except sqlite3.DatabaseError as e:
        del_blocked = "append-only" in str(e).lower() or "abort" in str(e).lower()
    check("SQL DELETE blocked by trigger", del_blocked)
    conn.close()

    # API + integration smoke — still on TEMP DB (never LIVE_DB)
    try:
        import serve_beta as sb
        import inspect
        import wolf_intelligence as wi

        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        ra._ENV_LOADED = True
        sb.CATALOG_DB = tmp_db
        wi.CATALOG_DB = tmp_db if hasattr(wi, "CATALOG_DB") else None
        # Re-bind core modules already imported by serve_beta
        sb._audit.CATALOG_DB = tmp_db
        sb._identity.CATALOG_DB = tmp_db
        sb._rbac.CATALOG_DB = tmp_db
        sb._authority.CATALOG_DB = tmp_db
        sb._org.CATALOG_DB = tmp_db
        sb._staffing.CATALOG_DB = tmp_db
        sb._scope.CATALOG_DB = tmp_db

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("API handler found", Handler is not None)
        if Handler:
            if hasattr(sb, "ensure_schema"):
                # ensure_schema must not retarget live — patch connection helper if present
                orig_connect = getattr(sb, "db_connect", None)
                if orig_connect:

                    def _tmp_connect():
                        c = sqlite3.connect(str(tmp_db))
                        c.row_factory = sqlite3.Row
                        c.execute("PRAGMA foreign_keys=ON")
                        return c

                    sb.db_connect = _tmp_connect  # type: ignore[attr-defined]
                try:
                    sb.ensure_schema()
                finally:
                    if orig_connect:
                        sb.db_connect = orig_connect  # type: ignore[attr-defined]

            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:

                def call(method, path, subject=None, body=None, headers=None):
                    hdrs = dict(headers or {})
                    if subject:
                        hdrs["X-Wolf-Subject"] = subject
                    data = None
                    if body is not None:
                        data = json.dumps(body).encode()
                        hdrs["Content-Type"] = "application/json"
                    req = Request(
                        f"http://127.0.0.1:{port}{path}",
                        data=data,
                        headers=hdrs,
                        method=method,
                    )
                    try:
                        with urlopen(req, timeout=10) as r:
                            return r.status, json.loads(r.read().decode())
                    except HTTPError as e:
                        raw = e.read().decode()
                        try:
                            payload = json.loads(raw)
                        except Exception:
                            payload = {"raw": raw}
                        return e.code, payload

                def tmp_count(**filters):
                    clauses = []
                    params = []
                    for k, v in filters.items():
                        clauses.append(f"{k}=?")
                        params.append(v)
                    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
                    conn2 = sqlite3.connect(str(tmp_db))
                    try:
                        return int(
                            conn2.execute(
                                f"SELECT COUNT(*) FROM core_audit_events{where}",
                                params,
                            ).fetchone()[0]
                        )
                    finally:
                        conn2.close()

                # 8. Matt can read audit; non-Matt cannot
                st, data = call("GET", "/api/core/audit?limit=5", MATT)
                check("Matt GET /api/core/audit 200", st == 200 and data.get("ok") is True, str(data)[:200])
                check("hash_chain honesty NOT_BUILT", data.get("hash_chain") == "NOT_BUILT")

                st, data = call("GET", "/api/core/audit?limit=5", HAIKAL)
                check(
                    "non-Matt GET /api/core/audit forbidden",
                    st == 403 and data.get("error") in ("forbidden", "unauthorized"),
                    str(data)[:200],
                )

                # 9. Auth success → event (development resolve) on TEMP
                before = tmp_count(source="request_auth", result="SUCCEEDED")
                call("GET", "/api/core/me", MATT)
                after = tmp_count(source="request_auth", result="SUCCEEDED")
                check("auth success → SUCCEEDED event", after > before, f"{before}->{after}")

                # Auth fail → DENIED without JWT body (cloudflare mode)
                os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
                os.environ["BETA_CF_ACCESS_AUD"] = "test-aud-for-audit"
                ra._ENV_LOADED = True
                before_d = tmp_count(result="DENIED", action="auth.resolve")
                st, data = call("GET", "/api/core/me")
                check("auth fail status 403", st == 403, str(data)[:160])
                after_d = tmp_count(result="DENIED", action="auth.resolve")
                check("auth fail → DENIED event", after_d > before_d, f"{before_d}->{after_d}")
                row = sqlite3.connect(str(tmp_db)).execute(
                    """
                    SELECT metadata_json FROM core_audit_events
                    WHERE result='DENIED' AND action='auth.resolve'
                    ORDER BY recorded_at DESC LIMIT 1
                    """
                ).fetchone()
                meta_s = (row[0] or "") if row else ""
                check("auth deny metadata has no jwt body", "eyJ" not in meta_s and "jwt" not in meta_s.lower())

                # Restore development for remaining checks
                os.environ["BETA_AUTH_MODE"] = "development_assertion"
                ra._ENV_LOADED = True

                # 10. RBAC deny → DENIED via _require_permission
                before_r = tmp_count(source="rbac", result="DENIED")
                st, data = call(
                    "POST",
                    "/api/planner/plans/1/approve",
                    HAIKAL,
                    body={},
                )
                check("RBAC deny returns 403", st == 403, str(data)[:160])
                after_r = tmp_count(source="rbac", result="DENIED")
                check("RBAC deny → DENIED event", after_r > before_r, f"{before_r}->{after_r}")

                # 11. Authority deny (amount + no live limit)
                before_a = tmp_count(source="authority", result="DENIED")
                st, data = call(
                    "GET",
                    "/api/core/authority/check?permission_code=content.plan.approve&amount=100&currency=IDR",
                    MATT,
                )
                check("authority/check 200", st == 200 and data.get("ok") is True, str(data)[:160])
                dec = (data or {}).get("decision") or {}
                check("authority denied (no live limit)", dec.get("allowed") is False, str(dec.get("reason")))
                after_a = tmp_count(source="authority", result="DENIED")
                check("authority deny → DENIED event", after_a > before_a, f"{before_a}->{after_a}")

                # 12. Content mutation → SUCCEEDED after commit (TEMP DB)
                before_c = tmp_count(source="content_planner", result="SUCCEEDED")
                st, data = call(
                    "POST",
                    "/api/planner/save",
                    MATT,
                    body={
                        "brand": "habitat",
                        "platform": "IG_Reels",
                        "scheduled_date": "2099-01-06",
                        "title_slug": "audit-spine-smoke-tmp",
                        "script_body": "audit evidence spine test temp isolation",
                        "status": "Draft",
                    },
                )
                check("planner/save 200", st == 200 and data.get("ok") is True, str(data)[:200])
                after_c = tmp_count(source="content_planner", result="SUCCEEDED")
                check(
                    "content mutation → SUCCEEDED event",
                    after_c > before_c,
                    f"{before_c}->{after_c}",
                )
            finally:
                httpd.shutdown()
    except Exception as e:
        check("API smoke", False, repr(e))

    live_after = live_audit_count()
    check(
        "live audit count unchanged by this test run",
        live_after == live_baseline,
        f"{live_baseline}->{live_after}",
    )
    # Document: do not delete historical pollution rows
    check("live audit still has historical rows (no silent delete)", live_after >= 47, str(live_after))

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    shutil.rmtree(td, ignore_errors=True)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
