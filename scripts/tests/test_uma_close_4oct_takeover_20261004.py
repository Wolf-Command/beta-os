#!/usr/bin/env python3
"""UMA-CLOSE-4OCT — finished bills off cash block; governance; takeover RBAC.

Temp in-memory sqlite only. Does not touch live VDC-64f5f529 or protected closes.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
BETA = "http://127.0.0.1:8788"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog_conn() -> tuple[Path, sqlite3.Connection]:
    td = Path(tempfile.mkdtemp(prefix="uma-close-4oct-takeover-"))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return db, conn


def fetch_served_page() -> tuple[int | None, str]:
    try:
        req = urllib.request.Request(BETA + "/uma-blu-close", method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"NOTE  served page unavailable: {exc}")
        return None, ""


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["WOLF_CLOSE_VISION_DRY"] = "1"

    from core import bzg_daily_close as bzg
    from core import rbac as _rbac
    from core import venue_close as vc

    html = UI.read_text(encoding="utf-8")

    m = re.search(
        r"function renderStaffCashBox\(cl\) \{([\s\S]*?)\n  \}",
        html,
    )
    check("renderStaffCashBox present", m is not None)
    cash_body = m.group(1) if m else ""
    check(
        "renderStaffCashBox excludes Finished bills",
        "Finished bills" not in cash_body,
        "Finished bills must not appear inside the cash box renderer",
    )
    check(
        "renderStaffCashBox keeps Difference money line",
        'staffCashLine("Difference", diffLabel)' in cash_body,
    )
    check(
        "renderStaffCashBox keeps ESB cash from payments",
        'staffCashLine("ESB cash", staffCashAmount(esbCash))' in cash_body,
    )

    fb = re.search(
        r"function renderFinishedBillsSection\(cl\) \{([\s\S]*?)\n  \}",
        html,
    )
    check("renderFinishedBillsSection present", fb is not None)
    fb_body = fb.group(1) if fb else ""
    check(
        "finished bills in separate operational section",
        "finished-bills-section" in fb_body and "Finished bills" in fb_body,
    )
    check(
        "renderClose wires finished bills section outside cash box",
        "renderFinishedBillsSection(close)" in html
        and html.index("renderFinishedBillsSection(close)") > html.index("renderStaffCashBox(close)"),
    )

    served_code, served = fetch_served_page()
    served_body = served if served_code == 200 else html
    served_via = "http" if served_code == 200 else "disk"
    if served_code not in (200, 403, None):
        print(f"NOTE  served page status: {served_code}")
    sm = re.search(
        r"function renderStaffCashBox\(cl\) \{([\s\S]*?)\n  \}",
        served_body,
    )
    served_cash = sm.group(1) if sm else ""
    check(
        f"served page cash box excludes Finished bills ({served_via})",
        "Finished bills" not in served_cash,
    )
    check(
        f"served page has finished-bills-section ({served_via})",
        "finished-bills-section" in served_body and "renderFinishedBillsSection" in served_body,
    )

    check(
        "photo inputs: esbCam capture environment",
        'id="esbCam"' in html and 'capture="environment"' in html,
    )
    check(
        "photo inputs: esbFile library upload",
        'id="esbFile"' in html and 'accept="image/*"' in html,
    )
    check("takeover button wired", 'id="btnTakeOver"' in html)
    check("governance masthead hook", 'id="mastGovernance"' in html)

    _db, conn = temp_catalog_conn()
    prev_vc = vc.CATALOG_DB
    prev_bzg = bzg.CATALOG_DB
    vc.CATALOG_DB = _db
    bzg.CATALOG_DB = _db
    try:
        biz = "2099-10-04"
        ts = "2099-10-04T13:24:15Z"
        cid = f"VDC-TEST-GOV-{uuid.uuid4()}"
        iza = "PERS-IZA"
        matt = "PERS-MATT"
        conn.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              submitted_by_person_id, taken_by_person_id, taken_at,
              declared_cash_amount, created_at, updated_at,
              esb_totals_json, esb_fingerprint_sha256
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, 'DATA_CAPTURED',
                      ?, ?, ?, NULL, ?, ?,
                      ?, 'sha-test-finished-off-cash')
            """,
            (
                cid,
                biz,
                iza,
                iza,
                ts,
                ts,
                ts,
                '{"cash_from_payments":360000,"finished_count":61}',
            ),
        )
        conn.commit()

        row = vc.get_close(cid, conn=conn)
        gov_before = vc.close_governance_info(row, conn=conn)
        check(
            "governance before takeover: original Iza",
            gov_before is not None
            and gov_before.get("original_closer_person_id") == iza
            and not gov_before.get("taken_over"),
            str(gov_before),
        )

        target = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
        check(
            "takeover permission is venue.close.reassign not hardcoded email",
            _rbac.can(matt, "venue.close.reassign", target, conn=conn),
            "PERS-MATT needs reassign via RBAC",
        )

        out = vc.take_over_venue_close(
            cid,
            verified_person_id=matt,
            reason="Iza shift ended / Owner takeover after workflow failure",
            conn=conn,
            commit=True,
        )
        check("takeover same close id", out.get("close_id") == cid)
        check("takeover preserves submitted_by Iza", out.get("submitted_by_person_id") == iza)
        check("takeover holder is Matt", out.get("taken_by_person_id") == matt)
        check("declared stayed null", out.get("declared_cash_amount") is None)

        enriched = bzg.enrich_close(vc.get_close(cid, conn=conn), conn=conn)
        gov_after = enriched.get("governance") if enriched else None
        check(
            "governance after takeover shows original + taken over",
            gov_after is not None
            and gov_after.get("original_closer_person_id") == iza
            and gov_after.get("taken_over") is True
            and gov_after.get("taken_over_by_person_id") == matt,
            str(gov_after),
        )
        check(
            "takeover reason audited",
            gov_after is not None
            and gov_after.get("takeover_reason")
            == "Iza shift ended / Owner takeover after workflow failure",
            str(gov_after.get("takeover_reason")),
        )

        sc = bzg.staff_cash_summary(cid, conn=conn)
        diff_label = str(sc.get("difference_label") or "")
        finished = sc.get("finished_bills")
        check(
            "difference cannot calculate without cash count",
            diff_label == "Cannot calculate yet",
            diff_label,
        )
        check(
            "difference label does not contain finished-bill count",
            finished is not None and str(finished) not in diff_label,
            f"diff={diff_label!r} finished={finished!r}",
        )
        check(
            "finished bills available separately from API",
            finished == 61,
            str(finished),
        )
        check(
            "ESB cash from cash_from_payments not finished_count",
            sc.get("esb_cash") == 360000.0 and sc.get("esb_cash_field") == "cash_from_payments",
            str(sc.get("esb_cash")),
        )
    finally:
        conn.close()
        vc.CATALOG_DB = prev_vc
        bzg.CATALOG_DB = prev_bzg

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
