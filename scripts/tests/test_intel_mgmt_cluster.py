#!/usr/bin/env python3
"""INTEL Learning Policy Management Cluster — compose approve-to-rule / ops / connective."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
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

from core import intel_mgmt_cluster as mc  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
HTML = ROOT / "dashboards" / "intel-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CR_05 = "CR-be51980bd1194448"
CR_AU = "CR-dca0ad62e1b0032e"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_module_honesty() -> None:
    flags = mc.honesty_flags()
    check("bound", flags["bound"] == "beta-intel-connect-safe")
    check("compose only", flags["compose_only"] is True and flags["additive_only"] is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no money", flags["money"] is None and flags["payment_executed"] is False)
    check("no production", flags["production"] is False and flags["production_mutate"] is False)
    check("no auto promote", flags["auto_promote"] is False)
    check("no auto execute", flags["auto_execute"] is False)
    check("no invent learning", flags["invented_learning"] is False)
    check("no invent adopted", flags["invented_adopted_rule"] is False)
    check("no invent performance", flags["invented_performance"] is False)
    check("no p4 reopen", flags["p4_reopened"] is False)
    check("no learning-policy-v1 relaunch", flags["learning_policy_v1_relaunched"] is False)
    check("no bzg reopen", flags["bzg_reopened"] is False)
    check("no ggv reopen", flags["ggv_reopened"] is False)
    check("no amg reopen", flags["amg_reopened"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 3)
    check("schema no money", schema["money_property"] is False)
    check("schema no auto promote", schema["auto_promote_property"] is False)
    try:
        mc.refuse_proven({})
        check("proven raises", False)
    except mc.MgmtClusterError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        mc.refuse_ready({})
        check("ready raises", False)
    except mc.MgmtClusterError as exc:
        check("ready refused", exc.code == "ready_refused")
    try:
        mc.refuse_money({})
        check("money raises", False)
    except mc.MgmtClusterError as exc:
        check("money refused", exc.code == "money_refused")
    try:
        mc.refuse_auto_promote({})
        check("promote raises", False)
    except mc.MgmtClusterError as exc:
        check("promote refused", exc.code == "auto_promote_refused")
    try:
        mc.refuse_auto_execute({})
        check("execute raises", False)
    except mc.MgmtClusterError as exc:
        check("execute refused", exc.code == "auto_execute_refused")
    try:
        mc.refuse_resolve({})
        check("resolve raises", False)
    except mc.MgmtClusterError as exc:
        check("resolve refused", exc.code == "resolve_refused")
    try:
        mc.require_actor(None)
        check("anon raises", False)
    except mc.MgmtClusterError as exc:
        check("anon forbidden", exc.code == "forbidden")
    try:
        mc.require_actor("PERS-STRANGER")
        check("outsider raises", False)
    except mc.MgmtClusterError as exc:
        check("outsider forbidden", exc.code == "forbidden")
    seat = mc.require_actor("PERS-MATT")
    check("matt seat", seat["seat"] == "owner")


def test_desk_compose() -> None:
    desk = mc.build_desk(verified_person_id="PERS-MATT")
    check("desk ok", desk.get("ok") is True)
    check("desk bound", desk.get("bound") == mc.BOUND)
    check("three modules", desk.get("module_count") == 3, str(desk.get("module_count")))
    check("no learning invent", desk.get("learning_proof") is None)
    check("no adopted invent", desk.get("adopted_rule") is None)
    check("no performance invent", desk.get("performance") is None)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in ("approve_to_rule", "ops_pack", "connective"):
        check(f"has {mid}", mid in mods)
    atr = mods["approve_to_rule"]["honesty_strip"]
    tags = atr.get("status_tags") or []
    check(
        "approve tags honest",
        any(t in tags for t in ("EMPTY", "UNWIRED", "WAITING_APPROVAL", "WAITING_DATA")),
        str(tags),
    )
    check("approve not live", atr.get("live") is False and atr.get("live_rule") is False)
    check("approve not invented", atr.get("invented") is False)
    check("approve next", bool((atr.get("next_action") or {}).get("label")))
    ops_strip = mods["ops_pack"]["honesty_strip"]
    check("ops not invented", ops_strip.get("invented") is False)
    check("ops distinct p4", (mods["ops_pack"].get("module_honesty") or {}).get("distinct_from_p4") is True)
    conn = mods["connective"]["honesty_strip"]
    check("connective p4 done", conn.get("p4_done") is True)
    check("connective not learning", conn.get("live_learning") is False)
    check(
        "connective not relaunch",
        (mods["connective"].get("module_honesty") or {}).get("learning_policy_v1_relaunched") is False,
    )
    check("primary next", isinstance(desk.get("primary_next"), dict) and bool(desk["primary_next"].get("label")))
    hand = desk.get("owner_empire_handoff") or {}
    check(
        "handoff class",
        hand.get("founder_dep_class") in {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"},
        str(hand.get("founder_dep_class")),
    )
    check("handoff no invent away", hand.get("invented_owner_control_away") is False)
    sr = desk.get("staff_ready") or {}
    check("staff_ready pack", sr.get("pack") == "intel_mgmt")
    check("staff lede human", "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""))
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("no auto promote action", (sr.get("exposed_actions") or {}).get("auto_promote") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    dist = desk.get("distinction") or {}
    check("distinction p4", "DONE" in (dist.get("p4_connective") or ""))
    check("distinction blocked", "BLOCKED" in (dist.get("learning_policy_v1") or ""))
    check("cap05 specified on desk", (desk.get("caps") or {}).get("CAP-INTEL-05", {}).get("maturity") == "SPECIFIED")

    strip = mc.module_strip("approve_to_rule", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip not live",
        (strip.get("module") or {}).get("honesty_strip", {}).get("live_rule") is False,
    )


def test_caps_crs_untouched() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("CAP-INTEL-01 BUILT", data["CAP-INTEL-01"][0] == "BUILT")
    check("CAP-INTEL-02 PROVEN", data["CAP-INTEL-02"][0] == "PROVEN")
    check("CAP-INTEL-03 PROVEN", data["CAP-INTEL-03"][0] == "PROVEN")
    check("CAP-INTEL-04 PROVEN", data["CAP-INTEL-04"][0] == "PROVEN")
    check("CAP-INTEL-05 SPECIFIED", data["CAP-INTEL-05"][0] == "SPECIFIED")
    check("ledger 77", len(data) == 77)
    check("no invent READY on 05", data["CAP-INTEL-05"][0] != "READY")
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        for cr in (CR_05, CR_AU):
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?", (cr,)
            ).fetchone()
            check(f"cr {cr} OPEN", row is not None and row[0] == "OPEN", str(row))
    finally:
        conn.close()


def test_html() -> None:
    check("html exists", HTML.is_file())
    text = HTML.read_text(encoding="utf-8")
    check("html phone width", "max-width: 440px" in text or "max-width:440px" in text)
    check("html api", "/api/intel/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent claim", "no invented" in text.lower() or "Not proven" in text or "no invented" in text)
    check("html p4 distinct", "P4" in text or "p4" in text.lower())
    check("html blocked distinct", "learning-policy-v1" in text)
    check("html no auto-promote", "No auto-promote" in text or "auto_promote=false" in text)


def test_wip_untouched() -> None:
    for rel in WIP:
        path = ROOT / rel
        check(f"wip exists {rel}", path.is_file())
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(ROOT),
        text=True,
    )
    for rel in WIP:
        check(f"wip not staged {rel}", rel not in staged)
    # Dirty GGV hasattr guards and AMG files must remain unstaged by this pack.
    check("ggv hasattr guards present", "hasattr(self, \"_ggv_mgmt_refuse_code\")" in (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8") or "hasattr(self, '_ggv_mgmt_refuse_code')" in (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8"))


def test_http() -> None:
    ra._ENV_LOADED = True
    import inspect
    import serve_beta as sb

    Handler = None
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

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(
            f"http://127.0.0.1:{port}{url_path}",
            headers=headers,
            method=method,
            data=data,
        )
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        for path in (
            "/api/intel/mgmt-cluster",
            "/api/intel/mgmt-cluster/modules",
            "/api/intel/mgmt-cluster/honesty",
            "/api/intel/mgmt-cluster/staff-ready",
            "/intel-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/intel/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt three mods", len(payload.get("modules") or []) == 3)
        check("matt no learning invent", payload.get("learning_proof") is None)
        check("matt cap05", (payload.get("caps") or {}).get("CAP-INTEL-05", {}).get("maturity") == "SPECIFIED")

        st, _ = call("GET", "/api/intel/mgmt-cluster", HAIKAL)
        check("haikal outsider 403", st == 403, str(st))

        st, _ = call("GET", "/api/intel/mgmt-cluster", DEVI)
        check("devi outsider 403", st == 403, str(st))

        st, _ = call("GET", "/api/intel/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/intel/mgmt-cluster/modules/approve_to_rule", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("approve strip not live", strip.get("live_rule") is False)

        st, page = call("GET", "/intel-mgmt-cluster", MATT)
        check(
            "page 200",
            st == 200
            and (
                isinstance(page, (bytes, bytearray))
                or isinstance(page, str)
                or (isinstance(page, dict) and "error" not in page)
            ),
            str(type(page)) + " " + str(st),
        )

        st, payload = call("POST", "/api/intel/mgmt-cluster/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/ready", MATT, {})
        check("ready refuse", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/money", MATT, {})
        check("money refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/auto_promote", MATT, {})
        check("auto_promote refuse", st == 405 and payload.get("error") == "auto_promote_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/auto_execute", MATT, {})
        check("auto_execute refuse", st == 405 and payload.get("error") == "auto_execute_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/resolve", MATT, {})
        check("resolve refuse", st == 405 and payload.get("error") == "resolve_refused", str(payload)[:120])
        st, payload = call("POST", "/api/intel/mgmt-cluster/production", MATT, {})
        check("production refuse", st == 405 and payload.get("error") == "production_refused", str(payload)[:120])
    finally:
        httpd.shutdown()


def test_ports() -> None:
    def up(port: int) -> bool:
        s = socket.socket()
        s.settimeout(1.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        finally:
            s.close()

    check("prod 8787 up", up(8787))
    check("beta 8788 up", up(8788))


def test_serve_wired() -> None:
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve import", "intel_mgmt_cluster" in serve)
    check("serve api route", "/api/intel/mgmt-cluster" in serve)
    check("serve page route", "/intel-mgmt-cluster" in serve)
    check("serve hasattr ggv preserved", "_ggv_mgmt_refuse_code" in serve and "hasattr" in serve)


def main() -> int:
    test_module_honesty()
    test_desk_compose()
    test_caps_crs_untouched()
    test_html()
    test_wip_untouched()
    test_serve_wired()
    test_http()
    test_ports()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
