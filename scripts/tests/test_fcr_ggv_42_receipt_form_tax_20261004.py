#!/usr/bin/env python3
"""FCR-GGV-42 — receipt confirm form optional tax on ggv-finance.html.

HTML contract checks plus schema-only temp sqlite for form-shaped confirm bodies.
Never writes catalog/content_library.sqlite.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
HTML = ROOT / "dashboards" / "ggv-finance.html"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def apply_migrations(conn: sqlite3.Connection) -> None:
    for name in (
        "005_org_registry.sql",
        "006_person_auth_identity.sql",
        "007_role_position_assignment.sql",
        "008_assignment_scope.sql",
        "009_rbac_permissions.sql",
    ):
        conn.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))


def seed_ggv_finance_reviewer(conn: sqlite3.Connection) -> str:
    from core import ggv_finance_nota as fin

    ts = "2026-10-04T00:00:00Z"
    person_id = f"PERS-FCR-GGV-42-{uuid.uuid4().hex[:10].upper()}"
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES ('ENT-GGV', 'GGV fixture', 'GGV', 'operating', 'ACTIVE', 1, ?, ?)
        """,
        (ts, ts),
    )
    for role_id, label in (
        ("ROLE-MATT", "Owner fixture"),
        ("ROLE-CONTENT-MGMT", "Content lead fixture"),
    ):
        conn.execute(
            """
            INSERT INTO org_roles (
              role_id, display_name, department_id, role_type, status, created_at, updated_at
            ) VALUES (?, ?, NULL, 'OPERATING', 'ACTIVE', ?, ?)
            """,
            (role_id, label, ts, ts),
        )
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'FCR GGV 42 reviewer', NULL, 'ACTIVE', ?, ?)
        """,
        (person_id, ts, ts),
    )
    fin.ensure_schema(conn)
    fin.ensure_rbac(conn, commit=False)
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (
            f"ASG-FCR-GGV-42-{uuid.uuid4().hex[:8].upper()}",
            person_id,
            fin.POSITION_EXTERNAL_ACCOUNTANT,
            ts,
            ts,
            ts,
        ),
    )
    conn.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
        """,
        (
            conn.execute(
                "SELECT assignment_id FROM org_assignments WHERE person_id=?",
                (person_id,),
            ).fetchone()[0],
            fin.SCOPE_GGV_FINANCE,
            ts,
            ts,
            ts,
        ),
    )
    conn.commit()
    return person_id


def insert_receipt(conn: sqlite3.Connection, receipt_key: str) -> None:
    ts = "2026-10-04T08:00:00Z"
    conn.execute(
        """
        INSERT INTO ggv_receipt_accounting (
          receipt_key, entity_id, vault_filename, vault_queue, vault_path,
          content_sha256, accounting_queue, extraction_json,
          human_confirmed_json, duplicate_of, missing_evidence,
          bank_match_proposed, bank_match_confirmed,
          confirmed_by_person_id, confirmed_at, upload_date,
          created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            receipt_key,
            "ENT-GGV",
            receipt_key,
            "processed",
            str(ROOT / "state" / "missing-evidence.jpg"),
            None,
            "needs_review",
            json.dumps({"vendor": "Fixture Vendor", "amount": "1000", "tax": "9000"}),
            None,
            None,
            1,
            None,
            0,
            None,
            None,
            "2026-10-04",
            ts,
            ts,
        ),
    )
    conn.commit()


def form_confirm_body(*, tax: str | None) -> dict[str, str]:
    """Mirror ggv-finance.html rx-confirm: tax key only when trimmed non-empty."""
    body = {
        "vendor": "Vendor Form",
        "amount": "50000",
        "date": "2026-05-20",
        "category": "Supplies",
        "account_code": "6100",
        "notes": "form-shaped body",
    }
    if tax is not None:
        tax_val = tax.strip()
        if tax_val:
            body["tax"] = tax_val
    return body


def test_html_contract() -> None:
    html = HTML.read_text(encoding="utf-8")
    check("receipt detail has Tax label input", 'id="rx-tax"' in html and "<label>Tax<input id=\"rx-tax\"" in html)
    check(
        "rx-tax populates from human or extraction",
        '$("rx-tax").value = h.tax || (r.extraction && r.extraction.tax)' in html,
    )
    check(
        "confirm omits tax when blank",
        'const taxVal = ($("rx-tax").value || "").trim();' in html
        and "if (taxVal) body.tax = taxVal;" in html,
    )
    check(
        "confirm POST still targets receipts confirm route",
        bool(re.search(r"/api/ggv/finance/accounting/receipts/\$\{encodeURIComponent\(rxSelectedKey\)\}/confirm", html)),
    )


def noop_sync(**_kw: object) -> dict[str, object]:
    return {"ok": True, "synced": 0}


def test_form_shaped_confirm_bodies() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.ggv_bank_statement1 as gbs
    import core.ggv_receipt_accounting1 as gra

    td = Path(tempfile.mkdtemp(prefix="fcr-ggv-42-", dir=str(ROOT / "state")))
    db_path = td / "content_library.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    key_blank = f"fcr-ggv-42-blank_{uuid.uuid4().hex[:12]}_ggv_receipt_test.jpg"
    key_tax = f"fcr-ggv-42-tax_{uuid.uuid4().hex[:12]}_ggv_receipt_test.jpg"
    tax_amount = "11000"

    orig_sync = gra.sync_vault_receipts
    gra.sync_vault_receipts = noop_sync  # type: ignore[assignment]

    try:
        apply_migrations(conn)
        reviewer = seed_ggv_finance_reviewer(conn)
        gra.ensure_schema(conn)
        gbs.ensure_schema(conn)
        insert_receipt(conn, key_blank)
        insert_receipt(conn, key_tax)

        blank_body = form_confirm_body(tax="")
        check("form-shaped blank body omits tax key", "tax" not in blank_body)
        blank_confirm = gra.confirm_receipt(
            verified_person_id=reviewer,
            receipt_key=key_blank,
            body=blank_body,
            conn=conn,
        )
        blank_human = (blank_confirm.get("receipt") or {}).get("human_confirmed") or {}
        check("omitted tax stores null", blank_human.get("tax") is None)

        taxed_body = form_confirm_body(tax=tax_amount)
        check("form-shaped taxed body includes tax", taxed_body.get("tax") == tax_amount)
        taxed_confirm = gra.confirm_receipt(
            verified_person_id=reviewer,
            receipt_key=key_tax,
            body=taxed_body,
            conn=conn,
        )
        taxed_human = (taxed_confirm.get("receipt") or {}).get("human_confirmed") or {}
        check("supplied tax stored", taxed_human.get("tax") == tax_amount)
    finally:
        gra.sync_vault_receipts = orig_sync
        conn.close()


def main() -> int:
    test_html_contract()
    test_form_shaped_confirm_bodies()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
