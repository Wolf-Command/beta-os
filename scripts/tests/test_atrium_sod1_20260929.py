#!/usr/bin/env python3
"""ATRIUM-SOD-1B — AP/AR seats, SoD by preparer_person_id, live-store pollution guard.

Decision: Matt APPROVED ATRIUM-SOD-1; UPDATE 29 Sep 14:10 (real AP/AR staffing).
"""
from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import atrium_fc_authority as fc  # noqa: E402
from core import atrium_historical as hist  # noqa: E402
from core import rbac  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_access import (  # noqa: E402
    AP_ASSIGNMENT,
    AP_EMAIL,
    AP_PERSON,
    AP_POSITION,
    ROLE_ATRIUM_AP,
    ROLE_ATRIUM_AR,
    ROLE_ATRIUM_FINANCE,
    ROLE_ATRIUM_FINANCIAL_CONTROLLER,
    ZAYEN_AR_ASSIGNMENT,
    ZAYEN_PERSON,
)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
PASS = 0
FAIL = 0
_LIVE_JOURNAL_IDS_AT_START: set[str] | None = None
_LIVE_JOURNAL_COUNT_AT_START: int | None = None


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def _snapshot_live() -> None:
    global _LIVE_JOURNAL_IDS_AT_START, _LIVE_JOURNAL_COUNT_AT_START
    if not ATRIUM_DB.is_file():
        return
    a = sqlite3.connect(str(ATRIUM_DB))
    try:
        rows = a.execute("SELECT journal_id FROM journal_headers").fetchall()
        _LIVE_JOURNAL_IDS_AT_START = {r[0] for r in rows}
        _LIVE_JOURNAL_COUNT_AT_START = len(rows)
    finally:
        a.close()


def _temp_catalog():
    tmp = Path(tempfile.mkdtemp(prefix="tmp-atriumsod1b-", dir=str(ROOT / "state")))
    db = tmp / "catalog.sqlite"
    shutil.copy2(CATALOG, db)
    return tmp, db


def _temp_atrium() -> Path:
    d = Path(tempfile.mkdtemp(prefix="tmp-atriumsod1b-atrium-", dir=str(ROOT / "state")))
    path = d / "atrium.sqlite"
    a = sqlite3.connect(str(path))
    a.executescript(
        """
        CREATE TABLE journal_headers (
          journal_id TEXT PRIMARY KEY,
          journal_date TEXT NOT NULL,
          period TEXT NOT NULL,
          status TEXT NOT NULL,
          source_type TEXT NOT NULL,
          source_reference TEXT NOT NULL DEFAULT '',
          created_by TEXT NOT NULL DEFAULT '',
          approved_by TEXT NOT NULL DEFAULT '',
          posted_at TEXT NOT NULL DEFAULT '',
          reversal_of TEXT,
          preparer_person_id TEXT NOT NULL DEFAULT '',
          posted_by TEXT NOT NULL DEFAULT '',
          return_reason TEXT NOT NULL DEFAULT '',
          wolf_created INTEGER NOT NULL DEFAULT 0,
          historical_import INTEGER NOT NULL DEFAULT 0,
          verified INTEGER NOT NULL DEFAULT 0,
          archived_reason TEXT NOT NULL DEFAULT '',
          evidence_ref TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE journal_lines (
          journal_id TEXT NOT NULL,
          line_no INTEGER NOT NULL,
          account_code TEXT NOT NULL,
          department_code TEXT,
          debit REAL NOT NULL,
          credit REAL NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          PRIMARY KEY (journal_id, line_no)
        );
        CREATE TABLE system_settings (
          id INTEGER PRIMARY KEY,
          property_name TEXT,
          room_count INTEGER,
          base_currency TEXT,
          fiscal_year TEXT,
          period_lock_date TEXT,
          controller_name TEXT,
          wolf_cutover_date TEXT DEFAULT '2026-09-29'
        );
        INSERT INTO system_settings (id, property_name, room_count, base_currency)
        VALUES (1, '', 0, 'IDR');
        """
    )
    a.commit()
    a.close()
    return path


