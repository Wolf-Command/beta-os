#!/usr/bin/env python3
"""GGV ops pack — Habitat lifecycle, Needs You, empty client/project, publish-gate read."""
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
MISA = "mlsary111@gmail.com"
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


def _stage(conn: sqlite3.Connection, lead_id: str) -> tuple[str | None, str | None]:
    row = conn.execute(
        "SELECT wolf_stage, source_stage FROM core_leads WHERE lead_id=?",
        (lead_id,),
    ).fetchone()
    return (row[0], row[1])


def test_matrix_and_honesty() -> None:
    seats = {row["person_id"]: row for row in pack.permission_matrix()}
    check("four seats", set(seats) == {"PERS-MATT", "PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA"})
    check("owner closes", seats["PERS-MATT"]["can_close"] is True and "CLOSED" in seats["PERS-MATT"]["lifecycle"])
    check("amanda closes", seats["PERS-AMANDA"]["can_close"] is True)
    check("haikal no close", seats["PERS-HAIKAL"]["can_close"] is False and "CLOSED" not in seats["PERS-HAIKAL"]["lifecycle"])
    check("misa no close", seats["PERS-MISA"]["can_close"] is False and seats["PERS-MISA"]["seat"] == "crew")
    check("outsider forbidden", pack.seat_for("PERS-DEVI") is None)
    framework = pack.client_project_framework()
    check("framework empty", framework["empty"] is True and framework["rows"] == [] and framework["recorded_count"] == 0)
    check(
        "empty is not profitability",
        framework["empty_is_profitability"] is False
        and framework["live_profitability"] is False
        and framework["revenue"] is None
        and framework["on_disk"] is False,
    )
    flags = pack.honesty_flags()
    check("cap stays built", flags["cap"] == "CAP-GGV-04" and flags["ledger_maturity"] == "BUILT")
    check("not invented prove", flags["invented_proven"] is False and flags["invented_ready"] is False and flags["proven"] is False and flags["ready"] is False)
    check("cr open", flags["cr_id"] == CR_ID and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
    check("client cr open", flags["client_cr_id"] == CLIENT_CR and flags["client_cr_state"] == "OPEN")
    check("bound", flags["bound"] == "beta-ggv-ops-safe")
    try:
        pack.refuse_metricool({})
        check("metricool raises", False)
    except pack.OpsPackError as exc:
        check("metricool refused", exc.code == "metricool_refused")
    try:
        pack.refuse_klaviyo({})
        check("klaviyo raises", False)
    except pack.OpsPackError as exc:
        check("klaviyo refused", exc.code == "klaviyo_refused")
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
    try:
        pack.refuse_resolve({})
        check("resolve raises", False)
    except pack.OpsPackError as exc:
        check("resolve refused", exc.code == "resolve_refused")
    try:
        pack.guard_brand("BZG-UMA")
        check("brand guard", False)
    except pack.OpsPackError as exc:
        check("other brand isolated", exc.code == "brand_isolated")


def test_lifecycle_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    shutil.copy(CATALOG, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        lead_id = _lead_id(conn, "demo-01")
        before_wolf, before_source = _stage(conn, lead_id)
        try:
            pack.move_lifecycle(lead_id, "ACTIVE", "  ", verified_person_id="PERS-MATT", conn=conn)
            check("blank next action raises", False)
        except pack.OpsPackError as exc:
            check("next action required", exc.code == "next_action_required")
        wolf_after_blank, source_after_blank = _stage(conn, lead_id)
        check("blank did not move", wolf_after_blank == before_wolf and source_after_blank == before_source)

        try:
            pack.move_lifecycle(
                lead_id,
                "CLOSED",
                "Haikal must not close this fixture.",
                verified_person_id="PERS-HAIKAL",
                conn=conn,
            )
            check("haikal close raises", False)
        except pack.OpsPackError as exc:
            check("haikal close forbidden", exc.code == "forbidden")
        try:
            pack.move_lifecycle(
                lead_id,
                "CLOSED",
                "Misa must not close this fixture.",
                verified_person_id="PERS-MISA",
                conn=conn,
            )
            check("misa close raises", False)
        except pack.OpsPackError as exc:
            check("misa close forbidden", exc.code == "forbidden")
        wolf_still, source_still = _stage(conn, lead_id)
        check("crew did not close", wolf_still == before_wolf and source_still == before_source)

        for stage, text in (
            ("ACTIVE", "Call the fixture lead back."),
            ("PARKED", "Wait for the fixture reply."),
            ("CLOSED", "Stop chasing this fixture. Closed is not a sale."),
        ):
            moved = pack.move_lifecycle(
                lead_id,
                stage,
                text,
                verified_person_id="PERS-MATT",
                conn=conn,
            )
            check(f"owner {stage}", moved["ok"] is True and moved["lead"]["wolf_lifecycle"] == stage)
            check(f"next action {stage}", moved["recorded_next_action"] == text)
            check(f"source held {stage}", moved["lead"]["source_stage"] == before_source)
        closed = pack.move_lifecycle(
            lead_id,
            "OPEN",
            "Amanda reopens the fixture.",
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check("amanda reopens", closed["lead"]["wolf_lifecycle"] == "OPEN" and closed["seat"]["seat"] == "content_management")
        wolf_now, source_now = _stage(conn, lead_id)
        check("source unchanged", source_now == before_source and wolf_now == "OPEN")

        other = spine.ingest_observation(
            entity_id="ENT-BZG",
            brand_id="BZG-UMA",
            source_system="fixture",
            source_id="ops-pack-other-brand",
            source_observed_at="2026-09-21T01:00:00Z",
            source_stage="new",
            provenance={"demo": True, "label": "OTHER BRAND"},
            actor_type="SYSTEM",
            conn=conn,
        )
        other_id = other["lead"]["lead_id"]
        try:
            pack.move_lifecycle(
                other_id,
                "ACTIVE",
                "Must not cross brands.",
                verified_person_id="PERS-MATT",
                conn=conn,
            )
            check("cross brand raises", False)
        except pack.OpsPackError as exc:
            check("cross brand isolated", exc.code == "brand_isolated")
        board = pack.build_board(verified_person_id="PERS-HAIKAL", conn=conn)
        ids = [row["lead_id"] for row in board["leads"]]
        check("board hides other brand", other_id not in ids and all(row["brand_id"] == "habitat" for row in board["leads"]))
        isolation = board["isolation"]
        check(
            "isolation counts only",
            isolation["other_brand_cards"] == []
            and isolation["other_brand_lead_rows"].get("BZG-UMA") == 1
            and isolation["isolated"] is True
            and isolation["external_crm_not_read"] is True,
        )
        silent = spine.ingest_observation(
            entity_id="ENT-GGV",
            brand_id="habitat",
            source_system="fixture",
            source_id="ops-pack-no-clock",
            source_observed_at=None,
            source_stage="new",
            provenance={"demo": True, "label": "NO CLOCK"},
            actor_type="SYSTEM",
            conn=conn,
        )
        waiting = spine.ingest_observation(
            entity_id="ENT-GGV",
            brand_id="habitat",
            source_system="fixture",
            source_id="ops-pack-waiting",
            source_observed_at=(datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source_stage="new",
            provenance={"demo": True, "label": "WAITING"},
            actor_type="SYSTEM",
            conn=conn,
        )
        exceptions = pack.speed_exceptions(conn)
        ex_ids = {row["lead_id"] for row in exceptions["exceptions"]}
        check("no clock is not a breach", silent["lead"]["lead_id"] not in ex_ids and exceptions["sla_breached"] is None)
        check("waiting is needs you", waiting["lead"]["lead_id"] in ex_ids and exceptions["invented_sla"] is False)
        waiting_row = next(row for row in exceptions["exceptions"] if row["lead_id"] == waiting["lead"]["lead_id"])
        check(
            "needs you has no sla",
            waiting_row["aging"]["needs_you"] is True
            and waiting_row["aging"]["kind"] == "needs_you"
            and waiting_row["aging"]["sla_breached"] is None
            and waiting_row["aging"]["sla_target_seconds"] is None,
        )
        check("framework still empty", board["framework"]["empty"] is True and board["framework"]["live_profitability"] is False)
        gate = board["publish_gate"]
        check(
            "publish gate read",
            gate["metricool_write"] is False
            and gate["real_external_publish"] == "NO"
            and all(item["write_performed"] is False and item["metricool"] == "DISABLED" for item in gate["items"]),
        )
        check("honesty on board", board["honesty"]["cr_state"] == "OPEN" and board["honesty"]["maturity"] == "BUILT")
    finally:
        conn.close()
    check("live cr untouched", _cr(CR_ID) == "OPEN" and _cr(CLIENT_CR) == "OPEN")


def test_sources() -> None:
    src = (SCRIPTS / "core" / "ggv_ops_pack.py").read_text(encoding="utf-8")
    check("no uma import", "uma_ops" not in src and "bzg_" not in src)
    check("no klaviyo reader", "habitat_klaviyo_reader" not in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/ggv/ops-pack" in serve)
    check("lifecycle route", "/lifecycle" in serve and "_ggv_ops_lifecycle" in serve)
    check("page route", "/ggv-ops-pack" in serve)
    check("metricool route refused", "/api/ggv/ops-pack/metricool" in serve)
    check("klaviyo route refused", "/api/ggv/ops-pack/klaviyo" in serve)
    check("crm route refused", "/api/ggv/ops-pack/crm" in serve)
    check("proven route refused", "/api/ggv/ops-pack/proven" in serve)
    check("resolve route refused", "/api/ggv/ops-pack/resolve" in serve)
    check("beta port", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "ggv-ops-pack.html").read_text(encoding="utf-8")
    check("page bound", "beta-ggv-ops-safe" in page)
    check("page not proven", "Not PROVEN" in page and "Not READY" in page)
    check("page no metricool write", "does not write Metricool" in page)
    check("page empty framework", "not live profitability" in page)
    check("page cr", "does not resolve the completion row" in page)
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
        live_id = _lead_id(live, "demo-01")
        live_before = _stage(live, live_id)
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
        st, _anon = call("GET", "/api/ggv/ops-pack", None)
        check("anon GET 403", st == 403, str(st))
        st, _out = call("GET", "/api/ggv/ops-pack", OUTSIDER)
        check("outsider GET 403", st == 403, str(st))
        st, _brand = call("GET", "/api/ggv/ops-pack?brand=BZG-UMA", MATT)
        check("owner other brand 403", st == 403, str(_brand)[:180])
        st, owner = call("GET", "/api/ggv/ops-pack", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner seat", owner.get("person_id") == "PERS-MATT" and (owner.get("seat") or {}).get("can_close") is True)
            check("owner no sla invent", owner.get("invented_sla") is False and owner.get("sla_breached") is None)
            check("owner framework empty", (owner.get("framework") or {}).get("empty") is True and owner.get("live_profitability") is False)
            check("owner metricool off", owner.get("metricool_write") is False and (owner.get("publish_gate") or {}).get("metricool_write") is False)
            flags = owner.get("honesty") or {}
            check("owner cr open", flags.get("cr_state") == "OPEN" and flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            ex = (owner.get("exceptions") or {}).get("exceptions") or []
            check(
                "exceptions are not breaches",
                all((row.get("aging") or {}).get("sla_breached") is None for row in ex),
            )
        st, amanda = call("GET", "/api/ggv/ops-pack/permissions", AMANDA)
        check("amanda permissions", st == 200 and isinstance(amanda, dict) and (amanda.get("seat") or {}).get("seat") == "content_management", str(amanda)[:180])
        st, haikal = call("GET", "/api/ggv/ops-pack/exceptions", HAIKAL)
        check("haikal exceptions", st == 200 and isinstance(haikal, dict) and haikal.get("invented_sla") is False, str(haikal)[:180])
        st, misa = call("GET", "/api/ggv/ops-pack/publish-gate", MISA)
        check("misa gate read", st == 200 and isinstance(misa, dict) and misa.get("metricool_write") is False, str(misa)[:180])
        st, page = call("GET", "/ggv-ops-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page_ok = call("GET", "/ggv-ops-pack", HAIKAL)
        check("haikal page 200", st == 200 and isinstance(page_ok, (bytes, bytearray)) and b"beta-ggv-ops-safe" in page_ok)
        st, _blank = call(
            "POST",
            f"/api/ggv/ops-pack/leads/{live_id}/lifecycle",
            MATT,
            {"wolf_stage": "ACTIVE", "next_action": "   "},
        )
        check("live blank next action 400", st == 400, str(_blank)[:180])
        st, _crew = call(
            "POST",
            f"/api/ggv/ops-pack/leads/{live_id}/lifecycle",
            HAIKAL,
            {"wolf_stage": "CLOSED", "next_action": "Do not close the live fixture."},
        )
        check("live haikal close 403", st == 403, str(_crew)[:180])
        st, missing = call(
            "POST",
            "/api/ggv/ops-pack/leads/LEAD-missing/lifecycle",
            AMANDA,
            {"wolf_stage": "ACTIVE", "next_action": "No such fixture."},
        )
        check("missing lead 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        for method, path in (
            ("POST", "/api/ggv/ops-pack/metricool"),
            ("POST", "/api/ggv/ops-pack/klaviyo"),
            ("POST", "/api/ggv/ops-pack/crm"),
            ("POST", "/api/ggv/ops-pack/proven"),
            ("POST", "/api/ggv/ops-pack/ready"),
            ("POST", "/api/ggv/ops-pack/resolve"),
            ("PUT", "/api/ggv/ops-pack"),
            ("PATCH", "/api/ggv/ops-pack/production"),
        ):
            code, body = call(method, path, MATT, {})
            check(f"{method} {path} refused", code == 405, str(body)[:160])
        st, _anon_post = call("POST", "/api/ggv/ops-pack/metricool", None, {})
        check("anon POST 403", st == 403, str(st))
    finally:
        httpd.shutdown()
    live = sqlite3.connect(str(CATALOG))
    try:
        check("live fixture unchanged", _stage(live, live_id) == live_before)
    finally:
        live.close()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger untouched", ledger.get("CAP-GGV-04", [None])[0] == "BUILT" and len(ledger) == 77)


def main() -> int:
    test_matrix_and_honesty()
    with tempfile.TemporaryDirectory(prefix="ggv-ops-pack-") as raw:
        test_lifecycle_on_copy(Path(raw))
    test_sources()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
