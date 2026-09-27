#!/usr/bin/env python3
"""Sprint2 P9-v2 CORE Operator Depth — SOP/escalation detail + refresh."""
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

from core import core_mgmt_cluster as core  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CRS = (
    "CR-c4ed4e3fa9f15a40",
    "CR-6e3fd7b9d7edca0e",
    "CR-7a022a9394592c75",
)
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": None,
    "scripts/phase26_team.py": None,
    "scripts/skills/__init__.py": None,
    "scripts/wolf_intelligence.py": None,
}
OBJ_SOP = "sop_factory"
OBJ_ESC = "escalation_burndown"


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
    flags = core.honesty_flags()
    check("bound", flags.get("bound") == "beta-core-safe")
    check(
        "operator depth schema",
        flags.get("operator_depth_schema_id") == core.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check("empty operator honesty", flags.get("empty_operator_is_not_invent") is True)
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("no auto approve", flags.get("auto_approve_sop") is False)
    check("cr not resolved", flags.get("cr_resolved") is False)
    check("p9 v1 not unparked", flags.get("p9_v1_unparked") is False)
    schema = core.schema_document()
    check(
        "operator depth in schema",
        schema.get("operator_depth_schema_id") == core.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check(
        "action kinds",
        schema.get("core_operator_action_kinds") == sorted(core.CORE_OPERATOR_ACTION_KINDS),
    )
    check(
        "depth modules",
        schema.get("depth_modules") == list(core.DEPTH_MODULE_IDS),
    )
    for fn, code in (
        (core.refuse_proven, "proven_refused"),
        (core.refuse_ready, "ready_refused"),
        (core.refuse_production, "production_refused"),
        (core.refuse_money, "money_refused"),
        (core.refuse_cloudflare, "cloudflare_refused"),
        (core.refuse_commission, "commission_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except core.MgmtClusterError as exc:
            check(f"{code}", exc.code == code, exc.code)
    check(
        "refuse_code skips operator-action",
        core.refuse_code("/api/core/mgmt-cluster/objects/X/operator-action") is None,
    )
    check(
        "refuse_code skips operator-depth",
        core.refuse_code("/api/core/mgmt-cluster/operator-depth") is None,
    )
    check(
        "refuse_code still refuses proven",
        core.refuse_code("/api/core/mgmt-cluster/proven") == "proven",
    )


def test_operator_depth_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    op_db = td / "operator.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        grant = core.ensure_operator_depth_rbac(conn=conn, commit=True)
        check(
            "rbac grant ok",
            grant.get("ok") is True and core.PERM_CORE_OPERATOR in (grant.get("grants") or []),
            str(grant)[:200],
        )
        prove = core.prove_core_operator(person_id="PERS-MATT", conn=conn)
        check(
            "PERS-MATT core operator",
            prove.get("can_core_operator") is True
            and prove.get("assignment_active") is True
            and prove.get("cf_seat_mint") is False
            and prove.get("actions", {}).get("auto_approve") is False
            and prove.get("actions", {}).get("money") is False
            and prove.get("actions", {}).get("handover_touch") is True
            and prove.get("actions", {}).get("acknowledge") is True,
            str(prove)[:240],
        )

        desk = core.operator_depth_desk(
            verified_person_id="PERS-MATT",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-core-safe"
            and desk.get("schema_id") == core.OPERATOR_DEPTH_SCHEMA_ID
            and len(desk.get("object_candidates") or []) == 2
            and desk.get("auto_approve") is False
            and desk.get("money") is False
            and (desk.get("owner_empire") or {}).get("empty") is True
            and (desk.get("staff_needs_you") or {}).get("empty") is True,
            str(desk)[:240],
        )

        detail = core.operator_object_detail(
            OBJ_SOP,
            verified_person_id="PERS-MATT",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator sop detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-core-safe"
            and bool(detail.get("actions", {}).get("core_operator"))
            and detail.get("proven") is False
            and detail.get("auto_approve") is False
            and "/core-mgmt-cluster#core-obj-" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )

        note = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_SOP,
            kind="note",
            note="CORE depth note — SOP fixture only.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator note",
            note.get("ok") is True
            and note.get("kind") == "note"
            and note.get("proven") is False
            and note.get("money") is False
            and (note.get("staff_needs_you") or {}).get("empty") is False,
            str(note)[:240],
        )

        nxt = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_SOP,
            kind="next-action-touch",
            note="Review SOP draft approve gate with Owner.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator next_action alias",
            nxt.get("ok") is True
            and nxt.get("kind") == "next_action"
            and (nxt.get("object") or {}).get("recorded_next_action")
            == "Review SOP draft approve gate with Owner."
            and (nxt.get("core_desk_next_action") or {}).get("empty") is False,
            str(nxt.get("object"))[:200],
        )

        ack = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_SOP,
            kind="acknowledge",
            note="Acknowledged SOP factory waiting strip — not live.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator acknowledge",
            ack.get("ok") is True
            and ack.get("kind") == "acknowledge"
            and (ack.get("staff_needs_you") or {}).get("caps_raised") is False,
        )

        esc = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_ESC,
            kind="escalate-touch",
            note="Escalate burn-down attention — counters not independence.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator escalate",
            esc.get("ok") is True
            and esc.get("kind") == "escalate_touch"
            and (esc.get("owner_empire") or {}).get("empty") is False
            and any(
                "escalate_touch" in (i.get("reasons") or [])
                for i in ((esc.get("owner_empire") or {}).get("items") or [])
            ),
            str(esc.get("owner_empire"))[:200],
        )

        ho = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_ESC,
            kind="handover-touch",
            note="Handover escalation burn-down review to Owner.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator handover",
            ho.get("ok") is True
            and ho.get("kind") == "handover_touch"
            and (ho.get("owner_empire") or {}).get("empty") is False
            and any(
                "handover_touch" in (i.get("reasons") or [])
                for i in ((ho.get("owner_empire") or {}).get("items") or [])
            ),
            str(ho.get("owner_empire"))[:200],
        )

        dismiss = core.record_core_operator_action(
            verified_person_id="PERS-MATT",
            object_id=OBJ_ESC,
            kind="dismiss-noise",
            note="Escalation noise dismissed — not invent PROVEN.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator dismiss",
            dismiss.get("ok") is True
            and dismiss.get("kind") == "dismiss_noise"
            and (dismiss.get("object") or {}).get("dismissed") is True,
        )
        desk2 = core.operator_depth_desk(
            verified_person_id="PERS-MATT",
            catalog_db=db,
            operator_db=op_db,
        )
        cand_ids = [c.get("object_id") for c in (desk2.get("object_candidates") or [])]
        check(
            "dismiss drops candidate",
            OBJ_ESC not in cand_ids and OBJ_SOP in cand_ids and len(cand_ids) == 1,
            str(cand_ids),
        )

        try:
            core.record_core_operator_action(
                verified_person_id="PERS-MATT",
                object_id=OBJ_SOP,
                kind="auto-approve",
                note="no",
                catalog_db=db,
                operator_db=op_db,
            )
            check("invalid auto-approve kind refused", False)
        except core.MgmtClusterError as exc:
            check("invalid auto-approve kind refused", exc.code == "invalid_kind", exc.code)

        try:
            core.operator_object_detail(
                "core_harden",
                verified_person_id="PERS-MATT",
                catalog_db=db,
                operator_db=op_db,
            )
            check("harden not in depth", False)
        except core.MgmtClusterError as exc:
            check("harden not in depth", exc.code == "not_found", exc.code)

        for cr in CRS:
            check(f"cr {cr} still open on copy", _cr(cr, db) == "OPEN")
    finally:
        conn.close()


