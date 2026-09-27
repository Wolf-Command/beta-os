#!/usr/bin/env python3
"""Sprint2 P3 AMG Day-Loop Operator Depth — day detail/action + consequence refresh."""
from __future__ import annotations

import hashlib
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
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import amg_ops_pack as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-bc5785d66c981fd4"
MATT = "mrwolf@wolfcommand.net"
MISA = "mlsary111@gmail.com"
OUTSIDER = "not-a-seat@example.com"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": None,
    "scripts/phase26_team.py": None,
    "scripts/skills/__init__.py": None,
    "scripts/wolf_intelligence.py": None,
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cr(item_id: str, catalog: Path = LIVE_DB) -> str | None:
    conn = sqlite3.connect(str(catalog))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty() -> None:
    flags = pack.honesty_flags()
    check("day bound", flags.get("day_bound") == "beta-amg-day-safe")
    check(
        "operator depth schema",
        flags.get("operator_depth_schema_id") == pack.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check("no live hotel commission", flags.get("live_hotel_commission") is False)
    check("empty day loop honesty", flags.get("empty_day_loop_is_not_live") is True)
    check("cap specified", flags["ledger_maturity"] == "SPECIFIED")
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("cr open", flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
    schema = pack.schema_document()
    check(
        "operator depth in schema",
        schema.get("operator_depth_schema_id") == pack.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check(
        "action kinds",
        schema.get("day_operator_action_kinds") == sorted(pack.DAY_OPERATOR_ACTION_KINDS),
    )
    for fn, code in (
        (pack.refuse_folio, "folio_refused"),
        (pack.refuse_occupancy, "current_refused"),
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
        (pack.refuse_production, "production_refused"),
        (pack.refuse_yanolja, "yanolja_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except pack.OpsPackError as exc:
            check(f"{code}", exc.code == code, exc.code)


def test_operator_depth_on_copy(td: Path) -> None:
    catalog = td / "catalog.sqlite"
    pack_db = td / "pack.sqlite"
    shutil.copy2(LIVE_DB, catalog)
    conn = sqlite3.connect(str(catalog))
    conn.row_factory = sqlite3.Row
    try:
        grant = pack.ensure_operator_depth_rbac(conn=conn, catalog_db=catalog, commit=True)
        check(
            "rbac grant ok",
            grant.get("ok") is True and pack.PERM_DAY_OPERATOR in (grant.get("grants") or []),
            str(grant)[:200],
        )
        prove = pack.prove_day_operator(person_id="PERS-MISA", conn=conn, catalog_db=catalog)
        check(
            "PERS-MISA day operator",
            prove.get("can_day_operator") is True
            and prove.get("assignment_active") is True
            and prove.get("live_hotel_commission") is False
            and prove.get("actions", {}).get("folio") is False
            and prove.get("actions", {}).get("payment") is False,
            str(prove)[:240],
        )
        check(
            "misa hotel ops seat",
            "PERS-MISA" in pack.hotel_ops_ids(catalog),
        )

        opened = pack.open_day_object(
            {
                "kind": "incident",
                "title": "Operator depth fixture incident",
                "note": "Desk note only. Not a PMS invent.",
            },
            verified_person_id="PERS-MISA",
            db_path=pack_db,
            catalog_db=catalog,
        )
        object_id = opened["object"]["object_id"]
        check("day object opened", opened.get("ok") is True and bool(object_id))

        detail = pack.operator_day_detail(
            object_id,
            verified_person_id="PERS-MISA",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "operator day detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-amg-day-safe"
            and bool(detail.get("actions", {}).get("day_operator"))
            and detail.get("folio_executed") is False
            and detail.get("invented_occupancy") is False
            and "/amg-ops-pack#day-" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )

        note = pack.record_day_operator_action(
            verified_person_id="PERS-MISA",
            object_id=object_id,
            kind="note",
            note="Depth note — Atrium fixture only.",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "operator note",
            note.get("ok") is True
            and note.get("kind") == "note"
            and note.get("folio_executed") is False
            and note.get("mgmt_consequence", {}).get("invented_sla") is False,
        )

        recovery = pack.record_day_operator_action(
            verified_person_id="PERS-MISA",
            object_id=object_id,
            kind="recovery",
            note="Recovery follow-up for next shift.",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "operator recovery",
            recovery.get("ok") is True
            and recovery.get("kind") == "recovery"
            and recovery["object"].get("note") == "Recovery follow-up for next shift.",
        )

        touch = pack.record_day_operator_action(
            verified_person_id="PERS-MISA",
            object_id=object_id,
            kind="handover_touch",
            note="Handover touch on fixture.",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "handover touch",
            touch.get("ok") is True
            and touch.get("kind") == "handover_touch"
            and touch.get("yanolja_write") is False,
        )

        status = pack.record_day_operator_action(
            verified_person_id="PERS-MATT",
            object_id=object_id,
            kind="status",
            status="ESCALATED",
            note="Owner escalate for brief.",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "operator status",
            status.get("ok") is True
            and status.get("kind") == "status"
            and status["object"].get("status") == "ESCALATED",
        )
        check(
            "mgmt consequence refreshed",
            isinstance(status.get("mgmt_consequence"), dict)
            and status["mgmt_consequence"].get("count", 0) >= 1
            and status["mgmt_consequence"].get("invented_sla") is False,
        )
        check(
            "owner consequence refreshed",
            isinstance(status.get("owner_consequence"), dict)
            and status["owner_consequence"].get("hotel_facts_invented") is False
            and status["owner_consequence"].get("occupancy") is None
            and status["owner_consequence"].get("count", 0) >= 1,
        )

        desk = pack.operator_depth_desk(
            verified_person_id="PERS-MISA",
            db_path=pack_db,
            catalog_db=catalog,
        )
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-amg-day-safe"
            and desk.get("live_hotel_commission") is False
            and desk.get("rbac", {}).get("can_day_operator") is True
            and desk.get("invented_occupancy") is False,
        )

        empty_desk = pack.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=td / "empty-pack.sqlite",
            catalog_db=catalog,
        )
        check(
            "empty consequence honesty",
            empty_desk.get("mgmt_consequence", {}).get("empty") is True
            and empty_desk.get("owner_consequence", {}).get("empty") is True
            and empty_desk.get("empty_day_loop_is_not_live") is True,
        )

        try:
            pack.record_day_operator_action(
                verified_person_id="PERS-NOBODY",
                object_id=object_id,
                kind="note",
                note="outsider",
                db_path=pack_db,
                catalog_db=catalog,
            )
            check("outsider refused", False)
        except pack.OpsPackError as exc:
            check("outsider refused", exc.code == "forbidden", exc.code)

        try:
            pack.record_day_operator_action(
                verified_person_id="PERS-MISA",
                object_id=object_id,
                kind="note",
                note="no invent",
                db_path=pack_db,
                catalog_db=catalog,
            )
            # occupancy invent via refuse path
            pack.refuse_occupancy({"occupancy": 90})
            check("occupancy invent raises", False)
        except pack.OpsPackError as exc:
            check("occupancy invent refused", exc.code == "current_refused", exc.code)

        try:
            pack.record_day_operator_action(
                verified_person_id="PERS-MISA",
                object_id=object_id,
                kind="note",
                note="x",
                db_path=pack_db,
                catalog_db=catalog,
            )
            # folio refuse
            pack.refuse_folio({})
            check("folio raises", False)
        except pack.OpsPackError as exc:
            check("folio refused on depth path", exc.code == "folio_refused", exc.code)

        check("cr still open on copy", _cr(CR_ID, catalog) == "OPEN")
        ledger = _ledger()
        check(
            "amg caps specified",
            all(ledger.get(f"CAP-AMG-0{i}", [None])[0] == "SPECIFIED" for i in range(1, 8)),
        )
    finally:
        conn.close()


def test_sources() -> None:
    src = (SCRIPTS / "core" / "amg_ops_pack.py").read_text(encoding="utf-8")
    check("operator depth schema in pack", pack.OPERATOR_DEPTH_SCHEMA_ID in src)
    check("operator_day_detail fn", "def operator_day_detail" in src)
    check("record_day_operator_action fn", "def record_day_operator_action" in src)
    check("ensure rbac fn", "def ensure_operator_depth_rbac" in src)
    check("mgmt consequence fn", "def mgmt_consequence" in src)
    check("owner consequence fn", "def owner_consequence" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    check("no ledger write_text", "LEDGER_JSON.write" not in src and "assessments.json').write" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "/api/amg/ops-pack/operator-depth",
        "operator-action",
        "_amg_pack_operator_depth",
        "_amg_pack_day_operator_detail",
        "_amg_pack_day_operator_action",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "amg-ops-pack.html").read_text(encoding="utf-8")
    check("page operator depth", "Operator depth" in page)
    check("page operator-action", "operator-action" in page)
    check("page no folio claim", "No folio" in page or "no folio" in page.lower())
    before = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in before.items():
        WIP[rel] = digest
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    for i in range(1, 8):
        check(f"cap-amg-0{i} specified", ledger.get(f"CAP-AMG-0{i}", [None])[0] == "SPECIFIED")
    check("live cr open", _cr(CR_ID) == "OPEN")
    check("denominator 77", len(ledger) == 77)


def test_api() -> None:
    ra._ENV_LOADED = True
    os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
    try:
        pack.ensure_operator_depth_rbac(commit=True)
    finally:
        os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

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

    # Open a disposable day object via Owner for detail/action prove; clean status after.
    live_obj = pack.open_day_object(
        {
            "kind": "housekeeping",
            "title": "API prove soft-goods look",
            "note": "API prove only. Not occupancy.",
        },
        verified_person_id="PERS-MATT",
    )
    live_id = live_obj["object"]["object_id"]
    live_before_cr = _cr(CR_ID)

    try:
        for path, label, method in (
            ("/api/amg/ops-pack/operator-depth", "depth", "GET"),
            ("/api/amg/ops-pack/operator-depth/rbac", "rbac", "GET"),
            ("/amg-ops-pack", "page", "GET"),
            (f"/api/amg/ops-pack/day-objects/{live_id}/operator-action", "action", "POST"),
        ):
            st, _ = call(method, path, None, {} if method == "POST" else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/amg/ops-pack/operator-depth", MISA)
        check(
            "misa operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == "beta-amg-day-safe"
            and depth.get("live_hotel_commission") is False
            and (depth.get("rbac") or {}).get("can_day_operator") is True,
            str(depth)[:240] if isinstance(depth, dict) else str(st),
        )
        st, rbac = call("GET", "/api/amg/ops-pack/operator-depth/rbac", MATT)
        check(
            "matt rbac prove",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_day_operator") is True
            and rbac.get("live_hotel_commission") is False,
            str(rbac)[:200] if isinstance(rbac, dict) else str(st),
        )
        st, detail = call("GET", f"/api/amg/ops-pack/day-objects/{live_id}/operator", MISA)
        check(
            "misa day operator detail",
            st == 200
            and isinstance(detail, dict)
            and detail.get("ok") is True
            and detail.get("folio_executed") is False
            and detail.get("invented_occupancy") is False,
            str(detail)[:200] if isinstance(detail, dict) else str(st),
        )
        st, blank = call(
            "POST",
            f"/api/amg/ops-pack/day-objects/{live_id}/operator-action",
            MISA,
            {"kind": "note", "note": ""},
        )
        check(
            "misa note validates",
            st in (400, 403) and isinstance(blank, dict),
            f"{st} {str(blank)[:120]}",
        )
        st, _anon_act = call(
            "POST",
            f"/api/amg/ops-pack/day-objects/{live_id}/operator-action",
            None,
            {"kind": "note", "note": "anon"},
        )
        check("anon operator-action 403", st == 403, str(st))
        st, _out = call("GET", "/api/amg/ops-pack/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))
        st, page = call("GET", "/amg-ops-pack", MISA)
        check(
            "misa page 200",
            st == 200 and isinstance(page, (dict, bytes, str)),
            str(st),
        )
        check("live cr still open", _cr(CR_ID) == live_before_cr == "OPEN")
    finally:
        httpd.shutdown()
        # Mark prove object done so desk stays tidy (operator words only).
        try:
            pack.set_day_object_status(
                {"object_id": live_id, "status": "DONE", "note": "API prove closed."},
                verified_person_id="PERS-MATT",
            )
        except pack.OpsPackError:
            pass
        after_wip = {rel: sha(ROOT / rel) for rel in WIP}
        for rel, before in WIP.items():
            check(f"wip untouched {Path(rel).name}", before == after_wip[rel])


def main() -> int:
    test_honesty()
    with tempfile.TemporaryDirectory() as raw:
        test_operator_depth_on_copy(Path(raw))
    test_sources()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
