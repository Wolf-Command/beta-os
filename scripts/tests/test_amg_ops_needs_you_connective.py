#!/usr/bin/env python3
"""AMG Ops × Needs-You connective — AMG-scoped projection on the existing desk."""
from __future__ import annotations

import json
import os
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

from core import amg_ops_pack as pack  # noqa: E402
from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import wolf_shell  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "amg-ops-pack.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_AMG = (
    "CMQ-DEVI-UMA-MOBILE",
    "CMQ-NAS-HAIKAL",
    "CMQ-AMANDA-GGV",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-INTEGRATION-HEALTH",
    "CM-HABITAT-STAFF",
    "CM-PROGRESS-UX",
    "CM-UMA-CLOSER",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ids(strip: dict) -> set[str]:
    return {str(i.get("object_id")) for i in (strip.get("items") or [])}


def _cr(item_id: str) -> str:
    conn = sqlite3.connect(str(CATALOG))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row and row[0] else "MISSING"


def test_honesty() -> None:
    flags = pack.honesty_flags()
    check("desk bound", flags["bound"] == "beta-amg-ops-safe")
    check("day bound", flags["day_bound"] == "beta-amg-day-safe")
    check("connective bound", flags["connective_bound"] == pack.CONNECTIVE_BOUND)
    check("claim id", flags["connective_claim_id"] == pack.CONNECTIVE_CLAIM_ID)
    check("schema", flags["connective_schema"] == pack.CONNECTIVE_SCHEMA_ID)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("not staff_ready", flags["staff_ready"] is False and flags["invented_staff_ready"] is False)
    check("haikal not started", flags["haikal_human"] == "not_started")
    check("devi parked", flags["devi_retest"] == "parked")
    check("no live hotel", flags["live_hotel"] is False and flags["hotel_operations"] is False)
    check("occupancy empty", flags["occupancy"] is None and flags["invented_occupancy"] is False)
    check("no duplicate mutate", flags["duplicate_mutate_surface"] is False)
    check("false resolve false", flags["false_resolve_cr"] is False)
    check("shell flag", wolf_shell.honesty_flags().get("amg_ops_needs_you_connective") is True)
    try:
        pack.refuse_staff_ready({})
        check("staff_ready raises", False)
    except pack.OpsPackError as exc:
        check("staff_ready refused", exc.code == "staff_ready_refused")
    try:
        pack.refuse_haikal_done({})
        check("haikal raises", False)
    except pack.OpsPackError as exc:
        check("haikal refused", exc.code == "haikal_done_refused")
    try:
        pack.refuse_devi_done({})
        check("devi raises", False)
    except pack.OpsPackError as exc:
        check("devi refused", exc.code == "devi_done_refused")
    try:
        pack.refuse_occupancy({})
        check("occupancy raises", False)
    except pack.OpsPackError as exc:
        check("occupancy refused", exc.code == "current_refused")
    check(
        "refuse paths",
        pack.connective_refuse_code("/api/amg/ops-pack/haikal-done") == "haikal_done"
        and pack.connective_refuse_code("/api/amg/ops-pack/devi-done") == "devi_done"
        and pack.connective_refuse_code("/api/amg/ops-pack/needs-you/staff-ready") == "staff_ready"
        and pack.connective_refuse_code("/api/amg/ops-pack/needs-you/occupancy") == "occupancy"
        and pack.connective_refuse_code("/api/amg/ops-pack/needs-you/proven") == "proven",
    )
    check(
        "staff-ready read not stolen",
        pack.connective_refuse_code("/api/amg/ops-pack/staff-ready") is None,
    )