def test_static_and_caps() -> None:
    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "_core_mgmt_operator_depth",
        "_core_mgmt_operator_depth_rbac",
        "_core_mgmt_object_operator_detail",
        "_core_mgmt_object_operator_action",
        "/api/core/mgmt-cluster/operator-depth",
        "objects/([^/]+)/operator-action",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "core-mgmt-cluster.html").read_text(encoding="utf-8")
    check("page operator depth", "Operator depth" in page)
    check("page operator-action", "operator-action" in page)
    check(
        "page no invent",
        "no invent" in page.lower() or "No invent" in page,
    )
    before = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in before.items():
        WIP[rel] = digest
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    check("CAP-CORE-11 specified", ledger.get("CAP-CORE-11", [None])[0] == "SPECIFIED")
    check("CAP-CORE-12 built", ledger.get("CAP-CORE-12", [None])[0] == "BUILT")
    for cr in CRS:
        check(f"live {cr} open", _cr(cr) == "OPEN")
    check("denominator 77", len(ledger) == 77)


def test_api() -> None:
    ra._ENV_LOADED = True
    os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
    try:
        core.ensure_operator_depth_rbac(commit=True)
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

    try:
        for path, label, method in (
            ("/api/core/mgmt-cluster/operator-depth", "depth", "GET"),
            ("/api/core/mgmt-cluster/operator-depth/rbac", "rbac", "GET"),
            ("/core-mgmt-cluster", "page", "GET"),
            (
                f"/api/core/mgmt-cluster/objects/{OBJ_SOP}/operator-action",
                "action",
                "POST",
            ),
        ):
            st, _ = call(method, path, None, {} if method == "POST" else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/core/mgmt-cluster/operator-depth", MATT)
        check(
            "matt operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == "beta-core-safe"
            and depth.get("cf_seat_mint") is False
            and (depth.get("rbac") or {}).get("can_core_operator") is True,
            str(depth)[:240] if isinstance(depth, dict) else str(st),
        )
        st, rbac = call("GET", "/api/core/mgmt-cluster/operator-depth/rbac", MATT)
        check(
            "matt rbac prove",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_core_operator") is True
            and rbac.get("actions", {}).get("auto_approve") is False,
            str(rbac)[:200] if isinstance(rbac, dict) else str(st),
        )
        st, detail = call(
            "GET",
            f"/api/core/mgmt-cluster/objects/{OBJ_ESC}/operator",
            MATT,
        )
        check(
            "matt escalation operator detail",
            st == 200
            and isinstance(detail, dict)
            and detail.get("ok") is True
            and detail.get("proven") is False,
            str(detail)[:200] if isinstance(detail, dict) else str(st),
        )
        st, blank = call(
            "POST",
            f"/api/core/mgmt-cluster/objects/{OBJ_SOP}/operator-action",
            MATT,
            {"kind": "note", "note": ""},
        )
        check(
            "matt note validates",
            st in (400, 403) and isinstance(blank, dict),
            f"{st} {str(blank)[:120]}",
        )
        st, refused = call(
            "POST",
            f"/api/core/mgmt-cluster/objects/{OBJ_SOP}/operator-action",
            MATT,
            {"kind": "note", "note": "x", "proven": True},
        )
        check(
            "matt proven body refused",
            st in (403, 405) and isinstance(refused, dict),
            f"{st} {str(refused)[:120]}",
        )
        st, _anon_act = call(
            "POST",
            f"/api/core/mgmt-cluster/objects/{OBJ_SOP}/operator-action",
            None,
            {"kind": "note", "note": "anon"},
        )
        check("anon operator-action 403", st == 403, str(st))
        st, _out = call("GET", "/api/core/mgmt-cluster/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))
        st, _staff = call("GET", "/api/core/mgmt-cluster/operator-depth", AMANDA)
        check("amanda depth 403", st == 403, str(st))
        st, page = call("GET", "/core-mgmt-cluster", MATT)
        check(
            "matt page 200",
            st == 200 and isinstance(page, (bytes, str)),
            str(st),
        )
    finally:
        httpd.shutdown()
        httpd.server_close()

    after = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in WIP.items():
        check(f"wip untouched {Path(rel).name}", after.get(rel) == digest)


def main() -> int:
    test_honesty()
    with tempfile.TemporaryDirectory(prefix="core-opdepth-") as tmp:
        test_operator_depth_on_copy(Path(tmp))
    test_static_and_caps()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
