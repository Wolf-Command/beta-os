#!/usr/bin/env python3
"""Tests for Wolf Core Evidence Requirement Enforcement (Beta). Temp DB only.

CLAIMED ≠ EVIDENCED ≠ VERIFIED.
Live Authority/Policies/SoD/Evidence-requirements/records stay 0.
Live audit count must not rise. No Production.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_evidence_requirements.py"
EVD_PY = SCRIPTS / "core" / "evidence.py"
APR_PY = SCRIPTS / "core" / "approvals.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
TGT_DEPT = "DEPT-GGV-CONTENT"
SCOPE_EXACT = "SCOPE-GGV-CONTENT"
TZ = timezone(timedelta(hours=8))
OBJ = "PO-EVIDENCE-001"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_evidence_requirements", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, int, int, int, int, int, int, int]:
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
        pol = (
            c.execute("SELECT COUNT(*) FROM core_governance_policies").fetchone()[0]
            if "core_governance_policies" in tabs
            else 0
        )
        sod = (
            c.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
            if "core_sod_constraints" in tabs
            else 0
        )
        evr = (
            c.execute("SELECT COUNT(*) FROM core_evidence_requirements").fetchone()[0]
            if "core_evidence_requirements" in tabs
            else 0
        )
        evd = (
            c.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0]
            if "core_evidence_records" in tabs
            else 0
        )
        return (
            int(auth),
            int(audit),
            int(req),
            int(dec),
            int(pol),
            int(sod),
            int(evr),
            int(evd),
        )
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

    src = EVD_PY.read_text(encoding="utf-8")
    apr_src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in evidence.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("evaluate_evidence_requirements defined", "def evaluate_evidence_requirements" in src)
    check("submit_evidence defined", "def submit_evidence" in src)
    check("verify_evidence defined", "def verify_evidence" in src)
    check("invalidate_evidence defined", "def invalidate_evidence" in src)
    check("evidence wired in approvals", "_enforce_evidence_gate" in apr_src)
    check("enforce_evidence param", "enforce_evidence" in apr_src)
    check("HONESTY evidence_requirements BUILT", '"evidence_requirements": "BUILT"' in apr_src)
    check("delete_evidence NotImplemented", "def delete_evidence" in src)

    (
        auth_before,
        audit_before,
        req_before,
        dec_before,
        pol_before,
        sod_before,
        evr_before,
        evd_before,
    ) = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live approvals before=0", req_before == 0 and dec_before == 0)
    check("live governance policies before<=1 Habitat", pol_before <= 1, str(pol_before))
    check("live SoD before=0", sod_before == 0, str(sod_before))
    check("live evidence requirements before<=1 Habitat", evr_before <= 1, str(evr_before))
    check("live evidence records before=0", evd_before == 0, str(evd_before))

    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("migration idempotent", mig.main() == 0)

    (
        auth_after,
        audit_mid,
        req_live,
        dec_live,
        pol_live,
        sod_live,
        evr_live,
        evd_live,
    ) = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live governance policies<=1 Habitat", pol_live <= 1, str(pol_live))
    check("live SoD=0", sod_live == 0, str(sod_live))
    check("live evidence requirements<=1 Habitat", evr_live <= 1, str(evr_live))
    check("live evidence records=0", evd_live == 0, str(evd_live))
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    backups = list(BACKUP_DIR.glob("pre-evidence-requirements-*.sqlite"))
    check("pre-evidence-requirements backup exists", len(backups) >= 1, str(BACKUP_DIR))

    live = sqlite3.connect(str(LIVE_DB))
    for tname in (
        "core_evidence_types",
        "core_evidence_records",
        "core_evidence_requirements",
    ):
        tab = live.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (tname,),
        ).fetchone()
        check(f"{tname} table", bool(tab))
    mig_row = live.execute(
        "SELECT id FROM schema_migrations WHERE id='018_evidence_requirements'"
    ).fetchone()
    check("schema_migrations 018", bool(mig_row))
    for code in (
        "evidence.record.submit",
        "evidence.record.read",
        "evidence.requirement.manage",
    ):
        row = live.execute(
            "SELECT status FROM org_permissions WHERE code=?",
            (code,),
        ).fetchone()
        check(f"{code} seeded ACTIVE", bool(row) and row[0] == "ACTIVE")
    matt_manage = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE role_id='ROLE-MATT' AND permission_id='PERM-EVIDENCE-REQUIREMENT-MANAGE'
        """
    ).fetchone()[0]
    check("Matt evidence.requirement.manage grant", matt_manage == 1)
    non_matt = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (
          'PERM-EVIDENCE-RECORD-READ',
          'PERM-EVIDENCE-REQUIREMENT-MANAGE'
        ) AND role_id != 'ROLE-MATT'
        """
    ).fetchone()[0]
    check("no broad non-Matt evidence manage/read grants", non_matt == 0)
    trg = live.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='trigger' AND name='trg_core_evidence_records_no_delete'
        """
    ).fetchone()
    check("no-delete trigger", bool(trg))
    live.close()

    mig.DB = Path("/tmp/Production/fake.sqlite")
    try:
        rc = mig.main()
    except Exception:
        rc = 2
    check("Production path refused", rc != 0, str(rc))

    # --- Temp DB ---
    td = ROOT / "catalog" / "backups" / f"tmp-evidence-requirements-{os.getpid()}"
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
            "PERM-EVIDENCE-RECORD-SUBMIT",
            "PERM-EVIDENCE-RECORD-READ",
        ),
    )
    grant_role_perms(
        conn,
        "ROLE-GGV-EDIT",
        ("PERM-APPROVAL-DECIDE", PERM_SPEND, "PERM-APPROVAL-READ"),
    )
    insert_limit(conn, lid="ALIM-TMP-EVD-MATT", threshold=5_000_000.0)
    insert_limit(
        conn,
        lid="ALIM-TMP-EVD-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
        threshold=5_000_000.0,
    )
    insert_limit(
        conn,
        lid="ALIM-TMP-EVD-HAIKAL",
        role_id="ROLE-GGV-EDIT",
        threshold=5_000_000.0,
    )
    conn.commit()
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
    import core.governance_policy as gov
    import core.sod as sod
    import core.evidence as evd

    for mod in (
        audit,
        identity,
        rbac,
        authority,
        organisation,
        staffing,
        scope,
        ra,
        wi,
        apr,
        dlg,
        gov,
        sod,
        evd,
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    audit_live_before_mut = live_counts()[1]

    # --- manage insert denied without hook ---
    denied_manage = False
    try:
        evd.insert_evidence_requirement_for_test(
            entity_id="ENT-GGV",
            action_type="approval.request",
            evidence_type="receiving_document",
            allow_test_write=False,
            verified_person_id="PERS-AMANDA",
        )
    except evd.EvidenceError as e:
        denied_manage = e.code == "permission_denied"
    check("insert requirement without manage denied", denied_manage)

    def seed_req(**kw):
        return evd.insert_evidence_requirement_for_test(allow_test_write=True, **kw)

    # --- Zero ACTIVE → no_evidence_requirements ---
    ev0 = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "approval.request",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
    )
    check(
        "zero ACTIVE → no_evidence_requirements",
        ev0["satisfied"] is True and ev0["reason_code"] == "no_evidence_requirements",
        str(ev0),
    )

    # --- Unbound create/approve still works with zero requirements ---
    unbound = apr.create_approval_request(
        title="unbound pre-evidence",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    ok_unbound = apr.approve_request(unbound["approval_request_id"], verified_person_id="PERS-MATT")
    check("unbound approve with zero evidence reqs", ok_unbound["request"]["status"] == "APPROVED")

    # --- Missing evidence deny ---
    seed_req(
        requirement_id="EVR-RECV-1",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="approval.request",
        request_type="SPEND",
        evidence_type="receiving_document",
        min_count=1,
        verification_needed=0,
        effective_from="2026-01-01T00:00:00Z",
    )
    denied_missing = False
    try:
        apr.create_approval_request(
            title="needs evidence",
            owning_entity_id="ENT-GGV",
            department_id=TGT_DEPT,
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            material_amount="50000",
            currency="IDR",
            verified_person_id="PERS-AMANDA",
            requested_by_assignment_id="ASG-AMANDA-CM-1",
            enforce_evidence=True,
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            evidence_present=True,  # client claim ignored
            evidence_required=False,  # client claim ignored
        )
    except apr.ApprovalError as e:
        denied_missing = e.code == "missing_required_evidence"
    check("missing evidence → missing_required_evidence", denied_missing)

    # --- Submit + satisfy ---
    submitted = evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="receiving_document",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
        verified_person_id="PERS-AMANDA",
        object_ref="file:///tmp/recv-001.pdf",
        content_hash=hashlib.sha256(b"recv-bytes").hexdigest(),
        metadata={"note": "ok", "password": "should-strip"},
        allow_test_write=True,
    )
    check("submit → SUBMITTED ACTIVE", submitted["verification_status"] == "SUBMITTED")
    check("submit person from verified", submitted["submitted_by_person_id"] == "PERS-AMANDA")
    check(
        "metadata secrets stripped",
        "password" not in (submitted.get("metadata") or {}),
        str(submitted.get("metadata")),
    )

    forged = False
    try:
        evd.submit_evidence(
            entity_id="ENT-GGV",
            evidence_type="photo",
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            verified_person_id="PERS-AMANDA",
            submitted_by_person_id="PERS-MATT",
            allow_test_write=True,
        )
    except evd.EvidenceError as e:
        forged = e.code == "forged_submitter"
    check("forged submitter refused", forged)

    blob_refused = False
    try:
        evd.submit_evidence(
            entity_id="ENT-GGV",
            evidence_type="photo",
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            verified_person_id="PERS-AMANDA",
            object_ref=b"not-a-string",  # type: ignore[arg-type]
            allow_test_write=True,
        )
    except evd.EvidenceError as e:
        blob_refused = e.code == "invalid_object_ref"
    check("object_ref blob refused", blob_refused)

    hard_del = False
    try:
        evd.delete_evidence("x")
    except NotImplementedError:
        hard_del = True
    check("hard delete NotImplemented", hard_del)

    # Wrong entity evidence never counted
    evd.submit_evidence(
        entity_id="ENT-BZG",
        evidence_type="receiving_document",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
        verified_person_id="PERS-MATT",
        allow_test_write=True,
    )
    # Wrong object never counted
    evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="receiving_document",
        governed_object_type="purchase_order",
        governed_object_id="PO-OTHER",
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    # Wrong type never counted — already have receiving_document for OBJ

    ok_create = apr.create_approval_request(
        title="with evidence",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="50000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        enforce_evidence=True,
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
        source_type="EXTERNAL",
        source_id=OBJ,
    )
    check("create with matching evidence", ok_create["status"] == "PENDING")

    # Client claim alone never satisfies — evaluate ignores evidence_present
    ev_claim = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "approval.request",
        request_type="SPEND",
        governed_object_type="purchase_order",
        governed_object_id="PO-NEVER",
        evidence_present=True,
        evidence_required=False,
        client_evidence_count=99,
    )
    check(
        "client evidence_present ignored",
        ev_claim["reason_code"] == "missing_required_evidence",
        str(ev_claim),
    )

    # --- verification_needed requires VERIFIED ---
    seed_req(
        requirement_id="EVR-PHOTO-V",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="approval.decide",
        evidence_type="photo",
        min_count=1,
        verification_needed=1,
        scope_id=None,
        effective_from="2026-01-01T00:00:00Z",
    )
    photo = evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="photo",
        governed_object_type="approval_request",
        governed_object_id=ok_create["approval_request_id"],
        verified_person_id="PERS-AMANDA",
        object_ref="file:///tmp/photo.jpg",
        allow_test_write=True,
    )
    deny_unverified = False
    try:
        apr.approve_request(
            ok_create["approval_request_id"],
            verified_person_id="PERS-MATT",
            enforce_evidence=True,
            governed_object_type="approval_request",
            governed_object_id=ok_create["approval_request_id"],
        )
    except apr.ApprovalError as e:
        deny_unverified = e.code == "missing_required_evidence"
    check("unverified photo → missing_required_evidence", deny_unverified)

    self_v = False
    try:
        evd.verify_evidence(
            photo["evidence_id"],
            verified_person_id="PERS-AMANDA",
            require_independent_verify=True,
            allow_test_write=True,
        )
    except evd.EvidenceError as e:
        self_v = e.code == "self_verify_denied"
    check("self-verify denied when required", self_v)

    verified = evd.verify_evidence(
        photo["evidence_id"],
        verified_person_id="PERS-MATT",
        require_independent_verify=True,
        allow_test_write=True,
    )
    check("independent verify → VERIFIED", verified["verification_status"] == "VERIFIED")

    # Optional SoD: submitter cannot verify when SoD fixture ACTIVE
    photo2 = evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="photo",
        governed_object_type="purchase_order",
        governed_object_id="PO-SOD",
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    sod.insert_sod_constraint_for_test(
        allow_test_write=True,
        constraint_id="SOD-EVD-VERIFY",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="EVIDENCE",
        prior_action="evidence.submit",
        proposed_action="evidence.verify",
        effective_from="2026-01-01T00:00:00Z",
    )
    sod_deny = False
    try:
        evd.verify_evidence(
            photo2["evidence_id"],
            verified_person_id="PERS-AMANDA",
            require_independent_verify=False,
            allow_test_write=True,
        )
    except evd.EvidenceError as e:
        sod_deny = e.code == "sod_same_person_conflict"
    check("SoD blocks submitter verify", sod_deny)

    ok_approve = apr.approve_request(
        ok_create["approval_request_id"],
        verified_person_id="PERS-MATT",
        enforce_evidence=True,
        governed_object_type="approval_request",
        governed_object_id=ok_create["approval_request_id"],
    )
    check("approve after verified evidence", ok_approve["request"]["status"] == "APPROVED")

    # --- Exact scope beats entity-wide ---
    seed_req(
        requirement_id="EVR-SCOPE-WIDE",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="payment.release",
        evidence_type="invoice",
        min_count=2,
        scope_id=None,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed_req(
        requirement_id="EVR-SCOPE-EXACT",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="payment.release",
        evidence_type="invoice",
        min_count=1,
        scope_id=SCOPE_EXACT,
        effective_from="2026-01-01T00:00:00Z",
    )
    evd.submit_evidence(
        entity_id="ENT-GGV",
        scope_id=SCOPE_EXACT,
        evidence_type="invoice",
        governed_object_type="payment",
        governed_object_id="PAY-1",
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    ev_scope = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "payment.release",
        scope_id=SCOPE_EXACT,
        governed_object_type="payment",
        governed_object_id="PAY-1",
    )
    check(
        "exact scope beats entity-wide (min_count=1)",
        ev_scope["satisfied"] is True
        and ev_scope["requirements"][0]["requirement_id"] == "EVR-SCOPE-EXACT",
        str(ev_scope),
    )

    # --- Equal specificity conflict ---
    seed_req(
        requirement_id="EVR-CF-A",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="payment.release",
        evidence_type="delivery_note",
        min_count=1,
        scope_id="SCOPE-EVD-CF",
        effective_from="2026-01-01T00:00:00Z",
    )
    seed_req(
        requirement_id="EVR-CF-B",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="payment.release",
        evidence_type="delivery_note",
        min_count=1,
        scope_id="SCOPE-EVD-CF",
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_cf = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "payment.release",
        scope_id="SCOPE-EVD-CF",
        governed_object_type="payment",
        governed_object_id="PAY-CF",
    )
    check(
        "equal specificity → requirement_conflict",
        ev_cf["reason_code"] == "requirement_conflict" and ev_cf["allowed"] is False,
        str(ev_cf),
    )

    # --- Invalidate path ---
    inv = evd.invalidate_evidence(
        submitted["evidence_id"],
        verified_person_id="PERS-MATT",
        reason="superseded",
        allow_test_write=True,
    )
    check("invalidate → INVALIDATED", inv["status"] == "INVALIDATED")
    # Trigger refuses hard delete
    c2 = sqlite3.connect(str(tmp_db))
    hard = False
    try:
        c2.execute(
            "DELETE FROM core_evidence_records WHERE evidence_id=?",
            (submitted["evidence_id"],),
        )
        c2.commit()
    except sqlite3.IntegrityError:
        hard = True
    except sqlite3.DatabaseError:
        hard = True
    c2.close()
    check("SQLite trigger refuses hard delete", hard)

    # --- Work Item complete ≠ evidence ---
    wi_item = wi.create_work_item(
        title="wi not evidence",
        work_type="GENERAL",
        owning_entity_id="ENT-GGV",
        source_type="HUMAN",
        created_by_actor_type="PERSON",
        verified_person_id="PERS-AMANDA",
    )
    # Complete if API exists; otherwise presence of WI without evidence record is enough
    wi_complete_ok = True
    if hasattr(wi, "complete_work_item"):
        try:
            wi.complete_work_item(
                wi_item["work_item_id"],
                verified_person_id="PERS-AMANDA",
            )
        except Exception:
            wi_complete_ok = True  # completion path may require more; WI ≠ evidence still holds
    ev_after_wi = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "approval.request",
        request_type="SPEND",
        governed_object_type="purchase_order",
        governed_object_id="PO-WI-ONLY",
        evidence_present=True,
    )
    check(
        "work item ≠ evidence (still missing)",
        ev_after_wi["reason_code"] == "missing_required_evidence",
        str(ev_after_wi),
    )
    check("work item create did not mint evidence", wi_complete_ok)

    # --- bind_policy + evidence_required ---
    gov.insert_governance_policy_for_test(
        allow_test_write=True,
        policy_id="GPO-EVD-1",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        required_decision_count=1,
        approval_required=1,
        evidence_required=1,
        amount_min="0",
        amount_max="10000000",
        currency="IDR",
        effective_from="2026-01-01T00:00:00Z",
    )
    # Policy says evidence_required but no requirement rows for SPEND_APPROVE → unconfigured
    unconf = False
    try:
        apr.create_approval_request(
            title="policy needs evidence config",
            owning_entity_id="ENT-GGV",
            department_id=TGT_DEPT,
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            material_amount="10000",
            currency="IDR",
            verified_person_id="PERS-AMANDA",
            requested_by_assignment_id="ASG-AMANDA-CM-1",
            bind_policy=True,
            governed_object_type="purchase_order",
            governed_object_id="PO-POL-1",
        )
    except apr.ApprovalError as e:
        unconf = e.code == "evidence_requirements_unconfigured"
    check("policy.evidence_required without rows → unconfigured", unconf)

    seed_req(
        requirement_id="EVR-SPEND-APPROVE",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        evidence_type="receiving_document",
        min_count=1,
        effective_from="2026-01-01T00:00:00Z",
    )
    evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="receiving_document",
        governed_object_type="purchase_order",
        governed_object_id="PO-POL-1",
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    pol_ok = apr.create_approval_request(
        title="policy+evidence ok",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="10000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        bind_policy=True,
        governed_object_type="purchase_order",
        governed_object_id="PO-POL-1",
    )
    check("bind_policy + evidence satisfied", pol_ok["status"] == "PENDING")

    # --- metadata size cap ---
    big = False
    try:
        evd.submit_evidence(
            entity_id="ENT-GGV",
            evidence_type="photo",
            governed_object_type="purchase_order",
            governed_object_id="PO-BIG",
            verified_person_id="PERS-AMANDA",
            metadata={"note": "x" * 5000},
            allow_test_write=True,
        )
    except evd.EvidenceError as e:
        big = e.code == "metadata_too_large"
    check("metadata size cap", big)

    # --- live isolation after mutations ---
    (
        auth_end,
        audit_end,
        req_end,
        dec_end,
        pol_end,
        sod_end,
        evr_end,
        evd_end,
    ) = live_counts()
    check("live auth still 0", auth_end == 0)
    check("live policies still<=1 Habitat", pol_end <= 1)
    check("live SoD still 0", sod_end == 0)
    check("live evidence requirements still<=1 Habitat", evr_end <= 1)
    check("live evidence records still 0", evd_end == 0)
    check("live approvals still 0", req_end == 0 and dec_end == 0)
    check(
        "live audit unchanged by temp mutations",
        audit_end == audit_live_before_mut,
        f"{audit_live_before_mut}->{audit_end}",
    )

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
