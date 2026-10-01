#!/usr/bin/env python3
"""Pack 3 — Atrium sales desk reads the V1 sqlite. No writes."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import amg_sales_desk_ro as desk  # noqa: E402

PASS = 0
FAIL = 0
DB = Path.home() / ".openclaw/workspace/wolf-system/atrium/atrium_sales.sqlite"
VIEWS = [
    "overview", "milestones", "payments", "newsale", "inventory", "deals",
    "leads", "comms", "cv", "payables", "tax", "vendors", "commonarea", "exceptions",
]


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    before = DB.stat()
    siblings = {
        p.name: p.stat().st_mtime_ns
        for p in DB.parent.glob(DB.name + "*")
    }
    index = desk.load_sales_desk()
    after = DB.stat()
    check("index ok", index.get("ok") is True, str(index.get("error")))
    check("staff_ready false", index.get("staff_ready") is False)
    check("writes false", index.get("writes") is False)
    check("units 88", index.get("counts", {}).get("units") == 88, str(index.get("counts")))
    check("leads 570", index.get("counts", {}).get("leads") == 570, str(index.get("counts")))
    check("payments 399", index.get("counts", {}).get("payments") == 399, str(index.get("counts")))
    check("sqlite mtime unchanged", before.st_mtime_ns == after.st_mtime_ns and before.st_size == after.st_size)
    after_siblings = {p.name: p.stat().st_mtime_ns for p in DB.parent.glob(DB.name + "*")}
    check("no new sqlite sidecar", set(siblings) == set(after_siblings), str(set(after_siblings) - set(siblings)))
    ids = [v.get("id") for v in index.get("views") or []]
    check("14 views", ids == VIEWS, str(ids))
    occ = index.get("occupancy") or {}
    check("in-house unknown", occ.get("in_house") == "UNKNOWN" and occ.get("guests") is None)
    check("occ not merged", occ.get("merged_pct") is None and occ.get("adr") is None)
    y = occ.get("yanolja") or {}
    check(
        "yanolja vacant versus rooms",
        isinstance(y.get("rooms_vacant"), int) and isinstance(y.get("rooms_total"), int) and y.get("guests") is None,
        str(y),
    )
    v1 = occ.get("v1_master_tile") or {}
    check("v1 tile labeled apart", v1.get("not_merged") is True and v1.get("val"), str(v1))
    kuta = index.get("kuta") or {}
    check("kuta on desk", kuta.get("learn_only") is True and kuta.get("booking") is False and kuta.get("official_total", 0) > 0, str(kuta.get("headline")))
    check("tax ceiling locked", index.get("source", {}).get("tax_ceiling") == 4_800_000_000)

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    unresolved = conn.execute("SELECT COUNT(*) FROM exceptions WHERE resolved=0").fetchone()[0]
    try:
        conn.execute("INSERT INTO leads(name) VALUES ('pack3-should-fail')")
        write_blocked = False
    except sqlite3.OperationalError:
        write_blocked = True
    conn.close()
    check("direct insert blocked", write_blocked)
    check("exceptions are unresolved", index.get("view_totals", {}).get("exceptions") == unresolved, str(unresolved))

    for vid in VIEWS:
        payload = desk.load_sales_desk(view=vid, limit=40)
        ok = (
            payload.get("ok") is True
            and payload.get("view") == vid
            and payload.get("staff_ready") is False
            and payload.get("writes") is False
            and payload.get("total") == index["view_totals"][vid]
            and len(payload.get("rows") or []) <= 40
        )
        check(f"view {vid}", ok, f"total={payload.get('total')} err={payload.get('error')}")

    leads = desk.load_sales_desk(view="leads", limit=5)
    row = (leads.get("rows") or [None])[0]
    check("lead row has no email", isinstance(row, dict) and "email" not in row and "phone" not in row, str(row))
    if isinstance(row, dict):
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        hit = conn.execute("SELECT name FROM leads WHERE id=?", (row.get("id"),)).fetchone()
        conn.close()
        check("lead name matches sqlite", hit is not None and hit[0] == row.get("name"), str(hit))
    newsale = desk.load_sales_desk(view="newsale", limit=5)
    check("newsale writes off", newsale.get("writes_enabled") is False and newsale.get("post") == "refused")
    refused = desk.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("staff_ready") is False)
    unknown = desk.load_sales_desk(view="housekeeping")
    check("housekeeping not a view", unknown.get("ok") is False and unknown.get("error") == "unknown_view")
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
