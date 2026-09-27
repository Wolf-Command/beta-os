#!/usr/bin/env python3
"""Sprint2 P3 AMG day loop — operable HK/maint/incident/recovery/handover on Beta."""
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


def test_honesty_and_schema() -> None:
    flags = pack.honesty_flags()
    check("day bound present", flags.get("day_bound") == "beta-amg-day-safe")
    check("ops bound kept", flags.get("bound") == "beta-amg-ops-safe")
    check(
        "cap specified",
        flags["ledger_maturity"] == "SPECIFIED"
        and flags["proven"] is False
        and flags["ready"] is False,
    )
    check("cr open", flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
    check("yanolja pms truth", flags.get("yanolja_pms_truth") is True and flags["yanolja_called"] is False)
    check("no invent arrivals", flags.get("invented_arrivals") is False and flags.get("invented_departures") is False)
    schema = pack.schema_document()
    check(
        "7 day stages",
        schema["day_loop_stages"] == list(pack.DAY_LOOP_STAGES)
        and len(schema["day_loop_stages"]) == 7,
    )
    check("day schema id", schema["day_schema_id"] == "wolf.amg-day-loop.v1")
    check(
        "day object kinds",
        schema["day_object_kinds"] == list(pack.DAY_OBJECT_KINDS)
        and "housekeeping" in schema["day_object_kinds"],
    )
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
        pack.refuse_yanolja({})
        check("yanolja raises", False)
    except pack.OpsPackError as exc:
        check("yanolja refused", exc.code == "yanolja_refused")
    try:
        pack.refuse_proven({})
        check("proven raises", False)
    except pack.OpsPackError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        pack.refuse_ready({})
        check("ready raises", False)
    except pack.OpsPackError as exc:
        check("ready refused", exc.code == "ready_refused")
    try:
        pack.refuse_production({})
        check("production raises", False)
    except pack.OpsPackError as exc:
        check("production refused", exc.code == "production_refused")


def test_day_loop_on_copy(td: Path) -> None:
    db = td / "pack.sqlite"
    board = pack.build_board(verified_person_id="PERS-MATT", db_path=db)
    check(
        "board has day loop",
        isinstance(board.get("day_loop"), dict)
        and board["day_loop"]["bound"] == "beta-amg-day-safe",
    )
    check(
        "board has mgmt exceptions",
        isinstance(board.get("management_exceptions"), dict)
        and board["management_exceptions"]["invented_sla"] is False
        and board["management_exceptions"]["empty"] is True,
    )
    check(
        "board owner visibility empty",
        board["owner_visibility"]["empty"] is True
        and board["owner_visibility"]["occupancy"] is None
        and board["owner_visibility"]["yanolja_called"] is False,
    )
    check(
        "today wait slots",
        all(
            slot["slot"] == "empty" and slot["occupancy"] is None
            for slot in board["today"]["slots"]
            if slot["kind"] in {"occupancy", "arrivals", "departures"}
        ),
    )
    check(
        "wait words held",
        "not an arrival list" in next(
            s["why"] for s in board["today"]["slots"] if s["kind"] == "arrivals"
        ).lower(),
    )

    try:
        pack.open_day_object(
            {"kind": "housekeeping", "title": "x", "note": "  "},
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        check("blank day note raises", False)
    except pack.OpsPackError as exc:
        check("day note required", exc.code == "invalid")

    try:
        pack.open_day_object(
            {
                "kind": "housekeeping",
                "title": "Invent rooms",
                "note": "Do not invent.",
                "occupancy": 88,
            },
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        check("occupancy on day object blocked", False)
    except pack.OpsPackError as exc:
        check("day occupancy refused", exc.code == "current_refused")

    try:
        pack.open_day_object(
            {"kind": "folio", "title": "No", "note": "No money."},
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        check("bad kind blocked", False)
    except pack.OpsPackError as exc:
        check("bad kind invalid", exc.code == "invalid")

    hk = pack.open_day_object(
        {
            "kind": "housekeeping",
            "title": "Corridor soft goods check",
            "note": "Desk ask for a look after lunch. Not a room count.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check(
        "hk opened",
        hk["ok"] is True
        and hk["object"]["kind"] == "housekeeping"
        and hk["object"]["hotel_fact"] is False
        and hk["object"]["occupancy"] is None
        and hk["object"]["room_number"] is None,
    )

    maint = pack.open_day_object(
        {
            "kind": "maintenance",
            "title": "Noisy AC note",
            "note": "Engineering follow-up. Not a Yanolja write.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("maint opened", maint["object"]["status"] == "OPEN" and maint["yanolja_called"] is False)

    incident = pack.open_day_object(
        {
            "kind": "incident",
            "title": "Guest noise complaint note",
            "note": "Operator incident note. Not an invented SLA timer.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check(
        "incident not pms invent",
        incident["object"]["incident_number"] is None
        and incident["object"]["live_incident"] is False
        and incident["object"]["sla_timer"] is None,
    )

    recovery = pack.open_day_object(
        {
            "kind": "service_recovery",
            "title": "Apology follow-up",
            "note": "Recovery note for next shift. Not a review score.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("recovery opened", recovery["object"]["kind"] == "service_recovery")

    handover = pack.open_day_object(
        {
            "kind": "handover",
            "title": "Night to morning",
            "note": "Carry the AC noise note and the soft-goods look.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("handover opened", handover["object"]["kind"] == "handover")

    raised = pack.raise_day_mgmt_exception(
        {
            "object_id": incident["object"]["object_id"],
            "reason": "Needs Owner eyes before evening brief.",
        },
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check(
        "mgmt raised",
        raised["ok"] is True
        and raised["object"]["needs_mgmt"] is True
        and raised["object"]["status"] == "ESCALATED"
        and raised["invented_sla"] is False
        and raised["sla_breached"] is None,
    )

    done = pack.set_day_object_status(
        {"object_id": hk["object"]["object_id"], "status": "DONE"},
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check("hk done", done["object"]["status"] == "DONE")

    try:
        pack.set_day_object_status(
            {"object_id": "DAY-missing", "status": "DONE"},
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        check("missing day object raises", False)
    except pack.OpsPackError as exc:
        check("missing day object 404 code", exc.code == "not_found")

    try:
        pack.open_day_object(
            {"kind": "housekeeping", "title": "No", "note": "No."},
            verified_person_id="PERS-DEVI",
            db_path=db,
        )
        check("devi day object blocked", False)
    except pack.OpsPackError as exc:
        check("devi forbidden", exc.code == "forbidden")

    board2 = pack.build_board(verified_person_id="PERS-MATT", db_path=db)
    check("day items listed", board2["day_loop"]["count"] == 5)
    check(
        "mgmt strip has incident",
        any(
            row["object_id"] == incident["object"]["object_id"]
            and "operator_raised" in row["reasons"]
            for row in board2["management_exceptions"]["exceptions"]
        ),
    )
    check(
        "owner visibility fed",
        board2["owner_visibility"]["count"] >= 1
        and board2["owner_visibility"]["hotel_facts_invented"] is False
        and board2["owner_visibility"]["arrivals"] is None
        and board2["owner_visibility"]["departures"] is None,
    )
    check(
        "slots still wait words",
        next(s for s in board2["today"]["slots"] if s["kind"] == "occupancy")["slot"] == "empty"
        and board2["pms"]["yanolja_called"] is False,
    )
    check("finance still off", board2["finance_controls"] is False and board2["money"] is None)
    check("live cr untouched", _cr(CR_ID) == "OPEN")
    ledger = _ledger()
    check(
        "amg caps specified",
        all(ledger.get(f"CAP-AMG-0{i}", [None])[0] == "SPECIFIED" for i in range(1, 8)),
    )


def test_sources() -> None:
    src = (SCRIPTS / "core" / "amg_ops_pack.py").read_text(encoding="utf-8")
    check("day bound in pack", "beta-amg-day-safe" in src)
    check("day objects table", "day_objects" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    check("no uma import", "uma_ops" not in src and "ggv_ops" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        'view == "day-loop"',
        'view == "management-exceptions"',
        'view == "owner-visibility"',
        "/api/amg/ops-pack/day-object",
        "/api/amg/ops-pack/day-object-status",
        "/api/amg/ops-pack/mgmt-exception",
    ):
        check(f"route {needle}", needle in serve)
    check("folio still refused", "/api/amg/ops-pack/folio" in serve)
    check("yanolja still refused", "/api/amg/ops-pack/yanolja" in serve)
    check("proven still refused", "/api/amg/ops-pack/proven" in serve)
    page = (ROOT / "dashboards" / "amg-ops-pack.html").read_text(encoding="utf-8")
    check("page day bound", "beta-amg-day-safe" in page)
    check("page ops bound", "beta-amg-ops-safe" in page)
    check("page not proven", "Not PROVEN" in page and "Not READY" in page)
    check("page day loop", "Day loop" in page)
    check("page mgmt", "Management exceptions" in page)
    check("page owner", "Owner visibility" in page)
    check("page no money button", "no payment, folio, bank" in page and ">Pay<" not in page)
    for rel in WIP:
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())


def test_api(td: Path) -> None:
    os.environ["AMG_OPS_PACK_DB"] = str(td / "http-pack.sqlite")
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = getattr(sb, "BetaHandler", None)
    if Handler is None:
        for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
            if (
                issubclass(obj, BaseHTTPRequestHandler)
                and obj is not BaseHTTPRequestHandler
                and obj.__module__ == "serve_beta"
                and obj.__name__ == "BetaHandler"
            ):
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
            "/api/amg/ops-pack",
            "/api/amg/ops-pack/day-loop",
            "/api/amg/ops-pack/management-exceptions",
            "/api/amg/ops-pack/owner-visibility",
            "/amg-ops-pack",
        ):
            st, _ = call("GET", path, None)
            check(f"anon GET {path} 403", st == 403, str(st))

        st, _ = call(
            "POST",
            "/api/amg/ops-pack/day-object",
            None,
            {"kind": "housekeeping", "title": "x", "note": "y"},
        )
        check("anon POST day-object 403", st == 403, str(st))
        st, _ = call(
            "POST",
            "/api/amg/ops-pack/mgmt-exception",
            None,
            {"object_id": "DAY-x", "reason": "y"},
        )
        check("anon POST mgmt 403", st == 403, str(st))

        st, owner = call("GET", "/api/amg/ops-pack", MATT)
        check(
            "owner GET 200",
            st == 200 and isinstance(owner, dict) and owner.get("ok") is True,
            str(owner)[:240],
        )
        if isinstance(owner, dict):
            check(
                "owner day bound",
                owner.get("day_bound") == "beta-amg-day-safe"
                and (owner.get("day_loop") or {}).get("bound") == "beta-amg-day-safe",
            )
            check(
                "owner wait honesty",
                owner.get("occupancy") is None
                and owner.get("yanolja_called") is False
                and (owner.get("owner_visibility") or {}).get("arrivals") is None,
            )
            flags = owner.get("honesty") or {}
            check(
                "owner caps specified",
                flags.get("maturity") == "SPECIFIED"
                and flags.get("proven") is False
                and flags.get("ready") is False,
            )

        st, loop = call("GET", "/api/amg/ops-pack/day-loop", MATT)
        check(
            "owner day-loop view",
            st == 200
            and isinstance(loop, dict)
            and loop.get("bound") == "beta-amg-day-safe"
            and loop.get("yanolja_called") is False,
            str(loop)[:200],
        )

        st, created = call(
            "POST",
            "/api/amg/ops-pack/day-object",
            MATT,
            {
                "kind": "maintenance",
                "title": "Lift light flicker note",
                "note": "Ask engineering. Not a room status invent.",
            },
        )
        check(
            "owner day-object 200",
            st == 200
            and isinstance(created, dict)
            and (created.get("object") or {}).get("hotel_fact") is False,
            str(created)[:200],
        )
        object_id = ((created or {}).get("object") or {}).get("object_id") if isinstance(created, dict) else None

        st, _crew = call(
            "POST",
            "/api/amg/ops-pack/day-object",
            HAIKAL,
            {"kind": "housekeeping", "title": "No", "note": "Haikal is not hotel ops."},
        )
        check("haikal day-object 403", st == 403, str(st))
        st, _amanda = call(
            "POST",
            "/api/amg/ops-pack/day-object",
            AMANDA,
            {"kind": "housekeeping", "title": "No", "note": "Amanda is not hotel ops."},
        )
        check("amanda day-object 403", st == 403, str(st))
        st, _devi = call(
            "POST",
            "/api/amg/ops-pack/day-object",
            DEVI,
            {"kind": "housekeeping", "title": "No", "note": "Devi is not hotel ops."},
        )
        check("devi day-object 403", st == 403, str(st))

        if object_id:
            st, raised = call(
                "POST",
                "/api/amg/ops-pack/mgmt-exception",
                MATT,
                {"object_id": object_id, "reason": "Owner look before close."},
            )
            check(
                "owner mgmt 200",
                st == 200
                and isinstance(raised, dict)
                and (raised.get("object") or {}).get("status") == "ESCALATED"
                and raised.get("invented_sla") is False,
                str(raised)[:200],
            )
            st, mgmt = call("GET", "/api/amg/ops-pack/management-exceptions", MATT)
            check(
                "mgmt view lists",
                st == 200
                and isinstance(mgmt, dict)
                and any(
                    row.get("object_id") == object_id
                    for row in (mgmt.get("exceptions") or [])
                ),
            )
            st, owner_v = call("GET", "/api/amg/ops-pack/owner-visibility", MATT)
            check(
                "owner visibility view",
                st == 200
                and isinstance(owner_v, dict)
                and owner_v.get("yanolja_called") is False
                and owner_v.get("occupancy") is None,
            )

        for method, path in (
            ("POST", "/api/amg/ops-pack/payment"),
            ("POST", "/api/amg/ops-pack/folio"),
            ("POST", "/api/amg/ops-pack/bank"),
            ("POST", "/api/amg/ops-pack/yanolja"),
            ("POST", "/api/amg/ops-pack/occupancy"),
            ("POST", "/api/amg/ops-pack/proven"),
            ("POST", "/api/amg/ops-pack/ready"),
            ("POST", "/api/amg/ops-pack/resolve"),
            ("PATCH", "/api/amg/ops-pack/production"),
        ):
            code, body = call(method, path, MATT, {})
            check(f"{method} {path} refused", code == 405, str(body)[:160])

        st, page = call("GET", "/amg-ops-pack", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"beta-amg-day-safe" in page
            and b">Pay<" not in page,
        )
        st, again = call("GET", "/api/amg/ops-pack", MATT)
        if isinstance(again, dict):
            kinds = {
                slot["kind"]: slot
                for slot in (again.get("today") or {}).get("slots") or []
            }
            check(
                "live occupancy still empty",
                kinds.get("occupancy", {}).get("slot") == "empty"
                and kinds.get("occupancy", {}).get("occupancy") is None,
            )
            check(
                "live arrivals wait",
                "not an arrival list" in (kinds.get("arrivals") or {}).get("why", "").lower(),
            )
    finally:
        httpd.shutdown()
    check("ledger bytes unchanged", LEDGER.read_text(encoding="utf-8") == ledger_before)
    check("cr still open", _cr(CR_ID) == cr_before == "OPEN")
    ledger = _ledger()
    check(
        "amg caps specified live",
        all(ledger.get(f"CAP-AMG-0{i}", [None])[0] == "SPECIFIED" for i in range(1, 8)),
    )
    check("ledger key count", len(ledger) == 77)


def main() -> int:
    test_honesty_and_schema()
    with tempfile.TemporaryDirectory(prefix="amg-day-loop-") as raw:
        test_day_loop_on_copy(Path(raw))
    test_sources()
    with tempfile.TemporaryDirectory(prefix="amg-day-loop-http-") as raw:
        test_api(Path(raw))
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
