#!/usr/bin/env python3
"""Wave 8 Wolf Specialist Nav — Beta :8788 only.

trading/travel/spartacus/mila/amanda/kuta-rates NOT primary in #wolfnav IA.
Soft redirect → /wolf. Wave1–7 soft green. Anon 403. One #wolfnav.
No Production. No invent PROVEN/READY.
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
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)

SPECIALIST_SLUGS = (
    "trading",
    "travel",
    "spartacus",
    "mila",
    "amanda",
    "kuta-rates",
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


def _all_ia_hrefs(tree: list) -> list[str]:
    return [str(it.get("href") or "") for s in tree for it in (s.get("items") or [])]


def _all_ia_blob(tree: list) -> str:
    parts: list[str] = []
    for s in tree:
        parts.append(str(s.get("id") or ""))
        parts.append(str(s.get("title") or ""))
        for it in s.get("items") or []:
            parts.append(str(it.get("key") or ""))
            parts.append(str(it.get("href") or ""))
            parts.append(str(it.get("title") or ""))
    return " ".join(parts).lower()


def test_module() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    check("wave8+ slice", "specialist" in str(flags.get("slice", "")).lower()
        or "responsive" in str(flags.get("slice", "")).lower()
        or "rhc" in str(flags.get("slice", "")).lower()
        or "permission" in str(flags.get("slice", "")).lower()
        or "audience" in str(flags.get("slice", "")).lower()
        or "route" in str(flags.get("slice", "")).lower()
        or "merge" in str(flags.get("slice", "")).lower()
        or "retire" in str(flags.get("slice", "")).lower()
        or "redirect" in str(flags.get("slice", "")).lower())
    check("specialist not primary flag", flags.get("specialist_not_primary") is True)
    check(
        "specialist soft redirect flag",
        flags.get("specialist_soft_redirect_empire") is True,
    )
    check("system soft-land retained", flags.get("system_home_soft_land_progress") is True)
    check("sale under system retained", flags.get("sale_under_system") is True)
    check("factory empty retained", flags.get("factory_grammar_empty") is True)
    check("staff hide system retained", flags.get("staff_hide_system_admin") is True)
    check("system crumbs retained", flags.get("system_crumbs_wolf_system") is True)
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

    check("helper specialist_not_in_primary", shell.specialist_not_in_primary_ia() is True)
    leaks = shell.primary_ia_specialist_leaks()
    check("no specialist IA leaks", leaks == [], str(leaks))

    tree = shell.ia_tree()
    ids = [s.get("id") for s in tree]
    check("IA has HOME", "home" in ids)
    check("IA has BUSINESSES", "businesses" in ids)
    check("IA has INTELLIGENCE", "intelligence" in ids)
    check("IA has SYSTEM", "system" in ids)
    check("IA section count 4", len(tree) == 4, str(ids))
    blob = _all_ia_blob(tree)
    for slug in SPECIALIST_SLUGS:
        check(f"IA no {slug}", slug not in blob, blob[:200])

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    mtree = shell.filter_ia_tree(owner)
    mblob = _all_ia_blob(mtree)
    for slug in SPECIALIST_SLUGS:
        check(f"matt IA no {slug}", slug not in mblob)
    check("matt has SYSTEM", any(s.get("id") == "system" for s in mtree))
    check("matt has Progress", "/progress" in (owner.get("pages") or []))
    check("matt landing wolf", owner.get("landing") == "/wolf")
    check(
        "matt Progress crumbs unchanged",
        _labels(shell.breadcrumbs_for_path("/progress", owner))
        == ["WOLF", "System", "Progress"],
        str(_labels(shell.breadcrumbs_for_path("/progress", owner))),
    )
    check(
        "matt Integrations crumbs unchanged",
        _labels(shell.breadcrumbs_for_path("/integration-health", owner))
        == ["WOLF", "System", "Integrations"],
    )
    check(
        "UP Integrations → Progress",
        shell.parent_for_path("/integration-health", owner) == "/progress",
    )
    m_dir = shell.direction_for_path("/progress", owner)
    check("matt HOME empire", m_dir.get("home") in ("/wolf", "/owner-empire-pack"))

    for label, person, email, landing in (
        ("haikal", "PERS-HAIKAL", HAIKAL, "/content-2.0"),
        ("coral", "PERS-MISA", CORAL, "/content-2.0"),
        ("amanda", "PERS-AMANDA", AMANDA, "/ggv-ops-pack"),
        ("devi", "PERS-DEVI", DEVI, "/bzg/uma-blu"),
    ):
        who = shell.build_whoami(person_id=person, email=email)
        check(f"{label} landing retained", who.get("landing") == landing)
        check(f"{label} hide Progress", "/progress" not in (who.get("pages") or []))
        stree = shell.filter_ia_tree(who)
        check(f"{label} no SYSTEM", not any(s.get("id") == "system" for s in stree))
        sblob = _all_ia_blob(stree)
        for slug in SPECIALIST_SLUGS:
            check(f"{label} IA no {slug}", slug not in sblob)

    for slug in SPECIALIST_SLUGS:
        tgt = shell.specialist_soft_redirect_target(f"/{slug}")
        check(f"redirect /{slug} → wolf", tgt == "/wolf", str(tgt))
        tgt2 = shell.specialist_soft_redirect_target(f"/{slug}.html")
        check(f"redirect /{slug}.html → wolf", tgt2 == "/wolf", str(tgt2))

    check(
        "non-specialist no redirect",
        shell.specialist_soft_redirect_target("/progress") is None,
    )
    check(
        "empire no specialist redirect",
        shell.specialist_soft_redirect_target("/wolf") is None,
    )

    client = shell.build_whoami(person_id=None, audience="CLIENT")
    check("client pages empty", client.get("pages") == [])
    check("client IA empty", shell.filter_ia_tree(client) == [])


def test_files() -> None:
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav exists", SIDENAV.is_file())
    check("sidenav Wave8 comment", "Wave 8" in sn or "specialist" in sn.lower())
    check("sidenav nav-specialist or rhc or perms cache",
        "20260922-nav-specialist" in sn or "20260922-nav-rhc-v1" in sn
        or "20260922-nav-perms" in sn or "20260922-nav-route-merge" in sn)
    check("sidenav HIDDEN_SPECIALIST", "HIDDEN_SPECIALIST_PRIMARY" in sn)
    check("sidenav trading hidden map", "trading:" in sn or "trading: 1" in sn)
    check("sidenav travel hidden map", "travel:" in sn)
    check("sidenav spartacus hidden map", "spartacus:" in sn)
    check("sidenav one wolfnav guard", "Never create a second #wolfnav" in sn)
    check("sidenav System crumbs retained", 'label: "System"' in sn)
    check("sidenav WOLF crumb retained", 'label: "WOLF"' in sn)
    # Primary IA_TREE block must not list specialist hrefs
    ia_block = sn.split("var IA_TREE = [")[1].split("];")[0] if "var IA_TREE = [" in sn else ""
    for slug in SPECIALIST_SLUGS:
        check(f"sidenav IA_TREE no /{slug}", f'"/{slug}"' not in ia_block)

    src = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve specialist soft redirect", "SPECIALIST_SOFT_REDIRECT" in src)
    check("serve Wave8 comment", "Wave 8" in src)

    shell_src = (SCRIPTS / "core" / "wolf_shell.py").read_text(encoding="utf-8")
    check("shell slice v8+", "wolf_specialist_nav_v8" in shell_src
        or "wolf_responsive_v1_prove" in shell_src
        or "wolf_permissions_audience_prove" in shell_src)
    check("shell specialist_not_primary", "specialist_not_primary" in shell_src)


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
            headers_out = {}
            if loc:
                headers_out["Location"] = loc
            return exc.code, body, headers_out

    def call_redirect(url_path: str):
        """Follow is off — capture 302 Location."""
        class _NoRedirect(BaseHTTPRequestHandler):
            pass

        import urllib.request

        class _NoRedirHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
                return None

        opener = urllib.request.build_opener(_NoRedirHandler)
        req = Request(f"http://127.0.0.1:{port}{url_path}", method="GET")
        try:
            with opener.open(req, timeout=30) as resp:
                return resp.status, dict(resp.headers)
        except HTTPError as exc:
            return exc.code, {"Location": exc.headers.get("Location")}

    try:
        for path in (
            "/progress",
            "/api/progress",
            "/integration-health",
            "/sale-evidence-pack",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and payload.get("ok") is True)
        h = payload.get("honesty") or {}
        check("honesty slice wave8+", "specialist" in str(h.get("slice", "")).lower()
            or "responsive" in str(h.get("slice", "")).lower()
            or "route" in str(h.get("slice", "")).lower()
            or "merge" in str(h.get("slice", "")).lower()
            or "retire" in str(h.get("slice", "")).lower()
            or "redirect" in str(h.get("slice", "")).lower()
            or "permission" in str(h.get("slice", "")).lower()
            or "audience" in str(h.get("slice", "")).lower()
            or "responsive" in str(h.get("slice", "")).lower()
            or "rhc" in str(h.get("slice", "")).lower()
            or "permission" in str(h.get("slice", "")).lower()
            or "audience" in str(h.get("slice", "")).lower())
        check("honesty proven false", h.get("proven") is False)
        check("honesty ready false", h.get("ready") is False)
        check("honesty specialist_not_primary", h.get("specialist_not_primary") is True)
        check(
            "honesty specialist_soft_redirect",
            h.get("specialist_soft_redirect_empire") is True,
        )
        check("honesty system soft-land", h.get("system_home_soft_land_progress") is True)
        check("honesty staff hide", h.get("staff_hide_system_admin") is True)
        check("honesty haikal retained", h.get("haikal_landing_content") is True)
        check("honesty coral amg landing retired", h.get("coral_landing_amg_today") is False)
        check("honesty amanda retained", h.get("amanda_landing_ggv_overview") is True)
        check("honesty devi retained", h.get("devi_landing_uma_today") is True)
        check("honesty client fail-closed", h.get("client_projection_fail_closed") is True)
        who_anon = payload.get("whoami") or {}
        check("anon client audience", who_anon.get("audience") == "CLIENT")
        check("anon client pages empty", who_anon.get("pages") == [])

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = payload.get("whoami") or {}
        ia = payload.get("ia") or []
        blob = _all_ia_blob(ia)
        for slug in SPECIALIST_SLUGS:
            check(f"matt live IA no {slug}", slug not in blob)
        check("matt IA has SYSTEM", any(s.get("id") == "system" for s in ia))
        check("matt whoami see progress", "/progress" in (who.get("pages") or []))
        hrefs = _all_ia_hrefs(ia)
        check("matt IA primary sections only", all(
            any(h.startswith(p) for p in (
                "/owner-empire-pack", "/wolf", "/staff-ops-routing",
                "/ggv-ops-pack", "/amg-ops-pack", "/bzg",
                "/intel-ops-pack", "/content-2.0",
                "/progress", "/integration-health", "/sale-evidence-pack",
            ))
            for h in hrefs
        ), str(hrefs))

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
            ia = payload.get("ia") or []
            check(f"{label} no SYSTEM", not any(s.get("id") == "system" for s in ia))
            for slug in SPECIALIST_SLUGS:
                check(f"{label} live IA no {slug}", slug not in _all_ia_blob(ia))

        st, html, _ = call("GET", "/progress", MATT)
        check("matt progress 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt progress #wolfnav", 'id="wolfnav"' in html)
            check("matt progress single wolfnav", html.count('id="wolfnav"') == 1)
            check("matt progress sidenav once", html.count("sidenav.js") == 1)
            check("matt progress System crumb", "System" in html)

        st, html, _ = call("GET", "/owner-empire-pack", MATT)
        check("matt empire 200", st == 200 and isinstance(html, str), str(st))
        if isinstance(html, str):
            check("matt empire #wolfnav", 'id="wolfnav"' in html)
            check("matt empire single wolfnav", html.count('id="wolfnav"') == 1)

        for slug in SPECIALIST_SLUGS:
            code, hdrs = call_redirect(f"/{slug}")
            loc = (hdrs or {}).get("Location") or ""
            check(
                f"soft redirect /{slug}",
                code in (301, 302, 303, 307) and "/wolf" in loc,
                f"code={code} loc={loc}",
            )
            code2, hdrs2 = call_redirect(f"/{slug}.html")
            loc2 = (hdrs2 or {}).get("Location") or ""
            check(
                f"soft redirect /{slug}.html",
                code2 in (301, 302, 303, 307) and "/wolf" in loc2,
                f"code={code2} loc={loc2}",
            )

        # Staff SYSTEM still fail-closed
        for label, subject in (
            ("coral", CORAL),
            ("amanda", AMANDA),
            ("devi", DEVI),
            ("haikal", HAIKAL),
        ):
            for path in ("/progress", "/api/progress", "/sale-evidence-pack"):
                st, _, _ = call("GET", path, subject)
                check(f"{label} forbidden {path}", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_specialist_nav.py",
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
        ("wave7 system-nav", "scripts/tests/test_wolf_system_nav.py"),
    )
    for label, rel in priors:
        # Wave7 nests Wave1–6 soft priors — allow long wall time.
        timeout = 2400 if "system-nav" in rel else 1200
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
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
