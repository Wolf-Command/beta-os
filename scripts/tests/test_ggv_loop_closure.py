#!/usr/bin/env python3
"""Sprint2 P2 GGV loop closure — Habitat loop desk on Beta."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import ggv_ops_pack as pack  # noqa: E402
from core import lead_spine as spine  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-f089b11530ab4673"
CLIENT_CR = "CR-ccb3287dabe91d4b"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
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


def _lead_id(conn: sqlite3.Connection, source_id: str) -> str:
    row = conn.execute(
        """
        SELECT lead_id FROM core_leads
        WHERE brand_id='habitat' AND source_system='fixture' AND source_id=?
        """,
        (source_id,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"missing fixture {source_id}")
    return str(row[0])


def test_honesty_and_schema() -> None:
    flags = pack.honesty_flags()
    check("loop bound present", flags.get("loop_bound") == "beta-ggv-loop-safe")
    check("ops bound kept", flags.get("bound") == "beta-ggv-ops-safe")
    check("cap built", flags["ledger_maturity"] == "BUILT" and flags["proven"] is False and flags["ready"] is False)
    check("cr open", flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
    check("client cr open", flags["client_cr_state"] == "OPEN")
    schema = pack.schema_document()
    check("14 loop stages", schema["loop_stages"] == list(pack.LOOP_STAGES) and len(schema["loop_stages"]) == 14)
    check("loop schema id", schema["loop_schema_id"] == "wolf.ggv-loop-closure.v1")
    cv = pack.client_visibility_strip()
    check(
        "client visibility empty",
        cv["empty"] is True and cv["live_client_report"] is False and cv["rows"] == [],
    )
    eng = pack.engagement_scaffold()
    check("engagement scaffold empty", eng["empty"] is True and eng["revenue"] is None and eng["contract"] is False)
    try:
        pack.refuse_external_crm({})
        check("crm raises", False)
    except pack.OpsPackError as exc:
        check("crm refused", exc.code == "crm_refused")
    try:
        pack.refuse_proven({})
        check("proven raises", False)
    except pack.OpsPackError as exc:
        check("proven refused", exc.code == "proven_refused")


def test_loop_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    shutil.copy(CATALOG, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        lead_id = _lead_id(conn, "demo-01")
        before_events = conn.execute(
            "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
            (lead_id,),
        ).fetchone()[0]

        board = pack.build_board(verified_person_id="PERS-AMANDA", conn=conn)
        check("board has loop", isinstance(board.get("loop"), dict) and board["loop"]["bound"] == "beta-ggv-loop-safe")
        check(
            "board has mgmt exceptions",
            isinstance(board.get("management_exceptions"), dict)
            and board["management_exceptions"]["invented_sla"] is False,
        )
        check(
            "board performance read",
            board["performance"]["metricool_write"] is False
            and board["performance"]["invented_metrics"] is False,
        )
        check(
            "board client visibility empty",
            board["client_visibility"]["empty"] is True
            and board["client_visibility"]["live_client_report"] is False,
        )
        check(
            "content work strip",
            board["content_work"]["metricool_write"] is False
            and board["content_work"]["approved_is_not_published"] is True,
        )

        card = next(row for row in board["leads"] if row["lead_id"] == lead_id)
        check("loop progress on card", "identity_contact" in (card.get("loop") or {}).get("stages", {}))
        check("loop next present", isinstance(card.get("loop_next_action"), dict))

        try:
            pack.qualify_lead(lead_id, "qualified", "  ", verified_person_id="PERS-AMANDA", conn=conn)
            check("blank qualify raises", False)
        except pack.OpsPackError as exc:
            check("qualify note required", exc.code == "invalid")

        idn = pack.note_identity_contact(
            lead_id,
            "Habitat fixture contact noted. Not a CRM write.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("identity noted", idn["ok"] is True and idn["action"] == "identity_contact")
        check(
            "identity stage done",
            idn["loop"]["stages"]["identity_contact"]["status"] == "done",
        )

        own = pack.assign_loop_owner(
            lead_id,
            "PERS-HAIKAL",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("owner assigned", own["lead"]["owner_person_id"] == "PERS-HAIKAL")

        qual = pack.qualify_lead(
            lead_id,
            "qualified",
            "Fixture is in scope for Habitat content work.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check(
            "qualified",
            qual["ok"] is True
            and qual["loop"]["stages"]["qualification"]["status"] == "done"
            and qual["loop"]["stages"]["qualification"]["decision"] == "qualified",
        )

        moved = pack.move_lifecycle(
            lead_id,
            "ACTIVE",
            "Draft Habitat proposal outline.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("lifecycle with next action", moved["lead"]["wolf_lifecycle"] == "ACTIVE")
        check(
            "next action stage done",
            moved["lead"]["loop"]["stages"]["next_action"]["status"] == "done",
        )

        eng = pack.record_proposal_engagement(
            lead_id,
            "proposal",
            "Outline sent as operator note. Not a contract.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check(
            "engagement recorded",
            eng["ok"] is True
            and eng["loop"]["stages"]["proposal_engagement"]["status"] == "done"
            and eng["loop"]["stages"]["proposal_engagement"]["kind"] == "proposal",
        )

        due = pack.set_due(
            lead_id,
            (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Follow up on the fixture proposal.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("due recorded", due["ok"] is True)

        raised = pack.raise_management_exception(
            lead_id,
            "Fixture waiting on reply past operator due.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("mgmt exception raised", raised["ok"] is True)

        mgmt = pack.management_exceptions(conn)
        mgmt_ids = {row["lead_id"] for row in mgmt["exceptions"]}
        check("lead on mgmt strip", lead_id in mgmt_ids and mgmt["invented_sla"] is False)
        row = next(r for r in mgmt["exceptions"] if r["lead_id"] == lead_id)
        check(
            "mgmt reasons honest",
            "operator_raised" in row["reasons"]
            and "operator_due_passed" in row["reasons"]
            and row["sla_breached"] is None,
        )

        other = spine.ingest_observation(
            entity_id="ENT-BZG",
            brand_id="BZG-UMA",
            source_system="fixture",
            source_id="loop-other-brand",
            source_observed_at="2026-09-22T01:00:00Z",
            source_stage="new",
            provenance={"demo": True, "label": "OTHER BRAND LOOP"},
            actor_type="SYSTEM",
            conn=conn,
        )
        other_id = other["lead"]["lead_id"]
        try:
            pack.qualify_lead(
                other_id,
                "qualified",
                "Must not cross brands.",
                verified_person_id="PERS-MATT",
                conn=conn,
            )
            check("cross brand qualify raises", False)
        except pack.OpsPackError as exc:
            check("cross brand isolated", exc.code == "brand_isolated")

        after_events = conn.execute(
            "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
            (lead_id,),
        ).fetchone()[0]
        check("events appended", after_events > before_events)

        # Source stage must stay append-only.
        src = conn.execute(
            "SELECT source_stage FROM core_leads WHERE lead_id=?",
            (lead_id,),
        ).fetchone()[0]
        check("source stage held", src == "new")
    finally:
        conn.close()
    check("live cr untouched", _cr(CR_ID) == "OPEN" and _cr(CLIENT_CR) == "OPEN")


def test_sources() -> None:
    src = (SCRIPTS / "core" / "ggv_ops_pack.py").read_text(encoding="utf-8")
    check("loop bound in pack", "beta-ggv-loop-safe" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    check("no klaviyo reader call path invent", "habitat_klaviyo_reader" not in src)
    spine_src = (SCRIPTS / "core" / "lead_spine.py").read_text(encoding="utf-8")
    for evt in (
        "identity_contact_noted",
        "qualification_recorded",
        "engagement_recorded",
        "due_recorded",
        "mgmt_exception_raised",
    ):
        check(f"spine event {evt}", evt in spine_src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for route in (
        "/api/ggv/ops-pack/loop",
        "/api/ggv/ops-pack/management-exceptions",
        "/api/ggv/ops-pack/performance",
        "/api/ggv/ops-pack/client-visibility",
        "/api/ggv/ops-pack/content-work",
        "_ggv_ops_loop_action",
    ):
        check(f"route {route}", route in serve)
    page = (ROOT / "dashboards" / "ggv-ops-pack.html").read_text(encoding="utf-8")
    check("page loop bound", "beta-ggv-loop-safe" in page)
    check("page not proven", "Not PROVEN" in page and "Not READY" in page)
    check("page mgmt", "Management exceptions" in page)
    check("page performance", "DERIVE read" in page)
    for rel in WIP:
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())


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
    live = sqlite3.connect(str(CATALOG))
    try:
        live_id = _lead_id(live, "demo-02")
        live_before = live.execute(
            "SELECT wolf_stage, owner_person_id, source_stage FROM core_leads WHERE lead_id=?",
            (live_id,),
        ).fetchone()
        live_events = live.execute(
            "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
            (live_id,),
        ).fetchone()[0]
    finally:
        live.close()

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
        st, _anon = call("GET", "/api/ggv/ops-pack/loop", None)
        check("anon loop 403", st == 403, str(st))
        st, _anon_mgmt = call("GET", "/api/ggv/ops-pack/management-exceptions", None)
        check("anon mgmt 403", st == 403, str(st))
        st, _anon_perf = call("GET", "/api/ggv/ops-pack/performance", None)
        check("anon performance 403", st == 403, str(st))
        st, _out = call("GET", "/api/ggv/ops-pack/loop", OUTSIDER)
        check("outsider loop 403", st == 403, str(st))
        st, loop = call("GET", "/api/ggv/ops-pack/loop", MATT)
        check("owner loop 200", st == 200 and isinstance(loop, dict) and loop.get("ok") is True, str(loop)[:200])
        if isinstance(loop, dict):
            check("loop bound", loop.get("bound") == "beta-ggv-loop-safe")
            check("loop no invent", loop.get("invented_leads") is False and loop.get("external_crm_write") is False)
        st, mgmt = call("GET", "/api/ggv/ops-pack/management-exceptions", AMANDA)
        check(
            "amanda mgmt 200",
            st == 200 and isinstance(mgmt, dict) and mgmt.get("invented_sla") is False,
            str(mgmt)[:180],
        )
        st, perf = call("GET", "/api/ggv/ops-pack/performance", HAIKAL)
        check(
            "haikal performance 200",
            st == 200
            and isinstance(perf, dict)
            and perf.get("metricool_write") is False
            and perf.get("invented_metrics") is False,
            str(perf)[:200],
        )
        st, cv = call("GET", "/api/ggv/ops-pack/client-visibility", MATT)
        check(
            "client visibility empty",
            st == 200 and isinstance(cv, dict) and cv.get("empty") is True and cv.get("live_client_report") is False,
        )
        st, _blank = call(
            "POST",
            f"/api/ggv/ops-pack/leads/{live_id}/qualify",
            MATT,
            {"decision": "qualified", "note": "   "},
        )
        check("live blank qualify 400", st == 400, str(_blank)[:180])
        st, missing = call(
            "POST",
            "/api/ggv/ops-pack/leads/LEAD-missing/qualify",
            AMANDA,
            {"decision": "qualified", "note": "No such fixture."},
        )
        check("missing qualify 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found")
        for method, path in (
            ("POST", "/api/ggv/ops-pack/metricool"),
            ("POST", "/api/ggv/ops-pack/crm"),
            ("POST", "/api/ggv/ops-pack/proven"),
            ("POST", "/api/ggv/ops-pack/resolve"),
        ):
            code, body = call(method, path, MATT, {})
            check(f"{method} {path} refused", code == 405, str(body)[:160])
        st, _anon_post = call(
            "POST",
            f"/api/ggv/ops-pack/leads/{live_id}/qualify",
            None,
            {"decision": "qualified", "note": "anon must fail"},
        )
        check("anon qualify 403", st == 403, str(st))
    finally:
        httpd.shutdown()
    live = sqlite3.connect(str(CATALOG))
    try:
        after = live.execute(
            "SELECT wolf_stage, owner_person_id, source_stage FROM core_leads WHERE lead_id=?",
            (live_id,),
        ).fetchone()
        after_events = live.execute(
            "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
            (live_id,),
        ).fetchone()[0]
        check("live fixture unchanged", after == live_before and after_events == live_events)
    finally:
        live.close()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger untouched", ledger.get("CAP-GGV-04", [None])[0] == "BUILT" and len(ledger) == 77)


def main() -> int:
    test_honesty_and_schema()
    with tempfile.TemporaryDirectory(prefix="ggv-loop-") as raw:
        test_loop_on_copy(Path(raw))
    test_sources()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
