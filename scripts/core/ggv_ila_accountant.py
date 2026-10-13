#!/usr/bin/env python3
"""ILA Global Consulting — GGV external accountant workspace.

Reuses ROLE-GGV-EXTERNAL-ACCOUNTANT (GGV_EXTERNAL_ACCOUNTANT). Does not
create a second accounting application or a parallel document store.

Cloudflare Access proves who the person is. It does not grant accounting
authority. Every read, download, and export checks RBAC on ENT-GGV.

Wolf prepares records. ILA reviews and records filing evidence. Nothing
here posts a journal, moves money, or submits a return to DJP.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from core import ggv_finance_nota as nota
from core import identity as identity
from core import rbac as rbac

ROLE_CODE = "GGV_EXTERNAL_ACCOUNTANT"
ROLE_ID = nota.ROLE_EXTERNAL_ACCOUNTANT
POSITION_ID = nota.POSITION_EXTERNAL_ACCOUNTANT
SCOPE_ID = nota.SCOPE_GGV_FINANCE
ENTITY = "ENT-GGV"
COMPANY = "PT Goss Group Ventures"
CURRENCY = "IDR"

ILA_EMAIL = "tax.accounting@ilaglobalconsulting.com"
ILA_PERSON_ID = "PERS-ILA"
ILA_ASSIGNMENT_ID = "ASG-ILA-GGV-ACCT-1"
ILA_DISPLAY = "ILA Global Consulting"
SEPTEMBER = "2026-09"

# View and prepare. Never payment, user admin, or journal posting.
GRANT_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-FIN-RECORDS-READ", "finance.records.read", "finance.records", "read"),
    ("PERM-FIN-RECON-REVIEW", "finance.recon.review", "finance.recon", "review"),
    ("PERM-FIN-EVIDENCE-READ", "finance.evidence.read", "finance.evidence", "read"),
    ("PERM-FIN-HISTORY-READ", "finance.history.read", "finance.history", "read"),
    ("PERM-FIN-JOURNAL-PROPOSE", "finance.journal.propose", "finance.journal", "propose"),
    ("PERM-FIN-REPORT-EXPORT", "finance.report.export", "finance.report", "export"),
    ("PERM-FIN-DOC-REQUEST", "finance.document.request", "finance.document", "request"),
    ("PERM-FIN-FILING-RECORD", "finance.filing.record", "finance.filing", "record"),
    ("PERM-FIN-INV-READ", "finance.invoice.read", "finance.invoice", "read"),
    ("PERM-FIN-CUST-READ", "finance.customer.read", "finance.customer", "read"),
)

# Created so tests can prove they stay ungranted. Never ALLOWed here.
DENY_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-FIN-JOURNAL-POST", "finance.journal.post", "finance.journal", "post"),
    ("PERM-PAYMENT-APPROVE", "payment.approve", "payment", "approve"),
    ("PERM-PAYMENT-EXECUTE", "payment.execute", "payment", "execute"),
    ("PERM-VENDOR-BANK-CHANGE", "vendor.bank.change", "vendor.bank", "change"),
    ("PERM-FIN-POLICY-ADMIN", "finance.policy.admin", "finance.policy", "admin"),
    ("PERM-ATRIUM-JOURNAL-POST", "atrium.journal.post", "atrium.journal", "post"),
    ("PERM-ATRIUM-JOURNAL-APPROVE", "atrium.journal.approve", "atrium.journal", "approve"),
    ("PERM-ORG-PERSON-WRITE", "organisation.person.write", "organisation.person", "write"),
    ("PERM-ORG-ROLE-WRITE", "organisation.role.write", "organisation.role", "write"),
)

TAX_CODES: tuple[dict[str, str], ...] = (
    {"code": "PPh21", "label": "PPh 21 payroll withholding"},
    {"code": "PPh23", "label": "PPh 23 withholding and certificates"},
    {"code": "PPh42", "label": "PPh 4(2), where applicable"},
    {"code": "PPh25", "label": "PPh 25 and annual corporate income tax preparation"},
    {"code": "PPN", "label": "PPN/VAT and e-Faktur supporting records, where applicable"},
    {"code": "SPT", "label": "Annual corporate SPT preparation"},
    {"code": "FS", "label": "Financial statements and supporting schedules"},
)

# September bank reconciliation exceptions. These are the five unresolved
# GGV bank items. Missing invoices, unposted journals, and tax setup are
# preparation tasks and are not members of this list.
SEPTEMBER_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "item_id": "GGV-2026-09-EX-01",
        "counterparty": "Alfamart",
        "amount_idr": 64000,
        "title": "Alfamart Rp64,000",
        "kind": "bank_exception",
        "match_terms": ("ALFAMART",),
    },
    {
        "item_id": "GGV-2026-09-EX-02",
        "counterparty": "Blu Zone",
        "amount_idr": 15000000,
        "title": "Blu Zone Rp15,000,000",
        "kind": "bank_exception",
        "match_terms": ("BLU ZONE", "BLUZONE"),
    },
    {
        "item_id": "GGV-2026-09-EX-03",
        "counterparty": "Keen Eye",
        "amount_idr": 24875000,
        "title": "Keen Eye Rp24,875,000",
        "kind": "bank_exception",
        "match_terms": ("KEEN EYE", "KEENEYE"),
    },
    {
        "item_id": "GGV-2026-09-EX-04",
        "counterparty": "Canva",
        "amount_idr": 390000,
        "title": "Canva Rp390,000",
        "kind": "bank_exception",
        "match_terms": ("CANVA",),
    },
    {
        "item_id": "GGV-2026-09-EX-05",
        "counterparty": "ATM",
        "amount_idr": 2500000,
        "title": "ATM Rp2,500,000",
        "kind": "bank_exception",
        "match_terms": ("ATM",),
    },
)

REIMBURSEMENT_PEOPLE: tuple[dict[str, Any], ...] = (
    {"person_id": "PERS-MATT", "name": "Matt", "terms": ("MATT", "MATTHEW")},
    {"person_id": "PERS-AMANDA", "name": "Amanda", "terms": ("AMANDA",)},
)

EXPORTS: tuple[dict[str, str], ...] = (
    {"id": "general-ledger", "label": "General ledger", "formats": "csv,xlsx"},
    {"id": "trial-balance", "label": "Trial balance", "formats": "csv,xlsx"},
    {"id": "bank-register", "label": "Bank transactions and reconciliation", "formats": "csv,xlsx"},
    {"id": "invoices-ar", "label": "Customer invoices and accounts receivable", "formats": "csv,xlsx"},
    {"id": "bills-ap", "label": "Supplier bills and accounts payable", "formats": "csv,xlsx"},
    {"id": "expenses", "label": "Expenses and notas", "formats": "csv,xlsx"},
    {"id": "reimbursements", "label": "Reimbursements and staff liabilities", "formats": "csv,xlsx"},
    {"id": "withholding", "label": "Withholding schedules and certificates", "formats": "csv,xlsx"},
    {"id": "tax-schedules", "label": "Tax-relevant revenue and expense schedules", "formats": "csv,xlsx"},
    {"id": "journals", "label": "Journal register and proposed adjustments", "formats": "csv,xlsx"},
    {"id": "audit", "label": "Audit trail, exceptions, and missing evidence", "formats": "csv,xlsx"},
    {"id": "evidence-pack", "label": "September evidence pack", "formats": "zip"},
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def _count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0] if row else 0)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ggv_accountant_periods (
          period_id TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          status TEXT NOT NULL,
          note TEXT,
          updated_at TEXT NOT NULL,
          updated_by TEXT,
          PRIMARY KEY (entity_id, period_id)
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_review_items (
          item_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          period_id TEXT NOT NULL,
          title TEXT NOT NULL,
          kind TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_decisions (
          decision_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          item_id TEXT NOT NULL,
          decision TEXT NOT NULL,
          note TEXT,
          actor_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_doc_requests (
          request_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          period_id TEXT,
          missing_item TEXT NOT NULL,
          reason TEXT NOT NULL,
          responsible_person_id TEXT,
          responsible_label TEXT,
          status TEXT NOT NULL,
          requested_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_journal_proposals (
          proposal_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          period_id TEXT,
          memo TEXT NOT NULL,
          lines_json TEXT NOT NULL,
          status TEXT NOT NULL,
          proposed_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          posted INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_filings (
          filing_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          tax_code TEXT NOT NULL,
          period_id TEXT,
          preparation_status TEXT NOT NULL,
          submission_reference TEXT,
          acknowledgement_note TEXT,
          evidence_ref TEXT,
          recorded_by TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_tax_profile (
          entity_id TEXT PRIMARY KEY,
          npwp TEXT,
          pkp_status TEXT NOT NULL,
          note TEXT,
          verified_by TEXT,
          verified_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ggv_accountant_evidence_links (
          link_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          period_id TEXT,
          invoice_id TEXT,
          source_kind TEXT NOT NULL,
          source_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )


def _upsert_perm(
    conn: sqlite3.Connection, perm_id: str, code: str, resource: str, action: str, ts: str
) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, f"GGV external accountant: {code}", ts, ts),
    )


def ensure_permissions(conn: sqlite3.Connection) -> None:
    """Grant the accountant role. Strip payment, posting, and user-admin codes."""
    ts = _now()
    if _table(conn, "org_roles"):
        existing = conn.execute(
            "SELECT role_id FROM org_roles WHERE role_id=?",
            (ROLE_ID,),
        ).fetchone()
        if existing is None:
            try:
                nota.ensure_rbac(conn, commit=False)
            except nota.FinanceNotaError:
                pass
    for perm_id, code, resource, action in GRANT_PERMS + DENY_PERMS:
        _upsert_perm(conn, perm_id, code, resource, action, ts)
    for perm_id, _code, _resource, _action in GRANT_PERMS:
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE_ID, perm_id, ts, ts),
        )
    deny_ids = [row[0] for row in DENY_PERMS]
    conn.execute(
        f"""
        DELETE FROM org_role_permissions
        WHERE role_id=? AND permission_id IN ({",".join("?" for _ in deny_ids)})
        """,
        (ROLE_ID, *deny_ids),
    )


def _people_for_email(conn: sqlite3.Connection, email: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT person_id FROM org_auth_identities
        WHERE provider IN ('email', 'cloudflare')
          AND lower(identifier)=?
        """,
        (email,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def seat_ila(conn: sqlite3.Connection) -> dict[str, Any]:
    """Bind the existing Cloudflare email to exactly one Person and the GGV seat.

    Does not create a second person when the email is already stored.
    Refuses when the same email is already on two people.
    """
    ensure_schema(conn)
    ensure_permissions(conn)
    email = ILA_EMAIL.lower()
    people = _people_for_email(conn, email)
    if len(people) > 1:
        raise nota.FinanceNotaError(
            "This email is already on more than one person. No duplicate was created.",
            code="duplicate_identity",
            http_status=409,
        )
    ts = _now()
    created_person = False
    if people:
        person_id = people[0]
    else:
        person_id = ILA_PERSON_ID
        created_person = True
        conn.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
            """,
            (person_id, ILA_DISPLAY, ILA_DISPLAY, ts, ts),
        )
    for provider, auth_id, primary in (
        ("cloudflare", "AUTH-ILA-CF", 1),
        ("email", "AUTH-ILA-EMAIL", 0),
    ):
        row = conn.execute(
            """
            SELECT auth_identity_id, person_id FROM org_auth_identities
            WHERE provider=? AND lower(identifier)=?
            """,
            (provider, email),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO org_auth_identities (
                  auth_identity_id, person_id, provider, identifier, status,
                  is_primary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """,
                (auth_id, person_id, provider, email, primary, ts, ts),
            )
        elif str(row[1]) != person_id:
            raise nota.FinanceNotaError(
                "This email is already on more than one person. No duplicate was created.",
                code="duplicate_identity",
                http_status=409,
            )
    occupied = conn.execute(
        """
        SELECT assignment_id, person_id FROM org_assignments
        WHERE position_id=? AND status='ACTIVE' AND end_at IS NULL AND is_primary=1
        """,
        (POSITION_ID,),
    ).fetchone()
    existing_asg = conn.execute(
        """
        SELECT assignment_id FROM org_assignments
        WHERE person_id=? AND position_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (person_id, POSITION_ID),
    ).fetchone()
    blocker = None
    if existing_asg is None:
        primary = 1
        if occupied is not None and str(occupied["person_id"]) != person_id:
            primary = 0
            blocker = "position_occupied"
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', ?, ?, ?)
            """,
            (ILA_ASSIGNMENT_ID, person_id, POSITION_ID, ts, primary, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
            """,
            (ILA_ASSIGNMENT_ID, SCOPE_ID, ts, ts, ts),
        )
    _preserve_september(conn, person_id)
    conn.commit()
    resolved = identity.resolve_verified_person(email, conn=conn)
    people_after = _people_for_email(conn, email)
    return {
        "ok": len(people_after) == 1 and resolved.get("ok") is True,
        "person_id": person_id,
        "email": email,
        "identity_count": len(people_after),
        "created_person": created_person,
        "reused_existing_person": not created_person,
        "role_id": ROLE_ID,
        "role_code": ROLE_CODE,
        "position_id": POSITION_ID,
        "scope_id": SCOPE_ID,
        "entity_id": ENTITY,
        "cloudflare_is_not_authorisation": True,
        "blocker": blocker,
    }


def _preserve_september(conn: sqlite3.Connection, actor: str) -> None:
    """September 2026 stays READY_FOR_REVIEW until a person records a decision.

    Existing review rows are left in place. Missing slots are inserted once.
    """
    ts = _now()
    current = conn.execute(
        """
        SELECT status FROM ggv_accountant_periods
        WHERE entity_id=? AND period_id=?
        """,
        (ENTITY, SEPTEMBER),
    ).fetchone()
    if current is None:
        conn.execute(
            """
            INSERT INTO ggv_accountant_periods (
              period_id, entity_id, status, note, updated_at, updated_by
            ) VALUES (?, ?, 'READY_FOR_REVIEW', ?, ?, ?)
            """,
            (
                SEPTEMBER,
                ENTITY,
                "September 2026 is ready for ILA review. Five bank exceptions stay unresolved until a recorded decision.",
                ts,
                actor,
            ),
        )
    for item in SEPTEMBER_ITEMS:
        found = conn.execute(
            "SELECT item_id, title, kind, status FROM ggv_accountant_review_items WHERE item_id=?",
            (item["item_id"],),
        ).fetchone()
        if found is None:
            conn.execute(
                """
                INSERT INTO ggv_accountant_review_items (
                  item_id, entity_id, period_id, title, kind, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (item["item_id"], ENTITY, SEPTEMBER, item["title"], item["kind"], ts),
            )
            continue
        decided = conn.execute(
            "SELECT COUNT(*) FROM ggv_accountant_decisions WHERE item_id=? AND entity_id=?",
            (item["item_id"], ENTITY),
        ).fetchone()[0]
        if decided or str(found["status"]) != "OPEN":
            continue
        if found["title"] != item["title"] or found["kind"] != item["kind"]:
            conn.execute(
                """
                UPDATE ggv_accountant_review_items
                SET title=?, kind=?
                WHERE item_id=? AND entity_id=? AND status='OPEN'
                """,
                (item["title"], item["kind"], item["item_id"], ENTITY),
            )


def _require(conn: sqlite3.Connection, person_id: str | None, code: str) -> None:
    if not nota.person_can(person_id, code, conn):
        raise nota.FinanceNotaError(
            "You do not have access to GGV accounting.",
            code="forbidden",
            http_status=403,
            extra={"required_permission": code},
        )


def _reject_other_entity(qs: dict[str, list[str]] | None, body: dict[str, Any] | None = None) -> None:
    wanted = ""
    if qs:
        wanted = ((qs.get("entity") or qs.get("entity_id") or [""])[0] or "").strip()
    if not wanted and body:
        wanted = str(body.get("entity_id") or body.get("entity") or "").strip()
    if wanted and wanted not in {ENTITY, "GGV"}:
        raise nota.FinanceNotaError(
            "This account only covers PT Goss Group Ventures.",
            code="forbidden",
            http_status=403,
        )


def _books_status() -> dict[str, Any]:
    """Read GGV books when the file is present. Never write a journal."""
    from core import entity_books as books

    path = books.BETA_DIR / books.ENTITY_FILES[ENTITY]
    if not path.is_file():
        return {
            "journals_posted": None,
            "general_ledger_available": False,
            "trial_balance_available": False,
            "profit_and_loss_available": False,
            "books_file_opened": False,
            "books_final": False,
            "note": (
                "The GGV books file was not opened in this runtime. "
                "A general ledger, trial balance, and profit and loss are not shown. "
                "GGV is an empty books shell until journals are posted."
            ),
        }
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        journals = 0
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='journal_headers'"
        ).fetchone():
            journals = int(conn.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0])
    finally:
        conn.close()
    available = journals > 0
    return {
        "journals_posted": journals,
        "general_ledger_available": available,
        "trial_balance_available": available,
        "profit_and_loss_available": available,
        "books_file_opened": True,
        "books_final": False,
        "note": (
            "Posted journals are on the GGV books file."
            if available
            else "GGV has zero posted journals. The general ledger, trial balance, and profit and loss are not final."
        ),
    }


