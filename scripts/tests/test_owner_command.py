#!/usr/bin/env python3
"""Owner Command Centre — /wolf pulse, exceptions, founder dependency."""
from __future__ import annotations

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

from core import owner_command as command  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PAGE = ROOT / "dashboards" / "owner-empire-pack.html"
CLASSES = {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"}
TRUTH = {"LIVE", "CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "NEEDS REVIEW"}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_model() -> None:
    try:
        command.build_command(verified_person_id="PERS-DEVI")
        check("devi command forbidden", False)
    except Exception as exc:
        check("devi command forbidden", getattr(exc, "code", "") == "forbidden", str(exc))
    try:
        command.refuse_external_write({"amount": 1})
        check("writes refused", False)
    except command.CommandError as exc:
        check("writes refused", exc.code == "writes_refused")
    desk = command.build_command(verified_person_id="PERS-MATT")
    check("desk ok", desk.get("ok") is True and desk.get("read") == "READ", str(desk.get("read")))
    check("not staff ready", desk.get("staff_ready") is False and desk.get("human_commissioned") is False)
    check("no money figure", desk.get("money") is None and desk.get("occupancy") is None and desk.get("green_kpi") is False)
    check("no path leak", "/Users/" not in json.dumps(desk))
    codes = [row.get("code") for row in desk.get("companies") or []]
    check("three companies", codes == ["GGV", "AMG", "BZG"], str(codes))
    questions = [row.get("question") for row in desk.get("answers") or []]
    check("seven answers", len(questions) == 7 and questions[0] == "Are my businesses okay?", str(questions))
    check(
        "dependency not measured",
        (desk.get("founder_dependency") or {}).get("less_dependent") == "NOT MEASURED"
        and (desk.get("founder_dependency") or {}).get("measured_reduction") is False,
    )
    classes = set((desk.get("founder_dependency") or {}).get("classes") or [])
    check("five classes", classes == CLASSES, str(classes))
    for card in desk.get("companies") or []:
        occ = card.get("occupancy") or {}
        fin = card.get("financial_position") or {}
        check(
            f"{card.get('code')} occupancy not a number",
            occ.get("value") is None and occ.get("state") in TRUTH | {"MISSING"},
            str(occ),
        )
        check(
            f"{card.get('code')} finance not a number",
            fin.get("value") is None and fin.get("state") in TRUTH | {"MISSING"},
            str(fin),
        )
        check(f"{card.get('code')} not a green kpi", card.get("green_kpi") is False)
    kinds = {item.get("kind") for item in (desk.get("needs_you") or {}).get("items") or []}
    check("needs you kinds", kinds <= {"approval", "exception", "financial", "commissioning"}, str(kinds))
    for item in (desk.get("exceptions") or {}).get("items") or []:
        check(
            "exception severity missing",
            item.get("severity") == "MISSING" and item.get("escalation_state") == "MISSING",
            str(item)[:180],
        )
        break
    else:
        check("exceptions read honest", (desk.get("exceptions") or {}).get("read") in {"READ", "UNAVAILABLE"})
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-owner-safe" in page and "Zayen" in page)
    check("page empty not zero", "EMPTY is not 0%" in page)
    check("page track d parked", "Track D is parked" in page)
    check("page no pay button", ">Pay<" not in page and ">Settle<" not in page)
    check("page truth stamp", 'data-surface="empire"' in page and "wolf-truth.js" in page)
    check("page no second nav", 'id="wolfnav"' not in page)
    check("page sections", "Needs you" in page and "Founder dependency" in page and "Are my businesses okay?" in page)
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
        st, anon = call("GET", "/api/owner/command", None)
        check(
            "anon command 403",
            st == 403 and isinstance(anon, dict) and anon.get("ui", {}).get("component") == "permission-denied",
            str(anon)[:240],
        )
        st, outsider = call("GET", "/api/owner/command", OUTSIDER)
        check("outsider command 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, body = call("GET", "/api/owner/command", subject)
            check(
                f"{label} command 403",
                st == 403 and isinstance(body, dict) and body.get("ui", {}).get("component") == "permission-denied",
                str(body)[:180],
            )
        st, owner = call("GET", "/api/owner/command", MATT)
        check("owner command 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner not commissioned", owner.get("human_commissioned") is False and owner.get("staff_ready") is False)
            check("owner money off", owner.get("money") is None and owner.get("payment_executed") is not True)
        st, missing = call("GET", "/api/owner/command/nope", MATT)
        check("unknown command view 404", st == 404, str(st))
        for method, path in (
            ("POST", "/api/owner/command"),
            ("POST", "/api/owner/command/payment"),
            ("PUT", "/api/owner/command"),
            ("PATCH", "/api/owner/command/bank"),
        ):
            code, body = call(method, path, MATT, {"amount": 1})
            check(f"{method} {path} refused", code == 405, str(body)[:180])
        st, anon_post = call("POST", "/api/owner/command/payment", None, {})
        check("anon POST command 403", st == 403, str(st))
        st, devi_post = call("POST", "/api/owner/command", DEVI, {})
        check("devi POST command 403", st == 403, str(st))
        for path in ("/wolf", "/owner-empire-pack", "/dashboards/owner-empire-pack.html"):
            st, page = call("GET", path, None)
            check(f"anon {path} 403", st == 403, str(st))
            st, devi_page = call("GET", path, DEVI)
            check(f"devi {path} 403", st == 403, str(devi_page)[:120] if not isinstance(devi_page, (bytes, bytearray)) else str(st))
        st, page_ok = call("GET", "/wolf", MATT)
        check(
            "owner wolf 200",
            st == 200
            and isinstance(page_ok, (bytes, bytearray))
            and b"beta-owner-safe" in page_ok
            and b"Are my businesses okay?" in page_ok
            and b">Pay<" not in page_ok,
            str(st),
        )
        st, alias = call("GET", "/owner-empire-pack", MATT)
        check("owner empire alias 200", st == 200 and isinstance(alias, (bytes, bytearray)) and b"Owner Command" in alias)

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
            ("owner-desktop", MATT, 1280, "/wolf", ("Are my businesses okay?", "Needs you", "GGV", "data-command-ready=\"1\"", "data-overflow=\"no\"")),
            ("owner-mobile", MATT, 390, "/wolf", ("AMG", "BZG", "NOT MEASURED", "data-overflow=\"no\"")),
            ("staff-denied", DEVI, 390, "/wolf", ("permission-denied",)),
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
        proxy.shutdown()
    finally:
        httpd.shutdown()


def main() -> int:
    test_model()
    test_http_and_headless()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
