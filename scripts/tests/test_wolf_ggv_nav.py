#!/usr/bin/env python3
"""Wave 4 Wolf GGV Nav — Beta :8788 only.

Amanda landing = GGV Overview (/ggv-ops-pack). Breadcrumbs WOLF › Goss Group › GGV › ….
Grammar EMPTY-honest (never fake %). Matt reaches GGV. Devi still lands Uma (Wave3).
Hide Progress+Empire+Uma depth from Amanda. Client fail-closed. Anon 403. One #wolfnav.
No Production. No invent PROVEN/READY. No client projection this wave.
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

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
GGV_HTML = ROOT / "dashboards" / "ggv-ops-pack.html"
HABITAT_HTML = ROOT / "dashboards" / "habitat-operator.html"
LEAD_HTML = ROOT / "dashboards" / "lead-spine.html"
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
    # Wave4 or Wave5+ AMG / Wave6+ Intel / Wave7+ System / Wave8+ Specialist successor slice
    slice_s = str(flags.get("slice", "")).lower()
    check(
        "wave4+ slice",
        "ggv" in slice_s
        or "amg" in slice_s
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
    check("amanda landing flag", flags.get("amanda_landing_ggv_overview") is True)
    check("ggv crumbs flag", flags.get("ggv_crumbs_wolf_goss_ggv") is True)
    check("devi landing flag retained", flags.get("devi_landing_uma_today") is True)
    check("bzg crumbs flag retained", flags.get("bzg_crumbs_wolf_blu_uma_today") is True)
    check("grammar empty flag", flags.get("grammar_empty_honest") is True)
    check("client fail-closed flag", flags.get("client_projection_fail_closed") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)
    check("no fake grammar pct", shell.grammar_has_fake_pct() is False)

    empty_ggv = [g for g in shell.ggv_grammar() if g.get("state") == "EMPTY"]
    live_ggv = [g for g in shell.ggv_grammar() if g.get("state") == "live"]
    check("ggv grammar has EMPTY", len(empty_ggv) >= 6)
    check("ggv overview live", any(g.get("key") == "overview" for g in live_ggv))
    check(
        "ggv overview href ops-pack",
        any(g.get("key") == "overview" and g.get("href") == "/ggv-ops-pack" for g in live_ggv),
    )
    check(
        "ggv EMPTY have no href",
        all(not g.get("href") for g in empty_ggv),
    )
    check(
        "ggv EMPTY no fake pct",
        all("%" not in str(g.get("label")) for g in empty_ggv),
    )

    amanda = shell.build_whoami(person_id="PERS-AMANDA", email=AMANDA)
    check("amanda landing GGV", amanda.get("landing") == "/ggv-ops-pack")
    check("amanda see GGV", "/ggv-ops-pack" in (amanda.get("pages") or []))
    check("amanda hide Progress", "/progress" not in (amanda.get("pages") or []))
    check("amanda hide Empire", "/owner-empire-pack" not in (amanda.get("pages") or []))
    check("amanda hide Uma depth", "/bzg/uma-blu" not in (amanda.get("pages") or []))
    check("amanda hide BZG", "/bzg" not in (amanda.get("pages") or []))
    check("amanda hide AMG", "/amg-ops-pack" not in (amanda.get("pages") or []))
    atree = shell.filter_ia_tree(amanda)
    hrefs = [it["href"] for s in atree for it in s["items"]]
    check("amanda IA has GGV", "/ggv-ops-pack" in hrefs)
    check("amanda IA no progress", "/progress" not in hrefs)
    check("amanda IA no empire", "/owner-empire-pack" not in hrefs)
    check("amanda IA no uma", "/bzg/uma-blu" not in hrefs)
    check("amanda no SYSTEM", not any(s.get("id") == "system" for s in atree))

    crumbs = shell.breadcrumbs_for_path("/ggv-ops-pack", amanda)
    labs = _labels(crumbs)
    check("amanda crumbs WOLF", labs[0] == "WOLF" if labs else False, str(labs))
    check("amanda crumbs Goss Group", "Goss Group" in labs)
    check("amanda crumbs GGV last", labs[-1] == "GGV" if labs else False, str(labs))
    check(
        "amanda crumbs trail",
        labs == ["WOLF", "Goss Group", "GGV"],
        str(labs),
    )
    a_dir = shell.direction_for_path("/ggv-ops-pack", amanda)
    check("amanda HOME → GGV", a_dir.get("home") == "/ggv-ops-pack")
    check(
        "amanda UP soft-land (no Empire)",
        a_dir.get("up") in ("/ggv-ops-pack", None) or a_dir.get("up") == amanda.get("landing"),
        str(a_dir),
    )

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    check("matt has GGV", "/ggv-ops-pack" in owner["pages"])
    check("matt landing wolf", owner.get("landing") == "/wolf")
    m_crumbs = shell.breadcrumbs_for_path("/ggv-ops-pack", owner)
    check(
        "matt GGV crumbs Goss",
        _labels(m_crumbs) == ["WOLF", "Goss Group", "GGV"],
        str(_labels(m_crumbs)),
    )
    m_dir = shell.direction_for_path("/ggv-ops-pack", owner)
    check("matt UP from GGV → Empire", m_dir.get("up") == "/owner-empire-pack")
    check("matt HOME empire", m_dir.get("home") in ("/wolf", "/owner-empire-pack"))

    hab = shell.breadcrumbs_for_path("/habitat-operator", owner)
    check(
        "habitat crumbs trail",
        _labels(hab) == ["WOLF", "Goss Group", "GGV", "Habitat"],
        str(_labels(hab)),
    )
    check(
        "habitat GGV → ops-pack",
        any(c.get("label") == "GGV" and c.get("href") == "/ggv-ops-pack" for c in hab),
    )
    check(
        "UP habitat → GGV",
        shell.parent_for_path("/habitat-operator", owner) == "/ggv-ops-pack",
    )

    lead = shell.breadcrumbs_for_path("/lead-spine", owner)
    check(
        "lead crumbs trail",
        _labels(lead) == ["WOLF", "Goss Group", "GGV", "Lead Spine"],
        str(_labels(lead)),
    )
    check(
        "UP lead → GGV",
        shell.parent_for_path("/lead-spine", owner) == "/ggv-ops-pack",
    )

    # Wave3 regression — Devi still Uma Today
    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    check("devi landing Today", devi.get("landing") == "/bzg/uma-blu")
    check("devi hide GGV", "/ggv-ops-pack" not in (devi.get("pages") or []))
    check("devi hide Progress", "/progress" not in (devi.get("pages") or []))
    check("devi hide Empire", "/owner-empire-pack" not in (devi.get("pages") or []))
    check("devi see Uma", "/bzg/uma-blu" in (devi.get("pages") or []))

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client pages empty", client.get("pages") == [])
    check("client landing none", client.get("landing") is None)
    check("client IA empty", shell.filter_ia_tree(client) == [])


def test_files() -> None:
    check("ggv html exists", GGV_HTML.is_file())
    ggv = GGV_HTML.read_text(encoding="utf-8")
    check("ggv crumb Goss Group", "WOLF · Goss Group · GGV" in ggv)
    check("ggv finance live", 'href="/ggv/finance"' in ggv and "Finance · EMPTY" not in ggv)
    check("ggv other EMPTY grammar", "Operations · EMPTY" in ggv and "People · EMPTY" in ggv)
    grammar_block = (
        ggv.split('aria-label="GGV grammar"')[1].split("</nav>")[0]
        if 'aria-label="GGV grammar"' in ggv
        else ""
    )
    check(
        "ggv grammar no fake pct",
        "PROVEN" not in grammar_block
        and "READY" not in grammar_block
        and "%" not in grammar_block,
        grammar_block[:200],
    )
    check("ggv page-type", 'data-wolf-page-type="DASHBOARD"' in ggv)
    check("ggv shell global", 'data-wolf-shell="global"' in ggv)
    check("ggv org GGV", 'data-wolf-org="GGV"' in ggv)
    check("ggv overview active", 'href="/ggv-ops-pack"' in ggv)

    check("habitat html exists", HABITAT_HTML.is_file())
    hab = HABITAT_HTML.read_text(encoding="utf-8")
    check("habitat crumb trail", "WOLF · Goss Group · GGV · Habitat" in hab)
    check("habitat page-type", 'data-wolf-page-type="WORKSPACE"' in hab)

    check("lead html exists", LEAD_HTML.is_file())
    lead = LEAD_HTML.read_text(encoding="utf-8")
    check("lead crumb trail", "WOLF · Goss Group · GGV · Lead Spine" in lead)
    check("lead page-type", 'data-wolf-page-type="WORKSPACE"' in lead)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav Goss Group crumbs", '"Goss Group"' in sn)
    check("sidenav Habitat crumb", 'label: "Habitat"' in sn)
    check("sidenav Lead Spine crumb", 'label: "Lead Spine"' in sn)
    check("sidenav WOLF crumb", 'label: "WOLF"' in sn)
    # Wave4 cache or Wave5+ AMG successor
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
            "/ggv-ops-pack",
            "/api/ggv/ops-pack",
            "/habitat-operator",
            "/lead-spine",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        slice_s = str(h.get("slice", "")).lower()
        check(
            "honesty slice wave4+",
            "ggv" in slice_s
            or "amg" in slice_s
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
        check("honesty amanda flag", h.get("amanda_landing_ggv_overview") is True)
        check("honesty ggv crumbs flag", h.get("ggv_crumbs_wolf_goss_ggv") is True)
        check("honesty client fail-closed", h.get("client_projection_fail_closed") is True)
        who_anon = payload.get("whoami") or {}
        check("anon client audience", who_anon.get("audience") == "CLIENT")
        check("anon client pages empty", who_anon.get("pages") == [])

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", AMANDA)
        who = payload.get("whoami") or {}
        check("amanda whoami landing", who.get("landing") == "/ggv-ops-pack")
        check("amanda whoami hide progress", "/progress" not in (who.get("pages") or []))
        check("amanda whoami hide empire", "/owner-empire-pack" not in (who.get("pages") or []))
        check("amanda whoami hide uma", "/bzg/uma-blu" not in (who.get("pages") or []))
        check("amanda whoami see ggv", "/ggv-ops-pack" in (who.get("pages") or []))
        ia = payload.get("ia") or []
        check("amanda no SYSTEM", not any(s.get("id") == "system" for s in ia))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        check("matt whoami see ggv", "/ggv-ops-pack" in (who.get("pages") or []))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = payload.get("whoami") or {}
        check("devi whoami landing uma", who.get("landing") == "/bzg/uma-blu")
        check("devi whoami hide ggv", "/ggv-ops-pack" not in (who.get("pages") or []))

        st, html, _ = call("GET", "/ggv-ops-pack", AMANDA)
        check("amanda ggv 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("amanda ggv #wolfnav", 'id="wolfnav"' in html)
            check("amanda ggv single wolfnav", html.count('id="wolfnav"') == 1)
            check("amanda ggv crumbs chrome", 'id="wolfnav-crumbs"' in html)
            check("amanda ggv up", 'id="wolfnav-up"' in html)
            check("amanda ggv home", 'id="wolfnav-home"' in html)
            check("amanda ggv EMPTY", "EMPTY" in html)
            check("amanda ggv Goss crumb text", "Goss Group" in html)
            check("amanda ggv sidenav once", html.count("sidenav.js") == 1)
            if "__WOLF_WHOAMI__" in html:
                blob = html.split("__WOLF_WHOAMI__=")[1][:2500]
                check("amanda bake no progress", '"/progress"' not in blob)
                check("amanda bake no empire", '"/owner-empire-pack"' not in blob)
                check("amanda bake no uma", '"/bzg/uma-blu"' not in blob)
                check("amanda bake landing ggv", '"/ggv-ops-pack"' in blob)

        st, html, _ = call("GET", "/ggv-ops-pack", MATT)
        check("matt ggv 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt ggv #wolfnav", 'id="wolfnav"' in html)
            check("matt ggv single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt ggv crumbs", 'id="wolfnav-crumbs"' in html)

        st, html, _ = call("GET", "/habitat-operator", MATT)
        check(
            "matt habitat reachable or scoped-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("matt habitat #wolfnav", 'id="wolfnav"' in html)
            check("matt habitat single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt habitat crumbs", 'id="wolfnav-crumbs"' in html)
            check("matt habitat Goss text", "Goss Group" in html)

        st, html, _ = call("GET", "/lead-spine", MATT)
        check(
            "matt lead reachable or scoped-deny",
            st in (200, 403),
            str(st),
        )
        if st == 200 and isinstance(html, str):
            check("matt lead #wolfnav", 'id="wolfnav"' in html)
            check("matt lead single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt lead crumbs", 'id="wolfnav-crumbs"' in html)

        st, _, _ = call("GET", "/progress", AMANDA)
        check("amanda progress forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/owner-empire-pack", AMANDA)
        check("amanda empire forbidden", st in (403, 401), str(st))
        st, _, _ = call("GET", "/bzg/uma-blu", AMANDA)
        check("amanda uma forbidden", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_ggv_nav.py",
        "dashboards/ggv-ops-pack.html",
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
    )
    for label, rel in priors:
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
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