def _load_mig():
    p = ROOT / "scripts" / "migrations" / "migrate_atrium_sod1_20260929.py"
    sp = importlib.util.spec_from_file_location("migrate_atrium_sod1_20260929", p)
    mod = importlib.util.module_from_spec(sp)
    assert sp and sp.loader
    sp.loader.exec_module(mod)
    return mod


def test_seats_and_grants() -> None:
    c = wi.db_connect(CATALOG)
    try:
        active = c.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE position_id='POS-AMG-FINANCE-OFFICER-1' AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchone()
        check("Finance Officer seat VACANT", active is None, str(active))
        fo = c.execute(
            "SELECT role_id FROM org_roles WHERE role_id=?", (ROLE_ATRIUM_FINANCE,)
        ).fetchone()
        check("ROLE-AMG-FINANCE-OFFICER exists", fo is not None)

        ap_role = c.execute(
            "SELECT display_name FROM org_roles WHERE role_id=?", (ROLE_ATRIUM_AP,)
        ).fetchone()
        check(
            "ROLE-AMG-ACCOUNTS-PAYABLE exists",
            ap_role is not None and ap_role[0] == "Accounts Payable",
            str(ap_role),
        )
        ar_role = c.execute(
            "SELECT display_name FROM org_roles WHERE role_id=?", (ROLE_ATRIUM_AR,)
        ).fetchone()
        check(
            "ROLE-AMG-ACCOUNTS-RECEIVABLE exists",
            ar_role is not None and ar_role[0] == "Accounts Receivable",
            str(ar_role),
        )

        ap = c.execute(
            """
            SELECT p.person_id, p.display_name, p.legal_name, a.identifier, a.status
            FROM org_persons p
            JOIN org_auth_identities a ON a.person_id=p.person_id
            WHERE a.provider='email' AND lower(a.identifier)=?
            """,
            (AP_EMAIL.lower(),),
        ).fetchone()
        check("AP person bound to email", ap is not None and ap[0] == AP_PERSON, str(ap))
        check("AP AuthIdentity ACTIVE", ap is not None and ap[4] == "ACTIVE", str(ap))
        check("AP legal_name NULL (not invented)", ap is not None and ap[2] is None, str(ap))
        asg = c.execute(
            """
            SELECT assignment_id, position_id, status FROM org_assignments
            WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (AP_ASSIGNMENT,),
        ).fetchone()
        check(
            "AP assignment ACTIVE on AP position",
            asg is not None and asg[1] == AP_POSITION,
            str(asg),
        )

        ar_asg = c.execute(
            """
            SELECT assignment_id, person_id, position_id, is_primary FROM org_assignments
            WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (ZAYEN_AR_ASSIGNMENT,),
        ).fetchone()
        check(
            "Zayen temp AR assignment ACTIVE",
            ar_asg is not None and ar_asg[1] == ZAYEN_PERSON and ar_asg[3] == 0,
            str(ar_asg),
        )
        fc_asg = c.execute(
            """
            SELECT assignment_id, is_primary FROM org_assignments
            WHERE assignment_id='ASG-ZAYEN-FC-1' AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchone()
        check("Zayen FC assignment kept primary", fc_asg is not None and fc_asg[1] == 1, str(fc_asg))

        check(
            "FC has approve",
            rbac.can(ZAYEN_PERSON, "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "FC has post",
            rbac.can(ZAYEN_PERSON, "atrium.journal.post", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP can draft",
            rbac.can(AP_PERSON, "atrium.journal.draft", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP cannot approve",
            not rbac.can(AP_PERSON, "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP cannot post",
            not rbac.can(AP_PERSON, "atrium.journal.post", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP denied payment",
            not rbac.can(AP_PERSON, "payment.execute", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP denied bank",
            not rbac.can(AP_PERSON, "vendor.bank.change", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP denied admin",
            not rbac.can(AP_PERSON, "finance.policy.admin", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "AP denied other entity",
            not rbac.can(AP_PERSON, "atrium.board.read", {"entity_id": "ENT-GGV"}, conn=c),
        )
        # AR role itself (no person-only check) has no approve/post
        row = c.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id=? AND rp.effect='ALLOW' AND p.code IN (
              'atrium.journal.approve','atrium.journal.post'
            )
            """,
            (ROLE_ATRIUM_AR,),
        ).fetchall()
        check("AR role has no approve/post", len(row) == 0, str(row))
        row_ap = c.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id=? AND rp.effect='ALLOW' AND p.code IN (
              'atrium.journal.approve','atrium.journal.post'
            )
            """,
            (ROLE_ATRIUM_AP,),
        ).fetchall()
        check("AP role has no approve/post", len(row_ap) == 0, str(row_ap))
        row_fo = c.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id=? AND rp.effect='ALLOW' AND p.code IN (
              'atrium.journal.approve','atrium.journal.post'
            )
            """,
            (ROLE_ATRIUM_FINANCE,),
        ).fetchall()
        check("Officer role has no approve/post", len(row_fo) == 0, str(row_fo))
        check(
            "FC denied payment",
            not rbac.can(ZAYEN_PERSON, "payment.execute", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "FC denied bank",
            not rbac.can(ZAYEN_PERSON, "vendor.bank.change", {"entity_id": "ENT-AMG"}, conn=c),
        )
    finally:
        c.close()


def test_state_machine_and_sod_on_temp() -> None:
    tmp, db = _temp_catalog()
    atrium = _temp_atrium()
    try:
        c = wi.db_connect(db)
        mig = _load_mig()
        mig.grant_fc_post(c)
        # Seed AP person grants on temp via migrate role helper
        ts = mig._ts()
        mig.ensure_preparer_role(
            c,
            role_id=ROLE_ATRIUM_AP,
            display_name="Accounts Payable",
            position_id=AP_POSITION,
            position_label="Accounts Payable",
            ts=ts,
        )
        mig.ensure_preparer_role(
            c,
            role_id=ROLE_ATRIUM_AR,
            display_name="Accounts Receivable",
            position_id="POS-AMG-ACCOUNTS-RECEIVABLE-1",
            position_label="Accounts Receivable",
            ts=ts,
        )
        # Minimal AP person + assignment for rbac
        c.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES (?, 'zenitalfathan', NULL, 'ACTIVE', ?, ?)
            ON CONFLICT(person_id) DO NOTHING
            """,
            (AP_PERSON, ts, ts),
        )
        c.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(assignment_id) DO NOTHING
            """,
            (AP_ASSIGNMENT, AP_PERSON, AP_POSITION, ts, ts, ts),
        )
        from core.scope import upsert_assignment_scope
        from core.staff_access import SCOPE_AMG_FINANCE

        upsert_assignment_scope(c, AP_ASSIGNMENT, SCOPE_AMG_FINANCE, ts, ts)
        c.commit()

        a = sqlite3.connect(str(atrium))
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by, preparer_person_id
            ) VALUES ('JRN-T-AP', '2026-09-29', '2026-09', 'DRAFT', 'MANUAL', 'zenitalfathan', ?)
            """,
            (AP_PERSON,),
        )
        a.execute(
            """
            INSERT INTO journal_lines VALUES
              ('JRN-T-AP', 1, '1020', '100', 1000, 0, 'd'),
              ('JRN-T-AP', 2, '4000', '100', 0, 1000, 'c')
            """
        )
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by, preparer_person_id
            ) VALUES ('JRN-T-AR-SELF', '2026-09-29', '2026-09', 'SUBMITTED', 'MANUAL', 'Zayen AR', ?)
            """,
            (ZAYEN_PERSON,),
        )
        a.commit()
        a.close()

        # AP can validate/submit
        v = fc.validate_journal(AP_PERSON, "JRN-T-AP", wolf_conn=c, atrium_db=atrium)
        check("AP validate DRAFT→VALIDATED", v["journal"]["status"] == "VALIDATED")
        s = fc.submit_journal(AP_PERSON, "JRN-T-AP", wolf_conn=c, atrium_db=atrium)
        check("AP submit VALIDATED→SUBMITTED", s["journal"]["status"] == "SUBMITTED")

        # AP cannot approve/post
        ap_deny = False
        try:
            fc.approve_journal(AP_PERSON, "JRN-T-AP", wolf_conn=c, atrium_db=atrium)
        except fc.FcAuthorityError as exc:
            ap_deny = exc.http_status == 403
        check("AP cannot approve", ap_deny)

        # Cannot skip DRAFT → APPROVED
        a = sqlite3.connect(str(atrium))
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by, preparer_person_id
            ) VALUES ('JRN-T-SKIP', '2026-09-29', '2026-09', 'DRAFT', 'MANUAL', 'zenitalfathan', ?)
            """,
            (AP_PERSON,),
        )
        a.commit()
        a.close()
        skip = False
        try:
            fc.approve_journal(ZAYEN_PERSON, "JRN-T-SKIP", wolf_conn=c, atrium_db=atrium)
        except fc.FcAuthorityError as exc:
            skip = exc.code == "invalid_status"
        check("cannot skip to approve from DRAFT", skip)

        # Return requires reason
        no_reason = False
        try:
            fc.reject_journal(ZAYEN_PERSON, "JRN-T-AP", wolf_conn=c, note="", atrium_db=atrium)
        except fc.FcAuthorityError as exc:
            no_reason = exc.code == "reason_required"
        check("RETURN requires reason", no_reason)

        # FC approve others' AP prep
        appr = fc.approve_journal(
            ZAYEN_PERSON, "JRN-T-AP", wolf_conn=c, approver_name="Zayen", atrium_db=atrium
        )
        check("FC approve AP journal", appr["journal"]["status"] == "APPROVED")

        # Zayen-as-AR prepare then FC self-approve = 403
        self_ap = False
        try:
            fc.approve_journal(
                ZAYEN_PERSON,
                "JRN-T-AR-SELF",
                wolf_conn=c,
                approver_name="Zayen",
                atrium_db=atrium,
            )
        except fc.FcAuthorityError as exc:
            self_ap = exc.code == "sod_self_approve"
        check("Zayen FC cannot approve own AR prep", self_ap)

        posted = fc.post_journal(
            ZAYEN_PERSON, "JRN-T-AP", wolf_conn=c, poster_name="Zayen", atrium_db=atrium
        )
        check("FC post AP journal", posted["journal"]["status"] == "POSTED")

        # Self-post blocked
        a = sqlite3.connect(str(atrium))
        a.execute(
            "UPDATE journal_headers SET status='APPROVED', preparer_person_id=? WHERE journal_id='JRN-T-AR-SELF'",
            (ZAYEN_PERSON,),
        )
        a.commit()
        a.close()
        self_post = False
        try:
            fc.post_journal(
                ZAYEN_PERSON, "JRN-T-AR-SELF", wolf_conn=c, poster_name="Zayen", atrium_db=atrium
            )
        except fc.FcAuthorityError as exc:
            self_post = exc.code == "sod_self_post"
        check("Zayen FC cannot post own AR prep", self_post)

        # Return path
        a = sqlite3.connect(str(atrium))
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by, preparer_person_id
            ) VALUES ('JRN-T-RET', '2026-09-29', '2026-09', 'SUBMITTED', 'MANUAL', 'AP', ?)
            """,
            (AP_PERSON,),
        )
        a.commit()
        a.close()
        ret = fc.reject_journal(
            ZAYEN_PERSON,
            "JRN-T-RET",
            wolf_conn=c,
            note="fix lines",
            atrium_db=atrium,
        )
        check("return → RETURNED", ret["journal"]["status"] == "RETURNED")
        check("return reason stored", ret["journal"].get("return_reason") == "fix lines")

        a = sqlite3.connect(str(atrium))
        n = a.execute(
            "SELECT COUNT(*) FROM journal_workflow_audit WHERE journal_id='JRN-T-AP'"
        ).fetchone()[0]
        lines = a.execute(
            """
            SELECT COUNT(*) FROM journal_lines jl
            JOIN journal_headers j ON j.journal_id=jl.journal_id
            WHERE j.status='POSTED' AND j.journal_id='JRN-T-AP'
            """
        ).fetchone()[0]
        a.close()
        check("audit rows per transitions on AP", n >= 3, str(n))
        check("GL has posted lines for AP journal", lines == 2, str(lines))
    finally:
        c.close()
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(atrium.parent, ignore_errors=True)


