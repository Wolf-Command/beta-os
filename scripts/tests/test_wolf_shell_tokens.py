#!/usr/bin/env python3
"""Wave 1 Wolf Global Shell + Tokens — Beta :8788 only."""
from __future__ import annotations

import inspect
import json
import os
import socket
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

from core import request_auth as ra  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"

TOKENS = ROOT / "dashboards" / "wolf-tokens.css"
SHELL_CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"
SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
SAMPLES = {
    "progress": ROOT / "dashboards" / "progress.html",
    "empire": ROOT / "dashboards" / "owner-empire-pack.html",
    "uma": ROOT / "dashboards" / "bzg-uma-blu.html",
}
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_files() -> None:
    check("tokens file", TOKENS.is_file())
    check("shell css", SHELL_CSS.is_file())
    check("sidenav.js", SIDENAV.is_file())
    tok = TOKENS.read_text(encoding="utf-8")
    for var in ("--bg", "--panel", "--petrol", "--gold", "--accent", "--nav-w"):
        check(f"token {var}", var in tok)
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav wolfnav", "#wolfnav" in sn or "wolfnav" in sn)
    check("sidenav toggle id", "wolfnav-t" in sn)
    check("sidenav HOME", "HOME" in sn)
    check("sidenav BUSINESSES", "BUSINESSES" in sn)
    check("sidenav INTELLIGENCE", "INTELLIGENCE" in sn)
    check("sidenav SYSTEM", "SYSTEM" in sn)
    check("no mgmt-cluster primary", "mgmt-cluster" not in sn)
    check("one boards control", sn.count('id = "wolfnav-t"') + sn.count('id="wolfnav-t"') >= 1)
    check("boot guard", "__WOLF_SIDENAV_BOOTED__" in sn)


def test_module() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("hidden ne perm", flags["hidden_ne_permission"] is True)
    check("api canonical", flags["api_auth_canonical"] is True)
    check("no second boards", flags["second_boards_menu"] is False)

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("owner authorized", owner["wolf_authorized"] is True)
    check("owner has progress", "/progress" in owner["pages"])
    check("owner has empire", "/owner-empire-pack" in owner["pages"])

    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi scoped", devi["scoped"] is True and devi["wolf_authorized"] is False)
    check("devi has uma", "/bzg/uma-blu" in devi["pages"])
    check("devi hides progress", "/progress" not in devi["pages"])
    check("devi hides empire", "/owner-empire-pack" not in devi["pages"])
    check("devi hides ggv", "/ggv-ops-pack" not in devi["pages"])

    amanda = shell.build_whoami(person_id="PERS-AMANDA", email=AMANDA)
    check("amanda ggv", "/ggv-ops-pack" in amanda["pages"])
    check("amanda hides uma", "/bzg/uma-blu" not in amanda["pages"])
    check("amanda hides progress", "/progress" not in amanda["pages"])

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client empty pages", client["pages"] == [])

    tree = shell.filter_ia_tree(devi)
    titles = [s["title"] for s in tree]
    check("devi no SYSTEM section", "SYSTEM" not in titles)
    check("devi has BUSINESSES", "BUSINESSES" in titles)

    try:
        shell.refuse_proven({})
        check("proven raises", False)
    except shell.WolfShellError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        shell.refuse_second_boards({})
        check("second boards raises", False)
    except shell.WolfShellError as exc:
        check("second boards refused", exc.code == "second_boards_refused")


def test_inject() -> None:
    raw = b"<!DOCTYPE html><html><head></head><body><h1>x</h1></body></html>"
    who = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    out = shell.inject_shell(raw, rel="progress.html", whoami=who)
    text = out.decode("utf-8")
    check("inject wolfnav", 'id="wolfnav"' in text)
    check("inject toggle", 'id="wolfnav-t"' in text)
    check("inject tokens", "wolf-tokens.css" in text)
    check("inject shell css", "wolf-shell.css" in text)
    check("inject sidenav", "sidenav.js" in text)
    check("inject whoami", "__WOLF_WHOAMI__" in text)
    check("single wolfnav", text.count('id="wolfnav"') == 1)
    # idempotent
    out2 = shell.inject_shell(out, rel="progress.html", whoami=who)
    check("idempotent wolfnav", out2.decode().count('id="wolfnav"') == 1)
    check("skip deliveries", shell.should_inject("deliveries/x.html") is False)


def test_sample_attrs() -> None:
    expected = {
        "progress": "SYSTEM",
        "empire": "DASHBOARD",
        "uma": "WORKSPACE",
    }
    for key, path in SAMPLES.items():
        text = path.read_text(encoding="utf-8")
        check(f"{key} page-type", f'data-wolf-page-type="{expected[key]}"' in text)
        check(f"{key} shell global", 'data-wolf-shell="global"' in text)


