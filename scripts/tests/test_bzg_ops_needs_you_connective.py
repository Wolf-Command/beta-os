#!/usr/bin/env python3
"""BZG Ops × Needs-You connective — BZG/Uma projection on the existing Uma desk."""
from __future__ import annotations

import json
import os
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

from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
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
HTML = ROOT / "dashboards" / "bzg-uma-blu.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_BZG = (
    "CMQ-AMG-DAY",
    "CMQ-AMANDA-GGV",
    "CMQ-NAS-HAIKAL",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-INTEGRATION-HEALTH",
)
CAP_EXPECT = {
    "CAP-BZG-01": "BUILT",
    "CAP-BZG-02": "SPECIFIED",
    "CAP-BZG-03": "READY",
    "CAP-BZG-04": "SPECIFIED",
    "CAP-BZG-05": "SPECIFIED",
    "CAP-BZG-06": "SPECIFIED",
    "CAP-BZG-07": "SPECIFIED",
}


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
    flags = ops.honesty_flags()
    check("desk bound", flags["bound"] == "beta-bzg-loop-safe")
    check("connective bound", flags["connective_bound"] == ops.CONNECTIVE_BOUND)
    check("claim id", flags["connective_claim_id"] == ops.CONNECTIVE_CLAIM_ID)
    check("schema", flags["connective_schema"] == ops.CONNECTIVE_SCHEMA_ID)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("not staff_ready", flags["staff_ready"] is False and flags["invented_staff_ready"] is False)
    check("haikal not started", flags["haikal_human"] == "not_started")
    check("devi parked", flags["devi_retest"] == "parked")
    check("no money", flags["money"] is None and flags["payment_execution"] == "NOT_BUILT")
    check("no compose", flags["bzg_compose"] is False)
    check("no live devi commission", flags["live_devi_commission"] is False)
    check("no duplicate mutate", flags["duplicate_mutate_surface"] is False)
    check("false resolve false", flags["false_resolve_cr"] is False)
    check("shell flag", wolf_shell.honesty_flags().get("bzg_ops_needs_you_connective") is True)
    try:
        ops.refuse_staff_ready({})
        check("staff_ready raises", False)
    except ops.UmaOpsError as exc:
        check("staff_ready refused", exc.code == "staff_ready_refused" and exc.http_status == 405)
    try:
        ops.refuse_haikal_done({})
        check("haikal raises", False)
    except ops.UmaOpsError as exc:
        check("haikal refused", exc.code == "haikal_done_refused")
    try:
        ops.refuse_devi_done({})
        check("devi raises", False)
    except ops.UmaOpsError as exc:
        check("devi refused", exc.code == "devi_done_refused")
    try:
        ops.refuse_money({})
        check("money raises", False)
    except ops.UmaOpsError as exc:
        check("money refused", exc.code == "money_refused")
    check(
        "refuse paths",
        ops.connective_refuse_code("/api/bzg/uma-blu/haikal-done") == "haikal_done"
        and ops.connective_refuse_code("/api/bzg/uma-blu/devi-done") == "devi_done"
        and ops.connective_refuse_code("/api/bzg/uma-blu/needs-you/staff-ready") == "staff_ready"
        and ops.connective_refuse_code("/api/bzg/uma-blu/needs-you/money") == "money"
        and ops.connective_refuse_code("/api/bzg/uma-blu/needs-you/proven") == "proven",
    )
    check(
        "staff-ready read not stolen",
        ops.connective_refuse_code("/api/bzg/uma-blu/staff-ready") is None,
    )