def test_live_commission_and_archive() -> None:
    if not ATRIUM_DB.is_file():
        check("live atrium present", False, "missing")
        return
    a = sqlite3.connect(str(ATRIUM_DB))
    try:
        comm = a.execute(
            "SELECT status, preparer_person_id, wolf_created FROM journal_headers WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
        ).fetchone()
        check(
            "commissioning journal SUBMITTED by AP",
            comm is not None
            and comm[0] in {"SUBMITTED", "APPROVED", "POSTED"}
            and comm[1] == AP_PERSON,
            str(comm),
        )
        evid = a.execute(
            "SELECT COUNT(*) FROM journal_evidence WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
        ).fetchone()[0]
        check("commissioning evidence attached", evid >= 1, str(evid))
        for jid in ("JRN-MUM7ZLIY-746", "JRN-MULZIJ3N-117", "JRN-ATRIUMSOD1-COMM1"):
            st = a.execute(
                "SELECT status, archived_reason FROM journal_headers WHERE journal_id=?",
                (jid,),
            ).fetchone()
            check(
                f"{jid} archived as test artifact",
                st is not None
                and st[0] == "ARCHIVED"
                and "automated test artifact" in (st[1] or ""),
                str(st),
            )
    finally:
        a.close()


def test_historical_honest_empty() -> None:
    out = hist.gl_empty_state(ATRIUM_DB)
    check("historical model ok", out.get("ok") is True, str(out))
    check(
        "nothing authoritative imported",
        out.get("status") == "NOTHING_AUTHORITATIVE" and out.get("imported_rows") == 0,
        str(out),
    )
    msg = out.get("honest_empty_message") or ""
    check(
        "honest empty cites sources searched",
        "Sources searched" in msg or "sources searched" in msg.lower(),
        msg[:200],
    )
    check(
        "cutover date present",
        "2026-09-29" in (out.get("wolf_cutover_date") or ""),
        str(out.get("wolf_cutover_date")),
    )


