#!/usr/bin/env python3
"""Business dashboards — AMG, BZG, Uma Blu, GGV, and canonical propagation."""
from __future__ import annotations

import copy
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import business_dashboard as desk  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PAGE = ROOT / "dashboards" / "business-dashboard.html"
TRUTH = {"LIVE", "CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "NEEDS REVIEW"}
SECTIONS = (
    "today",
    "performance",
    "people",
    "money",
    "customers",
    "exceptions",
    "priorities",
    "activity",
)
LEVELS = (
    "WOLF/GROUP",
    "LEGAL ENTITY",
    "SITE",
    "BUSINESS UNIT/VENUE",
    "DEPARTMENT/FUNCTION",
    "WORKSPACE",
    "OBJECT",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _by_code(body: dict) -> dict:
    return {row.get("code"): row for row in body.get("businesses") or []}


def test_model_and_propagation() -> None:
    try:
        desk.build_dashboards(verified_person_id="PERS-DEVI")
        check("devi dashboard forbidden", False)
    except Exception as exc:
        check("devi dashboard forbidden", getattr(exc, "code", "") == "forbidden", str(exc))
    try:
        desk.refuse_external_write({"amount": 1})
        check("writes refused", False)
    except desk.DashboardError as exc:
        check("writes refused", exc.code == "writes_refused")
    try:
        desk.build_dashboards(verified_person_id="PERS-MATT", code="nope")
        check("unknown code", False)
    except desk.DashboardError as exc:
        check("unknown code", exc.code == "not_found")

    report = desk.build_dashboards(verified_person_id="PERS-MATT")
    check("desk ok", report.get("ok") is True and report.get("read") == "READ", str(report.get("read")))
    check("not staff ready", report.get("staff_ready") is False and report.get("human_commissioned") is False)
    check("no money figure", report.get("money") is None and report.get("green_kpi") is False)
    check("no path leak", "/Users/" not in json.dumps(report))
    codes = [row.get("code") for row in report.get("businesses") or []]
    check("four businesses", codes == ["amg", "bzg", "uma-blu", "ggv"], str(codes))
    boards = _by_code(report)
    for code, board in boards.items():
        projection = board.get("projection") or {}
        check(
            f"{code} current projection",
            projection.get("display_state") == "CURRENT" and projection.get("shown_as_current") is True,
            str(projection.get("display_state")),
        )
        check(f"{code} not commissioned", board.get("human_commissioned") is False and board.get("staff_ready") is False)
        keys = [row.get("key") for row in board.get("sections") or []]
        check(f"{code} eight sections", keys == list(SECTIONS), str(keys))
        levels = [row.get("level") for row in board.get("hierarchy") or []]
        check(f"{code} seven levels", levels == list(LEVELS), str(levels))
        money = next(row for row in board["sections"] if row["key"] == "money")
        check(
            f"{code} money not a number",
            money.get("value") is None and money.get("state") in TRUTH | {"MISSING"},
            str(money),
        )
        performance = next(row for row in board["sections"] if row["key"] == "performance")
        check(
            f"{code} performance has no invented target",
            performance.get("state") == "MISSING" and performance.get("items") == [],
            str(performance.get("state")),
        )
        customers = next(row for row in board["sections"] if row["key"] == "customers")
        check(f"{code} guests not a number", customers.get("value") is None, str(customers.get("value")))
        workspaces = next(row for row in board["hierarchy"] if row["level"] == "WORKSPACE")
        hrefs = [item.get("href") for item in workspaces.get("items") or []]
        check(f"{code} specialist link", any(hrefs), str(hrefs))
    amg = boards["amg"]
    legal = next(row for row in amg["hierarchy"] if row["level"] == "LEGAL ENTITY")
    check(
        "amg legal name",
        any("Atrium Management Group" in str(item.get("legal_name")) for item in legal.get("items") or []),
        str(legal)[:240],
    )
    venue = next(row for row in amg["hierarchy"] if row["level"] == "BUSINESS UNIT/VENUE")
    check(
        "amg atrium brand",
        any("Atrium" in str(item.get("name")) for item in venue.get("items") or []),
        str(venue)[:240],
    )
    uma = boards["uma-blu"]
    today = next(row for row in uma["sections"] if row["key"] == "today")
    check("uma today not a group total", today.get("state") == "MISSING" and today.get("value") is None, str(today))
    uma_spaces = next(row for row in uma["hierarchy"] if row["level"] == "WORKSPACE")
    check(
        "uma specialist underneath",
        any(item.get("href") == "/bzg/uma-blu" for item in uma_spaces.get("items") or []),
        str(uma_spaces)[:240],
    )
    ggv_spaces = next(row for row in boards["ggv"]["hierarchy"] if row["level"] == "WORKSPACE")
    check(
        "ggv specialist underneath",
        any(item.get("href") == "/ggv-ops-pack" for item in ggv_spaces.get("items") or []),
    )
    bzg_spaces = next(row for row in boards["bzg"]["hierarchy"] if row["level"] == "WORKSPACE")
    check(
        "bzg specialist underneath",
        any(item.get("href") == "/bzg" for item in bzg_spaces.get("items") or []),
    )
    amg_spaces = next(row for row in amg["hierarchy"] if row["level"] == "WORKSPACE")
    check(
        "amg specialist underneath",
        any(item.get("href") == "/amg-ops-pack" for item in amg_spaces.get("items") or []),
    )

    before = desk.read_snapshot()
    after = copy.deepcopy(before)
    changed = False
    for row in after["entities"]:
        if row.get("entity_id") == "ENT-AMG":
            row["legal_name"] = str(row.get("legal_name") or "") + " · propagation"
            changed = True
    check("canonical mutation in memory", changed)
    proof = desk.prove_propagation(before, after)
    check("propagation did not write", proof.get("ledger_write") is False)
    check(
        "digest changed",
        proof.get("before_digest") and proof.get("before_digest") != proof.get("after_digest"),
        str(proof.get("before_digest"))[:16],
    )
    for row in proof.get("updated") or []:
        check(
            f"{row.get('code')} updated",
            row.get("changed") is True
            and row.get("display_state") == "CURRENT"
            and row.get("shown_as_current") is True,
            str(row),
        )
    for row in proof.get("stale") or []:
        check(
            f"{row.get('code')} held copy stale",
            row.get("display_state") == "STALE"
            and row.get("shown_as_current") is False
            and row.get("sections_shown_as_current") is False
            and row.get("withheld") is True,
            str(row),
        )
    fresh = desk.project_all(after)
    amg_fresh = next(row for row in fresh if row["code"] == "amg")
    legal_fresh = next(row for row in amg_fresh["hierarchy"] if row["level"] == "LEGAL ENTITY")
    check(
        "amg shows the changed legal name",
        any("propagation" in str(item.get("legal_name")) for item in legal_fresh.get("items") or []),
        str(legal_fresh)[:240],
    )
    for row in fresh:
        if row["code"] == "amg":
            continue
        legal_row = next(level for level in row["hierarchy"] if level["level"] == "LEGAL ENTITY")
        blob = json.dumps(legal_row)
        check(f"{row['code']} does not wear the amg name", "propagation" not in blob, blob[:180])
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-owner-safe" in page)
    check("page no second nav", 'id="wolfnav"' not in page)
    check("page truth stamp", "wolf-truth.js" in page and "data-wolf-truth" in page)
    check("page no pay button", ">Pay<" not in page and ">Settle<" not in page)
    check("page stale copy", "not shown as current" in page)
    check("page mobile", "@media (max-width: 860px)" in page)


def test_http_and_headless() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            if obj.__name__ == "BetaHandler":
                Handler = obj
                break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=90) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        st, anon = call("GET", "/api/business", None)
        check(
            "anon business 403",
            st == 403 and isinstance(anon, dict) and anon.get("ui", {}).get("component") == "permission-denied",
            str(anon)[:240],
        )
        st, outsider = call("GET", "/api/business/amg", OUTSIDER)
        check("outsider business 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, body = call("GET", "/api/business/bzg", subject)
            check(
                f"{label} business 403",
                st == 403 and isinstance(body, dict) and body.get("ui", {}).get("component") == "permission-denied",
                str(body)[:180],
            )
        st, owner = call("GET", "/api/business", MATT)
        check("owner business 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:180])
        if isinstance(owner, dict):
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner four", [row.get("code") for row in owner.get("businesses") or []] == ["amg", "bzg", "uma-blu", "ggv"])
        st, one = call("GET", "/api/business/ggv", MATT)
        check("owner ggv 200", st == 200 and isinstance(one, dict) and (one.get("businesses") or [{}])[0].get("code") == "ggv")
        st, missing = call("GET", "/api/business/nope", MATT)
        check("unknown business 404", st == 404, str(st))
        for method, path in (
            ("POST", "/api/business"),
            ("POST", "/api/business/amg/payment"),
            ("PUT", "/api/business"),
            ("PATCH", "/api/business/ggv/bank"),
        ):
            code, body = call(method, path, MATT, {"amount": 1})
            check(f"{method} {path} refused", code == 405, str(body)[:180])
        st, anon_post = call("POST", "/api/business", None, {})
        check("anon POST business 403", st == 403, str(st))
        st, devi_post = call("POST", "/api/business/uma-blu", DEVI, {})
        check("devi POST business 403", st == 403, str(st))
        digest = ""
        if isinstance(owner, dict):
            digest = str(owner.get("canonical") or "")
        st, same = call("GET", f"/api/business?projected={digest}", MATT)
        same_boards = (same.get("businesses") if isinstance(same, dict) else None) or []
        check(
            "held matching digest stays current",
            st == 200 and same_boards and all(
                (row.get("projection") or {}).get("display_state") == "CURRENT" for row in same_boards
            ),
            str(st),
        )
        st, stale = call("GET", "/api/business?projected=not-the-canonical-state", MATT)
        stale_boards = (stale.get("businesses") if isinstance(stale, dict) else None) or []
        check("stale http four", st == 200 and len(stale_boards) == 4, str(st))
        for row in stale_boards:
            check(
                f"{row.get('code')} http stale",
                (row.get("projection") or {}).get("display_state") == "STALE"
                and row.get("sections_shown_as_current") is False
                and row.get("sections") == []
                and "not shown as current" in str(row.get("withheld_why") or ""),
                str(row)[:220],
            )
        for path in (
            "/business/amg",
            "/business/bzg",
            "/business/uma-blu",
            "/business/ggv",
            "/business",
            "/business-dashboard.html",
            "/dashboards/business-dashboard.html",
        ):
            st, page = call("GET", path, None)
            check(f"anon {path} 403", st == 403, str(st))
            st, devi_page = call("GET", path, DEVI)
            check(
                f"devi {path} 403",
                st == 403 and isinstance(devi_page, dict) and devi_page.get("ui", {}).get("component") == "permission-denied",
                str(devi_page)[:160] if isinstance(devi_page, dict) else str(st),
            )
        st, page_ok = call("GET", "/business/amg", MATT)
        check(
            "owner amg page 200",
            st == 200 and isinstance(page_ok, (bytes, bytearray)) and b"beta-owner-safe" in page_ok and b">Pay<" not in page_ok,
            str(st),
        )
        st, nope = call("GET", "/business/nope", MATT)
        check("owner unknown page 404", st == 404, str(st))
        st, wolf = call("GET", "/api/owner/command", MATT)
        if isinstance(wolf, dict):
            hrefs = {row.get("code"): row.get("href") for row in wolf.get("companies") or []}
            check("wolf drills to businesses", hrefs == {"GGV": "/business/ggv", "AMG": "/business/amg", "BZG": "/business/bzg"}, str(hrefs))
            uma = []
            for card in wolf.get("companies") or []:
                if card.get("code") != "BZG":
                    continue
                uma = [
                    item.get("href")
                    for item in ((card.get("operating_businesses") or {}).get("items") or [])
                    if "uma" in str(item.get("name") or "").lower() or "uma" in str(item.get("id") or "").lower()
                ]
            check("wolf drills to uma", uma == ["/business/uma-blu"], str(uma))
        else:
            check("wolf command readable", False, str(wolf)[:180])

        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        check("chrome present", chrome.is_file())
        if not chrome.is_file():
            return

        class _Proxy(BaseHTTPRequestHandler):
            subject = MATT

            def log_message(self, fmt: str, *args) -> None:
                return

            def do_GET(self):  # noqa: N802
                req = Request(
                    f"http://127.0.0.1:{port}{self.path}",
                    headers={"X-Wolf-Subject": _Proxy.subject, "Accept": "*/*"},
                    method="GET",
                )
                try:
                    with urlopen(req, timeout=90) as resp:
                        body = resp.read()
                        ctype = resp.headers.get("Content-Type") or "text/html"
                        code = resp.status
                except HTTPError as exc:
                    body = exc.read()
                    ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                    code = exc.code
                self.send_response(code)
                self.send_header("Content-Type", ctype or "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
        pport = proxy.server_address[1]
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        import subprocess

        shots = (
            ("owner-desktop", MATT, 1280, "/business/amg", ("AMG / Atrium", "Today", "Performance", "Atrium Management Group", "data-business-ready=\"1\"", "data-overflow=\"no\"", "data-section=\"money\"")),
            ("owner-mobile", MATT, 390, "/business/uma-blu", ("Uma Blu", "Customers / guests", "data-overflow=\"no\"", "data-section=\"today\"")),
            ("owner-stale", MATT, 1280, "/business/ggv?projected=not-the-canonical-state", ("STALE", "not shown as current", "data-sections=\"withheld\"", "data-overflow=\"no\"")),
            ("staff-denied", DEVI, 390, "/business/bzg", ("permission-denied",)),
            ("wolf-drill", MATT, 1280, "/wolf", ("/business/amg", "/business/uma-blu", "data-command-ready=\"1\"")),
        )
        for label, subject, width, path, needles in shots:
            _Proxy.subject = subject
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=15000",
                    f"--window-size={width},900",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}{path}",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )
            dom = proc.stdout or ""
            for needle in needles:
                check(f"{label} shows {needle}", needle in dom, (proc.stderr or dom)[-240:])
            if label == "owner-stale":
                check("stale hides money section", 'data-section="money"' not in dom, dom[-240:])
        proxy.shutdown()
    finally:
        httpd.shutdown()


def main() -> int:
    test_model_and_propagation()
    test_http_and_headless()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
