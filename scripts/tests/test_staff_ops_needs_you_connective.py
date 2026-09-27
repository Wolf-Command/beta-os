#!/usr/bin/env python3
"""Staff Ops × Needs-You connective — per-seat projection + handoff."""
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

from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import staff_ops_routing as sor  # noqa: E402
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
HTML = ROOT / "dashboards" / "staff-ops-routing.html"
PROGRESS = ROOT / "dashboards" / "progress.html"
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
    flags = sor.honesty_flags()
    check("bound desk", flags["bound"] == "beta-connective-safe")
    check("connective bound", flags["connective_bound"] == sor.CONNECTIVE_BOUND)
    check("claim id", flags["connective_claim_id"] == sor.CONNECTIVE_CLAIM_ID)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("not staff_ready", flags["staff_ready"] is False and flags["invented_staff_ready"] is False)
    check("haikal not started", flags["haikal_human"] == "not_started")
    check("devi parked", flags["devi_retest"] == "parked")
    check("no duplicate mutate", flags["duplicate_mutate_surface"] is False)
    check("shell flag", wolf_shell.honesty_flags().get("staff_ops_needs_you_connective") is True)
    try:
        sor.refuse_staff_ready({})
        check("staff_ready raises", False)
    except sor.StaffOpsRoutingError as exc:
        check("staff_ready refused", exc.code == "staff_ready_refused")
    try:
        sor.refuse_haikal_done({})
        check("haikal raises", False)
    except sor.StaffOpsRoutingError as exc:
        check("haikal refused", exc.code == "haikal_done_refused")
    try:
        sor.refuse_devi_done({})
        check("devi raises", False)
    except sor.StaffOpsRoutingError as exc:
        check("devi refused", exc.code == "devi_done_refused")
    check(
        "refuse paths",
        sor.refuse_code("/api/staff/ops-routing/staff-ready") == "staff_ready"
        and sor.refuse_code("/api/staff/ops-routing/haikal-done") == "haikal_done"
        and sor.refuse_code("/api/staff/ops-routing/devi-done") == "devi_done",
    )


def test_projection_scope() -> None:
    owner = sor.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == sor.CONNECTIVE_BOUND)
    check("owner not empty", owner.get("empty") is False and owner.get("count", 0) > 0, str(owner.get("count")))
    owner_ids = _ids(owner)
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    by_kind = owner.get("by_kind") or {}
    check(
        "owner kind sum",
        sum(by_kind.get(k, 0) for k in sor.CONNECTIVE_KINDS) == owner.get("count"),
        str(by_kind),
    )
    check("owner has morning", "CMQ-NAS-HAIKAL" in owner_ids and "CMQ-DEVI-UMA-MOBILE" in owner_ids)
    check("owner has waiting", "CM-HABITAT-STAFF" in owner_ids)
    check("owner has needs you", "CM-PROGRESS-UX" in owner_ids)
    check("no policy kind", all(i.get("kind") != "policy" for i in owner.get("items") or []))
    check("owner next connective", (owner.get("next_action") or {}).get("code") == "needs_you_connective")
    check("owner next not invented", (owner.get("next_action") or {}).get("invented") is False)
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    caps = owner.get("caps") or {}
    check("CAP-CORE-11 SPECIFIED", caps.get("CAP-CORE-11") == "SPECIFIED", str(caps.get("CAP-CORE-11")))
    check("CAP-CORE-12 BUILT", caps.get("CAP-CORE-12") == "BUILT", str(caps.get("CAP-CORE-12")))

    amanda = sor.needs_you_connective_strip(verified_person_id="PERS-AMANDA")
    amanda_ids = _ids(amanda)
    check("amanda count honest", amanda.get("count") == len(amanda_ids))
    check("amanda sees own morning", "CMQ-AMANDA-GGV" in amanda_ids)
    check("amanda sees shared habitat", "CM-HABITAT-STAFF" in amanda_ids)
    check("amanda misses haikal nas", "CMQ-NAS-HAIKAL" not in amanda_ids)
    check("amanda misses devi", "CMQ-DEVI-UMA-MOBILE" not in amanda_ids)
    check("amanda misses matt nav", "CMQ-GLOBAL-NAV-OWNER" not in amanda_ids)
    check("amanda misses amg coral", "CMQ-AMG-DAY" not in amanda_ids)
    check(
        "amanda next is her morning",
        (amanda.get("next_action") or {}).get("object_id") == "CMQ-AMANDA-GGV",
        str((amanda.get("next_action") or {}).get("object_id")),
    )

    haikal = sor.needs_you_connective_strip(verified_person_id="PERS-HAIKAL")
    haikal_ids = _ids(haikal)
    check("haikal sees nas", "CMQ-NAS-HAIKAL" in haikal_ids and "CMQ-SMART-UPLOAD-RETEST" in haikal_ids)
    check("haikal misses devi", "CMQ-DEVI-UMA-MOBILE" not in haikal_ids)
    check("haikal misses amanda-only", "CMQ-AMANDA-GGV" not in haikal_ids)
    check(
        "haikal next nas",
        (haikal.get("next_action") or {}).get("object_id") == "CMQ-NAS-HAIKAL",
        str((haikal.get("next_action") or {}).get("object_id")),
    )
    check("haikal human flag", haikal.get("haikal_human") == "not_started")

    devi = sor.needs_you_connective_strip(verified_person_id="PERS-DEVI")
    devi_ids = _ids(devi)
    check("devi sees uma", "CMQ-DEVI-UMA-MOBILE" in devi_ids)
    check("devi misses nas", "CMQ-NAS-HAIKAL" not in devi_ids)
    check("devi retest parked", devi.get("devi_retest") == "parked")
    check(
        "devi next uma",
        (devi.get("next_action") or {}).get("object_id") == "CMQ-DEVI-UMA-MOBILE",
        str((devi.get("next_action") or {}).get("object_id")),
    )

    misa = sor.needs_you_connective_strip(verified_person_id="PERS-MISA")
    check("misa empty", misa.get("empty") is True and misa.get("count") == 0, str(misa.get("count")))
    check("misa no invented next", misa.get("next_action") is None)
    check("misa empty message", bool(misa.get("empty_message")))


