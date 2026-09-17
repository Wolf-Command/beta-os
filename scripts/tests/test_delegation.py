#!/usr/bin/env python3
"""Tests for Wolf Core Delegation (Beta). Temp DB only.

Live org_authority_limits must stay 0.
Live core_delegations must stay 0.
Live core_audit_events count must not rise.
Identity never delegates. No re-delegation. No self-approval laundering.
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
MIG = SCRIPTS / "migrations" / "migrate_delegation.py"
DLG_PY = SCRIPTS / "core" / "delegation.py"
BACKUP_DIR = ROOT / "catalog" / "backups"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"
PERM_SPEND = "PERM-TEST-SPEND"
CODE_SPEND = "test.spend.approve"
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
    spec = importlib.util.spec_from_file_location("migrate_delegation", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> tuple[int, int, int]:
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
        dlg = (
            c.execute("SELECT COUNT(*) FROM core_delegations").fetchone()[0]
            if "core_delegations" in tabs
            else 0
        )
        return int(auth), int(audit), int(dlg)
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


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    os.environ["BETA_APPROVAL_DENY_SELF_APPROVAL"] = "1"

    src = DLG_PY.read_text(encoding="utf-8")
    check("no LLM in delegation.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("refuses wolf-system", "refuses wolf-system" in src)
    check("refuses Production", "Production" in src)
    check("identity never delegates flag", "identity_never_delegates" in src)
    check("redelegation DENIED honesty", '"redelegation": "DENIED"' in src or "'redelegation': 'DENIED'" in src)

    auth_before, audit_before, dlg_before = live_counts()
    check("live auth_limits before=0", auth_before == 0, str(auth_before))
    check("live delegations before=0", dlg_before == 0, str(dlg_before))

    backups = list(BACKUP_DIR.glob("pre-delegation-*.sqlite"))
    check("pre-delegation backup exists", len(backups) >= 1, str(BACKUP_DIR))

    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("26 migration idempotent", mig.main() == 0)

    auth_after, audit_mid, dlg_live = live_counts()
    check("23 live Authority Limits remain 0", auth_after == 0, str(auth_after))
    check("25 live seeded delegations = 0", dlg_live == 0, str(dlg_live))
    check("live audit unchanged by migrate", audit_mid == audit_before, f"{audit_before}->{audit_mid}")

    live = sqlite3.connect(str(LIVE_DB))
    codes = [
        r[0]
        for r in live.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id='ROLE-MATT' AND p.code LIKE 'delegation.%'
            ORDER BY p.code
            """
        ).fetchall()
    ]
    check(
        "three Matt delegation.* grants",
        codes == ["delegation.create", "delegation.read", "delegation.revoke"],
        str(codes),
    )
    other = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (SELECT permission_id FROM org_permissions WHERE code LIKE 'delegation.%')
          AND role_id != 'ROLE-MATT'
        """
    ).fetchone()[0]
    check("no non-Matt delegation.* grants", other == 0)
    cols = {r[1] for r in live.execute("PRAGMA table_info(core_approval_decisions)")}
    check("authority_basis_type column", "authority_basis_type" in cols)
    check("authority_basis_delegation_id column", "authority_basis_delegation_id" in cols)
    live.close()

    # --- Temp DB for mutating tests ---
    td = ROOT / "catalog" / "backups" / f"tmp-delegation-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    mig.DB = tmp_db
    check("temp migrate exit 0", mig.main() == 0)

    # Production path refused
    mig.DB = Path("/tmp/Production/fake.sqlite")
    try:
        rc = mig.main()
    except Exception:
        rc = 2
    check("27 Production path refused", rc != 0, str(rc))
    mig.DB = tmp_db

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Activate spend perm + grant to Matt; fixture authority (TEMP ONLY)
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
    # Grant approval.decide + spend to Haikal's role for native-negative / delegate path
    # Haikal does NOT get approval.decide or spend — receives via delegation
    insert_limit(conn, lid="ALIM-TMP-DLG-MATT", threshold=5_000_000.0)
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

    ef = iso_now(delta_hours=-1)
    et = iso_now(delta_days=7)

    # 1. valid create + ACTIVE
    d1 = dlg.create_delegation(
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
        reason="temp cover",
    )
    check("1 valid delegation create + ACTIVE", d1["status"] == "ACTIVE", str(d1.get("status")))
    check("DLG- prefix", d1["delegation_id"].startswith("DLG-"))
    did = d1["delegation_id"]

    # 2. wrong Entity denied at evaluate
    ev_wrong_ent = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-OTHER-FAKE"},
        {"amount": "100", "currency": "IDR"},
    )
    check("2 wrong Entity denied", not ev_wrong_ent.get("allowed"), str(ev_wrong_ent.get("reason")))

    # 3. wrong Scope — create a dept-only target outside SCOPE-GGV-CONTENT coverage?
    # SCOPE-GGV-CONTENT covers DEPT-GGV-CONTENT. Use a brand not under content scope.
    # ENT-GGV entity-only is covered via department parent; use location that isn't covered.
    # Safer: create second delegation with SCOPE-GGV-CONTENT then evaluate brand not in scope.
    # Actually SCOPE-GGV-CONTENT only covers department DEPT-GGV-CONTENT.
    # Target with brand_id not in covered brands should fail.
    brands = sqlite3.connect(str(tmp_db)).execute(
        "SELECT brand_id FROM org_brands WHERE entity_id='ENT-GGV' LIMIT 1"
    ).fetchone()
    # Content scope covers departments not brands — brand_id alone may fail
    ev_wrong_scope = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-GGV", "brand_id": "BRAND-DOES-NOT-EXIST"},
        {"amount": "100", "currency": "IDR"},
    )
    check("3 wrong Scope denied", not ev_wrong_scope.get("allowed"), str(ev_wrong_scope.get("reason")))

    # 4. Permission not held by delegator → create denied
    # Amanda lacks test.spend.approve natively; try Matt creating with Amanda as delegator
    # Better: create with permission Amanda doesn't have — use Matt as verified but
    # Amanda as forged? Matt can create for others — use Amanda as delegator who lacks spend.
    denied4 = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-MATT",
            delegator_person_id="PERS-AMANDA",
            delegate_person_id="PERS-HAIKAL",
            delegator_assignment_id="ASG-AMANDA-CM-1",
            delegate_assignment_id="ASG-HAIKAL-VE-1",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied4 = e.code == "delegator_lacks_permission"
    check("4 Permission not held by delegator → create denied", denied4)

    # 5. delegate without valid Assignment
    denied5 = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-MATT",
            delegate_person_id="PERS-HAIKAL",
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id="ASG-DOES-NOT-EXIST",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied5 = e.code == "inactive_assignment"
    check("5 delegate without valid Assignment → create denied", denied5)

    # 6. before effective_from → denied
    d_future = dlg.create_delegation(
        verified_person_id="PERS-MATT",
        delegate_person_id="PERS-HAIKAL",
        delegator_assignment_id="ASG-MATT-OWNER-1",
        delegate_assignment_id="ASG-HAIKAL-VE-1",
        entity_id="ENT-GGV",
        scope_id="SCOPE-GGV-CONTENT",
        permission_code="approval.decide",
        effective_from=iso_now(delta_days=2),
        effective_to=iso_now(delta_days=10),
    )
    check("future create SCHEDULED", d_future["status"] == "SCHEDULED", str(d_future.get("status")))
    ev6 = dlg.evaluate_delegation("PERS-HAIKAL", "approval.decide", {"entity_id": "ENT-GGV"})
    # May find the ACTIVE spend one? approval.decide different code — should deny (scheduled)
    # But there may be no ACTIVE approval.decide yet
    check("6 before effective_from → denied", not ev6.get("allowed"), str(ev6.get("reason")))

    # 7. after effective_to → expired denied
    d_past = dlg.create_delegation(
        verified_person_id="PERS-MATT",
        delegate_person_id="PERS-MISA",
        delegator_assignment_id="ASG-MATT-OWNER-1",
        delegate_assignment_id="ASG-MISA-CC-1",
        entity_id="ENT-GGV",
        scope_id="SCOPE-GGV-CONTENT",
        permission_code="approval.read",
        effective_from=iso_now(delta_days=-10),
        effective_to=iso_now(delta_days=5),
    )
    # Force expire by updating window then lazy
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        """
        UPDATE core_delegations
        SET effective_from=?, effective_to=?, status='ACTIVE'
        WHERE delegation_id=?
        """,
        (iso_now(delta_days=-10), iso_now(delta_days=-1), d_past["delegation_id"]),
    )
    c.commit()
    c.close()
    got = dlg.get_delegation(d_past["delegation_id"])
    check("7 after effective_to → EXPIRED", got and got["status"] == "EXPIRED", str(got))
    ev7 = dlg.evaluate_delegation("PERS-MISA", "approval.read", {"entity_id": "ENT-GGV"})
    check("7 expired evaluate denied", not ev7.get("allowed"), str(ev7.get("reason")))

    # 8. revoked → denied
    dlg.revoke_delegation(did, verified_person_id="PERS-MATT", reason="test revoke")
    ev8 = dlg.evaluate_delegation(
        "PERS-HAIKAL", CODE_SPEND, {"entity_id": "ENT-GGV"}, {"amount": "100", "currency": "IDR"}
    )
    check("8 revoked → denied", not ev8.get("allowed"), str(ev8.get("reason")))
    # Recreate active spend delegation for later tests
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

    # 9. delegator inactive Assignment → evaluate denied
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        "UPDATE org_assignments SET status='INACTIVE' WHERE assignment_id='ASG-MATT-OWNER-1'"
    )
    c.commit()
    c.close()
    ev9 = dlg.evaluate_delegation(
        "PERS-HAIKAL", CODE_SPEND, {"entity_id": "ENT-GGV"}, {"amount": "100", "currency": "IDR"}
    )
    check("9 delegator inactive Assignment → denied", not ev9.get("allowed"), str(ev9.get("reason")))
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        "UPDATE org_assignments SET status='ACTIVE' WHERE assignment_id='ASG-MATT-OWNER-1'"
    )
    c.commit()
    c.close()

    # 10. forged delegate id refused (client cannot set verified as someone else via create body)
    # create with verified Matt but we check evaluate uses authentic person
    # "delegate remains real authenticated Person" — create with fake person id
    denied10 = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-MATT",
            delegate_person_id="PERS-FAKE-SPOOF",
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id="ASG-HAIKAL-VE-1",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied10 = e.code in ("inactive_assignment", "unknown_person")
    check("10 forged delegate id refused", denied10)

    # 11. no identity impersonation — covered in approval decision actor = delegate below
    # 12. client cannot forge delegator
    denied12 = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-HAIKAL",
            delegator_person_id="PERS-MATT",
            delegate_person_id="PERS-MISA",
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id="ASG-MISA-CC-1",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied12 = e.code in ("forged_delegator", "rbac_denied", "create_forbidden")
    check("12 client cannot forge delegator", denied12)

    # 13. client cannot forge delegate — when Haikal tries to create naming someone else as self?
    # Spec: "client cannot forge delegate" — typically means HTTP ignores client spoof of
    # identity. Here: Matt creates with mismatched assignment/person.
    denied13 = False
    try:
        dlg.create_delegation(
            verified_person_id="PERS-MATT",
            delegate_person_id="PERS-HAIKAL",
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id="ASG-MISA-CC-1",  # Misa's assignment, not Haikal
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-CONTENT",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied13 = e.code == "inactive_assignment"
    check("13 client cannot forge delegate (assignment mismatch)", denied13)

    # 14. cannot delegate more Authority than held
    denied14 = False
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
            delegated_cap_amount="999999999",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied14 = e.code == "authority_exceeded"
    check("14 cannot delegate more Authority than held", denied14)

    # 15. delegated cap enforced
    ev15 = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"},
        {"amount": "1500000", "currency": "IDR"},
    )
    check("15 delegated cap enforced (deny above)", not ev15.get("allowed"), str(ev15.get("reason")))
    ev15b = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"},
        {"amount": "500000", "currency": "IDR"},
    )
    check("15b within delegated cap allowed", ev15b.get("allowed"), str(ev15b))

    # 16. delegator Authority expiry/invalid → evaluate denies
    c = sqlite3.connect(str(tmp_db))
    c.execute("UPDATE org_authority_limits SET status='inactive' WHERE authority_limit_id='ALIM-TMP-DLG-MATT'")
    c.commit()
    c.close()
    ev16 = dlg.evaluate_delegation(
        "PERS-HAIKAL",
        CODE_SPEND,
        {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"},
        {"amount": "100", "currency": "IDR"},
    )
    check("16 delegator Authority invalid → deny", not ev16.get("allowed"), str(ev16.get("reason")))
    c = sqlite3.connect(str(tmp_db))
    c.execute("UPDATE org_authority_limits SET status='active' WHERE authority_limit_id='ALIM-TMP-DLG-MATT'")
    c.commit()
    c.close()

    # 17. re-delegation denied
    denied17 = False
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
            delegated_cap_amount="100",
            currency="IDR",
            allow_redelegation=1,
        )
    except dlg.DelegationError as e:
        denied17 = e.code == "redelegation_denied"
    check("17 re-delegation denied (allow_redelegation=1)", denied17)

    # Also: Haikal cannot create further grant of spend (lacks native RBAC —
    # even with delegation.create + entity-covering scope, power is not re-delegable)
    denied17b = False
    c = sqlite3.connect(str(tmp_db))
    c.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-GGV-EDIT', 'PERM-DELEGATION-CREATE', 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    # Bind entity-wide scope so create RBAC WHERE passes; WHAT (spend) still native-denied
    c.execute(
        """
        INSERT OR IGNORE INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES ('ASG-HAIKAL-VE-1', 'SCOPE-GGV-ALL', ?, NULL, 'ACTIVE', ?, ?)
        """,
        (TS, TS, TS),
    )
    c.commit()
    c.close()
    try:
        dlg.create_delegation(
            verified_person_id="PERS-HAIKAL",
            delegate_person_id="PERS-MISA",
            delegator_assignment_id="ASG-HAIKAL-VE-1",
            delegate_assignment_id="ASG-MISA-CC-1",
            entity_id="ENT-GGV",
            scope_id="SCOPE-GGV-ALL",
            permission_code=CODE_SPEND,
            effective_from=ef,
            effective_to=et,
            delegated_cap_amount="100",
            currency="IDR",
        )
    except dlg.DelegationError as e:
        denied17b = e.code == "delegator_lacks_permission"
        if not denied17b:
            print(f"  17b detail: {e.code}: {e}")
    check("17b cannot re-delegate via delegated power", denied17b)

    # 18–21 approval through delegation
    # Amanda creates request; Haikal decides via delegation
    c = sqlite3.connect(str(tmp_db))
    for pid in ("PERM-APPROVAL-REQUEST", "PERM-APPROVAL-READ"):
        c.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-CONTENT-MGMT', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
            """,
            (pid, TS, TS),
        )
    c.commit()
    c.close()

    req = apr.create_approval_request(
        title="Delegate spend",
        owning_entity_id="ENT-GGV",
        department_id="DEPT-GGV-CONTENT",
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="500000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    rid = req["approval_request_id"]
    check("approval request PENDING", req["status"] == "PENDING")

    result = apr.approve_request(rid, verified_person_id="PERS-HAIKAL")
    check("18 approval through valid delegation succeeds", result.get("ok") is True, str(result)[:200])
    decision = result.get("decision") or {}
    check(
        "11/20 decision actor = actual delegate",
        decision.get("decided_by_person_id") == "PERS-HAIKAL",
        str(decision.get("decided_by_person_id")),
    )
    check(
        "20 Approval Decision DELEGATION basis",
        decision.get("authority_basis_type") == "DELEGATION"
        and bool(decision.get("authority_basis_delegation_id")),
        str(decision),
    )

    # 19 above delegated cap denied
    req2 = apr.create_approval_request(
        title="Over cap",
        owning_entity_id="ENT-GGV",
        department_id="DEPT-GGV-CONTENT",
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="2000000",
        currency="IDR",
        verified_person_id="PERS-AMANDA",
        requested_by_assignment_id="ASG-AMANDA-CM-1",
    )
    denied19 = False
    try:
        apr.approve_request(req2["approval_request_id"], verified_person_id="PERS-HAIKAL")
    except apr.ApprovalError as e:
        denied19 = e.code in ("authority_denied", "required_permission_denied")
    check("19 approval above delegated cap denied", denied19)

    # 21 self-approval not bypassed via delegation
    req3 = apr.create_approval_request(
        title="Self launder",
        owning_entity_id="ENT-GGV",
        department_id="DEPT-GGV-CONTENT",
        required_permission_code=CODE_SPEND,
        request_type="SPEND",
        material_amount="100000",
        currency="IDR",
        verified_person_id="PERS-HAIKAL",
        requested_by_assignment_id="ASG-HAIKAL-VE-1",
    )
    # Grant Haikal approval.request temporarily for create above — may have failed
    # If create failed, seed via Matt as requester then... self means requester==decider
    if req3.get("approval_request_id"):
        denied21 = False
        try:
            apr.approve_request(req3["approval_request_id"], verified_person_id="PERS-HAIKAL")
        except apr.ApprovalError as e:
            denied21 = e.code == "self_approval_denied"
        check("21 delegation does not bypass self-approval", denied21)
    else:
        # create may fail without approval.request — grant and retry
        c = sqlite3.connect(str(tmp_db))
        c.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-GGV-EDIT', 'PERM-APPROVAL-REQUEST', 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
            """,
            (TS, TS),
        )
        c.commit()
        c.close()
        req3 = apr.create_approval_request(
            title="Self launder",
            owning_entity_id="ENT-GGV",
            department_id="DEPT-GGV-CONTENT",
            required_permission_code=CODE_SPEND,
            request_type="SPEND",
            material_amount="100000",
            currency="IDR",
            verified_person_id="PERS-HAIKAL",
            requested_by_assignment_id="ASG-HAIKAL-VE-1",
        )
        denied21 = False
        try:
            apr.approve_request(req3["approval_request_id"], verified_person_id="PERS-HAIKAL")
        except apr.ApprovalError as e:
            denied21 = e.code == "self_approval_denied"
        check("21 delegation does not bypass self-approval", denied21)

    # DLG-RT-001: forged PENDING SPEND with NULL amount + valid delegation → APPROVE denied
    c = sqlite3.connect(str(tmp_db))
    forge_id = "APR-DLG-FORGE-NULL-AMT"
    forge_ts = "2026-09-17T02:00:00Z"
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
          ?, 'SPEND', 'forged null amount via dlg', NULL,
          'ENT-GGV', NULL, NULL, 'DEPT-GGV-CONTENT',
          'PERS-AMANDA', 'ASG-AMANDA-CM-1',
          ?, ?,
          NULL, NULL, 'HUMAN', NULL,
          NULL, 'PENDING', ?, NULL, NULL,
          ?, ?, 'CORR-DLG-FORGE-NULL', NULL,
          NULL, 'dlg-forge-null-amt'
        )
        """,
        (forge_id, CODE_SPEND, PERM_SPEND, forge_ts, forge_ts, forge_ts),
    )
    c.commit()
    c.close()
    null_amt_denied = False
    null_amt_code = None
    try:
        apr.approve_request(forge_id, verified_person_id="PERS-HAIKAL", reason="should deny")
    except apr.ApprovalError as e:
        null_amt_code = e.code
        null_amt_denied = e.code == "missing_amount"
    forged_row = apr.get_approval_request(forge_id)
    check(
        "DLG-RT-001 forge NULL-amount SPEND via delegation → missing_amount; stays PENDING",
        null_amt_denied and forged_row and forged_row["status"] == "PENDING",
        f"code={null_amt_code} status={forged_row.get('status') if forged_row else None}",
    )

    # 22 audit provenance
    created_ev = audit.list_events(action="delegation.created", source="delegation", limit=20)
    used_ev = audit.list_events(action="delegation.used", source="delegation", limit=20)
    denied_ev = audit.list_events(action="delegation.denied", source="delegation", limit=20)
    revoked_ev = audit.list_events(action="delegation.revoked", source="delegation", limit=20)
    check("22 audit created", len(created_ev) >= 1)
    check("22 audit used", len(used_ev) >= 1)
    check("22 audit denied", len(denied_ev) >= 1)
    check("22 audit revoked", len(revoked_ev) >= 1)

    # 24 live audit unchanged by tests
    audit_live_after = live_counts()[1]
    check(
        "24 live audit count unchanged by tests",
        audit_live_after == audit_live_before_mut == audit_before,
        f"before={audit_before} mid={audit_live_before_mut} after={audit_live_after}",
    )
    auth_final, _, dlg_final = live_counts()
    check("23b live auth still 0 end", auth_final == 0)
    check("25b live delegations still 0 end", dlg_final == 0)

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