def test_projection_scope() -> None:
    owner = pack.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == pack.CONNECTIVE_BOUND)
    check("owner schema", owner.get("schema") == pack.CONNECTIVE_SCHEMA_ID)
    owner_ids = _ids(owner)
    check("owner not empty", owner.get("empty") is False and owner.get("count", 0) > 0, str(owner.get("count")))
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    by_kind = owner.get("by_kind") or {}
    check(
        "owner kind sum",
        sum(by_kind.get(k, 0) for k in pack.CONNECTIVE_KINDS) == owner.get("count"),
        str(by_kind),
    )
    check("owner sees amg morning", "CMQ-AMG-DAY" in owner_ids)
    check("owner sla not invented", by_kind.get("sla") == 0 and owner.get("invented_sla") is False)
    check("owner occupancy empty", owner.get("occupancy") is None and owner.get("live_hotel") is False)
    for oid in OUT_OF_AMG:
        check(f"owner excludes {oid}", oid not in owner_ids)
    check("owner next connective", (owner.get("next_action") or {}).get("code") == "needs_you_connective")
    check("owner next preferred", (owner.get("next_action") or {}).get("preferred_over_pack") is True)
    check(
        "owner next is amg morning",
        (owner.get("next_action") or {}).get("object_id") == "CMQ-AMG-DAY",
        str((owner.get("next_action") or {}).get("object_id")),
    )
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_amg") is True)
    caps = (owner.get("caps") or {}).get("caps") or {}
    for i in range(1, 8):
        cap = f"CAP-AMG-0{i}"
        check(f"{cap} SPECIFIED", caps.get(cap) == "SPECIFIED", str(caps.get(cap)))

    misa = pack.needs_you_connective_strip(verified_person_id="PERS-MISA")
    misa_ids = _ids(misa)
    check("misa strip ok", misa.get("ok") is True and misa.get("empty") is False)
    check("misa count honest", misa.get("count") == len(misa.get("items") or []))
    check("misa sees amg day", "CMQ-AMG-DAY" in misa_ids)
    check("misa not full owner", (misa.get("seat") or {}).get("sees_full_amg") is False)
    check("misa seat hotel", (misa.get("seat") or {}).get("seat") == "hotel_ops")
    for oid in OUT_OF_AMG:
        check(f"misa excludes {oid}", oid not in misa_ids)
    check(
        "misa next is amg morning",
        (misa.get("next_action") or {}).get("object_id") == "CMQ-AMG-DAY"
        and (misa.get("next_action") or {}).get("preferred_over_pack") is True,
        str((misa.get("next_action") or {}).get("object_id")),
    )
    check("misa sla empty", (misa.get("by_kind") or {}).get("sla") == 0)
    check("misa occupancy empty", misa.get("occupancy") is None and misa.get("live_hotel") is False)
    check("misa staff_ready false", misa.get("staff_ready") is False and misa.get("ready") is False)

    owner_only = {
        "kind": "morning_seed",
        "audience": "NEEDS_MATT",
        "who": "Matt",
        "title": "Owner AMG only",
        "capability": "CAP-AMG-04",
        "object_id": "CMQ-AMG-OWNER-ONLY",
    }
    misa_seat = pack.seat_for("PERS-MISA")
    owner_seat = pack.seat_for("PERS-MATT")
    check("seat misa present", isinstance(misa_seat, dict) and misa_seat.get("can_ops") is True)
    check(
        "misa misses owner-only row",
        pack._in_scope_for_seat(owner_only, misa_seat) is False,
    )
    check(
        "owner sees owner-only row",
        pack._in_scope_for_seat(owner_only, owner_seat) is True,
    )
    check("owner-only not live invented", "CMQ-AMG-OWNER-ONLY" not in owner_ids)

    for person, label in (
        ("PERS-AMANDA", "amanda"),
        ("PERS-HAIKAL", "haikal"),
        ("PERS-DEVI", "devi"),
        ("PERS-OUTSIDER", "outsider"),
    ):
        try:
            pack.needs_you_connective_strip(verified_person_id=person)
            check(f"{label} forbidden", False)
        except pack.OpsPackError as exc:
            check(f"{label} forbidden", exc.code == "forbidden")


