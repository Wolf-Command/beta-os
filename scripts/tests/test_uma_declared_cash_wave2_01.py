#!/usr/bin/env python3
"""Wave 2.01 — declared cash stays closed when no till count exists."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import uma_declared_cash_wave2_01 as cash  # noqa: E402
from core import venue_close  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def _evidence_id() -> str | None:
    conn = sqlite3.connect(f"file:{cash.CATALOG_DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT declared_cash_evidence_id, declared_cash_amount, state FROM venue_daily_closes WHERE close_id=?",
            (cash.NIGHT_CLOSE,),
        ).fetchone()
    finally:
        conn.close()
    return row


def main() -> int:
    catalog_mtime = cash.CATALOG_DB.stat().st_mtime_ns
    alchemist_mtime = cash.ALCHEMIST_DB.stat().st_mtime_ns
    before = _evidence_id()
    data = cash.load_declared_cash()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False and data.get("writes") is False)
    check("till not invented", data.get("till_invented") is False and data.get("attach_called_with_amount") is False)
    check(
        "fail closed",
        data.get("state") == "FAIL_CLOSED" and data.get("count_state") == "UNAVAILABLE" and data.get("attached") is False,
        str(data.get("state")),
    )
    night = data["night_close"]
    check(
        "night close still empty",
        night.get("close_id") == cash.NIGHT_CLOSE
        and night.get("state") == "DATA_CAPTURED"
        and night.get("business_date") == "2026-09-30"
        and night.get("declared_cash_amount") is None
        and night.get("declared_cash_evidence_id") is None,
        str(night),
    )
    today = data["today_close"]
    check(
        "today close still open",
        today.get("close_id") == cash.TODAY_CLOSE and today.get("state") == "OPEN" and today.get("declared_cash_evidence_id") is None,
    )
    counts = data["cash_count"]
    check("cash count empty", counts.get("present") is True and counts.get("count") == 0, str(counts))
    esb = data["esb_not_till"]
    check(
        "esb cash not copied",
        esb.get("copied_to_declared_cash") is False
        and esb.get("label") == "ESB_CASH_FROM_PAYMENTS"
        and esb.get("cash_from_payments") == 2610000
        and night.get("declared_cash_amount") is None,
        str(esb),
    )
    used = {row["evidence_id"]: row for row in data["not_used_as_cash"]}
    check(
        "receipt and petty not used as till",
        used[cash.RECEIPT_EVIDENCE]["used_as_declared_cash"] is False
        and used[cash.PETTY_EVIDENCE]["evidence_type"] == "photo"
        and used[cash.PETTY_EVIDENCE]["used_as_declared_cash"] is False,
    )
    gate = data["amount_gate"]
    check(
        "authority stays zero",
        gate.get("authority_limit_count") == 0
        and gate.get("allowed") is False
        and gate.get("reason") == "higher_approval_required"
        and gate.get("matched_limit") is None
        and gate.get("threshold_invented") is False
        and data.get("approval_request_count") == 1,
        str(gate),
    )
    try:
        venue_close.attach_declared_cash(
            cash.NIGHT_CLOSE,
            declared_cash_amount=None,
            verified_person_id="PERS-DEVI",
        )
        refused = False
        code = "no_error"
    except venue_close.VenueCloseError as exc:
        refused = True
        code = exc.code
    check("missing amount refused", refused and code == "invalid_amount", code)
    after = _evidence_id()
    check("close row unchanged", before == after and after[0] is None and after[1] is None and after[2] == "DATA_CAPTURED", str(after))
    page = (ROOT / "dashboards" / "uma-declared-cash.html").read_text(encoding="utf-8")
    check("page title", "<title>Uma declared cash</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page names the gap", "No till count was written" in page and "FAIL_CLOSED" in page)
    refused_post = cash.refuse_write()
    check("refuse write", refused_post.get("error") == "writes_off" and refused_post.get("till_invented") is False)
    check(
        "files unread",
        cash.CATALOG_DB.stat().st_mtime_ns == catalog_mtime and cash.ALCHEMIST_DB.stat().st_mtime_ns == alchemist_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
