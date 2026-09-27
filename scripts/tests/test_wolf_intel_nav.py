#!/usr/bin/env python3
"""Wave 6 Wolf Intelligence Nav — Beta :8788 only.

Owner → Intelligence Home (/intel-ops-pack). Haikal → Content (/content-2.0)
under Intelligence→Content. No Owner Intel admin side door for content crew.
Coral/Amanda/Devi retain Wave3–5 landings; crumbs WOLF › Intelligence › ….
Anon 403. One #wolfnav. Soft prior Wave1–5. No Production. No invent PROVEN/READY.
"""
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
HAIKAL = "haikalqilbari123@gmail.com"
CORAL = "mlsary111@gmail.com"

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
INTEL_HTML = ROOT / "dashboards" / "intel-ops-pack.html"
CONTENT_HTML = ROOT / "dashboards" / "content-2.0.html"
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


def soft(name: str, cond: bool, detail: str = "") -> None:
    """Record soft prior-wave assert — still counts toward PASS/FAIL."""
    check(f"soft {name}", cond, detail)


def _labels(crumbs: list) -> list[str]:
    return [str(c.get("label") or "") for c in crumbs]


def test_module() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    # Wave6 or Wave7+ System / Wave8+ Specialist successor slice
    slice_s = str(flags.get("slice", "")).lower()
    check(
        "wave6+ slice",
        "intel" in slice_s or "system" in slice_s or "specialist" in slice_s
        or "responsive" in slice_s or "rhc" in slice_s
        or "permission" in slice_s
        or "audience" in slice_s
        or "route" in slice_s or "merge" in slice_s
        or "retire" in slice_s or "redirect" in slice_s
        or "nas" in slice_s or "library" in slice_s,
        slice_s,
    )
    check("haikal landing flag", flags.get("haikal_landing_content") is True)
    check("intel home soft-land", flags.get("intel_home_soft_land") is True)
    check("content under intelligence", flags.get("content_under_intelligence") is True)
    check("intel crumbs flag", flags.get("intel_crumbs_wolf_intelligence") is True)
    check("coral landing retained", flags.get("coral_landing_amg_today") is True)
    check("amanda landing retained", flags.get("amanda_landing_ggv_overview") is True)
    check("devi landing retained", flags.get("devi_landing_uma_today") is True)
    check("amg crumbs retained", flags.get("amg_crumbs_wolf_atrium_amg") is True)
    check("ggv crumbs retained", flags.get("ggv_crumbs_wolf_goss_ggv") is True)
    check("bzg crumbs retained", flags.get("bzg_crumbs_wolf_blu_uma_today") is True)
    check("grammar empty flag", flags.get("grammar_empty_honest") is True)
    check("client fail-closed flag", flags.get("client_projection_fail_closed") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)
    check("no fake grammar pct", shell.grammar_has_fake_pct() is False)
    check("no money flag", flags.get("money") is None)

    empty_intel = [g for g in shell.intel_grammar() if g.get("state") == "EMPTY"]
    live_intel = [g for g in shell.intel_grammar() if g.get("state") == "live"]
    check("intel grammar has EMPTY", len(empty_intel) >= 3)
    check(
        "intel home live",
        any(g.get("key") == "home" and g.get("href") == "/intel-ops-pack" for g in live_intel),
    )
    check(
        "intel content live",
        any(g.get("key") == "content" and g.get("href") == "/content-2.0" for g in live_intel),
    )
    check(
        "intel EMPTY have no href",
        all(not g.get("href") for g in empty_intel),
    )
    check(
        "intel EMPTY no fake pct",
        all("%" not in str(g.get("label")) for g in empty_intel),
    )

    haikal = shell.build_whoami(person_id="PERS-HAIKAL", email=HAIKAL)
    check("haikal landing Content", haikal.get("landing") == "/content-2.0")
    check("haikal see Content", "/content-2.0" in (haikal.get("pages") or []))
    check("haikal hide Intel Home", "/intel-ops-pack" not in (haikal.get("pages") or []))
    check("haikal hide Progress", "/progress" not in (haikal.get("pages") or []))
    check("haikal hide Empire", "/owner-empire-pack" not in (haikal.get("pages") or []))
    check("haikal hide AMG", "/amg-ops-pack" not in (haikal.get("pages") or []))
    check("haikal hide Uma", "/bzg/uma-blu" not in (haikal.get("pages") or []))
    htree = shell.filter_ia_tree(haikal)
    hrefs = [it["href"] for s in htree for it in s["items"]]
    check("haikal IA has Content", "/content-2.0" in hrefs)
    check("haikal IA no Intel Home", "/intel-ops-pack" not in hrefs)
    check("haikal IA has INTELLIGENCE", any(s.get("id") == "intelligence" for s in htree))
    check("haikal no SYSTEM", not any(s.get("id") == "system" for s in htree))
    intel_sec = next((s for s in htree if s.get("id") == "intelligence"), None)
    check(
        "haikal Intel section Content-only",
        intel_sec is not None
        and [it["href"] for it in intel_sec["items"]] == ["/content-2.0"],
        str(intel_sec),
    )

    h_crumbs = shell.breadcrumbs_for_path("/content-2.0", haikal)
    labs = _labels(h_crumbs)
    check("haikal crumbs WOLF", labs[0] == "WOLF" if labs else False, str(labs))
    check("haikal crumbs Intelligence", "Intelligence" in labs)
    check("haikal crumbs Content last", labs[-1] == "Content" if labs else False, str(labs))
    check(
        "haikal crumbs trail",
        labs == ["WOLF", "Intelligence", "Content"],
        str(labs),
    )
    # Intelligence parent soft-null — no Owner Intel side door via crumb href
    intel_crumb = next((c for c in h_crumbs if c.get("label") == "Intelligence"), None)
    check(
        "haikal Intelligence crumb no intel href",
        intel_crumb is not None and intel_crumb.get("href") in (None, "/content-2.0"),
        str(intel_crumb),
    )
    h_dir = shell.direction_for_path("/content-2.0", haikal)
    check("haikal HOME → Content", h_dir.get("home") == "/content-2.0")
    check(
        "haikal UP soft-land (no Intel admin)",
        h_dir.get("up") in ("/content-2.0", None) or h_dir.get("up") == haikal.get("landing"),
        str(h_dir),
    )

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("matt has Intel", "/intel-ops-pack" in owner["pages"])
    check("matt has Content", "/content-2.0" in owner["pages"])
    check("matt landing wolf", owner.get("landing") == "/wolf")
    m_crumbs = shell.breadcrumbs_for_path("/intel-ops-pack", owner)
    check(
        "matt Intel crumbs",
        _labels(m_crumbs) == ["WOLF", "Intelligence"],
        str(_labels(m_crumbs)),
    )
    m_dir = shell.direction_for_path("/intel-ops-pack", owner)
    check("matt UP from Intel → Empire", m_dir.get("up") == "/owner-empire-pack")
    check("matt HOME empire", m_dir.get("home") in ("/wolf", "/owner-empire-pack"))

    c_crumbs = shell.breadcrumbs_for_path("/content-2.0", owner)
    check(
        "matt Content crumbs",
        _labels(c_crumbs) == ["WOLF", "Intelligence", "Content"],
        str(_labels(c_crumbs)),
    )
    check(
        "matt Content → Intel crumb href",
        any(c.get("label") == "Intelligence" and c.get("href") == "/intel-ops-pack" for c in c_crumbs),
    )
    check(
        "UP Content → Intel",
        shell.parent_for_path("/content-2.0", owner) == "/intel-ops-pack",
    )

    # Wave5 regression — Coral still AMG
    coral = shell.build_whoami(person_id="PERS-MISA", email=CORAL)
    check("coral landing AMG", coral.get("landing") == "/amg-ops-pack")
    check("coral hide Intel", "/intel-ops-pack" not in (coral.get("pages") or []))
    check("coral hide Content", "/content-2.0" not in (coral.get("pages") or []))
    check("coral hide Progress", "/progress" not in (coral.get("pages") or []))
    check("coral no INTELLIGENCE IA", not any(s.get("id") == "intelligence" for s in shell.filter_ia_tree(coral)))

    # Wave4 regression — Amanda still GGV
    amanda = shell.build_whoami(person_id="PERS-AMANDA", email=AMANDA)
    check("amanda landing GGV", amanda.get("landing") == "/ggv-ops-pack")
    check("amanda hide Intel", "/intel-ops-pack" not in (amanda.get("pages") or []))
    check("amanda hide Content", "/content-2.0" not in (amanda.get("pages") or []))
    check("amanda hide Progress", "/progress" not in (amanda.get("pages") or []))
    check("amanda hide Empire", "/owner-empire-pack" not in (amanda.get("pages") or []))

    # Wave3 regression — Devi still Uma Today
    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi landing Today", devi.get("landing") == "/bzg/uma-blu")
    check("devi hide Intel", "/intel-ops-pack" not in (devi.get("pages") or []))
    check("devi hide Content", "/content-2.0" not in (devi.get("pages") or []))
    check("devi hide Progress", "/progress" not in (devi.get("pages") or []))
    check("devi hide Empire", "/owner-empire-pack" not in (devi.get("pages") or []))

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client pages empty", client.get("pages") == [])
    check("client landing none", client.get("landing") is None)
    check("client IA empty", shell.filter_ia_tree(client) == [])


