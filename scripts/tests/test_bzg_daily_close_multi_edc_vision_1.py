#!/usr/bin/env python3
"""BZG-DAILY-CLOSE-MULTI-EDC-VISION-1 — engineering proof (Beta, temp DB).

Decision: 2026-09-17 Uma Blu Daily Close (extend) + Owner order MULTI-EDC-VISION-20261002.
Covers: 1/3 receipts, EDC-only, QRIS-only, both, unused terminal, vision extract,
wrong extract edited, low-confidence, ESB receipt, API mismatch, duplicate warn,
totals, phone workflow strings, evidence/audit. No invented TIDs/tolerances.
"""
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
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
VC_PY = SCRIPTS / "core" / "venue_close.py"
BZG_PY = SCRIPTS / "core" / "bzg_daily_close.py"
VISION_PY = SCRIPTS / "core" / "bzg_close_vision.py"
SERVE = SCRIPTS / "serve_beta.py"
UI = ROOT / "dashboards" / "uma-blu-close.html"

PASS = 0
FAIL = 0
TS = "2026-10-02T00:00:00+08:00"


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


def make_esb(
    path: Path,
    *,
    cash: float = 100000.0,
    card: float = 50000.0,
    qris: float = 25000.0,
    biz_date: str = "2026-10-01",
) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        pays = []
        if cash:
            pays.append({"paymentMethodTypeName": "CASH", "paymentAmount": cash})
        if card:
            pays.append({"paymentMethodTypeName": "CARD", "paymentAmount": card})
        if qris:
            pays.append({"paymentMethodTypeName": "QRIS", "paymentAmount": qris})
        total = cash + card + qris
        raw = {
            "branchCode": "BLZ",
            "salesNum": "S1",
            "billNum": "B1",
            "statusName": "Finished",
            "grandTotal": total,
            "paymentTotal": total,
            "salesPayments": pays,
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", biz_date, json.dumps(raw), "2026-10-01T20:00:00+08:00"),
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


def seed_optional_terminals(conn: sqlite3.Connection) -> None:
    """Optional configured terminals for unused-terminal test — not inventing live TIDs."""
    for tid, label, bank in (
        ("TERM-TEST-A", "Terminal A", "Bank A"),
        ("TERM-TEST-B", "Terminal B", "Bank B"),
        ("TERM-TEST-C", "Terminal C", "Bank C"),
    ):
        conn.execute(
            """
            INSERT OR REPLACE INTO venue_close_edc_terminals (
              terminal_config_id, outlet_id, terminal_label, acquirer_label,
              status, note, created_at, updated_at
            ) VALUES (?, 'BZG-UMA', ?, ?, 'CONFIGURED', 'test-only', ?, ?)
            """,
            (tid, label, bank, TS, TS),
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

    bzg_src = BZG_PY.read_text(encoding="utf-8")
    vision_src = VISION_PY.read_text(encoding="utf-8")
    serve_src = SERVE.read_text(encoding="utf-8")
    ui_src = UI.read_text(encoding="utf-8")
    esb_src = (SCRIPTS / "core" / "esb_close_snapshot.py").read_text(encoding="utf-8")

    check("extends venue_close engine", "engine" in bzg_src and "venue_close" in bzg_src)
    check("ai_is_not_accounting_truth", "ai_is_not_accounting_truth" in bzg_src)
    check("qris never merged", "qris_never_merged_into_card" in bzg_src)
    check("staff_ready false", '"staff_ready": False' in bzg_src or "'staff_ready': False" in bzg_src)
    check("human_commissioned false", '"human_commissioned": False' in bzg_src)
    check("no invented terminals flag", "invented_edc_terminals" in bzg_src)
    check("API edc-receipt extract", "/api/venue-close/edc-receipt-extract" in serve_src)
    check("API edc-receipt confirm", "/api/venue-close/edc-receipt" in serve_src)
    check("API esb-receipt", "/api/venue-close/esb-receipt" in serve_src)
    check("API recon-board", "recon-board" in serve_src)
    check("phone UI max-width", "max-width: 480px" in ui_src)
    check("phone Add EDC Receipt", "Add EDC Receipt" in ui_src)
    check("phone Looks Correct", "Looks Correct" in ui_src)
    check("phone recon board", "Reconciliation board" in ui_src)
    check("ESB classifies QRIS", 'return "QRIS"' in esb_src)
    check("vision low confidence no invent", "low_confidence_does_not_invent" in vision_src)

    live = sqlite3.connect(str(LIVE_DB))
    live_pol = live.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    live.close()
    check("live ACTIVE variance policies=0", live_pol == 0, str(live_pol))

    td = Path(tempfile.mkdtemp(prefix="bzg-medc-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    make_esb(esb_path)

    uma_mig = load_mod(UMA_MIG, "migrate_uma_blu_daily_close")
    uma_mig.DB = tmp_db
    check("uma migrate", uma_mig.main() == 0)

    mig031 = load_mod(MIG031, "migrate_bzg_daily_close_till_edc_1")
    mig031.DB = tmp_db
    check("031 migrate", mig031.main() == 0)

    mig032 = load_mod(MIG032, "migrate_bzg_daily_close_multi_edc_vision_1")
    mig032.DB = tmp_db
    check("032 migrate exit 0", mig032.main() == 0)
    check("032 migrate idempotent", mig032.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    check(
        "032 schema stamped",
        bool(
            conn.execute(
                "SELECT 1 FROM schema_migrations WHERE id='032_bzg_daily_close_multi_edc_vision'"
            ).fetchone()
        ),
    )
    for t in (
        "venue_close_edc_receipts",
        "venue_close_esb_closing_receipts",
        "venue_close_vision_events",
    ):
        check(f"table {t}", bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()))
    n_en = conn.execute(
        "SELECT COUNT(*) FROM venue_close_outlet_config WHERE human_close_enabled=1"
    ).fetchone()[0]
    check("only Uma human_close_enabled", n_en == 1, str(n_en))
    n_act = conn.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    check("no ACTIVE variance policies", n_act == 0, str(n_act))
    seed_test_closer(conn)
    seed_optional_terminals(conn)
    conn.close()

    vc, bzg, vision = wire(tmp_db, esb_path)

    ov = bzg.overview()
    check("overview staff_ready false", ov.get("staff_ready") is False)
    check("overview human_commissioned false", ov.get("human_commissioned") is False)
    check("overview ai honesty", ov.get("ai_is_not_accounting_truth") is True)

    opened = bzg.open_human_close(
        "2026-10-01",
        verified_person_id="PERS-TEST-CLOSER",
        outlet_id="BZG-UMA",
    )
    cid = opened["close_id"]
    captured = vc.capture_esb_snapshot(cid, verified_person_id="PERS-TEST-CLOSER")
    totals = captured.get("esb_totals") or {}
    check("ESB cash", float(totals.get("cash_from_payments") or 0) == 100000.0)
    check("ESB card separate", float(totals.get("card_from_payments") or 0) == 50000.0)
    check("ESB QRIS separate", float(totals.get("qris_from_payments") or 0) == 25000.0)
    check("ESB qris never merged flag", totals.get("qris_never_merged_into_card") is True)

    # --- ESB closing receipt extraction + API mismatch ---
    esb_draft = bzg.extract_esb_closing_receipt_draft(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        fixture_fields={
            "cash_amount": 90000.0,  # mismatch vs API 100000
            "edc_card_amount": 50000.0,
            "qris_amount": 25000.0,
            "ocr_confidence": 0.88,
        },
    )
    check("ESB receipt extraction", esb_draft.get("ok") is True and esb_draft.get("vision_event_id"))
    check(
        "ESB API vs receipt mismatch preview",
        (esb_draft.get("api_mismatch_preview") or {}).get("api_mismatch") is True,
    )
    esb_conf = bzg.confirm_esb_closing_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        action="edit",
        object_ref="photo://esb-close-20261001",
        cash_amount=90000.0,
        edc_card_amount=50000.0,
        qris_amount=25000.0,
        extracted=esb_draft.get("extracted"),
        vision_event_id=esb_draft.get("vision_event_id"),
        allow_test_write=True,
    )
    check("ESB receipt confirmed", esb_conf.get("ok") is True)
    check("ESB mismatch visible", esb_conf.get("api_mismatch") is True)
    check(
        "ESB API totals preserved (no silent overwrite)",
        float((esb_conf.get("esb_api_totals_preserved") or {}).get("cash_from_payments") or 0)
        == 100000.0,
    )

    # --- Vision image extraction (fixture = approved test path) ---
    draft1 = bzg.extract_edc_receipt_draft(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        image_bytes=b"fake-jpeg-bytes-edc-1",
        fixture_fields={
            "acquirer_label": "Mandiri",
            "edc_card_amount": 30000,
            "qris_amount": 0,
            "settlement_batch_date": "2026-10-01",
            "batch_ref": "BATCH-M1",
            "ocr_confidence": 0.9,
            "terminal_config_id": "TERM-TEST-A",
        },
    )
    check("image extraction draft", draft1.get("ok") is True and draft1.get("extracted"))
    check("ai not truth on draft", draft1.get("ai_is_not_accounting_truth") is True)

    # EDC-only receipt #1
    r1 = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="Mandiri",
        edc_card_amount=30000,
        qris_amount=0,
        action="looks_correct",
        object_ref="photo://edc-mandiri-1",
        content_hash=draft1.get("content_hash"),
        settlement_batch_date="2026-10-01",
        batch_ref="BATCH-M1",
        terminal_config_id="TERM-TEST-A",
        extracted=draft1.get("extracted"),
        vision_event_id=draft1.get("vision_event_id"),
        allow_test_write=True,
    )
    check("one receipt EDC-only", r1.get("ok") and r1["receipt_totals"]["confirmed_receipt_count"] == 1)
    check("EDC-only TOTAL_EDC", r1["receipt_totals"]["TOTAL_EDC"] == 30000.0)
    check("EDC-only TOTAL_QRIS 0", r1["receipt_totals"]["TOTAL_QRIS"] == 0.0)

    # Wrong extraction edited
    bad_draft = bzg.extract_edc_receipt_draft(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        fixture_fields={
            "acquirer_label": "BCA",
            "edc_card_amount": 999999,  # wrong
            "qris_amount": 5000,
            "ocr_confidence": 0.7,
            "settlement_batch_date": "2026-10-01",
            "batch_ref": "BATCH-BCA",
        },
    )
    r2 = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="BCA",
        edc_card_amount=999999,
        qris_amount=5000,
        action="edit",
        object_ref="photo://edc-bca-1",
        settlement_batch_date="2026-10-01",
        batch_ref="BATCH-BCA",
        terminal_config_id="TERM-TEST-B",
        extracted=bad_draft.get("extracted"),
        confirmed_overrides={"edc_card_amount": 15000, "qris_amount": 5000},
        vision_event_id=bad_draft.get("vision_event_id"),
        allow_test_write=True,
    )
    check("wrong extraction edited", r2.get("human_confirm_status") == "EDITED")
    check("edited amounts used", r2["edc_card_amount"] == 15000.0 and r2["qris_amount"] == 5000.0)
    check(
        "extracted preserved after edit",
        (r2["edc_receipts"][-1].get("extracted") or {}).get("edc_card_amount") == 999999
        or (r2["edc_receipts"][-1].get("extracted") or {}).get("edc_card_amount") == 999999.0,
    )

    # QRIS-only receipt #3
    r3 = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="BRI",
        edc_card_amount=0,
        qris_amount=20000,
        action="confirm",
        object_ref="photo://edc-bri-qris",
        settlement_batch_date="2026-10-01",
        batch_ref="BATCH-BRI-Q",
        allow_test_write=True,
    )
    check("three receipts", r3["receipt_totals"]["confirmed_receipt_count"] == 3)
    check("QRIS-only receipt", r3["edc_card_amount"] == 0.0 and r3["qris_amount"] == 20000.0)

    # Both on same receipt (extra day path) — also totals
    rt = bzg.receipt_totals(cid)
    check("TOTAL_EDC across receipts", rt["TOTAL_EDC"] == 45000.0, str(rt["TOTAL_EDC"]))
    check("TOTAL_QRIS across receipts", rt["TOTAL_QRIS"] == 25000.0, str(rt["TOTAL_QRIS"]))
    check(
        "TOTAL_CARD_QRIS",
        rt["TOTAL_CARD_QRIS"] == 70000.0,
        str(rt["TOTAL_CARD_QRIS"]),
    )

    # Both EDC+QRIS on one receipt (fresh close)
    make_esb(esb_path, cash=80000, card=10000, qris=10000, biz_date="2026-10-03")
    o3 = bzg.open_human_close(
        "2026-10-03", verified_person_id="PERS-TEST-CLOSER", outlet_id="BZG-UMA"
    )
    c3 = o3["close_id"]
    vc.capture_esb_snapshot(c3, verified_person_id="PERS-TEST-CLOSER")
    both = bzg.confirm_edc_receipt(
        c3,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="FreeText Bank",
        edc_card_amount=10000,
        qris_amount=10000,
        action="confirm",
        object_ref="photo://both-1",
        settlement_batch_date="2026-10-03",
        allow_test_write=True,
    )
    check("both EDC+QRIS same receipt", both["receipt_total"] == 20000.0)
    check("free-text bank without terminal config", both.get("ok") is True)

    # Unused configured terminal (A used on day1; C unused)
    unused = bzg.unused_configured_terminals(cid, "BZG-UMA")
    unused_ids = {t["terminal_config_id"] for t in unused["unused_terminals"]}
    check("unused configured terminal C", "TERM-TEST-C" in unused_ids, str(unused_ids))
    check("no fake placeholders", unused.get("no_fake_placeholders") is True)
    check("used terminal A not in unused", "TERM-TEST-A" not in unused_ids)

    # Low confidence — blank/flag, no invent
    low = vision.extract_edc_receipt(
        fixture_fields={
            "acquirer_label": "MaybeBank",
            "edc_card_amount": 12345,
            "qris_amount": 678,
            "ocr_confidence": 0.2,
        }
    )
    xf = low.get("extracted") or {}
    check("low-confidence flag", xf.get("low_confidence_flag") is True or xf.get("ocr_confidence_band") == "LOW")
    check("low-confidence blanks inventable", xf.get("edc_card_amount") is None and xf.get("qris_amount") is None)
    check("low-confidence not invented", xf.get("invented") is False)

    # Duplicate warning — no silent delete
    dup = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="Mandiri",
        edc_card_amount=30000,
        qris_amount=0,
        action="confirm",
        object_ref="photo://edc-mandiri-DUP",
        content_hash=draft1.get("content_hash"),
        settlement_batch_date="2026-10-01",
        batch_ref="BATCH-M1",
        allow_test_write=True,
    )
    check("duplicate warning", dup.get("duplicate_warn") is True)
    check(
        "duplicate superseded not double-counted",
        dup["receipt_totals"]["confirmed_receipt_count"] == 3,
        str(dup["receipt_totals"]["confirmed_receipt_count"]),
    )
    check(
        "duplicate TOTAL_EDC unchanged",
        dup["receipt_totals"]["TOTAL_EDC"] == 45000.0,
        str(dup["receipt_totals"]["TOTAL_EDC"]),
    )
    mandiri_hist = [
        r
        for r in dup.get("edc_receipts") or []
        if (r.get("acquirer_label") or "").upper().startswith("MAND")
    ]
    check(
        "duplicate mandiri history kept",
        len(mandiri_hist) >= 2,
        str(len(mandiri_hist)),
    )

    # Recon board + evidence completeness
    bzg.attach_till_with_z_report(
        cid,
        declared_cash_amount=100000.0,
        verified_person_id="PERS-TEST-CLOSER",
        object_ref="photo://z-20261001",
        allow_test_write=True,
    )
    board = bzg.recon_board(cid)
    check("recon board ok", board.get("ok") is True)
    check("recon cash expected", float(board["cash"]["esb_expected"]) == 100000.0)
    check("recon EDC confirmed", float(board["edc"]["receipts_confirmed"]) >= 45000.0)
    check("recon QRIS separate", board["qris_never_merged_into_card"] is True)
    check("recon evidence ESB receipt", board["evidence_completeness"]["esb_closing_receipt_confirmed"] is True)
    check("recon evidence complete path", board["evidence_complete"] is True)
    check("recon API mismatch flag", board.get("esb_api_vs_receipt_mismatch") is True)

    # Enrich / phone workflow
    enriched = bzg.enrich_close(vc.get_close(cid))
    check("enrich has edc_receipts", isinstance(enriched.get("edc_receipts"), list))
    check("enrich has recon_board", isinstance(enriched.get("recon_board"), dict))
    check("phone workflow UI strings", "Read receipt" in ui_src and "Reconciliation board" in ui_src)

    # Evidence / audit trail
    c2 = sqlite3.connect(str(tmp_db))
    c2.row_factory = sqlite3.Row
    vis_n = c2.execute(
        "SELECT COUNT(*) FROM venue_close_vision_events WHERE close_id=?", (cid,)
    ).fetchone()[0]
    check("vision events recorded", vis_n >= 2, str(vis_n))
    evid_n = c2.execute(
        """
        SELECT COUNT(*) FROM core_evidence_records
        WHERE governed_object_id=? AND evidence_type IN ('edc_settlement_slip','esb_closing_receipt')
        """,
        (cid,),
    ).fetchone()[0]
    check("evidence bound for receipts", evid_n >= 2, str(evid_n))
    aud_count = int(
        c2.execute(
            """
            SELECT COUNT(*) FROM core_audit_events
            WHERE resource_id=? AND action LIKE 'venue_close.%receipt%'
            """,
            (cid,),
        ).fetchone()[0]
    )
    check("audit events for receipt flow", aud_count >= 2, str(aud_count))
    c2.close()

    # Live still clean
    live2 = sqlite3.connect(str(LIVE_DB))
    live_pol2 = live2.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    live_term = live2.execute("SELECT COUNT(*) FROM venue_close_edc_terminals").fetchone()[0]
    live2.close()
    check("live ACTIVE policies still 0", live_pol2 == 0)
    check("live terminals not invented by tests", live_term == 0, str(live_term))

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
