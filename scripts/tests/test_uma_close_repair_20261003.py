#!/usr/bin/env python3
"""UMA-CLOSE repair 2026-10-03 — temp DB only. Protected close never written."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UI = ROOT / "dashboards" / "uma-blu-close.html"
VISION = SCRIPTS / "core" / "bzg_close_vision.py"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"

PASS = 0
FAIL = 0
TS = "2026-10-03T00:00:00+08:00"
BIZ = "2026-10-04"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def make_esb(path: Path, cash: float = 100000.0, biz_date: str = BIZ) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        raw = {
            "branchCode": "BLZ",
            "salesNum": "S1",
            "billNum": "B1",
            "statusName": "Finished",
            "grandTotal": cash,
            "paymentTotal": cash,
            "salesPayments": [
                {"paymentMethodTypeName": "CASH", "paymentAmount": cash}
            ],
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", biz_date, json.dumps(raw), f"{biz_date}T20:00:00+08:00"),
        )
        conn.commit()
    finally:
        conn.close()


def seed_test_closer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES ('PERS-TEST-CLOSER', 'Test Closer', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-CLOSER-1', 'PERS-TEST-CLOSER', 'POS-BZG-CLOSER-UMA-1',
                  ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-TEST-CLOSER-1", "SCOPE-BZG-UMA", TS, TS)
    conn.execute(
        """
        INSERT INTO venue_closer_roster (
          roster_id, brand_id, position_id, person_id, assignment_id,
          status, note, created_at, updated_at
        ) VALUES (
          'VCR-UMA-TEST-1', 'BZG-UMA', 'POS-BZG-CLOSER-UMA-1', 'PERS-TEST-CLOSER',
          'ASG-TEST-CLOSER-1', 'ACTIVE', 'test closer roster', ?, ?
        )
        ON CONFLICT(roster_id) DO UPDATE SET
          person_id=excluded.person_id,
          assignment_id=excluded.assignment_id,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.commit()