def test_projection_scope() -> None:
    owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == ops.CONNECTIVE_BOUND)
    check("owner schema", owner.get("schema") == ops.CONNECTIVE_SCHEMA_ID)
    owner_ids = _ids(owner)
    check("owner not empty", owner.get("empty") is False and owner.get("count", 0) > 0, str(owner.get("count")))
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    by_kind = owner.get("by_kind") or {}
    check(
        "owner kind sum",
        sum(by_kind.get(k, 0) for k in ops.CONNECTIVE_KINDS) == owner.get("count"),
        str(by_kind),
    )
    check("owner sees uma morning", "CMQ-DEVI-UMA-MOBILE" in owner_ids)
    check("owner money empty", owner.get("money") is None and owner.get("payment_execution") is False)
    check("owner no compose", owner.get("bzg_compose") is False)
    check("owner devi not commissioned", owner.get("live_devi_commission") is False)
    for oid in OUT_OF_BZG:
        check(f"owner excludes {oid}", oid not in owner_ids)
    check("owner next connective", (owner.get("next_action") or {}).get("code") == "needs_you_connective")
    check("owner next preferred", (owner.get("next_action") or {}).get("preferred_over_pack") is True)
    check(
        "owner next is uma morning",
        (owner.get("next_action") or {}).get("object_id") == "CMQ-DEVI-UMA-MOBILE",
        str((owner.get("next_action") or {}).get("object_id")),
    )
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_bzg") is True)
    caps = (owner.get("caps") or {}).get("caps") or {}
    for cap, expect in CAP_EXPECT.items():
        check(f"{cap} {expect}", caps.get(cap) == expect, str(caps.get(cap)))

    devi = ops.needs_you_connective_strip(verified_person_id="PERS-DEVI")
    devi_ids = _ids(devi)
    check("devi strip ok", devi.get("ok") is True and devi.get("empty") is False)
    check("devi count honest", devi.get("count") == len(devi.get("items") or []))
    check("devi sees uma morning", "CMQ-DEVI-UMA-MOBILE" in devi_ids)
    check("devi not full owner", (devi.get("seat") or {}).get("sees_full_bzg") is False)
    check("devi seat uma", (devi.get("seat") or {}).get("seat") == "uma_ops")
    check("devi commission not invented", (devi.get("seat") or {}).get("invented_commission") is False)
    check("devi retest parked", devi.get("devi_retest") == "parked" and devi.get("live_devi_commission") is False)
    for oid in OUT_OF_BZG:
        check(f"devi excludes {oid}", oid not in devi_ids)
    check(
        "devi next preferred",
        (devi.get("next_action") or {}).get("preferred_over_pack") is True
        and (devi.get("next_action") or {}).get("object_id") == "CMQ-DEVI-UMA-MOBILE",
    )

    for person in ("PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA", "PERS-OUTSIDER"):
        try:
            ops.needs_you_connective_strip(verified_person_id=person)
            check(f"{person} forbidden", False)
        except ops.UmaOpsError as exc:
            check(f"{person} forbidden", exc.code == "forbidden" and exc.http_status == 403)

    detail = ops.connective_item_detail("CMQ-DEVI-UMA-MOBILE", verified_person_id="PERS-MATT")
    check(
        "owner detail reuse",
        detail.get("reuse_needs_you_depth") is True
        and (detail.get("handoff") or {}).get("duplicate_mutate_surface") is False,
    )
    check("detail money empty", detail.get("money") is None and detail.get("payment_execution") is False)
    try:
        ops.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-MATT")
        check("foreign detail 404", False)
    except ops.UmaOpsError as exc:
        check("foreign detail 404", exc.code == "not_found" and exc.http_status == 404)
    try:
        ops.connective_item_detail("CMQ-DEVI-UMA-MOBILE", verified_person_id="PERS-AMANDA")
        check("amanda detail forbidden", False)
    except ops.UmaOpsError as exc:
        check("amanda detail forbidden", exc.code == "forbidden")

    devi_detail = ops.connective_item_detail(
        "CMQ-DEVI-UMA-MOBILE", verified_person_id="PERS-DEVI"
    )
    check("devi own detail", devi_detail.get("ok") is True and devi_detail.get("human_done") is False)


