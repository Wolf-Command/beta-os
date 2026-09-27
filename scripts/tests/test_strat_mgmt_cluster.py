#!/usr/bin/env python3
"""STRAT Management Cluster — compose 12wy prove + radar prove."""
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

from core import request_auth as ra  # noqa: E402
from core import strat_mgmt_cluster as mc  # noqa: E402

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
    "CR-6535f7cb02370850",
    "CR-7a145ad69d8bf3c5",
)
AU_CRS = (
    "CR-d6c1c6769b441944",
    "CR-df9f073e3c32ac6d",
)
CAPS = {
    "CAP-STRAT-01": "BUILT",
    "CAP-STRAT-02": "BUILT",
}
AUS = (
    "AU-STRAT-01-GGV",
    "AU-STRAT-02-OWNER",
)
HTML = ROOT / "dashboards" / "strat-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
ADOPTION = ROOT / "state" / "model-e-au-discovery.json"
CLAIM_ID = "bf-auto-pack-strat-20260922"
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
    check("bound", flags["bound"] == "beta-owner-safe")
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
    check("no invented mission", flags["invented_mission_scores"] is False)
    check("no invented au", flags["invented_au_adoption"] is False)
    check("aus not started flag", flags["aus_not_started"] is True)
    check("au started false", flags["au_started"] is False)
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
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("strat caps unchanged flag", flags["strat_caps_unchanged"] is True)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 2)
    check("schema no money", schema["money_property"] is False)
    check("schema no secret exfil", schema["secret_exfil_property"] is False)
    check("schema no cf mutate", schema["cloudflare_mutate_property"] is False)
    check("schema no access mutate", schema["access_mutate_property"] is False)
    check("schema no mission score", schema["mission_score_property"] is False)
    check("schema no au adoption", schema["au_adoption_property"] is False)
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
    check("two modules", desk.get("module_count") == 2, str(desk.get("module_count")))
    check("no money invent", desk.get("money") is None)
    check("not commissioned invent", desk.get("commissioned") is False)
    check("not adopted invent", desk.get("adopted") is False)
    check("no secret exfil desk", desk.get("secret_exfil") is False)
    check("no cf desk", desk.get("cloudflare_mutated") is False)
    check("no access desk", desk.get("access_mutated") is False)
    check("no mission invent", desk.get("invented_mission_scores") is False)
    check("no au invent", desk.get("invented_au_adoption") is False)
    check("mission scores null", desk.get("mission_scores") is None)
    check("pulse null", desk.get("pulse_count") is None)
    check("exception null", desk.get("exception_count") is None)
    check("aus not started desk", desk.get("aus_not_started") is True)
    check("au started desk false", desk.get("au_started") is False)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in ("strat_12wy_prove", "strat_radar_prove"):
        check(f"has {mid}", mid in mods)

    wy = mods["strat_12wy_prove"]["honesty_strip"]
    check(
        "12wy status honest",
        wy.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(wy.get("status")),
    )
    check("12wy no numbers", wy.get("numbers") is None)
    check("12wy no money", wy.get("money") is None)
    check("12wy percent null", wy.get("percent") is None)
    check("12wy empty not zero", wy.get("empty_is_not_zero") is True)
    check("12wy not invent", wy.get("invented") is False)
    check("12wy no mission invent", wy.get("invented_mission_scores") is False)
    check("12wy next", bool((wy.get("next_action") or {}).get("label")))

    rad = mods["strat_radar_prove"]["honesty_strip"]
    check(
        "radar status honest",
        rad.get("status") in {"WAITING_DATA", "EMPTY", "UNWIRED"},
        str(rad.get("status")),
    )
    check("radar empty tags or waiting", bool(rad.get("status_tags")))
    check("radar no pulse count", rad.get("pulse_count") is None)
    check("radar no exception count", rad.get("exception_count") is None)
    check("radar no invent pulse", rad.get("invented_pulse") is False)
    check("radar no invent au", rad.get("invented_au_adoption") is False)
    check("radar au not started", rad.get("au_started") is False)

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
    check("staff_ready pack", sr.get("pack") == "strat_mgmt")
    check(
        "staff lede human",
        "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""),
    )
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("no secret on screen", (sr.get("exposed_actions") or {}).get("secret_exfil") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)
    check("two crs open", len(desk.get("crs_open") or []) == 2, str(desk.get("crs_open")))

    aus = desk.get("aus") or {}
    for au_id in AUS:
        row = aus.get(au_id) or {}
        check(f"au {au_id} not started", row.get("started") is False)
        check(f"au {au_id} not adopted", row.get("adopted") is False)
        check(f"au {au_id} out of scope", row.get("in_scope") is False)

    strip = mc.module_strip("strat_radar_prove", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip no pulse invent",
        (strip.get("module") or {}).get("honesty_strip", {}).get("pulse_count") is None,
    )


