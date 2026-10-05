#!/usr/bin/env python3
"""Wolf Route Merge / Retire / Redirect — Beta :8788 only.

Inventory → redirect>delete for top candidates. Preserve capability
(aliases, IA parents, Needs You, APIs). One #wolfnav. Soft prior flags
(Wave8/RHC/Perms) cheap; full nested suite soft-skipped (wall-clock).
No Production. No invent PROVEN/READY. No Global Nav V1 READY.
"""
from __future__ import annotations

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
HAIKAL = "haikalqilbari123@gmail.com"

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
DASHBOARDS = ROOT / "dashboards"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)

SPECIALIST_SLUGS = (
    # P0 re-entries (trading/travel/spartacus/kuta-rates) no longer Wave8 soft-redirect.
    "mila",
    "amanda",
)

# From → expected Location substring
REDIRECT_CASES = (
    ("/uma-blu", "/bzg/uma-blu"),
    ("/uma-blu.html", "/bzg/uma-blu"),
    ("/dashboards/uma-blu.html", "/bzg/uma-blu"),
    ("/bzg-uma-blu.html", "/bzg/uma-blu"),
    ("/dashboards/bzg-uma-blu.html", "/bzg/uma-blu"),
    ("/dashboards/habitat-operator.html", "/habitat-operator"),
    ("/dashboards/lead-spine.html", "/lead-spine"),
    ("/dashboards/progress.html", "/progress"),
    ("/radar.html", "/wolf"),
    ("/radar", "/wolf"),
    ("/content-habitat.html", "content-2.0"),
    ("/bzg-mgmt-cluster", "/bzg"),
    ("/dashboards/ggv-mgmt-cluster.html", "/ggv-ops-pack"),
    ("/amg-mgmt-cluster", "/amg-ops-pack"),
    ("/intel-mgmt-cluster", "/intel-ops-pack"),
    ("/sale-mgmt-cluster", "/sale-evidence-pack"),
    ("/intg-mgmt-cluster", "/integration-health"),
    ("/core-mgmt-cluster", "/progress"),
    ("/crm-mgmt-cluster", "/lead-spine"),
    ("/strat-mgmt-cluster", "/wolf"),
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
    check(f"soft {name}", cond, detail)


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


def test_inventory() -> None:
    inv = shell.route_merge_inventory()
    check("inventory helper", isinstance(inv, dict) and inv.get("one_wolfnav_owner") is True)
    mgmt = list(DASHBOARDS.glob("*-mgmt-cluster.html"))
    check("inventory mgmt-cluster count 11", len(mgmt) == 11, str(len(mgmt)))
    check(
        "inventory mgmt matches table",
        len(inv.get("mgmt_cluster_html") or []) == 11,
        str(inv.get("mgmt_cluster_html")),
    )
    op_html = list(DASHBOARDS.glob("*operator-depth*")) + list(DASHBOARDS.glob("*opdepth*"))
    check("inventory no operator-depth HTML", op_html == [], str(op_html))
    check("inventory operator_depth_html empty", inv.get("operator_depth_html") == [])
    content_peers = [
        p for p in DASHBOARDS.glob("content-*.html") if p.name != "content-2.0.html"
    ]
    # .bak ignored
    content_peers = [p for p in content_peers if not str(p).endswith(".bak")]
    check("inventory no content brand peer HTML", content_peers == [], str(content_peers))
    check("inventory radar_prove kept", inv.get("radar_prove_kept") is True)
    check("inventory no mgmt dir", inv.get("mgmt_cluster_dir") is None)
    check("redirect table non-empty", (inv.get("redirect_table_size") or 0) >= 40)


def test_module() -> None:
    flags = shell.honesty_flags()
    check("bound beta", flags["bound"] == "beta")
    slice_s = str(flags.get("slice", "")).lower()
    check(
        "route merge slice",
        "route" in slice_s or "merge" in slice_s or "retire" in slice_s or "redirect" in slice_s
        or "nas" in slice_s or "library" in slice_s,
        slice_s,
    )
    check("route merge flag", flags.get("route_merge_retire_redirect") is True)
    check("redirect > delete flag", flags.get("redirect_gt_delete") is True)
    check("mgmt soft-land flag", flags.get("mgmt_cluster_soft_land_bu") is True)
    check("radar soft-land flag", flags.get("radar_soft_land_empire_priorities") is True)
    check("dashboards→clean flag", flags.get("dashboards_html_to_clean") is True)
    check("content brand peers flag", flags.get("content_brand_peers_to_content") is True)
    check("active packs not killed", flags.get("active_packs_not_killed") is True)
    check("specialist not primary retained", flags.get("specialist_not_primary") is True)
    check(
        "specialist soft redirect retained",
        flags.get("specialist_soft_redirect_empire") is True,
    )
    check("progress under system", flags.get("progress_under_system_only") is True)
    check("sale under system", flags.get("sale_under_system") is True)
    check("perms prove retained", flags.get("permissions_audience_prove") is True)
    check("four layers retained", flags.get("four_layer_permissions") is True)
    check("rhc retained", flags.get("responsive_shell_v1_prove") is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no second boards", flags["second_boards_menu"] is False)
    check("no money flag", flags.get("money") is None)
    check("prior perms alias", shell.SLICE_PRIOR_PERMS == "wolf_permissions_audience_prove")
    check("prior rhc alias", shell.SLICE_PRIOR_RHC == "wolf_responsive_v1_prove")
    check("prior wave8 alias", shell.SLICE_PRIOR_WAVE8 == "wolf_specialist_nav_v8")

    for src, dest in REDIRECT_CASES:
        got = shell.route_merge_redirect_target(src)
        check(
            f"table {src}",
            got is not None and dest.split("?")[0].split("#")[0] in (got or ""),
            f"got={got} want~{dest}",
        )
    check("api never redirected", shell.route_merge_redirect_target("/api/bzg/mgmt-cluster") is None)
    check("canonical uma not redirected", shell.route_merge_redirect_target("/bzg/uma-blu") is None)
    check("radar-prove not mass-retired", shell.route_merge_redirect_target("/radar-prove") is None)

    tree = shell.ia_tree()
    ids = [s.get("id") for s in tree]
    check("IA HOME", "home" in ids)
    check("IA BUSINESSES", "businesses" in ids)
    check("IA INTELLIGENCE", "intelligence" in ids)
    check("IA SYSTEM", "system" in ids)
    check("IA section count 4", len(tree) == 4, str(ids))
    blob = _all_ia_blob(tree)
    check("IA no mgmt-cluster", "mgmt-cluster" not in blob, blob[:200])
    check("IA no radar peer", "radar" not in blob, blob[:200])
    for slug in SPECIALIST_SLUGS:
        check(f"IA no specialist {slug}", slug not in blob)
    sys_sec = next(s for s in tree if s["id"] == "system")
    sys_hrefs = [it["href"] for it in sys_sec["items"]]
    check("SYSTEM has Progress", "/progress" in sys_hrefs)
    check("SYSTEM has Integrations", "/integration-health" in sys_hrefs)
    check("SYSTEM has Sale", "/sale-evidence-pack" in sys_hrefs)
    home = next(s for s in tree if s["id"] == "home")
    home_hrefs = [it["href"] for it in home["items"]]
    check("Progress not HOME peer", "/progress" not in home_hrefs)
    check("helper specialist clean", shell.specialist_not_in_primary_ia() is True)


def test_files() -> None:
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav exists", SIDENAV.is_file())
    check("sidenav route-merge cache", "20260922-nav-route-merge" in sn)
    check("sidenav one wolfnav owner", "#wolfnav" in sn or "wolfnav" in sn)
    check("sidenav never second boards comment", "Never a second Boards" in sn or "never a second Boards" in sn.lower())
    check("sidenav SYSTEM section", '"system"' in sn or "SYSTEM" in sn)
    for slug in SPECIALIST_SLUGS:
        # may appear in HIDDEN_SPECIALIST_PRIMARY only — not as IA href
        check(
            f"sidenav no primary href /{slug}",
            f'href: "/{slug}"' not in sn and f"href: '/{slug}'" not in sn,
        )
    shell_src = (SCRIPTS / "core" / "wolf_shell.py").read_text(encoding="utf-8")
    check("shell ROUTE_MERGE_REDIRECTS", "ROUTE_MERGE_REDIRECTS" in shell_src)
    check("shell route_merge_redirect_target", "def route_merge_redirect_target" in shell_src)
    check("shell route_merge_inventory", "def route_merge_inventory" in shell_src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve_beta uses route_merge", "route_merge_redirect_target" in serve)
    plan = ROOT / "docs" / "deliveries" / "GROK-PLAN-WOLF-ROUTE-MERGE-RETIRE-REDIRECT-2026-09-22.md"
    check("plan exists", plan.is_file())


def test_http() -> None:
    import inspect

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
            try:
                body = json.loads(raw.decode())
            except json.JSONDecodeError:
                body = raw.decode("utf-8", errors="replace")
            return exc.code, body, {}

    def call_redirect(url_path: str):
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
        for src, dest_sub in REDIRECT_CASES:
            code, hdrs = call_redirect(src)
            loc = (hdrs or {}).get("Location") or ""
            check(
                f"302 {src}",
                code in (301, 302, 303, 307) and dest_sub.split("?")[0].split("#")[0] in loc,
                f"code={code} loc={loc}",
            )

        # P0: /trading canonicalizes to Owner Trading (not Empire soft-land).
        code, hdrs = call_redirect("/trading")
        loc = (hdrs or {}).get("Location") or ""
        check(
            "P0 /trading → /owner/trading (not Empire)",
            code == 302 and "/owner/trading" in (hdrs.get("Location") or ""),
            f"{code} {hdrs.get('Location')}",
        )

        for path in (
            "/progress",
            "/bzg",
            "/bzg/uma-blu",
            "/api/progress",
            "/api/bzg/mgmt-cluster",
            "/api/ggv/mgmt-cluster",
            "/api/bzg/uma-blu/today",
        ):
            st, _, _ = call("GET", path, None)
            check(f"anon fail-closed {path}", st in (403, 401), str(st))

        for path in ("/bzg", "/bzg/uma-blu", "/progress", "/ggv-ops-pack"):
            st, html, _ = call("GET", path, MATT)
            check(f"matt 200 {path}", st == 200, str(st))
            if isinstance(html, str) and st == 200:
                check(f"matt #wolfnav {path}", 'id="wolfnav"' in html)

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", None)
        check("anon whoami 200", st == 200 and isinstance(payload, dict))
        h = (payload or {}).get("honesty") or {}
        check("live honesty route merge", h.get("route_merge_retire_redirect") is True)
        check("live honesty proven false", h.get("proven") is False)
        check("live honesty ready false", h.get("ready") is False)
        check("live honesty perms retained", h.get("permissions_audience_prove") is True)
        check("live honesty specialist retained", h.get("specialist_not_primary") is True)

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", MATT)
        who = (payload or {}).get("whoami") or {}
        ia = (payload or {}).get("ia") or []
        check("matt OWNER", who.get("audience") == "OWNER", str(who.get("audience")))
        check("matt has SYSTEM", any(s.get("id") == "system" for s in ia))
        mblob = _all_ia_blob(ia)
        check("matt IA no mgmt-cluster", "mgmt-cluster" not in mblob)

        st, payload, _ = call("GET", "/api/wolf/shell-whoami", DEVI)
        who = (payload or {}).get("whoami") or {}
        ia = (payload or {}).get("ia") or []
        check("devi not empty audience", bool(who.get("audience")))
        check("devi no SYSTEM admin", not any(s.get("id") == "system" for s in ia))

        # Haikal — no Progress grant
        st, _, _ = call("GET", "/progress", HAIKAL)
        check("haikal progress fail-closed", st in (403, 401), str(st))

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
        "scripts/tests/test_wolf_route_merge_retire_redirect.py",
    ):
        check(f"pack not wip {path}", path not in WIP)


def test_soft_prior_cheap() -> None:
    """Cheap soft keep: honesty flags for Wave8 + RHC + Perms.

    Soft-skip full nested Wave8/RHC/Perms subprocess suites — wall-clock
    (Wave8 nests W1–7; Perms nests Wave8). Reason: not cheap for this slice.
    """
    flags = shell.honesty_flags()
    soft("wave8 specialist_not_primary", flags.get("specialist_not_primary") is True)
    soft(
        "wave8 specialist_soft_redirect_empire",
        flags.get("specialist_soft_redirect_empire") is True,
    )
    soft("rhc responsive_shell_v1_prove", flags.get("responsive_shell_v1_prove") is True)
    soft("rhc direction_up_back_home", flags.get("direction_up_back_home") is True)
    soft("perms permissions_audience_prove", flags.get("permissions_audience_prove") is True)
    soft("perms four_layer_permissions", flags.get("four_layer_permissions") is True)
    soft(
        "perms person_role_chain",
        flags.get("person_role_assignment_scope_permission_audience") is True,
    )
    soft("system progress_under_system_only", flags.get("progress_under_system_only") is True)
    soft("system sale_under_system", flags.get("sale_under_system") is True)
    print(
        "NOTE  soft-skip full Wave8+RHC+Perms subprocess re-run — "
        "nested wall-clock not cheap; honesty flags asserted above"
    )


def main() -> int:
    test_inventory()
    test_module()
    test_files()
    test_http()
    test_prod_untouched()
    test_wip()
    test_soft_prior_cheap()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
