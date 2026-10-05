#!/usr/bin/env python3
"""UMA-CLOSE-DATE-TRUTH-1 — distinct snapshot_day totals per business date.

Temp ESB sqlite only. Never copies catalog/content_library.sqlite.
Protected closes are not touched.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

# Proved adjacent-date figures — accidental reuse must not pass.
DATE_FIXTURES: dict[str, dict[str, float | int]] = {
    "2026-09-28": {"cash": 2460000.0, "finished": 58},
    "2026-09-29": {"cash": 4135000.0, "finished": 51},
    "2026-09-30": {"cash": 2610000.0, "finished": 50},
    "2026-10-01": {"cash": 2435000.0, "finished": 45},
    "2026-10-02": {"cash": 2855000.0, "finished": 61},
    "2026-10-03": {"cash": 3465000.0, "finished": 52},
    "2026-10-04": {"cash": 360000.0, "finished": 61},
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def make_esb_day(path: Path, biz_date: str, cash: float, finished: int) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
              nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT
            )
            """
        )
        for i in range(finished):
            if i == 0:
                amt = cash
                payments = [{"paymentMethodTypeName": "CASH", "paymentAmount": cash}]
            else:
                amt = 1000.0
                payments = [
                    {
                        "paymentMethodTypeName": "CARD",
                        "paymentMethodName": "EDC BRI",
                        "paymentAmount": amt,
                    }
                ]
            raw = {
                "branchCode": "BLZ",
                "branchName": "UMA BLU",
                "salesNum": f"SBLZ{biz_date.replace('-', '')}{i:03d}",
                "statusName": "Finished",
                "grandTotal": amt,
                "paymentTotal": amt,
                "salesDate": biz_date,
                "salesPayments": payments,
            }
            nk = f"BLZ|{biz_date}|{i}"
            conn.execute(
                "INSERT OR REPLACE INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
                (nk, biz_date, json.dumps(raw), f"{biz_date}T20:00:00+08:00"),
            )
        conn.commit()
    finally:
        conn.close()


def build_fixture_esb(tmp: Path) -> Path:
    esb = tmp / "esb.sqlite"
    for date, spec in DATE_FIXTURES.items():
        make_esb_day(esb, date, float(spec["cash"]), int(spec["finished"]))
    return esb


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import esb_close_snapshot as esb

    with tempfile.TemporaryDirectory(prefix="uma-close-date-truth-1-") as td:
        esb_path = build_fixture_esb(Path(td))
        seen_cash: set[float] = set()
        pairs_by_date: dict[str, tuple[float, int]] = {}
        for date, spec in DATE_FIXTURES.items():
            snap = esb.snapshot_day(date, esb_path=esb_path)
            totals = snap.get("totals") or {}
            cash = round(float(totals.get("cash_from_payments") or 0), 2)
            finished = int(totals.get("finished_count") or 0)
            expect_cash = round(float(spec["cash"]), 2)
            expect_finished = int(spec["finished"])
            check(
                f"{date} cash_from_payments",
                cash == expect_cash,
                f"got {cash} expected {expect_cash}",
            )
            check(
                f"{date} finished_count",
                finished == expect_finished,
                f"got {finished} expected {expect_finished}",
            )
            check(
                f"{date} fingerprint present",
                bool(snap.get("fingerprint_sha256")),
                str(snap.get("fingerprint_sha256")),
            )
            meta = snap.get("query_meta") or {}
            check(
                f"{date} query business_date",
                meta.get("business_date") == date,
                str(meta.get("business_date")),
            )
            seen_cash.add(cash)
            pairs_by_date[date] = (cash, finished)

        check("all seven cash totals distinct", len(seen_cash) == 7, str(sorted(seen_cash)))
        check(
            "no two dates share both cash and finished count",
            len(set(pairs_by_date.values())) == len(pairs_by_date),
            str(pairs_by_date),
        )
        dup_finished = [
            d for d, s in DATE_FIXTURES.items() if int(s["finished"]) == 61
        ]
        check(
            "2 Oct and 4 Oct share finished 61 but different cash",
            len(dup_finished) == 2
            and DATE_FIXTURES["2026-10-02"]["cash"] != DATE_FIXTURES["2026-10-04"]["cash"],
            str(dup_finished),
        )
        wrong = esb.snapshot_day("2026-09-29", esb_path=esb_path)
        wrong_cash = round(float((wrong.get("totals") or {}).get("cash_from_payments") or 0), 2)
        check(
            "29 Sep not equal to 28 Sep cash",
            wrong_cash != DATE_FIXTURES["2026-09-28"]["cash"],
            f"{wrong_cash}",
        )

    print(f"\nTOTAL  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