def test_day_ops_and_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "amg.sqlite"
        opened = pack.open_day_object(
            {"kind": "housekeeping", "title": "Coral desk towel", "note": "operator words only"},
            verified_person_id="PERS-MISA",
            db_path=db,
        )
        oid = (opened.get("object") or {}).get("object_id")
        check("opened day object", bool(oid), str(opened)[:120])
        owner = pack.needs_you_connective_strip(
            verified_person_id="PERS-MATT",
            db_path=db,
        )
        misa = pack.needs_you_connective_strip(
            verified_person_id="PERS-MISA",
            db_path=db,
        )
        check("owner sees day ops", oid in _ids(owner))
        check("misa sees day ops", oid in _ids(misa))
        check(
            "day ops kind counted",
            (owner.get("by_kind") or {}).get("day_ops", 0) >= 1,
        )
        check("day still not hotel", owner.get("occupancy") is None and owner.get("live_hotel") is False)
        row = next(i for i in owner.get("items") or [] if i.get("object_id") == oid)
        hand = row.get("handoff") or {}
        check(
            "day handoff reuses depth",
            hand.get("reuse_day_ops") is True
            and hand.get("duplicate_mutate_surface") is False
            and str(hand.get("action") or "").endswith("/next-action-touch"),
        )
        detail = pack.connective_item_detail(oid, verified_person_id="PERS-MISA", db_path=db)
        check("misa day detail", detail.get("ok") is True and detail.get("reuse_needs_you_depth") is False)
        try:
            pack.acknowledge_handoff(oid, verified_person_id="PERS-MISA", db_path=db)
            check("day ack not second surface", False)
        except pack.OpsPackError as exc:
            check("day ack handoff only", exc.code == "handoff_only" and exc.http_status == 405)

        empty_db = Path(tmp) / "empty.sqlite"
        pack._connect(empty_db).close()
        parked = Path(tmp) / "parked.json"
        parked.write_text(
            json.dumps(
                {
                    "items": {
                        "CMQ-AMG-DAY": {
                            "operator_status": "PARKED",
                            "staff_ready": False,
                            "commissioned": False,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        quiet = pack.needs_you_connective_strip(
            verified_person_id="PERS-MATT",
            db_path=empty_db,
            state_path=parked,
        )
        check("missing state empty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("missing state next none", quiet.get("next_action") is None)
        check("missing state message", bool(quiet.get("empty_message")))
        check("missing not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)


def test_desk_prefers_connective() -> None:
    owner = pack.build_board(verified_person_id="PERS-MATT")
    nxt = owner.get("next_action") or {}
    check(
        "desk owner prefers connective",
        nxt.get("code") == "needs_you_connective" and nxt.get("preferred_over_pack") is True,
    )
    check("desk owner strip present", isinstance(owner.get("needs_you_connective"), dict))
    check("desk owner pack fallback kept", (owner.get("pack_next_action") or {}).get("code") == "pack_href")
    check("desk honesty staff_ready", (owner.get("honesty") or {}).get("staff_ready") is False)
    check("desk no occupancy", owner.get("occupancy") is None and owner.get("yanolja_called") is False)
    check(
        "desk owner object",
        nxt.get("object_id") == "CMQ-AMG-DAY",
        str(nxt.get("object_id")),
    )

    misa = pack.build_board(verified_person_id="PERS-MISA")
    check(
        "desk misa prefers own",
        (misa.get("next_action") or {}).get("object_id") == "CMQ-AMG-DAY",
        str((misa.get("next_action") or {}).get("object_id")),
    )
    check("desk misa seat", (misa.get("seat") or {}).get("person_id") == "PERS-MISA")
    check("desk day loop kept", isinstance(misa.get("day_loop"), dict))


def test_detail_and_ack() -> None:
    detail = pack.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-MISA")
    check("misa detail ok", detail.get("ok") is True)
    handoff = detail.get("handoff") or {}
    check(
        "handoff reuses depth",
        handoff.get("reuse_needs_you_depth") is True
        and handoff.get("duplicate_mutate_surface") is False
        and str(handoff.get("acknowledge") or "").startswith("/api/progress/needs-you/items/")
        and str(handoff.get("staff_acknowledge") or "").startswith("/api/staff/ops-routing/needs-you/items/")
        and str(handoff.get("amg_acknowledge") or "").endswith("/acknowledge"),
    )
    check("detail human flags", detail.get("haikal_human") == "not_started" and detail.get("devi_retest") == "parked")
    check("detail no hotel", detail.get("occupancy") is None and detail.get("live_hotel") is False)
    try:
        pack.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-AMANDA")
        check("amanda detail forbidden", False)
    except pack.OpsPackError as exc:
        check("amanda detail 403", exc.code == "forbidden")
    try:
        pack.connective_item_detail("CMQ-DEVI-UMA-MOBILE", verified_person_id="PERS-MATT")
        check("devi not amg", False)
    except pack.OpsPackError as exc:
        check("devi not amg 404", exc.code == "not_found")
    try:
        pack.connective_item_detail("CMQ-NAS-HAIKAL", verified_person_id="PERS-MISA")
        check("haikal not amg", False)
    except pack.OpsPackError as exc:
        check("haikal not amg 404", exc.code == "not_found")
    try:
        pack.connective_item_detail("does-not-exist", verified_person_id="PERS-MATT")
        check("missing detail", False)
    except pack.OpsPackError as exc:
        check("missing detail 404", exc.code == "not_found")

    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        events = Path(tmp) / "events.jsonl"
        try:
            pack.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-AMANDA",
                state_path=state,
                events_path=events,
            )
            check("wrong scope ack refused", False)
        except pack.OpsPackError as exc:
            check("wrong scope ack 403", exc.code == "forbidden")
        check("wrong scope wrote nothing", not state.exists() and not events.exists())
        try:
            pack.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-HAIKAL",
                state_path=state,
                events_path=events,
            )
            check("haikal ack refused", False)
        except pack.OpsPackError as exc:
            check("haikal ack 403", exc.code == "forbidden")

        ack = pack.acknowledge_handoff(
            "CMQ-AMG-DAY",
            verified_person_id="PERS-MISA",
            note="amg day operator saw it",
            state_path=state,
            events_path=events,
        )
        check("ack ok", ack.get("ok") is True and ack.get("recorded") is True)
        check(
            "ack not staff_ready",
            ack.get("staff_ready") is False and ack.get("proven") is False and ack.get("ready") is False,
        )
        check(
            "ack not human done",
            ack.get("haikal_human") == "not_started" and ack.get("devi_retest") == "parked",
        )
        check("ack not commissioned", ack.get("commissioned") is False and ack.get("cr_resolved") is False)
        check("ack no hotel", ack.get("occupancy") is None and ack.get("live_hotel") is False)
        check(
            "ack same surface",
            ack.get("duplicate_mutate_surface") is False and ack.get("reuse_needs_you_depth") is True,
        )
        event = ack.get("event") or {}
        check(
            "ack actor misa",
            event.get("person_id") == "PERS-MISA" and event.get("human_commissioned") is False,
        )
        saved = json.loads(state.read_text(encoding="utf-8"))
        row = (saved.get("items") or {}).get("CMQ-AMG-DAY") or {}
        check(
            "state acknowledged",
            row.get("operator_status") == "ACKNOWLEDGED" and row.get("staff_ready") is False,
        )
        check(
            "state not commissioned",
            row.get("commissioned") is False and row.get("haikal_human") == "not_started",
        )


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for i in range(1, 8):
        cap = f"CAP-AMG-0{i}"
        check(f"ledger {cap}", ledger.get(cap, [None])[0] == "SPECIFIED", str(ledger.get(cap, [None])[0]))
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    for cr in pack.AMG_TARGET_CRS:
        check(f"amg cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html empty honesty", "EMPTY" in text and "staff_ready" in text)
    check("html single now", text.count('id="now"') == 1)
    check("html no occupancy invent", "Not live hotel occupancy" in text)
    check("no orphan dashboard", not (ROOT / "dashboards" / "amg-ops-needs-you.html").exists())
    before = subprocess.check_output(["git", "hash-object"] + list(WIP), cwd=str(ROOT), text=True)
    check("wip hashes readable", len(before.split()) == 4, before[:80])


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
        for path in (
            "/api/amg/ops-pack",
            "/api/amg/ops-pack/needs-you",
            "/api/amg/ops-pack/needs-you/items/CMQ-AMG-DAY",
            "/amg-ops-pack",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path.split('/')[-1]}", st == 403, str(st))

        st, payload = call("GET", "/api/amg/ops-pack/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == pack.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http occupancy", payload.get("occupancy") is None and payload.get("live_hotel") is False)
        check("owner http has amg row", "CMQ-AMG-DAY" in _ids(payload))
        check("owner http excludes devi", "CMQ-DEVI-UMA-MOBILE" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))

        st, payload = call("GET", "/api/amg/ops-pack", MISA)
        check(
            "misa desk 200",
            st == 200 and (payload.get("next_action") or {}).get("code") == "needs_you_connective",
            str((payload.get("next_action") or {}).get("code")),
        )
        check(
            "misa desk object",
            (payload.get("next_action") or {}).get("object_id") == "CMQ-AMG-DAY",
        )
        check("misa desk strip", (payload.get("needs_you_connective") or {}).get("empty") is False)

        st, payload = call("GET", "/api/amg/ops-pack/needs-you/items/CMQ-AMG-DAY", AMANDA)
        check("amanda wrong seat 403", st == 403 and (payload or {}).get("error") == "forbidden", str(st))

        st, payload = call("GET", "/api/amg/ops-pack/needs-you/items/CMQ-AMG-DAY", MISA)
        check(
            "misa own detail 200",
            st == 200 and (payload.get("handoff") or {}).get("reuse_needs_you_depth") is True,
        )

        st, _ = call("GET", "/api/amg/ops-pack/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, _ = call("GET", "/api/amg/ops-pack/needs-you", DEVI)
        check("devi http 403", st == 403, str(st))
        st, _ = call("GET", "/api/amg/ops-pack/needs-you", HAIKAL)
        check("haikal http 403", st == 403, str(st))
        st, _ = call("GET", "/api/amg/ops-pack/needs-you", AMANDA)
        check("amanda http 403", st == 403, str(st))

        st, payload = call(
            "POST",
            "/api/amg/ops-pack/needs-you/items/CMQ-AMG-DAY/acknowledge",
            AMANDA,
            {"note": "no"},
        )
        check("ack wrong seat 403", st == 403, str(payload)[:160])

        st, payload = call(
            "POST",
            "/api/amg/ops-pack/needs-you/items/CMQ-AMG-DAY/acknowledge",
            MISA,
            {"note": "amg connective prove"},
        )
        check("ack misa 200", st == 200 and payload.get("recorded") is True, str(payload)[:180])
        check("ack http staff_ready false", payload.get("staff_ready") is False and payload.get("commissioned") is False)
        check("ack http no hotel", payload.get("occupancy") is None and payload.get("live_hotel") is False)
        event = payload.get("event") or {}
        check("ack http actor", event.get("person_id") == "PERS-MISA" and event.get("human_commissioned") is False)

        st, payload = call("POST", "/api/amg/ops-pack/haikal-done", MATT, {})
        check("haikal-done refuse", st == 405 and payload.get("error") == "haikal_done_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/ops-pack/devi-done", MATT, {})
        check("devi-done refuse", st == 405 and payload.get("error") == "devi_done_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/ops-pack/needs-you/staff-ready", MATT, {})
        check("staff-ready refuse", st == 405 and payload.get("error") == "staff_ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/ops-pack/needs-you/occupancy", MATT, {})
        check("occupancy refuse", st == 405 and payload.get("error") == "current_refused", str(payload)[:120])
        st, payload = call("POST", "/api/amg/ops-pack/proven", MATT, {})
        check("proven still refused", st == 405 and payload.get("error") == "proven_refused", str(payload)[:80])
        st, payload = call("POST", "/api/amg/ops-pack/ready", MATT, {})
        check("ready still refused", st == 405 and payload.get("error") == "ready_refused", str(payload)[:80])

        st, raw = call("GET", "/amg-ops-pack", MISA)
        check("misa page 200", st == 200, str(st))
        if isinstance(raw, (bytes, bytearray)):
            check("page has connective", b"Needs-You connective" in raw)
        else:
            check("page has connective", False, type(raw).__name__)
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
    test_honesty()
    test_projection_scope()
    test_day_ops_and_empty()
    test_desk_prefers_connective()
    test_detail_and_ack()
    test_crs_and_files()
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
