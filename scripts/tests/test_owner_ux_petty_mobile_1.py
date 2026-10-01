#!/usr/bin/env python3
"""OWNER-UX-PETTY-MOBILE-1 — Owner Home language + hierarchy + Uma petty phone.

Beta only. staff_ready stays false. No invent opening float.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import wolf_shell as shell  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import audit as audit  # noqa: E402
from core import authority as authority  # noqa: E402
from core import evidence as evidence  # noqa: E402
from core import venue_close as venue_close  # noqa: E402
from core import work_items as work_items  # noqa: E402

PASS = 0
FAIL = 0

OWNER_HTML = ROOT / "dashboards" / "owner-empire-pack.html"
PETTY_HTML = ROOT / "dashboards" / "bzg-uma-blu-petty.html"
SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
ORDER = ROOT / "state" / "build-factory" / "OWNER-ORDER-UX-RESET-MOBILE-COMMISSION-20261002.json"
BRIEF = ROOT / "state" / "build-factory" / "briefs" / "BRIEF-OWNER-UX-PETTY-MOBILE-1.md"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    check("order stamp exists", ORDER.is_file())
    check("brief exists", BRIEF.is_file())
    check("cache token", shell.CACHE_TOKEN == "20261002-owner-ux-petty")
    check("sidenav cache matches", f'CACHE = "{shell.CACHE_TOKEN}"' in SIDENAV.read_text(encoding="utf-8"))

    # --- hierarchy ---
    cat = shell.business_catalog_from_ia()
    keys = [b["id"] for b in cat]
    check("top has owner ggv amg bzg", keys[:4] == ["owner", "ggv", "amg", "bzg"] or set(keys) >= {"owner", "ggv", "amg", "bzg"})
    check("top excludes uma", "uma" not in keys)
    outlets = shell.bzg_outlet_catalog()
    titles = " ".join(o.get("title") or "" for o in outlets)
    for need in ("Uma Blu", "Blu Zone Restaurant", "Pool Bar", "Merah", "Rooftop", "Room Service", "Catering"):
        check(f"outlet {need}", need in titles)
    check("pre-opening in catalog", "PRE-OPENING" in titles)

    matt = shell.build_whoami(person_id="PERS-MATT", email="mrwolf@wolfcommand.net")
    bids = [b["id"] for b in (matt.get("businesses") or [])]
    check("matt no uma top chip", "uma" not in bids)
    check("matt has bzg", "bzg" in bids)
    check("matt context hidden", matt.get("context_switcher") is False)
    check("matt outlets present", any(o.get("id") == "uma" for o in (matt.get("outlet_children") or [])))
    check(
        "uma path activates bzg",
        shell.active_business_id("/bzg/uma-blu/petty", matt.get("businesses") or []) == "bzg",
    )

    devi = shell.build_whoami(person_id="PERS-DEVI", email="deviputu236@gmail.com")
    db = [b["id"] for b in (devi.get("businesses") or [])]
    check("devi uma or bzg", "uma" in db or "bzg" in db)

    # --- Owner Home human language ---
    oh = OWNER_HTML.read_text(encoding="utf-8")
    check("owner h1 Owner Home", "Owner Home" in oh)
    check("owner lede human job", "How are the businesses" in oh or "What needs you" in oh)
    check("freshness in diagnostics", "System diagnostics" in oh and 'id="freshness-badge"' in oh)
    check("no staff_ready in lede", "staff_ready=false" not in oh.split("<h2>")[0])
    check("no desktop_gate in primary", "desktop_gate_ready" not in oh.split("System diagnostics")[0])
    check("answers section present", 'data-answer="okay"' in oh and 'data-answer="blocked"' in oh)

    # --- Petty phone surface ---
    ph = PETTY_HTML.read_text(encoding="utf-8")
    check("petty capture camera", 'capture="environment"' in ph)
    check("petty no overflow-x body", "overflow-x: hidden" in ph)
    check("petty thumb height", "--thumb" in ph or "min-height: 48px" in ph or "var(--thumb)" in ph)
    check("petty category field", 'id="category"' in ph)
    check("petty outlet field", 'id="outlet"' in ph)
    check("petty person field", 'id="logged_by"' in ph)
    check("petty receipt upload route", "/api/bzg/uma-blu/petty/receipt" in ph)
    check("petty staff_ready false attr", 'data-staff-ready="false"' in ph)
    check("petty float not invented copy", "not set yet" in ph.lower() or "not invented" in ph.lower())
    check("petty cards not tables", "<table" not in ph.lower())

    # --- service: no invent float; phone fields persist ---
    scratch = ROOT / "state" / "tmp-owner-ux-petty-mobile-1"
    scratch.mkdir(parents=True, exist_ok=True)
    db = scratch / "content_library.sqlite"
    if db.exists():
        db.unlink()
    live = ROOT / "catalog" / "content_library.sqlite"
    shutil.copy2(live, db)
    ops.CATALOG_DB = db
    ops.PETTY_RECEIPT_DIR = scratch / "receipts"
    for m in (audit, authority, evidence, venue_close, work_items, ops):
        if hasattr(m, "CATALOG_DB"):
            m.CATALOG_DB = db
    conn = ops.db_connect(db)
    try:
        ops.ensure_schema(conn)
        conn.execute("DELETE FROM bzg_ops_petty_movements")
        conn.execute("DELETE FROM bzg_ops_petty_days")
        conn.commit()
        listed = ops.list_petty(conn=conn)
        check("float NOT_FOUND", listed.get("float_status") == "NOT_FOUND")
        check("phone_workflow flag", listed.get("phone_workflow") is True)
        check("staff_ready false api", listed.get("staff_ready") is False)
        check("categories present", "Transport" in (listed.get("categories") or []))
        saved = ops.save_petty_receipt_bytes(
            data=b"\xff\xd8\xff\xe0fakejpeg",
            filename="tin.jpg",
            content_type="image/jpeg",
        )
        check("receipt evidence id", str(saved.get("evidence_id") or "").startswith("EVD-PETTY-"))
        row = ops.insert_petty_movement(
            business_date="2026-10-02",
            direction="OUT",
            amount=75000,
            currency="IDR",
            purpose="Milk run",
            category="Food",
            outlet="Uma Blu",
            logged_by="PERS-DEVI",
            receipt_path=saved["receipt_path"],
            evidence_id=saved["evidence_id"],
            example=True,
            conn=conn,
        )
        conn.commit()
        check("movement category", row.get("category") == "Food")
        check("movement outlet", row.get("outlet") == "Uma Blu")
        check("movement logged_by", row.get("logged_by") == "PERS-DEVI")
        check("movement receipt", bool(row.get("receipt_path") or row.get("evidence_id")))
        check("no invent float on day", ops.get_petty_day("2026-10-02", conn=conn).get("opening_float") is None)
        big = ops.insert_petty_movement(
            business_date="2026-10-02",
            direction="OUT",
            amount=600000,
            purpose="Emergency",
            category="Supplies",
            outlet="Uma Blu",
            logged_by="PERS-DEVI",
            example=True,
            conn=conn,
        )
        conn.commit()
        check("500k needs approval", int(big.get("needs_approval") or 0) == 1)
    finally:
        conn.close()
        try:
            if db.exists():
                db.unlink()
        except OSError:
            pass

    # sidenav outlet chips
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav outlet chips", "nv-outlet-chip" in sn)
    check("sidenav no uma top IA", not re.search(r'key:\s*"uma"', sn.split("BUSINESSES")[1].split("INTELLIGENCE")[0]))

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
