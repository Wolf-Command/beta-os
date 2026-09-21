#!/usr/bin/env python3
"""AMG ops pack — Today desk, journey tasks, SLA list, service handoff."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
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

from core import amg_ops_pack as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-bc5785d66c981fd4"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _cr(cr_id: str, catalog: Path = CATALOG) -> str | None:
    conn = sqlite3.connect(str(catalog))
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


def test_honesty_and_seats() -> None:
    seats = {row["seat"]: row for row in pack.permission_matrix()}
    check("owner seat", seats["owner"]["person_id"] == "PERS-MATT" and seats["owner"]["can_ops"] is True)
    check("owner money off", seats["owner"]["money"] is False)
    check("hotel ops unassigned", seats["hotel_ops"]["assigned"] is False and seats["hotel_ops"]["person_id"] is None)
    check("devi forbidden", pack.seat_for("PERS-DEVI") is None)
    check("amanda forbidden", pack.seat_for("PERS-AMANDA") is None)
    check("misa forbidden on live roster", pack.seat_for("PERS-MISA") is None)
    flags = pack.honesty_flags()
    check("primary cap specified", flags["cap"] == "CAP-AMG-04" and flags["ledger_maturity"] == "SPECIFIED")
    check("caps not raised", all(row["state"] == "SPECIFIED" and row["raised"] is False for row in flags["caps"]))
    check("not invented prove", flags["invented_proven"] is False and flags["invented_ready"] is False and flags["proven"] is False and flags["ready"] is False)
    check("cr open", flags["cr_id"] == CR_ID and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
    check("bound", flags["bound"] == "beta-amg-ops-safe")
    check("no hotel numbers", flags["occupancy"] is None and flags["adr"] is None and flags["revpar"] is None and flags["yanolja_called"] is False)
    sla = pack.sla_list()
    check("sla empty", sla["empty"] is True and sla["open"] == [] and sla["live_incident"] is False and sla["recorded_count"] == 0)
    try:
        pack.refuse_folio({})
        check("folio raises", False)
    except pack.OpsPackError as exc:
        check("folio refused", exc.code == "folio_refused")
    try:
        pack.refuse_occupancy({})
        check("occupancy raises", False)
    except pack.OpsPackError as exc:
        check("occupancy refused", exc.code == "current_refused")
    try:
        pack.refuse_proven({})
        check("proven raises", False)
    except pack.OpsPackError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        pack.refuse_resolve({})
        check("resolve raises", False)
    except pack.OpsPackError as exc:
        check("resolve refused", exc.code == "resolve_refused")
    try:
        pack.refuse_yanolja({})
        check("yanolja raises", False)
    except pack.OpsPackError as exc:
        check("yanolja refused", exc.code == "yanolja_refused")
    try:
        pack.pack_db("/Users/wolfterminal/wolf-system/amg.sqlite")
        check("wolf-system path", False)
    except pack.OpsPackError as exc:
        check("wolf-system refused", exc.code == "not_beta")


def _arm_hotel_ops(catalog: Path) -> None:
    conn = sqlite3.connect(str(catalog))
    try:
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (
              'POS-AMG-DESK-TEST', 'ROLE-MATT', 'ENT-AMG', 'LOC-ATRIUM-LOMBOK', 'AMG-ATR', NULL,
              'Hotel desk test', 'ACTIVE', 1.0, '2026-09-21T00:00:00+08:00', '2026-09-21T00:00:00+08:00'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
            ) VALUES (
              'ASG-AMG-MISA-TEST', 'PERS-MISA', 'POS-AMG-DESK-TEST', '2026-09-21T00:00:00+08:00', NULL,
              'ACTIVE', 1, '2026-09-21T00:00:00+08:00', '2026-09-21T00:00:00+08:00'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_desk_loop(td: Path) -> None:
    db = td / "pack.sqlite"
    catalog = td / "catalog.sqlite"
    shutil.copy(CATALOG, catalog)
    _arm_hotel_ops(catalog)
    check("fixture hotel ops", pack.seat_for("PERS-MISA", catalog)["seat"] == "hotel_ops")
    check("fixture devi still out", pack.seat_for("PERS-DEVI", catalog) is None)
    check("live misa still out", pack.seat_for("PERS-MISA") is None)
    try:
        pack.save_note({"body": "Front desk word."}, verified_person_id="PERS-DEVI", db_path=db, catalog_db=catalog)
        check("devi note blocked", False)
    except pack.OpsPackError as exc:
        check("devi note forbidden", exc.code == "forbidden")
    try:
        pack.save_note(
            {"body": "Do not invent occupancy.", "occupancy": 41},
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        check("occupancy body blocked", False)
    except pack.OpsPackError as exc:
        check("occupancy body refused", exc.code == "current_refused")
    note = pack.save_note(
        {"body": "Late taxi for a named guest. Not a count.", "slot": "arrivals"},
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("note saved", note["ok"] is True and note["note"]["occupancy"] is None and note["note"]["hotel_fact"] is False)
    updated = pack.save_note(
        {"note_id": note["note"]["note_id"], "body": "Taxi moved to 18:00.", "slot": "arrivals"},
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("note updated", updated["note"]["body"] == "Taxi moved to 18:00." and updated["occupancy"] is None)
    look = pack.mark_attention(
        {"slot": "occupancy", "attention": True, "reason": "Ask the hotel system before quoting a number."},
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("attention is not occupancy", look["attention"] is True and look["occupancy"] is None and look["adr"] is None and look["revpar"] is None)
    journey = pack.open_journey(
        {"kind": "arrival", "title": "Confirm the airport note with the desk."},
        verified_person_id="PERS-MISA",
        db_path=db,
        catalog_db=catalog,
    )
    check(
        "journey is a task",
        journey["item"]["status"] == "OPEN"
        and journey["item"]["booking_count"] is None
        and journey["item"]["live_journey"] is False,
    )
    hand = pack.open_handoff(
        {"kind": "action", "note": "Next shift: ask engineering about the noisy corridor."},
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("handoff is not a score", hand["handoff"]["review_score"] is None and hand["handoff"]["desk_handoff"] is True)
    board = pack.build_board(verified_person_id="PERS-MATT", db_path=db, catalog_db=catalog)
    occ = next(slot for slot in board["today"]["slots"] if slot["kind"] == "occupancy")
    check("slot stays empty", occ["slot"] == "empty" and occ["occupancy"] is None and occ["attention"] is True)
    check("wait words", "not occupancy" in occ["why"].lower() and "Desk asked for a look" in occ["why"])
    check("one note", len(board["today"]["notes"]) == 1)
    check("journey listed", len(board["journey"]["items"]) == 1 and board["journey"]["framework_recorded_count"] == 0)
    check("sla still empty", board["sla"]["open"] == [] and board["sla"]["live_incident"] is False)
    check("handoff listed", len(board["handoff"]["items"]) == 1 and board["handoff"]["review_score"] is None)
    check("pms not called", board["pms"]["yanolja_called"] is False and board["pms"]["empty"] is True)
    check("finance hidden", board["finance_controls"] is False and board["money"] is None)
    check("board cr open", board["honesty"]["cr_state"] == "OPEN" and board["honesty"]["maturity"] == "SPECIFIED")
    try:
        pack.save_note({"body": "   "}, verified_person_id="PERS-MATT", db_path=db)
        check("blank note blocked", False)
    except pack.OpsPackError as exc:
        check("blank note invalid", exc.code == "invalid")
    try:
        pack.open_journey({"kind": "folio", "title": "No."}, verified_person_id="PERS-MATT", db_path=db)
        check("bad journey blocked", False)
    except pack.OpsPackError as exc:
        check("bad journey invalid", exc.code == "invalid")


def test_sources() -> None:
    src = (SCRIPTS / "core" / "amg_ops_pack.py").read_text(encoding="utf-8")
    check("reuses daily ops", "amg_daily_ops_state" in src)
    check("reuses journey", "amg_journey_workflow" in src)
    check("reuses sla", "amg_sla_incident" in src)
    check("reuses improve", "amg_service_improve" in src)
    check("reuses pms", "amg_pms_orchestration" in src)
    check("no uma import", "uma_ops" not in src and "bzg_" not in src and "ggv_ops" not in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/amg/ops-pack" in serve)
    check("page route", "/amg-ops-pack" in serve)
    check("folio route refused", "/api/amg/ops-pack/folio" in serve)
    check("payment route refused", "/api/amg/ops-pack/payment" in serve)
    check("yanolja route refused", "/api/amg/ops-pack/yanolja" in serve)
    check("proven route refused", "/api/amg/ops-pack/proven" in serve)
    check("resolve route refused", "/api/amg/ops-pack/resolve" in serve)
    check("track a still routed", "/api/bzg/uma-blu/today" in serve)
    check("track b still routed", "/api/ggv/ops-pack" in serve)
    check("daily ops still routed", "/api/amg/daily-ops-state" in serve)
    check("beta port", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "amg-ops-pack.html").read_text(encoding="utf-8")
    check("page bound", "beta-amg-ops-safe" in page)
    check("page not proven", "Not PROVEN" in page and "Not READY" in page)
    check("page no money button", "no payment, folio, bank" in page and ">Pay<" not in page and ">Settle<" not in page)
    check("page cr", "CR-bc5785d66c981fd4 stays OPEN" in page)
    check("page empty slot", "not live occupancy" in page)


def test_api(td: Path) -> None:
    os.environ["AMG_OPS_PACK_DB"] = str(td / "http-pack.sqlite")
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
    cr_before = _cr(CR_ID)

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
        st, _anon = call("GET", "/api/amg/ops-pack", None)
        check("anon GET 403", st == 403, str(st))
        st, _out = call("GET", "/api/amg/ops-pack", OUTSIDER)
        check("outsider GET 403", st == 403, str(st))
        st, _devi = call("GET", "/api/amg/ops-pack", DEVI)
        check("devi GET 403", st == 403, str(st))
        st, _misa = call("GET", "/api/amg/ops-pack", MISA)
        check("misa GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/amg/ops-pack", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner seat", owner.get("person_id") == "PERS-MATT" and (owner.get("seat") or {}).get("can_ops") is True)
            check("owner numbers empty", owner.get("occupancy") is None and owner.get("adr") is None and owner.get("revpar") is None)
            check("owner yanolja off", owner.get("yanolja_called") is False and (owner.get("pms") or {}).get("yanolja_called") is False)
            check("owner sla empty", ((owner.get("sla") or {}).get("open") or []) == [] and owner.get("invented_sla") is False)
            check("owner money off", owner.get("finance_controls") is False and owner.get("payment_executed") is False)
            flags = owner.get("honesty") or {}
            check("owner cr open", flags.get("cr_state") == "OPEN" and flags.get("maturity") == "SPECIFIED" and flags.get("proven") is False)
        st, sla = call("GET", "/api/amg/ops-pack/sla", MATT)
        check("owner sla view", st == 200 and isinstance(sla, dict) and sla.get("live_incident") is False and sla.get("open") == [])
        st, _blank = call("POST", "/api/amg/ops-pack/notes", MATT, {"body": "   "})
        check("blank note 400", st == 400, str(_blank)[:180])
        st, saved = call("POST", "/api/amg/ops-pack/notes", MATT, {"body": "Hold the late arrival note.", "slot": "arrivals"})
        check("owner note 200", st == 200 and isinstance(saved, dict) and (saved.get("note") or {}).get("occupancy") is None, str(saved)[:200])
        st, _crew = call("POST", "/api/amg/ops-pack/notes", HAIKAL, {"body": "Haikal is not hotel ops."})
        check("haikal note 403", st == 403, str(st))
        st, journey = call("POST", "/api/amg/ops-pack/journey", MATT, {"kind": "stay", "title": "Check the quiet-hours note."})
        check("owner journey 200", st == 200 and isinstance(journey, dict) and (journey.get("item") or {}).get("booking_count") is None, str(journey)[:200])
        st, missing = call("POST", "/api/amg/ops-pack/notes", AMANDA, {"note_id": "NOTE-missing", "body": "No such note."})
        check("amanda update 403", st == 403, str(st))
        st, absent = call("POST", "/api/amg/ops-pack/notes", MATT, {"note_id": "NOTE-missing", "body": "No such note."})
        check("missing note 404", st == 404 and isinstance(absent, dict) and absent.get("error") == "not_found", str(absent)[:180])
        for method, path in (
            ("POST", "/api/amg/ops-pack/payment"),
            ("POST", "/api/amg/ops-pack/folio"),
            ("POST", "/api/amg/ops-pack/bank"),
            ("POST", "/api/amg/ops-pack/zayen"),
            ("POST", "/api/amg/ops-pack/yanolja"),
            ("POST", "/api/amg/ops-pack/occupancy"),
            ("POST", "/api/amg/ops-pack/adr"),
            ("POST", "/api/amg/ops-pack/revpar"),
            ("POST", "/api/amg/ops-pack/proven"),
            ("POST", "/api/amg/ops-pack/ready"),
            ("POST", "/api/amg/ops-pack/resolve"),
            ("PUT", "/api/amg/ops-pack"),
            ("PATCH", "/api/amg/ops-pack/production"),
        ):
            code, body = call(method, path, MATT, {})
            check(f"{method} {path} refused", code == 405, str(body)[:160])
        st, _anon_post = call("POST", "/api/amg/ops-pack/notes", None, {"body": "anon"})
        check("anon POST notes 403", st == 403, str(st))
        st, _anon_pay = call("POST", "/api/amg/ops-pack/folio", None, {})
        check("anon POST folio 403", st == 403, str(st))
        st, _anon_put = call("PUT", "/api/amg/ops-pack", None, {})
        check("anon PUT 403", st == 403, str(st))
        st, page = call("GET", "/amg-ops-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page_ok = call("GET", "/amg-ops-pack", MATT)
        check("owner page 200", st == 200 and isinstance(page_ok, (bytes, bytearray)) and b"beta-amg-ops-safe" in page_ok and b">Pay<" not in page_ok)
        st, again = call("GET", "/api/amg/ops-pack", MATT)
        if isinstance(again, dict):
            kinds = {slot["kind"]: slot for slot in (again.get("today") or {}).get("slots") or []}
            check("live slot still empty", kinds.get("occupancy", {}).get("slot") == "empty" and kinds.get("occupancy", {}).get("occupancy") is None)
            check("journey on board", len((again.get("journey") or {}).get("items") or []) == 1)
    finally:
        httpd.shutdown()
    check("ledger bytes unchanged", LEDGER.read_text(encoding="utf-8") == ledger_before)
    check("cr still open", _cr(CR_ID) == cr_before == "OPEN")
    ledger = _ledger()
    check("amg caps specified", all(ledger.get(f"CAP-AMG-0{i}", [None])[0] == "SPECIFIED" for i in range(1, 8)))


def main() -> int:
    test_honesty_and_seats()
    with tempfile.TemporaryDirectory(prefix="amg-ops-pack-") as raw:
        test_desk_loop(Path(raw))
    test_sources()
    with tempfile.TemporaryDirectory(prefix="amg-ops-pack-http-") as raw:
        test_api(Path(raw))
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