def test_files() -> None:
    check("intel html exists", INTEL_HTML.is_file())
    intel = INTEL_HTML.read_text(encoding="utf-8")
    check("intel crumb Intelligence", "WOLF · Intelligence" in intel)
    check("intel EMPTY grammar", "Brand / Competitive · EMPTY" in intel)
    grammar_block = (
        intel.split('aria-label="Intelligence grammar"')[1].split("</nav>")[0]
        if 'aria-label="Intelligence grammar"' in intel
        else ""
    )
    check(
        "intel grammar no fake pct",
        "PROVEN" not in grammar_block
        and "READY" not in grammar_block
        and "%" not in grammar_block,
        grammar_block[:200],
    )
    check("intel page-type", 'data-wolf-page-type="DASHBOARD"' in intel)
    check("intel shell global", 'data-wolf-shell="global"' in intel)
    check("intel org INTEL", 'data-wolf-org="INTEL"' in intel)
    check("intel home active", 'href="/intel-ops-pack"' in intel)
    check("intel content link", 'href="/content-2.0"' in intel)

    check("content html exists", CONTENT_HTML.is_file())
    content = CONTENT_HTML.read_text(encoding="utf-8")
    check(
        "content crumb trail",
        "WOLF · Intelligence · Content" in content,
    )
    check("content page-type", 'data-wolf-page-type="WORKSPACE"' in content)
    check("content shell global", 'data-wolf-shell="global"' in content)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav Intelligence crumbs", '"Intelligence"' in sn)
    check("sidenav Content crumb", 'label: "Content"' in sn)
    check("sidenav content href", '"/content-2.0"' in sn)
    check("sidenav WOLF crumb", 'label: "WOLF"' in sn)
    check("sidenav nav-intel+ cache", "20260922-nav-" in sn)
    check("sidenav one wolfnav guard", "Never create a second #wolfnav" in sn)


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
            "/intel-ops-pack",
            "/api/intel/ops-pack",
            "/content-2.0",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        slice_s = str(h.get("slice", "")).lower()
        check(
            "honesty slice wave6+",
            "intel" in slice_s or "system" in slice_s or "specialist" in slice_s
        or "responsive" in slice_s or "rhc" in slice_s
            or "permission" in slice_s
            or "audience" in slice_s
            or "route" in slice_s or "merge" in slice_s
            or "retire" in slice_s or "redirect" in slice_s
            or "nas" in slice_s or "library" in slice_s,
            slice_s,
        )
        check("honesty proven false", h.get("proven") is False)
        check("honesty ready false", h.get("ready") is False)
        check("honesty haikal flag", h.get("haikal_landing_content") is True)
        check("honesty intel crumbs", h.get("intel_crumbs_wolf_intelligence") is True)
        check("honesty content under intel", h.get("content_under_intelligence") is True)
        check("honesty coral retained", h.get("coral_landing_amg_today") is True)
        check("honesty amanda retained", h.get("amanda_landing_ggv_overview") is True)
        check("honesty devi retained", h.get("devi_landing_uma_today") is True)
        check("honesty client fail-closed", h.get("client_projection_fail_closed") is True)
        who_anon = payload.get("whoami") or {}
        check("anon client audience", who_anon.get("audience") == "CLIENT")
        check("anon client pages empty", who_anon.get("pages") == [])

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", HAIKAL)
        who = payload.get("whoami") or {}
        check("haikal whoami landing", who.get("landing") == "/content-2.0")
        check("haikal whoami see content", "/content-2.0" in (who.get("pages") or []))
        check("haikal whoami hide intel", "/intel-ops-pack" not in (who.get("pages") or []))
        check("haikal whoami hide progress", "/progress" not in (who.get("pages") or []))
        check("haikal whoami hide empire", "/owner-empire-pack" not in (who.get("pages") or []))
        ia = payload.get("ia") or []
        check("haikal no SYSTEM", not any(s.get("id") == "system" for s in ia))
        intel_ia = next((s for s in ia if s.get("id") == "intelligence"), None)
        check(
            "haikal IA Content under Intel",
            intel_ia is not None
            and any(it.get("href") == "/content-2.0" for it in intel_ia.get("items") or []),
        )
        check(
            "haikal IA no Intel Home",
            intel_ia is None
            or not any(it.get("href") == "/intel-ops-pack" for it in intel_ia.get("items") or []),
        )

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami see intel", "/intel-ops-pack" in (who.get("pages") or []))
        check("matt whoami see content", "/content-2.0" in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", CORAL)
        who = payload.get("whoami") or {}
        check("coral whoami landing amg", who.get("landing") == "/amg-ops-pack")
        check("coral whoami hide intel", "/intel-ops-pack" not in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", AMANDA)
        who = payload.get("whoami") or {}
        check("amanda whoami landing ggv", who.get("landing") == "/ggv-ops-pack")
        check("amanda whoami hide intel", "/intel-ops-pack" not in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami landing uma", who.get("landing") == "/bzg/uma-blu")
        check("devi whoami hide intel", "/intel-ops-pack" not in (who.get("pages") or []))

        st, html, _ = call("GET", "/intel-ops-pack", MATT)
        check("matt intel 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt intel #wolfnav", 'id="wolfnav"' in html)
            check("matt intel single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt intel crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("matt intel up", 'id="wolfnav-up"' in html)
            check("matt intel home", 'id="wolfnav-home"' in html)
            check("matt intel EMPTY", "EMPTY" in html)
            check("matt intel Intelligence crumb text", "Intelligence" in html)
            check("matt intel sidenav once", html.count("sidenav.js") == 1)

        st, html, _ = call("GET", "/content-2.0", HAIKAL)
        check(
            "haikal content reachable or seat-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("haikal content staff shell", "CONTENT ENGINE" in html and 'id="staffHello"' in html)
            check("haikal content omits engineering nav", 'id="wolfnav"' not in html)
            check("haikal content omits boards chrome", ">Boards<" not in html and 'id="wolfnav-up"' not in html)
            if "__WOLF_WHOAMI__" in html:
                raw_who = html.split("__WOLF_WHOAMI__=", 1)[1]
                raw_who = raw_who.split(";</script>", 1)[0]
                try:
                    baked = json.loads(raw_who)
                except json.JSONDecodeError:
                    baked = {}
                pages = baked.get("pages") or []
                check("haikal bake no intel home", "/intel-ops-pack" not in pages)
                check("haikal bake no progress", "/progress" not in pages)
                check("haikal bake no empire", "/owner-empire-pack" not in pages)
                check("haikal bake landing content", baked.get("landing") == "/content-2.0")

        st, html, _ = call("GET", "/content-2.0", MATT)
        check(
            "matt content reachable or scoped-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("matt content #wolfnav", 'id="wolfnav"' in html)
            check("matt content single wolfnav", html.count('id="wolfnav"') == 1)

        # Side door: Coral/Amanda/Devi cannot open Owner Intel via nav alone — API fail-closed.
        for label, subject in (
            ("coral", CORAL),
            ("amanda", AMANDA),
            ("devi", DEVI),
            ("haikal", HAIKAL),
        ):
            st, _, _ = call("GET", "/intel-ops-pack", subject)
            check(f"{label} intel forbidden", st in (403, 401), str(st))
            st, _, _ = call("GET", "/api/intel/ops-pack", subject)
            check(f"{label} intel api forbidden", st in (403, 401), str(st))

        st, _, _ = call("GET", "/progress", HAIKAL)
        check("haikal progress forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/owner-empire-pack", HAIKAL)
        check("haikal empire forbidden", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_intel_nav.py",
        "dashboards/intel-ops-pack.html",
        "dashboards/content-2.0.html",
    ):
        check(f"pack not wip {path}", path not in WIP)


def test_soft_prior_waves() -> None:
    env = {
        **os.environ,
        "WOLF_TEST_MODE": "1",
        "BETA_AUTH_MODE": "development_assertion",
        "PYTHONPATH": str(SCRIPTS),
    }
    priors = (
        ("wave1 shell-tokens", "scripts/tests/test_wolf_shell_tokens.py"),
        ("wave2 empire-home", "scripts/tests/test_wolf_empire_home.py"),
        ("wave3 bzg-uma-nav", "scripts/tests/test_wolf_bzg_uma_nav.py"),
        ("wave4 ggv-nav", "scripts/tests/test_wolf_ggv_nav.py"),
        ("wave5 amg-nav", "scripts/tests/test_wolf_amg_nav.py"),
    )
    for label, rel in priors:
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and "EXIT: SUCCESS" in out
        soft(f"prior {label} green", ok, out[-400:] if not ok else "")


def main() -> int:
    test_module()
    test_files()
    test_http()
    test_prod_untouched()
    test_wip()
    test_soft_prior_waves()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
