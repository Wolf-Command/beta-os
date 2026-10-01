#!/usr/bin/env python3
"""Pack 5 — Atrium finance screens read the books and keep SoD."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import amg_finance_screens as fin  # noqa: E402

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
    before = fin.BOOKS.stat().st_mtime_ns
    data = fin.load_screens()
    after = fin.BOOKS.stat().st_mtime_ns
    check("books not written", before == after)
    check("staff_ready false", data.get("staff_ready") is False and data.get("human_proven") is False)
    check("xero off", data.get("xero_write") is False and data["writes"]["xero"] is False)
    check("payroll off", data.get("payroll") == "OFF")
    check("no bank balance", data.get("bank_balance") is None and data.get("bank_feed") is False)
    check("amg books", (data.get("books") or {}).get("legal_entity_id") == "ENT-AMG")
    check("books live shell", (data.get("books") or {}).get("shell_kind") == "live")

    screens = {row["id"]: row for row in data.get("screens") or []}
    check("five screens", set(screens) == {"night-audit", "flash", "cash", "close", "owner"})
    night = screens["night-audit"]
    check(
        "night audit is manual revenue",
        night.get("state") == "PARTIAL" and night.get("pms_night_audit") is False and len(night.get("lines") or []) == 2,
        str(night.get("value")),
    )
    check("flash not generated", screens["flash"].get("generated_flash") is False and screens["flash"].get("adr") is None)
    cash = screens["cash"]
    check(
        "cash unmatched",
        cash.get("state") == "UNKNOWN" and cash.get("statement_uploaded") is False and cash.get("match") is None and cash.get("bank_balance") is None,
        str(cash),
    )
    close = screens["close"]
    check("month not closed", close.get("month_closed") is False and close.get("journal_status_counts", {}).get("POSTED") == 4)
    check("owner not exported", screens["owner"].get("exported") is False)
    sod = data.get("sod") or {}
    check(
        "posted journal is segregated",
        sod.get("segregated") is True and sod.get("preparer_person_id") == fin.PRODUCER and sod.get("self_journal_approved_by") is None,
        str(sod),
    )

    zayen = fin.seat_matrix(fin.APPROVER)
    amanda = fin.seat_matrix(fin.AMANDA)
    check("zayen AMG yes", zayen.get("ENT-AMG") is True)
    check("zayen BZG yes", zayen.get("ENT-BZG") is True)
    check("zayen GGV deny", zayen.get("ENT-GGV") is False)
    check("amanda AMG deny", amanda.get("ENT-AMG") is False)
    check("amanda GGV allow", amanda.get("ENT-GGV") is True)

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "reviews.sqlite"
        blocked = fin.submit_review(fin.APPROVER, "close", db, entity_id="ENT-GGV")
        check("zayen cannot open GGV", blocked.get("error") == "entity_denied")
        opened = fin.submit_review(fin.PRODUCER, "close", db)
        check("zenit opens AMG review", opened.get("ok") is True and opened.get("amount") is None and opened.get("xero_write") is False)
        self_deny = fin.approve_review(fin.PRODUCER, opened["id"], db)
        check("self approve denied", self_deny.get("error") == "self_approval_denied")
        amanda_deny = fin.approve_review(fin.AMANDA, opened["id"], db)
        check("amanda cannot approve AMG", amanda_deny.get("error") == "entity_denied")
        approved = fin.approve_review(fin.APPROVER, opened["id"], db)
        check(
            "zayen approves zenit",
            approved.get("ok") is True and approved.get("approver_id") == fin.APPROVER and approved.get("posted") is False and approved.get("xero_write") is False,
            str(approved),
        )
    check("books still unread", fin.BOOKS.stat().st_mtime_ns == before)
    check("xero refuse", fin.refuse_xero().get("error") == "xero_write_blocked")
    check("payroll refuse", fin.refuse_payroll().get("error") == "payroll_blocked")

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
