#!/usr/bin/env python3
"""GGV-BILLS-605 — schema-only temp sqlite. Never copies live catalog."""
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

from core import ggv_bills_import1 as bills  # noqa: E402
from core import ggv_empty_chain_repair1 as repair  # noqa: E402
from core import ggv_finance_invoice as inv  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402

PASS = 0
FAIL = 0
TS = "2026-10-05T06:30:00+08:00"


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
          created_by TEXT,
          amount_due TEXT,
          amount_paid TEXT,
          contact_name TEXT,
          reference TEXT,
          source TEXT
        );
        INSERT INTO bill VALUES (
          'bill-1', 'GGV', 'vend-1', 'B-1', '2026-07-01', '2026-07-15', 'DRAFT',
          '1000000', 'IDR', 'test bill', '2026-08-20 18:05 WITA', 'xero_import',
          '1000000', '0', 'M-Mart', 'Wolf-IMG-1.jpg', 'xero_import'
        );
        INSERT INTO bill VALUES (
          'bill-2', 'GGV', NULL, NULL, '2026-07-02', NULL, 'DELETED',
          NULL, NULL, NULL, '2026-08-21 18:05 WITA', 'xero_import',
          NULL, NULL, 'Unknown Supplier', NULL, 'xero_import'
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

        first = bills.run_import(target, source_db=source)
        check("first import ok", first["bills"]["imported"] == 2, str(first["bills"]))
        check("target table ggv_bills", first["bills"]["target_table"] == "ggv_bills")

        conn = sqlite3.connect(str(target))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM ggv_bills WHERE bill_id='bill-1'"
        ).fetchone()
        check("bill id preserved", row is not None and row["bill_id"] == "bill-1")
        check("amount preserved", row is not None and row["amount"] == "1000000")
        check("contact name preserved", row is not None and row["contact_name"] == "M-Mart")
        check("provenance source_id", row is not None and row["source_id"] == "bill-1")
        check("provenance source_table", row is not None and row["source_table"] == "bill")
        check("provenance source_status", row is not None and row["source_status"] == "DRAFT")
        check("provenance source column", row is not None and row["source"] == "xero_import")
        check(
            "provenance file path set",
            row is not None and str(source) in (row["source_file_path"] or ""),
        )

        sparse = conn.execute(
            "SELECT amount, currency, bill_number FROM ggv_bills WHERE bill_id='bill-2'"
        ).fetchone()
        check("sparse amount null not zero", sparse is not None and sparse["amount"] is None)
        check("sparse currency null", sparse is not None and sparse["currency"] is None)
        check("sparse bill_number null", sparse is not None and sparse["bill_number"] is None)

        inv_before = conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0]
        nota_before = conn.execute("SELECT COUNT(*) FROM ggv_notas").fetchone()[0]
        conn.close()

        second = bills.run_import(target, source_db=source)
        check("second import zero", second["bills"]["imported"] == 0)
        check(
            "second already_exists",
            second["bills"]["skipped"].get("already_exists") == 2,
            str(second["bills"]["skipped"]),
        )

        conn = sqlite3.connect(str(target))
        bill_count = conn.execute("SELECT COUNT(*) FROM ggv_bills").fetchone()[0]
        inv_after = conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0]
        nota_after = conn.execute("SELECT COUNT(*) FROM ggv_notas").fetchone()[0]
        conn.close()
        check("bill count stable", bill_count == 2, str(bill_count))
        check("invoices untouched", inv_before == inv_after == 0)
        check("notas untouched", nota_before == nota_after == 0)


def test_empty_chain_repair_delegates() -> None:
    with tempfile.TemporaryDirectory() as td:
        source = Path(td) / "ggv-source-books.sqlite"
        target = Path(td) / "content_library.sqlite"
        _seed_source(source)
        _bootstrap_target(target)

        src = sqlite3.connect(str(source))
        src.row_factory = sqlite3.Row
        tgt = sqlite3.connect(str(target))
        tgt.row_factory = sqlite3.Row
        try:
            result = repair.import_bills(tgt, src)
            tgt.commit()
        finally:
            src.close()
            tgt.close()
        check("repair import uses ggv_bills", result["target_table"] == "ggv_bills")
        check("repair imported bills", result["imported"] == 2, str(result))


def test_live_read_only_snapshot() -> None:
    live = ROOT / "catalog" / "content_library.sqlite"
    if not live.is_file():
        check("live catalog present", False, "missing")
        return
    conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
    try:
        before = bills.target_counts(conn)
        check("live read ok", isinstance(before, dict))
    finally:
        conn.close()


def main() -> int:
    test_import_and_idempotency()
    test_empty_chain_repair_delegates()
    test_live_read_only_snapshot()
    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
