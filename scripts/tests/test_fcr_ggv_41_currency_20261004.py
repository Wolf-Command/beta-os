#!/usr/bin/env python3
"""FCR-GGV-41 — receipt currency field on ggv_receipt_accounting human confirm.

Schema-only temp sqlite. Never writes catalog/content_library.sqlite.
Protected closes and state/bzg-daily-close/receipts/ are not touched.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
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
    person_id = f"PERS-FCR-GGV-41-{uuid.uuid4().hex[:10].upper()}"
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
        VALUES (?, 'FCR GGV 41 reviewer', NULL, 'ACTIVE', ?, ?)
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
            f"ASG-FCR-GGV-41-{uuid.uuid4().hex[:8].upper()}",
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
            json.dumps({"vendor": "Fixture Vendor", "amount": "1000"}),
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


def human_currency_from_row(conn: sqlite3.Connection, receipt_key: str) -> object:
    row = conn.execute(
        "SELECT human_confirmed_json FROM ggv_receipt_accounting WHERE receipt_key=?",
        (receipt_key,),
    ).fetchone()
    if not row or not row[0]:
        return None
    human = json.loads(row[0])
    return human.get("currency")


def noop_sync(**_kw: object) -> dict[str, object]:
    return {"ok": True, "synced": 0}


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.ggv_bank_statement1 as gbs
    import core.ggv_receipt_accounting1 as gra

    td = Path(tempfile.mkdtemp(prefix="fcr-ggv-41-", dir=str(ROOT / "state")))
    db_path = td / "content_library.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    key_blank = f"fcr-ggv-41-blank_{uuid.uuid4().hex[:12]}_ggv_receipt_test.jpg"
    key_currency = f"fcr-ggv-41-cur_{uuid.uuid4().hex[:12]}_ggv_receipt_test.jpg"
    currency_code = "IDR"

    orig_sync = gra.sync_vault_receipts
    gra.sync_vault_receipts = noop_sync  # type: ignore[assignment]

    try:
        apply_migrations(conn)
        reviewer = seed_ggv_finance_reviewer(conn)
        gra.ensure_schema(conn)
        gbs.ensure_schema(conn)

        insert_receipt(conn, key_blank)
        insert_receipt(conn, key_currency)

        blank_confirm = gra.confirm_receipt(
            verified_person_id=reviewer,
            receipt_key=key_blank,
            body={
                "vendor": "Vendor A",
                "amount": "50000",
                "date": "2026-05-20",
                "category": "Supplies",
                "account_code": "6100",
                "notes": "no currency on confirm body",
            },
            conn=conn,
        )
        blank_human = (blank_confirm.get("receipt") or {}).get("human_confirmed") or {}
        check("missing currency stays None not default", blank_human.get("currency") is None)
        check("missing currency not coerced to IDR", blank_human.get("currency") != "IDR")
        check("missing currency not coerced to 0", blank_human.get("currency") != 0)
        check("missing currency not coerced to '0'", blank_human.get("currency") != "0")
        check(
            "SQL readback missing currency blank",
            human_currency_from_row(conn, key_blank) is None,
            str(human_currency_from_row(conn, key_blank)),
        )

        cur_confirm = gra.confirm_receipt(
            verified_person_id=reviewer,
            receipt_key=key_currency,
            body={
                "vendor": "Vendor B",
                "amount": "61000",
                "currency": currency_code,
                "date": "2026-06-01",
                "category": "Supplies",
                "account_code": "6100",
                "notes": "currency included on confirm",
            },
            conn=conn,
        )
        cur_human = (cur_confirm.get("receipt") or {}).get("human_confirmed") or {}
        check("confirm stores currency in human_confirmed", cur_human.get("currency") == currency_code)
        check(
            "get_receipt readback currency",
            (gra.get_receipt(verified_person_id=reviewer, receipt_key=key_currency, conn=conn)
             .get("receipt") or {})
            .get("human_confirmed", {})
            .get("currency")
            == currency_code,
        )
        check(
            "SQL readback currency from human_confirmed_json",
            human_currency_from_row(conn, key_currency) == currency_code,
            str(human_currency_from_row(conn, key_currency)),
        )
        check(
            "currency in confirmed_fields when provided",
            (cur_human.get("confirmed_fields") or {}).get("currency") == currency_code,
        )
        check(
            "currency absent from confirmed_fields when omitted",
            "currency" not in (blank_human.get("confirmed_fields") or {}),
        )

    finally:
        gra.sync_vault_receipts = orig_sync
        conn.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
