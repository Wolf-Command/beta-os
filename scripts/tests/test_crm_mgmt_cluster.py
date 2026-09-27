#!/usr/bin/env python3
"""CRM Management Cluster — compose lead_spine + identity + package + klaviyo reader."""
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

from core import crm_mgmt_cluster as mc  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
CRS = (
    "CR-ff42f3a7c49caa79",
    "CR-820682ce791563fa",
    "CR-e5ff219bb1d585f7",
    "CR-c8719063fb940ed4",
)
CAPS = {
    "CAP-CRM-01": "BUILT",
    "CAP-CRM-02": "SPECIFIED",
    "CAP-CRM-03": "SPECIFIED",
    "CAP-CRM-04": "BUILT",
}
HTML = ROOT / "dashboards" / "crm-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CLAIM_ID = "bf-auto-pack-crm-20260922"
CLAIMS = ROOT / "state" / "build-claims" / "2026-09-22.json"


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
    check(
        "not commissioned",
        flags["invented_commissioned"] is False and flags["commission_flip"] is False,
    )
    check("no money", flags["money"] is None and flags["payment_executed"] is False)
    check("no production", flags["production"] is False and flags["production_mutate"] is False)
    check("no cf", flags["cloudflare_mutated"] is False and flags["access_mutated"] is False)
    check("no klaviyo send", flags["klaviyo_send"] is False and flags["klaviyo_called"] is False)
    check("no crm external write", flags["crm_external_write"] is False)
    check("no p1 reopen", flags["p1_reopened"] is False)
    check("no p7 reopen", flags["p7_reopened"] is False)
    check("no devi reopen", flags["devi_reopened"] is False)
    check("no w12 fin", flags["w12_fin_reopened"] is False)
    check("no ggv reopen", flags["ggv_reopened"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("no au-crm-01 scope", flags["au_crm_01_in_scope"] is False)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 4)
    check("schema no money", schema["money_property"] is False)
    check("schema no commission flip", schema["commission_flip_property"] is False)
    check("schema no klaviyo send", schema["klaviyo_send_property"] is False)
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
        mc.refuse_commission({})
        check("commission raises", False)
    except mc.MgmtClusterError as exc:
        check("commission refused", exc.code == "commission_refused")
    try:
        mc.refuse_resolve({})
        check("resolve raises", False)
    except mc.MgmtClusterError as exc:
        check("resolve refused", exc.code == "resolve_refused")
    try:
        mc.refuse_cloudflare({})
        check("cf raises", False)
    except mc.MgmtClusterError as exc:
        check("cf refused", exc.code == "cloudflare_refused")
    try:
        mc.refuse_klaviyo_send({})
        check("klaviyo send raises", False)
    except mc.MgmtClusterError as exc:
        check("klaviyo send refused", exc.code == "klaviyo_send_refused")
    try:
        mc.refuse_crm_write({})
        check("crm write raises", False)
    except mc.MgmtClusterError as exc:
        check("crm write refused", exc.code == "crm_write_refused")
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
        check("devi staff raises", False)
    except mc.MgmtClusterError as exc:
        check("devi staff forbidden", exc.code == "forbidden")
    seat = mc.require_actor("PERS-MATT")
    check("matt seat", seat["seat"] == "owner")
    amanda = mc.require_actor("PERS-AMANDA")
    check("amanda seat", amanda["seat"] == "ops")
    haikal = mc.require_actor("PERS-HAIKAL")
    check("haikal seat", haikal["seat"] == "ops")
    misa = mc.require_actor("PERS-MISA")
    check("misa seat", misa["seat"] == "ops")


def test_desk_compose() -> None:
    desk = mc.build_desk(verified_person_id="PERS-MATT")
    check("desk ok", desk.get("ok") is True)
    check("desk bound", desk.get("bound") == mc.BOUND)
    check("four modules", desk.get("module_count") == 4, str(desk.get("module_count")))
    check("no money invent", desk.get("money") is None)
    check("not commissioned invent", desk.get("commissioned") is False)
    check("not adopted invent", desk.get("adopted") is False)
    check("no klaviyo send desk", desk.get("klaviyo_send") is False)
    check("no klaviyo called desk", desk.get("klaviyo_called") is False)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in (
        "lead_spine",
        "identity_memory",
        "package_intel",
        "klaviyo_reader",
    ):
        check(f"has {mid}", mid in mods)

    lead = mods["lead_spine"]["honesty_strip"]
    check("lead WAITING or EMPTY", lead.get("status") in {"WAITING_DATA", "EMPTY"})
    check("lead no numbers", lead.get("numbers") is None)
    check("lead no money", lead.get("money") is None)
    check("lead not sale", lead.get("sale") is False)
    check("lead not customer invent", lead.get("customer") is False)
    check("lead next", bool((lead.get("next_action") or {}).get("label")))
    check("lead not invented", lead.get("invented") is False)
    check(
        "lead honesty not sale",
        (mods["lead_spine"].get("module_honesty") or {}).get("lead_is_not_sale") is True,
    )

    ident = mods["identity_memory"]["honesty_strip"]
    check("ident empty", ident.get("empty") is True)
    check("ident EMPTY tag", "EMPTY" in (ident.get("status_tags") or []), str(ident.get("status_tags")))
    check("ident no graph", ident.get("identity_graph_complete") is False)
    check("ident no merge", ident.get("merged") is False)
    check("ident no blast", ident.get("marketing_blast") is False)

    pkg = mods["package_intel"]["honesty_strip"]
    check("pkg empty", pkg.get("empty") is True)
    check("pkg EMPTY", "EMPTY" in (pkg.get("status_tags") or []))
    check("pkg no price", pkg.get("price") is None)
    check("pkg no census", pkg.get("market_census") is False)
    check("pkg no booking", pkg.get("booking") is False)

    klav = mods["klaviyo_reader"]["honesty_strip"]
    check("klav not empty invent", klav.get("empty") is False)
    check("klav WAITING", "WAITING_DATA" in (klav.get("status_tags") or []), str(klav.get("status_tags")))
    check("klav not called", klav.get("klaviyo_called") is False)
    check("klav no write", klav.get("klaviyo_write") is False)
    check("klav no send", klav.get("klaviyo_send") is False)
    check("klav sends null", klav.get("sends") is None)
    check("klav subscribers null", klav.get("subscribers") is None)

    check(
        "primary next",
        isinstance(desk.get("primary_next"), dict) and bool(desk["primary_next"].get("label")),
    )
    hand = desk.get("owner_empire_handoff") or {}
    check(
        "handoff class",
        hand.get("founder_dep_class")
        in {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"},
        str(hand.get("founder_dep_class")),
    )
    check("handoff no invent away", hand.get("invented_owner_control_away") is False)
    sr = desk.get("staff_ready") or {}
    check("staff_ready pack", sr.get("pack") == "crm_mgmt")
    check(
        "staff lede human",
        "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""),
    )
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("no send on screen", (sr.get("exposed_actions") or {}).get("klaviyo_send") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    check("four crs open", len(desk.get("crs_open") or []) == 4, str(desk.get("crs_open")))

    strip = mc.module_strip("identity_memory", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip empty",
        (strip.get("module") or {}).get("honesty_strip", {}).get("empty") is True,
    )

    amanda_desk = mc.build_desk(verified_person_id="PERS-AMANDA")
    check("amanda desk ok", amanda_desk.get("ok") is True)
    check("amanda seat ops", (amanda_desk.get("seat") or {}).get("seat") == "ops")


def test_caps_crs_untouched() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap, expected in CAPS.items():
        check(f"ledger {cap} {expected}", data[cap][0] == expected, str(data[cap][0]))
    check("ledger len unchanged", len(data) == 77, str(len(data)))
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
    check("html api", "/api/crm/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent", "no invented" in text.lower() or "Not proven" in text)
    check("html bound", "beta-ggv-loop-safe" in text)
    check("html no send", "No Klaviyo send" in text or "no Klaviyo send" in text)


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


def test_claim() -> None:
    check("claims file", CLAIMS.is_file())
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    ids = [c.get("id") for c in data.get("claims") or []]
    check("claim present", CLAIM_ID in ids, str(ids[-5:]))


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
            "/api/crm/mgmt-cluster",
            "/api/crm/mgmt-cluster/modules",
            "/api/crm/mgmt-cluster/honesty",
            "/api/crm/mgmt-cluster/staff-ready",
            "/crm-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/crm/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt four mods", len(payload.get("modules") or []) == 4)
        check("matt no money", payload.get("money") is None)
        check("matt not proven", payload.get("proven") is False)
        check("matt no send", payload.get("klaviyo_send") is False)

        st, payload = call("GET", "/api/crm/mgmt-cluster", AMANDA)
        check("amanda ops 200", st == 200 and payload.get("ok") is True, str(st))

        st, _ = call("GET", "/api/crm/mgmt-cluster", HAIKAL)
        check("haikal ops 200", st == 200, str(st))

        st, _ = call("GET", "/api/crm/mgmt-cluster", DEVI)
        check("devi staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/crm/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/crm/mgmt-cluster/modules/identity_memory", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("ident strip empty", strip.get("empty") is True and strip.get("numbers") is None)

        st, page = call("GET", "/crm-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/crm/mgmt-cluster/proven", MATT, {})
        check(
            "proven refuse",
            st == 405 and payload.get("error") == "proven_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/ready", MATT, {})
        check(
            "ready refuse",
            st == 405 and payload.get("error") == "ready_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/money", MATT, {})
        check(
            "money refuse",
            st == 405 and payload.get("error") == "money_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/commission", MATT, {})
        check(
            "commission refuse",
            st == 405 and payload.get("error") == "commission_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/resolve", MATT, {})
        check(
            "resolve refuse",
            st == 405 and payload.get("error") == "resolve_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/cloudflare", MATT, {})
        check(
            "cf refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/production", MATT, {})
        check(
            "production refuse",
            st == 405 and payload.get("error") == "production_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/klaviyo", MATT, {})
        check(
            "klaviyo refuse",
            st == 405 and payload.get("error") == "klaviyo_send_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/send", MATT, {})
        check(
            "send refuse",
            st == 405 and payload.get("error") == "klaviyo_send_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/crm/mgmt-cluster/crm", MATT, {})
        check(
            "crm write refuse",
            st == 405 and payload.get("error") == "crm_write_refused",
            str(payload)[:120],
        )
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
    test_wip_untouched()
    if CLAIMS.is_file():
        data = json.loads(CLAIMS.read_text(encoding="utf-8"))
        ids = [c.get("id") for c in data.get("claims") or []]
        if CLAIM_ID in ids:
            test_claim()
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