def _live_snapshot(conn: sqlite3.Connection, period: str) -> dict[str, Any]:
    like = period + "%"
    bank_open = 0
    if _table(conn, "ggv_bank_transactions"):
        bank_open = _count(
            conn,
            """
            SELECT COUNT(*) FROM ggv_bank_transactions
            WHERE entity_id=? AND txn_date LIKE ?
              AND recon_status IN ('UNIDENTIFIED','NEEDS_RECEIPT','NEEDS_REVIEW')
            """,
            (ENTITY, like),
        )
    unclassified = 0
    if _table(conn, "ggv_receipt_accounting"):
        unclassified = _count(
            conn,
            """
            SELECT COUNT(*) FROM ggv_receipt_accounting
            WHERE entity_id=? AND COALESCE(created_at, '') LIKE ?
              AND (human_confirmed_json IS NULL OR human_confirmed_json='')
            """,
            (ENTITY, like),
        )
    invoices = 0
    invoices_missing_pdf = 0
    if _table(conn, "ggv_invoices"):
        invoices = _count(
            conn,
            """
            SELECT COUNT(*) FROM ggv_invoices
            WHERE entity_id=? AND COALESCE(invoice_date, created_at, '') LIKE ?
            """,
            (ENTITY, like),
        )
        if _table(conn, "ggv_invoice_documents"):
            invoices_missing_pdf = _count(
                conn,
                """
                SELECT COUNT(*) FROM ggv_invoices i
                WHERE i.entity_id=? AND COALESCE(i.invoice_date, i.created_at, '') LIKE ?
                  AND NOT EXISTS (
                    SELECT 1 FROM ggv_invoice_documents d WHERE d.invoice_id=i.invoice_id
                  )
                """,
                (ENTITY, like),
            )
        else:
            invoices_missing_pdf = invoices
    notas_missing = 0
    if _table(conn, "ggv_notas"):
        notas_missing = _count(
            conn,
            """
            SELECT COUNT(*) FROM ggv_notas n
            WHERE n.entity_id=? AND COALESCE(n.nota_date, n.created_at, '') LIKE ?
              AND NOT EXISTS (SELECT 1 FROM ggv_nota_files f WHERE f.nota_id=n.nota_id)
            """,
            (ENTITY, like),
        )
    open_requests = _count(
        conn,
        """
        SELECT COUNT(*) FROM ggv_accountant_doc_requests
        WHERE entity_id=? AND status='OPEN' AND (period_id=? OR period_id IS NULL)
        """,
        (ENTITY, period),
    )
    return {
        "period": period,
        "bank_rows_unreconciled": bank_open,
        "transactions_awaiting_classification": unclassified,
        "customer_invoices": invoices,
        "customer_invoices_missing_original_pdf": invoices_missing_pdf,
        "notas_missing_file": notas_missing,
        "open_document_requests": open_requests,
        "amounts_invented": False,
    }


