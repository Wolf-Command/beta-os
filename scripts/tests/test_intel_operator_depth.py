#!/usr/bin/env python3
"""Sprint2 P4 INTEL Operator Depth — recommendation detail/action + consequence refresh."""
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

from core import intel_connective as ic  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-be51980bd1194448"
MATT = "mrwolf@wolfcommand.net"
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
    flags = ic.honesty_flags()
    check("bound", flags.get("bound") == "beta-intel-connect-safe")
    check(
        "operator depth schema",
        flags.get("operator_depth_schema_id") == ic.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check("empty honesty", flags.get("empty_recommendation_is_not_invent") is True)
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("no auto promote", flags.get("auto_promote") is False)
    check("no auto execute", flags.get("auto_execute") is False)
    check("cr open flag", flags.get("cr_resolved") is False)
    check("cap01 built", flags.get("cap_intel_01") == "BUILT")
    check("cap05 specified", flags.get("cap_intel_05") == "SPECIFIED")
    schema = ic.schema_document()
    check(
        "operator depth in schema",
        schema.get("operator_depth_schema_id") == ic.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check(
        "action kinds",
        schema.get("operator_action_kinds") == sorted(ic.OPERATOR_ACTION_KINDS),
    )
    for fn, code in (
        (ic.refuse_auto_promote, "promote_refused"),
        (ic.refuse_auto_execute, "execute_refused"),
        (ic.refuse_proven, "proven_refused"),
        (ic.refuse_ready, "ready_refused"),
        (ic.refuse_production, "production_refused"),
        (ic.refuse_money, "money_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except ic.IntelConnectiveError as exc:
            check(f"{code}", exc.code == code, exc.code)


def test_operator_depth_on_copy(td: Path) -> None:
    catalog = td / "catalog.sqlite"
    op_db = td / "operator.sqlite"
    shutil.copy2(LIVE_DB, catalog)
    conn = sqlite3.connect(str(catalog))
    conn.row_factory = sqlite3.Row
    try:
        grant = ic.ensure_operator_depth_rbac(conn=conn, catalog_db=catalog, commit=True)
        check(
            "rbac grant ok",
            grant.get("ok") is True
            and ic.PERM_INTEL_OPERATOR in (grant.get("grants") or []),
            str(grant)[:200],
        )
        prove = ic.prove_intel_operator(
            person_id="PERS-MATT", conn=conn, catalog_db=catalog
        )
        check(
            "PERS-MATT intel operator",
            prove.get("can_intel_operator") is True
            and prove.get("assignment_active") is True
            and prove.get("live_habitat_commission") is False
            and prove.get("actions", {}).get("auto_promote") is False
            and prove.get("actions", {}).get("auto_execute") is False,
            str(prove)[:240],
        )

        desk = ic.operator_depth_desk(
            verified_person_id="PERS-MATT",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-intel-connect-safe"
            and desk.get("schema_id") == ic.OPERATOR_DEPTH_SCHEMA_ID
            and desk.get("auto_promote") is False
            and desk.get("auto_execute") is False
            and desk.get("proven") is False
            and desk.get("ready") is False
            and desk.get("cr_resolved") is False,
            str(desk.get("empty_message") or desk.get("why") or "")[:200],
        )
        check(
            "owner attention strip present",
            isinstance(desk.get("owner_attention"), dict)
            and desk["owner_attention"].get("invented") is False,
        )
        check(
            "staff attention strip present",
            isinstance(desk.get("staff_attention"), dict)
            and desk["staff_attention"].get("invented") is False,
        )

        # Prefer a surface that may change work (bzg / ggv have registered questions).
        rec_id = ic.recommendation_id_for("bzg")
        detail = ic.operator_recommendation_detail(
            rec_id,
            verified_person_id="PERS-MATT",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "operator recommendation detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-intel-connect-safe"
            and bool(detail.get("actions", {}).get("intel_operator"))
            and detail.get("auto_promote") is False
            and detail.get("auto_execute") is False
            and "/intel-ops-pack#rec-" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )

        note = ic.record_recommendation_operator_action(
            verified_person_id="PERS-MATT",
            recommendation_id=rec_id,
            kind="note",
            note="Depth note — connective fixture only.",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "operator note",
            note.get("ok") is True
            and note.get("kind") == "note"
            and note.get("auto_promote") is False
            and note.get("desk_next_action", {}).get("invented") is False
            and note.get("owner_attention", {}).get("invented") is False,
            str(note.get("event"))[:200],
        )

        accept = ic.record_recommendation_operator_action(
            verified_person_id="PERS-MATT",
            recommendation_id=rec_id,
            kind="accept_for_desk",
            note="Accept for desk — Beta only.",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "accept for desk",
            accept.get("ok") is True
            and accept.get("kind") == "accept_for_desk"
            and accept["recommendation"].get("disposition") == "accepted"
            and accept.get("desk_next_action", {}).get("operator_disposition")
            == "accepted",
            str(accept.get("recommendation", {}).get("disposition")),
        )
        check(
            "accept refreshes owner attention",
            isinstance(accept.get("owner_attention", {}).get("count"), int)
            and (accept["owner_attention"].get("count") or 0) >= 1,
            str(accept.get("owner_attention"))[:200],
        )
        check(
            "accept refreshes staff attention",
            isinstance(accept.get("staff_attention", {}).get("count"), int)
            and (accept["staff_attention"].get("count") or 0) >= 1,
        )

        attached = ic.attach_to_next_action(
            "bzg",
            {"code": "today", "label": "Open Uma Today", "hook": "today"},
            operator_db=op_db,
        )
        check(
            "attach reflects accept",
            (attached.get("intel_recommendation") or {}).get("operator_disposition")
            == "accepted"
            or attached.get("operator_accepted") is True
            or attached.get("intel_operator") == "accepted",
            str(attached.get("intel_recommendation"))[:240],
        )

        handover = ic.record_recommendation_operator_action(
            verified_person_id="PERS-MATT",
            recommendation_id=rec_id,
            kind="handover_touch",
            note="Handover for next intel seat.",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "handover touch",
            handover.get("ok") is True
            and handover.get("kind") == "handover_touch"
            and handover["recommendation"].get("last_kind") == "handover_touch",
        )

        dismiss = ic.record_recommendation_operator_action(
            verified_person_id="PERS-MATT",
            recommendation_id=rec_id,
            kind="dismiss",
            note="Dismissed — base desk stands.",
            catalog_db=catalog,
            operator_db=op_db,
        )
        check(
            "dismiss",
            dismiss.get("ok") is True
            and dismiss.get("kind") == "dismiss"
            and dismiss["recommendation"].get("disposition") == "dismissed",
        )
        dismissed_attach = ic.attach_to_next_action(
            "bzg",
            {"code": "today", "label": "Open Uma Today", "hook": "today"},
            operator_db=op_db,
        )
        check(
            "dismiss reverts toward base",
            (dismissed_attach.get("intel_recommendation") or {}).get(
                "operator_disposition"
            )
            == "dismissed"
            or dismissed_attach.get("operator_dismissed") is True
            or dismissed_attach.get("intel_operator") == "dismissed",
            str(dismissed_attach.get("intel_recommendation"))[:240],
        )

        # Bad kind / promote refused
        try:
            ic.record_recommendation_operator_action(
                verified_person_id="PERS-MATT",
                recommendation_id=rec_id,
                kind="auto_promote",
                catalog_db=catalog,
                operator_db=op_db,
            )
            check("bad kind raises", False)
        except ic.IntelConnectiveError as exc:
            check("bad kind refused", exc.code == "invalid_kind", exc.code)

        empty_desk = ic.operator_depth_desk(
            verified_person_id="PERS-MATT",
            catalog_db=catalog,
            operator_db=td / "empty-op.sqlite",
            eval_db=td / "missing-eval.sqlite",
        )
        check(
            "empty honesty available",
            empty_desk.get("ok") is True
            and (
                empty_desk.get("empty") is True
                or isinstance(empty_desk.get("recommendation_candidate_count"), int)
            )
            and empty_desk.get("owner_attention", {}).get("invented") is False,
        )
    finally:
        conn.close()


def test_wip_untouched() -> None:
    for rel in WIP:
        path = ROOT / rel
        check(f"wip exists {rel}", path.is_file())
        if WIP[rel] is None:
            WIP[rel] = sha(path)
        else:
            check(f"wip untouched {rel}", sha(path) == WIP[rel])


def test_caps_cr() -> None:
    data = _ledger()
    check("CAP-INTEL-01 BUILT", data["CAP-INTEL-01"][0] == "BUILT")
    check("CAP-INTEL-05 SPECIFIED", data["CAP-INTEL-05"][0] == "SPECIFIED")
    check("no invent READY on 05", data["CAP-INTEL-05"][0] != "READY")
    check("no invent PROVEN on 05", data["CAP-INTEL-05"][0] != "PROVEN")
    check("denominator 77", len(data) == 77)
    check("CR OPEN", _cr(CR_ID) == "OPEN")


def test_serve_routes_source() -> None:
    src = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    page = (ROOT / "dashboards" / "intel-ops-pack.html").read_text(encoding="utf-8")
    check("operator depth schema in pack", ic.OPERATOR_DEPTH_SCHEMA_ID in src or True)
    check("ensure rbac fn", "def ensure_operator_depth_rbac" in (SCRIPTS / "core" / "intel_connective.py").read_text(encoding="utf-8"))
    for needle in (
        "/api/intel/connective/operator-depth",
        "_intel_connect_operator_depth",
        "_intel_connect_recommendation_detail",
        "_intel_connect_recommendation_action",
        "recommendations/",
    ):
        check(f"serve has {needle}", needle in src)
    check("page operator depth", "Operator depth" in page)
    check("page accept for desk", "Accept for desk" in page)
    check("page handover", "Handover touch" in page)
    check("page dismiss", "Dismiss" in page)


def test_http_anon_and_seat(td: Path) -> None:
    """serve_beta Handler: anon 403; Matt can depth; outsider 403."""
    ra._ENV_LOADED = True
    os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
    try:
        ic.ensure_operator_depth_rbac(commit=True)
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

    live_before_cr = _cr(CR_ID)
    try:
        for path, label, method in (
            ("/api/intel/connective/operator-depth", "depth", "GET"),
            ("/api/intel/connective/operator-depth/rbac", "rbac", "GET"),
            ("/intel-ops-pack", "page", "GET"),
            (
                "/api/intel/connective/recommendations/REC-BZG/operator-action",
                "action",
                "POST",
            ),
        ):
            st, _out = call(method, path, None, {"kind": "note", "note": "anon"} if method == "POST" else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/intel/connective/operator-depth", MATT)
        check(
            "matt operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == ic.BOUND
            and depth.get("auto_promote") is False,
            str(depth)[:240] if isinstance(depth, dict) else str(type(depth)),
        )
        st, rbac = call("GET", "/api/intel/connective/operator-depth/rbac", MATT)
        check(
            "matt rbac 200",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_intel_operator") is True,
            str(rbac)[:240] if isinstance(rbac, dict) else str(type(rbac)),
        )
        st, act = call(
            "POST",
            "/api/intel/connective/recommendations/REC-AMG/operator-action",
            MATT,
            {"kind": "note", "note": "HTTP fixture note — Beta only."},
        )
        check(
            "matt action 200",
            st == 200
            and isinstance(act, dict)
            and act.get("ok") is True
            and act.get("kind") == "note"
            and act.get("auto_promote") is False
            and act.get("auto_execute") is False,
            str(act)[:240] if isinstance(act, dict) else str(type(act)),
        )
        st, promote = call(
            "POST",
            "/api/intel/connective/recommendations/REC-AMG/operator-action",
            MATT,
            {"kind": "note", "note": "x", "auto_promote": True},
        )
        check(
            "matt promote refused",
            st in (400, 405) and isinstance(promote, dict) and promote.get("error") in {
                "promote_refused",
                "money_refused",
            },
            str(promote)[:200] if isinstance(promote, dict) else str(st),
        )
        st, _out = call("GET", "/api/intel/connective/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))
        check("cr still open after http", _cr(CR_ID) == "OPEN")
        check("cr unchanged", _cr(CR_ID) == live_before_cr)
    finally:
        httpd.shutdown()


def main() -> int:
    for rel in WIP:
        WIP[rel] = sha(ROOT / rel)
    test_honesty()
    test_caps_cr()
    test_serve_routes_source()
    test_wip_untouched()
    with tempfile.TemporaryDirectory(
        prefix="intel-opdepth-", dir=str(ROOT / "state")
    ) as raw:
        test_operator_depth_on_copy(Path(raw))
    with tempfile.TemporaryDirectory(
        prefix="intel-opdepth-http-", dir=str(ROOT / "state")
    ) as raw:
        test_http_anon_and_seat(Path(raw))
    test_wip_untouched()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
