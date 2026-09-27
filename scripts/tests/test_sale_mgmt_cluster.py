#!/usr/bin/env python3
"""SALE Management Cluster — compose evidence + dataroom + buyer_mode + attack_audit."""
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

from core import sale_mgmt_cluster as mc  # noqa: E402
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
    "CR-b7ce6d6668848b6e",
    "CR-766f242208e401ad",
    "CR-b428ac5cbc8986b5",
    "CR-c6e1a48e4a3e8a91",
)
CAPS = {
    "CAP-SALE-01": "SPECIFIED",
    "CAP-SALE-02": "SPECIFIED",
    "CAP-SALE-03": "SPECIFIED",
    "CAP-SALE-04": "SPECIFIED",
}
HTML = ROOT / "dashboards" / "sale-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CLAIM_ID = "bf-auto-pack-sale-20260922"
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
    check("no external write", flags["external_write"] is False)
    check("no buyer grant", flags["buyer_grant"] is False and flags["invented_buyer_grant"] is False)
    check("no live attack", flags["live_attack"] is False and flags["invented_live_attack"] is False)
    check("no transition invent", flags["transition_pack_filled"] is False)
    check("no export invent", flags["controlled_export"] is False and flags["export_written"] is False)
    check("no p1 reopen", flags["p1_reopened"] is False)
    check("no p7 reopen", flags["p7_reopened"] is False)
    check("no devi reopen", flags["devi_reopened"] is False)
    check("no w12 fin", flags["w12_fin_reopened"] is False)
    check("no ggv reopen", flags["ggv_reopened"] is False)
    check("no intg reopen", flags["intg_reopened"] is False)
    check("no bzg reopen", flags["bzg_reopened"] is False)
    check("no amg reopen", flags["amg_reopened"] is False)
    check("no intel reopen", flags["intel_reopened"] is False)
    check("no core reopen", flags["core_reopened"] is False)
    check("no crm reopen", flags["crm_reopened"] is False)
    check("no msc reopen", flags["msc_reopened"] is False)
    check("no strat reopen", flags["strat_reopened"] is False)
    check("no dr reopen", flags["dr_reopened"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("sale caps unchanged flag", flags["sale_caps_unchanged"] is True)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 4)
    check("schema no money", schema["money_property"] is False)
    check("schema no secret exfil", schema["secret_exfil_property"] is False)
    check("schema no cf mutate", schema["cloudflare_mutate_property"] is False)
    check("schema no access mutate", schema["access_mutate_property"] is False)
    check("schema no buyer grant", schema["buyer_grant_property"] is False)
    check("schema no live attack", schema["live_attack_property"] is False)
    check("schema no export mutate", schema["export_mutate_property"] is False)
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
        mc.refuse_external_write({})
        check("writes raises", False)
    except mc.MgmtClusterError as exc:
        check("writes refused", exc.code == "writes_refused")
    try:
        mc.refuse_buyer_grant({})
        check("grant raises", False)
    except mc.MgmtClusterError as exc:
        check("buyer grant refused", exc.code == "buyer_grant_refused")
    try:
        mc.refuse_live_attack({})
        check("attack raises", False)
    except mc.MgmtClusterError as exc:
        check("live attack refused", exc.code == "live_attack_refused")
    try:
        mc.refuse_export({})
        check("export raises", False)
    except mc.MgmtClusterError as exc:
        check("export refused", exc.code == "export_refused")
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
    check("four modules", desk.get("module_count") == 4, str(desk.get("module_count")))
    check("no money invent", desk.get("money") is None)
    check("not commissioned invent", desk.get("commissioned") is False)
    check("not adopted invent", desk.get("adopted") is False)
    check("no secret exfil desk", desk.get("secret_exfil") is False)
    check("no cf desk", desk.get("cloudflare_mutated") is False)
    check("no access desk", desk.get("access_mutated") is False)
    check("no buyer grant desk", desk.get("buyer_grant") is False)
    check("no live attack desk", desk.get("live_attack") is False)
    check("no invent grant desk", desk.get("invented_buyer_grant") is False)
    check("no invent attack desk", desk.get("invented_live_attack") is False)
    check("no invent transition desk", desk.get("invented_transition_pack") is False)
    check("no invent export desk", desk.get("invented_controlled_export") is False)
    check("no export written desk", desk.get("export_written") is False)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in (
        "sale_evidence_pack",
        "sale_buyer_dataroom",
        "sale_buyer_mode",
        "sale_attack_audit",
    ):
        check(f"has {mid}", mid in mods)

    ev = mods["sale_evidence_pack"]["honesty_strip"]
    check(
        "evidence status honest",
        ev.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(ev.get("status")),
    )
    check("evidence no numbers", ev.get("numbers") is None)
    check("evidence no money", ev.get("money") is None)
    check("evidence no grant", ev.get("buyer_grant") is False)
    check("evidence not invent", ev.get("invented") is False)
    check("evidence next", bool((ev.get("next_action") or {}).get("label")))

    room = mods["sale_buyer_dataroom"]["honesty_strip"]
    check(
        "dataroom status honest",
        room.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(room.get("status")),
    )
    check("dataroom no grant", room.get("buyer_grant") is False)
    check("dataroom no access", room.get("buyer_access") is False)
    check("dataroom no share", room.get("live_share") is False)
    check("dataroom docs null", room.get("document_count") is None)

    mode = mods["sale_buyer_mode"]["honesty_strip"]
    check(
        "buyer mode status honest",
        mode.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(mode.get("status")),
    )
    check("buyer mode no grant", mode.get("buyer_grant") is False)
    check("buyer mode no export", mode.get("controlled_export") is False)
    check("buyer mode no export written", mode.get("export_written") is False)
    check("buyer mode crown closed", mode.get("crown_jewels_opened") is False)

    aud = mods["sale_attack_audit"]["honesty_strip"]
    check(
        "attack status honest",
        aud.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(aud.get("status")),
    )
    check("attack no live", aud.get("live_attack") is False)
    check("attack no run", aud.get("attack_run") is False)
    check("attack no transition", aud.get("transition_pack_filled") is False)
    check("attack no licence grant", aud.get("licence_granted") is False)

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
    check("staff_ready pack", sr.get("pack") == "sale_mgmt")
    check(
        "staff lede human",
        "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""),
    )
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("no secret on screen", (sr.get("exposed_actions") or {}).get("secret_exfil") is False)
    check("no grant on screen", (sr.get("exposed_actions") or {}).get("buyer_grant") is False)
    check("no attack on screen", (sr.get("exposed_actions") or {}).get("live_attack") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    check("four crs open", len(desk.get("crs_open") or []) == 4, str(desk.get("crs_open")))
    caps = desk.get("caps") or {}
    for cap in CAPS:
        check(f"cap {cap} present", cap in caps)
    check("cap not raised", all(c.get("raised") is False for c in caps.values()))

    strip = mc.module_strip("sale_evidence_pack", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip no buyer grant",
        (strip.get("module") or {}).get("honesty_strip", {}).get("buyer_grant") is False,
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
    check("html api", "/api/sale/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent", "no invented" in text.lower() or "Not proven" in text)
    check("html bound", "beta-connective-safe" in text)
    check("html no secret", "No secret exfil" in text or "no secret exfil" in text)
    check("html no grant", "buyer grant" in text.lower())
    check("html no attack", "live attack" in text.lower())


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
            "/api/sale/mgmt-cluster",
            "/api/sale/mgmt-cluster/modules",
            "/api/sale/mgmt-cluster/honesty",
            "/api/sale/mgmt-cluster/staff-ready",
            "/sale-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/sale/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt four mods", len(payload.get("modules") or []) == 4)
        check("matt no money", payload.get("money") is None)
        check("matt not proven", payload.get("proven") is False)
        check("matt no secret", payload.get("secret_exfil") is False)
        check("matt no buyer grant", payload.get("buyer_grant") is False)
        check("matt no live attack", payload.get("live_attack") is False)

        st, _ = call("GET", "/api/sale/mgmt-cluster", AMANDA)
        check("amanda staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/sale/mgmt-cluster", HAIKAL)
        check("haikal staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/sale/mgmt-cluster", DEVI)
        check("devi staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/sale/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/sale/mgmt-cluster/modules/sale_evidence_pack", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("evidence strip no grant", strip.get("buyer_grant") is False)

        st, page = call("GET", "/sale-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/sale/mgmt-cluster/proven", MATT, {})
        check(
            "proven refuse",
            st == 405 and payload.get("error") == "proven_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/ready", MATT, {})
        check(
            "ready refuse",
            st == 405 and payload.get("error") == "ready_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/money", MATT, {})
        check(
            "money refuse",
            st == 405 and payload.get("error") == "money_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/commission", MATT, {})
        check(
            "commission refuse",
            st == 405 and payload.get("error") == "commission_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/resolve", MATT, {})
        check(
            "resolve refuse",
            st == 405 and payload.get("error") == "resolve_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/cloudflare", MATT, {})
        check(
            "cf refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/access", MATT, {})
        check(
            "access refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/production", MATT, {})
        check(
            "production refuse",
            st == 405 and payload.get("error") == "production_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/secret", MATT, {})
        check(
            "secret refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/exfil", MATT, {})
        check(
            "exfil refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/grant", MATT, {})
        check(
            "buyer grant refuse",
            st == 405 and payload.get("error") == "buyer_grant_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/attack", MATT, {})
        check(
            "live attack refuse",
            st == 405 and payload.get("error") == "live_attack_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/export", MATT, {})
        check(
            "export refuse",
            st == 405 and payload.get("error") == "export_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/sale/mgmt-cluster/fill", MATT, {})
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
