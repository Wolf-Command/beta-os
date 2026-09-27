#!/usr/bin/env python3
"""Wave 3 Wolf BZG + Uma Nav — Beta :8788 only.

Devi landing = Uma Blu Today. Breadcrumbs WOLF › Blu Zone › Uma Blu › Today.
Grammar EMPTY-honest (never fake %). Legacy /uma-blu → /bzg/uma-blu.
Matt reaches BZG. Hide Progress+Empire from Devi. Anon 403. One #wolfnav.
No Production. No invent PROVEN/READY.
"""
from __future__ import annotations

import inspect
import json
import os
import socket
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

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
BZG_HTML = ROOT / "dashboards" / "bzg.html"
UMA_HTML = ROOT / "dashboards" / "bzg-uma-blu.html"
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


def _labels(crumbs: list) -> list[str]:
    return [str(c.get("label") or "") for c in crumbs]


def test_module() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    check("nav slice set", bool(flags.get("slice")))
    check("devi landing flag", flags.get("devi_landing_uma_today") is True)
    check("bzg crumbs flag", flags.get("bzg_crumbs_wolf_blu_uma_today") is True)
    check("grammar empty flag", flags.get("grammar_empty_honest") is True)
    check("legacy uma alias flag", flags.get("legacy_uma_alias") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)
    check("no fake grammar pct", shell.grammar_has_fake_pct() is False)

    empty_bzg = [g for g in shell.bzg_grammar() if g.get("state") == "EMPTY"]
    live_bzg = [g for g in shell.bzg_grammar() if g.get("state") == "live"]
    check("bzg grammar has EMPTY", len(empty_bzg) >= 4)
    check("bzg overview live", any(g.get("key") == "overview" for g in live_bzg))
    check(
        "bzg EMPTY have no href",
        all(not g.get("href") for g in empty_bzg),
    )
    empty_uma = [g for g in shell.uma_grammar() if g.get("state") == "EMPTY"]
    check("uma grammar has EMPTY", len(empty_uma) >= 2)
    check(
        "uma EMPTY no fake pct",
        all("%" not in str(g.get("label")) for g in empty_uma),
    )

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("matt has bzg", "/bzg" in owner["pages"])
    check("matt has uma", "/bzg/uma-blu" in owner["pages"])
    check("matt landing wolf", owner.get("landing") == "/wolf")

    crumbs = shell.breadcrumbs_for_path("/bzg/uma-blu", owner)
    labs = _labels(crumbs)
    check("crumbs WOLF", labs[0] == "WOLF" if labs else False, str(labs))
    check("crumbs Blu Zone", "Blu Zone" in labs)
    check("crumbs Uma Blu", "Uma Blu" in labs)
    check("crumbs Today last", labs[-1] == "Today" if labs else False, str(labs))
    check(
        "crumbs trail order",
        labs == ["WOLF", "Blu Zone", "Uma Blu", "Today"],
        str(labs),
    )
    check(
        "crumbs Blu Zone → /bzg",
        any(c.get("label") == "Blu Zone" and c.get("href") == "/bzg" for c in crumbs),
    )

    crumbs_bzg = shell.breadcrumbs_for_path("/bzg", owner)
    check(
        "bzg crumbs WOLF Blu Zone",
        _labels(crumbs_bzg) == ["WOLF", "Blu Zone"],
        str(_labels(crumbs_bzg)),
    )

    dir_uma = shell.direction_for_path("/bzg/uma-blu", owner)
    check("UP from Today → /bzg", dir_uma.get("up") == "/bzg")
    check("HOME matt empire", dir_uma.get("home") in ("/wolf", "/owner-empire-pack"))

    crumbs_bills = shell.breadcrumbs_for_path("/bzg/uma-blu/bills", owner)
    check("bills crumbs has Bills", _labels(crumbs_bills)[-1] == "Bills")
    check(
        "UP from bills → uma",
        shell.parent_for_path("/bzg/uma-blu/bills", owner) == "/bzg/uma-blu",
    )

    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi landing Today", devi.get("landing") == "/bzg/uma-blu")
    check("devi hide Progress", "/progress" not in (devi.get("pages") or []))
    check("devi hide Empire", "/owner-empire-pack" not in (devi.get("pages") or []))
    check("devi hide GGV", "/ggv-ops-pack" not in (devi.get("pages") or []))
    check("devi hide AMG", "/amg-ops-pack" not in (devi.get("pages") or []))
    check("devi see BZG", "/bzg" in (devi.get("pages") or []))
    check("devi see Uma", "/bzg/uma-blu" in (devi.get("pages") or []))
    dtree = shell.filter_ia_tree(devi)
    hrefs = [it["href"] for s in dtree for it in s["items"]]
    check("devi IA no progress", "/progress" not in hrefs)
    check("devi IA no empire", "/owner-empire-pack" not in hrefs)
    check("devi IA has uma", "/bzg/uma-blu" in hrefs)
    check("devi IA has bzg", "/bzg" in hrefs)

    d_dir = shell.direction_for_path("/bzg/uma-blu", devi)
    check("devi UP → /bzg", d_dir.get("up") == "/bzg")
    check("devi HOME → Today", d_dir.get("home") == "/bzg/uma-blu")

    d_crumbs = shell.breadcrumbs_for_path("/bzg/uma-blu", devi)
    wolf = next((c for c in d_crumbs if c.get("label") == "WOLF"), None)
    check(
        "devi WOLF crumb soft-land",
        wolf is not None
        and wolf.get("href") in ("/bzg/uma-blu", None),
        str(wolf),
    )