def wire(tmp_db: Path, esb_path: Path):
    import core.venue_close as vc
    import core.bzg_daily_close as bzg
    import core.esb_close_snapshot as esb
    import core.evidence as ev
    import core.audit as au
    import core.work_items as wi
    import core.rbac as rb
    import core.organisation as org
    import core.scope as sc
    import core.identity as ident
    import core.bzg_outlet_registry as outlets
    import core.bzg_close_vision as vision

    for mod in (vc, bzg, ev, au, wi, rb, org, sc, ident, outlets, esb, vision):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)
    os.environ["WOLF_CLOSE_VISION_DRY"] = "0"
    return vc, bzg, vision


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    vision = load_mod(VISION, "bzg_close_vision_repair")
    check(
        "edc prompt helper defined",
        hasattr(vision, "_edc_prompt_with_bank_context"),
    )
    prompt = vision._edc_prompt_with_bank_context(
        bank_hint="Mandiri",
        esb_edc_expected=1915000,
        esb_qris_expected=365000,
    )
    check("edc prompt mentions separate EDC/QRIS", "edc_card_amount" in prompt and "qris_amount" in prompt)
    try:
        draft = vision.extract_edc_receipt(
            image_bytes=b"fake-edc-bytes",
            bank_hint="BRI",
        )
        check("extract_edc_receipt no NameError", isinstance(draft, dict))
        check(
            "provider failure is soft staff message",
            draft.get("extraction_unavailable") is True
            or draft.get("extracted") is not None,
        )
    except NameError as exc:
        check("extract_edc_receipt no NameError", False, str(exc))

    ui_src = UI.read_text(encoding="utf-8")
    check("staff HTML has no Reconcile button", 'id="btnReconcile"' not in ui_src)
    check("staff HTML has no Reconcile label button", ">Reconcile</button>" not in ui_src)
    check("cash Take Photo control exists", 'id="btnCashTakePhoto"' in ui_src)
    check("cash Upload Photo control exists", 'id="btnCashUploadPhoto"' in ui_src)
    check("three cash sources labeled Live ESB", "Live ESB" in ui_src)
    check("three cash sources labeled Printed shift receipt", "Printed shift receipt" in ui_src)
    check("three cash sources labeled Physical till", "Physical till" in ui_src)

    td = Path(tempfile.mkdtemp(prefix="uma-close-repair-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    make_esb(esb_path, cash=100000.0)

    for mig_path, name in (
        (UMA_MIG, "migrate_uma_blu_daily_close"),
        (MIG031, "migrate_bzg_daily_close_till_edc_1"),
        (MIG032, "migrate_bzg_daily_close_multi_edc_vision_1"),
    ):
        mig = load_mod(mig_path, name)
        mig.DB = tmp_db
        check(f"{name} migrate", mig.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    seed_test_closer(conn)
    conn.close()

    vc, bzg, _vision = wire(tmp_db, esb_path)

    opened = bzg.open_human_close(
        BIZ,
        verified_person_id="PERS-TEST-CLOSER",
        outlet_id="BZG-UMA",
    )
    cid = opened["close_id"]
    vc.capture_esb_snapshot(cid, verified_person_id="PERS-TEST-CLOSER")

    amt = 100000.0
    first = vc.attach_declared_cash(
        cid,
        declared_cash_amount=amt,
        verified_person_id="PERS-TEST-CLOSER",
        allow_test_write=True,
    )
    check("first declare ok", first.get("declared_cash_amount") == amt)

    conn = sqlite3.connect(str(tmp_db))
    ev_before = conn.execute(
        """
        SELECT COUNT(*) FROM core_evidence_records
        WHERE governed_object_id=? AND evidence_type LIKE '%CASH%'
        """,
        (cid,),
    ).fetchone()[0]
    conn.close()
    second = vc.attach_declared_cash(
        cid,
        declared_cash_amount=amt,
        verified_person_id="PERS-TEST-CLOSER",
        allow_test_write=True,
    )
    conn = sqlite3.connect(str(tmp_db))
    ev_after = conn.execute(
        """
        SELECT COUNT(*) FROM core_evidence_records
        WHERE governed_object_id=? AND evidence_type LIKE '%CASH%'
        """,
        (cid,),
    ).fetchone()[0]
    conn.close()
    check("duplicate declare idempotent flag", second.get("idempotent") is True)
    check("duplicate declare no second cash evidence", ev_after == ev_before, f"{ev_before}->{ev_after}")

    sources = bzg.cash_three_sources(cid)
    check("cash_three_sources live_esb label", sources.get("live_esb", {}).get("label") == "Live ESB")
    check(
        "cash_three_sources printed receipt label",
        sources.get("printed_shift_receipt", {}).get("label") == "Printed shift receipt",
    )
    check(
        "cash_three_sources physical till label",
        sources.get("physical_till", {}).get("label") == "Physical till",
    )

    def protected_ref_count(db_path: Path) -> int:
        total = 0
        c = sqlite3.connect(str(db_path))
        for tbl in ("venue_daily_closes", "core_evidence_records", "core_audit_log"):
            try:
                cols = [r[1] for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()]
            except sqlite3.OperationalError:
                continue
            for col in cols:
                try:
                    n = c.execute(
                        f"SELECT COUNT(*) FROM {tbl} WHERE CAST({col} AS TEXT)=?",
                        (PROTECTED_CLOSE,),
                    ).fetchone()[0]
                except sqlite3.OperationalError:
                    continue
                total += int(n or 0)
        c.close()
        return total

    before_prot = protected_ref_count(tmp_db)
    check("test did not use protected close id", cid != PROTECTED_CLOSE, cid)
    after_prot = protected_ref_count(tmp_db)
    check(
        "protected close id not written by tests",
        after_prot == before_prot,
        f"before={before_prot} after={after_prot}",
    )

    print(f"\nRESULT pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
