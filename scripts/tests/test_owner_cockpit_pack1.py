#!/usr/bin/env python3
"""Pack 1 — Owner cockpit keeps the pulse and does not invent the dropped questions."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import owner_cockpit as cockpit  # noqa: E402

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
    before = {path: path.stat().st_mtime_ns for path in (
        cockpit.R2_STATE, cockpit.OFFBOX, cockpit.DAEMON_STATUS, cockpit.WOLF_TASKS, cockpit.PEACHES_THREADS,
    ) if path.is_file()}
    data = cockpit.load_cockpit()
    after = {path: path.stat().st_mtime_ns for path in before}
    check("sources unread-only", before == after)
    check("staff_ready false", data.get("staff_ready") is False and data.get("human_proven") is False)
    check("read only", data.get("read_only") is True and data.get("writes") is False)

    pulse = data.get("pulse") or {}
    tiles = pulse.get("tiles") or []
    ids = [t.get("id") for t in tiles]
    check("ten pulse cards", len(tiles) == 10, str(ids))
    check("unknown lines kept", any("UNKNOWN" in str(t.get("why") or "") + str(t.get("value") or "") for t in tiles))

    by_id = {t.get("id"): t for t in tiles}
    check("occ desk", (by_id.get("atrium_occ") or {}).get("href") == "/amg/sales-desk#occ")
    check("kuta desk", (by_id.get("kuta_rates") or {}).get("href") == "/amg/sales-desk#kuta")
    check("uma desk", (by_id.get("bzg_night") or {}).get("href") == "/bzg/uma-blu#closes")

    staff_ids = [t.get("id") for t in data.get("staff_primary") or []]
    check("fitness off staff primary", "fitness" not in staff_ids and len(staff_ids) == 9, str(staff_ids))
    personal_ids = [t.get("id") for t in data.get("personal_rail") or []]
    check("personal rail", set(personal_ids) == {"fitness", "trading"}, str(personal_ids))
    fitness = next(t for t in data["personal_rail"] if t.get("id") == "fitness")
    check(
        "fitness personal partial",
        fitness.get("state") == "PARTIAL" and fitness.get("staff_primary") is False and fitness.get("live") is False,
        str(fitness.get("state")),
    )
    trading = next(t for t in data["personal_rail"] if t.get("id") == "trading")
    check(
        "trading partial",
        trading.get("state") == "PARTIAL" and trading.get("live_broker") is False and trading.get("staff_primary") is False,
        str(trading.get("state")),
    )

    restored = {t.get("id"): t for t in data.get("restored") or []}
    check("restored set", set(restored) == {"brief", "r2_gap", "system", "asks", "peaches", "content", "money"})

    brief = restored["brief"]
    check(
        "brief not a ready stamp",
        brief.get("state") in ("PARTIAL", "UNKNOWN")
        and brief.get("rebuilt") is False
        and "Ready" not in str(brief.get("value") or "")
        and brief.get("body_copied") is not True,
        str(brief),
    )
    r2 = restored["r2_gap"]
    check(
        "r2 not live zero",
        r2.get("state") != "LIVE"
        and r2.get("live_absent_count") is None
        and r2.get("remeasured") is False
        and r2.get("v1_zero_absent_used_as_live") is False
        and "0 absent" not in str(r2.get("value") or ""),
        str(r2.get("value")),
    )
    system = restored["system"]
    check(
        "system opens no job",
        system.get("opens_job") is False
        and system.get("treated_as_green") is False
        and system.get("fault_job_id") is None
        and "14/14" not in str(system.get("value") or ""),
        str(system.get("value")),
    )
    asks = restored["asks"]
    check(
        "asks not invented",
        asks.get("answer_in_place") is False
        and asks.get("titles_copied") is False
        and isinstance(asks.get("open_count"), int),
        str(asks),
    )
    peaches = restored["peaches"]
    check(
        "peaches not live",
        peaches.get("live") is False
        and peaches.get("state") != "LIVE"
        and peaches.get("text_included") is False
        and peaches.get("beta_store") is False,
        str(peaches.get("value")),
    )
    content = restored["content"]
    check(
        "content desk",
        content.get("href") == "/content/tick-draft"
        and content.get("publish") == "OFF"
        and content.get("haikal_upload_retest") == "OPEN"
        and "MISA-CBA83917AE23" in (content.get("queue_ids") or []),
        str(content.get("value")),
    )
    money = restored["money"]
    check("money has no figure", money.get("value") is None and money.get("figure_invented") is False)
    refused = cockpit.refuse_write()
    check("write refused", refused.get("ok") is False and refused.get("writes") is False and refused.get("staff_ready") is False)
    check("auth documented", "403" in (data.get("auth") or {}).get("empire_page", ""))

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
