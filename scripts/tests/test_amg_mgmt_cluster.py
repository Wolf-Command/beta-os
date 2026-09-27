#!/usr/bin/env python3
"""AMG Management Cluster — compose six AMG capability modules (distinct from P3 day-loop)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
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

from core import amg_mgmt_cluster as mc  # noqa: E402
from core import amg_ops_pack as ops  # noqa: E402
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
CRS = (
    "CR-29c6ac36a9ca03f1",
    "CR-49f6461020b693fc",
    "CR-bc5785d66c981fd4",
    "CR-ce127471ba41692b",
    "CR-d212cdefaef81166",
    "CR-e9b3d23e63c1c8a7",
)
CAPS = (
    "CAP-AMG-01",
    "CAP-AMG-02",
    "CAP-AMG-04",
    "CAP-AMG-05",
    "CAP-AMG-06",
    "CAP-AMG-07",
)
HTML = ROOT / "dashboards" / "amg-mgmt-cluster.html"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _arm_hotel_ops(catalog: Path) -> None:
    conn = sqlite3.connect(str(catalog))
    try:
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (
              'POS-AMG-MGMT-TEST', 'ROLE-MATT', 'ENT-AMG', 'LOC-ATRIUM-LOMBOK', 'AMG-ATR', NULL,
              'Hotel mgmt cluster test', 'ACTIVE', 1.0, '2026-09-22T00:00:00+08:00', '2026-09-22T00:00:00+08:00'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
            ) VALUES (
              'ASG-AMG-MGMT-MISA', 'PERS-MISA', 'POS-AMG-MGMT-TEST', '2026-09-22T00:00:00+08:00', NULL,
              'ACTIVE', 1, '2026-09-22T00:00:00+08:00', '2026-09-22T00:00:00+08:00'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_module_honesty() -> None:
    flags = mc.honesty_flags()
    check("bound", flags["bound"] == "beta-amg-day-safe")
    check("compose only", flags["compose_only"] is True and flags["additive_only"] is True)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no money", flags["money"] is None and flags["payment_executed"] is False)
    check("no production", flags["production"] is False and flags["production_mutate"] is False)
    check("no p3 reopen", flags["p3_reopened"] is False)
    check("no day loop rewrite", flags["day_loop_rewritten"] is False)
    check("no ggv touch", flags["ggv_touched"] is False)
    check("no bzg touch", flags["bzg_touched"] is False)
    check("no wip touch", flags["wip_quartet_touched"] is False)
    check("no invent hotel", flags["invented_hotel_facts"] is False)
    check("no yanolja write", flags["yanolja_write"] is False)
    schema = mc.schema_document()
    check("schema modules", len(schema["modules"]) == 6)
    check("schema no money", schema["money_property"] is False)
    check("schema no yanolja write", schema["yanolja_write_property"] is False)
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
        mc.refuse_yanolja({})
        check("yanolja raises", False)
    except mc.MgmtClusterError as exc:
        check("yanolja refused", exc.code == "yanolja_refused")
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
    check("six modules", desk.get("module_count") == 6, str(desk.get("module_count")))
    check("no occupancy invent", desk.get("occupancy") is None and desk.get("adr") is None)
    mods = {m["id"]: m for m in desk.get("modules") or []}
    for mid in (
        "service_improve",
        "revenue_yield",
        "daily_ops_state",
        "journey_workflow",
        "pms_orchestration",
        "sla_incident",
    ):
        check(f"has {mid}", mid in mods)
    for mid in (
        "service_improve",
        "revenue_yield",
        "journey_workflow",
        "sla_incident",
    ):
        strip = mods[mid]["honesty_strip"]
        check(f"{mid} empty", strip.get("empty") is True)
        tags = strip.get("status_tags") or []
        check(f"{mid} EMPTY tag", "EMPTY" in tags, str(tags))
        check(f"{mid} no numbers", strip.get("numbers") is None)
        check(f"{mid} next", bool((strip.get("next_action") or {}).get("label")))
        check(f"{mid} not invented", strip.get("invented") is False)
    daily = mods["daily_ops_state"]["honesty_strip"]
    check("daily EMPTY", "EMPTY" in (daily.get("status_tags") or []), str(daily.get("status_tags")))
    check("daily not occupancy", daily.get("day_loop_not_occupancy") is True)
    check("daily occ null", daily.get("occupancy") is None)
    mod_h = mods["daily_ops_state"].get("module_honesty") or {}
    check("daily day loop separate", mod_h.get("day_loop_separate") is True)
    pms = mods["pms_orchestration"]["honesty_strip"]
    check("pms EMPTY", "EMPTY" in (pms.get("status_tags") or []), str(pms.get("status_tags")))
    check("pms no yanolja", pms.get("yanolja_connected") is False)
    check("primary next", isinstance(desk.get("primary_next"), dict) and bool(desk["primary_next"].get("label")))
    hand = desk.get("owner_empire_handoff") or {}
    check(
        "handoff class",
        hand.get("founder_dep_class") in {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"},
        str(hand.get("founder_dep_class")),
    )
    check("handoff no invent away", hand.get("invented_owner_control_away") is False)
    sr = desk.get("staff_ready") or {}
    check("staff_ready pack", sr.get("pack") == "amg_mgmt")
    check("staff lede human", "CAP-" not in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""))
    check("staff who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("no payment on screen", (sr.get("exposed_actions") or {}).get("payment_on_screen") is False)
    check("crs not resolved here", desk.get("crs_resolved_here") is False)
    check("desk proven false", desk.get("proven") is False and desk.get("ready") is False)

    strip = mc.module_strip("revenue_yield", verified_person_id="PERS-MATT")
    check("module strip ok", strip.get("ok") is True)
    check(
        "module strip empty",
        (strip.get("module") or {}).get("honesty_strip", {}).get("empty") is True,
    )


def test_hotel_ops_seat() -> None:
    td = Path(tempfile.mkdtemp(prefix="amg-mgmt-"))
    try:
        catalog = td / "catalog.sqlite"
        shutil.copy(CATALOG, catalog)
        _arm_hotel_ops(catalog)
        check("fixture hotel ops", "PERS-MISA" in ops.hotel_ops_ids(catalog))
        seat = mc.require_actor("PERS-MISA", catalog_db=catalog)
        check("misa hotel ops", seat["seat"] == "hotel_ops")
        desk = mc.build_desk(verified_person_id="PERS-MISA", catalog_db=catalog)
        check("misa desk ok", desk.get("ok") is True)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_caps_crs_untouched() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap in CAPS:
        check(f"ledger {cap} SPECIFIED", data[cap][0] == "SPECIFIED", str(data[cap][0]))
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
    check("html api", "/api/amg/mgmt-cluster" in text)
    check("html empty honesty", "Empty stays empty" in text or "empty stays empty" in text.lower())
    check("html no invent claim", "no invented" in text.lower() or "Not proven" in text)
    check("html day loop distinct", "day-loop" in text.lower() or "day loop" in text.lower())


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
            "/api/amg/mgmt-cluster",
            "/api/amg/mgmt-cluster/modules",
            "/api/amg/mgmt-cluster/honesty",
            "/api/amg/mgmt-cluster/staff-ready",
            "/amg-mgmt-cluster",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/amg/mgmt-cluster", MATT)
        check("matt desk 200", st == 200 and payload.get("ok") is True, str(st))
        check("matt bound", payload.get("bound") == mc.BOUND)
        check("matt six mods", len(payload.get("modules") or []) == 6)
        check("matt empty strips", int(payload.get("empty_count") or 0) >= 5)
        check("matt no hotel invent", payload.get("occupancy") is None)

        st, _ = call("GET", "/api/amg/mgmt-cluster", HAIKAL)
        check("haikal outsider 403", st == 403, str(st))

        st, _ = call("GET", "/api/amg/mgmt-cluster", DEVI)
        check("devi outsider 403", st == 403, str(st))

        st, _ = call("GET", "/api/amg/mgmt-cluster", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("GET", "/api/amg/mgmt-cluster/modules/revenue_yield", MATT)
        check("module strip 200", st == 200 and payload.get("ok") is True)
        strip = ((payload.get("module") or {}).get("honesty_strip") or {})
        check("yield strip empty", strip.get("empty") is True and strip.get("numbers") is None)

        st, page = call("GET", "/amg-mgmt-cluster", MATT)
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

        st, payload = call("POST", "/api/amg/mgmt-cluster/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/mgmt-cluster/ready", MATT, {})
        check("ready refuse", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/mgmt-cluster/money", MATT, {})
        check("money refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/mgmt-cluster/yanolja", MATT, {})
        check("yanolja refuse", st == 405 and payload.get("error") == "yanolja_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/mgmt-cluster/resolve", MATT, {})
        check("resolve refuse", st == 405 and payload.get("error") == "resolve_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/mgmt-cluster/production", MATT, {})
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


def main() -> int:
    test_module_honesty()
    test_desk_compose()
    test_hotel_ops_seat()
    test_caps_crs_untouched()
    test_html()
    test_wip_untouched()
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
