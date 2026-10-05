#!/usr/bin/env python3
"""UMA-CLOSE-SOURCE-WIZARD-1 — dual warehouse + printed source; phone wizard.

Uses temp sqlite copy of catalog for 29 Sep assertions. Protected closes read-only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
BETA = "http://127.0.0.1:8788"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def read_protected_snapshots() -> dict[str, dict]:
    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out = {}
    for cid in (OCT3, OCT4):
        row = conn.execute(
            "SELECT close_id, declared_cash_amount, updated_at FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        out[cid] = dict(row) if row else {}
    conn.close()
    return out


def fetch_html() -> tuple[int | None, str]:
    try:
        req = urllib.request.Request(BETA + "/uma-blu-close", method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"NOTE  served page unavailable: {exc}")
        return None, UI.read_text(encoding="utf-8")


def prod_pid_8787() -> int | None:
    try:
        import subprocess

        out = subprocess.check_output(
            ["lsof", "-ti", "tcp:8787"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except Exception:
        return None


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import bzg_daily_close as bzg

    before = read_protected_snapshots()
    html = UI.read_text(encoding="utf-8")
    code, served = fetch_html()
    body = served if code == 200 else html

    check("wizard screens in HTML", "wiz-screen" in body and "wizIntro" in body)
    check("date register API path in HTML", "date-register" in body)
    check("source-wizard API path in HTML", "source-wizard" in body)
    check("no AI is not truth on staff HTML", "AI is not truth" not in body)
    check("no CHECK THIS AMOUNT on staff HTML", "CHECK THIS AMOUNT" not in body)
    check("no Sales EDC engineering string", "Sales EDC" not in body)
    check("SOURCE DIFFERENCE FOUND present", "SOURCE DIFFERENCE FOUND" in body)
    check("seven day limit removed from calendar", "lastSevenDates" not in body)

    # Live catalog read — warehouse unchanged on 29 Sep
    conn_ro = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn_ro.row_factory = sqlite3.Row
    sep_row = conn_ro.execute(
        "SELECT esb_totals_json, esb_fingerprint_sha256, updated_at FROM venue_daily_closes WHERE close_id=?",
        (SEP29,),
    ).fetchone()
    conn_ro.close()
    check("29 Sep close row exists", sep_row is not None)
    totals = json.loads(sep_row["esb_totals_json"]) if sep_row else {}
    fp_before = sep_row["esb_fingerprint_sha256"] if sep_row else None
    updated_before = sep_row["updated_at"] if sep_row else None
    check(
        "29 Sep warehouse cash 4135000",
        totals.get("cash_from_payments") == 4135000.0,
        str(totals.get("cash_from_payments")),
    )
    check(
        "29 Sep warehouse finished bills 51",
        totals.get("finished_count") == 51,
        str(totals.get("finished_count")),
    )

    # Writable temp copy for owner-typed attach + wizard APIs
    td = Path(tempfile.mkdtemp(prefix="uma-close-source-wizard-1-"))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    bzg.ensure_schema(conn)
    bzg.configure_outlet_settlement_banks("BZG-UMA", conn=conn)
    conn.commit()

    attach = bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    check(
        "owner-typed printed source present",
        attach and (attach.get("attached") or attach.get("already_present")),
        str(attach),
    )
    check("no photo attached", attach and not attach.get("image_attached"))
    check(
        "honest missing file status",
        attach
        and attach.get("image_status") == "MISSING_FILE_VALUES_SUPPLIED_BY_OWNER",
    )

    wiz = bzg.source_wizard_state(SEP29, conn=conn)
    wh = wiz.get("warehouse_source") or {}
    pr = wiz.get("printed_source") or {}
    disc = wiz.get("source_discrepancy") or {}

    check("warehouse cash preserved in wizard", wh.get("cash_rp") == 4135000.0)
    check("warehouse bills preserved in wizard", wh.get("finished_bills") == 51)
    check("printed cash 3790000", pr.get("cash_rp") == 3790000.0)
    check("printed bills 50", pr.get("bills") == 50)
    check("printed gross 13435000", pr.get("gross_sales_rp") == 13435000.0)
    check("printed pax 79", pr.get("pax") == 79)
    check(
        "executive chef non-sales 78512",
        pr.get("non_sales_executive_chef_rp") == 78512,
    )
    check("payment total 13435000", pr.get("payment_total_rp") == 13435000.0)
    check("scott etik 1425000", pr.get("scott_etik_rp") == 1425000.0)
    check("source discrepancy cash 345000", disc.get("difference", {}).get("cash_rp") == 345000.0)
    check("source discrepancy bills 1", disc.get("difference", {}).get("bills") == 1)
    check("discrepancy visible flag", disc.get("has_discrepancy") is True)

    cards = (wiz.get("wizard_bank_cards") or {}).get("cards") or []
    mandiri = next((c for c in cards if c.get("bank") == "MANDIRI"), None)
    bni = next((c for c in cards if c.get("bank") == "BNI"), None)
    bri = next((c for c in cards if c.get("bank") == "BRI"), None)
    check("Mandiri NOT USED", mandiri and mandiri.get("staff_label") == "NOT USED")
    check("BNI expected EDC 2545000", bni and bni.get("expected_edc") == 2545000.0)
    check("BNI expected QRIS 145000", bni and bni.get("expected_qris") == 145000.0)
    check("BRI expected EDC 4465000", bri and bri.get("expected_edc") == 4465000.0)
    check("BRI expected QRIS 1065000", bri and bri.get("expected_qris") == 1065000.0)

    petty = wiz.get("wizard_petty") or {}
    mov_ids = [
        str(m.get("movement_id") or m.get("petty_movement_id") or "")
        for m in (petty.get("out_movements") or []) + (petty.get("in_movements") or [])
    ]
    check(
        "29 Sep petty excludes PETTY-UMA-6D853EEAE0",
        not any("6D853EEAE0" in x for x in mov_ids),
        str(mov_ids),
    )

    readiness = wiz.get("submit_readiness") or {}
    check(
        "submit disabled until prerequisites",
        readiness.get("submit_enabled") is False,
        str(readiness),
    )
    check("next action present", bool(readiness.get("next_action")))

    reg = bzg.close_date_register(search="2026-09-03", conn=conn)
    days = {d["business_date"]: d for d in (reg.get("days") or [])}
    check("3 Sep selectable in register", "2026-09-03" in days)
    check("seven_day_limit_removed flag", reg.get("seven_day_limit_removed") is True)

    conn.close()

    after = read_protected_snapshots()
    for cid, snap in before.items():
        a = after.get(cid) or {}
        check(
            f"{cid} updated_at unchanged",
            a.get("updated_at") == snap.get("updated_at"),
            f"before={snap.get('updated_at')} after={a.get('updated_at')}",
        )
        check(
            f"{cid} declared cash unchanged",
            a.get("declared_cash_amount") == snap.get("declared_cash_amount"),
        )

    # Re-read live 29 Sep warehouse after tests — must not mutate live row bytes
    conn_ro2 = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn_ro2.row_factory = sqlite3.Row
    sep_after = conn_ro2.execute(
        "SELECT esb_totals_json, esb_fingerprint_sha256, updated_at FROM venue_daily_closes WHERE close_id=?",
        (SEP29,),
    ).fetchone()
    conn_ro2.close()
    totals_after = json.loads(sep_after["esb_totals_json"]) if sep_after else {}
    check(
        "live 29 Sep fingerprint unchanged",
        sep_after["esb_fingerprint_sha256"] == fp_before,
    )
    check(
        "live 29 Sep warehouse cash still 4135000",
        totals_after.get("cash_from_payments") == 4135000.0,
    )

    prod = prod_pid_8787()
    check("production pid 1297 on 8787", prod == 1297, str(prod))

    print(f"\nTOTAL  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
