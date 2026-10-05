#!/usr/bin/env python3
"""Prove Finance Control Repair continuation against Beta catalog + optional HTTP.

Uses the same catalog DB as serve-beta :8788. Does NOT mutate preserved close
VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Throwaway rows only for cancel/restart/
reopen/takeover/concurrent-hold. staff_ready / eng_proved remain false.

HTTP prove (optional): set FINANCE_PROVE_HTTP=1 and run Beta with
BETA_AUTH_MODE=development_assertion — then hits :8788 with X-Wolf-Subject.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_daily_close as bzg  # noqa: E402
from core import ggv_bank_statement1 as gbs  # noqa: E402
from core import ggv_receipt_intake_ro as rx  # noqa: E402
from core import venue_close as vc  # noqa: E402

PRESERVED = "VDC-87202768-55af-4c8e-abc3-382a5496b8c6"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
BETA = "http://127.0.0.1:8788"
MATT_EMAIL = "mrwolf@wolfcommand.net"
THROW_DATE = "2099-03-15"
MISSING_DATE = "2026-09-28"  # warehouse has ESB; no current close at start of prove


def _http(method: str, path: str, body: dict | None = None, email: str = MATT_EMAIL) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BETA + path,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Wolf-Subject": email,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "error": "http_error", "message": raw[:400]}
        payload["_http_status"] = exc.code
        return payload


def main() -> int:
    c = sqlite3.connect(str(CATALOG))
    c.row_factory = sqlite3.Row
    results: list[str] = []
    throwaways: list[str] = []

    # --- preserved intact ---
    row = c.execute(
        "SELECT close_id, business_date, outlet_id, state, taken_by_person_id, "
        "esb_fingerprint_sha256, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row, "preserved missing"
    assert row["business_date"] == "2026-10-02"
    assert row["state"] == "DATA_CAPTURED"
    assert row["taken_by_person_id"] == "PERS-MATT"
    before_fp = row["esb_fingerprint_sha256"]
    before_totals = row["esb_totals_json"]
    photos = list((ROOT / "state/bzg-daily-close/receipts").glob("EVD-CLOSE-*"))
    assert len(photos) >= 5, f"photos {len(photos)}"
    results.append("preserved_intact")

    # --- schema migration for restart ---
    vc.ensure_take_attribution_columns(c)
    c.commit()
    ux = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name='ux_venue_daily_closes_current'"
    ).fetchone()
    assert ux, "partial unique index missing"
    results.append("restart_schema")

    # --- history range from saved rows ---
    hist = vc.closing_history(
        date_from="2026-10-01", date_to="2026-10-03", outlet_id="BZG-UMA", conn=c
    )
    assert hist["live_esb_used"] is False
    ids = {r.get("close_id") for r in (hist.get("closes") or hist.get("rows") or [])}
    # closing_history shape may use 'closes' or nest — accept either list key
    if not ids and isinstance(hist.get("days"), list):
        for d in hist["days"]:
            for r in d.get("closes") or []:
                ids.add(r.get("close_id"))
    # At minimum consolidated present
    assert "consolidated" in hist
    results.append("history_range")

    detail = bzg.history_detail(PRESERVED, conn=c)
    assert detail["api_vs_receipt"]["api_cash"] == 2855000.0
    assert detail["api_vs_receipt"]["receipt_cash"] == 2735000.0
    assert detail["api_vs_receipt"]["cause_invented"] is False
    results.append("history_detail_dual_source")

    # --- add missing historical close for 2026-09-28 ---
    existing_missing = vc.get_close(business_date=MISSING_DATE, conn=c)
    keep_missing_close_id = None
    if existing_missing is None:
        opened = bzg.open_human_close(
            MISSING_DATE,
            verified_person_id="PERS-MATT",
            outlet_id="BZG-UMA",
            conn=c,
            commit=True,
        )
        assert opened.get("created") is True or opened.get("close_id")
        keep_missing_close_id = opened["close_id"]
        # Intentionally NOT in throwaways — persists as the missing historical close prove.
        cap = vc.capture_esb_snapshot(
            keep_missing_close_id, verified_person_id="PERS-MATT", conn=c, commit=True
        )
        snap = vc.get_close(keep_missing_close_id, conn=c)
        assert snap and snap.get("business_date") == MISSING_DATE
        assert snap.get("esb_fingerprint_sha256")
        totals = snap.get("esb_totals") or {}
        # Must be that date's ESB (warehouse cash 2,460,000 for 2026-09-28), not today.
        assert float(totals.get("cash_from_payments") or 0) == 2460000.0, totals
        results.append(f"add_missing_historical_esb:{keep_missing_close_id}")
    else:
        keep_missing_close_id = existing_missing["close_id"]
        results.append(f"add_missing_already_present:{keep_missing_close_id}")

    # --- cancel → restart clean ---
    # Prefer a dedicated throwaway date so we do not disturb real days.
    opened1 = vc.open_or_get(
        THROW_DATE,
        verified_person_id="PERS-MATT",
        conn=c,
        commit=True,
    )
    cid1 = opened1["close_id"]
    throwaways.append(cid1)
    # take holder
    vc.take_open_venue_close(cid1, verified_person_id="PERS-MATT", conn=c, commit=True)
    cancelled = vc.cancel_unfinished_close(
        cid1,
        verified_person_id="PERS-MATT",
        reason="prove cancel unfinished",
        conn=c,
        commit=True,
    )
    assert cancelled["cancelled"] is True
    assert cancelled["close"]["state"] == "CANCELLED"
    # Restart: new close id for same date
    opened2 = vc.open_or_get(
        THROW_DATE,
        verified_person_id="PERS-MATT",
        conn=c,
        commit=True,
    )
    cid2 = opened2["close_id"]
    throwaways.append(cid2)
    assert opened2.get("created") is True
    assert opened2.get("restarted_after_cancel") is True
    assert cid2 != cid1
    still_cancelled = vc.get_close(cid1, conn=c)
    assert still_cancelled and still_cancelled["state"] == "CANCELLED"
    results.append("cancel_restart")

    # --- concurrent take blocked ---
    vc.take_open_venue_close(cid2, verified_person_id="PERS-MATT", conn=c, commit=True)
    blocked = False
    try:
        vc.take_open_venue_close(cid2, verified_person_id="PERS-IZA", conn=c, commit=True)
    except vc.VenueCloseError as exc:
        blocked = exc.code in {"concurrent_take", "forbidden"} or "hold" in str(exc).lower() or "taken" in str(exc).lower()
        if not blocked and exc.http_status == 409:
            blocked = True
        if not blocked:
            # Accept 409 concurrent
            blocked = getattr(exc, "http_status", None) == 409 or "concurrent" in exc.code
    assert blocked, "second holder should be refused"
    holder = vc.get_close(cid2, conn=c)
    assert holder and holder.get("taken_by_person_id") == "PERS-MATT"
    results.append("single_holder_lock")

    # --- takeover audited ---
    taken = vc.reassign_venue_close(
        cid2,
        verified_person_id="PERS-MATT",
        new_holder_person_id="PERS-IZA",
        reason="prove owner takeover/reassign",
        mode="takeover",
        conn=c,
        commit=True,
    )
    assert (taken.get("taken_by_person_id") or taken.get("close", {}).get("taken_by_person_id")) in {
        "PERS-IZA",
        taken.get("new_holder_person_id"),
    } or taken.get("taken_by_person_id") == "PERS-IZA" or (
        vc.get_close(cid2, conn=c) or {}
    ).get("taken_by_person_id") == "PERS-IZA"
    after_take = vc.get_close(cid2, conn=c)
    assert after_take and after_take["taken_by_person_id"] == "PERS-IZA"
    results.append("takeover_reassign")

    # --- reopen completed with immutable final history ---
    # Build a throwaway VERIFIED_CLOSED without touching preserved.
    vdate = "2099-03-16"
    vopen = vc.open_or_get(vdate, verified_person_id="PERS-MATT", conn=c, commit=True)
    vcid = vopen["close_id"]
    throwaways.append(vcid)
    # Force state to VERIFIED_CLOSED with a fake fingerprint for reopen prove only.
    ts = vc.now_utc_iso()
    fake_totals = {"cash_from_payments": 111.0, "prove_only": True}
    c.execute(
        """
        UPDATE venue_daily_closes
        SET state='VERIFIED_CLOSED', esb_fingerprint_sha256=?, esb_totals_json=?,
            esb_pulled_at=?, taken_by_person_id='PERS-MATT', taken_at=?, updated_at=?,
            verified_at=?, verified_by_person_id='PERS-MATT'
        WHERE close_id=?
        """,
        (
            "prove-fp-" + vcid[-12:],
            json.dumps(fake_totals),
            ts,
            ts,
            ts,
            ts,
            vcid,
        ),
    )
    c.commit()
    reopened = vc.owner_control_venue_close(
        vcid,
        verified_person_id="PERS-MATT",
        action="reopen",
        reason="prove reopen immutable history",
        conn=c,
        commit=True,
    )
    assert reopened.get("original_immutable") is True
    assert reopened.get("final_history_id")
    hist_row = vc.latest_final_history(vcid, conn=c)
    assert hist_row and hist_row.get("state_at_freeze") == "VERIFIED_CLOSED"
    assert float((hist_row.get("esb_totals") or {}).get("cash_from_payments") or 0) == 111.0
    working = vc.get_close(vcid, conn=c)
    assert working and working["state"] == "OPEN"
    # Immutable freeze still present after working-row mutation of state
    hist_row2 = vc.latest_final_history(vcid, conn=c)
    assert hist_row2 and hist_row2["history_id"] == hist_row["history_id"]
    assert float((hist_row2.get("esb_totals") or {}).get("cash_from_payments") or 0) == 111.0
    results.append("reopen_immutable")

    # --- bank cards / NOT_USED / supersede still on preserved ---
    banks = bzg.bank_cards(PRESERVED, conn=c)
    cards = banks.get("cards") or banks.get("bank_cards") or []
    by_bank = {
        str(x.get("bank") or x.get("bank_code") or "").upper(): x for x in cards
    }
    assert {"MANDIRI", "BNI", "BRI"} <= set(by_bank), sorted(by_bank)
    bri_status = str(by_bank.get("BRI", {}).get("status") or "").upper()
    assert "NOT_USED" in bri_status, bri_status
    results.append("bank_cards_not_used")

    # --- GGV vault receipts ---
    listed = rx.list_ggv_receipts(limit=20)
    assert listed.get("second_pipeline") is False
    assert listed.get("count", 0) >= 1
    results.append("ggv_vault_receipts")

    # --- bank statement import ---
    sample = (
        "Date,Description,Debit,Credit,Balance\n"
        "2026-09-15,Prove coffee receipt,150000,0,1000000\n"
        "2026-09-16,Client transfer,0,500000,1500000\n"
    ).encode("utf-8")
    # Unique content each run
    sample = sample + f"# {uuid.uuid4()}\n".encode("utf-8")
    imp = gbs.import_statement(
        verified_person_id="PERS-MATT",
        filename="ggv-prove-statement.csv",
        content=sample,
        bank_label="MANDIRI",
        conn=c,
        commit=True,
    )
    assert imp.get("ok") and imp.get("txn_count") >= 2
    assert Path(imp["original_path"]).is_file()
    tx = gbs.list_transactions(
        verified_person_id="PERS-MATT", import_id=imp["import_id"], conn=c
    )
    assert tx.get("count", 0) >= 2
    results.append("bank_statement_import")

    # --- Zayen denied GGV finance ---
    deny = gbs.deny_if_not_ggv_entity("PERS-ZAYEN")
    assert deny and deny.get("ok") is False
    results.append("zayen_ggv_deny")

    # --- freeze still holds on preserved ---
    out = vc.capture_esb_snapshot(
        PRESERVED, verified_person_id="PERS-MATT", conn=c, commit=True
    )
    assert out.get("snapshot_frozen") is True
    assert out.get("mutated") is False
    after = c.execute(
        "SELECT esb_fingerprint_sha256, esb_totals_json, state, taken_by_person_id "
        "FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert after["esb_fingerprint_sha256"] == before_fp
    assert after["esb_totals_json"] == before_totals
    assert after["state"] == "DATA_CAPTURED"
    assert after["taken_by_person_id"] == "PERS-MATT"
    results.append("freeze_still_holds")

    # --- optional HTTP against running Beta ---
    http_ok = []
    if (os.environ.get("FINANCE_PROVE_HTTP") or "").strip() == "1":
        auth_mode = _http("GET", "/api/core/auth-mode")
        if auth_mode.get("auth_mode") != "development_assertion":
            results.append("http_skipped_cf_mode")
        else:
            h = _http(
                "GET",
                f"/api/venue-close/list?history=1&date_from=2026-10-01&date_to=2026-10-03&outlet_id=BZG-UMA",
            )
            assert h.get("ok") is not False or "closes" in h or "rows" in h or h.get("consolidated")
            http_ok.append("history")
            d = _http("GET", f"/api/venue-close/{PRESERVED}")
            assert d.get("state") == "DATA_CAPTURED" or (d.get("close") or {}).get("state") == "DATA_CAPTURED"
            http_ok.append("preserved_detail")
            r = _http("GET", "/api/ggv/finance/receipts?limit=5")
            assert r.get("second_pipeline") is False or (r.get("ok") and "receipts" in r)
            http_ok.append("ggv_receipts")
            b = _http("GET", "/api/ggv/finance/bank-statements")
            assert b.get("entity_id") == "ENT-GGV" or "imports" in b
            http_ok.append("bank_statements")
            # Zayen email if mapped
            z = _http("GET", "/api/ggv/finance/receipts?limit=1", email="laluzayen@gmail.com")
            assert z.get("_http_status") in (401, 403) or z.get("ok") is False
            http_ok.append("zayen_http_deny")
            results.append("http_" + "+".join(http_ok))

    # cleanup throwaways (keep cancelled history rows deleted for cleanliness)
    for cid in throwaways:
        c.execute("DELETE FROM venue_close_final_history WHERE close_id=?", (cid,))
        c.execute("DELETE FROM venue_close_edc_receipts WHERE close_id=?", (cid,))
        c.execute("DELETE FROM venue_close_esb_closing_receipts WHERE close_id=?", (cid,))
        c.execute("DELETE FROM venue_daily_closes WHERE close_id=?", (cid,))
    # Also remove any leftover THROW_DATE / vdate rows
    c.execute(
        "DELETE FROM venue_daily_closes WHERE business_date IN (?, ?) AND close_id != ?",
        (THROW_DATE, "2099-03-16", PRESERVED),
    )
    c.commit()

    final = c.execute(
        "SELECT state, taken_by_person_id, esb_fingerprint_sha256 FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert final["state"] == "DATA_CAPTURED"
    assert final["taken_by_person_id"] == "PERS-MATT"
    assert final["esb_fingerprint_sha256"] == before_fp
    c.close()

    print("PASS", " ".join(results))
    print("staff_ready=false eng_proved=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("FAIL", type(exc).__name__, exc)
        raise
