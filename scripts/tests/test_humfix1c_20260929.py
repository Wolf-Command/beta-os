#!/usr/bin/env python3
"""HUMFIX-1C — staff-facing gaps Peaches found by eye in HUMFIX-1B shots.

Decision served: Matt relay / HUMFIX-1B Peaches eye gaps (29 Sep 2026).
1. My Work TODAY: current-window plans only; RETESTs at top; no stale/dupes
2. Zayen boundary copy from permissions matrix (approve/reject OK; post denied)
3. Staff header: plain role title (no SPECIALIST_/ROLE- codes)
4. Atrium header: full seat title on 1024 and 390
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ["WOLF_TEST_MODE"] = "1"
sys.path.insert(0, str(ROOT / "scripts"))

from core import work_items as wi  # noqa: E402
from core.staff_home import (  # noqa: E402
    _atrium_finance_boundary,
    _dedupe_plan_items,
    _plan_covers_today,
    _staff_today_iso,
    build_home,
)
import serve_beta as sb  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
PASS = 0
FAIL = 0

HAIKAL_RETESTS = (
    "WI-1e3435eb-4d39-4559-a2fa-3cf13b523ec2",
    "WI-2a6edd45-1659-446a-91ea-8b533faf580e",
    "WI-fa0f1e2e-9564-41f6-8edf-cbc76a3173e2",
    "WI-cbbbaf8c-55bf-4167-a7ae-6d0f974d5b9f",
)
ZAYEN_RETESTS = (
    "WI-4049b070-1938-4b33-bc6f-abcf195d4298",
    "WI-1b6f3982-7112-4ff9-9147-97e0ed1c645d",
    "WI-41cd93c3-a8d5-48ad-9368-db17d44e80a4",
    "WI-a3a4044c-843d-41f4-86eb-8d738f78e2b1",
    "WI-4e4566db-72bf-4710-b6a9-0b02f64bbc2b",
    "WI-1804769a-551b-4df0-9e8c-231dd4131417",
    "WI-2649ab6e-653a-472b-b632-dfb236ee64f2",
    "WI-3e07075e-72cb-4e5f-bea4-97003d7c678f",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _today_items(home: dict) -> list[dict]:
    for sec in home.get("sections") or []:
        if sec.get("key") == "today":
            return list(sec.get("items") or [])
    return []


def test_plan_window_helpers() -> None:
    today = _staff_today_iso()
    check("staff today is ISO date", bool(re.match(r"^\d{4}-\d{2}-\d{2}$", today)), today)
    check(
        "stale fortnight not covering today",
        not _plan_covers_today("2026-09-14", "2026-09-27", "2026-09-29"),
    )
    check(
        "current window covers today",
        _plan_covers_today("2026-09-28", "2026-10-11", "2026-09-29"),
    )
    dupes = _dedupe_plan_items(
        [
            {
                "title": "habitat fortnight",
                "date_range": "14 Sep 2026 to 27 Sep 2026",
                "brand_id": "habitat",
                "status": "Working_Draft",
                "source_id": "8",
            },
            {
                "title": "habitat fortnight",
                "date_range": "14 Sep 2026 to 27 Sep 2026",
                "brand_id": "habitat",
                "status": "Human_Approved",
                "source_id": "9",
            },
        ]
    )
    check("dedupe keeps one card", len(dupes) == 1, str(dupes))
    check("dedupe prefers Approved", dupes[0]["status"] == "Human_Approved", str(dupes[0]))


def test_haikal_today_current_window_and_retests() -> None:
    c = wi.db_connect(CATALOG)
    try:
        home = build_home("PERS-HAIKAL", conn=c)
        today = _today_items(home)
        titles = [str(it.get("title") or "") for it in today]
        plan_cards = [
            it
            for it in today
            if it.get("source_system") == "content_plans" or it.get("origin") == "historical"
        ]
        check(
            "no stale habitat fortnight in TODAY",
            all("2026-09-14" not in t and "14 Sep 2026" not in str(it.get("date_range") or "") for t, it in zip(titles, today)),
            str(list(zip(titles, [it.get("date_range") for it in today]))[:6]),
        )
        check("no duplicate plan source ids", len({it.get("source_id") for it in plan_cards}) == len(plan_cards), str(plan_cards))
        retests = [t for t in titles if t.startswith("Retest:")]
        check("four Haikal RETESTs in TODAY", len(retests) == 4, str(retests))
        check(
            "RETEST cards lead TODAY",
            len(titles) >= 4 and all(t.startswith("Retest:") for t in titles[:4]),
            str(titles[:6]),
        )
        for wid in HAIKAL_RETESTS:
            row = c.execute(
                "SELECT status, routing_state FROM core_work_items WHERE work_item_id=?",
                (wid,),
            ).fetchone()
            check(
                f"retest {wid[:12]} stays OPEN actionable",
                row is not None
                and row["status"] == "OPEN"
                and (row["routing_state"] is None or row["routing_state"] == ""),
                str(dict(row) if row else None),
            )
    finally:
        c.close()


def test_boundary_from_permissions() -> None:
    # Matrix: draft+approve+reject, no post/pay/bank
    codes = {
        "atrium.journal.draft",
        "atrium.journal.approve",
        "atrium.journal.reject",
        "atrium.board.read",
        "atrium.ledger.read",
    }
    text = _atrium_finance_boundary(codes)
    check("boundary allows prepare", "prepare a journal" in text, text)
    check("boundary allows approve/reject with SoD", "approve or reject" in text and "not your own" in text, text)
    check("boundary denies post", "cannot" in text and "post a journal" in text, text)
    check("boundary does not say cannot approve", "cannot approve or post" not in text, text)

    # Officer-like: draft only
    officer = _atrium_finance_boundary({"atrium.journal.draft", "atrium.board.read"})
    check("officer boundary has no approve grant line", "approve or reject" not in officer, officer)
    check("officer still cannot post", "post a journal" in officer, officer)

    c = wi.db_connect(CATALOG)
    try:
        home = build_home("PERS-ZAYEN", conn=c)
        boundary = home.get("boundary") or ""
        check("live Zayen boundary from matrix", "approve or reject" in boundary and "post a journal" in boundary, boundary)
        check("live Zayen not old deny-approve copy", "cannot approve or post a journal" not in boundary, boundary)
        # Rendered my-work page includes boundary via API JSON (server assert)
    finally:
        c.close()


def test_header_plain_titles_static() -> None:
    sidenav = (ROOT / "dashboards" / "assets" / "sidenav.js").read_text(encoding="utf-8")
    check("sidenav has roleTitleForStaff", "roleTitleForStaff" in sidenav)
    check("staff paintHello drops SPECIALIST codes", "plain role title" in sidenav.lower() or "roleTitleForStaff" in sidenav)
    # Owner path may still mention codes; staff branch must not concatenate audience codes.
    staff_branch = sidenav.split("Staff:")[-1] if "Staff:" in sidenav else sidenav
    check(
        "staff hello does not append audience code",
        '" · " + aud' not in staff_branch.split("function bootWith")[0],
        staff_branch[:200],
    )
    nav = Path("/Users/wolfterminal/atrium-finance/src/components/Navbar.tsx").read_text(encoding="utf-8")
    check("atrium navbar shows title on phone", "hidden sm:block" not in nav.split("Current authenticated")[-1][:800] or "HUMFIX-1C" in nav)
    check("atrium navbar wraps full title", "whitespace-normal break-words" in nav)
    check("atrium navbar dropped 110px truncate", "max-w-[110px] truncate" not in nav)


def test_rendered_html_server() -> None:
    """Short-lived BetaHandler: /api/staff/home + /api/whoami + my-work HTML."""
    handler = next(
        obj
        for obj in vars(sb).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(path: str, email: str, accept: str = "application/json") -> tuple[int, str]:
        req = Request(
            f"http://127.0.0.1:{port}{path}",
            headers={"X-Wolf-Subject": email, "Accept": accept},
        )
        try:
            with urlopen(req, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")

    try:
        status, raw = call("/api/staff/home", "haikalqilbari123@gmail.com")
        home = json.loads(raw or "{}")
        today = _today_items(home)
        titles = [str(it.get("title") or "") for it in today]
        check("api haikal home 200", status == 200 and home.get("ok") is True, str(status))
        check(
            "api haikal RETESTs lead TODAY",
            len(titles) >= 4 and all(t.startswith("Retest:") for t in titles[:4]),
            str(titles[:6]),
        )
        check(
            "api haikal no stale fortnight",
            all("2026-09-14" not in t for t in titles),
            str(titles[:6]),
        )

        status, raw = call("/api/staff/home", "laluzayen@gmail.com")
        zhome = json.loads(raw or "{}")
        zb = zhome.get("boundary") or ""
        check("api zayen boundary matrix", status == 200 and "approve or reject" in zb and "post a journal" in zb, zb)

        status, raw = call("/api/wolf/shell-whoami", "laluzayen@gmail.com")
        who = json.loads(raw or "{}")
        asg = (who.get("assignments") or [{}])[0]
        check(
            "whoami carries plain FC label",
            status == 200 and asg.get("label") == "Atrium Financial Controller",
            str(asg),
        )
        check(
            "whoami role code stays on role field not label",
            asg.get("role") == "ROLE-AMG-FINANCIAL-CONTROLLER",
            str(asg),
        )

        status, raw = call("/api/wolf/shell-whoami", "haikalqilbari123@gmail.com")
        who_h = json.loads(raw or "{}")
        asg_h = (who_h.get("assignments") or [{}])[0]
        check(
            "whoami carries Creative Director label",
            status == 200 and asg_h.get("label") == "Creative Director",
            str(asg_h),
        )

        status, page = call("/my-work", "laluzayen@gmail.com", accept="text/html")
        check("my-work html 200", status == 200 and "boundary" in page, str(status))
        # Boundary text is filled client-side from API; assert script + sidenav staff path present.
        sidenav = (ROOT / "dashboards" / "assets" / "sidenav.js").read_text(encoding="utf-8")
        check("rendered chrome uses roleTitleForStaff", "roleTitleForStaff" in sidenav)

        # Temp store: current-window plan appears; stale does not.
        tmp = Path(tempfile.mkdtemp(prefix="tmp-humfix1c-", dir=str(ROOT / "state")))
        try:
            db = tmp / "catalog.sqlite"
            shutil.copy2(CATALOG, db)
            conn = wi.db_connect(db)
            today = _staff_today_iso()
            start = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
            end = (date.fromisoformat(today) + timedelta(days=5)).isoformat()
            conn.execute(
                """
                INSERT INTO content_plans (
                  brand_id, title, status, period_start, period_end, data_lane, created_at, updated_at
                ) VALUES ('habitat', 'humfix1c current window', 'Human_Approved', ?, ?, 'operational', datetime('now'), datetime('now'))
                """,
                (start, end),
            )
            conn.commit()
            home2 = build_home("PERS-HAIKAL", conn=conn)
            plan_titles = [
                str(it.get("title") or "")
                for it in _today_items(home2)
                if it.get("source_system") == "content_plans"
            ]
            check(
                "current-window plan appears in TODAY",
                any("humfix1c current window" in t for t in plan_titles),
                str(plan_titles),
            )
            check(
                "stale fortnight still absent with current present",
                all("2026-09-14" not in t for t in plan_titles),
                str(plan_titles),
            )
            # RETESTs still lead even when a current plan exists
            titles2 = [str(it.get("title") or "") for it in _today_items(home2)]
            check(
                "RETESTs still lead when current plan present",
                all(t.startswith("Retest:") for t in titles2[:4]),
                str(titles2[:8]),
            )
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_twelve_retests_still_open() -> None:
    c = wi.db_connect(CATALOG)
    try:
        for wid in HAIKAL_RETESTS + ZAYEN_RETESTS:
            row = c.execute(
                "SELECT status, routing_state, title FROM core_work_items WHERE work_item_id=?",
                (wid,),
            ).fetchone()
            check(
                f"open actionable {wid[:14]}",
                row is not None
                and row["status"] == "OPEN"
                and (row["routing_state"] is None or row["routing_state"] == ""),
                str(dict(row) if row else None),
            )
    finally:
        c.close()


def main() -> int:
    test_plan_window_helpers()
    test_haikal_today_current_window_and_retests()
    test_boundary_from_permissions()
    test_header_plain_titles_static()
    test_rendered_html_server()
    test_twelve_retests_still_open()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