def test_owner_only_and_ops_loop() -> None:
    real = ops._commissioning_rows

    def _with_owner_only(*, state_path=None):
        rows = real(state_path=state_path)
        rows.append(
            {
                "object_id": "CMQ-BZG-OWNER-ONLY",
                "kind": "needs_you",
                "title": "Owner only BZG commissioning",
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "person_to_test": "Matt",
                "priority": "P0",
                "business": "BZG",
                "surface": "uma_ops",
                "href": "/bzg/uma-blu",
            }
        )
        return rows

    ops._commissioning_rows = _with_owner_only
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        devi = ops.needs_you_connective_strip(verified_person_id="PERS-DEVI")
        check("owner sees owner-only", "CMQ-BZG-OWNER-ONLY" in _ids(owner))
        check("devi misses owner-only", "CMQ-BZG-OWNER-ONLY" not in _ids(devi))
        check(
            "owner-only not on devi next",
            (devi.get("next_action") or {}).get("object_id") != "CMQ-BZG-OWNER-ONLY",
        )
    finally:
        ops._commissioning_rows = real

    real_loop = ops._ops_loop_rows

    def _one_loop(*, conn=None):
        return [
            {
                "object_id": "LOOP-ORD-FIXTURE",
                "kind": "ops_loop",
                "title": "Fixture ordered PR",
                "audience": "NEEDS_STAFF",
                "priority": "P1",
                "business": "BZG",
                "brand_id": "BZG-UMA",
                "href": "/bzg/uma-blu/bills",
                "open_href": "/bzg/uma-blu",
                "invented": False,
                "payment_execution": False,
                "money": None,
            }
        ]

    ops._ops_loop_rows = _one_loop
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        devi = ops.needs_you_connective_strip(verified_person_id="PERS-DEVI")
        check("owner sees ops loop", "LOOP-ORD-FIXTURE" in _ids(owner))
        check("devi sees ops loop", "LOOP-ORD-FIXTURE" in _ids(devi))
        check("ops loop not invented money", owner.get("money") is None)
        detail = ops.connective_item_detail("LOOP-ORD-FIXTURE", verified_person_id="PERS-DEVI")
        check(
            "ops loop handoff reuse",
            (detail.get("handoff") or {}).get("reuse_ops_loop") is True
            and detail.get("reuse_needs_you_depth") is False,
        )
        try:
            ops.acknowledge_handoff("LOOP-ORD-FIXTURE", verified_person_id="PERS-DEVI", note="no")
            check("ops loop ack 405", False)
        except ops.UmaOpsError as exc:
            check("ops loop ack handoff_only", exc.code == "handoff_only" and exc.http_status == 405)
    finally:
        ops._ops_loop_rows = real_loop


