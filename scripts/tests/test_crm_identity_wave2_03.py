#!/usr/bin/env python3
"""Wave 2.03 — CRM stores stay separate. No invented merge."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import crm_identity_wave2_03 as crm  # noqa: E402

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
    glance_mtime = crm.GLANCE.stat().st_mtime_ns
    catalog_mtime = crm.CATALOG_DB.stat().st_mtime_ns
    guest_mtime = crm.GUEST_DB.stat().st_mtime_ns
    data = crm.load_identity()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False and data.get("writes") is False)
    check("not one crm", data.get("one_crm") is False and data.get("master_table_written") is False)
    habitat = data["sources"]["habitat_sheet"]
    check(
        "habitat count only",
        habitat.get("count") == 271
        and habitat.get("as_of_wita") == "2026-10-01T09:43:42+08:00"
        and habitat.get("write") is False
        and habitat.get("join_keys") == "UNAVAILABLE"
        and habitat.get("email_rows") is None,
        str(habitat),
    )
    leads = data["sources"]["core_leads"]
    check(
        "core leads are fixtures",
        leads.get("count") == 8
        and leads.get("fixture_only") is True
        and leads.get("email_rows") == 0
        and leads.get("phone_rows") == 0
        and leads.get("join_keys") == "UNAVAILABLE",
        str(leads),
    )
    guest = data["sources"]["guest_profiles"]
    check(
        "one guest profile",
        guest.get("guests") == 1
        and guest.get("visits") == 1
        and guest.get("observations") == 2
        and guest.get("email_rows") == 1
        and guest.get("phone_rows") == 1
        and guest.get("businesses") == ["AMG"]
        and guest.get("values_omitted") is True,
        str(guest),
    )
    onboard = data["sources"]["ggv_onboard"]
    check("ggv onboard shell", onboard.get("state") == "SHELL" and onboard.get("count") is None and onboard.get("table") is None)
    join = data["join"]
    check(
        "join unavailable",
        join.get("state") == "UNAVAILABLE" and join.get("matched_pairs") is None and join.get("compared") is False,
        str(join),
    )
    page = (ROOT / "dashboards" / "crm-identity-wave2.html").read_text(encoding="utf-8")
    check("page title", "<title>CRM identity</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page refuses one crm", "Not one customer record" in page)
    refused = crm.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("one_crm") is False)
    check(
        "files unread",
        crm.GLANCE.stat().st_mtime_ns == glance_mtime
        and crm.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and crm.GUEST_DB.stat().st_mtime_ns == guest_mtime
        and crm.IDENTITY_DB.is_file() is False,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
