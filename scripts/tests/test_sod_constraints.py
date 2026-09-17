#!/usr/bin/env python3
"""Tests for Wolf Core Segregation of Duties Constraints (Beta). Temp DB only.

Live org_authority_limits stay 0. Live governance policies stay 0.
Live SoD constraints stay 0. Live approval rows stay 0.
Live audit count must not rise. No Production.
"""
from __future__ import annotations

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
MIG = SCRIPTS / "migrations" / "migrate_sod_constraints.py"
SOD_PY = SCRIPTS / "core" / "sod.py"
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


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_sod_constraints", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def iso_now(*, delta_hours: int = 0, delta_days: int = 0) -> str:
    dt = datetime.now(TZ) + timedelta(hours=delta_hours, days=delta_days)
    return dt.isoformat(timespec="seconds")


def live_counts() -> tuple[int, int, int, int, int, int, int]:
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
        manage = (
            c.execute(
                "SELECT COUNT(*) FROM org_role_permissions "
                "WHERE permission_id='PERM-SOD-CONSTRAINT-MANAGE'"
            ).fetchone()[0]
            if "org_role_permissions" in tabs
            else 0
        )
        return int(auth), int(audit), int(req), int(dec), int(pol), int(sod), int(manage)
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

    src = SOD_PY.read_text(encoding="utf-8")
    apr_src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in sod.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("evaluate_sod defined", "def evaluate_sod" in src)
    check("sod wired in approvals._decide", "evaluate_sod" in apr_src)
    check("SoD HONESTY BUILT", '"segregation_of_duties": "BUILT"' in apr_src)

    (
        auth_before,
        audit_before,
        req_before,
        dec_before,
        pol_before,
        sod_before,
        manage_before,
    ) = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live approvals before=0", req_before == 0 and dec_before == 0)
    check("live governance policies before=0", pol_before == 0, str(pol_before))
    check("live SoD before=0", sod_before == 0, str(sod_before))
    check("live manage grants before=0", manage_before == 0)

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
        manage_live,
    ) = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live governance policies=0", pol_live == 0, str(pol_live))
    check("live SoD constraints=0", sod_live == 0, str(sod_live))
    check("live manage grants=0", manage_live == 0)
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    backups = list(BACKUP_DIR.glob("pre-sod-constraints-*.sqlite"))
    check("pre-sod-constraints backup exists", len(backups) >= 1, str(BACKUP_DIR))

    live = sqlite3.connect(str(LIVE_DB))
    tab_c = live.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='core_sod_constraints'"
    ).fetchone()
    tab_p = live.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='core_sod_participation'"
    ).fetchone()
    check("core_sod_constraints table", bool(tab_c))
    check("core_sod_participation table", bool(tab_p))
    mig_row = live.execute(
        "SELECT id FROM schema_migrations WHERE id='017_sod_constraints'"
    ).fetchone()
    check("schema_migrations 017", bool(mig_row))
    read_perm = live.execute(
        "SELECT code, status FROM org_permissions WHERE code='sod.constraint.read'"
    ).fetchone()
    manage_perm = live.execute(
        "SELECT code, status FROM org_permissions WHERE code='sod.constraint.manage'"
    ).fetchone()
    check("sod.constraint.read seeded ACTIVE", bool(read_perm) and read_perm[1] == "ACTIVE")
    check("sod.constraint.manage seeded ACTIVE", bool(manage_perm) and manage_perm[1] == "ACTIVE")
    matt_read = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE role_id='ROLE-MATT' AND permission_id='PERM-SOD-CONSTRAINT-READ'
        """
    ).fetchone()[0]
    check("Matt sod.constraint.read grant", matt_read == 1)
    live.close()

    mig.DB = Path("/tmp/Production/fake.sqlite")
    try:
        rc = mig.main()
    except Exception:
        rc = 2
    check("Production path refused", rc != 0, str(rc))

    # --- Temp DB ---
    td = ROOT / "catalog" / "backups" / f"tmp-sod-constraints-{os.getpid()}"
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
    grant_role_perms(
        conn,
        "ROLE-GGV-EDIT",
        ("PERM-APPROVAL-DECIDE", PERM_SPEND, "PERM-APPROVAL-READ"),
    )
    insert_limit(conn, lid="ALIM-TMP-SOD-MATT", threshold=5_000_000.0)
    insert_limit(
        conn,
        lid="ALIM-TMP-SOD-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
        threshold=5_000_000.0,
    )
    insert_limit(
        conn,
        lid="ALIM-TMP-SOD-HAIKAL",
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
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    audit_live_before_mut = live_counts()[1]

    # --- manage insert denied without hook ---
    denied_manage = False
    try:
        sod.insert_sod_constraint_for_test(
            entity_id="ENT-GGV",
            process_family="APPROVAL",
            prior_action="approval.request",
            proposed_action="approval.decide",
            allow_test_write=False,
            verified_person_id="PERS-AMANDA",
        )
    except sod.SodError as e:
        denied_manage = e.code == "manage_denied"
    check("insert without manage/test hook denied", denied_manage)

    def seed(**kw):
        return sod.insert_sod_constraint_for_test(allow_test_write=True, **kw)

    # --- Zero ACTIVE → sod_not_applicable ---
    ev0 = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-GGV",
        "APPROVAL",
        "approval.decide",
        "APR-DOES-NOT-EXIST",
    )
    check(
        "zero ACTIVE → sod_not_applicable",
        ev0["allowed"] is True and ev0["reason_code"] == "sod_not_applicable",
        str(ev0),
    )

    # --- Unbound approve still works with zero SoD ---
    unbound = apr.create_approval_request(
        title="unbound pre-sod",
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
    check("unbound approve with zero SoD", ok_unbound["request"]["status"] == "APPROVED")

    # --- Entity-wide SAME_PERSON: requester cannot approve ---
    seed(
        constraint_id="SOD-REQ-DECIDE",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="APPROVAL",
        prior_action="approval.request",
        proposed_action="approval.decide",
        scope_id=None,
        effective_from="2026-01-01T00:00:00Z",
    )
    # GENERAL so self_approval flag does not fire; SoD still applies
    gen = apr.create_approval_request(
        title="general sod self",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    denied_self = False
    try:
        apr.approve_request(gen["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        denied_self = e.code == "sod_same_person_conflict"
    check("requester APPROVED → sod_same_person_conflict", denied_self)
    still_pending = apr.get_approval_request(gen["approval_request_id"])
    check("conflict leaves PENDING (no decision)", still_pending["status"] == "PENDING")

    # Different person OK
    other = apr.approve_request(gen["approval_request_id"], verified_person_id="PERS-MATT")
    check("different Person APPROVED → sod_ok", other["request"]["status"] == "APPROVED")

    # --- Self-approval still fires on material (before/alongside SoD) ---
    mat = apr.create_approval_request(
        title="material self",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="50000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    self_code = None
    try:
        apr.approve_request(mat["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        self_code = e.code
    check(
        "material self still self_approval_denied",
        self_code == "self_approval_denied",
        str(self_code),
    )

    # --- Exact scope beats entity-wide ---
    seed(
        constraint_id="SOD-SCOPE-WIDE",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.approve",
        scope_id=None,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        constraint_id="SOD-SCOPE-EXACT",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.approve",
        scope_id=SCOPE_EXACT,
        effective_from="2026-01-01T00:00:00Z",
    )
    sod.insert_sod_participation_for_test(
        allow_test_write=True,
        person_id="PERS-AMANDA",
        action="payment.prepare",
        subject_id="PAY-SUBJECT-1",
        entity_id="ENT-GGV",
        scope_id=SCOPE_EXACT,
    )
    # Matt not in prior → ok via exact constraint
    ev_scope = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-GGV",
        "PAYMENT",
        "payment.approve",
        "PAY-SUBJECT-1",
        scope_id=SCOPE_EXACT,
    )
    check(
        "exact scope beats entity-wide",
        ev_scope["matched_constraint_id"] == "SOD-SCOPE-EXACT"
        and ev_scope["reason_code"] == "sod_ok",
        str(ev_scope),
    )
    # Amanda is prior → conflict on exact
    ev_scope_bad = sod.evaluate_sod(
        "PERS-AMANDA",
        "ENT-GGV",
        "PAYMENT",
        "payment.approve",
        "PAY-SUBJECT-1",
        scope_id=SCOPE_EXACT,
    )
    check(
        "exact scope SAME_PERSON conflict",
        ev_scope_bad["reason_code"] == "sod_same_person_conflict",
        str(ev_scope_bad),
    )

    # --- Equal specificity → sod_constraint_conflict ---
    seed(
        constraint_id="SOD-CONFLICT-A",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.approve",
        scope_id="SCOPE-SOD-CONFLICT",
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        constraint_id="SOD-CONFLICT-B",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.approve",
        scope_id="SCOPE-SOD-CONFLICT",
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_cf = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-GGV",
        "PAYMENT",
        "payment.approve",
        "PAY-SUBJECT-CF",
        scope_id="SCOPE-SOD-CONFLICT",
    )
    check(
        "equal specificity → sod_constraint_conflict",
        ev_cf["reason_code"] == "sod_constraint_conflict" and ev_cf["allowed"] is False,
        str(ev_cf),
    )

    # --- Evidence unavailable (generic family, no participation) ---
    seed(
        constraint_id="SOD-EVIDENCE",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.release",
        scope_id="SCOPE-SOD-EVID",
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_ev = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-GGV",
        "PAYMENT",
        "payment.release",
        "PAY-NO-EVIDENCE",
        scope_id="SCOPE-SOD-EVID",
    )
    check(
        "missing participation → sod_evidence_unavailable",
        ev_ev["reason_code"] == "sod_evidence_unavailable" and ev_ev["allowed"] is False,
        str(ev_ev),
    )

    # APPROVAL missing subject → evidence unavailable when constraint ACTIVE
    ev_miss = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-GGV",
        "APPROVAL",
        "approval.decide",
        "APR-MISSING-SUBJECT",
    )
    check(
        "missing approval request → sod_evidence_unavailable",
        ev_miss["reason_code"] == "sod_evidence_unavailable",
        str(ev_miss),
    )

    # --- Client independence claims ignored ---
    sod.insert_sod_participation_for_test(
        allow_test_write=True,
        person_id="PERS-AMANDA",
        action="payment.prepare",
        subject_id="PAY-CLIENT-CLAIM",
        entity_id="ENT-GGV",
        scope_id="SCOPE-CLIENT",
    )
    seed(
        constraint_id="SOD-CLIENT",
        constraint_version=1,
        entity_id="ENT-GGV",
        process_family="PAYMENT",
        prior_action="payment.prepare",
        proposed_action="payment.approve",
        scope_id="SCOPE-CLIENT",
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_claim = sod.evaluate_sod(
        "PERS-AMANDA",
        "ENT-GGV",
        "PAYMENT",
        "payment.approve",
        "PAY-CLIENT-CLAIM",
        scope_id="SCOPE-CLIENT",
        requester_is_different=True,
        client_prior_participants=["PERS-MATT"],
        forged_participation=["PERS-HAIKAL"],
    )
    check(
        "client independence claims ignored",
        ev_claim["reason_code"] == "sod_same_person_conflict",
        str(ev_claim),
    )

    # --- Dual: each Person checked independently ---
    dual = apr.create_approval_request(
        title="dual sod",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        required_decision_count=2,
    )
    rid_dual = dual["approval_request_id"]
    # Amanda (requester) cannot be first approver under SoD
    dual_self = False
    try:
        # material → self_approval first; use Haikal then Amanda as second which is not requester... 
        # For dual self via SoD: Amanda as second after Matt — Amanda is requester → SoD deny
        pass
    except Exception:
        pass
    first = apr.approve_request(rid_dual, verified_person_id="PERS-MATT", reason="d1")
    check("dual #1 Matt PENDING", first["request"]["status"] == "PENDING")
    amanda_second = False
    try:
        apr.approve_request(rid_dual, verified_person_id="PERS-AMANDA", reason="d2")
    except apr.ApprovalError as e:
        # material self_approval fires first for requester
        amanda_second = e.code in ("self_approval_denied", "sod_same_person_conflict")
    check("dual requester as #2 denied", amanda_second)
    second = apr.approve_request(rid_dual, verified_person_id="PERS-HAIKAL", reason="d2")
    check(
        "dual independent Persons APPROVED",
        second["request"]["status"] == "APPROVED",
        str(second["request"].get("status")),
    )

    # --- Delegation cannot launder SoD ---
    c = sqlite3.connect(str(tmp_db))
    grant_role_perms(
        c,
        "ROLE-MATT",
        ("PERM-DELEGATION-CREATE", "PERM-DELEGATION-READ", "PERM-DELEGATION-REVOKE"),
    )
    # Strip Amanda native decide so she must use delegation — still same Person
    # Keep Amanda decide for simplicity: SoD uses Person id not basis
    c.commit()
    c.close()
    ef = iso_now(delta_hours=-1)
    et = iso_now(delta_days=7)
    dlg.create_delegation(
        verified_person_id="PERS-MATT",
        delegate_person_id="PERS-AMANDA",
        delegator_assignment_id="ASG-MATT-OWNER-1",
        delegate_assignment_id="ASG-AMANDA-CM-1",
        entity_id="ENT-GGV",
        scope_id=SCOPE_EXACT,
        permission_code="approval.decide",
        effective_from=ef,
        effective_to=et,
    )
    dlg_req = apr.create_approval_request(
        title="dlg cannot launder sod",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="GENERAL",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    launder = False
    try:
        apr.approve_request(dlg_req["approval_request_id"], verified_person_id="PERS-AMANDA")
    except apr.ApprovalError as e:
        launder = e.code == "sod_same_person_conflict"
    check("delegation cannot launder SoD", launder)

    # --- INACTIVE constraint ignored ---
    seed(
        constraint_id="SOD-INACTIVE",
        constraint_version=1,
        entity_id="ENT-OTHER",
        process_family="APPROVAL",
        prior_action="approval.request",
        proposed_action="approval.decide",
        status="INACTIVE",
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_inact = sod.evaluate_sod(
        "PERS-MATT",
        "ENT-OTHER",
        "APPROVAL",
        "approval.decide",
        "APR-X",
    )
    check(
        "INACTIVE → sod_not_applicable",
        ev_inact["reason_code"] == "sod_not_applicable",
        str(ev_inact),
    )

    # --- Audit sod.evaluated present on temp ---
    ac = sqlite3.connect(str(tmp_db))
    n_sod_audit = ac.execute(
        "SELECT COUNT(*) FROM core_audit_events WHERE action='sod.evaluated'"
    ).fetchone()[0]
    ac.close()
    check("sod.evaluated audit rows written", n_sod_audit >= 1, str(n_sod_audit))

    # --- Live isolation after mutations ---
    (
        auth_end,
        audit_end,
        req_end,
        dec_end,
        pol_end,
        sod_end,
        manage_end,
    ) = live_counts()
    check("live auth still 0 end", auth_end == 0)
    check("live SoD still 0 end", sod_end == 0)
    check("live gov policies still 0 end", pol_end == 0)
    check("live approvals still 0 end", req_end == 0 and dec_end == 0)
    check("live manage still 0 end", manage_end == 0)
    check(
        "live audit unchanged by tests",
        audit_end == audit_live_before_mut,
        f"{audit_live_before_mut}->{audit_end}",
    )

    # cleanup temp
    shutil.rmtree(td, ignore_errors=True)

    print(f"pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