def test_live_store_pollution_guard() -> None:
    """Suite must not add journals to live Beta store beyond pre-suite snapshot."""
    if not ATRIUM_DB.is_file():
        check("pollution guard atrium", False)
        return
    a = sqlite3.connect(str(ATRIUM_DB))
    try:
        after_ids = {r[0] for r in a.execute("SELECT journal_id FROM journal_headers").fetchall()}
        after_n = len(after_ids)
        if _LIVE_JOURNAL_COUNT_AT_START is not None:
            check(
                "live journal count unchanged by temp suite work",
                after_n == _LIVE_JOURNAL_COUNT_AT_START,
                f"before={_LIVE_JOURNAL_COUNT_AT_START} after={after_n}",
            )
        if _LIVE_JOURNAL_IDS_AT_START is not None:
            gained = after_ids - _LIVE_JOURNAL_IDS_AT_START
            check(
                "live store gained no new journals during suite",
                len(gained) == 0,
                f"gained={sorted(gained)}",
            )
        working = a.execute(
            """
            SELECT journal_id, status FROM journal_headers
            WHERE status IN ('DRAFT','VALIDATED','SUBMITTED','APPROVED','RETURNED')
            """
        ).fetchall()
        ids = {r[0] for r in working}
        check(
            "live working queue has AP commissioning (no test pollution)",
            "JRN-ATRIUMSOD1B-COMM1" in ids or len(ids) == 0,
            str(working),
        )
        check(
            "live working queue excludes MUM7ZLIY",
            "JRN-MUM7ZLIY-746" not in ids,
            str(working),
        )
    finally:
        a.close()


