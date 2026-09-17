#!/usr/bin/env python3
"""Tests for Wolf Core Dual Approval (Beta). Temp DB only.

Extends Approval Engine. Live org_authority_limits stay 0.
Live approval rows stay 0. Live audit count must not rise.
No dual business policy seed. No Production.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_dual_approval.py"
APR_PY = SCRIPTS / "core" / "approvals.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
TGT_DEPT = "DEPT-GGV-CONTENT"
TZ = timezone.utc


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_dual_approval", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, int, int, int, int]:
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
        dlg = (
            c.execute("SELECT COUNT(*) FROM core_delegations").fetchone()[0]
            if "core_delegations" in tabs
            else 0
        )
        return int(auth), int(audit), int(req), int(dec), int(dlg)
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


def iso_now(delta_days: int = 0, delta_hours: int = 0) -> str:
    dt = datetime.now(TZ) + timedelta(days=delta_days, hours=delta_hours)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def grant_role_perms(conn, role_id: str, perm_ids: tuple[str, ...]) -> None:
    for pid in perm_ids:
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
            """,
            (role_id, pid, TS, TS),
        )


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    os.environ["BETA_APPROVAL_DENY_SELF_APPROVAL"] = "1"

    src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in approvals.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("dual_approval BUILT honesty", '"dual_approval": "BUILT"' in src or "'dual_approval': 'BUILT'" in src)
    check("required_decision_count in create", "required_decision_count" in src)
    check("duplicate_person_approval code", "duplicate_person_approval" in src)
    check("partial audit decision_recorded", "approval.decision_recorded" in src)

    auth_before, audit_before, req_before, dec_before, dlg_before = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live approvals before=0", req_before == 0 and dec_before == 0)
    check("live delegations before=0", dlg_before == 0)

    backups = list(BACKUP_DIR.glob("pre-dual-approval-*.sqlite"))
    check("pre-dual-approval backup exists", len(backups) >= 1, str(BACKUP_DIR))

    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("migration idempotent", mig.main() == 0)

    auth_after, audit_mid, req_live, dec_live, dlg_live = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live delegations=0", dlg_live == 0)
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    live = sqlite3.connect(str(LIVE_DB))
    cols = {r[1] for r in live.execute("PRAGMA table_info(core_approval_requests)")}
    check("required_decision_count column live", "required_decision_count" in cols)
    idx = live.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_core_approval_dec_one_approve_per_person'
        """
    ).fetchone()
    check("unique approve-per-person index", bool(idx))
    mig_row = live.execute(
        "SELECT id FROM schema_migrations WHERE id='015_dual_approval'"
    ).fetchone()
    check("schema_migrations 015_dual_approval", bool(mig_row))
    live.close()

    # Production path refused
    mig.DB = Path("/tmp/Production/fake.sqlite")
    try:
        rc = mig.main()
    except Exception:
        rc = 2
    check("Production path refused", rc != 0, str(rc))

    # --- Temp DB ---
    td = ROOT / "catalog" / "backups" / f"tmp-dual-approval-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    mig.DB = tmp_db
    check("temp migrate exit 0", mig.main() == 0)
    check("temp migrate idempotent", mig.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "UPDATE org_permissions SET status='ACTIVE', updated_at=? WHERE permission_id=?",
        (TS, PERM_SPEND),
    )
    grant_role_perms(conn, "ROLE-MATT", (PERM_SPEND,))
    grant_role_perms(
        conn,
        "ROLE-CONTENT-MGMT",
        (
            "PERM-APPROVAL-READ",
            "PERM-APPROVAL-REQUEST",
            "PERM-APPROVAL-DECIDE",
            "PERM-APPROVAL-CANCEL",
            PERM_SPEND,
        ),
    )
    haikal_role_id = "ROLE-GGV-EDIT"
    grant_role_perms(
        conn,
        haikal_role_id,
        (
            "PERM-APPROVAL-READ",
            "PERM-APPROVAL-REQUEST",
            "PERM-APPROVAL-DECIDE",
            PERM_SPEND,
        ),
    )
    insert_limit(conn, lid="ALIM-TMP-DUAL-MATT", threshold=5_000_000.0)
    insert_limit(
        conn,
        lid="ALIM-TMP-DUAL-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
        threshold=5_000_000.0,
    )
    insert_limit(
        conn,
        lid="ALIM-TMP-DUAL-HAIKAL",
        role_id=haikal_role_id,
        threshold=5_000_000.0,
    )
    conn.commit()
    tmp_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
    check("temp has fixture authority limits", tmp_auth >= 1, str(tmp_auth))
    live_auth_check = sqlite3.connect(str(LIVE_DB)).execute(
        "SELECT COUNT(*) FROM org_authority_limits"
    ).fetchone()[0]
    check("live auth still 0 after temp fixtures", live_auth_check == 0)
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
    import core.approvals as apr
    import core.delegation as dlg

    for mod in (
        audit, identity, rbac, authority, organisation, staffing, scope, ra, wi, apr, dlg
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    audit_live_before_mut = live_counts()[1]

    # --- invalid required_decision_count ---
    bad = False
    try:
        apr.create_approval_request(
            title="bad count",
            owning_entity_id="ENT-GGV",
            required_permission_code=CODE_SPEND,
            verified_person_id="PERS-AMANDA",
            required_decision_count=0,
        )
    except apr.ApprovalError as e:
        bad = e.code == "invalid_required_decision_count"
    check("required_decision_count <1 denied", bad)

    # --- one-approval compat (default 1) ---
    one = apr.create_approval_request(
        title="single compat",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    check("default required_decision_count=1", int(one.get("required_decision_count") or 0) == 1)
    check("create stays PENDING", one["status"] == "PENDING")
    a1 = apr.approve_request(one["approval_request_id"], verified_person_id="PERS-MATT")
    check(
        "one-approval → APPROVED terminal",
        a1["request"]["status"] == "APPROVED" and a1.get("terminal") is True,
        str(a1.get("terminal")),
    )
    check("executed_source False", a1["executed_source"] is False)
    check("work_item_completed False", a1["work_item_completed"] is False)

    # --- two-person dual flow ---
    dual = apr.create_approval_request(
        title="dual spend",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="250000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        required_decision_count=2,
        link_work_item=True,
        review_owner_person_id="PERS-AMANDA",
    )
    rid = dual["approval_request_id"]
    linked = dual.get("linked_work_item_id")
    check("dual create count=2", int(dual["required_decision_count"]) == 2)
    check("dual honesty note mentions 2", "2" in str(dual.get("honesty_note") or ""))
    check("dual starts PENDING", dual["status"] == "PENDING")

    first = apr.approve_request(rid, verified_person_id="PERS-MATT", reason="approval 1")
    check(
        "first approve stays PENDING",
        first["request"]["status"] == "PENDING" and first.get("terminal") is False,
        str(first["request"].get("status")),
    )
    check("valid_approve_count=1 after first", first.get("valid_approve_count") == 1)
    check("approvals_remaining=1", first.get("approvals_remaining") == 1)
    partial_aud = audit.list_events(action="approval.decision_recorded", source="approvals", limit=10)
    check("audit partial decision_recorded", len(partial_aud) >= 1)
    grant_aud_mid = [
        e for e in audit.list_events(action="approval.granted", source="approvals", limit=20)
        if (e.get("resource_id") == rid)
    ]
    check("no terminal granted after partial", len(grant_aud_mid) == 0)

    # same person / alternate AuthIdentity blocked
    dup = False
    try:
        apr.approve_request(
            rid,
            verified_person_id="PERS-MATT",
            identity={"auth_identity_id": "AUTH-MATT-ALT", "identity_assurance": "email"},
        )
    except apr.ApprovalError as e:
        dup = e.code == "duplicate_person_approval"
    check("same Person second APPROVED → duplicate_person_approval", dup)
    check("still PENDING after duplicate", apr.get_approval_request(rid)["status"] == "PENDING")
    check("still one APPROVED decision", apr.valid_approve_count(rid) == 1)

    # requester self-approval on material
    self_denied = False
    try:
        apr.approve_request(rid, verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        self_denied = e.code == "self_approval_denied"
    check("requester self-approval denied", self_denied)

    # second distinct Person → APPROVED
    second = apr.approve_request(rid, verified_person_id="PERS-HAIKAL", reason="approval 2")
    check(
        "second approve → APPROVED",
        second["request"]["status"] == "APPROVED" and second.get("terminal") is True,
        str(second["request"].get("status")),
    )
    check("valid_approve_count=2", second.get("valid_approve_count") == 2)
    decs = apr.list_decisions(rid)
    check("both APPROVED decisions preserved", len(decs) == 2 and all(d["decision"] == "APPROVED" for d in decs))
    persons = {d["decided_by_person_id"] for d in decs}
    check("two distinct Persons", persons == {"PERS-MATT", "PERS-HAIKAL"})
    grant_aud = [
        e for e in audit.list_events(action="approval.granted", source="approvals", limit=20)
        if e.get("resource_id") == rid
    ]
    check("audit approval.granted on terminal", len(grant_aud) >= 1)

    # WI not completed by approval
    if linked:
        wi_row = wi.get_work_item(linked)
        check(
            "WI not completed by dual approval",
            wi_row and wi_row["status"] in ("OPEN", "IN_PROGRESS", "BLOCKED"),
            str(wi_row.get("status") if wi_row else None),
        )
        wi.start_work_item(linked, verified_person_id="PERS-AMANDA")
        wi.claim_complete(linked, verified_person_id="PERS-AMANDA", outcome="done")
        wi.verify_work_item(linked, verified_person_id="PERS-MATT")
        # already APPROVED — completing WI must not change decisions
        check(
            "WI complete ≠ change approval status",
            apr.get_approval_request(rid)["status"] == "APPROVED",
        )

    # --- immutability ---
    imm = False
    try:
        apr.refuse_immutable_mutation({"required_decision_count": 1, "material_amount": "9"})
    except apr.ApprovalError as e:
        imm = e.code == "immutable_fields"
    check("immutable required_decision_count + amount", imm)
    upd_refused = False
    try:
        apr.update_approval_request(rid, required_decision_count=1)
    except apr.ApprovalError as e:
        upd_refused = e.code == "immutable_fields"
    check("no update API for security fields", upd_refused)

    # After first decision on a fresh dual, cannot lower via update (already covered);
    # snapshot includes count
    snap_dual = apr.create_approval_request(
        title="snap dual",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    h1 = snap_dual["snapshot_hash"]
    h2 = apr.compute_snapshot_hash(
        owning_entity_id="ENT-GGV",
        brand_id=None,
        location_id=None,
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        required_permission_id=PERM_SPEND,
        material_amount="100000",
        currency="IDR",
        source_type="HUMAN",
        source_id=None,
        request_type="SPEND",
        required_decision_count=2,
    )
    check("snapshot_hash includes required_decision_count", h1 == h2, f"{h1[:12]} vs {h2[:12]}")
    h_low = apr.compute_snapshot_hash(
        owning_entity_id="ENT-GGV",
        brand_id=None,
        location_id=None,
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        required_permission_id=PERM_SPEND,
        material_amount="100000",
        currency="IDR",
        source_type="HUMAN",
        source_id=None,
        request_type="SPEND",
        required_decision_count=1,
    )
    check("lowering count changes snapshot", h1 != h_low)

    # --- REJECT terminates ---
    rej_req = apr.create_approval_request(
        title="reject dual",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    rr = rej_req["approval_request_id"]
    apr.approve_request(rr, verified_person_id="PERS-MATT")
    check("partial before reject still PENDING", apr.get_approval_request(rr)["status"] == "PENDING")
    rejected = apr.reject_request(rr, verified_person_id="PERS-HAIKAL", reason="no")
    check("REJECT → REJECTED immediately", rejected["request"]["status"] == "REJECTED")
    further = False
    try:
        apr.approve_request(rr, verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        further = e.code in ("not_pending", "already_decided", "duplicate_person_approval")
    check("further decisions denied after REJECT", further)
    check("partial APPROVED row preserved after REJECT", apr.valid_approve_count(rr) == 1)
    check(
        "REJECT decision present",
        any(d["decision"] == "REJECTED" for d in apr.list_decisions(rr)),
    )

    # --- RBAC / scope / permission / assignment denials ---
    deny_req = apr.create_approval_request(
        title="deny gates",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    drid = deny_req["approval_request_id"]
    # Misa lacks approval.decide + spend (unless granted) — expect rbac or required_permission
    misa_denied = False
    try:
        apr.approve_request(drid, verified_person_id="PERS-MISA")
    except apr.ApprovalError as e:
        misa_denied = e.code in ("rbac_denied", "required_permission_denied", "no_active_assignment")
    check("RBAC/permission deny for unscoped Person", misa_denied)

    # inactive assignment
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        "UPDATE org_assignments SET status='INACTIVE' WHERE assignment_id='ASG-HAIKAL-VE-1'"
    )
    c.commit()
    c.close()
    asg_denied = False
    try:
        apr.approve_request(drid, verified_person_id="PERS-HAIKAL")
    except apr.ApprovalError as e:
        asg_denied = e.code in ("no_active_assignment", "inactive_assignment", "rbac_denied")
    check("inactive assignment deny", asg_denied)
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        "UPDATE org_assignments SET status='ACTIVE' WHERE assignment_id='ASG-HAIKAL-VE-1'"
    )
    c.commit()
    c.close()

    # Authority over limit
    over = apr.create_approval_request(
        title="over limit dual",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="9000000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    auth_denied = False
    try:
        apr.approve_request(over["approval_request_id"], verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        auth_denied = e.code == "authority_denied"
    check("authority denied above limit", auth_denied)

    # APR-RT-001 forge NULL amount
    c = sqlite3.connect(str(tmp_db))
    forge_id = "APR-DUAL-FORGE-NULL-AMT"
    forge_ts = "2026-09-17T03:00:00Z"
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
          prior_request_id, snapshot_hash, required_decision_count
        ) VALUES (
          ?, 'SPEND', 'forged null amount dual', NULL,
          'ENT-GGV', NULL, NULL, ?,
          'PERS-AMANDA', 'ASG-AMANDA-CM-1',
          ?, ?,
          NULL, NULL, 'HUMAN', NULL,
          NULL, 'PENDING', ?, NULL, NULL,
          ?, ?, 'CORR-DUAL-FORGE-NULL', NULL,
          NULL, 'dual-forge-null', 2
        )
        """,
        (forge_id, TGT_DEPT, CODE_SPEND, PERM_SPEND, forge_ts, forge_ts, forge_ts),
    )
    c.commit()
    c.close()
    null_amt = False
    try:
        apr.approve_request(forge_id, verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        null_amt = e.code == "missing_amount"
    check("APR-RT-001 missing_amount on forge NULL", null_amt)

    # --- Delegation once / not double-count ---
    # Strip Haikal native spend+decide; grant via Matt delegation only
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        """
        DELETE FROM org_role_permissions
        WHERE role_id=? AND permission_id IN (?, 'PERM-APPROVAL-DECIDE')
        """,
        (haikal_role_id, PERM_SPEND),
    )
    # Ensure Matt has delegation.create
    grant_role_perms(
        c,
        "ROLE-MATT",
        ("PERM-DELEGATION-CREATE", "PERM-DELEGATION-READ", "PERM-DELEGATION-REVOKE"),
    )
    c.commit()
    c.close()

    ef = iso_now(delta_hours=-1)
    et = iso_now(delta_days=7)
    d_spend = dlg.create_delegation(
        verified_person_id="PERS-MATT",
        delegate_person_id="PERS-HAIKAL",
        delegator_assignment_id="ASG-MATT-OWNER-1",
        delegate_assignment_id="ASG-HAIKAL-VE-1",
        entity_id="ENT-GGV",
        scope_id="SCOPE-GGV-CONTENT",
        permission_code=CODE_SPEND,
        effective_from=ef,
        effective_to=et,
        delegated_cap_amount="1000000",
        currency="IDR",
    )
    d_decide = dlg.create_delegation(
        verified_person_id="PERS-MATT",
        delegate_person_id="PERS-HAIKAL",
        delegator_assignment_id="ASG-MATT-OWNER-1",
        delegate_assignment_id="ASG-HAIKAL-VE-1",
        entity_id="ENT-GGV",
        scope_id="SCOPE-GGV-CONTENT",
        permission_code="approval.decide",
        effective_from=ef,
        effective_to=et,
    )
    check("delegation spend ACTIVE", d_spend["status"] == "ACTIVE")
    check("delegation decide ACTIVE", d_decide["status"] == "ACTIVE")

    dlg_req = apr.create_approval_request(
        title="dlg dual",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="200000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    dlg_rid = dlg_req["approval_request_id"]
    # Matt native #1
    apr.approve_request(dlg_rid, verified_person_id="PERS-MATT")
    # Haikal via delegation #2 — counts as Haikal Person only (not Matt+Haikal)
    dlg_ok = apr.approve_request(dlg_rid, verified_person_id="PERS-HAIKAL")
    check(
        "delegation second Person → APPROVED",
        dlg_ok["request"]["status"] == "APPROVED",
        str(dlg_ok["request"].get("status")),
    )
    dlg_decs = apr.list_decisions(dlg_rid)
    check("delegation does not double-count Persons", len(dlg_decs) == 2)
    check(
        "delegate actor stamped",
        any(
            d["decided_by_person_id"] == "PERS-HAIKAL"
            and d.get("authority_basis_type") == "DELEGATION"
            for d in dlg_decs
        ),
    )

    # DLG-RT-001 via delegation
    c = sqlite3.connect(str(tmp_db))
    forge2 = "APR-DUAL-DLG-FORGE-NULL"
    c.execute(
        """
        INSERT INTO core_approval_requests (
          approval_request_id, request_type, title,
          owning_entity_id, department_id,
          requested_by_person_id, requested_by_assignment_id,
          required_permission_code, required_permission_id,
          material_amount, currency, source_type,
          status, requested_at, created_at, updated_at, correlation_id,
          snapshot_hash, required_decision_count
        ) VALUES (
          ?, 'SPEND', 'dlg forge null',
          'ENT-GGV', ?,
          'PERS-AMANDA', 'ASG-AMANDA-CM-1',
          ?, ?,
          NULL, NULL, 'HUMAN',
          'PENDING', ?, ?, ?, 'CORR-DUAL-DLG-NULL',
          'x', 1
        )
        """,
        (forge2, TGT_DEPT, CODE_SPEND, PERM_SPEND, forge_ts, forge_ts, forge_ts),
    )
    c.commit()
    c.close()
    dlg_null = False
    try:
        apr.approve_request(forge2, verified_person_id="PERS-HAIKAL")
    except apr.ApprovalError as e:
        dlg_null = e.code == "missing_amount"
    check("DLG-RT-001 missing_amount via delegation", dlg_null)

    # expired / revoked / re-delegation
    dlg.revoke_delegation(d_spend["delegation_id"], verified_person_id="PERS-MATT")
    revoked_deny = False
    try:
        apr.approve_request(
            apr.create_approval_request(
                title="after revoke",
                owning_entity_id="ENT-GGV",
                department_id=TGT_DEPT,
                required_permission_code=CODE_SPEND,
                request_type="SPEND",
                material_amount="100000",
                currency="IDR",
                verified_person_id="PERS-AMANDA",
            )["approval_request_id"],
            verified_person_id="PERS-HAIKAL",
        )
    except apr.ApprovalError as e:
        revoked_deny = e.code in ("required_permission_denied", "rbac_denied", "authority_denied")
    check("revoked delegation cannot approve", revoked_deny)

    redeleg = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-MATT",
            delegate_person_id="PERS-HAIKAL",
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id="ASG-HAIKAL-VE-1",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            allow_redelegation=1,
        )
    except dlg.DelegationError as e:
        redeleg = e.code == "redelegation_denied"
    check("re-delegation denied", redeleg)

    # after revoke, no valid spend delegation
    expired_eval = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-GGV"},
        {"amount": "100", "currency": "IDR"},
    )
    check(
        "no valid spend delegation after revoke",
        expired_eval.get("allowed") is False,
        str(expired_eval.get("reason")),
    )

    # --- concurrency: same Person ---
    conc = apr.create_approval_request(
        title="conc same",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    crid = conc["approval_request_id"]
    results: list[str] = []
    lock = threading.Lock()

    def _approve_matt():
        try:
            apr.approve_request(crid, verified_person_id="PERS-MATT")
            with lock:
                results.append("ok")
        except apr.ApprovalError as e:
            with lock:
                results.append(e.code)

    t1 = threading.Thread(target=_approve_matt)
    t2 = threading.Thread(target=_approve_matt)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    check(
        "concurrent same Person: one ok + duplicate/pending",
        results.count("ok") == 1
        and (
            "duplicate_person_approval" in results
            or "already_decided" in results
            or "not_pending" in results
        ),
        str(results),
    )
    check("concurrent same Person: one APPROVED row", apr.valid_approve_count(crid) == 1)

    # concurrency: distinct Persons on count=2
    conc2 = apr.create_approval_request(
        title="conc distinct",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        required_decision_count=2,
    )
    c2id = conc2["approval_request_id"]
    # Restore Haikal native for this concurrency (delegation revoked)
    c = sqlite3.connect(str(tmp_db))
    grant_role_perms(
        c,
        haikal_role_id,
        ("PERM-APPROVAL-DECIDE", PERM_SPEND),
    )
    c.commit()
    c.close()

    errs: list[str] = []

    def _apr(person: str):
        try:
            apr.approve_request(c2id, verified_person_id=person)
        except apr.ApprovalError as e:
            with lock:
                errs.append(e.code)

    ta = threading.Thread(target=_apr, args=("PERS-MATT",))
    tb = threading.Thread(target=_apr, args=("PERS-HAIKAL",))
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    st = apr.get_approval_request(c2id)["status"]
    n = apr.valid_approve_count(c2id)
    check(
        "concurrent distinct Persons both rows + APPROVED",
        st == "APPROVED" and n == 2,
        f"status={st} count={n} errs={errs}",
    )

    # replay after terminal
    replay = False
    try:
        apr.approve_request(c2id, verified_person_id="PERS-MATT")
    except apr.ApprovalError as e:
        replay = e.code in ("not_pending", "already_decided", "duplicate_person_approval")
    check("replay after APPROVED denied", replay)

    # --- HTTP: required_decision_count on create only ---
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
            "_delegation",
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
                "title": "HTTP dual",
                "owning_entity_id": "ENT-GGV",
                "department_id": TGT_DEPT,
                "request_type": "SPEND",
                "required_permission_code": CODE_SPEND,
                "material_amount": "150000",
                "currency": "IDR",
                "required_decision_count": 2,
            },
        )
        check("HTTP create dual 201", st == 201 and data.get("ok"), str(data)[:200])
        http_id = data["approval"]["approval_request_id"]
        check(
            "HTTP required_decision_count=2",
            int(data["approval"].get("required_decision_count") or 0) == 2,
        )
        # decide body must ignore required_decision_count if supplied
        st, data = call(
            "POST",
            f"/api/core/approvals/{http_id}/approve",
            "amanda@wolfcommand.net",
            {"reason": "a1", "required_decision_count": 1},
        )
        # Amanda is requester → self deny on material; use Haikal
        st, data = call(
            "POST",
            f"/api/core/approvals/{http_id}/cancel",
            MATT,
            {"reason": "cleanup"},
        )
        # recreate as Amanda then Matt approve
        st, data = call(
            "POST",
            "/api/core/approvals",
            "amanda@wolfcommand.net",
            {
                "title": "HTTP dual2",
                "owning_entity_id": "ENT-GGV",
                "department_id": TGT_DEPT,
                "request_type": "SPEND",
                "required_permission_code": CODE_SPEND,
                "material_amount": "150000",
                "currency": "IDR",
                "required_decision_count": 2,
            },
        )
        check("HTTP Amanda create dual", st == 201, str(data)[:200])
        http_id2 = data["approval"]["approval_request_id"]
        st, data = call(
            "POST",
            f"/api/core/approvals/{http_id2}/approve",
            MATT,
            {"reason": "partial", "required_decision_count": 99},
        )
        check(
            "HTTP approve ignores required_decision_count on decide",
            st == 200
            and data.get("request", {}).get("status") == "PENDING"
            and data.get("valid_approve_count") == 1,
            str(data)[:240],
        )
        httpd.shutdown()
    except Exception as exc:  # noqa: BLE001
        check("HTTP section", False, str(exc))

    # live isolation
    auth_end, audit_end, req_end, dec_end, dlg_end = live_counts()
    check("FINAL live auth_limits=0", auth_end == 0, str(auth_end))
    check("FINAL live approvals=0", req_end == 0 and dec_end == 0)
    check(
        "FINAL live audit unchanged",
        audit_end == audit_before == audit_live_before_mut,
        f"{audit_before}->{audit_end}",
    )
    # live delegations may still be 0 (temp-only creates)
    check("FINAL live delegations=0", dlg_end == 0, str(dlg_end))

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