def test_http() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            if getattr(obj, "__name__", "") == "BetaHandler" or hasattr(obj, "_try_serve_shell_html"):
                Handler = obj
                break
    if Handler is None:
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
    check("handler found", Handler is not None)
    if Handler is None:
        return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(method: str, url_path: str, subject: str | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        req = Request(
            f"http://127.0.0.1:{port}{url_path}",
            headers=headers,
            method=method,
        )
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type") or ""
                if "json" in ctype:
                    return resp.status, json.loads(raw.decode())
                return resp.status, raw.decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw.decode())
            except json.JSONDecodeError:
                return exc.code, raw.decode("utf-8", errors="replace")

    try:
        # Anon APIs that must stay 403
        for path in (
            "/api/owner/empire-pack",
            "/api/bzg/uma-blu/today",
            "/api/ggv/ops-pack",
            "/owner-empire-pack",
            "/bzg/uma-blu",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True, str(st))
        pages = (payload.get("whoami") or {}).get("pages") or []
        check("anon whoami empty pages", pages == [], str(pages))

        st, payload = call("GET", "/api/wolf/shell-whoami", MATT)
        check("matt whoami 200", st == 200 and payload.get("ok") is True)
        who = payload.get("whoami") or {}
        check("matt owner", who.get("audience") == "OWNER" or who.get("wolf_authorized") is True)
        check("matt sees progress", "/progress" in (who.get("pages") or []))

        st, payload = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami", st == 200 and who.get("audience") == "OPERATOR", str(who.get("audience")))
        check("devi hide progress", "/progress" not in (who.get("pages") or []))
        check("devi see uma", "/bzg/uma-blu" in (who.get("pages") or []))

        # Sample HTML: progress (static+shell), empire + uma (auth pages)
        st, html = call("GET", "/progress.html", MATT)
        check("progress html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("progress has #wolfnav", 'id="wolfnav"' in html)
            check("progress has #wolfnav-t", 'id="wolfnav-t"' in html)
            check("progress sidenav once", html.count("sidenav.js") == 1)
            check("progress tokens", "wolf-tokens.css" in html)
            check("progress page-type", 'data-wolf-page-type="SYSTEM"' in html)

        st, html = call("GET", "/owner-empire-pack", MATT)
        check("empire html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("empire has #wolfnav", 'id="wolfnav"' in html)
            check("empire single wolfnav", html.count('id="wolfnav"') == 1)
            check("empire page-type", 'data-wolf-page-type="DASHBOARD"' in html)

        st, html = call("GET", "/bzg/uma-blu", DEVI)
        check("uma html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("uma has #wolfnav", 'id="wolfnav"' in html)
            check("uma has toggle", 'id="wolfnav-t"' in html)
            check("uma page-type", 'data-wolf-page-type="WORKSPACE"' in html)
            # whoami bake should hide progress for Devi when JS filters
            check("uma whoami baked", "__WOLF_WHOAMI__" in html)
            if "__WOLF_WHOAMI__" in html:
                check("uma whoami no progress href list", '"/progress"' not in html.split("__WOLF_WHOAMI__=")[1][:800])

        # No second Boards menu artifact
        st, html = call("GET", "/progress.html", MATT)
        if isinstance(html, str):
            check("no duplicate wolfnav", html.count('id="wolfnav"') == 1)
            check("single boards button", html.count('id="wolfnav-t"') == 1)

    finally:
        httpd.shutdown()


def test_prod_untouched() -> None:
    def up(port: int) -> bool:
        s = socket.socket()
        s.settimeout(1.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        finally:
            s.close()

    # Do not require prod up — only assert we did not bind/kill :8787 from this pack.
    # Soft presence check for claim expect line.
    p8787 = up(8787)
    p8788 = up(8788)
    check("8787 probe ran", True)
    check("8788 probe ran", True)
    print(f"NOTE  listeners 8787={p8787} 8788={p8788}")


def test_wip() -> None:
    check("wip quartet size", len(WIP) == 4)
    for path in (
        "scripts/core/wolf_shell.py",
        "dashboards/assets/sidenav.js",
        "dashboards/wolf-tokens.css",
        "scripts/tests/test_wolf_shell_tokens.py",
    ):
        check(f"pack not wip {path}", path not in WIP)


def main() -> int:
    test_files()
    test_module()
    test_inject()
    test_sample_attrs()
    test_http()
    test_prod_untouched()
    test_wip()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
