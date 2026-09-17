#!/usr/bin/env python3
"""Tests for Wolf Core Approval Engine (Beta). Temp DB only.

Live org_authority_limits must stay 0.
Live core_audit_events count must not rise.
Completing linked Work Item must NOT approve.
No dual / SoD / UI / LLM / Production.
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
MIG = SCRIPTS / "migrations" / "migrate_approval_engine.py"
APR_PY = SCRIPTS / "core" / "approvals.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
TGT_DEPT = "DEPT-GGV-CONTENT"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_approval_engine", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, int, int, int]:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        auth = (
            c.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            if "org_authority_limits" in tabs
            else 0
        )
        audit = (
            c.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0]
            if "core_audit_events" in tabs
            else 0
        )
        req = (
            c.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0]
            if "core_approval_requests" in tabs
            else 0
        )
        dec = (
            c.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0]
            if "core_approval_decisions" in tabs
            else 0
        )
        return int(auth), int(audit), int(req), int(dec)
    finally:
        c.close()


def insert_limit(conn, *, lid, permission_id=PERM_SPEND, threshold=5_000_000.0, role_id="ROLE-MATT"):
    conn.execute(
        """
        INSERT INTO org_authority_limits (
          authority_limit_id, role_id, assignment_id, permission_id, scope_id,
          limit_type, currency, threshold_value, comparison_rule,
          effective_from, effective_to, status, created_at, updated_at
        ) VALUES (?, ?, NULL, ?, NULL, 'AMOUNT', 'IDR', ?, 'LTE_INCLUSIVE',
                  '2026-01-01T00:00:00+08:00', NULL, 'active', ?, ?)
        """,
        (lid, role_id, permission_id, threshold, TS, TS),
    )


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    os.environ["BETA_APPROVAL_DENY_SELF_APPROVAL"] = "1"

    src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in approvals.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("refuses wolf-system", "refuses wolf-system" in src)
    check("refuses Production", "Production" in src)
    check("self-approval flag env", "BETA_APPROVAL_DENY_SELF_APPROVAL" in src)
    check("WI complete ≠ approve comment", "Completing a linked Work Item" in src or "≠ approving" in src)

    auth_before, audit_before, _, _ = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))

    backups = list(BACKUP_DIR.glob("pre-approval-engine-*.sqlite"))
    check("pre-approval-engine backup exists", len(backups) >= 1, str(BACKUP_DIR))

    # Live migrate
    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("live migrate idempotent", mig.main() == 0)

    auth_after, audit_mid, req_live, dec_live = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    live = sqlite3.connect(str(LIVE_DB))
    codes = [
        r[0]
        for r in live.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id='ROLE-MATT' AND p.code LIKE 'approval.%'
            ORDER BY p.code
            """
        ).fetchall()
    ]
    check("four Matt approval.* grants", codes == [
        "approval.cancel", "approval.decide", "approval.read", "approval.request"
    ], str(codes))
    other = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (SELECT permission_id FROM org_permissions WHERE code LIKE 'approval.%')
          AND role_id NOT IN (
            'ROLE-MATT',
            'ROLE-GGV-CREATIVE-DIRECTOR',
            'ROLE-CONTENT-MGMT',
            'ROLE-GGV-EDIT',
            'ROLE-CONTENT-CREW'
          )
        """
    ).fetchone()[0]
    check("no unexpected non-Habitat approval.* grants", other == 0)
    live.close()

    # Temp DB for all mutating tests
    td = ROOT / "catalog" / "backups" / f"tmp-approval-engine-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    mig.DB = tmp_db
    check("temp migrate exit 0", mig.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Activate PERM-TEST-SPEND + grant + fixture authority limit (TEMP ONLY)
    conn.execute(
        "UPDATE org_permissions SET status='ACTIVE', updated_at=? WHERE permission_id=?",
        (TS, PERM_SPEND),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-MATT', ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
        """,
        (PERM_SPEND, TS, TS),
    )
    insert_limit(conn, lid="ALIM-TMP-SPEND-MATT", threshold=5_000_000.0)
    conn.commit()
    tmp_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
    check("temp has fixture authority limits", tmp_auth >= 1, str(tmp_auth))
    conn.close()

    # Point all modules at temp
    import core.audit as audit
    import core.identity as identity
    import core.rbac as rbac
    import core.authority as authority
    import core.organisation as organisation
    import core.staffing as staffing
    import core.scope as scope
    import core.request_auth as ra
    import core.work_items as wi
    import core.approvals as apr

    for mod in (
        audit, identity, rbac, authority, organisation, staffing, scope, ra, wi, apr
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    # --- Create general request ---
    req = apr.create_approval_request(
        title="Buy cameras",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="1000000",
        currency="IDR",
        verified_person_id="PERS-MATT",
        requested_by_assignment_id="ASG-MATT-OWNER-1",
        link_work_item=True,
        review_owner_person_id="PERS-MATT",
    )
    check("create PENDING spend request", req["status"] == "PENDING", str(req)[:200])
    rid = req["approval_request_id"]
    check("APR- prefix", rid.startswith("APR-"))
    check("snapshot_hash set", bool(req.get("snapshot_hash")))
    check("linked work item created", bool(req.get("linked_work_item_id")))
    linked = req["linked_work_item_id"]
    wi_row = wi.get_work_item(linked)
    check(
        "linked WI is APPROVAL_REQUIRED SYSTEM",
        wi_row
        and wi_row["work_type"] == "APPROVAL_REQUIRED"
        and wi_row["source_type"] == "SYSTEM"
        and wi_row["source_id"] == rid
        and wi_row["status"] == "OPEN",
        str(wi_row)[:200] if wi_row else "missing",
    )

    # Forged requester refused
    forged = False
    try:
        apr.create_approval_request(
            title="spoof",
            owning_entity_id="ENT-GGV",
            required_permission_code=CODE_SPEND,
            verified_person_id="PERS-MATT",
            requested_by_person_id="PERS-HAIKAL",
        )
    except apr.ApprovalError as e:
        forged = e.code == "forged_requester"
    check("forged requested_by refused", forged)

    # APR-RT-001: material types require amount+currency at create
    spend_no_amt = False
    try:
        apr.create_approval_request(
            title="spend no amount",
            owning_entity_id="ENT-GGV",
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            currency="IDR",
            verified_person_id="PERS-MATT",
        )
    except apr.ApprovalError as e:
        spend_no_amt = e.code == "missing_amount"
    check("create SPEND without amount fails", spend_no_amt)

    exc_no_amt = False
    try:
        apr.create_approval_request(
            title="exception no amount",
            owning_entity_id="ENT-GGV",
            required_permission_code=CODE_SPEND,
            request_type="EXCEPTION",
            currency="IDR",
            verified_person_id="PERS-MATT",
        )
    except apr.ApprovalError as e:
        exc_no_amt = e.code == "missing_amount"
    check("create EXCEPTION without amount fails", exc_no_amt)

    spend_no_cur = False
    try:
        apr.create_approval_request(
            title="spend no currency",
            owning_entity_id="ENT-GGV",
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            material_amount="1000",
            verified_person_id="PERS-MATT",
        )
    except apr.ApprovalError as e:
        spend_no_cur = e.code == "missing_currency"
    check("create SPEND without currency fails", spend_no_cur)

    # Immutable mutation helper
    imm = False
    try:
        apr.refuse_immutable_mutation({"material_amount": "9", "title": "x"})
    except apr.ApprovalError as e:
        imm = e.code == "immutable_fields"
    check("immutable fields helper", imm)

    # Completing linked WI must NOT approve
    wi.start_work_item(linked, verified_person_id="PERS-MATT")
    wi.claim_complete(linked, verified_person_id="PERS-MATT", outcome="reviewed")
    wi.verify_work_item(linked, verified_person_id="PERS-MATT")
    still = apr.get_approval_request(rid)
    check(
        "WI complete/verify does NOT approve",
        still and still["status"] == "PENDING",
        str(still.get("status") if still else None),
    )
    check("no decision rows after WI verify", len(apr.list_decisions(rid)) == 0)

    # Self-approval denied (same person, material)
    self_denied = False
    try:
        apr.approve_request(rid, verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        self_denied = e.code == "self_approval_denied"
    check("self-approval DENIED on material", self_denied)
    check("still PENDING after self-deny", apr.get_approval_request(rid)["status"] == "PENDING")
    self_aud = audit.list_events(action="approval.self_denied", source="approvals", limit=5)
    check("audit approval.self_denied", len(self_aud) >= 1)

    # Create second request as Matt, approve needs a different approver —
    # For temp: create as Amanda path. Seed Amanda ROLE with spend + approval.decide?
    # Simpler: create request as SYSTEM-like via raw insert of second person request,
    # then Matt (not requester) approves.
    # Amanda may lack approval.decide. Grant on TEMP only to ROLE-CONTENT-MGMT for fixtures.
    c = sqlite3.connect(str(tmp_db))
    for pid in (
        "PERM-APPROVAL-READ",
        "PERM-APPROVAL-REQUEST",
        "PERM-APPROVAL-DECIDE",
        "PERM-APPROVAL-CANCEL",
        PERM_SPEND,
    ):
        c.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-CONTENT-MGMT', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
            """,
            (pid, TS, TS),
        )
    insert_limit(
        c,
        lid="ALIM-TMP-SPEND-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
        threshold=5_000_000.0,
    )
    c.commit()
    c.close()

    # Amanda creates; Matt approves (different person → not self)
    amanda_req = apr.create_approval_request(
        title="Lens kit",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="500000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    arid = amanda_req["approval_request_id"]
    approved = apr.approve_request(arid, verified_person_id="PERS-MATT", reason="ok within limit")
    check(
        "Matt approves Amanda spend",
        approved["request"]["status"] == "APPROVED"
        and approved["executed_source"] is False
        and approved["work_item_completed"] is False,
        str(approved)[:240],
    )
    check("decision row APPROVED", approved["decision"]["decision"] == "APPROVED")
    grant_aud = audit.list_events(action="approval.granted", source="approvals", limit=5)
    check("audit approval.granted", len(grant_aud) >= 1)

    # Second decide → 409
    second = False
    try:
        apr.approve_request(arid, verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        second = e.code in ("already_decided", "not_pending") and e.http_status == 409
    check("second decide → 409", second)

    # Authority denied: amount above fixture limit
    over = apr.create_approval_request(
        title="Too much",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="9000000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
    )
    auth_denied = False
    try:
        apr.approve_request(over["approval_request_id"], verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        auth_denied = e.code == "authority_denied"
    check("authority denied above limit", auth_denied)
    auth_aud = audit.list_events(action="approval.authority_denied", source="approvals", limit=5)
    check("audit approval.authority_denied", len(auth_aud) >= 1)

    # APR-RT-001: forged PENDING SPEND with NULL amount → APPROVE must deny (fail-closed)
    c = sqlite3.connect(str(tmp_db))
    c.row_factory = sqlite3.Row
    forge_id = "APR-FORGE-NULL-AMT"
    forge_ts = "2026-09-17T01:00:00Z"
    c.execute(
        """
        INSERT INTO core_approval_requests (
          approval_request_id, request_type, title, description,
          owning_entity_id, brand_id, location_id, department_id,
          requested_by_person_id, requested_by_assignment_id,
          required_permission_code, required_permission_id,
          material_amount, currency, source_type, source_id,
          evidence_reference, status, requested_at, decided_at, expires_at,
          created_at, updated_at, correlation_id, linked_work_item_id,
          prior_request_id, snapshot_hash
        ) VALUES (
          ?, 'SPEND', 'forged null amount', NULL,
          'ENT-GGV', NULL, NULL, ?,
          'PERS-AMANDA', 'ASG-AMANDA-CM-1',
          ?, ?,
          NULL, NULL, 'HUMAN', NULL,
          NULL, 'PENDING', ?, NULL, NULL,
          ?, ?, 'CORR-FORGE-NULL', NULL,
          NULL, 'forge-null-amt'
        )
        """,
        (forge_id, TGT_DEPT, CODE_SPEND, PERM_SPEND, forge_ts, forge_ts, forge_ts),
    )
    c.commit()
    c.close()
    null_amt_denied = False
    null_amt_code = None
    try:
        apr.approve_request(forge_id, verified_person_id="PERS-MATT", reason="should deny")
    except apr.ApprovalError as e:
        null_amt_code = e.code
        # DLG-RT-001 / APR-RT-001: fail-closed missing_amount before authority (native + dlg)
        null_amt_denied = e.code == "missing_amount"
    forged_row = apr.get_approval_request(forge_id)
    check(
        "forge NULL-amount SPEND approve → missing_amount denied",
        null_amt_denied and forged_row and forged_row["status"] == "PENDING",
        f"code={null_amt_code} status={forged_row.get('status') if forged_row else None}",
    )

    # Reject path (no authority required) — amount over limit still rejectable
    rejected = apr.reject_request(
        over["approval_request_id"],
        verified_person_id="PERS-MATT",
        reason="too expensive",
    )
    check("reject without authority", rejected["request"]["status"] == "REJECTED")
    rej_aud = audit.list_events(action="approval.rejected", source="approvals", limit=5)
    check("audit approval.rejected", len(rej_aud) >= 1)

    # Cancel own
    cancel_me = apr.create_approval_request(
        title="cancel me",
        owning_entity_id="ENT-GGV",
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-MATT",
    )
    cancelled = apr.cancel_request(cancel_me["approval_request_id"], verified_person_id="PERS-MATT")
    check("cancel own PENDING", cancelled["status"] == "CANCELLED")
    can_aud = audit.list_events(action="approval.cancelled", source="approvals", limit=5)
    check("audit approval.cancelled", len(can_aud) >= 1)

    # Lazy expire
    exp = apr.create_approval_request(
        title="expired",
        owning_entity_id="ENT-GGV",
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-AMANDA",
        expires_at="2020-01-01T00:00:00Z",
    )
    got_exp = apr.get_approval_request(exp["approval_request_id"])
    check("lazy expire on get", got_exp and got_exp["status"] == "EXPIRED")
    exp_decide = False
    try:
        apr.approve_request(exp["approval_request_id"], verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        exp_decide = e.code == "expired"
    check("decide on expired → denied", exp_decide)

    # Append-only decisions
    del_rej = False
    try:
        apr.delete_decision("x")
    except NotImplementedError:
        del_rej = True
    check("delete decision refused", del_rej)

    # Live DB still clean after temp tests
    auth_end, audit_end, req_end, dec_end = live_counts()
    check("live auth_limits still 0", auth_end == 0, str(auth_end))
    check("live approval requests still 0", req_end == 0, str(req_end))
    check("live approval decisions still 0", dec_end == 0, str(dec_end))
    check(
        "live audit count did not rise",
        audit_end == audit_before,
        f"{audit_before}->{audit_end}",
    )

    # HTTP API on temp DB
    try:
        import inspect
        import serve_beta as sb
        import wolf_intelligence as wintel

        ra._ENV_LOADED = True
        sb.CATALOG_DB = tmp_db
        wintel.CATALOG_DB = tmp_db
        for attr in (
            "_audit",
            "_identity",
            "_rbac",
            "_authority",
            "_org",
            "_staffing",
            "_scope",
            "_work_items",
            "_approvals",
        ):
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

        def call(method, path, email, body=None):
            data = None if body is None else json.dumps(body).encode()
            req = Request(
                f"http://127.0.0.1:{port}{path}",
                data=data,
                method=method,
                headers={
                    "Content-Type": "application/json",
                    "X-Wolf-Subject": email,
                },
            )
            try:
                with urlopen(req, timeout=10) as resp:
                    return resp.status, json.loads(resp.read().decode())
            except HTTPError as e:
                return e.code, json.loads(e.read().decode())

        st, data = call(
            "POST",
            "/api/core/approvals",
            MATT,
            {
                "title": "HTTP spend",
                "owning_entity_id": "ENT-GGV",
                "department_id": TGT_DEPT,
                "request_type": "SPEND",
                "required_permission_code": CODE_SPEND,
                "material_amount": "250000",
                "currency": "IDR",
                # spoof should be ignored / not used
                "requested_by_person_id": "PERS-HAIKAL",
            },
        )
        check("HTTP POST create 201", st == 201 and data.get("ok"), str(data)[:200])
        http_id = data["approval"]["approval_request_id"]
        check(
            "HTTP ignore client requested_by",
            data["approval"]["requested_by_person_id"] == "PERS-MATT",
        )

        st, data = call("GET", "/api/core/approvals", MATT)
        check("HTTP GET list", st == 200 and data.get("ok") and data.get("count", 0) >= 1)

        st, data = call("GET", f"/api/core/approvals/{http_id}", MATT)
        check("HTTP GET one", st == 200 and data.get("approval", {}).get("approval_request_id") == http_id)

        # Self-approve via HTTP → deny
        st, data = call("POST", f"/api/core/approvals/{http_id}/approve", MATT, {"reason": "self"})
        check("HTTP self-approve denied", st == 403 and data.get("error") == "self_approval_denied")

        st, data = call("POST", f"/api/core/approvals/{http_id}/cancel", MATT, {"reason": "n/a"})
        check("HTTP cancel", st == 200 and data.get("approval", {}).get("status") == "CANCELLED")

        httpd.shutdown()
    except Exception as exc:  # noqa: BLE001
        check("HTTP section", False, str(exc))

    # Final live isolation
    auth_final, audit_final, req_final, dec_final = live_counts()
    check("FINAL live auth_limits=0", auth_final == 0, str(auth_final))
    check("FINAL live approvals=0", req_final == 0 and dec_final == 0)
    check(
        "FINAL live audit unchanged",
        audit_final == audit_before,
        f"{audit_before}->{audit_final}",
    )

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
