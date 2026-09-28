#!/usr/bin/env python3
"""ZAYENFIX-1. Root / follows the primary assignment. Page denials are HTML.

Beta catalog is read-only. Does not grant, mark staff_ready, or mark commissioned.
"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import rbac  # noqa: E402
from core.staff_access import (  # noqa: E402
    ATRIUM_FINANCE_HREF,
    FINANCE_EMAIL,
    ZAYEN_PERSON,
    officer_must_deny,
    primary_human_landing,
)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
AMG = {"entity_id": "ENT-AMG"}
HTML = {"Accept": "text/html", "X-Wolf-Subject": ""}
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


def live() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def test_root_cause() -> None:
    conn = live()
    try:
        check(
            "wall still denies Zayen on /",
            officer_must_deny(ZAYEN_PERSON, "/", conn) is True,
        )
        check(
            "wall allows Zayen on Atrium Finance",
            officer_must_deny(ZAYEN_PERSON, ATRIUM_FINANCE_HREF, conn) is False,
        )
        check(
            "primary landing is Atrium Finance",
            primary_human_landing(ZAYEN_PERSON, conn) == ATRIUM_FINANCE_HREF,
        )
        check(
            "Zayen still cannot pay",
            rbac.can(ZAYEN_PERSON, "payment.execute", AMG, conn=conn) is False
            and rbac.can(ZAYEN_PERSON, "payment.approve", AMG, conn=conn) is False
            and rbac.can(ZAYEN_PERSON, "vendor.bank.change", AMG, conn=conn) is False,
        )
        check(
            "Zayen board read stays on Atrium",
            rbac.can(ZAYEN_PERSON, "atrium.board.read", AMG, conn=conn) is True,
        )
        for person, href in (
            ("PERS-HAIKAL", "/content-2.0"),
            ("PERS-MISA", "/content-2.0"),
            ("PERS-YUDI", "/content-2.0"),
            ("PERS-DEVI", "/bzg/uma-blu"),
            ("PERS-AMANDA", "/content-2.0"),
            ("PERS-MATT", "/wolf"),
        ):
            check(f"{person} primary landing {href}", primary_human_landing(person, conn) == href)
    finally:
        conn.close()


PEOPLE = (
    {
        "name": "Zayen",
        "email": FINANCE_EMAIL,
        "landing": "/amg/finance",
        "marker": "Atrium Finance",
        "also": (),
        "forbidden_pages": ("/ggv/finance", "/bzg/uma-blu", "/wolf", "/staff-ops-routing"),
        "forbidden_api": "/api/core/roles",
    },
    {
        "name": "Haikal",
        "email": "haikalqilbari123@gmail.com",
        "landing": "/content-2.0",
        "marker": "Content Engine",
        "also": (),
        "forbidden_pages": ("/wolf", "/ggv/finance", "/amg/finance"),
        "forbidden_api": "/api/amg/finance",
    },
    {
        "name": "Misa",
        "email": "mlsary111@gmail.com",
        "landing": "/content-2.0",
        "marker": "Content Engine",
        "also": (),
        "forbidden_pages": ("/wolf", "/amg/finance", "/ggv/finance"),
        "forbidden_api": "/api/core/roles",
    },
    {
        "name": "Yudi",
        "email": "widiatmika.11@gmail.com",
        "landing": "/content-2.0",
        "marker": "Content Engine",
        "also": (),
        "forbidden_pages": ("/ggv/finance", "/wolf"),
        "forbidden_api": "/api/amg/finance",
    },
    {
        "name": "Devi",
        "email": "deviputu236@gmail.com",
        "landing": "/bzg/uma-blu",
        "marker": "Uma Blu",
        "also": (),
        "forbidden_pages": ("/content-2.0", "/ggv/finance", "/wolf", "/amg/finance"),
        "forbidden_api": "/api/amg/finance",
    },
    {
        "name": "Amanda",
        "email": "amanda@wolfcommand.net",
        "landing": "/content-2.0",
        "marker": "Content Engine",
        "also": (("/ggv/finance", "GGV Finance"),),
        "forbidden_pages": ("/amg/finance", "/wolf"),
        "forbidden_api": "/api/amg/finance",
    },
    {
        "name": "Owner",
        "email": "mrwolf@wolfcommand.net",
        "landing": "/wolf",
        "marker": "Owner Command",
        "also": (("/content-2.0", "Content Engine"),),
        "forbidden_pages": (),
        "forbidden_api": "",
    },
)


def http_call(port: int, path: str, email: str | None, accept: str) -> tuple[int, str, str, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        return resp.status, resp.getheader("Location") or "", resp.getheader("Content-Type") or "", body
    finally:
        conn.close()


def test_http() -> None:
    from core import ggv_finance_nota as fin
    from core import wolf_shell as shell

    tmp = Path(tempfile.mkdtemp(prefix="role-routing-", dir=str(ROOT / "state")))
    copy = tmp / "catalog.sqlite"
    shutil.copy(CATALOG, copy)
    fin.CATALOG_DB = copy
    shell._CATALOG_DB = copy
    import serve_beta as sb

    handler = None
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            handler = obj
            break
    check("beta handler found", handler is not None)
    if handler is None:
        shutil.rmtree(tmp, ignore_errors=True)
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, _loc, _ctype, body = http_call(port, "/", None, "text/html")
        check("unsigned / is 403", status == 403, f"status={status} body={body[:80]!r}")
        status, _loc, ctype, body = http_call(port, "/api/health", None, "*/*")
        check("health 200", status == 200 and b"beta-os" in body, f"status={status} type={ctype}")

        for person in PEOPLE:
            email = person["email"]
            landing = person["landing"]
            name = person["name"]
            status, loc, _ctype, body = http_call(port, "/", email, "text/html")
            check(
                f"{name} / redirects to {landing}",
                status == 302 and loc == landing and not body.startswith(b"{"),
                f"status={status} loc={loc} body={body[:60]!r}",
            )
            status, loc, _ctype, _body = http_call(port, "/index.html", email, "text/html")
            check(
                f"{name} index redirects to {landing}",
                status == 302 and loc == landing,
                f"status={status} loc={loc}",
            )
            status, loc, ctype, body = http_call(port, landing, email, "text/html")
            text = body.decode("utf-8", "replace")
            check(
                f"{name} own page renders",
                status == 200 and "text/html" in ctype and person["marker"] in text and "Access denied" not in text,
                f"status={status} type={ctype} head={text[:120]!r}",
            )
            status2, _loc2, _ctype2, body2 = http_call(port, landing, email, "text/html")
            check(
                f"{name} refresh stays on own page",
                status2 == 200 and person["marker"] in body2.decode("utf-8", "replace"),
                f"status={status2}",
            )
            status, loc, _ctype, _body = http_call(port, "/signout", email, "text/html")
            check(f"{name} signout is logout", status == 302 and "cdn-cgi/access/logout" in loc, f"status={status} loc={loc}")
            status, loc, _ctype, _body = http_call(port, "/", email, "text/html")
            check(
                f"{name} post-login / returns to {landing}",
                status == 302 and loc == landing,
                f"status={status} loc={loc}",
            )
            for extra, marker in person["also"]:
                status, _loc, ctype, body = http_call(port, extra, email, "text/html")
                text = body.decode("utf-8", "replace")
                check(
                    f"{name} deep link {extra}",
                    status == 200 and marker in text and "text/html" in ctype,
                    f"status={status} head={text[:80]!r}",
                )
            for path in person["forbidden_pages"]:
                status, _loc, ctype, body = http_call(port, path, email, "text/html")
                text = body.decode("utf-8", "replace")
                check(
                    f"{name} denied page {path} is HTML",
                    status == 403
                    and "text/html" in ctype
                    and text.lstrip().startswith("<!DOCTYPE html>")
                    and "Access denied" in text
                    and email in text
                    and 'href="' + landing + '"' in text
                    and "Back to your workspace" in text
                    and not text.lstrip().startswith("{"),
                    f"status={status} type={ctype} head={text[:160]!r}",
                )
            api = person["forbidden_api"]
            if api:
                status, _loc, ctype, body = http_call(port, api, email, "text/html")
                check(
                    f"{name} denied API {api} stays JSON",
                    status == 403 and "json" in ctype and body.lstrip().startswith(b"{"),
                    f"status={status} type={ctype} body={body[:120]!r}",
                )
                if name == "Zayen":
                    payload = json.loads(body.decode())
                    check(
                        "Zayen API deny names the limit",
                        payload.get("error") == "forbidden"
                        and "Atrium Finance" in str(payload.get("message") or ""),
                        str(payload)[:200],
                    )

        status, _loc, ctype, body = http_call(port, "/ggv/finance", FINANCE_EMAIL, "*/*")
        check(
            "script Accept keeps JSON 403",
            status == 403 and "json" in ctype and body.lstrip().startswith(b"{"),
            f"status={status} type={ctype}",
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    test_root_cause()
    test_http()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
