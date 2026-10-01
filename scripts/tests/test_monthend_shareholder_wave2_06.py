#!/usr/bin/env python3
"""Wave 2.06 — historical boards stay preserved. No P&L is invented."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import monthend_shareholder_wave2_06 as month  # noqa: E402

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


def main() -> int:
    catalog_mtime = month.CATALOG_DB.stat().st_mtime_ns
    matrix_mtime = month.XERO_MATRIX.stat().st_mtime_ns
    july_mtime = (month.V1_DASH / "bzg-july-2026.html").stat().st_mtime_ns
    august_mtime = (month.V1_DASH / "bzg-august-2026.html").stat().st_mtime_ns
    index_mtime = (month.V1_DASH / "bzg-shareholder-reports.html").stat().st_mtime_ns
    data = month.load_monthend()
    check(
        "staff not ready",
        data.get("staff_ready") is False
        and data.get("human_proven") is False
        and data.get("writes") is False
        and data.get("xero_enabled") is False
        and data.get("state") == "SHELL"
        and data.get("chain") == "BROKEN"
        and data.get("pnl") is None
        and data.get("pnl_invented") is False
        and data.get("pack_completed") is False,
    )
    boards = {item["id"]: item for item in data["historical_boards"]}
    july = boards["july-2026"]
    august = boards["august-2026"]
    check(
        "july preserved",
        july.get("v1_present") is True
        and july.get("beta_present") is False
        and july.get("role") == "PRESERVE"
        and july.get("live_replacement") is False
        and july.get("figures_copied") is False
        and july.get("title") == "Blu Zone Group Shareholder Report, July 2026",
        str(july),
    )
    check(
        "august preserved",
        august.get("v1_present") is True
        and august.get("beta_present") is False
        and august.get("role") == "PRESERVE"
        and august.get("live_replacement") is False
        and august.get("figures_copied") is False
        and august.get("title") == "Blu Zone Group Shareholder Report, August 2026",
        str(august),
    )
    index = data["shareholder_index"]
    check(
        "index is not a completed pack",
        index.get("v1_present") is True
        and index.get("beta_present") is False
        and index.get("title") == "BZG Shareholder Reports"
        and index.get("links_historical_boards") is True
        and index.get("pack_completed") is False
        and index.get("live_replacement") is False,
        str(index),
    )
    closes = data["daily_closes"]
    rows = closes.get("rows") or []
    check(
        "daily closes are not a pack",
        closes.get("count") == 2
        and closes.get("figures_copied") is False
        and rows[0].get("close_id") == "VDC-25a3123a-3e26-43db-8085-10c6f208bbcd"
        and rows[0].get("business_date") == "2026-09-30"
        and rows[0].get("state") == "DATA_CAPTURED"
        and rows[0].get("declared_cash_evidence_id") is None
        and rows[0].get("month_end_pack") is False
        and rows[1].get("close_id") == "VDC-3353351f-3234-4f7d-acf0-a63e0e176114"
        and rows[1].get("state") == "OPEN"
        and rows[1].get("month_end_pack") is False
        and "esb_totals_json" not in rows[0],
        str(closes),
    )
    books = data["books"]
    check(
        "catalog is not a xero book",
        books.get("ggv_notas") == 0
        and books.get("ggv_invoices") == 0
        and books.get("xero_tables") == []
        and books.get("xero_book") is False,
        str(books),
    )
    xero = data["xero"]
    check(
        "xero absent",
        xero.get("precise_state") == "ABSENT"
        and xero.get("beta_connected") is False
        and xero.get("credential_found") is False
        and xero.get("write_capability") is False
        and xero.get("live_read_tested") is False
        and xero.get("last_success") is None
        and xero.get("enabled") is False
        and xero.get("as_of_wita") == "2026-10-01T07:17:29+08:00",
        str(xero),
    )
    page = (ROOT / "dashboards" / "bzg-month-end.html").read_text(encoding="utf-8")
    check("page title", "<title>Month-end</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page invents no pnl", "No P&amp;L was copied" in page or "No P&L was copied" in page)
    refused = month.refuse_write()
    check(
        "refuse write",
        refused.get("error") == "writes_off" and refused.get("xero_enabled") is False and refused.get("pnl_invented") is False,
    )
    check(
        "files unread",
        month.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and month.XERO_MATRIX.stat().st_mtime_ns == matrix_mtime
        and (month.V1_DASH / "bzg-july-2026.html").stat().st_mtime_ns == july_mtime
        and (month.V1_DASH / "bzg-august-2026.html").stat().st_mtime_ns == august_mtime
        and (month.V1_DASH / "bzg-shareholder-reports.html").stat().st_mtime_ns == index_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