def test_caps_crs_aus_untouched() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap, expected in CAPS.items():
        check(f"ledger {cap} {expected}", data[cap][0] == expected, str(data[cap][0]))
    check("ledger len unchanged", len(data) == 77, str(len(data)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        for cr in CRS + AU_CRS:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?", (cr,)
            ).fetchone()
            check(f"cr {cr} OPEN", row is not None and row[0] == "OPEN", str(row))
    finally:
        conn.close()
    adoption = json.loads(ADOPTION.read_text(encoding="utf-8"))
    rows = adoption if isinstance(adoption, list) else None
    if not isinstance(rows, list) and isinstance(adoption, dict):
        for value in adoption.values():
            if isinstance(value, list):
                rows = value
                break
    by_id = {
        row.get("au_id"): row
        for row in (rows or [])
        if isinstance(row, dict) and row.get("au_id")
    }
    for au_id in AUS:
        state = str((by_id.get(au_id) or {}).get("state") or "")
        check(
            f"au file {au_id} NOT STARTED",
            state.upper() in {"NOT STARTED", "NOT_STARTED"},
            state,
        )


def test_html() -> None:
    check("html exists", HTML.is_file())
    text = HTML.read_text(encoding="utf-8")
    check("html phone width", "max-width: 440px" in text or "max-width:440px" in text)
    check("html api", "/api/strat/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent", "no invented" in text.lower() or "Not proven" in text)
    check("html bound", "beta-owner-safe" in text)
    check("html no secret", "No secret exfil" in text or "no secret exfil" in text)
    check("html aus", "NOT STARTED" in text)


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
            "/api/strat/mgmt-cluster",
            "/api/strat/mgmt-cluster/modules",
            "/api/strat/mgmt-cluster/honesty",
            "/api/strat/mgmt-cluster/staff-ready",
            "/strat-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/strat/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt two mods", len(payload.get("modules") or []) == 2)
        check("matt no money", payload.get("money") is None)
        check("matt not proven", payload.get("proven") is False)
        check("matt no secret", payload.get("secret_exfil") is False)
        check("matt aus not started", payload.get("aus_not_started") is True)

        st, _ = call("GET", "/api/strat/mgmt-cluster", AMANDA)
        check("amanda staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/strat/mgmt-cluster", HAIKAL)
        check("haikal staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/strat/mgmt-cluster", DEVI)
        check("devi staff 403", st == 403, str(st))

        st, _ = call("GET", "/api/strat/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/strat/mgmt-cluster/modules/strat_12wy_prove", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("12wy strip percent null", strip.get("percent") is None)

        st, page = call("GET", "/strat-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/strat/mgmt-cluster/proven", MATT, {})
        check(
            "proven refuse",
            st == 405 and payload.get("error") == "proven_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/ready", MATT, {})
        check(
            "ready refuse",
            st == 405 and payload.get("error") == "ready_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/money", MATT, {})
        check(
            "money refuse",
            st == 405 and payload.get("error") == "money_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/commission", MATT, {})
        check(
            "commission refuse",
            st == 405 and payload.get("error") == "commission_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/resolve", MATT, {})
        check(
            "resolve refuse",
            st == 405 and payload.get("error") == "resolve_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/cloudflare", MATT, {})
        check(
            "cf refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/access", MATT, {})
        check(
            "access refuse",
            st == 405 and payload.get("error") == "cloudflare_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/production", MATT, {})
        check(
            "production refuse",
            st == 405 and payload.get("error") == "production_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/secret", MATT, {})
        check(
            "secret refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/exfil", MATT, {})
        check(
            "exfil refuse",
            st == 405 and payload.get("error") == "secret_exfil_refused",
            str(payload)[:120],
        )
        st, payload = call("POST", "/api/strat/mgmt-cluster/fill", MATT, {})
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
    test_caps_crs_aus_untouched()
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
