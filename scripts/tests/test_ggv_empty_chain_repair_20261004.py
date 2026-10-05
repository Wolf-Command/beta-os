#!/usr/bin/env python3
"""GGV-EMPTY-CHAIN-REPAIR — schema-only temp sqlite. Never copies live catalog."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
sys.path.insert(0, str(SCRIPTS))
os.environ["WOLF_TEST_MODE"] = "1"

from core import ggv_empty_chain_repair1 as repair  # noqa: E402
from core import ggv_finance_invoice as inv  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402

PASS = 0
FAIL = 0
TS = "2026-10-04T19:00:00+08:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _seed_source(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE contact (
          id TEXT PRIMARY KEY,
          name TEXT
        );
        CREATE TABLE sales_invoice (
          id TEXT PRIMARY KEY,
          entity TEXT NOT NULL,
          contact_id TEXT,
          number TEXT,
          issued_on TEXT,
          due_on TEXT,
          status TEXT,
          amount TEXT,
          currency TEXT,
          notes TEXT,
          created_at TEXT NOT NULL,
          created_by TEXT,
          description TEXT,
          contact_name TEXT,
          contact_email TEXT,
          reference TEXT,
          source TEXT
        );
        CREATE TABLE bill (
          id TEXT PRIMARY KEY,
          entity TEXT NOT NULL,
          contact_id TEXT,
          number TEXT,
          issued_on TEXT,
          due_on TEXT,
          status TEXT,
          amount TEXT,
          currency TEXT,
          notes TEXT,
          created_at TEXT NOT NULL,
          created_by TEXT
        );
        CREATE TABLE ggv_nota (
          id TEXT PRIMARY KEY,
          filename TEXT,
          supplier TEXT,
          nota_number TEXT,
          nota_date TEXT,
          total_idr INTEGER,
          currency TEXT,
          status TEXT,
          note TEXT,
          source TEXT,
          uploaded_by TEXT,
          uploaded_at TEXT,
          learned_at TEXT,
          company TEXT,
          coa_name TEXT
        );
        INSERT INTO contact VALUES ('cust-1', 'PT Test Customer');
        INSERT INTO sales_invoice VALUES (
          'inv-paid-1', 'GGV', 'cust-1', '021A', '2026-07-01', '2026-07-15', 'PAID',
          '25000000', 'IDR', 'test paid', '2026-08-20 18:05 WITA', 'xero_import',
          NULL, 'PT Test Customer', NULL, '021A ref', 'xero_import'
        );
        INSERT INTO sales_invoice VALUES (
          'inv-draft-1', 'GGV', 'cust-1', NULL, '2026-09-01', NULL, 'DRAFT',
          '1000000', 'IDR', 'draft row', '2026-09-01 10:00 WITA', 'manual',
          NULL, 'PT Test Customer', NULL, NULL, 'manual'
        );
        INSERT INTO sales_invoice VALUES (
          'inv-deleted-1', 'GGV', 'cust-1', '099Z', '2026-07-02', '2026-07-16', 'DELETED',
          '500000', 'IDR', 'deleted row', '2026-08-21 18:05 WITA', 'xero_import',
          NULL, 'PT Test Customer', NULL, '099Z ref', 'xero_import'
        );
        INSERT INTO bill VALUES (
          'bill-1', 'GGV', NULL, 'B-1', '2026-07-01', NULL, 'DRAFT',
          '1000', 'IDR', NULL, '2026-08-20 18:05 WITA', 'xero_import'
        );
        INSERT INTO ggv_nota VALUES (
          'nota-1', 'slip.jpg', 'M-Mart', 'N-1', '2026-09-02', 500000, 'IDR', 'learned',
          'Peaches Upload', 'telegram-menu', 'matthew', '2026-09-02 10:59 WITA',
          '2026-09-02 10:59 WITA', 'Jivana Resort', 'Entertainment'
        );
        """
    )
    conn.commit()
    conn.close()