def test_my_work_items() -> None:
    c = wi.db_connect(CATALOG)
    try:
        for cap in (
            "COMM-ZAYEN-SOD-REVIEW",
            "COMM-ZAYEN-SOD-APPROVE",
            "COMM-ZAYEN-SOD-POST",
            "COMM-ZAYEN-SOD-GL",
            "COMM-ZAYEN-SOD-AR-TEMP",
        ):
            row = c.execute(
                """
                SELECT status FROM core_work_items
                WHERE commissioning_capability_id=? AND owner_person_id=?
                  AND status NOT IN ('CANCELLED')
                """,
                (cap, ZAYEN_PERSON),
            ).fetchone()
            check(f"My Work {cap}", row is not None, str(row))
        for cap in ("COMM-AP-SOD-PREPARE", "COMM-AP-SOD-SUBMIT"):
            row = c.execute(
                """
                SELECT routing_state, opened_at, status FROM core_work_items
                WHERE commissioning_capability_id=? AND owner_person_id=?
                  AND status NOT IN ('CANCELLED')
                """,
                (cap, AP_PERSON),
            ).fetchone()
            # ATRIUM-SOD-1C: Peaches activated after Matt CF confirm (no longer HELD).
            check(
                f"AP {cap} active after CF",
                row is not None
                and (row[0] is None or str(row[0]).strip() == "")
                and bool(row[1])
                and row[2] == "OPEN",
                str(row),
            )
        vacant = c.execute(
            """
            SELECT status FROM core_work_items
            WHERE commissioning_capability_id='COMM-OWNER-SOD-FO-VACANT'
              AND owner_person_id='PERS-MATT'
              AND status NOT IN ('CANCELLED')
            """
        ).fetchone()
        check("Owner FO-vacant item", vacant is not None)
        finding = c.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE commissioning_capability_id='FIND-ATRIUMSOD1-ZAYEN-PREPARER-SEAT'
            """
        ).fetchone()
        check("Zayen 13:32 finding recorded (history kept)", finding is not None)
        findings = (ROOT / "state" / "atrium-sod" / "findings.md").read_text(encoding="utf-8")
        check("findings.md keeps 13:32 text", "29 Sep 13:32" in findings)
        check("findings.md appends 1B update", "14:10" in findings or "SOD-1B" in findings)
    finally:
        c.close()


def test_flags_unchanged() -> None:
    from core.staff_home import build_home

    h = build_home(ZAYEN_PERSON)
    check("staff_ready false", h.get("staff_ready") is False)
    check("human_commissioned false", h.get("human_commissioned") is False)
    hap = build_home(AP_PERSON)
    check("AP staff_ready false", hap.get("staff_ready") is False)
    check("AP human_commissioned false", hap.get("human_commissioned") is False)


def test_ui_plain_titles() -> None:
    path = Path("/Users/wolfterminal/atrium-finance/server/betaMount.ts")
    text = path.read_text(encoding="utf-8")
    check("UI maps Accounts Payable title", "'Accounts Payable'" in text or '"Accounts Payable"' in text)
    check(
        "UI maps Accounts Receivable title",
        "'Accounts Receivable'" in text or '"Accounts Receivable"' in text,
    )
    check("UI has no raw ROLE code as seat title value for AP", "ROLE-AMG-ACCOUNTS-PAYABLE': 'Accounts Payable'" in text.replace('"', "'"))
    jw = Path("/Users/wolfterminal/atrium-finance/src/components/JournalWorkbenchView.tsx")
    jw_text = jw.read_text(encoding="utf-8")
    check("workbench SoD copy present", "segregation of duties" in jw_text.lower())


def main() -> int:
    print("=== ATRIUM-SOD-1B ===")
    _snapshot_live()
    test_seats_and_grants()
    test_state_machine_and_sod_on_temp()
    test_live_commission_and_archive()
    test_historical_honest_empty()
    test_live_store_pollution_guard()
    test_my_work_items()
    test_flags_unchanged()
    test_ui_plain_titles()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