def test_empty_and_unauthorised_devi() -> None:
    real_rows = ops._bzg_candidates
    ops._bzg_candidates = lambda **_k: []
    try:
        quiet = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        check("empty honesty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("empty next null", quiet.get("next_action") is None)
        check("empty not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)
        check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
    finally:
        ops._bzg_candidates = real_rows

    with tempfile.TemporaryDirectory() as td:
        bare = Path(td) / "empty.sqlite"
        sqlite3.connect(bare).close()
        check("devi not authorised on bare catalog", ops._devi_already_authorised(bare) is False)
        try:
            ops.needs_you_connective_strip(verified_person_id="PERS-DEVI", catalog_db=bare)
            check("bare devi forbidden", False)
        except ops.UmaOpsError as exc:
            check(
                "bare devi forbidden",
                exc.code == "forbidden" and "not invented" in str(exc).lower(),
            )
        owner = ops.needs_you_connective_strip(
            verified_person_id="PERS-MATT", catalog_db=bare
        )
        check("owner still full without devi catalog", (owner.get("seat") or {}).get("sees_full_bzg") is True)


def test_acknowledge_temp_state() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = Path(td) / "state.json"
        events = Path(td) / "events.jsonl"
        ack = ops.acknowledge_handoff(
            "CMQ-DEVI-UMA-MOBILE",
            verified_person_id="PERS-DEVI",
            note="bzg connective prove",
            state_path=state,
            events_path=events,
        )
        check("ack recorded", ack.get("recorded") is True and ack.get("commissioned") is False)
        check("ack no human done", ack.get("human_done") is False and ack.get("devi_retest") == "parked")
        check("ack no money", ack.get("money") is None and ack.get("payment_execution") is False)
        check(
            "ack same surface",
            ack.get("duplicate_mutate_surface") is False and ack.get("reuse_needs_you_depth") is True,
        )
        event = ack.get("event") or {}
        check(
            "ack actor devi",
            event.get("person_id") == "PERS-DEVI" and event.get("human_commissioned") is False,
        )
        saved = json.loads(state.read_text(encoding="utf-8"))
        row = (saved.get("items") or {}).get("CMQ-DEVI-UMA-MOBILE") or {}
        check(
            "state acknowledged",
            row.get("operator_status") == "ACKNOWLEDGED" and row.get("staff_ready") is False,
        )
        check(
            "state not commissioned",
            row.get("commissioned") is False and row.get("haikal_human") == "not_started",
        )
        try:
            ops.acknowledge_handoff(
                "CMQ-DEVI-UMA-MOBILE",
                verified_person_id="PERS-HAIKAL",
                note="no",
                state_path=state,
                events_path=events,
            )
            check("ack haikal forbidden", False)
        except ops.UmaOpsError as exc:
            check("ack haikal forbidden", exc.code == "forbidden")


def test_desk_prefers_connective() -> None:
    today = ops.today_cards(person_id="PERS-MATT")
    check("today ok", today.get("ok") is True)
    check("today strip", isinstance(today.get("needs_you_connective"), dict))
    check(
        "today count matches",
        (today.get("needs_you_connective") or {}).get("count")
        == len((today.get("needs_you_connective") or {}).get("items") or []),
    )
    nxt = today.get("next_action") or {}
    check(
        "today next preferred",
        nxt.get("code") == "needs_you_connective" and nxt.get("preferred_over_pack") is True,
        str(nxt.get("code")),
    )
    check("today keeps intel", isinstance(today.get("intel_connective"), dict))
    check("today pack next kept", isinstance(today.get("pack_next_action"), dict))
    check("today no money", today.get("payment_execution") in (False, "NOT_BUILT") or (today.get("honesty") or {}).get("payment_executed") is False)
    loop = ops.loop_desk(person_id="PERS-DEVI")
    check("loop strip", isinstance(loop.get("needs_you_connective"), dict))
    check(
        "loop next preferred",
        (loop.get("next_action") or {}).get("code") == "needs_you_connective",
        str((loop.get("next_action") or {}).get("code")),
    )
    check("loop base kept", isinstance(loop.get("loop_next_action"), dict))
    check("loop no payment", loop.get("payment_execution") is False)


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap, expect in CAP_EXPECT.items():
        check(f"ledger {cap}", ledger.get(cap, [None])[0] == expect, str(ledger.get(cap, [None])[0]))
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    for cr in ops.BZG_TARGET_CRS:
        check(f"bzg cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html empty honesty", "EMPTY" in text and "staff_ready" in text)
    check("html devi parked", "Devi retest stays parked" in text)
    check("html no money", "Not money" in text)
    check("html single now", text.count('id="now"') == 1)
    check("no orphan dashboard", not (ROOT / "dashboards" / "bzg-ops-needs-you.html").exists())
    source = (SCRIPTS / "core" / "uma_ops_console.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.bzg-ops-needs-you-connective.v1" in source)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve route", "/api/bzg/uma-blu/needs-you" in serve)
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
            "/api/bzg/uma-blu/needs-you",
            "/api/bzg/uma-blu/today",
            "/api/bzg/uma-blu/needs-you/items/CMQ-DEVI-UMA-MOBILE",
            "/bzg/uma-blu",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path.rsplit('/', 1)[-1]}", st == 403, str(st))

        st, payload = call("GET", "/api/bzg/uma-blu/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == ops.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http money", payload.get("money") is None and payload.get("payment_execution") is False)
        check("owner http has uma row", "CMQ-DEVI-UMA-MOBILE" in _ids(payload))
        check("owner http excludes amg", "CMQ-AMG-DAY" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))
        check("owner http devi parked", payload.get("devi_retest") == "parked")

        st, payload = call("GET", "/api/bzg/uma-blu/today", DEVI)
        check(
            "devi desk 200",
            st == 200 and (payload.get("next_action") or {}).get("code") == "needs_you_connective",
            str((payload.get("next_action") or {}).get("code")),
        )
        check(
            "devi desk object",
            (payload.get("next_action") or {}).get("object_id") == "CMQ-DEVI-UMA-MOBILE",
        )
        check("devi desk strip", (payload.get("needs_you_connective") or {}).get("empty") is False)

        st, payload = call("GET", "/api/bzg/uma-blu/needs-you/items/CMQ-DEVI-UMA-MOBILE", AMANDA)
        check("amanda wrong seat 403", st == 403, str(st))

        st, payload = call("GET", "/api/bzg/uma-blu/needs-you/items/CMQ-DEVI-UMA-MOBILE", DEVI)
        check(
            "devi own detail 200",
            st == 200 and (payload.get("handoff") or {}).get("reuse_needs_you_depth") is True,
        )

        st, payload = call("GET", "/api/bzg/uma-blu/needs-you/items/CMQ-AMG-DAY", MATT)
        check("foreign http 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))

        st, _ = call("GET", "/api/bzg/uma-blu/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, _ = call("GET", "/api/bzg/uma-blu/needs-you", HAIKAL)
        check("haikal http 403", st == 403, str(st))
        st, _ = call("GET", "/api/bzg/uma-blu/needs-you", MISA)
        check("misa http 403", st == 403, str(st))
        st, _ = call("GET", "/api/bzg/uma-blu/needs-you", AMANDA)
        check("amanda http 403", st == 403, str(st))

        st, payload = call(
            "POST",
            "/api/bzg/uma-blu/needs-you/items/CMQ-DEVI-UMA-MOBILE/acknowledge",
            AMANDA,
            {"note": "no"},
        )
        check("ack wrong seat 403", st == 403, str(st))

        st, payload = call(
            "POST",
            "/api/bzg/uma-blu/needs-you/items/CMQ-DEVI-UMA-MOBILE/acknowledge",
            DEVI,
            {"note": "bzg connective http prove"},
        )
        check("ack devi 200", st == 200 and payload.get("recorded") is True, str(payload)[:180])
        check("ack http staff_ready false", payload.get("staff_ready") is False and payload.get("commissioned") is False)
        check("ack http no money", payload.get("money") is None and payload.get("payment_execution") is False)
        event = payload.get("event") or {}
        check("ack http actor", event.get("person_id") == "PERS-DEVI" and event.get("human_commissioned") is False)

        st, payload = call("POST", "/api/bzg/uma-blu/haikal-done", MATT, {})
        check("haikal-done refuse", st == 405 and payload.get("error") == "haikal_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/bzg/uma-blu/devi-done", MATT, {})
        check("devi-done refuse", st == 405 and payload.get("error") == "devi_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/bzg/uma-blu/needs-you/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/bzg/uma-blu/needs-you/money", MATT, {})
        check("money route refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
    finally:
        httpd.shutdown()


def main() -> None:
    test_honesty()
    test_projection_scope()
    test_owner_only_and_ops_loop()
    test_empty_and_unauthorised_devi()
    test_acknowledge_temp_state()
    test_desk_prefers_connective()
    test_crs_and_files()
    test_http()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        raise SystemExit(1)
    print("EXIT: SUCCESS")


if __name__ == "__main__":
    main()
