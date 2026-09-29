#!/usr/bin/env python3
"""OPSFIX-1. Repair pack checks. Does not mark staff_ready or human_commissioned.

Uses a short-lived Beta handler in development_assertion. Does not switch the
live :8788 process and does not touch production :8787.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

from core.lead_spine import _row_is_demo  # noqa: E402
from core.staff_home import _plan_in_scope, build_home  # noqa: E402

import serve_beta as sb  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
YUDI = "widiatmika.11@gmail.com"
ZAYEN = "laluzayen@gmail.com"
DEVI = "deviputu236@gmail.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MATRIX = ROOT / "state" / "ops" / "testability-matrix.json"
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


def call(port: int, method: str, path: str, email: str | None = None, accept: str = "application/json"):
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type") or ""
    except HTTPError as exc:
        return exc.code, exc.read(), (exc.headers.get("Content-Type") if exc.headers else "") or ""


def test_static() -> None:
    wolf = (ROOT / "dashboards" / "owner-empire-pack.html").read_text(encoding="utf-8")
    check("owner cards have a 3 second deadline", "3000" in wolf and "data-answer" in wolf)
    check("owner cards name UNKNOWN", "UNKNOWN." in wolf)
    plan = (ROOT / "dashboards" / "content-2.0.html").read_text(encoding="utf-8")
    check("plan actions wrap", "plan-actions" in plan and "overflow-x: clip" in plan)
    progress = (ROOT / "dashboards" / "progress.html").read_text(encoding="utf-8")
    check("progress clips sideways overflow", "overflow-x: clip" in progress)
    shell = (ROOT / "dashboards" / "assets" / "wolf-shell.css").read_text(encoding="utf-8")
    check("phone role chip stays visible", "display: block !important" in shell and "white-space: normal" in shell)
    check("phone nav does not force a full-width crumb row", "flex: 1 1 100%" not in shell)
    lead = (ROOT / "dashboards" / "lead-spine.html").read_text(encoding="utf-8")
    check("lead spine says not wired", "NOT WIRED" in lead and "Demo data. Not live leads." in lead)
    work = (ROOT / "dashboards" / "my-work.html").read_text(encoding="utf-8")
    check("my work shows provenance", "staff_footnote" in work and "footnote" in work)
    room = (ROOT / "dashboards" / "finish-war-room.html").read_text(encoding="utf-8")
    check("war room queue title", "GIVE THIS TO A HUMAN NOW" in room)
    icon = ROOT / "dashboards" / "favicon.ico"
    check("favicon file exists", icon.is_file() and icon.stat().st_size > 20)
    check("lead list withholds demo rows", "hide_demo=True" in (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8"))
    chip = sb._ATRIUM_SETUP_CHIP.decode("utf-8")
    check("atrium chip script", "Property unset" in chip and "propertyConfigured" in chip)


def test_plans() -> None:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        stored = conn.execute("SELECT COUNT(*) FROM content_plans WHERE lower(brand_id)='habitat'").fetchone()[0]
        work_count = conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
        check("nine habitat plans stored", stored == 9, str(stored))
        # MYWORK-1 populates core_work_items (commissioning + legacy). Plans stay historical projections.
        check("core work items populated by MYWORK-1", work_count >= 1, str(work_count))
        haikal = build_home("PERS-HAIKAL", conn=conn)
        misa = build_home("PERS-MISA", conn=conn)
        yudi = build_home("PERS-YUDI", conn=conn)
        devi = build_home("PERS-DEVI", conn=conn)

        def _plans(items):
            return [row for row in items if row.get("origin") == "historical" or row.get("source_system") == "content_plans"]

        h_items = _plans(haikal["sections"][0]["items"])
        m_items = _plans(misa["sections"][0]["items"])
        y_items = _plans(yudi["sections"][0]["items"])
        # HUMFIX-1C: only plans whose window covers Asia/Makassar today.
        # On 29 Sep 2026 habitat fortnight 14–27 is stale — zero plan cards in TODAY.
        check(
            "creative director current-window plans only",
            haikal["experience"] == "creative_director"
            and all("2026-09-14" not in str(row.get("title") or "") for row in h_items),
            str([(r.get("title"), r.get("date_range")) for r in h_items]),
        )
        check(
            "same current-window plans for every creative director",
            [row.get("source_id") for row in h_items] == [row.get("source_id") for row in m_items],
        )
        check("test lane plans stay off the staff list", all(str(row.get("source_id")) not in {"1", "2", "3"} for row in h_items))
        check(
            "plans are historical and not verified",
            all(row.get("origin") == "historical" and row.get("verified_by_wolf") is False for row in h_items),
        )
        check("plans are not person-hardcoded", "PERS-HAIKAL" not in json.dumps(h_items) and "PERS-MISA" not in json.dumps(m_items))
        check(
            "creator sees habitat scope only",
            yudi["experience"] == "content_creator"
            and all(row.get("brand_id") == "habitat" for row in y_items)
            and all("2026-09-14" not in str(row.get("title") or "") for row in y_items),
            str([(r.get("brand_id"), r.get("title")) for r in y_items]),
        )
        check("atrium is outside a creator scope", _plan_in_scope("atrium", {"SCOPE-GGV-CONTENT"}) is False)
        check("habitat is inside a creator scope", _plan_in_scope("habitat", {"SCOPE-GGV-CONTENT"}) is True)
        devi_blob = json.dumps(devi["sections"])
        check("devi does not receive habitat plans", "content-plan-" not in devi_blob)
        demo_rows = conn.execute("SELECT provenance_json FROM core_leads").fetchall()
        check(
            "stored leads are demo rows",
            bool(demo_rows) and all(_row_is_demo({"provenance_json": row[0]}) for row in demo_rows),
            str(len(demo_rows)),
        )
    finally:
        conn.close()


def test_matrix() -> None:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    check("matrix not staff ready", matrix.get("staff_ready") is False)
    check("matrix not commissioned", matrix.get("human_commissioned") is False)
    surfaces = {row["surface"]: row for row in matrix["surfaces"]}
    check("testability surface exists", "Operational testability" in surfaces)
    for name in ("Atrium Finance full product", "Atrium Finance reduced desk"):
        history = " ".join(item.get("result") or "" for item in surfaces[name].get("human_results") or [])
        check(f"fail kept on {name}", "FAIL" in history, history[:180])
    queue = [row["surface"] for row in matrix["surfaces"] if row.get("ready_to_test_now") == "yes"]
    check("human queue is not empty", len(queue) >= 5, str(queue))


def test_http(port: int) -> None:
    status, raw, _ctype = call(port, "GET", "/favicon.ico")
    check("favicon 200 unsigned", status == 200 and raw[:4] == b"\x00\x00\x01\x00", f"status={status}")
    status, raw, _ctype = call(port, "GET", "/wolf", accept="text/html")
    check("unsigned wolf 403", status == 403, str(status))
    started = time.perf_counter()
    status, raw, _ctype = call(port, "GET", "/api/owner/command", OWNER)
    elapsed = time.perf_counter() - started
    body = json.loads(raw.decode() or "{}")
    answers = {row.get("id"): row.get("answer") for row in body.get("answers") or []}
    check("owner command under 3s", status == 200 and elapsed < 3, f"status={status} seconds={elapsed:.2f}")
    check(
        "owner command answers the six cards",
        all(answers.get(key) for key in ("okay", "changed", "wrong", "decision", "money", "blocked")),
        str(sorted(answers)),
    )
    status, raw, _ctype = call(port, "GET", "/api/owner/war-room/testability", OWNER)
    room = json.loads(raw.decode() or "{}")
    check(
        "owner testability queue",
        status == 200 and room.get("title") == "GIVE THIS TO A HUMAN NOW" and room.get("queue"),
        str(status),
    )
    status, _raw, _ctype = call(port, "GET", "/api/owner/war-room/testability", HAIKAL)
    check("haikal testability 403", status == 403, str(status))
    status, raw, _ctype = call(port, "GET", "/amg/finance/lite", OWNER, accept="text/html")
    text = raw.decode("utf-8", "replace")
    check("owner lite 200", status == 200 and "Atrium Finance" in text, str(status))
    status, _raw, _ctype = call(port, "GET", "/amg/finance/lite", HAIKAL, accept="text/html")
    check("haikal lite 403", status == 403, str(status))
    status, raw, _ctype = call(port, "GET", "/amg-ops-pack", OWNER, accept="text/html")
    text = raw.decode("utf-8", "replace")
    check("owner finance slot", status == 200 and 'href="/amg/finance"' in text and "Finance · EMPTY" not in text, str(status))
    status, raw, _ctype = call(port, "GET", "/lead-spine", OWNER, accept="text/html")
    page = raw.decode("utf-8", "replace")
    check(
        "lead spine view has no demo rows",
        status == 200 and "NOT WIRED" in page and "DEMO Open unassigned" not in page,
        str(status),
    )
    status, raw, _ctype = call(port, "GET", "/api/staff/home", HAIKAL)
    home = json.loads(raw.decode() or "{}")
    today = [
        row for row in (((home.get("sections") or [{}])[0]).get("items") or [])
        if row.get("origin") == "historical" or row.get("source_system") == "content_plans"
    ]
    # HUMFIX-1C: TODAY only surfaces plans whose window covers Asia/Makassar today.
    # Habitat fortnight 14–27 Sep is stale on 29 Sep — must not appear.
    stale = [row for row in today if "2026-09-14" in str(row.get("title") or "") or "14 Sep" in str(row.get("date_range") or "")]
    check(
        "haikal home has no stale habitat plan cards",
        status == 200 and len(stale) == 0,
        str([(r.get("title"), r.get("date_range")) for r in today]),
    )
    status, raw, ctype = call(port, "GET", "/amg/finance", ZAYEN, accept="text/html")
    page = raw.decode("utf-8", "replace")
    check(
        "zayen shell carries the setup chip",
        status == 200 and "opsfix1-live-chip" in page and "Property unset" in page and "html" in ctype,
        f"status={status} type={ctype}",
    )


def main() -> int:
    test_static()
    test_plans()
    test_matrix()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        test_http(port)
    finally:
        httpd.shutdown()
        httpd.server_close()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