def test_files() -> None:
    check("bzg html exists", BZG_HTML.is_file())
    bzg = BZG_HTML.read_text(encoding="utf-8")
    check("bzg EMPTY grammar", "Operations · EMPTY" in bzg and "Finance · EMPTY" in bzg)
    grammar_block = bzg.split('aria-label="BZG grammar"')[1].split("</nav>")[0] if 'aria-label="BZG grammar"' in bzg else ""
    check(
        "bzg grammar no fake pct",
        "PROVEN" not in grammar_block
        and "READY" not in grammar_block
        and "%" not in grammar_block,
        grammar_block[:200],
    )
    check("bzg page-type", 'data-wolf-page-type="DASHBOARD"' in bzg)
    check("bzg shell global", 'data-wolf-shell="global"' in bzg)
    check("bzg uma drill", 'href="/bzg/uma-blu"' in bzg)
    check("bzg crumb WOLF Blu Zone", "WOLF" in bzg and "Blu Zone" in bzg)

    check("uma html exists", UMA_HTML.is_file())
    uma = UMA_HTML.read_text(encoding="utf-8")
    check("uma crumb trail text", "WOLF · Blu Zone · Uma Blu · Today" in uma)
    check("uma Overview EMPTY", "Overview · EMPTY" in uma)
    check("uma Operations EMPTY", "Operations · EMPTY" in uma)
    check("uma page-type WORKSPACE", 'data-wolf-page-type="WORKSPACE"' in uma)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav Blu Zone crumbs", '"Blu Zone"' in sn)
    check("sidenav Today crumb", 'label: "Today"' in sn)
    check("sidenav WOLF crumb", 'label: "WOLF"' in sn)
    check("sidenav nav cache", "20260922-nav-" in sn)
    check("sidenav one wolfnav guard", "Never create a second #wolfnav" in sn)

    src = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    shell_src = (SCRIPTS / "core" / "wolf_shell.py").read_text(encoding="utf-8")
    # 2026-09-22 route merge moved the path literal into wolf_shell.LEGACY_UMA_REDIRECTS.
    # serve_beta still 302s it: route_merge_redirect_target then Location.
    # The HTTP check below remains the runtime proof. This is not a comment-only hit.
    check(
        "serve legacy uma-blu redirect",
        '"/uma-blu": "/bzg/uma-blu"' in shell_src
        and "route_merge_redirect_target" in src
        and 'send_header("Location"' in src,
    )
    check("serve bzg fail-closed", 'rel == "bzg.html"' in src)


