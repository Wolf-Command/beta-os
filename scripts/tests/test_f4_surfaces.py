#!/usr/bin/env python3
"""F4 staff-eye — four surfaces, phone and desktop, isolated catalog.

Development assertion on an ephemeral handler. Not a Cloudflare session.
Does not open Atrium books. Does not write the live catalog.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
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

PASS = 0
FAIL = 0

HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    import serve_beta as sb
    from core.canonical_guard import isolate_runtime_catalog

    catalog = isolate_runtime_catalog()
    handler = None
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            handler = obj
            break
    check("handler found", handler is not None)
    if handler is None:
        return 1

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    class Proxy(BaseHTTPRequestHandler):
        subject = ""

        def log_message(self, *_args):  # noqa: ANN002
            return

        def do_GET(self):  # noqa: N802
            headers = {"Accept": "*/*"}
            if Proxy.subject:
                headers["X-Wolf-Subject"] = Proxy.subject
            req = Request(f"http://127.0.0.1:{port}{self.path}", headers=headers, method="GET")
            try:
                with urlopen(req, timeout=40) as resp:
                    body = resp.read()
                    code = resp.status
                    ctype = resp.headers.get("Content-Type") or "text/html"
            except HTTPError as exc:
                body = exc.read()
                code = exc.code
                ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
            self.send_response(code)
            self.send_header("Content-Type", ctype or "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    pport = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()

    def call(path: str, subject: str | None) -> tuple[int, str]:
        headers = {"Accept": "*/*"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method="GET")
        try:
            with urlopen(req, timeout=40) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")

    def laid_out(label: str, subject: str, path: str, width: int, needles: tuple[str, ...], banned: tuple[str, ...]) -> str:
        Proxy.subject = subject
        proc = subprocess.run(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--virtual-time-budget=12000",
                f"--window-size={width},844",
                "--dump-dom",
                f"http://127.0.0.1:{pport}{path}",
            ],
            capture_output=True,
            text=True,
            timeout=50,
        )
        dom = proc.stdout or ""
        visible = re.sub(r"<script\b[^>]*>.*?</script>", " ", dom, flags=re.S | re.I)
        for needle in needles:
            check(f"{label} shows {needle}", needle in visible)
        for ban in banned:
            check(f"{label} hides {ban}", ban not in visible)
        check(
            f"{label} no sideways scroll",
            'data-overflow="no"' in dom and 'data-ready="1"' in dom,
            "ready" if 'data-ready="1"' in dom else "not-ready",
        )
        return dom

    try:
        check("chrome present", CHROME.is_file())
        for path in ("/content-2.0", "/bzg/uma-blu", "/bzg/uma-blu/bills", "/bzg/uma-blu/issues", "/ggv/finance", "/amg-ops-pack"):
            status, body = call(path, None)
            check(f"unsigned {path} denied", status == 403 and "<!DOCTYPE" not in body, str(status))

        status, body = call("/content-2.0", HAIKAL)
        check("creative director content 200", status == 200 and "CONTENT PLAN" in body, str(status))
        status, body = call("/bzg/uma-blu", HAIKAL)
        check("creative director uma denied", status == 403 and "<!DOCTYPE" not in body, str(status))
        status, body = call("/ggv/finance", HAIKAL)
        check("creative director finance denied", status == 403 and "<!DOCTYPE" not in body, str(status))

        status, body = call("/bzg/uma-blu", DEVI)
        check("operations lead today 200", status == 200 and "Uma Blu" in body, str(status))
        status, _body = call("/content-2.0", DEVI)
        check("operations lead content denied", status == 403, str(status))
        status, _body = call("/ggv/finance", DEVI)
        check("operations lead finance denied", status == 403, str(status))

        uma_nav = (
            "/bzg/uma-blu",
            "/uma-blu-close",
            "/bzg/uma-blu/issues",
            "/bzg/uma-blu/bills",
            "/bzg/uma-blu/evidence",
            "/bzg/uma-blu/exceptions",
            "/my-work",
            "/bzg/uma-blu/petty",
        )
        for path in uma_nav:
            status, text = call(path, DEVI)
            check(f"operations lead nav {path}", status == 200 and "<!DOCTYPE" in text, str(status))

        status, bills = call("/bzg/uma-blu/bills", DEVI)
        check("bills purchasing anchor", status == 200 and 'id="purchasing"' in bills, str(status))
        check("bills omits practice rows", "Practice example" not in bills and "fixtureBanner" not in bills)

        status, fin = call("/ggv/finance", AMANDA)
        check("content management finance 200", status == 200 and "Notas / Bills" in fin, str(status))
        status, overview = call("/api/ggv/finance/overview", AMANDA)
        check("finance overview 200", status == 200 and "needs_review" in overview, str(status))
        status, vendors = call("/api/ggv/finance/vendors", AMANDA)
        check("vendor list 200", status == 200 and "vendors" in vendors, str(status))
        status, _body = call("/api/ggv/finance/pay", AMANDA)
        check("pay route is not a get", status in {403, 405}, str(status))

        status, _body = call("/ggv/finance", MATT)
        check("owner finance 200", status == 200, str(status))

        status, amg = call("/amg-ops-pack", MATT)
        check("owner hotel desk 200", status == 200 and "Finance · EMPTY" in amg, str(status))
        check(
            "finance slot is not a link",
            'id="financeClosed"' in amg and "Hotel books are not open on this desk." in amg,
        )
        finance_tag = re.search(r'<span class="empty" id="financeClosed"[^>]*>', amg)
        check("finance span has no href", finance_tag is not None and "href" not in (finance_tag.group(0) if finance_tag else "href"))

        if not CHROME.is_file():
            return 1

        laid_out(
            "content phone",
            HAIKAL,
            "/content-2.0",
            390,
            ("CONTENT PLAN", "LIBRARY", "UPLOAD"),
            ("DEV fixture", "empty framework"),
        )
        laid_out(
            "content desktop",
            HAIKAL,
            "/content-2.0",
            1280,
            ("CONTENT PLAN", "Sign out"),
            ("DEV fixture",),
        )
        laid_out(
            "uma phone",
            DEVI,
            "/bzg/uma-blu",
            390,
            ("No stock count is on this screen.", "Daily Close", "Petty cash"),
            ("empty framework", "Open Needs-You", "Practice example"),
        )
        laid_out(
            "uma desktop",
            DEVI,
            "/bzg/uma-blu",
            1280,
            ("What do I need to do now?", "You run the day's operations."),
            ("empty framework", "Open Needs-You"),
        )
        laid_out(
            "bills phone",
            DEVI,
            "/bzg/uma-blu/bills",
            430,
            ("No purchase requests yet.", "Purchasing"),
            ("Practice example", "These rows are examples"),
        )
        laid_out(
            "finance phone",
            AMANDA,
            "/ggv/finance",
            390,
            ("Not paid from this screen", "Nothing added yet.", "Entering a nota is not the same as paying it."),
            ("Payment not verified",),
        )
        laid_out(
            "finance desktop",
            AMANDA,
            "/ggv/finance",
            1280,
            ("Vendors", "Notas / Bills", "Not paid from this screen"),
            ("Payment not verified",),
        )
        laid_out(
            "finance owner desktop",
            MATT,
            "/ggv/finance",
            1280,
            ("GGV", "Not paid from this screen"),
            ("Payment not verified",),
        )
        amg_dom = laid_out(
            "atrium slot phone",
            MATT,
            "/amg-ops-pack",
            390,
            ("Hotel books are not open on this desk.", "Finance · EMPTY"),
            (),
        )
        laid_out(
            "atrium slot desktop",
            MATT,
            "/amg-ops-pack",
            1280,
            ("Hotel books are not open on this desk.",),
            (),
        )
        check("atrium dump has no books href", "href" not in (re.search(r'id="financeClosed"[^>]*>', amg_dom).group(0) if re.search(r'id="financeClosed"', amg_dom) else "href"))
    finally:
        httpd.shutdown()
        proxy.shutdown()
        shutil.rmtree(catalog.parent, ignore_errors=True)

    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
