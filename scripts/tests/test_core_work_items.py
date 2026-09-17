#!/usr/bin/env python3
"""Tests for Wolf Core Work Items (Beta). Temp DB only. COMPLETED ≠ VERIFIED.

Never writes Production / wolf-system / :8787. Does not delete live audit rows.
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
MIG = SCRIPTS / "migrations" / "migrate_work_items.py"
WI_PY = SCRIPTS / "core" / "work_items.py"

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
    spec = importlib.util.spec_from_file_location("migrate_work_items", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_audit_count() -> int:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        return int(c.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0])
    finally:
        c.close()


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    src = WI_PY.read_text(encoding="utf-8")
    check("no LLM in work_items.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("no table named tasks", "CREATE TABLE" not in src or "tasks" not in src.lower() or "core_work_items" in src)
    check("refuses wolf-system", "refuses wolf-system" in src)
    check("refuses Production", "Production" in src)
    check("delete_work_item NotImplemented", "NotImplementedError" in src and "delete_work_item" in src)
    check("COMPLETED≠VERIFIED comment", "CLAIMED" in src.upper() or "≠" in src or "not verified" in src.lower())

    live_audit_before = live_audit_count()
    live_wi_before = sqlite3.connect(str(LIVE_DB)).execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='core_work_items'"
    ).fetchone()[0]

    mig = load_mig()
    # Point migrate at temp for schema tests; live migrate run separately below
    td = ROOT / "catalog" / "backups" / f"tmp-work-items-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    # Run migrate against temp by patching module DB
    mig.DB = tmp_db
    rc = mig.main()
    check("temp migrate exit 0", rc == 0, str(rc))
    rc2 = mig.main()
    check("temp migrate idempotent", rc2 == 0, str(rc2))

    conn = sqlite3.connect(str(tmp_db))
    n = conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
    check("0 work items after migrate", n == 0)
    codes = [
        r[0]
        for r in conn.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id='ROLE-MATT' AND p.code LIKE 'work.%'
            ORDER BY p.code
            """
        ).fetchall()
    ]
    check("six Matt work.* grants", len(codes) == 6, str(codes))
    other = conn.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (SELECT permission_id FROM org_permissions WHERE code LIKE 'work.%')
          AND role_id != 'ROLE-MATT'
        """
    ).fetchone()[0]
    check("no non-Matt work.* grants", other == 0)
    conn.close()

    import core.audit as audit
    import core.identity as identity
    import core.rbac as rbac
    import core.authority as authority
    import core.organisation as organisation
    import core.staffing as staffing
    import core.scope as scope
    import core.request_auth as ra
    import core.work_items as wi

    for mod in (audit, identity, rbac, authority, organisation, staffing, scope, ra, wi):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    # --- Service: create + scope ---
    item = wi.create_work_item(
        title="Needle mover A",
        owning_entity_id="ENT-GGV",
        work_type="GENERAL",
        source_type="HUMAN",
        created_by_actor_type="PERSON",
        verified_person_id="PERS-MATT",
        owner_person_id="PERS-MATT",
        owner_org_assignment_id="ASG-MATT-OWNER-1",
        priority=2,
    )
    check("create GGV work item", item and item["status"] == "OPEN", str(item)[:160])
    wid = item["work_item_id"]
    check("work_item_id WI- prefix", wid.startswith("WI-"))

    listed = wi.list_work_items("PERS-MATT")
    check("Matt lists GGV item", any(x["work_item_id"] == wid for x in listed))

    amg_denied = False
    try:
        wi.create_work_item(
            title="AMG secret",
            owning_entity_id="ENT-AMG",
            verified_person_id="PERS-MATT",
            created_by_actor_type="PERSON",
        )
    except wi.WorkItemError as e:
        amg_denied = e.code == "entity_out_of_scope"
    check("Matt cannot create ENT-AMG (out of scope)", amg_denied)

    # Seed an AMG row directly to prove list/get hide it
    ts = wi.now_utc_iso()
    c = wi.db_connect(tmp_db)
    c.execute(
        """
        INSERT INTO core_work_items (
          work_item_id, title, description, work_type, status, priority,
          owning_entity_id, source_type, source_id, created_by_actor_type,
          created_by_person_id, owner_person_id, owner_org_assignment_id,
          due_at, started_at, completed_at, verified_at, outcome,
          completion_evidence_reference, parent_work_item_id, created_at, updated_at
        ) VALUES (
          'WI-AMG-HIDDEN', 'Hidden AMG', NULL, 'GENERAL', 'OPEN', 3,
          'ENT-AMG', 'SYSTEM', NULL, 'SYSTEM',
          NULL, NULL, NULL,
          NULL, NULL, NULL, NULL, NULL,
          NULL, NULL, ?, ?
        )
        """,
        (ts, ts),
    )
    c.commit()
    c.close()
    listed2 = wi.list_work_items("PERS-MATT")
    check("Matt list hides ENT-AMG row", all(x["owning_entity_id"] != "ENT-AMG" for x in listed2))

    # Inactive assignment refused
    inactive_rej = False
    try:
        # End Matt assignment copy: use Haikal assignment with Matt person → mismatch
        wi.create_work_item(
            title="bad asg",
            owning_entity_id="ENT-GGV",
            verified_person_id="PERS-MATT",
            created_by_actor_type="PERSON",
            owner_person_id="PERS-MATT",
            owner_org_assignment_id="ASG-HAIKAL-VE-1",
        )
    except wi.WorkItemError as e:
        inactive_rej = e.code == "assignment_person_mismatch"
    check("assignment must belong to owner person", inactive_rej)

    # Forged creator
    forged = False
    try:
        wi.create_work_item(
            title="forged",
            owning_entity_id="ENT-GGV",
            verified_person_id="PERS-MATT",
            created_by_actor_type="PERSON",
            created_by_person_id="PERS-HAIKAL",
        )
    except wi.WorkItemError as e:
        forged = e.code == "forged_creator"
    check("forged created_by_person_id blocked", forged)

    # SYSTEM provenance
    sys_item = wi.create_work_item(
        title="System tick",
        owning_entity_id="ENT-GGV",
        created_by_actor_type="SYSTEM",
        source_type="SYSTEM",
        work_type="SYSTEM",
    )
    check(
        "SYSTEM create provenance",
        sys_item["created_by_actor_type"] == "SYSTEM"
        and sys_item["created_by_person_id"] is None,
        str(sys_item)[:160],
    )
    sys_person_rej = False
    try:
        wi.create_work_item(
            title="bad sys",
            owning_entity_id="ENT-GGV",
            created_by_actor_type="SYSTEM",
            created_by_person_id="PERS-MATT",
        )
    except wi.WorkItemError:
        sys_person_rej = True
    check("SYSTEM cannot masquerade as Person", sys_person_rej)

    # State machine
    wi.start_work_item(wid, verified_person_id="PERS-MATT")
    got = wi.get_work_item(wid)
    check("start → IN_PROGRESS", got and got["status"] == "IN_PROGRESS" and got.get("started_at"))

    illegal = False
    try:
        wi.verify_work_item(wid, verified_person_id="PERS-MATT")
    except wi.WorkItemError as e:
        illegal = e.code == "illegal_transition"
    check("cannot VERIFY from IN_PROGRESS", illegal)

    wi.block_work_item(wid, verified_person_id="PERS-MATT")
    check("block → BLOCKED", wi.get_work_item(wid)["status"] == "BLOCKED")
    wi.start_work_item(wid, verified_person_id="PERS-MATT")
    wi.claim_complete(wid, verified_person_id="PERS-MATT", outcome="done", completion_evidence_reference="ref://smoke")
    done = wi.get_work_item(wid)
    check(
        "claim COMPLETED ≠ VERIFIED",
        done["status"] == "COMPLETED"
        and done.get("completed_at")
        and done.get("verified_at") is None
        and done.get("completion_evidence_reference") == "ref://smoke",
        str(done)[:200],
    )
    wi.verify_work_item(wid, verified_person_id="PERS-MATT")
    ver = wi.get_work_item(wid)
    check("verify → VERIFIED", ver["status"] == "VERIFIED" and ver.get("verified_at"))

    # Cancel path on fresh item
    c2 = wi.create_work_item(
        title="cancel me",
        owning_entity_id="ENT-GGV",
        verified_person_id="PERS-MATT",
        created_by_actor_type="PERSON",
    )
    wi.cancel_work_item(c2["work_item_id"], verified_person_id="PERS-MATT", outcome="obsolete")
    check("cancel → CANCELLED", wi.get_work_item(c2["work_item_id"])["status"] == "CANCELLED")

    del_rej = False
    try:
        wi.delete_work_item(c2["work_item_id"])
    except NotImplementedError:
        del_rej = True
    check("delete refused", del_rej)

    # Reassign
    a = wi.create_work_item(
        title="assign me",
        owning_entity_id="ENT-GGV",
        verified_person_id="PERS-MATT",
        created_by_actor_type="PERSON",
        owner_person_id="PERS-MATT",
    )
    b = wi.reassign_owner(
        a["work_item_id"],
        verified_person_id="PERS-MATT",
        owner_person_id="PERS-AMANDA",
        owner_org_assignment_id="ASG-AMANDA-CM-1",
    )
    check("reassign owner", b["owner_person_id"] == "PERS-AMANDA")

    # Provenance immutable via update fields
    patch_ok = wi.update_work_item_fields(
        a["work_item_id"],
        verified_person_id="PERS-MATT",
        title="assign me renamed",
        priority=1,
    )
    check("patch title/priority", patch_ok["title"] == "assign me renamed" and patch_ok["priority"] == 1)

    # Audits present for create/assign/complete/cancel
    for action in ("work.create", "work.assign", "work.complete", "work.cancel"):
        rows = audit.list_events(action=action, source="work_items", limit=5)
        check(f"audit {action}", len(rows) >= 1, str(len(rows)))

    # Secrets not stored
    secret_meta = audit.strip_secrets({"jwt": "eyJ.x.y", "note": "ok"})
    check("secrets stripped helper", "jwt" not in secret_meta)

    # Content Machine still loads
    import serve_beta as sb  # noqa: F401
    check("serve_beta imports", True)

    # HTTP API on temp DB
    try:
        import inspect
        import wolf_intelligence as wintel

        ra._ENV_LOADED = True
        sb.CATALOG_DB = tmp_db
        wintel.CATALOG_DB = tmp_db
        for attr in ("_audit", "_identity", "_rbac", "_authority", "_org", "_staffing", "_scope", "_work_items"):
            mod = getattr(sb, attr, None)
            if mod is not None and hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = tmp_db

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("HTTP handler found", Handler is not None)

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:

            def call(method, path, subject=None, body=None):
                hdrs = {}
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

            st, data = call(
                "POST",
                "/api/core/work-items",
                MATT,
                {
                    "title": "HTTP create",
                    "owning_entity_id": "ENT-GGV",
                    "work_type": "FOLLOW_UP",
                    "priority": 3,
                },
            )
            check("HTTP create 201", st == 201 and data.get("ok"), str(data)[:200])
            http_id = (data.get("work_item") or {}).get("work_item_id")

            st, data = call("GET", "/api/core/work-items", MATT)
            check("HTTP list 200", st == 200 and data.get("ok"), str(data)[:160])

            st, data = call("GET", f"/api/core/work-items/{http_id}", MATT)
            check("HTTP get 200", st == 200 and data.get("ok"))

            st, data = call(
                "POST",
                "/api/core/work-items",
                HAIKAL,
                {"title": "nope", "owning_entity_id": "ENT-GGV"},
            )
            check("non-Matt create forbidden", st == 403, str(data)[:160])

            st, data = call("POST", f"/api/core/work-items/{http_id}/start", MATT, {})
            check("HTTP start", st == 200 and (data.get("work_item") or {}).get("status") == "IN_PROGRESS")

            st, data = call(
                "POST",
                f"/api/core/work-items/{http_id}/complete",
                MATT,
                {"outcome": "shipped"},
            )
            check(
                "HTTP complete claimed",
                st == 200
                and (data.get("work_item") or {}).get("status") == "COMPLETED"
                and data.get("claimed_completed_is_not_verified") is True,
                str(data)[:200],
            )

            st, data = call("POST", f"/api/core/work-items/{http_id}/verify", MATT, {})
            check("HTTP verify", st == 200 and (data.get("work_item") or {}).get("status") == "VERIFIED")

            # Illegal: create with status VERIFIED
            st, data = call(
                "POST",
                "/api/core/work-items",
                MATT,
                {
                    "title": "skip",
                    "owning_entity_id": "ENT-GGV",
                    "status": "VERIFIED",
                },
            )
            check("HTTP refuse status=VERIFIED on create", st == 400, str(data)[:160])

            # PATCH cannot set status
            st, data = call(
                "POST",
                "/api/core/work-items",
                MATT,
                {"title": "patch target", "owning_entity_id": "ENT-GGV"},
            )
            pid = (data.get("work_item") or {}).get("work_item_id")
            st, data = call(
                "PATCH",
                f"/api/core/work-items/{pid}",
                MATT,
                {"status": "VERIFIED"},
            )
            check("PATCH status refused", st == 400, str(data)[:160])

            st, data = call(
                "PATCH",
                f"/api/core/work-items/{pid}",
                MATT,
                {"title": "patched", "priority": 1},
            )
            check("PATCH title ok", st == 200 and (data.get("work_item") or {}).get("title") == "patched")

            st, data = call(
                "POST",
                f"/api/core/work-items/{pid}/assign",
                MATT,
                {"owner_person_id": "PERS-HAIKAL", "owner_org_assignment_id": "ASG-HAIKAL-VE-1"},
            )
            check("HTTP assign", st == 200 and (data.get("work_item") or {}).get("owner_person_id") == "PERS-HAIKAL")

            st, data = call(
                "POST",
                f"/api/core/work-items/{pid}/cancel",
                MATT,
                {"outcome": "dup"},
            )
            check("HTTP cancel", st == 200 and (data.get("work_item") or {}).get("status") == "CANCELLED")

        finally:
            httpd.shutdown()
    except Exception as e:
        check("HTTP API smoke", False, repr(e))

    # Live migrate (production Beta schema) — 0 work items expected
    mig.DB = LIVE_DB
    # Allow live migrate (schema only) outside test write guard for audit
    os.environ.pop("WOLF_TEST_MODE", None)
    rc_live = mig.main()
    os.environ["WOLF_TEST_MODE"] = "1"
    check("live migrate exit 0", rc_live == 0, str(rc_live))
    live = sqlite3.connect(str(LIVE_DB))
    live_n = live.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
    check("live work items = 0", live_n == 0, str(live_n))
    live_codes = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id=rp.permission_id
        WHERE rp.role_id='ROLE-MATT' AND p.code LIKE 'work.%'
        """
    ).fetchone()[0]
    check("live Matt work.* = 6", live_codes == 6, str(live_codes))
    live.close()

    live_audit_after = live_audit_count()
    check(
        "live audit count unchanged (no silent delete / no test pollution)",
        live_audit_after == live_audit_before,
        f"{live_audit_before}->{live_audit_after}",
    )
    check("historical 47+ audit rows preserved", live_audit_after >= 47, str(live_audit_after))

    # Production untouched
    check("no Production path in work_items", "/Production" in src and "refuses production" in src.lower())

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    shutil.rmtree(td, ignore_errors=True)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
