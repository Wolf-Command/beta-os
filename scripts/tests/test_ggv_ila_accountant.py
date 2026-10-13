#!/usr/bin/env python3
"""ILA GGV external accountant: one identity, GGV only, no posting."""
from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import audit as audit  # noqa: E402
from core import ggv_finance_nota as nota  # noqa: E402
from core import ggv_ila_accountant as ila  # noqa: E402
from core import identity as identity  # noqa: E402
from core import rbac as rbac  # noqa: E402

PASS = 0
FAIL = 0
DB = ROOT / "state" / "beta-os-ila-test" / "catalog.sqlite"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def bootstrap() -> None:
    if DB.parent.exists():
        shutil.rmtree(DB.parent)
    DB.parent.mkdir(parents=True)
    conn = connect()
    try:
        for name in (
            "005_org_registry.sql",
            "006_person_auth_identity.sql",
            "007_role_position_assignment.sql",
            "008_assignment_scope.sql",
            "009_rbac_permissions.sql",
            "011_audit_evidence_spine.sql",
        ):
            conn.executescript((ROOT / "scripts" / "migrations" / name).read_text(encoding="utf-8"))
        ts = "2026-10-13T00:00:00Z"
        conn.execute(
            """
            INSERT INTO org_entities (
              entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
            ) VALUES ('ENT-GGV', 'PT Goss Group Ventures', 'GGV', 'company', 'ACTIVE', 1, ?, ?),
                     ('ENT-AMG', 'Atrium', 'AMG', 'company', 'ACTIVE', 1, ?, ?),
                     ('ENT-BZG', 'Blu Zone', 'BZG', 'company', 'ACTIVE', 1, ?, ?)
            """,
            (ts, ts, ts, ts, ts, ts),
        )
        for role_id, label in (
            ("ROLE-MATT", "Owner"),
            ("ROLE-CONTENT-MGMT", "Content lead"),
        ):
            conn.execute(
                """
                INSERT INTO org_roles (
                  role_id, display_name, department_id, role_type, status, created_at, updated_at
                ) VALUES (?, ?, NULL, 'INTERNAL', 'ACTIVE', ?, ?)
                """,
                (role_id, label, ts, ts),
            )
        conn.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES ('PERS-CF-ONLY', 'Cloudflare only', 'Cloudflare only', 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status, is_primary, created_at, updated_at
            ) VALUES ('AUTH-CF-ONLY', 'PERS-CF-ONLY', 'cloudflare', 'nobody@example.test', 'ACTIVE', 1, ?, ?)
            """,
            (ts, ts),
        )
        nota.ensure_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ggv_invoices (
              invoice_id TEXT PRIMARY KEY,
              entity_id TEXT NOT NULL,
              customer_id TEXT NOT NULL,
              invoice_number TEXT,
              invoice_date TEXT NOT NULL,
              due_date TEXT,
              terms TEXT,
              currency TEXT NOT NULL,
              notes TEXT,
              reference TEXT,
              payment_method TEXT,
              payment_reference TEXT,
              lines_json TEXT NOT NULL,
              subtotal TEXT NOT NULL,
              tax_total TEXT NOT NULL,
              grand_total TEXT NOT NULL,
              rounding_json TEXT NOT NULL,
              status TEXT NOT NULL,
              number_source TEXT NOT NULL,
              created_by_person_id TEXT NOT NULL,
              finalised_by_person_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              issued_at TEXT,
              draft_email_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ggv_invoice_documents (
              document_id TEXT PRIMARY KEY,
              invoice_id TEXT NOT NULL,
              version INTEGER NOT NULL,
              sha256 TEXT NOT NULL,
              pdf BLOB NOT NULL,
              created_by_person_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ggv_invoices (
              invoice_id, entity_id, customer_id, invoice_number, invoice_date, currency,
              lines_json, subtotal, tax_total, grand_total, rounding_json, status,
              number_source, created_by_person_id, created_at, updated_at
            ) VALUES
              ('INV-GGV-1', 'ENT-GGV', 'CUST-1', '067A', '2026-09-12', 'IDR', '[]', '0', '0', '100', '{}', 'ISSUED', 'issued', 'PERS-MATT', ?, ?),
              ('INV-GGV-2', 'ENT-GGV', 'CUST-1', '068A', '2026-09-20', 'IDR', '[]', '0', '0', '50', '{}', 'ISSUED', 'issued', 'PERS-MATT', ?, ?),
              ('INV-AMG-1', 'ENT-AMG', 'CUST-9', 'AMG-1', '2026-09-12', 'IDR', '[]', '0', '0', '999', '{}', 'ISSUED', 'issued', 'PERS-MATT', ?, ?)
            """,
            (ts, ts, ts, ts, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO ggv_invoice_documents (
              document_id, invoice_id, version, sha256, pdf, created_by_person_id, created_at
            ) VALUES ('PDF-1', 'INV-GGV-1', 1, 'abc', ?, 'PERS-MATT', ?)
            """,
            (b"%PDF-1.4 original", ts),
        )
        conn.execute(
            """
            INSERT INTO ggv_notas (
              nota_id, entity_id, vendor_id, invoice_no, nota_date, currency, amount,
              workflow_state, created_by_person_id, created_at, updated_at
            ) VALUES ('NOTA-AUG', 'ENT-GGV', NULL, 'OLD', '2026-08-02', 'IDR', '10', 'needs_review', 'PERS-MATT', ?, ?)
            """,
            (ts, ts),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    for module in (nota, identity, rbac, audit, ila.nota):
        module.CATALOG_DB = DB
    bootstrap()
    html = (ROOT / "dashboards" / "ggv-finance.html").read_text(encoding="utf-8")
    check("accountant tab", 'data-tab="accountant"' in html)
    check("request documents control", "Request documents" in html)
    check("touch target", "min-height: var(--touch)" in html and "--touch: 44px" in html)
    check("viewport", 'name="viewport"' in html)
    check("no table layout on accountant", "<table" not in html)
    check("accountant path", "/ggv/finance/accountant" in html)

    conn = connect()
    try:
        seated = ila.seat_ila(conn)
        check("one identity", seated["identity_count"] == 1 and seated["ok"] is True, str(seated))
        person_id = seated["person_id"]
        again = ila.seat_ila(conn)
        check("seat is reused", again["person_id"] == person_id and again["created_person"] is False)
        resolved = identity.resolve_verified_person(ila.ILA_EMAIL, conn=conn)
        emailed = identity.resolve_person_from_email(ila.ILA_EMAIL, conn=conn)
        check("cloudflare resolve", resolved.get("ok") is True and resolved.get("person_id") == person_id)
        check("email resolve matches", emailed is not None and emailed["person_id"] == person_id)
        people = conn.execute(
            """
            SELECT COUNT(DISTINCT person_id) FROM org_auth_identities
            WHERE lower(identifier)=?
            """,
            (ila.ILA_EMAIL,),
        ).fetchone()[0]
        check("email is one person", people == 1, str(people))

        allowed = {
            "finance.records.read": True,
            "finance.recon.review": True,
            "finance.evidence.read": True,
            "finance.history.read": True,
            "finance.journal.propose": True,
            "finance.report.export": True,
            "finance.document.request": True,
            "finance.filing.record": True,
            "finance.invoice.read": True,
            "finance.journal.post": False,
            "payment.approve": False,
            "payment.execute": False,
            "vendor.bank.change": False,
            "finance.policy.admin": False,
            "atrium.journal.post": False,
            "organisation.person.write": False,
            "organisation.role.write": False,
        }
        for code, expect in allowed.items():
            got = rbac.can(person_id, code, {"entity_id": "ENT-GGV"}, conn=conn)
            check(f"perm {code}", got is expect, str(got))
        check(
            "GGV scope does not open AMG",
            rbac.can(person_id, "finance.records.read", {"entity_id": "ENT-AMG"}, conn=conn) is False,
        )
        check(
            "GGV scope does not open BZG",
            rbac.can(person_id, "finance.records.read", {"entity_id": "ENT-BZG"}, conn=conn) is False,
        )
        check(
            "cloudflare without a seat is not an accountant",
            rbac.can("PERS-CF-ONLY", "finance.records.read", {"entity_id": "ENT-GGV"}, conn=conn) is False,
        )

        before_date = conn.execute("SELECT nota_date FROM ggv_notas WHERE nota_id='NOTA-AUG'").fetchone()[0]
        invoice_count = conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0]
        desk = ila.dashboard(person_id, conn)
        after_date = conn.execute("SELECT nota_date FROM ggv_notas WHERE nota_id='NOTA-AUG'").fetchone()[0]
        check("historical nota unchanged", before_date == after_date == "2026-08-02")
        check("no invented invoice", conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0] == invoice_count)
        queue = desk["finance_review_queue"]
        check("september ready", queue["status"] == "READY_FOR_REVIEW" and queue["period"] == "2026-09")
        check("five exceptions", len(queue["exceptions"]) == 5 and queue["unresolved_count"] == 5, str(queue["unresolved_count"]))
        periods = {row["period"]: row["status"] for row in desk["accounting_status"]["periods"]}
        check("september period stored", periods.get("2026-09") == "READY_FOR_REVIEW")
        check("august is visible", "2026-08" in periods)
        check("books not final", desk["accounting_status"]["books"]["books_final"] is False)
        check("no automatic filing", desk["automatic_filing"] is False and desk["automatic_payment"] is False)
        missing = desk["original_invoice_pdfs"]["missing"]
        check(
            "missing original named",
            any(item["invoice_id"] == "INV-GGV-2" for item in missing),
            str(missing),
        )
        check(
            "AMG invoice not in the missing list",
            all(item["invoice_id"] != "INV-AMG-1" for item in missing),
        )
        linked = conn.execute(
            "SELECT source_id FROM ggv_accountant_evidence_links WHERE invoice_id='INV-GGV-1'"
        ).fetchone()
        check("existing pdf linked", linked is not None and linked[0] == "INV-GGV-1")
        tax = desk["tax_compliance"]
        check("npwp unknown", tax["profile"]["npwp"] is None and tax["profile"]["pkp_status"] == "UNKNOWN")
        check("no invented liability", all(row["calculation"] is None and row["liability_invented"] is False for row in tax["obligations"]))
        check("format not claimed", all(row["compatibility_claimed"] is False for row in tax["obligations"]))

        try:
            ila.dashboard("PERS-CF-ONLY", conn)
            check("unseated cloudflare denied", False)
        except nota.FinanceNotaError as exc:
            check("unseated cloudflare denied", exc.http_status == 403)

        try:
            ila.export_register(person_id, "invoices-ar", {"period": ["2026-09"], "entity": ["ENT-AMG"], "format": ["csv"]}, conn)
            check("AMG export denied", False)
        except nota.FinanceNotaError as exc:
            check("AMG export denied", exc.http_status == 403)

        exported = ila.export_register(person_id, "invoices-ar", {"period": ["2026-09"], "format": ["csv"]}, conn)
        text = exported["_file"]["data"].decode("utf-8")
        check("export names the company", "PT Goss Group Ventures" in text and "IDR" in text)
        check("export includes GGV invoice", "INV-GGV-1" in text and "067A" in text)
        check("export hides AMG", "INV-AMG-1" not in text and "AMG-1" not in text)
        ledger = ila.export_register(person_id, "general-ledger", {"period": ["2026-09"], "format": ["csv"]}, conn)
        ledger_text = ledger["_file"]["data"].decode("utf-8")
        check("ledger is a gap", "not_available" in ledger_text and "books_final" in ledger_text)
        check("ledger is not a profit statement", "Net profit" not in ledger_text)
        xlsx = ila.export_register(person_id, "tax-schedules", {"period": ["2026-09"], "format": ["xlsx"]}, conn)
        check("xlsx is a workbook", xlsx["_file"]["data"][:2] == b"PK")
        with zipfile.ZipFile(io.BytesIO(xlsx["_file"]["data"])) as archive:
            sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        check("tax workbook has no liability figure", "PPh21" in sheet and "NOT_VERIFIED" in sheet)

        decided = ila.decide_review(
            person_id,
            "GGV-2026-09-EX-01",
            {"decision": "approve", "note": "Reconciliation reviewed. No posting."},
            conn,
        )
        check("decision recorded", decided["decision"] == "APPROVED" and decided["journal_posted"] is False)
        check("decision history", decided["history"][0]["actor_person_id"] == person_id)
        ila._preserve_september(conn, person_id)
        conn.commit()
        kept = conn.execute(
            "SELECT status FROM ggv_accountant_review_items WHERE item_id='GGV-2026-09-EX-01'"
        ).fetchone()[0]
        check("decision not rewritten", kept == "APPROVED")
        period = conn.execute(
            "SELECT status FROM ggv_accountant_periods WHERE period_id='2026-09'"
        ).fetchone()[0]
        check("period stays ready", period == "READY_FOR_REVIEW")
        audit_rows = conn.execute(
            "SELECT action FROM core_audit_events WHERE resource_id='GGV-2026-09-EX-01'"
        ).fetchall()
        check("audit written", any(row[0] == "ggv.accountant.review" for row in audit_rows))

        requested = ila.request_document(
            person_id,
            {
                "missing_item": "Original PDF for 068A",
                "period": "2026-09",
                "reason": "Issued invoice has no stored PDF.",
                "responsible_label": "GGV Finance",
            },
            conn,
        )
        check("document request open", requested["status"] == "OPEN" and requested["entity_id"] == "ENT-GGV")
        proposed = ila.propose_journal(
            person_id,
            {"memo": "Accrual to review", "lines": [{"description": "Debit expense"}], "period": "2026-09"},
            conn,
        )
        check("proposal not posted", proposed["posted"] is False and proposed["status"] == "AWAITING_MANAGEMENT")
        try:
            ila.record_filing(person_id, {"tax_code": "PPh23", "file_now": True}, conn)
            check("government filing refused", False)
        except nota.FinanceNotaError as exc:
            check("government filing refused", exc.http_status == 403)

        original = ila.invoice_original(person_id, "INV-GGV-1", conn)
        check("original pdf bytes", original["_file"]["data"].startswith(b"%PDF"))
        try:
            ila.invoice_original(person_id, "INV-AMG-1", conn)
            check("AMG pdf denied", False)
        except nota.FinanceNotaError as exc:
            check("AMG pdf denied", exc.http_status == 403)

        try:
            ila.http(
                "POST",
                "/accountant/journal-proposals/JPR-1/post",
                {},
                {},
                person_id,
            )
            check("post route refused", False, "expected exception")
        except nota.FinanceNotaError as exc:
            check("post route refused", exc.http_status == 403, str(exc))
    finally:
        conn.close()

    try:
        pay = ila.http("POST", "/accountant/payments", {}, {}, person_id)
        check("payment route refused", False, str(pay)[:120])
    except nota.FinanceNotaError as exc:
        check("payment route refused", exc.http_status == 403)

    dup = connect()
    try:
        ts = "2026-10-13T00:00:00Z"
        dup.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES ('PERS-OTHER', 'Other', 'Other', 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        dup.execute(
            "DELETE FROM org_auth_identities WHERE lower(identifier)=?",
            (ila.ILA_EMAIL,),
        )
        dup.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status, is_primary, created_at, updated_at
            ) VALUES ('AUTH-DUP-EMAIL', ?, 'email', ?, 'ACTIVE', 1, ?, ?),
                     ('AUTH-DUP-CF', 'PERS-OTHER', 'cloudflare', ?, 'ACTIVE', 1, ?, ?)
            """,
            (person_id, ila.ILA_EMAIL, ts, ts, ila.ILA_EMAIL, ts, ts),
        )
        dup.commit()
        try:
            ila.seat_ila(dup)
            check("duplicate identity refused", False)
        except nota.FinanceNotaError as exc:
            check("duplicate identity refused", exc.code == "duplicate_identity")
        still = dup.execute(
            "SELECT COUNT(*) FROM org_persons WHERE person_id='PERS-ILA-DUP'"
        ).fetchone()[0]
        check("no third person created", still == 0)
    finally:
        dup.close()

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
