#!/usr/bin/env python3
"""Core Harden pack — commissioning honesty and factory claim hygiene."""
from __future__ import annotations

import hashlib
import json
import os
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

from core import core_harden_pack as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
ADOPTION = ROOT / "state" / "model-e-au-discovery.json"
MISSION = ROOT / "state" / "build-factory" / "missions" / "compressed-sprint-20260921.json"
CR_SOP = "CR-c4ed4e3fa9f15a40"
CR_ESC = "CR-6e3fd7b9d7edca0e"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PAGE = ROOT / "dashboards" / "core-harden-pack.html"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}


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


def _au(au_id: str) -> dict:
    rows = json.loads(ADOPTION.read_text(encoding="utf-8"))
    return next(row for row in rows if row.get("au_id") == au_id)


def test_honesty() -> None:
    for rel, digest in WIP.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP unchanged {Path(rel).name}", got == digest, got)
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--", *WIP],
        cwd=ROOT,
        text=True,
    )
    for rel in WIP:
        line = next((ln for ln in status.splitlines() if ln[3:] == rel), "")
        check(f"WIP unstaged {Path(rel).name}", bool(line) and line[0] == " ", line or "missing")

    seat = pack.seat_for("PERS-MATT")
    check("owner seat", seat is not None and seat["money"] is False and seat["can_commission"] is False)
    check("devi forbidden", pack.seat_for("PERS-DEVI") is None)
    check("amanda forbidden", pack.seat_for("PERS-AMANDA") is None)
    check("haikal forbidden", pack.seat_for("PERS-HAIKAL") is None)
    check("misa forbidden", pack.seat_for("PERS-MISA") is None)
    flags = pack.honesty_flags()
    ledger = _ledger()
    check(
        "core caps match ledger",
        flags["cap_core_11"] == ledger["CAP-CORE-11"][0]
        and flags["cap_core_12"] == ledger["CAP-CORE-12"][0]
        and flags["caps_raised"] is False
        and flags["cap_core_11"] == "SPECIFIED"
        and flags["cap_core_12"] == "BUILT",
    )
    check(
        "not invented prove",
        flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["invented_commissioned"] is False
        and flags["invented_adopted"] is False
        and flags["not_done_is_done"] is False,
    )
    check("hidden money surfaces", "zayen" in flags["hidden"] and "trading" in flags["hidden"] and "hr" in flags["hidden"])
    check("bound", flags["bound"] == "beta-core-safe")
    uma = _au("AU-BZG-03-UMA")
    devi = pack.devi_gate()
    check(
        "devi not done",
        devi["human_commissioning"] == "NOT_DONE"
        and devi["commissioned"] is False
        and devi["status_detail"] == "PARTIAL_FEEDBACK_RECEIVED"
        and devi["partial_is_done"] is False
        and devi["loud"] is True,
    )
    check(
        "au not flipped",
        devi["au"]["state"] == uma["state"]
        and devi["au"]["state"] == "NOT STARTED"
        and devi["au"]["flipped"] is False
        and devi["au"]["adopted"] is False,
    )
    check("phone retest parked", devi["phone_retest"] == "PARKED")
    check(
        "cf disagreement kept",
        devi["cf_access_claim"] == "UNLOCKED_BY_MATT"
        and devi["cf_access_review"] == "NEEDS_MATT"
        and devi["cloudflare_write"] is False,
    )
    habitat = pack.habitat_gate()
    check(
        "habitat not commissioned",
        habitat["human_commissioning"] == "NOT_DONE"
        and habitat["commissioned"] is False
        and habitat["invented_commissioned"] is False
        and habitat["loud"] is True,
    )
    check(
        "prove week not proved",
        habitat["prove_week"]["proved"] is False
        and habitat["prove_week"]["status"] == "NOT_PROVED"
        and habitat["prove_week"]["planning_phrase_present"] is True,
    )
    check(
        "habitat aus not adopted",
        all(unit["state"] == "NOT STARTED" and unit["adopted"] is False for unit in habitat["adoption_units"])
        and habitat["adopted"] is False,
    )
    factory = pack.factory_strip()
    active = (ROOT / "state" / "build-factory" / "ACTIVE").read_text(encoding="utf-8").strip()
    check("active run read", factory["active_run_id"] == active and factory["active_run_read"] is True)
    check(
        "mission lane read",
        factory["mission_id"] == "compressed-sprint-20260921"
        and factory["active_lane_id"] == "sprint-track-f-core-harden-pack",
    )
    track_d = factory["track_d"]
    check(
        "track d parked",
        track_d["state"] == "PARKED"
        and track_d["restarted"] is False
        and track_d["ops_pack_built"] is False
        and track_d["reason"] == "dead_cursor_after_one_relaunch_no_agent_output",
    )
    check(
        "finance lanes not restarted",
        factory["wave12"]["status"] == "PARKED"
        and factory["wave12"]["restarted"] is False
        and "fin-profit-leakage-v1" in factory["wave12"]["parked_pending"],
    )
    by_id = {row["id"]: row for row in factory["claims"]}
    file_claims = {
        row["id"]: row
        for row in json.loads((ROOT / "state" / "build-claims" / "2026-09-21.json").read_text(encoding="utf-8"))["claims"]
    }
    for cid in pack.SPRINT_CLAIM_IDS:
        if cid not in file_claims:
            check(f"{cid} absent", by_id[cid]["verify"] == "ABSENT")
        else:
            expected = str(file_claims[cid].get("verify") or "UNCHECKED")
            check(f"{cid} echoed", by_id[cid]["verify"] == expected, by_id[cid]["verify"])
    deferred = [row for row in factory["lanes"] if row.get("track") in {"A", "B", "C", "E"}]
    check("deferred lanes present", len(deferred) == 4)
    check(
        "deferred commits are not git shas",
        all(row["real_git_sha"] is False and row["commit_deferred"] is True for row in deferred),
    )
    actions = pack.next_actions(devi, habitat)
    nxt = actions.get("next") or {}
    check(
        "next human action",
        nxt.get("kind") == "human"
        and nxt.get("done") is False
        and nxt.get("id") == "devi-phone-retest",
    )
    try:
        pack.require_owner("PERS-DEVI")
        check("devi require raises", False)
    except pack.HardenPackError as exc:
        check("devi require forbidden", exc.code == "forbidden")
    for fn, code in (
        (pack.refuse_payment, "payment_refused"),
        (pack.refuse_bank, "bank_refused"),
        (pack.refuse_finance, "finance_refused"),
        (pack.refuse_hr, "hr_refused"),
        (pack.refuse_trading, "trading_refused"),
        (pack.refuse_cloudflare, "cloudflare_refused"),
        (pack.refuse_commission, "commission_refused"),
        (pack.refuse_adopt, "adopt_refused"),
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
        (pack.refuse_resolve, "resolve_refused"),
    ):
        try:
            fn({})
            check(code, False)
        except pack.HardenPackError as exc:
            check(code, exc.code == code)
    try:
        pack.refuse_external_write({"au_id": "AU-BZG-03-UMA", "state": "ADOPTED"})
        check("adopt body refused", False)
    except pack.HardenPackError as exc:
        check("adopt body refused", exc.code == "adopt_refused")
    try:
        pack.refuse_external_write({"state": "COMMISSIONED"})
        check("commission body refused", False)
    except pack.HardenPackError as exc:
        check("commission body refused", exc.code == "commission_refused")
    desk = pack.build_desk(verified_person_id="PERS-MATT")
    check("desk next action", ((desk.get("actions") or {}).get("next") or {}).get("id") == "devi-phone-retest")
    check("desk hides money", desk.get("money") is None and desk.get("payment_executed") is False)
    check("desk no cloudflare write", desk.get("cloudflare_mutated") is False)
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-core-safe" in page)
    check("page not done", "NOT_DONE is not done" in page)
    check("page no money button", ">Pay<" not in page and ">Settle<" not in page)
    check("page no commission button", "Mark commissioned" not in page and "Mark adopted" not in page)
    source = (SCRIPTS / "core" / "core_harden_pack.py").read_text(encoding="utf-8")
    for name in WIP:
        check(f"module does not reference {Path(name).name}", Path(name).name not in source)


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
    adoption_before = ADOPTION.read_text(encoding="utf-8")
    mission_before = MISSION.read_text(encoding="utf-8")
    cr_sop_before = _cr(CR_SOP)
    cr_esc_before = _cr(CR_ESC)

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
        st, _anon = call("GET", "/api/core/harden-pack", None)
        check("anon GET 403", st == 403, str(st))
        st, _out = call("GET", "/api/core/harden-pack", OUTSIDER)
        check("outsider GET 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, _body = call("GET", "/api/core/harden-pack", subject)
            check(f"{label} GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/core/harden-pack", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:400])
        if isinstance(owner, dict):
            check("owner person", owner.get("person_id") == "PERS-MATT")
            devi = owner.get("devi") or {}
            check(
                "owner devi not done",
                devi.get("human_commissioning") == "NOT_DONE" and devi.get("commissioned") is False,
            )
            habitat = owner.get("habitat") or {}
            check(
                "owner habitat not commissioned",
                habitat.get("commissioned") is False and (habitat.get("prove_week") or {}).get("proved") is False,
            )
            nxt = ((owner.get("actions") or {}).get("next") or {})
            check("owner next human", nxt.get("kind") == "human" and nxt.get("done") is False)
            flags = owner.get("honesty") or {}
            check(
                "owner caps unchanged in payload",
                flags.get("cap_core_11") == "SPECIFIED"
                and flags.get("cap_core_12") == "BUILT"
                and flags.get("au_flipped") is False,
            )
            check("owner money off", owner.get("payment_executed") is False and owner.get("money") is None)
            check("owner track d still parked", ((owner.get("factory") or {}).get("track_d") or {}).get("restarted") is False)
        st, devi_view = call("GET", "/api/core/harden-pack/devi", MATT)
        check("owner devi view", st == 200 and isinstance(devi_view, dict) and devi_view.get("human_commissioning") == "NOT_DONE")
        st, _missing = call("GET", "/api/core/harden-pack/nope", MATT)
        check("unknown view 404", st == 404, str(st))
        for method, path in (
            ("POST", "/api/core/harden-pack/payment"),
            ("POST", "/api/core/harden-pack/bank"),
            ("POST", "/api/core/harden-pack/zayen"),
            ("POST", "/api/core/harden-pack/hr"),
            ("POST", "/api/core/harden-pack/trading"),
            ("POST", "/api/core/harden-pack/cloudflare"),
            ("POST", "/api/core/harden-pack/cf"),
            ("POST", "/api/core/harden-pack/commission"),
            ("POST", "/api/core/harden-pack/adopt"),
            ("POST", "/api/core/harden-pack/proven"),
            ("POST", "/api/core/harden-pack/ready"),
            ("POST", "/api/core/harden-pack/resolve"),
            ("PUT", "/api/core/harden-pack"),
            ("PATCH", "/api/core/harden-pack/production"),
        ):
            code, body = call(method, path, MATT, {"au_id": "AU-BZG-03-UMA", "state": "ADOPTED", "amount": 1})
            check(f"{method} {path} refused", code == 405, str(body)[:180])
        st, _anon_post = call("POST", "/api/core/harden-pack/payment", None, {})
        check("anon POST payment 403", st == 403, str(st))
        st, _anon_cf = call("POST", "/api/core/harden-pack/cloudflare", None, {})
        check("anon POST cloudflare 403", st == 403, str(st))
        st, _anon_adopt = call(
            "POST",
            "/api/core/harden-pack/adopt",
            None,
            {"au_id": "AU-BZG-03-UMA", "state": "ADOPTED"},
        )
        check("anon POST adopt 403", st == 403, str(st))
        st, _anon_put = call("PUT", "/api/core/harden-pack", None, {})
        check("anon PUT 403", st == 403, str(st))
        st, _staff = call("POST", "/api/core/harden-pack/commission", DEVI, {"state": "COMMISSIONED"})
        check("devi POST commission 403", st == 403, str(st))
        st, page = call("GET", "/core-harden-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page_ok = call("GET", "/core-harden-pack", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page_ok, (bytes, bytearray))
            and b"beta-core-safe" in page_ok
            and b"NOT_DONE is not done" in page_ok
            and b">Pay<" not in page_ok,
        )
        st, uma = call("GET", "/api/bzg/uma-blu/today", None)
        check("uma anon still 403", st == 403, str(st))
        st, ggv = call("GET", "/api/ggv/ops-pack", None)
        check("ggv anon still 403", st == 403, str(st))
        st, amg = call("GET", "/api/amg/ops-pack", None)
        check("amg anon still 403", st == 403, str(st))
        st, empire = call("GET", "/api/owner/empire-pack", None)
        check("empire anon still 403", st == 403, str(st))
        st, empire_page = call("GET", "/owner-empire-pack", None)
        check("empire page anon still 403", st == 403, str(st))
    finally:
        httpd.shutdown()
    check("ledger bytes unchanged", LEDGER.read_text(encoding="utf-8") == ledger_before)
    check("adoption bytes unchanged", ADOPTION.read_text(encoding="utf-8") == adoption_before)
    check("mission bytes unchanged", MISSION.read_text(encoding="utf-8") == mission_before)
    check("sop cr unchanged", _cr(CR_SOP) == cr_sop_before == "OPEN")
    check("escalation cr unchanged", _cr(CR_ESC) == cr_esc_before == "OPEN")


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