def test_desk_prefers_connective() -> None:
    owner = sor.build_desk(verified_person_id="PERS-MATT")
    nxt = owner.get("next_action") or {}
    check("desk owner prefers connective", nxt.get("code") == "needs_you_connective" and nxt.get("preferred_over_pack") is True)
    check("desk owner strip present", isinstance(owner.get("needs_you_connective"), dict))
    check("desk still trio", {c.get("pack") for c in owner.get("cards") or []} == {"bzg", "ggv", "amg"})
    check("desk honesty staff_ready", (owner.get("honesty") or {}).get("staff_ready") is False)

    amanda = sor.build_desk(verified_person_id="PERS-AMANDA")
    check(
        "desk amanda prefers own",
        (amanda.get("next_action") or {}).get("object_id") == "CMQ-AMANDA-GGV",
        str((amanda.get("next_action") or {}).get("object_id")),
    )
    check("desk amanda home ggv", (amanda.get("home") or {}).get("pack") == "ggv")

    misa = sor.build_desk(verified_person_id="PERS-MISA")
    check(
        "desk misa falls back to pack",
        (misa.get("next_action") or {}).get("code") != "needs_you_connective",
        str((misa.get("next_action") or {}).get("code")),
    )
    check("desk misa strip empty", (misa.get("needs_you_connective") or {}).get("empty") is True)