def _bootstrap_target(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    for sql_name in (
        "005_org_registry.sql",
        "006_person_auth_identity.sql",
        "007_role_position_assignment.sql",
        "008_assignment_scope.sql",
        "009_rbac_permissions.sql",
        "011_audit_evidence_spine.sql",
    ):
        sql_path = MIGRATIONS / sql_name
        if sql_path.is_file():
            conn.executescript(sql_path.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, status, created_at, updated_at)
        VALUES ('PERS-MATT', 'Matthew', 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO NOTHING
        """,
        (TS, TS),
    )
    fin.ensure_schema(conn)
    inv.ensure_schema(conn)
    conn.commit()
    conn.close()


def test_import_and_idempotency() -> None:
    with tempfile.TemporaryDirectory() as td:
        source = Path(td) / "ggv-source-books.sqlite"
        target = Path(td) / "content_library.sqlite"
        _seed_source(source)
        _bootstrap_target(target)

        first = repair.run_import(target, source_db=source)
        check("first import ok", first["invoices"]["imported"] == 3, str(first["invoices"]))
        check("nota imported", first["notas"]["imported"] == 1, str(first["notas"]))
        check(
            "bill imported into ggv_bills",
            first["bills"]["imported"] == 1,
            str(first["bills"]),
        )
        check(
            "source invoice status split recorded",
            first["source_invoice_status_split"].get("PAID") == 1
            and first["source_invoice_status_split"].get("DRAFT") == 1
            and first["source_invoice_status_split"].get("DELETED") == 1,
            str(first["source_invoice_status_split"]),
        )

        conn = sqlite3.connect(str(target))
        conn.row_factory = sqlite3.Row
        paid = conn.execute(
            "SELECT invoice_id, status, grand_total, invoice_number FROM ggv_invoices WHERE invoice_id='inv-paid-1'"
        ).fetchone()
        check("paid invoice id preserved", paid is not None and paid["invoice_id"] == "inv-paid-1")
        check("paid amount preserved", paid is not None and paid["grand_total"] == "25000000")
        check("paid mapped status", paid is not None and paid["status"] == "PAID_CLAIMED")

        deleted = conn.execute(
            "SELECT status, notes FROM ggv_invoices WHERE invoice_id='inv-deleted-1'"
        ).fetchone()
        check("deleted mapped void", deleted is not None and deleted["status"] == "VOID")
        check(
            "deleted source status noted",
            deleted is not None and "source_status=DELETED" in (deleted["notes"] or ""),
        )

        draft = conn.execute(
            "SELECT invoice_number, status FROM ggv_invoices WHERE invoice_id='inv-draft-1'"
        ).fetchone()
        check("draft has no number", draft is not None and draft["invoice_number"] is None)
        check("draft status", draft is not None and draft["status"] == "DRAFT")

        nota = conn.execute(
            "SELECT nota_id, amount, workflow_state FROM ggv_notas WHERE nota_id='nota-1'"
        ).fetchone()
        check("nota id preserved", nota is not None and nota["nota_id"] == "nota-1")
        check("nota amount preserved", nota is not None and nota["amount"] == "500000")
        check("nota workflow", nota is not None and nota["workflow_state"] == "needs_review")
        conn.close()

        second = repair.run_import(target, source_db=source)
        check("second invoices skipped", second["invoices"]["imported"] == 0)
        check(
            "second invoices already_exists",
            second["invoices"]["skipped"].get("already_exists") == 3,
            str(second["invoices"]["skipped"]),
        )
        check("second notas skipped", second["notas"]["imported"] == 0)
        check(
            "second notas already_exists",
            second["notas"]["skipped"].get("already_exists") == 1,
            str(second["notas"]["skipped"]),
        )

        conn = sqlite3.connect(str(target))
        inv_count = conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0]
        nota_count = conn.execute("SELECT COUNT(*) FROM ggv_notas").fetchone()[0]
        conn.close()
        check("invoice count stable", inv_count == 3, str(inv_count))
        check("nota count stable", nota_count == 1, str(nota_count))


def test_live_read_only_snapshot() -> None:
    live = ROOT / "catalog" / "content_library.sqlite"
    if not live.is_file():
        check("live catalog present", False, "missing")
        return
    conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
    try:
        before = repair.target_counts(conn)
        check("live read ok", isinstance(before, dict))
    finally:
        conn.close()


def main() -> int:
    test_import_and_idempotency()
    test_live_read_only_snapshot()
    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