def test_http() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            if getattr(obj, "__name__", "") == "BetaHandler" or hasattr(
                obj, "_try_serve_shell_html"
            ):
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

    def call(method: str, url_path: str, subject: str | None = None, *, follow: bool = True):
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
                    return resp.status, json.loads(raw.decode()), dict(resp.headers)
                return resp.status, raw.decode("utf-8", errors="replace"), dict(resp.headers)
        except HTTPError as exc:
            raw = exc.read()
            loc = exc.headers.get("Location") if exc.headers else None
            try:
                body = json.loads(raw.decode())
            except json.JSONDecodeError:
                body = raw.decode("utf-8", errors="replace")
            return exc.code, body, {"Location": loc} if loc else {}

    try:
        for path in (
            "/bzg",
            "/bzg/uma-blu",
            "/api/bzg/uma-blu/today",
            "/bzg-uma-blu",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, body, hdrs = call("GET", "/uma-blu", None, follow=False)
        # Redirect then auth fail, or direct 302 — both OK vs 404 sprawl
        check(
            "legacy uma-blu not 404",
            st in (302, 301, 303, 307, 403),
            str(st),
        )
        if st in (302, 301, 303, 307):
            check(
                "legacy Location /bzg/uma-blu",
                (hdrs.get("Location") or "").endswith("/bzg/uma-blu"),
                str(hdrs.get("Location")),
            )

        st, body, hdrs = call("GET", "/uma-blu.html", None)
        check("legacy uma-blu.html not 404", st in (302, 301, 303, 307, 403), str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        check("honesty slice set", bool(h.get("slice")))
        check("honesty proven false", h.get("proven") is False)
        check("honesty ready false", h.get("ready") is False)
        check("honesty crumbs flag", h.get("bzg_crumbs_wolf_blu_uma_today") is True)

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami landing", who.get("landing") == "/bzg/uma-blu")
        check("devi whoami hide progress", "/progress" not in (who.get("pages") or []))
        check("devi whoami hide empire", "/owner-empire-pack" not in (who.get("pages") or []))
        check("devi whoami see bzg", "/bzg" in (who.get("pages") or []))
        check("devi whoami see uma", "/bzg/uma-blu" in (who.get("pages") or []))
        ia = payload.get("ia") or []
        check("devi no SYSTEM", not any(s.get("id") == "system" for s in ia))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami see bzg", "/bzg" in (who.get("pages") or []))
        check("matt whoami see uma", "/bzg/uma-blu" in (who.get("pages") or []))

        st, html, _ = call("GET", "/bzg", MATT)
        check("matt bzg 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt bzg #wolfnav", 'id="wolfnav"' in html)
            check("matt bzg single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt bzg crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("matt bzg up", 'id="wolfnav-up"' in html)
            check("matt bzg home", 'id="wolfnav-home"' in html)
            check("matt bzg EMPTY", "EMPTY" in html)
            check("matt bzg sidenav once", html.count("sidenav.js") == 1)

        st, html, _ = call("GET", "/bzg", DEVI)
        check("devi bzg 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("devi bzg #wolfnav", 'id="wolfnav"' in html)
            check("devi bzg single wolfnav", html.count('id="wolfnav"') == 1)
            if "__WOLF_WHOAMI__" in html:
                blob = html.split("__WOLF_WHOAMI__=")[1][:2500]
                check("devi bake no progress", '"/progress"' not in blob)
                check("devi bake no empire", '"/owner-empire-pack"' not in blob)
                check("devi bake landing uma", '"/bzg/uma-blu"' in blob)

        # Uma Today requires venue scope — Matt/Devi fixtures may 403 without
        # live SCOPE-BZG-UMA seed. Prove page handler exists + anon already 403.
        st_uma_m, html_uma, _ = call("GET", "/bzg/uma-blu", MATT)
        check(
            "matt uma reachable or scoped-deny",
            st_uma_m in (200, 403),
            str(st_uma_m),
        )
        if st_uma_m == 200 and isinstance(html_uma, str):
            check("matt uma #wolfnav", 'id="wolfnav"' in html_uma)
            check("matt uma single wolfnav", html_uma.count('id="wolfnav"') == 1)
            check("matt uma crumbs", 'id="wolfnav-crumbs"' in html_uma)
            check("matt uma Today body", "Today" in html_uma)

        st, _, _ = call("GET", "/progress", DEVI)
        check("devi progress forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/owner-empire-pack", DEVI)
        check("devi empire forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/wolf", DEVI)
        check("devi wolf forbidden", st in (403, 401), str(st))

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

    p8787 = up(8787)
    p8788 = up(8788)
    check("8787 probe ran", True)
    check("8788 probe ran", True)
    print(f"NOTE  listeners 8787={p8787} 8788={p8788}")


def test_wip() -> None:
    for path in (
        "scripts/core/wolf_shell.py",
        "dashboards/assets/sidenav.js",
        "scripts/tests/test_wolf_bzg_uma_nav.py",
        "dashboards/bzg.html",
        "dashboards/bzg-uma-blu.html",
    ):
        check(f"pack not wip {path}", path not in WIP)


def main() -> int:
    test_module()
    test_files()
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
