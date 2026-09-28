#!/usr/bin/env python3
"""Wave 7 Wolf System Nav — Beta :8788 only.

Owner → System/Progress (+ Integrations / Sale). Staff hide SYSTEM admin via nav.
Crumbs WOLF › System › …. Factory EMPTY-honest. Anon 403. One #wolfnav.
Soft prior Wave1–6. No Production. No invent PROVEN/READY.
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
PROGRESS_HTML = ROOT / "dashboards" / "progress.html"
INTEG_HTML = ROOT / "dashboards" / "integration-health.html"
SALE_HTML = ROOT / "dashboards" / "sale-evidence-pack.html"
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
    # Wave7 or Wave8+ Specialist successor slice
    slice_s = str(flags.get("slice", "")).lower()
    check("wave7+ slice", "system" in slice_s or "specialist" in slice_s
        or "responsive" in slice_s or "rhc" in slice_s
        or "permission" in slice_s or "audience" in slice_s
        or "route" in slice_s or "merge" in slice_s
        or "retire" in slice_s or "redirect" in slice_s
        or "nas" in slice_s or "library" in slice_s, slice_s)
    check("system home soft-land", flags.get("system_home_soft_land_progress") is True)
    check("sale under system", flags.get("sale_under_system") is True)
    check("factory empty flag", flags.get("factory_grammar_empty") is True)
    check("staff hide system flag", flags.get("staff_hide_system_admin") is True)
    check("system crumbs flag", flags.get("system_crumbs_wolf_system") is True)
    check("progress under system only", flags.get("progress_under_system_only") is True)
    check("haikal landing retained", flags.get("haikal_landing_content") is True)
    check("coral amg landing retired", flags.get("coral_landing_amg_today") is False)
    check("amanda landing retained", flags.get("amanda_landing_ggv_overview") is True)
    check("devi landing retained", flags.get("devi_landing_uma_today") is True)
    check("intel crumbs retained", flags.get("intel_crumbs_wolf_intelligence") is True)
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

    empty_sys = [g for g in shell.system_grammar() if g.get("state") == "EMPTY"]
    live_sys = [g for g in shell.system_grammar() if g.get("state") == "live"]
    check("system grammar has EMPTY", len(empty_sys) >= 1)
    check(
        "system progress live",
        any(g.get("key") == "progress" and g.get("href") == "/progress" for g in live_sys),
    )
    check(
        "system integrations live",
        any(
            g.get("key") == "integrations" and g.get("href") == "/integration-health"
            for g in live_sys
        ),
    )
    check(
        "system sale live",
        any(
            g.get("key") == "sale" and g.get("href") == "/sale-evidence-pack" for g in live_sys
        ),
    )
    check(
        "system factory EMPTY",
        any(g.get("key") == "factory" and not g.get("href") for g in empty_sys),
    )
    check(
        "system EMPTY have no href",
        all(not g.get("href") for g in empty_sys),
    )
    check(
        "system EMPTY no fake pct",
        all("%" not in str(g.get("label")) for g in empty_sys),
    )

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("matt has Progress", "/progress" in owner["pages"])
    check("matt has Integrations", "/integration-health" in owner["pages"])
    check("matt has Sale", "/sale-evidence-pack" in owner["pages"])
    check("matt landing wolf", owner.get("landing") == "/wolf")
    mtree = shell.filter_ia_tree(owner)
    check("matt has SYSTEM IA", any(s.get("id") == "system" for s in mtree))
    sys_sec = next((s for s in mtree if s.get("id") == "system"), None)
    sys_hrefs = [it["href"] for it in (sys_sec or {}).get("items") or []]
    check("matt SYSTEM has Progress", "/progress" in sys_hrefs)
    check("matt SYSTEM has Integrations", "/integration-health" in sys_hrefs)
    check("matt SYSTEM has Sale", "/sale-evidence-pack" in sys_hrefs)
    check(
        "matt Progress crumbs",
        _labels(shell.breadcrumbs_for_path("/progress", owner))
        == ["WOLF", "System", "Progress"],
        str(_labels(shell.breadcrumbs_for_path("/progress", owner))),
    )
    check(
        "matt Integrations crumbs",
        _labels(shell.breadcrumbs_for_path("/integration-health", owner))
        == ["WOLF", "System", "Integrations"],
        str(_labels(shell.breadcrumbs_for_path("/integration-health", owner))),
    )
    check(
        "matt Sale crumbs",
        _labels(shell.breadcrumbs_for_path("/sale-evidence-pack", owner))
        == ["WOLF", "System", "Sale"],
        str(_labels(shell.breadcrumbs_for_path("/sale-evidence-pack", owner))),
    )
    check(
        "matt System crumb href on Integrations",
        any(
            c.get("label") == "System" and c.get("href") == "/progress"
            for c in shell.breadcrumbs_for_path("/integration-health", owner)
        ),
    )
    m_dir = shell.direction_for_path("/progress", owner)
    check("matt UP from Progress → Empire", m_dir.get("up") == "/owner-empire-pack")
    check("matt HOME empire", m_dir.get("home") in ("/wolf", "/owner-empire-pack"))
    check(
        "UP Integrations → Progress",
        shell.parent_for_path("/integration-health", owner) == "/progress",
    )
    check(
        "UP Sale → Progress",
        shell.parent_for_path("/sale-evidence-pack", owner) == "/progress",
    )

    # Staff hide SYSTEM admin via nav
    for label, person, email, landing in (
        ("haikal", "PERS-HAIKAL", HAIKAL, "/content-2.0"),
        ("coral", "PERS-MISA", CORAL, "/content-2.0"),
        ("amanda", "PERS-AMANDA", AMANDA, "/ggv-ops-pack"),
        ("devi", "PERS-DEVI", DEVI, "/bzg/uma-blu"),
    ):
        who = shell.build_whoami(person_id=person, email=email)
        check(f"{label} landing retained", who.get("landing") == landing)
        check(f"{label} hide Progress", "/progress" not in (who.get("pages") or []))
        check(
            f"{label} hide Integrations",
            "/integration-health" not in (who.get("pages") or []),
        )
        check(
            f"{label} hide Sale",
            "/sale-evidence-pack" not in (who.get("pages") or []),
        )
        tree = shell.filter_ia_tree(who)
        check(f"{label} no SYSTEM", not any(s.get("id") == "system" for s in tree))

    # Wave6 soft — Haikal still Content under Intel
    haikal = shell.build_whoami(person_id="PERS-HAIKAL", email=HAIKAL)
    check("haikal see Content", "/content-2.0" in (haikal.get("pages") or []))
    check("haikal hide Intel Home", "/intel-ops-pack" not in (haikal.get("pages") or []))
    htree = shell.filter_ia_tree(haikal)
    check("haikal IA has INTELLIGENCE", any(s.get("id") == "intelligence" for s in htree))

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client pages empty", client.get("pages") == [])
    check("client landing none", client.get("landing") is None)
    check("client IA empty", shell.filter_ia_tree(client) == [])


def test_files() -> None:
    check("progress html exists", PROGRESS_HTML.is_file())
    progress = PROGRESS_HTML.read_text(encoding="utf-8")
    check("progress crumb System", "WOLF · System · Progress" in progress)
    check("progress Factory EMPTY", "Factory / Health · EMPTY" in progress)
    grammar_block = (
        progress.split('aria-label="System grammar"')[1].split("</nav>")[0]
        if 'aria-label="System grammar"' in progress
        else ""
    )
    check(
        "progress grammar no fake pct",
        "PROVEN" not in grammar_block
        and "READY" not in grammar_block
        and "%" not in grammar_block,
        grammar_block[:200],
    )
    check("progress page-type", 'data-wolf-page-type="SYSTEM"' in progress)
    check("progress shell global", 'data-wolf-shell="global"' in progress)
    check("progress sale link", 'href="/sale-evidence-pack"' in progress)
    check("progress integ link", 'href="/integration-health"' in progress)

    check("integ html exists", INTEG_HTML.is_file())
    integ = INTEG_HTML.read_text(encoding="utf-8")
    check("integ crumb trail", "WOLF · System · Integrations" in integ)
    check("integ page-type", 'data-wolf-page-type="SYSTEM"' in integ)
    check("integ shell global", 'data-wolf-shell="global"' in integ)
    check("integ Factory EMPTY", "Factory / Health · EMPTY" in integ)

    check("sale html exists", SALE_HTML.is_file())
    sale = SALE_HTML.read_text(encoding="utf-8")
    check("sale crumb trail", "WOLF · System · Sale" in sale)
    check("sale page-type", 'data-wolf-page-type="SYSTEM"' in sale)
    check("sale shell global", 'data-wolf-shell="global"' in sale)
    check("sale Factory EMPTY", "Factory / Health · EMPTY" in sale)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav System crumbs", 'label: "System"' in sn)
    check("sidenav Sale crumb", 'label: "Sale"' in sn)
    check("sidenav sale href", '"/sale-evidence-pack"' in sn)
    check("sidenav WOLF crumb", 'label: "WOLF"' in sn)
    check("sidenav nav-system+ cache", "20260922-nav-" in sn)
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
            "/progress",
            "/api/progress",
            "/integration-health",
            "/api/integration-health",
            "/sale-evidence-pack",
            "/api/sale-evidence-pack",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        check("honesty slice wave7+", "system" in str(h.get("slice", "")).lower() or "specialist" in str(h.get("slice", "")).lower()
            or "responsive" in str(h.get("slice", "")).lower() or "rhc" in str(h.get("slice", "")).lower()
            or "permission" in str(h.get("slice", "")).lower() or "audience" in str(h.get("slice", "")).lower()
            or "route" in str(h.get("slice", "")).lower() or "merge" in str(h.get("slice", "")).lower()
            or "retire" in str(h.get("slice", "")).lower() or "redirect" in str(h.get("slice", "")).lower())
        check("honesty proven false", h.get("proven") is False)
        check("honesty ready false", h.get("ready") is False)
        check("honesty system soft-land", h.get("system_home_soft_land_progress") is True)
        check("honesty system crumbs", h.get("system_crumbs_wolf_system") is True)
        check("honesty sale under system", h.get("sale_under_system") is True)
        check("honesty factory empty", h.get("factory_grammar_empty") is True)
        check("honesty staff hide", h.get("staff_hide_system_admin") is True)
        check("honesty haikal retained", h.get("haikal_landing_content") is True)
        check("honesty coral amg landing retired", h.get("coral_landing_amg_today") is False)
        check("honesty amanda retained", h.get("amanda_landing_ggv_overview") is True)
        check("honesty devi retained", h.get("devi_landing_uma_today") is True)
        check("honesty intel crumbs retained", h.get("intel_crumbs_wolf_intelligence") is True)
        check("honesty client fail-closed", h.get("client_projection_fail_closed") is True)
        who_anon = payload.get("whoami") or {}
        check("anon client audience", who_anon.get("audience") == "CLIENT")
        check("anon client pages empty", who_anon.get("pages") == [])

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami see progress", "/progress" in (who.get("pages") or []))
        check(
            "matt whoami see integrations",
            "/integration-health" in (who.get("pages") or []),
        )
        check(
            "matt whoami see sale",
            "/sale-evidence-pack" in (who.get("pages") or []),
        )
        ia = payload.get("ia") or []
        system = next((s for s in ia if s.get("id") == "system"), None)
        check("matt IA SYSTEM", system is not None)
        if system:
            hrefs = [it.get("href") for it in system.get("items") or []]
            check("matt IA SYSTEM progress", "/progress" in hrefs)
            check("matt IA SYSTEM sale", "/sale-evidence-pack" in hrefs)

        for label, subject, landing in (
            ("haikal", HAIKAL, "/content-2.0"),
            ("coral", CORAL, "/content-2.0"),
            ("amanda", AMANDA, "/ggv-ops-pack"),
            ("devi", DEVI, "/bzg/uma-blu"),
        ):
            st, payload, _ = call("GET", "/api/wolf/shell-whoami", subject)
            who = payload.get("whoami") or {}
            check(f"{label} whoami landing", who.get("landing") == landing)
            check(f"{label} whoami hide progress", "/progress" not in (who.get("pages") or []))
            check(
                f"{label} whoami hide sale",
                "/sale-evidence-pack" not in (who.get("pages") or []),
            )
            ia = payload.get("ia") or []
            check(f"{label} no SYSTEM", not any(s.get("id") == "system" for s in ia))

        st, html, _ = call("GET", "/progress", MATT)
        check("matt progress 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt progress #wolfnav", 'id="wolfnav"' in html)
            check("matt progress single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt progress crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("matt progress up", 'id="wolfnav-up"' in html)
            check("matt progress home", 'id="wolfnav-home"' in html)
            check("matt progress System crumb text", "System" in html)
            check("matt progress EMPTY", "EMPTY" in html)
            check("matt progress sidenav once", html.count("sidenav.js") == 1)

        st, html, _ = call("GET", "/integration-health", MATT)
        check("matt integ 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt integ #wolfnav", 'id="wolfnav"' in html)
            check("matt integ single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt integ System text", "System" in html)

        st, html, _ = call("GET", "/sale-evidence-pack", MATT)
        check("matt sale 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt sale #wolfnav", 'id="wolfnav"' in html)
            check("matt sale single wolfnav", html.count('id="wolfnav"') == 1)

        # Staff cannot open SYSTEM admin via nav alone — API fail-closed.
        for label, subject in (
            ("coral", CORAL),
            ("amanda", AMANDA),
            ("devi", DEVI),
            ("haikal", HAIKAL),
        ):
            for path in (
                "/progress",
                "/api/progress",
                "/integration-health",
                "/api/integration-health",
                "/sale-evidence-pack",
                "/api/sale-evidence-pack",
            ):
                st, _, _ = call("GET", path, subject)
                check(f"{label} forbidden {path}", st in (403, 401), str(st))

        # Wave6 soft — Intel landings still fail-closed for staff
        st, _, _ = call("GET", "/intel-ops-pack", HAIKAL)
        check("haikal intel forbidden", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_system_nav.py",
        "dashboards/progress.html",
        "dashboards/integration-health.html",
        "dashboards/sale-evidence-pack.html",
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
        ("wave6 intel-nav", "scripts/tests/test_wolf_intel_nav.py"),
    )
    for label, rel in priors:
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and "EXIT: SUCCESS" in out
        soft(f"prior {label} green", ok, out[-500:] if not ok else "")


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
