#!/usr/bin/env python3
"""GGV Management Cluster V3 — wire compose desk on Beta :8788."""
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

from core import ggv_mgmt_cluster as mc  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
CRS = (
    "CR-6a19c9221cab0178",
    "CR-8c1fa12404180c02",
    "CR-ccb3287dabe91d4b",
    "CR-e20099e21930b9a6",
    "CR-f089b11530ab4673",
)
CAPS = {
    "CAP-GGV-01": "BUILT",
    "CAP-GGV-02": "READY",
    "CAP-GGV-03": "SPECIFIED",
    "CAP-GGV-04": "BUILT",
    "CAP-GGV-05": "BUILT",
    "CAP-GGV-06": "SPECIFIED",
}
HTML = ROOT / "dashboards" / "ggv-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CLAIM_ID = "bf-auto-pack-ggv-v3-20260922"
CLAIMS = ROOT / "state" / "build-claims" / "2026-09-22.json"
SERVE = ROOT / "scripts" / "serve_beta.py"


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
    check("bound", flags["bound"] == "beta-ggv-loop-safe")
    check("compose only", flags["compose_only"] is True and flags["additive_only"] is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no money", flags["money"] is None and flags["payment_executed"] is False)
    check("no production", flags["production"] is False and flags["production_mutate"] is False)
    check("no cf", flags["cloudflare_mutated"] is False and flags["access_mutated"] is False)
    check("no crm write", flags["crm_external_write"] is False and flags["metricool_write"] is False)
    check("no invent strategy", flags["invented_strategy_score"] is False)
    check("no invent pnl", flags["invented_client_pnl"] is False)
    check("no invent sla", flags["invented_sla"] is False)
    check("no invent social", flags["invented_social_metrics"] is False)
    check("no invent ic", flags["invented_intercompany"] is False)
    check("no false resolve", flags["false_resolve_cr"] is False and flags["cr_resolved"] is False)
    check("no p2 reopen", flags["p2_reopened"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("anon fail closed", flags["anon_fail_closed"] is True)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 5)
    check("schema no money", schema["money_property"] is False)
    check("schema no crm write", schema["crm_write_property"] is False)
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
        mc.refuse_resolve({})
        check("resolve raises", False)
    except mc.MgmtClusterError as exc:
        check("resolve refused", exc.code == "resolve_refused")
    try:
        mc.refuse_production({})
        check("production raises", False)
    except mc.MgmtClusterError as exc:
        check("production refused", exc.code == "production_refused")
    try:
        mc.refuse_cloudflare({})
        check("cf raises", False)
    except mc.MgmtClusterError as exc:
        check("cf refused", exc.code == "cloudflare_refused")
    try:
        mc.refuse_crm_write({})
        check("crm raises", False)
    except mc.MgmtClusterError as exc:
        check("crm refused", exc.code == "crm_write_refused")
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
    try:
        mc.require_actor("PERS-DEVI")
        check("devi raises", False)
    except mc.MgmtClusterError as exc:
        check("devi forbidden", exc.code == "forbidden")
    seat = mc.require_actor("PERS-MATT")
    check("matt seat", seat["seat"] == "owner")
    amanda = mc.require_actor("PERS-AMANDA")
    check("amanda seat", amanda["seat"] == "ops" and amanda["label"] == "Amanda")
    haikal = mc.require_actor("PERS-HAIKAL")
    check("haikal seat", haikal["seat"] == "ops")
    misa = mc.require_actor("PERS-MISA")
    check("misa seat", misa["seat"] == "ops")


def test_desk_compose() -> None:
    desk = mc.build_desk(verified_person_id="PERS-MATT")
    check("desk ok", desk.get("ok") is True)
    check("desk bound", desk.get("bound") == mc.BOUND)
    check("five modules", desk.get("module_count") == 5, str(desk.get("module_count")))
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in (
        "strategy_machine",
        "client_profitability",
        "speed_to_lead",
        "social_derive",
        "intercompany_client",
    ):
        check(f"has {mid}", mid in mods)
        strip = mods[mid]["honesty_strip"]
        check(f"{mid} no invent", strip.get("invented") is False)
        check(f"{mid} numbers null", strip.get("numbers") is None)
        check(f"{mid} next", bool((strip.get("next_action") or {}).get("label")))
    for mid in ("strategy_machine", "client_profitability", "intercompany_client"):
        strip = mods[mid]["honesty_strip"]
        tags = strip.get("status_tags") or []
        check(f"{mid} empty", strip.get("empty") is True)
        check(f"{mid} EMPTY tag", "EMPTY" in tags, str(tags))
    check("primary next", isinstance(desk.get("primary_next"), dict) and bool(desk["primary_next"].get("label")))
    hand = desk.get("owner_empire_handoff") or {}
    check(
        "handoff class",
        hand.get("founder_dep_class") in {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"},
        str(hand.get("founder_dep_class")),
    )
    check("handoff no invent away", hand.get("invented_owner_control_away") is False)
    sr = desk.get("staff_ready") or {}
    check("staff_ready pack", sr.get("pack") == "ggv_mgmt")
    check("staff lede human", "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""))
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    check("desk money null", desk.get("money") is None)

    strip = mc.module_strip("strategy_machine", verified_person_id="PERS-AMANDA")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip empty",
        (strip.get("module") or {}).get("honesty_strip", {}).get("empty") is True,
    )


def test_caps_crs_untouched() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger len 77", len(data) == 77, str(len(data)))
    for cap, mat in CAPS.items():
        check(f"ledger {cap}", data[cap][0] == mat, str(data[cap][0]))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        for cr in CRS:
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
    check("html api", "/api/ggv/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent claim", "not invented" in text.lower() or "no invented" in text.lower())


def test_handlers_wired() -> None:
    serve = SERVE.read_text(encoding="utf-8")
    for name in (
        "_ggv_mgmt_quiet",
        "_ggv_mgmt_refuse_code",
        "_ggv_mgmt_fail",
        "_ggv_mgmt_write_refused",
        "_ggv_mgmt_page",
        "_ggv_mgmt_get",
        "_require_ggv_mgmt_seat",
    ):
        check(f"handler {name}", f"def {name}" in serve)
    check("import ggv_mgmt", "ggv_mgmt_cluster as _ggv_mgmt" in serve)


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


def test_claim_present() -> None:
    check("claims file", CLAIMS.is_file())
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    ids = [c.get("id") for c in data.get("claims") or []]
    check("claim id present", CLAIM_ID in ids, str(ids[-3:]))


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
            "/api/ggv/mgmt-cluster",
            "/api/ggv/mgmt-cluster/modules",
            "/api/ggv/mgmt-cluster/honesty",
            "/api/ggv/mgmt-cluster/staff-ready",
            "/ggv-mgmt-cluster",
        ):
            st, payload = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))
            if isinstance(payload, dict):
                check(f"anon not 404 {path}", payload.get("error") != "not_wired")

        st, payload = call("GET", "/api/ggv/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt five mods", len(payload.get("modules") or []) == 5)
        check("matt empty strips", int(payload.get("empty_count") or 0) >= 3)

        st, payload = call("GET", "/api/ggv/mgmt-cluster", AMANDA)
        check("amanda desk 200", st == 200 and payload.get("ok") is True, str(st))
        who = ((payload.get("staff_ready") or {}).get("who_line") or "")
        check("amanda who human", "Amanda" in who and "PERS-" not in who, who)

        st, _ = call("GET", "/api/ggv/mgmt-cluster", HAIKAL)
        check("haikal desk 200", st == 200, str(st))
        st, _ = call("GET", "/api/ggv/mgmt-cluster", MISA)
        check("misa desk 200", st == 200, str(st))

        st, _ = call("GET", "/api/ggv/mgmt-cluster", DEVI)
        check("devi 403", st == 403, str(st))
        st, _ = call("GET", "/api/ggv/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/ggv/mgmt-cluster/modules/strategy_machine", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("strategy strip empty", strip.get("empty") is True and strip.get("numbers") is None)

        st, page = call("GET", "/ggv-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/ggv/mgmt-cluster/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/ready", MATT, {})
        check("ready refuse", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/money", MATT, {})
        check("money refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/resolve", MATT, {})
        check("resolve refuse", st == 405 and payload.get("error") == "resolve_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/production", MATT, {})
        check("production refuse", st == 405 and payload.get("error") == "production_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/cloudflare", MATT, {})
        check("cf refuse", st == 405 and payload.get("error") == "cloudflare_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/crm", MATT, {})
        check("crm refuse", st == 405 and payload.get("error") == "crm_write_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/metricool", MATT, {})
        check("metricool refuse", st == 405 and payload.get("error") == "crm_write_refused", str(payload)[:120])
        st, payload = call("POST", "/api/ggv/mgmt-cluster/access", MATT, {})
        check("access refuse", st == 405 and payload.get("error") == "cloudflare_refused", str(payload)[:120])
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


def main() -> int:
    test_module_honesty()
    test_desk_compose()
    test_caps_crs_untouched()
    test_html()
    test_handlers_wired()
    test_wip_untouched()
    test_claim_present()
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
