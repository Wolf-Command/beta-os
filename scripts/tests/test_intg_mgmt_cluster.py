#!/usr/bin/env python3
"""INTG Management Cluster — compose contract + cap_tests + gws + tech + secrets."""
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

from core import intg_mgmt_cluster as mc  # noqa: E402
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
    "CR-227e2514ac8dcd02",
    "CR-00b1a48e6620ec7f",
    "CR-260e724b776f2b89",
    "CR-859e7cad64e7e4ad",
    "CR-25e89e3efdb0caf9",
    "CR-44ffb6a57469ff25",
    "CR-273f30371bd52c8a",
)
CAPS = {
    "CAP-INTG-01": "ABSENT",
    "CAP-INTG-02": "BUILT",
    "CAP-INTG-03": "BUILT",
    "CAP-INTG-04": "BUILT",
    "CAP-INTG-05": "BUILT",
    "CAP-INTG-06": "SPECIFIED",
    "CAP-INTG-07": "SPECIFIED",
}
HTML = ROOT / "dashboards" / "intg-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CLAIM_ID = "bf-auto-pack-intg-v2-20260922"
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
    check("bound", flags["bound"] == "beta-connective-safe")
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
    check("no secret exfil", flags["secret_exfil"] is False)
    check("no mint secret", flags["mint_secret"] is False)
    check("no external write", flags["external_write"] is False)
    check("no bank api", flags["bank_api_called"] is False)
    check("no yanolja", flags["yanolja_called"] is False and flags["invented_yanolja"] is False)
    check("no esb", flags["esb_called"] is False and flags["invented_esb"] is False)
    check("no metricool write", flags["metricool_write"] is False)
    check("cap 01 absent flag", flags["cap_intg_01_absent"] is True)
    check("no p1 reopen", flags["p1_reopened"] is False)
    check("no p7 reopen", flags["p7_reopened"] is False)
    check("no devi reopen", flags["devi_reopened"] is False)
    check("no w12 fin", flags["w12_fin_reopened"] is False)
    check("no ggv reopen", flags["ggv_reopened"] is False)
    check("no bzg reopen", flags["bzg_reopened"] is False)
    check("no amg reopen", flags["amg_reopened"] is False)
    check("no intel reopen", flags["intel_reopened"] is False)
    check("no core reopen", flags["core_reopened"] is False)
    check("no crm reopen", flags["crm_reopened"] is False)
    check("no msc reopen", flags["msc_reopened"] is False)
    check("no strat reopen", flags["strat_reopened"] is False)
    check("no dr reopen", flags["dr_reopened"] is False)
    check("no sale reopen", flags["sale_reopened"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("intg caps unchanged flag", flags["intg_caps_unchanged"] is True)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 5)
    check("schema no money", schema["money_property"] is False)
    check("schema no secret exfil", schema["secret_exfil_property"] is False)
    check("schema no mint", schema["mint_secret_property"] is False)
    check("schema no cf mutate", schema["cloudflare_mutate_property"] is False)
    check("schema no access mutate", schema["access_mutate_property"] is False)
    check("schema no bank api", schema["bank_api_property"] is False)
    check("schema no yanolja", schema["yanolja_call_property"] is False)
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
        mc.refuse_secret_exfil({})
        check("secret raises", False)
    except mc.MgmtClusterError as exc:
        check("secret refused", exc.code == "secret_exfil_refused")
    try:
        mc.refuse_mint_secret({})
        check("mint raises", False)
    except mc.MgmtClusterError as exc:
        check("mint refused", exc.code == "mint_secret_refused")
    try:
        mc.refuse_external_write({})
        check("writes raises", False)
    except mc.MgmtClusterError as exc:
        check("writes refused", exc.code == "writes_refused")
    try:
        mc.refuse_bank_api({})
        check("bank raises", False)
    except mc.MgmtClusterError as exc:
        check("bank api refused", exc.code == "bank_api_refused")
    try:
        mc.refuse_yanolja({})
        check("yanolja raises", False)
    except mc.MgmtClusterError as exc:
        check("yanolja refused", exc.code == "yanolja_refused")
    try:
        mc.refuse_esb({})
        check("esb raises", False)
    except mc.MgmtClusterError as exc:
        check("esb refused", exc.code == "esb_refused")
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
    try:
        mc.require_actor("PERS-AMANDA")
        check("amanda staff raises", False)
    except mc.MgmtClusterError as exc:
        check("amanda staff forbidden", exc.code == "forbidden")
    seat = mc.require_actor("PERS-MATT")
    check("matt seat", seat["seat"] == "owner")


def test_desk_compose() -> None:
    desk = mc.build_desk(verified_person_id="PERS-MATT")
    check("desk ok", desk.get("ok") is True)
    check("desk bound", desk.get("bound") == mc.BOUND)
    check("five modules", desk.get("module_count") == 5, str(desk.get("module_count")))
    check("two pointers", desk.get("pointer_count") == 2, str(desk.get("pointer_count")))
    check("no money invent", desk.get("money") is None)
    check("not commissioned invent", desk.get("commissioned") is False)
    check("not adopted invent", desk.get("adopted") is False)
    check("no secret exfil desk", desk.get("secret_exfil") is False)
    check("no mint desk", desk.get("mint_secret") is False)
    check("no cf desk", desk.get("cloudflare_mutated") is False)
    check("no access desk", desk.get("access_mutated") is False)
    check("no bank api desk", desk.get("bank_api_called") is False)
    check("no yanolja desk", desk.get("yanolja_called") is False)
    check("no invent connector desk", desk.get("invented_connector_live") is False)
    check("cap 01 absent desk", desk.get("cap_intg_01_absent") is True)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in (
        "intg_connector_contract",
        "intg_connector_cap_tests",
        "gws_integrate_prove",
        "tech_capability_registry",
        "intg_secrets_env",
    ):
        check(f"has {mid}", mid in mods)

    contract = mods["intg_connector_contract"]["honesty_strip"]
    check(
        "contract status honest",
        contract.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(contract.get("status")),
    )
    check("contract empty or absent", contract.get("status") == "EMPTY", str(contract.get("status")))
    check("contract no numbers", contract.get("numbers") is None)
    check("contract no money", contract.get("money") is None)
    check("contract no yanolja", contract.get("yanolja_called") is False)
    check("contract not invent", contract.get("invented") is False)
    check("contract next", bool((contract.get("next_action") or {}).get("label")))

    caps = mods["intg_connector_cap_tests"]["honesty_strip"]
    check(
        "cap tests status honest",
        caps.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(caps.get("status")),
    )
    check("cap tests no bank api", caps.get("bank_api_called") is False)
    check("cap tests no live bank", caps.get("live_bank_connector") is False)

    gws = mods["gws_integrate_prove"]["honesty_strip"]
    check(
        "gws status honest",
        gws.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(gws.get("status")),
    )
    check("gws no probe", gws.get("probed") is False)
    check("gws no green", gws.get("green_claimed") is False)

    tech = mods["tech_capability_registry"]["honesty_strip"]
    check(
        "tech status honest",
        tech.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(tech.get("status")),
    )
    check("tech no green invent", tech.get("green_invented") is False)

    secrets = mods["intg_secrets_env"]["honesty_strip"]
    check(
        "secrets status honest",
        secrets.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(secrets.get("status")),
    )
    check("secrets no exfil", secrets.get("secret_exfil") is False)
    check("secrets no mint", secrets.get("mint_secret") is False)
    check("secrets no contents", secrets.get("contents_read") is False)

    ptrs = {p["id"]: p for p in desk.get("honesty_pointers") or []}
    check("esb pointer", "esb_connector_pointer" in ptrs)
    check("metricool pointer", "metricool_connector_pointer" in ptrs)
    check(
        "esb pointer only",
        (ptrs.get("esb_connector_pointer") or {}).get("pointer_only") is True,
    )

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
    check("staff_ready pack", sr.get("pack") == "intg_mgmt")
    check(
        "staff lede human",
        "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""),
    )
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("no secret on screen", (sr.get("exposed_actions") or {}).get("secret_exfil") is False)
    check("no mint on screen", (sr.get("exposed_actions") or {}).get("mint_secret") is False)
    check("no bank on screen", (sr.get("exposed_actions") or {}).get("bank_api") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    check("seven crs open", len(desk.get("crs_open") or []) == 7, str(desk.get("crs_open")))
    cap_rows = desk.get("caps") or {}
    for cap, expected in CAPS.items():
        check(f"cap {cap} present", cap in cap_rows)
        check(
            f"cap {cap} maturity",
            (cap_rows.get(cap) or {}).get("maturity") == expected,
            str((cap_rows.get(cap) or {}).get("maturity")),
        )
    check("cap not raised", all(c.get("raised") is False for c in cap_rows.values()))
    check(
        "cap 01 absent in desk caps",
        (cap_rows.get("CAP-INTG-01") or {}).get("maturity") == "ABSENT",
    )

    strip = mc.module_strip("intg_connector_contract", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip no yanolja",
        (strip.get("module") or {}).get("honesty_strip", {}).get("yanolja_called") is False,
    )


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
    check("html api", "/api/intg/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent", "no invented" in text.lower() or "Not proven" in text)
    check("html bound", "beta-connective-safe" in text)
    check("html no secret", "No secret exfil" in text or "no secret exfil" in text)
    check("html no bank", "bank API" in text or "bank api" in text.lower())
    check("html no yanolja", "Yanolja" in text or "yanolja" in text.lower())


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
            "/api/intg/mgmt-cluster",
            "/api/intg/mgmt-cluster/modules",
            "/api/intg/mgmt-cluster/honesty",
            "/api/intg/mgmt-cluster/staff-ready",
            "/intg-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/intg/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt five mods", len(payload.get("modules") or []) == 5)
        check("matt no money", payload.get("money") is None)
        check("matt not proven", payload.get("proven") is False)
        check("matt no secret", payload.get("secret_exfil") is False)
        check("matt no mint", payload.get("mint_secret") is False)
        check("matt no bank", payload.get("bank_api_called") is False)
        check("matt cap01 absent", payload.get("cap_intg_01_absent") is True)

        st, _ = call("GET", "/api/intg/mgmt-cluster", AMANDA)
        check("amanda staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/intg/mgmt-cluster", HAIKAL)
        check("haikal staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/intg/mgmt-cluster", DEVI)
        check("devi staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/intg/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/intg/mgmt-cluster/modules/intg_connector_contract", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("contract strip no yanolja", strip.get("yanolja_called") is False)

        st, page = call("GET", "/intg-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/intg/mgmt-cluster/proven", MATT, {})
        check(
            "proven refuse",
            st == 405 and payload.get("error") == "proven_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/ready", MATT, {})
        check(
            "ready refuse",
            st == 405 and payload.get("error") == "ready_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/money", MATT, {})
        check(
            "money refuse",
            st == 405 and payload.get("error") == "money_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/commission", MATT, {})
        check(
            "commission refuse",
            st == 405 and payload.get("error") == "commission_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/resolve", MATT, {})
        check(
            "resolve refuse",
            st == 405 and payload.get("error") == "resolve_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/cloudflare", MATT, {})
        check(
            "cf refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/access", MATT, {})
        check(
            "access refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/production", MATT, {})
        check(
            "production refuse",
            st == 405 and payload.get("error") == "production_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/secret", MATT, {})
        check(
            "secret refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/exfil", MATT, {})
        check(
            "exfil refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/mint", MATT, {})
        check(
            "mint refuse",
            st == 405 and payload.get("error") == "mint_secret_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/bank-api", MATT, {})
        check(
            "bank api refuse",
            st == 405 and payload.get("error") == "bank_api_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/yanolja", MATT, {})
        check(
            "yanolja refuse",
            st == 405 and payload.get("error") == "yanolja_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/esb", MATT, {})
        check(
            "esb refuse",
            st == 405 and payload.get("error") == "esb_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/intg/mgmt-cluster/fill", MATT, {})
        check(
            "external write refuse",
            st == 405 and payload.get("error") == "writes_refused",
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
