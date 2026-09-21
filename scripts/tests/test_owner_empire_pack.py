#!/usr/bin/env python3
"""Owner Empire pack — Progress, Radar, 12WY, and pack handoffs on one desk."""
from __future__ import annotations

import json
import os
import sqlite3
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

from core import owner_empire_pack as pack  # noqa: E402
from core import progress_read_model as progress  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_12WY = "CR-6535f7cb02370850"
CR_RADAR = "CR-7a145ad69d8bf3c5"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PAGE = ROOT / "dashboards" / "owner-empire-pack.html"
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


def _cr(cr_id: str) -> str | None:
    conn = sqlite3.connect(str(CATALOG))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (cr_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty() -> None:
    seat = pack.seat_for("PERS-MATT")
    check("owner seat", seat is not None and seat["money"] is False and seat["finance"] is False)
    check("devi forbidden", pack.seat_for("PERS-DEVI") is None)
    check("amanda forbidden", pack.seat_for("PERS-AMANDA") is None)
    check("haikal forbidden", pack.seat_for("PERS-HAIKAL") is None)
    check("misa forbidden", pack.seat_for("PERS-MISA") is None)
    flags = pack.honesty_flags()
    ledger = _ledger()
    check(
        "strat caps match ledger",
        flags["cap_strat_01"] == ledger["CAP-STRAT-01"][0]
        and flags["cap_strat_02"] == ledger["CAP-STRAT-02"][0]
        and flags["caps_raised"] is False,
    )
    check(
        "not invented prove",
        flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["invented_system_pct"] is False
        and flags["invented_12wy_percent"] is False
        and flags["second_scoring_table"] is False,
    )
    check("hidden money surfaces", "zayen" in flags["hidden"] and "trading" in flags["hidden"] and "hr" in flags["hidden"])
    check("track d parked flag", flags["track_d_built"] is False)
    check("bound", flags["bound"] == "beta-owner-safe")
    expected = progress.compute_system_from_ledger()
    today = pack.today_strip()
    check(
        "today uses ledger projection",
        today["system_pct"] == expected["system_pct"]
        and today["invented_system_pct"] is False
        and today["formula"] == progress.SYSTEM_FORMULA,
    )
    radar = pack.radar_strip()
    check(
        "radar does not copy system percent",
        radar["system_pct"] is None
        and radar["progress_used_as_cap"] is False
        and radar["pulse_count"] is None
        and radar["cap"] == "CAP-STRAT-02"
        and radar["maturity"] == ledger["CAP-STRAT-02"][0],
    )
    check("radar loud when empty", radar["display"] in {"UNWIRED", "EMPTY", "NAMED"})
    if radar["display"] in {"UNWIRED", "EMPTY"}:
        check("radar unwired is loud", radar["loud"] is True and "zero" in radar["why"].lower())
    else:
        check("radar named keeps counts empty", radar["exception_count"] is None)
    wy = pack.wy_strip()
    check("12wy cap", wy["cap"] == "CAP-STRAT-01" and wy["maturity"] == ledger["CAP-STRAT-01"][0])
    check("12wy does not invent tactics", wy["tactics_invented"] is False and wy["invented_percent"] is False)
    if wy["display"] == "EMPTY":
        check("empty 12wy is not zero", wy["percent"] is None and "not 0%" in wy["why"])
    elif wy["display"] == "UNWIRED":
        check("unwired 12wy has no percent", wy["percent"] is None and wy["loud"] is True)
    else:
        check("wired 12wy percent is evidenced", isinstance(wy["percent"], int) and wy["percent"] is not None)
    intel = pack.intel_strip()
    check("intel parked", intel["state"] == "PARKED" and intel["ops_pack_built"] is False and intel["href"] is None)
    try:
        pack.require_owner("PERS-DEVI")
        check("devi require raises", False)
    except pack.EmpirePackError as exc:
        check("devi require forbidden", exc.code == "forbidden")
    for fn, code in (
        (pack.refuse_payment, "payment_refused"),
        (pack.refuse_bank, "bank_refused"),
        (pack.refuse_finance, "finance_refused"),
        (pack.refuse_hr, "hr_refused"),
        (pack.refuse_trading, "trading_refused"),
        (pack.refuse_percent, "percent_refused"),
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
        (pack.refuse_resolve, "resolve_refused"),
    ):
        try:
            fn({})
            check(code, False)
        except pack.EmpirePackError as exc:
            check(code, exc.code == code)
    try:
        pack.refuse_external_write({"system_pct": 99})
        check("invent percent body", False)
    except pack.EmpirePackError as exc:
        check("invent percent body", exc.code == "percent_refused")
    desk = pack.build_desk(verified_person_id="PERS-MATT")
    nxt = (desk.get("actions") or {}).get("next") or {}
    check("next action is a board link", bool(nxt.get("href")) and nxt.get("kind") == "board")
    check("desk hides money", desk.get("money") is None and desk.get("payment_executed") is False)
    check("desk no finance", desk.get("finance_controls") is False and "finance" in (desk.get("hidden") or []))
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-owner-safe" in page)
    check("page no money button", ">Pay<" not in page and ">Settle<" not in page and "Zayen" in page)
    check("page empty not zero", "EMPTY is not 0%" in page)
    check("page track d parked", "Track D is parked" in page)
    source = (SCRIPTS / "core" / "owner_empire_pack.py").read_text(encoding="utf-8")
    for name in WIP:
        check(f"module does not reference {Path(name).name}", Path(name).name not in source or name.endswith("nope"))


def test_api() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
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
    ledger_before = LEDGER.read_text(encoding="utf-8")
    cr_12_before = _cr(CR_12WY)
    cr_radar_before = _cr(CR_RADAR)

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=60) as resp:
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
        st, _anon = call("GET", "/api/owner/empire-pack", None)
        check("anon GET 403", st == 403, str(st))
        st, _out = call("GET", "/api/owner/empire-pack", OUTSIDER)
        check("outsider GET 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, _body = call("GET", "/api/owner/empire-pack", subject)
            check(f"{label} GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/owner/empire-pack", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:300])
        if isinstance(owner, dict):
            check("owner person", owner.get("person_id") == "PERS-MATT")
            today = owner.get("today") or {}
            check("owner today honest", today.get("invented_system_pct") is False and today.get("href") == "/progress.html")
            radar = owner.get("radar") or {}
            check("owner radar no system pct", radar.get("system_pct") is None and radar.get("progress_used_as_cap") is False)
            wy = owner.get("twelve_wy") or {}
            if wy.get("display") == "EMPTY":
                check("owner 12wy empty", wy.get("percent") is None and "not 0%" in str(wy.get("why")))
            else:
                check(
                    "owner 12wy not invented",
                    wy.get("invented_percent") is False
                    and (wy.get("percent") is None or isinstance(wy.get("percent"), int)),
                )
            nxt = ((owner.get("actions") or {}).get("next") or {})
            check("owner next link", isinstance(nxt.get("href"), str) and nxt.get("href").startswith("/"))
            check("owner intel parked", (owner.get("intel") or {}).get("ops_pack_built") is False)
            check("owner money off", owner.get("payment_executed") is False and owner.get("money") is None)
            flags = owner.get("honesty") or {}
            check(
                "owner caps unchanged in payload",
                flags.get("cap_strat_01") == _ledger()["CAP-STRAT-01"][0]
                and flags.get("caps_raised") is False
                and flags.get("cr_mutated") is False,
            )
        st, today_view = call("GET", "/api/owner/empire-pack/today", MATT)
        check("owner today view", st == 200 and isinstance(today_view, dict) and "system_pct" in today_view)
        st, _missing = call("GET", "/api/owner/empire-pack/nope", MATT)
        check("unknown view 404", st == 404, str(st))
        for method, path in (
            ("POST", "/api/owner/empire-pack/payment"),
            ("POST", "/api/owner/empire-pack/bank"),
            ("POST", "/api/owner/empire-pack/zayen"),
            ("POST", "/api/owner/empire-pack/hr"),
            ("POST", "/api/owner/empire-pack/trading"),
            ("POST", "/api/owner/empire-pack/percent"),
            ("POST", "/api/owner/empire-pack/proven"),
            ("POST", "/api/owner/empire-pack/ready"),
            ("POST", "/api/owner/empire-pack/resolve"),
            ("PUT", "/api/owner/empire-pack"),
            ("PATCH", "/api/owner/empire-pack/production"),
        ):
            code, body = call(method, path, MATT, {"system_pct": 12, "amount": 1})
            check(f"{method} {path} refused", code == 405, str(body)[:180])
        st, _anon_post = call("POST", "/api/owner/empire-pack/payment", None, {})
        check("anon POST payment 403", st == 403, str(st))
        st, _anon_put = call("PUT", "/api/owner/empire-pack", None, {})
        check("anon PUT 403", st == 403, str(st))
        st, _staff = call("POST", "/api/owner/empire-pack/percent", DEVI, {"percent": 0})
        check("devi POST percent 403", st == 403, str(st))
        st, page = call("GET", "/owner-empire-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page_ok = call("GET", "/owner-empire-pack", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page_ok, (bytes, bytearray))
            and b"beta-owner-safe" in page_ok
            and b">Pay<" not in page_ok,
        )
        st, uma = call("GET", "/api/bzg/uma-blu/today", MATT)
        check("uma route still present", st in {200, 403}, str(st))
        st, ggv = call("GET", "/api/ggv/ops-pack", None)
        check("ggv anon still 403", st == 403, str(st))
        st, amg = call("GET", "/api/amg/ops-pack", None)
        check("amg anon still 403", st == 403, str(st))
    finally:
        httpd.shutdown()
    check("ledger bytes unchanged", LEDGER.read_text(encoding="utf-8") == ledger_before)
    check("12wy cr unchanged", _cr(CR_12WY) == cr_12_before)
    check("radar cr unchanged", _cr(CR_RADAR) == cr_radar_before)


def main() -> int:
    test_honesty()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
