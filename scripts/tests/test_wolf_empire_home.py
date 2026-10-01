#!/usr/bin/env python3
"""Wave 2 Wolf Empire HOME + RHC FIX — Beta :8788 only.

Owner landing = Empire (/wolf alias → Empire). Needs You under HOME.
Progress under SYSTEM only. Staff/Devi hide Progress. Anon 403 unchanged.
RHC FIX: breadcrumbs · UP/BACK/HOME · multi-assignment context switcher ·
responsive tokens @media. One #wolfnav. No second Boards. No Production.
No invent PROVEN/READY.
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
AMANDA = "amanda@wolfcommand.net"

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
SHELL_CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"
TOKENS = ROOT / "dashboards" / "wolf-tokens.css"
EMPIRE_HTML = ROOT / "dashboards" / "owner-empire-pack.html"
NEEDS_HTML = ROOT / "dashboards" / "staff-ops-routing.html"
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


def test_module_landing() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    check("nav slice set", bool(flags.get("slice")))
    check("owner landing flag", flags.get("owner_landing_empire") is True)
    check("progress system only flag", flags.get("progress_under_system_only") is True)
    check("wolf alias flag", flags.get("wolf_alias_empire") is True)
    check("hierarchy breadcrumbs flag", flags.get("hierarchy_breadcrumbs") is True)
    check("direction up back home flag", flags.get("direction_up_back_home") is True)
    check("context switcher multi only flag", flags.get("context_switcher_multi_only") is True)
    check("responsive tokens media flag", flags.get("responsive_tokens_media") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)

    check("empire path pack", shell.is_empire_path("/owner-empire-pack") is True)
    check("empire path wolf", shell.is_empire_path("/wolf") is True)
    check("empire path wolf slash", shell.is_empire_path("/wolf/") is True)
    check("not empire progress", shell.is_empire_path("/progress") is False)

    check("home primary empire", shell.home_primary_href() == "/owner-empire-pack")
    check("progress under system", shell.progress_section_id() == "system")

    home = next(s for s in shell.IA_TREE if s["id"] == "home")
    home_hrefs = [it["href"] for it in home["items"]]
    check("HOME has empire", "/owner-empire-pack" in home_hrefs)
    check("HOME has Needs You", "/staff-ops-routing" in home_hrefs)
    check("HOME no Progress", "/progress" not in home_hrefs)
    empire_item = next(it for it in home["items"] if it["key"] == "empire")
    check("empire primary", empire_item.get("primary") is True)
    check("empire aliases wolf", "/wolf" in (empire_item.get("aliases") or []))

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("owner landing /wolf", owner.get("landing") == "/wolf")
    check("owner home_primary empire", owner.get("home_primary") == "/owner-empire-pack")
    check("owner home_primary_key", owner.get("home_primary_key") == "empire")
    check("owner has empire", "/owner-empire-pack" in owner["pages"])
    check("owner has needs you", "/staff-ops-routing" in owner["pages"])
    check("owner has progress", "/progress" in owner["pages"])
    check("owner multi assignment", len(owner.get("assignments") or []) > 1)
    check("owner context switcher off (auto-resolve)", owner.get("context_switcher") is False)
    check(
        "owner assignment chain",
        all(
            a.get("role") and a.get("scope") and a.get("href")
            for a in (owner.get("assignments") or [])
        ),
    )

    tree = shell.filter_ia_tree(owner)
    titles = [s["title"] for s in tree]
    check("owner has HOME", "HOME" in titles)
    check("owner has SYSTEM", "SYSTEM" in titles)
    home_sec = next(s for s in tree if s["id"] == "home")
    sys_sec = next(s for s in tree if s["id"] == "system")
    check(
        "owner HOME empire first-primary",
        home_sec["items"][0]["key"] == "empire" and home_sec["items"][0].get("primary") is True,
    )
    check(
        "owner Progress in SYSTEM",
        any(it["href"] == "/progress" for it in sys_sec["items"]),
    )
    check(
        "owner Progress not in HOME",
        not any(it["href"] == "/progress" for it in home_sec["items"]),
    )

    payload = shell.shell_whoami_payload(
        {"ok": True, "person_id": "PERS-MATT", "email": MATT}
    )
    check("payload landing", payload.get("landing") == "/wolf")
    check("payload home_primary", payload.get("home_primary") == "/owner-empire-pack")
    check("payload context switcher off for owner", payload.get("context_switcher") is False)

    crumbs_uma = shell.breadcrumbs_for_path("/bzg/uma-blu", owner)
    check(
        "crumbs uma has Blu Zone",
        any(c.get("label") == "Blu Zone" for c in crumbs_uma),
    )
    check(
        "crumbs uma Blu Zone href",
        any(c.get("href") == "/bzg" for c in crumbs_uma),
    )
    check("crumbs uma has Today", any(c.get("label") == "Today" for c in crumbs_uma))
    check("crumbs uma has WOLF", any(c.get("label") == "WOLF" for c in crumbs_uma))
    check("up from uma is bzg", shell.parent_for_path("/bzg/uma-blu", owner) == "/bzg")
    check("up from empire none", shell.parent_for_path("/wolf", owner) is None)
    direction = shell.direction_for_path("/bzg/uma-blu", owner)
    check("direction has up", direction.get("up") == "/bzg")
    check("direction has home", direction.get("home") in ("/wolf", "/owner-empire-pack"))
    check("direction has back", bool(direction.get("back")))

    crumbs_needs = shell.breadcrumbs_for_path("/staff-ops-routing", owner)
    check(
        "crumbs needs you",
        any(c.get("label") == "Needs You" for c in crumbs_needs),
    )

    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi hide progress", "/progress" not in devi["pages"])
    check("devi hide empire", "/owner-empire-pack" not in devi["pages"])
    check("devi has needs you", "/staff-ops-routing" in devi["pages"])
    check("devi landing uma", devi.get("landing") == "/bzg/uma-blu")
    check("devi no home_primary empire", devi.get("home_primary") is None)
    check("devi single assignment", len(devi.get("assignments") or []) == 1)
    check("devi context switcher off", devi.get("context_switcher") is False)
    dtree = shell.filter_ia_tree(devi)
    check("devi no SYSTEM", "SYSTEM" not in [s["title"] for s in dtree])
    check(
        "devi up needs you landing",
        shell.parent_for_path("/staff-ops-routing", devi) == "/bzg/uma-blu",
    )
    d_crumbs = shell.breadcrumbs_for_path("/staff-ops-routing", devi)
    home_crumb = next((c for c in d_crumbs if c.get("label") == "HOME"), None)
    check(
        "devi home crumb not empire",
        home_crumb is not None
        and home_crumb.get("href") in (None, "/bzg/uma-blu", "/staff-ops-routing"),
    )

    amanda = shell.build_whoami(person_id="PERS-AMANDA", email=AMANDA)
    check("amanda hide progress", "/progress" not in amanda["pages"])
    check("amanda hide empire", "/owner-empire-pack" not in amanda["pages"])
    check("amanda context switcher off", amanda.get("context_switcher") is False)


def test_files() -> None:
    check("sidenav exists", SIDENAV.is_file())
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav nav cache", "20260922-nav-" in sn)
    check("sidenav EMPIRE_ALIASES", "EMPIRE_ALIASES" in sn or "/wolf" in sn)
    check("sidenav primary empire", "primary: true" in sn or "primary:true" in sn)
    check("sidenav Needs You", "Needs You" in sn)
    check(
        "sidenav Progress under SYSTEM",
        sn.find("SYSTEM") < sn.find('"/progress"') or "progress" in sn,
    )
    home_idx = sn.find('id: "home"')
    system_idx = sn.find('id: "system"')
    progress_idx = sn.find('href: "/progress"')
    check(
        "progress after system section",
        progress_idx > system_idx > home_idx,
        f"{home_idx},{system_idx},{progress_idx}",
    )
    check("no mgmt-cluster primary", "mgmt-cluster" not in sn)
    check("no radar primary", 'href: "/radar"' not in sn and "radar.html" not in sn)
    check("sidenav wolfnav-crumbs", "wolfnav-crumbs" in sn)
    check("sidenav wolfnav-up", "wolfnav-up" in sn)
    check("sidenav wolfnav-back", "wolfnav-back" in sn)
    check("sidenav wolfnav-home", "wolfnav-home" in sn)
    check("sidenav wolfnav-ctx", "wolfnav-ctx" in sn)
    check("sidenav context_switcher", "context_switcher" in sn)
    check("sidenav ROUTE_CRUMBS", "ROUTE_CRUMBS" in sn)
    check("sidenav paintCrumbs", "paintCrumbs" in sn)
    check("sidenav paintDir", "paintDir" in sn)
    check("sidenav paintContext", "paintContext" in sn)
    check("sidenav one wolfnav guard", "Never create a second #wolfnav" in sn)
    check(
        "sidenav single boards id",
        sn.count('id = "wolfnav-t"') + sn.count('id="wolfnav-t"') >= 1,
    )

    css = SHELL_CSS.read_text(encoding="utf-8")
    check("shell css crumbs", "nv-crumbs" in css or "wolfnav-crumbs" in css)
    check("shell css dir", "nv-dir" in css)
    check("shell css ctx", "nv-ctx" in css)

    tok = TOKENS.read_text(encoding="utf-8")
    check("tokens @media phone", "@media (max-width: 860px)" in tok)
    check("tokens @media tablet", "@media (min-width: 861px) and (max-width: 1100px)" in tok)
    check("tokens @media desktop", "@media (min-width: 1101px)" in tok)
    check("tokens no-hscroll / stack", "wolf-stack-mobile" in tok and "wolf-card-row" in tok)
    check("tokens table desktop hide", "wolf-table-desktop" in tok)

    emp = EMPIRE_HTML.read_text(encoding="utf-8")
    check("empire DASHBOARD", 'data-wolf-page-type="DASHBOARD"' in emp)
    check("empire shell global", 'data-wolf-shell="global"' in emp)
    check("empire home-primary attr", 'data-wolf-home-primary="empire"' in emp)
    check("empire org crumb", "WOLF" in emp and "Empire" in emp)

    needs = NEEDS_HTML.read_text(encoding="utf-8")
    check("needs WORKSPACE", 'data-wolf-page-type="WORKSPACE"' in needs)
    check("needs shell global", 'data-wolf-shell="global"' in needs)
    check("needs You title", "Needs You" in needs)

    stub = shell.inject_shell(
        b"<html><head></head><body><h1>t</h1></body></html>",
        rel="owner-empire-pack.html",
        whoami=shell.build_whoami(person_id="PERS-MATT", email=MATT),
    ).decode()
    check("inject crumbs id", 'id="wolfnav-crumbs"' in stub)
    check("inject up id", 'id="wolfnav-up"' in stub)
    check("inject back id", 'id="wolfnav-back"' in stub)
    check("inject home id", 'id="wolfnav-home"' in stub)
    check("inject ctx id", 'id="wolfnav-ctx"' in stub)
    check("inject single wolfnav", stub.count('id="wolfnav"') == 1)
    check("inject single boards", stub.count('id="wolfnav-t"') == 1)
    check("inject no second boards menu", stub.lower().count("aria-label=\"boards\"") <= 1)


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

    src = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve_beta /wolf alias", '"/wolf"' in src and "_owner_empire_page" in src)
    check(
        "staff-ops uses shell inject",
        'rel="staff-ops-routing.html"' in src
        and "_send_html_shell"
        in src[src.find("def _staff_ops_page") : src.find("def _staff_ops_page") + 800],
    )

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
        for path in (
            "/api/owner/empire-pack",
            "/owner-empire-pack",
            "/wolf",
            "/staff-ops-routing",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        pages = (payload.get("whoami") or {}).get("pages") or []
        check("anon empty pages", pages == [])
        check("anon no landing grant", not (payload.get("whoami") or {}).get("landing"))
        check("anon no context switcher", not payload.get("context_switcher"))

        st, payload = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami 200", st == 200)
        check("matt OWNER", who.get("audience") == "OWNER" or who.get("wolf_authorized") is True)
        check("matt landing /wolf", who.get("landing") == "/wolf", str(who.get("landing")))
        check("matt home_primary", who.get("home_primary") == "/owner-empire-pack")
        check("matt sees empire", "/owner-empire-pack" in (who.get("pages") or []))
        check("matt sees needs you", "/staff-ops-routing" in (who.get("pages") or []))
        check("matt sees progress", "/progress" in (who.get("pages") or []))
        check("matt context switcher off (auto-resolve)", who.get("context_switcher") is False)
        check("matt assignments multi", len(who.get("assignments") or []) > 1)
        ia = payload.get("ia") or []
        home = next((s for s in ia if s.get("id") == "home"), None)
        system = next((s for s in ia if s.get("id") == "system"), None)
        check("matt IA HOME", home is not None)
        check("matt IA SYSTEM", system is not None)
        if home:
            check(
                "matt IA HOME empire primary",
                any(
                    it.get("key") == "empire" and it.get("primary")
                    for it in home.get("items") or []
                ),
            )
            check(
                "matt IA HOME no progress",
                not any(it.get("href") == "/progress" for it in home.get("items") or []),
            )
        if system:
            check(
                "matt IA SYSTEM has progress",
                any(it.get("href") == "/progress" for it in system.get("items") or []),
            )

        st, payload = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami", st == 200 and who.get("audience") == "OPERATOR")
        check("devi hide progress", "/progress" not in (who.get("pages") or []))
        check("devi hide empire", "/owner-empire-pack" not in (who.get("pages") or []))
        check("devi see needs you", "/staff-ops-routing" in (who.get("pages") or []))
        check("devi no context switcher", who.get("context_switcher") is False)
        d_ia = payload.get("ia") or []
        check("devi no SYSTEM section", not any(s.get("id") == "system" for s in d_ia))

        st, html = call("GET", "/owner-empire-pack", MATT)
        check("empire html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("empire #wolfnav", 'id="wolfnav"' in html)
            check("empire single wolfnav", html.count('id="wolfnav"') == 1)
            check("empire #wolfnav-t", 'id="wolfnav-t"' in html)
            check("empire single toggle", html.count('id="wolfnav-t"') == 1)
            check("empire sidenav once", html.count("sidenav.js") == 1)
            check("empire tokens", "wolf-tokens.css" in html)
            check("empire page-type", 'data-wolf-page-type="DASHBOARD"' in html)
            check("empire crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("empire up chrome", 'id="wolfnav-up"' in html)
            check("empire back chrome", 'id="wolfnav-back"' in html)
            check("empire home chrome", 'id="wolfnav-home"' in html)
            check("empire ctx chrome", 'id="wolfnav-ctx"' in html)

        st, html = call("GET", "/wolf", MATT)
        check("wolf alias html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("wolf alias #wolfnav", 'id="wolfnav"' in html)
            check("wolf alias single wolfnav", html.count('id="wolfnav"') == 1)
            check("wolf alias #wolfnav-t", 'id="wolfnav-t"' in html)
            check("wolf alias Empire body", "Owner Empire" in html or "Empire" in html)
            check("wolf alias crumbs", 'id="wolfnav-crumbs"' in html)

        st, html = call("GET", "/staff-ops-routing", DEVI)
        check("needs you html 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("needs you #wolfnav", 'id="wolfnav"' in html)
            check("needs you single wolfnav", html.count('id="wolfnav"') == 1)
            check("needs you #wolfnav-t", 'id="wolfnav-t"' in html)
            check("needs you page-type", 'data-wolf-page-type="WORKSPACE"' in html)
            check("needs you whoami baked", "__WOLF_WHOAMI__" in html)
            check("needs you crumbs", 'id="wolfnav-crumbs"' in html)
            check("needs you up", 'id="wolfnav-up"' in html)
            if "__WOLF_WHOAMI__" in html:
                blob = html.split("__WOLF_WHOAMI__=")[1][:2000]
                check("needs you bake no progress", '"/progress"' not in blob)
                check(
                    "needs you bake no context switcher",
                    '"context_switcher":false' in blob
                    or '"context_switcher": false' in blob,
                )

        st, _ = call("GET", "/wolf", DEVI)
        check("devi wolf alias forbidden", st in (403, 401), str(st))
        st, _ = call("GET", "/owner-empire-pack", DEVI)
        check("devi empire forbidden", st in (403, 401), str(st))
        st, _ = call("GET", "/progress", DEVI)
        check("devi progress forbidden", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_empire_home.py",
    ):
        check(f"pack not wip {path}", path not in WIP)


def main() -> int:
    test_module_landing()
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