def link_original_invoice_pdfs(conn: sqlite3.Connection, period: str = SEPTEMBER) -> dict[str, Any]:
    """Link invoice PDFs and nota files that already exist. Never insert an invoice."""
    ensure_schema(conn)
    linked = 0
    missing: list[dict[str, Any]] = []
    if not _table(conn, "ggv_invoices"):
        return {
            "ok": True,
            "linked": 0,
            "missing": [],
            "invoices_invented": 0,
            "note": "No GGV invoice table is in this catalog. No invoice rows were created.",
        }
    like = period + "%"
    rows = conn.execute(
        """
        SELECT invoice_id, invoice_number, invoice_date
        FROM ggv_invoices
        WHERE entity_id=? AND COALESCE(invoice_date, created_at, '') LIKE ?
        """,
        (ENTITY, like),
    ).fetchall()
    ts = _now()
    for row in rows:
        invoice_id = str(row["invoice_id"])
        number = str(row["invoice_number"] or "")
        has_pdf = False
        if _table(conn, "ggv_invoice_documents"):
            has_pdf = (
                conn.execute(
                    "SELECT 1 FROM ggv_invoice_documents WHERE invoice_id=? LIMIT 1",
                    (invoice_id,),
                ).fetchone()
                is not None
            )
        if has_pdf:
            link_id = f"LINK-PDF-{invoice_id}"
            conn.execute(
                """
                INSERT INTO ggv_accountant_evidence_links (
                  link_id, entity_id, period_id, invoice_id, source_kind, source_id, created_at
                ) VALUES (?, ?, ?, ?, 'invoice_pdf', ?, ?)
                ON CONFLICT(link_id) DO NOTHING
                """,
                (link_id, ENTITY, period, invoice_id, invoice_id, ts),
            )
            linked += 1
        else:
            missing.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_number": number or None,
                    "period": period,
                    "original_pdf": False,
                }
            )
        if number and _table(conn, "ggv_nota_files"):
            files = conn.execute(
                """
                SELECT file_id, original_filename FROM ggv_nota_files
                WHERE original_filename LIKE ?
                """,
                (f"%{number}%",),
            ).fetchall()
            for file_row in files:
                link_id = f"LINK-NOTA-{invoice_id}-{file_row['file_id']}"
                conn.execute(
                    """
                    INSERT INTO ggv_accountant_evidence_links (
                      link_id, entity_id, period_id, invoice_id, source_kind, source_id, created_at
                    ) VALUES (?, ?, ?, ?, 'nota_file', ?, ?)
                    ON CONFLICT(link_id) DO NOTHING
                    """,
                    (link_id, ENTITY, period, invoice_id, file_row["file_id"], ts),
                )
                linked += 1
    return {
        "ok": True,
        "period": period,
        "linked": linked,
        "missing": missing,
        "invoices_invented": 0,
        "note": "Existing originals were linked. Missing PDFs stay missing. No invoice was created.",
    }


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table(conn, table):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _as_amount(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _spec_for(item_id: str) -> dict[str, Any] | None:
    for item in SEPTEMBER_ITEMS:
        if item["item_id"] == item_id:
            return item
    return None


def _public_bank(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "txn_id": row["txn_id"],
        "txn_date": row["txn_date"],
        "value_date": row["value_date"],
        "description": row["description"],
        "reference": row["reference"],
        "debit": row["debit"],
        "credit": row["credit"],
        "recon_status": row["recon_status"],
        "matched_receipt_ref": row["matched_receipt_ref"],
        "match_confidence": row["match_confidence"],
        "match_proposed": bool(row["match_proposed"]),
        "human_confirmed": bool(row["human_confirmed"]),
        "notes": row["notes"],
        "bank_account": row["bank_account"],
        "entity_id": ENTITY,
    }


def _match_bank_exception(conn: sqlite3.Connection, spec: dict[str, Any], period: str) -> dict[str, Any]:
    """Attach one stored GGV September bank row. Never invent a row and never read AMG or BZG."""
    empty = {
        "status": "not_stored",
        "match_basis": None,
        "bank_transaction": None,
        "candidate_count": 0,
        "bank_row_invented": False,
        "note": (
            f"No {period} GGV bank row stores Rp{int(spec['amount_idr']):,} for {spec['counterparty']}. "
            "The transaction was not created for this review."
        ),
    }
    if not _table(conn, "ggv_bank_transactions"):
        empty["status"] = "bank_table_absent"
        return empty
    rows = conn.execute(
        """
        SELECT txn_id, txn_date, value_date, description, reference, debit, credit,
               recon_status, matched_receipt_ref, match_confidence, match_proposed,
               human_confirmed, notes, bank_account, entity_id
        FROM ggv_bank_transactions
        WHERE entity_id=?
        """,
        (ENTITY,),
    ).fetchall()
    target = float(spec["amount_idr"])
    september = []
    for row in rows:
        if str(row["entity_id"]) != ENTITY:
            continue
        debit = _as_amount(row["debit"])
        credit = _as_amount(row["credit"])
        if abs(debit - target) >= 1 and abs(credit - target) >= 1:
            continue
        if str(row["txn_date"] or "").startswith(period):
            september.append(row)
    if not september:
        return empty
    if len(september) == 1:
        return {
            "status": "matched",
            "match_basis": "amount_unique",
            "bank_transaction": _public_bank(september[0]),
            "candidate_count": 1,
            "bank_row_invented": False,
            "note": "One September GGV bank row matches this amount.",
        }
    return {
        "status": "ambiguous",
        "match_basis": None,
        "bank_transaction": None,
        "candidate_count": len(september),
        "bank_row_invented": False,
        "note": (
            f"{len(september)} September GGV bank rows share Rp{int(target):,}. "
            "None was selected."
        ),
    }


def _evidence_for(conn: sqlite3.Connection, bank: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not bank or not bank.get("matched_receipt_ref"):
        return [
            {
                "kind": "supporting_evidence",
                "original_present": False,
                "missing_evidence": True,
                "note": "No supporting receipt or invoice is linked on the GGV bank row.",
                "manufactured": False,
            }
        ]
    ref = str(bank["matched_receipt_ref"])
    found: list[dict[str, Any]] = []
    if _table(conn, "ggv_receipt_accounting"):
        row = conn.execute(
            """
            SELECT receipt_key, vault_filename, vault_path, missing_evidence
            FROM ggv_receipt_accounting
            WHERE entity_id=? AND (receipt_key=? OR vault_filename=?)
            """,
            (ENTITY, ref, ref),
        ).fetchone()
        if row is not None:
            path = Path(str(row["vault_path"] or ""))
            present = path.is_file()
            found.append(
                {
                    "kind": "receipt_photograph",
                    "source_id": row["receipt_key"],
                    "filename": row["vault_filename"],
                    "original_present": present,
                    "missing_evidence": bool(row["missing_evidence"]) or not present,
                    "entity_id": ENTITY,
                    "open_path": (
                        f"/api/ggv/finance/accounting/receipts/{row['receipt_key']}/image"
                        if present
                        else None
                    ),
                    "manufactured": False,
                }
            )
    if _table(conn, "ggv_nota_files") and _table(conn, "ggv_notas"):
        cols = _columns(conn, "ggv_nota_files")
        name_col = "original_filename" if "original_filename" in cols else "filename"
        if name_col in cols or "filename" in cols:
            file_rows = conn.execute(
                f"""
                SELECT f.file_id, f.filename, f.rel_path, f.{name_col} AS original_name
                FROM ggv_nota_files f
                JOIN ggv_notas n ON n.nota_id = f.nota_id
                WHERE n.entity_id=? AND (f.file_id=? OR f.filename=? OR f.{name_col}=?)
                """,
                (ENTITY, ref, ref, ref),
            ).fetchall()
            for file_row in file_rows:
                path = Path(str(file_row["rel_path"] or ""))
                present = path.is_file()
                found.append(
                    {
                        "kind": "nota_file",
                        "source_id": file_row["file_id"],
                        "filename": file_row["original_name"] or file_row["filename"],
                        "original_present": present,
                        "missing_evidence": not present,
                        "entity_id": ENTITY,
                        "manufactured": False,
                    }
                )
    if found:
        return found
    return [
        {
            "kind": "supporting_evidence",
            "source_id": ref,
            "original_present": False,
            "missing_evidence": True,
            "note": "The bank row names evidence that is not stored on a GGV receipt or nota.",
            "manufactured": False,
        }
    ]


def _allocation_history(bank: dict[str, Any] | None) -> dict[str, Any]:
    if not bank:
        return {
            "entries": [],
            "invented": False,
            "note": "No GGV bank row is stored, so there is no allocation history to open.",
        }
    return {
        "entries": [
            {
                "source": "ggv_bank_transactions",
                "txn_id": bank["txn_id"],
                "recon_status": bank["recon_status"],
                "matched_receipt_ref": bank["matched_receipt_ref"],
                "match_confidence": bank["match_confidence"],
                "match_proposed": bank["match_proposed"],
                "human_confirmed": bank["human_confirmed"],
                "notes": bank["notes"],
            }
        ],
        "invented": False,
        "note": (
            "Allocation history is the match fields on this GGV bank row. "
            "A separate allocation ledger is not stored."
        ),
    }


def _proposed_treatment(spec: dict[str, Any], bank: dict[str, Any] | None) -> dict[str, Any]:
    if not bank:
        return {
            "lines": [],
            "posted": False,
            "balanced": False,
            "bank_row_invented": False,
            "memo": (
                f"Direction for {spec['counterparty']} is not on a stored GGV bank row. "
                "No debit or credit line was proposed."
            ),
        }
    debit = _as_amount(bank.get("debit"))
    credit = _as_amount(bank.get("credit"))
    if debit > 0 and credit > 0:
        return {
            "lines": [],
            "posted": False,
            "balanced": False,
            "bank_row_invented": False,
            "memo": "The stored bank row has both a debit and a credit. No treatment was chosen.",
        }
    amount = int(round(debit if debit > 0 else credit))
    name = spec["counterparty"]
    if debit > 0:
        lines = [
            {"side": "debit", "account": f"Unclassified — {name}", "amount_idr": amount},
            {"side": "credit", "account": "GGV bank", "amount_idr": amount},
        ]
        memo = f"Bank debit. Proposed only. Not posted. {spec['title']}."
    else:
        lines = [
            {"side": "debit", "account": "GGV bank", "amount_idr": amount},
            {"side": "credit", "account": f"Unclassified receipt — {name}", "amount_idr": amount},
        ]
        memo = f"Bank credit. Proposed only. Not posted. {spec['title']}."
    return {
        "lines": lines,
        "posted": False,
        "balanced": True,
        "bank_row_invented": False,
        "status": "PROPOSED_NOT_POSTED",
        "memo": memo,
    }


def _exception_detail(conn: sqlite3.Connection, row: sqlite3.Row, period: str) -> dict[str, Any]:
    spec = _spec_for(str(row["item_id"])) or {
        "item_id": row["item_id"],
        "counterparty": row["title"],
        "amount_idr": 0,
        "title": row["title"],
        "kind": row["kind"],
    }
    match = _match_bank_exception(conn, spec, period) if _spec_for(str(row["item_id"])) else {
        "status": "not_a_bank_exception",
        "bank_transaction": None,
        "bank_row_invented": False,
        "match_basis": None,
        "candidate_count": 0,
        "note": "This row is not one of the five September bank exceptions.",
    }
    bank = match.get("bank_transaction")
    evidence = _evidence_for(conn, bank)
    treatment = _proposed_treatment(spec, bank)
    if bank:
        live = (
            f"{spec['title']} opens bank {bank['txn_id']} "
            f"({bank['txn_date'] or 'no date'}). Posted: false."
        )
    else:
        live = match.get("note") or spec["title"]
    return {
        "item_id": row["item_id"],
        "title": row["title"],
        "kind": "bank_exception",
        "counterparty": spec.get("counterparty"),
        "amount_idr": spec.get("amount_idr"),
        "recognition_terms": list(spec.get("match_terms") or []),
        "currency": CURRENCY,
        "status": row["status"],
        "period": period,
        "entity_id": ENTITY,
        "is_bank_exception": True,
        "bank_match": {
            "status": match.get("status"),
            "match_basis": match.get("match_basis"),
            "candidate_count": match.get("candidate_count"),
            "bank_row_invented": False,
            "note": match.get("note"),
        },
        "bank_transaction": bank,
        "evidence": evidence,
        "allocation_history": _allocation_history(bank),
        "proposed_treatment": treatment,
        "live_evidence": live,
        "decisions": _decisions(conn, row["item_id"]),
        "amounts_invented": False,
    }


def _decisions(conn: sqlite3.Connection, item_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT decision_id, decision, note, actor_person_id, created_at
        FROM ggv_accountant_decisions
        WHERE entity_id=? AND item_id=?
        ORDER BY created_at
        """,
        (ENTITY, item_id),
    ).fetchall()
    return [dict(row) for row in rows]


def _periods(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    stored = {
        str(row["period_id"]): str(row["status"])
        for row in conn.execute(
            "SELECT period_id, status FROM ggv_accountant_periods WHERE entity_id=?",
            (ENTITY,),
        ).fetchall()
    }
    months = [f"2026-{month:02d}" for month in range(1, 11)]
    for period in stored:
        if period not in months:
            months.append(period)
    months.sort()
    out = []
    for period in months:
        snap = _live_snapshot(conn, period)
        status = stored.get(period)
        if status is None:
            activity = (
                snap["bank_rows_unreconciled"]
                + snap["transactions_awaiting_classification"]
                + snap["customer_invoices"]
                + snap["notas_missing_file"]
            )
            if period == SEPTEMBER:
                status = "READY_FOR_REVIEW"
            elif activity == 0:
                status = "MISSING"
            else:
                status = "PROVISIONAL"
        out.append(
            {
                "period": period,
                "status": status,
                "entity_id": ENTITY,
                "live": snap,
                "books_final": False,
            }
        )
    return out


def _review_queue(conn: sqlite3.Connection, period: str, books: dict[str, Any]) -> list[dict[str, Any]]:
    del books
    if period != SEPTEMBER:
        return []
    wanted = [item["item_id"] for item in SEPTEMBER_ITEMS]
    rows = {
        str(row["item_id"]): row
        for row in conn.execute(
            """
            SELECT item_id, title, kind, status, created_at
            FROM ggv_accountant_review_items
            WHERE entity_id=? AND period_id=? AND item_id IN ({})
            """.format(",".join("?" for _ in wanted)),
            (ENTITY, period, *wanted),
        ).fetchall()
    }
    items = []
    for item_id in wanted:
        row = rows.get(item_id)
        if row is None:
            continue
        items.append(_exception_detail(conn, row, period))
    return items


def _names_person(text: str, terms: tuple[str, ...]) -> bool:
    blob = (text or "").upper()
    for term in terms:
        if re.search(rf"(?<![A-Z]){re.escape(term)}(?![A-Z])", blob):
            return True
    return False


def _reimbursement_schedules(conn: sqlite3.Connection) -> dict[str, Any]:
    """Matt and Amanda rows already stored on GGV notas or GGV bank text. No invented amounts."""
    schedules = []
    for person in REIMBURSEMENT_PEOPLE:
        lines: list[dict[str, Any]] = []
        if _table(conn, "ggv_notas"):
            for row in conn.execute(
                """
                SELECT nota_id, invoice_no, nota_date, amount, notes, workflow_state
                FROM ggv_notas
                WHERE entity_id=? AND created_by_person_id=?
                ORDER BY nota_date
                """,
                (ENTITY, person["person_id"]),
            ).fetchall():
                lines.append(
                    {
                        "source": "nota",
                        "source_id": row["nota_id"],
                        "date": row["nota_date"],
                        "description": row["invoice_no"] or row["notes"] or row["nota_id"],
                        "amount_idr": row["amount"],
                        "workflow_state": row["workflow_state"],
                        "entity_id": ENTITY,
                        "manufactured": False,
                    }
                )
        if _table(conn, "ggv_bank_transactions"):
            for row in conn.execute(
                """
                SELECT txn_id, txn_date, description, reference, debit, credit
                FROM ggv_bank_transactions
                WHERE entity_id=?
                ORDER BY txn_date
                """,
                (ENTITY,),
            ).fetchall():
                blob = f"{row['description'] or ''} {row['reference'] or ''}"
                if not _names_person(blob, tuple(person["terms"])):
                    continue
                amount = row["debit"] if _as_amount(row["debit"]) > 0 else row["credit"]
                lines.append(
                    {
                        "source": "bank",
                        "source_id": row["txn_id"],
                        "date": row["txn_date"],
                        "description": row["description"],
                        "amount_idr": amount,
                        "entity_id": ENTITY,
                        "manufactured": False,
                    }
                )
        schedules.append(
            {
                "person_id": person["person_id"],
                "name": person["name"],
                "lines": lines,
                "line_count": len(lines),
                "manufactured": False,
                "complete": False,
                "note": (
                    f"{len(lines)} stored GGV rows name {person['name']}."
                    if lines
                    else f"No stored GGV nota or bank row names {person['name']}. None was manufactured."
                ),
            }
        )
    return {
        "schedules": schedules,
        "manufactured": False,
        "complete": False,
        "note": "Reimbursement schedules are incomplete. Empty people stay empty.",
    }


def _preparation_tasks(conn: sqlite3.Connection, books: dict[str, Any], period: str = SEPTEMBER) -> list[dict[str, Any]]:
    """Invoices, unposted journals, and tax setup. These are not bank exceptions."""
    snap = _live_snapshot(conn, period)
    missing: list[dict[str, Any]] = []
    if _table(conn, "ggv_invoices"):
        for row in conn.execute(
            """
            SELECT invoice_id, invoice_number
            FROM ggv_invoices
            WHERE entity_id=? AND COALESCE(invoice_date, created_at, '') LIKE ?
            """,
            (ENTITY, period + "%"),
        ).fetchall():
            has_pdf = False
            if _table(conn, "ggv_invoice_documents"):
                has_pdf = (
                    conn.execute(
                        "SELECT 1 FROM ggv_invoice_documents WHERE invoice_id=?",
                        (row["invoice_id"],),
                    ).fetchone()
                    is not None
                )
            if not has_pdf:
                missing.append(
                    {
                        "invoice_id": row["invoice_id"],
                        "invoice_number": row["invoice_number"],
                        "original_pdf": False,
                    }
                )
    profile = None
    if _table(conn, "ggv_tax_profile"):
        profile = conn.execute(
            "SELECT npwp, pkp_status FROM ggv_tax_profile WHERE entity_id=?",
            (ENTITY,),
        ).fetchone()
    outstanding = []
    if profile is None or not profile["npwp"]:
        outstanding.append("NPWP is not verified.")
    if profile is None or str(profile["pkp_status"] or "UNKNOWN") == "UNKNOWN":
        outstanding.append("PKP status is unknown.")
    outstanding.append("Which of PPh 21, PPh 23, PPh 4(2), PPh 25, and PPN apply is not verified.")
    outstanding.append("The filing calendar is not stored.")
    outstanding.append("DJP/Coretax format has not been tested.")
    return [
        {
            "task_id": "PREP-MISSING-INVOICE-PDF",
            "kind": "missing_invoice_pdf",
            "title": "Customer invoices missing an original PDF",
            "period": period,
            "count": len(missing) or snap["customer_invoices_missing_original_pdf"],
            "items": missing,
            "is_bank_exception": False,
            "note": "Missing PDFs stay missing. No invoice was created.",
        },
        {
            "task_id": "PREP-UNPOSTED-JOURNALS",
            "kind": "unposted_journals",
            "title": "Journals are not posted. The books are not final.",
            "period": period,
            "journals_posted": books.get("journals_posted"),
            "books_final": False,
            "is_bank_exception": False,
            "note": books.get("note"),
        },
        {
            "task_id": "PREP-TAX-SETUP",
            "kind": "tax_setup",
            "title": "Tax setup is not verified",
            "period": period,
            "outstanding": outstanding,
            "blocks_filing": True,
            "is_bank_exception": False,
            "government_submitted_by_wolf": False,
        },
    ]


def _tax_workspace(conn: sqlite3.Connection) -> dict[str, Any]:
    profile = conn.execute(
        "SELECT npwp, pkp_status, note, verified_by, verified_at FROM ggv_tax_profile WHERE entity_id=?",
        (ENTITY,),
    ).fetchone()
    if profile is None:
        profile_out = {
            "npwp": None,
            "pkp_status": "UNKNOWN",
            "note": "ILA must verify NPWP, PKP status, and which regimes apply. Wolf has not assumed a registration.",
            "verified_by": None,
            "verified_at": None,
        }
    else:
        profile_out = dict(profile)
    filings = [
        dict(row)
        for row in conn.execute(
            """
            SELECT filing_id, tax_code, period_id, preparation_status, submission_reference,
                   acknowledgement_note, evidence_ref, recorded_by, created_at
            FROM ggv_accountant_filings WHERE entity_id=? ORDER BY created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    by_code = {row["tax_code"]: row for row in filings}
    obligations = []
    for spec in TAX_CODES:
        recorded = by_code.get(spec["code"])
        obligations.append(
            {
                "code": spec["code"],
                "label": spec["label"],
                "applies": None,
                "preparation_status": (recorded or {}).get("preparation_status") or "NOT_VERIFIED",
                "deadline": None,
                "deadline_note": "Filing deadline is not stored. ILA confirms the current DJP calendar.",
                "calculation": None,
                "liability_invented": False,
                "certificates_on_record": 0,
                "submission_reference": (recorded or {}).get("submission_reference"),
                "government_submitted_by_wolf": False,
                "format_tested": False,
                "compatibility_claimed": False,
            }
        )
    open_requests = [
        dict(row)
        for row in conn.execute(
            """
            SELECT request_id, period_id, missing_item, reason, responsible_person_id,
                   responsible_label, status, requested_by, created_at
            FROM ggv_accountant_doc_requests
            WHERE entity_id=? AND status='OPEN'
            ORDER BY created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    return {
        "profile": profile_out,
        "obligations": obligations,
        "filings": filings,
        "open_questions": [
            "NPWP is not verified.",
            "PKP status is unknown.",
            "Which of PPh 21, PPh 23, PPh 4(2), PPh 25, and PPN apply is not verified.",
            "DJP/Coretax file formats have not been tested. Wolf does not claim filing compatibility.",
        ],
        "missing_information_blocking_filing": open_requests,
        "blocks_filing": True,
        "wolf_files": False,
    }


def _accounting_status(conn: sqlite3.Connection, books: dict[str, Any]) -> dict[str, Any]:
    periods = _periods(conn, )
    current = datetime.now(timezone.utc).strftime("%Y-%m")
    snap = _live_snapshot(conn, current)
    proposals = _count(
        conn,
        "SELECT COUNT(*) FROM ggv_accountant_journal_proposals WHERE entity_id=? AND posted=0",
        (ENTITY,),
    )
    return {
        "company": COMPANY,
        "entity_id": ENTITY,
        "currency": CURRENCY,
        "current_period": current,
        "current_period_live": snap,
        "periods": periods,
        "bank_reconciliation": {
            "auto_reconcile": False,
            "unreconciled_current_period": snap["bank_rows_unreconciled"],
        },
        "transactions_awaiting_classification": snap["transactions_awaiting_classification"],
        "invoices": {
            "current_period": snap["customer_invoices"],
            "missing_original_pdf": snap["customer_invoices_missing_original_pdf"],
        },
        "supplier_bills": _count(
            conn,
            "SELECT COUNT(*) FROM ggv_bills WHERE entity_id=?",
            (ENTITY,),
        )
        if _table(conn, "ggv_bills")
        else 0,
        "expenses": _count(
            conn, "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=?", (ENTITY,)
        )
        if _table(conn, "ggv_notas")
        else 0,
        "reimbursements": _reimbursement_schedules(conn),
        "missing_documents": snap["notas_missing_file"] + snap["open_document_requests"],
        "journal_preparation": {
            "proposals_unposted": proposals,
            "posted": books.get("journals_posted"),
        },
        "month_end_close": {
            "september_2026": "READY_FOR_REVIEW",
            "books_final": False,
        },
        "books": books,
    }


def _review_history(conn: sqlite3.Connection) -> dict[str, Any]:
    decisions = [
        dict(row)
        for row in conn.execute(
            """
            SELECT d.decision_id, d.item_id, d.decision, d.note, d.actor_person_id, d.created_at,
                   i.title, i.status AS item_status
            FROM ggv_accountant_decisions d
            LEFT JOIN ggv_accountant_review_items i
              ON i.item_id = d.item_id AND i.entity_id = d.entity_id
            WHERE d.entity_id=?
            ORDER BY d.created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    proposals = [
        dict(row)
        for row in conn.execute(
            """
            SELECT proposal_id, period_id, memo, status, posted, proposed_by, created_at
            FROM ggv_accountant_journal_proposals
            WHERE entity_id=?
            ORDER BY created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    return {
        "decisions": decisions,
        "journal_proposals": proposals,
        "september_approved": False,
        "journals_posted": False,
        "note": "A review decision does not approve September and does not post a journal.",
    }


def _filing_history(conn: sqlite3.Connection) -> dict[str, Any]:
    filings = [
        dict(row)
        for row in conn.execute(
            """
            SELECT filing_id, tax_code, period_id, preparation_status, submission_reference,
                   acknowledgement_note, evidence_ref, recorded_by, created_at
            FROM ggv_accountant_filings
            WHERE entity_id=?
            ORDER BY created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    return {
        "filings": filings,
        "government_submitted_by_wolf": False,
        "note": "A filing row records evidence ILA already holds. Wolf does not submit a return.",
    }


def home(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    _require(conn, person_id, "finance.nota.read")
    roles = nota.active_role_ids(person_id, conn)
    return nota.public_payload(
        {
            "ok": True,
            "role_code": ROLE_CODE,
            "force_accountant_home": roles == {ROLE_ID},
            "dashboard_path": "/ggv/finance/accountant",
            "cloudflare_is_not_authorisation": True,
        }
    )


def dashboard(person_id: str, conn: sqlite3.Connection, qs: dict[str, list[str]] | None = None) -> dict[str, Any]:
    _reject_other_entity(qs)
    _require(conn, person_id, "finance.records.read")
    ensure_schema(conn)
    _preserve_september(conn, person_id)
    links = link_original_invoice_pdfs(conn, SEPTEMBER)
    conn.commit()
    books = _books_status()
    queue = _review_queue(conn, SEPTEMBER, books)
    unresolved = [item for item in queue if item["status"] == "OPEN"]
    preparations = _preparation_tasks(conn, books, SEPTEMBER)
    requests = [
        dict(row)
        for row in conn.execute(
            """
            SELECT request_id, period_id, missing_item, reason, responsible_label,
                   status, requested_by, created_at, updated_at
            FROM ggv_accountant_doc_requests
            WHERE entity_id=?
            ORDER BY created_at
            """,
            (ENTITY,),
        ).fetchall()
    ]
    return nota.public_payload(
        {
            "ok": True,
            "company": COMPANY,
            "entity_id": ENTITY,
            "currency": CURRENCY,
            "accountant": ILA_DISPLAY,
            "role_code": ROLE_CODE,
            "accounting_status": _accounting_status(conn, books),
            "finance_review_queue": {
                "period": SEPTEMBER,
                "status": "READY_FOR_REVIEW",
                "exceptions": queue,
                "unresolved_count": len(unresolved),
                "approved": False,
                "evidence_pack": "/api/ggv/finance/export/month?year=2026&month=09&entity=ENT-GGV",
            },
            "preparation_tasks": preparations,
            "reimbursements": _reimbursement_schedules(conn),
            "document_requests": requests,
            "review_history": _review_history(conn),
            "filing_history": _filing_history(conn),
            "tax_compliance": _tax_workspace(conn),
            "exports": list(EXPORTS),
            "original_invoice_pdfs": links,
            "actions_separated": {
                "wolf": "Extract, reconcile, classify provisionally, calculate, and prepare.",
                "ila": "Review treatments, prepare adjustments, validate schedules, and record filing evidence.",
                "ggv_management": "Approve material adjustments and payments.",
            },
            "automatic_filing": False,
            "automatic_journal_post": False,
            "automatic_payment": False,
            "cloudflare_is_not_authorisation": True,
        }
    )


def decide_review(
    person_id: str,
    item_id: str,
    body: dict[str, Any],
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.recon.review")
    decision = str(body.get("decision") or "").strip().lower()
    allowed = {"approve": "APPROVED", "return": "RETURNED", "request_information": "INFO_REQUESTED"}
    if decision not in allowed:
        raise nota.FinanceNotaError(
            "Choose approve, return, or request information.",
            code="bad_decision",
        )
    note = str(body.get("note") or "").strip()
    if not note:
        raise nota.FinanceNotaError("Write the reason for this decision.", code="missing_note")
    row = conn.execute(
        """
        SELECT item_id, status, title, period_id FROM ggv_accountant_review_items
        WHERE item_id=? AND entity_id=?
        """,
        (item_id, ENTITY),
    ).fetchone()
    if row is None:
        raise nota.FinanceNotaError("That review item was not found.", code="not_found", http_status=404)
    before = row["status"]
    status = allowed[decision]
    ts = _now()
    decision_id = nota._mint("DEC")
    conn.execute(
        """
        INSERT INTO ggv_accountant_decisions (
          decision_id, entity_id, item_id, decision, note, actor_person_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (decision_id, ENTITY, item_id, status, note, person_id, ts),
    )
    conn.execute(
        "UPDATE ggv_accountant_review_items SET status=? WHERE item_id=? AND entity_id=?",
        (status, item_id, ENTITY),
    )
    request_id = None
    if decision == "request_information":
        request_id = nota._mint("REQ")
        conn.execute(
            """
            INSERT INTO ggv_accountant_doc_requests (
              request_id, entity_id, period_id, missing_item, reason,
              responsible_person_id, responsible_label, status, requested_by,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
            """,
            (
                request_id,
                ENTITY,
                row["period_id"],
                str(body.get("missing_item") or row["title"]),
                note,
                str(body.get("responsible_person_id") or "").strip() or None,
                str(body.get("responsible_label") or "GGV Finance").strip(),
                person_id,
                ts,
                ts,
            ),
        )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.review",
        resource_type="ggv_accountant_review_item",
        resource_id=item_id,
        metadata={
            "entity_id": ENTITY,
            "decision": status,
            "status": before,
            "note": note[:240],
            "exception_id": item_id,
        },
    )
    conn.commit()
    after = conn.execute(
        "SELECT status FROM ggv_accountant_review_items WHERE item_id=?",
        (item_id,),
    ).fetchone()
    return nota.public_payload(
        {
            "ok": True,
            "item_id": item_id,
            "decision_id": decision_id,
            "decision": status,
            "previous_status": before,
            "status": after["status"] if after else status,
            "journal_posted": False,
            "payment_executed": False,
            "tax_filed": False,
            "document_request_id": request_id,
            "history": _decisions(conn, item_id),
        }
    )


def request_document(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.document.request")
    missing_item = str(body.get("missing_item") or "").strip()
    reason = str(body.get("reason") or "").strip()
    period = str(body.get("period") or SEPTEMBER).strip()
    responsible = str(body.get("responsible_person_id") or "").strip() or None
    label = str(body.get("responsible_label") or "").strip()
    if not missing_item or not reason or not label:
        raise nota.FinanceNotaError(
            "Name the missing item, the period reason, and who should supply it.",
            code="missing_fields",
        )
    if not period or len(period) != 7:
        raise nota.FinanceNotaError("Use a period like 2026-09.", code="bad_period")
    ts = _now()
    request_id = nota._mint("REQ")
    conn.execute(
        """
        INSERT INTO ggv_accountant_doc_requests (
          request_id, entity_id, period_id, missing_item, reason,
          responsible_person_id, responsible_label, status, requested_by,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """,
        (request_id, ENTITY, period, missing_item, reason, responsible, label, person_id, ts, ts),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.document_request",
        resource_type="ggv_accountant_doc_request",
        resource_id=request_id,
        metadata={"entity_id": ENTITY, "status": "OPEN", "note": missing_item[:240]},
    )
    conn.commit()
    return nota.public_payload(
        {
            "ok": True,
            "request_id": request_id,
            "entity_id": ENTITY,
            "period": period,
            "missing_item": missing_item,
            "reason": reason,
            "responsible_person_id": responsible,
            "responsible_label": label,
            "status": "OPEN",
        }
    )


def _balanced_journal_lines(lines: Any) -> list[dict[str, Any]]:
    if not isinstance(lines, list) or not lines:
        raise nota.FinanceNotaError(
            "A proposal needs debit and credit lines.",
            code="missing_fields",
        )
    parsed: list[dict[str, Any]] = []
    debit = 0.0
    credit = 0.0
    for line in lines:
        if not isinstance(line, dict):
            raise nota.FinanceNotaError(
                "Each line needs a debit or credit, an account, and an amount.",
                code="unbalanced",
            )
        side = str(line.get("side") or "").strip().lower()
        account = str(line.get("account") or "").strip()
        try:
            amount = float(line.get("amount_idr"))
        except (TypeError, ValueError):
            amount = 0.0
        if side not in {"debit", "credit"} or not account or amount <= 0:
            raise nota.FinanceNotaError(
                "Each line needs a debit or credit, an account, and an amount.",
                code="unbalanced",
            )
        if side == "debit":
            debit += amount
        else:
            credit += amount
        parsed.append({"side": side, "account": account, "amount_idr": round(amount, 2)})
    if abs(debit - credit) > 0.5:
        raise nota.FinanceNotaError(
            "Debit and credit lines must balance. Nothing was posted.",
            code="unbalanced",
        )
    return parsed


def propose_journal(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.journal.propose")
    memo = str(body.get("memo") or "").strip()
    lines = _balanced_journal_lines(body.get("lines"))
    if not memo:
        raise nota.FinanceNotaError("A proposal needs a memo and lines.", code="missing_fields")
    ts = _now()
    proposal_id = nota._mint("JPR")
    conn.execute(
        """
        INSERT INTO ggv_accountant_journal_proposals (
          proposal_id, entity_id, period_id, memo, lines_json, status,
          proposed_by, created_at, posted
        ) VALUES (?, ?, ?, ?, ?, 'AWAITING_MANAGEMENT', ?, ?, 0)
        """,
        (
            proposal_id,
            ENTITY,
            str(body.get("period") or SEPTEMBER),
            memo,
            json.dumps(lines),
            person_id,
            ts,
        ),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.journal_propose",
        resource_type="ggv_accountant_journal_proposal",
        resource_id=proposal_id,
        metadata={"entity_id": ENTITY, "status": "AWAITING_MANAGEMENT"},
    )
    conn.commit()
    return nota.public_payload(
        {
            "ok": True,
            "proposal_id": proposal_id,
            "status": "AWAITING_MANAGEMENT",
            "posted": False,
            "balanced": True,
            "lines": lines,
            "message": "GGV management must approve this adjustment. It was not posted.",
        }
    )


def update_document_request(
    person_id: str,
    request_id: str,
    body: dict[str, Any],
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.document.request")
    status = str(body.get("status") or "").strip().upper()
    if status not in {"OPEN", "FULFILLED", "CANCELLED"}:
        raise nota.FinanceNotaError("Status must be OPEN, FULFILLED, or CANCELLED.", code="bad_status")
    row = conn.execute(
        """
        SELECT request_id FROM ggv_accountant_doc_requests
        WHERE request_id=? AND entity_id=?
        """,
        (request_id, ENTITY),
    ).fetchone()
    if row is None:
        raise nota.FinanceNotaError("That document request was not found.", code="not_found", http_status=404)
    ts = _now()
    conn.execute(
        """
        UPDATE ggv_accountant_doc_requests
        SET status=?, updated_at=?
        WHERE request_id=? AND entity_id=?
        """,
        (status, ts, request_id, ENTITY),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.document_request_status",
        resource_type="ggv_accountant_doc_request",
        resource_id=request_id,
        metadata={"entity_id": ENTITY, "status": status},
    )
    conn.commit()
    return nota.public_payload(
        {
            "ok": True,
            "request_id": request_id,
            "status": status,
            "document_created": False,
            "note": "Marking a request fulfilled does not create a document.",
        }
    )


def review_item(person_id: str, item_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    _require(conn, person_id, "finance.records.read")
    if _spec_for(item_id) is None:
        raise nota.FinanceNotaError(
            "That item is not one of the five September bank exceptions.",
            code="not_found",
            http_status=404,
        )
    row = conn.execute(
        """
        SELECT item_id, title, kind, status, created_at
        FROM ggv_accountant_review_items
        WHERE item_id=? AND entity_id=? AND period_id=?
        """,
        (item_id, ENTITY, SEPTEMBER),
    ).fetchone()
    if row is None:
        raise nota.FinanceNotaError("That exception is not stored.", code="not_found", http_status=404)
    detail = _exception_detail(conn, row, SEPTEMBER)
    detail["ok"] = True
    return nota.public_payload(detail)


def accountant_history(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    _require(conn, person_id, "finance.history.read")
    return nota.public_payload(
        {
            "ok": True,
            "entity_id": ENTITY,
            "review_history": _review_history(conn),
            "filing_history": _filing_history(conn),
            "document_requests": [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT request_id, period_id, missing_item, status, created_at, updated_at
                    FROM ggv_accountant_doc_requests
                    WHERE entity_id=?
                    ORDER BY created_at
                    """,
                    (ENTITY,),
                ).fetchall()
            ],
            "september_approved": False,
            "journals_posted": False,
            "tax_filed": False,
        }
    )


def record_filing(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.filing.record")
    if body.get("submit") or body.get("file_now"):
        raise nota.FinanceNotaError(
            "Wolf does not submit a return. Record the reference after ILA files.",
            code="filing_refused",
            http_status=403,
        )
    code = str(body.get("tax_code") or "").strip()
    known = {item["code"] for item in TAX_CODES}
    if code not in known:
        raise nota.FinanceNotaError("Unknown tax code.", code="bad_tax_code")
    status = str(body.get("preparation_status") or "PREPARING").strip()
    if status not in {"NOT_VERIFIED", "PREPARING", "READY_FOR_ILA", "FILED_RECORDED"}:
        raise nota.FinanceNotaError("Unknown preparation status.", code="bad_status")
    ts = _now()
    filing_id = nota._mint("FIL")
    conn.execute(
        """
        INSERT INTO ggv_accountant_filings (
          filing_id, entity_id, tax_code, period_id, preparation_status,
          submission_reference, acknowledgement_note, evidence_ref, recorded_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filing_id,
            ENTITY,
            code,
            str(body.get("period") or "").strip() or None,
            status,
            str(body.get("submission_reference") or "").strip() or None,
            str(body.get("acknowledgement_note") or "").strip() or None,
            str(body.get("evidence_ref") or "").strip() or None,
            person_id,
            ts,
        ),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.filing_record",
        resource_type="ggv_accountant_filing",
        resource_id=filing_id,
        metadata={"entity_id": ENTITY, "status": status, "evidence_type": code},
    )
    conn.commit()
    return nota.public_payload(
        {
            "ok": True,
            "filing_id": filing_id,
            "tax_code": code,
            "preparation_status": status,
            "government_submitted_by_wolf": False,
            "compatibility_claimed": False,
        }
    )


def record_tax_profile(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    _reject_other_entity(None, body)
    _require(conn, person_id, "finance.filing.record")
    npwp = str(body.get("npwp") or "").strip() or None
    pkp = str(body.get("pkp_status") or "UNKNOWN").strip().upper()
    if pkp not in {"UNKNOWN", "PKP", "NON_PKP"}:
        raise nota.FinanceNotaError("PKP status must be UNKNOWN, PKP, or NON_PKP.", code="bad_status")
    if not npwp and pkp == "UNKNOWN" and not str(body.get("note") or "").strip():
        raise nota.FinanceNotaError("Record what ILA verified.", code="missing_fields")
    ts = _now()
    conn.execute(
        """
        INSERT INTO ggv_tax_profile (
          entity_id, npwp, pkp_status, note, verified_by, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(entity_id) DO UPDATE SET
          npwp=excluded.npwp,
          pkp_status=excluded.pkp_status,
          note=excluded.note,
          verified_by=excluded.verified_by,
          verified_at=excluded.verified_at
        """,
        (ENTITY, npwp, pkp, str(body.get("note") or "").strip() or None, person_id, ts),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.tax_profile",
        resource_type="ggv_tax_profile",
        resource_id=ENTITY,
        metadata={"entity_id": ENTITY, "status": pkp},
    )
    conn.commit()
    return nota.public_payload({"ok": True, "npwp_recorded": bool(npwp), "pkp_status": pkp, "assumed": False})


def _stamp(period: str, status: str) -> list[tuple[str, str]]:
    books = _books_status()
    return [
        ("company", COMPANY),
        ("entity_id", ENTITY),
        ("period", period),
        ("currency", CURRENCY),
        ("generated_at", _now()),
        ("accounting_status", status),
        ("source_evidence", "GGV catalog"),
        ("journals_posted", "" if books.get("journals_posted") is None else str(books["journals_posted"])),
        ("books_final", "false"),
        ("liability_invented", "false"),
        ("note", str(books.get("note") or "")),
    ]


def _rows_for(conn: sqlite3.Connection, kind: str, period: str) -> tuple[list[str], list[list[Any]], str]:
    books = _books_status()
    status = "NOT_FINAL"
    if kind in {"general-ledger", "trial-balance"}:
        status = "GAP"
        headers = ["gap", "detail"]
        rows = [
            [
                "not_available",
                books.get("note")
                or "General ledger and trial balance are not final because posted journals are not available.",
            ]
        ]
        return headers, rows, status
    if kind == "bank-register":
        headers = ["txn_date", "description", "debit", "credit", "recon_status", "entity_id"]
        rows = []
        if _table(conn, "ggv_bank_transactions"):
            for row in conn.execute(
                """
                SELECT txn_date, description, debit, credit, recon_status, entity_id
                FROM ggv_bank_transactions
                WHERE entity_id=? AND COALESCE(txn_date,'') LIKE ?
                ORDER BY txn_date
                """,
                (ENTITY, period + "%"),
            ).fetchall():
                rows.append([row["txn_date"], row["description"], row["debit"], row["credit"], row["recon_status"], row["entity_id"]])
        if not rows:
            rows.append(["", "No GGV bank rows for this period.", "", "", "MISSING", ENTITY])
            status = "GAP"
        return headers, rows, status
    if kind == "invoices-ar":
        headers = ["invoice_id", "invoice_number", "invoice_date", "status", "total", "original_pdf", "entity_id"]
        rows = []
        if _table(conn, "ggv_invoices"):
            for row in conn.execute(
                """
                SELECT invoice_id, invoice_number, invoice_date, status, grand_total, entity_id
                FROM ggv_invoices
                WHERE entity_id=? AND COALESCE(invoice_date, created_at, '') LIKE ?
                """,
                (ENTITY, period + "%"),
            ).fetchall():
                has_pdf = False
                if _table(conn, "ggv_invoice_documents"):
                    has_pdf = (
                        conn.execute(
                            "SELECT 1 FROM ggv_invoice_documents WHERE invoice_id=?",
                            (row["invoice_id"],),
                        ).fetchone()
                        is not None
                    )
                rows.append(
                    [
                        row["invoice_id"],
                        row["invoice_number"],
                        row["invoice_date"],
                        row["status"],
                        row["grand_total"],
                        "yes" if has_pdf else "missing",
                        ENTITY,
                    ]
                )
        if not rows:
            rows.append(["", "", "", "GAP", "", "No customer invoices stored for this period.", ENTITY])
            status = "GAP"
        return headers, rows, status
    if kind == "bills-ap":
        headers = ["bill_id", "supplier", "bill_date", "amount", "entity_id"]
        rows = []
        if _table(conn, "ggv_bills"):
            for row in conn.execute(
                """
                SELECT bill_id, contact_name, issued_on, amount, entity_id
                FROM ggv_bills
                WHERE entity_id=? AND COALESCE(issued_on, created_at, '') LIKE ?
                """,
                (ENTITY, period + "%"),
            ).fetchall():
                rows.append([row["bill_id"], row["contact_name"], row["issued_on"], row["amount"], ENTITY])
        if not rows:
            rows.append(["", "", "", "", "No supplier bills stored for this period."])
            status = "GAP"
        return headers, rows, status
    if kind == "expenses":
        headers = ["nota_id", "invoice_no", "nota_date", "amount", "workflow_state", "file_count", "entity_id"]
        rows = []
        if _table(conn, "ggv_notas"):
            for row in conn.execute(
                """
                SELECT nota_id, invoice_no, nota_date, amount, workflow_state, entity_id
                FROM ggv_notas
                WHERE entity_id=? AND COALESCE(nota_date, created_at, '') LIKE ?
                """,
                (ENTITY, period + "%"),
            ).fetchall():
                files = _count(conn, "SELECT COUNT(*) FROM ggv_nota_files WHERE nota_id=?", (row["nota_id"],))
                rows.append(
                    [row["nota_id"], row["invoice_no"], row["nota_date"], row["amount"], row["workflow_state"], files, ENTITY]
                )
        if not rows:
            rows.append(["", "", "", "", "GAP", 0, "No notas stored for this period."])
            status = "GAP"
        return headers, rows, status
    if kind == "reimbursements":
        headers = [
            "person",
            "source",
            "source_id",
            "date",
            "description",
            "amount_idr",
            "complete",
            "manufactured",
        ]
        rows = []
        for schedule in _reimbursement_schedules(conn)["schedules"]:
            if not schedule["lines"]:
                rows.append(
                    [
                        schedule["name"],
                        "",
                        "",
                        "",
                        schedule["note"],
                        "",
                        "false",
                        "false",
                    ]
                )
                continue
            for line in schedule["lines"]:
                rows.append(
                    [
                        schedule["name"],
                        line["source"],
                        line["source_id"],
                        line.get("date"),
                        line.get("description"),
                        line.get("amount_idr"),
                        "false",
                        "false",
                    ]
                )
        return headers, rows, "INCOMPLETE"
    if kind == "withholding":
        return (
            ["tax_code", "certificates_on_record", "liability", "detail"],
            [
                [item["code"], 0, "", "No withholding certificate is stored. None was invented."]
                for item in TAX_CODES
                if item["code"].startswith("PPh")
            ],
            "GAP",
        )
    if kind == "tax-schedules":
        headers = ["tax_code", "label", "applies", "preparation_status", "liability", "format_tested"]
        rows = [
            [item["code"], item["label"], "", "NOT_VERIFIED", "", "false"]
            for item in TAX_CODES
        ]
        return headers, rows, "NOT_VERIFIED"
    if kind == "journals":
        headers = ["proposal_id", "memo", "status", "posted", "proposed_by", "created_at"]
        rows = []
        for row in conn.execute(
            """
            SELECT proposal_id, memo, status, posted, proposed_by, created_at
            FROM ggv_accountant_journal_proposals
            WHERE entity_id=? AND (period_id=? OR period_id IS NULL)
            """,
            (ENTITY, period),
        ).fetchall():
            rows.append([row["proposal_id"], row["memo"], row["status"], row["posted"], row["proposed_by"], row["created_at"]])
        rows.append(["", books.get("note") or "Posted journal register is not a final ledger.", "GAP", 0, "", ""])
        return headers, rows, "NOT_FINAL"
    headers = ["kind", "detail", "entity_id"]
    rows = []
    for item in _review_queue(conn, period, books):
        rows.append([item["item_id"], f"bank_exception {item['status']}: {item['live_evidence']}", ENTITY])
    for task in _preparation_tasks(conn, books, period):
        rows.append([task["task_id"], f"preparation_task: {task['title']}", ENTITY])
    for req in conn.execute(
        """
        SELECT request_id, missing_item, status FROM ggv_accountant_doc_requests
        WHERE entity_id=? AND period_id=?
        """,
        (ENTITY, period),
    ).fetchall():
        rows.append([req["request_id"], f"{req['status']}: {req['missing_item']}", ENTITY])
    if not rows:
        rows.append(["", "No audit rows for this period.", ENTITY])
        status = "GAP"
    return headers, rows, status


def _csv_bytes(stamp: list[tuple[str, str]], headers: list[str], rows: list[list[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["field", "value"])
    for key, value in stamp:
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _xlsx_bytes(stamp: list[tuple[str, str]], headers: list[str], rows: list[list[Any]]) -> bytes:
    def cell(ref: str, value: Any) -> str:
        text = xml_escape("" if value is None else str(value))
        return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    sheet_rows = []
    all_rows = [["field", "value"], *([key, value] for key, value in stamp), [], headers, *rows]
    for index, row in enumerate(all_rows, start=1):
        cells = []
        for col, value in enumerate(row):
            letter = chr(ord("A") + col)
            cells.append(cell(f"{letter}{index}", value))
        sheet_rows.append(f'<row r="{index}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="GGV" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def export_register(
    person_id: str,
    kind: str,
    qs: dict[str, list[str]],
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    _reject_other_entity(qs)
    _require(conn, person_id, "finance.report.export")
    known = {item["id"] for item in EXPORTS}
    if kind not in known:
        raise nota.FinanceNotaError("That export is not available.", code="not_found", http_status=404)
    if kind == "evidence-pack":
        year, month = SEPTEMBER.split("-")
        return nota.export_month_pack(
            person_id,
            {"year": [year], "month": [month], "entity": [ENTITY]},
            conn=conn,
        )
    period = ((qs.get("period") or [SEPTEMBER])[0] or SEPTEMBER).strip()
    fmt = ((qs.get("format") or ["csv"])[0] or "csv").strip().lower()
    if fmt not in {"csv", "xlsx"}:
        raise nota.FinanceNotaError("Choose csv or xlsx.", code="bad_format")
    period_row = conn.execute(
        "SELECT status FROM ggv_accountant_periods WHERE entity_id=? AND period_id=?",
        (ENTITY, period),
    ).fetchone()
    status = period_row["status"] if period_row else "PROVISIONAL"
    headers, rows, data_status = _rows_for(conn, kind, period)
    stamp = _stamp(period, status if data_status != "GAP" else data_status)
    if fmt == "xlsx":
        payload = _xlsx_bytes(stamp, headers, rows)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"ggv-{kind}-{period}.xlsx"
    else:
        payload = _csv_bytes(stamp, headers, rows)
        content_type = "text/csv; charset=utf-8"
        filename = f"ggv-{kind}-{period}.csv"
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.accountant.export",
        resource_type="ggv_accountant_export",
        resource_id=f"{kind}:{period}",
        metadata={"entity_id": ENTITY, "status": data_status, "evidence_type": fmt},
    )
    conn.commit()
    return {
        "_file": {
            "data": payload,
            "content_type": content_type,
            "filename": filename,
            "disposition": "attachment",
        }
    }


def invoice_original(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    _require(conn, person_id, "finance.evidence.read")
    if not _table(conn, "ggv_invoices"):
        raise nota.FinanceNotaError("That invoice was not found.", code="not_found", http_status=404)
    row = conn.execute(
        "SELECT entity_id FROM ggv_invoices WHERE invoice_id=?",
        (invoice_id,),
    ).fetchone()
    if row is None or str(row["entity_id"]) != ENTITY:
        raise nota.FinanceNotaError(
            "That invoice is not a GGV record.",
            code="forbidden",
            http_status=403,
        )
    from core import ggv_finance_invoice as invoices

    return invoices.invoice_pdf(person_id, invoice_id, conn)


def granted_codes(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT p.code FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id=? AND rp.effect='ALLOW'
        ORDER BY p.code
        """,
        (ROLE_ID,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def http(
    method: str,
    rest: str,
    qs: dict[str, list[str]],
    body: dict[str, Any] | None,
    person_id: str | None,
) -> dict[str, Any]:
    body = body or {}
    conn = nota._open_ready()
    try:
        ensure_schema(conn)
        ensure_permissions(conn)
        conn.commit()
        if method == "GET" and rest == "/accountant/home":
            return home(person_id or "", conn)
        if method == "GET" and rest == "/accountant/dashboard":
            return dashboard(person_id or "", conn, qs)
        if method == "GET" and rest == "/accountant/history":
            return accountant_history(person_id or "", conn)
        if method == "GET" and rest.startswith("/accountant/review/") and rest.count("/") == 3:
            return review_item(person_id or "", rest.split("/")[3], conn)
        if method == "POST" and rest.startswith("/accountant/review/") and rest.count("/") == 3:
            item_id = rest.split("/")[3]
            return decide_review(person_id or "", item_id, body, conn)
        if method == "POST" and rest == "/accountant/document-requests":
            return request_document(person_id or "", body, conn)
        if method == "POST" and rest.startswith("/accountant/document-requests/") and rest.count("/") == 3:
            return update_document_request(person_id or "", rest.split("/")[3], body, conn)
        if method == "POST" and rest == "/accountant/journal-proposals":
            return propose_journal(person_id or "", body, conn)
        if method == "POST" and rest in {
            "/accountant/journal-proposals/post",
            "/accountant/payments",
        } or rest.endswith("/post") or rest.endswith("/pay"):
            raise nota.FinanceNotaError(
                "This workspace does not post journals or pay from the bank.",
                code="forbidden",
                http_status=403,
            )
        if method == "POST" and rest == "/accountant/filings":
            return record_filing(person_id or "", body, conn)
        if method == "POST" and rest in {"/accountant/filings/submit", "/accountant/tax/submit"}:
            raise nota.FinanceNotaError(
                "Wolf does not file with the government from this workspace.",
                code="filing_refused",
                http_status=403,
            )
        if method == "POST" and rest == "/accountant/tax-profile":
            return record_tax_profile(person_id or "", body, conn)
        export_match = rest.startswith("/accountant/exports/")
        if method == "GET" and export_match:
            kind = rest.split("/")[3]
            return export_register(person_id or "", kind, qs, conn)
        pdf_match = rest.startswith("/accountant/invoices/") and rest.endswith("/pdf")
        if method == "GET" and pdf_match:
            invoice_id = rest.split("/")[3]
            return invoice_original(person_id or "", invoice_id, conn)
        raise nota.FinanceNotaError("Not found.", code="not_found", http_status=404)
    finally:
        conn.close()
