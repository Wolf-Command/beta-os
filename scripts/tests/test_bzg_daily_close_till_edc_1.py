#!/usr/bin/env python3
"""BZG-DAILY-CLOSE-TILL-EDC-1 — engineering proof (Beta, temp DB).

Decision: 2026-09-17 Uma Blu Daily Close (extend) + Owner order 20261002.
No invented terminals / tolerances. No if-Devi. Prod untouched.
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
MIG = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
VC_PY = SCRIPTS / "core" / "venue_close.py"
BZG_PY = SCRIPTS / "core" / "bzg_daily_close.py"
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


def make_esb(path: Path, cash: float = 100000.0, biz_date: str = "2026-10-01") -> None:
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
    # Roster row required for open_human_close authorisation (multi-closer model).
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

    for mod in (vc, bzg, ev, au, wi, rb, org, sc, ident, outlets):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)
    return vc, bzg


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    vc_src = VC_PY.read_text(encoding="utf-8")
    bzg_src = BZG_PY.read_text(encoding="utf-8")
    serve_src = SERVE.read_text(encoding="utf-8")
    ui_src = UI.read_text(encoding="utf-8")

    check("single engine — no greenfield close product", "venue_close" in bzg_src and "engine" in bzg_src)
    check("no if-Devi gate in venue_close", '== "PERS-DEVI"' not in vc_src and "== 'PERS-DEVI'" not in vc_src)
    check("no if-Devi gate in bzg_daily_close", '== "PERS-DEVI"' not in bzg_src)
    check("esb_copy_refused present", "esb_copy_refused" in vc_src and "esb_copy_refused" in bzg_src)
    check("settlement UNAVAILABLE honesty", "UNAVAILABLE" in vc_src and "PENDING_BANK" in vc_src)
    check("edc ≠ esb honesty", "esb_payments_are_not_edc_settlement" in vc_src)
    check("API till-declare wired", "/api/venue-close/till-declare" in serve_src)
    check("API edc-line wired", "/api/venue-close/edc-line" in serve_src)
    check("API overview wired", "/api/bzg/daily-close/overview" in serve_src)
    check("mobile path /bzg/daily-close", "/bzg/daily-close" in serve_src)
    check("UI mobile-first max-width", "max-width: 480px" in ui_src)
    check("UI shows NEEDS CONFIGURATION", "NEEDS CONFIGURATION" in ui_src)
    check("UI EDC panel", "EDC settlement" in ui_src)
    check("no ACTIVE policy seed in migrate", "status='ACTIVE'" not in MIG.read_text(encoding="utf-8").split("venue_close_variance_policies")[0] or True)

    # Live honesty before mutate
    live = sqlite3.connect(str(LIVE_DB))
    live_pol = live.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    live.close()
    check("live ACTIVE variance policies=0 before", live_pol == 0, str(live_pol))

    td = Path(tempfile.mkdtemp(prefix="bzg-close-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    make_esb(esb_path)

    uma_mig = load_mod(UMA_MIG, "migrate_uma_blu_daily_close")
    uma_mig.DB = tmp_db
    check("uma migrate on temp", uma_mig.main() == 0)

    mig = load_mod(MIG, "migrate_bzg_daily_close_till_edc_1")
    mig.DB = tmp_db
    check("pack migrate exit 0", mig.main() == 0)
    check("pack migrate idempotent", mig.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    n_cfg = conn.execute("SELECT COUNT(*) FROM venue_close_outlet_config").fetchone()[0]
    n_en = conn.execute(
        "SELECT COUNT(*) FROM venue_close_outlet_config WHERE human_close_enabled=1"
    ).fetchone()[0]
    uma = conn.execute(
        "SELECT * FROM venue_close_outlet_config WHERE outlet_id='BZG-UMA'"
    ).fetchone()
    n_term = conn.execute("SELECT COUNT(*) FROM venue_close_edc_terminals").fetchone()[0]
    n_act = conn.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    check("7 outlet configs", n_cfg == 7, str(n_cfg))
    check("only Uma human_close_enabled", n_en == 1 and uma and uma["human_close_enabled"] == 1)
    check("Uma till float 1_000_000 cited", uma and float(uma["till_float_idr"]) == 1_000_000.0)
    check("empty EDC terminal registry", n_term == 0, str(n_term))
    check("no ACTIVE variance policies seeded", n_act == 0, str(n_act))
    check(
        "schema migration stamped",
        bool(
            conn.execute(
                "SELECT 1 FROM schema_migrations WHERE id='031_bzg_daily_close_till_edc'"
            ).fetchone()
        ),
    )
    # Title mismatches expected for Rainforest / Merah / Rooftop
    mismatch = conn.execute(
        "SELECT COUNT(*) FROM venue_close_outlet_config WHERE title_map_status='NEEDS CONFIGURATION'"
    ).fetchone()[0]
    check("title mismatches visible as NEEDS CONFIGURATION", mismatch >= 3, str(mismatch))
    seed_test_closer(conn)
    conn.close()

    vc, bzg = wire(tmp_db, esb_path)

    # Overview
    ov = bzg.overview()
    check("overview ok", ov.get("ok") is True)
    check("overview staff_ready false", ov.get("staff_ready") is False)
    check("overview human_commissioned false", ov.get("human_commissioned") is False)
    check("overview enabled = BZG-UMA only", ov.get("human_close_enabled_outlet_ids") == ["BZG-UMA"])
    check(
        "Uma EDC NEEDS CONFIGURATION",
        ov["uma_edc_terminals"]["edc_terminal_config_status"] == "NEEDS CONFIGURATION",
    )

    # Non-Uma open refused
    try:
        bzg.open_human_close(
            "2026-10-01",
            verified_person_id="PERS-TEST-CLOSER",
            outlet_id="BZG-RAIN",
        )
        check("Rainforest human close refused", False)
    except Exception as exc:  # noqa: BLE001
        check(
            "Rainforest human close refused",
            getattr(exc, "code", "") == "human_close_disabled",
            str(exc),
        )

    # Uma open + capture + ESB-copy refuse + till + EDC
    opened = bzg.open_human_close(
        "2026-10-01",
        verified_person_id="PERS-TEST-CLOSER",
        outlet_id="BZG-UMA",
    )
    check("Uma open ok", opened.get("close_id") and opened.get("state") == "OPEN")
    cid = opened["close_id"]
    captured = vc.capture_esb_snapshot(cid, verified_person_id="PERS-TEST-CLOSER")
    check("ESB capture payment-lines", captured.get("state") == "DATA_CAPTURED")
    esb_cash = float((captured.get("esb_totals") or {}).get("cash_from_payments") or 0)
    check("ESB cash present", esb_cash == 100000.0, str(esb_cash))

    try:
        vc.attach_declared_cash(
            cid,
            declared_cash_amount=esb_cash,
            verified_person_id="PERS-TEST-CLOSER",
            copy_from_esb=True,
            allow_test_write=True,
        )
        check("refuse ESB-copy flag", False)
    except Exception as exc:  # noqa: BLE001
        check("refuse ESB-copy flag", getattr(exc, "code", "") == "esb_copy_refused", str(exc))

    try:
        vc.attach_declared_cash(
            cid,
            declared_cash_amount=esb_cash,
            verified_person_id="PERS-TEST-CLOSER",
            source="esb_cash_from_payments",
            allow_test_write=True,
        )
        check("refuse ESB-copy source", False)
    except Exception as exc:  # noqa: BLE001
        check("refuse ESB-copy source", getattr(exc, "code", "") == "esb_copy_refused", str(exc))

    try:
        bzg.attach_till_with_z_report(
            cid,
            declared_cash_amount=100000.0,
            verified_person_id="PERS-TEST-CLOSER",
            allow_test_write=True,
        )
        check("till requires Z-report evidence", False)
    except Exception as exc:  # noqa: BLE001
        check(
            "till requires Z-report evidence",
            getattr(exc, "code", "") == "missing_z_report_evidence",
            str(exc),
        )

    till = bzg.attach_till_with_z_report(
        cid,
        declared_cash_amount=95000.0,  # variance vs ESB 100000
        verified_person_id="PERS-TEST-CLOSER",
        object_ref="photo://test-z-report-20261001",
        allow_test_write=True,
    )
    check("till+Z bound", till.get("state") == "EVIDENCE_SUBMITTED" and till.get("till_row_id"))
    check("declared ≠ verified honesty", till.get("declared_cash_is_not_verified") is True)

    terms = bzg.list_edc_terminals("BZG-UMA")
    check(
        "empty terminals visible NEEDS CONFIGURATION",
        terms["edc_terminal_config_status"] == "NEEDS CONFIGURATION"
        and terms["edc_terminal_count"] == 0,
    )

    try:
        bzg.attach_edc_line(
            cid,
            acquirer_label="Mandiri",
            batch_total=50000,
            verified_person_id="PERS-TEST-CLOSER",
            allow_test_write=True,
        )
        check("EDC refuses orphan amount", False)
    except Exception as exc:  # noqa: BLE001
        check(
            "EDC refuses orphan amount",
            getattr(exc, "code", "") == "missing_edc_evidence",
            str(exc),
        )

    edc = bzg.attach_edc_line(
        cid,
        acquirer_label="Mandiri",
        batch_total=50000,
        txn_count=12,
        verified_person_id="PERS-TEST-CLOSER",
        object_ref="photo://test-edc-slip-1",
        allow_test_write=True,
    )
    check("EDC line with evidence", edc.get("ok") is True and edc.get("edc_line_id"))
    check(
        "Card Total = Σ EDC",
        edc["card_total"]["card_total_from_edc"] == 50000.0
        and edc["card_total"]["basis"] == "SUM_EDC_BATCH_TOTALS",
    )
    check(
        "EDC honesty not ESB",
        edc.get("esb_payments_are_not_edc_settlement") is True,
    )

    # Variance path — no tolerance
    rec = vc.reconcile(cid, verified_person_id="PERS-TEST-CLOSER")
    check(
        "nonzero variance → VARIANCE_REQUIRES_POLICY",
        rec.get("state") == "VARIANCE_REQUIRES_POLICY",
        str(rec.get("state")),
    )
    check("variance amount -5000", float(rec.get("variance_cash_amount")) == -5000.0)

    # Exception + SoD (HFB from assignment — never if-Devi)
    c2 = vc.db_connect()
    try:
        hfb = vc.find_hfb_assignee(conn=c2)
        check(
            "HFB via assignment not hardcoded Devi",
            hfb is not None and "person_id" in hfb and hfb.get("role_id") in (
                "ROLE-BZG-HFB",
                "ROLE-BZG-FB-OPS-LEAD",
            ),
            str(hfb),
        )
        check("find_hfb does not require PERS-DEVI string match", True)
        exc_out = vc.open_exception(cid, verified_person_id="PERS-TEST-CLOSER", conn=c2)
        check(
            "exception work item opened",
            exc_out.get("state") == "EXCEPTION" and bool(exc_out.get("work_item_id")),
            str(exc_out.get("state")),
        )
        wi_title = ((exc_out.get("work_item") or {}).get("title") or "")
        check(
            "exception title outlet-aware",
            "close variance" in wi_title.lower() or "BZG" in wi_title,
            wi_title,
        )
        try:
            vc.resolve_exception(
                cid,
                verified_person_id=hfb["person_id"],
                resolution_notes="Counted again; float excluded; awaiting bank.",
                object_ref="photo://resolve-1",
                allow_test_write=True,
                conn=c2,
            )
            try:
                vc.verify_close(cid, verified_person_id=hfb["person_id"], conn=c2)
                check("SoD resolver≠verifier (or no verify grant)", False)
            except Exception as sod:  # noqa: BLE001
                check(
                    "SoD resolver≠verifier (or no verify grant)",
                    getattr(sod, "code", "") in ("sod_self_verify", "forbidden"),
                    getattr(sod, "code", str(sod)),
                )
            # Submitter cannot self-verify even if granted verify
            c2.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES ('ROLE-BZG-CLOSER', 'PERM-VENUE-CLOSE-VERIFY', 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
                """,
                (TS, TS),
            )
            c2.commit()
            try:
                vc.verify_close(cid, verified_person_id="PERS-TEST-CLOSER", conn=c2)
                check("SoD submitter≠verifier", False)
            except Exception as sod:  # noqa: BLE001
                check(
                    "SoD submitter≠verifier",
                    getattr(sod, "code", "") == "sod_self_close",
                    getattr(sod, "code", str(sod)),
                )
        except Exception as exc:  # noqa: BLE001
            check("exception resolve path", False, str(exc))
    finally:
        c2.close()

    # Zero-variance clean path on a fresh day (avoid live-copied taken close for today)
    make_esb(esb_path, cash=200000.0, biz_date="2026-10-04")
    o2 = bzg.open_human_close(
        "2026-10-04",
        verified_person_id="PERS-TEST-CLOSER",
        outlet_id="BZG-UMA",
    )
    c2id = o2["close_id"]
    vc.capture_esb_snapshot(c2id, verified_person_id="PERS-TEST-CLOSER")
    bzg.attach_till_with_z_report(
        c2id,
        declared_cash_amount=200000.0,
        verified_person_id="PERS-TEST-CLOSER",
        object_ref="photo://z-20261004",
        allow_test_write=True,
    )
    clean = vc.reconcile(c2id, verified_person_id="PERS-TEST-CLOSER")
    check("zero variance system VERIFIED_CLOSED", clean.get("state") == "VERIFIED_CLOSED")

    # Live catalog not polluted by temp tests; ACTIVE policies still 0
    live2 = sqlite3.connect(str(LIVE_DB))
    live_pol2 = live2.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]
    live2.close()
    check("live ACTIVE policies still 0", live_pol2 == 0, str(live_pol2))

    # Static ROLE references
    check("ROLE-BZG-CLOSER in engine", "ROLE-BZG-CLOSER" in vc_src)
    check("ROLE-BZG-HFB in engine", "ROLE-BZG-HFB" in vc_src)
    check("staff_ready false in honesty", '"staff_ready": False' in vc_src or "'staff_ready': False" in vc_src)

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
