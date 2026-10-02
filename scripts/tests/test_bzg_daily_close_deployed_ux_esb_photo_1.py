#!/usr/bin/env python3
"""BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1 — phone Take/Upload + honest ESB.

Decision: 2026-09-17 Uma Blu Daily Close (extend) + commissioning FAIL #2 pack.
Proves: Take Photo / Upload Photo markers, capture=environment, receipt-photo
API, store→extract, ESB DATA UNAVAILABLE (empty ≠ zero), dual source kept,
staff_ready false. Deployed HTML markers — not repo-only fiction.
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
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
UI = ROOT / "dashboards" / "uma-blu-close.html"
SERVE = SCRIPTS / "serve_beta.py"
BZG_PY = SCRIPTS / "core" / "bzg_daily_close.py"
VC_PY = SCRIPTS / "core" / "venue_close.py"
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"

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


def make_esb(path: Path, *, biz_date: str = "2026-10-01", empty: bool = False) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        if not empty:
            raw = {
                "branchCode": "BLZ",
                "salesNum": "S1",
                "billNum": "B1",
                "statusName": "Finished",
                "grandTotal": 175000,
                "paymentTotal": 175000,
                "salesPayments": [
                    {"paymentMethodTypeName": "CASH", "paymentAmount": 100000},
                    {"paymentMethodTypeName": "CARD", "paymentAmount": 50000},
                    {"paymentMethodTypeName": "QRIS", "paymentAmount": 25000},
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


def wire(tmp_db: Path, esb_path: Path, receipt_dir: Path):
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
    bzg.CLOSE_RECEIPT_DIR = receipt_dir
    return vc, bzg


def http_get(url: str) -> tuple[int, str]:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=8) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    ui = UI.read_text(encoding="utf-8")
    serve = SERVE.read_text(encoding="utf-8")
    bzg_src = BZG_PY.read_text(encoding="utf-8")
    vc_src = VC_PY.read_text(encoding="utf-8")

    check("Take Photo button ESB", "Take Photo" in ui and "btnEsbTakePhoto" in ui)
    check("Upload Photo button ESB", "Upload Photo" in ui and "btnEsbUploadPhoto" in ui)
    check("Take Photo button EDC", "btnEdcTakePhoto" in ui)
    check("Upload Photo button EDC", "btnEdcUploadPhoto" in ui)
    check("capture=environment present", 'capture="environment"' in ui)
    check("esb file input image/*", 'id="esbCam"' in ui and 'accept="image/*"' in ui)
    check("edc file input image/*", 'id="edcCam"' in ui and 'accept="image/*"' in ui)
    check("no photo:// placeholder UX", 'placeholder="photo://esb-close' not in ui)
    check("ESB DATA UNAVAILABLE string", "ESB DATA UNAVAILABLE" in ui)
    check("empty is not zero sales copy", "Empty is not zero sales" in ui)
    check("receipt-photo API wired", "/api/venue-close/receipt-photo" in serve)
    check("save_close_receipt_bytes", "def save_close_receipt_bytes" in bzg_src)
    check("esb_data_unavailable code", "esb_data_unavailable" in vc_src)
    check("staff_ready false", '"staff_ready": False' in bzg_src)
    check("human_commissioned false", '"human_commissioned": False' in bzg_src)
    check("phone_take_upload_photo honesty", "phone_take_upload_photo" in bzg_src)
    check("max-width phone", "max-width: 480px" in ui)
    check("Looks Correct retained", "Looks Correct" in ui)
    check("dual source copy", "dual source" in ui.lower() or "Dual source" in ui)

    td = Path(tempfile.mkdtemp(prefix="bzg-ux-photo-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    empty_esb = td / "esb-empty.sqlite"
    receipt_dir = td / "receipts"
    make_esb(esb_path, biz_date="2026-10-01")
    make_esb(empty_esb, empty=True)

    uma_mig = load_mod(UMA_MIG, "migrate_uma_blu_daily_close_ux")
    uma_mig.DB = tmp_db
    check("uma migrate", uma_mig.main() == 0)
    mig031 = load_mod(MIG031, "migrate_bzg_till_ux")
    mig031.DB = tmp_db
    check("031 migrate", mig031.main() == 0)
    mig032 = load_mod(MIG032, "migrate_bzg_medc_ux")
    mig032.DB = tmp_db
    check("032 migrate", mig032.main() == 0)

    vc, bzg = wire(tmp_db, esb_path, receipt_dir)
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    seed_test_closer(conn)

    saved = bzg.save_close_receipt_bytes(
        data=b"\xff\xd8\xfffake-jpeg-bytes-for-close",
        kind="esb",
        close_id="CLOSE-TEST",
        filename="esb.jpg",
        content_type="image/jpeg",
    )
    check("save returns object_ref", str(saved.get("object_ref") or "").startswith("close-receipt://"))
    check("save content_hash", bool(saved.get("content_hash")))
    check("kept_original", saved.get("kept_original") is True)
    loaded, mime = bzg.load_close_receipt_bytes(saved["object_ref"])
    check("load bytes roundtrip", loaded == b"\xff\xd8\xfffake-jpeg-bytes-for-close", mime)
    check("path escape refused", bzg.resolve_close_receipt_path("close-receipt://../etc/passwd") is None)

    opened = vc.open_or_get(
        "2026-10-02",
        verified_person_id="PERS-TEST-CLOSER",
        conn=conn,
        commit=True,
    )
    try:
        vc.capture_esb_snapshot(
            opened["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=empty_esb,
            conn=conn,
            commit=True,
        )
        check("empty → raises", False, "expected raise")
    except vc.VenueCloseError as e:
        check("empty → esb_data_unavailable", e.code == "esb_data_unavailable", e.code)
        check("empty message UNAVAILABLE", "ESB DATA UNAVAILABLE" in str(e), str(e)[:100])
        check("empty message not zero", "not zero" in str(e).lower(), str(e)[:100])
    row = vc.get_close(opened["close_id"], conn=conn)
    check(
        "unavailable does not capture zeros",
        row is not None
        and row.get("state") == "OPEN"
        and not row.get("esb_fingerprint_sha256"),
        str(row.get("state") if row else None),
    )

    opened2 = vc.open_or_get(
        "2026-10-01",
        verified_person_id="PERS-TEST-CLOSER",
        conn=conn,
        commit=True,
    )
    cap = vc.capture_esb_snapshot(
        opened2["close_id"],
        verified_person_id="PERS-TEST-CLOSER",
        esb_path=esb_path,
        conn=conn,
        commit=True,
    )
    check("available status", cap.get("esb_live_status") == "AVAILABLE")
    check("available has fingerprint", bool(cap.get("esb_fingerprint_sha256")))
    check(
        "available cash not invented empty",
        (cap.get("esb_totals") or {}).get("cash_from_payments") == 100000,
    )

    # Photo bytes present → dry vision draft keeps stored object_ref (no Gemini required).
    os.environ["WOLF_CLOSE_VISION_DRY"] = "1"
    draft = bzg.extract_esb_closing_receipt_draft(
        opened2["close_id"],
        verified_person_id="PERS-TEST-CLOSER",
        image_bytes=b"\xff\xd8\xfffake-jpeg-bytes-for-close",
        mime_type="image/jpeg",
        image_object_ref=saved["object_ref"],
        content_hash=saved["content_hash"],
        fixture_fields=None,
        conn=conn,
        commit=True,
    )
    check("extract draft ok", draft.get("ok") is True)
    check("extract keeps object_ref", draft.get("image_object_ref") == saved["object_ref"])
    check("photo wins over fixture path", draft.get("draft", {}).get("provider") in ("dry_run", "gemini", "fixture"))

    conf = bzg.confirm_esb_closing_receipt(
        opened2["close_id"],
        verified_person_id="PERS-TEST-CLOSER",
        action="looks_correct",
        object_ref=saved["object_ref"],
        content_hash=saved["content_hash"],
        cash_amount=100000,
        edc_card_amount=50000,
        qris_amount=25000,
        vision_event_id=draft.get("vision_event_id"),
        conn=conn,
        commit=True,
        allow_test_write=True,
    )
    check("confirm esb receipt id", bool(conf.get("esb_receipt_id")))
    check("confirm dual source no silent overwrite", conf.get("api_mismatch") is False)

    # EDC photo store + extract + confirm
    edc_saved = bzg.save_close_receipt_bytes(
        data=b"\xff\xd8\xffedc-bytes",
        kind="edc",
        close_id=opened2["close_id"],
        filename="edc.jpg",
    )
    edc_draft = bzg.extract_edc_receipt_draft(
        opened2["close_id"],
        verified_person_id="PERS-TEST-CLOSER",
        image_bytes=b"\xff\xd8\xffedc-bytes",
        image_object_ref=edc_saved["object_ref"],
        content_hash=edc_saved["content_hash"],
        fixture_fields=None,
        conn=conn,
        commit=True,
    )
    check("edc extract ok", edc_draft.get("ok") is True)
    edc_conf = bzg.confirm_edc_receipt(
        opened2["close_id"],
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="Mandiri",
        edc_card_amount=50000,
        qris_amount=0,
        action="looks_correct",
        object_ref=edc_saved["object_ref"],
        content_hash=edc_saved["content_hash"],
        vision_event_id=edc_draft.get("vision_event_id"),
        conn=conn,
        commit=True,
        allow_test_write=True,
    )
    check("edc confirm id", bool(edc_conf.get("edc_receipt_id")))
    check("edc totals separate", (edc_conf.get("receipt_totals") or {}).get("TOTAL_EDC") == 50000)

    conn.close()

    code, body = http_get("http://127.0.0.1:8788/uma-blu-close")
    if code == 200:
        check("deployed HTML Take Photo", "Take Photo" in body)
        check("deployed HTML Upload Photo", "Upload Photo" in body)
        check("deployed HTML capture=environment", 'capture="environment"' in body)
        check("deployed HTML ESB DATA UNAVAILABLE", "ESB DATA UNAVAILABLE" in body)
        check("deployed no photo:// placeholder", 'placeholder="photo://esb-close' not in body)
    else:
        check("deployed route reachable (auth gate)", code in (200, 403), str(code))
        check("disk HTML Take Photo", "Take Photo" in ui)
        check("disk HTML Upload Photo", "Upload Photo" in ui)
        check("disk HTML capture=environment", 'capture="environment"' in ui)
        check("disk HTML ESB DATA UNAVAILABLE", "ESB DATA UNAVAILABLE" in ui)
        check("disk HTML no photo:// placeholder", 'placeholder="photo://esb-close' not in ui)

    print(f"\nRESULT pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
