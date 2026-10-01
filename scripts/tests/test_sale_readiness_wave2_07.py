#!/usr/bin/env python3
"""Wave 2.07 — the sale page is a system checklist, not a buyer room."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import sale_evidence_pack as evidence  # noqa: E402
from core import sale_readiness_wave2_07 as sale  # noqa: E402

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
    catalog_mtime = evidence.CATALOG_DB.stat().st_mtime_ns
    csv_mtime = evidence.SALE_CSV.stat().st_mtime_ns
    ledger_mtime = evidence.LEDGER_JSON.stat().st_mtime_ns
    page_mtime = sale.PAGE.stat().st_mtime_ns
    data = sale.load_readiness()
    check(
        "staff not ready",
        data.get("staff_ready") is False
        and data.get("human_proven") is False
        and data.get("writes") is False
        and data.get("sale_ready") is False
        and data.get("buyer_data_room") is False
        and data.get("state") == "SHELL",
    )
    page = data["system_page"]
    check(
        "system page",
        page.get("present") is True
        and page.get("page_type") == "SYSTEM"
        and page.get("title") == "Wolf · Sale evidence pack"
        and page.get("nav_says_sale_readiness") is True
        and page.get("buyer_data_room") is False,
        str(page),
    )
    pack = data["evidence_pack"]
    check(
        "checklist is empty",
        pack.get("cap") == "CAP-SALE-01"
        and pack.get("controls_read") == 60
        and pack.get("controls_expected") == 60
        and pack.get("control_list_matches_canon") is True
        and pack.get("empty_slots") == 60
        and pack.get("filled_slots") == 0
        and pack.get("maturity") == "SPECIFIED"
        and pack.get("proven") is False
        and pack.get("ready") is False
        and pack.get("cr_state") == "OPEN"
        and pack.get("buyer_export") is False
        and pack.get("evidence_invented") is False,
        str(pack),
    )
    built = data["data_room"]
    check(
        "room is not on disk",
        built.get("cap") == "CAP-SALE-02"
        and built.get("on_disk") is False
        and built.get("document_count") == 0
        and built.get("buyer_count") == 0
        and built.get("buyer_access") is False
        and built.get("live_share") is False
        and built.get("empty_slots") == 60
        and built.get("filled_slots") == 0
        and built.get("proven") is False
        and built.get("ready") is False
        and built.get("documents_invented") is False,
        str(built),
    )
    gaps = {row["id"]: row for row in data["gaps"]}
    check(
        "gaps are empty counts",
        gaps["FINANCE"]["empty_controls"] == 12
        and gaps["HR"]["empty_controls"] == 15
        and gaps["LEGAL"]["empty_controls"] == 6
        and gaps["OPS"]["empty_controls"] == 12
        and gaps["COMPLIANCE"]["empty_controls"] == 3
        and gaps["TECH"]["empty_controls"] == 9
        and gaps["UNKNOWN"]["empty_controls"] == 3
        and all(row.get("filled_controls") == 0 and row.get("evidence") is None for row in data["gaps"]),
        str({key: row.get("empty_controls") for key, row in gaps.items()}),
    )
    desk = (ROOT / "dashboards" / "sale-readiness.html").read_text(encoding="utf-8")
    check("page title", "<title>Sale readiness</title>" in desk)
    check("tiles start closed", desk.count("<details>") >= 4 and "<details open" not in desk)
    check("page refuses the room", "This is not a buyer data room" in desk)
    refused = sale.refuse_write()
    check(
        "refuse write",
        refused.get("error") == "writes_off"
        and refused.get("buyer_data_room") is False
        and refused.get("sale_ready") is False,
    )
    check(
        "files unread",
        evidence.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and evidence.SALE_CSV.stat().st_mtime_ns == csv_mtime
        and evidence.LEDGER_JSON.stat().st_mtime_ns == ledger_mtime
        and sale.PAGE.stat().st_mtime_ns == page_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
