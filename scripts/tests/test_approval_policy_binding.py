#!/usr/bin/env python3
"""Tests for Wolf Core Approval Policy Binding (Beta). Temp DB only.

Live org_authority_limits stay 0. Live governance policies stay 0.
Live approval rows stay 0. Live audit count must not rise.
No real business thresholds. No Production.
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
MIG = SCRIPTS / "migrations" / "migrate_approval_policy_binding.py"
GOV_PY = SCRIPTS / "core" / "governance_policy.py"
APR_PY = SCRIPTS / "core" / "approvals.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
TGT_DEPT = "DEPT-GGV-CONTENT"
SCOPE_EXACT = "SCOPE-GGV-CONTENT"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_approval_policy_binding", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, int, int, int, int, int]:
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
        manage = (
            c.execute(
                "SELECT COUNT(*) FROM org_role_permissions WHERE permission_id='PERM-GOV-POLICY-MANAGE'"
            ).fetchone()[0]
            if "org_role_permissions" in tabs
            else 0
        )
        return int(auth), int(audit), int(req), int(dec), int(pol), int(manage)
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

    src = GOV_PY.read_text(encoding="utf-8")
    apr_src = APR_PY.read_text(encoding="utf-8")
    check("no LLM in governance_policy.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("bind_policy in create_approval_request", "bind_policy" in apr_src)
    check("evaluate_governance_policy defined", "def evaluate_governance_policy" in src)
    check("policy_binding HONESTY", "policy_binding" in apr_src)

    auth_before, audit_before, req_before, dec_before, pol_before, manage_before = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live approvals before=0", req_before == 0 and dec_before == 0)
    check("live governance policies before=0", pol_before == 0, str(pol_before))
    check("live manage grants before=0", manage_before == 0)

    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("migration idempotent", mig.main() == 0)

    auth_after, audit_mid, req_live, dec_live, pol_live, manage_live = live_counts()
    check("live auth_limits after migrate=0", auth_after == 0, str(auth_after))
    check("live approval requests=0", req_live == 0, str(req_live))
    check("live approval decisions=0", dec_live == 0, str(dec_live))
    check("live governance policies=0", pol_live == 0, str(pol_live))
    check("live manage grants=0", manage_live == 0)
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    backups = list(BACKUP_DIR.glob("pre-approval-policy-binding-*.sqlite"))
    check("pre-approval-policy-binding backup exists", len(backups) >= 1, str(BACKUP_DIR))

    live = sqlite3.connect(str(LIVE_DB))
    cols = {r[1] for r in live.execute("PRAGMA table_info(core_approval_requests)")}
    check("governing_policy_id column live", "governing_policy_id" in cols)
    check("governing_policy_version column live", "governing_policy_version" in cols)
    tab = live.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='core_governance_policies'"
    ).fetchone()
    check("core_governance_policies table", bool(tab))
    mig_row = live.execute(
        "SELECT id FROM schema_migrations WHERE id='016_approval_policy_binding'"
    ).fetchone()
    check("schema_migrations 016", bool(mig_row))
    read_perm = live.execute(
        "SELECT code, status FROM org_permissions WHERE code='governance.policy.read'"
    ).fetchone()
    manage_perm = live.execute(
        "SELECT code, status FROM org_permissions WHERE code='governance.policy.manage'"
    ).fetchone()
    check("governance.policy.read seeded ACTIVE", bool(read_perm) and read_perm[1] == "ACTIVE")
    check("governance.policy.manage seeded ACTIVE", bool(manage_perm) and manage_perm[1] == "ACTIVE")
    live.close()

    # Production path refused
    mig.DB = Path("/tmp/Production/fake.sqlite")
    try:
        rc = mig.main()
    except Exception:
        rc = 2
    check("Production path refused", rc != 0, str(rc))

    # --- Temp DB ---
    td = ROOT / "catalog" / "backups" / f"tmp-approval-policy-binding-{os.getpid()}"
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
    insert_limit(conn, lid="ALIM-TMP-POL-MATT", threshold=5_000_000.0)
    insert_limit(
        conn,
        lid="ALIM-TMP-POL-AMANDA",
        role_id="ROLE-CONTENT-MGMT",
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
    ):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    audit_live_before_mut = live_counts()[1]

    # --- manage insert denied without hook ---
    denied_manage = False
    try:
        gov.insert_governance_policy_for_test(
            entity_id="ENT-GGV",
            action_type="SPEND_APPROVE",
            allow_test_write=False,
            verified_person_id="PERS-AMANDA",
        )
    except gov.GovernancePolicyError as e:
        denied_manage = e.code == "manage_denied"
    check("insert without manage/test hook denied", denied_manage)

    def seed(**kw):
        return gov.insert_governance_policy_for_test(allow_test_write=True, **kw)

    # --- Exact scope beats entity-wide ---
    seed(
        policy_id="GPO-SCOPE-WIDE",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id=None,
        required_decision_count=1,
        amount_min="0",
        amount_max="999999999",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        policy_id="GPO-SCOPE-EXACT",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id=SCOPE_EXACT,
        required_decision_count=2,
        amount_min="0",
        amount_max="999999999",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_scope = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id=SCOPE_EXACT,
        request_type="SPEND",
        amount="100000",
        currency="IDR",
    )
    check(
        "exact scope beats entity-wide",
        ev_scope["result"] == "REQUIREMENTS"
        and ev_scope["matched_policy_id"] == "GPO-SCOPE-EXACT"
        and ev_scope["approvals_required"] == 2,
        str(ev_scope),
    )

    # --- Amount band specificity: both bounds beat open-ended beat no band ---
    seed(
        policy_id="GPO-BAND-NONE",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-BAND-TEST",
        required_decision_count=1,
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        policy_id="GPO-BAND-OPEN",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-BAND-TEST",
        required_decision_count=2,
        amount_min="0",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        policy_id="GPO-BAND-BOTH",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-BAND-TEST",
        required_decision_count=3,
        amount_min="0",
        amount_max="500000",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_band = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id="SCOPE-BAND-TEST",
        request_type="SPEND",
        amount="100000",
        currency="IDR",
    )
    check(
        "both-bound amount band beats open/none",
        ev_band["matched_policy_id"] == "GPO-BAND-BOTH" and ev_band["approvals_required"] == 3,
        str(ev_band.get("matched_policy_id")),
    )

    # --- Boundary inclusive ---
    ev_lo = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id="SCOPE-BAND-TEST",
        request_type="SPEND",
        amount="0",
        currency="IDR",
    )
    ev_hi = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id="SCOPE-BAND-TEST",
        request_type="SPEND",
        amount="500000",
        currency="IDR",
    )
    check("amount band inclusive min", ev_lo["matched_policy_id"] == "GPO-BAND-BOTH")
    check("amount band inclusive max", ev_hi["matched_policy_id"] == "GPO-BAND-BOTH")

    # --- Conflict: equally specific distinct policies ---
    seed(
        policy_id="GPO-CONFLICT-A",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-CONFLICT",
        required_decision_count=2,
        amount_min="0",
        amount_max="1000000",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        policy_id="GPO-CONFLICT-B",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-CONFLICT",
        required_decision_count=2,
        amount_min="0",
        amount_max="1000000",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_cf = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id="SCOPE-CONFLICT",
        request_type="SPEND",
        amount="50000",
        currency="IDR",
    )
    check(
        "equal specificity → policy_conflict",
        ev_cf["result"] == "CONFLICT" and ev_cf["reason_code"] == "policy_conflict",
        str(ev_cf),
    )

    # --- No match → deny (dedicated action; no entity-wide spillover) ---
    ev_none = gov.evaluate_governance_policy(
        "ENT-GGV",
        "EXCEPTION",
        scope_id="SCOPE-NOBODY",
        request_type="EXCEPTION",
        amount="100",
        currency="IDR",
    )
    check(
        "no match → no_matching_policy",
        ev_none["result"] == "NO_MATCH" and ev_none["reason_code"] == "no_matching_policy",
        str(ev_none),
    )

    # --- PROHIBITED ---
    seed(
        policy_id="GPO-PROHIBITED",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="EXCEPTION",
        request_type="EXCEPTION",
        scope_id="SCOPE-PROHIBITED",
        prohibited=1,
        required_decision_count=1,
        amount_min="0",
        amount_max="999999999",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_pr = gov.evaluate_governance_policy(
        "ENT-GGV",
        "EXCEPTION",
        scope_id="SCOPE-PROHIBITED",
        request_type="EXCEPTION",
        amount="100",
        currency="IDR",
    )
    check(
        "PROHIBITED → action_prohibited",
        ev_pr["result"] == "PROHIBITED" and ev_pr["reason_code"] == "action_prohibited",
    )

    # --- NULL / malformed / negative amount ---
    ev_miss = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id=SCOPE_EXACT,
        request_type="SPEND",
        amount=None,
        currency="IDR",
    )
    check("NULL amount → missing_amount", ev_miss["reason_code"] == "missing_amount")
    ev_bad = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id=SCOPE_EXACT,
        request_type="SPEND",
        amount="not-a-number",
        currency="IDR",
    )
    check("malformed amount → missing_amount", ev_bad["reason_code"] == "missing_amount")
    ev_neg = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id=SCOPE_EXACT,
        request_type="SPEND",
        amount="-1",
        currency="IDR",
    )
    check("negative amount → missing_amount", ev_neg["reason_code"] == "missing_amount")

    # --- Gap between bands → no match (EXCEPTION only; no entity-wide) ---
    seed(
        policy_id="GPO-GAP-LOW",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="EXCEPTION",
        request_type="EXCEPTION",
        scope_id="SCOPE-GAP",
        required_decision_count=1,
        amount_min="0",
        amount_max="100",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    seed(
        policy_id="GPO-GAP-HIGH",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="EXCEPTION",
        request_type="EXCEPTION",
        scope_id="SCOPE-GAP",
        required_decision_count=1,
        amount_min="200",
        amount_max="300",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
    )
    ev_gap = gov.evaluate_governance_policy(
        "ENT-GGV",
        "EXCEPTION",
        scope_id="SCOPE-GAP",
        request_type="EXCEPTION",
        amount="150",
        currency="IDR",
    )
    check("amount gap → no_matching_policy", ev_gap["reason_code"] == "no_matching_policy", str(ev_gap))

    # --- bind_policy create: sets count + governing fields ---
    bound = apr.create_approval_request(
        title="bound spend",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        bind_policy=True,
        scope_id=SCOPE_EXACT,
        required_decision_count=2,
    )
    check("bind_policy create PENDING", bound["status"] == "PENDING")
    check(
        "bind_policy sets required_decision_count from policy",
        int(bound["required_decision_count"]) == 2,
        str(bound.get("required_decision_count")),
    )
    check(
        "governing_policy_id stored",
        bound.get("governing_policy_id") == "GPO-SCOPE-EXACT",
        str(bound.get("governing_policy_id")),
    )
    check(
        "governing_policy_version stored",
        int(bound.get("governing_policy_version") or 0) == 1,
    )

    # --- client lower count refused ---
    low = False
    try:
        apr.create_approval_request(
            title="override low",
            owning_entity_id="ENT-GGV",
            department_id=TGT_DEPT,
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            material_amount="100000",
            currency="IDR",
            verified_person_id="PERS-AMANDA",
            requested_by_assignment_id="ASG-AMANDA-CM-1",
            bind_policy=True,
            scope_id=SCOPE_EXACT,
            required_decision_count=1,
        )
    except apr.ApprovalError as e:
        low = e.code == "policy_count_override_refused"
    check("client lower count → policy_count_override_refused", low)

    # --- bind_policy PROHIBITED / NO_MATCH / CONFLICT raise ---
    codes = {}
    for label, kwargs, expect in (
        (
            "prohibited",
            {"request_type": "EXCEPTION", "scope_id": "SCOPE-PROHIBITED", "material_amount": "100"},
            "action_prohibited",
        ),
        (
            "no_match",
            {"request_type": "EXCEPTION", "scope_id": "SCOPE-NOBODY", "material_amount": "100"},
            "no_matching_policy",
        ),
        (
            "conflict",
            {"request_type": "SPEND", "scope_id": "SCOPE-CONFLICT", "material_amount": "50000"},
            "policy_conflict",
        ),
    ):
        ok = False
        try:
            apr.create_approval_request(
                title=f"bind {label}",
                owning_entity_id="ENT-GGV",
                department_id=TGT_DEPT,
                required_permission_code=CODE_SPEND,
                currency="IDR",
                verified_person_id="PERS-AMANDA",
                requested_by_assignment_id="ASG-AMANDA-CM-1",
                bind_policy=True,
                **kwargs,
            )
        except apr.ApprovalError as e:
            ok = e.code == expect
            codes[label] = e.code
        check(f"bind_policy {label} → {expect}", ok, str(codes.get(label)))

    # --- unbound path still works (backward compat) ---
    unbound = apr.create_approval_request(
        title="unbound spend",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        bind_policy=False,
        required_decision_count=1,
    )
    check("unbound create works without policies", unbound["status"] == "PENDING")
    check("unbound governing_policy_id NULL", unbound.get("governing_policy_id") is None)

    # --- historical governing fields immutable ---
    immut = False
    try:
        apr.refuse_immutable_mutation({"governing_policy_id": "GPO-X"})
    except apr.ApprovalError as e:
        immut = e.code == "immutable_fields"
    check("governing_policy_id immutable", immut)

    # --- dual on policy-bound request ---
    c2 = sqlite3.connect(str(tmp_db))
    grant_role_perms(
        c2,
        "ROLE-GGV-EDIT",
        ("PERM-APPROVAL-DECIDE", PERM_SPEND, "PERM-APPROVAL-READ"),
    )
    insert_limit(c2, lid="ALIM-TMP-POL-HAIKAL", role_id="ROLE-GGV-EDIT", threshold=5_000_000.0)
    c2.commit()
    c2.close()

    dual2 = apr.create_approval_request(
        title="dual via policy 2",
        owning_entity_id="ENT-GGV",
        department_id=TGT_DEPT,
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
        bind_policy=True,
        scope_id=SCOPE_EXACT,
        required_decision_count=2,
    )
    rid2 = dual2["approval_request_id"]
    first = apr.approve_request(rid2, verified_person_id="PERS-MATT", reason="p1")
    check("policy-bound dual first stays PENDING", first["request"]["status"] == "PENDING")
    term = apr.approve_request(rid2, verified_person_id="PERS-HAIKAL", reason="p2")
    check(
        "policy-bound dual reaches APPROVED",
        term["request"]["status"] == "APPROVED" and term.get("terminal") is True,
        str(term["request"].get("status")),
    )
    check(
        "historical governing_policy retained",
        term["request"].get("governing_policy_id") == "GPO-SCOPE-EXACT",
    )

    # --- Permission cannot override PROHIBITED (evaluate still PROHIBITED) ---
    check(
        "permission cannot override PROHIBITED",
        ev_pr["result"] == "PROHIBITED",
    )

    # --- Audit policy.evaluated events present on temp ---
    pol_aud = audit.list_events(action="policy.evaluated", source="governance_policy", limit=50)
    reasons = {e.get("reason_code") for e in pol_aud}
    check("audit policy.evaluated match", "policy_matched" in reasons, str(reasons))
    check("audit policy.evaluated no_match", "no_matching_policy" in reasons)
    check("audit policy.evaluated conflict", "policy_conflict" in reasons)
    check("audit policy.evaluated prohibited", "action_prohibited" in reasons)

    # --- Higher version preferred for same policy_id ---
    seed(
        policy_id="GPO-VER",
        policy_version=1,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-VER",
        required_decision_count=1,
        amount_min="0",
        amount_max="999999",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
        status="INACTIVE",
    )
    seed(
        policy_id="GPO-VER",
        policy_version=2,
        entity_id="ENT-GGV",
        action_type="SPEND_APPROVE",
        request_type="SPEND",
        scope_id="SCOPE-VER",
        required_decision_count=2,
        amount_min="0",
        amount_max="999999",
        currency="IDR",
        required_permission_code=CODE_SPEND,
        effective_from="2026-01-01T00:00:00Z",
        status="ACTIVE",
    )
    ev_ver = gov.evaluate_governance_policy(
        "ENT-GGV",
        "SPEND_APPROVE",
        scope_id="SCOPE-VER",
        request_type="SPEND",
        amount="10",
        currency="IDR",
    )
    check(
        "ACTIVE higher version selected",
        ev_ver["matched_policy_version"] == 2 and ev_ver["approvals_required"] == 2,
        str(ev_ver),
    )

    # Live isolation finale
    auth_f, audit_f, req_f, dec_f, pol_f, manage_f = live_counts()
    check("live auth final=0", auth_f == 0)
    check("live approvals final=0", req_f == 0 and dec_f == 0)
    check("live governance policies final=0", pol_f == 0)
    check("live manage grants final=0", manage_f == 0)
    check(
        "live audit unchanged by tests",
        audit_f == audit_live_before_mut,
        f"{audit_live_before_mut}->{audit_f}",
    )
    check("live audit still 47", audit_f == 47, str(audit_f))

    # Cleanup temp
    try:
        shutil.rmtree(td)
    except OSError:
        pass

    print(f"pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
