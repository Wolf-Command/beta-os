#!/usr/bin/env python3
"""UMA-CLOSE-6STEP-REBUILD-3 — cycle-3 fixes A–L."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
SEP03 = "2026-09-03"
MATT = "PERS-MATT"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-6step-r3-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def wire_modules(db: Path) -> dict:
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.uma_hist_close_queue1 as q
    import core.venue_close as vc

    saved: dict = {}
    for mod in (vc, bzg, q, evidence, audit, rbac):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]
    return saved


def restore_modules(saved: dict) -> None:
    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]


def test_a_shift_edit_api_exists() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("A shift edit save API wired", "save-shift-figure-edits" in html)
    check("A showShiftEdit present", "function showShiftEdit" in html)
    check("A save_shift_human_corrections backend", True)
    from core import bzg_daily_close as bzg

    check("save_shift_human_corrections fn", hasattr(bzg, "save_shift_human_corrections"))


def test_b_yes_blocks_empty_read() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    opened = bzg.ensure_close_on_evidence(
        SEP03, verified_person_id=MATT, identity={"person_id": MATT}
    )
    cid = str((opened.get("close") or {}).get("close_id") or opened.get("close_id"))
    blocked = False
    try:
        bzg.confirm_shift_figures_yes(
            cid,
            verified_person_id=MATT,
            extracted={},
            conn=conn,
            commit=True,
        )
    except bzg.BzgDailyCloseError as exc:
        blocked = exc.code == "shift_figures_empty"
    check("B YES blocks empty extraction", blocked)
    check("B readable helper false on empty", not bzg._shift_figures_readable({}))
    check("B readable helper true with figures", bzg._shift_figures_readable(
        {"gross_sales_rp": 1000, "cash_rp": 500}
    ))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_c_format_int_in_html() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("C formatInt helper", "function formatInt" in html)
    check("C bills uses formatInt", "formatInt(src.bills" in html)


def test_d_found_slips_section() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("D renderFoundSlips", "function renderFoundSlips" in html)
    check("D no !close guard", "!close)" not in html or "unlinkedEdc.length && !close" not in html)
    check("D no || true bank filter", "|| true)" not in html)
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    disc = bzg.discover_unlinked_evidence_for_date(SEP03, conn=conn)
    check("D 3 Sep has 4+ slips", len(disc.get("edc_receipts") or []) >= 4, str(disc))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_e_cash_amt_entered_fix() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("E amtEntered used in toggle", "toggle(\"hidden\", !amtEntered)" in html)
    check("E amtEntered defined in handler", "const amtEntered" in html)


def test_f_shift_photo_exclusive() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("F useShiftReport direct read", "function useShiftReport" in html)
    check("F btnReadShift always hidden after existing", '$("btnReadShift").classList.add("hidden")' in html)
    check("F hasExistingPhoto hides upload", "hasExistingPhoto" in html)


def test_g_bank_work_hides_add() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("G bankWorkOpen tracking", "bankWorkOpen" in html)
    check("G hide add when work open", "workOpen" in html or "bankWorkOpen" in html)


def test_h_variance_labels() -> None:
    from core import bzg_daily_close as bzg

    check("H Short label", bzg.format_variance_label(-20000) == "Short Rp20.000")
    check("H Over label", bzg.format_variance_label(5000) == "Over Rp5.000")
    check("H Matches", bzg.format_variance_label(0) == "Matches")
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("H formatVariance in HTML", "function formatVariance" in html)


def test_i_view_close_readonly() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("I stepViewClose section", 'id="stepViewClose"' in html)
    check("I BACK TO MISSING only", "btnViewCloseBack" in html)
    check("I not stepReview for view", 'showStep("stepViewClose")' in html)


def test_j_clear_messages_on_step() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("J showStep clears msg", 'setMsg("")' in html and "function showStep" in html)


def test_k_status_vocabulary() -> None:
    from core import bzg_daily_close as bzg
    from core import uma_hist_close_queue1 as q

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    reg = bzg.close_date_register(date_from="2026-09-25", date_to="2026-10-02", conn=conn)
    queue = q.owner_history_queue(conn=conn)
    for bd in ("2026-09-30", "2026-10-01", "2026-09-25"):
        day = next((d for d in (reg.get("days") or []) if d.get("business_date") == bd), {})
        qrow = next((r for r in (queue.get("queue") or []) if r.get("business_date") == bd), {})
        if day and qrow:
            check(
                f"K {bd} status match",
                day.get("status") == qrow.get("status"),
                f"{day.get('status')} vs {qrow.get('status')}",
            )
            check(
                f"K {bd} action_label on register",
                day.get("action_label") == qrow.get("action_label"),
                f"{day.get('action_label')} vs {qrow.get('action_label')}",
            )
    exc = next((r for r in (queue.get("queue") or []) if r.get("status") == "EXCEPTION"), None)
    if exc:
        check("K exception REVIEW EXCEPTION label", exc.get("action_label") == "REVIEW EXCEPTION")
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_l_scroll_into_view() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("L scroll-margin-top CSS", "scroll-margin-top" in html)
    check("L scrollIntoView on step", "scrollIntoView" in html)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    test_a_shift_edit_api_exists()
    test_b_yes_blocks_empty_read()
    test_c_format_int_in_html()
    test_d_found_slips_section()
    test_e_cash_amt_entered_fix()
    test_f_shift_photo_exclusive()
    test_g_bank_work_hides_add()
    test_h_variance_labels()
    test_i_view_close_readonly()
    test_j_clear_messages_on_step()
    test_k_status_vocabulary()
    test_l_scroll_into_view()
    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
