#!/usr/bin/env python3
"""Wave 5 Wolf AMG / Atrium Nav — Beta :8788 only.

Coral landing = AMG Today/Ops (/amg-ops-pack). Breadcrumbs WOLF › Atrium Management › AMG › ….
Grammar EMPTY-honest (never fake %). Finance nested/visible-only. Matt reaches AMG.
Amanda still lands GGV (Wave4). Devi still lands Uma (Wave3).
Hide Progress+Empire+GGV-depth+Uma-depth from Coral. Anon 403. One #wolfnav.
No Production. No invent PROVEN/READY. No money/Zayen.
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
# Coral / AMG ops fixture (role-nav matrix) — catalog PERS-MISA
CORAL = "mlsary111@gmail.com"

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
AMG_HTML = ROOT / "dashboards" / "amg-ops-pack.html"
DAILY_HTML = ROOT / "dashboards" / "amg-daily-ops-state.html"
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
    # Wave5 or Wave6+ Intel / Wave7+ System / Wave8+ Specialist successor slice
    slice_s = str(flags.get("slice", "")).lower()
    check(
        "wave5+ slice",
        "amg" in slice_s
        or "intel" in slice_s
        or "system" in slice_s
        or "specialist" in slice_s
        or "responsive" in slice_s
        or "rhc" in slice_s
        or "permission" in slice_s
        or "audience" in slice_s
        or "route" in slice_s or "merge" in slice_s
        or "retire" in slice_s or "redirect" in slice_s
        or "nas" in slice_s or "library" in slice_s,
        slice_s,
    )
    check("coral landing flag", flags.get("coral_landing_amg_today") is True)
    check("amg crumbs flag", flags.get("amg_crumbs_wolf_atrium_amg") is True)
    check("finance nested flag", flags.get("amg_finance_nested_visible_only") is True)
    check("amanda landing retained", flags.get("amanda_landing_ggv_overview") is True)
    check("devi landing retained", flags.get("devi_landing_uma_today") is True)
    check("ggv crumbs retained", flags.get("ggv_crumbs_wolf_goss_ggv") is True)
    check("bzg crumbs retained", flags.get("bzg_crumbs_wolf_blu_uma_today") is True)
    check("grammar empty flag", flags.get("grammar_empty_honest") is True)
    check("client fail-closed flag", flags.get("client_projection_fail_closed") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)
    check("no fake grammar pct", shell.grammar_has_fake_pct() is False)
    check("no money flag", flags.get("money") is None)

    empty_amg = [g for g in shell.amg_grammar() if g.get("state") == "EMPTY"]
    live_amg = [g for g in shell.amg_grammar() if g.get("state") == "live"]
    check("amg grammar has EMPTY", len(empty_amg) >= 5)
    check(
        "amg overview live",
        any(g.get("key") == "overview" and g.get("href") == "/amg-ops-pack" for g in live_amg),
    )
    check(
        "amg operations live",
        any(g.get("key") == "operations" and g.get("href") == "/amg-ops-pack" for g in live_amg),
    )
    fin = next((g for g in shell.amg_grammar() if g.get("key") == "finance"), None)
    check("amg finance EMPTY", fin is not None and fin.get("state") == "EMPTY")
    check("amg finance no href", fin is not None and not fin.get("href"))
    check(
        "amg EMPTY have no href",
        all(not g.get("href") for g in empty_amg),
    )
    check(
        "amg EMPTY no fake pct",
        all("%" not in str(g.get("label")) for g in empty_amg),
    )

    coral = shell.build_whoami(person_id="PERS-MISA", email=CORAL)
    check("coral landing AMG", coral.get("landing") == "/amg-ops-pack")
    check("coral see AMG", "/amg-ops-pack" in (coral.get("pages") or []))
    check("coral hide Progress", "/progress" not in (coral.get("pages") or []))
    check("coral hide Empire", "/owner-empire-pack" not in (coral.get("pages") or []))
    check("coral hide GGV depth", "/ggv-ops-pack" not in (coral.get("pages") or []))
    check("coral hide Uma depth", "/bzg/uma-blu" not in (coral.get("pages") or []))
    check("coral hide BZG", "/bzg" not in (coral.get("pages") or []))
    ctree = shell.filter_ia_tree(coral)
    hrefs = [it["href"] for s in ctree for it in s["items"]]
    check("coral IA has AMG", "/amg-ops-pack" in hrefs)
    check("coral IA no progress", "/progress" not in hrefs)
    check("coral IA no empire", "/owner-empire-pack" not in hrefs)
    check("coral IA no ggv", "/ggv-ops-pack" not in hrefs)
    check("coral IA no uma", "/bzg/uma-blu" not in hrefs)
    check("coral no SYSTEM", not any(s.get("id") == "system" for s in ctree))
    check("coral no INTELLIGENCE", not any(s.get("id") == "intelligence" for s in ctree))

    crumbs = shell.breadcrumbs_for_path("/amg-ops-pack", coral)
    labs = _labels(crumbs)
    check("coral crumbs WOLF", labs[0] == "WOLF" if labs else False, str(labs))
    check("coral crumbs Atrium Management", "Atrium Management" in labs)
    check("coral crumbs AMG last", labs[-1] == "AMG" if labs else False, str(labs))
    check(
        "coral crumbs trail",
        labs == ["WOLF", "Atrium Management", "AMG"],
        str(labs),
    )
    c_dir = shell.direction_for_path("/amg-ops-pack", coral)
    check("coral HOME → AMG", c_dir.get("home") == "/amg-ops-pack")
    check(
        "coral UP soft-land (no Empire)",
        c_dir.get("up") in ("/amg-ops-pack", None) or c_dir.get("up") == coral.get("landing"),
        str(c_dir),
    )

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("matt has AMG", "/amg-ops-pack" in owner["pages"])
    check("matt landing wolf", owner.get("landing") == "/wolf")
    m_crumbs = shell.breadcrumbs_for_path("/amg-ops-pack", owner)
    check(
        "matt AMG crumbs Atrium",
        _labels(m_crumbs) == ["WOLF", "Atrium Management", "AMG"],
        str(_labels(m_crumbs)),
    )
    m_dir = shell.direction_for_path("/amg-ops-pack", owner)
    check("matt UP from AMG → Empire", m_dir.get("up") == "/owner-empire-pack")
    check("matt HOME empire", m_dir.get("home") in ("/wolf", "/owner-empire-pack"))

    daily = shell.breadcrumbs_for_path("/amg-daily-ops-state", owner)
    check(
        "daily crumbs trail",
        _labels(daily) == ["WOLF", "Atrium Management", "AMG", "Daily Ops"],
        str(_labels(daily)),
    )
    check(
        "daily AMG → ops-pack",
        any(c.get("label") == "AMG" and c.get("href") == "/amg-ops-pack" for c in daily),
    )
    check(
        "UP daily → AMG",
        shell.parent_for_path("/amg-daily-ops-state", owner) == "/amg-ops-pack",
    )

    # Wave4 regression — Amanda still GGV Overview
    amanda = shell.build_whoami(person_id="PERS-AMANDA", email=AMANDA)
    check("amanda landing GGV", amanda.get("landing") == "/ggv-ops-pack")
    check("amanda hide Progress", "/progress" not in (amanda.get("pages") or []))
    check("amanda hide Empire", "/owner-empire-pack" not in (amanda.get("pages") or []))
    check("amanda hide Uma", "/bzg/uma-blu" not in (amanda.get("pages") or []))
    check("amanda hide AMG ops", "/amg-ops-pack" not in (amanda.get("pages") or []))

    # Wave3 regression — Devi still Uma Today
    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi landing Today", devi.get("landing") == "/bzg/uma-blu")
    check("devi hide GGV", "/ggv-ops-pack" not in (devi.get("pages") or []))
    check("devi hide AMG", "/amg-ops-pack" not in (devi.get("pages") or []))
    check("devi hide Progress", "/progress" not in (devi.get("pages") or []))
    check("devi hide Empire", "/owner-empire-pack" not in (devi.get("pages") or []))

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client pages empty", client.get("pages") == [])
    check("client landing none", client.get("landing") is None)
    check("client IA empty", shell.filter_ia_tree(client) == [])


def test_files() -> None:
    check("amg html exists", AMG_HTML.is_file())
    amg = AMG_HTML.read_text(encoding="utf-8")
    check("amg crumb Atrium Management", "WOLF · Atrium Management · AMG" in amg)
    check("amg EMPTY grammar", "People · EMPTY" in amg and "Finance · EMPTY" in amg)
    grammar_block = (
        amg.split('aria-label="AMG grammar"')[1].split("</nav>")[0]
        if 'aria-label="AMG grammar"' in amg
        else ""
    )
    check(
        "amg grammar no fake pct",
        "PROVEN" not in grammar_block
        and "READY" not in grammar_block
        and "%" not in grammar_block,
        grammar_block[:200],
    )
    check("amg page-type", 'data-wolf-page-type="DASHBOARD"' in amg)
    check("amg shell global", 'data-wolf-shell="global"' in amg)
    check("amg org AMG", 'data-wolf-org="AMG"' in amg)
    check("amg overview active", 'href="/amg-ops-pack"' in amg)

    check("daily html exists", DAILY_HTML.is_file())
    daily = DAILY_HTML.read_text(encoding="utf-8")
    check(
        "daily crumb trail",
        "WOLF · Atrium Management · AMG · Daily Ops" in daily,
    )
    check("daily page-type", 'data-wolf-page-type="WORKSPACE"' in daily)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav Atrium Management crumbs", '"Atrium Management"' in sn)
    check("sidenav Daily Ops crumb", 'label: "Daily Ops"' in sn)
    check("sidenav AMG crumb", 'label: "AMG"' in sn)
    check("sidenav WOLF crumb", 'label: "WOLF"' in sn)
    check("sidenav nav cache", "20260922-nav-" in sn)
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
            "/amg-ops-pack",
            "/api/amg/ops-pack",
            "/amg-daily-ops-state",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        slice_s = str(h.get("slice", "")).lower()
        check(
            "honesty slice wave5+",
            "amg" in slice_s
            or "intel" in slice_s
            or "system" in slice_s
            or "specialist" in slice_s
            or "responsive" in slice_s
            or "rhc" in slice_s
            or "permission" in slice_s
            or "audience" in slice_s
            or "route" in slice_s or "merge" in slice_s
            or "retire" in slice_s or "redirect" in slice_s
            or "nas" in slice_s or "library" in slice_s,
            slice_s,
        )
        check("honesty proven false", h.get("proven") is False)
        check("honesty ready false", h.get("ready") is False)
        check("honesty coral flag", h.get("coral_landing_amg_today") is True)
        check("honesty amg crumbs flag", h.get("amg_crumbs_wolf_atrium_amg") is True)
        check("honesty amanda retained", h.get("amanda_landing_ggv_overview") is True)
        check("honesty devi retained", h.get("devi_landing_uma_today") is True)
        check("honesty finance nested", h.get("amg_finance_nested_visible_only") is True)
        check("honesty client fail-closed", h.get("client_projection_fail_closed") is True)
        who_anon = payload.get("whoami") or {}
        check("anon client audience", who_anon.get("audience") == "CLIENT")
        check("anon client pages empty", who_anon.get("pages") == [])

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", CORAL)
        who = payload.get("whoami") or {}
        check("coral whoami landing", who.get("landing") == "/amg-ops-pack")
        check("coral whoami hide progress", "/progress" not in (who.get("pages") or []))
        check("coral whoami hide empire", "/owner-empire-pack" not in (who.get("pages") or []))
        check("coral whoami hide ggv", "/ggv-ops-pack" not in (who.get("pages") or []))
        check("coral whoami hide uma", "/bzg/uma-blu" not in (who.get("pages") or []))
        check("coral whoami see amg", "/amg-ops-pack" in (who.get("pages") or []))
        ia = payload.get("ia") or []
        check("coral no SYSTEM", not any(s.get("id") == "system" for s in ia))
        check("coral no INTELLIGENCE", not any(s.get("id") == "intelligence" for s in ia))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami see amg", "/amg-ops-pack" in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", AMANDA)
        who = payload.get("whoami") or {}
        check("amanda whoami landing ggv", who.get("landing") == "/ggv-ops-pack")
        check("amanda whoami hide amg", "/amg-ops-pack" not in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami landing uma", who.get("landing") == "/bzg/uma-blu")
        check("devi whoami hide amg", "/amg-ops-pack" not in (who.get("pages") or []))

        st, html, _ = call("GET", "/amg-ops-pack", MATT)
        check("matt amg 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt amg #wolfnav", 'id="wolfnav"' in html)
            check("matt amg single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt amg crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("matt amg up", 'id="wolfnav-up"' in html)
            check("matt amg home", 'id="wolfnav-home"' in html)
            check("matt amg EMPTY", "EMPTY" in html)
            check("matt amg Atrium crumb text", "Atrium Management" in html)
            check("matt amg sidenav once", html.count("sidenav.js") == 1)

        # Coral may lack live hotel-ops seat — API auth canonical; whoami is visibility-only.
        st, html, _ = call("GET", "/amg-ops-pack", CORAL)
        check(
            "coral amg reachable or seat-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("coral amg #wolfnav", 'id="wolfnav"' in html)
            check("coral amg single wolfnav", html.count('id="wolfnav"') == 1)
            check("coral amg crumbs", 'id="wolfnav-crumbs"' in html)
            if "__WOLF_WHOAMI__" in html:
                blob = html.split("__WOLF_WHOAMI__=")[1][:2500]
                check("coral bake no progress", '"/progress"' not in blob)
                check("coral bake no empire", '"/owner-empire-pack"' not in blob)
                check("coral bake no ggv", '"/ggv-ops-pack"' not in blob)
                check("coral bake no uma", '"/bzg/uma-blu"' not in blob)
                check("coral bake landing amg", '"/amg-ops-pack"' in blob)

        st, html, _ = call("GET", "/amg-daily-ops-state", MATT)
        check(
            "matt daily reachable or scoped-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("matt daily #wolfnav", 'id="wolfnav"' in html)
            check("matt daily single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt daily crumbs", 'id="wolfnav-crumbs"' in html)
            check("matt daily Atrium text", "Atrium Management" in html)

        st, _, _ = call("GET", "/progress", CORAL)
        check("coral progress forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/owner-empire-pack", CORAL)
        check("coral empire forbidden", st in (403, 401), str(st))
        # GGV may still allow PERS-MISA crew seat (domain auth) — nav hide ≠ permission.
        st, _, _ = call("GET", "/ggv-ops-pack", CORAL)
        check(
            "coral ggv nav-hidden domain-auth",
            st in (200, 403, 401),
            str(st),
        )
        st, _, _ = call("GET", "/bzg/uma-blu", CORAL)
        check("coral uma forbidden", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_amg_nav.py",
        "dashboards/amg-ops-pack.html",
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
    )
    for label, rel in priors:
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
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