def test_detail_and_ack() -> None:
    detail = sor.connective_item_detail("CMQ-AMANDA-GGV", verified_person_id="PERS-AMANDA")
    check("amanda detail ok", detail.get("ok") is True)
    handoff = detail.get("handoff") or {}
    check(
        "handoff reuses depth",
        handoff.get("reuse_needs_you_depth") is True
        and handoff.get("duplicate_mutate_surface") is False
        and handoff.get("acknowledge", "").startswith("/api/progress/needs-you/items/"),
    )
    check("detail human flags", detail.get("haikal_human") == "not_started" and detail.get("devi_retest") == "parked")
    try:
        sor.connective_item_detail("CMQ-NAS-HAIKAL", verified_person_id="PERS-AMANDA")
        check("amanda nas detail forbidden", False)
    except sor.StaffOpsRoutingError as exc:
        check("amanda nas detail 403", exc.code == "forbidden")
    try:
        sor.connective_item_detail("does-not-exist", verified_person_id="PERS-MATT")
        check("missing detail", False)
    except sor.StaffOpsRoutingError as exc:
        check("missing detail 404", exc.code == "not_found")

    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        events = Path(tmp) / "events.jsonl"
        try:
            sor.acknowledge_handoff(
                "CMQ-NAS-HAIKAL",
                verified_person_id="PERS-AMANDA",
                state_path=state,
                events_path=events,
            )
            check("wrong scope ack refused", False)
        except sor.StaffOpsRoutingError as exc:
            check("wrong scope ack 403", exc.code == "forbidden")
        check("wrong scope wrote nothing", not state.exists() and not events.exists())

        ack = sor.acknowledge_handoff(
            "CMQ-AMANDA-GGV",
            verified_person_id="PERS-AMANDA",
            note="seat saw it",
            state_path=state,
            events_path=events,
        )
        check("ack ok", ack.get("ok") is True and ack.get("recorded") is True)
        check("ack not staff_ready", ack.get("staff_ready") is False and ack.get("proven") is False and ack.get("ready") is False)
        check("ack not human done", ack.get("haikal_human") == "not_started" and ack.get("devi_retest") == "parked")
        check("ack not commissioned", ack.get("commissioned") is False and ack.get("cr_resolved") is False)
        check("ack same surface", ack.get("duplicate_mutate_surface") is False and ack.get("reuse_needs_you_depth") is True)
        event = ack.get("event") or {}
        check("ack actor amanda", event.get("person_id") == "PERS-AMANDA" and event.get("human_commissioned") is False)
        saved = json.loads(state.read_text(encoding="utf-8"))
        row = (saved.get("items") or {}).get("CMQ-AMANDA-GGV") or {}
        check("state acknowledged", row.get("operator_status") == "ACKNOWLEDGED" and row.get("staff_ready") is False)
        check("state not commissioned", row.get("commissioned") is False and row.get("haikal_human") == "not_started")


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger 11", ledger.get("CAP-CORE-11", [None])[0] == "SPECIFIED")
    check("ledger 12", ledger.get("CAP-CORE-12", [None])[0] == "BUILT")
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    for cr in nye.TARGET_CRS:
        check(f"cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text)
    check("html empty honesty", "EMPTY" in text and "staff_ready" in text)
    progress = PROGRESS.read_text(encoding="utf-8")
    check("progress links staff ops", "/staff-ops-routing" in progress and "needs-you-depth" in progress)
    check("no orphan dashboard", not (ROOT / "dashboards" / "staff-ops-needs-you.html").exists())
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
            "/api/staff/ops-routing",
            "/api/staff/ops-routing/needs-you",
            "/api/staff/ops-routing/needs-you/items/CMQ-NAS-HAIKAL",
            "/staff-ops-routing",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path.split('/')[-1]}", st == 403, str(st))

        st, payload = call("GET", "/api/staff/ops-routing/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == sor.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)

        st, payload = call("GET", "/api/staff/ops-routing", AMANDA)
        check("amanda desk 200", st == 200 and (payload.get("next_action") or {}).get("code") == "needs_you_connective")
        check("amanda desk strip", (payload.get("needs_you_connective") or {}).get("empty") is False)

        st, payload = call("GET", "/api/staff/ops-routing/needs-you/items/CMQ-NAS-HAIKAL", AMANDA)
        check("amanda wrong scope 403", st == 403 and (payload or {}).get("error") == "forbidden", str(st))

        st, payload = call("GET", "/api/staff/ops-routing/needs-you/items/CMQ-AMANDA-GGV", AMANDA)
        check("amanda own detail 200", st == 200 and (payload.get("handoff") or {}).get("reuse_needs_you_depth") is True)

        st, payload = call("GET", "/api/staff/ops-routing/needs-you", MISA)
        check("misa http empty", st == 200 and payload.get("empty") is True and payload.get("count") == 0)

        st, _ = call("GET", "/api/staff/ops-routing/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("POST", "/api/staff/ops-routing/needs-you/items/CMQ-NAS-HAIKAL/acknowledge", AMANDA, {"note": "no"})
        check("ack wrong scope 403", st == 403, str(payload)[:160])

        st, payload = call("POST", "/api/staff/ops-routing/staff-ready", MATT, {})
        check("staff-ready refuse", st == 405 and payload.get("error") == "staff_ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/staff/ops-routing/haikal-done", MATT, {})
        check("haikal-done refuse", st == 405 and payload.get("error") == "haikal_done_refused", str(payload)[:120])
        st, payload = call("POST", "/api/staff/ops-routing/devi-done", MATT, {})
        check("devi-done refuse", st == 405 and payload.get("error") == "devi_done_refused", str(payload)[:120])
        st, payload = call("POST", "/api/staff/ops-routing/proven", MATT, {})
        check("proven still refused", st == 405 and payload.get("error") == "proven_refused", str(payload)[:80])

        st, raw = call("GET", "/staff-ops-routing", HAIKAL)
        check("haikal page 200", st == 200, str(st))
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
