#!/usr/bin/env python3
"""Tests for Wolf Core Exception / Override Governance (Beta). Temp DB only.

EXCEPTION ≠ COMPLIANCE. Live exceptions/policies/SoD/evidence-reqs/authority = 0.
Live audit count must not rise from mutations. No Production.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_exception_override.py"
EXC_PY = SCRIPTS / "core" / "exceptions.py"
APR_PY = SCRIPTS / "core" / "approvals.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
TGT_DEPT = "DEPT-GGV-CONTENT"
OBJ = "PO-EXC-001"
REASON_OK = "material delivery delay documented by ops"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_exception_override", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, ...]:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def cnt(table: str) -> int:
            if table not in tabs:
                return 0
            return int(c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

        return (
            cnt("org_authority_limits"),
            cnt("core_audit_events"),
            cnt("core_approval_requests"),
            cnt("core_approval_decisions"),
            cnt("core_governance_policies"),
            cnt("core_sod_constraints"),
            cnt("core_evidence_requirements"),
            cnt("core_evidence_records"),
            cnt("core_governance_exceptions"),
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

    src = EXC_PY.read_text(encoding="utf-8")
    apr_src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in exceptions.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("request_exception defined", "def request_exception" in src)
    check("authorise_exception defined", "def authorise_exception" in src)
    check("reject_exception defined", "def reject_exception" in src)
    check("revoke_exception defined", "def revoke_exception" in src)
    check("evaluate_exception_for_control defined", "def evaluate_exception_for_control" in src)
    check("consume_exception defined", "def consume_exception" in src)
    check("PERS_MATT gate", 'PERS_MATT = "PERS-MATT"' in src)
    check("exception wired in approvals evidence gate", "try_allow_under_exception" in apr_src)
    check("ALLOWED_UNDER_EXCEPTION in approvals", "ALLOWED_UNDER_EXCEPTION" in apr_src)
    check("HONESTY exception_override BUILT", '"exception_override": "BUILT"' in apr_src)

    (
        auth_before,
        audit_before,
        req_before,
        dec_before,
        pol_before,
        sod_before,
        evr_before,
        evd_before,
        exc_before,
    ) = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live approvals before=0", req_before == 0 and dec_before == 0)
    check("live governance policies before<=1 Habitat", pol_before <= 1, str(pol_before))
    check("live SoD before=0", sod_before == 0, str(sod_before))
    check("live evidence requirements before<=1 Habitat", evr_before <= 1, str(evr_before))
    check("live evidence records before=0", evd_before == 0, str(evd_before))
    check("live exceptions before=0", exc_before == 0, str(exc_before))

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
        exc_live,
    ) = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live governance policies<=1 Habitat", pol_live <= 1, str(pol_live))
    check("live SoD=0", sod_live == 0, str(sod_live))
    check("live evidence requirements<=1 Habitat", evr_live <= 1, str(evr_live))
    check("live evidence records=0", evd_live == 0, str(evd_live))
    check("live exceptions=0", exc_live == 0, str(exc_live))
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    backups = list(BACKUP_DIR.glob("pre-exception-override-*.sqlite"))
    check("pre-exception-override backup exists", len(backups) >= 1, str(BACKUP_DIR))

    live = sqlite3.connect(str(LIVE_DB))
    for tname in ("core_exceptionable_controls", "core_governance_exceptions"):
        tab = live.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (tname,),
        ).fetchone()
        check(f"{tname} table", bool(tab))
    mig_row = live.execute(
        "SELECT id FROM schema_migrations WHERE id='019_exception_override'"
    ).fetchone()
    check("schema_migrations 019", bool(mig_row))
    for code in (
        "governance.exception.request",
        "governance.exception.authorise",
        "governance.exception.revoke",
        "governance.exception.read",
    ):
        row = live.execute(
            "SELECT status FROM org_permissions WHERE code=?",
            (code,),
        ).fetchone()
        check(f"{code} seeded ACTIVE", bool(row) and row[0] == "ACTIVE")
    matt_auth = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE role_id='ROLE-MATT' AND permission_id='PERM-GOV-EXCEPTION-AUTHORISE'
        """
    ).fetchone()[0]
    matt_rev = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE role_id='ROLE-MATT' AND permission_id='PERM-GOV-EXCEPTION-REVOKE'
        """
    ).fetchone()[0]
    check("Matt authorise grant", matt_auth == 1)
    check("Matt revoke grant", matt_rev == 1)
    non_matt = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id LIKE 'PERM-GOV-EXCEPTION-%' AND role_id != 'ROLE-MATT'
        """
    ).fetchone()[0]
    check("no broad non-Matt exception grants", non_matt == 0)
    trg = live.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='trigger' AND name='trg_core_governance_exceptions_no_delete'
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
    td = ROOT / "catalog" / "backups" / f"tmp-exception-override-{os.getpid()}"
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
            "PERM-GOV-EXCEPTION-REQUEST",
            "PERM-GOV-EXCEPTION-READ",
        ),
    )
    grant_role_perms(
        conn,
        "ROLE-GGV-EDIT",
        ("PERM-APPROVAL-DECIDE", PERM_SPEND, "PERM-APPROVAL-READ"),
    )
    insert_limit(conn, lid="ALIM-TMP-EXC-MATT", threshold=5_000_000.0)
    insert_limit(
        conn,
        lid="ALIM-TMP-EXC-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
        threshold=5_000_000.0,
    )
    insert_limit(
        conn,
        lid="ALIM-TMP-EXC-HAIKAL",
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
    import core.exceptions as gex

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
        gex,
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    audit_live_before_mut = live_counts()[1]

    # --- manage insert denied without hook ---
    denied_manage = False
    try:
        gex.insert_exceptionable_control_for_test(
            control_type="EVIDENCE_REQUIREMENT",
            control_reference="EVR-X",
            allow_test_write=False,
        )
    except gex.ExceptionError as e:
        denied_manage = e.code == "manage_denied"
    check("insert exceptionable without hook denied", denied_manage)

    def seed_ctl(**kw):
        return gex.insert_exceptionable_control_for_test(allow_test_write=True, **kw)

    # --- Reason validation ---
    seed_ctl(control_type="EVIDENCE_REQUIREMENT", control_reference="EVR-REASON")
    bad_reason = False
    try:
        gex.request_exception(
            entity_id="ENT-GGV",
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            control_type="EVIDENCE_REQUIREMENT",
            control_reference="EVR-REASON",
            reason="because",
            verified_person_id="PERS-AMANDA",
            allow_test_write=True,
        )
    except gex.ExceptionError as e:
        bad_reason = e.code == "invalid_reason"
    check("placeholder reason rejected", bad_reason)

    short_reason = False
    try:
        gex.request_exception(
            entity_id="ENT-GGV",
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            control_type="EVIDENCE_REQUIREMENT",
            control_reference="EVR-REASON",
            reason="too short",
            verified_person_id="PERS-AMANDA",
            allow_test_write=True,
        )
    except gex.ExceptionError as e:
        short_reason = e.code == "invalid_reason"
    check("short reason rejected", short_reason)

    # --- NON_EXCEPTIONABLE hard ---
    non_exc = False
    try:
        gex.request_exception(
            entity_id="ENT-GGV",
            governed_object_type="auth",
            governed_object_id="x",
            control_type="AUTHENTICATION",
            control_reference="login",
            reason=REASON_OK,
            verified_person_id="PERS-AMANDA",
            allow_test_write=True,
        )
    except gex.ExceptionError as e:
        non_exc = e.code == "non_exceptionable"
    check("AUTHENTICATION non-exceptionable", non_exc)

    entity_iso = False
    try:
        gex.request_exception(
            entity_id="ENT-GGV",
            governed_object_type="entity",
            governed_object_id="ENT-BZG",
            control_type="ENTITY_ISOLATION",
            control_reference="cross-tenant",
            reason=REASON_OK,
            verified_person_id="PERS-AMANDA",
            allow_test_write=True,
        )
    except gex.ExceptionError as e:
        entity_iso = e.code == "non_exceptionable"
    check("ENTITY_ISOLATION non-exceptionable", entity_iso)

    # --- Request does not bypass; registry required ---
    no_reg = False
    try:
        gex.request_exception(
            entity_id="ENT-GGV",
            governed_object_type="purchase_order",
            governed_object_id=OBJ,
            control_type="EVIDENCE_REQUIREMENT",
            control_reference="EVR-MISSING-REG",
            reason=REASON_OK,
            verified_person_id="PERS-AMANDA",
            allow_test_write=True,
        )
    except gex.ExceptionError as e:
        no_reg = e.code == "not_exceptionable"
    check("missing registry → not_exceptionable", no_reg)

    seed_ctl(
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        exceptionable=1,
    )
    req1 = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
        force=True,
        override=True,
        skip_control=True,
        client_exception_id="FORGED",
    )
    check("request → REQUESTED", req1["status"] == "REQUESTED")
    check("request does not authorise", req1["authorised_by_person_id"] is None)

    # Client flags ignored on evaluate
    ev_flags = gex.evaluate_exception_for_control(
        entity_id="ENT-GGV",
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
        force=True,
        override=True,
        client_exception_authorised=True,
    )
    check(
        "REQUESTED not usable + client flags ignored",
        ev_flags["allowed"] is False and ev_flags["reason_code"] == "no_authorised_exception",
        str(ev_flags),
    )

    # --- Non-Matt cannot authorise ---
    non_matt_auth = False
    try:
        gex.authorise_exception(req1["exception_id"], verified_person_id="PERS-AMANDA")
    except gex.ExceptionError as e:
        non_matt_auth = e.code == "matt_gate_denied"
    check("non-Matt authorise denied", non_matt_auth)

    # --- Delegation ignored for authorise (Amanda acting with Matt delegation claims) ---
    dlg_ignored = False
    try:
        gex.authorise_exception(
            req1["exception_id"],
            verified_person_id="PERS-AMANDA",
            acting_as_matt=True,
            delegation_id="DLG-FAKE",
            delegated_from="PERS-MATT",
        )
    except gex.ExceptionError as e:
        dlg_ignored = e.code == "matt_gate_denied"
    check("delegation claims ignored for authorise", dlg_ignored)

    # --- Matt authorises ---
    auth1 = gex.authorise_exception(req1["exception_id"], verified_person_id="PERS-MATT")
    check("Matt authorise → AUTHORISED", auth1["status"] == "AUTHORISED")
    check("authorised_by PERS-MATT", auth1["authorised_by_person_id"] == "PERS-MATT")

    ev_ok = gex.evaluate_exception_for_control(
        entity_id="ENT-GGV",
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        governed_object_type="purchase_order",
        governed_object_id=OBJ,
    )
    check("evaluate finds AUTHORISED", ev_ok["allowed"] is True, str(ev_ok))

    # Wrong object never matches
    ev_wrong = gex.evaluate_exception_for_control(
        entity_id="ENT-GGV",
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        governed_object_type="purchase_order",
        governed_object_id="PO-OTHER",
    )
    check("wrong object no match", ev_wrong["allowed"] is False)

    # --- required_for_authorise evidence ---
    seed_ctl(
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-NEED-EVD",
        exceptionable=1,
        required_for_authorise=1,
    )
    req_ev = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="purchase_order",
        governed_object_id="PO-NEED-EVD",
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-NEED-EVD",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    need_evd = False
    try:
        gex.authorise_exception(req_ev["exception_id"], verified_person_id="PERS-MATT")
    except gex.ExceptionError as e:
        need_evd = e.code == "evidence_required_for_authorise"
    check("required_for_authorise without evidence denied", need_evd)

    ev_rec = evd.submit_evidence(
        entity_id="ENT-GGV",
        evidence_type="photo",
        governed_object_type="purchase_order",
        governed_object_id="PO-NEED-EVD",
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    auth_ev = gex.authorise_exception(
        req_ev["exception_id"],
        verified_person_id="PERS-MATT",
        evidence_id=ev_rec["evidence_id"],
    )
    check("authorise with ACTIVE evidence", auth_ev["status"] == "AUTHORISED")

    # --- Atomic consume ---
    consumed = gex.consume_exception(auth1["exception_id"], verified_person_id="PERS-MATT")
    check("consume → CONSUMED (limit 1)", consumed["status"] == "CONSUMED")
    check("used_count=1", int(consumed["used_count"]) == 1)
    double = False
    try:
        gex.consume_exception(auth1["exception_id"], verified_person_id="PERS-MATT")
    except gex.ExceptionError as e:
        double = e.code == "consume_failed"
    check("second consume fails", double)

    # --- Revoke ---
    seed_ctl(control_type="SOD_CONSTRAINT", control_reference="SOD-REV-1")
    req_rev = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="approval_request",
        governed_object_id="APR-REV-1",
        control_type="SOD_CONSTRAINT",
        control_reference="SOD-REV-1",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    gex.authorise_exception(req_rev["exception_id"], verified_person_id="PERS-MATT")
    non_matt_rev = False
    try:
        gex.revoke_exception(
            req_rev["exception_id"],
            verified_person_id="PERS-AMANDA",
            reason="trying to revoke without matt gate here",
        )
    except gex.ExceptionError as e:
        non_matt_rev = e.code == "matt_gate_denied"
    check("non-Matt revoke denied", non_matt_rev)
    rev = gex.revoke_exception(
        req_rev["exception_id"],
        verified_person_id="PERS-MATT",
        reason="operational window closed by governance",
    )
    check("Matt revoke → REVOKED", rev["status"] == "REVOKED")

    # --- Reject ---
    req_rej = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="approval_request",
        governed_object_id="APR-REJ-1",
        control_type="SOD_CONSTRAINT",
        control_reference="SOD-REV-1",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    rej = gex.reject_exception(req_rej["exception_id"], verified_person_id="PERS-MATT")
    check("Matt reject → REJECTED", rej["status"] == "REJECTED")

    # --- Evidence gate under exception ---
    evd.insert_evidence_requirement_for_test(
        allow_test_write=True,
        requirement_id="EVR-RECV-EXC",
        requirement_version=1,
        entity_id="ENT-GGV",
        action_type="approval.request",
        request_type="SPEND",
        evidence_type="receiving_document",
        min_count=1,
        verification_needed=0,
        effective_from="2026-01-01T00:00:00Z",
    )
    # Deny without exception
    denied_ev = False
    try:
        apr.create_approval_request(
            title="need evidence",
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
            governed_object_id="PO-GATE-1",
            source_type="EXTERNAL",
            source_id="PO-GATE-1",
        )
    except apr.ApprovalError as e:
        denied_ev = e.code == "missing_required_evidence"
    check("evidence gate DENY without exception", denied_ev)

    # Authorise exception for that object + requirement
    req_gate = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="purchase_order",
        governed_object_id="PO-GATE-1",
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-RECV-EXC",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    gex.authorise_exception(req_gate["exception_id"], verified_person_id="PERS-MATT")
    under = apr.create_approval_request(
        title="under exception",
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
        governed_object_id="PO-GATE-1",
        source_type="EXTERNAL",
        source_id="PO-GATE-1",
    )
    check("evidence DENY → ALLOWED_UNDER_EXCEPTION create", under["status"] == "PENDING")
    # Exception consumed — second create without evidence fails again
    denied_again = False
    try:
        apr.create_approval_request(
            title="exhausted exception",
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
            governed_object_id="PO-GATE-1",
            source_type="EXTERNAL",
            source_id="PO-GATE-1",
        )
    except apr.ApprovalError as e:
        denied_again = e.code == "missing_required_evidence"
    check("consumed exception does not reuse", denied_again)
    # Confirm exception row consumed and normal deny code preserved on evaluate
    row_gate = gex.get_exception(req_gate["exception_id"])
    check("gate exception CONSUMED", row_gate and row_gate["status"] == "CONSUMED")
    normal_still = evd.evaluate_evidence_requirements(
        "ENT-GGV",
        "approval.request",
        request_type="SPEND",
        governed_object_type="purchase_order",
        governed_object_id="PO-GATE-1",
    )
    check(
        "normal evaluator still DENIED (not rewritten PASS)",
        normal_still["satisfied"] is False
        and normal_still["reason_code"] == "missing_required_evidence",
        str(normal_still),
    )

    # --- SoD under exception (bound to that constraint only) ---
    sod.insert_sod_constraint_for_test(
        allow_test_write=True,
        constraint_id="SOD-EXC-1",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="APPROVAL",
        prior_action="approval.request",
        proposed_action="approval.decide",
        scope_id=None,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed_ctl(control_type="SOD_CONSTRAINT", control_reference="SOD-EXC-1")
    gen = apr.create_approval_request(
        title="sod self under exception",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    denied_sod = False
    try:
        apr.approve_request(gen["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        denied_sod = e.code == "sod_same_person_conflict"
    check("SoD DENY without exception", denied_sod)

    # Evidence exception must NOT cover SoD
    seed_ctl(control_type="EVIDENCE_REQUIREMENT", control_reference="EVR-NOT-SOD")
    req_wrong_type = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="approval_request",
        governed_object_id=gen["approval_request_id"],
        control_type="EVIDENCE_REQUIREMENT",
        control_reference="EVR-NOT-SOD",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    gex.authorise_exception(req_wrong_type["exception_id"], verified_person_id="PERS-MATT")
    still_sod = False
    try:
        apr.approve_request(gen["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        still_sod = e.code == "sod_same_person_conflict"
    check("EVIDENCE exception does not cover SOD", still_sod)

    req_sod = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="approval_request",
        governed_object_id=gen["approval_request_id"],
        control_type="SOD_CONSTRAINT",
        control_reference="SOD-EXC-1",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    gex.authorise_exception(req_sod["exception_id"], verified_person_id="PERS-MATT")
    ok_sod = apr.approve_request(gen["approval_request_id"], verified_person_id="PERS-AMANDA")
    check(
        "SoD DENY → ALLOWED_UNDER_EXCEPTION approve",
        ok_sod["request"]["status"] == "APPROVED",
        str(ok_sod.get("request", {}).get("status")),
    )
    sod_row = gex.get_exception(req_sod["exception_id"])
    check("SoD exception consumed", sod_row and sod_row["status"] == "CONSUMED")
    # Normal SoD evaluator still DENIES for same person
    sod_normal = sod.evaluate_sod(
        "PERS-AMANDA",
        "ENT-GGV",
        "APPROVAL",
        "approval.decide",
        gen["approval_request_id"],
    )
    check(
        "normal SoD still CONFLICT (not rewritten PASS)",
        sod_normal["allowed"] is False
        and sod_normal["reason_code"] == "sod_same_person_conflict",
        str(sod_normal),
    )

    # Wrong constraint_id exception does not apply
    gen2 = apr.create_approval_request(
        title="wrong constraint binding",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    seed_ctl(control_type="SOD_CONSTRAINT", control_reference="SOD-OTHER")
    req_wrong_cid = gex.request_exception(
        entity_id="ENT-GGV",
        governed_object_type="approval_request",
        governed_object_id=gen2["approval_request_id"],
        control_type="SOD_CONSTRAINT",
        control_reference="SOD-OTHER",
        reason=REASON_OK,
        verified_person_id="PERS-AMANDA",
        allow_test_write=True,
    )
    gex.authorise_exception(req_wrong_cid["exception_id"], verified_person_id="PERS-MATT")
    wrong_cid = False
    try:
        apr.approve_request(gen2["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        wrong_cid = e.code == "sod_same_person_conflict"
    check("exception bound to other constraint_id ignored", wrong_cid)

    # Hard delete refused
    hard_del = False
    try:
        cdel = sqlite3.connect(str(tmp_db))
        cdel.execute(
            "DELETE FROM core_governance_exceptions WHERE exception_id=?",
            (req1["exception_id"],),
        )
        cdel.commit()
        cdel.close()
    except sqlite3.IntegrityError:
        hard_del = True
    except sqlite3.DatabaseError:
        hard_del = True
    check("hard delete refused by trigger", hard_del)

    # Live isolation after mutations
    (
        auth_end,
        audit_end,
        req_end,
        dec_end,
        pol_end,
        sod_end,
        evr_end,
        evd_end,
        exc_end,
    ) = live_counts()
    check("live auth still 0", auth_end == 0)
    check("live approvals still 0", req_end == 0 and dec_end == 0)
    check("live policies still<=1 Habitat", pol_end <= 1)
    check("live SoD still 0", sod_end == 0)
    check("live evidence reqs still<=1 Habitat", evr_end <= 1)
    check("live evidence records still 0", evd_end == 0)
    check("live exceptions still 0", exc_end == 0)
    check(
        "live audit unchanged by temp mutations",
        audit_end == audit_live_before_mut,
        f"{audit_live_before_mut}->{audit_end}",
    )

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
